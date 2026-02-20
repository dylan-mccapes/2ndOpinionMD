# server/api/timeline_routes.py

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_session
from server.ann.flare import find_flare_precursors
from server.ann.diagnostic import estimate_diagnostic_landscape
from server.eoh.fusion import fuse_timeline_context
from server.eoh.validators import validate_response_safety

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api",
    tags=["timeline", "eoh"],
)


# ---------------------------------------------------------------------------
# GET /api/timeline/{patient_id}
# ---------------------------------------------------------------------------

@router.get("/timeline/{patient_id}")
async def get_timeline(
    patient_id: str,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Return chronologically ordered, normalized timeline for a patient.

    Shape is as documented in docs/timeline.md:
    {
      "patient_id": "...",
      "events": [...],
      "total_events": N
    }
    """
    # total count
    total_q = await db.execute(
        text(
            """
            SELECT COUNT(*) AS n
            FROM ehr.patient_timeline
            WHERE patient_id = :pid
            """
        ),
        {"pid": patient_id},
    )
    total_events = total_q.scalar_one()

    if total_events == 0:
        return {
            "patient_id": patient_id,
            "events": [],
            "total_events": 0,
        }

    # page of events
    rows_q = await db.execute(
        text(
            """
            SELECT patient_id,
                   ts,
                   event_type,
                   source,
                   structured,
                   text,
                   meta
            FROM ehr.patient_timeline
            WHERE patient_id = :pid
            ORDER BY ts ASC
            LIMIT :limit OFFSET :offset
            """
        ),
        {"pid": patient_id, "limit": limit, "offset": offset},
    )
    rows = rows_q.mappings().all()

    events: List[Dict[str, Any]] = []
    for row in rows:
        events.append(
            {
                "ts": row["ts"].isoformat(),
                "event_type": row["event_type"],
                "source": row["source"],
                "structured": row["structured"],
                "text": row["text"],
                "meta": row["meta"] or {},
            }
        )

    return {
        "patient_id": patient_id,
        "events": events,
        "total_events": total_events,
    }


# ---------------------------------------------------------------------------
# POST /api/timeline/{patient_id}/events  (simple bulk insert)
# ---------------------------------------------------------------------------

@router.post("/timeline/{patient_id}/events")
async def create_timeline_events(
    patient_id: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Create timeline events for a patient.

    Expected payload:
    {
      "events": [
        {
          "ts": "2024-01-15T10:30:00Z",
          "event_type": "...",
          "source": "...",
          "structured": {...},
          "text": "...",
          "meta": {...}
        },
        ...
      ]
    }
    """
    events = payload.get("events") or []
    if not isinstance(events, list) or not events:
        raise HTTPException(status_code=400, detail="events[] required")

    rows_to_insert: List[Dict[str, Any]] = []
    for e in events:
        ts_raw = e.get("ts")
        if not ts_raw:
            raise HTTPException(status_code=400, detail="Each event must have ts")

        try:
            ts = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
        except Exception:
            raise HTTPException(status_code=400, detail=f"Invalid ts: {ts_raw!r}")

        rows_to_insert.append(
            {
                "patient_id": patient_id,
                "ts": ts,
                "event_type": e.get("event_type") or "unknown",
                "source": e.get("source") or "EHR",
                "structured": e.get("structured"),
                "text": e.get("text"),
                "meta": e.get("meta") or {},
            }
        )

    await db.execute(
        text(
            """
            INSERT INTO ehr.patient_timeline
                (patient_id, ts, event_type, source, structured, text, meta)
            VALUES
                (:patient_id, :ts, :event_type, :source, :structured, :text, :meta)
            """
        ),
        rows_to_insert,
    )
    await db.commit()

    return {
        "patient_id": patient_id,
        "inserted": len(rows_to_insert),
    }


# ---------------------------------------------------------------------------
# POST /api/timeline/{patient_id}/search  (simple text search)
# ---------------------------------------------------------------------------

@router.post("/timeline/{patient_id}/search")
async def search_timeline(
    patient_id: str,
    payload: Dict[str, Any],
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Simple semantic-ish search over timeline events.

    Payload:
    {
      "query": "CRP",
      "limit": 50
    }

    For now this is ILIKE on text + structured::text; later you can
    upgrade to pgvector ANN search over the embedding column.
    """
    query = (payload.get("query") or "").strip()
    limit = int(payload.get("limit") or 50)
    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    limit = max(1, min(limit, 200))

    rows_q = await db.execute(
        text(
            """
            SELECT patient_id,
                   ts,
                   event_type,
                   source,
                   structured,
                   text,
                   meta
            FROM ehr.patient_timeline
            WHERE patient_id = :pid
              AND (
                    text ILIKE :q
                 OR structured::text ILIKE :q
              )
            ORDER BY ts DESC
            LIMIT :limit
            """
        ),
        {"pid": patient_id, "q": f"%{query}%", "limit": limit},
    )
    rows = rows_q.mappings().all()

    matches: List[Dict[str, Any]] = []
    for row in rows:
        matches.append(
            {
                "ts": row["ts"].isoformat(),
                "event_type": row["event_type"],
                "source": row["source"],
                "structured": row["structured"],
                "text": row["text"],
                "meta": row["meta"] or {},
            }
        )

    return {
        "patient_id": patient_id,
        "query": query,
        "matches": matches,
        "count": len(matches),
    }


# ---------------------------------------------------------------------------
# Shared helper: load events as dicts for ANN / EoH
# ---------------------------------------------------------------------------

async def _load_timeline_events_for_eoh(
    db: AsyncSession,
    patient_id: str,
    window_days: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """
    Load events from ehr.patient_timeline and convert to the simple dict
    structure expected by server.ann.* and server.eoh.* helpers.
    """
    if window_days is not None:
        # Use proper interval math: int * INTERVAL '1 day'
        where_clause = """
            WHERE patient_id = :pid
              AND ts >= (NOW() AT TIME ZONE 'utc' - (:window_days * INTERVAL '1 day'))
        """
        params = {"pid": patient_id, "window_days": window_days}
    else:
        where_clause = "WHERE patient_id = :pid"
        params = {"pid": patient_id}

    rows_q = await db.execute(
        text(
            f"""
            SELECT ts,
                   event_type,
                   source,
                   structured,
                   text,
                   meta
            FROM ehr.patient_timeline
            {where_clause}
            ORDER BY ts ASC
            """
        ),
        params,
    )
    rows = rows_q.mappings().all()

    # Convert to the simple dict structure expected by ANN / EoH
    events: List[Dict[str, Any]] = []
    for row in rows:
        events.append(
            {
                "ts": row["ts"],
                "event_type": row["event_type"],
                "source": row["source"],
                "structured": row["structured"] or {},
                "text": row["text"],
                "meta": row["meta"] or {},
            }
        )
    return events


# ---------------------------------------------------------------------------
# GET /api/eoh/flarereport/{patient_id}
# ---------------------------------------------------------------------------

@router.get("/eoh/flarereport/{patient_id}")
async def eoh_flare_report(
    patient_id: str,
    window_days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Complete flare prediction report as described in docs/eoh_router.md.
    """
    events = await _load_timeline_events_for_eoh(db, patient_id, window_days=window_days)

    if not events:
        raise HTTPException(status_code=404, detail="No timeline events for patient")

    flare_result = find_flare_precursors(patient_id, window_days=window_days, events=events)
    diagnostic_result = estimate_diagnostic_landscape(patient_id, events=events)

    fused = fuse_timeline_context(
        events=events,
        flare_result=flare_result,
        diagnostic_result=diagnostic_result,
    )

    # Basic narrative; keep it regulatory-friendly
    flare_level = flare_result.get("flare_likelihood", {}).get("level", "unknown")
    flare_forecast = f"Pattern analysis suggests {flare_level} flare risk within the next {window_days} days."

    report = {
        "patient_id": patient_id,
        "window_days": window_days,
        "flare_forecast": flare_forecast,
        "probabilistic_differential": diagnostic_result.get("diagnostic_probabilities", {}),
        "precursor_signals": flare_result.get("precursors", []),
        "contradictions": fused.get("contradictions", []),
        "risk_drivers": diagnostic_result.get("drivers", []),
        "timeline_summary": f"{fused.get('event_count', len(events))} events analyzed over {window_days} days",
        "guidance_for_clinician": [
            "Consider monitoring inflammatory markers and symptom trends over time.",
            "Review medication adherence and recent treatment changes in context.",
        ],
    }

    safety = validate_response_safety(
        {
            "diagnostic_probabilities": report["probabilistic_differential"],
            "drivers": report["risk_drivers"],
            "narrative": report["flare_forecast"],
        }
    )
    if not safety["is_safe"]:
        report["safety_warnings"] = safety["violations"]

    return report


# ---------------------------------------------------------------------------
# GET /api/eoh/landscape/{patient_id}
# ---------------------------------------------------------------------------

@router.get("/eoh/landscape/{patient_id}")
async def eoh_landscape(
    patient_id: str,
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Probabilistic diagnostic landscape only.
    """
    events = await _load_timeline_events_for_eoh(db, patient_id, window_days=None)
    if not events:
        raise HTTPException(status_code=404, detail="No timeline events for patient")

    diagnostic_result = estimate_diagnostic_landscape(patient_id, events=events)

    safety = validate_response_safety(
        {
            "diagnostic_probabilities": diagnostic_result.get("diagnostic_probabilities", {}),
            "drivers": diagnostic_result.get("drivers", []),
        }
    )
    result: Dict[str, Any] = {
        "patient_id": patient_id,
        "diagnostic_probabilities": diagnostic_result.get("diagnostic_probabilities", {}),
        "drivers": diagnostic_result.get("drivers", []),
    }
    if not safety["is_safe"]:
        result["safety_warnings"] = safety["violations"]

    return result


# ---------------------------------------------------------------------------
# GET /api/eoh/flareprediction/{patient_id}
# ---------------------------------------------------------------------------

@router.get("/eoh/flareprediction/{patient_id}")
async def eoh_flare_prediction(
    patient_id: str,
    window_days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Flare likelihood prediction only (thin wrapper over ann.flare).
    """
    events = await _load_timeline_events_for_eoh(db, patient_id, window_days=window_days)
    if not events:
        raise HTTPException(status_code=404, detail="No timeline events for patient")

    flare_result = find_flare_precursors(patient_id, window_days=window_days, events=events)
    return {
        "patient_id": patient_id,
        "window_days": window_days,
        "result": flare_result,
    }


# ---------------------------------------------------------------------------
# GET /api/eoh/timeline-context/{patient_id}
# ---------------------------------------------------------------------------

@router.get("/eoh/timeline-context/{patient_id}")
async def eoh_timeline_context(
    patient_id: str,
    window_days: int = Query(180, ge=1, le=365),
    db: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Return the fused timeline context for EoH router integration.

    This is what you'd prepend (or pass as a side-channel) when using
    ?use_timeline=1 in /api/rag/eoh_stream.
    """
    events = await _load_timeline_events_for_eoh(db, patient_id, window_days=window_days)
    if not events:
        raise HTTPException(status_code=404, detail="No timeline events for patient")

    flare_result = find_flare_precursors(patient_id, window_days=window_days, events=events)
    diagnostic_result = estimate_diagnostic_landscape(patient_id, events=events)

    fused = fuse_timeline_context(
        events=events,
        flare_result=flare_result,
        diagnostic_result=diagnostic_result,
    )

    return {
        "patient_id": patient_id,
        "window_days": window_days,
        "fused_context": fused,
    }
