#!/usr/bin/env python3
"""
Per-tool agent harness — after each graph tool (and optional PE step), send a bounded JSON
summary to eoh-llama-lucifer for analysis. Default **flagship** pipeline: structural
**graph_reduce** → **temporal graph_reduce** (recent window) → **semantic hybrid** on that
corpus → **BFS** (seeds + restrict) → Lorenz → govern → token budget; then native PE plus
extra tool rounds from JSON.

Usage (repo root, venv, PYTHONPATH=.):
  python sandbox/norman_graph_retrieval/tool_agent_harness.py -q "flare drivers in 2023"
  python sandbox/norman_graph_retrieval/tool_agent_harness.py --no-agent    # tools only, no Ollama
  python sandbox/norman_graph_retrieval/tool_agent_harness.py --extra-rounds extra_tools.json

Env: NORMAN_PTV_JSON, OLLAMA_URL, OLLAMA_MODEL (default eoh-llama-lucifer)

Structured logs: every stdout line is prefixed with `[tool-harness]` and uses emoji section markers
(timing, metrics, LLM previews). Use `--quiet` to disable logs while still writing JSON.

Each run also writes a companion **inspection .log** file (same timestamp as the JSON) containing the
**full tool JSON** for every round plus the eoh-llama response text, for offline review.

Agent prompts include **context_nodes**: resolved PTV fields (preview, type, time, edges) capped by
`--max-context-nodes` / `--context-preview-chars`, not raw ids alone.

After all rounds, a **final_synthesis** JSON block is produced (unless `--no-agent` or `--no-final-synthesis`):
`response`, `suggested_nodes` (confidence + rationale), and `suggested_nodes_with_full_context` (full PTV dicts).
If the closing step throws or OOMs, you still get a **receipt** (`ok: false`, `status: failed`, traceback excerpt) and the run **does not crash** — graph rounds remain in `rounds`.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / "server" / ".env", override=False)
    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass

from server.eoh.patient_timeline_vision import PatientTimelineVision
from server.graph_traversal.agent_tools import execute_graph_tool
from server.graph_traversal.ollama_local import ollama_chat, ollama_preflight, ollama_reply_text
from server.graph_traversal.pe_adapter import run_provenance_engine_classify, vision_to_pe_nodes
from server.graph_traversal.agent_node_context import compact_node, enrich_tool_result_for_agent
from server.graph_traversal.tool_result_summary import summarize_tool_result_for_llm

DEFAULT_PTV = (
    ROOT
    / "artifacts"
    / "timeline_ollama_20260329_1805"
    / "patient_timeline_vision_norman_eric_roberts_20260329_195915.json"
)

AGENT_SYSTEM = """You are an Ethos-of-Health (EoH) graph operator assistant. You receive ONE JSON response from a deterministic graph tool that ran against a Patient Timeline Vision (PTV).

The JSON includes `context_nodes` when available: each entry has event_id, event_type, timestamp, preview (clinical text), edge_count, and optional connascence_counts. Prefer reasoning from previews and tool fields, not raw ids alone.

Rules:
- Do not invent event_ids or clinical facts not present in the JSON.
- Quote relevant event_ids when the tool returns them.
- Note uncertainty, empty results, or when another tool would help next.
- Keep the answer concise (roughly 5–12 sentences) unless the tool output is trivial."""

FINAL_SYNTHESIS_SYSTEM = """You output exactly one JSON object and nothing else. No markdown code fences, no prose before or after the JSON.
Use only event_ids that appear in the provided candidate list. Confidence is a number from 0.0 to 1.0."""

# Console logging (emoji + structure). UTF-8 reconfigure avoids mojibake on modern Windows terminals.
_LOG_PREFIX = "[tool-harness]"


def _configure_utf8_streams() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, OSError, ValueError):
            pass


def _log(line: str = "", *, to: Any = None) -> None:
    out = to or sys.stdout
    print(f"{_LOG_PREFIX} {line}".rstrip() if line else _LOG_PREFIX, file=out, flush=True)


def _log_banner(char: str = "=", width: int = 78) -> None:
    _log(char * width)


def _build_agent_document(
    vision: PatientTimelineVision,
    tool_label: str,
    raw_result: Dict[str, Any],
    *,
    max_context_nodes: int,
    context_preview_chars: int,
) -> Dict[str, Any]:
    """Bounded tool JSON + resolved PTV nodes (previews) for the LLM."""
    summarized = summarize_tool_result_for_llm(tool_label, raw_result)
    return enrich_tool_result_for_agent(
        vision,
        tool_label,
        raw_result,
        summarized,
        max_context_nodes=max_context_nodes,
        preview_chars=context_preview_chars,
    )


def _dedupe_preserve_ids(ids: List[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for x in ids:
        s = str(x).strip()
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def _final_candidate_event_ids(ctx: Dict[str, Any], *, max_ids: int) -> List[str]:
    pool: List[str] = []
    for key in ("hybrid_ids", "bfs_ids", "working_ids", "budget_seed_ids", "hybrid_seed_ids"):
        pool.extend(ctx.get(key) or [])
    return _dedupe_preserve_ids(pool)[:max_ids]


def _extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    t = (text or "").strip()
    if not t:
        return None
    if "```" in t:
        for block in t.split("```"):
            b = block.strip()
            if b.lower().startswith("json"):
                b = b[4:].strip()
            if b.startswith("{"):
                t = b
                break
    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        i, j = t.find("{"), t.rfind("}")
        if i >= 0 and j > i:
            try:
                obj = json.loads(t[i : j + 1])
                return obj if isinstance(obj, dict) else None
            except json.JSONDecodeError:
                pass
    return None


def _normalize_suggested_nodes(
    raw: Any,
    allowed_ids: Set[str],
    *,
    max_n: int = 10,
) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        eid = str(item.get("event_id") or "").strip()
        if eid not in allowed_ids:
            continue
        try:
            conf = float(item.get("confidence", 0))
        except (TypeError, ValueError):
            conf = 0.0
        conf = max(0.0, min(1.0, conf))
        out.append(
            {
                "event_id": eid,
                "confidence": conf,
                "rationale": str(item.get("rationale") or "").strip()[:4000],
            }
        )
    out.sort(key=lambda x: -x["confidence"])
    return out[:max_n]


def _attach_full_ptv_to_suggested(
    suggested: List[Dict[str, Any]],
    vision: PatientTimelineVision,
) -> List[Dict[str, Any]]:
    rich: List[Dict[str, Any]] = []
    for row in suggested:
        eid = row.get("event_id")
        ev = vision.events.get(str(eid)) if eid else None
        r = dict(row)
        r["ptv_full"] = ev.to_dict() if ev else None
        rich.append(r)
    return rich


def _run_final_synthesis_impl(
    vision: PatientTimelineVision,
    ctx: Dict[str, Any],
    *,
    query: str,
    rounds_out: List[Dict[str, Any]],
    ollama_url: str,
    ollama_model: str,
    max_json_chars: int,
    max_candidates: int,
    candidate_preview_chars: int,
    emit_fn: Callable[[str], None],
) -> Dict[str, Any]:
    """
    One closing JSON call: { response, suggested_nodes } plus enriched full PTV payloads
    for downstream answer assembly. May raise; see run_final_synthesis wrapper.
    """
    candidate_ids = _final_candidate_event_ids(ctx, max_ids=max_candidates)
    allowed = set(candidate_ids) & set(vision.events.keys())
    digest_lines: List[str] = []
    for r in rounds_out[-6:]:
        sid = r.get("step_id", "")
        tool = r.get("tool", "")
        aa = (r.get("agent_analysis") or "")[:320].replace("\n", " ")
        digest_lines.append(f"- {sid} ({tool}): {aa}")

    candidates_payload = [
        compact_node(vision, eid, preview_max=candidate_preview_chars, include_connascence=True)
        for eid in candidate_ids
        if eid in vision.events
    ]
    pool_json = json.dumps(
        {"candidate_nodes": candidates_payload, "candidate_event_id_set_size": len(allowed)},
        indent=2,
        ensure_ascii=False,
    )
    if len(pool_json) > max_json_chars:
        pool_json = pool_json[:max_json_chars] + "\n... [truncated — raise --max-json-chars or lower --final-synthesis-candidates]"

    schema = """{
  "response": "<concise synthesis that answers the clinical query using the run below>",
  "suggested_nodes": [
    {
      "event_id": "<must be exactly one of the candidate event_ids>",
      "confidence": 0.0,
      "rationale": "<one or two sentences; cite clinical content from previews>"
    }
  ],
  "meta": {
    "notes": "<optional short operator notes>"
  }
}"""

    user_msg = f"""Clinical query: {query}

