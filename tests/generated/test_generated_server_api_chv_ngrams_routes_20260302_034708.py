try:
    import pytest
    from unittest import mock
    from server.api import chv_ngrams_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
async def test_ngram_search(monkeypatch):
    class FakeConn:
        async def fetch(self, sql, q, limit):
            return [{'term': 'foo', 'meta': None, 'mod': None, 'disparaged': False, 'misspelled': False, 'comment': ''}]
    class FakePool:
        async def acquire(self):
            class Ctx:
                async def __aenter__(self): return FakeConn()
                async def __aexit__(self, exc_type, exc, tb): pass
            return Ctx()
    monkeypatch.setattr(chv_ngrams_routes, 'get_pool', lambda: FakePool())
    monkeypatch.setattr(chv_ngrams_routes, 'NgramItem', lambda **kwargs: kwargs)
    result = await chv_ngrams_routes.ngram_search('foo', 1)
    assert isinstance(result, list)
    assert result[0]['term'] == 'foo'
