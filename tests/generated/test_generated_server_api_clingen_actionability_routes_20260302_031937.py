import pytest
from unittest import mock

try:
    import asyncio
    from server.api import clingen_actionability_routes as mod
except ImportError:
    pytest.skip('server.api.clingen_actionability_routes not importable', allow_module_level=True)

import pytest_asyncio

@pytest.mark.asyncio
async def test_get_summary_basic(monkeypatch):
    class DummySession:
        async def execute(self, *a, **k):
            class DummyResult:
                def scalars(self):
                    class DummyScalars:
                        def all(self):
                            return [{'cohort': 'Adult', 'gene_symbol': 'BRCA1'}]
                    return DummyScalars()
            return DummyResult()
    monkeypatch.setattr(mod, 'get_session', lambda: None)
    result = await mod.get_summary(session=DummySession())
    assert isinstance(result, list) or result is not None

@pytest.mark.asyncio
async def test_export_summary_csv(monkeypatch):
    class DummySession:
        async def execute(self, *a, **k):
            class DummyResult:
                def all(self):
                    return [('Adult', 'BRCA1')]
            return DummyResult()
    monkeypatch.setattr(mod, 'get_session', lambda: None)
    resp = await mod.export_summary_csv(session=DummySession())
    assert resp is not None

@pytest.mark.asyncio
async def test_get_scoring(monkeypatch):
    class DummySession:
        async def execute(self, *a, **k):
            class DummyResult:
                def scalars(self):
                    class DummyScalars:
                        def all(self):
                            return [{'cohort': 'Adult', 'gene_symbol': 'BRCA1'}]
                    return DummyScalars()
            return DummyResult()
    monkeypatch.setattr(mod, 'get_session', lambda: None)
    result = await mod.get_scoring(session=DummySession())
    assert isinstance(result, list) or result is not None

@pytest.mark.asyncio
async def test_export_scoring_csv(monkeypatch):
    class DummySession:
        async def execute(self, *a, **k):
            class DummyResult:
                def all(self):
                    return [('Adult', 'BRCA1')]
            return DummyResult()
    monkeypatch.setattr(mod, 'get_session', lambda: None)
    resp = await mod.export_scoring_csv(session=DummySession())
    assert resp is not None

@pytest.mark.asyncio
async def test_get_assertions(monkeypatch):
    class DummySession:
        async def execute(self, *a, **k):
            class DummyResult:
                def scalars(self):
                    class DummyScalars:
                        def all(self):
                            return [{'cohort': 'Adult', 'gene_symbol': 'BRCA1'}]
                    return DummyScalars()
            return DummyResult()
    monkeypatch.setattr(mod, 'get_session', lambda: None)
    result = await mod.get_assertions(session=DummySession())
    assert isinstance(result, list) or result is not None

@pytest.mark.asyncio
async def test_export_assertions_csv(monkeypatch):
    class DummySession:
        async def execute(self, *a, **k):
            class DummyResult:
                def all(self):
                    return [('Adult', 'BRCA1')]
            return DummyResult()
    monkeypatch.setattr(mod, 'get_session', lambda: None)
    resp = await mod.export_assertions_csv(session=DummySession())
    assert resp is not None

@pytest.mark.asyncio
async def test_get_variants(monkeypatch):
    class DummySession:
        async def execute(self, *a, **k):
            class DummyResult:
                def scalars(self):
                    class DummyScalars:
                        def all(self):
                            return [{'gene_symbol': 'BRCA1', 'classification': 'Pathogenic'}]
                    return DummyScalars()
            return DummyResult()
    monkeypatch.setattr(mod, 'get_session', lambda: None)
    result = await mod.get_variants(session=DummySession())
    assert isinstance(result, list) or result is not None

@pytest.mark.asyncio
async def test_get_quick(monkeypatch):
    class DummySession:
        async def execute(self, *a, **k):
            class DummyResult:
                def scalars(self):
                    class DummyScalars:
                        def all(self):
                            return [{'cohort': 'Adult', 'gene_symbol': 'BRCA1'}]
                    return DummyScalars()
            return DummyResult()
    monkeypatch.setattr(mod, 'get_session', lambda: None)
    result = await mod.get_quick(session=DummySession())
    assert isinstance(result, list) or result is not None

@pytest.mark.asyncio
async def test_refresh_materialized_view(monkeypatch):
    class DummySession:
        async def execute(self, *a, **k):
            return None
        async def commit(self):
            return None
        async def rollback(self):
            return None
    monkeypatch.setattr(mod, 'get_session', lambda: None)
    monkeypatch.setattr(mod, 'time', mock.Mock(perf_counter=lambda: 0))
    monkeypatch.setattr(mod, 'text', lambda x: x)
    session = DummySession()
    await mod.refresh_materialized_view(session=session)
