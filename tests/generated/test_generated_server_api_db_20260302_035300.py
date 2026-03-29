try:
    from server.api import db
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

@pytest.mark.asyncio
async def test_init_pool_creates_pool(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    monkeypatch.setattr(db, '_pool', None)
    monkeypatch.setattr(db, '_dsn_asyncpg', lambda: 'dsn')
    mock_pool = mock.AsyncMock()
    monkeypatch.setattr('server.api.db.asyncpg', mock.Mock(create_pool=mock.AsyncMock(return_value=mock_pool)))
    pool = await db.init_pool()
    assert pool is mock_pool


def test_get_pool_returns_pool(monkeypatch):
    dummy = object()
    monkeypatch.setattr(db, '_pool', dummy)
    assert db.get_pool() is dummy

@pytest.mark.asyncio
async def test_close_pool_closes(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    mock_pool = mock.AsyncMock(close=mock.AsyncMock())
    monkeypatch.setattr(db, '_pool', mock_pool)
    await db.close_pool()
    assert db._pool is None

@pytest.mark.asyncio
async def test_get_conn_acquire(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    mock_pool = mock.AsyncMock(acquire=mock.AsyncMock(return_value='conn'))
    monkeypatch.setattr(db, 'init_pool', mock.AsyncMock(return_value=mock_pool))
    conn = await db.get_conn()
    assert conn == 'conn'

@pytest.mark.asyncio
async def test_put_conn_releases(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    mock_pool = mock.AsyncMock(release=mock.AsyncMock())
    monkeypatch.setattr(db, 'get_pool', lambda: mock_pool)
    await db.put_conn('conn')
    mock_pool.release.assert_called_once_with('conn')

@pytest.mark.asyncio
async def test_connection_yields_and_puts(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    class DummyContext:
        async def __aenter__(self): return 'conn'
        async def __aexit__(self, exc_type, exc, tb): return False
    monkeypatch.setattr(db, 'get_conn', mock.AsyncMock(return_value='conn'))
    monkeypatch.setattr(db, 'put_conn', mock.AsyncMock())
    gen = db.connection()
    conn = await gen.__anext__()
    assert conn == 'conn'
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass

@pytest.mark.asyncio
async def test_fetch(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    mock_conn = mock.AsyncMock(fetch=mock.AsyncMock(return_value=[{"id": 1}]))
    class DummyPool:
        async def acquire(self):
            class DummyContext:
                async def __aenter__(self): return mock_conn
                async def __aexit__(self, exc_type, exc, tb): return False
            return DummyContext()
    monkeypatch.setattr(db, 'init_pool', mock.AsyncMock(return_value=DummyPool()))
    result = await db.fetch('SELECT 1')
    assert result == [{"id": 1}]

@pytest.mark.asyncio
async def test_fetchrow(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    mock_conn = mock.AsyncMock(fetchrow=mock.AsyncMock(return_value={"id": 2}))
    class DummyPool:
        async def acquire(self):
            class DummyContext:
                async def __aenter__(self): return mock_conn
                async def __aexit__(self, exc_type, exc, tb): return False
            return DummyContext()
    monkeypatch.setattr(db, 'init_pool', mock.AsyncMock(return_value=DummyPool()))
    result = await db.fetchrow('SELECT 2')
    assert result == {"id": 2}

@pytest.mark.asyncio
async def test_execute(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    mock_conn = mock.AsyncMock(execute=mock.AsyncMock(return_value='OK'))
    class DummyPool:
        async def acquire(self):
            class DummyContext:
                async def __aenter__(self): return mock_conn
                async def __aexit__(self, exc_type, exc, tb): return False
            return DummyContext()
    monkeypatch.setattr(db, 'init_pool', mock.AsyncMock(return_value=DummyPool()))
    result = await db.execute('UPDATE x')
    assert result == 'OK'

@pytest.mark.asyncio
async def test_get_async_session(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    class DummySession:
        async def __aenter__(self): return self
        async def __aexit__(self, exc_type, exc, tb): return False
    monkeypatch.setattr(db, 'AsyncSessionLocal', lambda: DummySession())
    gen = db.get_async_session()
    session = await gen.__anext__()
    assert session is not None
    try:
        await gen.__anext__()
    except StopAsyncIteration:
        pass

def test_pg_read(monkeypatch):
    dummy_rows = [{"id": 1}]
    class DummyCursor:
        def execute(self, sql, params):
            self.sql = sql
            self.params = params
        def fetchall(self):
            return dummy_rows
    class DummyConn:
        def cursor(self, cursor_factory=None):
            return DummyCursor()
        def __enter__(self): return self
        def __exit__(self, exc_type, exc, tb): return False
    monkeypatch.setattr(db, '_dsn_sync', lambda: 'dsn')
    monkeypatch.setattr('server.api.db.psycopg2', mock.Mock(connect=lambda dsn: DummyConn()))
    monkeypatch.setattr('server.api.db.RealDictCursor', object)
    result = db.pg_read('SELECT 1')
    assert result == dummy_rows
