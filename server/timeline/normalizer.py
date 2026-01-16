"""
Timeline Normalizer Module
Location: server/timeline/normalizer.py
Version: v100 (Cipher + Devin Method)

This module enforces the exact normalization contracts for timeline events.
All events MUST be transformed into the required structure before storage.

NORMALIZATION CONTRACTS (MANDATORY):

LAB EVENTS:
structured MUST include: test_name, value, unit, reference_range, flag

SYMPTOM EVENTS:
structured MUST include: primary_symptom, severity, duration, body_regions, modifiers

MEDICATION EVENTS:
structured MUST include: drug, dose, frequency, changes, adherence_gaps

IMAGING EVENTS:
structured MUST include: modality, impression, key_findings

FLARE EVENTS:
structured MUST include: severity, duration, affected_regions, trigger_pattern

NOTES & OTHER:
structured = {}
text MUST be cleaned narrative.

If data is missing: represent with null or empty arrays, not omitted.
"""

import logging
import re
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator

logger = logging.getLogger(__name__)


# ============================================================================
# Enums for constrained values
# ============================================================================

class LabFlag(str, Enum):
    """Lab result flag values."""
    HIGH = "high"
    LOW = "low"
    NORMAL = "normal"
    UNKNOWN = "unknown"


class SymptomSeverity(str, Enum):
    """Symptom severity levels."""
    MILD = "mild"
    MODERATE = "moderate"
    SEVERE = "severe"


class EventType(str, Enum):
    """Timeline event types."""
    LAB = "lab"
    SYMPTOM = "symptom"
    MEDICATION = "medication"
    IMAGING = "imaging"
    FLARE = "flare"
    NOTE = "note"
    SELF_REPORT = "self_report"


class EventSource(str, Enum):
    """Timeline event sources."""
    PATIENT_UPLOAD = "patient_upload"
    EHR = "EHR"
    SYNCED_DEVICE = "synced_device"
    CLINICIAN_NOTE = "clinician_note"


# ============================================================================
# Normalized Structured Data Models (v100 Contract)
# ============================================================================

class NormalizedLab(BaseModel):
    """
    Normalized lab event structured data.
    
    MUST include: test_name, value, unit, reference_range, flag
    """
    test_name: Optional[str] = None
    value: Optional[float] = None
    unit: Optional[str] = None
    reference_range: Optional[str] = None
    flag: str = Field(default="unknown")
    
    @field_validator("flag")
    @classmethod
    def validate_flag(cls, v: str) -> str:
        """Ensure flag is one of: high, low, normal, unknown."""
        valid_flags = {"high", "low", "normal", "unknown"}
        if v.lower() in valid_flags:
            return v.lower()
        # Map common variations
        flag_map = {
            "h": "high", "elevated": "high", "above": "high", "increased": "high",
            "l": "low", "decreased": "low", "below": "low", "reduced": "low",
            "n": "normal", "wnl": "normal", "within range": "normal",
            "borderline": "unknown", "positive": "high", "negative": "normal",
        }
        return flag_map.get(v.lower(), "unknown")


class NormalizedSymptom(BaseModel):
    """
    Normalized symptom event structured data.
    
    MUST include: primary_symptom, severity, duration, body_regions, modifiers
    """
    primary_symptom: Optional[str] = None
    severity: Optional[str] = None  # mild, moderate, severe
    duration: Optional[str] = None
    body_regions: List[str] = Field(default_factory=list)
    modifiers: List[str] = Field(default_factory=list)
    
    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: Optional[str]) -> Optional[str]:
        """Ensure severity is one of: mild, moderate, severe, or None."""
        if v is None:
            return None
        valid = {"mild", "moderate", "severe"}
        if v.lower() in valid:
            return v.lower()
        # Map numeric severities (1-10 scale) to categories
        try:
            num = int(v)
            if num <= 3:
                return "mild"
            elif num <= 6:
                return "moderate"
            else:
                return "severe"
        except (ValueError, TypeError):
            pass
        # Map common variations
        severity_map = {
            "slight": "mild", "minor": "mild", "light": "mild",
            "medium": "moderate", "average": "moderate",
            "intense": "severe", "significant": "severe", "major": "severe",
        }
        return severity_map.get(v.lower(), None)


class NormalizedMedication(BaseModel):
    """
    Normalized medication event structured data.
    
    MUST include: drug, dose, frequency, changes, adherence_gaps
    """
    drug: Optional[str] = None
    dose: Optional[str] = None
    frequency: Optional[str] = None
    changes: Optional[str] = None  # started, stopped, increased, decreased
    adherence_gaps: Optional[str] = None


