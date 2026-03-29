# AUTO-GENERATED TESTS FOR server/alembic/versions/002_add_operators_sessions_timelines.py
import pytest
from unittest import mock

@pytest.mark.skipif('server.alembic.versions.002_add_operators_sessions_timelines' not in globals(), reason='Module not importable')
def test_upgrade(monkeypatch):
    try:
        import server.alembic.versions.002_add_operators_sessions_timelines as mod
    except ImportError:
        pytest.skip('module not importable')
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    mod.upgrade()
    assert op_mock.create_table.called

@pytest.mark.skipif('server.alembic.versions.002_add_operators_sessions_timelines' not in globals(), reason='Module not importable')
def test_downgrade(monkeypatch):
    try:
        import server.alembic.versions.002_add_operators_sessions_timelines as mod
    except ImportError:
        pytest.skip('module not importable')
    op_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    mod.downgrade()
    assert op_mock.drop_table.call_count == 4
