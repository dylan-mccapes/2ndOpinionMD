import pytest
try:
    from server.ann import diagnostic
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_estimate_diagnostic_landscape_returns_schema():
    patient_id = "test_patient"
    result = diagnostic.estimate_diagnostic_landscape(patient_id)
    assert isinstance(result, dict)
    assert "diagnostic_probabilities" in result
    assert "drivers" in result
    assert isinstance(result["diagnostic_probabilities"], dict)
    assert isinstance(result["drivers"], list)

def test_get_probabilistic_differential_formats_output(monkeypatch):
    patient_id = "test_patient"
    fake_landscape = {
        "diagnostic_probabilities": {
            "ra_like": 0.5,
            "sle_like": 0.2,
            "psa_like": 0.1,
            "sjogren_like": 0.1,
            "mctd_like": 0.05,
            "other": 0.05
        },
        "drivers": ["driver1", "driver2"]
    }
    monkeypatch.setattr(diagnostic, 'estimate_diagnostic_landscape', lambda *a, **kw: fake_landscape)
    result = diagnostic.get_probabilistic_differential(patient_id)
    assert isinstance(result, dict)
    assert "narrative" in result or "diagnostic_probabilities" in result
