try:
    import pytest
    from unittest import mock
    import server.alembic.versions.004_add_doctor_id as migration
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

def test_upgrade_adds_column_and_fk(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    # Simulate missing column and fk
    inspector_mock.get_columns.return_value = [{"name": "id"}, {"name": "email"}]
    inspector_mock.get_foreign_keys.return_value = [{"name": "other_fk"}]
    sa_mock.inspect.return_value = inspector_mock
    op_mock.get_bind.return_value = bind
    monkeypatch.setattr(migration, 'op', op_mock)
    monkeypatch.setattr(migration, 'sa', sa_mock)
    migration.upgrade()
    assert op_mock.add_column.called
    assert op_mock.create_foreign_key.called

def test_upgrade_skips_if_exists(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    # Simulate column and fk already exist
    inspector_mock.get_columns.return_value = [{"name": "id"}, {"name": "doctor_id"}]
    inspector_mock.get_foreign_keys.return_value = [{"name": "users_doctor_id_fkey"}]
    sa_mock.inspect.return_value = inspector_mock
    op_mock.get_bind.return_value = bind
    monkeypatch.setattr(migration, 'op', op_mock)
    monkeypatch.setattr(migration, 'sa', sa_mock)
    migration.upgrade()
    assert not op_mock.add_column.called
    assert not op_mock.create_foreign_key.called

def test_downgrade_drops_fk_and_column(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_foreign_keys.return_value = [{"name": "users_doctor_id_fkey"}]
    inspector_mock.get_columns.return_value = [{"name": "id"}, {"name": "doctor_id"}]
    sa_mock.inspect.return_value = inspector_mock
    op_mock.get_bind.return_value = bind
    monkeypatch.setattr(migration, 'op', op_mock)
    monkeypatch.setattr(migration, 'sa', sa_mock)
    migration.downgrade()
    assert op_mock.drop_constraint.called
    assert op_mock.drop_column.called

def test_downgrade_skips_if_not_exists(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_foreign_keys.return_value = [{"name": "other_fk"}]
    inspector_mock.get_columns.return_value = [{"name": "id"}]
    sa_mock.inspect.return_value = inspector_mock
    op_mock.get_bind.return_value = bind
    monkeypatch.setattr(migration, 'op', op_mock)
    monkeypatch.setattr(migration, 'sa', sa_mock)
    migration.downgrade()
    assert not op_mock.drop_constraint.called
    assert not op_mock.drop_column.called
