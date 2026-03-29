# AUTO-GENERATED TESTS for server/api/app_postgres.py
import pytest
try:
    from server.api import app_postgres
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

from unittest import mock
import os

@pytest.mark.asyncio
def test_lifespan_env(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@host/db')
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None))
    class DummyApp: pass
    # Should not raise
    pytest.run(asyncio_run=app_postgres.lifespan(DummyApp()))

@pytest.mark.asyncio
def test_lifespan_no_env(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('SYNC_DATABASE_URL', raising=False)
    with pytest.raises(RuntimeError):
        pytest.run(asyncio_run=app_postgres.lifespan(mock.Mock()))

@pytest.mark.asyncio
def test_get_pool_creates(monkeypatch):
    monkeypatch.setattr(app_postgres, 'asyncpg', mock.Mock(create_pool=mock.AsyncMock(return_value='pool')))
    monkeypatch.setattr(app_postgres, '_pool', None)
    monkeypatch.setenv('POSTGRES_DSN', 'postgres://localhost/2ndopinionmd')
    monkeypatch.setenv('PGPOOL_MAX', '2')
    result = pytest.run(asyncio_run=app_postgres.get_pool())
    assert result == 'pool'

@pytest.mark.asyncio
def test_log_requests_success(monkeypatch):
    class DummyRequest:
        method = 'GET'
        url = type('URL', (), {'path': '/foo'})()
    dummy_response = mock.Mock()
    async def call_next(request):
        return dummy_response
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None, exception=lambda *a, **k: None))
    result = pytest.run(asyncio_run=app_postgres.log_requests(DummyRequest(), call_next))
    assert result == dummy_response

@pytest.mark.asyncio
def test_log_requests_exception(monkeypatch):
    class DummyRequest:
        method = 'POST'
        url = type('URL', (), {'path': '/fail'})()
    async def call_next(request):
        raise Exception('fail')
    logs = []
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None, exception=lambda msg: logs.append(msg)))
    with pytest.raises(Exception):
        pytest.run(asyncio_run=app_postgres.log_requests(DummyRequest(), call_next))
    assert any('Unhandled error' in l for l in logs)

@pytest.mark.asyncio
def test_rate_limit_exception_handler(monkeypatch):
    class DummyRequest:
        headers = {'Retry-After': '99'}
    dummy_exc = mock.Mock(detail='Too many')
    monkeypatch.setattr(app_postgres, 'status', mock.Mock(HTTP_429_TOO_MANY_REQUESTS=429))
    monkeypatch.setattr(app_postgres, 'JSONResponse', lambda **kwargs: kwargs)
    result = pytest.run(asyncio_run=app_postgres.rate_limit_exception_handler(DummyRequest(), dummy_exc))
    assert result['status_code'] == 429
    assert result['content']['detail'] == 'Too many'
    assert result['headers']['Retry-After'] == '99'

@pytest.mark.asyncio
def test_diagnose_invalid_symptoms(monkeypatch):
    class DummyRequest:
        symptoms = None
        demographics = None
        model = None
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None))
    with pytest.raises(app_postgres.HTTPException) as exc:
        pytest.run(asyncio_run=app_postgres.diagnose(DummyRequest()))
    assert exc.value.status_code == 400
    assert 'invalid_symptoms' in str(exc.value.detail)

@pytest.mark.asyncio
def test_diagnose_alias(monkeypatch):
    class DummyRequest:
        symptoms = ['a']
        demographics = None
        model = None
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(warning=lambda *a, **k: None))
    async def fake_diagnose(request, session, none):
        return {'diagnoses': ['foo']}
    monkeypatch.setattr(app_postgres, 'diagnose', fake_diagnose)
    result = pytest.run(asyncio_run=app_postgres.diagnose_alias(DummyRequest(), None, None))
    assert isinstance(result, dict)
    assert 'diagnoses' in result

@pytest.mark.asyncio
def test_health_check_ok(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            return None
    monkeypatch.setattr(app_postgres, 'query_engine', True)
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(warning=lambda *a, **k: None))
    result = pytest.run(asyncio_run=app_postgres.health_check(DummySession()))
    assert result['status'] == 'ok'
    assert result['services']['postgresql'] == 'ok'
    assert result['services']['pgvector'] == 'ok'

@pytest.mark.asyncio
def test_openapi_json(monkeypatch):
    monkeypatch.setattr(app_postgres, 'app', mock.Mock(openapi=lambda: {'openapi': 1}))
    result = pytest.run(asyncio_run=app_postgres.openapi_json())
    assert result == {'openapi': 1}
