# server/eoh/module_index.py
"""
EoH Module Index

Defines the MODULE_INDEX dictionary containing all EoH modules used for
flare prediction, interpretation, and care planning. Based on Andras's
"EoH Reasoning Map: The Module Index, Dictionary, and Routing Framework".

Layers:
- terrain: Patient terrain & baseline (M1-M3)
- signal_tagging: Signal, narrative, and tagging (M4, M5, M7A, M9, M12)
- flare_detection: Flare detection, forecasting, escalation (M6, M10, M11, M13, M14, M20)
- care_planning: Care planning, adaptation, tapering (M7B, M15, M21-M24)
- governance: Governance & learning (M19, M25, M41, M48)
"""

from typing import Dict, Any, List

# Type alias for doc handles
DocHandle = Dict[str, str]

MODULE_INDEX: Dict[str, Dict[str, Any]] = {
    # =========================================================================
    # LAYER 1: TERRAIN & STATE (where the patient "is")
    # =========================================================================
    "M1": {
        "name": "Patient Terrain Model",
        "layer": "terrain",
        "llm_use_when": "You need 'where is this patient on the terrain right now / over time?' - Stack Level, Stability Band, drift, Zone-5 persistence.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m1_patient_terrain"},
            {"kind": "pg_table", "name": "eoh_patient_stack_history"},
        ],
    },
    "M2": {
        "name": "CBM & Baseline Drift Engine",
        "layer": "terrain",
        "llm_use_when": "Deciding whether a change is 'worse than their best baseline' and if they're in CBM (Chronic Baseline Mode) or not.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m2_baseline_drift"},
            {"kind": "pg_table", "name": "eoh_cbm_state"},
        ],
    },
    "M3A": {
        "name": "Stability Score to Band Engine",
        "layer": "terrain",
        "llm_use_when": "You need to reason how daily signals translate into Band changes (stability_score -> Band 0-5).",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m3a_stability_band"},
            {"kind": "pg_table", "name": "eoh_daily_stability_scores"},
        ],
    },
    "M3B": {
        "name": "Stack Scoring Engine",
        "layer": "terrain",
        "llm_use_when": "Computing Stack Level from chronic burden and multi-condition complexity.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m3b_stack_scoring"},
        ],
    },

    # =========================================================================
    # LAYER 2: SIGNAL, NARRATIVE, AND TAGGING (what's happening today)
    # =========================================================================
    "M4": {
        "name": "Reflex Suppression Audit Trail",
        "layer": "signal_tagging",
        "llm_use_when": "Discriminating 'real flare vs transient vs psychosomatic vs lab error' - classifies suppression reasons (Overshoot, Healing Pain, Symbolic Flare, Lab Error).",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m4_suppression_audit"},
            {"kind": "pg_table", "name": "eoh_suppression_events"},
        ],
    },
    "M5": {
        "name": "Symbolic Interpreter / PSI",
        "layer": "signal_tagging",
        "llm_use_when": "You need to factor narrative distortion into flare risk or decide whether to lean on / discount patient-reported severity. Computes Psychosomatic Index (PSI 0-3).",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m5_psi_scores"},
            {"kind": "pg_table", "name": "eoh_symbolic_tags"},
        ],
    },
    "M7A": {
        "name": "Data Quality & Sanity Checks",
        "layer": "signal_tagging",
        "llm_use_when": "Evaluating whether to trust specific data points or treat them as low-confidence in reasoning. Handles missingness, contradictions, outliers.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m7a_data_quality"},
            {"kind": "pg_table", "name": "eoh_qa_flags"},
        ],
    },
    "M9": {
        "name": "Suppression Core (Policy)",
        "layer": "signal_tagging",
        "llm_use_when": "Interpreting whether a held flare should still influence risk, and how long a 'pause' is valid. Priority ladder + TTLs + resolution taxonomy.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m9_suppression_policy"},
            {"kind": "pg_table", "name": "eoh_pause_flags"},
        ],
    },
    "M12": {
        "name": "Symptom Narrative Engine",
        "layer": "signal_tagging",
        "llm_use_when": "You need a compressed but faithful view of what's been happening over days/weeks. Summarizes free text into digest + structured findings.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m12_narrative_digest"},
            {"kind": "ann_index", "name": "eoh_narrative_embeddings"},
            {"kind": "doc_corpus", "name": "eoh_journal_corpus"},
        ],
    },

    # =========================================================================
    # LAYER 3: FLARE DETECTION, FORECASTING, ESCALATION
    # =========================================================================
    "M6": {
        "name": "Escalation Router / Central Switchboard",
        "layer": "flare_detection",
        "llm_use_when": "Choosing the severity tier and who should be notified based on state transitions. Converts state into tiered alerts (0-3).",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m6_escalation_tiers"},
            {"kind": "pg_table", "name": "eoh_alert_history"},
        ],
    },
    "M10": {
        "name": "Crisis Engine / Critical Escalation",
        "layer": "flare_detection",
        "llm_use_when": "Any question touches 'is this an emergency / crisis protocol?' - handles Tier-4 / crisis (Zone 5 persistence, collapse language, suicidality, sepsis cues).",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m10_crisis_flags"},
            {"kind": "pg_table", "name": "eoh_critical_escalations"},
        ],
    },
    "M11": {
        "name": "Patient Guidance & Containment",
        "layer": "flare_detection",
        "llm_use_when": "Choosing between 'reassure + support' vs 'alarm + escalate' in patient-facing text. Converts suppression events into reflective prompts.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m11_patient_guidance"},
            {"kind": "doc_corpus", "name": "eoh_patient_communications"},
        ],
    },
    "M13": {
        "name": "Trend & Prognostic Engine",
        "layer": "flare_detection",
        "llm_use_when": "Answering 'flare risk over next X days/months' or 'is trajectory improving/worsening and why?'. Computes flare probabilities and risk trajectories.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m13_forecasts"},
            {"kind": "pg_table", "name": "eoh_flare_probabilities"},
            {"kind": "pg_table", "name": "eoh_risk_trajectories"},
        ],
    },
    "M14": {
        "name": "Action & Escalation Engine",
        "layer": "flare_detection",
        "llm_use_when": "Deciding concrete next steps for both patient and clinician given a forecast. Harmonizes risk into tiers T0-T4.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m14_tiers"},
            {"kind": "pg_table", "name": "eoh_patient_tasks"},
            {"kind": "pg_table", "name": "eoh_clinician_flags"},
        ],
    },
    "M20": {
        "name": "Early-Warning Engine",
        "layer": "flare_detection",
        "llm_use_when": "Reasoning about earlier subtler shifts ('pre-flare signals') rather than late obvious flares. Streaming anomaly detection.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m20_early_warnings"},
            {"kind": "pg_table", "name": "eoh_trend_observations"},
        ],
    },

    # =========================================================================
    # LAYER 4: CARE PLANNING, ADAPTATION, TAPERING
    # =========================================================================
    "M7B": {
        "name": "Care Plan Orchestrator",
        "layer": "care_planning",
        "llm_use_when": "Translating risk tiers into concrete workflow steps. Converts escalations into Tasks, ServiceRequests, CarePlan adjustments.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m7b_care_tasks"},
            {"kind": "pg_table", "name": "eoh_service_requests"},
        ],
    },
    "M15": {
        "name": "Care Plan Composer",
        "layer": "care_planning",
        "llm_use_when": "Answering 'how should we adjust their plan over the next weeks/months?' - builds multi-condition, capacity-aware CarePlan timeline.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m15_care_plans"},
            {"kind": "pg_table", "name": "eoh_care_plan_timeline"},
        ],
    },
    "M21": {
        "name": "Vault",
        "layer": "care_planning",
        "llm_use_when": "You need to explain why past flare predictions/actions were made. Append-only decision vault with full provenance.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m21_vault"},
            {"kind": "pg_table", "name": "eoh_decision_packets"},
        ],
    },
    "M22": {
        "name": "Intervention Modulator",
        "layer": "care_planning",
        "llm_use_when": "Explaining or proposing intensity adjustments (tighten vs loosen monitoring/therapy). Modulates CarePlan based on forecasts.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m22_interventions"},
            {"kind": "pg_table", "name": "eoh_intensity_adjustments"},
        ],
    },
    "M23": {
        "name": "Adaptive Tapering & Maintenance",
        "layer": "care_planning",
        "llm_use_when": "Questions like 'Is it safe to taper?' or 'how should we taper given this trajectory?'. Governs safe taper from active treatment to CBM/OHB.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m23_tapering"},
            {"kind": "pg_table", "name": "eoh_taper_schedules"},
        ],
    },
    "M24": {
        "name": "Interface Hub",
        "layer": "care_planning",
        "llm_use_when": "Designing or reasoning about how this appears to users, not core clinical logic. UI hub for Bands, flare risk, trajectories, tasks.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m24_interface_state"},
        ],
    },

    # =========================================================================
    # LAYER 5: GOVERNANCE & LEARNING
    # =========================================================================
    "M19": {
        "name": "QA & Continuous Learning Loop",
        "layer": "governance",
        "llm_use_when": "Monitoring AUROC, Brier, calibration, suppression errors. Routes retraining requests to M48.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m19_calibration_metrics"},
            {"kind": "pg_table", "name": "eoh_model_performance"},
        ],
    },
    "M25": {
        "name": "Narrative Synthesizer (Cross-Audience)",
        "layer": "governance",
        "llm_use_when": "Harmonizing patient, clinician, and governance narratives. Ensures no contradictory messaging.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m25_narratives"},
            {"kind": "doc_corpus", "name": "eoh_audience_templates"},
        ],
    },
    "M41": {
        "name": "Suppression Audit",
        "layer": "governance",
        "llm_use_when": "Reviewing suppression audit trail for true/false positive holds. Meta-analysis of suppression decisions.",
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m41_suppression_audit"},
            {"kind": "pg_table", "name": "eoh_suppression_outcomes"},
        ],
    },
    "M48": {
        "id": "M48",
        "name": "Global calibration & suppression governance",
        "layer": "governance",
        "llm_use_when": (
            "Type E questions about overall EoH calibration, missed flares vs "
            "false positives, and suppression policies across the population."
        ),
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m48_global_calibration"},
            {"kind": "pg_view", "name": "eoh_m48_suppression_audit"},
        ],
    },
    "M48B": {
        "id": "M48B",
        "name": "Condition-level calibration & flare suppression audit (Gold Module 49B)",
        "layer": "governance",
        "llm_use_when": (
            "Type E questions about calibration or suppression for a specific "
            "disease/phenotype (e.g. RA, SLE, IBD) or for a board-facing QA "
            "about missed flares / over-suppression in that condition. "
            "Backed by the EoH Gold 2025 Module 49B policy text."
        ),
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m48b_condition_calibration"},
            {"kind": "pg_view", "name": "eoh_m48b_condition_suppression_audit"},
            # Sneak-preview governance policy text from rag_corpus:
            {"kind": "ethos_module_doc", "name": "eoh_gold_2025:mod_49b"},
        ],
    },
    "M48C": {
        "id": "M48C",
        "name": "Diagnostic landscape stability & drift (Gold Module 49C)",
        "layer": "governance",
        "llm_use_when": (
            "Type C or E questions where the focus is on diagnostic landscape "
            "consistency over time (e.g. shifts in RA-like vs SLE-like vs PsA-like "
            "weights) and whether EoH is drifting or unstable. "
            "Backed by the EoH Gold 2025 Module 49C policy text."
        ),
        "doc_handles": [
            {"kind": "pg_view", "name": "eoh_m48c_diagnostic_landscape_qc"},
            {"kind": "pg_view", "name": "eoh_m48c_drift_monitor"},
            # Sneak-preview governance policy text from rag_corpus:
            {"kind": "ethos_module_doc", "name": "eoh_gold_2025:mod_49c"},
        ],
    },
    "M50": {
        "id": "M50",
        "name": "DxLandscapeFromEoH – Diagnostic Landscape Engine",
        "layer": "governance",
        "llm_use_when": (
            "You need to derive or reason about a structured diagnostic landscape "
            "for an Episode of Health: clustered candidate diagnoses with scores, "
            "evidence back to timeline facts, and suggested next diagnostic moves. "
            "Use this when the question asks for a differential / diagnostic landscape "
            "in an EoH-aware way (often type C or E questions, sometimes A/D when "
            "the focus is on how diagnosis and flare interact)."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_gold_2025:mod_50"},
        ],
    },

    # =========================================================================
    # V6 MODULES (M55–M68)
    # =========================================================================
    "M55": {
        "id": "M55",
        "name": "Execution Modes (QUERY_ONLY / DEBUG_LOOP)",
        "layer": "governance",
        "llm_use_when": (
            "Determining whether the system is in QUERY_ONLY (read-only posture, "
            "no computation/scheduling/mutation) or DEBUG_LOOP (human-directed "
            "inspection with no autonomous progression). Enforces execution-mode "
            "MUST-NOT guarantees."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_canon_v6:m55"},
        ],
    },
    "M56": {
        "id": "M56",
        "name": "Patient Vision Unification",
        "layer": "governance",
        "llm_use_when": (
            "Reasoning about how to unify the patient view across modules — "
            "ensuring terrain, narrative, suppression, and plan state present a "
            "single coherent patient picture. Analysis-only / non-executable."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_canon_v6:m56"},
        ],
    },
    "M57": {
        "id": "M57",
        "name": "Clinical Invariants System",
        "layer": "governance",
        "llm_use_when": (
            "You need to reference, verify, or audit the hard non-negotiable "
            "constraints that shape reasoning flow (ordering, gating, eligibility) "
            "across EoH modules. Invariants constrain flow, never answers or scores."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_canon_v6:m57"},
        ],
    },
    "M58": {
        "id": "M58",
        "name": "HITL Interruption Controller (HIC)",
        "layer": "governance",
        "llm_use_when": (
            "Handling mid-stream human interruption of EoH processing — suppression, "
            "pause, and audit-controlled behaviour for clinician or governance overrides."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_canon_v6:m58"},
        ],
    },
    "M59": {
        "id": "M59",
        "name": "Plan Co-Creation Contract (PCC)",
        "layer": "care_planning",
        "llm_use_when": (
            "Defining how human input shapes care plans through confirmation-gated, "
            "draft-only artifacts. Plans remain non-authoritative until confirmed "
            "through V5.2 execution gates."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_canon_v6:m59"},
        ],
    },
    "M60": {
        "id": "M60",
        "name": "HITL Audit & Replay Frame (HARF)",
        "layer": "governance",
        "llm_use_when": (
            "Reconstructing or replaying HITL interactions (interruptions, edits, "
            "approvals) in an audit-grade, read-only fashion. Replay is derived, "
            "not re-executed."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_canon_v6:m60"},
        ],
    },
    "M61": {
        "id": "M61",
        "name": "Pattern Inspiration (Non-binding)",
        "layer": "governance",
        "llm_use_when": (
            "Reference-only pattern recognition inspired by prior clinical usage. "
            "Non-authoritative — names patterns but does not own or execute "
            "escalation, routing, or tier logic."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_canon_v6:m61"},
        ],
    },
    "M63": {
        "id": "M63",
        "name": "Derivation Transparency Contract",
        "layer": "governance",
        "llm_use_when": (
            "Ensuring every output carries a DerivationChain (inputs, "
            "transformations, assumptions, uncertainty markers). No output may "
            "claim transparency without a traceable derivation record."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_canon_v6:m63"},
        ],
    },
    "M64": {
        "id": "M64",
        "name": "Functional Utilization Discordance Detector (FUDD)",
        "layer": "signal_tagging",
        "llm_use_when": (
            "Detecting cases where serum/plasma levels appear normal but tissue-level "
            "utilization is impaired (or inverse: abnormal serum but adequate tissue "
            "status). Two-layer detection: curated FUD signatures + general "
            "discordance heuristic. Generates role-differentiated output payloads."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_canon_v6:m64"},
        ],
    },
    "M65": {
        "id": "M65",
        "name": "Dark Passenger — Voice Identity Drift Detection",
        "layer": "signal_tagging",
        "llm_use_when": (
            "Detecting longitudinal voice identity drift in patient journal text — "
            "persona shifts, addiction-driven concealment, metabolic mimics. Scores "
            "engagement severity on a six-stage ladder and emits coaching posture "
            "advisories for patient-facing modules."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_canon_v6:m65"},
        ],
    },
    "M66": {
        "id": "M66",
        "name": "Exploratory Wellness Actions (EWA)",
        "layer": "care_planning",
        "llm_use_when": (
            "Surfacing terrain-stabilizing, low-risk, reversible lifestyle/diet/"
            "nervous-system actions that reduce load and increase reserve without "
            "asserting causality or claiming treatment. Non-diagnostic, "
            "non-prescriptive, non-escalatory."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_canon_v6:m66"},
        ],
    },
    "M67": {
        "id": "M67",
        "name": "Adversarial Reasoning Governance Layer (ARGL)",
        "layer": "governance",
        "llm_use_when": (
            "Enforcing reasoning quality: evidence provenance (typed, traceable tags), "
            "contextual validity rebinding, and mandatory falsification before "
            "publishing conclusions. Meta-governance above reasoning modules, below "
            "user-facing response layer."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_canon_v6:m67"},
        ],
    },
    "M68": {
        "id": "M68",
        "name": "Inflammatory Capacity Model (ICM)",
        "layer": "flare_detection",
        "llm_use_when": (
            "Estimating real-time allostatic headroom (inflammatory capacity) via "
            "three-valve dynamics (inflow/outflow/capacity), turbulence regime, and "
            "physiological infrastructure variables (lymphatic tone, vagal tone, "
            "system viscosity). Proactive flare prevention through headroom-based "
            "risk assessment."
        ),
        "doc_handles": [
            {"kind": "ethos_module_doc", "name": "eoh_canon_v6:m68"},
        ],
    },
}


