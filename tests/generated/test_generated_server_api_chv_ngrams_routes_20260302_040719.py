try:
    import pytest
    from unittest import mock
    from server.api import chv_ngrams_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_ngram_search_basic(monkeypatch):
    dummy_rows = [
        {'term': 'heart attack', 'meta': {}, 'mod': None, 'disparaged': False, 'misspelled': False, 'comment': ''}
    ]
    class DummyConn:
        async def fetch(self, sql, q, limit):
            return dummy_rows
    class DummyPool:
        async def acquire(self):
            return DummyConn()
    monkeypatch.setattr(chv_ngrams_routes, 'get_pool', mock.AsyncMock(return_value=DummyPool()))
    monkeypatch.setattr(chv_ngrams_routes, 'NgramItem', lambda **kwargs: kwargs)
    result = None
    async def run():
        nonlocal result
        result = await chv_ngrams_routes.ngram_search('heart', 1)
    import asyncio
    asyncio.run(run())
    assert isinstance(result, list)
    assert result[0]['term'] == 'heart attack'
