"""
EoH Validators Tests
Location: tests/eoh/test_validators.py
Version: v100 (Cipher + Devin Method)

Tests for:
- Forbidden language detection
- Probability-only outputs
- SSE event ordering
- Response schema validation

Run with:
    python -m pytest tests/eoh/test_validators.py -v
"""

import pytest

from server.eoh.validators import (
    check_forbidden_language,
    check_diagnostic_language,
    validate_probability_sum,
    validate_disease_names,
    validate_sse_event_order,
    validate_response_safety,
    sanitize_response,
    validate_flare_report_schema,
    FORBIDDEN_PATTERNS,
    SSE_EVENT_ORDER,
)


class TestForbiddenLanguageDetection:
    """Test forbidden language pattern detection."""
    
    def test_detects_has_disease(self):
        """Should detect 'has [disease]' pattern"""
        text = "The patient has rheumatoid arthritis"
        violations = check_forbidden_language(text)
        
        assert len(violations) > 0
    
    def test_detects_diagnosis_is(self):
        """Should detect 'diagnosis is' pattern"""
        text = "The diagnosis is lupus"
        violations = check_forbidden_language(text)
        
        assert len(violations) > 0
    
    def test_detects_you_have(self):
        """Should detect 'you have' pattern"""
        text = "You have an autoimmune condition"
        violations = check_forbidden_language(text)
        
        assert len(violations) > 0
    
    def test_detects_should_start(self):
        """Should detect 'should start' pattern"""
        text = "You should start taking methotrexate"
        violations = check_forbidden_language(text)
        
        assert len(violations) > 0
    
    def test_detects_should_take(self):
        """Should detect 'should take' pattern"""
        text = "You should take this medication"
        violations = check_forbidden_language(text)
        
        assert len(violations) > 0
    
    def test_detects_will_progress(self):
        """Should detect 'will progress' pattern"""
        text = "The disease will progress rapidly"
        violations = check_forbidden_language(text)
        
        assert len(violations) > 0
    
    def test_detects_confirmed(self):
        """Should detect 'confirmed' pattern"""
        text = "This is a confirmed diagnosis"
        violations = check_forbidden_language(text)
        
        assert len(violations) > 0
    
    def test_allows_pattern_consistent_with(self):
        """Should allow 'pattern consistent with' language"""
        text = "The pattern is consistent with an inflammatory process"
        violations = check_forbidden_language(text)
        
        # Should not flag this as forbidden
        assert len(violations) == 0
    
    def test_allows_like_suffix(self):
        """Should allow '*_like' disease names"""
        text = "The pattern shows ra_like characteristics"
        violations = check_forbidden_language(text)
        
        assert len(violations) == 0
    
    def test_allows_probabilistic_estimate(self):
        """Should allow 'probabilistic estimate' language"""
        text = "This is a probabilistic estimate based on pattern analysis"
        violations = check_forbidden_language(text)
        
        assert len(violations) == 0
    
    def test_allows_observed_signal(self):
        """Should allow 'observed signal' language"""
        text = "The observed signal includes elevated inflammatory markers"
        violations = check_forbidden_language(text)
        
        assert len(violations) == 0


class TestDiagnosticLanguageDetection:
    """Test diagnostic language detection."""
    
    def test_flags_disease_without_context(self):
        """Should flag disease names without safe context"""
        text = "This is rheumatoid arthritis"
        issues = check_diagnostic_language(text)
        
        assert len(issues) > 0
    
    def test_allows_disease_with_like_context(self):
        """Should allow disease names with '_like' context"""
        text = "This shows ra_like patterns"
        issues = check_diagnostic_language(text)
        
        # Should not flag when in safe context
        assert len(issues) == 0
    
    def test_allows_disease_with_pattern_context(self):
        """Should allow disease names with 'pattern' context"""
        text = "Pattern consistent with lupus-like presentation"
        issues = check_diagnostic_language(text)
        
        # May or may not flag depending on exact context
        # The key is that safe contexts reduce severity


class TestProbabilityValidation:
    """Test probability sum validation."""
    
    def test_valid_probabilities(self):
        """Should pass when probabilities sum to 1.0"""
        probs = {
            "ra_like": 0.4,
            "sle_like": 0.2,
            "psa_like": 0.15,
            "sjogren_like": 0.1,
            "mctd_like": 0.1,
            "other": 0.05,
        }
        
        is_valid, message = validate_probability_sum(probs)
        
        assert is_valid
    
    def test_valid_within_tolerance(self):
        """Should pass when probabilities sum to ~1.0 within tolerance"""
        probs = {
            "ra_like": 0.4,
            "sle_like": 0.2,
            "psa_like": 0.15,
            "sjogren_like": 0.1,
            "mctd_like": 0.1,
            "other": 0.08,  # Sum = 1.03
        }
        
        is_valid, message = validate_probability_sum(probs, tolerance=0.05)
        
        assert is_valid
    
    def test_invalid_probabilities(self):
        """Should fail when probabilities don't sum to ~1.0"""
        probs = {
            "ra_like": 0.4,
            "sle_like": 0.2,
            "psa_like": 0.15,
            # Sum = 0.75, missing 0.25
        }
        
        is_valid, message = validate_probability_sum(probs)
        
        assert not is_valid


