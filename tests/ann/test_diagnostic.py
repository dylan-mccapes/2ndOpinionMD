"""
Diagnostic Landscape Engine Tests
Location: tests/ann/test_diagnostic.py
Version: v100 (Cipher + Devin Method)

Tests for:
- Output schema validation
- Probability sum validation (~1.0)
- Disease names must use "_like" suffix
- No diagnostic statements

Run with:
    python -m pytest tests/ann/test_diagnostic.py -v
"""

import pytest
from datetime import datetime, timedelta, timezone

from server.ann.diagnostic import (
    estimate_diagnostic_landscape,
    get_probabilistic_differential,
    PATTERN_SIGNATURES,
)


class TestEstimateDiagnosticLandscape:
    """Test the estimate_diagnostic_landscape function."""
    
    def test_output_schema(self):
        """Output MUST follow exact schema with diagnostic_probabilities and drivers"""
        result = estimate_diagnostic_landscape(patient_id="TEST001")
        
        assert "diagnostic_probabilities" in result
        assert "drivers" in result
        assert isinstance(result["diagnostic_probabilities"], dict)
        assert isinstance(result["drivers"], list)
    
    def test_required_probability_keys(self):
        """diagnostic_probabilities MUST include all required keys"""
        result = estimate_diagnostic_landscape(patient_id="TEST001")
        
        required_keys = ["ra_like", "sle_like", "psa_like", "sjogren_like", "mctd_like", "other"]
        probs = result["diagnostic_probabilities"]
        
        for key in required_keys:
            assert key in probs, f"Missing required key: {key}"
    
    def test_probabilities_sum_to_one(self):
        """Values MUST sum to ~1.0"""
        result = estimate_diagnostic_landscape(patient_id="TEST001")
        
        probs = result["diagnostic_probabilities"]
        total = sum(probs.values())
        
        # Allow 5% tolerance
        assert abs(total - 1.0) <= 0.05, f"Probabilities sum to {total}, expected ~1.0"
    
    def test_disease_names_use_like_suffix(self):
        """Disease names MUST be '*_like' (except 'other')"""
        result = estimate_diagnostic_landscape(patient_id="TEST001")
        
        probs = result["diagnostic_probabilities"]
        
        for key in probs.keys():
            if key != "other":
                assert key.endswith("_like"), f"Disease name '{key}' must end with '_like'"
    
    def test_probabilities_are_floats(self):
        """All probability values must be floats"""
        result = estimate_diagnostic_landscape(patient_id="TEST001")
        
        probs = result["diagnostic_probabilities"]
        
        for key, value in probs.items():
            assert isinstance(value, (int, float)), f"Probability for '{key}' must be numeric"
    
    def test_probabilities_in_valid_range(self):
        """All probabilities must be between 0 and 1"""
        result = estimate_diagnostic_landscape(patient_id="TEST001")
        
        probs = result["diagnostic_probabilities"]
        
        for key, value in probs.items():
            assert 0 <= value <= 1, f"Probability for '{key}' must be between 0 and 1"
    
    def test_no_diagnostic_statements(self):
        """Output must NOT contain diagnostic statements"""
        events = [
            {
                "event_type": "lab",
                "ts": datetime.now(timezone.utc),
                "structured": {"test_name": "RF", "flag": "positive"},
                "text": "RF positive",
            },
        ]
        
        result = estimate_diagnostic_landscape(patient_id="TEST001", events=events)
        
        # Check drivers don't contain diagnostic language
        for driver in result["drivers"]:
            driver_lower = driver.lower()
            assert "diagnosis is" not in driver_lower
            assert "has rheumatoid" not in driver_lower
            assert "has lupus" not in driver_lower
            assert "confirmed" not in driver_lower
    
    def test_pattern_matching_with_events(self):
        """Should detect patterns from events"""
        events = [
            {
                "event_type": "lab",
                "ts": datetime.now(timezone.utc),
                "structured": {"test_name": "RF", "flag": "high"},
                "text": "RF positive, anti-CCP positive, elevated CRP",
            },
            {
                "event_type": "symptom",
                "ts": datetime.now(timezone.utc),
                "structured": {"primary_symptom": "joint pain", "body_regions": ["hands"]},
                "text": "Symmetric joint pain, morning stiffness, small joint involvement",
            },
        ]
        
        result = estimate_diagnostic_landscape(patient_id="TEST001", events=events)
        
        # Should have some drivers detected
        assert len(result["drivers"]) > 0 or result["diagnostic_probabilities"]["other"] < 1.0


class TestGetProbabilisticDifferential:
    """Test the get_probabilistic_differential function."""
    
    def test_returns_required_fields(self):
        """Should return probabilities, drivers, and narrative"""
        result = get_probabilistic_differential(patient_id="TEST001")
        
        assert "probabilities" in result
        assert "drivers" in result
        assert "narrative" in result
    
    def test_narrative_uses_probabilistic_language(self):
        """Narrative should use probabilistic language"""
        events = [
            {
                "event_type": "lab",
                "ts": datetime.now(timezone.utc),
                "structured": {"test_name": "RF", "flag": "high"},
                "text": "RF positive",
            },
        ]
        
        result = get_probabilistic_differential(patient_id="TEST001", events=events)
        
        narrative = result["narrative"].lower()
        
        # Should not contain diagnostic certainty
        assert "definitely" not in narrative
        assert "certainly" not in narrative
        assert "you have" not in narrative
        assert "diagnosis is" not in narrative
        
        # Should contain probabilistic language
        assert any(word in narrative for word in ["pattern", "probability", "estimate", "consistent", "like"])
    
    def test_narrative_mentions_top_pattern(self):
        """Narrative should mention the top pattern"""
        result = get_probabilistic_differential(patient_id="TEST001")
        
        narrative = result["narrative"].lower()
        
        # Should mention some pattern
        assert "_like" in narrative or "pattern" in narrative


class TestPatternSignatures:
    """Test the pattern signature definitions."""
    
    def test_signatures_have_required_fields(self):
        """Each signature must have description, lab_patterns, symptom_patterns, imaging_patterns, weight"""
        for name, sig in PATTERN_SIGNATURES.items():
            assert "description" in sig
            assert "lab_patterns" in sig
            assert "symptom_patterns" in sig
            assert "imaging_patterns" in sig
            assert "weight" in sig
    
    def test_all_signatures_use_like_suffix(self):
        """All signature names must use '_like' suffix"""
        for name in PATTERN_SIGNATURES.keys():
            assert name.endswith("_like"), f"Signature '{name}' must end with '_like'"
    
    def test_weights_are_valid(self):
        """Weights should be between 0 and 1"""
        for name, sig in PATTERN_SIGNATURES.items():
            assert 0 <= sig["weight"] <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
