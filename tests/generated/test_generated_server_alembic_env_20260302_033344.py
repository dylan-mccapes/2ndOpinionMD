# AUTO-GENERATED TESTS FOR server/alembic/env.py
import pytest
from unittest import mock

@pytest.mark.skipif('server.alembic.env' not in globals(), reason='Module not importable')
def test_run_migrations_offline(monkeypatch):
    try:
        import server.alembic.env as env
    except ImportError:
        pytest.skip('server.alembic.env not importable')
    config_mock = mock.Mock()
    context_mock = mock.Mock()
    monkeypatch.setattr(env, 'config', config_mock)
    monkeypatch.setattr(env, 'context', context_mock)
    config_mock.get_main_option.return_value = 'sqlite:///:memory:'
    context_mock.begin_transaction.return_value.__enter__.return_value = None
    env.run_migrations_offline()
    context_mock.configure.assert_called()
    context_mock.run_migrations.assert_called()

@pytest.mark.skipif('server.alembic.env' not in globals(), reason='Module not importable')
def test_do_run_migrations(monkeypatch):
    try:
        import server.alembic.env as env
    except ImportError:
        pytest.skip('server.alembic.env not importable')
    context_mock = mock.Mock()
    monkeypatch.setattr(env, 'context', context_mock)
    connection = mock.Mock()
    context_mock.begin_transaction.return_value.__enter__.return_value = None
    env.do_run_migrations(connection)
    context_mock.configure.assert_called_with(connection=connection, target_metadata=mock.ANY)
    context_mock.run_migrations.assert_called()

@pytest.mark.asyncio
def test_run_async_migrations(monkeypatch):
    try:
        import server.alembic.env as env
    except ImportError:
        pytest.skip('server.alembic.env not importable')
    async_engine_mock = mock.AsyncMock()
    connectable_mock = mock.AsyncMock()
    connection_mock = mock.AsyncMock()
    connectable_mock.connect.return_value.__aenter__.return_value = connection_mock
    monkeypatch.setattr(env, 'async_engine_from_config', mock.Mock(return_value=connectable_mock))
    monkeypatch.setattr(env, 'config', mock.Mock())
    monkeypatch.setattr(env, 'pool', mock.Mock())
    monkeypatch.setattr(env, 'do_run_migrations', mock.AsyncMock())
    connection_mock.run_sync = mock.AsyncMock()
    connectable_mock.dispose = mock.AsyncMock()
    import asyncio
    asyncio.run(env.run_async_migrations())
    connection_mock.run_sync.assert_awaited()
    connectable_mock.dispose.assert_awaited()

@pytest.mark.skipif('server.alembic.env' not in globals(), reason='Module not importable')
def test_run_migrations_online(monkeypatch):
    try:
        import server.alembic.env as env
    except ImportError:
        pytest.skip('server.alembic.env not importable')
    monkeypatch.setattr(env, 'run_async_migrations', mock.Mock())
    import asyncio
    monkeypatch.setattr(asyncio, 'run', mock.Mock())
    env.run_migrations_online()
    asyncio.run.assert_called_with(env.run_async_migrations())
