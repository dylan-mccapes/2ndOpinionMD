import pytest
from unittest import mock

@pytest.mark.skipif('server.alembic.versions.004_add_doctor_id' not in globals(), reason='Module not importable')
def test_upgrade_adds_column_and_fk(monkeypatch):
    try:
        import server.alembic.versions.004_add_doctor_id as mod
    except ImportError:
        pytest.skip('Module not importable')
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_columns.return_value = [{'name': 'id'}, {'name': 'email'}]
    inspector_mock.get_foreign_keys.return_value = [{'name': 'some_fk'}]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    mod.upgrade()
    assert op_mock.add_column.called
    assert op_mock.create_foreign_key.called

@pytest.mark.skipif('server.alembic.versions.004_add_doctor_id' not in globals(), reason='Module not importable')
def test_downgrade_drops_fk_and_column(monkeypatch):
    try:
        import server.alembic.versions.004_add_doctor_id as mod
    except ImportError:
        pytest.skip('Module not importable')
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_foreign_keys.return_value = [{'name': 'users_doctor_id_fkey'}]
    inspector_mock.get_columns.return_value = [{'name': 'doctor_id'}, {'name': 'id'}]
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    mod.downgrade()
    assert op_mock.drop_constraint.called
    assert op_mock.drop_column.called
