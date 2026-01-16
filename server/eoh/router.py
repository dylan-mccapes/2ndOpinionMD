"""
EoH Router with Timeline Integration
Location: server/eoh/router.py
Version: v100 (Cipher + Devin Method)

This module provides the main EoH router with timeline integration.

EoH Router flag:
?use_timeline=1
-> MUST prepend timeline context doc
-> MUST emit SSE events in this order:
  1. timeline_loaded
  2. timeline_signals
  3. timeline_flare_features
  4. timeline_probabilistic_differential

REGULATORY GUARDRAILS:
- NEVER provide a diagnosis
- ALWAYS use probabilistic, non-certain language
- NEVER output "you have X"
- ALWAYS produce explainability (drivers, not conclusions)
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from .router_llm import eoh_llm_router, create_mock_router_response
from .fusion import fuse_timeline_context, create_timeline_context_doc
from .validators import validate_response_safety, SSE_EVENT_ORDER

logger = logging.getLogger(__name__)


# ============================================================================
# SSE Event Types (MANDATORY ORDER)
# ============================================================================

SSE_EVENTS = {
    "timeline_loaded": {
        "order": 1,
        "description": "Timeline data has been loaded for the patient",
    },
    "timeline_signals": {
        "order": 2,
        "description": "Signals extracted from timeline events",
    },
    "timeline_flare_features": {
        "order": 3,
        "description": "Flare-related features from timeline analysis",
    },
    "timeline_probabilistic_differential": {
        "order": 4,
        "description": "Probabilistic differential landscape",
    },
}


# ============================================================================
# SSE Event Generators
# ============================================================================

def create_sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """
    Create an SSE event string.
    
    Args:
        event_type: Type of event
        data: Event data
        
    Returns:
        SSE formatted string
    """
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


async def emit_timeline_events(
    patient_id: str,
    events: List[Dict[str, Any]],
    flare_result: Dict[str, Any],
    diagnostic_result: Dict[str, Any],
) -> AsyncGenerator[str, None]:
    """
    Emit SSE events in the mandatory order.
    
    Order:
    1. timeline_loaded
    2. timeline_signals
    3. timeline_flare_features
    4. timeline_probabilistic_differential
    
    Args:
        patient_id: Patient identifier
        events: Timeline events
        flare_result: Result from flare precursor analysis
        diagnostic_result: Result from diagnostic landscape analysis
        
    Yields:
        SSE event strings
    """
    # 1. timeline_loaded
    yield create_sse_event("timeline_loaded", {
        "patient_id": patient_id,
        "event_count": len(events),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    
    # 2. timeline_signals
    signals = extract_timeline_signals(events)
    yield create_sse_event("timeline_signals", {
        "patient_id": patient_id,
        "signals": signals,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    
    # 3. timeline_flare_features
    yield create_sse_event("timeline_flare_features", {
        "patient_id": patient_id,
        "precursors": flare_result.get("precursors", []),
        "scores": flare_result.get("scores", []),
        "flare_likelihood": flare_result.get("flare_likelihood", {}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    
    # 4. timeline_probabilistic_differential
    yield create_sse_event("timeline_probabilistic_differential", {
        "patient_id": patient_id,
        "probabilities": diagnostic_result.get("diagnostic_probabilities", {}),
        "drivers": diagnostic_result.get("drivers", []),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })


def extract_timeline_signals(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Extract key signals from timeline events.
    
    Args:
        events: List of timeline events
        
    Returns:
        List of extracted signals
    """
    signals = []
    
    # Count events by type
    event_counts = {}
    for event in events:
        event_type = event.get("event_type", "unknown")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    signals.append({
        "type": "event_distribution",
        "data": event_counts,
    })
    
    # Extract lab signals
    lab_signals = []
    for event in events:
        if event.get("event_type") == "lab":
            structured = event.get("structured", {})
            if structured.get("flag") in ("high", "low"):
                lab_signals.append({
                    "test": structured.get("test_name"),
                    "flag": structured.get("flag"),
                    "value": structured.get("value"),
                })
    
    if lab_signals:
        signals.append({
            "type": "abnormal_labs",
            "data": lab_signals[:10],  # Limit to top 10
        })
    
    # Extract symptom signals
    symptom_signals = []
    for event in events:
        if event.get("event_type") == "symptom":
            structured = event.get("structured", {})
            if structured.get("severity") in ("moderate", "severe"):
                symptom_signals.append({
                    "symptom": structured.get("primary_symptom"),
                    "severity": structured.get("severity"),
                    "regions": structured.get("body_regions", []),
                })
    
    if symptom_signals:
        signals.append({
            "type": "significant_symptoms",
            "data": symptom_signals[:10],  # Limit to top 10
        })
    
    return signals


# ============================================================================
# Main Router Functions
# ============================================================================

