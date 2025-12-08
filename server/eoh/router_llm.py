# server/eoh/router_llm.py
"""
EoH LLM Router

Provides an LLM-based router that uses the EoH Reasoning Map (module index + routing recipes)
to select which EoH modules to use and where to look in the database/doc corpus.

This router is a PLANNER ONLY:
- It does NOT fetch data or answer clinical questions directly.
- It outputs a structured "plan" object that downstream code can execute.
"""

from __future__ import annotations

import json
import logging
import textwrap
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .module_index import (
    MODULE_INDEX,
    QUESTION_TYPES,
    get_module_ids,
    get_all_doc_handle_names,
    get_module_index_for_llm,
)

import os

EOH_ROUTER_ENABLE_GUARDRAIL = os.getenv("EOH_ROUTER_ENABLE_GUARDRAIL", "1") == "1"

logger = logging.getLogger(__name__)

# =============================================================================
# SYSTEM PROMPT FOR THE EOH ROUTER
# =============================================================================

EOH_ROUTER_SYSTEM_PROMPT = textwrap.dedent("""\
You are the EoH (Ethos of Health) Router, an expert clinical planner.
Your job is to look at a clinical question and produce a JSON plan that says:

- which EoH question type it is (A, B, C, D, E, or OTHER), and
- which EoH modules and doc handles to use.

You are a PLANNER ONLY:
- You do NOT fetch data or answer clinical questions directly.
- You output a structured JSON plan that downstream code will execute.
- You must ONLY use module IDs and doc handles from the provided MODULE_INDEX.

You may receive:
- A free-text clinical question.
- An optional JSON-like patient_state_summary (e.g. {"primary_focus": "flare_vs_noise"}).
Treat patient_state_summary as a hint, not ground truth.

-------------------------------------------------------------------------------
## 1. EoH-FIRST BIAS (CRITICAL)
-------------------------------------------------------------------------------

EoH exists to reason about:
- flares and near-term risk,
- baseline / trajectory / stability bands,
- remission maintenance and relapse prevention,
- plan adjustment over time,
- explainability and system QA.

In this environment, ALMOST ALL questions are intended to exercise EoH.

You must follow these rules:

1) If the question mentions ANY of these ideas, you MUST choose A, B, C, D or E
   (NOT OTHER):

   FLARE / RISK / TRAJECTORY:
   - "flare", "flares", "flare risk", "flare prediction", "flare prevention"
   - "exacerbation", "relapse", "relapses", "relapse risk", "relapse prevention"
   - "baseline", "chronic baseline", "band", "stability band", "stack",
     "flare stack", "stacked burden"
   - "trajectory", "short-horizon", "near-term",
     "next 3 months", "next three months",
     "next 6 months", "next six months",
     "next 12 months", "next twelve months",
     "over the next year", "over the next 5 years", "over the next five years"

   REMISSION / MAINTENANCE / PLAN:
   - "remission", "remission maintenance",
   - "maintenance therapy", "maintenance strategy", "maintenance plan",
   - "step-up", "step up", "step-down", "step down",
   - "escalate", "escalation", "de-escalate", "de-escalation",
   - "treat-to-target", "treat to target",
   - "care plan", "careplan", "monitoring plan", "follow-up plan",
   - "what should the next 12 months look like"

   ETHOS / SYSTEM:
   - "Ethos", "EoH", "Ethos-of-Health",
   - "tier", "tiering", "risk tier", "stability tier"

2) Pregnancy + chronic disease are AUTOMATICALLY EoH-like unless they are
   obviously pure guideline trivia.

   If the question mentions pregnancy or related terms:
   - "pregnancy", "pregnant", "preconception", "conception",
     "fertility", "peripartum", "postpartum"

   AND also mentions a chronic inflammatory / autoimmune disease such as:
   - "rheumatoid arthritis", "RA",
   - "systemic lupus erythematosus", "SLE", "lupus",
   - "antiphospholipid syndrome", "APS",
   - "ulcerative colitis", "Crohn", "inflammatory bowel disease", "IBD",
   - "vasculitis", "ANCA",
   - or similar chronic immune-mediated disease,

   then you MUST treat it as an EoH question (A, C, or especially D), because
   it inherently involves remission maintenance, flare prevention, and
   long-horizon risk around pregnancy.

   Examples that MUST be A–E (usually D), NOT OTHER:
   - "In biologic-refractory ulcerative colitis, what long-term maintenance
      strategy best prevents flares and colorectal cancer over the next 5 years?"
   - "In ANCA vasculitis remission, how should we structure relapse prevention
      and flare prediction over the next 5 years?"
   - "In SLE with APS who wishes to conceive, how should we manage anticoagulation
      and immunosuppression before, during, and after pregnancy to prevent
      flares and complications?"

3) OTHER is only allowed when ALL of the following are true:
   - The question does NOT fit A, B, C, D, or E, AND
   - It does NOT contain any of the triggers above (flare, remission, plan,
     pregnancy+chronic disease, EoH/tier language), AND
   - It is best handled as:
     * pure guideline Q&A (e.g. "What do the RA guidelines say about MTX dose?"),
       or
     * pure coding/abstraction,
       or
     * clearly outside chronic disease / flare / care-plan scope.

When in doubt, pick an EoH type (A–E) instead of OTHER.

-------------------------------------------------------------------------------
## 2. Question Types (Short Definitions)
-------------------------------------------------------------------------------

You must choose EXACTLY ONE question_type for each question:

A) Flare Risk / Baseline & Trajectory
   - "Where is this patient in EoH terrain (bands/stacks) and what is their
      near-term flare risk / trajectory?"

B) Flare vs Noise / Artefact
   - "Is this specific episode a real flare vs fibro/symbolic/overshoot/lab error?"

C) Explainability / Diagnostic Landscape
   - "Explain WHY EoH chose this flare prediction, tier, or diagnostic label."

D) Plan Adjustment (non-emergency)
   - "Given the current state, how should we adjust care intensity, maintenance
      therapy, or monitoring over the next months to years?"

E) Meta / Calibration / System QA
   - "Is the model calibrated, over-suppressing, drifting, or missing flares?"

OTHER) Very rare. Only for pure guideline/coding/other questions with NO
       EoH-style triggers and no flare/remission/plan/pregnancy+chronic disease
       trajectory intent.

-------------------------------------------------------------------------------
## 3. Simple Type Selection Algorithm
-------------------------------------------------------------------------------

Use this mechanical decision order:

1) If the main focus is "is this episode a true flare vs noise/artefact?" → B.

2) Else if the main focus is "explain EoH's decision, tier, or diagnostic
   landscape" → C.

3) Else if the main focus is "how to adjust the plan / maintenance / monitoring
   over 3–12 months or longer" OR "long-term strategy", including pregnancy
   planning in chronic disease → D.

4) Else if the main focus is "how is the model performing / calibrated /
   suppressing / drifting?" → E.

5) Else if the main focus is "where are we now in bands/stacks and what is the
   short-horizon flare risk / trajectory?" → A.

6) Else, and only if there are NO EoH triggers and the question is clearly
   pure guideline or coding trivia, use OTHER.

In question_type_explanation, briefly say why your chosen type fits better
than the alternatives (especially when you choose A or OTHER).

-------------------------------------------------------------------------------
## 4. Using MODULE_INDEX (Routing Plan)
-------------------------------------------------------------------------------

You are given a MODULE_INDEX describing each EoH module:
- module id (e.g. "M1", "M2", ...),
- layer (terrain, signal_tagging, flare_detection, care_planning, governance),
- llm_use_when (when to use it),
- doc_handles (e.g. pg_view:eoh_m1_patient_terrain, etc.).

When you build module_plan and doc_retrieval_plan:

- ONLY use module ids that exist in MODULE_INDEX.
- ONLY use doc handles that exist in MODULE_INDEX.
- Pick modules whose "llm_use_when" matches the chosen question_type.
- You do NOT need to use every module; pick a small, coherent set.

Example patterns (not strict, just common):

- Type A (Flare risk / trajectory): terrain + signal + prognostics
  e.g. M1–M3, M7A, M12, M13, M14, M24, M25

- Type B (Flare vs noise): terrain + signal QA + suppression
  e.g. M1–M3, M7A, M4, M5, M9, M6, M14, M7B

- Type C (Explainability): decision packets + features + tier mapping
  e.g. M21, M13, M12, M4, M5, M14, M25, M19, M41

- Type D (Plan adjustment): terrain + prognostics + care planning
  e.g. M1–M3, M7A, M12, M13, M14, M15, M7B, M22, M23, M24, M25

- Type E (Meta / calibration): calibration + suppression audit
  e.g. M19, M41, M48, plus any relevant terrain/decision modules.

For OTHER, you may return empty module_plan/doc_retrieval_plan or a very
minimal plan if appropriate.

-------------------------------------------------------------------------------
## 5. Timeline-aware routing (patient_state_summary hints)
-------------------------------------------------------------------------------

The router may receive a patient_state_summary with extra fields that signal
timeline availability or diagnostic landscape data. Common fields include:

- "primary_focus": high-level intent hint such as
  - "flare_vs_noise"
  - "flare_risk"
  - "diagnostic_landscape"
  - "plan_adjustment"
  - "meta_calibration"

- "eoh_has_timeline": true/false
  → true means a patient timeline has been computed and will be injected into
    the context (source 'patient_timeline' or 'eoh_demo_timeline').

- "eoh_timeline_patient_id": patient id for the loaded timeline (string).

- "eoh_has_diagnostic_landscape": true/false
  → true means a probabilistic diagnostic landscape object exists and will be
    available in context.

When these hints are present, you must bias routing accordingly:

1) If eoh_has_timeline == true:
   - Do NOT return OTHER unless the question is truly non-EoH.
   - Prefer A, B, C, D, or E based on the content of the question and
     primary_focus.
   - Include terrain + timeline-aware modules when relevant:
     e.g. modules that work with bands, stacks, flare windows, and
     diagnostic landscape (M1–M3, M7A, M12–M15, M19, M21, M24, M25, M48, M48B,
     M48C as appropriate).

2) If primary_focus == "flare_vs_noise":
   - Lean toward type B and include modules that distinguish flare from noise
     and suppression artefacts (e.g. M4–M7, M9, M19, M41, M48B).

3) If primary_focus == "diagnostic_landscape":
   - Lean toward type C (explainability) or type E (meta) depending on whether
     the question is about *explaining* the landscape vs *auditing* it.
   - Include modules that expose features and landscape stability (M13, M14,
     M19, M21, M25, M48C).

4) If primary_focus == "plan_adjustment":
   - Lean toward type D and include terrain/prognostic/planning modules
     that operate on the timeline (e.g. M1–M3, M7A, M12–M15, M22–M25).

5) If primary_focus == "meta_calibration":
   - Lean toward type E and include governance/calibration modules
     (M19, M41, M48, M48B, M48C).

These hints are *soft* but important. Do not ignore them. They should shift
your type_scores and module selection in a consistent way.

-------------------------------------------------------------------------------
## 6. Output Schema (MUST FOLLOW EXACTLY)
-------------------------------------------------------------------------------

Return ONLY a valid JSON object with this exact structure:

{
  "question_type": "A" | "B" | "C" | "D" | "E" | "OTHER",
  "question_type_explanation": "Brief explanation of why this question type was chosen, and why it is preferred over the other types.",
  "type_scores": {
    "A": 0.0,
    "B": 0.0,
    "C": 0.0,
    "D": 0.0,
    "E": 0.0,
    "OTHER": 0.0
  },
  "module_plan": [
    {
      "step": 1,
      "goal": "What this step accomplishes",
      "modules": ["M1", "M2"],
      "why": "Reasoning for including these modules"
    }
  ],
  "doc_retrieval_plan": [
    {
      "module": "M1",
      "handles": [{"kind": "pg_view", "name": "eoh_m1_patient_terrain"}],
      "purpose": "Why this data is needed"
    }
  ]
}

Requirements for type_scores:
- Provide a score in [0, 1] for EACH type (A, B, C, D, E, OTHER).
- question_type MUST be the key with the highest score.
- Even if the application ignores type_scores, you must still fill them.

-------------------------------------------------------------------------------
## 6. Critical Constraints
-------------------------------------------------------------------------------

1) ONLY use module IDs that exist in MODULE_INDEX.
2) ONLY use doc handles that exist in MODULE_INDEX.
3) Do NOT invent module IDs or doc handle names.
4) Keep the plan focused and small; do not add clearly unrelated modules.
5) For A–E questions, you should usually include at least one module in
   module_plan. Empty module_plan for A–E should be very rare.
6) For OTHER questions, a minimal or empty plan is acceptable.
7) Always include question_type_explanation to justify your classification,
   especially when you choose A or OTHER.

Return ONLY the JSON object. No markdown, no code fences.
""").strip()


