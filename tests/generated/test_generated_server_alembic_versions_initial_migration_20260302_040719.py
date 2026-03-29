import pytest
try:
    from server.alembic.versions import initial_migration
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_creates_users_table(monkeypatch):
    mock_op = mock.Mock()
    monkeypatch.setattr(initial_migration, 'op', mock_op)
    monkeypatch.setattr(initial_migration, 'sa', mock.Mock())
    initial_migration.upgrade()
    assert mock_op.create_table.called
    args, kwargs = mock_op.create_table.call_args
    assert 'users' in args

def test_downgrade_drops_tables(monkeypatch):
    mock_op = mock.Mock()
    monkeypatch.setattr(initial_migration, 'op', mock_op)
    initial_migration.downgrade()
    calls = [mock.call.drop_table('medical_knowledge'), mock.call.drop_table('journal_entries'), mock.call.drop_table('users')]
    mock_op.drop_table.assert_has_calls(calls, any_order=False)
