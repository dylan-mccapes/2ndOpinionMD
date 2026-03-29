import pytest
try:
    import server.alembic.env as env
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock


def test_run_migrations_offline_calls_context(monkeypatch):
    mock_config = mock.Mock()
    mock_context = mock.Mock()
    monkeypatch.setattr(env, 'config', mock_config)
    monkeypatch.setattr(env, 'context', mock_context)
    monkeypatch.setattr(env, 'target_metadata', 'meta')
    mock_config.get_main_option.return_value = 'sqlite:///:memory:'
    env.run_migrations_offline()
    mock_context.configure.assert_called_once()
    assert mock_context.begin_transaction.called
    assert mock_context.run_migrations.called


def test_do_run_migrations_calls_context(monkeypatch):
    mock_context = mock.Mock()
    monkeypatch.setattr(env, 'context', mock_context)
    monkeypatch.setattr(env, 'target_metadata', 'meta')
    mock_conn = mock.Mock()
    env.do_run_migrations(mock_conn)
    mock_context.configure.assert_called_once_with(connection=mock_conn, target_metadata='meta')
    assert mock_context.begin_transaction.called
    assert mock_context.run_migrations.called

@pytest.mark.asyncio
async def test_run_async_migrations(monkeypatch):
    try:
        import pytest_asyncio  # noqa: F401
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    mock_engine = mock.AsyncMock()
    mock_connect = mock.AsyncMock()
    mock_conn = mock.AsyncMock()
    monkeypatch.setattr(env, 'async_engine_from_config', mock.Mock(return_value=mock_engine))
    monkeypatch.setattr(env, 'config', mock.Mock())
    monkeypatch.setattr(env, 'pool', mock.Mock())
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn
    mock_conn.run_sync = mock.AsyncMock()
    mock_engine.dispose = mock.AsyncMock()
    monkeypatch.setattr(env, 'do_run_migrations', mock.Mock())
    await env.run_async_migrations()
    assert mock_conn.run_sync.called
    assert mock_engine.dispose.called


def test_run_migrations_online_calls_asyncio_run(monkeypatch):
    mock_asyncio = mock.Mock()
    monkeypatch.setattr(env, 'asyncio', mock_asyncio)
    monkeypatch.setattr(env, 'run_async_migrations', mock.Mock())
    env.run_migrations_online()
    assert mock_asyncio.run.called
