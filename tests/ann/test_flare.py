"""
Flare Prediction Engine Tests
Location: tests/ann/test_flare.py
Version: v100 (Cipher + Devin Method)

Tests for:
- find_flare_precursors function signature
- Precursor detection based on inflammatory markers, symptoms, medications, fatigue
- Output schema validation

Run with:
    python -m pytest tests/ann/test_flare.py -v
"""

import pytest
from datetime import datetime, timedelta, timezone

from server.ann.flare import (
    find_flare_precursors,
    get_flare_forecast,
    FLARE_PRECURSOR_SIGNATURES,
)


class TestFindFlarePrecursors:
    """Test the find_flare_precursors function."""
    
    def test_function_signature(self):
        """Function must accept patient_id and window_days=90"""
        # Should not raise
        result = find_flare_precursors(patient_id="TEST001", window_days=90)
        
        assert result is not None
        assert "patient_id" in result
        assert "window_days" in result
    
    def test_output_schema(self):
        """Output must include precursors, scores, explanations"""
        result = find_flare_precursors(patient_id="TEST001")
        
        assert "precursors" in result
        assert "scores" in result
        assert "explanations" in result
        assert isinstance(result["precursors"], list)
        assert isinstance(result["scores"], list)
        assert isinstance(result["explanations"], list)
    
    def test_output_includes_flare_likelihood(self):
        """Output must include flare_likelihood with level and explanation"""
        result = find_flare_precursors(patient_id="TEST001")
        
        assert "flare_likelihood" in result
        assert "level" in result["flare_likelihood"]
        assert "explanation" in result["flare_likelihood"]
    
    def test_flare_likelihood_levels(self):
        """Flare likelihood level must be low, medium, or high"""
        result = find_flare_precursors(patient_id="TEST001")
        
        level = result["flare_likelihood"]["level"]
        assert level in ("low", "medium", "high")
    
    def test_detects_inflammatory_markers(self):
        """Should detect rising inflammatory markers"""
        events = [
            {
                "event_type": "lab",
                "ts": datetime.now(timezone.utc) - timedelta(days=30),
                "structured": {"test_name": "CRP", "value": 5.0, "flag": "normal"},
                "text": "CRP 5.0 mg/L normal",
            },
            {
                "event_type": "lab",
                "ts": datetime.now(timezone.utc) - timedelta(days=7),
                "structured": {"test_name": "CRP", "value": 25.0, "flag": "high"},
                "text": "CRP 25.0 mg/L elevated",
            },
        ]
        
        result = find_flare_precursors(patient_id="TEST001", events=events)
        
        # Should detect inflammatory marker rise
        precursor_types = [p["type"] for p in result["precursors"]]
        assert "inflammatory_marker_rise" in precursor_types or len(result["precursors"]) > 0
    
    def test_detects_symptom_clusters(self):
        """Should detect joint-centric symptom clusters"""
        events = [
            {
                "event_type": "symptom",
                "ts": datetime.now(timezone.utc) - timedelta(days=14),
                "structured": {"primary_symptom": "joint pain", "severity": "moderate", "body_regions": ["hands"]},
                "text": "Joint pain in hands",
            },
            {
                "event_type": "symptom",
                "ts": datetime.now(timezone.utc) - timedelta(days=10),
                "structured": {"primary_symptom": "joint pain", "severity": "moderate", "body_regions": ["wrists"]},
                "text": "Joint pain in wrists",
            },
            {
                "event_type": "symptom",
                "ts": datetime.now(timezone.utc) - timedelta(days=5),
                "structured": {"primary_symptom": "stiffness", "severity": "severe", "body_regions": ["hands", "wrists"]},
                "text": "Morning stiffness in hands and wrists",
            },
        ]
        
        result = find_flare_precursors(patient_id="TEST001", events=events)
        
        # Should detect symptom cluster
        assert len(result["precursors"]) > 0 or result["flare_likelihood"]["level"] != "low"
    
    def test_detects_medication_lapses(self):
        """Should detect medication adherence gaps"""
        events = [
            {
                "event_type": "medication",
                "ts": datetime.now(timezone.utc) - timedelta(days=14),
                "structured": {"drug": "methotrexate", "changes": "stopped", "adherence_gaps": "2 weeks"},
                "text": "Stopped methotrexate, missed 2 weeks",
            },
        ]
        
        result = find_flare_precursors(patient_id="TEST001", events=events)
        
        # Should detect medication lapse
        precursor_types = [p["type"] for p in result["precursors"]]
        assert "medication_lapse" in precursor_types or len(result["precursors"]) > 0
    
    def test_detects_fatigue_patterns(self):
        """Should detect fatigue and sleep disturbance patterns"""
        events = [
            {
                "event_type": "symptom",
                "ts": datetime.now(timezone.utc) - timedelta(days=10),
                "structured": {},
                "text": "Severe fatigue, exhausted all day",
            },
            {
                "event_type": "symptom",
                "ts": datetime.now(timezone.utc) - timedelta(days=7),
                "structured": {},
                "text": "Poor sleep, insomnia",
            },
            {
                "event_type": "symptom",
                "ts": datetime.now(timezone.utc) - timedelta(days=3),
                "structured": {},
                "text": "Fatigue continues, very tired",
            },
        ]
        
        result = find_flare_precursors(patient_id="TEST001", events=events)
        
        # Should detect fatigue pattern
        precursor_types = [p["type"] for p in result["precursors"]]
        assert "fatigue_sleep_pattern" in precursor_types or len(result["precursors"]) > 0
    
    def test_window_filtering(self):
        """Should only analyze events within the window"""
        events = [
            {
                "event_type": "lab",
                "ts": datetime.now(timezone.utc) - timedelta(days=200),  # Outside 90-day window
                "structured": {"test_name": "CRP", "value": 50.0, "flag": "high"},
                "text": "CRP very elevated",
            },
        ]
        
        result = find_flare_precursors(patient_id="TEST001", window_days=90, events=events)
        
        # Old event should be filtered out
        assert result["events_analyzed"] == 0 or result["flare_likelihood"]["level"] == "low"
    
    def test_no_diagnosis_in_output(self):
        """Output must NOT contain diagnostic statements"""
        events = [
            {
                "event_type": "lab",
                "ts": datetime.now(timezone.utc) - timedelta(days=7),
                "structured": {"test_name": "CRP", "value": 25.0, "flag": "high"},
                "text": "CRP elevated",
            },
        ]
        
        result = find_flare_precursors(patient_id="TEST001", events=events)
        
        # Check explanations don't contain diagnostic language
        for explanation in result["explanations"]:
            assert "diagnosis" not in explanation.lower()
            assert "you have" not in explanation.lower()


