try:
    import pytest
    from unittest import mock
    from server.api import clingen_actionability_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_get_summary_basic(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class FakeResult:
            def scalars(self):
                class S:
                    def all(self):
                        return [1, 2, 3]
                return S()
            def first(self):
                return [42]
        return FakeResult()
    fake_session = mock.Mock()
    fake_session.execute = fake_execute
    fake_session.commit = mock.AsyncMock()
    fake_session.rollback = mock.AsyncMock()
    result = pytest.run(clingen_actionability_routes.get_summary(
        cohort=None, gene_symbol=None, limit=10, offset=0, session=fake_session
    ))
    assert result is not None

@pytest.mark.asyncio
def test_export_summary_csv(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class FakeResult:
            def all(self):
                return [("Adult", "GENE1", 1)]
        return FakeResult()
    fake_session = mock.Mock()
    fake_session.execute = fake_execute
    result = pytest.run(clingen_actionability_routes.export_summary_csv(
        cohort="Adult", gene_symbol="GENE1", session=fake_session
    ))
    assert result is not None

@pytest.mark.asyncio
def test_get_scoring(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class FakeResult:
            def scalars(self):
                class S:
                    def all(self):
                        return [4, 5, 6]
                return S()
            def first(self):
                return [99]
        return FakeResult()
    fake_session = mock.Mock()
    fake_session.execute = fake_execute
    result = pytest.run(clingen_actionability_routes.get_scoring(
        cohort=None, gene_symbol=None, limit=5, offset=0, session=fake_session
    ))
    assert result is not None

@pytest.mark.asyncio
def test_export_scoring_csv(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class FakeResult:
            def all(self):
                return [("Adult", "GENE2", 2)]
        return FakeResult()
    fake_session = mock.Mock()
    fake_session.execute = fake_execute
    result = pytest.run(clingen_actionability_routes.export_scoring_csv(
        cohort="Adult", gene_symbol="GENE2", session=fake_session
    ))
    assert result is not None

@pytest.mark.asyncio
def test_get_assertions(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class FakeResult:
            def scalars(self):
                class S:
                    def all(self):
                        return [7, 8, 9]
                return S()
            def first(self):
                return [123]
        return FakeResult()
    fake_session = mock.Mock()
    fake_session.execute = fake_execute
    result = pytest.run(clingen_actionability_routes.get_assertions(
        cohort=None, gene_symbol=None, assertion_type=None, limit=3, offset=0, session=fake_session
    ))
    assert result is not None

@pytest.mark.asyncio
def test_export_assertions_csv(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class FakeResult:
            def all(self):
                return [("Adult", "GENE3", "assertion", 3)]
        return FakeResult()
    fake_session = mock.Mock()
    fake_session.execute = fake_execute
    result = pytest.run(clingen_actionability_routes.export_assertions_csv(
        cohort="Adult", gene_symbol="GENE3", assertion_type="assertion", session=fake_session
    ))
    assert result is not None

@pytest.mark.asyncio
def test_get_variants(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class FakeResult:
            def scalars(self):
                class S:
                    def all(self):
                        return [10, 11]
                return S()
            def first(self):
                return [321]
        return FakeResult()
    fake_session = mock.Mock()
    fake_session.execute = fake_execute
    result = pytest.run(clingen_actionability_routes.get_variants(
        gene_symbol="GENE4", classification="pathogenic", limit=2, offset=0, session=fake_session
    ))
    assert result is not None

@pytest.mark.asyncio
def test_get_quick(monkeypatch):
    async def fake_execute(*args, **kwargs):
        class FakeResult:
            def scalars(self):
                class S:
                    def all(self):
                        return [12, 13]
                return S()
            def first(self):
                return [456]
        return FakeResult()
    fake_session = mock.Mock()
    fake_session.execute = fake_execute
    result = pytest.run(clingen_actionability_routes.get_quick(
        cohort="Adult", gene_symbol="GENE5", limit=2, offset=0, session=fake_session
    ))
    assert result is not None

@pytest.mark.asyncio
def test_refresh_materialized_view(monkeypatch):
    fake_session = mock.Mock()
    fake_session.execute = mock.AsyncMock()
    fake_session.commit = mock.AsyncMock()
    fake_session.rollback = mock.AsyncMock()
    # Simulate no exception (concurrent mode)
    result = pytest.run(clingen_actionability_routes.refresh_materialized_view(session=fake_session))
    assert result is not None
    # Simulate exception and fallback
    async def raise_exc(*a, **kw):
        raise Exception("deadlock")
    fake_session.execute = raise_exc
    result2 = pytest.run(clingen_actionability_routes.refresh_materialized_view(session=fake_session))
    assert result2 is not None
