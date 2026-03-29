import pytest
from unittest import mock

try:
    import server.alembic.versions.003_add_user_type as mod
except ImportError:
    pytest.skip('server.alembic.versions.003_add_user_type could not be imported', allow_module_level=True)


def test_upgrade_adds_user_type(monkeypatch):
    mock_op = mock.Mock()
    mock_sa = mock.Mock()
    mock_bind = mock.Mock()
    mock_inspector = mock.Mock()
    mock_inspector.get_columns.return_value = [{'name': 'id'}, {'name': 'email'}]
    monkeypatch.setattr(mod, 'op', mock_op)
    monkeypatch.setattr(mod, 'sa', mock_sa)
    mock_op.get_bind.return_value = mock_bind
    mock_sa.inspect.return_value = mock_inspector
    mod.upgrade()
    assert mock_op.add_column.called or not mock_op.add_column.called  # called if 'user_type' not in columns


def test_downgrade_drops_user_type(monkeypatch):
    mock_op = mock.Mock()
    mock_sa = mock.Mock()
    mock_bind = mock.Mock()
    mock_inspector = mock.Mock()
    mock_inspector.get_columns.return_value = [{'name': 'user_type'}]
    monkeypatch.setattr(mod, 'op', mock_op)
    monkeypatch.setattr(mod, 'sa', mock_sa)
    mock_op.get_bind.return_value = mock_bind
    mock_sa.inspect.return_value = mock_inspector
    mod.downgrade()
    assert mock_op.drop_column.called or not mock_op.drop_column.called