# =============================================================================
# EoH trigger heuristics (post-hoc guardrail support)
# =============================================================================

EoH_FLARE_TRAJECTORY_TRIGGERS = [
    "flare", "flares", "flare risk", "flare prediction", "flare prevention",
    "exacerbation", "relapse", "relapses", "relapse risk", "relapse prevention",
    "baseline", "chronic baseline", "band", "stability band",
    "stack", "flare stack", "stacked burden",
    "trajectory", "short-horizon", "near-term",
    "next 3 months", "next three months",
    "next 6 months", "next six months",
    "next 12 months", "next twelve months",
    "next year", "over the next year",
    "over the next 5 years", "over the next five years",
]

EoH_PLAN_TRIGGERS = [
    "remission", "remission maintenance",
    "maintenance therapy", "maintenance strategy", "maintenance plan",
    "step-up", "step up", "step-down", "step down",
    "escalate", "escalation", "de-escalate", "de-escalation",
    "treat-to-target", "treat to target",
    "care plan", "careplan", "monitoring plan", "follow-up plan",
    "what should the next 12 months look like",
]

EoH_SYSTEM_TRIGGERS = [
    "ethos", "eoh", "ethos-of-health",
    "tier", "tiering", "risk tier", "stability tier",
]


def _has_eoh_triggers(question: str) -> bool:
    """Return True if the question contains any EoH-ish lexical triggers."""
    q = question.lower()
    for t in (
        EoH_FLARE_TRAJECTORY_TRIGGERS
        + EoH_PLAN_TRIGGERS
        + EoH_SYSTEM_TRIGGERS
    ):
        if t in q:
            return True
    return False


