try:
    import pytest
    from unittest import mock
    import server.alembic.versions.005_add_doctor_patient_invites as migration
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

def test_upgrade_creates_table(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_table_names.return_value = ["users"]
    sa_mock.inspect.return_value = inspector_mock
    op_mock.get_bind.return_value = bind
    monkeypatch.setattr(migration, 'op', op_mock)
    monkeypatch.setattr(migration, 'sa', sa_mock)
    migration.upgrade()
    assert op_mock.create_table.called

def test_upgrade_skips_if_table_exists(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_table_names.return_value = ["users", "doctor_patient_invites"]
    sa_mock.inspect.return_value = inspector_mock
    op_mock.get_bind.return_value = bind
    monkeypatch.setattr(migration, 'op', op_mock)
    monkeypatch.setattr(migration, 'sa', sa_mock)
    migration.upgrade()
    assert not op_mock.create_table.called

def test_downgrade_drops_table(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_table_names.return_value = ["doctor_patient_invites", "users"]
    sa_mock.inspect.return_value = inspector_mock
    op_mock.get_bind.return_value = bind
    monkeypatch.setattr(migration, 'op', op_mock)
    monkeypatch.setattr(migration, 'sa', sa_mock)
    migration.downgrade()
    assert op_mock.drop_table.called

def test_downgrade_skips_if_table_not_exists(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_table_names.return_value = ["users"]
    sa_mock.inspect.return_value = inspector_mock
    op_mock.get_bind.return_value = bind
    monkeypatch.setattr(migration, 'op', op_mock)
    monkeypatch.setattr(migration, 'sa', sa_mock)
    migration.downgrade()
    assert not op_mock.drop_table.called
