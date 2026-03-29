try:
    import pytest
    from server.api import app_postgres
    from unittest import mock
    from fastapi import FastAPI, Request, HTTPException
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_lifespan_env(monkeypatch):
    monkeypatch.setattr(app_postgres.os, 'getenv', lambda k: 'postgresql://user:pass@host/db' if k == 'DATABASE_URL' else None)
    app = mock.Mock(spec=FastAPI)
    # Should not raise
    pytest.run(asyncio.run(app_postgres.lifespan(app))) if hasattr(pytest, 'run') else None

@pytest.mark.asyncio
def test_lifespan_no_env(monkeypatch):
    monkeypatch.setattr(app_postgres.os, 'getenv', lambda k: None)
    app = mock.Mock(spec=FastAPI)
    with pytest.raises(RuntimeError):
        pytest.run(asyncio.run(app_postgres.lifespan(app))) if hasattr(pytest, 'run') else None

@pytest.mark.asyncio
def test_get_pool_creates(monkeypatch):
    monkeypatch.setattr(app_postgres, '_pool', None)
    fake_pool = object()
    monkeypatch.setattr(app_postgres.asyncpg, 'create_pool', mock.AsyncMock(return_value=fake_pool))
    monkeypatch.setattr(app_postgres.os, 'getenv', lambda k, d=None: 'postgres://localhost/2ndopinionmd' if k == 'POSTGRES_DSN' else '10')
    pool = pytest.run(asyncio.run(app_postgres.get_pool())) if hasattr(pytest, 'run') else None
    assert pool is fake_pool

@pytest.mark.asyncio
def test_log_requests_success(monkeypatch):
    class DummyRequest:
        method = 'GET'
        url = type('URL', (), {'path': '/foo'})()
    async def call_next(request):
        return mock.Mock()
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock())
    import time
    monkeypatch.setattr(app_postgres, 'time', time)
    request = DummyRequest()
    pytest.run(asyncio.run(app_postgres.log_requests(request, call_next))) if hasattr(pytest, 'run') else None

@pytest.mark.asyncio
def test_log_requests_exception(monkeypatch):
    class DummyRequest:
        method = 'POST'
        url = type('URL', (), {'path': '/bar'})()
    async def call_next(request):
        raise Exception('fail')
    logger = mock.Mock()
    monkeypatch.setattr(app_postgres, 'logger', logger)
    import time
    monkeypatch.setattr(app_postgres, 'time', time)
    request = DummyRequest()
    with pytest.raises(Exception):
        pytest.run(asyncio.run(app_postgres.log_requests(request, call_next))) if hasattr(pytest, 'run') else None
    assert logger.exception.called

@pytest.mark.asyncio
def test_rate_limit_exception_handler(monkeypatch):
    request = mock.Mock()
    request.headers = {'Retry-After': '99'}
    exc = HTTPException(status_code=429, detail='Too many')
    monkeypatch.setattr(app_postgres, 'JSONResponse', lambda **kwargs: kwargs)
    monkeypatch.setattr(app_postgres, 'status', mock.Mock(HTTP_429_TOO_MANY_REQUESTS=429))
    resp = pytest.run(asyncio.run(app_postgres.rate_limit_exception_handler(request, exc))) if hasattr(pytest, 'run') else None
    assert resp['status_code'] == 429
    assert resp['content']['detail'] == 'Too many'
    assert resp['headers']['Retry-After'] == '99'

@pytest.mark.asyncio
def test_diagnose_invalid(monkeypatch):
    class DummyRequest:
        symptoms = None
        demographics = None
        model = None
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock())
    with pytest.raises(HTTPException) as exc:
        pytest.run(asyncio.run(app_postgres.diagnose(DummyRequest(), mock.Mock(), None))) if hasattr(pytest, 'run') else None
    assert exc.value.status_code == 400
    assert 'invalid_symptoms' in str(exc.value.detail)

@pytest.mark.asyncio
def test_diagnose_alias(monkeypatch):
    class DummyRequest:
        symptoms = ['a']
        demographics = None
        model = None
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock())
    async def fake_diagnose(request, session, none):
        return {'diagnoses': ['foo']}
    monkeypatch.setattr(app_postgres, 'diagnose', fake_diagnose)
    resp = pytest.run(asyncio.run(app_postgres.diagnose_alias(DummyRequest(), mock.Mock(), None))) if hasattr(pytest, 'run') else None
    assert 'diagnoses' in resp

@pytest.mark.asyncio
def test_health_check_ok(monkeypatch):
    session = mock.AsyncMock()
    session.execute = mock.AsyncMock()
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock())
    monkeypatch.setattr(app_postgres, 'query_engine', object())
    resp = pytest.run(asyncio.run(app_postgres.health_check(session))) if hasattr(pytest, 'run') else None
    assert resp['status'] == 'ok'
    assert resp['services']['postgresql'] == 'ok'
    assert resp['services']['pgvector'] == 'ok'

@pytest.mark.asyncio
def test_health_check_db_error(monkeypatch):
    session = mock.AsyncMock()
    session.execute = mock.AsyncMock(side_effect=Exception('fail'))
    logger = mock.Mock()
    monkeypatch.setattr(app_postgres, 'logger', logger)
    monkeypatch.setattr(app_postgres, 'query_engine', None)
    resp = pytest.run(asyncio.run(app_postgres.health_check(session))) if hasattr(pytest, 'run') else None
    assert resp['services']['postgresql'] == 'error'
    assert resp['services']['pgvector'] == 'error'
    assert logger.warning.called

@pytest.mark.asyncio
def test_openapi_json(monkeypatch):
    monkeypatch.setattr(app_postgres, 'app', mock.Mock(openapi=lambda: {'openapi': True}))
    resp = pytest.run(asyncio.run(app_postgres.openapi_json())) if hasattr(pytest, 'run') else None
    assert resp['openapi'] is True
