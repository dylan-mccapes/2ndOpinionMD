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

logger = logging.getLogger(__name__)

# =============================================================================
# SYSTEM PROMPT FOR THE EOH ROUTER
# =============================================================================

EOH_ROUTER_SYSTEM_PROMPT = textwrap.dedent("""\
You are the EoH (Ethos of Health) Router, an expert clinical planning system.
Your job is to analyze clinical questions and create a structured execution plan
that specifies which EoH modules to invoke and which data sources to query.

You are a PLANNER ONLY:
- You do NOT fetch data or answer clinical questions directly.
- You output a structured JSON plan that downstream code will execute.
- You must ONLY use module IDs and doc handles from the provided MODULE_INDEX.

## Question Types

You must classify each question into one of these types:

A) "What is this patient's flare risk over the next X days/weeks?"
   Goal: Compute flare probability, interpret trajectory, give drivers + safety context.

B) "Is this a real flare or symbolic / overshoot / lab error?"
   Goal: Classification of the instability event.

C) "Why did the system predict / escalate a flare?" (Explainability)
   Goal: Reconstruct the decision chain.

D) "Given this state, how should we adjust the plan?" (non-emergency)
   Goal: Adjust tasks/plan intensity, not trigger crisis.

E) "Is the model still calibrated / are we over-suppressing flares?" (meta)
   Goal: Meta on performance, not per-patient.

OTHER) Questions that don't fit the above categories.

## Routing Recipes

### Type A (Flare Risk):
1. Check terrain & baseline: M1, M2, M3A/B
2. Validate and tag signals: M7A, M4, M5, M9
3. Compress narratives: M12
4. Generate prognostic vector: M13
5. Attach safety/suppression context: M13, M41, M9
6. Output to user: M14, M24, M25, M21

### Type B (Real Flare vs Symbolic):
1. Locate event in terrain: M1, M2, M3A
2. Examine raw signals + QA: M7A, M12, M4, M5
3. Run suppression reasoning: M4, M9, M5
4. Decide classification
5. Route outcome: M6, M14, M10 (if T4), M11, M7B

### Type C (Explainability):
1. Pull stored decision packet: M21
2. Backtrack to features and digests: M13, M12, M4, M5
3. Reconstruct tier mapping: M14
4. Include suppression and QA context: M9, M41, M7A, M19
5. Generate explanation: M25

### Type D (Plan Adjustment):
1. Understand trajectory and risk: M1-3, M7A, M12, M13
2. Map risk to tier & suggested actions: M14
3. Build or adjust CarePlan: M15, M7B, M22, M23
4. Surface to humans: M24, M25

### Type E (Meta/Calibration):
1. M19: calibration metrics, drift detection
2. M41: suppression audit trail
3. M48: retraining and policy updates lineage

## Output Schema

You MUST return a valid JSON object with this exact structure:
{
  "question_type": "A" | "B" | "C" | "D" | "E" | "OTHER",
  "question_type_explanation": "Brief explanation of why this question type was chosen",
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

## Critical Constraints

1. ONLY use module IDs that exist in the MODULE_INDEX provided.
2. ONLY use doc handles that exist in the MODULE_INDEX provided.
3. Do NOT fabricate or invent module IDs or doc handle names.
4. Keep the plan focused and relevant to the question.
5. For "OTHER" questions, provide a minimal fallback plan or empty arrays.
6. Always include question_type_explanation to justify your classification.
""").strip()


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
    
    - Drops unknown module IDs from module_plan
    - Drops unknown doc handles from doc_retrieval_plan
    - Logs warnings for any dropped items
    """
    cleaned_plan = {
        "question_type": plan.get("question_type", "OTHER"),
        "question_type_explanation": plan.get("question_type_explanation", "Unable to classify question"),
        "module_plan": [],
        "doc_retrieval_plan": [],
    }
    
    # Validate question_type
    valid_types = {"A", "B", "C", "D", "E", "OTHER"}
    if cleaned_plan["question_type"] not in valid_types:
        logger.warning(
            "Invalid question_type '%s', defaulting to OTHER",
            cleaned_plan["question_type"]
        )
        cleaned_plan["question_type"] = "OTHER"
    
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
    return {
        "question_type": question_type,
        "question_type_explanation": "Fallback plan due to parsing error",
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
        
        # Log the validated plan
        logger.info(
            "EoH Router plan: question_type=%s, steps=%d, modules=%s",
            cleaned_plan["question_type"],
            len(cleaned_plan["module_plan"]),
            [m for step in cleaned_plan["module_plan"] for m in step.get("modules", [])]
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
