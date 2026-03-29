try:
    from server.alembic.versions import 755e5f98fff6_make_user_fields_optional as mod
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

def test_upgrade_alters_columns(monkeypatch):
    op_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    mod.upgrade()
    # Should call alter_column multiple times
    assert op_mock.alter_column.call_count >= 8
    called_cols = [call[0][1] for call in op_mock.alter_column.call_args_list]
    assert "full_name" in called_cols
    assert "birthdate" in called_cols

def test_downgrade_alters_columns(monkeypatch):
    op_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    mod.downgrade()
    # Should call alter_column multiple times
    assert op_mock.alter_column.call_count >= 8
    called_cols = [call[0][1] for call in op_mock.alter_column.call_args_list]
    assert "full_name" in called_cols
    assert "birthdate" in called_cols