class NormalizedImaging(BaseModel):
    """
    Normalized imaging event structured data.
    
    MUST include: modality, impression, key_findings
    """
    modality: Optional[str] = None
    impression: Optional[str] = None
    key_findings: List[str] = Field(default_factory=list)


class NormalizedFlare(BaseModel):
    """
    Normalized flare event structured data.
    
    MUST include: severity, duration, affected_regions, trigger_pattern
    """
    severity: Optional[str] = None  # mild, moderate, severe
    duration: Optional[str] = None
    affected_regions: List[str] = Field(default_factory=list)
    trigger_pattern: Optional[str] = None
    
    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v: Optional[str]) -> Optional[str]:
        """Ensure severity is one of: mild, moderate, severe, or None."""
        if v is None:
            return None
        valid = {"mild", "moderate", "severe"}
        if v.lower() in valid:
            return v.lower()
        # Map numeric severities (1-10 scale) to categories
        try:
            num = int(v)
            if num <= 3:
                return "mild"
            elif num <= 6:
                return "moderate"
            else:
                return "severe"
        except (ValueError, TypeError):
            pass
        # Map common variations
        severity_map = {
            "slight": "mild", "minor": "mild",
            "medium": "moderate", "moderate-severe": "severe",
            "intense": "severe", "significant": "severe", "major": "severe",
        }
        return severity_map.get(v.lower(), None)


# ============================================================================
# Normalized Timeline Event
# ============================================================================

class NormalizedEvent(BaseModel):
    """
    Fully normalized timeline event ready for storage.
    
    This is the final output of the normalization process.
    """
    ts: datetime
    event_type: str
    source: str
    structured: Dict[str, Any]
    text: str
    meta: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# Normalization Functions
# ============================================================================

def clean_text(text: str) -> str:
    """
    Clean and normalize narrative text.
    
    - Remove excessive whitespace
    - Remove control characters
    - Normalize line endings
    """
    if not text:
        return ""
    
    # Remove control characters except newlines
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]", "", text)
    
    # Normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n", "\n\n", text)
    
    return text.strip()


