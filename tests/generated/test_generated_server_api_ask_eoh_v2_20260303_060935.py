# Auto-generated tests for server/api/ask_eoh_v2.py
import pytest
try:
    from server.api import ask_eoh_v2 as askmod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

from unittest import mock

@pytest.mark.asyncio
def test_ask_eoh_v2_missing_q(monkeypatch):
    class DummyRequest: pass
    payload = {}
    monkeypatch.setenv('OPENAI_API_KEY', '')
    with pytest.raises(Exception) as exc:
        pytest.run(asyncio=True)(askmod.ask_eoh_v2)(DummyRequest(), payload)
    assert "Missing 'q'" in str(exc.value)

@pytest.mark.asyncio
def test_ask_eoh_v2_no_openai_key(monkeypatch):
    class DummyRequest: pass
    payload = {'q': 'test'}
    monkeypatch.setenv('OPENAI_API_KEY', '')
    with pytest.raises(Exception) as exc:
        pytest.run(asyncio=True)(askmod.ask_eoh_v2)(DummyRequest(), payload)
    assert 'OPENAI_API_KEY' in str(exc.value) or '500' in str(exc.value)
