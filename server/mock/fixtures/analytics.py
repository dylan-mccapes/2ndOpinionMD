"""Static analytics fixtures for timeline analytics endpoints."""
from __future__ import annotations

ANALYTICS_SUMMARY = {
    "patient_id": "norman-dev-timeline",
    "total_events": 106,
    "span_days": 14236,
    "windows": [
        {
            "window_start": "2025-11-01T00:00:00Z",
            "window_end": "2025-11-08T00:00:00Z",
            "stability_score": 0.52,
            "event_count": 9,
        },
        {
            "window_start": "2025-11-08T00:00:00Z",
            "window_end": "2025-11-15T00:00:00Z",
            "stability_score": 0.48,
            "event_count": 11,
        },
        {
            "window_start": "2025-11-15T00:00:00Z",
            "window_end": "2025-11-22T00:00:00Z",
            "stability_score": 0.41,
            "event_count": 14,
        },
        {
            "window_start": "2025-11-22T00:00:00Z",
            "window_end": "2025-11-29T00:00:00Z",
            "stability_score": 0.38,
            "event_count": 18,
        },
        {
            "window_start": "2025-11-29T00:00:00Z",
            "window_end": "2025-12-05T00:00:00Z",
            "stability_score": 0.35,
            "event_count": 21,
        },
    ],
    "phase_shifts": [
        {
            "timestamp": "2019-06-15T00:00:00Z",
            "from_phase": "Stable",
            "to_phase": "Flare",
        },
        {
            "timestamp": "2022-11-10T00:00:00Z",
            "from_phase": "Remission",
            "to_phase": "Transitioning",
        },
        {
            "timestamp": "2025-10-01T00:00:00Z",
            "from_phase": "Transitioning",
            "to_phase": "Decompensation",
        },
    ],
    "flare_episodes": [
        {"start": "2019-06-01", "end": "2019-09-30", "confidence": 0.88},
        {"start": "2022-11-01", "end": "2023-03-31", "confidence": 0.74},
        {"start": "2025-10-01", "end": "2025-12-10", "confidence": 0.81},
    ],
    "noise_floor": 0.12,
    "charts": {
        "stability_band": "",
        "terrain_trajectory": "",
    },
    "disclaimer": "This analysis is generated from structured timeline data and is intended for informational purposes only. It does not constitute medical advice.",
}

ANALYTICS_PRECEDENCE = {
    "patient_id": "norman-dev-timeline",
    "edges": [
        {
            "source": "pdf_p0010_e0000",
            "target": "pdf_p3396_e0000",
            "edge_type": "temporal",
            "weight": 0.91,
            "label": "A1c 6.2% → follow-up lab cluster",
        },
        {
            "source": "pdf_p0010_e0000",
            "target": "pdf_p3313_e0000",
            "edge_type": "treatment",
            "weight": 0.84,
            "label": "A1c elevation → metformin initiation",
        },
        {
            "source": "pdf_p3396_e0000",
            "target": "pdf_p3398_e0000",
            "edge_type": "temporal",
            "weight": 0.79,
            "label": "Lab cluster → endocrinology visit",
        },
        {
            "source": "pdf_p3186_e0000",
            "target": "pdf_p3004_e0000",
            "edge_type": "diagnostic",
            "weight": 0.73,
            "label": "ANA positive → rheumatology referral",
        },
        {
            "source": "pdf_p2970_e0000",
            "target": "pdf_p2993_e0000",
            "edge_type": "treatment",
            "weight": 0.68,
            "label": "Prednisone course → symptom resolution",
        },
    ],
    "total_edges": 5,
}

ANALYTICS_EXPORT = {
    "patient_id": "norman-dev-timeline",
    "export_format": "json",
    "summary": ANALYTICS_SUMMARY,
    "precedence": ANALYTICS_PRECEDENCE,
}
