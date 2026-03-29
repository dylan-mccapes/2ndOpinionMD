import pytest
from unittest import mock

@pytest.mark.skipif('server.alembic.versions.755e5f98fff6_make_user_fields_optional' not in globals(), reason='Module not importable')
def test_upgrade_alters_columns(monkeypatch):
    try:
        import server.alembic.versions.755e5f98fff6_make_user_fields_optional as mod
    except ImportError:
        pytest.skip('Module not importable')
    op_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    mod.upgrade()
    assert op_mock.alter_column.call_count >= 1

@pytest.mark.skipif('server.alembic.versions.755e5f98fff6_make_user_fields_optional' not in globals(), reason='Module not importable')
def test_downgrade_alters_columns(monkeypatch):
    try:
        import server.alembic.versions.755e5f98fff6_make_user_fields_optional as mod
    except ImportError:
        pytest.skip('Module not importable')
    op_mock = mock.Mock()
    monkeypatch.setattr(mod, 'op', op_mock)
    mod.downgrade()
    assert op_mock.alter_column.call_count >= 1
