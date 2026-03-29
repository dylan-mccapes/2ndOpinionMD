try:
    import pytest
    from server.api import app_postgres
    from unittest import mock
    from fastapi import HTTPException, Request
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_lifespan_env(monkeypatch):
    monkeypatch.setenv('DATABASE_URL', 'postgresql://user:pass@host/db')
    class DummyApp: pass
    # Patch logger to avoid output
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None))
    # Should not raise
    try:
        await app_postgres.lifespan(DummyApp())
    except RuntimeError:
        pytest.fail('Should not raise RuntimeError when env is set')

@pytest.mark.asyncio
def test_lifespan_no_env(monkeypatch):
    monkeypatch.delenv('DATABASE_URL', raising=False)
    monkeypatch.delenv('SYNC_DATABASE_URL', raising=False)
    class DummyApp: pass
    with pytest.raises(RuntimeError):
        await app_postgres.lifespan(DummyApp())

@pytest.mark.asyncio
def test_get_pool(monkeypatch):
    monkeypatch.setattr(app_postgres, 'asyncpg', mock.Mock(create_pool=mock.AsyncMock(return_value='pool')))
    monkeypatch.setattr(app_postgres, '_pool', None)
    monkeypatch.setenv('POSTGRES_DSN', 'postgres://localhost/2ndopinionmd')
    monkeypatch.setenv('PGPOOL_MAX', '2')
    pool = await app_postgres.get_pool()
    assert pool == 'pool'

@pytest.mark.asyncio
def test_log_requests_success(monkeypatch):
    class DummyRequest:
        method = 'GET'
        url = type('url', (), {'path': '/test'})()
    async def call_next(request):
        class DummyResponse:
            pass
        return DummyResponse()
    logs = []
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: logs.append(a)))
    await app_postgres.log_requests(DummyRequest(), call_next)
    assert any('/test' in str(args) for args in logs)

@pytest.mark.asyncio
def test_log_requests_exception(monkeypatch):
    class DummyRequest:
        method = 'POST'
        url = type('url', (), {'path': '/fail'})()
    async def call_next(request):
        raise Exception('fail')
    errors = []
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None, exception=lambda *a, **k: errors.append(a)))
    with pytest.raises(Exception):
        await app_postgres.log_requests(DummyRequest(), call_next)
    assert errors

@pytest.mark.asyncio
def test_rate_limit_exception_handler(monkeypatch):
    class DummyRequest:
        headers = {'Retry-After': '33'}
    exc = HTTPException(status_code=429, detail='Too many requests')
    monkeypatch.setattr(app_postgres, 'status', mock.Mock(HTTP_429_TOO_MANY_REQUESTS=429))
    monkeypatch.setattr(app_postgres, 'JSONResponse', lambda **kwargs: kwargs)
    resp = await app_postgres.rate_limit_exception_handler(DummyRequest(), exc)
    assert resp['status_code'] == 429
    assert resp['headers']['Retry-After'] == '33'

@pytest.mark.asyncio
def test_diagnose_invalid_symptoms(monkeypatch):
    class DummyRequest:
        symptoms = None
        demographics = None
        model = None
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(info=lambda *a, **k: None))
    with pytest.raises(HTTPException) as exc:
        await app_postgres.diagnose(DummyRequest(), mock.Mock(), None)
    assert exc.value.status_code == 400
    assert 'invalid_symptoms' in str(exc.value.detail)

@pytest.mark.asyncio
def test_diagnose_alias(monkeypatch):
    class DummyRequest:
        symptoms = ['a']
        demographics = None
        model = None
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(warning=lambda *a, **k: None))
    async def fake_diagnose(request, session, _):
        return {'diagnoses': ['foo']}
    monkeypatch.setattr(app_postgres, 'diagnose', fake_diagnose)
    resp = await app_postgres.diagnose_alias(DummyRequest(), mock.Mock(), None)
    assert 'diagnoses' in resp

@pytest.mark.asyncio
def test_health_check_ok(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            return 1
    monkeypatch.setattr(app_postgres, 'query_engine', True)
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(warning=lambda *a, **k: None))
    resp = await app_postgres.health_check(DummySession())
    assert resp['status'] == 'ok'
    assert resp['services']['postgresql'] == 'ok'
    assert resp['services']['pgvector'] == 'ok'

@pytest.mark.asyncio
def test_health_check_fail(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            raise Exception('fail')
    monkeypatch.setattr(app_postgres, 'query_engine', False)
    monkeypatch.setattr(app_postgres, 'logger', mock.Mock(warning=lambda *a, **k: None))
    resp = await app_postgres.health_check(DummySession())
    assert resp['services']['postgresql'] == 'error'
    assert resp['services']['pgvector'] == 'error'

@pytest.mark.asyncio
def test_openapi_json(monkeypatch):
    monkeypatch.setattr(app_postgres, 'app', mock.Mock(openapi=lambda: {'openapi': True}))
    resp = await app_postgres.openapi_json()
    assert resp['openapi'] is True
