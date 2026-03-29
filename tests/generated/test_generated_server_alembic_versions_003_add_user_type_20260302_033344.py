# AUTO-GENERATED TESTS FOR server/alembic/versions/003_add_user_type.py
import pytest
from unittest import mock

@pytest.mark.skipif('server.alembic.versions.003_add_user_type' not in globals(), reason='Module not importable')
def test_upgrade(monkeypatch):
    try:
        import server.alembic.versions.003_add_user_type as mod
    except ImportError:
        pytest.skip('module not importable')
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    bind_mock = mock.Mock()
    inspector_mock = mock.Mock()
    inspector_mock.get_columns.return_value = [{"name": "id"}]
    monkeypatch.setattr(op_mock, 'get_bind', mock.Mock(return_value=bind_mock))
    monkeypatch.setattr(sa_mock, 'inspect', mock.Mock(return_value=inspector_mock))
    mod.upgrade()
    # Should call add_column since 'user_type' not in columns
    assert op_mock.add_column.called

@pytest.mark.skipif('server.alembic.versions.003_add_user_type' not in globals(), reason='Module not importable')
def test_downgrade(monkeypatch):
    try:
        import server.alembic.versions.003_add_user_type as mod
    except ImportError:
        pytest.skip('module not importable')
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    monkeypatch.setattr(mod, 'sa', sa_mock)
    bind_mock = mock.Mock()
    inspector_mock = mock.Mock()
    inspector_mock.get_columns.return_value = [{"name": "user_type"}]
    monkeypatch.setattr(op_mock, 'get_bind', mock.Mock(return_value=bind_mock))
    monkeypatch.setattr(sa_mock, 'inspect', mock.Mock(return_value=inspector_mock))
    mod.downgrade()
    assert op_mock.drop_column.called
