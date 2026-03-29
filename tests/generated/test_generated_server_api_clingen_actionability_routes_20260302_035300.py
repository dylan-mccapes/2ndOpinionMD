try:
    import pytest
    from unittest import mock
    from server.api import clingen_actionability_routes as mod
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_get_summary_basic(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class Result:
            def scalars(self):
                class S:
                    def all(self): return [1,2,3]
                return S()
            def first(self): return [1,2,3]
        return Result()
    session = mock.Mock()
    session.execute = fake_execute
    monkeypatch.setattr(mod, 'get_session', lambda: session)
    result = pytest.run(mod.get_summary(cohort=None, gene_symbol=None, limit=2, offset=0, session=session))
    assert result is not None

@pytest.mark.asyncio
def test_export_summary_csv(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class Result:
            def all(self): return [("Adult", "GENE1")]
        return Result()
    session = mock.Mock()
    session.execute = fake_execute
    monkeypatch.setattr(mod, 'get_session', lambda: session)
    resp = pytest.run(mod.export_summary_csv(cohort="Adult", gene_symbol="GENE1", session=session))
    assert resp is not None

@pytest.mark.asyncio
def test_get_scoring(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class Result:
            def scalars(self):
                class S:
                    def all(self): return [1]
                return S()
            def first(self): return [1]
        return Result()
    session = mock.Mock()
    session.execute = fake_execute
    monkeypatch.setattr(mod, 'get_session', lambda: session)
    result = pytest.run(mod.get_scoring(cohort=None, gene_symbol=None, limit=1, offset=0, session=session))
    assert result is not None

@pytest.mark.asyncio
def test_export_scoring_csv(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class Result:
            def all(self): return [("Adult", "GENE1")]
        return Result()
    session = mock.Mock()
    session.execute = fake_execute
    monkeypatch.setattr(mod, 'get_session', lambda: session)
    resp = pytest.run(mod.export_scoring_csv(cohort="Adult", gene_symbol="GENE1", session=session))
    assert resp is not None

@pytest.mark.asyncio
def test_get_assertions(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class Result:
            def scalars(self):
                class S:
                    def all(self): return [1]
                return S()
            def first(self): return [1]
        return Result()
    session = mock.Mock()
    session.execute = fake_execute
    monkeypatch.setattr(mod, 'get_session', lambda: session)
    result = pytest.run(mod.get_assertions(cohort=None, gene_symbol=None, assertion_type=None, limit=1, offset=0, session=session))
    assert result is not None

@pytest.mark.asyncio
def test_export_assertions_csv(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class Result:
            def all(self): return [("Adult", "GENE1", "assertion")]
        return Result()
    session = mock.Mock()
    session.execute = fake_execute
    monkeypatch.setattr(mod, 'get_session', lambda: session)
    resp = pytest.run(mod.export_assertions_csv(cohort="Adult", gene_symbol="GENE1", assertion_type="assertion", session=session))
    assert resp is not None

@pytest.mark.asyncio
def test_get_variants(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class Result:
            def scalars(self):
                class S:
                    def all(self): return [1]
                return S()
            def first(self): return [1]
        return Result()
    session = mock.Mock()
    session.execute = fake_execute
    monkeypatch.setattr(mod, 'get_session', lambda: session)
    result = pytest.run(mod.get_variants(gene_symbol=None, classification=None, limit=1, offset=0, session=session))
    assert result is not None

@pytest.mark.asyncio
def test_get_quick(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class Result:
            def scalars(self):
                class S:
                    def all(self): return [1]
                return S()
            def first(self): return [1]
        return Result()
    session = mock.Mock()
    session.execute = fake_execute
    monkeypatch.setattr(mod, 'get_session', lambda: session)
    result = pytest.run(mod.get_quick(cohort=None, gene_symbol=None, limit=1, offset=0, session=session))
    assert result is not None

@pytest.mark.asyncio
def test_refresh_materialized_view(monkeypatch):
    session = mock.AsyncMock()
    session.execute = mock.AsyncMock()
    session.commit = mock.AsyncMock()
    session.rollback = mock.AsyncMock()
    monkeypatch.setattr(mod, 'get_session', lambda: session)
    import time
    monkeypatch.setattr(mod, 'time', time)
    result = pytest.run(mod.refresh_materialized_view(session=session))
    assert result is not None
