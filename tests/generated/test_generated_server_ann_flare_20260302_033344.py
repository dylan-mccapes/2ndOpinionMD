import pytest
from unittest import mock

@pytest.mark.skipif('server.ann.flare' not in globals(), reason='Module not importable')
@pytest.mark.asyncio
def test_find_flare_precursors(monkeypatch):
    try:
        from server.ann import flare
    except ImportError:
        pytest.skip('flare module not importable')
    # Patch logger to avoid side effects
    monkeypatch.setattr(flare, 'logger', mock.Mock())
    # Patch any DB/network calls inside if needed
    result = await flare.find_flare_precursors('patient123', window_days=30, events=[{"event": 1}], session=None)
    assert isinstance(result, dict)
    assert "precursors" in result
    assert "scores" in result
    assert "explanations" in result

@pytest.mark.skipif('server.ann.flare' not in globals(), reason='Module not importable')
@pytest.mark.asyncio
def test_get_flare_forecast(monkeypatch):
    try:
        from server.ann import flare
    except ImportError:
        pytest.skip('flare module not importable')
    fake_precursor_result = {
        "flare_likelihood": "high",
        "precursors": ["a"],
        "explanations": ["b"]
    }
    monkeypatch.setattr(flare, 'find_flare_precursors', mock.AsyncMock(return_value=fake_precursor_result))
    result = await flare.get_flare_forecast('patient123')
    assert isinstance(result, str)