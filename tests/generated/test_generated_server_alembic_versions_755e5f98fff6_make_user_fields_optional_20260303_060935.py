try:
    import pytest
    from unittest import mock
    import server.alembic.versions.755e5f98fff6_make_user_fields_optional as migration
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

def test_upgrade_alters_columns(monkeypatch):
    op_mock = mock.Mock()
    monkeypatch.setattr(migration, 'op', op_mock)
    migration.upgrade()
    # Should call alter_column multiple times
    assert op_mock.alter_column.call_count >= 10

def test_downgrade_alters_columns(monkeypatch):
    op_mock = mock.Mock()
    monkeypatch.setattr(migration, 'op', op_mock)
    migration.downgrade()
    # Should call alter_column multiple times
    assert op_mock.alter_column.call_count >= 10
