# test_generated_server_alembic_versions_002_add_operators_sessions_timelines_20260302_040719.py
import pytest
try:
    from server.alembic.versions import 002_add_operators_sessions_timelines as mod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_creates_tables(monkeypatch):
    op_mock = mock.Mock()
    sa_mock = mock.Mock()
    monkeypatch.setattr(mod, "op", op_mock)
    monkeypatch.setattr(mod, "sa", sa_mock)
    mod.upgrade()
    assert op_mock.create_table.called
    assert op_mock.create_table.call_args[0][0] == "operators"


def test_downgrade_drops_tables(monkeypatch):
    op_mock = mock.Mock()
    monkeypatch.setattr(mod, "op", op_mock)
    mod.downgrade()
    assert op_mock.drop_table.call_count == 4
    calls = [mock.call("timeline_access"), mock.call("patient_timelines"), mock.call("sessions"), mock.call("operators")]
    op_mock.drop_table.assert_has_calls(calls, any_order=False)
