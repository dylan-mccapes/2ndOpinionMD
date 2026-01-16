"""
Timeline Normalizer Tests
Location: tests/timeline/test_normalizer.py
Version: v100 (Cipher + Devin Method)

Tests for the normalization contracts:
- LAB: test_name, value, unit, reference_range, flag
- SYMPTOM: primary_symptom, severity, duration, body_regions, modifiers
- MEDICATION: drug, dose, frequency, changes, adherence_gaps
- IMAGING: modality, impression, key_findings
- FLARE: severity, duration, affected_regions, trigger_pattern

Run with:
    python -m pytest tests/timeline/test_normalizer.py -v
"""

import pytest
from datetime import datetime, timezone

from server.timeline.normalizer import (
    normalize_event,
    normalize_lab,
    normalize_symptom,
    normalize_medication,
    normalize_imaging,
    normalize_flare,
    clean_text,
    NormalizedLab,
    NormalizedSymptom,
    NormalizedMedication,
    NormalizedImaging,
    NormalizedFlare,
)


class TestNormalizedLab:
    """Test LAB normalization contract."""
    
    def test_lab_has_required_fields(self):
        """LAB structured MUST include: test_name, value, unit, reference_range, flag"""
        parsed = {
            "event_type": "lab",
            "structured": {
                "test_name": "CRP",
                "value": 15.5,
                "unit": "mg/L",
                "reference_range": "<5",
                "flag": "high",
            },
            "text": "CRP elevated at 15.5 mg/L",
        }
        
        result = normalize_lab(parsed)
        
        # All required fields must be present
        assert "test_name" in result
        assert "value" in result
        assert "unit" in result
        assert "reference_range" in result
        assert "flag" in result
    
    def test_lab_flag_validation(self):
        """Flag must be one of: high, low, normal, unknown"""
        valid_flags = ["high", "low", "normal", "unknown"]
        
        for flag in valid_flags:
            lab = NormalizedLab(flag=flag)
            assert lab.flag in valid_flags
    
    def test_lab_flag_mapping(self):
        """Common flag variations should be mapped correctly"""
        mappings = {
            "H": "high",
            "elevated": "high",
            "L": "low",
            "decreased": "low",
            "N": "normal",
            "WNL": "normal",
        }
        
        for input_flag, expected in mappings.items():
            lab = NormalizedLab(flag=input_flag)
            assert lab.flag == expected
    
    def test_lab_missing_fields_use_null(self):
        """Missing data should be represented with null, not omitted"""
        parsed = {
            "event_type": "lab",
            "structured": {},
            "text": "Lab results",
        }
        
        result = normalize_lab(parsed)
        
        # Fields should be present even if None
        assert "test_name" in result
        assert "value" in result
        assert "unit" in result
        assert "reference_range" in result
        assert "flag" in result


class TestNormalizedSymptom:
    """Test SYMPTOM normalization contract."""
    
    def test_symptom_has_required_fields(self):
        """SYMPTOM structured MUST include: primary_symptom, severity, duration, body_regions, modifiers"""
        parsed = {
            "event_type": "symptom",
            "structured": {
                "primary_symptom": "joint pain",
                "severity": "moderate",
                "duration": "2 weeks",
                "body_regions": ["hands", "wrists"],
                "modifiers": ["bilateral", "morning stiffness"],
            },
            "text": "Joint pain in hands and wrists",
        }
        
        result = normalize_symptom(parsed)
        
        assert "primary_symptom" in result
        assert "severity" in result
        assert "duration" in result
        assert "body_regions" in result
        assert "modifiers" in result
    
    def test_symptom_severity_validation(self):
        """Severity must be one of: mild, moderate, severe"""
        valid_severities = ["mild", "moderate", "severe"]
        
        for severity in valid_severities:
            symptom = NormalizedSymptom(severity=severity)
            assert symptom.severity in valid_severities
    
    def test_symptom_severity_numeric_mapping(self):
        """Numeric severities (1-10) should map to categories"""
        mappings = {
            "1": "mild",
            "3": "mild",
            "4": "moderate",
            "6": "moderate",
            "7": "severe",
            "10": "severe",
        }
        
        for input_val, expected in mappings.items():
            symptom = NormalizedSymptom(severity=input_val)
            assert symptom.severity == expected
    
    def test_symptom_body_regions_is_list(self):
        """body_regions must be a list"""
        symptom = NormalizedSymptom(body_regions=["hands"])
        assert isinstance(symptom.body_regions, list)
    
    def test_symptom_modifiers_is_list(self):
        """modifiers must be a list"""
        symptom = NormalizedSymptom(modifiers=["bilateral"])
        assert isinstance(symptom.modifiers, list)


