"""
Graph analysis tools for PatientTimelineVision.

Pure Python functions that operate on an in-memory graph.
Designed to be called by gap agents or exposed as tool functions.
No LLM calls — fast and free.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from server.eoh.patient_timeline_vision import PatientTimelineVision
from server.utils.parse_date import parse_clinical_date


def event_type_distribution(vision: PatientTimelineVision) -> Dict[str, int]:
    """Count events by type."""
    counts: Counter = Counter()
    for e in vision.events.values():
        counts[e.event_type] += 1
    return dict(counts.most_common())


def edge_density_by_type(vision: PatientTimelineVision) -> Dict[str, Dict[str, int]]:
    """Edge counts per event type per connascence kind."""
    result: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for e in vision.events.values():
        for kind, targets in e.connascence.items():
            result[e.event_type][kind] += len(targets)
    return {k: dict(v) for k, v in result.items()}


def temporal_gaps(
    vision: PatientTimelineVision,
    min_days: int = 90,
) -> List[Dict[str, Any]]:
    """Find gaps > min_days between consecutive timestamped events."""
    dated: List[Tuple[datetime, str]] = []
    for e in vision.events.values():
        dt = parse_clinical_date(e.timestamp) if e.timestamp else None
        if dt:
            dated.append((dt, e.event_id))
    dated.sort()

    gaps = []
    for i in range(1, len(dated)):
        delta = (dated[i][0] - dated[i - 1][0]).days
        if delta >= min_days:
            gaps.append({
                "from_date": dated[i - 1][0].isoformat()[:10],
                "to_date": dated[i][0].isoformat()[:10],
                "gap_days": delta,
                "from_event": dated[i - 1][1],
                "to_event": dated[i][1],
            })
    return gaps


def orphan_nodes(vision: PatientTimelineVision) -> List[Dict[str, str]]:
    """Nodes with zero connascence edges."""
    results = []
    for e in vision.events.values():
        total_edges = sum(len(v) for v in e.connascence.values())
        if total_edges == 0:
            results.append({
                "event_id": e.event_id,
                "event_type": e.event_type,
                "preview": e.preview[:120],
            })
    return results


def medication_timeline(vision: PatientTimelineVision) -> List[Dict[str, Any]]:
    """Chronological medication events with drug names."""
    meds = []
    for e in vision.events.values():
        if e.event_type != "medication":
            continue
        dt = parse_clinical_date(e.timestamp) if e.timestamp else None
        meds.append({
            "event_id": e.event_id,
            "date": dt.isoformat()[:10] if dt else None,
            "drug_name": e.annotations.get("drug_name", ""),
            "preview": e.preview[:120],
        })
    meds.sort(key=lambda x: x["date"] or "~")
    return meds


def lab_trend(
    vision: PatientTimelineVision,
    lab_keyword: str,
) -> List[Dict[str, Any]]:
    """Filter lab nodes by keyword, return chronological series."""
    kw = lab_keyword.lower()
    results = []
    for e in vision.events.values():
        if e.event_type != "lab":
            continue
        if kw not in e.preview.lower():
            continue
        dt = parse_clinical_date(e.timestamp) if e.timestamp else None
        results.append({
            "event_id": e.event_id,
            "date": dt.isoformat()[:10] if dt else None,
            "preview": e.preview[:120],
        })
    results.sort(key=lambda x: x["date"] or "~")
    return results


def cluster_by_type_and_month(
    vision: PatientTimelineVision,
    event_type: str,
) -> Dict[str, int]:
    """Monthly event counts for a given type. Keys are YYYY-MM."""
    counts: Counter = Counter()
    for e in vision.events.values():
        if e.event_type != event_type:
            continue
        dt = parse_clinical_date(e.timestamp) if e.timestamp else None
        if dt:
            counts[dt.strftime("%Y-%m")] += 1
    return dict(sorted(counts.items()))


GRAPH_TOOLS: Dict[str, Any] = {
    "event_type_distribution": event_type_distribution,
    "edge_density_by_type": edge_density_by_type,
    "temporal_gaps": temporal_gaps,
    "orphan_nodes": orphan_nodes,
    "medication_timeline": medication_timeline,
    "lab_trend": lab_trend,
    "cluster_by_type_and_month": cluster_by_type_and_month,
}