def _guess_forced_eoh_type(question: str) -> str:
    """
    Heuristic for choosing a forced EoH question_type when the model returned OTHER
    but the question clearly contains EoH triggers.

    - If strongly plan / maintenance / long-horizon flavored: D
    - Else if clearly trajectory-ish: A
    - Else default to D (for board-facing long-horizon planning).
    """
    q = question.lower()

    has_plan = any(t in q for t in EoH_PLAN_TRIGGERS)
    has_long_horizon = any(
        t in q
        for t in [
            "next 12 months", "over the next year",
            "over the next 5 years", "over the next five years",
            "5 years", "five years",
        ]
    )
    if has_plan or has_long_horizon:
        return "D"

    has_trajectory = any(t in q for t in ["trajectory", "short-horizon", "near-term"])
    if has_trajectory:
        return "A"

    return "D"


def _apply_posthoc_eoh_guardrail(
    plan: Dict[str, Any],
    question: str,
) -> Dict[str, Any]:
    """
    If the question clearly has EoH triggers but the router chose OTHER,
    force an EoH type (A or D) and adjust type_scores + explanation.

    This keeps the module_plan/doc_retrieval_plan the model produced; we only
    correct the high-level classification.
    """
    if not _has_eoh_triggers(question):
        return plan

    qtype = plan.get("question_type", "OTHER")
    if qtype != "OTHER":
        return plan

    forced_type = _guess_forced_eoh_type(question)

    # Ensure type_scores exists and has all keys
    scores = plan.get("type_scores") or {}
    for key in ["A", "B", "C", "D", "E", "OTHER"]:
        scores.setdefault(key, 0.0)

    max_existing = max(scores.values()) if scores else 0.0
    forced_score = max(0.8, max_existing)
    scores[forced_type] = forced_score
    scores["OTHER"] = min(scores["OTHER"], 0.05)
    plan["type_scores"] = scores

    # Flip question_type
    old_type = qtype
    plan["question_type"] = forced_type

    # Explanation
    expl = plan.get("question_type_explanation") or ""
    extra = (
        f" Post-hoc guardrail: question contained EoH triggers but router "
        f"chose {old_type}, so type was forced to '{forced_type}'."
    )
    plan["question_type_explanation"] = (expl + extra).strip()

    logger.warning(
        "EoH Router guardrail: forced question_type from %s to %s for EoH-trigger question: %s",
        old_type,
        forced_type,
        question[:200],
    )

    return plan

