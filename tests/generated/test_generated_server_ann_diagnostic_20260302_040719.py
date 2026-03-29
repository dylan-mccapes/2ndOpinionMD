import pytest
try:
    from server.ann import diagnostic
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_estimate_diagnostic_landscape_returns_schema():
    patient_id = 'p1'
    result = diagnostic.estimate_diagnostic_landscape(patient_id)
    assert isinstance(result, dict)
    assert 'diagnostic_probabilities' in result
    assert 'drivers' in result
    for key in ["ra_like", "sle_like", "psa_like", "sjogren_like", "mctd_like", "other"]:
        assert key in result["diagnostic_probabilities"]

def test_get_probabilistic_differential_formats_output(monkeypatch):
    fake_landscape = {
        "diagnostic_probabilities": {
            "ra_like": 0.1,
            "sle_like": 0.2,
            "psa_like": 0.3,
            "sjogren_like": 0.05,
            "mctd_like": 0.15,
            "other": 0.2
        },
        "drivers": ["driver1", "driver2"]
    }
    monkeypatch.setattr(diagnostic, 'estimate_diagnostic_landscape', lambda *a, **kw: fake_landscape)
    result = diagnostic.get_probabilistic_differential('p1')
    assert isinstance(result, dict)
    assert 'narrative' in result or 'diagnostic_probabilities' in result
