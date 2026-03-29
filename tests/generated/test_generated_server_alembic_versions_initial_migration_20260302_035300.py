try:
    from server.alembic.versions import initial_migration as mod
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

def test_upgrade_creates_users_table(monkeypatch):
    op_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    mod.upgrade()
    assert op_mock.create_table.called
    args, kwargs = op_mock.create_table.call_args
    assert 'users' in args

def test_downgrade_drops_tables(monkeypatch):
    op_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    mod.downgrade()
    # Should drop all three tables
    dropped = [call[0][0] for call in op_mock.drop_table.call_args_list]
    assert 'users' in dropped
    assert 'journal_entries' in dropped
    assert 'medical_knowledge' in dropped
