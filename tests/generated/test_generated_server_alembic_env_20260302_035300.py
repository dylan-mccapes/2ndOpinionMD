# test_generated_server_alembic_env_20260302_035300.py
import pytest
try:
    import server.alembic.env as env
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

from unittest import mock


def test_run_migrations_offline(monkeypatch):
    mock_config = mock.Mock()
    mock_context = mock.Mock()
    monkeypatch.setattr(env, 'config', mock_config)
    monkeypatch.setattr(env, 'context', mock_context)
    monkeypatch.setattr(env, 'target_metadata', object())
    mock_config.get_main_option.return_value = 'sqlite:///:memory:'
    env.run_migrations_offline()
    assert mock_context.configure.called
    assert mock_context.begin_transaction.called
    assert mock_context.run_migrations.called


def test_do_run_migrations(monkeypatch):
    mock_context = mock.Mock()
    monkeypatch.setattr(env, 'context', mock_context)
    monkeypatch.setattr(env, 'target_metadata', object())
    mock_conn = mock.Mock()
    env.do_run_migrations(mock_conn)
    mock_context.configure.assert_called_with(connection=mock_conn, target_metadata=mock.ANY)
    assert mock_context.begin_transaction.called
    assert mock_context.run_migrations.called

@pytest.mark.asyncio
async def test_run_async_migrations(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    mock_engine = mock.AsyncMock()
    mock_conn = mock.AsyncMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn
    monkeypatch.setattr(env, 'async_engine_from_config', mock.Mock(return_value=mock_engine))
    monkeypatch.setattr(env, 'config', mock.Mock())
    monkeypatch.setattr(env, 'pool', mock.Mock())
    monkeypatch.setattr(env, 'do_run_migrations', mock.AsyncMock())
    await env.run_async_migrations()
    assert mock_engine.connect.called
    assert mock_conn.run_sync.called
    assert mock_engine.dispose.called


def test_run_migrations_online(monkeypatch):
    monkeypatch.setattr(env, 'asyncio', mock.Mock())
    monkeypatch.setattr(env, 'run_async_migrations', mock.Mock())
    env.run_migrations_online()
    assert env.asyncio.run.called
