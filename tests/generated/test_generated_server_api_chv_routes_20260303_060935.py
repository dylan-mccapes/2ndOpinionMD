try:
    from server.api import chv_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

@pytest.mark.asyncio
async def test_chv_search_like(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"term": "foo", "cui": "C123", "score": 0.9}]
                        def first(self): return {"term": "foo", "cui": "C123", "score": 0.9}
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(chv_routes, "get_session", lambda: DummySession())
    result = await chv_routes.chv_search(q="foo", limit=1, mode="like", threshold=0.3, session=DummySession())
    assert isinstance(result, list)
    assert result and "term" in result[0]

@pytest.mark.asyncio
async def test_chv_terms_for_cui_valid(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"term": "foo", "cui": "C123"}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(chv_routes, "get_session", lambda: DummySession())
    result = await chv_routes.chv_terms_for_cui(cui="C123", limit=1, session=DummySession())
    assert isinstance(result, list)
    assert result and "term" in result[0]

@pytest.mark.asyncio
async def test_chv_terms_for_cui_invalid(monkeypatch):
    with pytest.raises(chv_routes.HTTPException) as e:
        await chv_routes.chv_terms_for_cui(cui="BAD", limit=1, session=None)
    assert e.value.status_code == 400

@pytest.mark.asyncio
async def test_chv_stats(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def first(self): return {"rows_total": 10, "distinct_cui": 5, "alpha_terms": 8}
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(chv_routes, "get_session", lambda: DummySession())
    result = await chv_routes.chv_stats(session=DummySession())
    assert isinstance(result, dict)
    assert "rows_total" in result

@pytest.mark.asyncio
async def test_chv_map_terms(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"term": "foo", "cui": "C123", "score": 0.9}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(chv_routes, "get_session", lambda: DummySession())
    payload = {"terms": ["foo"], "mode": "fuzzy", "limit_per_term": 1, "threshold": 0.3, "use_best": True, "include_ngrams": True}
    result = await chv_routes.chv_map_terms(payload=payload, session=DummySession())
    assert isinstance(result, list) or isinstance(result, dict)

@pytest.mark.asyncio
async def test_search_ngrams(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"term": "foo", "meta": "bar", "mod": None, "disparaged": False, "misspelled": False, "comment": "baz"}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(chv_routes, "get_session", lambda: DummySession())
    class DummyCHVNgramItem:
        def __init__(self, **kwargs): self.__dict__.update(kwargs)
    class DummyCHVNgramSearchResponse:
        def __init__(self, items, total): self.items = items; self.total = total
    monkeypatch.setattr(chv_routes, "CHVNgramItem", DummyCHVNgramItem)
    monkeypatch.setattr(chv_routes, "CHVNgramSearchResponse", DummyCHVNgramSearchResponse)
    result = await chv_routes.search_ngrams(q="foo", limit=1, include_disparaged=False, include_misspelled=False, session=DummySession())
    assert hasattr(result, "items")
    assert hasattr(result, "total")

@pytest.mark.asyncio
async def test_map_ngrams_to_cui(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"term": "foo", "cuis": ["C123"]}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(chv_routes, "get_session", lambda: DummySession())
    result = await chv_routes.map_ngrams_to_cui(q="foo", limit=1, session=DummySession())
    assert isinstance(result, list)
    assert result and "term" in result[0]

@pytest.mark.asyncio
async def test_suggest_ngrams(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"term": "foo"}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(chv_routes, "get_session", lambda: DummySession())
    result = await chv_routes.suggest_ngrams(q="fo", limit=1, session=DummySession())
    assert isinstance(result, list) or hasattr(result, "__iter__")

@pytest.mark.asyncio
async def test_ngrams_for_cui(monkeypatch):
    class DummySession:
        async def execute(self, *a, **kw):
            class DummyResult:
                def mappings(self):
                    class DummyMap:
                        def all(self): return [{"term": "foo"}]
                    return DummyMap()
            return DummyResult()
    monkeypatch.setattr(chv_routes, "get_session", lambda: DummySession())
    result = await chv_routes.ngrams_for_cui(cui="C123", limit=1, session=DummySession())
    assert isinstance(result, list)
    assert result and result[0] == "foo"

@pytest.mark.asyncio
async def test_ngrams_for_cui_invalid(monkeypatch):
    with pytest.raises(chv_routes.HTTPException) as e:
        await chv_routes.ngrams_for_cui(cui="BAD", limit=1, session=None)
    assert e.value.status_code == 400