# test_generated_server_alembic_versions_003_add_user_type_20260302_034348.py
import pytest
try:
    from server.alembic.versions import 003_add_user_type as mod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_adds_user_type(monkeypatch):
    called = {}
    class FakeInspector:
        def get_columns(self, table):
            return [{"name": "id"}, {"name": "email"}]
    monkeypatch.setattr(mod.op, 'get_bind', lambda: 'bind')
    monkeypatch.setattr(mod.sa, 'inspect', lambda bind: FakeInspector())
    monkeypatch.setattr(mod.op, 'add_column', lambda table, col: called.setdefault('add_column', True))
    monkeypatch.setattr(mod.sa, 'Column', lambda *a, **kw: None)
    monkeypatch.setattr(mod.sa, 'String', lambda *a, **kw: None)
    mod.upgrade()
    assert called.get('add_column')

def test_downgrade_drops_user_type(monkeypatch):
    called = {}
    class FakeInspector:
        def get_columns(self, table):
            return [{"name": "user_type"}]
    monkeypatch.setattr(mod.op, 'get_bind', lambda: 'bind')
    monkeypatch.setattr(mod.sa, 'inspect', lambda bind: FakeInspector())
    monkeypatch.setattr(mod.op, 'drop_column', lambda table, col: called.setdefault('drop_column', True))
    mod.downgrade()
    assert called.get('drop_column')
