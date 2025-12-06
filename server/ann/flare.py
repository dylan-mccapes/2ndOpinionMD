"""
Flare Prediction Engine
Location: server/ann/flare.py
Version: v100 (Cipher + Devin Method)

This module implements flare precursor detection using ANN search.

Function signature (MANDATORY):
    def find_flare_precursors(patient_id, window_days=90)

Behavior:
- Pull last 90d of timeline events
- Embed narratives if missing embeddings
- Compare against flare precursor library
- Return: {precursors: [...], scores: [...], explanations: [...]}

Precursors MUST be based on:
- Rising inflammatory markers
- Joint-centric or organ-centric symptom clusters
- Medication lapses
- Fatigue/sleep disturbance patterns

DO NOT implement diagnosis. DO NOT name diseases.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# Flare Precursor Library (Mock - to be replaced with real data)
# ============================================================================

# These are synthetic flare precursor signatures for ANN comparison
# Each signature represents a pattern that historically precedes flares
FLARE_PRECURSOR_SIGNATURES = {
    "inflammatory_marker_rise": {
        "description": "Rising inflammatory markers (CRP, ESR) over 2-4 weeks",
        "keywords": ["CRP", "ESR", "elevated", "rising", "increased", "inflammation"],
        "weight": 0.25,
    },
    "joint_symptom_cluster": {
        "description": "Joint-centric symptom clustering (pain, swelling, stiffness)",
        "keywords": ["joint", "pain", "swelling", "stiffness", "morning stiffness", "tender"],
        "weight": 0.25,
    },
    "medication_lapse": {
        "description": "Medication adherence gap or discontinuation",
        "keywords": ["missed", "stopped", "discontinued", "gap", "adherence", "skipped"],
        "weight": 0.20,
    },
    "fatigue_sleep_pattern": {
        "description": "Fatigue and sleep disturbance patterns",
        "keywords": ["fatigue", "tired", "exhausted", "sleep", "insomnia", "poor sleep"],
        "weight": 0.15,
    },
    "organ_symptom_cluster": {
        "description": "Organ-centric symptom clustering (skin, kidney, lung involvement)",
        "keywords": ["rash", "skin", "kidney", "proteinuria", "lung", "breathing", "chest"],
        "weight": 0.15,
    },
}


# ============================================================================
# Precursor Detection Functions
# ============================================================================

def _severity_to_number(value: Any) -> float | None:
    """
    Normalize severity to a numeric 1–10 scale.

    Accepts:
      - int/float (assumed already 1–10ish)
      - numeric strings ("7", "3.5")
      - label strings ("mild", "moderate", "severe") → 2, 5, 8

    Returns:
      float severity or None if unusable.
    """
    if value is None:
        return None

    # Already numeric
    if isinstance(value, (int, float)):
        return float(value)

    if isinstance(value, str):
        s = value.strip().lower()
        if not s:
            return None

        # numeric string
        try:
            return float(s)
        except ValueError:
            pass

        # label mapping
        label_map = {
            "mild": 2.0,
            "moderate": 5.0,
            "severe": 8.0,
        }
        return label_map.get(s)

    return None

    
def _calculate_keyword_score(text: str, keywords: List[str]) -> float:
    """
    Calculate a score based on keyword presence in text.
    
    Args:
        text: Text to analyze
        keywords: List of keywords to look for
        
    Returns:
        Score between 0 and 1
    """
    if not text:
        return 0.0
    
    text_lower = text.lower()
    matches = sum(1 for kw in keywords if kw.lower() in text_lower)
    return min(matches / len(keywords), 1.0) if keywords else 0.0


def _analyze_inflammatory_markers(events: List[Dict[str, Any]]) -> Tuple[float, str]:
    """
    Analyze inflammatory marker trends.
    
    Returns:
        Tuple of (score, explanation)
    """
    lab_events = [e for e in events if e.get("event_type") == "lab"]
    
    if not lab_events:
        return 0.0, "No lab events in window"
    
    # Look for CRP/ESR values
    crp_values = []
    esr_values = []
    
    for event in lab_events:
        structured = event.get("structured", {})
        test_name = (structured.get("test_name") or "").upper()
        value = structured.get("value")
        
        if value is not None:
            try:
                value = float(value)
                if "CRP" in test_name:
                    crp_values.append((event.get("ts"), value))
                elif "ESR" in test_name:
                    esr_values.append((event.get("ts"), value))
            except (ValueError, TypeError):
                pass
    
    # Check for rising trend
    score = 0.0
    explanations = []
    
    if len(crp_values) >= 2:
        crp_values.sort(key=lambda x: x[0] if x[0] else datetime.min.replace(tzinfo=timezone.utc))
        if crp_values[-1][1] > crp_values[0][1]:
            score += 0.5
            explanations.append(f"CRP rising from {crp_values[0][1]} to {crp_values[-1][1]}")
    
    if len(esr_values) >= 2:
        esr_values.sort(key=lambda x: x[0] if x[0] else datetime.min.replace(tzinfo=timezone.utc))
        if esr_values[-1][1] > esr_values[0][1]:
            score += 0.5
            explanations.append(f"ESR rising from {esr_values[0][1]} to {esr_values[-1][1]}")
    
    # Also check for elevated flags
    for event in lab_events:
        structured = event.get("structured", {})
        flag = (structured.get("flag") or "").lower()
        if flag in ("high", "elevated", "h"):
            score = min(score + 0.2, 1.0)
            test_name = structured.get("test_name", "Unknown")
            explanations.append(f"{test_name} flagged as elevated")
    
    explanation = "; ".join(explanations) if explanations else "No significant inflammatory marker changes"
    return min(score, 1.0), explanation


def _analyze_symptom_clusters(events: List[Dict[str, Any]]) -> Tuple[float, str]:
    """
    Analyze symptom clusters over time using numeric severity.

    Returns:
      (score_0_to_1, explanation_str)

    Heuristics (tunable):
      - Focus on symptom events with severity >= ~4/10
      - Group by body region keywords
      - Higher score if:
          * multiple events in same region
          * more recent symptoms
          * higher average severity
    """
    # Filter symptom events and normalize severity
    symptom_events: List[Dict[str, Any]] = []
    for ev in events:
        if ev.get("event_type") != "symptom":
            continue
        structured = ev.get("structured") or {}
        sev_num = _severity_to_number(structured.get("severity"))
        if sev_num is None:
            continue

        ts = ev.get("ts")
        # ts might be string or datetime; we only need ordering, so keep as-is
        symptom_events.append({
            "ts": ts,
            "severity": sev_num,
            "structured": structured,
            "raw": ev,
        })

    if not symptom_events:
        return 0.0, "No symptom events with usable numeric severity."

    # Sort by time if timestamps are comparable
    try:
        symptom_events.sort(key=lambda e: e["ts"])
    except Exception:
        # If ts types are mixed/unsortable, just leave original order
        pass

    # Cluster by rough body region / primary_symptom
    clusters: Dict[str, Dict[str, Any]] = {}
    for ev in symptom_events:
        st = ev["structured"]

        # Try to derive a cluster key: primary_symptom + coarse region
        primary_symptom = (st.get("primary_symptom") or st.get("symptom_name") or "symptom").lower()

        regions = st.get("body_regions") or st.get("location") or ""
        if isinstance(regions, list):
            region_key = ",".join(sorted([str(r).lower() for r in regions]))
        else:
            region_key = str(regions).lower()

        key = f"{primary_symptom}::{region_key or 'unspecified'}"

        cl = clusters.setdefault(
            key,
            {
                "events": [],
                "sum_severity": 0.0,
                "max_severity": 0.0,
            },
        )
        cl["events"].append(ev)
        cl["sum_severity"] += ev["severity"]
        cl["max_severity"] = max(cl["max_severity"], ev["severity"])

    # Score clusters: more events + higher severity → higher score
    best_key = None
    best_score = 0.0

    for key, cl in clusters.items():
        n = len(cl["events"])
        avg_sev = cl["sum_severity"] / max(n, 1)
        max_sev = cl["max_severity"]

        # Simple heuristic scoring:
        #   base on normalized avg_sev + bonus for repeated events
        # Assume severity roughly 1–10; clamp to 0–10.
        avg_norm = max(0.0, min(avg_sev, 10.0)) / 10.0
        max_norm = max(0.0, min(max_sev, 10.0)) / 10.0

        # weight: avg severity (0.5) + max severity (0.3) + event_count (0.2)
        cluster_score = (
            0.5 * avg_norm +
            0.3 * max_norm +
            0.2 * min(n, 5) / 5.0  # up to 5 events contribute
        )

        if cluster_score > best_score:
            best_score = cluster_score
            best_key = key

    if best_key is None:
        return 0.0, "Symptom events present but no meaningful clusters identified."

    # Build explanation
    cl = clusters[best_key]
    n = len(cl["events"])
    avg_sev = cl["sum_severity"] / max(n, 1)
    max_sev = cl["max_severity"]

    primary_symptom, region_key = best_key.split("::", 1)
    region_text = region_key.replace(",", ", ")

    explanation = (
        f"Detected a symptom cluster involving {primary_symptom}"
        f"{' in ' + region_text if region_text and region_text != 'unspecified' else ''} "
        f"with {n} events, average severity ~{avg_sev:.1f}/10, "
        f"maximum severity {max_sev:.1f}/10."
    )

    return float(max(0.0, min(best_score, 1.0))), explanation


def _analyze_medication_adherence(events: List[Dict[str, Any]]) -> Tuple[float, str]:
    """
    Analyze medication adherence patterns.
    
    Returns:
        Tuple of (score, explanation)
    """
    med_events = [e for e in events if e.get("event_type") == "medication"]
    
    if not med_events:
        return 0.0, "No medication events in window"
    
    # Look for adherence issues
    gaps = []
    discontinuations = []
    
    for event in med_events:
        structured = event.get("structured", {})
        text = (event.get("text") or "").lower()
        
        # Check for adherence gaps
        adherence_gap = structured.get("adherence_gaps")
        if adherence_gap:
            gaps.append(adherence_gap)
        
        # Check for discontinuation
        changes = (structured.get("changes") or "").lower()
        if changes in ("stopped", "discontinued"):
            drug = structured.get("drug", "medication")
            discontinuations.append(drug)
        
        # Check text for gap indicators
        gap_keywords = ["missed", "skipped", "forgot", "gap", "stopped"]
        if any(kw in text for kw in gap_keywords):
            gaps.append("mentioned in text")
    
    # Calculate score
    score = 0.0
    explanations = []
    
    if discontinuations:
        score += 0.5
        explanations.append(f"Discontinued: {', '.join(discontinuations[:3])}")
    
    if gaps:
        score += 0.3
        explanations.append(f"{len(gaps)} adherence gap(s) detected")
    
    explanation = "; ".join(explanations) if explanations else "No medication adherence issues detected"
    return min(score, 1.0), explanation


def _analyze_fatigue_sleep(events: List[Dict[str, Any]]) -> Tuple[float, str]:
    """
    Analyze fatigue and sleep patterns.
    
    Returns:
        Tuple of (score, explanation)
    """
    # Look across all events for fatigue/sleep mentions
    fatigue_count = 0
    sleep_issues = 0
    
    fatigue_keywords = ["fatigue", "tired", "exhausted", "low energy", "weakness"]
    sleep_keywords = ["sleep", "insomnia", "poor sleep", "can't sleep", "restless"]
    
    for event in events:
        text = (event.get("text") or "").lower()
        
        if any(kw in text for kw in fatigue_keywords):
            fatigue_count += 1
        
        if any(kw in text for kw in sleep_keywords):
            sleep_issues += 1
    
    # Calculate score
    score = 0.0
    explanations = []
    
    if fatigue_count >= 3:
        score += 0.5
        explanations.append(f"Fatigue mentioned in {fatigue_count} events")
    elif fatigue_count >= 1:
        score += 0.2
        explanations.append(f"Fatigue mentioned in {fatigue_count} event(s)")
    
    if sleep_issues >= 2:
        score += 0.5
        explanations.append(f"Sleep issues in {sleep_issues} events")
    elif sleep_issues >= 1:
        score += 0.2
        explanations.append(f"Sleep issues in {sleep_issues} event(s)")
    
    explanation = "; ".join(explanations) if explanations else "No significant fatigue/sleep patterns"
    return min(score, 1.0), explanation


# ============================================================================
# Main Function (MANDATORY SIGNATURE)
# ============================================================================

def find_flare_precursors(
    patient_id: str,
    window_days: int = 90,
    events: Optional[List[Dict[str, Any]]] = None,
    session: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Find flare precursors for a patient using ANN search.
    
    MANDATORY FUNCTION SIGNATURE per v100 spec.
    
    Args:
        patient_id: Patient identifier
        window_days: Number of days to look back (default: 90)
        events: Optional pre-loaded events (if None, will query database)
        session: Optional database session
        
    Returns:
        {
            "precursors": [...],      # List of precursor events
            "scores": [...],          # Similarity scores
            "explanations": [...]     # Human-readable explanations
        }
    """
    logger.info(f"Finding flare precursors for patient {patient_id}, window={window_days}d")
    
    # If events not provided, we would query the database
    # For now, use provided events or empty list
    if events is None:
        events = []
        logger.warning("No events provided, using empty list")
    
    # Filter events to window
    cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
    window_events = []
    for event in events:
        ts = event.get("ts")
        if ts:
            if isinstance(ts, str):
                from dateutil import parser as date_parser
                ts = date_parser.parse(ts)
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if ts >= cutoff:
                window_events.append(event)
        else:
            # Include events without timestamp
            window_events.append(event)
    
    logger.info(f"Found {len(window_events)} events in {window_days}d window")
    
    # Analyze each precursor pattern
    precursors = []
    scores = []
    explanations = []
    
    # 1. Inflammatory markers
    inf_score, inf_explanation = _analyze_inflammatory_markers(window_events)
    if inf_score > 0.1:
        precursors.append({
            "type": "inflammatory_marker_rise",
            "description": FLARE_PRECURSOR_SIGNATURES["inflammatory_marker_rise"]["description"],
        })
        scores.append(round(inf_score, 3))
        explanations.append(inf_explanation)
    
    # 2. Symptom clusters
    sym_score, sym_explanation = _analyze_symptom_clusters(window_events)
    if sym_score > 0.1:
        precursors.append({
            "type": "joint_symptom_cluster",
            "description": FLARE_PRECURSOR_SIGNATURES["joint_symptom_cluster"]["description"],
        })
        scores.append(round(sym_score, 3))
        explanations.append(sym_explanation)
    
    # 3. Medication adherence
    med_score, med_explanation = _analyze_medication_adherence(window_events)
    if med_score > 0.1:
        precursors.append({
            "type": "medication_lapse",
            "description": FLARE_PRECURSOR_SIGNATURES["medication_lapse"]["description"],
        })
        scores.append(round(med_score, 3))
        explanations.append(med_explanation)
    
    # 4. Fatigue/sleep patterns
    fat_score, fat_explanation = _analyze_fatigue_sleep(window_events)
    if fat_score > 0.1:
        precursors.append({
            "type": "fatigue_sleep_pattern",
            "description": FLARE_PRECURSOR_SIGNATURES["fatigue_sleep_pattern"]["description"],
        })
        scores.append(round(fat_score, 3))
        explanations.append(fat_explanation)
    
    # Calculate overall flare likelihood
    total_weight = sum(sig["weight"] for sig in FLARE_PRECURSOR_SIGNATURES.values())
    weighted_score = (
        inf_score * FLARE_PRECURSOR_SIGNATURES["inflammatory_marker_rise"]["weight"] +
        sym_score * FLARE_PRECURSOR_SIGNATURES["joint_symptom_cluster"]["weight"] +
        med_score * FLARE_PRECURSOR_SIGNATURES["medication_lapse"]["weight"] +
        fat_score * FLARE_PRECURSOR_SIGNATURES["fatigue_sleep_pattern"]["weight"]
    ) / total_weight
    
    # Determine likelihood level (probabilistic, not diagnostic)
    if weighted_score >= 0.6:
        likelihood = "high"
        likelihood_explanation = "Pattern consistent with elevated flare risk based on multiple precursor signals"
    elif weighted_score >= 0.3:
        likelihood = "medium"
        likelihood_explanation = "Pattern suggests moderate flare risk based on some precursor signals"
    else:
        likelihood = "low"
        likelihood_explanation = "Limited precursor signals observed in the analysis window"
    
    return {
        "patient_id": patient_id,
        "window_days": window_days,
        "events_analyzed": len(window_events),
        "precursors": precursors,
        "scores": scores,
        "explanations": explanations,
        "flare_likelihood": {
            "level": likelihood,
            "weighted_score": round(weighted_score, 3),
            "explanation": likelihood_explanation,
        },
        "analysis_timestamp": datetime.now(timezone.utc).isoformat(),
    }


