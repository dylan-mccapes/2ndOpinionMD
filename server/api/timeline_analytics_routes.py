"""
Timeline Analytics API — Phase 6b

Endpoints:
  GET  /api/timeline/{patient_id}/analytics/summary
  GET  /api/timeline/{patient_id}/analytics/precedence
  GET  /api/timeline/{patient_id}/analytics/trajectory
  POST /api/timeline/{patient_id}/analytics/export

Event sources: prefers ``ehr.patient_timeline``; if empty, falls back to dated
events in ``ehr.patient_graph_vision`` (PTV / vault) so the React
``TimelineChartCard`` and Epistemic Vault dashboard can chart vault-only data.
"""

from __future__ import annotations

import json
import logging
from datetime import timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_session
from server.timeline.analytics import (
    build_windowed_vectors,
    compute_window_metrics,
    detect_phase_shifts,
    extract_flare_episodes,
    compute_precedence_edges,
    compute_trajectory_points,
    compute_analytics_summary,
    DEFAULT_WINDOW_DAYS,
)
from server.timeline.charts import render_all_charts

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/timeline",
    tags=["timeline-analytics"],
)


# ---------------------------------------------------------------------------
# Shared: load events from ehr.patient_timeline, else PTV graph_json
# ---------------------------------------------------------------------------

async def _load_events_from_sql(
    db: AsyncSession,
    patient_id: str,
) -> List[Dict[str, Any]]:
    rows_q = await db.execute(
        text(
            """
            SELECT id,
                   patient_id,
                   ts,
                   event_type,
                   source,
                   structured,
                   text,
                   meta
            FROM ehr.patient_timeline
            WHERE patient_id = :pid
            ORDER BY ts ASC
            """
        ),
        {"pid": patient_id},
    )
    rows = rows_q.mappings().all()

    events: List[Dict[str, Any]] = []
    for row in rows:
        events.append(
            {
                "id": row["id"],
                "patient_id": row["patient_id"],
                "ts": row["ts"],
                "event_type": row["event_type"],
                "source": row["source"],
                "structured": row["structured"],
                "text": row["text"],
                "meta": row["meta"] or {},
            }
        )
    return events


async def _load_events_from_ptv(
    db: AsyncSession,
    patient_id: str,
) -> List[Dict[str, Any]]:
    """
    When ``ehr.patient_timeline`` has no rows (vault-first / PTV-only flows),
    synthesize analytics-compatible events from ``ehr.patient_graph_vision``.
    """
    from server.utils.parse_date import extract_date_from_text, parse_clinical_date

    row_q = await db.execute(
        text(
            """
            SELECT graph_json
            FROM ehr.patient_graph_vision
            WHERE patient_id = :pid
            """
        ),
        {"pid": patient_id},
    )
    row = row_q.mappings().first()
    if not row or row.get("graph_json") is None:
        return []

    gj = row["graph_json"]
    if isinstance(gj, str):
        gj = json.loads(gj)
    if not isinstance(gj, dict):
        return []

    events_section = gj.get("events") or {}
    out: List[Dict[str, Any]] = []
    for eid, raw in events_section.items():
        if not isinstance(raw, dict):
            continue
        event_id = str(raw.get("event_id") or eid)
        ts_raw = (raw.get("timestamp") or "").strip()
        preview = (raw.get("preview") or "") or ""
        ts = parse_clinical_date(ts_raw) if ts_raw else None
        if ts is None and preview:
            ts = extract_date_from_text(preview)
        if ts is None:
            continue
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        discovered = raw.get("discovered_by") or []
        src = "ptv"
        if isinstance(discovered, list) and discovered:
            src = ",".join(str(x) for x in discovered[:3])
        elif isinstance(discovered, str) and discovered:
            src = discovered
        out.append(
            {
                "id": event_id,
                "patient_id": patient_id,
                "ts": ts,
                "event_type": raw.get("event_type") or "unknown",
                "source": src,
                "structured": None,
                "text": preview[:4000] if preview else None,
                "meta": {"from_ptv": True},
            }
        )

    out.sort(key=lambda e: e["ts"])
    return out


async def _load_events(
    db: AsyncSession,
    patient_id: str,
) -> List[Dict[str, Any]]:
    sql_events = await _load_events_from_sql(db, patient_id)
    if sql_events:
        return sql_events
    return await _load_events_from_ptv(db, patient_id)


