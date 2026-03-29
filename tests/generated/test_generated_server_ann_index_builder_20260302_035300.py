# test_generated_server_ann_index_builder_20260302_035300.py
import pytest
try:
    from server.ann import index_builder
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

from unittest import mock

def test_get_create_index_sql_hnsw(monkeypatch):
    monkeypatch.setattr(index_builder, 'HNSW_CONFIG', {'distance_metric': 'cosine', 'm': 8, 'ef_search': 32})
    sql = index_builder.get_create_index_sql('idx1', 'tbl', 'col', 'hnsw')
    assert 'CREATE INDEX' in sql
    assert 'USING hnsw' in sql
    assert 'idx1' in sql
    assert 'tbl' in sql
    assert 'col' in sql

def test_get_drop_index_sql():
    sql = index_builder.get_drop_index_sql('idx1')
    assert sql.strip().startswith('DROP INDEX')
    assert 'idx1' in sql

def test_get_set_ef_search_sql(monkeypatch):
    monkeypatch.setattr(index_builder, 'HNSW_CONFIG', {'ef_search': 42})
    sql = index_builder.get_set_ef_search_sql()
    assert 'SET hnsw.ef_search' in sql
    assert '42' in sql

@pytest.mark.asyncio
async def test_build_index(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    session = mock.AsyncMock()
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda *a, **k: 'CREATE INDEX ...')
    monkeypatch.setattr(session, 'execute', mock.AsyncMock())
    monkeypatch.setattr(session, 'commit', mock.AsyncMock())
    result = await index_builder.build_index(session, 'idx', 'tbl', 'col', 'hnsw', False)
    assert isinstance(result, dict)
    assert result['index_name'] == 'idx'
    assert 'status' in result

@pytest.mark.asyncio
async def test_check_index_health(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    session = mock.AsyncMock()
    # Patch session.execute to return a mock result
    mock_result = mock.AsyncMock()
    mock_result.fetchall.return_value = [('idx', 'def')]
    session.execute.return_value = mock_result
    result = await index_builder.check_index_health(session, 'idx')
    assert isinstance(result, dict)
    assert result['index_name'] == 'idx'
    assert 'exists' in result

@pytest.mark.asyncio
async def test_rebuild_if_corrupted(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    session = mock.AsyncMock()
    monkeypatch.setattr(index_builder, 'check_index_health', mock.AsyncMock(return_value={'healthy': False, 'index_name': 'idx'}))
    monkeypatch.setattr(index_builder, 'build_index', mock.AsyncMock(return_value={'rebuilt': True, 'index_name': 'idx'}))
    monkeypatch.setattr(index_builder, 'logger', mock.Mock())
    result = await index_builder.rebuild_if_corrupted(session, 'idx', 'tbl', 'col')
    assert isinstance(result, dict)
    assert result['index_name'] == 'idx'


def test_build_index_sync(monkeypatch):
    conn = mock.Mock()
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda *a, **k: 'CREATE INDEX ...')
    conn.cursor.return_value.__enter__.return_value = mock.Mock()
    result = index_builder.build_index_sync(conn, 'idx', 'tbl', 'col', 'hnsw', False)
    assert isinstance(result, dict)
    assert result['index_name'] == 'idx'
    assert 'status' in result

def test_get_all_index_sql(monkeypatch):
    monkeypatch.setattr(index_builder, 'INDEX_DEFINITIONS', {
        'idx1': {'table': 'tbl1', 'column': 'col1', 'type': 'hnsw'},
        'idx2': {'table': 'tbl2', 'column': 'col2', 'type': 'ivfflat'}
    })
    monkeypatch.setattr(index_builder, 'get_create_index_sql', lambda i, t, c, ty: f'CREATE INDEX {i} ON {t} ({c}) USING {ty}')
    monkeypatch.setattr(index_builder, 'get_set_ef_search_sql', lambda: 'SET hnsw.ef_search = 32;')
    sql = index_builder.get_all_index_sql()
    assert 'CREATE INDEX idx1' in sql
    assert 'CREATE INDEX idx2' in sql
    assert 'SET hnsw.ef_search' in sql
