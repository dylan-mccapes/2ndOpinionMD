# AUTO-GENERATED TESTS FOR server/alembic/versions/005_add_doctor_patient_invites.py
import pytest
try:
    import server.alembic.versions.005_add_doctor_patient_invites as mod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_creates_table(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_table_names.return_value = ["users"]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    mod.upgrade()
    op_mock.create_table.assert_called_with(
        "doctor_patient_invites",
        mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY, mock.ANY
    )

def test_upgrade_skips_if_table_exists(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_table_names.return_value = ["users", "doctor_patient_invites"]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    mod.upgrade()
    op_mock.create_table.assert_not_called()

def test_downgrade_drops_table(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_table_names.return_value = ["doctor_patient_invites", "users"]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    mod.downgrade()
    op_mock.drop_table.assert_called_with("doctor_patient_invites")

def test_downgrade_skips_if_table_missing(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_table_names.return_value = ["users"]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    mod.downgrade()
    op_mock.drop_table.assert_not_called()
