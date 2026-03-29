# AUTO-GENERATED TESTS FOR server/alembic/versions/004_add_doctor_id.py
import pytest
try:
    import server.alembic.versions.004_add_doctor_id as mod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_adds_column_and_fk(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    # Simulate doctor_id not present, fk not present
    inspector_mock.get_columns.return_value = [{"name": "id"}, {"name": "email"}]
    inspector_mock.get_foreign_keys.return_value = [{"name": "other_fk"}]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    mod.upgrade()
    op_mock.add_column.assert_called()
    op_mock.create_foreign_key.assert_called()

def test_upgrade_skips_if_column_and_fk_exist(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_columns.return_value = [{"name": "id"}, {"name": "doctor_id"}]
    inspector_mock.get_foreign_keys.return_value = [{"name": "users_doctor_id_fkey"}]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    mod.upgrade()
    op_mock.add_column.assert_not_called()
    op_mock.create_foreign_key.assert_not_called()

def test_downgrade_drops_fk_and_column(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_foreign_keys.return_value = [{"name": "users_doctor_id_fkey"}]
    inspector_mock.get_columns.return_value = [{"name": "id"}, {"name": "doctor_id"}]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    mod.downgrade()
    op_mock.drop_constraint.assert_called_with("users_doctor_id_fkey", "users", type_="foreignkey")
    op_mock.drop_column.assert_called_with("users", "doctor_id")

def test_downgrade_skips_if_no_fk_or_column(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_foreign_keys.return_value = [{"name": "other_fk"}]
    inspector_mock.get_columns.return_value = [{"name": "id"}]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    mod.downgrade()
    op_mock.drop_constraint.assert_not_called()
    op_mock.drop_column.assert_not_called()
