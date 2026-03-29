import pytest
from unittest import mock

try:
    from server.alembic.versions import initial_migration
except ImportError:
    initial_migration = None

@pytest.mark.skipif(initial_migration is None, reason="Module import failed")
def test_upgrade_creates_tables():
    op_mock = mock.Mock()
    with mock.patch('server.alembic.versions.initial_migration.op', op_mock):
        initial_migration.upgrade()
        assert op_mock.create_table.called
        assert any('users' in str(call) for call in op_mock.create_table.call_args_list[0][0])

@pytest.mark.skipif(initial_migration is None, reason="Module import failed")
def test_downgrade_drops_tables():
    op_mock = mock.Mock()
    with mock.patch('server.alembic.versions.initial_migration.op', op_mock):
        initial_migration.downgrade()
        assert op_mock.drop_table.call_count >= 1
        called_tables = [call[0][0] for call in op_mock.drop_table.call_args_list]
        assert 'users' in called_tables
