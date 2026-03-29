import pytest
try:
    from server.api import db
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock
import types
import sys

@pytest.mark.asyncio
def test_init_pool_creates_pool(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    monkeypatch.setattr(db, '_pool', None)
    monkeypatch.setattr(db, '_dsn_asyncpg', lambda: 'dsn')
    dummy_pool = mock.AsyncMock()
    monkeypatch.setattr('asyncpg.create_pool', mock.AsyncMock(return_value=dummy_pool))
    pool = pytest.run(db.init_pool())
    assert pool is dummy_pool


def test_get_pool_returns_pool(monkeypatch):
    dummy = object()
    monkeypatch.setattr(db, '_pool', dummy)
    assert db.get_pool() is dummy

@pytest.mark.asyncio
def test_close_pool_closes(monkeypatch):
    dummy_pool = mock.AsyncMock()
    monkeypatch.setattr(db, '_pool', dummy_pool)
    pytest.run(db.close_pool())
    assert db._pool is None

@pytest.mark.asyncio
def test_get_conn_acquires(monkeypatch):
    dummy_pool = mock.AsyncMock()
    dummy_pool.acquire = mock.AsyncMock(return_value='conn')
    monkeypatch.setattr(db, 'init_pool', mock.AsyncMock(return_value=dummy_pool))
    conn = pytest.run(db.get_conn())
    assert conn == 'conn'

@pytest.mark.asyncio
def test_put_conn_releases(monkeypatch):
    dummy_pool = mock.AsyncMock()
    dummy_pool.release = mock.AsyncMock()
    monkeypatch.setattr(db, 'get_pool', lambda: dummy_pool)
    pytest.run(db.put_conn('conn'))
    dummy_pool.release.assert_called_with('conn')

@pytest.mark.asyncio
def test_connection_yields_and_puts(monkeypatch):
    dummy_conn = object()
    monkeypatch.setattr(db, 'get_conn', mock.AsyncMock(return_value=dummy_conn))
    monkeypatch.setattr(db, 'put_conn', mock.AsyncMock())
    async def run():
        gen = db.connection()
        conn = await gen.__anext__()
        assert conn is dummy_conn
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()
    pytest.run(run())

@pytest.mark.asyncio
def test_fetch(monkeypatch):
    dummy_pool = mock.AsyncMock()
    dummy_conn = mock.AsyncMock()
    dummy_conn.fetch = mock.AsyncMock(return_value=[{"a": 1}])
    dummy_pool.acquire = mock.AsyncMock()
    dummy_pool.acquire.__aenter__ = mock.AsyncMock(return_value=dummy_conn)
    dummy_pool.acquire.__aexit__ = mock.AsyncMock(return_value=None)
    monkeypatch.setattr(db, 'init_pool', mock.AsyncMock(return_value=dummy_pool))
    result = pytest.run(db.fetch('sql'))
    assert result == [{"a": 1}]

@pytest.mark.asyncio
def test_fetchrow(monkeypatch):
    dummy_pool = mock.AsyncMock()
    dummy_conn = mock.AsyncMock()
    dummy_conn.fetchrow = mock.AsyncMock(return_value={"a": 2})
    dummy_pool.acquire = mock.AsyncMock()
    dummy_pool.acquire.__aenter__ = mock.AsyncMock(return_value=dummy_conn)
    dummy_pool.acquire.__aexit__ = mock.AsyncMock(return_value=None)
    monkeypatch.setattr(db, 'init_pool', mock.AsyncMock(return_value=dummy_pool))
    result = pytest.run(db.fetchrow('sql'))
    assert result == {"a": 2}

@pytest.mark.asyncio
def test_execute(monkeypatch):
    dummy_pool = mock.AsyncMock()
    dummy_conn = mock.AsyncMock()
    dummy_conn.execute = mock.AsyncMock(return_value='OK')
    dummy_pool.acquire = mock.AsyncMock()
    dummy_pool.acquire.__aenter__ = mock.AsyncMock(return_value=dummy_conn)
    dummy_pool.acquire.__aexit__ = mock.AsyncMock(return_value=None)
    monkeypatch.setattr(db, 'init_pool', mock.AsyncMock(return_value=dummy_pool))
    result = pytest.run(db.execute('sql'))
    assert result == 'OK'

@pytest.mark.asyncio
def test_get_async_session(monkeypatch):
    class DummySession:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
    monkeypatch.setattr(db, 'AsyncSessionLocal', lambda: DummySession())
    async def run():
        gen = db.get_async_session()
        session = await gen.__anext__()
        assert isinstance(session, DummySession)
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()
    pytest.run(run())

def test_pg_read(monkeypatch):
    dummy_conn = mock.MagicMock()
    dummy_cursor = mock.MagicMock()
    dummy_cursor.fetchall.return_value = [{"a": 1}]
    dummy_conn.cursor.return_value.__enter__.return_value = dummy_cursor
    monkeypatch.setattr(db, '_dsn_sync', lambda: 'dsn')
    monkeypatch.setattr('psycopg2.connect', lambda dsn: dummy_conn)
    result = db.pg_read('sql')
    assert result == [{"a": 1}]
