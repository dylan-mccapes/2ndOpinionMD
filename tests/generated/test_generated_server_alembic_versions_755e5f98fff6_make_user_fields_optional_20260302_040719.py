# AUTO-GENERATED TESTS FOR server/alembic/versions/755e5f98fff6_make_user_fields_optional.py
import pytest
try:
    import server.alembic.versions.755e5f98fff6_make_user_fields_optional as mod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_alters_columns(monkeypatch):
    op_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    mod.upgrade()
    # Should call alter_column for each field
    assert op_mock.alter_column.call_count >= 10

def test_downgrade_alters_columns(monkeypatch):
    op_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    mod.downgrade()
    # Should call alter_column for each field
    assert op_mock.alter_column.call_count >= 10
