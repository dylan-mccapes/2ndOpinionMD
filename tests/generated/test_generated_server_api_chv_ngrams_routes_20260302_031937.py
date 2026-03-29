import pytest
from unittest import mock

pytestmark = pytest.mark.asyncio

try:
    from server.api import chv_ngrams_routes
except ImportError:
    pytest.skip('server.api.chv_ngrams_routes not importable', allow_module_level=True)

@pytest.mark.asyncio
async def test_ngram_search_success(monkeypatch):
    fake_pool = mock.MagicMock()
    fake_conn = mock.MagicMock()
    fake_rows = [
        {'term': 'foo', 'meta': None, 'mod': None, 'disparaged': False, 'misspelled': False, 'comment': None}
    ]
    async def fake_fetch(sql, q, limit):
        return fake_rows
    fake_conn.fetch = fake_fetch
    class FakeAcquire:
        async def __aenter__(self): return fake_conn
        async def __aexit__(self, exc_type, exc, tb): pass
    fake_pool.acquire.return_value = FakeAcquire()
    monkeypatch.setattr(chv_ngrams_routes, 'get_pool', mock.AsyncMock(return_value=fake_pool))
    monkeypatch.setattr(chv_ngrams_routes, 'NgramItem', lambda **kw: kw)
    res = await chv_ngrams_routes.ngram_search('foo', 1)
    assert isinstance(res, list)
    assert res[0]['term'] == 'foo'
