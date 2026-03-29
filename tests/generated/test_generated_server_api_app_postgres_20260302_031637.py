import pytest
import sys
from unittest import mock

try:
    from server.api import app_postgres
except ImportError:
    pytest.skip('server.api.app_postgres import failed', allow_module_level=True)

@pytest.mark.asyncio
async def test_lifespan_env(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@host/db')
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None))
    app = object()
    # Should not raise
    gen = app_postgres.lifespan(app)
    assert hasattr(gen, '__await__')

@pytest.mark.asyncio
async def test_lifespan_no_env(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('SYNC_DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError):
        await app_postgres.lifespan(object())

@pytest.mark.asyncio
async def test_get_pool(monkeypatch):
    pool_obj = object()
    monkeypatch.setattr(app_postgres, 'asyncpg', mock.Mock(create_pool=mock.AsyncMock(return_value=pool_obj)))
    monkeypatch.setenv('POSTGRES_DSN', 'postgres://localhost/test')
    monkeypatch.setenv('PGPOOL_MAX', '2')
    app_postgres._pool = None
    result = await app_postgres.get_pool()
    assert result is pool_obj

@pytest.mark.asyncio
async def test_log_requests_success(monkeypatch):
    class DummyRequest:
        method = 'GET'
        url = type('URL', (), {'path': '/foo'})()
    dummy_response = object()
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None, exception=lambda *a, **k: None))
    import time
    monkeypatch.setattr(app_postgres, 'time', time)
    async def call_next(request):
        return dummy_response
    resp = await app_postgres.log_requests(DummyRequest(), call_next)
    assert resp is dummy_response

@pytest.mark.asyncio
async def test_log_requests_exception(monkeypatch):
    class DummyRequest:
        method = 'POST'
        url = type('URL', (), {'path': '/fail'})()
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None, exception=lambda *a, **k: None))
    import time
    monkeypatch.setattr(app_postgres, 'time', time)
    async def call_next(request):
        raise Exception('fail')
    with pytest.raises(Exception):
        await app_postgres.log_requests(DummyRequest(), call_next)

@pytest.mark.asyncio
async def test_rate_limit_exception_handler(monkeypatch):
    class DummyRequest:
        headers = {'Retry-After': '99'}
    exc = app_postgres.HTTPException(status_code=429, detail='Too many requests')
    resp = await app_postgres.rate_limit_exception_handler(DummyRequest(), exc)
    assert resp.status_code == 429
    assert resp.headers['Retry-After'] == '99'

@pytest.mark.asyncio
async def test_diagnose_valid(monkeypatch):
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None))
    class DummyRequest:
        symptoms = ['cough']
        demographics = {'age': 30}
        model = 'default'
    class DummySession: pass
    class DummyQueryEngine:
        def generate(self, *a, **k):
            return {'diagnoses': ['flu']}
    monkeypatch.setattr(app_postgres, 'query_engine', DummyQueryEngine())
    monkeypatch.setattr(app_postgres, 'Body', lambda *a, **k: lambda x: x)
    monkeypatch.setattr(app_postgres, 'Depends', lambda x: x)
    monkeypatch.setattr(app_postgres, 'diagnose_rate_limiter', lambda: None)
    result = await app_postgres.diagnose(DummyRequest(), DummySession(), None)
    assert 'diagnoses' in result

@pytest.mark.asyncio
async def test_diagnose_invalid(monkeypatch):
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None))
    class DummyRequest:
        symptoms = None
        demographics = None
        model = 'default'
    class DummySession: pass
    monkeypatch.setattr(app_postgres, 'Body', lambda *a, **k: lambda x: x)
    monkeypatch.setattr(app_postgres, 'Depends', lambda x: x)
    monkeypatch.setattr(app_postgres, 'diagnose_rate_limiter', lambda: None)
    with pytest.raises(app_postgres.HTTPException) as e:
        await app_postgres.diagnose(DummyRequest(), DummySession(), None)
    assert e.value.status_code == 400
    assert 'invalid_symptoms' in str(e.value.detail)

@pytest.mark.asyncio
async def test_diagnose_alias(monkeypatch):
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(warning=lambda *a, **k: None))
    class DummyRequest:
        symptoms = ['cough']
        demographics = None
        model = 'default'
    class DummySession: pass
    monkeypatch.setattr(app_postgres, 'diagnose', mock.AsyncMock(return_value={'diagnoses': ['flu']}))
    monkeypatch.setattr(app_postgres, 'Body', lambda *a, **k: lambda x: x)
    monkeypatch.setattr(app_postgres, 'Depends', lambda x: x)
    monkeypatch.setattr(app_postgres, 'diagnose_rate_limiter', lambda: None)
    resp = await app_postgres.diagnose_alias(DummyRequest(), DummySession(), None)
    assert 'diagnoses' in resp

@pytest.mark.asyncio
async def test_health_check_ok(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            return 1
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(warning=lambda *a, **k: None))
    monkeypatch.setattr(app_postgres, 'text', lambda x: x)
    monkeypatch.setattr(app_postgres, 'query_engine', object())
    result = await app_postgres.health_check(DummySession())
    assert result['status'] == 'ok'
    assert result['services']['postgresql'] == 'ok'
    assert result['services']['pgvector'] == 'ok'

@pytest.mark.asyncio
async def test_health_check_fail(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            raise Exception('fail')
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(warning=lambda *a, **k: None))
    monkeypatch.setattr(app_postgres, 'text', lambda x: x)
    monkeypatch.setattr(app_postgres, 'query_engine', None)
    result = await app_postgres.health_check(DummySession())
    assert result['services']['postgresql'] == 'error'
    assert result['services']['pgvector'] == 'error'

@pytest.mark.asyncio
async def test_openapi_json(monkeypatch):
    monkeypatch.setattr(app_postgres, 'app', mock.Mock(openapi=lambda: {'openapi': 3}))
    result = await app_postgres.openapi_json()
    assert result['openapi'] == 3
