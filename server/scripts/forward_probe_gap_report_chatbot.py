#!/usr/bin/env python3
"""Terminal chatbot: probe (3.2) → gap (8B) → report (8B).

**Probe** (default ``eoh-llama3.2-source-router``):

- Calls the source-router planner (same stack as MKG harness) to produce
  ``semantic_query`` (MKG dense lane) and ``ts_terms`` (Postgres FTS lane).
- Second 3.2 call chooses exactly one PTV graph tool + JSON args.
- Executes: MKG semantic + per-term TS, PTV ``semantic_search`` with the
  router's semantic string, and the chosen graph tool.

**Gap** (default ``eoh-llama``):

- Consumes probe bundle; may request at most one extra PTV semantic query,
  up to two additional TS terms, and one follow-up graph tool.
- Emits a structured ``gap_report`` plus optional follow-up tool results.

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
from server.ptv_toolkit.graph import load_graph
from server.ptv_toolkit.registry import call_tool, tool_names

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
        return {
            "ok": False,
            "error": "no_database_url",
            "semantic_hits": [],
            "ts_hits": [],
        }
    import psycopg
    from psycopg.rows import dict_row

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
    user = json.dumps(
        {
            "user_question": question,
            "router_plan_summary": {
                "question_type": router_plan.get("question_type"),
                "semantic_query": router_plan.get("semantic_query"),
                "ts_terms": router_plan.get("ts_terms"),
            },
            "graph_orientation": graph_brief[:6000],
        },
        ensure_ascii=False,
        indent=2,
    )
    raw = _ollama_chat(
        url=ollama_url,
        model=model,
        system=system,
        user=user,
        temperature=temperature,
        timeout=timeout,
        num_ctx=num_ctx,
    )
    parsed = _extract_json(raw) or {}
    name = str(parsed.get("graph_tool") or "").strip()
    args = parsed.get("graph_args") if isinstance(parsed.get("graph_args"), dict) else {}
    if name not in _GRAPH_TOOLS:
        return "semantic_search", {"query": question, "k": 12}
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
) -> Dict[str, Any]:
    system = (
        "You are the GAP agent for a hybrid PTV + MKG retrieval pipeline.\n"
        "You receive JSON: user question, probe MKG hits summary, probe PTV semantic result,\n"
        "and one graph tool outcome.\n\n"
        "Return STRICT JSON only:\n"
        "{\n"
        '  "follow_ptv_semantic_query": null or string,\n'
        '  "follow_ts_terms": [],\n'
        '  "follow_graph_tool": null or one of '
        + json.dumps(_GRAPH_TOOLS)
        + ",\n"
        '  "follow_graph_args": {},\n'
        '  "gap_report": "markdown: what probe covered, what is missing, contradictions, next evidence needs"\n'
        "}\n\n"
        "Rules:\n"
        "- follow_ts_terms: at most TWO strings; use only if TS lane clearly missed key tokens.\n"
        "- follow_ptv_semantic_query: optional ONE extra PTV semantic query if probe PTV context is thin.\n"
        "- follow_graph_tool: optional ONE extra graph tool (same catalog); omit if not needed.\n"
        "- gap_report is required and should be concise (<= 400 words).\n"
    )
    user = json.dumps({"user_question": question, "probe": probe_bundle}, default=str, indent=2)[:120000]
    raw = _ollama_chat(
        url=ollama_url,
        model=model,
        system=system,
        user=user,
        temperature=temperature,
        timeout=timeout,
        num_ctx=num_ctx,
    )
    parsed = _extract_json(raw) or {}
    follow_sem = parsed.get("follow_ptv_semantic_query")
    follow_terms = parsed.get("follow_ts_terms") or []
    if not isinstance(follow_terms, list):
        follow_terms = []
    follow_terms = [str(t).strip() for t in follow_terms if str(t).strip()][:2]
    fg_tool = parsed.get("follow_graph_tool")
    fg_args = parsed.get("follow_graph_args") if isinstance(parsed.get("follow_graph_args"), dict) else {}
    gap_report = str(parsed.get("gap_report") or "").strip() or "(no gap_report)"

    follow_mkg: Dict[str, Any] = {}
    if follow_terms:
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
        follow_ptv = call_tool("semantic_search", gh, {"query": follow_sem.strip(), "k": 12})

    follow_graph = None
    if fg_tool and str(fg_tool).strip() in _GRAPH_TOOLS:
        follow_graph = call_tool(str(fg_tool).strip(), gh, dict(fg_args or {}))

    return {
        "raw_gap_json": parsed,
        "gap_report": gap_report,
        "follow_ptv_semantic": follow_ptv,
        "follow_mkg": follow_mkg,
        "follow_graph": follow_graph,
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
    return _ollama_chat(
        url=ollama_url,
        model=model,
        system=system,
        user=user,
        temperature=temperature,
        timeout=timeout,
        num_ctx=num_ctx,
    )


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
) -> Dict[str, Any]:
    graph_stats = call_tool("graph_stats", gh, {})
    brief = json.dumps(graph_stats.get("result") or graph_stats, default=str)[:8000]

    route = plan_route(
        question,
        ollama_url=ollama_url,
        model=probe_model,
        num_ctx=probe_num_ctx,
        timeout=timeout,
        temperature=temperature,
        clinical_context=brief,
    )
    sources = _router_sources(route)

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

    g_tool, g_args = _pick_graph_tool(
        question=question,
        router_plan=route,
        graph_brief=brief,
        ollama_url=ollama_url,
        model=probe_model,
        temperature=temperature,
        timeout=timeout,
        num_ctx=probe_num_ctx,
    )
    graph_out = call_tool(g_tool, gh, g_args)

    ptv_sem = call_tool(
        "semantic_search",
        gh,
        {"query": str(route.get("semantic_query") or question), "k": min(16, top_k + 2)},
    )

    return {
        "router_plan": route,
        "mkg": mkg,
        "ptv_semantic_search": ptv_sem,
        "graph_tool": g_tool,
        "graph_args": g_args,
        "graph_tool_result": graph_out,
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