class TestNormalizedMedication:
    """Test MEDICATION normalization contract."""
    
    def test_medication_has_required_fields(self):
        """MEDICATION structured MUST include: drug, dose, frequency, changes, adherence_gaps"""
        parsed = {
            "event_type": "medication",
            "structured": {
                "drug": "methotrexate",
                "dose": "15mg",
                "frequency": "weekly",
                "changes": "started",
                "adherence_gaps": None,
            },
            "text": "Started methotrexate 15mg weekly",
        }
        
        result = normalize_medication(parsed)
        
        assert "drug" in result
        assert "dose" in result
        assert "frequency" in result
        assert "changes" in result
        assert "adherence_gaps" in result


class TestNormalizedImaging:
    """Test IMAGING normalization contract."""
    
    def test_imaging_has_required_fields(self):
        """IMAGING structured MUST include: modality, impression, key_findings"""
        parsed = {
            "event_type": "imaging",
            "structured": {
                "modality": "x-ray",
                "impression": "Joint space narrowing",
                "key_findings": ["erosions", "soft tissue swelling"],
            },
            "text": "X-ray shows joint space narrowing",
        }
        
        result = normalize_imaging(parsed)
        
        assert "modality" in result
        assert "impression" in result
        assert "key_findings" in result
    
    def test_imaging_key_findings_is_list(self):
        """key_findings must be a list"""
        imaging = NormalizedImaging(key_findings=["erosions"])
        assert isinstance(imaging.key_findings, list)


class TestNormalizedFlare:
    """Test FLARE normalization contract."""
    
    def test_flare_has_required_fields(self):
        """FLARE structured MUST include: severity, duration, affected_regions, trigger_pattern"""
        parsed = {
            "event_type": "flare",
            "structured": {
                "severity": "moderate",
                "duration": "2 weeks",
                "affected_regions": ["hands", "knees"],
                "trigger_pattern": "medication gap",
            },
            "text": "Flare affecting hands and knees",
        }
        
        result = normalize_flare(parsed)
        
        assert "severity" in result
        assert "duration" in result
        assert "affected_regions" in result
        assert "trigger_pattern" in result
    
    def test_flare_severity_validation(self):
        """Severity must be one of: mild, moderate, severe"""
        valid_severities = ["mild", "moderate", "severe"]
        
        for severity in valid_severities:
            flare = NormalizedFlare(severity=severity)
            assert flare.severity in valid_severities
    
    def test_flare_affected_regions_is_list(self):
        """affected_regions must be a list"""
        flare = NormalizedFlare(affected_regions=["hands"])
        assert isinstance(flare.affected_regions, list)


class TestNormalizeEvent:
    """Test the main normalize_event function."""
    
    def test_normalize_event_returns_normalized_event(self):
        """normalize_event should return a NormalizedEvent"""
        parsed = {
            "ts": datetime.now(timezone.utc),
            "event_type": "lab",
            "source": "EHR",
            "structured": {"test_name": "CRP"},
            "text": "CRP test",
            "meta": {},
        }
        
        result = normalize_event(parsed)
        
        assert hasattr(result, "ts")
        assert hasattr(result, "event_type")
        assert hasattr(result, "source")
        assert hasattr(result, "structured")
        assert hasattr(result, "text")
        assert hasattr(result, "meta")
    
    def test_normalize_event_handles_missing_timestamp(self):
        """Should use current time if timestamp is missing"""
        parsed = {
            "ts": None,
            "event_type": "note",
            "source": "patient_upload",
            "structured": {},
            "text": "Note text",
        }
        
        result = normalize_event(parsed)
        
        assert result.ts is not None
    
    def test_normalize_event_validates_source(self):
        """Source should be validated to allowed values"""
        parsed = {
            "ts": datetime.now(timezone.utc),
            "event_type": "note",
            "source": "invalid_source",
            "structured": {},
            "text": "Note text",
        }
        
        result = normalize_event(parsed)
        
        # Should default to patient_upload for invalid source
        assert result.source == "patient_upload"


class TestCleanText:
    """Test text cleaning function."""
    
    def test_clean_text_removes_control_characters(self):
        """Should remove control characters"""
        text = "Hello\x00World\x1f"
        result = clean_text(text)
        assert "\x00" not in result
        assert "\x1f" not in result
    
    def test_clean_text_normalizes_whitespace(self):
        """Should normalize excessive whitespace"""
        text = "Hello    World"
        result = clean_text(text)
        assert "    " not in result
    
    def test_clean_text_strips_edges(self):
        """Should strip leading/trailing whitespace"""
        text = "  Hello World  "
        result = clean_text(text)
        assert result == "Hello World"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
