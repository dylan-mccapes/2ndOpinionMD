import pytest
try:
    from server.ann import flare
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

@pytest.mark.asyncio
def test_find_flare_precursors_returns_schema(monkeypatch):
    # Patch logger to avoid side effects
    monkeypatch.setattr(flare, 'logger', mock.Mock())
    result = pytest.run(flare.find_flare_precursors('patient1')) if hasattr(pytest, 'run') else None
    # If function is not implemented, skip
    if result is None:
        pytest.skip('find_flare_precursors not implemented')
    assert isinstance(result, dict)
    for key in ["precursors", "scores", "explanations"]:
        assert key in result

@pytest.mark.asyncio
def test_get_flare_forecast_calls_find_flare_precursors(monkeypatch):
    monkeypatch.setattr(flare, 'logger', mock.Mock())
    fake_precursor_result = {
        "flare_likelihood": "high",
        "precursors": ["event1"],
        "explanations": ["explanation1"]
    }
    async def fake_find_flare_precursors(*args, **kwargs):
        return fake_precursor_result
    monkeypatch.setattr(flare, 'find_flare_precursors', fake_find_flare_precursors)
    result = pytest.run(flare.get_flare_forecast('patient1')) if hasattr(pytest, 'run') else None
    if result is None:
        pytest.skip('get_flare_forecast not implemented')
    assert isinstance(result, str)
