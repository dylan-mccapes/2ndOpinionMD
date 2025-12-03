# server/eoh_demo/mock_ra_timeline.py

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, List, Dict, Any


EventKind = Literal["visit", "lab", "flare", "med_change", "journal"]


@dataclass
class Event:
    ts: datetime
    kind: EventKind
    summary: str
    detail: str | None = None
    payload: Dict[str, Any] | None = None


# Synthetic RA patient: 38F, seropositive RA, MTX + adalimumab, 2 flares
MOCK_EVENTS: List[Event] = [
    Event(
        ts=datetime(2024, 12, 1, 9),
        kind="visit",
        summary="Initial rheumatology visit – seropositive RA diagnosed",
        detail="Swollen MCPs/PIPs, morning stiffness > 1h, RF+, anti-CCP+",
        payload={"das28": 5.6, "seropositive": True},
    ),
    Event(
        ts=datetime(2024, 12, 1, 10),
        kind="med_change",
        summary="Start methotrexate 15 mg weekly + folic acid",
        payload={"methotrexate_mg_weekly": 15, "adalimumab": "none"},
    ),
    Event(
        ts=datetime(2025, 2, 15, 9),
        kind="lab",
        summary="CRP/ESR improved but still elevated",
        payload={"CRP": 12.0, "ESR": 34},
    ),
    Event(
        ts=datetime(2025, 3, 1, 9),
        kind="med_change",
        summary="Add adalimumab 40 mg q2w",
        payload={"adalimumab_mg": 40, "adalimumab_freq": "q2w"},
    ),
    Event(
        ts=datetime(2025, 4, 10, 8),
        kind="flare",
        summary="Moderate flare – swollen hands, morning stiffness 2h",
        payload={"severity": "moderate", "steroids_burst_mg": 20},
    ),
    Event(
        ts=datetime(2025, 4, 10, 9),
        kind="lab",
        summary="CRP and ESR rise with flare",
        payload={"CRP": 28.0, "ESR": 52},
    ),
    Event(
        ts=datetime(2025, 6, 5, 8),
        kind="flare",
        summary="Moderate flare – knees and wrists",
        payload={"severity": "moderate", "steroids_burst_mg": 15},
    ),
    Event(
        ts=datetime(2025, 6, 20, 9),
        kind="lab",
        summary="Inflammatory markers back toward baseline",
        payload={"CRP": 6.0, "ESR": 22},
    ),
    Event(
        ts=datetime(2025, 7, 1, 8),
        kind="visit",
        summary="Clinic visit – low disease activity on MTX + adalimumab",
        payload={"das28": 3.0, "global": "low_activity"},
    ),
    Event(
        ts=datetime(2025, 7, 15, 22),
        kind="journal",
        summary="Pt reports mild stiffness on busy weeks, otherwise doing well",
        detail="Logs in app: ‘When I work 10+ hour days, hands ache more in evening.’",
    ),
]
