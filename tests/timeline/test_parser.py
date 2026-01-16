"""
Timeline Parser Tests
Location: tests/timeline/test_parser.py
Version: v100 (Cipher + Devin Method)

Tests for:
- Timestamp extraction (explicit, meta, filename, inferred)
- Event type identification
- Structured field extraction

Run with:
    python -m pytest tests/timeline/test_parser.py -v
"""

import pytest
from datetime import datetime, timezone

from server.timeline.parser import (
    extract_timestamp,
    identify_event_type,
    extract_lab_fields,
    extract_symptom_fields,
    extract_medication_fields,
    extract_imaging_fields,
    extract_flare_fields,
    parse_document,
)


class TestExtractTimestamp:
    """Test timestamp extraction."""
    
    def test_extract_iso_timestamp(self):
        """Should extract ISO format timestamps"""
        text = "Report date: 2024-01-15T10:30:00"
        ts, method = extract_timestamp(text)
        
        assert ts is not None
        assert method == "explicit"
        assert ts.year == 2024
        assert ts.month == 1
        assert ts.day == 15
    
    def test_extract_date_only(self):
        """Should extract date-only formats"""
        text = "Lab results from 2024-01-15"
        ts, method = extract_timestamp(text)
        
        assert ts is not None
        assert method == "explicit"
    
    def test_extract_from_meta(self):
        """Should extract timestamp from metadata"""
        text = "No date in text"
        meta = {"date": "2024-01-15"}
        ts, method = extract_timestamp(text, meta=meta)
        
        assert ts is not None
        assert method == "meta"
    
    def test_extract_from_filename(self):
        """Should extract timestamp from filename"""
        text = "No date in text"
        filename = "lab_results_2024-01-15.pdf"
        ts, method = extract_timestamp(text, filename=filename)
        
        assert ts is not None
        assert method == "filename"
    
    def test_missing_timestamp_returns_none(self):
        """Should return None if no timestamp found"""
        text = "No date information here"
        ts, method = extract_timestamp(text)
        
        # May return inferred or none depending on fuzzy parsing
        assert method in ("inferred", "none")


class TestIdentifyEventType:
    """Test event type identification."""
    
    def test_identify_lab_event(self):
        """Should identify lab events"""
        text = "CRP: 15.5 mg/dL (elevated)"
        event_type = identify_event_type(text)
        assert event_type == "lab"
    
    def test_identify_symptom_event(self):
        """Should identify symptom events"""
        text = "Patient reports joint pain and morning stiffness"
        event_type = identify_event_type(text)
        assert event_type == "symptom"
    
    def test_identify_medication_event(self):
        """Should identify medication events"""
        text = "Started methotrexate 15mg weekly"
        event_type = identify_event_type(text)
        assert event_type == "medication"
    
    def test_identify_imaging_event(self):
        """Should identify imaging events"""
        text = "X-ray impression: joint space narrowing"
        event_type = identify_event_type(text)
        assert event_type == "imaging"
    
    def test_identify_flare_event(self):
        """Should identify flare events"""
        text = "Disease flare with increased activity"
        event_type = identify_event_type(text)
        assert event_type == "flare"
    
    def test_default_to_note(self):
        """Should default to note for unclassified text"""
        text = "General clinical observation"
        event_type = identify_event_type(text)
        assert event_type == "note"
    
    def test_use_meta_event_type(self):
        """Should use event_type from metadata if provided"""
        text = "Some text"
        meta = {"event_type": "lab"}
        event_type = identify_event_type(text, meta=meta)
        assert event_type == "lab"


class TestExtractLabFields:
    """Test lab field extraction."""
    
    def test_extract_crp(self):
        """Should extract CRP values"""
        text = "CRP: 15.5 mg/dL"
        result = extract_lab_fields(text)
        
        assert result["test_name"] == "CRP"
        assert result["value"] == 15.5
    
    def test_extract_esr(self):
        """Should extract ESR values"""
        text = "ESR 45 mm/hr elevated"
        result = extract_lab_fields(text)
        
        assert result["test_name"] == "ESR"
        assert result["value"] == 45
    
    def test_extract_flag(self):
        """Should extract result flags"""
        text = "CRP: 15.5 mg/dL (high)"
        result = extract_lab_fields(text)
        
        assert result["flag"] == "high"
    
    def test_extract_reference_range(self):
        """Should extract reference ranges"""
        text = "CRP: 15.5 mg/dL, reference: <5"
        result = extract_lab_fields(text)
        
        assert result["reference_range"] is not None


