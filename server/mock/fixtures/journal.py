"""Seed journal entries for mock server."""
from __future__ import annotations

import copy
from datetime import datetime, timezone

_SEED: list[dict] = [
    {
        "id": "jrn-001",
        "user_id": "user-norman-dev",
        "date": "2025-12-01",
        "symptoms": [
            {"symptom": "joint pain", "severity": 6},
            {"symptom": "morning stiffness", "severity": 5},
            {"symptom": "fatigue", "severity": 7},
        ],
        "environmental_factors": [
            {"factor_type": "sleep", "description": "Poor sleep, woke 3 times"},
            {"factor_type": "diet", "description": "High-carb meals, skipped lunch"},
        ],
        "stress_level": 6,
        "diet_notes": "Skipped breakfast, pizza for dinner",
        "sleep_quality": 3,
        "notes": "Knees and wrists aching more than usual. Hard to open jars this morning.",
        "analysis": "Symptom cluster consistent with inflammatory flare precursor. Morning stiffness duration >45 min warrants close monitoring over the next 7 days.",
        "pattern_observations": [
            "Morning stiffness correlating with poor sleep nights (sleep 3/10 → stiffness 5/10)",
            "Joint pain intensity tracking with dietary glycemic load",
        ],
        "ai_analysis": {
            "analysis": (
                "Stack 2 | Band 3 deviation detected. Sleep disruption (3/10) is amplifying "
                "inflammatory terrain — morning stiffness duration indicates M3 baseline breach. "
                "Dietary pattern (high-glycemic, meal skipping) consistent with elevated cortisol "
                "load and tissue utilization impairment. Recommend 7-day daily symptom logging and "
                "sleep hygiene prioritization before next assessment."
            ),
            "band": "3 (Decompensation)",
            "flare_risk": "Moderate — 48%",
            "recommendation": "Sleep hygiene first. Log daily for 7 days.",
        },
        "created_at": "2025-12-01T08:30:00Z",
    },
    {
        "id": "jrn-002",
        "user_id": "user-norman-dev",
        "date": "2025-12-05",
        "symptoms": [
            {"symptom": "fatigue", "severity": 8},
            {"symptom": "brain fog", "severity": 6},
        ],
        "environmental_factors": [
            {"factor_type": "stress", "description": "High-pressure work deadline"},
        ],
        "stress_level": 8,
        "diet_notes": "Mostly normal, added anti-inflammatory smoothie",
        "sleep_quality": 4,
        "notes": "Exhausted by midday. Hard to concentrate on anything. Skipped my afternoon walk.",
        "analysis": "Fatigue spike likely stress-potentiated. Fatigue–cognitive pairing consistent with M5 PSI elevation. Sleep partially recovered but insufficient.",
        "pattern_observations": [
            "Fatigue spikes correlating with high-stress periods (stress 8/10 → fatigue 8/10)",
            "Brain fog emerging as secondary symptom when fatigue exceeds 7/10",
        ],
        "ai_analysis": {
            "analysis": (
                "Stack 2 | Band 3→4 trajectory. Fatigue–cognitive pairing at this severity "
                "(fatigue 8/10, brain fog 6/10) indicates M5 neurological stress potentiation. "
                "Current adaptive capacity is insufficient — stress load (8/10) is exceeding the "
                "homeostatic buffer established in prior entries. Flare probability elevated to ~68% "
                "if this pattern persists beyond 48 hours. Immediate priority: cognitive load "
                "reduction and sleep extension."
            ),
            "band": "3→4 (Escalating)",
            "flare_risk": "Moderate–High — 68%",
            "recommendation": "Reduce cognitive load. Extend sleep. Reassess in 48h.",
        },
        "created_at": "2025-12-05T19:00:00Z",
    },
    {
        "id": "jrn-003",
        "user_id": "user-norman-dev",
        "date": "2025-12-10",
        "symptoms": [
            {"symptom": "joint pain", "severity": 3},
            {"symptom": "fatigue", "severity": 4},
        ],
        "environmental_factors": [
            {"factor_type": "exercise", "description": "30-min walk, light yoga"},
        ],
        "stress_level": 3,
        "diet_notes": "Salad, grilled fish, turmeric tea",
        "sleep_quality": 7,
        "notes": "Better day overall. Movement helped. Joints still stiff in the morning but manageable by 10am.",
        "analysis": "Measurable improvement correlates with sleep quality recovery and physical activity. Symptom severity across all axes reduced vs. prior two entries.",
        "pattern_observations": [
            "Physical activity (30-min walk + yoga) associated with same-day symptom reduction",
            "Sleep quality improvement (4→7) directly correlating with fatigue and pain scores",
            "Diet quality positively correlated with cognitive clarity and energy level",
        ],
        "ai_analysis": {
            "analysis": (
                "Stack 2 | Band 2 — active stabilization phase. Sleep quality improvement (7/10) "
                "is correlating with measurable terrain normalization across all tracked axes. "
                "Exercise and anti-inflammatory diet are supporting M3 recovery pattern. "
                "This entry represents a positive deviation from the Band 3 trajectory logged "
                "12/01–12/05. Continue current pattern; 14-day positive streak required to "
                "confirm stable baseline reclassification."
            ),
            "band": "2 (Stabilization)",
            "flare_risk": "Low–Moderate — 22%",
            "recommendation": "Maintain current activity and diet pattern. Reassess in 14 days.",
        },
        "created_at": "2025-12-10T20:15:00Z",
    },
]


def seed_entries() -> list[dict]:
    """Return a deep copy of the seed entries (so the in-memory store can mutate)."""
    return copy.deepcopy(_SEED)


def make_entry(body: dict, entry_id: str) -> dict:
    """Build a new journal entry from a POST body."""
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "id": entry_id,
        "user_id": "user-norman-dev",
        "date": body.get("date", now[:10]),
        "symptoms": body.get("symptoms", []),
        "environmental_factors": body.get("environmental_factors", []),
        "stress_level": body.get("stress_level"),
        "diet_notes": body.get("diet_notes"),
        "sleep_quality": body.get("sleep_quality"),
        "notes": body.get("notes"),
        "analysis": (
            "Symptom pattern logged. Insufficient longitudinal data for deviation "
            "classification — baseline requires a minimum of 5 entries."
        ),
        "pattern_observations": [
            "New entry — continue logging daily to establish deviation baseline.",
        ],
        "ai_analysis": {
            "analysis": (
                "Stack 2 | Band undetermined — new entry, insufficient history for classification. "
                "Continue daily logging to establish M3 baseline. "
                "Next structured assessment available after 5 entries."
            ),
            "band": "Undetermined",
            "flare_risk": "Insufficient data",
            "recommendation": "Log daily for 5 days to establish baseline.",
        },
        "created_at": now,
    }


MOCK_TIMELINE_BUNDLE = {
    "report_id": "default",
    "patient_id": "user-norman-dev",
    "generated_at": "2025-12-10T00:00:00Z",
    "symptom_trend": [
        {"date": "2025-12-01", "avg_severity": 6.0, "dominant": "joint pain"},
        {"date": "2025-12-05", "avg_severity": 7.0, "dominant": "fatigue"},
        {"date": "2025-12-10", "avg_severity": 3.5, "dominant": "joint pain"},
    ],
    "top_symptoms": ["fatigue", "joint pain", "morning stiffness", "brain fog"],
    "stress_trend": [6, 8, 3],
    "sleep_trend": [3, 4, 7],
}
