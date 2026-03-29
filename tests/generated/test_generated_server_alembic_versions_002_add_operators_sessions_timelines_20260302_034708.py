try:
    import pytest
    from server.alembic.versions import 002_add_operators_sessions_timelines as mod
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_calls_create_table(monkeypatch):
    op = mock.Mock()
    sa = mock.Mock()
    monkeypatch.setattr(mod, 'op', op)
    monkeypatch.setattr(mod, 'sa', sa)
    mod.upgrade()
    assert op.create_table.called


def test_downgrade_calls_drop_table(monkeypatch):
    op = mock.Mock()
    monkeypatch.setattr(mod, 'op', op)
    mod.downgrade()
    assert op.drop_table.call_count >= 1