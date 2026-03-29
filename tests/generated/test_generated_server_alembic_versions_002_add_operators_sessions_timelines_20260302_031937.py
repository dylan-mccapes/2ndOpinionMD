import pytest
from unittest import mock

def test_upgrade_creates_tables(monkeypatch):
    try:
        import server.alembic.versions.002_add_operators_sessions_timelines as mod
    except ImportError:
        pytest.skip('module not importable')
    called = {}
    monkeypatch.setattr(mod.op, 'create_table', lambda *a, **k: called.setdefault('create_table', []).append(a[0]) if 'create_table' in called else called.setdefault('create_table', [a[0]]))
    monkeypatch.setattr(mod.sa, 'Column', lambda *a, **k: None)
    monkeypatch.setattr(mod.sa, 'UUID', lambda: None)
    monkeypatch.setattr(mod.sa, 'String', lambda *a, **k: None)
    monkeypatch.setattr(mod.sa, 'DateTime', lambda *a, **k: None)
    monkeypatch.setattr(mod.sa, 'text', lambda *a, **k: None)
    monkeypatch.setattr(mod.sa, 'ForeignKeyConstraint', lambda *a, **k: None)
    monkeypatch.setattr(mod.sa, 'PrimaryKeyConstraint', lambda *a, **k: None)
    monkeypatch.setattr(mod.sa, 'UniqueConstraint', lambda *a, **k: None)
    mod.upgrade()
    assert 'operators' in called.get('create_table', [])


def test_downgrade_drops_tables(monkeypatch):
    try:
        import server.alembic.versions.002_add_operators_sessions_timelines as mod
    except ImportError:
        pytest.skip('module not importable')
    called = {}
    monkeypatch.setattr(mod.op, 'drop_table', lambda name: called.setdefault('drop', []).append(name))
    mod.downgrade()
    for tbl in ['timeline_access', 'patient_timelines', 'sessions', 'operators']:
        assert tbl in called['drop']
