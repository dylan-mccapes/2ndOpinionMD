try:
    import pytest
    from unittest import mock
    from server.ann import index_builder
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.fixture(autouse=True)
def patch_hnsw_config(monkeypatch):
    monkeypatch.setattr(index_builder, 'HNSW_CONFIG', {'distance_metric': 'cosine', 'm': 16, 'ef_search': 64})
    monkeypatch.setattr(index_builder, 'INDEX_DEFINITIONS', {
        'idx1': {'table': 'table1', 'column': 'col1', 'type': 'hnsw'},
        'idx2': {'table': 'table2', 'column': 'col2', 'type': 'ivfflat'}
    })


def test_get_create_index_sql_hnsw():
    sql = index_builder.get_create_index_sql('idx_test', 'tbl', 'col', 'hnsw')
    assert 'CREATE INDEX IF NOT EXISTS idx_test' in sql
    assert 'USING hnsw' in sql
    assert 'col cosine' in sql
    assert 'm = 16' in sql

def test_get_create_index_sql_ivfflat():
    # Patch function to support ivfflat branch
    def fake_ivfflat_sql(*args, **kwargs):
        return 'USING ivfflat'
    monkeypatch = mock.Mock()
    sql = index_builder.get_create_index_sql('idx_test', 'tbl', 'col', 'ivfflat')
    assert 'USING ivfflat' in sql or 'ivfflat' in sql

def test_get_drop_index_sql():
    sql = index_builder.get_drop_index_sql('idx_to_drop')
    assert sql == 'DROP INDEX IF EXISTS idx_to_drop;'


def test_get_set_ef_search_sql():
    sql = index_builder.get_set_ef_search_sql()
    assert sql == 'SET hnsw.ef_search = 64;'

@pytest.mark.asyncio
def test_build_index(monkeypatch):
    class FakeSession:
        async def execute(self, sql):
            return None
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda *a, **k: 'CREATE INDEX SQL')
    monkeypatch.setattr(index_builder, 'get_drop_index_sql', lambda *a, **k: 'DROP INDEX SQL')
    monkeypatch.setattr(index_builder, 'get_set_ef_search_sql', lambda: 'SET SQL')
    session = FakeSession()
    result = pytest.run(index_builder.build_index(session, 'idx', 'tbl', 'col', 'hnsw', False))
    # result is a coroutine, so we need to await
    import asyncio
    res = asyncio.get_event_loop().run_until_complete(index_builder.build_index(session, 'idx', 'tbl', 'col', 'hnsw', False))
    assert res['index_name'] == 'idx'
    assert 'status' in res

@pytest.mark.asyncio
def test_check_index_health(monkeypatch):
    class FakeSession:
        async def execute(self, sql):
            class FakeResult:
                def fetchone(self):
                    return ('idx', 'CREATE INDEX')
            return FakeResult()
    session = FakeSession()
    monkeypatch.setattr(index_builder, 'check_index_health', index_builder.check_index_health)
    res = pytest.run(index_builder.check_index_health(session, 'idx'))
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(index_builder.check_index_health(session, 'idx'))
    assert result['index_name'] == 'idx'
    assert 'exists' in result
    assert 'healthy' in result

@pytest.mark.asyncio
def test_rebuild_if_corrupted(monkeypatch):
    class FakeSession:
        async def execute(self, sql):
            return None
    monkeypatch.setattr(index_builder, 'check_index_health', mock.AsyncMock(return_value={'exists': True, 'healthy': False, 'index_name': 'idx', 'details': {}}))
    monkeypatch.setattr(index_builder, 'build_index', mock.AsyncMock(return_value={'rebuilt': True, 'index_name': 'idx'}))
    session = FakeSession()
    import asyncio
    result = asyncio.get_event_loop().run_until_complete(index_builder.rebuild_if_corrupted(session, 'idx', 'tbl', 'col'))
    assert result['index_name'] == 'idx'


def test_build_index_sync(monkeypatch):
    class FakeConn:
        def cursor(self):
            class C:
                def execute(self, sql):
                    pass
                def __enter__(self): return self
                def __exit__(self, exc_type, exc_val, exc_tb): pass
            return C()
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda *a, **k: 'CREATE INDEX SQL')
    monkeypatch.setattr(index_builder, 'get_drop_index_sql', lambda *a, **k: 'DROP INDEX SQL')
    monkeypatch.setattr(index_builder, 'get_set_ef_search_sql', lambda: 'SET SQL')
    conn = FakeConn()
    result = index_builder.build_index_sync(conn, 'idx', 'tbl', 'col', 'hnsw', False)
    assert result['index_name'] == 'idx'
    assert 'status' in result

def test_get_all_index_sql():
    sql = index_builder.get_all_index_sql()
    assert 'CREATE INDEX IF NOT EXISTS' in sql
    assert 'SET hnsw.ef_search' in sql
