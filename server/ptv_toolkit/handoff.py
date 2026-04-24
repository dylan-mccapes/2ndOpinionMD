"""
handoff.py — package the 8B probe's working set for the 70B gap agent.

The 8B probe agent on Lucifer collects evidence via the toolkit and emits
a final_answer. For the three-agent pipeline (8B probe -> 70B gap -> 70B
report) the gap agent needs:

* the original question and the probe's plan (route, expanded_query)
* the tool-call sequence and args (provenance)
* the union of every event_id surfaced by any tool (the "working set")
* full event rows for the top-N by probe-evidence weight
* a compact graph header (hash, counts, date range)

``build_handoff`` produces a single JSON-serializable dict. ``save_handoff``
writes it to disk next to the harness transcript.

The gap agent then treats the working_set as the default ``event_ids``
argument for ``bfs_expand`` and ``semantic_search`` — it can break out by
omitting that restriction, but the starting posture is "expand from here."
"""
from __future__ import annotations

import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from .agent import AgentLog
from .graph import GraphHandle
from .tools import _event_card


_EID_RX = re.compile(r"pdf_p\d{4,5}_e\d{3,5}")
_HANDOFF_TOP_N_ROWS = 24
_HANDOFF_WORKING_SET_MAX = 120


# ---------------------------------------------------------------------------
# Event-id harvesting
# ---------------------------------------------------------------------------

def _harvest_ids_from_value(value: Any, into: "OrderedDict[str, int]") -> None:
    if isinstance(value, str):
        for m in _EID_RX.findall(value):
            into[m] = into.get(m, 0) + 1
    elif isinstance(value, list):
        for v in value:
            _harvest_ids_from_value(v, into)
    elif isinstance(value, dict):
        for v in value.values():
            _harvest_ids_from_value(v, into)


def _score_seed_ids(log: AgentLog) -> "OrderedDict[str, Dict[str, Any]]":
    """Collect every event_id the probe saw, with a simple weight.

    Weights boost:
      * events the agent cited in final_answer.evidence_event_ids (x3)
      * events returned by code_index_lookup exact / contains (x2)
      * events that appeared in multiple tool results (cumulative)
    """
    scores: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
    first_source: Dict[str, str] = {}

    for turn in log.turns:
        if turn.role != "tool" or not turn.tool:
            continue
        try:
            payload = json.loads(turn.content)
        except Exception:
            payload = {}
        counts: "OrderedDict[str, int]" = OrderedDict()
        _harvest_ids_from_value(payload, counts)
        for eid, c in counts.items():
            bucket = scores.setdefault(eid, {"weight": 0, "sources": [], "mentions": 0})
            bonus = 2 if turn.tool == "code_index_lookup" else 1
            bucket["weight"] += bonus * c
            bucket["mentions"] += c
            if turn.tool not in bucket["sources"]:
                bucket["sources"].append(turn.tool)
            first_source.setdefault(eid, turn.tool)

    # Final-answer citations are strong signal.
    fa = log.final_answer or {}
    for eid in (fa.get("evidence_event_ids") or []):
        if isinstance(eid, str):
            bucket = scores.setdefault(eid, {"weight": 0, "sources": [], "mentions": 0})
            bucket["weight"] += 3
            if "final_answer" not in bucket["sources"]:
                bucket["sources"].append("final_answer")

    ordered = OrderedDict(
        sorted(
            scores.items(),
            key=lambda kv: (-kv[1]["weight"], kv[0]),
        )
    )
    return ordered


# ---------------------------------------------------------------------------
# Handoff build
# ---------------------------------------------------------------------------

def _serialize_tool_trace(log: AgentLog) -> List[Dict[str, Any]]:
    trace: List[Dict[str, Any]] = []
    pending: Optional[Dict[str, Any]] = None
    for turn in log.turns:
        if turn.role == "assistant" and turn.tool and turn.tool != "_plan":
            pending = {
                "tool": turn.tool,
                "args": turn.args,
                "ok": None,
                "n_events_returned": 0,
                "error": None,
            }
            trace.append(pending)
        elif turn.role == "tool" and pending is not None:
            try:
                payload = json.loads(turn.content)
            except Exception:
                payload = {}
            pending["ok"] = bool(payload.get("ok"))
            if not pending["ok"]:
                pending["error"] = payload.get("error")
            ids: "OrderedDict[str, int]" = OrderedDict()
            _harvest_ids_from_value(payload.get("result"), ids)
            pending["n_events_returned"] = len(ids)
            pending = None
    return trace


def _top_event_rows(
    gh: GraphHandle,
    scored: "OrderedDict[str, Dict[str, Any]]",
    limit: int,
) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for eid, meta in scored.items():
        if eid not in gh.events:
            continue
        ev = gh.events[eid]
        card = _event_card(gh, eid)
        ann = ev.get("annotations") or {}
        card["probe_weight"] = meta["weight"]
        card["probe_sources"] = meta["sources"]
        # Pull a bit more context than the tool-card version for the 70B.
        card["card_title"] = ((ann.get("card") or {}).get("title") or "")
        card["card_one_line"] = ((ann.get("card") or {}).get("one_line") or "")
        card["status_flags"] = ann.get("status_flags") or []
        rows.append(card)
        if len(rows) >= limit:
            break
    return rows


def build_handoff(
    gh: GraphHandle,
    log: AgentLog,
    *,
    working_set_max: int = _HANDOFF_WORKING_SET_MAX,
    top_n_rows: int = _HANDOFF_TOP_N_ROWS,
) -> Dict[str, Any]:
    """Assemble the JSON blob the 70B gap agent consumes."""
    scored = _score_seed_ids(log)
    working_set = list(scored.keys())[:working_set_max]

    return {
        "schema": "ptv_toolkit.handoff.v1",
        "patient_id": gh.graph.get("patient_id"),
        "graph": {
            "path": str(gh.path),
            "graph_hash": gh.graph_hash,
            "n_events": len(gh.events),
            "date_range": gh._date_range(),
            "code_index_summary": gh.snapshot().get("code_index_summary"),
        },
        "probe": {
            "question": log.question,
            "model": log.model,
            "elapsed_sec": log.elapsed_sec,
            "reason_stopped": log.reason_stopped,
            "plan": log.plan,
            "tools_used": log.tools_used,
            "tool_call_sequence": log.tool_call_sequence(),
            "tool_trace": _serialize_tool_trace(log),
            "final_answer": log.final_answer,
        },
        "working_set": {
            "event_ids": working_set,
            "n_total_seen": len(scored),
            "n_included": len(working_set),
            "scoring": "weight = 2*code_lookup_hit + 1*other_tool_hit + 3*final_evidence",
        },
        "top_events": _top_event_rows(gh, scored, top_n_rows),
        "gap_agent_directives": {
            "default_event_ids_for_bfs_expand": working_set,
            "default_event_ids_for_semantic_search": working_set,
            "hint": (
                "Treat working_set as your starting scope. Call bfs_expand or "
                "semantic_search with event_ids=working_set unless the question "
                "specifically requires breaking out. The probe already ran the "
                "toolkit once and surfaced these ids; your job is to find what "
                "was missed."
            ),
        },
    }


def save_handoff(handoff: Dict[str, Any], path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(handoff, indent=2, default=str), encoding="utf-8")
    return p