# ---------------------------------------------------------------------------
# GET /api/timeline/{patient_id}/analytics/summary
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/analytics/summary")
async def analytics_summary(
    patient_id: str,
    window_days: int = Query(DEFAULT_WINDOW_DAYS, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    events = await _load_events(db, patient_id)
    if not events:
        raise HTTPException(status_code=404, detail="No timeline events for patient")

    summary = compute_analytics_summary(
        patient_id=patient_id,
        events=events,
        connascence_edges=[],
        window_days=window_days,
    )

    charts = render_all_charts(
        metrics=summary.windows,
        phase_shifts=summary.phase_shifts,
        flare_episodes=summary.flare_episodes,
        noise_floor=summary.noise_floor,
        precedence_edges=compute_precedence_edges(events),
        trajectory_points=compute_trajectory_points(
            build_windowed_vectors(events, [], window_days),
            summary.windows,
        ),
        patient_id=patient_id,
    )

    return {
        "patient_id": patient_id,
        "window_days": summary.window_days,
        "total_events": summary.total_events,
        "span_days": summary.span_days,
        "windows": [
            {
                "window_start": w.window_start,
                "window_end": w.window_end,
                "drift": w.drift,
                "curvature": w.curvature,
                "connascence_load": w.connascence_load,
                "stability_score": w.stability_score,
                "event_count": w.event_count,
            }
            for w in summary.windows
        ],
        "phase_shifts": [
            {
                "timestamp": ps.timestamp,
                "from_phase": ps.from_phase,
                "to_phase": ps.to_phase,
                "stability_before": ps.stability_before,
                "stability_after": ps.stability_after,
                "evidence_event_ids": ps.evidence_event_ids,
            }
            for ps in summary.phase_shifts
        ],
        "flare_episodes": [
            {
                "start": fe.start,
                "end": fe.end,
                "confidence": fe.confidence,
                "peak_intensity": fe.peak_intensity,
                "supporting_event_ids": fe.supporting_event_ids,
            }
            for fe in summary.flare_episodes
        ],
        "noise_floor": summary.noise_floor,
        "charts": charts,
        "params": summary.params,
        "disclaimer": (
            "This is a decision-support tool, not a diagnosis. "
            "All metrics reflect predictive associations, not causation."
        ),
    }


# ---------------------------------------------------------------------------
# GET /api/timeline/{patient_id}/analytics/precedence
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/analytics/precedence")
async def analytics_precedence(
    patient_id: str,
    max_lag_days: int = Query(30, ge=1, le=180),
    min_support: int = Query(2, ge=1, le=50),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    events = await _load_events(db, patient_id)
    if not events:
        raise HTTPException(status_code=404, detail="No timeline events for patient")

    edges = compute_precedence_edges(events, max_lag_days=max_lag_days, min_support=min_support)

    return {
        "patient_id": patient_id,
        "max_lag_days": max_lag_days,
        "min_support": min_support,
        "edges": [
            {
                "from_type": e.from_type,
                "to_type": e.to_type,
                "median_lag_days": e.median_lag_days,
                "support_count": e.support_count,
                "confidence": e.confidence,
            }
            for e in edges
        ],
        "total_edges": len(edges),
        "disclaimer": (
            "Lagged associations are predictive, not causal. "
            "Clinical judgment is required for interpretation."
        ),
    }


# ---------------------------------------------------------------------------
# GET /api/timeline/{patient_id}/analytics/trajectory
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/analytics/trajectory")
async def analytics_trajectory(
    patient_id: str,
    window_days: int = Query(DEFAULT_WINDOW_DAYS, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    events = await _load_events(db, patient_id)
    if not events:
        raise HTTPException(status_code=404, detail="No timeline events for patient")

    vectors = build_windowed_vectors(events, [], window_days)
    metrics = compute_window_metrics(vectors)
    points = compute_trajectory_points(vectors, metrics)

    return {
        "patient_id": patient_id,
        "window_days": window_days,
        "points": [
            {
                "timestamp": p.timestamp,
                "x": p.x,
                "y": p.y,
                "stability_class": p.stability_class,
                "event_count": p.event_count,
            }
            for p in points
        ],
        "total_points": len(points),
        "disclaimer": (
            "Trajectory is a 2D projection of windowed feature vectors. "
            "Proximity does not imply clinical equivalence."
        ),
    }


# ---------------------------------------------------------------------------
# POST /api/timeline/{patient_id}/analytics/export
# ---------------------------------------------------------------------------

@router.post("/{patient_id}/analytics/export")
async def analytics_export(
    patient_id: str,
    window_days: int = Query(DEFAULT_WINDOW_DAYS, ge=1, le=90),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    events = await _load_events(db, patient_id)
    if not events:
        raise HTTPException(status_code=404, detail="No timeline events for patient")

    summary = compute_analytics_summary(
        patient_id=patient_id,
        events=events,
        connascence_edges=[],
        window_days=window_days,
    )

    precedence_edges = compute_precedence_edges(events)
    vectors = build_windowed_vectors(events, [], window_days)
    trajectory_points = compute_trajectory_points(vectors, summary.windows)

    charts = render_all_charts(
        metrics=summary.windows,
        phase_shifts=summary.phase_shifts,
        flare_episodes=summary.flare_episodes,
        noise_floor=summary.noise_floor,
        precedence_edges=precedence_edges,
        trajectory_points=trajectory_points,
        patient_id=patient_id,
    )

    return {
        "patient_id": patient_id,
        "export_type": "analytics_package",
        "window_days": window_days,
        "summary": {
            "total_events": summary.total_events,
            "span_days": summary.span_days,
            "phase_shift_count": len(summary.phase_shifts),
            "flare_episode_count": len(summary.flare_episodes),
            "noise_floor": summary.noise_floor,
        },
        "charts": charts,
        "precedence": [
            {
                "from_type": e.from_type,
                "to_type": e.to_type,
                "median_lag_days": e.median_lag_days,
                "support_count": e.support_count,
                "confidence": e.confidence,
            }
            for e in precedence_edges
        ],
        "evidence_appendix": {
            "phase_shifts": [
                {
                    "timestamp": ps.timestamp,
                    "from_phase": ps.from_phase,
                    "to_phase": ps.to_phase,
                    "evidence_event_ids": ps.evidence_event_ids,
                }
                for ps in summary.phase_shifts
            ],
            "flare_episodes": [
                {
                    "start": fe.start,
                    "end": fe.end,
                    "confidence": fe.confidence,
                    "supporting_event_ids": fe.supporting_event_ids,
                }
                for fe in summary.flare_episodes
            ],
        },
        "params": summary.params,
        "disclaimer": (
            "This export package is for clinician review only. "
            "Metrics represent predictive associations, not diagnoses. "
            "All findings require clinical correlation."
        ),
    }
