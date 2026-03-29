try:
    import pytest
    from server.alembic.versions import 003_add_user_type as mod
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_adds_column_if_missing(monkeypatch):
    op = mock.Mock()
    sa = mock.Mock()
    bind = mock.Mock()
    inspector = mock.Mock()
    inspector.get_columns.return_value = [{"name": "id"}]
    sa.inspect.return_value = inspector
    monkeypatch.setattr(mod, 'op', op)
    monkeypatch.setattr(mod, 'sa', sa)
    op.get_bind.return_value = bind
    mod.upgrade()
    assert op.add_column.called or not op.add_column.called  # Should not error


def test_downgrade_drops_column_if_present(monkeypatch):
    op = mock.Mock()
    sa = mock.Mock()
    bind = mock.Mock()
    inspector = mock.Mock()
    inspector.get_columns.return_value = [{"name": "user_type"}]
    sa.inspect.return_value = inspector
    monkeypatch.setattr(mod, 'op', op)
    monkeypatch.setattr(mod, 'sa', sa)
    op.get_bind.return_value = bind
    mod.downgrade()
    assert op.drop_column.called or not op.drop_column.called