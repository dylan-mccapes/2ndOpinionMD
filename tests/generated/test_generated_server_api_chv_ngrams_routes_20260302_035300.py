try:
    import pytest
    from unittest import mock
    from server.api import chv_ngrams_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_ngram_search(monkeypatch):
    async def dummy_get_pool():
        class DummyConn:
            async def fetch(self, sql, q, limit):
                return [{'term': 'foo', 'meta': None, 'mod': None, 'disparaged': False, 'misspelled': False, 'comment': ''}]
            async def __aenter__(self): return self
            async def __aexit__(self, exc_type, exc, tb): pass
        class DummyPool:
            async def acquire(self):
                return DummyConn()
        return DummyPool()
    monkeypatch.setattr(chv_ngrams_routes, 'get_pool', dummy_get_pool)
    monkeypatch.setattr(chv_ngrams_routes, 'NgramItem', lambda **kwargs: kwargs)
    import asyncio
    result = asyncio.run(chv_ngrams_routes.ngram_search('foo', 1))
    assert isinstance(result, list)
    assert result[0]['term'] == 'foo'
