import pytest
try:
    from server.alembic.versions import 002_add_operators_sessions_timelines as mod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_calls_create_table(monkeypatch):
    op_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', mock.Mock())
    mod.upgrade()
    assert op_mock.create_table.called

def test_downgrade_calls_drop_table(monkeypatch):
    op_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    mod.downgrade()
    assert op_mock.drop_table.call_count >= 1
