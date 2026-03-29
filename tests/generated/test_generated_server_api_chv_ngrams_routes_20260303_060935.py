try:
    from server.api import chv_ngrams_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

@pytest.mark.asyncio
async def test_ngram_search_basic(monkeypatch):
    # Patch get_pool and NgramItem
    async def fake_get_pool():
        class FakeConn:
            async def fetch(self, sql, q, limit):
                return [
                    {"term": "foo", "meta": "bar", "mod": None, "disparaged": False, "misspelled": False, "comment": "baz"}
                ]
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc, tb): pass
        class FakePool:
            async def acquire(self): return FakeConn()
        return FakePool()
    monkeypatch.setattr(chv_ngrams_routes, "get_pool", fake_get_pool)
    class DummyNgramItem:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)
    monkeypatch.setattr(chv_ngrams_routes, "NgramItem", DummyNgramItem)
    result = await chv_ngrams_routes.ngram_search("foo", limit=1)
    assert isinstance(result, list)
    assert result and hasattr(result[0], "term")