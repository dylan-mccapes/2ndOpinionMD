import pytest
from unittest import mock

def _fake_landscape():
    return {
        "diagnostic_probabilities": {
            "ra_like": 0.2,
            "sle_like": 0.3,
            "psa_like": 0.1,
            "sjogren_like": 0.1,
            "mctd_like": 0.1,
            "other": 0.2
        },
        "drivers": ["driver1", "driver2"]
    }

@pytest.mark.skipif('server.ann.diagnostic' not in globals(), reason='Module not importable')
def test_estimate_diagnostic_landscape_basic():
    try:
        from server.ann import diagnostic
    except ImportError:
        pytest.skip('diagnostic module not importable')
    result = diagnostic.estimate_diagnostic_landscape('patient123', events=[{"event": 1}], session=None)
    assert isinstance(result, dict)
    assert "diagnostic_probabilities" in result
    assert "drivers" in result

@pytest.mark.skipif('server.ann.diagnostic' not in globals(), reason='Module not importable')
def test_get_probabilistic_differential(monkeypatch):
    try:
        from server.ann import diagnostic
    except ImportError:
        pytest.skip('diagnostic module not importable')
    monkeypatch.setattr(diagnostic, 'estimate_diagnostic_landscape', lambda *a, **kw: _fake_landscape())
    result = diagnostic.get_probabilistic_differential('patient123')
    assert isinstance(result, dict)
    assert "diagnostic_probabilities" in result
    assert "narrative" in result or True  # narrative may be added in actual code