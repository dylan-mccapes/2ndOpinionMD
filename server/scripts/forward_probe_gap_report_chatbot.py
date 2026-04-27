#!/usr/bin/env python3
"""Terminal chatbot: probe (3.2) → gap (8B) → report (8B).

**Probe** (default ``eoh-llama3.2-source-router``):

- Scans ``metadata.code_index`` **before** the source-router (same rows as
  ``code_index_lookup``): every bucket/key with first/last observation dates
  and event counts. The router and graph-picker receive a JSON slice that fits
  their context budget; GAP/REPORT get the full inventory on the probe bundle.
- Calls the source-router planner (same stack as MKG harness) to produce
  ``semantic_query`` (MKG dense lane) and ``ts_terms`` (Postgres FTS lane).
- Second 3.2 call chooses exactly one PTV graph tool + JSON args.
- Executes: MKG semantic + per-term TS, PTV ``semantic_search`` with the
  router's semantic string, and the chosen graph tool.

**Gap** (default ``eoh-llama``):

- Consumes probe bundle; may request at most one extra PTV semantic query,
  up to two additional TS terms, and one follow-up graph tool.
- Emits a structured ``gap_report`` plus optional follow-up tool results.
- If the model leaves all follow fields empty but ``mkg_jaccard`` is 0.0 with
  both MKG lanes populated, a small heuristic adds TS terms from the user
  question or an enriched PTV semantic query (disable with ``--no-gap-heuristic``).

**Report** (default ``eoh-llama``):

- Synthesizes a single markdown answer from probe + gap context (no tools).

Env: same DB/embed/Ollama as ``mkg_retrieval_harness`` (``SYNC_DATABASE_URL``,
``LOCAL_EMBED_MODEL``, ``OLLAMA_URL``). If no DSN, MKG lanes are skipped with a
notice; PTV-only still works.

Examples::

    python server/scripts/forward_probe_gap_report_chatbot.py
    python server/scripts/forward_probe_gap_report_chatbot.py --graph path/to/ptv.json
    python server/scripts/forward_probe_gap_report_chatbot.py --no-mkg
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.mkg.router_planner import plan_route
from server.ptv_toolkit.code_inventory import (
    build_patient_code_inventory,
    fit_code_inventory_to_budget,
    strip_n_events,
)
from server.ptv_toolkit.graph import load_graph
from server.ptv_toolkit.registry import call_tool


def _log(emoji: str, msg: str) -> None:
    print(f"{emoji} {msg}", file=sys.stderr, flush=True)

DEFAULT_GRAPH = (
    ROOT
    / "artifacts"
    / "forward_kaleb_package_20260423"
    / "synthetic_pro_cohort"
    / "ptv_synth_P1_early_responder.json"
)

_GRAPH_TOOLS = [
    "graph_stats",
    "list_event_types",
    "code_index_lookup",
    "semantic_search",
    "bfs_expand",
    "temporal_scan",
    "get_event",
]

_BLOCK_RX = re.compile(r"\{.*\}", re.DOTALL)


def _mkg_dsn() -> Optional[str]:
    for k in ("SYNC_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL"):
        v = os.environ.get(k)
        if v and v.strip():
            return v.strip()
    return None


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    s = (text or "").strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL | re.IGNORECASE)
    if fence:
        try:
            return json.loads(fence.group(1))
        except Exception:
            pass
    m = _BLOCK_RX.search(s)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def _extract_first_json_object(text: str) -> Optional[Dict[str, Any]]:
    """First top-level JSON object in text (handles prose before/after JSON)."""
    dec = json.JSONDecoder()
    s = text or ""
    for i, ch in enumerate(s):
        if ch != "{":
            continue
        try:
            obj, _end = dec.raw_decode(s, i)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    return None


_GAP_STOP = {
    "with",
    "from",
    "that",
    "this",
    "have",
    "what",
    "does",
    "when",
    "where",
    "tell",
    "about",
    "please",
    "any",
    "especially",
    "patient",
    "clinical",
    "medications",
    "medication",
    "confounders",
    "confounder",
}


def _probe_metrics(probe_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Compact stats for GAP prompting and heuristic follow-ups."""
    mkg = probe_bundle.get("mkg") or {}
    if mkg.get("skipped"):
        return {
            "mkg_skipped": True,
            "mkg_jaccard": None,
            "mkg_semantic_hits": 0,
            "mkg_ts_hits": 0,
            "mkg_ok": False,
            "ptv_semantic_result_count": 0,
        }
    ov = mkg.get("overlap") or {}
    j_raw = ov.get("jaccard")
    try:
        j = float(j_raw) if j_raw is not None else 0.0
    except (TypeError, ValueError):
        j = 0.0
    n_sem = len(mkg.get("semantic_hits") or [])
    n_ts = len(mkg.get("ts_hits") or [])
    mkg_ok = bool(mkg.get("ok", True))
    ptv_wr = probe_bundle.get("ptv_semantic_search") or {}
    res = (ptv_wr.get("result") or {}) if ptv_wr.get("ok") else {}
    n_ptv = len(res.get("results") or []) if isinstance(res, dict) else 0
    return {
        "mkg_skipped": False,
        "mkg_jaccard": j,
        "mkg_semantic_hits": n_sem,
        "mkg_ts_hits": n_ts,
        "mkg_ok": mkg_ok,
        "ptv_semantic_result_count": n_ptv,
    }


