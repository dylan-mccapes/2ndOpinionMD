import pytest
try:
    from server.alembic.versions import 003_add_user_type as mod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_adds_column_if_missing(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    inspector_mock = mock.Mock()
    inspector_mock.get_columns.return_value = [{"name": "id"}]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    monkeypatch.setattr(mod.op, 'get_bind', lambda: None)
    mod.upgrade()
    assert op_mock.add_column.called

def test_upgrade_skips_if_column_exists(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    inspector_mock = mock.Mock()
    inspector_mock.get_columns.return_value = [{"name": "user_type"}]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    monkeypatch.setattr(mod.op, 'get_bind', lambda: None)
    mod.upgrade()
    assert not op_mock.add_column.called

def test_downgrade_drops_column_if_exists(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    inspector_mock = mock.Mock()
    inspector_mock.get_columns.return_value = [{"name": "user_type"}]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    monkeypatch.setattr(mod.op, 'get_bind', lambda: None)
    mod.downgrade()
    assert op_mock.drop_column.called

def test_downgrade_skips_if_column_missing(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    inspector_mock = mock.Mock()
    inspector_mock.get_columns.return_value = [{"name": "id"}]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    monkeypatch.setattr(mod.op, 'get_bind', lambda: None)
    mod.downgrade()
    assert not op_mock.drop_column.called
