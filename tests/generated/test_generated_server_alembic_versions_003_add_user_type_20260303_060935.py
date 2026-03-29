import pytest
try:
    import server.alembic.versions.003_add_user_type as mod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_adds_user_type_column(monkeypatch):
    mock_op = mock.Mock()
    mock_sa = mock.Mock()
    mock_bind = mock.Mock()
    mock_inspector = mock.Mock()
    mock_inspector.get_columns.return_value = [{"name": "id"}, {"name": "email"}]
    mock_sa.inspect.return_value = mock_inspector
    mock_op.get_bind.return_value = mock_bind
    monkeypatch.setattr(mod, 'op', mock_op)
    monkeypatch.setattr(mod, 'sa', mock_sa)
    mod.upgrade()
    assert mock_op.add_column.called
    args = mock_op.add_column.call_args[0]
    assert "users" in args


def test_upgrade_skips_if_column_exists(monkeypatch):
    mock_op = mock.Mock()
    mock_sa = mock.Mock()
    mock_bind = mock.Mock()
    mock_inspector = mock.Mock()
    mock_inspector.get_columns.return_value = [{"name": "user_type"}]
    mock_sa.inspect.return_value = mock_inspector
    mock_op.get_bind.return_value = mock_bind
    monkeypatch.setattr(mod, 'op', mock_op)
    monkeypatch.setattr(mod, 'sa', mock_sa)
    mod.upgrade()
    assert not mock_op.add_column.called


def test_downgrade_drops_user_type_column(monkeypatch):
    mock_op = mock.Mock()
    mock_sa = mock.Mock()
    mock_bind = mock.Mock()
    mock_inspector = mock.Mock()
    mock_inspector.get_columns.return_value = [{"name": "user_type"}]
    mock_sa.inspect.return_value = mock_inspector
    mock_op.get_bind.return_value = mock_bind
    monkeypatch.setattr(mod, 'op', mock_op)
    monkeypatch.setattr(mod, 'sa', mock_sa)
    mod.downgrade()
    assert mock_op.drop_column.called
    args = mock_op.drop_column.call_args[0]
    assert "users" in args and "user_type" in args
