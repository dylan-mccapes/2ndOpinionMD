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
        "notes": "Knees and wrists aching more than usual. Hard to open jars.",
        "analysis": "Symptom cluster consistent with inflammatory flare precursor. Morning stiffness >1 hr warrants monitoring.",
        "pattern_observations": [
            "Morning stiffness correlating with poor sleep nights",
            "Joint pain intensity tracking with dietary choices",
        ],
        "ai_analysis": {
            "eoh_band_estimate": 3,
            "flare_risk": "moderate",
            "recommended_action": "Log symptoms daily for 7 days",
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
            {"factor_type": "stress", "description": "High work pressure deadline"},
        ],
        "stress_level": 8,
        "diet_notes": "Mostly normal, added anti-inflammatory smoothie",
        "sleep_quality": 4,
        "notes": "Exhausted by midday. Hard to concentrate. Skipped afternoon walk.",
        "analysis": "Fatigue spike likely stress-potentiated. Brain fog pattern consistent with M5 PSI elevation.",
        "pattern_observations": [
            "Fatigue spikes correlate with high-stress periods",
        ],
        "ai_analysis": {
            "eoh_band_estimate": 3,
            "flare_risk": "moderate-high",
            "recommended_action": "Prioritize sleep hygiene and stress reduction",
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
        "diet_notes": "Salad, fish, turmeric tea",
        "sleep_quality": 7,
        "notes": "Better day. Movement helped. Joints still stiff but manageable.",
        "analysis": "Improvement correlates with sleep quality improvement and physical activity.",
        "pattern_observations": [
            "Physical activity associated with symptom improvement",
            "Diet quality positively correlated with energy",
        ],
        "ai_analysis": {
            "eoh_band_estimate": 2,
            "flare_risk": "low-moderate",
            "recommended_action": "Maintain current activity and diet pattern",
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
        "analysis": "Mock AI analysis: symptom pattern logged successfully. Monitoring recommended.",
        "pattern_observations": ["New entry added — insufficient data for pattern detection yet."],
        "ai_analysis": {"eoh_band_estimate": 2, "flare_risk": "unknown", "recommended_action": "Continue logging"},
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
