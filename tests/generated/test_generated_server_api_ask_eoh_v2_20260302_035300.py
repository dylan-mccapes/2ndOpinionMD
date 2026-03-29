try:
    import pytest
    from server.api import ask_eoh_v2
    from unittest import mock
    from fastapi import Request, HTTPException
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_ask_eoh_v2_missing_q(monkeypatch):
    request = mock.Mock(spec=Request)
    payload = {}
    monkeypatch.setattr(ask_eoh_v2.os, 'getenv', lambda k: 'somekey')
    with pytest.raises(HTTPException) as exc:
        pytest.run(asyncio.run(ask_eoh_v2.ask_eoh_v2(request, payload))) if hasattr(pytest, 'run') else None
    assert exc.value.status_code == 400
    assert "Missing 'q'" in str(exc.value.detail)

@pytest.mark.asyncio
def test_ask_eoh_v2_missing_openai_key(monkeypatch):
    request = mock.Mock(spec=Request)
    payload = {'q': 'test'}
    monkeypatch.setattr(ask_eoh_v2.os, 'getenv', lambda k: None)
    with pytest.raises(HTTPException) as exc:
        pytest.run(asyncio.run(ask_eoh_v2.ask_eoh_v2(request, payload))) if hasattr(pytest, 'run') else None
    assert exc.value.status_code == 500
