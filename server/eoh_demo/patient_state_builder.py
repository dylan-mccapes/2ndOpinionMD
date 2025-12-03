# server/eoh_demo/patient_state_builder.py

from __future__ import annotations

from datetime import datetime, date, timedelta
from typing import Any, Dict, List

from .mock_ra_timeline import MOCK_EVENTS, Event


def _filter_events(as_of: datetime) -> List[Event]:
    return [e for e in MOCK_EVENTS if e.ts <= as_of]


def _recent_events(events: List[Event], days: int) -> List[Event]:
    if not events:
        return []
    cutoff = events[-1].ts - timedelta(days=days)
    return [e for e in events if e.ts >= cutoff]


def build_patient_state(as_of: datetime | None = None) -> Dict[str, Any]:
    """
    Build a conceptual patient_state JSON that matches the EoH plan proposal.
    No DB, just mock data.
    """
    if as_of is None:
        as_of = max(e.ts for e in MOCK_EVENTS)

    events = _filter_events(as_of)
    recent90 = _recent_events(events, 90)

    flares = [e for e in events if e.kind == "flare"]
    recent_flares = [e for e in recent90 if e.kind == "flare"]
    labs = [e for e in events if e.kind == "lab"]

    latest_lab_payload = labs[-1].payload if labs else {}
    latest_visit = next((e for e in reversed(events) if e.kind == "visit"), None)

    # Simple conceptual summaries
    flare_count_last_12m = len(flares)
    flare_count_last_6m = len([e for e in flares if (as_of - e.ts).days <= 180])

    return {
        "as_of": as_of.isoformat(),
        "diagnosis": {
            "primary": "seropositive_rheumatoid_arthritis",
            "notes": [
                "RF+, anti-CCP+ at baseline",
                "Adults onset RA, 38-year-old female",
            ],
        },
        "medications": {
            "methotrexate": {
                "status": "ongoing",
                "dose_mg_weekly": 15,
                "start_date": "2024-12-01",
            },
            "adalimumab": {
                "status": "ongoing",
                "dose_mg": 40,
                "frequency": "q2w",
                "start_date": "2025-03-01",
            },
        },
        "labs": {
            "latest": latest_lab_payload or {},
            "note": "Values are conceptual; CRP/ESR trend interpreted qualitatively.",
        },
        "recent_flares": {
            "last_12m_count": flare_count_last_12m,
            "last_6m_count": flare_count_last_6m,
            "examples": [
                {
                    "ts": e.ts.isoformat(),
                    "severity": (e.payload or {}).get("severity", "unknown"),
                    "summary": e.summary,
                }
                for e in flares
            ],
        },
        "recent_events_window": [
            {
                "ts": e.ts.isoformat(),
                "kind": e.kind,
                "summary": e.summary,
            }
            for e in recent90
        ],
        "disease_activity": {
            "latest_das28": (latest_visit.payload or {}).get("das28") if latest_visit else None,
            "qualitative_state": (latest_visit.payload or {}).get("global", "unknown")
            if latest_visit
            else "unknown",
        },
        "notes": [
            "Patient currently in low disease activity but has had 2 moderate flares in the past year.",
            "On combination csDMARD + bDMARD therapy.",
        ],
    }
