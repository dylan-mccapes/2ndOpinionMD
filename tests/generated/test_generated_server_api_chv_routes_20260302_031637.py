# AUTO-GENERATED TESTS for server/api/chv_routes.py
import pytest
from unittest import mock

try:
    from server.api import chv_routes
except ImportError:
    pytest.skip('server.api.chv_routes not importable', allow_module_level=True)

@pytest.mark.asyncio
async def test_chv_search_like(monkeypatch):
    session = mock.AsyncMock()
    # Patch session.execute
    session.execute.return_value.mappings.return_value.all.return_value = [
        {'term': 'foo', 'cui': 'C123'}
    ]
    result = await chv_routes.chv_search(q='foo', limit=1, mode='like', threshold=0.3, session=session)
    assert isinstance(result, list)
    assert result[0]['term'] == 'foo'

@pytest.mark.asyncio
async def test_chv_terms_for_cui_invalid(monkeypatch):
    session = mock.AsyncMock()
    with pytest.raises(chv_routes.HTTPException) as e:
        await chv_routes.chv_terms_for_cui('BAD', 1, session)
    assert e.value.status_code == 400
    assert 'Invalid CUI format' in str(e.value.detail)

@pytest.mark.asyncio
async def test_chv_stats_success(monkeypatch):
    session = mock.AsyncMock()
    row = {'rows_total': 10, 'distinct_cui': 5, 'alpha_terms': 8}
    session.execute.return_value.mappings.return_value.first.return_value = row
    result = await chv_routes.chv_stats(session)
    assert result['rows_total'] == 10
    assert result['distinct_cui'] == 5
    assert result['alpha_terms'] == 8

@pytest.mark.asyncio
async def test_chv_map_terms_basic(monkeypatch):
    session = mock.AsyncMock()
    payload = {'terms': ['foo'], 'mode': 'like', 'limit_per_term': 1, 'threshold': 0.3, 'use_best': True, 'include_ngrams': True}
    # Patch session.execute
    session.execute.return_value.mappings.return_value.all.return_value = [
        {'term': 'foo', 'cui': 'C123'}
    ]
    result = await chv_routes.chv_map_terms(payload, session)
    assert isinstance(result, list) or isinstance(result, dict)

@pytest.mark.asyncio
async def test_search_ngrams(monkeypatch):
    session = mock.AsyncMock()
    session.execute.return_value.mappings.return_value.all.return_value = [
        {'term': 'foo', 'meta': None, 'mod': None, 'disparaged': False, 'misspelled': False, 'comment': None}
    ]
    monkeypatch.setattr(chv_routes, 'CHVNgramItem', lambda **kwargs: type('CHVNgramItem', (), kwargs))
    monkeypatch.setattr(chv_routes, 'CHVNgramSearchResponse', lambda items, total: type('Resp', (), {'items': items, 'total': total}))
    resp = await chv_routes.search_ngrams('foo', 1, False, False, session)
    assert hasattr(resp, 'items')
    assert resp.total == 1

@pytest.mark.asyncio
async def test_map_ngrams_to_cui(monkeypatch):
    session = mock.AsyncMock()
    session.execute.return_value.mappings.return_value.all.return_value = [
        {'term': 'foo', 'cuis': ['C123']}
    ]
    result = await chv_routes.map_ngrams_to_cui('foo', 1, session)
    assert isinstance(result, list)
    assert result[0]['term'] == 'foo'

@pytest.mark.asyncio
async def test_suggest_ngrams(monkeypatch):
    session = mock.AsyncMock()
    session.execute.return_value.mappings.return_value.all.return_value = [
        {'term': 'foo'}
    ]
    monkeypatch.setattr(chv_routes, 'CHVNgramSuggestResponse', lambda items, total: type('Resp', (), {'items': items, 'total': total}))
    resp = await chv_routes.suggest_ngrams('fo', 1, session)
    assert hasattr(resp, 'items')

@pytest.mark.asyncio
async def test_ngrams_for_cui_invalid(monkeypatch):
    session = mock.AsyncMock()
    with pytest.raises(chv_routes.HTTPException) as e:
        await chv_routes.ngrams_for_cui('BAD', 1, session)
    assert e.value.status_code == 400
    assert 'Invalid CUI' in str(e.value.detail)
