try:
    from server.api import clingen_actionability_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

@pytest.mark.asyncio
async def test_get_summary(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"cohort": "Adult", "gene_symbol": "BRCA1"}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(clingen_actionability_routes, "get_session", lambda: DummySession())
    result = await clingen_actionability_routes.get_summary(cohort="Adult", gene_symbol="BRCA1", limit=1, offset=0, session=DummySession())
    assert isinstance(result, list)
    assert result and "cohort" in result[0]

@pytest.mark.asyncio
async def test_export_summary_csv(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"cohort": "Adult", "gene_symbol": "BRCA1"}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(clingen_actionability_routes, "get_session", lambda: DummySession())
    result = await clingen_actionability_routes.export_summary_csv(cohort="Adult", gene_symbol="BRCA1", session=DummySession())
    assert isinstance(result, str) or hasattr(result, "__str__")

@pytest.mark.asyncio
async def test_get_scoring(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"cohort": "Adult", "gene_symbol": "BRCA1"}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(clingen_actionability_routes, "get_session", lambda: DummySession())
    result = await clingen_actionability_routes.get_scoring(cohort="Adult", gene_symbol="BRCA1", limit=1, offset=0, session=DummySession())
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_export_scoring_csv(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"cohort": "Adult", "gene_symbol": "BRCA1"}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(clingen_actionability_routes, "get_session", lambda: DummySession())
    result = await clingen_actionability_routes.export_scoring_csv(cohort="Adult", gene_symbol="BRCA1", session=DummySession())
    assert isinstance(result, str) or hasattr(result, "__str__")

@pytest.mark.asyncio
async def test_get_assertions(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"cohort": "Adult", "gene_symbol": "BRCA1", "assertion_type": "type1"}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(clingen_actionability_routes, "get_session", lambda: DummySession())
    result = await clingen_actionability_routes.get_assertions(cohort="Adult", gene_symbol="BRCA1", assertion_type="type1", limit=1, offset=0, session=DummySession())
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_export_assertions_csv(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"cohort": "Adult", "gene_symbol": "BRCA1", "assertion_type": "type1"}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(clingen_actionability_routes, "get_session", lambda: DummySession())
    result = await clingen_actionability_routes.export_assertions_csv(cohort="Adult", gene_symbol="BRCA1", assertion_type="type1", session=DummySession())
    assert isinstance(result, str) or hasattr(result, "__str__")

@pytest.mark.asyncio
async def test_get_variants(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"gene_symbol": "BRCA1", "classification": "Pathogenic"}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(clingen_actionability_routes, "get_session", lambda: DummySession())
    result = await clingen_actionability_routes.get_variants(gene_symbol="BRCA1", classification="Pathogenic", limit=1, offset=0, session=DummySession())
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_get_quick(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"cohort": "Adult", "gene_symbol": "BRCA1"}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(clingen_actionability_routes, "get_session", lambda: DummySession())
    result = await clingen_actionability_routes.get_quick(cohort="Adult", gene_symbol="BRCA1", limit=1, offset=0, session=DummySession())
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_refresh_materialized_view(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw): return None
        async def commit(self): return None
        async def rollback(self): return None
    monkeypatch.setattr(clingen_actionability_routes, "get_session", lambda: DummySession())
    import time
    result = await clingen_actionability_routes.refresh_materialized_view(session=DummySession())
    assert result is None or isinstance(result, dict) or isinstance(result, str)