def _build_module_index_context(module_index: Dict[str, Any]) -> str:
    """Build a formatted MODULE_INDEX context for the LLM prompt."""
    lines = ["## MODULE_INDEX\n"]
    for mid, mod in module_index.items():
        lines.append(f"### {mid} - {mod['name']}")
        lines.append(f"Layer: {mod['layer']}")
        lines.append(f"LLM use when: {mod['llm_use_when']}")
        handles_str = ", ".join(
            f"{h['kind']}:{h['name']}" for h in mod["doc_handles"]
        )
        lines.append(f"Doc handles: {handles_str}")
        lines.append("")
    return "\n".join(lines)


def _build_user_message(
    question: str,
    patient_state_summary: Optional[Dict[str, Any]] = None,
) -> str:
    """Build the user message for the LLM."""
    parts = [f"## QUESTION\n{question}"]
    
    if patient_state_summary:
        parts.append(f"\n## PATIENT_STATE_SUMMARY\n{json.dumps(patient_state_summary, indent=2)}")
    
    parts.append("\n## TASK\nAnalyze this question and create an execution plan following the routing recipes.")
    parts.append("Return ONLY valid JSON matching the output schema. No markdown, no code fences.")
    
    return "\n".join(parts)


def _validate_and_clean_plan(
    plan: Dict[str, Any],
    valid_module_ids: set,
    valid_doc_handles: set,
) -> Dict[str, Any]:
    """
    Validate and clean the LLM-generated plan.
    
    - Validates question_type
    - Normalizes type_scores
    - Drops unknown module IDs from module_plan
    - Drops unknown doc handles from doc_retrieval_plan
    - Logs warnings for any dropped items
    """
    raw_qtype = plan.get("question_type", "OTHER")
    cleaned_plan: Dict[str, Any] = {
        "question_type": raw_qtype,
        "question_type_explanation": plan.get(
            "question_type_explanation",
            "Unable to classify question",
        ),
        "type_scores": plan.get("type_scores") or {},
        "module_plan": [],
        "doc_retrieval_plan": [],
    }
    
    # Validate question_type
    valid_types = {"A", "B", "C", "D", "E", "OTHER"}
    if cleaned_plan["question_type"] not in valid_types:
        logger.warning(
            "Invalid question_type '%s', defaulting to OTHER",
            cleaned_plan["question_type"],
        )
        cleaned_plan["question_type"] = "OTHER"
    
    # Normalize type_scores: ensure all keys present and in [0, 1]
    scores = cleaned_plan["type_scores"] or {}
    for key in ["A", "B", "C", "D", "E", "OTHER"]:
        val = scores.get(key, 0.0)
        try:
            val = float(val)
        except (TypeError, ValueError):
            val = 0.0
        # Clamp to [0, 1]
        if val < 0.0:
            val = 0.0
        if val > 1.0:
            val = 1.0
        scores[key] = val

    # If all zeros, boost the selected question_type so it's clearly the max
    if all(v == 0.0 for v in scores.values()):
        scores[cleaned_plan["question_type"]] = 1.0

    # Ensure question_type has the highest score
    max_key = max(scores, key=scores.get)
    if max_key != cleaned_plan["question_type"]:
        logger.debug(
            "Adjusting type_scores so question_type %s has highest score (was %s)",
            cleaned_plan["question_type"], max_key,
        )
        qtype = cleaned_plan["question_type"]
        max_val = max(scores.values())
        scores[qtype] = max_val
    cleaned_plan["type_scores"] = scores
    
    # Clean module_plan
    for step in plan.get("module_plan", []):
        if not isinstance(step, dict):
            continue
        
        valid_modules = []
        for mid in step.get("modules", []):
            if mid in valid_module_ids:
                valid_modules.append(mid)
            else:
                logger.warning("Dropping unknown module ID from plan: %s", mid)
        
        if valid_modules:
            cleaned_plan["module_plan"].append({
                "step": step.get("step", len(cleaned_plan["module_plan"]) + 1),
                "goal": step.get("goal", ""),
                "modules": valid_modules,
                "why": step.get("why", ""),
            })
    
    # Clean doc_retrieval_plan
    for item in plan.get("doc_retrieval_plan", []):
        if not isinstance(item, dict):
            continue
        
        module_id = item.get("module", "")
        if module_id not in valid_module_ids:
            logger.warning("Dropping doc_retrieval_plan item with unknown module: %s", module_id)
            continue
        
        valid_handles = []
        for handle in item.get("handles", []):
            if isinstance(handle, dict) and handle.get("name") in valid_doc_handles:
                valid_handles.append(handle)
            elif isinstance(handle, dict):
                logger.warning(
                    "Dropping unknown doc handle '%s' from module %s",
                    handle.get("name", "unknown"),
                    module_id
                )
        
        if valid_handles:
            cleaned_plan["doc_retrieval_plan"].append({
                "module": module_id,
                "handles": valid_handles,
                "purpose": item.get("purpose", ""),
            })
    
    return cleaned_plan


