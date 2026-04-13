from fastapi import APIRouter, Query
from server.mock.fixtures.analytics import (
    ANALYTICS_SUMMARY,
    ANALYTICS_PRECEDENCE,
    ANALYTICS_EXPORT,
)

router = APIRouter(prefix="/api/timeline", tags=["timeline"])

# Import lazily to avoid heavy load at import time
def _fixtures():
    from server.dev_fixtures import get_timeline_status, get_timeline_events
    return get_timeline_status, get_timeline_events


@router.get("/status")
async def timeline_status():
    get_status, _ = _fixtures()
    status = get_status()
    # Always return has_timeline=True in mock mode
    if not status.get("has_timeline"):
        status = {
            "has_timeline": True,
            "timeline_id": "norman-dev-timeline",
            "event_count": 247,
            "last_updated": "2025-12-05T00:00:00Z",
        }
    return status


@router.get("/{patient_id}/analytics/summary")
async def analytics_summary(patient_id: str, window_days: int = Query(7)):
    return {**ANALYTICS_SUMMARY, "patient_id": patient_id, "window_days": window_days}


@router.get("/{patient_id}/analytics/precedence")
async def analytics_precedence(patient_id: str):
    return {**ANALYTICS_PRECEDENCE, "patient_id": patient_id}


@router.post("/{patient_id}/analytics/export")
async def analytics_export(patient_id: str, body: dict = None):
    return {**ANALYTICS_EXPORT, "patient_id": patient_id}


@router.post("/import-pdf")
async def import_pdf():
    return {"status": "complete", "event_count": 247, "timeline_id": "norman-dev-timeline"}


@router.post("/initialize")
async def initialize():
    return {"timeline_id": "norman-dev-timeline", "created": True}


@router.get("/{patient_id}")
async def get_timeline(
    patient_id: str,
    limit: int = Query(200, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    _, get_events = _fixtures()
    try:
        return get_events(limit=limit, offset=offset)
    except Exception:
        # Fallback if PTV file isn't available
        return {
            "patient_id": patient_id,
            "events": [],
            "total_events": 0,
        }
