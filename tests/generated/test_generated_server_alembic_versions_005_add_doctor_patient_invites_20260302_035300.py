try:
    from server.alembic.versions import 005_add_doctor_patient_invites as invites_mod
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

def test_upgrade_creates_table_when_missing(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector = mock.Mock()
    inspector.get_table_names.return_value = ["other_table"]
    sa_mock.inspect.return_value = inspector
    monkeypatch.setattr(invites_mod, 'op', op_mock)
    monkeypatch.setattr(invites_mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    invites_mod.upgrade()
    assert op_mock.create_table.called
    args, kwargs = op_mock.create_table.call_args
    assert "doctor_patient_invites" in args

def test_upgrade_skips_if_table_exists(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector = mock.Mock()
    inspector.get_table_names.return_value = ["doctor_patient_invites"]
    sa_mock.inspect.return_value = inspector
    monkeypatch.setattr(invites_mod, 'op', op_mock)
    monkeypatch.setattr(invites_mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    invites_mod.upgrade()
    assert not op_mock.create_table.called

def test_downgrade_drops_table_when_exists(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector = mock.Mock()
    inspector.get_table_names.return_value = ["doctor_patient_invites", "other"]
    sa_mock.inspect.return_value = inspector
    monkeypatch.setattr(invites_mod, 'op', op_mock)
    monkeypatch.setattr(invites_mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    invites_mod.downgrade()
    assert op_mock.drop_table.called
    args, kwargs = op_mock.drop_table.call_args
    assert args[0] == "doctor_patient_invites"

def test_downgrade_skips_if_table_missing(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector = mock.Mock()
    inspector.get_table_names.return_value = ["other"]
    sa_mock.inspect.return_value = inspector
    monkeypatch.setattr(invites_mod, 'op', op_mock)
    monkeypatch.setattr(invites_mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    invites_mod.downgrade()
    assert not op_mock.drop_table.called
