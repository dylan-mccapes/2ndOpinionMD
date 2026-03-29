import pytest
try:
    import server.alembic.versions.002_add_operators_sessions_timelines as mod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_creates_tables(monkeypatch):
    mock_op = mock.Mock()
    monkeypatch.setattr(mod, 'op', mock_op)
    monkeypatch.setattr(mod, 'sa', mock.Mock())
    mod.upgrade()
    assert mock_op.create_table.called
    calls = [c[0][0] for c in mock_op.create_table.call_args_list]
    assert "operators" in calls or any("operators" in str(arg) for arg in calls)


def test_downgrade_drops_tables(monkeypatch):
    mock_op = mock.Mock()
    monkeypatch.setattr(mod, 'op', mock_op)
    mod.downgrade()
    assert mock_op.drop_table.call_count >= 1
    dropped = [c[0][0] for c in mock_op.drop_table.call_args_list]
    assert "operators" in dropped or any("operators" in str(arg) for arg in dropped)
