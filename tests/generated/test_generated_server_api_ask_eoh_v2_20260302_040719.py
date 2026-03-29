try:
    import pytest
    from server.api import ask_eoh_v2
    from unittest import mock
    from fastapi import HTTPException, Request
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_ask_eoh_v2_missing_q(monkeypatch):
    class DummyRequest: pass
    payload = {}
    monkeypatch.setenv('OPENAI_API_KEY', 'dummy')
    with pytest.raises(HTTPException) as exc:
        await ask_eoh_v2.ask_eoh_v2(DummyRequest(), payload)
    assert exc.value.status_code == 400
    assert "Missing 'q'" in str(exc.value.detail)

@pytest.mark.asyncio
def test_ask_eoh_v2_missing_openai_key(monkeypatch):
    class DummyRequest: pass
    payload = {'q': 'test'}
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    with pytest.raises(HTTPException) as exc:
        await ask_eoh_v2.ask_eoh_v2(DummyRequest(), payload)
    assert exc.value.status_code == 500
