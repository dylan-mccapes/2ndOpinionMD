"""
Diagnostic Landscape Engine
Location: server/ann/diagnostic.py
Version: v100 (Cipher + Devin Method)

This module implements the diagnostic landscape estimator using ANN search.

Output MUST follow EXACT schema:
{
    "diagnostic_probabilities": {
        "ra_like": float,
        "sle_like": float,
        "psa_like": float,
        "sjogren_like": float,
        "mctd_like": float,
        "other": float
    },
    "drivers": ["...", "..."]
}

Rules:
- Values MUST sum to ~1.0
- Disease names MUST be "*_like"
- NO diagnostic statements allowed

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
# Pattern Signatures for Autoimmune Conditions
# ============================================================================

# These are pattern signatures used for probabilistic matching
# NOT for diagnosis - only for pattern similarity estimation
PATTERN_SIGNATURES = {
    "ra_like": {
        "description": "Pattern consistent with rheumatoid arthritis-like presentation",
        "lab_patterns": ["RF positive", "anti-CCP positive", "elevated CRP", "elevated ESR"],
        "symptom_patterns": ["symmetric joint pain", "morning stiffness", "small joint involvement", "bilateral"],
        "imaging_patterns": ["erosions", "joint space narrowing", "synovitis"],
        "weight": 0.20,
    },
    "sle_like": {
        "description": "Pattern consistent with systemic lupus-like presentation",
        "lab_patterns": ["ANA positive", "anti-dsDNA", "low complement", "low C3", "low C4"],
        "symptom_patterns": ["malar rash", "photosensitivity", "oral ulcers", "fatigue", "joint pain"],
        "imaging_patterns": ["pleuritis", "pericarditis"],
        "weight": 0.20,
    },
    "psa_like": {
        "description": "Pattern consistent with psoriatic arthritis-like presentation",
        "lab_patterns": ["RF negative", "elevated CRP", "elevated ESR"],
        "symptom_patterns": ["asymmetric joint pain", "dactylitis", "enthesitis", "nail changes", "skin psoriasis"],
        "imaging_patterns": ["pencil-in-cup", "new bone formation"],
        "weight": 0.20,
    },
    "sjogren_like": {
        "description": "Pattern consistent with Sjogren's-like presentation",
        "lab_patterns": ["anti-SSA", "anti-SSB", "ANA positive", "RF positive"],
        "symptom_patterns": ["dry eyes", "dry mouth", "sicca", "fatigue", "joint pain"],
        "imaging_patterns": ["parotid enlargement"],
        "weight": 0.20,
    },
    "mctd_like": {
        "description": "Pattern consistent with mixed connective tissue disease-like presentation",
        "lab_patterns": ["anti-U1 RNP", "ANA positive", "elevated CRP"],
        "symptom_patterns": ["raynaud", "swollen hands", "myositis", "joint pain", "fatigue"],
        "imaging_patterns": ["interstitial lung disease"],
        "weight": 0.20,
    },
}


# ============================================================================
# Pattern Matching Functions
# ============================================================================

def _calculate_pattern_score(
    events: List[Dict[str, Any]],
    lab_patterns: List[str],
    symptom_patterns: List[str],
    imaging_patterns: List[str],
) -> tuple[float, List[str]]:
    """
    Calculate pattern match score for a condition signature.
    
    Args:
        events: List of timeline events
        lab_patterns: Lab patterns to look for
        symptom_patterns: Symptom patterns to look for
        imaging_patterns: Imaging patterns to look for
        
    Returns:
        Tuple of (score, list of matched drivers)
    """
    score = 0.0
    drivers = []
    
    # Combine all event text for pattern matching
    all_text = " ".join([
        (e.get("text") or "").lower() for e in events
    ])
    
    # Check lab patterns
    lab_matches = 0
    for pattern in lab_patterns:
        if pattern.lower() in all_text:
            lab_matches += 1
            drivers.append(f"Lab: {pattern}")
    if lab_patterns:
        score += (lab_matches / len(lab_patterns)) * 0.4
    
    # Check symptom patterns
    symptom_matches = 0
    for pattern in symptom_patterns:
        if pattern.lower() in all_text:
            symptom_matches += 1
            drivers.append(f"Symptom: {pattern}")
    if symptom_patterns:
        score += (symptom_matches / len(symptom_patterns)) * 0.4
    
    # Check imaging patterns
    imaging_matches = 0
    for pattern in imaging_patterns:
        if pattern.lower() in all_text:
            imaging_matches += 1
            drivers.append(f"Imaging: {pattern}")
    if imaging_patterns:
        score += (imaging_matches / len(imaging_patterns)) * 0.2
    
    # Also check structured data
    for event in events:
        structured = event.get("structured", {})
        event_type = event.get("event_type", "")
        
        if event_type == "lab":
            test_name = (structured.get("test_name") or "").upper()
            flag = (structured.get("flag") or "").lower()
            
            # Check for specific lab markers
            if "RF" in test_name and flag in ("high", "positive"):
                if "Lab: RF positive" not in drivers:
                    drivers.append("Lab: RF positive")
                    score += 0.05
            if "CCP" in test_name and flag in ("high", "positive"):
                if "Lab: anti-CCP positive" not in drivers:
                    drivers.append("Lab: anti-CCP positive")
                    score += 0.05
            if "ANA" in test_name and flag in ("high", "positive"):
                if "Lab: ANA positive" not in drivers:
                    drivers.append("Lab: ANA positive")
                    score += 0.05
            if "CRP" in test_name and flag == "high":
                if "Lab: elevated CRP" not in drivers:
                    drivers.append("Lab: elevated CRP")
                    score += 0.03
            if "ESR" in test_name and flag == "high":
                if "Lab: elevated ESR" not in drivers:
                    drivers.append("Lab: elevated ESR")
                    score += 0.03
    
    return min(score, 1.0), drivers


def _normalize_probabilities(raw_scores: Dict[str, float]) -> Dict[str, float]:
    """
    Normalize raw scores to probabilities that sum to ~1.0.
    
    Args:
        raw_scores: Dictionary of condition -> raw score
        
    Returns:
        Dictionary of condition -> probability (summing to ~1.0)
    """
    total = sum(raw_scores.values())
    
    if total == 0:
        # Equal distribution if no signals
        n = len(raw_scores)
        return {k: round(1.0 / n, 4) for k in raw_scores}
    
    # Normalize to sum to 1.0
    normalized = {}
    for condition, score in raw_scores.items():
        normalized[condition] = round(score / total, 4)
    
    # Ensure sum is exactly 1.0 by adjusting "other"
    current_sum = sum(normalized.values())
    if "other" in normalized:
        normalized["other"] = round(normalized["other"] + (1.0 - current_sum), 4)
    
    return normalized


# ============================================================================
# Main Function
# ============================================================================

def estimate_diagnostic_landscape(
    patient_id: str,
    events: Optional[List[Dict[str, Any]]] = None,
    session: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Estimate the diagnostic landscape for a patient.
    
    This function produces PROBABILISTIC estimates only.
    It does NOT provide diagnoses.
    
    Output follows EXACT v100 schema:
    {
        "diagnostic_probabilities": {
            "ra_like": float,
            "sle_like": float,
            "psa_like": float,
            "sjogren_like": float,
            "mctd_like": float,
            "other": float
        },
        "drivers": ["...", "..."]
    }
    
    Args:
        patient_id: Patient identifier
        events: Optional pre-loaded events
        session: Optional database session
        
    Returns:
        Diagnostic landscape with probabilities and drivers
    """
    logger.info(f"Estimating diagnostic landscape for patient {patient_id}")
    
    if events is None:
        events = []
        logger.warning("No events provided, using empty list")
    
    # Calculate pattern scores for each condition
    raw_scores = {}
    all_drivers = []
    
    for condition, signature in PATTERN_SIGNATURES.items():
        score, drivers = _calculate_pattern_score(
            events,
            signature["lab_patterns"],
            signature["symptom_patterns"],
            signature["imaging_patterns"],
        )
        raw_scores[condition] = score
        
        # Add drivers with condition prefix
        for driver in drivers:
            driver_with_context = f"{driver} (pattern consistent with {condition})"
            if driver_with_context not in all_drivers:
                all_drivers.append(driver)
    
    # Add "other" category for unmatched patterns
    raw_scores["other"] = 0.1  # Base probability for other conditions
    
    # Normalize to probabilities
    probabilities = _normalize_probabilities(raw_scores)
    
    # Select top drivers (most informative)
    # Remove duplicates and limit to top 10
    unique_drivers = []
    seen = set()
    for driver in all_drivers:
        driver_key = driver.split(" (")[0]  # Get base driver without context
        if driver_key not in seen:
            seen.add(driver_key)
            unique_drivers.append(driver)
    
    top_drivers = unique_drivers[:10]
    
    # If no drivers found, add generic observation
    if not top_drivers:
        top_drivers = ["Limited pattern signals in available timeline data"]
    
    return {
        "diagnostic_probabilities": {
            "ra_like": probabilities.get("ra_like", 0.0),
            "sle_like": probabilities.get("sle_like", 0.0),
            "psa_like": probabilities.get("psa_like", 0.0),
            "sjogren_like": probabilities.get("sjogren_like", 0.0),
            "mctd_like": probabilities.get("mctd_like", 0.0),
            "other": probabilities.get("other", 0.0),
        },
        "drivers": top_drivers,
    }


