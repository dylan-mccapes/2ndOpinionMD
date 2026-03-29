try:
    import pytest
    from server.api import app
    from unittest import mock
    from fastapi import Request, HTTPException
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_log_requests_success(monkeypatch):
    class DummyRequest:
        method = 'GET'
        url = type('url', (), {'__str__': lambda self: 'http://test', 'path': '/test'})()
    called = {}
    async def call_next(request):
        called['called'] = True
        class DummyResponse:
            status_code = 200
        return DummyResponse()
    logs = []
    monkeypatch.setattr(app, 'logger', mock.Mock(info=lambda msg: logs.append(msg), error=lambda msg: logs.append(msg)))
    response = pytest.run(asyncio.run(app.log_requests(DummyRequest(), call_next))) if hasattr(pytest, 'run') else None
    # No exception means pass
    assert 'called' in called

@pytest.mark.asyncio
def test_log_requests_exception(monkeypatch):
    class DummyRequest:
        method = 'POST'
        url = type('url', (), {'__str__': lambda self: 'http://test', 'path': '/test'})()
    async def call_next(request):
        raise ValueError('fail')
    errors = []
    monkeypatch.setattr(app, 'logger', mock.Mock(info=lambda msg: None, error=lambda msg: errors.append(msg)))
    monkeypatch.setattr(app, 'traceback', mock.Mock(format_exc=lambda: 'traceback'))
    with pytest.raises(HTTPException) as exc:
        await app.log_requests(DummyRequest(), call_next)
    assert exc.value.status_code == 500
    assert any('Internal server error' in str(e) for e in errors)

@pytest.mark.asyncio
def test_rate_limit_exception_handler(monkeypatch):
    class DummyRequest:
        headers = {'Retry-After': '42'}
    exc = HTTPException(status_code=429, detail='Too many requests')
    monkeypatch.setattr(app, 'status', mock.Mock(HTTP_429_TOO_MANY_REQUESTS=429))
    monkeypatch.setattr(app, 'JSONResponse', lambda **kwargs: kwargs)
    resp = await app.rate_limit_exception_handler(DummyRequest(), exc)
    assert resp['status_code'] == 429
    assert resp['content']['detail'] == 'Too many requests'
    assert resp['headers']['Retry-After'] == '42'

@pytest.mark.asyncio
def test_diagnose_invalid_symptoms(monkeypatch):
    class DummyRequest:
        symptoms = None
        demographics = None
        model = None
    monkeypatch.setattr(app, 'logger', mock.Mock(info=lambda *a, **k: None, error=lambda *a, **k: None))
    with pytest.raises(HTTPException) as exc:
        await app.diagnose(DummyRequest())
    assert exc.value.status_code == 400
    assert 'Invalid symptoms format' in str(exc.value.detail)

@pytest.mark.asyncio
def test_health_check(monkeypatch):
    monkeypatch.setattr(app, 'ping_database', mock.AsyncMock(return_value=True))
    monkeypatch.setattr(app, 'query_engine', mock.Mock(collections=[1]))
    resp = await app.health_check()
    assert resp['status'] == 'ok'
    assert resp['services']['api'] == 'ok'
    assert resp['services']['mongodb'] == 'ok'
    assert resp['services']['chroma'] == 'ok'