# Question type definitions with canonical module paths
QUESTION_TYPES: Dict[str, Dict[str, Any]] = {
    "A": {
        "description": "What is this patient's flare risk over the next X days/weeks?",
        "goal": "Compute flare probability, interpret trajectory, give drivers + safety context.",
        "canonical_modules": [
            "M1", "M2", "M3A", "M7A", "M4", "M5", "M9", "M12", "M13", "M14",
            "M21", "M24", "M25", "M41", "M64", "M68",
        ],
    },
    "B": {
        "description": "Is this a real flare or symbolic / overshoot / lab error?",
        "goal": "Classification of the instability event.",
        "canonical_modules": [
            "M1", "M2", "M3A", "M7A", "M12", "M4", "M5", "M9", "M6", "M11",
            "M7B", "M10", "M14", "M64", "M65", "M68",
        ],
    },
    "C": {
        "description": "Why did the system predict / escalate a flare? (Explainability)",
        "goal": "Reconstruct the decision chain.",
        "canonical_modules": [
            "M21", "M13", "M12", "M4", "M5", "M14", "M9", "M41", "M7A", "M19",
            "M25", "M48", "M48B", "M48C", "M50", "M63", "M67",
        ],
    },
    "D": {
        "description": "Given this state, how should we adjust the plan? (non-emergency)",
        "goal": "Adjust tasks/plan intensity, not trigger crisis.",
        "canonical_modules": [
            "M1", "M2", "M3A", "M7A", "M12", "M13", "M14", "M15", "M7B",
            "M22", "M23", "M24", "M25", "M59", "M66",
        ],
    },
    "E": {
        "description": "Is the model still calibrated / are we over-suppressing flares? (meta)",
        "goal": "Meta on performance, not per-patient.",
        "canonical_modules": ["M19", "M41", "M48", "M48B", "M48C", "M50", "M57", "M67"],
    },
}


