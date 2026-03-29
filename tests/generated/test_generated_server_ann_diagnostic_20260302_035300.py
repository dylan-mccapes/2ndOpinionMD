# test_generated_server_ann_diagnostic_20260302_035300.py
import pytest
try:
    from server.ann import diagnostic
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

from unittest import mock

def test_estimate_diagnostic_landscape_basic(monkeypatch):
    # Patch any DB/session access if needed
    result = diagnostic.estimate_diagnostic_landscape('patient123')
    assert isinstance(result, dict)
    assert 'diagnostic_probabilities' in result
    assert 'drivers' in result
    assert isinstance(result['diagnostic_probabilities'], dict)
    assert isinstance(result['drivers'], list)


def test_get_probabilistic_differential(monkeypatch):
    # Patch estimate_diagnostic_landscape to return a known value
    fake_landscape = {
        "diagnostic_probabilities": {
            "ra_like": 0.5,
            "sle_like": 0.2,
            "psa_like": 0.1,
            "sjogren_like": 0.1,
            "mctd_like": 0.05,
            "other": 0.05
        },
        "drivers": ["symptom1", "symptom2"]
    }
    monkeypatch.setattr(diagnostic, 'estimate_diagnostic_landscape', lambda *a, **kw: fake_landscape)
    result = diagnostic.get_probabilistic_differential('patient123')
    assert isinstance(result, dict)
    assert 'diagnostic_probabilities' in result or 'narrative' in result or 'drivers' in result
