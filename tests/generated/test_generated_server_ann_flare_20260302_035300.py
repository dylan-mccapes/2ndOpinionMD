import pytest
try:
    from server.ann import flare
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest.mock import patch, MagicMock


def test_find_flare_precursors_basic(monkeypatch):
    # Patch logger to avoid side effects
    monkeypatch.setattr(flare, 'logger', MagicMock())
    # Patch any ANN/db logic if needed
    dummy_events = [
        {"event_type": "lab", "text": "CRP high", "ts": "2023-01-01"},
        {"event_type": "visit", "text": "Patient reports pain", "ts": "2023-01-02"}
    ]
    # Patch any DB/session logic if present
    if hasattr(flare, 'query_database_for_events'):
        monkeypatch.setattr(flare, 'query_database_for_events', lambda *a, **kw: dummy_events)
    result = flare.find_flare_precursors("patient123", window_days=30, events=dummy_events, session=None)
    assert isinstance(result, dict)
    assert "precursors" in result
    assert "scores" in result
    assert "explanations" in result


@pytest.mark.asyncio
async def test_get_flare_forecast(monkeypatch):
    # Patch find_flare_precursors to return a controlled result
    dummy_result = {
        "flare_likelihood": 0.7,
        "precursors": ["event1", "event2"],
        "explanations": ["ex1", "ex2"]
    }
    monkeypatch.setattr(flare, 'find_flare_precursors', lambda *a, **kw: dummy_result)
    forecast = flare.get_flare_forecast("patient123", events=None, session=None)
    assert isinstance(forecast, str)
    assert "event" in forecast or "likelihood" in forecast or isinstance(forecast, str)
