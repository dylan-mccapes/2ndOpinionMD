# test_generated_server_alembic_versions_003_add_user_type_20260302_040719.py
import pytest
try:
    from server.alembic.versions import 003_add_user_type as mod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_adds_user_type(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = mock.Mock()
    inspector = mock.Mock()
    inspector.get_columns.return_value = [{"name": "id"}, {"name": "email"}]
    monkeypatch.setattr(mod, "op", op_mock)
    monkeypatch.setattr(mod, "sa", sa_mock)
    op_mock.get_bind.return_value = bind
    sa_mock.inspect.return_value = inspector
    mod.upgrade()
    assert op_mock.add_column.called
    assert op_mock.add_column.call_args[0][0] == "users"


def test_upgrade_skips_if_exists(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = mock.Mock()
    inspector = mock.Mock()
    inspector.get_columns.return_value = [{"name": "user_type"}]
    monkeypatch.setattr(mod, "op", op_mock)
    monkeypatch.setattr(mod, "sa", sa_mock)
    op_mock.get_bind.return_value = bind
    sa_mock.inspect.return_value = inspector
    mod.upgrade()
    assert not op_mock.add_column.called


def test_downgrade_drops_user_type(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = mock.Mock()
    inspector = mock.Mock()
    inspector.get_columns.return_value = [{"name": "user_type"}]
    monkeypatch.setattr(mod, "op", op_mock)
    monkeypatch.setattr(mod, "sa", sa_mock)
    op_mock.get_bind.return_value = bind
    sa_mock.inspect.return_value = inspector
    mod.downgrade()
    assert op_mock.drop_column.called
    assert op_mock.drop_column.call_args[0] == ("users", "user_type")


def test_downgrade_skips_if_not_exists(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    bind = mock.Mock()
    inspector = mock.Mock()
    inspector.get_columns.return_value = [{"name": "id"}]
    monkeypatch.setattr(mod, "op", op_mock)
    monkeypatch.setattr(mod, "sa", sa_mock)
    op_mock.get_bind.return_value = bind
    sa_mock.inspect.return_value = inspector
    mod.downgrade()
    assert not op_mock.drop_column.called
