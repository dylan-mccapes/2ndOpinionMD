import pytest
from unittest import mock

def test_upgrade_adds_user_type_column(monkeypatch):
    try:
        import server.alembic.versions.003_add_user_type as mod
    except ImportError:
        pytest.skip('module not importable')
    called = {}
    class FakeInspector:
        def get_columns(self, table):
            return [{"name": "id"}, {"name": "email"}]
    monkeypatch.setattr(mod.op, 'get_bind', lambda: None)
    monkeypatch.setattr(mod.sa, 'inspect', lambda bind: FakeInspector())
    monkeypatch.setattr(mod.op, 'add_column', lambda table, col: called.setdefault('add', True))
    monkeypatch.setattr(mod.sa, 'Column', lambda *a, **k: None)
    monkeypatch.setattr(mod.sa, 'String', lambda *a, **k: None)
    mod.upgrade()
    assert called['add']

def test_downgrade_drops_user_type_column(monkeypatch):
    try:
        import server.alembic.versions.003_add_user_type as mod
    except ImportError:
        pytest.skip('module not importable')
    called = {}
    class FakeInspector:
        def get_columns(self, table):
            return [{"name": "user_type"}]
    monkeypatch.setattr(mod.op, 'get_bind', lambda: None)
    monkeypatch.setattr(mod.sa, 'inspect', lambda bind: FakeInspector())
    monkeypatch.setattr(mod.op, 'drop_column', lambda table, col: called.setdefault('drop', True))
    mod.downgrade()
    assert called['drop']
