"""
EoH Context Fusion Module
Location: server/eoh/fusion.py
Version: v100 (Cipher + Devin Method)

This module handles fusing timeline context with RAG content for the EoH system.

The fusion process:
1. Creates a timeline context document from patient events
2. Combines with RAG-retrieved medical knowledge
3. Produces a unified context for LLM reasoning

REGULATORY GUARDRAILS:
- NEVER provide a diagnosis
- ALWAYS use probabilistic, non-certain language
- NEVER output "you have X"
- ALWAYS produce explainability (drivers, not conclusions)
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Timeline Context Document Creation
# ============================================================================

def create_timeline_context_doc(
    events: List[Dict[str, Any]],
    flare_result: Optional[Dict[str, Any]] = None,
    diagnostic_result: Optional[Dict[str, Any]] = None,
    max_events: int = 50,
) -> str:
    """
    Create a timeline context document for LLM consumption.
    
    This document is prepended to the fused context when use_timeline=1.
    
    Args:
        events: List of timeline events
        flare_result: Optional flare precursor analysis result
        diagnostic_result: Optional diagnostic landscape result
        max_events: Maximum events to include in narrative
        
    Returns:
        Formatted context document string
    """
    sections = []
    
    # Header
    sections.append("## PATIENT TIMELINE CONTEXT")
    sections.append(f"Analysis timestamp: {datetime.now(timezone.utc).isoformat()}")
    sections.append(f"Total events analyzed: {len(events)}")
    sections.append("")
    
    # Event summary by type
    event_counts = {}
    for event in events:
        event_type = event.get("event_type", "unknown")
        event_counts[event_type] = event_counts.get(event_type, 0) + 1
    
    sections.append("### Event Distribution")
    for event_type, count in sorted(event_counts.items()):
        sections.append(f"- {event_type}: {count} events")
    sections.append("")
    
    # Recent events narrative
    sections.append("### Recent Timeline Events")
    sorted_events = sorted(
        events,
        key=lambda x: x.get("ts") or "",
        reverse=True,
    )[:max_events]
    
    for event in sorted_events:
        ts = event.get("ts")
        if isinstance(ts, datetime):
            ts_str = ts.strftime("%Y-%m-%d")
        elif ts:
            ts_str = str(ts)[:10]
        else:
            ts_str = "Unknown date"
        
        event_type = event.get("event_type", "unknown")
        text = (event.get("text") or "")[:200]
        
        sections.append(f"- [{ts_str}] {event_type.upper()}: {text}")
    sections.append("")
    
    # Flare analysis section
    if flare_result:
        sections.append("### Flare Precursor Analysis")
        
        likelihood = flare_result.get("flare_likelihood", {})
        level = likelihood.get("level", "unknown")
        explanation = likelihood.get("explanation", "")
        
        sections.append(f"Flare risk pattern: {level}")
        sections.append(f"Interpretation: {explanation}")
        
        precursors = flare_result.get("precursors", [])
        if precursors:
            sections.append("Observed precursor patterns:")
            for i, precursor in enumerate(precursors):
                score = flare_result.get("scores", [])[i] if i < len(flare_result.get("scores", [])) else 0
                sections.append(f"- {precursor.get('type', 'unknown')}: score {score:.2f}")
        sections.append("")
    
    # Diagnostic landscape section
    if diagnostic_result:
        sections.append("### Probabilistic Pattern Analysis")
        sections.append("NOTE: These are pattern similarities, NOT diagnoses.")
        sections.append("")
        
        probs = diagnostic_result.get("diagnostic_probabilities", {})
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)
        
        for condition, prob in sorted_probs:
            sections.append(f"- {condition}: {prob:.1%} pattern similarity")
        
        drivers = diagnostic_result.get("drivers", [])
        if drivers:
            sections.append("")
            sections.append("Key pattern drivers:")
            for driver in drivers[:5]:
                sections.append(f"- {driver}")
        sections.append("")
    
    # Regulatory notice
    sections.append("### IMPORTANT NOTICE")
    sections.append("This analysis provides pattern-based observations only.")
    sections.append("It does NOT constitute a medical diagnosis.")
    sections.append("All probabilities are estimates based on pattern similarity.")
    sections.append("")
    
    return "\n".join(sections)


def create_event_narrative(event: Dict[str, Any]) -> str:
    """
    Create a narrative string from a single event.
    
    Args:
        event: Timeline event dictionary
        
    Returns:
        Narrative string
    """
    parts = []
    
    ts = event.get("ts")
    if isinstance(ts, datetime):
        parts.append(ts.strftime("%Y-%m-%d"))
    elif ts:
        parts.append(str(ts)[:10])
    
    event_type = event.get("event_type", "unknown")
    parts.append(f"[{event_type.upper()}]")
    
    # Add structured data summary
    structured = event.get("structured", {})
    if event_type == "lab":
        test = structured.get("test_name", "")
        value = structured.get("value", "")
        flag = structured.get("flag", "")
        if test:
            parts.append(f"{test}: {value} ({flag})")
    elif event_type == "symptom":
        symptom = structured.get("primary_symptom", "")
        severity = structured.get("severity", "")
        if symptom:
            parts.append(f"{symptom} - {severity}")
    elif event_type == "medication":
        drug = structured.get("drug", "")
        changes = structured.get("changes", "")
        if drug:
            parts.append(f"{drug} {changes}")
    
    # Add text if no structured summary
    if len(parts) <= 2:
        text = (event.get("text") or "")[:100]
        if text:
            parts.append(text)
    
    return " ".join(parts)


# ============================================================================
# Context Fusion
# ============================================================================

def fuse_timeline_context(
    events: List[Dict[str, Any]],
    flare_result: Optional[Dict[str, Any]] = None,
    diagnostic_result: Optional[Dict[str, Any]] = None,
    rag_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Fuse timeline context with RAG content.
    
    Args:
        events: List of timeline events
        flare_result: Optional flare precursor analysis result
        diagnostic_result: Optional diagnostic landscape result
        rag_context: Optional RAG-retrieved context
        
    Returns:
        Fused context dictionary
    """
    # Create timeline context document
    timeline_doc = create_timeline_context_doc(
        events=events,
        flare_result=flare_result,
        diagnostic_result=diagnostic_result,
    )
    
    # Build fused context
    fused = {
        "timeline_context": timeline_doc,
        "event_count": len(events),
        "has_flare_analysis": flare_result is not None,
        "has_diagnostic_analysis": diagnostic_result is not None,
        "has_rag_context": rag_context is not None,
        "fusion_timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Add RAG context if provided
    if rag_context:
        fused["rag_context"] = rag_context
        fused["combined_context"] = f"{timeline_doc}\n\n## MEDICAL KNOWLEDGE CONTEXT\n{rag_context}"
    else:
        fused["combined_context"] = timeline_doc
    
    # Add summary statistics
    fused["summary"] = {
        "total_events": len(events),
        "event_types": _count_event_types(events),
        "date_range": _get_date_range(events),
    }
    
    # Add flare summary if available
    if flare_result:
        fused["flare_summary"] = {
            "likelihood_level": flare_result.get("flare_likelihood", {}).get("level"),
            "precursor_count": len(flare_result.get("precursors", [])),
            "top_precursors": [p.get("type") for p in flare_result.get("precursors", [])[:3]],
        }
    
    # Add diagnostic summary if available
    if diagnostic_result:
        probs = diagnostic_result.get("diagnostic_probabilities", {})
        top_pattern = max(probs.items(), key=lambda x: x[1]) if probs else (None, 0)
        fused["diagnostic_summary"] = {
            "top_pattern": top_pattern[0],
            "top_probability": top_pattern[1],
            "driver_count": len(diagnostic_result.get("drivers", [])),
        }
    
    return fused


def _count_event_types(events: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count events by type."""
    counts = {}
    for event in events:
        event_type = event.get("event_type", "unknown")
        counts[event_type] = counts.get(event_type, 0) + 1
    return counts


def _get_date_range(events: List[Dict[str, Any]]) -> Dict[str, Optional[str]]:
    """Get the date range of events."""
    dates = []
    for event in events:
        ts = event.get("ts")
        if ts:
            if isinstance(ts, datetime):
                dates.append(ts)
            else:
                try:
                    from dateutil import parser as date_parser
                    dates.append(date_parser.parse(str(ts)))
                except Exception:
                    pass
    
    if not dates:
        return {"earliest": None, "latest": None}
    
    return {
        "earliest": min(dates).isoformat(),
        "latest": max(dates).isoformat(),
    }


# ============================================================================
# Context Preparation for LLM
# ============================================================================

def prepare_llm_context(
    fused_context: Dict[str, Any],
    question: str,
    max_context_length: int = 8000,
) -> str:
    """
    Prepare the final context string for LLM consumption.
    
    Args:
        fused_context: Fused context dictionary
        question: The clinical question
        max_context_length: Maximum context length in characters
        
    Returns:
        Formatted context string for LLM
    """
    parts = []
    
    # Add combined context
    combined = fused_context.get("combined_context", "")
    if len(combined) > max_context_length:
        combined = combined[:max_context_length] + "\n[Context truncated...]"
    parts.append(combined)
    
    # Add question
    parts.append("\n## CLINICAL QUESTION")
    parts.append(question)
    
    # Add instructions
    parts.append("\n## INSTRUCTIONS")
    parts.append("Analyze the timeline context and answer the question.")
    parts.append("Use probabilistic language only.")
    parts.append("Do NOT provide diagnoses.")
    parts.append("Focus on pattern observations and explainability.")
    
    return "\n".join(parts)


def extract_key_signals(events: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
    """
    Extract the most important signals from timeline events.
    
    Args:
        events: List of timeline events
        limit: Maximum signals to return
        
    Returns:
        List of key signal dictionaries
    """
    signals = []
    
    # Prioritize abnormal labs
    for event in events:
        if event.get("event_type") == "lab":
            structured = event.get("structured", {})
            if structured.get("flag") in ("high", "low"):
                signals.append({
                    "type": "abnormal_lab",
                    "test": structured.get("test_name"),
                    "value": structured.get("value"),
                    "flag": structured.get("flag"),
                    "ts": event.get("ts"),
                })
    
    # Add severe symptoms
    for event in events:
        if event.get("event_type") == "symptom":
            structured = event.get("structured", {})
            if structured.get("severity") in ("moderate", "severe"):
                signals.append({
                    "type": "significant_symptom",
                    "symptom": structured.get("primary_symptom"),
                    "severity": structured.get("severity"),
                    "ts": event.get("ts"),
                })
    
    # Add medication changes
    for event in events:
        if event.get("event_type") == "medication":
            structured = event.get("structured", {})
            if structured.get("changes"):
                signals.append({
                    "type": "medication_change",
                    "drug": structured.get("drug"),
                    "change": structured.get("changes"),
                    "ts": event.get("ts"),
                })
    
    # Add flare events
    for event in events:
        if event.get("event_type") == "flare":
            signals.append({
                "type": "flare_event",
                "severity": event.get("structured", {}).get("severity"),
                "ts": event.get("ts"),
            })
    
    # Sort by timestamp (most recent first) and limit
    signals.sort(key=lambda x: x.get("ts") or "", reverse=True)
    return signals[:limit]
