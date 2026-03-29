import pytest
try:
    from server.alembic.versions import initial_migration
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_calls_create_table():
    with mock.patch('server.alembic.versions.initial_migration.op.create_table') as mock_create_table:
        initial_migration.upgrade()
        assert mock_create_table.called

def test_downgrade_calls_drop_table():
    with mock.patch('server.alembic.versions.initial_migration.op.drop_table') as mock_drop_table:
        initial_migration.downgrade()
        # Should drop all three tables
        calls = [mock.call('medical_knowledge'), mock.call('journal_entries'), mock.call('users')]
        mock_drop_table.assert_has_calls(calls, any_order=False)
        assert mock_drop_table.call_count == 3