Per-round digest (most recent steps):
{chr(10).join(digest_lines)}

Candidate timeline nodes for final answer context (choose up to 10; confidence 0–1, sort by importance):
{pool_json}

Return ONLY valid JSON matching this schema (meta is optional; suggested_nodes length at most 10):
{schema}"""

    t0 = time.perf_counter()
    raw_text = ""
    parsed: Optional[Dict[str, Any]] = None
    err: Optional[str] = None
    try:
        resp = ollama_chat(
            ollama_url,
            ollama_model,
            user_msg,
            system=FINAL_SYNTHESIS_SYSTEM,
            temperature=0.15,
        )
        raw_text = ollama_reply_text(resp)
        parsed = _extract_json_object(raw_text)
        if parsed is None:
            err = "model output was not valid JSON"
    except Exception as e:
        err = str(e)
        raw_text = f"[final_synthesis_error] {e!s}"

    response_text = ""
    suggested_norm: List[Dict[str, Any]] = []
    meta_out: Any = None

    if parsed:
        response_text = str(parsed.get("response") or "").strip()
        suggested_norm = _normalize_suggested_nodes(
            parsed.get("suggested_nodes"),
            allowed,
            max_n=10,
        )
        meta_out = parsed.get("meta")

    suggested_with_full = _attach_full_ptv_to_suggested(suggested_norm, vision)
    ms = (time.perf_counter() - t0) * 1000.0

    emit_fn("-" * 78)
    emit_fn("FINAL SYNTHESIS  (structured JSON: response + suggested_nodes + full PTV)")
    emit_fn(f"   candidates considered: {len(candidate_ids)}  |  LLM ms: {ms:.1f}")
    emit_fn(f"   suggested_nodes (normalized): {len(suggested_norm)}")
    if err:
        emit_fn(f"   ⚠️  {err}")
    emit_fn("-" * 78)

    return {
        "ok": True,
        "status": "ok",
        "receipt": True,
        "response": response_text,
        "suggested_nodes": suggested_norm,
        "suggested_nodes_with_full_context": suggested_with_full,
        "meta": meta_out,
        "model_raw_text_excerpt": (raw_text[:8000] + ("..." if len(raw_text) > 8000 else "")) if raw_text else "",
        "parse_error": err,
        "candidate_event_ids_count": len(candidate_ids),
        "llm_ms": round(ms, 3),
    }


def run_final_synthesis(
    vision: PatientTimelineVision,
    ctx: Dict[str, Any],
    *,
    query: str,
    rounds_out: List[Dict[str, Any]],
    ollama_url: str,
    ollama_model: str,
    max_json_chars: int,
    max_candidates: int,
    candidate_preview_chars: int,
    emit_fn: Callable[[str], None],
) -> Dict[str, Any]:
    """
    Never raises: on any failure returns a receipt dict so the harness run completes and
    `rounds` are still persisted. Successful runs include ok/status; failures include traceback excerpt.
    """
    try:
        return _run_final_synthesis_impl(
            vision,
            ctx,
            query=query,
            rounds_out=rounds_out,
            ollama_url=ollama_url,
            ollama_model=ollama_model,
            max_json_chars=max_json_chars,
            max_candidates=max_candidates,
            candidate_preview_chars=candidate_preview_chars,
            emit_fn=emit_fn,
        )
    except Exception as e:
        tb = traceback.format_exc()
        cids_sample: List[str] = []
        n_cand = 0
        try:
            all_c = _final_candidate_event_ids(ctx, max_ids=max_candidates)
            n_cand = len(all_c)
            cids_sample = all_c[:24]
        except Exception:
            pass
        emit_fn("-" * 78)
        emit_fn("FINAL SYNTHESIS  (FAILED — receipt only; graph rounds above are valid)")
        emit_fn(f"   {type(e).__name__}: {e!s}")
        emit_fn("   Full traceback in bundle final_synthesis.traceback_excerpt")
        emit_fn("-" * 78)
        return {
            "ok": False,
            "status": "failed",
            "receipt": True,
            "error_kind": "final_synthesis_exception",
            "error_class": type(e).__name__,
            "error_message": str(e),
            "traceback_excerpt": tb[-8000:],
            "candidate_event_ids_sample": cids_sample,
            "response": "",
            "suggested_nodes": [],
            "suggested_nodes_with_full_context": [],
            "meta": None,
            "model_raw_text_excerpt": "",
            "parse_error": f"uncaught_exception:{type(e).__name__}",
            "candidate_event_ids_count": n_cand,
            "llm_ms": None,
        }


def _one_line_preview(text: str, max_len: int = 220) -> str:
    t = " ".join((text or "").split())
    if len(t) <= max_len:
        return t
    return t[: max_len - 3] + "..."


def _class_histogram(items: Optional[List[Dict[str, Any]]]) -> str:
    if not items:
        return "(no items)"
    c = Counter(str(it.get("classification") or "?") for it in items)
    return ", ".join(f"{k}={v}" for k, v in sorted(c.items()))


def _tool_metrics_line(tool: str, result: Dict[str, Any]) -> str:
    """Single human-readable line of numbers for logs (copy/paste friendly)."""
    err = result.get("error")
    sid = result.get("strategy_id") or ""

    if err:
        return f"strategy={sid} ERROR={err!s}" if sid else f"ERROR={err!s}"

    if tool == "graph_reduce":
        kc = result.get("kept_count")
        dc = result.get("dropped_count")
        ne = len(result.get("event_ids") or [])
        line = f"strategy={sid} kept={kc} dropped={dc} event_ids_returned~{ne}"
        tf = result.get("temporal_filter")
        if isinstance(tf, dict):
            ir = tf.get("inactive_reason")
            if ir:
                line += f" temporal_inactive={ir}"
            elif tf.get("start") or tf.get("end"):
                line += f" temporal=[{tf.get('start')}..{tf.get('end')}]"
        return line

    if tool == "graph_hybrid_search":
        ne = len(result.get("event_ids") or [])
        line = (
            f"strategy={sid} merged_hits={ne} kw={result.get('keyword_hits')} "
            f"sem={result.get('semantic_hits')} scope={result.get('corpus_scope')} "
            f"corpus_n={result.get('corpus_size')}"
        )
        note = result.get("note")
        if note:
            ns = str(note).replace("\n", " ")
            if len(ns) > 160:
                ns = ns[:157] + "..."
            line += f" | {ns}"
        return line

    if tool == "graph_bfs_expand":
        ne = len(result.get("event_ids") or [])
        return f"strategy={sid} expanded_event_ids={ne}"

    if tool == "graph_pe_lorenz_classify":
        items = result.get("items") or []
        return f"strategy={sid} items={len(items)} labels=[{_class_histogram(items)}]"

    if tool == "graph_pe_govern_adjust":
        items = result.get("items") or []
        return f"strategy={sid} governance_rows={len(items)}"

    if tool == "graph_token_budget":
        picked = len(result.get("event_ids") or [])
        est = result.get("estimated_tokens")
        cons = result.get("considered")
        mt = result.get("max_tokens")
        return f"strategy={sid} picked_events={picked} est_tokens~{est}/{mt} considered={cons}"

    if tool.startswith("provenance_engine"):
        ok = result.get("ok")
        n = result.get("node_count")
        items = result.get("items") or []
        if ok is False:
            return f"native_PE ok={ok} err={result.get('error')!s}"
        return f"native_PE ok={ok} items={len(items)} node_count={n} labels=[{_class_histogram(items)}]"

    # Generic fallback
    if "event_ids" in result:
        return f"strategy={sid} event_ids~{len(result.get('event_ids') or [])}"
    if "items" in result:
        return f"strategy={sid} items~{len(result.get('items') or [])}"
    return f"strategy={sid} keys={list(result.keys())[:8]}"


# (step_id, emoji, one-line purpose) — used in logs
_STEP_BLURBS: Dict[str, Tuple[str, str]] = {
    "reduce": ("✂️", "Structural graph_reduce: pages, isolates, etc. → baseline corpus"),
    "temporal_reduce": ("📅", "Temporal slice on same rules + time window → flagship corpus for hybrid/BFS"),
    "hybrid_search": ("🔎", "Hybrid search (semantic + keyword) on temporal/reduced event_ids only"),
    "bfs_expand": ("🕸️", "Multi-seed BFS inside reduced set → neighborhood for PE / working set"),
    "pe_lorenz": ("🌀", "In-repo Lorenz classify on working_ids (ρ/τ attractor)"),
    "pe_govern": ("⚖️", "Governance: protect load-bearing from silent EVICT"),
    "token_budget": ("🪙", "Token budget: rank events for downstream LLM context"),
    "provenance_engine": ("🧪", "Native provenance-engine classify (cross-check vs Lorenz)"),
}


def _format_agent_logs(agent_text: Optional[str], *, ran_agent: bool) -> List[str]:
    """Indented lines for the eoh-llama step (copy/paste friendly)."""
    if not ran_agent:
        return ["      🤖 LLM: skipped (--no-agent)"]
    if agent_text is None:
        return ["      🤖 LLM: skipped"]
    if agent_text.startswith("[agent_error]"):
        return [f"      ❌ LLM FAILED: {_one_line_preview(agent_text, 400)}"]
    return [
        f"      🤖 LLM OK — {len(agent_text)} chars",
        f"         💬 {_one_line_preview(agent_text, 360)}",
    ]


def _dedupe(ids: List[str]) -> List[str]:
    seen: set = set()
    out: List[str] = []
    for x in ids:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _resolve_placeholders(obj: Any, ctx: Dict[str, Any]) -> Any:
    if isinstance(obj, str):
        if obj == "__reduced_ids__":
            return ctx.get("reduced_ids")
        if obj == "__structural_reduced_ids__":
            return ctx.get("structural_reduced_ids")
        if obj == "__hybrid_ids__":
            return ctx.get("hybrid_ids")
        if obj == "__bfs_ids__":
            return ctx.get("bfs_ids")
        if obj == "__working_ids__":
            return ctx.get("working_ids")
        return obj
    if isinstance(obj, dict):
        return {k: _resolve_placeholders(v, ctx) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_resolve_placeholders(v, ctx) for v in obj]
    return obj


def default_pipeline_rounds(
    vision: PatientTimelineVision,
    ctx: Dict[str, Any],
) -> List[Tuple[str, str, Dict[str, Any]]]:
    """Returns list of (step_id, tool_name, args).

    Flagship story: structural reduce → temporal reduce (optional) → hybrid → BFS → …
    """
    q = ctx["query"]
    sem = ctx.get("semantic", True)
    structural: Dict[str, Any] = {
        "drop_page": True,
        "drop_unknown_timestamp": False,
        "drop_isolates": True,
    }
    rounds: List[Tuple[str, str, Dict[str, Any]]] = [
        ("reduce", "graph_reduce", dict(structural)),
    ]
    tr_years = ctx.get("temporal_recent_years")
    if tr_years is not None:
        try:
            ry = float(tr_years)
        except (TypeError, ValueError):
            ry = 0.0
        if ry > 0:
            anchor = str(ctx.get("temporal_anchor") or "latest_in_corpus")
            temporal_args = dict(structural)
            temporal_args["recent_years"] = ry
            temporal_args["temporal_anchor"] = anchor
            rounds.append(("temporal_reduce", "graph_reduce", temporal_args))
    rounds.extend(
        [
            (
                "hybrid_search",
                "graph_hybrid_search",
                {
                    "query": q,
                    "top_k": 30,
                    "semantic": sem,
                    "event_ids": "__reduced_ids__",
                },
            ),
            (
                "bfs_expand",
                "graph_bfs_expand",
                {
                    "seed_event_ids": "__hybrid_seed_ids__",
                    "restrict_to_event_ids": "__reduced_ids__",
                    "max_depth": 2,
                    "max_nodes": 600,
                },
            ),
            (
                "pe_lorenz",
                "graph_pe_lorenz_classify",
                {
                    "event_ids": "__working_ids__",
                    "rho": 28.0,
                    "tau": 2.0,
                    "steps": 1500,
                },
            ),
            (
                "pe_govern",
                "graph_pe_govern_adjust",
                {"items": "__lorenz_items__"},
            ),
            (
                "token_budget",
                "graph_token_budget",
                {
                    "event_ids": "__budget_seed_ids__",
                    "max_tokens": 8000,
                    "query": q,
                    "prefer_recent": True,
                },
            ),
        ]
    )
    return rounds


def _apply_special_placeholders(
    vision: PatientTimelineVision,
    ctx: Dict[str, Any],
    args: Dict[str, Any],
) -> Dict[str, Any]:
    """Replace placeholders that need computed lists (not in _resolve_placeholders)."""
    a = json.loads(json.dumps(args))  # deep copy via json
    hybrid_ids: List[str] = ctx.get("hybrid_ids") or []
    seed_n = min(10, max(3, len(hybrid_ids)))
    ctx["hybrid_seed_ids"] = hybrid_ids[:seed_n] if hybrid_ids else (ctx.get("reduced_ids") or [])[:5]

    w = _dedupe((hybrid_ids[:50] if hybrid_ids else []) + (ctx.get("bfs_ids") or []))[
        : int(ctx.get("pe_nodes", 400))
    ]
    if not w:
        w = (ctx.get("reduced_ids") or [])[: int(ctx.get("pe_nodes", 400))]
    ctx["working_ids"] = w

    lorenz_items = ctx.get("_lorenz_raw_items") or []
    ctx["lorenz_items"] = lorenz_items

    budget_seed = hybrid_ids[:80] if hybrid_ids else (ctx.get("reduced_ids") or [])[:400]
    ctx["budget_seed_ids"] = budget_seed

    def walk(o: Any) -> Any:
        if o == "__hybrid_seed_ids__":
            return ctx["hybrid_seed_ids"]
        if o == "__working_ids__":
            return ctx["working_ids"]
        if o == "__lorenz_items__":
            return lorenz_items
        if o == "__budget_seed_ids__":
            return ctx["budget_seed_ids"]
        if isinstance(o, dict):
            return {k: walk(v) for k, v in o.items()}
        if isinstance(o, list):
            return [walk(v) for v in o]
        return o

    return walk(a)


def _round_payload(
    *,
    step_id: str,
    tool: str,
    result: Dict[str, Any],
    summarized: Dict[str, Any],
    agent_text: Optional[str],
    full_tool_json: bool,
) -> Dict[str, Any]:
    row: Dict[str, Any] = {
        "step_id": step_id,
        "tool": tool,
        "result_summary": summarized,
        "agent_analysis": agent_text,
    }
    if full_tool_json:
        row["result"] = result
    return row


def _safe_json_dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, default=str)


def _append_inspection_entry(
    log_entries: List[Dict[str, Any]],
    *,
    round_index: int,
    step_id: str,
    tool: str,
    args: Dict[str, Any],
    result: Dict[str, Any],
    agent_analysis: Optional[str],
    tool_ms: float,
    llm_ms: Optional[float],
) -> None:
    """Full tool payloads + LLM text for the inspection .log file (always, independent of --full-tool-json)."""
    ent: Dict[str, Any] = {
        "round_index": round_index,
        "step_id": step_id,
        "tool": tool,
        "args": args,
        "result": result,
        "agent_analysis": agent_analysis,
        "timings_ms": {
            "tool": round(tool_ms, 3),
            "llm": None if llm_ms is None else round(llm_ms, 3),
        },
    }
    log_entries.append(ent)


def write_inspection_log(
    path: Path,
    *,
    written_at_utc: str,
    meta: Dict[str, Any],
    entries: List[Dict[str, Any]],
) -> None:
    """Write human-readable log: resolved args, full tool JSON, LLM response per round."""
    lines: List[str] = [
        "TOOL AGENT HARNESS - INSPECTION LOG (full tool JSON + LLM responses)",
        f"Written (UTC): {written_at_utc}",
        "",
        "--- SESSION ---",
    ]
    for k in sorted(meta.keys()):
        lines.append(f"  {k}: {meta[k]}")
    lines.append("")

    for ent in entries:
        lines.append("=" * 80)
        ri = ent.get("round_index", "?")
        sid = ent.get("step_id", "")
        tool = ent.get("tool", "")
        lines.append(f"ROUND {ri}  step={sid!r}  tool={tool}")
        lines.append("-" * 80)
        lines.append("[ARGS PASSED INTO TOOL]")
        lines.append(_safe_json_dumps(ent.get("args") or {}))
        lines.append("")
        lines.append("[TOOL RESULT - full JSON]")
        lines.append(_safe_json_dumps(ent.get("result") or {}))
        lines.append("")
        lines.append("[EOH-LLAMA RESPONSE]")
        resp = ent.get("agent_analysis")
        if resp is None:
            lines.append("(none — LLM not called or skipped)")
        else:
            lines.append(str(resp))
        lines.append("")
        tm = ent.get("timings_ms") or {}
        lines.append(f"[TIMINGS MS] tool={tm.get('tool')}  llm={tm.get('llm')}")
        lines.append("")

    lines.append("=" * 80)
    lines.append("END OF INSPECTION LOG")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def run_harness(
    vision: PatientTimelineVision,
    *,
    query: str,
    semantic: bool,
    pe_nodes: int,
    ollama_url: str,
    ollama_model: str,
    run_agent: bool,
    max_json_chars: int,
    extra_rounds: Optional[List[Dict[str, Any]]] = None,
    full_tool_json: bool = False,
    quiet: bool = False,
    emit: Optional[Callable[[str], None]] = None,
    max_context_nodes: int = 48,
    context_preview_chars: int = 480,
    enable_final_synthesis: bool = True,
    final_synthesis_max_candidates: int = 80,
    final_synthesis_preview_chars: int = 350,
    temporal_recent_years: Optional[float] = 1.0,
    temporal_anchor: str = "latest_in_corpus",
) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
    emit_fn = emit if emit is not None else _log
    if quiet:
        emit_fn = lambda _line="": None  # noqa: E731

    t_run0 = time.perf_counter()
    ctx: Dict[str, Any] = {
        "query": query,
        "semantic": semantic,
        "pe_nodes": pe_nodes,
        "temporal_recent_years": temporal_recent_years,
        "temporal_anchor": temporal_anchor,
    }

    log_entries: List[Dict[str, Any]] = []
    round_index = 0

    rounds_out: List[Dict[str, Any]] = []
    spec = default_pipeline_rounds(vision, ctx)
    n_extra = len(extra_rounds or [])
    total_rounds_planned = len(spec) + 1 + n_extra  # pipeline + PE + optional extras

    emit_fn()
    emit_fn("🚀 Tool Agent Harness — flagship STRATEGY v1.1 + native PE cross-check" + (f" + {n_extra} extra tool(s)" if n_extra else ""))
    tr = ctx.get("temporal_recent_years")
    if tr is not None:
        emit_fn(
            "   Flow: structural reduce → temporal reduce → hybrid (semantic) → BFS → "
            "Lorenz → govern → token budget → PE → [extras]"
        )
        emit_fn(f"   Temporal window: recent_years={tr!r}  anchor={ctx.get('temporal_anchor')!r}")
    else:
        emit_fn(
            "   Flow: structural reduce → hybrid (semantic) → BFS → "
            "Lorenz → govern → token budget → PE → [extras]  (no temporal round)"
        )
    emit_fn()

    for idx, (step_id, tool, args_template) in enumerate(spec, start=1):
        emoji, blurb = _STEP_BLURBS.get(step_id, ("🔧", "Graph tool"))
        emit_fn("-" * 78)
        emit_fn(f"ROUND {idx}/{total_rounds_planned}  {emoji}  step={step_id!r}  tool={tool}")
        emit_fn(f"   📌 {blurb}")

        args = _apply_special_placeholders(vision, ctx, args_template)
        args = _resolve_placeholders(args, ctx)
        if not isinstance(args, dict):
            args = {}

        t_tool = time.perf_counter()
        result = execute_graph_tool(tool, vision, args)
        ms_tool = (time.perf_counter() - t_tool) * 1000.0

        if step_id == "reduce":
            rids = result.get("event_ids") or []
            ctx["structural_reduced_ids"] = rids
            ctx["reduced_ids"] = rids
        elif step_id == "temporal_reduce":
            rids = result.get("event_ids") or []
            ctx["temporal_reduced_ids"] = rids
            ctx["reduced_ids"] = rids
        elif step_id == "hybrid_search":
            ctx["hybrid_ids"] = result.get("event_ids") or []
        elif step_id == "bfs_expand":
            ctx["bfs_ids"] = result.get("event_ids") or []
        elif step_id == "pe_lorenz":
            ctx["_lorenz_raw_items"] = result.get("items") or []

        emit_fn(f"   ⚙️  deterministic tool finished in {ms_tool:.1f} ms")
        emit_fn(f"   📊 {_tool_metrics_line(tool, result)}")

        agent_doc = _build_agent_document(
            vision,
            tool,
            result,
            max_context_nodes=max_context_nodes,
            context_preview_chars=context_preview_chars,
        )
        payload = json.dumps(agent_doc, indent=2, ensure_ascii=False)
        if len(payload) > max_json_chars:
            payload = payload[:max_json_chars] + "\n... [truncated for agent context]"

        agent_text = None
        t_llm = time.perf_counter()
        if run_agent:
            user_msg = f"""Step: {step_id}
