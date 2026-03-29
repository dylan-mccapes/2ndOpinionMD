# AUTO-GENERATED TESTS for server/api/ask_eoh_v2.py
import pytest
try:
    from server.api import ask_eoh_v2 as ask_eoh_v2_mod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

from unittest import mock
import os

@pytest.mark.asyncio
def test_ask_eoh_v2_missing_q(monkeypatch):
    class DummyRequest: pass
    payload = {}
    monkeypatch.setenv('OPENAI_API_KEY', 'dummy')
    with pytest.raises(ask_eoh_v2_mod.HTTPException) as exc:
        pytest.run(asyncio_run=ask_eoh_v2_mod.ask_eoh_v2(DummyRequest(), payload))
    assert exc.value.status_code == 400
    assert "Missing 'q'" in str(exc.value.detail)

@pytest.mark.asyncio
def test_ask_eoh_v2_missing_openai_key(monkeypatch):
    class DummyRequest: pass
    payload = {'q': 'test'}
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    with pytest.raises(ask_eoh_v2_mod.HTTPException) as exc:
        pytest.run(asyncio_run=ask_eoh_v2_mod.ask_eoh_v2(DummyRequest(), payload))
    assert exc.value.status_code == 500
