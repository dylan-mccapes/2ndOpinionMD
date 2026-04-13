"""Static analytics fixtures for timeline analytics endpoints."""
from __future__ import annotations

ANALYTICS_SUMMARY = {
    "patient_id": "norman-dev-timeline",
    "window_days": 7,
    "event_counts": {
        "lab": 42,
        "medication": 31,
        "visit": 18,
        "diagnosis": 9,
        "procedure": 6,
        "page": 0,
    },
    "total_events": 106,
    "recent_events": [
        {
            "event_type": "lab",
            "count": 8,
            "latest_ts": "2025-12-05T00:00:00Z",
        },
        {
            "event_type": "visit",
            "count": 2,
            "latest_ts": "2025-11-28T00:00:00Z",
        },
    ],
    "top_event_types": ["lab", "medication", "visit", "diagnosis"],
    "date_range": {
        "earliest": "1987-03-15T00:00:00Z",
        "latest": "2025-12-05T00:00:00Z",
    },
    "flare_windows": [
        {"start": "2019-06-01", "end": "2019-09-30", "intensity": "high"},
        {"start": "2022-11-01", "end": "2023-03-31", "intensity": "moderate"},
        {"start": "2025-10-01", "end": "2025-12-10", "intensity": "moderate"},
    ],
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
