try:
    import pytest
    from unittest import mock
    from server.ann import index_builder
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)


def test_get_create_index_sql_hnsw(monkeypatch):
    monkeypatch.setattr(index_builder, 'HNSW_CONFIG', {'distance_metric': 'cosine', 'm': 16, 'ef_construction': 200, 'ef_search': 32})
    sql = index_builder.get_create_index_sql('idx_test', 'tbl', 'col', 'hnsw')
    assert 'CREATE INDEX' in sql
    assert 'USING hnsw' in sql
    assert 'idx_test' in sql
    assert 'tbl' in sql
    assert 'col' in sql


def test_get_create_index_sql_ivfflat(monkeypatch):
    monkeypatch.setattr(index_builder, 'HNSW_CONFIG', {'distance_metric': 'cosine', 'm': 16, 'ef_construction': 200, 'ef_search': 32})
    monkeypatch.setattr(index_builder, 'IVFFLAT_CONFIG', {'distance_metric': 'l2', 'lists': 100})
    sql = index_builder.get_create_index_sql('idx_ivf', 'tbl', 'col', 'ivfflat')
    assert 'USING ivfflat' in sql or 'ivfflat' in sql
    assert 'idx_ivf' in sql


def test_get_drop_index_sql():
    sql = index_builder.get_drop_index_sql('idx_test')
    assert sql == 'DROP INDEX IF EXISTS idx_test;'


def test_get_set_ef_search_sql(monkeypatch):
    monkeypatch.setattr(index_builder, 'HNSW_CONFIG', {'ef_search': 42})
    sql = index_builder.get_set_ef_search_sql()
    assert 'SET hnsw.ef_search = 42' in sql

@pytest.mark.asyncio
async def test_build_index(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            return None
        async def commit(self):
            return None
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda *a, **kw: 'CREATE INDEX ...')
    monkeypatch.setattr(index_builder, 'get_drop_index_sql', lambda *a, **kw: 'DROP INDEX ...')
    monkeypatch.setattr(index_builder, 'get_set_ef_search_sql', lambda: 'SET ...')
    session = DummySession()
    result = await index_builder.build_index(session, 'idx', 'tbl', 'col', 'hnsw', force_rebuild=True)
    assert result['index_name'] == 'idx'
    assert 'status' in result

@pytest.mark.asyncio
async def test_check_index_health(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            class DummyResult:
                def fetchall(self):
                    return [("idx", "CREATE INDEX ...")]
            return DummyResult()
    session = DummySession()
    monkeypatch.setattr(index_builder, 'logger', mock.Mock())
    result = await index_builder.check_index_health(session, 'idx')
    assert result['index_name'] == 'idx'
    assert 'exists' in result
    assert 'healthy' in result

@pytest.mark.asyncio
async def test_rebuild_if_corrupted(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            return None
        async def commit(self):
            return None
    monkeypatch.setattr(index_builder, 'logger', mock.Mock())
    monkeypatch.setattr(index_builder, 'check_index_health', mock.AsyncMock(return_value={'exists': True, 'healthy': False, 'index_name': 'idx', 'details': {}}))
    monkeypatch.setattr(index_builder, 'build_index', mock.AsyncMock(return_value={'rebuilt': True, 'index_name': 'idx'}))
    session = DummySession()
    result = await index_builder.rebuild_if_corrupted(session, 'idx', 'tbl', 'col')
    assert result['index_name'] == 'idx'
    assert 'rebuilt' in result or 'status' in result

def test_build_index_sync(monkeypatch):
    class DummyConn:
        def cursor(self):
            class DummyCursor:
                def execute(self, sql):
                    return None
                def close(self):
                    return None
            return DummyCursor()
        def commit(self):
            return None
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda *a, **kw: 'CREATE INDEX ...')
    monkeypatch.setattr(index_builder, 'get_drop_index_sql', lambda *a, **kw: 'DROP INDEX ...')
    monkeypatch.setattr(index_builder, 'get_set_ef_search_sql', lambda: 'SET ...')
    conn = DummyConn()
    result = index_builder.build_index_sync(conn, 'idx', 'tbl', 'col', 'hnsw', force_rebuild=True)
    assert result['index_name'] == 'idx'
    assert 'status' in result

def test_get_all_index_sql(monkeypatch):
    monkeypatch.setattr(index_builder, 'INDEX_DEFINITIONS', {'idx1': {'table': 'tbl', 'column': 'col', 'type': 'hnsw'}})
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda *a, **kw: 'CREATE INDEX ...')
    monkeypatch.setattr(index_builder, 'get_set_ef_search_sql', lambda: 'SET ...')
    sql = index_builder.get_all_index_sql()
    assert 'CREATE INDEX' in sql
    assert 'SET' in sql
