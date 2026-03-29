import pytest
from unittest import mock

try:
    from server.ann import index_builder
except ImportError:
    pytest.skip('server.ann.index_builder not importable', allow_module_level=True)

# get_create_index_sql

def test_get_create_index_sql_hnsw(monkeypatch):
    monkeypatch.setattr(index_builder, 'HNSW_CONFIG', {'distance_metric': 'cosine', 'm': 16, 'ef_construction': 200, 'ef_search': 32})
    sql = index_builder.get_create_index_sql('idx1', 'mytable', 'embedding', 'hnsw')
    assert 'CREATE INDEX IF NOT EXISTS idx1' in sql
    assert 'USING hnsw' in sql
    assert 'embedding cosine' in sql
    assert 'm = 16' in sql
    assert 'ef_construction = 200' in sql

def test_get_create_index_sql_ivfflat(monkeypatch):
    monkeypatch.setattr(index_builder, 'IVFFLAT_CONFIG', {'lists': 100, 'distance_metric': 'l2'})
    sql = index_builder.get_create_index_sql('idx2', 'mytable', 'embedding', 'ivfflat')
    assert 'USING ivfflat' in sql
    assert 'embedding l2' in sql
    assert 'lists = 100' in sql

def test_get_create_index_sql_invalid_type():
    with pytest.raises(ValueError):
        index_builder.get_create_index_sql('idx3', 'mytable', 'embedding', 'unknown')

# get_drop_index_sql

def test_get_drop_index_sql():
    sql = index_builder.get_drop_index_sql('idx1')
    assert sql == 'DROP INDEX IF EXISTS idx1;'

# get_set_ef_search_sql

def test_get_set_ef_search_sql(monkeypatch):
    monkeypatch.setattr(index_builder, 'HNSW_CONFIG', {'ef_search': 42})
    sql = index_builder.get_set_ef_search_sql()
    assert sql == 'SET hnsw.ef_search = 42;'

# build_index (async)
import pytest_asyncio
@pytest.mark.asyncio
async def test_build_index(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            return None
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda *a, **kw: 'CREATE INDEX SQL')
    monkeypatch.setattr(index_builder, 'get_drop_index_sql', lambda *a, **kw: 'DROP INDEX SQL')
    monkeypatch.setattr(index_builder, 'get_set_ef_search_sql', lambda: 'SET SQL')
    session = DummySession()
    result = await index_builder.build_index(session, 'idx', 'tbl', 'col', index_type='hnsw', force_rebuild=True)
    assert result['index_name'] == 'idx'
    assert 'status' in result
    assert 'duration' in result

# check_index_health (async)
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
    assert result['exists'] in (True, False)
    assert 'healthy' in result
    assert isinstance(result['details'], dict)

# rebuild_if_corrupted (async)
@pytest.mark.asyncio
async def test_rebuild_if_corrupted(monkeypatch):
    class DummySession:
        pass
    monkeypatch.setattr(index_builder, 'logger', mock.Mock())
    monkeypatch.setattr(index_builder, 'check_index_health', mock.AsyncMock(return_value={'healthy': False, 'exists': True, 'index_name': 'idx', 'details': {}}))
    monkeypatch.setattr(index_builder, 'build_index', mock.AsyncMock(return_value={'rebuilt': True, 'index_name': 'idx'}))
    session = DummySession()
    result = await index_builder.rebuild_if_corrupted(session, 'idx', 'tbl', 'col')
    assert result['index_name'] == 'idx'
    assert result.get('rebuilt', False) is True

# build_index_sync

def test_build_index_sync(monkeypatch):
    class DummyConn:
        def cursor(self):
            class DummyCursor:
                def execute(self, sql):
                    return None
                def close(self):
                    pass
            return DummyCursor()
        def commit(self):
            pass
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda *a, **kw: 'CREATE INDEX SQL')
    monkeypatch.setattr(index_builder, 'get_drop_index_sql', lambda *a, **kw: 'DROP INDEX SQL')
    monkeypatch.setattr(index_builder, 'get_set_ef_search_sql', lambda: 'SET SQL')
    conn = DummyConn()
    result = index_builder.build_index_sync(conn, 'idx', 'tbl', 'col', index_type='hnsw', force_rebuild=True)
    assert result['index_name'] == 'idx'
    assert 'status' in result
    assert 'duration' in result

# get_all_index_sql

def test_get_all_index_sql(monkeypatch):
    monkeypatch.setattr(index_builder, 'INDEX_DEFINITIONS', {
        'idx1': {'table': 'tbl1', 'column': 'col1', 'type': 'hnsw'},
        'idx2': {'table': 'tbl2', 'column': 'col2', 'type': 'ivfflat'}
    })
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda n, t, c, ty: f'CREATE {n} ON {t} ({c}) TYPE {ty}')
    monkeypatch.setattr(index_builder, 'get_set_ef_search_sql', lambda: 'SET SQL')
    sql = index_builder.get_all_index_sql()
    assert 'CREATE idx1' in sql
    assert 'CREATE idx2' in sql
    assert 'SET SQL' in sql
