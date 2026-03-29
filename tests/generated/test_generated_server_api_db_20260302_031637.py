import pytest
from unittest import mock

try:
    import asyncio
    import pytest_asyncio
    from server.api import db
except ImportError:
    db = None

@pytest.mark.asyncio
@pytest.mark.skipif(db is None, reason="Module not importable")
async def test_init_pool(monkeypatch):
    fake_pool = object()
    monkeypatch.setattr(db, "_pool", None)
    monkeypatch.setattr(db, "_dsn_asyncpg", lambda: "dsn")
    monkeypatch.setattr("server.api.db.asyncpg.create_pool", mock.AsyncMock(return_value=fake_pool))
    result = await db.init_pool()
    assert result is fake_pool

@pytest.mark.skipif(db is None, reason="Module not importable")
def test_get_pool(monkeypatch):
    fake_pool = object()
    monkeypatch.setattr(db, "_pool", fake_pool)
    assert db.get_pool() is fake_pool

@pytest.mark.asyncio
@pytest.mark.skipif(db is None, reason="Module not importable")
async def test_close_pool(monkeypatch):
    fake_pool = mock.AsyncMock()
    monkeypatch.setattr(db, "_pool", fake_pool)
    await db.close_pool()
    assert db._pool is None

@pytest.mark.asyncio
@pytest.mark.skipif(db is None, reason="Module not importable")
async def test_get_conn(monkeypatch):
    fake_pool = mock.AsyncMock()
    fake_pool.acquire = mock.AsyncMock(return_value="conn")
    monkeypatch.setattr(db, "init_pool", mock.AsyncMock(return_value=fake_pool))
    result = await db.get_conn()
    assert result == "conn"

@pytest.mark.asyncio
@pytest.mark.skipif(db is None, reason="Module not importable")
async def test_put_conn(monkeypatch):
    fake_pool = mock.AsyncMock()
    fake_pool.release = mock.AsyncMock()
    monkeypatch.setattr(db, "get_pool", lambda: fake_pool)
    await db.put_conn("conn")
    fake_pool.release.assert_awaited_with("conn")

@pytest.mark.asyncio
@pytest.mark.skipif(db is None, reason="Module not importable")
async def test_connection(monkeypatch):
    async def fake_get_conn(): return "conn"
    async def fake_put_conn(conn): nonlocal_called.append(conn)
    nonlocal_called = []
    monkeypatch.setattr(db, "get_conn", fake_get_conn)
    monkeypatch.setattr(db, "put_conn", fake_put_conn)
    gen = db.connection()
    conn = await gen.__anext__()
    assert conn == "conn"
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass
    assert nonlocal_called == ["conn"]

@pytest.mark.asyncio
@pytest.mark.skipif(db is None, reason="Module not importable")
async def test_fetch(monkeypatch):
    fake_conn = mock.AsyncMock()
    fake_conn.fetch = mock.AsyncMock(return_value=[{"a": 1}])
    fake_pool = mock.AsyncMock()
    fake_pool.acquire = mock.AsyncMock()
    fake_pool.acquire.__aenter__ = mock.AsyncMock(return_value=fake_conn)
    fake_pool.acquire.__aexit__ = mock.AsyncMock(return_value=None)
    monkeypatch.setattr(db, "init_pool", mock.AsyncMock(return_value=fake_pool))
    result = await db.fetch("sql")
    assert result == [{"a": 1}]

@pytest.mark.asyncio
@pytest.mark.skipif(db is None, reason="Module not importable")
async def test_fetchrow(monkeypatch):
    fake_conn = mock.AsyncMock()
    fake_conn.fetchrow = mock.AsyncMock(return_value={"a": 1})
    fake_pool = mock.AsyncMock()
    fake_pool.acquire = mock.AsyncMock()
    fake_pool.acquire.__aenter__ = mock.AsyncMock(return_value=fake_conn)
    fake_pool.acquire.__aexit__ = mock.AsyncMock(return_value=None)
    monkeypatch.setattr(db, "init_pool", mock.AsyncMock(return_value=fake_pool))
    result = await db.fetchrow("sql")
    assert result == {"a": 1}

@pytest.mark.asyncio
@pytest.mark.skipif(db is None, reason="Module not importable")
async def test_execute(monkeypatch):
    fake_conn = mock.AsyncMock()
    fake_conn.execute = mock.AsyncMock(return_value="OK")
    fake_pool = mock.AsyncMock()
    fake_pool.acquire = mock.AsyncMock()
    fake_pool.acquire.__aenter__ = mock.AsyncMock(return_value=fake_conn)
    fake_pool.acquire.__aexit__ = mock.AsyncMock(return_value=None)
    monkeypatch.setattr(db, "init_pool", mock.AsyncMock(return_value=fake_pool))
    result = await db.execute("sql")
    assert result == "OK"

@pytest.mark.asyncio
@pytest.mark.skipif(db is None, reason="Module not importable")
async def test_get_async_session(monkeypatch):
    class FakeSession:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): pass
    monkeypatch.setattr(db, "AsyncSessionLocal", lambda: FakeSession())
    gen = db.get_async_session()
    session = await gen.__anext__()
    assert isinstance(session, FakeSession)
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass

@pytest.mark.skipif(db is None, reason="Module not importable")
def test_pg_read(monkeypatch):
    fake_conn = mock.Mock()
    fake_cursor = mock.Mock()
    fake_cursor.fetchall.return_value = [{"a": 1}]
    fake_conn.cursor.return_value.__enter__.return_value = fake_cursor
    monkeypatch.setattr(db, "_dsn_sync", lambda: "dsn")
    monkeypatch.setattr("server.api.db.psycopg2.connect", mock.Mock(return_value=fake_conn))
    result = db.pg_read("sql")
    assert result == [{"a": 1}]