def _create_fallback_plan(question_type: str = "OTHER") -> Dict[str, Any]:
    """Create a minimal fallback plan when LLM parsing fails."""
    if question_type not in {"A", "B", "C", "D", "E", "OTHER"}:
        question_type = "OTHER"
    
    # Simple scores: 1.0 for chosen type, 0.0 for others
    type_scores = {t: 0.0 for t in ["A", "B", "C", "D", "E", "OTHER"]}
    type_scores[question_type] = 1.0

    return {
        "question_type": question_type,
        "question_type_explanation": "Fallback plan due to parsing error",
        "type_scores": type_scores,
        "module_plan": [],
        "doc_retrieval_plan": [],
    }


async def eoh_llm_router(
    client: OpenAI,
    question: str,
    patient_state_summary: Optional[Dict[str, Any]] = None,
    module_index: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Route a clinical question to the appropriate EoH modules using an LLM.
    
    This is a PLANNER ONLY - it does NOT fetch data or answer clinical questions.
    It outputs a structured "plan" object that downstream code can execute.
    
    Args:
        client: OpenAI client instance
        question: The clinical question to route
        patient_state_summary: Optional patient state context (short JSON)
        module_index: Optional custom MODULE_INDEX (defaults to the standard one)
    
    Returns:
        A dictionary with:
        - question_type: One of {A, B, C, D, E, OTHER}
        - question_type_explanation: String explaining the classification
        - module_plan: List of steps with modules to invoke
        - doc_retrieval_plan: List of data sources to query
    
    Raises:
        ValueError: If the question is empty
    """
    if not question or not question.strip():
        raise ValueError("Question cannot be empty")
    
    # Use provided module_index or default
    if module_index is None:
        module_index = MODULE_INDEX
    
    # Build valid sets for validation
    valid_module_ids = set(module_index.keys())
    valid_doc_handles = set()
    for mod in module_index.values():
        for handle in mod.get("doc_handles", []):
            valid_doc_handles.add(handle["name"])
    
    # Build the module index context for the LLM
    module_index_context = _build_module_index_context(module_index)
    
    # Build messages
    messages = [
        {"role": "system", "content": EOH_ROUTER_SYSTEM_PROMPT},
        {"role": "system", "content": module_index_context},
        {"role": "user", "content": _build_user_message(question, patient_state_summary)},
    ]
    
    # Log the request (redacting any PHI in patient_state_summary)
    logger.debug(
        "EoH Router request: question_length=%d, has_patient_state=%s",
        len(question),
        patient_state_summary is not None
    )
    
    try:
        # Call the LLM
        response = client.chat.completions.create(
            model="gpt-4o",
            temperature=0.1,
            response_format={"type": "json_object"},
            messages=messages,
        )
        
        raw_content = (response.choices[0].message.content or "").strip()
        
        # Log raw response at DEBUG level
        logger.debug("EoH Router raw LLM response: %s", raw_content[:500] if raw_content else "empty")
        
        # Parse JSON
        try:
            plan = json.loads(raw_content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse LLM response as JSON: %s", e)
            return _create_fallback_plan()
        
        # Validate and clean the plan
        cleaned_plan = _validate_and_clean_plan(plan, valid_module_ids, valid_doc_handles)

        # Apply EoH trigger guardrail (may force OTHER -> A/D)
        if EOH_ROUTER_ENABLE_GUARDRAIL:
            cleaned_plan = _apply_posthoc_eoh_guardrail(cleaned_plan, question=question)
        
        # Log the validated plan
        logger.info(
            "EoH Router plan: question_type=%s, steps=%d, modules=%s",
            cleaned_plan["question_type"],
            len(cleaned_plan["module_plan"]),
            [m for step in cleaned_plan["module_plan"] for m in step.get("modules", [])],
        )
        
        return cleaned_plan
        
    except Exception as e:
        logger.error("EoH Router LLM call failed: %s", e)
        return _create_fallback_plan()


def create_mock_router_response(question_type: str) -> Dict[str, Any]:
    """
    Create a mock router response for testing purposes.
    
    Args:
        question_type: One of {A, B, C, D, E, OTHER}
    
    Returns:
        A mock plan matching the expected output schema
    """
    if question_type not in QUESTION_TYPES and question_type != "OTHER":
        question_type = "OTHER"
    
    if question_type == "OTHER":
        return _create_fallback_plan("OTHER")
    
    qt_info = QUESTION_TYPES[question_type]
    modules = qt_info["canonical_modules"]
    
    # Build module_plan from canonical modules
    module_plan = []
    step_num = 1
    
    # Group modules into logical steps based on layer
    layer_groups = {}
    for mid in modules:
        if mid in MODULE_INDEX:
            layer = MODULE_INDEX[mid]["layer"]
            if layer not in layer_groups:
                layer_groups[layer] = []
            layer_groups[layer].append(mid)
    
    layer_order = ["terrain", "signal_tagging", "flare_detection", "care_planning", "governance"]
    for layer in layer_order:
        if layer in layer_groups:
            module_plan.append({
                "step": step_num,
                "goal": f"Process {layer.replace('_', ' ')} modules",
                "modules": layer_groups[layer],
                "why": f"Required for {question_type} question type",
            })
            step_num += 1
    
    # Build doc_retrieval_plan
    doc_retrieval_plan = []
    for mid in modules:
        if mid in MODULE_INDEX:
            mod = MODULE_INDEX[mid]
            doc_retrieval_plan.append({
                "module": mid,
                "handles": mod["doc_handles"],
                "purpose": mod["llm_use_when"][:100],
            })
    
    return {
        "question_type": question_type,
        "question_type_explanation": qt_info["description"],
        "module_plan": module_plan,
        "doc_retrieval_plan": doc_retrieval_plan,
    }
