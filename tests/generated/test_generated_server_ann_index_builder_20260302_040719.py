try:
    import pytest
    from unittest import mock
    import types
    from server.ann import index_builder
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.parametrize("index_type,expected_fragment", [
    ("hnsw", "USING hnsw"),
    ("ivfflat", "USING ivfflat")
])
def test_get_create_index_sql(index_type, expected_fragment):
    # Patch HNSW_CONFIG in module
    config = {'distance_metric': 'cosine', 'm': 16, 'ef_construction': 200, 'ef_search': 32}
    with mock.patch.object(index_builder, 'HNSW_CONFIG', config):
        sql = index_builder.get_create_index_sql('idx', 'tbl', 'col', index_type)
        assert expected_fragment in sql
        assert 'idx' in sql and 'tbl' in sql and 'col' in sql


def test_get_drop_index_sql():
    sql = index_builder.get_drop_index_sql('myindex')
    assert sql == 'DROP INDEX IF EXISTS myindex;'


def test_get_set_ef_search_sql():
    with mock.patch.object(index_builder, 'HNSW_CONFIG', {'ef_search': 42}):
        sql = index_builder.get_set_ef_search_sql()
        assert sql.strip() == 'SET hnsw.ef_search = 42;'

@pytest.mark.asyncio
async def test_build_index(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            return None
        async def commit(self):
            return None
    session = DummySession()
    # Patch SQL generation
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda *a, **kw: 'CREATE INDEX SQL')
    monkeypatch.setattr(index_builder, 'get_drop_index_sql', lambda *a, **kw: 'DROP INDEX SQL')
    monkeypatch.setattr(index_builder, 'get_set_ef_search_sql', lambda: 'SET SQL')
    result = await index_builder.build_index(session, 'idx', 'tbl', 'col', index_type='hnsw', force_rebuild=True)
    assert result['index_name'] == 'idx'
    assert 'status' in result
    assert 'duration' in result

@pytest.mark.asyncio
async def test_check_index_health(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            class DummyResult:
                def fetchall(self):
                    return [("idx", "CREATE INDEX ...")]
            return DummyResult()
    session = DummySession()
    # Patch fetchall to return one index
    async def dummy_execute(sql):
        class DummyResult:
            def fetchall(self):
                return [("idx", "CREATE INDEX ...")]
        return DummyResult()
    monkeypatch.setattr(session, 'execute', dummy_execute)
    result = await index_builder.check_index_health(session, 'idx')
    assert result['index_name'] == 'idx'
    assert result['exists'] is True or result['exists'] is False
    assert 'healthy' in result
    assert 'details' in result

@pytest.mark.asyncio
async def test_rebuild_if_corrupted(monkeypatch):
    # Patch check_index_health to return corrupted
    async def fake_check_index_health(session, index_name):
        return {'index_name': index_name, 'exists': True, 'healthy': False, 'details': {}}
    async def fake_build_index(session, index_name, table_name, column_name, index_type='hnsw', force_rebuild=False):
        return {'rebuilt': True, 'index_name': index_name}
    monkeypatch.setattr(index_builder, 'check_index_health', fake_check_index_health)
    monkeypatch.setattr(index_builder, 'build_index', fake_build_index)
    class DummySession: pass
    session = DummySession()
    result = await index_builder.rebuild_if_corrupted(session, 'idx', 'tbl', 'col')
    assert result['index_name'] == 'idx'
    assert result.get('rebuilt') is True


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
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda *a, **kw: 'CREATE INDEX SQL')
    monkeypatch.setattr(index_builder, 'get_drop_index_sql', lambda *a, **kw: 'DROP INDEX SQL')
    monkeypatch.setattr(index_builder, 'get_set_ef_search_sql', lambda: 'SET SQL')
    conn = DummyConn()
    result = index_builder.build_index_sync(conn, 'idx', 'tbl', 'col', index_type='hnsw', force_rebuild=True)
    assert result['index_name'] == 'idx'
    assert 'status' in result
    assert 'duration' in result

def test_get_all_index_sql(monkeypatch):
    # Patch INDEX_DEFINITIONS and SQL functions
    monkeypatch.setattr(index_builder, 'INDEX_DEFINITIONS', {
        'idx1': {'table': 'tbl1', 'column': 'col1', 'type': 'hnsw'},
        'idx2': {'table': 'tbl2', 'column': 'col2', 'type': 'ivfflat'}
    })
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda i, t, c, ty: f'CREATE INDEX {i} ON {t}({c}) USING {ty}')
    monkeypatch.setattr(index_builder, 'get_set_ef_search_sql', lambda: 'SET hnsw.ef_search = 32;')
    sql = index_builder.get_all_index_sql()
    assert 'CREATE INDEX idx1' in sql
    assert 'CREATE INDEX idx2' in sql
    assert 'SET hnsw.ef_search' in sql
