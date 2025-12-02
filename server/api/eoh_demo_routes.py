# server/api/eoh_demo_routes.py

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query
from server.eoh_demo.patient_state_builder import build_patient_state

router = APIRouter(prefix="/api/eoh_demo", tags=["eoh-demo"])


@router.get("/patient_state")
async def get_demo_patient_state(as_of: Optional[str] = Query(None)):
    """
    Return a mock patient_state JSON for the synthetic RA patient timeline.
    """
    dt = datetime.fromisoformat(as_of) if as_of else None
    return build_patient_state(dt)

# server/api/eoh_demo_routes.py (add this)

from server.eoh_demo.mock_ra_timeline import MOCK_EVENTS

@router.get("/timeline")
async def get_demo_timeline():
    return [
        {
            "ts": e.ts.isoformat(),
            "kind": e.kind,
            "summary": e.summary,
            "payload": e.payload,
        }
        for e in MOCK_EVENTS
    ]