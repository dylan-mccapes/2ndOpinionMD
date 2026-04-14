#!/usr/bin/env python3
"""
Agentic probe harness — the agent **chooses** which tools to call.

Unlike tool_agent_harness.py (fixed pipeline), this harness:

1. Loads the PTV, runs a structural graph_reduce once (shared across queries).
2. For each query from the Grok-20 query set (or a custom JSON):
   a. Runs graph_hybrid_search (semantic=True) on the reduced corpus to get seed event_ids.
   b. Hands the agent the seeds, context_nodes, query, and the **full tool registry**.
   c. The agent responds with a JSON tool_call or a final_answer.
   d. The harness executes the tool, returns the result, and loops (up to --max-rounds).
   e. When the agent emits final_answer, the harness records the probe result.
3. After all queries, produces a **gap report** and writes a timestamped **JSON** bundle plus a plain-text
   **`.log`** with each query and model answer for easy reading.

Usage (repo root, venv, PYTHONPATH=.):
  python sandbox/norman_graph_retrieval/agentic_probe_harness.py --no-agent   # tools only, seeds per query
  python sandbox/norman_graph_retrieval/agentic_probe_harness.py -n 3         # first 3 queries only
  python sandbox/norman_graph_retrieval/agentic_probe_harness.py --query-ids Q01,Q05,Q12
"""

from __future__ import annotations

import argparse
import copy
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
from server.graph_traversal.agent_tools import (
    GRAPH_TOOL_DEFINITIONS,
    execute_graph_tool,
    list_graph_tool_names,
)
from server.graph_traversal.ollama_local import (
    ollama_chat_messages,
    ollama_preflight,
    ollama_reply_text,
)
from server.graph_traversal.agent_node_context import compact_node, enrich_tool_result_for_agent
from server.graph_traversal.tool_result_summary import summarize_tool_result_for_llm

DEFAULT_PTV = (
    ROOT
    / "artifacts"
    / "timeline_ollama_20260329_1805"
    / "patient_timeline_vision_norman_eric_roberts_20260329_195915.json"
)
DEFAULT_QUERIES = Path(__file__).resolve().parent / "grok_20_queries.json"

_LOG_PREFIX = "[agentic-probe]"


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

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


def _emit_full_query_and_answer(
    emit_fn: Callable[[str], None],
    *,
    query_id: str,
    query: str,
    response_text: str,
    gaps: Optional[List[str]],
    status: str,
    seeds_only: bool = False,
    curated_pack: Optional[Dict[str, Any]] = None,
) -> None:
    """Print full query and full final answer to the terminal (copy/paste friendly)."""
    w = 76
    bar = "=" * w
    emit_fn("")
    emit_fn(bar)
    emit_fn(f"  FULL QUERY  [{query_id}]  (status={status})")
    emit_fn(bar)
    emit_fn(query.strip() if query else "(empty query)")
    emit_fn("")
    if curated_pack and not seeds_only:
        emit_fn(bar)
        emit_fn("  CURATED CONTEXT (handoff to reasoning agent)")
        emit_fn(bar)
        emit_fn(f"  confidence:    {curated_pack.get('confidence')}")
        emit_fn(f"  primary nodes: {len(curated_pack.get('primary_event_ids') or [])}")
        emit_fn(f"  working set:   {curated_pack.get('total_nodes_in_working_set', '?')} unique event_ids across all rounds")
        emit_fn(f"  explanation:   {str(curated_pack.get('what_this_context_is') or '').strip()}")
        pids = curated_pack.get("primary_event_ids") or []
        if pids:
            emit_fn(f"  event_ids:     {', '.join(pids[:15])}")
            if len(pids) > 15:
                emit_fn(f"                 ... +{len(pids) - 15} more")
        emit_fn("")
    emit_fn(bar)
    emit_fn("  FULL FINAL ANSWER (operator response text)")
    emit_fn(bar)
    if seeds_only:
        emit_fn("(No LLM answer — run without --no-agent to produce a final answer.)")
    elif (response_text or "").strip():
        emit_fn(response_text.strip())
    else:
        emit_fn("(empty response)")
    if gaps:
        emit_fn("")
        emit_fn(bar)
        emit_fn("  GAPS")
        emit_fn(bar)
        for g in gaps:
            emit_fn(str(g).strip())
    emit_fn(bar)
    emit_fn("")


# ---------------------------------------------------------------------------
# Tool registry doc for the agent prompt
# ---------------------------------------------------------------------------

_TOOL_REGISTRY_DOC = """REQUIRED JSON SHAPE (use exactly these keys — the host parser rejects alternate shapes):
  {"tool_call": "<registry_name>", "args": { ... }}

WRONG (do not emit): "name", "tool", "parameters", "strategy_id", OpenAI "function" wrappers, or mixing Lorenz parameters with graph_reduce fields.

When you have gathered enough evidence (include curated_context for the downstream reasoning agent):
  {"final_answer": {"curated_context": {"confidence": 0.0, "what_this_context_is": "...", "primary_event_ids": []},
   "response": "...", "suggested_nodes": [{"event_id": "...", "confidence": 0.0, "rationale": "..."}], "gaps": ["..."]}}

Parameter rules:
- Time windows: ONLY in graph_reduce args: recent_years, temporal_anchor, temporal_start, temporal_end (plus drop_* flags).
- graph_pe_lorenz_classify args: event_ids, rho, tau, steps — NEVER put temporal_* or recent_years here.
- graph_bfs_expand: use "edge_types": ["temporal"] (list of strings). NOT "connascence_type".

Examples:
{"tool_call":"graph_reduce","args":{"drop_page":true,"drop_unknown_timestamp":false,"drop_isolates":true,"recent_years":5.0,"temporal_anchor":"latest_in_corpus"}}
{"tool_call":"graph_bfs_expand","args":{"seed_event_ids":["pdf_x_e0001"],"max_depth":3,"restrict_to_event_ids":["..."],"edge_types":["temporal"]}}
{"tool_call":"graph_pe_lorenz_classify","args":{"event_ids":["..."],"rho":28.0,"tau":2.0,"steps":1500}}

RULES:
- One JSON object per turn — tool_call+args OR final_answer. No markdown fences, no prose.
- event_ids must come from tool output or seeds.
- Up to {max_rounds} tool turns; then final_answer.

Available tools:
"""


