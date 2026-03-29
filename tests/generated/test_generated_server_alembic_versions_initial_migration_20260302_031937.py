import pytest
from unittest import mock

try:
    import server.alembic.versions.initial_migration as initial_migration
except ImportError:
    initial_migration = None

def test_upgrade_creates_tables(monkeypatch):
    if initial_migration is None:
        pytest.skip('initial_migration module not importable')
    op_mock = mock.Mock()
    monkeypatch.setattr(initial_migration, 'op', op_mock)
    monkeypatch.setattr(initial_migration, 'sa', mock.Mock())
    initial_migration.upgrade()
    assert op_mock.create_table.called
    assert any('users' in str(call) for call in op_mock.create_table.call_args_list[0][0])

def test_downgrade_drops_tables(monkeypatch):
    if initial_migration is None:
        pytest.skip('initial_migration module not importable')
    op_mock = mock.Mock()
    monkeypatch.setattr(initial_migration, 'op', op_mock)
    initial_migration.downgrade()
    calls = [call[0][0] for call in op_mock.drop_table.call_args_list]
    assert 'users' in calls
    assert 'journal_entries' in calls
    assert 'medical_knowledge' in calls