async def route_with_timeline(
    client: Any,
    question: str,
    patient_id: str,
    events: Optional[List[Dict[str, Any]]] = None,
    session: Optional[Any] = None,
    use_timeline: bool = True,
) -> Dict[str, Any]:
    """
    Route a question through the EoH system with timeline context.
    
    Args:
        client: OpenAI client
        question: Clinical question
        patient_id: Patient identifier
        events: Optional pre-loaded timeline events
        session: Optional database session
        use_timeline: Whether to include timeline context
        
    Returns:
        Router result with plan and timeline context
    """
    logger.info(f"Routing question for patient {patient_id}, use_timeline={use_timeline}")
    
    result = {
        "patient_id": patient_id,
        "question": question,
        "use_timeline": use_timeline,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Load timeline events if needed
    if use_timeline and events is None:
        events = []  # Would load from database
        logger.warning("No events provided, using empty list")
    
    # Build patient state summary from timeline
    patient_state_summary = None
    if use_timeline and events:
        patient_state_summary = build_patient_state_summary(events)
        result["timeline_summary"] = patient_state_summary
    
    # Route through EoH LLM router
    try:
        plan = await eoh_llm_router(
            client=client,
            question=question,
            patient_state_summary=patient_state_summary,
        )
        result["plan"] = plan
    except Exception as e:
        logger.error(f"EoH router failed: {e}")
        result["plan"] = create_mock_router_response("OTHER")
        result["error"] = str(e)
    
    # Add timeline context if enabled
    if use_timeline and events:
        from server.ann.flare import find_flare_precursors
        from server.ann.diagnostic import estimate_diagnostic_landscape
        
        # Run flare analysis
        flare_result = find_flare_precursors(patient_id, events=events)
        result["flare_analysis"] = flare_result
        
        # Run diagnostic landscape
        diagnostic_result = estimate_diagnostic_landscape(patient_id, events=events)
        result["diagnostic_landscape"] = diagnostic_result
        
        # Create fused context
        fused_context = fuse_timeline_context(
            events=events,
            flare_result=flare_result,
            diagnostic_result=diagnostic_result,
        )
        result["fused_context"] = fused_context
    
    # Validate response safety
    safety_result = validate_response_safety(result)
    if not safety_result["is_safe"]:
        logger.warning(f"Safety validation failed: {safety_result['violations']}")
        result["safety_warnings"] = safety_result["violations"]
    
    return result


def build_patient_state_summary(events: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Build a patient state summary from timeline events.
    
    Args:
        events: List of timeline events
        
    Returns:
        Summary dictionary
    """
    summary = {
        "total_events": len(events),
        "event_types": {},
        "recent_labs": [],
        "recent_symptoms": [],
        "active_medications": [],
    }
    
    # Count event types
    for event in events:
        event_type = event.get("event_type", "unknown")
        summary["event_types"][event_type] = summary["event_types"].get(event_type, 0) + 1
    
    # Get recent labs (last 5)
    lab_events = [e for e in events if e.get("event_type") == "lab"]
    lab_events.sort(key=lambda x: x.get("ts") or "", reverse=True)
    for lab in lab_events[:5]:
        structured = lab.get("structured", {})
        summary["recent_labs"].append({
            "test": structured.get("test_name"),
            "value": structured.get("value"),
            "flag": structured.get("flag"),
        })
    
    # Get recent symptoms (last 5)
    symptom_events = [e for e in events if e.get("event_type") == "symptom"]
    symptom_events.sort(key=lambda x: x.get("ts") or "", reverse=True)
    for symptom in symptom_events[:5]:
        structured = symptom.get("structured", {})
        summary["recent_symptoms"].append({
            "symptom": structured.get("primary_symptom"),
            "severity": structured.get("severity"),
        })
    
    # Get active medications
    med_events = [e for e in events if e.get("event_type") == "medication"]
    for med in med_events:
        structured = med.get("structured", {})
        if structured.get("changes") not in ("stopped", "discontinued"):
            summary["active_medications"].append({
                "drug": structured.get("drug"),
                "dose": structured.get("dose"),
            })
    
    return summary


async def stream_with_timeline(
    client: Any,
    question: str,
    patient_id: str,
    events: Optional[List[Dict[str, Any]]] = None,
    session: Optional[Any] = None,
) -> AsyncGenerator[str, None]:
    """
    Stream EoH response with timeline SSE events.
    
    This function emits SSE events in the mandatory order:
    1. timeline_loaded
    2. timeline_signals
    3. timeline_flare_features
    4. timeline_probabilistic_differential
    
    Args:
        client: OpenAI client
        question: Clinical question
        patient_id: Patient identifier
        events: Optional pre-loaded timeline events
        session: Optional database session
        
    Yields:
        SSE event strings
    """
    logger.info(f"Streaming with timeline for patient {patient_id}")
    
    # Load events if not provided
    if events is None:
        events = []
        logger.warning("No events provided, using empty list")
    
    # Import here to avoid circular imports
    from server.ann.flare import find_flare_precursors
    from server.ann.diagnostic import estimate_diagnostic_landscape
    
    # Run analyses
    flare_result = find_flare_precursors(patient_id, events=events)
    diagnostic_result = estimate_diagnostic_landscape(patient_id, events=events)
    
    # Emit timeline events in order
    async for event in emit_timeline_events(
        patient_id=patient_id,
        events=events,
        flare_result=flare_result,
        diagnostic_result=diagnostic_result,
    ):
        yield event
    
    # Route the question
    result = await route_with_timeline(
        client=client,
        question=question,
        patient_id=patient_id,
        events=events,
        session=session,
        use_timeline=True,
    )
    
    # Emit final result
    yield create_sse_event("eoh_result", {
        "plan": result.get("plan", {}),
        "fused_context": result.get("fused_context", {}),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
