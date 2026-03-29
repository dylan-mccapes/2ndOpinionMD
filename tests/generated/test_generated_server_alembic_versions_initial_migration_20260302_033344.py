import pytest
from unittest import mock

@pytest.mark.skipif('server.alembic.versions.initial_migration' not in globals(), reason='Module not importable')
def test_upgrade_and_downgrade(monkeypatch):
    try:
        from server.alembic.versions import initial_migration
    except ImportError:
        pytest.skip('initial_migration module not importable')
    op_mock = mock.Mock()
    monkeypatch.setattr(initial_migration, 'op', op_mock)
    # Test upgrade
    initial_migration.upgrade()
    assert op_mock.create_table.called
    # Test downgrade
    op_mock.reset_mock()
    initial_migration.downgrade()
    assert op_mock.drop_table.call_count >= 1