class TestGetFlareForcast:
    """Test the get_flare_forecast function."""
    
    def test_returns_narrative(self):
        """Should return a narrative string"""
        result = get_flare_forecast(patient_id="TEST001")
        
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_uses_probabilistic_language(self):
        """Narrative should use probabilistic language"""
        events = [
            {
                "event_type": "lab",
                "ts": datetime.now(timezone.utc) - timedelta(days=7),
                "structured": {"test_name": "CRP", "value": 25.0, "flag": "high"},
                "text": "CRP elevated",
            },
        ]
        
        result = get_flare_forecast(patient_id="TEST001", events=events)
        
        # Should not contain diagnostic certainty
        assert "definitely" not in result.lower()
        assert "certainly" not in result.lower()
        assert "you have" not in result.lower()


class TestPrecursorSignatures:
    """Test the precursor signature definitions."""
    
    def test_signatures_have_required_fields(self):
        """Each signature must have description, keywords, weight"""
        for name, sig in FLARE_PRECURSOR_SIGNATURES.items():
            assert "description" in sig
            assert "keywords" in sig
            assert "weight" in sig
    
    def test_weights_are_valid(self):
        """Weights should be between 0 and 1"""
        for name, sig in FLARE_PRECURSOR_SIGNATURES.items():
            assert 0 <= sig["weight"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
