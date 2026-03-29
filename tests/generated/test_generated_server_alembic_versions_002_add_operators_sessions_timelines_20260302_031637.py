import pytest
from unittest import mock

try:
    import server.alembic.versions.002_add_operators_sessions_timelines as mod
except ImportError:
    pytest.skip('server.alembic.versions.002_add_operators_sessions_timelines could not be imported', allow_module_level=True)


def test_upgrade_creates_tables(monkeypatch):
    mock_op = mock.Mock()
    monkeypatch.setattr(mod, 'op', mock_op)
    monkeypatch.setattr(mod, 'sa', mock.Mock())
    mod.upgrade()
    assert mock_op.create_table.called


def test_downgrade_drops_tables(monkeypatch):
    mock_op = mock.Mock()
    monkeypatch.setattr(mod, 'op', mock_op)
    mod.downgrade()
    assert mock_op.drop_table.call_count >= 1