def _norm_gap_follow_field(val: Any) -> Any:
    """Treat JSON-ish string 'null' / empty as absent."""
    if val is None:
        return None
    if isinstance(val, str) and val.strip().lower() in ("", "null", "none", "undefined"):
        return None
    return val


def _heuristic_ts_terms_from_question(
    question: str,
    router_terms: List[str],
    *,
    max_terms: int = 2,
) -> List[str]:
    """Extra TS tokens from the user question (avoid duplicating router terms)."""
    rt = {t.strip().lower() for t in router_terms if t and str(t).strip()}
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", question)
    out: List[str] = []
    for t in tokens:
        low = t.lower()
        if low in _GAP_STOP or low in rt:
            continue
        out.append(t)
        if len(out) >= max_terms:
            break
    return out


def _ollama_chat(
    *,
    url: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": max(2048, int(num_ctx))},
    }
    r = requests.post(f"{url.rstrip('/')}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    return (r.json().get("message") or {}).get("content") or ""


def _router_sources(plan: Dict[str, Any]) -> Optional[List[str]]:
    rows = plan.get("selected_sources") or []
    out = []
    for r in rows:
        if isinstance(r, dict) and r.get("source"):
            out.append(str(r["source"]).strip().lower())
    return out or None


def _mkg_retrieve_bundle(
    *,
    semantic_query: str,
    ts_terms: List[str],
    top_k: int,
    embed_model: str,
    sources: Optional[List[str]],
    text_chars: int,
) -> Dict[str, Any]:
    from server.scripts.mkg_retrieval_harness import (  # type: ignore
        ann_local,
        bm25_ts_terms,
        embed_query,
        _compact_hit,
        _overlap,
        _vec_literal,
    )

    dsn = _mkg_dsn()
    if not dsn:
        _log("🗄️", "MKG retrieve skipped: no SYNC_DATABASE_URL / DATABASE_URL")
        return {
            "ok": False,
            "error": "no_database_url",
            "semantic_hits": [],
            "ts_hits": [],
        }
    import psycopg
    from psycopg.rows import dict_row

    _log("🧠", f"MKG embed+retrieve top_k={top_k} ts_terms={len(ts_terms or [])} sources={sources or 'all'}")
    vec, device = embed_query(embed_model, semantic_query or "")
    lit = _vec_literal(vec)
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '120s';")
            sem_rows = ann_local(cur, lit, top_k, sources=sources)
            ts_rows = bm25_ts_terms(cur, ts_terms, top_k, sources=sources) if ts_terms else []
    sem_c = [_compact_hit(r, text_chars=text_chars) for r in sem_rows]
    ts_c = [_compact_hit(r, text_chars=text_chars) for r in ts_rows]
    overlap = _overlap([h["id"] for h in sem_c], [h["id"] for h in ts_c])
    _log("📚", f"MKG done semantic_hits={len(sem_c)} ts_hits={len(ts_c)} jaccard={overlap.get('jaccard', 0):.3f}")
    return {
        "ok": True,
        "embed_device": device,
        "semantic_hits": sem_c,
        "ts_hits": ts_c,
        "overlap": overlap,
        "ts_terms_used": list(ts_terms or []),
    }


def _pick_graph_tool(
    *,
    question: str,
    router_plan: Dict[str, Any],
    graph_brief: str,
    patient_code_inventory: Optional[Dict[str, Any]],
    ollama_url: str,
    model: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
) -> Tuple[str, Dict[str, Any]]:
    system = (
        "You are a PTV graph routing assistant. Return STRICT JSON only, one object, no markdown.\n"
        "Pick exactly ONE tool from this list and provide args:\n"
        + ", ".join(_GRAPH_TOOLS)
        + "\n\nSchema:\n"
        '{"graph_tool":"<name>","graph_args":{...}}\n'
        "Rules:\n"
        "- patient_code_inventory (when present) already lists codes on this timeline with date spans;\n"
        "  prefer semantic_search, temporal_scan, bfs_expand, or code_index_lookup **detail** (exact key / contains)\n"
        "  over repeating a full-bucket list_keys unless the user needs a fresh slice.\n"
        "- graph_args must match the tool (see toolkit hints below).\n"
        "- Prefer semantic_search with an expanded clinical query, temporal_scan for date windows,\n"
        "  code_index_lookup for drug/ICD/RxNorm/LOINC strings, bfs_expand only if you have seed event_ids,\n"
        "  graph_stats or list_event_types for orientation.\n"
        "- Do not invent event_ids.\n\n"
        "Arg hints:\n"
        "- semantic_search: query (required), k optional default 12.\n"
        "- temporal_scan: start, end (ISO), event_types optional, query optional, limit optional.\n"
        "- code_index_lookup: bucket (drugs|rxnorm|icd|labs|loinc), key or key_contains, limit.\n"
        "- bfs_expand: seed_event_ids (list), depth, max_events, edge_kinds optional.\n"
        "- get_event: event_id.\n"
        "- graph_stats / list_event_types: {}.\n"
    )
    payload: Dict[str, Any] = {
        "user_question": question,
        "router_plan_summary": {
            "question_type": router_plan.get("question_type"),
            "semantic_query": router_plan.get("semantic_query"),
            "ts_terms": router_plan.get("ts_terms"),
        },
        "graph_orientation": graph_brief[:6000],
    }
    if patient_code_inventory is not None:
        payload["patient_code_inventory"] = patient_code_inventory
    user = json.dumps(payload, ensure_ascii=False, indent=2)
    _log("🧭", f"Probe graph-pick model={model} num_ctx={num_ctx}")
    raw = _ollama_chat(
        url=ollama_url,
        model=model,
        system=system,
        user=user,
        temperature=temperature,
        timeout=timeout,
        num_ctx=num_ctx,
    )
    parsed = _extract_first_json_object(raw) or _extract_json(raw) or {}
    name = str(parsed.get("graph_tool") or "").strip()
    args = parsed.get("graph_args") if isinstance(parsed.get("graph_args"), dict) else {}
    if name not in _GRAPH_TOOLS:
        _log("⚠️", f"Graph pick parse miss len={len(raw)} — defaulting to semantic_search")
        return "semantic_search", {"query": question, "k": 12}
    _log("🎯", f"Graph pick → {name} args_keys={list((args or {}).keys())}")
    return name, dict(args or {})


def _gap_phase(
    *,
    question: str,
    probe_bundle: Dict[str, Any],
    gh: Any,
    ollama_url: str,
    model: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
    top_k: int,
    embed_model: str,
    gap_sources: Optional[List[str]],
    text_chars: int,
    gap_heuristic: bool = True,
) -> Dict[str, Any]:
    metrics = _probe_metrics(probe_bundle)
    system = (
        "You are the GAP agent for a hybrid PTV + MKG retrieval pipeline.\n"
        "You receive JSON: user question, probe_metrics (summary), full probe bundle (MKG + PTV + graph).\n"
        "The probe bundle includes pre_router_code_inventory when enabled: indexed patient codes\n"
        "with first/last dates (from metadata.code_index) — use for gap analysis and follow-ups.\n\n"
        "OUTPUT: Reply with a SINGLE JSON object only. No markdown fences, no prose before or after.\n"
        "Schema:\n"
        "{\n"
        '  "follow_ptv_semantic_query": null,\n'
        '  "follow_ts_terms": [],\n'
        '  "follow_graph_tool": null,\n'
        '  "follow_graph_args": {},\n'
        '  "gap_report": "required markdown string"\n'
        "}\n"
        f"follow_graph_tool must be null or one of: {', '.join(_GRAPH_TOOLS)}.\n\n"
        "Rules:\n"
        "- probe_metrics.mkg_jaccard is overlap between dense (semantic) and BM25 (ts_terms) hit *ids*.\n"
        "  If mkg_jaccard is 0.0 but both mkg_semantic_hits and mkg_ts_hits are > 0, the two lanes disagree;\n"
        "  you SHOULD set at least one of: follow_ts_terms (1–2 NEW tokens from the user question),\n"
        "  follow_ptv_semantic_query (narrower retrieval), or follow_graph_tool (e.g. code_index_lookup on drugs).\n"
        "- follow_ts_terms: at most TWO strings; prefer tokens the user said explicitly that probe ts_terms may have missed.\n"
        "- follow_ptv_semantic_query: optional ONE extra PTV semantic query if probe PTV context is thin or user asks new angles.\n"
        "- follow_graph_tool: optional ONE extra graph tool; use null if not needed.\n"
        "- gap_report is REQUIRED: what probe covered, gaps, contradictions, what evidence is still missing.\n"
        "- Keep gap_report under 400 words.\n"
    )
    user = json.dumps(
        {
            "user_question": question,
            "probe_metrics": metrics,
            "probe": probe_bundle,
        },
        default=str,
        indent=2,
    )[:120000]
    _log("🔎", f"Stage GAP model={model} num_ctx={num_ctx} user_json_chars={len(user)}")
    raw = _ollama_chat(
        url=ollama_url,
        model=model,
        system=system,
        user=user,
        temperature=temperature,
        timeout=timeout,
        num_ctx=num_ctx,
    )
    _log("🔎", f"GAP raw response chars={len(raw)} preview={raw[:120]!r}…")

    parsed = _extract_first_json_object(raw) or _extract_json(raw) or {}
    if not parsed:
        _log("⚠️", "GAP JSON parse failed — using raw text as gap_report fallback")
    follow_sem = _norm_gap_follow_field(parsed.get("follow_ptv_semantic_query"))
    if not isinstance(follow_sem, str):
        follow_sem = None
    follow_terms = parsed.get("follow_ts_terms") or []
    if not isinstance(follow_terms, list):
        follow_terms = []
    follow_terms = [
        str(t).strip()
        for t in follow_terms
        if str(t).strip() and str(t).strip().lower() not in ("null", "none")
    ][:2]
    fg_tool = _norm_gap_follow_field(parsed.get("follow_graph_tool"))
    fg_args = parsed.get("follow_graph_args") if isinstance(parsed.get("follow_graph_args"), dict) else {}
    gap_report = str(parsed.get("gap_report") or "").strip()
    if not gap_report:
        gap_report = (raw or "").strip() or "(no gap_report)"
        if gap_report != "(no gap_report)":
            gap_report = "[gap JSON unparsed — model prose below]\n\n" + gap_report[:12000]

    model_wants_graph = bool(fg_tool and str(fg_tool).strip() in _GRAPH_TOOLS)
    model_wants_any = bool(follow_terms) or bool(follow_sem and follow_sem.strip()) or model_wants_graph

    if gap_heuristic and not model_wants_any and metrics.get("mkg_ok") and not metrics.get("mkg_skipped"):
        j = float(metrics.get("mkg_jaccard") or 0.0)
        n_sem = int(metrics.get("mkg_semantic_hits") or 0)
        n_ts = int(metrics.get("mkg_ts_hits") or 0)
        if j == 0.0 and n_sem > 0 and n_ts > 0:
            router_ts = list((probe_bundle.get("router_plan") or {}).get("ts_terms") or [])
            extra = _heuristic_ts_terms_from_question(question, router_ts)
            if extra:
                follow_terms = extra
                _log(
                    "🔧",
                    "Heuristic GAP: mkg_jaccard=0 with both lanes populated → "
                    f"follow_ts_terms={follow_terms!r}",
                )
            else:
                follow_sem = (question.strip() + " medications drugs concomitant confounding adverse reactions")[:400]
                _log(
                    "🔧",
                    "Heuristic GAP: mkg_jaccard=0, no extra question tokens → "
                    "follow_ptv_semantic_query (enriched)",
                )

    follow_mkg: Dict[str, Any] = {}
    if follow_terms:
        _log("🔁", f"GAP follow-up MKG ts_terms={follow_terms!r}")
        sq = str(follow_sem or probe_bundle.get("router_plan", {}).get("semantic_query") or question)
        follow_mkg = _mkg_retrieve_bundle(
            semantic_query=sq,
            ts_terms=follow_terms,
            top_k=top_k,
            embed_model=embed_model,
            sources=gap_sources,
            text_chars=text_chars,
        )

    follow_ptv = None
    if isinstance(follow_sem, str) and follow_sem.strip():
        _log("🔁", "GAP follow-up PTV semantic_search")
        follow_ptv = call_tool("semantic_search", gh, {"query": follow_sem.strip(), "k": 12})

    follow_graph = None
    if fg_tool and str(fg_tool).strip() in _GRAPH_TOOLS:
        _log("🔁", f"GAP follow-up graph tool={fg_tool!r}")
        follow_graph = call_tool(str(fg_tool).strip(), gh, dict(fg_args or {}))

    if not follow_mkg and not follow_ptv and not follow_graph:
        if model_wants_graph and fg_tool:
            _log("⚠️", f"GAP follow_graph_tool not executed (invalid tool?): {fg_tool!r}")
        else:
            _log("⏭️", "GAP: no follow-up MKG/PTV/graph executions")

    _log("✅", f"GAP phase done gap_report_chars={len(gap_report)}")
    return {
        "raw_gap_json": parsed,
        "raw_gap_text": raw[:20000],
        "gap_report": gap_report,
        "follow_ptv_semantic": follow_ptv,
        "follow_mkg": follow_mkg,
        "follow_graph": follow_graph,
        "probe_metrics": metrics,
    }


def _report_phase(
    *,
    question: str,
    probe_bundle: Dict[str, Any],
    gap_bundle: Dict[str, Any],
    ollama_url: str,
    model: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
) -> str:
    system = (
        "You are a clinical synthesis assistant. You receive structured JSON from a "
        "probe→gap hybrid run (PTV graph tools + MKG rag_corpus hits). "
        "probe_context may include pre_router_code_inventory (patient codes + date spans). "
        "Produce one markdown answer to the user question.\n\n"
        "Rules:\n"
        "- Ground claims in supplied hit ids (MKG: id/source; PTV: event_ids from tool results).\n"
        "- Cite uncertainty where evidence is thin.\n"
        "- Do not describe internal pipeline stage names unless useful; focus on patient-relevant synthesis.\n"
        "- Keep under 900 words unless the question requires detail.\n"
    )
    payload = {
        "user_question": question,
        "probe_context": probe_bundle,
        "gap_context": gap_bundle,
    }
    user = json.dumps(payload, default=str, indent=2)[:120000]
    _log("📝", f"Stage REPORT model={model} num_ctx={num_ctx} context_chars={len(user)}")
    out = _ollama_chat(
        url=ollama_url,
        model=model,
        system=system,
        user=user,
        temperature=temperature,
        timeout=timeout,
        num_ctx=num_ctx,
    )
    _log("✅", f"REPORT done out_chars={len(out or '')}")
    return out


def _run_probe(
    *,
    question: str,
    gh: Any,
    ollama_url: str,
    probe_model: str,
    probe_num_ctx: int,
    temperature: float,
    timeout: float,
    top_k: int,
    embed_model: str,
    enable_mkg: bool,
    text_chars: int,
    enable_code_inventory: bool,
    code_inventory_compact: bool,
    code_inventory_router_json_max: int,
    code_inventory_graph_json_max: int,
) -> Dict[str, Any]:
    inv_full: Optional[Dict[str, Any]] = None
    inv_for_router: Optional[Dict[str, Any]] = None
    inv_for_graph: Optional[Dict[str, Any]] = None
    if enable_code_inventory:
        _log("📇", "Stage PROBE — patient code_index inventory (pre-router; same index as code_index_lookup)")
        inv_full = build_patient_code_inventory(gh)
        slim_base = strip_n_events(inv_full) if code_inventory_compact else inv_full
        inv_for_router = fit_code_inventory_to_budget(slim_base, code_inventory_router_json_max)
        inv_for_graph = fit_code_inventory_to_budget(slim_base, code_inventory_graph_json_max)
        _log(
            "📇",
            "code_index inventory "
            f"n_keys={inv_full.get('n_keys_total')} "
            f"router_slice_json={len(json.dumps(inv_for_router, ensure_ascii=True))} "
            f"graph_pick_slice_json={len(json.dumps(inv_for_graph, ensure_ascii=True))}",
        )

    _log("🛰️", "Stage PROBE — graph_stats for router clinical_context")
    graph_stats = call_tool("graph_stats", gh, {})
    brief = json.dumps(graph_stats.get("result") or graph_stats, default=str)[:8000]

    _log("🧭", "Stage PROBE — plan_route (semantic_query + ts_terms + sources)")
    route = plan_route(
        question,
        ollama_url=ollama_url,
        model=probe_model,
        num_ctx=probe_num_ctx,
        timeout=timeout,
        temperature=temperature,
        clinical_context=brief,
        patient_code_inventory=inv_for_router,
    )
    sources = _router_sources(route)
    _log(
        "🧭",
        f"Router qtype={route.get('question_type')} ts_terms={len(route.get('ts_terms') or [])} "
        f"sources={len(sources or [])}",
    )

    mkg: Dict[str, Any] = {"skipped": True}
    if enable_mkg:
        mkg = _mkg_retrieve_bundle(
            semantic_query=str(route.get("semantic_query") or question),
            ts_terms=list(route.get("ts_terms") or []),
            top_k=top_k,
            embed_model=embed_model,
            sources=sources,
            text_chars=text_chars,
        )
    else:
        _log("⏭️", "Stage PROBE — MKG skipped (--no-mkg)")

    g_tool, g_args = _pick_graph_tool(
        question=question,
        router_plan=route,
        graph_brief=brief,
        patient_code_inventory=inv_for_graph,
        ollama_url=ollama_url,
        model=probe_model,
        temperature=temperature,
        timeout=timeout,
        num_ctx=probe_num_ctx,
    )
    _log("🔧", f"Stage PROBE — graph tool call {g_tool}")
    graph_out = call_tool(g_tool, gh, g_args)
    if not graph_out.get("ok"):
        _log("⚠️", f"Graph tool error: {graph_out.get('error', graph_out)}")

    _log("🔍", "Stage PROBE — PTV semantic_search (router semantic_query)")
    ptv_sem = call_tool(
        "semantic_search",
        gh,
        {"query": str(route.get("semantic_query") or question), "k": min(16, top_k + 2)},
    )
    if not ptv_sem.get("ok"):
        _log("⚠️", f"PTV semantic_search error: {ptv_sem.get('error', ptv_sem)}")

    _log("✅", "Stage PROBE complete")
    return {
        "router_plan": route,
        "mkg": mkg,
        "ptv_semantic_search": ptv_sem,
        "graph_tool": g_tool,
        "graph_args": g_args,
        "graph_tool_result": graph_out,
        "pre_router_code_inventory": inv_full,
    }


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graph", type=Path, default=DEFAULT_GRAPH, help="PTV JSON graph path.")
    ap.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    ap.add_argument("--probe-model", default=os.environ.get("EOH_SOURCE_ROUTER_MODEL", "eoh-llama3.2-source-router"))
    ap.add_argument("--probe-num-ctx", type=int, default=int(os.environ.get("OLLAMA_ROUTER_NUM_CTX", "8192")))
    ap.add_argument("--gap-model", default=os.environ.get("FORWARD_GAP_MODEL", "eoh-llama"))
    ap.add_argument("--report-model", default=os.environ.get("FORWARD_SYNTH_MODEL", "eoh-llama"))
    ap.add_argument("--gap-num-ctx", type=int, default=int(os.environ.get("OLLAMA_AGENT_NUM_CTX", "32768")))
    ap.add_argument("--report-num-ctx", type=int, default=int(os.environ.get("OLLAMA_SYNTH_NUM_CTX", "32768")))
    ap.add_argument("--temperature", type=float, default=0.15)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--top-k", type=int, default=8)
    ap.add_argument("--embed-model", default=os.environ.get("LOCAL_EMBED_MODEL", "BAAI/bge-base-en-v1.5"))
    ap.add_argument("--text-chars", type=int, default=400)
    ap.add_argument("--no-mkg", action="store_true", help="Skip MKG DB retrieval (PTV + graph pick only).")
    ap.add_argument(
        "--no-gap-heuristic",
        action="store_true",
        help="Disable deterministic GAP follow-ups when mkg_jaccard=0 and the model returned no follow fields.",
    )
    ap.add_argument(
        "--no-code-inventory",
        action="store_true",
        help="Do not scan metadata.code_index before the source router (ablation).",
    )
    ap.add_argument(
        "--code-inventory-compact",
        action="store_true",
        help="Omit n_events per code in JSON sent to router / graph-picker only; probe still stores full rows.",
    )
    ap.add_argument(
        "--code-inventory-router-json-max",
        type=int,
        default=int(os.environ.get("ROUTER_CODE_INVENTORY_MAX_JSON", "14000")),
        metavar="N",
        help="Max JSON chars for patient_code_inventory embedded in plan_route user payload.",
    )
    ap.add_argument(
        "--code-inventory-graph-json-max",
        type=int,
        default=8000,
        metavar="N",
        help="Max JSON chars for patient_code_inventory in probe graph-picker user payload.",
    )
    return ap.parse_args()


def main() -> int:
    args = _parse_args()
    path = args.graph.expanduser().resolve()
    if not path.is_file():
        print(f"error: graph not found: {path}", file=sys.stderr)
        return 2

    gh = load_graph(path)
    print(f"Loaded {path.name} events={len(gh.events)} hash={gh.graph_hash}")
    print(f"probe={args.probe_model} gap={args.gap_model} report={args.report_model}")
    print("Commands: quit | exit | q\n")

    while True:
        try:
            q = input("hybrid> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0
        if not q or q.lower() in {"quit", "exit", "q"}:
            print("bye")
            return 0

        try:
            _log("💬", f"User question ({len(q)} chars): {q[:100]}{'…' if len(q) > 100 else ''}")
            probe = _run_probe(
                question=q,
                gh=gh,
                ollama_url=args.ollama_url,
                probe_model=args.probe_model,
                probe_num_ctx=args.probe_num_ctx,
                temperature=args.temperature,
                timeout=args.timeout,
                top_k=args.top_k,
                embed_model=args.embed_model,
                enable_mkg=not args.no_mkg,
                text_chars=args.text_chars,
                enable_code_inventory=not args.no_code_inventory,
                code_inventory_compact=args.code_inventory_compact,
                code_inventory_router_json_max=args.code_inventory_router_json_max,
                code_inventory_graph_json_max=args.code_inventory_graph_json_max,
            )
            gap_sources = _router_sources(probe.get("router_plan") or {})
            gap = _gap_phase(
                question=q,
                probe_bundle=probe,
                gh=gh,
                ollama_url=args.ollama_url,
                model=args.gap_model,
                temperature=args.temperature,
                timeout=args.timeout,
                num_ctx=args.gap_num_ctx,
                top_k=args.top_k,
                embed_model=args.embed_model,
                gap_sources=gap_sources,
                text_chars=args.text_chars,
                gap_heuristic=not args.no_gap_heuristic,
            )
            report = _report_phase(
                question=q,
                probe_bundle=probe,
                gap_bundle=gap,
                ollama_url=args.ollama_url,
                model=args.report_model,
                temperature=args.temperature,
                timeout=args.timeout,
                num_ctx=args.report_num_ctx,
            )
        except Exception as exc:  # noqa: BLE001
            print(f"\nerror: {exc}\n", file=sys.stderr)
            continue

        print("\n--- gap report ---\n")
        print(gap.get("gap_report") or "")
        print("\n--- final report ---\n")
        print(report or "(empty)")
        print()


if __name__ == "__main__":
    raise SystemExit(main())
