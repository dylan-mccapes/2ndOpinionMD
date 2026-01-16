"""
EoH Validators Module
Location: server/eoh/validators.py
Version: v100 (Cipher + Devin Method)

This module provides safety validation for EoH responses.

REGULATORY GUARDRAILS (MANDATORY):
- NEVER provide a diagnosis
- ALWAYS use probabilistic, non-certain language
- NEVER output "you have X"
- ALWAYS produce explainability (drivers, not conclusions)
- AVOID clinical instructions, treatment guidance, or medical plans

Forbidden language patterns:
- "has [disease]"
- "diagnosis is"
- "should start"
- "should take"
- "will progress"
- "confirmed"

Allowed language:
- "pattern consistent with..."
- "...like"
- "probabilistic estimate"
- "observed signal includes..."
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ============================================================================
# SSE Event Order (MANDATORY)
# ============================================================================

SSE_EVENT_ORDER = [
    "timeline_loaded",
    "timeline_signals",
    "timeline_flare_features",
    "timeline_probabilistic_differential",
]


# ============================================================================
# Forbidden Language Patterns (MANDATORY)
# ============================================================================

FORBIDDEN_PATTERNS = [
    # Diagnostic statements
    r"\bhas\s+(?:rheumatoid\s+arthritis|lupus|psoriatic\s+arthritis|sjogren|mctd|vasculitis)\b",
    r"\bdiagnosis\s+is\b",
    r"\bdiagnosed\s+with\b",
    r"\byou\s+have\b",
    r"\bpatient\s+has\b",
    r"\bconfirmed\s+(?:diagnosis|case)\b",
    r"\bdefinitely\s+has\b",
    r"\bclearly\s+has\b",
    
    # Treatment instructions
    r"\bshould\s+start\b",
    r"\bshould\s+take\b",
    r"\bshould\s+begin\b",
    r"\bmust\s+take\b",
    r"\bneed\s+to\s+take\b",
    r"\bprescribe\b",
    r"\brecommend\s+starting\b",
    
    # Prognostic certainty
    r"\bwill\s+progress\b",
    r"\bwill\s+develop\b",
    r"\bwill\s+worsen\b",
    r"\bcertainly\s+will\b",
    r"\bdefinitely\s+will\b",
    
    # Absolute statements
    r"\bthis\s+is\s+(?:definitely|certainly|clearly)\b",
    r"\bno\s+doubt\b",
    r"\bwithout\s+question\b",
    r"\b100\s*%\s*(?:certain|sure|confident)\b",
]


# ============================================================================
# Allowed Language Patterns
# ============================================================================

ALLOWED_PATTERNS = [
    r"pattern\s+consistent\s+with",
    r"_like\b",  # e.g., ra_like, sle_like
    r"probabilistic\s+estimate",
    r"observed\s+signal",
    r"may\s+suggest",
    r"could\s+indicate",
    r"pattern\s+similarity",
    r"based\s+on\s+pattern",
]


# ============================================================================
# Validation Functions
# ============================================================================

def check_forbidden_language(text: str) -> List[Dict[str, Any]]:
    """
    Check text for forbidden language patterns.
    
    Args:
        text: Text to check
        
    Returns:
        List of violations found
    """
    violations = []
    text_lower = text.lower()
    
    for pattern in FORBIDDEN_PATTERNS:
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            violations.append({
                "pattern": pattern,
                "matched_text": match.group(),
                "position": match.start(),
                "severity": "high",
            })
    
    return violations


def check_diagnostic_language(text: str) -> List[Dict[str, Any]]:
    """
    Check for diagnostic language that should be avoided.
    
    Args:
        text: Text to check
        
    Returns:
        List of potential issues
    """
    issues = []
    text_lower = text.lower()
    
    # Check for disease names without "_like" suffix
    disease_names = [
        "rheumatoid arthritis",
        "lupus",
        "psoriatic arthritis",
        "sjogren",
        "mixed connective tissue disease",
        "vasculitis",
    ]
    
    for disease in disease_names:
        # Find mentions of disease
        pattern = rf"\b{disease}\b"
        matches = re.finditer(pattern, text_lower, re.IGNORECASE)
        for match in matches:
            # Check if it's in a safe context (e.g., "ra_like" or "pattern consistent with")
            context_start = max(0, match.start() - 50)
            context_end = min(len(text_lower), match.end() + 50)
            context = text_lower[context_start:context_end]
            
            safe_contexts = ["_like", "pattern", "consistent with", "similar to", "probability"]
            is_safe = any(safe in context for safe in safe_contexts)
            
            if not is_safe:
                issues.append({
                    "type": "disease_mention",
                    "disease": disease,
                    "context": context,
                    "severity": "medium",
                })
    
    return issues


def validate_probability_sum(probabilities: Dict[str, float], tolerance: float = 0.05) -> Tuple[bool, str]:
    """
    Validate that probabilities sum to approximately 1.0.
    
    Args:
        probabilities: Dictionary of condition -> probability
        tolerance: Acceptable deviation from 1.0
        
    Returns:
        Tuple of (is_valid, message)
    """
    total = sum(probabilities.values())
    
    if abs(total - 1.0) <= tolerance:
        return True, f"Probabilities sum to {total:.4f} (within tolerance)"
    else:
        return False, f"Probabilities sum to {total:.4f} (expected ~1.0)"


def validate_disease_names(probabilities: Dict[str, float]) -> Tuple[bool, List[str]]:
    """
    Validate that disease names use "_like" suffix.
    
    Args:
        probabilities: Dictionary of condition -> probability
        
    Returns:
        Tuple of (is_valid, list of invalid names)
    """
    invalid_names = []
    
    for name in probabilities.keys():
        if name != "other" and not name.endswith("_like"):
            invalid_names.append(name)
    
    return len(invalid_names) == 0, invalid_names


def validate_sse_event_order(events: List[str]) -> Tuple[bool, str]:
    """
    Validate that SSE events are emitted in the correct order.
    
    Args:
        events: List of event types in order emitted
        
    Returns:
        Tuple of (is_valid, message)
    """
    # Filter to only timeline events
    timeline_events = [e for e in events if e.startswith("timeline_")]
    
    # Check order
    expected_order = [e for e in SSE_EVENT_ORDER if e in timeline_events]
    
    if timeline_events == expected_order:
        return True, "SSE events in correct order"
    else:
        return False, f"SSE events out of order. Expected: {expected_order}, Got: {timeline_events}"


# ============================================================================
# Main Validation Function
# ============================================================================

def validate_response_safety(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate a response for regulatory safety compliance.
    
    Args:
        response: Response dictionary to validate
        
    Returns:
        Validation result with is_safe flag and violations
    """
    result = {
        "is_safe": True,
        "violations": [],
        "warnings": [],
        "checks_performed": [],
    }
    
    # Check all text fields for forbidden language
    text_fields = []
    
    def extract_text_fields(obj: Any, path: str = "") -> None:
        if isinstance(obj, str):
            text_fields.append((path, obj))
        elif isinstance(obj, dict):
            for key, value in obj.items():
                extract_text_fields(value, f"{path}.{key}" if path else key)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                extract_text_fields(item, f"{path}[{i}]")
    
    extract_text_fields(response)
    
    # Check each text field
    for path, text in text_fields:
        violations = check_forbidden_language(text)
        for v in violations:
            v["field"] = path
            result["violations"].append(v)
            result["is_safe"] = False
        
        issues = check_diagnostic_language(text)
        for issue in issues:
            issue["field"] = path
            result["warnings"].append(issue)
    
    result["checks_performed"].append("forbidden_language")
    result["checks_performed"].append("diagnostic_language")
    
    # Check probability sums if present
    if "diagnostic_probabilities" in response:
        probs = response["diagnostic_probabilities"]
        is_valid, message = validate_probability_sum(probs)
        if not is_valid:
            result["warnings"].append({
                "type": "probability_sum",
                "message": message,
            })
        result["checks_performed"].append("probability_sum")
        
        # Check disease names
        is_valid, invalid_names = validate_disease_names(probs)
        if not is_valid:
            result["violations"].append({
                "type": "invalid_disease_names",
                "names": invalid_names,
                "message": "Disease names must use '_like' suffix",
            })
            result["is_safe"] = False
        result["checks_performed"].append("disease_names")
    
    # Check nested diagnostic_landscape
    if "diagnostic_landscape" in response:
        landscape = response["diagnostic_landscape"]
        if "diagnostic_probabilities" in landscape:
            probs = landscape["diagnostic_probabilities"]
            is_valid, message = validate_probability_sum(probs)
            if not is_valid:
                result["warnings"].append({
                    "type": "probability_sum",
                    "message": message,
                    "location": "diagnostic_landscape",
                })
            
            is_valid, invalid_names = validate_disease_names(probs)
            if not is_valid:
                result["violations"].append({
                    "type": "invalid_disease_names",
                    "names": invalid_names,
                    "message": "Disease names must use '_like' suffix",
                    "location": "diagnostic_landscape",
                })
                result["is_safe"] = False
    
    return result


