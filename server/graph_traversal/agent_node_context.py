"""
Attach PTV timeline nodes (human-readable context) to tool JSON for LLM prompts.

The graph tools often return event_ids; this module resolves them to compact node records
so operators/models reason over previews, not opaque identifiers alone.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional, Set

from server.eoh.patient_timeline_vision import PatientTimelineVision, TimelineEventVision


def _edge_total(ev: TimelineEventVision) -> int:
    return sum(len(v) for v in ev.connascence.values())


def _connascence_counts(ev: TimelineEventVision, *, max_kinds: int = 12) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for i, (kind, targets) in enumerate(ev.connascence.items()):
        if i >= max_kinds:
            break
        out[str(kind)] = len(targets)
    return out


def compact_node(
    vision: PatientTimelineVision,
    event_id: str,
    *,
    preview_max: int = 480,
    include_connascence: bool = True,
) -> Dict[str, Any]:
    """Single event as JSON-safe dict for agent context."""
    ev = vision.events.get(event_id)
    if ev is None:
        return {"event_id": event_id, "missing_in_ptv": True}
    prev = ev.preview or ""
    if len(prev) > preview_max:
        prev = prev[: preview_max - 3] + "..."
    row: Dict[str, Any] = {
        "event_id": ev.event_id,
        "event_type": ev.event_type,
        "timestamp": ev.timestamp,
        "status": ev.status,
        "preview": prev,
        "edge_count": _edge_total(ev),
    }
    if include_connascence and ev.connascence:
        row["connascence_counts"] = _connascence_counts(ev)
    return row


def _dedupe_preserve(ids: List[str]) -> List[str]:
    seen: Set[str] = set()
    out: List[str] = []
    for x in ids:
        s = str(x)
        if s and s not in seen:
            seen.add(s)
            out.append(s)
    return out


def collect_ordered_event_ids(raw_result: Dict[str, Any], *, max_ids: int) -> List[str]:
    """
    Pull event ids in a stable, tool-friendly order: primary lists first, then item rows.
    """
    out: List[str] = []

    def add_from_list(lst: Any) -> None:
        if not isinstance(lst, list) or len(out) >= max_ids:
            return
        for x in lst:
            if len(out) >= max_ids:
                break
            if not isinstance(x, str):
                continue
            s = x.strip()
            if not s:
                continue
            # summarize_tool_result_for_llm may append "... +N more" placeholders
            if s.startswith("...") and "more" in s:
                continue
            out.append(s)

    eids = raw_result.get("event_ids")
    add_from_list(eids)

    snap = raw_result.get("snapshot")
    if isinstance(snap, dict) and len(out) < max_ids:
        nodes = snap.get("nodes")
        if isinstance(nodes, list):
            for n in nodes:
                if len(out) >= max_ids:
                    break
                if isinstance(n, dict) and n.get("event_id"):
                    out.append(str(n["event_id"]))

    items = raw_result.get("items")
    if isinstance(items, list):
        for it in items:
            if len(out) >= max_ids:
                break
            if not isinstance(it, dict):
                continue
            eid = it.get("event_id") or it.get("id")
            if eid:
                out.append(str(eid))

    return _dedupe_preserve(out)[:max_ids]


def _item_hints_for_ids(raw_result: Dict[str, Any], ids: List[str]) -> Dict[str, Dict[str, Any]]:
    """Map event_id -> small dict of tool-specific fields (classification, etc.)."""
    want = set(ids)
    found: Dict[str, Dict[str, Any]] = {}
    items = raw_result.get("items")
    if not isinstance(items, list):
        return found
    keys_keep = (
        "classification",
        "classification_before",
        "classification_after",
        "mean_x",
        "load_bearing",
        "reason",
    )
    for it in items:
        if not isinstance(it, dict):
            continue
        eid = str(it.get("event_id") or it.get("id") or "")
        if not eid or eid not in want or eid in found:
            continue
        hint = {k: it[k] for k in keys_keep if k in it}
        if hint:
            found[eid] = hint
    return found


def enrich_tool_result_for_agent(
    vision: PatientTimelineVision,
    tool_name: str,
    raw_result: Dict[str, Any],
    summarized: Dict[str, Any],
    *,
    max_context_nodes: int = 48,
    preview_chars: int = 480,
) -> Dict[str, Any]:
    """
    Return a copy of `summarized` with `context_nodes` (and metadata) for the LLM.
    Does not remove original fields; adds structured timeline context alongside capped ids.
    """
    out = copy.deepcopy(summarized)
    ids = collect_ordered_event_ids(raw_result, max_ids=max(64, max_context_nodes * 2))
    ids = ids[:max_context_nodes]
    hints = _item_hints_for_ids(raw_result, ids)

    nodes: List[Dict[str, Any]] = []
    for eid in ids:
        n = compact_node(vision, eid, preview_max=preview_chars, include_connascence=True)
        h = hints.get(eid)
        if h:
            n["tool_row"] = h
        nodes.append(n)

    out["context_nodes"] = nodes
    out["context_node_count"] = len(nodes)
    out["context_note"] = (
        f"Expanded {len(nodes)} PTV timeline node(s) with preview text; "
        f"event_id lists above may list additional ids without full text."
    )
    # Shrink id spam in agent copy when reduce returned a huge kept set (counts stay in kept_count)
    full_n = len(raw_result.get("event_ids") or [])
    if tool_name == "graph_reduce" and full_n > 24:
        evs = out.get("event_ids")
        if isinstance(evs, list):
            head = [
                x
                for x in evs
                if isinstance(x, str) and x.strip() and not (x.strip().startswith("...") and "more" in x)
            ][:24]
            out["event_ids_head"] = head
            out["event_ids_total"] = full_n
            del out["event_ids"]

    return out
