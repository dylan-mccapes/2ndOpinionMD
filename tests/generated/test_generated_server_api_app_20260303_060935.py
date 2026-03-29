# Auto-generated tests for server/api/app.py
import pytest
try:
    from server.api import app
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

import types
from unittest import mock

@pytest.mark.asyncio
def test_log_requests_success(monkeypatch):
    class DummyRequest:
        method = 'GET'
        url = type('URL', (), {'__str__': lambda self: 'http://test', 'path': '/test'})()
    called = {}
    async def call_next(request):
        called['called'] = True
        class DummyResponse:
            status_code = 200
        return DummyResponse()
    logs = []
    monkeypatch.setattr(app, 'logger', mock.Mock(info=lambda msg: logs.append(msg), error=lambda msg: logs.append(msg)))
    response = pytest.run(asyncio=True)(app.log_requests)(DummyRequest(), call_next)
    assert called['called']

@pytest.mark.asyncio
def test_log_requests_exception(monkeypatch):
    class DummyRequest:
        method = 'POST'
        url = type('URL', (), {'__str__': lambda self: 'http://fail', 'path': '/fail'})()
    async def call_next(request):
        raise Exception('fail')
    errors = []
    monkeypatch.setattr(app, 'logger', mock.Mock(info=lambda msg: None, error=lambda msg: errors.append(msg)))
    monkeypatch.setattr(app, 'traceback', mock.Mock(format_exc=lambda: 'trace'))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        pytest.run(asyncio=True)(app.log_requests)(DummyRequest(), call_next)
    assert exc.value.status_code == 500
    assert any('fail' in e for e in errors)

@pytest.mark.asyncio
def test_rate_limit_exception_handler(monkeypatch):
    class DummyRequest:
        headers = {'Retry-After': '42'}
    class DummyExc:
        detail = 'Too many requests'
    monkeypatch.setattr(app, 'status', mock.Mock(HTTP_429_TOO_MANY_REQUESTS=429))
    monkeypatch.setattr(app, 'JSONResponse', lambda **kwargs: kwargs)
    resp = pytest.run(asyncio=True)(app.rate_limit_exception_handler)(DummyRequest(), DummyExc())
    assert resp['status_code'] == 429
    assert resp['content']['detail'] == 'Too many requests'
    assert resp['headers']['Retry-After'] == '42'

@pytest.mark.asyncio
def test_diagnose_invalid_symptoms(monkeypatch):
    class DummyRequest:
        symptoms = None
        demographics = None
        model = None
    class DummyUser: pass
    monkeypatch.setattr(app, 'logger', mock.Mock(info=lambda *a, **k: None, error=lambda *a, **k: None))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        pytest.run(asyncio=True)(app.diagnose)(DummyRequest(), DummyUser(), None)
    assert exc.value.status_code == 400
    assert 'Invalid symptoms format' in str(exc.value.detail)

@pytest.mark.asyncio
def test_health_check(monkeypatch):
    monkeypatch.setattr(app, 'ping_database', mock.AsyncMock(return_value=True))
    monkeypatch.setattr(app, 'query_engine', mock.Mock(collections=True))
    result = pytest.run(asyncio=True)(app.health_check)()
    assert result['status'] == 'ok'
    assert result['services']['mongodb'] == 'ok'
    assert result['services']['chroma'] == 'ok'
