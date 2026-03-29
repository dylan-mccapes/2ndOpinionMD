# AUTO-GENERATED TESTS for server/api/chv_ngrams_routes.py
import pytest
from unittest import mock

try:
    from server.api import chv_ngrams_routes
except ImportError:
    pytest.skip('server.api.chv_ngrams_routes not importable', allow_module_level=True)

@pytest.mark.asyncio
async def test_ngram_search_returns_items(monkeypatch):
    # Patch get_pool and conn.fetch
    pool = mock.AsyncMock()
    conn = mock.AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    monkeypatch.setattr(chv_ngrams_routes, 'get_pool', mock.AsyncMock(return_value=pool))
    conn.fetch.return_value = [
        {'term': 'foo', 'meta': None, 'mod': None, 'disparaged': False, 'misspelled': False, 'comment': None}
    ]
    monkeypatch.setattr(chv_ngrams_routes, 'NgramItem', lambda **kwargs: type('NgramItem', (), kwargs))
    items = await chv_ngrams_routes.ngram_search('foo', 1)
    assert len(items) == 1
    assert hasattr(items[0], 'term')