def normalize_lab(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize lab event structured data to v100 contract.
    
    MUST include: test_name, value, unit, reference_range, flag
    """
    structured = parsed.get("structured", {})
    
    # Map from various field names to normalized names
    test_name = (
        structured.get("test_name") or
        structured.get("name") or
        structured.get("lab_name") or
        None
    )
    
    value = structured.get("value")
    if value is not None:
        try:
            value = float(value)
        except (ValueError, TypeError):
            value = None
    
    unit = structured.get("unit") or structured.get("units")
    
    reference_range = (
        structured.get("reference_range") or
        structured.get("ref_range") or
        structured.get("normal_range") or
        None
    )
    
    # Build reference range from low/high if not provided
    if not reference_range:
        ref_low = structured.get("reference_low")
        ref_high = structured.get("reference_high")
        if ref_low is not None and ref_high is not None:
            reference_range = f"{ref_low}-{ref_high}"
        elif ref_high is not None:
            reference_range = f"<{ref_high}"
        elif ref_low is not None:
            reference_range = f">{ref_low}"
    
    flag = structured.get("flag", "unknown")
    
    normalized = NormalizedLab(
        test_name=test_name,
        value=value,
        unit=unit,
        reference_range=reference_range,
        flag=flag,
    )
    
    return normalized.model_dump()


def normalize_symptom(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize symptom event structured data to v100 contract.
    
    MUST include: primary_symptom, severity, duration, body_regions, modifiers
    """
    structured = parsed.get("structured", {})
    
    primary_symptom = (
        structured.get("primary_symptom") or
        structured.get("symptom_name") or
        structured.get("symptom") or
        None
    )
    
    severity = structured.get("severity")
    if severity is not None:
        severity = str(severity)
    
    duration = structured.get("duration")
    
    body_regions = (
        structured.get("body_regions") or
        structured.get("location") or
        []
    )
    if isinstance(body_regions, str):
        body_regions = [body_regions]
    
    modifiers = (
        structured.get("modifiers") or
        structured.get("pattern") or
        []
    )
    if isinstance(modifiers, str):
        modifiers = [modifiers]
    
    # Add associated symptoms as modifiers
    associated = structured.get("associated_symptoms", [])
    if isinstance(associated, list):
        modifiers.extend(associated)
    
    normalized = NormalizedSymptom(
        primary_symptom=primary_symptom,
        severity=severity,
        duration=duration,
        body_regions=body_regions,
        modifiers=modifiers,
    )
    
    return normalized.model_dump()


def normalize_medication(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize medication event structured data to v100 contract.
    
    MUST include: drug, dose, frequency, changes, adherence_gaps
    """
    structured = parsed.get("structured", {})
    
    drug = (
        structured.get("drug") or
        structured.get("medication_name") or
        structured.get("medication") or
        None
    )
    
    dose = structured.get("dose")
    frequency = structured.get("frequency")
    
    changes = (
        structured.get("changes") or
        structured.get("action") or
        structured.get("status") or
        None
    )
    
    adherence_gaps = (
        structured.get("adherence_gaps") or
        structured.get("adherence_gap_days") or
        None
    )
    if adherence_gaps is not None:
        adherence_gaps = str(adherence_gaps)
    
    normalized = NormalizedMedication(
        drug=drug,
        dose=dose,
        frequency=frequency,
        changes=changes,
        adherence_gaps=adherence_gaps,
    )
    
    return normalized.model_dump()


def normalize_imaging(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize imaging event structured data to v100 contract.
    
    MUST include: modality, impression, key_findings
    """
    structured = parsed.get("structured", {})
    
    modality = structured.get("modality")
    impression = structured.get("impression")
    
    key_findings = structured.get("key_findings") or structured.get("findings") or []
    if isinstance(key_findings, str):
        key_findings = [key_findings]
    
    normalized = NormalizedImaging(
        modality=modality,
        impression=impression,
        key_findings=key_findings,
    )
    
    return normalized.model_dump()


def normalize_flare(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize flare event structured data to v100 contract.
    
    MUST include: severity, duration, affected_regions, trigger_pattern
    """
    structured = parsed.get("structured", {})
    
    severity = structured.get("severity")
    if severity is not None:
        severity = str(severity)
    
    duration = structured.get("duration") or structured.get("duration_days")
    if duration is not None:
        duration = str(duration)
        if duration.isdigit():
            duration = f"{duration} days"
    
    affected_regions = (
        structured.get("affected_regions") or
        structured.get("joints_involved") or
        structured.get("organ_involvement") or
        []
    )
    if isinstance(affected_regions, str):
        affected_regions = [affected_regions]
    
    trigger_pattern = (
        structured.get("trigger_pattern") or
        structured.get("trigger") or
        None
    )
    # Handle triggers list
    triggers = structured.get("triggers")
    if triggers and isinstance(triggers, list) and not trigger_pattern:
        trigger_pattern = triggers[0] if triggers else None
    
    normalized = NormalizedFlare(
        severity=severity,
        duration=duration,
        affected_regions=affected_regions,
        trigger_pattern=trigger_pattern,
    )
    
    return normalized.model_dump()


def normalize_event(parsed: Dict[str, Any]) -> NormalizedEvent:
    """
    Normalize a parsed event to the v100 contract.
    
    This is the main entry point for event normalization.
    
    Args:
        parsed: Parsed event from parser.py
        
    Returns:
        NormalizedEvent ready for storage
    """
    event_type = parsed.get("event_type", "note")
    
    # Normalize structured data based on event type
    if event_type == "lab":
        structured = normalize_lab(parsed)
    elif event_type == "symptom":
        structured = normalize_symptom(parsed)
    elif event_type == "medication":
        structured = normalize_medication(parsed)
    elif event_type == "imaging":
        structured = normalize_imaging(parsed)
    elif event_type == "flare":
        structured = normalize_flare(parsed)
    else:
        # Notes and other types have empty structured
        structured = {}
    
    # Clean narrative text
    text = clean_text(parsed.get("text", ""))
    
    # Handle timestamp
    ts = parsed.get("ts")
    if ts is None:
        ts = datetime.now(timezone.utc)
    elif isinstance(ts, str):
        from dateutil import parser as date_parser
        ts = date_parser.parse(ts)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    
    # Validate source
    source = parsed.get("source", "patient_upload")
    valid_sources = {"patient_upload", "EHR", "synced_device", "clinician_note"}
    if source not in valid_sources:
        source = "patient_upload"
    
    # Build meta with normalization info
    meta = parsed.get("meta", {})
    meta["ts_inference_method"] = parsed.get("ts_inference_method", "unknown")
    
    return NormalizedEvent(
        ts=ts,
        event_type=event_type,
        source=source,
        structured=structured,
        text=text,
        meta=meta,
    )


def normalize_batch(parsed_events: List[Dict[str, Any]]) -> List[NormalizedEvent]:
    """
    Normalize a batch of parsed events.
    
    Args:
        parsed_events: List of parsed events from parser.py
        
    Returns:
        List of NormalizedEvents ready for storage
    """
    normalized = []
    for parsed in parsed_events:
        try:
            event = normalize_event(parsed)
            normalized.append(event)
        except Exception as e:
            logger.error(f"Failed to normalize event: {e}")
            # Continue processing other events
            continue
    return normalized