Tool: {tool}

Clinical query (session): {query}

Tool JSON output:
{payload}

Summarize what this step established for the operator and which event_ids (if any) matter next."""
            try:
                resp = ollama_chat(ollama_url, ollama_model, user_msg, system=AGENT_SYSTEM)
                agent_text = ollama_reply_text(resp)
            except Exception as e:
                agent_text = f"[agent_error] {e!s}"
        ms_llm = (time.perf_counter() - t_llm) * 1000.0

        for line in _format_agent_logs(agent_text, ran_agent=run_agent):
            emit_fn(line)
        if run_agent and agent_text and not str(agent_text).startswith("[agent_error]"):
            emit_fn(f"   ⏱️  LLM call took {ms_llm:.1f} ms  (model={ollama_model!r})")

        round_index += 1
        _append_inspection_entry(
            log_entries,
            round_index=round_index,
            step_id=step_id,
            tool=tool,
            args=args,
            result=result,
            agent_analysis=agent_text,
            tool_ms=ms_tool,
            llm_ms=ms_llm if run_agent else None,
        )

        rounds_out.append(
            _round_payload(
                step_id=step_id,
                tool=tool,
                result=result,
                summarized=agent_doc,
                agent_text=agent_text,
                full_tool_json=full_tool_json,
            )
        )

    # provenance-engine cross-check (optional package)
    emit_fn("-" * 78)
    emit_fn(f"ROUND {len(spec) + 1}/{total_rounds_planned}  🧪  step=provenance_engine  tool=provenance_engine.classify")
    emit_fn(f"   📌 {_STEP_BLURBS['provenance_engine'][1]}")
    pe_nodes_list = vision_to_pe_nodes(
        vision,
        event_ids=ctx.get("working_ids"),
        max_nodes=pe_nodes,
    )
    emit_fn(f"   🧬 vision_to_pe_nodes: {len(pe_nodes_list)} nodes (cap pe_nodes={pe_nodes})")

    t_pe = time.perf_counter()
    pe_raw = run_provenance_engine_classify(pe_nodes_list, rho=28.0, tau=2.0)
    ms_pe = (time.perf_counter() - t_pe) * 1000.0
    emit_fn(f"   ⚙️  native provenance_engine.classify finished in {ms_pe:.1f} ms")
    emit_fn(f"   📊 {_tool_metrics_line('provenance_engine.classify', pe_raw)}")

    agent_doc_pe = _build_agent_document(
        vision,
        "provenance_engine.classify",
        pe_raw,
        max_context_nodes=max_context_nodes,
        context_preview_chars=context_preview_chars,
    )
    pe_payload = json.dumps(agent_doc_pe, indent=2, ensure_ascii=False)
    if len(pe_payload) > max_json_chars:
        pe_payload = pe_payload[:max_json_chars] + "\n... [truncated for agent context]"
    agent_pe = None
    t_llm_pe = time.perf_counter()
    if run_agent:
        try:
            resp = ollama_chat(
                ollama_url,
                ollama_model,
                f"""Step: provenance_engine_crosscheck
