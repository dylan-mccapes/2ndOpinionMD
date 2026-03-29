import pytest
from unittest import mock

try:
    from server.api import app_postgres
except ImportError:
    pytest.skip('server.api.app_postgres not importable', allow_module_level=True)

import types

@pytest.mark.asyncio
async def test_lifespan_env(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@host/db')
    class DummyApp: pass
    # Patch create_async_engine to avoid real DB
    monkeypatch.setattr(app_postgres, 'create_async_engine', lambda *a, **k: None)
    # Patch logger
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock())
    # Should not raise
    await app_postgres.lifespan(DummyApp())

@pytest.mark.asyncio
async def test_lifespan_no_env(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('SYNC_DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError):
        await app_postgres.lifespan(mock.Mock())

@pytest.mark.asyncio
async def test_get_pool(monkeypatch):
    monkeypatch.setattr(app_postgres, '_pool', None)
    fake_pool = object()
    async def fake_create_pool(**kwargs):
        return fake_pool
    monkeypatch.setattr(app_postgres.asyncpg, 'create_pool', fake_create_pool)
    monkeypatch.setenv('POSTGRES_DSN', 'postgres://localhost/2ndopinionmd')
    monkeypatch.setenv('PGPOOL_MAX', '2')
    pool = await app_postgres.get_pool()
    assert pool is fake_pool

@pytest.mark.asyncio
async def test_log_requests_success(monkeypatch):
    class DummyRequest:
        method = 'GET'
        url = type('URL', (), {'path': '/api', '__str__': lambda self: '/api'})()
    dummy_response = mock.Mock()
    async def call_next(request):
        return dummy_response
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock())
    result = await app_postgres.log_requests(DummyRequest(), call_next)
    assert result is dummy_response

@pytest.mark.asyncio
async def test_log_requests_exception(monkeypatch):
    class DummyRequest:
        method = 'POST'
        url = type('URL', (), {'path': '/fail', '__str__': lambda self: '/fail'})()
    async def call_next(request):
        raise Exception('fail')
    logger = mock.Mock()
    monkeypatch.setattr(app_postgres, 'logger', logger)
    with pytest.raises(Exception):
        await app_postgres.log_requests(DummyRequest(), call_next)
    assert logger.exception.called

@pytest.mark.asyncio
async def test_rate_limit_exception_handler(monkeypatch):
    class DummyRequest:
        headers = {'Retry-After': '99'}
    exc = mock.Mock(detail='Too many', spec=app_postgres.HTTPException)
    resp = await app_postgres.rate_limit_exception_handler(DummyRequest(), exc)
    assert resp.status_code == 429
    assert resp.headers['Retry-After'] == '99'

@pytest.mark.asyncio
async def test_diagnose_invalid(monkeypatch):
    class DummyRequest:
        symptoms = None
        demographics = None
        model = 'test'
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock())
    with pytest.raises(app_postgres.HTTPException) as exc:
        await app_postgres.diagnose(DummyRequest(), session=mock.Mock(), _=None)
    assert exc.value.status_code == 400
    assert 'invalid_symptoms' in str(exc.value.detail)

@pytest.mark.asyncio
async def test_diagnose_alias(monkeypatch):
    class DummyRequest:
        symptoms = ['cough']
        demographics = None
        model = 'test'
    async def fake_diagnose(request, session, _):
        return {'diagnoses': ['flu']}
    monkeypatch.setattr(app_postgres, 'diagnose', fake_diagnose)
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock())
    resp = await app_postgres.diagnose_alias(DummyRequest(), session=mock.Mock(), _=None)
    assert resp == {'diagnoses': ['flu']}

@pytest.mark.asyncio
async def test_health_check_ok(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            return 1
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock())
    monkeypatch.setattr(app_postgres, 'query_engine', True)
    result = await app_postgres.health_check(session=DummySession())
    assert result['status'] == 'ok'
    assert result['services']['postgresql'] == 'ok'
    assert result['services']['pgvector'] == 'ok'

@pytest.mark.asyncio
async def test_health_check_fail(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            raise Exception('fail')
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock())
    monkeypatch.setattr(app_postgres, 'query_engine', False)
    result = await app_postgres.health_check(session=DummySession())
    assert result['services']['postgresql'] == 'error'
    assert result['services']['pgvector'] == 'error'

@pytest.mark.asyncio
async def test_openapi_json(monkeypatch):
    monkeypatch.setattr(app_postgres, 'app', mock.Mock())
    app_postgres.app.openapi.return_value = {'openapi': '3.0.0'}
    result = await app_postgres.openapi_json()
    assert result == {'openapi': '3.0.0'}
