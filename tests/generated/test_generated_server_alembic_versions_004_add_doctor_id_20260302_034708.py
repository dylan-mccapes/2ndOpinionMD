try:
    from server.alembic.versions import 004_add_doctor_id as mod
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

def test_upgrade_adds_column_and_fk(monkeypatch):
    op = mock.Mock()
    sa = mock.Mock()
    bind = object()
    inspector = mock.Mock()
    inspector.get_columns.return_value = [{"name": "id"}]
    inspector.get_foreign_keys.return_value = [{"name": "some_other_fk"}]
    monkeypatch.setattr(mod, 'op', op)
    monkeypatch.setattr(mod, 'sa', sa)
    op.get_bind.return_value = bind
    sa.inspect.return_value = inspector
    # doctor_id not in columns, users_doctor_id_fkey not in fks
    mod.upgrade()
    assert op.add_column.called
    assert op.create_foreign_key.called

def test_upgrade_skips_if_exists(monkeypatch):
    op = mock.Mock()
    sa = mock.Mock()
    bind = object()
    inspector = mock.Mock()
    inspector.get_columns.return_value = [{"name": "doctor_id"}]
    inspector.get_foreign_keys.return_value = [{"name": "users_doctor_id_fkey"}]
    monkeypatch.setattr(mod, 'op', op)
    monkeypatch.setattr(mod, 'sa', sa)
    op.get_bind.return_value = bind
    sa.inspect.return_value = inspector
    mod.upgrade()
    assert not op.add_column.called
    assert not op.create_foreign_key.called

def test_downgrade_drops_fk_and_column(monkeypatch):
    op = mock.Mock()
    sa = mock.Mock()
    bind = object()
    inspector = mock.Mock()
    inspector.get_foreign_keys.return_value = [{"name": "users_doctor_id_fkey"}]
    inspector.get_columns.return_value = [{"name": "doctor_id"}]
    monkeypatch.setattr(mod, 'op', op)
    monkeypatch.setattr(mod, 'sa', sa)
    op.get_bind.return_value = bind
    sa.inspect.return_value = inspector
    mod.downgrade()
    assert op.drop_constraint.called
    assert op.drop_column.called

def test_downgrade_skips_if_not_exists(monkeypatch):
    op = mock.Mock()
    sa = mock.Mock()
    bind = object()
    inspector = mock.Mock()
    inspector.get_foreign_keys.return_value = [{"name": "other_fk"}]
    inspector.get_columns.return_value = [{"name": "id"}]
    monkeypatch.setattr(mod, 'op', op)
    monkeypatch.setattr(mod, 'sa', sa)
    op.get_bind.return_value = bind
    sa.inspect.return_value = inspector
    mod.downgrade()
    assert not op.drop_constraint.called
    assert not op.drop_column.called
