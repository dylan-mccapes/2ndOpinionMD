try:
    import pytest
    from server.api import db
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

from unittest import mock
import types

@pytest.mark.asyncio
async def test_init_pool(monkeypatch):
    monkeypatch.setattr(db, "_pool", None)
    monkeypatch.setattr(db, "_dsn_asyncpg", lambda: "dsn")
    class DummyPool:
        pass
    async def create_pool(dsn, min_size, max_size):
        return DummyPool()
    monkeypatch.setattr("server.api.db.asyncpg", mock.Mock(create_pool=create_pool))
    pool = await db.init_pool()
    assert pool is not None

def test_get_pool(monkeypatch):
    dummy = object()
    monkeypatch.setattr(db, "_pool", dummy)
    assert db.get_pool() is dummy

@pytest.mark.asyncio
async def test_close_pool(monkeypatch):
    class DummyPool:
        async def close(self):
            self.closed = True
    dummy = DummyPool()
    monkeypatch.setattr(db, "_pool", dummy)
    await db.close_pool()
    assert getattr(dummy, "closed", False)
    assert db._pool is None

@pytest.mark.asyncio
async def test_get_conn(monkeypatch):
    class DummyPool:
        async def acquire(self):
            return "conn"
    async def fake_init_pool():
        return DummyPool()
    monkeypatch.setattr(db, "init_pool", fake_init_pool)
    conn = await db.get_conn()
    assert conn == "conn"

@pytest.mark.asyncio
async def test_put_conn(monkeypatch):
    class DummyPool:
        async def release(self, conn):
            self.released = conn
    dummy = DummyPool()
    monkeypatch.setattr(db, "get_pool", lambda: dummy)
    await db.put_conn("abc")
    assert getattr(dummy, "released", None) == "abc"

@pytest.mark.asyncio
async def test_connection_context(monkeypatch):
    class DummyConn:
        pass
    async def fake_get_conn():
        return DummyConn()
    async def fake_put_conn(conn):
        fake_put_conn.called = True
    monkeypatch.setattr(db, "get_conn", fake_get_conn)
    monkeypatch.setattr(db, "put_conn", fake_put_conn)
    gen = db.connection()
    conn = await gen.__anext__()
    assert isinstance(conn, DummyConn)
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass
    assert getattr(fake_put_conn, "called", False)

@pytest.mark.asyncio
async def test_fetch(monkeypatch):
    class DummyConn:
        async def fetch(self, sql, *args):
            return [1,2,3]
    class DummyPool:
        async def acquire(self):
            class DummyContext:
                async def __aenter__(self): return DummyConn()
                async def __aexit__(self, exc_type, exc, tb): return False
            return DummyContext()
    async def fake_init_pool():
        return DummyPool()
    monkeypatch.setattr(db, "init_pool", fake_init_pool)
    result = await db.fetch("sql")
    assert result == [1,2,3]

@pytest.mark.asyncio
async def test_fetchrow(monkeypatch):
    class DummyConn:
        async def fetchrow(self, sql, *args):
            return {"row": 1}
    class DummyPool:
        async def acquire(self):
            class DummyContext:
                async def __aenter__(self): return DummyConn()
                async def __aexit__(self, exc_type, exc, tb): return False
            return DummyContext()
    async def fake_init_pool():
        return DummyPool()
    monkeypatch.setattr(db, "init_pool", fake_init_pool)
    result = await db.fetchrow("sql")
    assert result == {"row": 1}

@pytest.mark.asyncio
async def test_execute(monkeypatch):
    class DummyConn:
        async def execute(self, sql, *args):
            return "ok"
    class DummyPool:
        async def acquire(self):
            class DummyContext:
                async def __aenter__(self): return DummyConn()
                async def __aexit__(self, exc_type, exc, tb): return False
            return DummyContext()
    async def fake_init_pool():
        return DummyPool()
    monkeypatch.setattr(db, "init_pool", fake_init_pool)
    result = await db.execute("sql")
    assert result == "ok"

@pytest.mark.asyncio
async def test_get_async_session(monkeypatch):
    class DummySession:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
    monkeypatch.setattr(db, "AsyncSessionLocal", lambda: DummySession())
    gen = db.get_async_session()
    session = await gen.__anext__()
    assert session is not None
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass

def test_pg_read(monkeypatch):
    class DummyCursor:
        def execute(self, sql, params):
            self.executed = (sql, params)
        def fetchall(self):
            return [{"a": 1}]
    class DummyConn:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
        def cursor(self, cursor_factory=None): return DummyCursor()
    class DummyPsycopg2:
        def connect(self, dsn): return DummyConn()
    monkeypatch.setattr(db, "_dsn_sync", lambda: "dsn")
    monkeypatch.setattr(db, "psycopg2", DummyPsycopg2())
    monkeypatch.setattr(db, "RealDictCursor", object())
    result = db.pg_read("SELECT 1", params=(1,))
    assert isinstance(result, list)
    assert result[0]["a"] == 1
