import pytest
from unittest import mock

@pytest.mark.skipif('server.alembic.env' not in globals(), reason='Module not importable')
def test_run_migrations_offline_calls_configure_and_run(monkeypatch):
    try:
        from server.alembic import env
    except ImportError:
        pytest.skip('server.alembic.env not importable')
    called = {}
    monkeypatch.setattr(env.config, 'get_main_option', lambda key: 'sqlite:///:memory:')
    def fake_configure(**kwargs):
        called['configured'] = kwargs
    monkeypatch.setattr(env.context, 'configure', fake_configure)
    class FakeTrans:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
    monkeypatch.setattr(env.context, 'begin_transaction', lambda: FakeTrans())
    monkeypatch.setattr(env.context, 'run_migrations', lambda: called.setdefault('ran', True))
    env.run_migrations_offline()
    assert 'configured' in called
    assert 'ran' in called

@pytest.mark.skipif('server.alembic.env' not in globals(), reason='Module not importable')
def test_do_run_migrations_calls_configure_and_run(monkeypatch):
    try:
        from server.alembic import env
    except ImportError:
        pytest.skip('server.alembic.env not importable')
    called = {}
    monkeypatch.setattr(env.context, 'configure', lambda **kwargs: called.setdefault('configured', True))
    class FakeTrans:
        def __enter__(self): return self
        def __exit__(self, exc_type, exc_val, exc_tb): pass
    monkeypatch.setattr(env.context, 'begin_transaction', lambda: FakeTrans())
    monkeypatch.setattr(env.context, 'run_migrations', lambda: called.setdefault('ran', True))
    env.do_run_migrations(connection=mock.Mock())
    assert called['configured']
    assert called['ran']

@pytest.mark.asyncio
def test_run_async_migrations_calls_run_sync(monkeypatch):
    try:
        from server.alembic import env
    except ImportError:
        pytest.skip('server.alembic.env not importable')
    called = {}
    class FakeConn:
        async def run_sync(self, fn):
            called['run_sync'] = True
    class FakeEngine:
        async def connect(self):
            class Ctx:
                async def __aenter__(self): return FakeConn()
                async def __aexit__(self, exc_type, exc_val, exc_tb): pass
            return Ctx()
        async def dispose(self): called['disposed'] = True
    monkeypatch.setattr(env, 'async_engine_from_config', lambda *a, **k: FakeEngine())
    monkeypatch.setattr(env.config, 'get_section', lambda *a, **k: {})
    await env.run_async_migrations()
    assert called['run_sync']
    assert called['disposed']

def test_run_migrations_online_calls_asyncio_run(monkeypatch):
    try:
        from server.alembic import env
    except ImportError:
        pytest.skip('server.alembic.env not importable')
    called = {}
    monkeypatch.setattr(env, 'run_async_migrations', lambda: called.setdefault('ran', True))
    monkeypatch.setattr(env.asyncio, 'run', lambda coro: called.setdefault('asyncio_run', True))
    env.run_migrations_online()
    assert 'asyncio_run' in called
