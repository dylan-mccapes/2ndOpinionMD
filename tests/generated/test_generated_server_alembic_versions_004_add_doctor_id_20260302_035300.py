import pytest
try:
    from server.alembic.versions import 004_add_doctor_id as mod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_adds_column_and_fk(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    inspector_mock = mock.Mock()
    inspector_mock.get_columns.return_value = [{"name": "id"}]
    inspector_mock.get_foreign_keys.return_value = []
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    monkeypatch.setattr(mod.op, 'get_bind', lambda: None)
    mod.upgrade()
    assert op_mock.add_column.called
    assert op_mock.create_foreign_key.called

def test_upgrade_skips_if_column_and_fk_exist(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    inspector_mock = mock.Mock()
    inspector_mock.get_columns.return_value = [{"name": "doctor_id"}]
    inspector_mock.get_foreign_keys.return_value = [{"name": "users_doctor_id_fkey"}]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    monkeypatch.setattr(mod.op, 'get_bind', lambda: None)
    mod.upgrade()
    assert not op_mock.add_column.called
    assert not op_mock.create_foreign_key.called

def test_downgrade_drops_fk_and_column(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    inspector_mock = mock.Mock()
    inspector_mock.get_foreign_keys.return_value = [{"name": "users_doctor_id_fkey"}]
    inspector_mock.get_columns.return_value = [{"name": "doctor_id"}]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    monkeypatch.setattr(mod.op, 'get_bind', lambda: None)
    mod.downgrade()
    assert op_mock.drop_constraint.called
    assert op_mock.drop_column.called
