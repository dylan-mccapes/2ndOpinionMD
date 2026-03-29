import pytest
from unittest import mock

try:
    from server.api import ask_eoh_v2 as askmod
except ImportError:
    pytest.skip('server.api.ask_eoh_v2 import failed', allow_module_level=True)

@pytest.mark.asyncio
async def test_ask_eoh_v2_missing_q(monkeypatch):
    class DummyRequest: pass
    payload = {}
    monkeypatch.setattr(askmod, 'os', mock.Mock(getenv=lambda k: 'dummy'))
    with pytest.raises(askmod.HTTPException) as e:
        await askmod.ask_eoh_v2(DummyRequest(), payload)
    assert e.value.status_code == 400
    assert "Missing 'q'" in str(e.value.detail)

@pytest.mark.asyncio
async def test_ask_eoh_v2_no_openai_key(monkeypatch):
    class DummyRequest: pass
    payload = {'q': 'What is flu?'}
    monkeypatch.setattr(askmod, 'os', mock.Mock(getenv=lambda k: None))
    with pytest.raises(askmod.HTTPException) as e:
        await askmod.ask_eoh_v2(DummyRequest(), payload)
    assert e.value.status_code == 500