Clinical query: {query}

Cross-check JSON (native PE classify on working set):
{pe_payload}

Briefly compare this to the in-repo Lorenz step if both ran; note agreement or divergence.""",
                system=AGENT_SYSTEM,
            )
            agent_pe = ollama_reply_text(resp)
        except Exception as e:
            agent_pe = f"[agent_error] {e!s}"
    ms_llm_pe = (time.perf_counter() - t_llm_pe) * 1000.0

    for line in _format_agent_logs(agent_pe, ran_agent=run_agent):
        emit_fn(line)
    if run_agent and agent_pe and not str(agent_pe).startswith("[agent_error]"):
        emit_fn(f"   ⏱️  LLM call took {ms_llm_pe:.1f} ms  (model={ollama_model!r})")

    pe_args_log = {
        "rho": 28.0,
        "tau": 2.0,
        "pe_nodes_built": len(pe_nodes_list),
        "note": "Native provenance_engine: nodes built via vision_to_pe_nodes (not embedded here).",
    }
    round_index += 1
    _append_inspection_entry(
        log_entries,
        round_index=round_index,
        step_id="provenance_engine",
        tool="provenance_engine.classify",
        args=pe_args_log,
        result=pe_raw,
        agent_analysis=agent_pe,
        tool_ms=ms_pe,
        llm_ms=ms_llm_pe if run_agent else None,
    )

    rounds_out.append(
        _round_payload(
            step_id="provenance_engine",
            tool="provenance_engine.classify",
            result=pe_raw,
            summarized=agent_doc_pe,
            agent_text=agent_pe,
            full_tool_json=full_tool_json,
        )
    )

    # Extra JSON-specified tools
    if extra_rounds:
        emit_fn("-" * 78)
        emit_fn(f"➕ EXTRA TOOL ROUNDS ({len(extra_rounds)}) — appended after default pipeline + PE")
        for i, spec_ex in enumerate(extra_rounds):
            tool = spec_ex.get("tool") or spec_ex.get("name")
            args = spec_ex.get("args") or {}
            step_id = spec_ex.get("step_id") or f"extra_{i}"
            round_no = len(spec) + 2 + i  # after default + PE
            if not tool:
                emit_fn(f"   ⚠️  skip extra[{i}]: missing tool name")
                continue
            emoji, blurb = _STEP_BLURBS.get(step_id, ("➕", "Extra graph tool from --extra-rounds JSON"))
            emit_fn("-" * 78)
            emit_fn(
                f"ROUND {round_no}/{total_rounds_planned}  {emoji}  [extra {i + 1}/{len(extra_rounds)}]  "
                f"step={step_id!r}  tool={tool}"
            )
            emit_fn(f"   📌 {blurb}")
            args = _apply_special_placeholders(vision, ctx, args)
            args = _resolve_placeholders(args, ctx)
            if not isinstance(args, dict):
                args = {}
            t_tool = time.perf_counter()
            result = execute_graph_tool(str(tool), vision, args)
            ms_tool = (time.perf_counter() - t_tool) * 1000.0
            emit_fn(f"   ⚙️  deterministic tool finished in {ms_tool:.1f} ms")
            emit_fn(f"   📊 {_tool_metrics_line(str(tool), result)}")

            agent_doc = _build_agent_document(
                vision,
                str(tool),
                result,
                max_context_nodes=max_context_nodes,
                context_preview_chars=context_preview_chars,
            )
            payload = json.dumps(agent_doc, indent=2, ensure_ascii=False)
            if len(payload) > max_json_chars:
                payload = payload[:max_json_chars] + "\n... [truncated for agent context]"
            agent_text = None
            t_llm = time.perf_counter()
            if run_agent:
                try:
                    resp = ollama_chat(
                        ollama_url,
                        ollama_model,
                        f"""Step: {step_id}
