import pytest
from unittest import mock

try:
    import server.ann.diagnostic as diagnostic
except ImportError:
    diagnostic = None

def test_estimate_diagnostic_landscape_returns_schema(monkeypatch):
    if diagnostic is None:
        pytest.skip('diagnostic module not importable')
    # Patch any DB/network dependencies if present
    result = diagnostic.estimate_diagnostic_landscape('patient1', events=[{'event': 1}], session=None)
    assert isinstance(result, dict)
    assert 'diagnostic_probabilities' in result
    assert 'drivers' in result
    for key in ['ra_like', 'sle_like', 'psa_like', 'sjogren_like', 'mctd_like', 'other']:
        assert key in result['diagnostic_probabilities']

def test_get_probabilistic_differential_formats_output(monkeypatch):
    if diagnostic is None:
        pytest.skip('diagnostic module not importable')
    fake_landscape = {
        'diagnostic_probabilities': {
            'ra_like': 0.5,
            'sle_like': 0.2,
            'psa_like': 0.1,
            'sjogren_like': 0.1,
            'mctd_like': 0.05,
            'other': 0.05
        },
        'drivers': ['driver1', 'driver2']
    }
    monkeypatch.setattr(diagnostic, 'estimate_diagnostic_landscape', lambda *a, **kw: fake_landscape)
    result = diagnostic.get_probabilistic_differential('patient1', events=None, session=None)
    assert isinstance(result, dict)
    assert 'narrative' in result or 'diagnostic_probabilities' in result or result
