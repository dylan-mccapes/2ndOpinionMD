# test_generated_server_alembic_env_20260302_040719.py
import pytest
try:
    import sys
    from unittest import mock
    import types
    from server.alembic import env
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)


def test_run_migrations_offline(monkeypatch):
    config_mock = mock.Mock()
    config_mock.get_main_option.return_value = "sqlite:///:memory:"
    context_mock = mock.Mock()
    monkeypatch.setattr(env, "config", config_mock)
    monkeypatch.setattr(env, "context", context_mock)
    monkeypatch.setattr(env, "target_metadata", None)
    env.run_migrations_offline()
    context_mock.configure.assert_called()
    assert context_mock.begin_transaction.called
    assert context_mock.run_migrations.called


def test_do_run_migrations(monkeypatch):
    context_mock = mock.Mock()
    monkeypatch.setattr(env, "context", context_mock)
    monkeypatch.setattr(env, "target_metadata", None)
    connection = mock.Mock()
    env.do_run_migrations(connection)
    context_mock.configure.assert_called_with(connection=connection, target_metadata=None)
    assert context_mock.begin_transaction.called
    assert context_mock.run_migrations.called

@pytest.mark.asyncio
async def test_run_async_migrations(monkeypatch):
    try:
        import pytest_asyncio  # noqa: F401
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    async_engine_mock = mock.AsyncMock()
    connectable_mock = mock.AsyncMock()
    connection_mock = mock.AsyncMock()
    connectable_mock.connect.return_value.__aenter__.return_value = connection_mock
    monkeypatch.setattr(env, "async_engine_from_config", mock.Mock(return_value=connectable_mock))
    config_mock = mock.Mock()
    config_mock.get_section.return_value = {}
    config_mock.config_ini_section = "section"
    monkeypatch.setattr(env, "config", config_mock)
    monkeypatch.setattr(env, "pool", mock.Mock())
    monkeypatch.setattr(env, "do_run_migrations", mock.AsyncMock())
    await env.run_async_migrations()
    assert connectable_mock.connect.called
    assert connection_mock.run_sync.called
    assert connectable_mock.dispose.called


def test_run_migrations_online(monkeypatch):
    run_async_migrations_mock = mock.Mock()
    monkeypatch.setattr(env, "run_async_migrations", run_async_migrations_mock)
    monkeypatch.setattr(env, "asyncio", mock.Mock())
    env.run_migrations_online()
    assert env.asyncio.run.called