Tool: {tool}
Query: {query}
Tool JSON:
{payload}""",
                        system=AGENT_SYSTEM,
                    )
                    agent_text = ollama_reply_text(resp)
                except Exception as e:
                    agent_text = f"[agent_error] {e!s}"
            ms_llm = (time.perf_counter() - t_llm) * 1000.0
            for line in _format_agent_logs(agent_text, ran_agent=run_agent):
                emit_fn(line)
            if run_agent and agent_text and not str(agent_text).startswith("[agent_error]"):
                emit_fn(f"   ⏱️  LLM call took {ms_llm:.1f} ms  (model={ollama_model!r})")

            round_index += 1
            _append_inspection_entry(
                log_entries,
                round_index=round_index,
                step_id=str(step_id),
                tool=str(tool),
                args=args,
                result=result,
                agent_analysis=agent_text,
                tool_ms=ms_tool,
                llm_ms=ms_llm if run_agent else None,
            )
            rounds_out.append(
                _round_payload(
                    step_id=step_id,
                    tool=str(tool),
                    result=result,
                    summarized=agent_doc,
                    agent_text=agent_text,
                    full_tool_json=full_tool_json,
                )
            )

    final_synthesis_block: Optional[Dict[str, Any]] = None
    if run_agent and enable_final_synthesis:
        final_synthesis_block = run_final_synthesis(
            vision,
            ctx,
            query=query,
            rounds_out=rounds_out,
            ollama_url=ollama_url,
            ollama_model=ollama_model,
            max_json_chars=max_json_chars,
            max_candidates=final_synthesis_max_candidates,
            candidate_preview_chars=final_synthesis_preview_chars,
            emit_fn=emit_fn,
        )
    elif not run_agent:
        final_synthesis_block = {"skipped": True, "reason": "--no-agent"}
    else:
        final_synthesis_block = {"skipped": True, "reason": "--no-final-synthesis"}

    total_s = time.perf_counter() - t_run0
    emit_fn("-" * 78)
    emit_fn(f"✅ Harness run finished in {total_s:.2f} s  |  total rounds written: {len(rounds_out)}")
    emit_fn(
        f"   ({len(spec)} graph tools + 1 native PE"
        + (f" + {n_extra} extra" if n_extra else "")
        + " — each round may include an eoh-llama analysis block in the JSON)"
    )

    bundle = {
        "patient_id": vision.patient_id,
        "query": query,
        "rounds": rounds_out,
        "context_keys": {k: len(v) if isinstance(v, list) else v for k, v in ctx.items() if not k.startswith("_")},
        "final_synthesis": final_synthesis_block,
        "harness_wall_time_s": round(total_s, 3),
    }
    return bundle, log_entries


def main() -> None:
    parser = argparse.ArgumentParser(description="Per-tool eoh-llama agent harness")
    parser.add_argument("--ptv", type=Path, default=None)
    parser.add_argument("--query", "-q", type=str, default="What patterns matter for inflammatory load?")
    parser.add_argument("--no-semantic", action="store_true")
    parser.add_argument("--no-agent", action="store_true", help="Run tools only; skip Ollama per round")
    parser.add_argument("--pe-nodes", type=int, default=400)
    parser.add_argument("--max-json-chars", type=int, default=14000)
    parser.add_argument(
        "--extra-rounds",
        type=Path,
        default=None,
        help="JSON array of {step_id, tool, args} — args may use __reduced_ids__, __structural_reduced_ids__, __hybrid_ids__, etc.",
    )
    parser.add_argument(
        "--full-tool-json",
        action="store_true",
        help="Include full raw tool results in output JSON (large); default is result_summary only",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress structured harness logs (JSON output still written)",
    )
    parser.add_argument(
        "--skip-ollama-preflight",
        action="store_true",
        help="Skip GET /api/tags check (not recommended; for unusual Ollama setups)",
    )
    parser.add_argument(
        "--max-context-nodes",
        type=int,
        default=48,
        help="Max PTV timeline nodes (previews) to attach per round for the LLM (default 48)",
    )
    parser.add_argument(
        "--context-preview-chars",
        type=int,
        default=480,
        help="Max characters per event preview in context_nodes (default 480)",
    )
    parser.add_argument(
        "--no-final-synthesis",
        action="store_true",
        help="Skip closing JSON synthesis (response + suggested_nodes with full PTV)",
    )
    parser.add_argument(
        "--final-synthesis-max-candidates",
        type=int,
        default=80,
        help="Max candidate event_ids pooled for the final suggestion step (default 80)",
    )
    parser.add_argument(
        "--final-synthesis-preview-chars",
        type=int,
        default=350,
        help="Preview length per candidate in the final synthesis pool (default 350)",
    )
    parser.add_argument(
        "--temporal-recent-years",
        type=float,
        default=1.0,
        metavar="N",
        help="Second graph_reduce: keep events within N years of temporal anchor (default 1.0); ignored with --no-temporal-reduce",
    )
    parser.add_argument(
        "--temporal-anchor",
        type=str,
        default="latest_in_corpus",
        choices=("latest_in_corpus", "utc_now"),
        help="Anchor for --temporal-recent-years window (default latest_in_corpus)",
    )
    parser.add_argument(
        "--no-temporal-reduce",
        action="store_true",
        help="Skip the temporal graph_reduce round; hybrid/BFS use structural corpus only",
    )
    args = parser.parse_args()

    temporal_recent_years_effective: Optional[float] = None if args.no_temporal_reduce else args.temporal_recent_years
    if temporal_recent_years_effective is not None and temporal_recent_years_effective <= 0:
        temporal_recent_years_effective = None

    _configure_utf8_streams()

    ollama_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model = os.environ.get("OLLAMA_MODEL", "eoh-llama-lucifer")

    if not args.no_agent and not args.skip_ollama_preflight:
        ok, pre_msg = ollama_preflight(ollama_url, ollama_model)
        if not ok:
            print(f"{_LOG_PREFIX} Ollama preflight FAILED: {pre_msg}", file=sys.stderr)
            sys.exit(2)
        if not args.quiet:
            _log(f"✅ {pre_msg}")

    ptv_path = args.ptv or Path(os.environ.get("NORMAN_PTV_JSON", str(DEFAULT_PTV)))
    if not ptv_path.is_file():
        print(f"PTV not found: {ptv_path}", file=sys.stderr)
        sys.exit(1)

    with open(ptv_path, encoding="utf-8") as f:
        vision = PatientTimelineVision.from_dict(json.load(f))

    extra: Optional[List[Dict[str, Any]]] = None
    if args.extra_rounds and args.extra_rounds.is_file():
        with open(args.extra_rounds, encoding="utf-8") as f:
            extra = json.load(f)
        if not isinstance(extra, list):
            print("--extra-rounds must be a JSON array", file=sys.stderr)
            sys.exit(1)

    if not args.quiet:
        _log_banner()
        _log("📋 SESSION  (copy/paste this block for bug reports or demos)")
        _log_banner()
        _log(f"📂 PTV file: {ptv_path}")
        _log(f"👤 patient_id={vision.patient_id}")
        _log(f"📊 timeline events loaded: {len(vision.events)}")
        _log(f"💬 clinical query: {args.query!r}")
        _log(f"🔎 semantic hybrid: {'OFF' if args.no_semantic else 'ON'}  (keyword-only if OFF)")
        _log(f"🤖 eoh-llama per round: {'OFF (--no-agent)' if args.no_agent else 'ON'}")
        _log(f"🌐 OLLAMA_URL={ollama_url!r}  OLLAMA_MODEL={ollama_model!r}")
        _log(f"🧬 pe_nodes (PE + working set cap): {args.pe_nodes}")
        _log(f"📏 max_json_chars (prompt to LLM): {args.max_json_chars}")
        _log(f"🧩 max_context_nodes (PTV previews per round): {args.max_context_nodes}")
        _log(f"📎 context_preview_chars (per node): {args.context_preview_chars}")
        _log(
            f"📬 final synthesis JSON: {'OFF' if args.no_final_synthesis else 'ON'} "
            f"(candidates≤{args.final_synthesis_max_candidates}, preview≤{args.final_synthesis_preview_chars})"
        )
        if temporal_recent_years_effective is None:
            _log(
                "📅 temporal reduce: OFF — hybrid/BFS use structural reduce only "
                "(--no-temporal-reduce, or non-positive --temporal-recent-years)"
            )
        else:
            _log(
                f"📅 temporal reduce: ON  recent_years={temporal_recent_years_effective}  "
                f"anchor={args.temporal_anchor!r}"
            )
        _log(f"📦 full_tool_json in output file: {'YES' if args.full_tool_json else 'NO (result_summary only)'}")
        _log(f"➕ extra-rounds file: {args.extra_rounds!s}" if args.extra_rounds else "➕ extra-rounds: (none)")
        _log_banner("-")

    bundle, inspection_entries = run_harness(
        vision,
        query=args.query,
        semantic=not args.no_semantic,
        pe_nodes=args.pe_nodes,
        ollama_url=ollama_url,
        ollama_model=ollama_model,
        run_agent=not args.no_agent,
        max_json_chars=args.max_json_chars,
        extra_rounds=extra,
        full_tool_json=args.full_tool_json,
        quiet=args.quiet,
        max_context_nodes=args.max_context_nodes,
        context_preview_chars=args.context_preview_chars,
        enable_final_synthesis=not args.no_final_synthesis,
        final_synthesis_max_candidates=args.final_synthesis_max_candidates,
        final_synthesis_preview_chars=args.final_synthesis_preview_chars,
        temporal_recent_years=temporal_recent_years_effective,
        temporal_anchor=args.temporal_anchor,
    )

    out_dir = Path(__file__).resolve().parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"tool_agent_harness_{stamp}.json"
    out_log = out_dir / f"tool_agent_harness_{stamp}.log"
    written_at = datetime.now(timezone.utc).isoformat()

    log_meta = {
        "ptv_path": str(ptv_path.resolve()),
        "patient_id": vision.patient_id,
        "query": args.query,
        "semantic_hybrid": not args.no_semantic,
        "run_agent": not args.no_agent,
        "ollama_url": ollama_url,
        "ollama_model": ollama_model,
        "pe_nodes": args.pe_nodes,
        "temporal_recent_years": temporal_recent_years_effective,
        "temporal_anchor": args.temporal_anchor,
        "json_output": str(out_path.resolve()),
        "inspection_log_output": str(out_log.resolve()),
    }
    write_inspection_log(
        out_log,
        written_at_utc=written_at,
        meta=log_meta,
        entries=inspection_entries,
    )

    fs = bundle.get("final_synthesis")
    if isinstance(fs, dict) and not fs.get("skipped"):
        with open(out_log, "a", encoding="utf-8") as lf:
            lf.write("\n\n")
            lf.write("=" * 80 + "\n")
            if fs.get("ok") is False or fs.get("status") == "failed":
                lf.write("FINAL SYNTHESIS — FAILURE RECEIPT (graph rounds above are still valid)\n")
            else:
                lf.write("FINAL SYNTHESIS (structured JSON — response + suggested_nodes + full PTV)\n")
            lf.write(json.dumps(fs, indent=2, ensure_ascii=False))
            lf.write("\n")

    bundle["written_artifacts"] = {
        "json": str(out_path.resolve()),
        "inspection_log": str(out_log.resolve()),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    if not args.quiet:
        _log_banner()
        wall = bundle.get("harness_wall_time_s")
        _log(f"📄 JSON written: {out_path}")
        _log(f"📝 Inspection log (full tool JSON + LLM text): {out_log}")
        _log(f"📊 rounds in file: {len(bundle['rounds'])}  |  wall_time_s: {wall}")
        fsb = bundle.get("final_synthesis")
        if isinstance(fsb, dict) and fsb.get("skipped"):
            _log(f"   final_synthesis: skipped ({fsb.get('reason')})")
        elif isinstance(fsb, dict) and fsb.get("ok") is False:
            _log("   final_synthesis: FAILED (see receipt in JSON — graph rounds are still valid)")
        else:
            _log("   final_synthesis: OK (response + suggested_nodes in JSON)")
        _log("   .log: tool rounds + final block (success or failure receipt).")
        _log_banner()
    else:
        fsb = bundle.get("final_synthesis")
        fs_note = ""
        if isinstance(fsb, dict):
            if fsb.get("skipped"):
                fs_note = f" final_synthesis=skipped:{fsb.get('reason')}"
            elif fsb.get("ok") is False:
                fs_note = " final_synthesis=FAILED(receipt_in_json)"
            else:
                fs_note = " final_synthesis=ok"
        print(
            f"{_LOG_PREFIX} wrote json={out_path} log={out_log} rounds={len(bundle['rounds'])}{fs_note}",
            flush=True,
        )


if __name__ == "__main__":
    main()
