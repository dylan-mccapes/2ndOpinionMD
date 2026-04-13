"""Static EoH router plan fixture matching EohdPage.tsx schema."""
from __future__ import annotations

ROUTER_PLAN = {
    "question_type": "A",
    "question_type_explanation": (
        "Flare risk assessment — requires M13 trajectory computation, "
        "M68 ICM headroom evaluation, and M14 escalation staging."
    ),
    "module_plan": [
        {
            "step": 1,
            "goal": "Assess current stability band and baseline deviation",
            "modules": ["M1", "M2", "M3"],
            "why": (
                "Establish the patient's coordinate in Stack × Band × Time space "
                "before computing flare probability."
            ),
        },
        {
            "step": 2,
            "goal": "Compute flare probability and risk trajectory",
            "modules": ["M13", "M20", "M68"],
            "why": (
                "M13 provides the longitudinal flare probability estimate. "
                "M20 scans for early-warning signal anomalies. "
                "M68 quantifies allostatic headroom via three-valve ICM dynamics."
            ),
        },
        {
            "step": 3,
            "goal": "Stage escalation recommendation and generate clinician guidance",
            "modules": ["M6", "M14", "M63"],
            "why": (
                "M6 converts state transitions to tiered alerts. "
                "M14 generates concrete next steps per risk tier. "
                "M63 ensures full derivation transparency on all outputs."
            ),
        },
    ],
    "doc_retrieval_plan": [
        {
            "module": "M13",
            "handles": [
                {"kind": "lab", "name": "CRP, ESR, ANA, A1c time series"},
                {"kind": "visit", "name": "Rheumatology and endocrinology encounters"},
            ],
            "purpose": "Build longitudinal trajectory for flare probability estimation.",
        },
        {
            "module": "M68",
            "handles": [
                {"kind": "medication", "name": "Current immunosuppressant regimen"},
                {"kind": "lab", "name": "Recent inflammatory markers"},
            ],
            "purpose": "Estimate inflow/outflow valve balance and ICmax headroom.",
        },
    ],
}
