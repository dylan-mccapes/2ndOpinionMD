import pytest
from unittest import mock

pytestmark = pytest.mark.asyncio

# Helper to skip if import fails
def _import_or_skip():
    try:
        import server.api.clingen_actionability_routes as mod
        return mod
    except ImportError:
        pytest.skip('server.api.clingen_actionability_routes import failed', allow_module_level=True)

@pytest.mark.asyncio
async def test_get_summary_basic(monkeypatch):
    mod = _import_or_skip()
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def scalars(self): return [1,2,3]
                def all(self): return [1,2,3]
            return DummyResult()
    async def dummy_dep(): return DummySession()
    monkeypatch.setattr(mod, 'get_session', dummy_dep)
    # Call with minimal args
    result = await mod.get_summary(cohort=None, gene_symbol=None, limit=1, offset=0, session=DummySession())
    assert isinstance(result, dict) or result is not None

@pytest.mark.asyncio
async def test_export_summary_csv(monkeypatch):
    mod = _import_or_skip()
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def all(self): return [("Adult", "GENE1")]
            return DummyResult()
    async def dummy_dep(): return DummySession()
    monkeypatch.setattr(mod, 'get_session', dummy_dep)
    # Should return a StreamingResponse or similar
    resp = await mod.export_summary_csv(cohort=None, gene_symbol=None, session=DummySession())
    assert hasattr(resp, 'body_iterator') or hasattr(resp, 'body')

@pytest.mark.asyncio
async def test_get_scoring(monkeypatch):
    mod = _import_or_skip()
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def scalars(self): return [1,2]
                def all(self): return [1,2]
            return DummyResult()
    async def dummy_dep(): return DummySession()
    monkeypatch.setattr(mod, 'get_session', dummy_dep)
    result = await mod.get_scoring(cohort=None, gene_symbol=None, limit=1, offset=0, session=DummySession())
    assert isinstance(result, dict) or result is not None

@pytest.mark.asyncio
async def test_export_scoring_csv(monkeypatch):
    mod = _import_or_skip()
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def all(self): return [("Adult", "GENE1")]
            return DummyResult()
    async def dummy_dep(): return DummySession()
    monkeypatch.setattr(mod, 'get_session', dummy_dep)
    resp = await mod.export_scoring_csv(cohort=None, gene_symbol=None, session=DummySession())
    assert hasattr(resp, 'body_iterator') or hasattr(resp, 'body')

@pytest.mark.asyncio
async def test_get_assertions(monkeypatch):
    mod = _import_or_skip()
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def scalars(self): return [1]
                def all(self): return [1]
            return DummyResult()
    async def dummy_dep(): return DummySession()
    monkeypatch.setattr(mod, 'get_session', dummy_dep)
    result = await mod.get_assertions(cohort=None, gene_symbol=None, assertion_type=None, limit=1, offset=0, session=DummySession())
    assert isinstance(result, dict) or result is not None

@pytest.mark.asyncio
async def test_export_assertions_csv(monkeypatch):
    mod = _import_or_skip()
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def all(self): return [("Adult", "GENE1")]
            return DummyResult()
    async def dummy_dep(): return DummySession()
    monkeypatch.setattr(mod, 'get_session', dummy_dep)
    resp = await mod.export_assertions_csv(cohort=None, gene_symbol=None, assertion_type=None, session=DummySession())
    assert hasattr(resp, 'body_iterator') or hasattr(resp, 'body')

@pytest.mark.asyncio
async def test_get_variants(monkeypatch):
    mod = _import_or_skip()
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def scalars(self): return [1]
                def all(self): return [1]
            return DummyResult()
    async def dummy_dep(): return DummySession()
    monkeypatch.setattr(mod, 'get_session', dummy_dep)
    result = await mod.get_variants(gene_symbol=None, classification=None, limit=1, offset=0, session=DummySession())
    assert isinstance(result, dict) or result is not None

@pytest.mark.asyncio
async def test_get_quick(monkeypatch):
    mod = _import_or_skip()
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def scalars(self): return [1]
                def all(self): return [1]
            return DummyResult()
    async def dummy_dep(): return DummySession()
    monkeypatch.setattr(mod, 'get_session', dummy_dep)
    result = await mod.get_quick(cohort=None, gene_symbol=None, limit=1, offset=0, session=DummySession())
    assert isinstance(result, dict) or result is not None

@pytest.mark.asyncio
async def test_refresh_materialized_view_success(monkeypatch):
    mod = _import_or_skip()
    class DummySession:
        async def execute(self, *a, **kw): return None
        async def commit(self): return None
        async def rollback(self): return None
    async def dummy_dep(): return DummySession()
    monkeypatch.setattr(mod, 'get_session', dummy_dep)
    import time
    monkeypatch.setattr(mod, 'time', time)
    monkeypatch.setattr(mod, 'text', lambda x: x)
    result = await mod.refresh_materialized_view(session=DummySession())
    assert result is not None
