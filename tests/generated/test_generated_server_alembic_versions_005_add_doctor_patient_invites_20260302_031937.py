import pytest
from unittest import mock

@pytest.mark.skipif('server.alembic.versions.005_add_doctor_patient_invites' not in globals(), reason='Module not importable')
def test_upgrade_creates_table(monkeypatch):
    try:
        import server.alembic.versions.005_add_doctor_patient_invites as mod
    except ImportError:
        pytest.skip('Module not importable')
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_table_names.return_value = ['users']
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    mod.upgrade()
    assert op_mock.create_table.called

@pytest.mark.skipif('server.alembic.versions.005_add_doctor_patient_invites' not in globals(), reason='Module not importable')
def test_downgrade_drops_table(monkeypatch):
    try:
        import server.alembic.versions.005_add_doctor_patient_invites as mod
    except ImportError:
        pytest.skip('Module not importable')
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = object()
    inspector_mock = mock.Mock()
    inspector_mock.get_table_names.return_value = ['doctor_patient_invites']
    sa_mock.inspect.return_value = inspector_mock
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    op_mock.get_bind.return_value = bind
    mod.downgrade()
    assert op_mock.drop_table.called