def get_module_ids() -> List[str]:
    """Return all valid module IDs."""
    return list(MODULE_INDEX.keys())


def get_doc_handles() -> Dict[str, List[DocHandle]]:
    """Return a mapping of module ID to its doc handles."""
    return {mid: mod["doc_handles"] for mid, mod in MODULE_INDEX.items()}


def get_all_doc_handle_names() -> set:
    """Return a set of all valid doc handle names across all modules."""
    names = set()
    for mod in MODULE_INDEX.values():
        for handle in mod["doc_handles"]:
            names.add(handle["name"])
    return names


def get_modules_for_question_type(question_type: str) -> List[str]:
    """Return the canonical module list for a given question type."""
    if question_type in QUESTION_TYPES:
        return QUESTION_TYPES[question_type]["canonical_modules"]
    return []


def get_module_index_for_llm() -> List[Dict[str, Any]]:
    """
    Return a simplified MODULE_INDEX suitable for injection into LLM prompts.
    Includes only the fields the LLM needs: id, name, layer, llm_use_when, doc_handles.
    """
    return [
        {
            "id": mid,
            "name": mod["name"],
            "layer": mod["layer"],
            "llm_use_when": mod["llm_use_when"],
            "doc_handles": mod["doc_handles"],
        }
        for mid, mod in MODULE_INDEX.items()
    ]
