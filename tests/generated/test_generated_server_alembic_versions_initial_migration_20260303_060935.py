import pytest
try:
    from server.alembic.versions import initial_migration
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
import types
from unittest import mock

def test_upgrade_calls_create_table(monkeypatch):
    op_mock = mock.Mock()
    monkeypatch.setattr(initial_migration, 'op', op_mock)
    monkeypatch.setattr(initial_migration, 'sa', mock.Mock())
    initial_migration.upgrade()
    assert op_mock.create_table.called

def test_downgrade_calls_drop_table(monkeypatch):
    op_mock = mock.Mock()
    monkeypatch.setattr(initial_migration, 'op', op_mock)
    initial_migration.downgrade()
    assert op_mock.drop_table.call_count >= 1
