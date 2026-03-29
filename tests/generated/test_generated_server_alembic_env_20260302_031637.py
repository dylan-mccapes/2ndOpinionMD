import pytest
from unittest import mock

try:
    import server.alembic.env as env
except ImportError:
    pytest.skip('server.alembic.env could not be imported', allow_module_level=True)


def test_run_migrations_offline(monkeypatch):
    mock_config = mock.Mock()
    mock_context = mock.Mock()
    monkeypatch.setattr(env, 'config', mock_config)
    monkeypatch.setattr(env, 'context', mock_context)
    monkeypatch.setattr(env, 'target_metadata', object())
    mock_config.get_main_option.return_value = 'sqlite:///:memory:'
    mock_context.begin_transaction.return_value.__enter__.return_value = None
    env.run_migrations_offline()
    assert mock_context.configure.called
    assert mock_context.run_migrations.called


def test_do_run_migrations(monkeypatch):
    mock_context = mock.Mock()
    monkeypatch.setattr(env, 'context', mock_context)
    monkeypatch.setattr(env, 'target_metadata', object())
    connection = mock.Mock()
    mock_context.begin_transaction.return_value.__enter__.return_value = None
    env.do_run_migrations(connection)
    mock_context.configure.assert_called_with(connection=connection, target_metadata=mock.ANY)
    assert mock_context.run_migrations.called

@pytest.mark.asyncio
def test_run_async_migrations(monkeypatch):
    mock_engine = mock.AsyncMock()
    mock_connect = mock.AsyncMock()
    mock_connection = mock.AsyncMock()
    mock_connect.__aenter__.return_value = mock_connection
    mock_engine.connect.return_value = mock_connect
    monkeypatch.setattr(env, 'async_engine_from_config', lambda *a, **kw: mock_engine)
    monkeypatch.setattr(env, 'config', mock.Mock())
    monkeypatch.setattr(env, 'pool', mock.Mock())
    monkeypatch.setattr(env, 'do_run_migrations', mock.AsyncMock())
    await env.run_async_migrations()
    assert mock_engine.connect.called
    assert mock_connection.run_sync.called
    assert mock_engine.dispose.called


def test_run_migrations_online(monkeypatch):
    monkeypatch.setattr(env, 'run_async_migrations', mock.AsyncMock())
    monkeypatch.setattr(env, 'asyncio', mock.Mock())
    env.asyncio.run = mock.Mock()
    env.run_migrations_online()
    env.asyncio.run.assert_called_with(env.run_async_migrations())