def _build_tool_registry_prompt(max_rounds: int) -> str:
    lines = [_TOOL_REGISTRY_DOC.replace("{max_rounds}", str(max_rounds)).strip(), ""]
    for td in GRAPH_TOOL_DEFINITIONS:
        arg_str = json.dumps(td["args"], ensure_ascii=False)
        lines.append(f'  {td["name"]} ({td["strategy_id"]}): {td["summary"]}')
        lines.append(f'    default args: {arg_str}')
    lines.append("")
    lines.append("IMPORTANT: graph_reduce has already been run. You receive `reduced_event_ids` as your starting corpus.")
    lines.append("Use these ids in event_ids / restrict_to_event_ids args to stay on the cleaned subgraph.")
    lines.append("For temporal slicing, call graph_reduce again with recent_years / temporal_anchor on top of the reduced set.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Agent system prompt
# ---------------------------------------------------------------------------

AGENT_SYSTEM = """You are an Ethos-of-Health (EoH) graph operator on a Patient Timeline Vision (PTV) connascence graph.
Your job: iteratively call graph tools to collect the best set of PTV nodes that answer the clinical query,
then hand off that curated context to a downstream reasoning agent.

STRATEGY (how to think across rounds):
1. You start with semantic search seeds (previews + edges). Read them. Decide what's missing.
2. Call tools to EXPAND (graph_bfs_expand), FILTER (graph_reduce with temporal window),
   EVALUATE (graph_pe_lorenz_classify + graph_pe_govern_adjust), or EXPLORE (graph_centrality,
   graph_bridges, graph_kcore, graph_biomarker_icm). Each tool returns event_ids or structured data.
3. Accumulate evidence across rounds. The harness tracks all event_ids you've seen.
4. When you have enough evidence, emit final_answer with curated_context.

OUTPUT FORMAT (critical): each turn emit a single JSON object with EITHER:
  {"tool_call": "<name>", "args": { ... }}   OR   {"final_answer": { ... }}
Do not use "name", "tool", "parameters", or "strategy_id". Those are rejected.

FINAL ANSWER — curated handoff to the reasoning agent:
- "curated_context": {
    "confidence": <0.0-1.0 overall confidence that these nodes answer the query>,
    "what_this_context_is": "<1-4 sentences: what clinical evidence this bundle contains and why it matters for the query>",
    "primary_event_ids": ["<ids in priority order; must come from tool output or seeds; these get full PTV rows attached>"]
  }
- "response": "<short operator-facing summary of what you found and what the reasoning agent should focus on>"
- "suggested_nodes": [{"event_id","confidence","rationale"}, ...]  (up to 10, most clinically relevant)
- "gaps": ["<things the graph could NOT answer — missing labs, monitoring gaps, absent data types, etc.>"]

Parameter rules:
- Temporal windows (recent_years, temporal_anchor, temporal_start, temporal_end): ONLY in graph_reduce args.
- graph_pe_lorenz_classify: event_ids, rho, tau, steps ONLY.
- graph_bfs_expand: use "edge_types" (list), NOT "connascence_type"."""


# ---------------------------------------------------------------------------
# Parsing agent output
# ---------------------------------------------------------------------------

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


# Keys that must never be copied into tool args when merging a loose JSON blob
_RESERVED_PARSED_KEYS = frozenset(
    {
        "tool_call",
        "tool",
        "name",
        "final_answer",
        "parameters",
        "args",
        "strategy_id",
        "function",
        "id",
    }
)

_TEMPORAL_KEYS = frozenset({"recent_years", "temporal_anchor", "temporal_start", "temporal_end"})


def normalize_agent_tool_json(parsed: Dict[str, Any]) -> Tuple[str, Optional[str], Dict[str, Any], List[str]]:
    """
    Normalize LLM tool JSON into (kind, tool_name, args, notes).

    kind is 'final_answer' | 'tool' | 'invalid'.
    Accepts common mistakes: OpenAI-style name/parameters, top-level 'tool', temporal args on wrong tool, etc.
    """
    notes: List[str] = []

    if "final_answer" in parsed:
        fa = parsed["final_answer"]
        if isinstance(fa, dict):
            return ("final_answer", None, fa, notes)
        return ("final_answer", None, {"response": str(fa)}, notes)

    # OpenAI-style function wrapper
    fn = parsed.get("function")
    if isinstance(fn, dict):
        inner_name = fn.get("name")
        if isinstance(inner_name, str) and inner_name.strip():
            parsed = {**parsed, "name": inner_name.strip()}
        argstr = fn.get("arguments")
        if isinstance(argstr, str) and argstr.strip():
            try:
                inner = json.loads(argstr)
                if isinstance(inner, dict):
                    parsed = {**parsed, "parameters": inner}
            except json.JSONDecodeError:
                notes.append("function.arguments_not_json")

    known = frozenset(list_graph_tool_names())

    name: Optional[str] = None
    tc = parsed.get("tool_call")
    if isinstance(tc, str) and tc.strip():
        name = tc.strip()
    elif isinstance(tc, dict):
        n = tc.get("name") or tc.get("function")
        if n is not None:
            name = str(n).strip() or None
        if isinstance(tc.get("arguments"), dict):
            parsed = {**parsed, "args": tc["arguments"]}
        if name:
            notes.append("tool_call_was_object")

    if not name and isinstance(parsed.get("tool"), str):
        name = parsed["tool"].strip()
        notes.append("used_key_tool_instead_of_tool_call")
    if not name and isinstance(parsed.get("name"), str):
        cand = parsed["name"].strip()
        if cand in known:
            name = cand
            notes.append("used_key_name_instead_of_tool_call")

    if not name:
        return ("invalid", None, {}, notes + ["missing_tool_name"])

    args: Dict[str, Any] = {}
    if isinstance(parsed.get("args"), dict):
        args.update(parsed["args"])
    if isinstance(parsed.get("parameters"), dict):
        args.update(parsed["parameters"])
    elif isinstance(parsed.get("parameters"), str):
        try:
            p = json.loads(parsed["parameters"])
            if isinstance(p, dict):
                args.update(p)
        except json.JSONDecodeError:
            notes.append("parameters_not_json")

    for k, v in parsed.items():
        if k in _RESERVED_PARSED_KEYS:
            continue
        args[k] = v

    args.pop("strategy_id", None)
    args.pop("tool", None)
    args.pop("name", None)

    # BFS: connascence_type → edge_types (list of connascence kind strings)
    if "connascence_type" in args and "edge_types" not in args:
        ct = args.pop("connascence_type")
        if isinstance(ct, str):
            args["edge_types"] = [ct]
        elif isinstance(ct, list):
            args["edge_types"] = ct
        notes.append("renamed_connascence_type_to_edge_types")

    has_temporal = bool(_TEMPORAL_KEYS & set(args.keys()))

    # Lorenz must not receive temporal slice parameters — those belong on graph_reduce
    if name == "graph_pe_lorenz_classify" and has_temporal:
        if args.get("event_ids"):
            for k in list(_TEMPORAL_KEYS):
                args.pop(k, None)
            notes.append("stripped_temporal_keys_from_pe_lorenz_kept_event_ids")
        else:
            name = "graph_reduce"
            for drop in ("rho", "tau", "steps", "event_ids"):
                args.pop(drop, None)
            args.setdefault("drop_page", True)
            args.setdefault("drop_unknown_timestamp", False)
            args.setdefault("drop_isolates", True)
            notes.append("temporal_misrouted_from_pe_lorenz_to_graph_reduce")

    if name not in known:
        return ("invalid", name, args, notes + [f"unknown_tool:{name}"])

    return ("tool", name, args, notes)


# ---------------------------------------------------------------------------
# Structural reduce (shared across queries)
# ---------------------------------------------------------------------------

def structural_reduce(
    vision: PatientTimelineVision, emit_fn: Callable[[str], None]
) -> List[str]:
    t0 = time.perf_counter()
    result = execute_graph_tool(
        "graph_reduce",
        vision,
        {"drop_page": True, "drop_unknown_timestamp": False, "drop_isolates": True},
    )
    ms = (time.perf_counter() - t0) * 1000.0
    kept = result.get("event_ids") or []
    dropped = result.get("dropped_count", 0)
    emit_fn(f"✂️  Structural reduce: kept={len(kept)}  dropped={dropped}  ({ms:.1f} ms)")
    return kept


# ---------------------------------------------------------------------------
# Seed generation: hybrid search per query
# ---------------------------------------------------------------------------

def generate_seeds(
    vision: PatientTimelineVision,
    query: str,
    reduced_ids: List[str],
    *,
    top_k: int = 20,
    semantic: bool = True,
    emit_fn: Callable[[str], None],
) -> Tuple[Dict[str, Any], List[str]]:
    t0 = time.perf_counter()
    result = execute_graph_tool(
        "graph_hybrid_search",
        vision,
        {"query": query, "top_k": top_k, "semantic": semantic, "event_ids": reduced_ids},
    )
    ms = (time.perf_counter() - t0) * 1000.0
    seeds = result.get("event_ids") or []
    kw = result.get("keyword_hits", 0)
    sem = result.get("semantic_hits", 0)
    note = result.get("note") or ""
    emit_fn(f"🔎 Seeds: {len(seeds)} hits (kw={kw} sem={sem})  ({ms:.1f} ms)")
    if note:
        emit_fn(f"   note: {note[:200]}")
    return result, seeds


# ---------------------------------------------------------------------------
# Build the user message for each agent turn
# ---------------------------------------------------------------------------

def _build_initial_prompt(
    vision: PatientTimelineVision,
    query: str,
    query_meta: Dict[str, Any],
    seed_result: Dict[str, Any],
    seed_ids: List[str],
    reduced_ids: List[str],
    *,
    max_context_nodes: int,
    preview_chars: int,
    max_rounds: int,
) -> str:
    tool_reg = _build_tool_registry_prompt(max_rounds)
    seed_nodes = [
        compact_node(vision, eid, preview_max=preview_chars, include_connascence=True)
        for eid in seed_ids[:max_context_nodes]
        if eid in vision.events
    ]
    seed_json = json.dumps(seed_nodes, indent=2, ensure_ascii=False)
    if len(seed_json) > 28000:
        seed_json = seed_json[:28000] + "\n... [truncated]"

    hints = query_meta.get("tool_hints") or []
    hint_str = f"\nTool hints (suggestions, not mandatory): {', '.join(hints)}" if hints else ""

    reduced_head = reduced_ids[:60]
    reduced_json = json.dumps(reduced_head, ensure_ascii=False)
    if len(reduced_ids) > 60:
        reduced_json += f"\n... ({len(reduced_ids)} total — use these in restrict_to_event_ids or event_ids for subgraph tools)"

    return f"""{tool_reg}

--- CLINICAL QUERY (this is what the downstream reasoning agent needs answered) ---
{query}{hint_str}

--- REDUCED CORPUS (structural reduce already done; use for restrict_to_event_ids / event_ids) ---
Total reduced_event_ids: {len(reduced_ids)}
First {min(60, len(reduced_ids))} ids: {reduced_json}

--- SEED EVENT_IDS (semantic+keyword hybrid search on the reduced corpus) ---
Seed count: {len(seed_ids)}

Seed context_nodes (preview text, edges, connascence — read these carefully):
{seed_json}

Your goal: call tools to iteratively collect the best PTV nodes that answer the query above.
When you have enough evidence, emit final_answer with curated_context (confidence, explanation, primary_event_ids).
Output ONE JSON object now — your first tool_call."""


# ---------------------------------------------------------------------------
# Normalize final_answer
# ---------------------------------------------------------------------------

def _normalize_suggested(raw: Any, allowed: Set[str], max_n: int = 10) -> List[Dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    out: List[Dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        eid = str(item.get("event_id") or "").strip()
        if eid not in allowed:
            continue
        try:
            conf = max(0.0, min(1.0, float(item.get("confidence", 0))))
        except (TypeError, ValueError):
            conf = 0.0
        out.append({
            "event_id": eid,
            "confidence": conf,
            "rationale": str(item.get("rationale") or "")[:4000],
        })
    out.sort(key=lambda x: -x["confidence"])
    return out[:max_n]


def _attach_ptv(suggested: List[Dict[str, Any]], vision: PatientTimelineVision) -> List[Dict[str, Any]]:
    rich: List[Dict[str, Any]] = []
    for row in suggested:
        eid = row.get("event_id")
        ev = vision.events.get(str(eid)) if eid else None
        r = dict(row)
        r["ptv_full"] = ev.to_dict() if ev else None
        rich.append(r)
    return rich


def build_curated_context_for_reasoning_agent(
    vision: PatientTimelineVision,
    final_answer: Dict[str, Any],
    suggested_full: List[Dict[str, Any]],
    all_event_ids: Optional[Set[str]] = None,
) -> Dict[str, Any]:
    """
    Handoff package for a downstream reasoning agent: confidence, explanation, full PTV rows.
    Merges model `curated_context` with enriched node payloads.
    Falls back to suggested_nodes and then to the accumulated working set
    when primary_event_ids are missing from curated_context.
    """
    cc = final_answer.get("curated_context")
    if not isinstance(cc, dict):
        cc = {}
    try:
        conf = float(cc.get("confidence", float("nan")))
    except (TypeError, ValueError):
        conf = float("nan")
    if conf != conf:  # NaN
        confs = [
            float(x.get("confidence", 0))
            for x in suggested_full
            if isinstance(x, dict)
        ]
        conf = sum(confs) / len(confs) if confs else 0.5
    conf = max(0.0, min(1.0, conf))

    desc = str(
        cc.get("what_this_context_is")
        or cc.get("description")
        or ""
    ).strip()
    if not desc:
        desc = (
            str(final_answer.get("response") or "")[:800].strip()
            or "Curated PTV evidence from graph tools and seeds for downstream reasoning."
        )

    primary_raw: List[str] = []
    for x in cc.get("primary_event_ids") or cc.get("event_ids") or []:
        s = str(x).strip()
        if s and s in vision.events:
            primary_raw.append(s)

    # Fallback: if model didn't provide primary_event_ids, use suggested_nodes
    if not primary_raw and suggested_full:
        for sf in suggested_full:
            eid = sf.get("event_id")
            if eid and str(eid) in vision.events:
                primary_raw.append(str(eid))

    # Last resort: top nodes from the accumulated working set
    if not primary_raw and all_event_ids:
        for eid in sorted(all_event_ids):
            if eid in vision.events:
                primary_raw.append(eid)
            if len(primary_raw) >= 10:
                break

    seen: Set[str] = set()
    primary: List[str] = []
    for x in primary_raw:
        if x not in seen:
            seen.add(x)
            primary.append(x)

    nodes_out: List[Dict[str, Any]] = []
    for eid in primary:
        ev = vision.events.get(eid)
        nodes_out.append(
            {
                "event_id": eid,
                "ptv_full": ev.to_dict() if ev else None,
            }
        )

    return {
        "confidence": conf,
        "what_this_context_is": desc,
        "primary_event_ids": [n.get("event_id") for n in nodes_out if isinstance(n, dict)],
        "context_nodes_with_full_ptv": nodes_out,
        "model_curated_context": cc,
        "total_nodes_in_working_set": len(all_event_ids) if all_event_ids else 0,
    }


def _build_enriched_user_message_after_tool(
    vision: PatientTimelineVision,
    tool_name: str,
    result: Dict[str, Any],
    round_num: int,
    max_rounds: int,
    *,
    query: str,
    all_event_ids: Set[str],
    max_context_nodes: int,
    preview_chars: int,
    max_json_chars: int,
) -> Tuple[str, Dict[str, Any], bool]:
    """Build the exact user message sent to the model + full enriched document (for audit). Third value: truncated."""
    summarized = summarize_tool_result_for_llm(tool_name, result)
    enriched = enrich_tool_result_for_agent(
        vision,
        tool_name,
        result,
        summarized,
        max_context_nodes=max_context_nodes,
        preview_chars=preview_chars,
    )
    payload = json.dumps(enriched, indent=2, ensure_ascii=False)
    truncated = len(payload) > max_json_chars
    if truncated:
        payload = payload[:max_json_chars] + "\n... [truncated for LLM context window]"

    budget_note = ""
    remaining = max_rounds - round_num
    if remaining <= 1:
        budget_note = "\n⚠️  This is your LAST round. You MUST output a final_answer now."
    elif remaining <= 2:
        budget_note = f"\n⚠️  You have {remaining} tool call(s) left. Start preparing your final_answer — prioritize the most relevant nodes."

    collected_count = len(all_event_ids)
    collected_sample = sorted(all_event_ids)[:20]
    collected_str = ", ".join(collected_sample)
    if collected_count > 20:
        collected_str += f" ... ({collected_count} total)"

    user_msg = f"""--- REMINDER: CLINICAL QUERY ---
{query}

--- TOOL RESULT: {tool_name} (round {round_num}/{max_rounds}) ---
{payload}

--- YOUR WORKING SET (nodes collected across all rounds so far) ---
{collected_count} unique event_ids accumulated: [{collected_str}]

Consider: does this working set have enough evidence to answer the query?
- If YES → emit final_answer with curated_context (confidence, explanation, primary_event_ids from your working set).
- If NO → call another tool to expand, filter, or evaluate nodes.{budget_note}

Output ONE JSON object."""
    return user_msg, enriched, truncated


# ---------------------------------------------------------------------------
# Single-query agentic loop
# ---------------------------------------------------------------------------

def run_query_probe(
    vision: PatientTimelineVision,
    query_meta: Dict[str, Any],
    reduced_ids: List[str],
    *,
    ollama_url: str,
    ollama_model: str,
    run_agent: bool,
    semantic: bool,
    seed_top_k: int,
    max_rounds: int,
    max_json_chars: int,
    max_context_nodes: int,
    preview_chars: int,
    emit_fn: Callable[[str], None],
) -> Dict[str, Any]:
    qid = query_meta["id"]
    query = query_meta["query"]
    t0 = time.perf_counter()

    seed_result, seed_ids = generate_seeds(
        vision, query, reduced_ids,
        top_k=seed_top_k, semantic=semantic, emit_fn=emit_fn,
    )

    rounds: List[Dict[str, Any]] = [{
        "round": 0,
        "step": "hybrid_search_seeds",
        "tool": "graph_hybrid_search",
        "args": {"query": query, "top_k": seed_top_k, "semantic": semantic, "event_ids": f"[{len(reduced_ids)} reduced_ids]"},
        "args_full": {
            "query": query,
            "top_k": seed_top_k,
            "semantic": semantic,
            "event_ids": reduced_ids,
        },
        "result_summary": {
            "seed_count": len(seed_ids),
            "keyword_hits": seed_result.get("keyword_hits"),
            "semantic_hits": seed_result.get("semantic_hits"),
        },
        "result_full": copy.deepcopy(seed_result),
        "seed_event_ids": list(seed_ids),
    }]

    tool_usage: Counter = Counter({"graph_hybrid_search": 1})
    all_event_ids: Set[str] = set(seed_ids)

    if not run_agent:
        emit_fn("   🤖 agent OFF — seed-only probe")
        wall = time.perf_counter() - t0
        audit_trail_seeds: List[Dict[str, Any]] = [
            {"kind": "llm_system_prompt", "content": AGENT_SYSTEM},
            {
                "kind": "note",
                "text": "Agent disabled — only structural corpus + hybrid seeds below.",
            },
            {
                "kind": "hybrid_search_seeds",
                "tool": "graph_hybrid_search",
                "args_full": {"query": query, "top_k": seed_top_k, "semantic": semantic, "event_ids": reduced_ids},
                "result_full": copy.deepcopy(seed_result),
                "seed_event_ids": list(seed_ids),
            },
        ]
        _emit_full_query_and_answer(
            emit_fn,
            query_id=qid,
            query=query,
            response_text="",
            gaps=["agent was disabled — use full agent run for an answer"],
            status="seeds_only",
            seeds_only=True,
        )
        return {
            "query_id": qid,
            "query": query,
            "probe_type": query_meta.get("probe_type"),
            "tool_hints": query_meta.get("tool_hints"),
            "rounds": rounds,
            "tool_usage": dict(tool_usage),
            "final_answer": {
                "response": "",
                "suggested_nodes": [],
                "suggested_nodes_with_full_context": [],
                "gaps": ["agent was disabled"],
                "curated_context": None,
            },
            "curated_context_for_reasoning_agent": None,
            "audit_trail": audit_trail_seeds,
            "wall_time_s": round(wall, 3),
            "agent_rounds": 0,
            "status": "seeds_only",
        }

    # Multi-turn chat (system passed once via ollama_chat_messages)
    initial_user = _build_initial_prompt(
        vision, query, query_meta, seed_result, seed_ids, reduced_ids,
        max_context_nodes=max_context_nodes, preview_chars=preview_chars,
        max_rounds=max_rounds,
    )
    chat_messages: List[Dict[str, str]] = [{"role": "user", "content": initial_user}]

    audit_trail: List[Dict[str, Any]] = [
        {"kind": "llm_system_prompt", "role": "system", "content": AGENT_SYSTEM},
        {"kind": "initial_user_message", "round": 0, "content": initial_user},
    ]

    final_answer: Optional[Dict[str, Any]] = None
    agent_rounds = 0

    for rnd in range(1, max_rounds + 1):
        agent_rounds = rnd
        emit_fn(f"   🤖 agent round {rnd}/{max_rounds} ...")

        t_llm = time.perf_counter()
        try:
            resp = ollama_chat_messages(
                ollama_url,
                ollama_model,
                chat_messages,
                system=AGENT_SYSTEM,
                temperature=0.2,
            )
            raw_text = ollama_reply_text(resp)
        except Exception as e:
            emit_fn(f"   ❌ LLM error: {e!s}")
            audit_trail.append({"kind": "llm_error", "round": rnd, "error": str(e)})
            rounds.append({"round": rnd, "step": "agent_error", "error": str(e)})
            break
        ms_llm = (time.perf_counter() - t_llm) * 1000.0

        parsed = _extract_json_object(raw_text)
        audit_trail.append(
            {
                "kind": "assistant_message",
                "round": rnd,
                "raw_text": raw_text,
                "parsed_json": parsed,
                "llm_ms": round(ms_llm, 3),
            }
        )
        if parsed is None:
            emit_fn(f"   ⚠️  unparseable response ({len(raw_text)} chars), forcing final_answer")
            final_answer = {
                "response": raw_text[:8000],
                "suggested_nodes": [],
                "gaps": ["agent response was not valid JSON"],
            }
            audit_trail.append(
                {
                    "kind": "final_answer_forced_unparseable_json",
                    "round": rnd,
                    "raw_text_full": raw_text,
                }
            )
            rounds.append({"round": rnd, "step": "parse_failure", "raw_text_excerpt": raw_text[:2000], "llm_ms": round(ms_llm, 1)})
            break

        kind, nt_name, body, norm_notes = normalize_agent_tool_json(parsed)

        if kind == "final_answer":
            final_answer = body if isinstance(body, dict) else {}
            audit_trail.append(
                {
                    "kind": "final_answer_from_model",
                    "round": rnd,
                    "final_answer": copy.deepcopy(final_answer),
                }
            )
            emit_fn(f"   ✅ final_answer received  ({ms_llm:.0f} ms LLM)")
            rounds.append({"round": rnd, "step": "final_answer", "llm_ms": round(ms_llm, 1)})
            break

        if kind == "invalid":
            raw_excerpt = json.dumps(parsed, ensure_ascii=False)[:600]
            emit_fn(
                f"   ⚠️  invalid tool JSON (notes={norm_notes}) excerpt={raw_excerpt}"
            )
            final_answer = {
                "response": f"Could not parse a valid tool_call from the model. Notes: {norm_notes}",
                "suggested_nodes": [],
                "gaps": [f"invalid_tool_json: {norm_notes}"],
            }
            audit_trail.append(
                {
                    "kind": "final_answer_forced_invalid_tool",
                    "round": rnd,
                    "normalization_notes": norm_notes,
                    "parsed_excerpt": raw_excerpt,
                    "forced_final_answer": copy.deepcopy(final_answer),
                }
            )
            rounds.append({
                "round": rnd,
                "step": "invalid_tool",
                "normalization_notes": norm_notes,
                "raw_model_json_excerpt": raw_excerpt,
                "llm_ms": round(ms_llm, 1),
            })
            break

        if norm_notes:
            emit_fn(f"   🔧 normalized: {norm_notes}")

        tool_name = nt_name
        tool_args = body if isinstance(body, dict) else {}
        assert tool_name is not None
        emit_fn(f"   🔧 tool_call: {tool_name}  ({ms_llm:.0f} ms LLM)")
        tool_usage[tool_name] += 1

        t_tool = time.perf_counter()
        try:
            result = execute_graph_tool(tool_name, vision, tool_args)
        except Exception as e:
            result = {"error": str(e)}
        ms_tool = (time.perf_counter() - t_tool) * 1000.0

        new_ids = result.get("event_ids") or []
        all_event_ids.update(new_ids)
        items = result.get("items") or []
        for it in items:
            eid = it.get("event_id") or it.get("id")
            if eid:
                all_event_ids.add(str(eid))

        emit_fn(f"   ⚙️  {tool_name} done ({ms_tool:.1f} ms)")

        audit_trail.append(
            {
                "kind": "tool_execution",
                "round": rnd,
                "tool": tool_name,
                "args_full": copy.deepcopy(tool_args),
                "normalization_notes": norm_notes,
                "result_full": copy.deepcopy(result),
                "tool_ms": round(ms_tool, 3),
            }
        )

        rounds.append({
            "round": rnd,
            "step": "tool_call",
            "tool": tool_name,
            "args": _safe_args(tool_args),
            "args_full": copy.deepcopy(tool_args),
            "normalization_notes": norm_notes,
            "result_summary": _brief_metrics(tool_name, result),
            "result_full": copy.deepcopy(result),
            "tool_ms": round(ms_tool, 1),
            "llm_ms": round(ms_llm, 1),
        })

        next_msg, enriched_full, trunc = _build_enriched_user_message_after_tool(
            vision, tool_name, result, rnd, max_rounds,
            query=query,
            all_event_ids=all_event_ids,
            max_context_nodes=max_context_nodes,
            preview_chars=preview_chars,
            max_json_chars=max_json_chars,
        )
        audit_trail.append(
            {
                "kind": "context_sent_to_agent_next_turn",
                "round": rnd,
                "user_message_text_sent_to_llm": next_msg,
                "enriched_tool_document_full": enriched_full,
                "enriched_json_truncated_in_user_message": trunc,
            }
        )
        chat_messages.append({"role": "assistant", "content": raw_text})
        chat_messages.append({"role": "user", "content": next_msg})

    # If we exhausted rounds without a final_answer, force one
    if final_answer is None:
        emit_fn("   ⚠️  max rounds exhausted — no final_answer from agent")
        final_answer = {
            "response": "Agent did not produce a final answer within the round budget.",
            "suggested_nodes": [],
            "gaps": ["round budget exhausted"],
        }
        audit_trail.append(
            {
                "kind": "final_answer_forced_max_rounds",
                "reason": "no final_answer JSON within tool budget",
            }
        )

    audit_trail.append({"kind": "ollama_chat_transcript", "messages": copy.deepcopy(chat_messages)})

    # Normalize
    response_text = str(final_answer.get("response") or "")
    allowed = all_event_ids & set(vision.events.keys())
    suggested = _normalize_suggested(final_answer.get("suggested_nodes"), allowed)
    suggested_full = _attach_ptv(suggested, vision)
    gaps = final_answer.get("gaps") or []
    if not isinstance(gaps, list):
        gaps = [str(gaps)]

    curated_pack = build_curated_context_for_reasoning_agent(vision, final_answer, suggested_full, all_event_ids)
    audit_trail.append(
        {"kind": "curated_context_for_reasoning_agent_normalized", "payload": copy.deepcopy(curated_pack)}
    )

    wall = time.perf_counter() - t0
    emit_fn(f"   📊 probe done: {agent_rounds} agent rounds, {sum(tool_usage.values())} tool calls, {len(suggested)} suggested nodes  ({wall:.1f} s)")

    st = "ok" if response_text.strip() else "empty_response"
    _emit_full_query_and_answer(
        emit_fn,
        query_id=qid,
        query=query,
        response_text=response_text,
        gaps=gaps,
        status=st,
        seeds_only=False,
        curated_pack=curated_pack,
    )

    return {
        "query_id": qid,
        "query": query,
        "probe_type": query_meta.get("probe_type"),
        "tool_hints": query_meta.get("tool_hints"),
        "rounds": rounds,
        "tool_usage": dict(tool_usage),
        "final_answer": {
            "response": response_text,
            "suggested_nodes": suggested,
            "suggested_nodes_with_full_context": suggested_full,
            "gaps": gaps,
            "curated_context": final_answer.get("curated_context"),
        },
        "curated_context_for_reasoning_agent": curated_pack,
        "audit_trail": audit_trail,
        "wall_time_s": round(wall, 3),
        "agent_rounds": agent_rounds,
        "status": st,
    }


def _safe_args(args: Dict[str, Any]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for k, v in args.items():
        if isinstance(v, list) and len(v) > 30:
            out[k] = f"[{len(v)} items]"
        else:
            out[k] = v
    return out


def _brief_metrics(tool: str, result: Dict[str, Any]) -> Dict[str, Any]:
    m: Dict[str, Any] = {}
    if "error" in result:
        m["error"] = str(result["error"])[:500]
        return m
    if "event_ids" in result:
        m["event_ids_count"] = len(result["event_ids"])
    if "kept_count" in result:
        m["kept"] = result["kept_count"]
        m["dropped"] = result.get("dropped_count")
    if "items" in result:
        m["items_count"] = len(result["items"])
        labels = Counter(str(it.get("classification", "?")) for it in (result.get("items") or []))
        if labels:
            m["labels"] = dict(labels)
    if "top" in result:
        m["top_count"] = len(result["top"])
    if "bridges" in result:
        m["bridges_count"] = len(result["bridges"])
        m["articulation_points_count"] = len(result.get("articulation_points") or [])
    if "series" in result:
        m["biomarker_series"] = {k: len(v) for k, v in (result.get("series") or {}).items()}
    tf = result.get("temporal_filter")
    if isinstance(tf, dict):
        m["temporal_filter"] = tf
    return m


# ---------------------------------------------------------------------------
# Gap report
# ---------------------------------------------------------------------------

def write_agentic_probe_readability_log(
    path: Path,
    *,
    written_at_utc: str,
    meta: Dict[str, Any],
    bundle: Dict[str, Any],
) -> None:
    """
    Plain-text full audit: query, curated handoff package, operator answer, then complete audit_trail
    (system prompt, every user/assistant message, full tool args/results, full enriched context JSON).
    """
    lines: List[str] = [
        "AGENTIC PROBE HARNESS — FULL AUDIT LOG (queries, curated context, every tool + LLM turn)",
        f"Written (UTC): {written_at_utc}",
        "",
        "--- SESSION ---",
    ]
    for k in sorted(meta.keys()):
        lines.append(f"  {k}: {meta[k]}")
    lines.extend(
        [
            "",
            f"reduced_corpus_size: {bundle.get('reduced_corpus_size')}",
            f"wall_time_s: {bundle.get('wall_time_s')}",
            "",
        ]
    )

    probes = bundle.get("probes") or []
    for i, p in enumerate(probes, 1):
        qid = p.get("query_id", "?")
        lines.append("=" * 80)
        lines.append(f"PROBE {i}/{len(probes)}  [{qid}]  status={p.get('status')!s}")
        if p.get("probe_type"):
            lines.append(f"probe_type: {p.get('probe_type')}")
        lines.append("")
        lines.append("-" * 80)
        lines.append("QUERY (full text)")
        lines.append("-" * 80)
        lines.append(str(p.get("query") or "").strip() or "(missing)")
        lines.append("")

        cc = p.get("curated_context_for_reasoning_agent")
        if cc is not None:
            lines.append("-" * 80)
            lines.append(
                "CURATED CONTEXT FOR REASONING AGENT (confidence + explanation + full PTV nodes)"
            )
            lines.append("-" * 80)
            lines.append(json.dumps(cc, indent=2, ensure_ascii=False, default=str))
            lines.append("")

        fa = p.get("final_answer")
        if isinstance(fa, dict):
            lines.append("-" * 80)
            lines.append("OPERATOR final_answer.response (full text)")
            lines.append("-" * 80)
            resp = str(fa.get("response") or "").strip()
            lines.append(resp if resp else "(empty response)")
            lines.append("")
            mcc = fa.get("curated_context")
            if isinstance(mcc, dict) and mcc:
                lines.append("-" * 80)
                lines.append("MODEL curated_context (raw JSON from final_answer)")
                lines.append("-" * 80)
                lines.append(json.dumps(mcc, indent=2, ensure_ascii=False, default=str))
                lines.append("")
            gaps = fa.get("gaps") or []
            if isinstance(gaps, list) and gaps:
                lines.append("GAPS:")
                for g in gaps:
                    lines.append(f"  - {g}")
                lines.append("")
            sn = fa.get("suggested_nodes") or []
            if isinstance(sn, list) and sn:
                lines.append("SUGGESTED NODES (summary):")
                for row in sn:
                    if not isinstance(row, dict):
                        continue
                    lines.append(json.dumps(row, ensure_ascii=False, default=str))
                lines.append("")
        else:
            lines.append("-" * 80)
            lines.append("No structured final_answer (e.g. --no-agent or error)")
            lines.append("-" * 80)
            gl = p.get("gaps")
            if isinstance(gl, list) and gl:
                for g in gl:
                    lines.append(str(g))
            lines.append("")

        tu = p.get("tool_usage")
        if isinstance(tu, dict) and tu:
            lines.append(f"tool_usage summary: {json.dumps(tu, ensure_ascii=False)}")
            lines.append("")

        rounds = p.get("rounds")
        if isinstance(rounds, list) and rounds:
            lines.append("*" * 80)
            lines.append("ROUNDS (per-step; includes args_full + result_full for tools)")
            lines.append("*" * 80)
            lines.append(json.dumps(rounds, indent=2, ensure_ascii=False, default=str))
            lines.append("")

        trail = p.get("audit_trail")
        if isinstance(trail, list) and trail:
            lines.append("#" * 80)
            lines.append(
                "AUDIT TRAIL — complete: system prompt, initial user message, each assistant reply, "
                "each tool args_full + result_full, each enriched_tool_document_full sent to the model "
                "(full context curation), and ollama_chat_transcript."
            )
            lines.append("#" * 80)
            lines.append(json.dumps(trail, indent=2, ensure_ascii=False, default=str))
            lines.append("")

        lines.append("")

    gr = bundle.get("gap_report") or {}
    lines.append("=" * 80)
    lines.append("GAP REPORT (summary)")
    lines.append(json.dumps(gr, indent=2, ensure_ascii=False))
    lines.append("")
    lines.append("END OF LOG")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")


def build_gap_report(
    probes: List[Dict[str, Any]],
    all_tool_names: List[str],
) -> Dict[str, Any]:
    total_queries = len(probes)
    tool_coverage: Counter = Counter()
    queries_with_gaps: List[str] = []
    queries_empty: List[str] = []
    all_gaps: List[Dict[str, Any]] = []
    suggested_total = 0
    high_confidence_total = 0

    for p in probes:
        for t, c in (p.get("tool_usage") or {}).items():
            tool_coverage[t] += c
        fa = p.get("final_answer") or {}
        gaps = fa.get("gaps") or []
        if gaps:
            queries_with_gaps.append(p["query_id"])
            for g in gaps:
                all_gaps.append({"query_id": p["query_id"], "gap": g})
        sn = fa.get("suggested_nodes") or []
        suggested_total += len(sn)
        high_confidence_total += sum(1 for s in sn if s.get("confidence", 0) >= 0.7)
        if p.get("status") == "empty_response" or not fa.get("response"):
            queries_empty.append(p["query_id"])

    tools_never_used = sorted(set(all_tool_names) - set(tool_coverage.keys()))
    tools_by_frequency = tool_coverage.most_common()

    return {
        "total_queries": total_queries,
        "queries_with_gaps": queries_with_gaps,
        "queries_with_empty_response": queries_empty,
        "total_suggested_nodes": suggested_total,
        "high_confidence_nodes": high_confidence_total,
        "tool_coverage": dict(tools_by_frequency),
        "tools_never_used": tools_never_used,
        "gaps": all_gaps,
    }


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def run_probe_session(
    vision: PatientTimelineVision,
    queries: List[Dict[str, Any]],
    *,
    ollama_url: str,
    ollama_model: str,
    run_agent: bool,
    semantic: bool,
    seed_top_k: int,
    max_rounds: int,
    max_json_chars: int,
    max_context_nodes: int,
    preview_chars: int,
    quiet: bool = False,
) -> Dict[str, Any]:
    emit_fn = _log if not quiet else (lambda _line="": None)

    t0 = time.perf_counter()
    emit_fn()
    _log_banner()
    emit_fn("🚀 Agentic Probe Harness — Grok-20 question probe → gap → report")
    _log_banner()
    emit_fn(f"📊 PTV events: {len(vision.events)}  |  queries: {len(queries)}")
    emit_fn(f"🤖 agent: {'ON' if run_agent else 'OFF'}  |  max_rounds/query: {max_rounds}")
    emit_fn(f"🔎 semantic seeds: {'ON' if semantic else 'OFF'}  |  seed_top_k: {seed_top_k}")
    emit_fn()

    emit_fn("-" * 78)
    emit_fn("PHASE 1: Structural reduce (shared)")
    reduced_ids = structural_reduce(vision, emit_fn)
    emit_fn()

    emit_fn("-" * 78)
    emit_fn("PHASE 2: Per-query agentic probes")
    emit_fn()

    probes: List[Dict[str, Any]] = []
    for i, qm in enumerate(queries, 1):
        emit_fn("-" * 78)
        emit_fn(f"QUERY {i}/{len(queries)}  [{qm['id']}]  {qm['query'][:100]}")
        try:
            probe = run_query_probe(
                vision, qm, reduced_ids,
                ollama_url=ollama_url,
                ollama_model=ollama_model,
                run_agent=run_agent,
                semantic=semantic,
                seed_top_k=seed_top_k,
                max_rounds=max_rounds,
                max_json_chars=max_json_chars,
                max_context_nodes=max_context_nodes,
                preview_chars=preview_chars,
                emit_fn=emit_fn,
            )
        except Exception as e:
            emit_fn(f"   ❌ QUERY FAILED: {type(e).__name__}: {e!s}")
            probe = {
                "query_id": qm["id"],
                "query": qm["query"],
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()[-4000:],
                "rounds": [],
                "tool_usage": {},
                "final_answer": None,
                "curated_context_for_reasoning_agent": None,
                "audit_trail": [],
                "suggested_nodes": [],
                "gaps": [f"query failed: {e!s}"],
                "wall_time_s": 0,
                "agent_rounds": 0,
            }
        probes.append(probe)
        emit_fn()

    emit_fn("-" * 78)
    emit_fn("PHASE 3: Gap report")
    gap_report = build_gap_report(probes, list_graph_tool_names())
    emit_fn(f"   queries with gaps: {len(gap_report['queries_with_gaps'])}/{len(queries)}")
    emit_fn(f"   tools never used: {gap_report['tools_never_used']}")
    emit_fn(f"   total suggested nodes: {gap_report['total_suggested_nodes']} (high-conf ≥0.7: {gap_report['high_confidence_nodes']})")
    emit_fn(f"   total gaps reported: {len(gap_report['gaps'])}")
    emit_fn()

    wall = time.perf_counter() - t0
    emit_fn("-" * 78)
    emit_fn(f"✅ Session done: {len(probes)} probes in {wall:.1f} s")
    _log_banner()

    return {
        "patient_id": vision.patient_id,
        "session_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_queries": len(queries),
        "reduced_corpus_size": len(reduced_ids),
        "probes": probes,
        "gap_report": gap_report,
        "wall_time_s": round(wall, 3),
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agentic probe harness: agent picks tools per query, produces gap report"
    )
    parser.add_argument("--ptv", type=Path, default=None)
    parser.add_argument(
        "--queries", type=Path, default=None,
        help="JSON array of {id, query, tool_hints, probe_type}. Default: grok_20_queries.json",
    )
    parser.add_argument(
        "-n", "--num-queries", type=int, default=None,
        help="Run only the first N queries",
    )
    parser.add_argument(
        "--query-ids", type=str, default=None,
        help="Comma-separated query IDs to run (e.g. Q01,Q05,Q12)",
    )
    parser.add_argument("--no-agent", action="store_true", help="Seeds only, no LLM loop")
    parser.add_argument("--no-semantic", action="store_true", help="Keyword-only seeds")
    parser.add_argument("--seed-top-k", type=int, default=20, help="Seeds per query (default 20)")
    parser.add_argument(
        "--max-rounds", type=int, default=6,
        help="Max agent tool calls per query (default 6)",
    )
    parser.add_argument("--max-json-chars", type=int, default=18000)
    parser.add_argument("--max-context-nodes", type=int, default=48)
    parser.add_argument("--context-preview-chars", type=int, default=480)
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument("--skip-ollama-preflight", action="store_true")
    args = parser.parse_args()

    _configure_utf8_streams()

    ollama_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    ollama_model = os.environ.get("OLLAMA_MODEL", "eoh-llama-lucifer")

    if not args.no_agent and not args.skip_ollama_preflight:
        ok, msg = ollama_preflight(ollama_url, ollama_model)
        if not ok:
            print(f"{_LOG_PREFIX} Ollama preflight FAILED: {msg}", file=sys.stderr)
            sys.exit(2)
        if not args.quiet:
            _log(f"✅ {msg}")

    ptv_path = args.ptv or Path(os.environ.get("NORMAN_PTV_JSON", str(DEFAULT_PTV)))
    if not ptv_path.is_file():
        print(f"PTV not found: {ptv_path}", file=sys.stderr)
        sys.exit(1)

    with open(ptv_path, encoding="utf-8") as f:
        vision = PatientTimelineVision.from_dict(json.load(f))

    queries_path = args.queries or DEFAULT_QUERIES
    with open(queries_path, encoding="utf-8") as f:
        all_queries: List[Dict[str, Any]] = json.load(f)

    if args.query_ids:
        wanted = {s.strip() for s in args.query_ids.split(",")}
        all_queries = [q for q in all_queries if q["id"] in wanted]
    if args.num_queries is not None:
        all_queries = all_queries[: args.num_queries]

    if not all_queries:
        print("No queries to run (check --query-ids / -n)", file=sys.stderr)
        sys.exit(1)

    if not args.quiet:
        _log_banner()
        _log("📋 SESSION")
        _log_banner()
        _log(f"📂 PTV: {ptv_path}")
        _log(f"👤 patient_id={vision.patient_id}")
        _log(f"📊 events: {len(vision.events)}")
        _log(f"📝 queries: {len(all_queries)} from {queries_path}")
        _log(f"🤖 agent: {'OFF' if args.no_agent else 'ON'}  model={ollama_model!r}")
        _log(f"🔎 semantic: {'OFF' if args.no_semantic else 'ON'}  seed_top_k={args.seed_top_k}")
        _log(f"🔄 max_rounds/query: {args.max_rounds}")
        _log(f"📏 max_json_chars: {args.max_json_chars}  context_nodes: {args.max_context_nodes}  preview: {args.context_preview_chars}")
        _log_banner("-")

    bundle = run_probe_session(
        vision, all_queries,
        ollama_url=ollama_url,
        ollama_model=ollama_model,
        run_agent=not args.no_agent,
        semantic=not args.no_semantic,
        seed_top_k=args.seed_top_k,
        max_rounds=args.max_rounds,
        max_json_chars=args.max_json_chars,
        max_context_nodes=args.max_context_nodes,
        preview_chars=args.context_preview_chars,
        quiet=args.quiet,
    )

    out_dir = Path(__file__).resolve().parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"agentic_probe_{stamp}.json"
    out_log = out_dir / f"agentic_probe_{stamp}.log"
    written_at = datetime.now(timezone.utc).isoformat()

    log_meta = {
        "ptv_path": str(ptv_path.resolve()),
        "queries_path": str(queries_path.resolve()),
        "patient_id": vision.patient_id,
        "ollama_model": ollama_model,
        "ollama_url": ollama_url,
        "run_agent": not args.no_agent,
        "semantic_seeds": not args.no_semantic,
        "seed_top_k": args.seed_top_k,
        "max_rounds_per_query": args.max_rounds,
    }
    bundle["written_artifacts"] = {
        "json": str(out_path.resolve()),
        "query_answer_log": str(out_log.resolve()),
    }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)

    write_agentic_probe_readability_log(
        out_log,
        written_at_utc=written_at,
        meta=log_meta,
        bundle=bundle,
    )

    if not args.quiet:
        _log_banner()
        _log(f"📄 JSON written: {out_path}")
        _log(f"📝 Query/answer log (readable): {out_log}")
        gap = bundle.get("gap_report") or {}
        _log(f"📊 probes: {bundle['total_queries']}  |  wall: {bundle['wall_time_s']:.1f} s")
        _log(f"   tools used: {gap.get('tool_coverage')}")
        _log(f"   tools never used: {gap.get('tools_never_used')}")
        _log(f"   queries with gaps: {len(gap.get('queries_with_gaps', []))}")
        _log(f"   suggested nodes total: {gap.get('total_suggested_nodes')} (≥0.7 conf: {gap.get('high_confidence_nodes')})")
        _log_banner()
    else:
        print(
            f"{_LOG_PREFIX} wrote json={out_path} log={out_log} probes={bundle['total_queries']}",
            flush=True,
        )


if __name__ == "__main__":
    main()
