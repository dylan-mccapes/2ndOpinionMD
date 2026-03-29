# test_generated_server_alembic_versions_002_add_operators_sessions_timelines_20260302_034348.py
import pytest
try:
    from server.alembic.versions import 002_add_operators_sessions_timelines as mod
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock

def test_upgrade_creates_tables(monkeypatch):
    called = {}
    monkeypatch.setattr(mod.op, 'create_table', lambda *a, **kw: called.setdefault('create_table', []).append(a[0]))
    monkeypatch.setattr(mod.sa, 'Column', lambda *a, **kw: None)
    monkeypatch.setattr(mod.sa, 'UUID', lambda: None)
    monkeypatch.setattr(mod.sa, 'String', lambda *a, **kw: None)
    monkeypatch.setattr(mod.sa, 'DateTime', lambda *a, **kw: None)
    monkeypatch.setattr(mod.sa, 'text', lambda x: None)
    monkeypatch.setattr(mod.sa, 'ForeignKeyConstraint', lambda *a, **kw: None)
    monkeypatch.setattr(mod.sa, 'PrimaryKeyConstraint', lambda *a, **kw: None)
    monkeypatch.setattr(mod.sa, 'UniqueConstraint', lambda *a, **kw: None)
    mod.upgrade()
    assert 'operators' in called.get('create_table', [])

def test_downgrade_drops_tables(monkeypatch):
    called = {}
    monkeypatch.setattr(mod.op, 'drop_table', lambda name: called.setdefault('drop_table', []).append(name))
    mod.downgrade()
    assert set(['timeline_access', 'patient_timelines', 'sessions', 'operators']).issubset(set(called.get('drop_table', [])))
