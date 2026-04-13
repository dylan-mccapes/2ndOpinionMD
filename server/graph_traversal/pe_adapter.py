"""
Convert PatientTimelineVision events into provenance-engine JSONL-style nodes.

Used by the Norman graph sandbox and optional `pe` CLI workflows.
Edge types map to PE weights (STRUCTURAL, TEMPORAL, SUPPORTING, ...).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from server.eoh.patient_timeline_vision import PatientTimelineVision, TimelineEventVision
from server.utils.parse_date import parse_clinical_date

_PE_EDGE_MAP = {
    "temporal": "TEMPORAL",
    "treatment": "STRUCTURAL",
    "diagnostic": "SUPPORTING",
    "causal": "STRUCTURAL",
    "lab_trend": "SUPPORTING",
    "symptom_cluster": "CO_OCCURRENCE",
    "drug_response": "STRUCTURAL",
}


def _edge_total(ev: TimelineEventVision) -> int:
    return sum(len(v) for v in ev.connascence.values())


def _importance(ev: TimelineEventVision) -> str:
    et = ev.event_type
    n = _edge_total(ev)
    if et in ("diagnosis", "lab") and n >= 3:
        return "high"
    if n >= 1:
        return "medium"
    return "low"


def _load_bearing(ev: TimelineEventVision) -> bool:
    return ev.event_type == "diagnosis" or _edge_total(ev) > 12


def _created_at_iso(ev: TimelineEventVision) -> str:
    dt = parse_clinical_date(ev.timestamp) if ev.timestamp else None
    if dt:
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def ptv_event_to_pe_node(
    ev: TimelineEventVision,
    id_set: Set[str],
    *,
    default_strength: float = 0.75,
) -> Dict[str, Any]:
    edges: List[Dict[str, Any]] = []
    for kind, targets in ev.connascence.items():
        pe_type = _PE_EDGE_MAP.get(kind, "CO_OCCURRENCE")
        for tid in targets:
            if tid not in id_set:
                continue
            edges.append({"target": tid, "type": pe_type, "strength": default_strength})

    return {
        "id": ev.event_id,
        "edges": edges,
        "importance": _importance(ev),
        "load_bearing": _load_bearing(ev),
        "created_at": _created_at_iso(ev),
        "metadata": {
            "event_type": ev.event_type,
            "preview": ev.preview[:300],
        },
    }


def vision_to_pe_nodes(
    vision: PatientTimelineVision,
    *,
    event_ids: Optional[List[str]] = None,
    max_nodes: int = 500,
) -> List[Dict[str, Any]]:
    """
    Build PE node list. If event_ids is None, take first max_nodes keys (arbitrary order —
    callers should pass reduced IDs from graph_reduce for quality).
    """
    id_set: Set[str] = set(vision.events.keys())
    if event_ids is None:
        eids = list(vision.events.keys())[:max_nodes]
    else:
        eids = [e for e in event_ids if e in vision.events][:max_nodes]

    id_subset = set(eids)
    return [ptv_event_to_pe_node(vision.events[eid], id_subset) for eid in eids if eid in vision.events]


def run_provenance_engine_classify(
    nodes: List[Dict[str, Any]],
    *,
    rho: float = 28.0,
    tau: float = 2.0,
) -> Dict[str, Any]:
    """
    Classify nodes using provenance-engine when installed.
    Returns { ok, error?, items: [...] }.
    """
    try:
        from provenance_engine import build_graph, classify_node, integrate_portal, normalize_and_scale
    except ImportError as e:
        return {"ok": False, "error": f"provenance_engine_import:{e!s}", "items": []}

    if not nodes:
        return {"ok": True, "items": [], "note": "empty_nodes"}

    try:
        graph = build_graph(nodes)
        scaled = normalize_and_scale(graph)
        items: List[Dict[str, Any]] = []
        for node in scaled:
            traj = integrate_portal(node["x0"], node["y0"], node["z0"])
            lb = bool(node.get("load_bearing", False))
            result = classify_node(traj, tau=tau, load_bearing=lb)
            items.append(
                {
                    "id": node.get("id"),
                    "classification": result.get("classification"),
                    "mean_x": result.get("mean_x"),
                    "rho": rho,
                    "tau": tau,
                }
            )
        return {"ok": True, "items": items, "node_count": len(items)}
    except Exception as e:
        return {"ok": False, "error": f"provenance_engine_runtime:{e!s}", "items": []}
