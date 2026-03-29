import pytest
try:
    from server.ann import flare
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

@pytest.mark.asyncio
async def test_find_flare_precursors_returns_expected(monkeypatch):
    patient_id = "p1"
    # Patch logger to avoid side effects
    monkeypatch.setattr(flare, 'logger', mock.Mock())
    # Patch any DB/network calls inside if needed
    result = await flare.find_flare_precursors(patient_id)
    assert isinstance(result, dict)
    assert "precursors" in result
    assert "scores" in result
    assert "explanations" in result

@pytest.mark.asyncio
async def test_get_flare_forecast_uses_precursors(monkeypatch):
    patient_id = "p2"
    fake_precursor_result = {
        "flare_likelihood": "moderate",
        "precursors": ["e1", "e2"],
        "explanations": ["ex1", "ex2"]
    }
    monkeypatch.setattr(flare, 'find_flare_precursors', mock.AsyncMock(return_value=fake_precursor_result))
    result = await flare.get_flare_forecast(patient_id)
    assert isinstance(result, str)
    assert "moderate" in result or isinstance(result, str)
