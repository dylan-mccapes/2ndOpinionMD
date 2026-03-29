import pytest
import sys
from unittest import mock

try:
    from server.api import app
except ImportError:
    pytest.skip('server.api.app import failed', allow_module_level=True)

import types

@pytest.mark.asyncio
async def test_log_requests_success(monkeypatch):
    class DummyRequest:
        method = 'GET'
        url = type('URL', (), {'__str__': lambda self: 'http://test', 'path': '/test'})()
    dummy_request = DummyRequest()
    dummy_response = type('Resp', (), {'status_code': 200})()
    logs = []
    monkeypatch.setattr(app, 'logger', mock.Mock(info=lambda msg: logs.append(msg), error=lambda msg: logs.append(msg)))
    async def call_next(request):
        return dummy_response
    resp = await app.log_requests(dummy_request, call_next)
    assert resp is dummy_response
    assert any('Request:' in l for l in logs)
    assert any('Response:' in l for l in logs)

@pytest.mark.asyncio
async def test_log_requests_exception(monkeypatch):
    class DummyRequest:
        method = 'POST'
        url = type('URL', (), {'__str__': lambda self: 'http://fail', 'path': '/fail'})()
    dummy_request = DummyRequest()
    monkeypatch.setattr(app, 'logger', mock.Mock(info=lambda msg: None, error=lambda msg: None))
    monkeypatch.setattr(app, 'traceback', mock.Mock(format_exc=lambda: 'trace'))
    async def call_next(request):
        raise ValueError('fail')
    with pytest.raises(app.HTTPException) as e:
        await app.log_requests(dummy_request, call_next)
    assert e.value.status_code == 500
    assert 'Internal server error' in str(e.value.detail)

@pytest.mark.asyncio
async def test_rate_limit_exception_handler(monkeypatch):
    class DummyRequest:
        headers = {'Retry-After': '42'}
    exc = app.HTTPException(status_code=429, detail='Too many requests')
    resp = await app.rate_limit_exception_handler(DummyRequest(), exc)
    assert resp.status_code == 429
    assert resp.headers['Retry-After'] == '42'
    assert resp.body is not None

@pytest.mark.asyncio
async def test_diagnose_valid(monkeypatch):
    # Patch logger, query_engine, get_current_user, general_rate_limiter
    monkeypatch.setattr(app, 'logger', mock.Mock(info=lambda *a, **k: None, error=lambda *a, **k: None))
    class DummyUser: pass
    monkeypatch.setattr(app, 'get_current_user', lambda: DummyUser())
    monkeypatch.setattr(app, 'general_rate_limiter', lambda: None)
    class DummyRequest:
        symptoms = ['cough']
        demographics = {'age': 30}
        model = 'default'
    class DummyQueryEngine:
        def generate(self, *a, **k):
            return {'diagnoses': ['flu']}
    monkeypatch.setattr(app, 'query_engine', DummyQueryEngine())
    # Patch Body and Depends to pass through
    monkeypatch.setattr(app, 'Body', lambda *a, **k: lambda x: x)
    monkeypatch.setattr(app, 'Depends', lambda x: x)
    # Call diagnose
    result = await app.diagnose(DummyRequest(), DummyUser(), None)
    assert 'diagnoses' in result

@pytest.mark.asyncio
async def test_diagnose_invalid_symptoms(monkeypatch):
    monkeypatch.setattr(app, 'logger', mock.Mock(info=lambda *a, **k: None, error=lambda *a, **k: None))
    class DummyUser: pass
    class DummyRequest:
        symptoms = None
        demographics = None
        model = 'default'
    monkeypatch.setattr(app, 'Body', lambda *a, **k: lambda x: x)
    monkeypatch.setattr(app, 'Depends', lambda x: x)
    with pytest.raises(app.HTTPException) as e:
        await app.diagnose(DummyRequest(), DummyUser(), None)
    assert e.value.status_code == 400
    assert 'Invalid symptoms format' in str(e.value.detail)

@pytest.mark.asyncio
async def test_health_check(monkeypatch):
    monkeypatch.setattr(app, 'ping_database', mock.AsyncMock(return_value=True))
    class DummyQueryEngine:
        collections = [1]
    monkeypatch.setattr(app, 'query_engine', DummyQueryEngine())
    result = await app.health_check()
    assert result['status'] == 'ok'
    assert result['services']['api'] == 'ok'
    assert result['services']['mongodb'] == 'ok'
    assert result['services']['chroma'] == 'ok'
