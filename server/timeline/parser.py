"""
Timeline Parser Module
Location: server/timeline/parser.py
Version: v100 (Cipher + Devin Method)

This module handles raw document parsing including:
- Timestamp extraction (explicit or inferred)
- Event type identification
- Basic field extraction from various document formats

All parsed documents are passed to normalizer.py for final normalization.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from dateutil import parser as date_parser
from dateutil.parser import ParserError

logger = logging.getLogger(__name__)


# Event type patterns for classification
EVENT_TYPE_PATTERNS = {
    "lab": [
        r"\b(lab|test|result|panel|blood|urine|serum|plasma)\b",
        r"\b(CRP|ESR|WBC|RBC|ANA|RF|anti-CCP|complement|C3|C4)\b",
        r"\b(mg/dL|IU/mL|mm/hr|g/L|mmol/L)\b",
    ],
    "symptom": [
        r"\b(pain|ache|stiffness|swelling|fatigue|fever|rash)\b",
        r"\b(symptom|complaint|discomfort|tenderness)\b",
        r"\b(morning stiffness|joint pain|muscle pain)\b",
    ],
    "medication": [
        r"\b(medication|drug|prescription|dose|mg|tablet|capsule)\b",
        r"\b(started|stopped|discontinued|increased|decreased)\b",
        r"\b(methotrexate|prednisone|hydroxychloroquine|adalimumab|naproxen)\b",
    ],
    "imaging": [
        r"\b(x-ray|xray|MRI|CT|ultrasound|scan|imaging)\b",
        r"\b(impression|findings|radiology|radiograph)\b",
    ],
    "flare": [
        r"\b(flare|exacerbation|worsening|acute episode)\b",
        r"\b(disease activity|active disease)\b",
    ],
    "note": [
        r"\b(note|visit|appointment|consult|follow-up)\b",
        r"\b(assessment|plan|history)\b",
    ],
    "self_report": [
        r"\b(patient reports|self-reported|journal|diary)\b",
        r"\b(feeling|mood|energy level)\b",
    ],
}


def extract_timestamp(
    text: str,
    meta: Optional[Dict[str, Any]] = None,
    filename: Optional[str] = None,
) -> Tuple[Optional[datetime], str]:
    """
    Extract timestamp from text, metadata, or filename.
    
    Args:
        text: Document text content
        meta: Optional metadata dictionary
        filename: Optional filename for date inference
        
    Returns:
        Tuple of (datetime or None, inference_method)
        inference_method is one of: "explicit", "meta", "filename", "inferred", "none"
    """
    # Try explicit date patterns in text
    date_patterns = [
        r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})",  # ISO format
        r"(\d{4}-\d{2}-\d{2})",  # YYYY-MM-DD
        r"(\d{2}/\d{2}/\d{4})",  # MM/DD/YYYY
        r"(\d{2}-\d{2}-\d{4})",  # MM-DD-YYYY
        r"((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4})",  # Month DD, YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            try:
                dt = date_parser.parse(match.group(1))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt, "explicit"
            except (ParserError, ValueError):
                continue
    
    # Try metadata
    if meta:
        for key in ["date", "timestamp", "ts", "created_at", "event_date"]:
            if key in meta and meta[key]:
                try:
                    dt = date_parser.parse(str(meta[key]))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt, "meta"
                except (ParserError, ValueError):
                    continue
    
    # Try filename
    if filename:
        # Look for date patterns in filename
        for pattern in date_patterns[:3]:  # Use simpler patterns for filenames
            match = re.search(pattern, filename)
            if match:
                try:
                    dt = date_parser.parse(match.group(1))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    return dt, "filename"
                except (ParserError, ValueError):
                    continue
    
    # Fuzzy date parsing as last resort
    try:
        dt = date_parser.parse(text[:500], fuzzy=True)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt, "inferred"
    except (ParserError, ValueError):
        pass
    
    return None, "none"


def identify_event_type(text: str, meta: Optional[Dict[str, Any]] = None) -> str:
    """
    Identify the event type from text content.
    
    Args:
        text: Document text content
        meta: Optional metadata dictionary
        
    Returns:
        Event type string: lab|symptom|medication|flare|note|imaging|self_report
    """
    # Check metadata first
    if meta and "event_type" in meta:
        event_type = str(meta["event_type"]).lower()
        if event_type in EVENT_TYPE_PATTERNS:
            return event_type
    
    # Score each event type based on pattern matches
    scores: Dict[str, int] = {et: 0 for et in EVENT_TYPE_PATTERNS}
    text_lower = text.lower()
    
    for event_type, patterns in EVENT_TYPE_PATTERNS.items():
        for pattern in patterns:
            matches = re.findall(pattern, text_lower, re.IGNORECASE)
            scores[event_type] += len(matches)
    
    # Return highest scoring type, default to "note"
    max_score = max(scores.values())
    if max_score > 0:
        for event_type, score in scores.items():
            if score == max_score:
                return event_type
    
    return "note"


def extract_lab_fields(text: str) -> Dict[str, Any]:
    """
    Extract structured lab fields from text.
    
    Returns dict with: test_name, value, unit, reference_range, flag
    """
    result = {
        "test_name": None,
        "value": None,
        "unit": None,
        "reference_range": None,
        "flag": "unknown",
    }
    
    # Common lab test patterns
    lab_patterns = [
        # Pattern: Test Name: value unit (reference: range)
        r"(CRP|ESR|WBC|RBC|RF|ANA|anti-CCP|C3|C4|Hemoglobin|Hgb|Platelets?)[:\s]+(\d+\.?\d*)\s*(mg/dL|IU/mL|mm/hr|g/L|%)?",
        # Pattern: Test Name value unit
        r"(CRP|ESR|WBC|RBC|RF|ANA|anti-CCP|C3|C4)\s+(?:is\s+)?(\d+\.?\d*)\s*(mg/dL|IU/mL|mm/hr)?",
    ]
    
    for pattern in lab_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["test_name"] = match.group(1).upper()
            try:
                result["value"] = float(match.group(2))
            except (ValueError, TypeError):
                result["value"] = match.group(2)
            if len(match.groups()) > 2 and match.group(3):
                result["unit"] = match.group(3)
            break
    
    # Extract reference range
    ref_match = re.search(r"(?:reference|ref|normal)[:\s]*([<>]?\d+\.?\d*(?:\s*-\s*\d+\.?\d*)?)", text, re.IGNORECASE)
    if ref_match:
        result["reference_range"] = ref_match.group(1)
    
    # Determine flag
    flag_patterns = {
        "high": r"\b(high|elevated|above|increased|H)\b",
        "low": r"\b(low|decreased|below|reduced|L)\b",
        "normal": r"\b(normal|within range|WNL|N)\b",
    }
    for flag, pattern in flag_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            result["flag"] = flag
            break
    
    return result


def extract_symptom_fields(text: str) -> Dict[str, Any]:
    """
    Extract structured symptom fields from text.
    
    Returns dict with: primary_symptom, severity, duration, body_regions, modifiers
    """
    result = {
        "primary_symptom": None,
        "severity": None,
        "duration": None,
        "body_regions": [],
        "modifiers": [],
    }
    
    # Extract primary symptom
    symptom_patterns = [
        r"\b(joint pain|muscle pain|fatigue|stiffness|swelling|rash|fever|headache|nausea)\b",
        r"\b(morning stiffness|back pain|neck pain|knee pain|hand pain|wrist pain)\b",
    ]
    for pattern in symptom_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            result["primary_symptom"] = match.group(1).lower()
            break
    
    # Extract severity
    severity_patterns = {
        "mild": r"\b(mild|slight|minor|1-3/10|[123]/10)\b",
        "moderate": r"\b(moderate|medium|4-6/10|[456]/10)\b",
        "severe": r"\b(severe|intense|significant|7-10/10|[789]|10/10)\b",
    }
    for severity, pattern in severity_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            result["severity"] = severity
            break
    
    # Extract duration
    duration_match = re.search(r"(\d+\s*(?:days?|weeks?|months?|hours?|minutes?))", text, re.IGNORECASE)
    if duration_match:
        result["duration"] = duration_match.group(1)
    
    # Extract body regions
    body_regions = [
        "hands", "wrists", "knees", "ankles", "feet", "shoulders", "elbows",
        "hips", "back", "neck", "fingers", "toes", "joints", "muscles",
        "face", "cheeks", "scalp", "skin", "eyes", "mouth",
    ]
    for region in body_regions:
        if re.search(rf"\b{region}\b", text, re.IGNORECASE):
            result["body_regions"].append(region)
    
    # Extract modifiers
    modifiers = [
        "bilateral", "unilateral", "symmetric", "asymmetric",
        "intermittent", "constant", "progressive", "improving",
        "worse in morning", "worse with activity", "worse at rest",
    ]
    for modifier in modifiers:
        if re.search(rf"\b{modifier}\b", text, re.IGNORECASE):
            result["modifiers"].append(modifier)
    
    return result


def extract_medication_fields(text: str) -> Dict[str, Any]:
    """
    Extract structured medication fields from text.
    
    Returns dict with: drug, dose, frequency, changes, adherence_gaps
    """
    result = {
        "drug": None,
        "dose": None,
        "frequency": None,
        "changes": None,
        "adherence_gaps": None,
    }
    
    # Common medications
    medications = [
        "methotrexate", "prednisone", "hydroxychloroquine", "plaquenil",
        "adalimumab", "humira", "etanercept", "enbrel", "infliximab", "remicade",
        "naproxen", "ibuprofen", "meloxicam", "celecoxib",
        "mycophenolate", "azathioprine", "leflunomide", "sulfasalazine",
    ]
    
    for med in medications:
        if re.search(rf"\b{med}\b", text, re.IGNORECASE):
            result["drug"] = med.lower()
            break
    
    # Extract dose
    dose_match = re.search(r"(\d+\.?\d*\s*(?:mg|mcg|g|ml|units?))", text, re.IGNORECASE)
    if dose_match:
        result["dose"] = dose_match.group(1)
    
    # Extract frequency
    freq_patterns = {
        "daily": r"\b(daily|once daily|qd|every day)\b",
        "twice daily": r"\b(twice daily|bid|two times daily)\b",
        "weekly": r"\b(weekly|once weekly|every week)\b",
        "every 2 weeks": r"\b(every 2 weeks|biweekly|every two weeks)\b",
        "monthly": r"\b(monthly|once monthly|every month)\b",
    }
    for freq, pattern in freq_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            result["frequency"] = freq
            break
    
    # Extract changes
    change_patterns = {
        "started": r"\b(started|initiated|began|new)\b",
        "stopped": r"\b(stopped|discontinued|ceased|ended)\b",
        "increased": r"\b(increased|raised|upped)\b",
        "decreased": r"\b(decreased|reduced|lowered)\b",
    }
    for change, pattern in change_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            result["changes"] = change
            break
    
    # Extract adherence gaps
    gap_match = re.search(r"missed\s+(?:for\s+)?(\d+\s*(?:days?|weeks?|doses?))", text, re.IGNORECASE)
    if gap_match:
        result["adherence_gaps"] = gap_match.group(1)
    
    return result


def extract_imaging_fields(text: str) -> Dict[str, Any]:
    """
    Extract structured imaging fields from text.
    
    Returns dict with: modality, impression, key_findings
    """
    result = {
        "modality": None,
        "impression": None,
        "key_findings": [],
    }
    
    # Extract modality
    modalities = {
        "x-ray": r"\b(x-ray|xray|radiograph|plain film)\b",
        "MRI": r"\b(MRI|magnetic resonance)\b",
        "CT": r"\b(CT|computed tomography|CAT scan)\b",
        "ultrasound": r"\b(ultrasound|US|sonograph)\b",
    }
    for modality, pattern in modalities.items():
        if re.search(pattern, text, re.IGNORECASE):
            result["modality"] = modality
            break
    
    # Extract impression
    impression_match = re.search(r"impression[:\s]+(.+?)(?:\n|$)", text, re.IGNORECASE)
    if impression_match:
        result["impression"] = impression_match.group(1).strip()
    
    # Extract key findings
    findings_patterns = [
        r"\b(erosion|erosive changes)\b",
        r"\b(synovitis|synovial thickening)\b",
        r"\b(joint space narrowing)\b",
        r"\b(osteopenia|osteoporosis)\b",
        r"\b(soft tissue swelling)\b",
        r"\b(no acute findings)\b",
        r"\b(normal|unremarkable)\b",
    ]
    for pattern in findings_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result["key_findings"].append(match.group(1).lower())
    
    return result


def extract_flare_fields(text: str) -> Dict[str, Any]:
    """
    Extract structured flare fields from text.
    
    Returns dict with: severity, duration, affected_regions, trigger_pattern
    """
    result = {
        "severity": None,
        "duration": None,
        "affected_regions": [],
        "trigger_pattern": None,
    }
    
    # Extract severity
    severity_patterns = {
        "mild": r"\b(mild|minor|slight)\b",
        "moderate": r"\b(moderate|medium)\b",
        "severe": r"\b(severe|significant|major|intense)\b",
    }
    for severity, pattern in severity_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            result["severity"] = severity
            break
    
    # Extract duration
    duration_match = re.search(r"(\d+\s*(?:days?|weeks?|months?))", text, re.IGNORECASE)
    if duration_match:
        result["duration"] = duration_match.group(1)
    
    # Extract affected regions
    regions = [
        "hands", "wrists", "knees", "ankles", "feet", "shoulders",
        "elbows", "hips", "back", "neck", "fingers", "toes",
        "joints", "skin", "kidneys", "lungs", "heart",
    ]
    for region in regions:
        if re.search(rf"\b{region}\b", text, re.IGNORECASE):
            result["affected_regions"].append(region)
    
    # Extract trigger pattern
    triggers = [
        "medication gap", "missed doses", "stress", "infection",
        "sun exposure", "overexertion", "weather change",
    ]
    for trigger in triggers:
        if re.search(rf"\b{trigger}\b", text, re.IGNORECASE):
            result["trigger_pattern"] = trigger
            break
    
    return result


def parse_document(
    text: str,
    meta: Optional[Dict[str, Any]] = None,
    filename: Optional[str] = None,
    source: str = "patient_upload",
) -> Dict[str, Any]:
    """
    Parse a raw document into a structured event.
    
    This is the main entry point for document parsing.
    The output is passed to normalizer.py for final normalization.
    
    Args:
        text: Raw document text
        meta: Optional metadata dictionary
        filename: Optional filename for date inference
        source: Data source (patient_upload|EHR|synced_device|clinician_note)
        
    Returns:
        Parsed event dictionary ready for normalization
    """
    # Extract timestamp
    ts, ts_method = extract_timestamp(text, meta, filename)
    
    # Identify event type
    event_type = identify_event_type(text, meta)
    
    # Extract structured fields based on event type
    if event_type == "lab":
        structured = extract_lab_fields(text)
    elif event_type == "symptom":
        structured = extract_symptom_fields(text)
    elif event_type == "medication":
        structured = extract_medication_fields(text)
    elif event_type == "imaging":
        structured = extract_imaging_fields(text)
    elif event_type == "flare":
        structured = extract_flare_fields(text)
    else:
        structured = {}
    
    return {
        "ts": ts,
        "ts_inference_method": ts_method,
        "event_type": event_type,
        "source": source,
        "structured": structured,
        "text": text.strip(),
        "meta": meta or {},
    }
