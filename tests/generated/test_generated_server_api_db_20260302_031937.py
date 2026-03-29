# Auto-generated tests for server.api.db
import pytest
import sys
from unittest import mock

try:
    import asyncio
    from server.api import db as db_mod
except ImportError:
    pytest.skip('server.api.db import failed', allow_module_level=True)

@pytest.mark.asyncio
async def test_init_pool_creates_pool(monkeypatch):
    called = {}
    async def fake_create_pool(**kwargs):
        called['args'] = kwargs
        return 'poolobj'
    monkeypatch.setattr(db_mod, '_pool', None)
    monkeypatch.setattr(db_mod, '_dsn_asyncpg', lambda: 'dsnval')
    monkeypatch.setattr('server.api.db.asyncpg.create_pool', fake_create_pool)
    pool = await db_mod.init_pool(min_size=2, max_size=5)
    assert pool == 'poolobj'
    assert called['args']['dsn'] == 'dsnval'
    assert called['args']['min_size'] == 2
    assert called['args']['max_size'] == 5

@pytest.mark.asyncio
async def test_init_pool_raises_if_no_dsn(monkeypatch):
    monkeypatch.setattr(db_mod, '_pool', None)
    monkeypatch.setattr(db_mod, '_dsn_asyncpg', lambda: None)
    with pytest.raises(RuntimeError):
        await db_mod.init_pool()

def test_get_pool_returns_pool(monkeypatch):
    monkeypatch.setattr(db_mod, '_pool', 'poolval')
    assert db_mod.get_pool() == 'poolval'

@pytest.mark.asyncio
async def test_close_pool_closes_and_resets(monkeypatch):
    class DummyPool:
        def __init__(self):
            self.closed = False
        async def close(self):
            self.closed = True
    dummy = DummyPool()
    monkeypatch.setattr(db_mod, '_pool', dummy)
    await db_mod.close_pool()
    assert dummy.closed
    assert db_mod._pool is None

@pytest.mark.asyncio
async def test_close_pool_noop_if_none(monkeypatch):
    monkeypatch.setattr(db_mod, '_pool', None)
    await db_mod.close_pool()
    assert db_mod._pool is None

@pytest.mark.asyncio
async def test_get_conn_acquires(monkeypatch):
    class DummyPool:
        async def acquire(self):
            return 'connobj'
    async def fake_init_pool():
        return DummyPool()
    monkeypatch.setattr(db_mod, 'init_pool', fake_init_pool)
    conn = await db_mod.get_conn()
    assert conn == 'connobj'

@pytest.mark.asyncio
async def test_put_conn_releases(monkeypatch):
    class DummyPool:
        def __init__(self):
            self.released = None
        async def release(self, conn):
            self.released = conn
    dummy = DummyPool()
    monkeypatch.setattr(db_mod, 'get_pool', lambda: dummy)
    await db_mod.put_conn('abc')
    assert dummy.released == 'abc'

@pytest.mark.asyncio
async def test_put_conn_noop_if_none(monkeypatch):
    monkeypatch.setattr(db_mod, 'get_pool', lambda: None)
    # Should not raise
    await db_mod.put_conn(None)

@pytest.mark.asyncio
async def test_connection_yields_and_releases(monkeypatch):
    class DummyConn: pass
    dummy_conn = DummyConn()
    called = {}
    async def fake_get_conn():
        called['got'] = True
        return dummy_conn
    async def fake_put_conn(conn):
        called['released'] = conn
    monkeypatch.setattr(db_mod, 'get_conn', fake_get_conn)
    monkeypatch.setattr(db_mod, 'put_conn', fake_put_conn)
    gen = db_mod.connection()
    conn = await gen.__anext__()
    assert conn is dummy_conn
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()
    assert called['released'] is dummy_conn

@pytest.mark.asyncio
async def test_fetch_calls_fetch(monkeypatch):
    class DummyConn:
        async def fetch(self, sql, *args):
            return ['row1', 'row2']
    class DummyAcquire:
        async def __aenter__(self): return DummyConn()
        async def __aexit__(self, exc_type, exc, tb): pass
    class DummyPool:
        def acquire(self): return DummyAcquire()
    async def fake_init_pool(): return DummyPool()
    monkeypatch.setattr(db_mod, 'init_pool', fake_init_pool)
    rows = await db_mod.fetch('SELECT 1', 123)
    assert rows == ['row1', 'row2']

@pytest.mark.asyncio
async def test_fetchrow_calls_fetchrow(monkeypatch):
    class DummyConn:
        async def fetchrow(self, sql, *args):
            return {'a': 1}
    class DummyAcquire:
        async def __aenter__(self): return DummyConn()
        async def __aexit__(self, exc_type, exc, tb): pass
    class DummyPool:
        def acquire(self): return DummyAcquire()
    async def fake_init_pool(): return DummyPool()
    monkeypatch.setattr(db_mod, 'init_pool', fake_init_pool)
    row = await db_mod.fetchrow('SELECT 1', 123)
    assert row == {'a': 1}

@pytest.mark.asyncio
async def test_execute_calls_execute(monkeypatch):
    class DummyConn:
        async def execute(self, sql, *args):
            return 'ok'
    class DummyAcquire:
        async def __aenter__(self): return DummyConn()
        async def __aexit__(self, exc_type, exc, tb): pass
    class DummyPool:
        def acquire(self): return DummyAcquire()
    async def fake_init_pool(): return DummyPool()
    monkeypatch.setattr(db_mod, 'init_pool', fake_init_pool)
    res = await db_mod.execute('UPDATE x', 1)
    assert res == 'ok'

@pytest.mark.asyncio
async def test_get_async_session_yields_session(monkeypatch):
    class DummySession:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
    monkeypatch.setattr(db_mod, 'AsyncSessionLocal', lambda: DummySession())
    gen = db_mod.get_async_session()
    session = await gen.__anext__()
    assert isinstance(session, DummySession)
    with pytest.raises(StopAsyncIteration):
        await gen.__anext__()

def test_pg_read_returns_rows(monkeypatch):
    class DummyCursor:
        def execute(self, sql, params):
            self.sql = sql
            self.params = params
        def fetchall(self):
            return [{'a': 1}]
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): pass
    class DummyConn:
        def cursor(self, cursor_factory=None): return DummyCursor()
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): pass
    monkeypatch.setattr(db_mod, '_dsn_sync', lambda: 'dsn')
    monkeypatch.setattr('server.api.db.psycopg2.connect', lambda dsn: DummyConn())
    rows = db_mod.pg_read('SELECT', ('x',))
    assert rows == [{'a': 1}]