def get_probabilistic_differential(
    patient_id: str,
    events: Optional[List[Dict[str, Any]]] = None,
    session: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Get the probabilistic differential for the flare report.
    
    This is a wrapper around estimate_diagnostic_landscape
    that formats output for the flare report endpoint.
    
    Args:
        patient_id: Patient identifier
        events: Optional pre-loaded events
        session: Optional database session
        
    Returns:
        Probabilistic differential with narrative
    """
    landscape = estimate_diagnostic_landscape(patient_id, events, session)
    
    # Find top probability
    probs = landscape["diagnostic_probabilities"]
    top_condition = max(probs.items(), key=lambda x: x[1])
    
    # Build narrative (probabilistic language only)
    narrative = (
        f"Based on pattern analysis, the timeline shows signals most consistent with "
        f"{top_condition[0].replace('_', ' ')} patterns ({top_condition[1]:.1%} probability estimate). "
    )
    
    # Add secondary patterns if significant
    secondary = sorted(
        [(k, v) for k, v in probs.items() if k != top_condition[0] and v >= 0.15],
        key=lambda x: x[1],
        reverse=True,
    )
    if secondary:
        secondary_names = [f"{k.replace('_', ' ')} ({v:.1%})" for k, v in secondary[:2]]
        narrative += f"Secondary pattern signals include: {', '.join(secondary_names)}. "
    
    # Add drivers
    if landscape["drivers"]:
        narrative += f"Key observed signals: {'; '.join(landscape['drivers'][:5])}."
    
    return {
        "probabilities": landscape["diagnostic_probabilities"],
        "drivers": landscape["drivers"],
        "narrative": narrative,
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }
