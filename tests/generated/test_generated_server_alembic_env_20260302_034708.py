try:
    import pytest
    from server.alembic import env
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import sys
from unittest import mock


def test_run_migrations_offline(monkeypatch):
    mock_context = mock.Mock()
    monkeypatch.setattr(env, 'context', mock_context)
    mock_config = mock.Mock()
    mock_config.get_main_option.return_value = 'sqlite:///:memory:'
    monkeypatch.setattr(env, 'config', mock_config)
    monkeypatch.setattr(env, 'target_metadata', object())
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
    assert mock_context.configure.called
    assert mock_context.begin_transaction.called
    assert mock_context.run_migrations.called


def test_run_async_migrations(monkeypatch):
    pytest.importorskip('pytest_asyncio')
    import asyncio
    async def fake_connect():
        class FakeConn:
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc, tb): pass
            async def run_sync(self, fn):
                return fn(mock.Mock())
        return FakeConn()
    fake_engine = mock.Mock()
    fake_engine.connect.side_effect = fake_connect
    fake_engine.dispose = mock.AsyncMock()
    monkeypatch.setattr(env, 'async_engine_from_config', lambda *a, **kw: fake_engine)
    monkeypatch.setattr(env, 'config', mock.Mock())
    monkeypatch.setattr(env, 'pool', mock.Mock())
    monkeypatch.setattr(env, 'do_run_migrations', lambda conn: None)
    async def run():
        await env.run_async_migrations()
        assert fake_engine.connect.called
        assert fake_engine.dispose.called
    asyncio.run(run())


def test_run_migrations_online(monkeypatch):
    called = {}
    def fake_run(coro):
        called['ran'] = True
    monkeypatch.setattr(env.asyncio, 'run', fake_run)
    monkeypatch.setattr(env, 'run_async_migrations', mock.Mock())
    env.run_migrations_online()
    assert called.get('ran')