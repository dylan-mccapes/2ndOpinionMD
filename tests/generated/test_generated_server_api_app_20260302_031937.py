import pytest
from unittest import mock

try:
    from server.api import app
except ImportError:
    pytest.skip('server.api.app not importable', allow_module_level=True)

import types

@pytest.mark.asyncio
async def test_log_requests_success(monkeypatch):
    class DummyRequest:
        method = 'GET'
        url = type('URL', (), {'__str__': lambda self: 'http://test', '__repr__': lambda self: 'http://test'})()
    dummy_response = mock.Mock(status_code=200)
    async def call_next(request):
        return dummy_response
    logs = []
    monkeypatch.setattr(app.logger, 'info', logs.append)
    request = DummyRequest()
    result = await app.log_requests(request, call_next)
    assert result is dummy_response
    assert any('Request:' in str(l) for l in logs)
    assert any('Response:' in str(l) for l in logs)

@pytest.mark.asyncio
async def test_log_requests_exception(monkeypatch):
    class DummyRequest:
        method = 'POST'
        url = type('URL', (), {'__str__': lambda self: 'http://fail', '__repr__': lambda self: 'http://fail'})()
    async def call_next(request):
        raise Exception('fail')
    errors = []
    monkeypatch.setattr(app.logger, 'error', errors.append)
    with pytest.raises(app.HTTPException) as exc:
        await app.log_requests(DummyRequest(), call_next)
    assert exc.value.status_code == 500
    assert any('Error processing request' in str(e) for e in errors)

@pytest.mark.asyncio
async def test_rate_limit_exception_handler(monkeypatch):
    class DummyRequest:
        headers = {'Retry-After': '42'}
    exc = mock.Mock(detail='Too many', spec=app.HTTPException)
    resp = await app.rate_limit_exception_handler(DummyRequest(), exc)
    assert resp.status_code == 429
    assert resp.headers['Retry-After'] == '42'
    assert resp.body is not None

@pytest.mark.asyncio
async def test_diagnose_invalid_symptoms(monkeypatch):
    class DummyRequest:
        symptoms = None
        demographics = None
        model = 'test'
    monkeypatch.setattr(app.logger, 'info', lambda *a, **k: None)
    monkeypatch.setattr(app.logger, 'error', lambda *a, **k: None)
    with pytest.raises(app.HTTPException) as exc:
        await app.diagnose(DummyRequest(), current_user=mock.Mock(), _=None)
    assert exc.value.status_code == 400
    assert 'Invalid symptoms format' in str(exc.value.detail)

@pytest.mark.asyncio
async def test_health_check(monkeypatch):
    monkeypatch.setattr(app, 'ping_database', lambda: True)
    monkeypatch.setattr(app, 'query_engine', type('QE', (), {'collections': [1]})())
    result = await app.health_check()
    assert result['status'] == 'ok'
    assert result['services']['api'] == 'ok'
    assert result['services']['mongodb'] == 'ok'
    assert result['services']['chroma'] == 'ok'