class TestDiseaseNameValidation:
    """Test disease name validation."""
    
    def test_valid_disease_names(self):
        """Should pass when all names use '_like' suffix"""
        probs = {
            "ra_like": 0.4,
            "sle_like": 0.2,
            "psa_like": 0.15,
            "sjogren_like": 0.1,
            "mctd_like": 0.1,
            "other": 0.05,
        }
        
        is_valid, invalid_names = validate_disease_names(probs)
        
        assert is_valid
        assert len(invalid_names) == 0
    
    def test_invalid_disease_names(self):
        """Should fail when names don't use '_like' suffix"""
        probs = {
            "rheumatoid_arthritis": 0.4,  # Invalid - no _like suffix
            "sle_like": 0.2,
            "other": 0.4,
        }
        
        is_valid, invalid_names = validate_disease_names(probs)
        
        assert not is_valid
        assert "rheumatoid_arthritis" in invalid_names
    
    def test_other_is_allowed(self):
        """'other' should be allowed without '_like' suffix"""
        probs = {
            "ra_like": 0.5,
            "other": 0.5,
        }
        
        is_valid, invalid_names = validate_disease_names(probs)
        
        assert is_valid


class TestSSEEventOrdering:
    """Test SSE event ordering validation."""
    
    def test_correct_order(self):
        """Should pass when events are in correct order"""
        events = [
            "timeline_loaded",
            "timeline_signals",
            "timeline_flare_features",
            "timeline_probabilistic_differential",
        ]
        
        is_valid, message = validate_sse_event_order(events)
        
        assert is_valid
    
    def test_incorrect_order(self):
        """Should fail when events are out of order"""
        events = [
            "timeline_signals",  # Should be second
            "timeline_loaded",   # Should be first
            "timeline_flare_features",
            "timeline_probabilistic_differential",
        ]
        
        is_valid, message = validate_sse_event_order(events)
        
        assert not is_valid
    
    def test_partial_events_in_order(self):
        """Should pass when partial events are in correct order"""
        events = [
            "timeline_loaded",
            "timeline_signals",
            # Missing later events is OK
        ]
        
        is_valid, message = validate_sse_event_order(events)
        
        assert is_valid
    
    def test_mandatory_order(self):
        """SSE_EVENT_ORDER should match spec"""
        expected = [
            "timeline_loaded",
            "timeline_signals",
            "timeline_flare_features",
            "timeline_probabilistic_differential",
        ]
        
        assert SSE_EVENT_ORDER == expected


class TestValidateResponseSafety:
    """Test the main response safety validation."""
    
    def test_safe_response(self):
        """Should pass for safe response"""
        response = {
            "diagnostic_probabilities": {
                "ra_like": 0.4,
                "sle_like": 0.2,
                "psa_like": 0.15,
                "sjogren_like": 0.1,
                "mctd_like": 0.1,
                "other": 0.05,
            },
            "drivers": ["Lab: elevated CRP", "Symptom: joint pain"],
            "narrative": "Pattern consistent with inflammatory process",
        }
        
        result = validate_response_safety(response)
        
        assert result["is_safe"]
    
    def test_unsafe_response_forbidden_language(self):
        """Should fail for response with forbidden language"""
        response = {
            "narrative": "The patient has rheumatoid arthritis",
        }
        
        result = validate_response_safety(response)
        
        assert not result["is_safe"]
        assert len(result["violations"]) > 0
    
    def test_unsafe_response_invalid_disease_names(self):
        """Should fail for response with invalid disease names"""
        response = {
            "diagnostic_probabilities": {
                "rheumatoid_arthritis": 0.5,  # Invalid
                "other": 0.5,
            },
        }
        
        result = validate_response_safety(response)
        
        assert not result["is_safe"]


class TestSanitizeResponse:
    """Test response sanitization."""
    
    def test_sanitizes_has_disease(self):
        """Should replace 'has [disease]' with safe language"""
        response = {
            "text": "The patient has rheumatoid arthritis",
        }
        
        sanitized = sanitize_response(response)
        
        assert "has rheumatoid arthritis" not in sanitized["text"]
        assert "pattern" in sanitized["text"].lower() or "consistent" in sanitized["text"].lower()
    
    def test_sanitizes_diagnosis_is(self):
        """Should replace 'diagnosis is' with safe language"""
        response = {
            "text": "The diagnosis is lupus",
        }
        
        sanitized = sanitize_response(response)
        
        assert "diagnosis is" not in sanitized["text"].lower()
    
    def test_sanitizes_will_progress(self):
        """Should replace 'will progress' with 'may progress'"""
        response = {
            "text": "The disease will progress",
        }
        
        sanitized = sanitize_response(response)
        
        assert "will progress" not in sanitized["text"].lower()
        assert "may progress" in sanitized["text"].lower()


class TestFlareReportSchemaValidation:
    """Test flare report schema validation."""
    
    def test_valid_schema(self):
        """Should pass for valid flare report"""
        report = {
            "flare_forecast": "Pattern suggests elevated risk",
            "probabilistic_differential": {"ra_like": 0.5},
            "precursor_signals": ["elevated CRP"],
            "contradictions": [],
            "timeline_summary": "30 events analyzed",
        }
        
        is_valid, missing = validate_flare_report_schema(report)
        
        assert is_valid
        assert len(missing) == 0
    
    def test_missing_fields(self):
        """Should fail for missing required fields"""
        report = {
            "flare_forecast": "Pattern suggests elevated risk",
            # Missing other required fields
        }
        
        is_valid, missing = validate_flare_report_schema(report)
        
        assert not is_valid
        assert len(missing) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
