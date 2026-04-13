"""Static flare report fixture matching EohdPage.tsx schema."""
from __future__ import annotations

FLARE_REPORT = {
    "patient_id": "norman-dev-timeline",
    "window_days": 90,
    "flare_forecast": (
        "Moderate-high flare risk over the next 30 days. "
        "Inflammatory trajectory is upward based on the past 90-day event window. "
        "Allostatic headroom estimated at 22% of ICmax — caution advised."
    ),
    "probabilistic_differential": {
        "Systemic Lupus Erythematosus (SLE)": 0.61,
        "Rheumatoid Arthritis": 0.44,
        "Sjögren's Syndrome": 0.29,
        "Undifferentiated Connective Tissue Disease": 0.18,
        "Fibromyalgia (secondary)": 0.12,
    },
    "precursor_signals": [
        {
            "signal": "Morning stiffness >60 min",
            "weight": 0.78,
            "description": (
                "Documented across multiple visit notes in 2023–2025. "
                "Duration correlates with inflammatory band elevation."
            ),
        },
        {
            "signal": "A1c borderline elevation (6.2%)",
            "weight": 0.52,
            "description": (
                "Metabolic dysregulation potentiates inflammatory inflow "
                "via M68 ICM. Not diagnostic for diabetes — monitoring required."
            ),
        },
        {
            "signal": "Sleep quality deterioration",
            "weight": 0.47,
            "description": (
                "Journal entries show sleep quality scores ≤4 on high-symptom days. "
                "Sleep disruption reduces outflow valve clearance capacity."
            ),
        },
    ],
    "risk_drivers": [
        {"driver": "Chronic inflammatory load", "weight": 0.81},
        {"driver": "Metabolic burden (A1c)", "weight": 0.53},
        {"driver": "Sleep deprivation", "weight": 0.47},
        {"driver": "Psychosocial stress (M5 PSI)", "weight": 0.39},
    ],
    "timeline_summary": (
        "Norman's 38-year medical record shows a pattern of escalating autoimmune activity "
        "punctuated by periods of relative remission. The 2023 lab cluster (A1c 6.2%, CRP elevated) "
        "coincides with increased visit frequency and medication adjustments. "
        "Current trajectory suggests the patient is in a pre-flare accumulation phase."
    ),
    "contradictions": [
        "Some lab values within normal range despite clinical symptom severity — possible FUDD pattern (M64).",
        "Hydroxychloroquine compliance unclear from record — efficacy assessment limited.",
    ],
    "guidance_for_clinician": [
        "Re-check CRP and ESR within 2 weeks given upward trajectory.",
        "Review M9 suppression channel — confirm no active pauseFlag masking signal.",
        "Consider M22 plan modulation: tighten monitoring frequency to bi-weekly.",
        "EWA trial (M66): anti-inflammatory diet protocol, vagal regulation exercises.",
    ],
    "safety_warnings": [
        "If joint swelling becomes asymmetric or fever >38°C develops, escalate immediately — T2 alert threshold.",
    ],
}