def sanitize_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize a response by removing or replacing forbidden content.
    
    Args:
        response: Response to sanitize
        
    Returns:
        Sanitized response
    """
    import copy
    sanitized = copy.deepcopy(response)
    
    def sanitize_text(text: str) -> str:
        """Replace forbidden patterns with safe alternatives."""
        result = text
        
        # Replace diagnostic statements
        result = re.sub(r"\bhas\s+(rheumatoid\s+arthritis|lupus|psoriatic\s+arthritis)", 
                       r"shows patterns consistent with \1-like presentation", result, flags=re.IGNORECASE)
        result = re.sub(r"\bdiagnosis\s+is\b", "pattern analysis suggests", result, flags=re.IGNORECASE)
        result = re.sub(r"\byou\s+have\b", "the pattern is consistent with", result, flags=re.IGNORECASE)
        result = re.sub(r"\bconfirmed\b", "observed", result, flags=re.IGNORECASE)
        
        # Replace treatment instructions
        result = re.sub(r"\bshould\s+start\b", "may consider discussing with provider", result, flags=re.IGNORECASE)
        result = re.sub(r"\bshould\s+take\b", "may benefit from discussing", result, flags=re.IGNORECASE)
        
        # Replace prognostic certainty
        result = re.sub(r"\bwill\s+progress\b", "may progress", result, flags=re.IGNORECASE)
        result = re.sub(r"\bwill\s+develop\b", "may develop", result, flags=re.IGNORECASE)
        
        return result
    
    def sanitize_obj(obj: Any) -> Any:
        if isinstance(obj, str):
            return sanitize_text(obj)
        elif isinstance(obj, dict):
            return {k: sanitize_obj(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize_obj(item) for item in obj]
        else:
            return obj
    
    return sanitize_obj(sanitized)


# ============================================================================
# Response Schema Validation
# ============================================================================

def validate_flare_report_schema(report: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate that a flare report has the required fields.
    
    Required fields:
    - flare_forecast
    - probabilistic_differential (or differential_landscape)
    - precursor_signals (or key_precursors)
    - contradictions
    - timeline_summary
    
    Args:
        report: Flare report dictionary
        
    Returns:
        Tuple of (is_valid, list of missing fields)
    """
    required_fields = [
        ("flare_forecast", ["flare_forecast"]),
        ("differential", ["probabilistic_differential", "differential_landscape", "diagnostic_landscape"]),
        ("precursors", ["precursor_signals", "key_precursors", "precursors"]),
        ("contradictions", ["contradictions"]),
        ("timeline_summary", ["timeline_summary"]),
    ]
    
    missing = []
    
    for field_name, alternatives in required_fields:
        found = any(alt in report for alt in alternatives)
        if not found:
            missing.append(field_name)
    
    return len(missing) == 0, missing


def validate_timeline_endpoint_schema(response: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate the timeline endpoint response schema.
    
    Args:
        response: Timeline endpoint response
        
    Returns:
        Tuple of (is_valid, list of issues)
    """
    issues = []
    
    # Check for events array
    if "events" not in response and "timeline" not in response:
        issues.append("Missing 'events' or 'timeline' field")
    
    # Check event structure
    events = response.get("events") or response.get("timeline") or []
    if events:
        sample = events[0]
        required_event_fields = ["ts", "event_type", "source"]
        for field in required_event_fields:
            if field not in sample:
                issues.append(f"Event missing required field: {field}")
    
    return len(issues) == 0, issues
