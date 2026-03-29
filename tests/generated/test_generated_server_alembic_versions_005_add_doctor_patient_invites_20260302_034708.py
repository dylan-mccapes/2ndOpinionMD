try:
    from server.alembic.versions import 005_add_doctor_patient_invites as mod
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

def test_upgrade_creates_table(monkeypatch):
    op = mock.Mock()
    sa = mock.Mock()
    bind = object()
    inspector = mock.Mock()
    inspector.get_table_names.return_value = ["users"]
    monkeypatch.setattr(mod, 'op', op)
    monkeypatch.setattr(mod, 'sa', sa)
    op.get_bind.return_value = bind
    sa.inspect.return_value = inspector
    mod.upgrade()
    assert op.create_table.called

def test_upgrade_skips_if_exists(monkeypatch):
    op = mock.Mock()
    sa = mock.Mock()
    bind = object()
    inspector = mock.Mock()
    inspector.get_table_names.return_value = ["doctor_patient_invites"]
    monkeypatch.setattr(mod, 'op', op)
    monkeypatch.setattr(mod, 'sa', sa)
    op.get_bind.return_value = bind
    sa.inspect.return_value = inspector
    mod.upgrade()
    assert not op.create_table.called

def test_downgrade_drops_table(monkeypatch):
    op = mock.Mock()
    sa = mock.Mock()
    bind = object()
    inspector = mock.Mock()
    inspector.get_table_names.return_value = ["doctor_patient_invites"]
    monkeypatch.setattr(mod, 'op', op)
    monkeypatch.setattr(mod, 'sa', sa)
    op.get_bind.return_value = bind
    sa.inspect.return_value = inspector
    mod.downgrade()
    assert op.drop_table.called

def test_downgrade_skips_if_not_exists(monkeypatch):
    op = mock.Mock()
    sa = mock.Mock()
    bind = object()
    inspector = mock.Mock()
    inspector.get_table_names.return_value = ["users"]
    monkeypatch.setattr(mod, 'op', op)
    monkeypatch.setattr(mod, 'sa', sa)
    op.get_bind.return_value = bind
    sa.inspect.return_value = inspector
    mod.downgrade()
    assert not op.drop_table.called
