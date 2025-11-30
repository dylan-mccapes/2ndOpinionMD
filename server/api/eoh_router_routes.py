# server/api/eoh_router_routes.py
"""
EoH Router API Endpoints

Provides a FastAPI router for the EoH (Ethos of Health) planning system.
This is a PLANNING ONLY layer - it does NOT fetch data or execute care plan changes.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field
from openai import OpenAI

from server.eoh.router_llm import eoh_llm_router
from server.eoh.module_index import MODULE_INDEX, QUESTION_TYPES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/eoh", tags=["eoh_router"])


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class DocHandle(BaseModel):
    """A document/data handle reference."""
    kind: str = Field(..., description="Type of handle: pg_view, pg_table, ann_index, or doc_corpus")
    name: str = Field(..., description="Name of the handle/resource")


class ModulePlanStep(BaseModel):
    """A single step in the module execution plan."""
    step: int = Field(..., description="Step number in the execution sequence")
    goal: str = Field(..., description="What this step accomplishes")
    modules: List[str] = Field(..., description="List of module IDs to invoke in this step")
    why: str = Field(..., description="Reasoning for including these modules")


class DocRetrievalItem(BaseModel):
    """A data retrieval specification for a module."""
    module: str = Field(..., description="Module ID this retrieval is for")
    handles: List[DocHandle] = Field(..., description="List of doc handles to query")
    purpose: str = Field(..., description="Why this data is needed")


class RouterPlanRequest(BaseModel):
    """Request body for the router_plan endpoint."""
    question: str = Field(..., description="The clinical question to route", min_length=1)
    patient_state_summary: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional patient state context as a short JSON object"
    )


class RouterPlanResponse(BaseModel):
    """Response from the router_plan endpoint."""
    question_type: str = Field(
        ...,
        description="Question type classification: A, B, C, D, E, or OTHER"
    )
    question_type_explanation: str = Field(
        ...,
        description="Explanation of why this question type was chosen"
    )
    module_plan: List[ModulePlanStep] = Field(
        ...,
        description="Ordered list of execution steps with modules to invoke"
    )
    doc_retrieval_plan: List[DocRetrievalItem] = Field(
        ...,
        description="List of data sources to query for each module"
    )


class QuestionTypeInfo(BaseModel):
    """Information about a question type."""
    type_code: str
    description: str
    goal: str
    canonical_modules: List[str]


class ModuleInfo(BaseModel):
    """Information about an EoH module."""
    id: str
    name: str
    layer: str
    llm_use_when: str
    doc_handles: List[DocHandle]


# =============================================================================
# ENDPOINTS
# =============================================================================

@router.post("/router_plan", response_model=RouterPlanResponse)
async def router_plan(
    request: RouterPlanRequest = Body(...),
) -> RouterPlanResponse:
    """
    Generate an EoH execution plan for a clinical question.
    
    This endpoint uses an LLM to analyze the question and create a structured
    execution plan specifying which EoH modules to invoke and which data sources
    to query.
    
    This is a PLANNING ONLY endpoint:
    - It does NOT fetch data or answer clinical questions directly.
    - It does NOT execute care plan changes.
    - It returns a plan that downstream code can execute.
    
    Question Types:
    - A: "What is this patient's flare risk over the next X days/weeks?"
    - B: "Is this a real flare or symbolic / overshoot / lab error?"
    - C: "Why did the system predict / escalate a flare?" (Explainability)
    - D: "Given this state, how should we adjust the plan?" (non-emergency)
    - E: "Is the model still calibrated / are we over-suppressing flares?" (meta)
    - OTHER: Questions that don't fit the above categories
    """
    # Validate OpenAI API key
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY not configured")
        raise HTTPException(
            status_code=500,
            detail={"code": "config_error", "message": "OPENAI_API_KEY not configured"}
        )
    
    # Validate question
    if not request.question.strip():
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_question", "message": "Question cannot be empty"}
        )
    
    if len(request.question) > 10000:
        raise HTTPException(
            status_code=400,
            detail={"code": "question_too_long", "message": "Question exceeds 10000 characters"}
        )
    
    try:
        # Create OpenAI client
        client = OpenAI(api_key=api_key)
        
        # Call the router
        plan = await eoh_llm_router(
            client=client,
            question=request.question,
            patient_state_summary=request.patient_state_summary,
            module_index=MODULE_INDEX,
        )
        
        # Validate response structure
        if not isinstance(plan, dict):
            logger.error("Router returned non-dict response: %s", type(plan))
            raise HTTPException(
                status_code=500,
                detail={"code": "invalid_response", "message": "Router returned invalid response"}
            )
        
        # Ensure required fields exist
        required_fields = ["question_type", "question_type_explanation", "module_plan", "doc_retrieval_plan"]
        for field in required_fields:
            if field not in plan:
                logger.error("Router response missing field: %s", field)
                plan[field] = [] if field.endswith("_plan") else "OTHER" if field == "question_type" else ""
        
        # Validate question_type
        valid_types = {"A", "B", "C", "D", "E", "OTHER"}
        if plan["question_type"] not in valid_types:
            logger.warning("Invalid question_type '%s', defaulting to OTHER", plan["question_type"])
            plan["question_type"] = "OTHER"
        
        logger.info(
            "Router plan generated: question_type=%s, steps=%d",
            plan["question_type"],
            len(plan.get("module_plan", []))
        )
        
        return RouterPlanResponse(**plan)
        
    except HTTPException:
        raise
    except ValueError as e:
        logger.error("Router validation error: %s", e)
        raise HTTPException(
            status_code=400,
            detail={"code": "validation_error", "message": str(e)}
        )
    except Exception as e:
        logger.error("Router error: %s", e, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={"code": "router_error", "message": f"Error generating plan: {str(e)}"}
        )


@router.get("/question_types", response_model=List[QuestionTypeInfo])
async def get_question_types() -> List[QuestionTypeInfo]:
    """
    Get information about all supported question types.
    
    Returns the question type codes, descriptions, goals, and canonical module paths.
    """
    return [
        QuestionTypeInfo(
            type_code=code,
            description=info["description"],
            goal=info["goal"],
            canonical_modules=info["canonical_modules"],
        )
        for code, info in QUESTION_TYPES.items()
    ]


@router.get("/modules", response_model=List[ModuleInfo])
async def get_modules() -> List[ModuleInfo]:
    """
    Get information about all EoH modules in the MODULE_INDEX.
    
    Returns module IDs, names, layers, usage hints, and doc handles.
    """
    return [
        ModuleInfo(
            id=mid,
            name=mod["name"],
            layer=mod["layer"],
            llm_use_when=mod["llm_use_when"],
            doc_handles=[DocHandle(**h) for h in mod["doc_handles"]],
        )
        for mid, mod in MODULE_INDEX.items()
    ]


@router.get("/modules/{module_id}", response_model=ModuleInfo)
async def get_module(module_id: str) -> ModuleInfo:
    """
    Get information about a specific EoH module.
    
    Args:
        module_id: The module ID (e.g., "M1", "M13", "M21")
    
    Returns:
        Module information including name, layer, usage hints, and doc handles.
    """
    if module_id not in MODULE_INDEX:
        raise HTTPException(
            status_code=404,
            detail={"code": "module_not_found", "message": f"Module '{module_id}' not found"}
        )
    
    mod = MODULE_INDEX[module_id]
    return ModuleInfo(
        id=module_id,
        name=mod["name"],
        layer=mod["layer"],
        llm_use_when=mod["llm_use_when"],
        doc_handles=[DocHandle(**h) for h in mod["doc_handles"]],
    )


@router.get("/health")
async def eoh_router_health() -> Dict[str, Any]:
    """
    Health check for the EoH router.
    
    Returns status and configuration information.
    """
    has_api_key = bool(os.getenv("OPENAI_API_KEY"))
    
    return {
        "status": "ok" if has_api_key else "degraded",
        "openai_configured": has_api_key,
        "module_count": len(MODULE_INDEX),
        "question_types": list(QUESTION_TYPES.keys()),
    }