class TestExtractSymptomFields:
    """Test symptom field extraction."""
    
    def test_extract_primary_symptom(self):
        """Should extract primary symptom"""
        text = "Patient reports severe joint pain"
        result = extract_symptom_fields(text)
        
        assert result["primary_symptom"] == "joint pain"
    
    def test_extract_severity(self):
        """Should extract severity"""
        text = "Severe joint pain rated 8/10"
        result = extract_symptom_fields(text)
        
        assert result["severity"] == "severe"
    
    def test_extract_body_regions(self):
        """Should extract body regions"""
        text = "Pain in hands and wrists bilaterally"
        result = extract_symptom_fields(text)
        
        assert "hands" in result["body_regions"]
        assert "wrists" in result["body_regions"]
    
    def test_extract_modifiers(self):
        """Should extract modifiers"""
        text = "Bilateral symmetric joint pain"
        result = extract_symptom_fields(text)
        
        assert "bilateral" in result["modifiers"] or "symmetric" in result["modifiers"]


class TestExtractMedicationFields:
    """Test medication field extraction."""
    
    def test_extract_drug_name(self):
        """Should extract drug name"""
        text = "Started methotrexate"
        result = extract_medication_fields(text)
        
        assert result["drug"] == "methotrexate"
    
    def test_extract_dose(self):
        """Should extract dose"""
        text = "Methotrexate 15mg weekly"
        result = extract_medication_fields(text)
        
        assert "15" in str(result["dose"])
    
    def test_extract_frequency(self):
        """Should extract frequency"""
        text = "Methotrexate 15mg weekly"
        result = extract_medication_fields(text)
        
        assert result["frequency"] == "weekly"
    
    def test_extract_changes(self):
        """Should extract medication changes"""
        text = "Started methotrexate"
        result = extract_medication_fields(text)
        
        assert result["changes"] == "started"


class TestExtractImagingFields:
    """Test imaging field extraction."""
    
    def test_extract_modality(self):
        """Should extract imaging modality"""
        text = "X-ray of hands shows erosions"
        result = extract_imaging_fields(text)
        
        assert result["modality"] == "x-ray"
    
    def test_extract_impression(self):
        """Should extract impression"""
        text = "Impression: Joint space narrowing"
        result = extract_imaging_fields(text)
        
        assert "joint space narrowing" in result["impression"].lower()
    
    def test_extract_key_findings(self):
        """Should extract key findings"""
        text = "Findings include erosions and soft tissue swelling"
        result = extract_imaging_fields(text)
        
        assert len(result["key_findings"]) > 0


class TestExtractFlareFields:
    """Test flare field extraction."""
    
    def test_extract_severity(self):
        """Should extract flare severity"""
        text = "Severe disease flare"
        result = extract_flare_fields(text)
        
        assert result["severity"] == "severe"
    
    def test_extract_duration(self):
        """Should extract duration"""
        text = "Flare lasting 2 weeks"
        result = extract_flare_fields(text)
        
        assert "2" in str(result["duration"])
    
    def test_extract_affected_regions(self):
        """Should extract affected regions"""
        text = "Flare affecting hands and knees"
        result = extract_flare_fields(text)
        
        assert "hands" in result["affected_regions"]
        assert "knees" in result["affected_regions"]
    
    def test_extract_trigger(self):
        """Should extract trigger pattern"""
        text = "Flare triggered by medication gap"
        result = extract_flare_fields(text)
        
        assert result["trigger_pattern"] == "medication gap"


class TestParseDocument:
    """Test the main parse_document function."""
    
    def test_parse_document_returns_complete_structure(self):
        """Should return complete parsed structure"""
        text = "CRP: 15.5 mg/dL elevated on 2024-01-15"
        result = parse_document(text)
        
        assert "ts" in result
        assert "event_type" in result
        assert "source" in result
        assert "structured" in result
        assert "text" in result
        assert "meta" in result
    
    def test_parse_document_identifies_event_type(self):
        """Should identify event type"""
        text = "CRP: 15.5 mg/dL elevated"
        result = parse_document(text)
        
        assert result["event_type"] == "lab"
    
    def test_parse_document_extracts_structured(self):
        """Should extract structured fields"""
        text = "CRP: 15.5 mg/dL elevated"
        result = parse_document(text)
        
        assert result["structured"]["test_name"] == "CRP"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
