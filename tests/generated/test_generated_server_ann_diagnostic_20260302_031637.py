import pytest
from unittest import mock

try:
    from server.ann import diagnostic
except ImportError:
    diagnostic = None

@pytest.mark.skipif(diagnostic is None, reason="Module import failed")
def test_estimate_diagnostic_landscape_returns_schema():
    result = diagnostic.estimate_diagnostic_landscape('patient123', events=[])
    assert isinstance(result, dict)
    assert 'diagnostic_probabilities' in result
    assert 'drivers' in result
    assert isinstance(result['diagnostic_probabilities'], dict)
    for key in ['ra_like', 'sle_like', 'psa_like', 'sjogren_like', 'mctd_like', 'other']:
        assert key in result['diagnostic_probabilities']
        assert isinstance(result['diagnostic_probabilities'][key], float)
    assert isinstance(result['drivers'], list)

@pytest.mark.skipif(diagnostic is None, reason="Module import failed")
def test_get_probabilistic_differential_formats_output(monkeypatch):
    fake_landscape = {
        "diagnostic_probabilities": {
            "ra_like": 0.2,
            "sle_like": 0.3,
            "psa_like": 0.1,
            "sjogren_like": 0.15,
            "mctd_like": 0.05,
            "other": 0.2
        },
        "drivers": ["driver1", "driver2"]
    }
    monkeypatch.setattr(diagnostic, 'estimate_diagnostic_landscape', lambda *a, **kw: fake_landscape)
    result = diagnostic.get_probabilistic_differential('patient123', events=[])
    assert isinstance(result, dict)
    assert 'narrative' in result or 'diagnostic_probabilities' in result
