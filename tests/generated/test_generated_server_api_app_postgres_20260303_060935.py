# Auto-generated tests for server/api/app_postgres.py
import pytest
try:
    from server.api import app_postgres
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

from unittest import mock

@pytest.mark.asyncio
def test_lifespan_env(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@host/db')
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None))
    class DummyApp: pass
    # Should not raise
    pytest.run(asyncio=True)(app_postgres.lifespan)(DummyApp())

@pytest.mark.asyncio
def test_lifespan_no_env(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('SYNC_DATABASE_URL', raising=False)
    class DummyApp: pass
    with pytest.raises(RuntimeError):
        pytest.run(asyncio=True)(app_postgres.lifespan)(DummyApp())

@pytest.mark.asyncio
def test_get_pool(monkeypatch):
    monkeypatch.setenv('POSTGRES_DSN', 'postgres://localhost/test')
    monkeypatch.setenv('PGPOOL_MAX', '2')
    fake_pool = object()
    monkeypatch.setattr(app_postgres, 'asyncpg', mock.Mock(create_pool=mock.AsyncMock(return_value=fake_pool)))
    app_postgres._pool = None
    pool = pytest.run(asyncio=True)(app_postgres.get_pool)()
    assert pool is fake_pool

@pytest.mark.asyncio
def test_log_requests_success(monkeypatch):
    class DummyRequest:
        method = 'GET'
        url = type('URL', (), {'path': '/foo'})()
    async def call_next(request):
        class DummyResponse:
            pass
        return DummyResponse()
    logs = []
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: logs.append(a)))
    pytest.run(asyncio=True)(app_postgres.log_requests)(DummyRequest(), call_next)
    assert logs

@pytest.mark.asyncio
def test_log_requests_exception(monkeypatch):
    class DummyRequest:
        method = 'POST'
        url = type('URL', (), {'path': '/err'})()
    async def call_next(request):
        raise Exception('fail')
    logs = []
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None, exception=lambda *a, **k: logs.append(a)))
    with pytest.raises(Exception):
        pytest.run(asyncio=True)(app_postgres.log_requests)(DummyRequest(), call_next)
    assert logs

@pytest.mark.asyncio
def test_rate_limit_exception_handler(monkeypatch):
    class DummyRequest:
        headers = {'Retry-After': '99'}
    class DummyExc:
        detail = 'Too many'
    monkeypatch.setattr(app_postgres, 'status', mock.Mock(HTTP_429_TOO_MANY_REQUESTS=429))
    monkeypatch.setattr(app_postgres, 'JSONResponse', lambda **kwargs: kwargs)
    resp = pytest.run(asyncio=True)(app_postgres.rate_limit_exception_handler)(DummyRequest(), DummyExc())
    assert resp['status_code'] == 429
    assert resp['headers']['Retry-After'] == '99'

@pytest.mark.asyncio
def test_diagnose_invalid(monkeypatch):
    class DummyRequest:
        symptoms = None
        demographics = None
        model = None
    class DummySession: pass
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None))
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc:
        pytest.run(asyncio=True)(app_postgres.diagnose)(DummyRequest(), DummySession(), None)
    assert exc.value.status_code == 400
    assert 'invalid_symptoms' in str(exc.value.detail)

@pytest.mark.asyncio
def test_diagnose_alias(monkeypatch):
    class DummyRequest:
        symptoms = ['a']
        demographics = None
        model = None
    class DummySession: pass
    monkeypatch.setattr(app_postgres, 'diagnose', mock.AsyncMock(return_value={'diagnoses': ['x']}))
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(warning=lambda *a, **k: None))
    resp = pytest.run(asyncio=True)(app_postgres.diagnose_alias)(DummyRequest(), DummySession(), None)
    assert 'diagnoses' in resp

@pytest.mark.asyncio
def test_health_check_ok(monkeypatch):
    class DummySession:
        async def execute(self, sql): return None
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(warning=lambda *a, **k: None))
    monkeypatch.setattr(app_postgres, 'query_engine', object())
    from sqlalchemy import text
    result = pytest.run(asyncio=True)(app_postgres.health_check)(DummySession())
    assert result['status'] == 'ok'
    assert result['services']['postgresql'] == 'ok'
    assert result['services']['pgvector'] == 'ok'

@pytest.mark.asyncio
def test_openapi_json(monkeypatch):
    monkeypatch.setattr(app_postgres, 'app', mock.Mock(openapi=lambda: {'openapi': True}))
    resp = pytest.run(asyncio=True)(app_postgres.openapi_json)()
    assert resp['openapi'] is True