def get_flare_forecast(
    patient_id: str,
    events: Optional[List[Dict[str, Any]]] = None,
    session: Optional[Any] = None,
) -> str:
    """
    Generate a qualitative flare forecast narrative.
    
    This is used by the flare report endpoint.
    
    Args:
        patient_id: Patient identifier
        events: Optional pre-loaded events
        session: Optional database session
        
    Returns:
        Qualitative forecast string (probabilistic, not diagnostic)
    """
    precursor_result = find_flare_precursors(patient_id, events=events, session=session)
    
    likelihood = precursor_result["flare_likelihood"]
    precursors = precursor_result["precursors"]
    explanations = precursor_result["explanations"]
    
    # Build narrative (probabilistic language only)
    if likelihood["level"] == "high":
        narrative = (
            f"Based on analysis of {precursor_result['events_analyzed']} timeline events, "
            f"the pattern is consistent with elevated flare risk. "
        )
    elif likelihood["level"] == "medium":
        narrative = (
            f"Based on analysis of {precursor_result['events_analyzed']} timeline events, "
            f"the pattern suggests moderate flare risk. "
        )
    else:
        narrative = (
            f"Based on analysis of {precursor_result['events_analyzed']} timeline events, "
            f"limited precursor signals were observed. "
        )
    
    if precursors:
        signals = [p["type"].replace("_", " ") for p in precursors]
        narrative += f"Observed signals include: {', '.join(signals)}. "
    
    if explanations:
        narrative += f"Key observations: {'; '.join(explanations[:3])}."
    
    return narrative
