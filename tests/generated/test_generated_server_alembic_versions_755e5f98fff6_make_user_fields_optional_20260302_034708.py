try:
    from server.alembic.versions import 755e5f98fff6_make_user_fields_optional as mod
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

def test_upgrade_alters_columns(monkeypatch):
    op = mock.Mock()
    monkeypatch.setattr(mod, 'op', op)
    mod.upgrade()
    # Should call alter_column for each field
    assert op.alter_column.call_count >= 10

def test_downgrade_alters_columns(monkeypatch):
    op = mock.Mock()
    monkeypatch.setattr(mod, 'op', op)
    mod.downgrade()
    assert op.alter_column.call_count >= 10
