# test_generated_server_alembic_env_20260302_034348.py
import pytest
try:
    import sys
    from unittest import mock
    from server.alembic import env
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)


def test_run_migrations_offline(monkeypatch):
    called = {}
    monkeypatch.setattr(env.config, 'get_main_option', lambda key: 'sqlite:///:memory:')
    def fake_configure(**kwargs):
        called['configured'] = kwargs
    monkeypatch.setattr(env.context, 'configure', fake_configure)
    class FakeContext:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
    monkeypatch.setattr(env.context, 'begin_transaction', lambda: FakeContext())
    monkeypatch.setattr(env.context, 'run_migrations', lambda: called.setdefault('ran', True))
    env.run_migrations_offline()
    assert 'configured' in called
    assert 'ran' in called


def test_do_run_migrations(monkeypatch):
    called = {}
    def fake_configure(**kwargs):
        called['configured'] = kwargs
    monkeypatch.setattr(env.context, 'configure', fake_configure)
    class FakeContext:
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc_val, exc_tb):
            pass
    monkeypatch.setattr(env.context, 'begin_transaction', lambda: FakeContext())
    monkeypatch.setattr(env.context, 'run_migrations', lambda: called.setdefault('ran', True))
    env.do_run_migrations(connection='dummy')
    assert 'configured' in called
    assert 'ran' in called

@pytest.mark.asyncio
async def test_run_async_migrations(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    called = {}
    class FakeConnectable:
        async def connect(self):
            class Conn:
                async def __aenter__(self):
                    return self
                async def __aexit__(self, exc_type, exc_val, exc_tb):
                    pass
                async def run_sync(self, fn):
                    called['ran_sync'] = True
            return Conn()
        async def dispose(self):
            called['disposed'] = True
    monkeypatch.setattr(env, 'async_engine_from_config', lambda *a, **kw: FakeConnectable())
    monkeypatch.setattr(env.config, 'get_section', lambda *a, **kw: {})
    await env.run_async_migrations()
    assert called.get('ran_sync')
    assert called.get('disposed')

def test_run_migrations_online(monkeypatch):
    called = {}
    monkeypatch.setattr(env.asyncio, 'run', lambda coro: called.setdefault('ran', True))
    env.run_migrations_online()
    assert called['ran']
