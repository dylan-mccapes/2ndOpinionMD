import pytest
import sys
from unittest import mock

pytestmark = pytest.mark.asyncio

try:
    from server.api.ask_eoh_v2 import ask_eoh_v2
except ImportError:
    ask_eoh_v2 = None

@pytest.mark.asyncio
@pytest.mark.skipif(ask_eoh_v2 is None, reason='Import failed')
async def test_ask_eoh_v2_missing_q(monkeypatch):
    class DummyRequest:
        pass
    payload = {}
    # Patch os.getenv to return a dummy API key
    monkeypatch.setattr('server.api.ask_eoh_v2.os', mock.Mock(getenv=lambda k: 'dummy'))
    with pytest.raises(Exception) as excinfo:
        await ask_eoh_v2(DummyRequest(), payload)
    assert "Missing 'q'" in str(excinfo.value)

@pytest.mark.asyncio
@pytest.mark.skipif(ask_eoh_v2 is None, reason='Import failed')
async def test_ask_eoh_v2_no_openai_key(monkeypatch):
    class DummyRequest:
        pass
    payload = {"q": "test"}
    # Patch os.getenv to return None
    monkeypatch.setattr('server.api.ask_eoh_v2.os', mock.Mock(getenv=lambda k: None))
    with pytest.raises(Exception) as excinfo:
        await ask_eoh_v2(DummyRequest(), payload)
    assert "OPENAI_API_KEY" in str(excinfo.value)
