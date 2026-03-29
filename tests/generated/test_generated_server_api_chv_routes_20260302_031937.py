import pytest
from unittest import mock

pytestmark = pytest.mark.asyncio

try:
    from server.api import chv_routes
except ImportError:
    pytest.skip('server.api.chv_routes not importable', allow_module_level=True)

@pytest.mark.asyncio
async def test_chv_search_like(monkeypatch):
    fake_session = mock.MagicMock()
    monkeypatch.setattr(chv_routes, 'text', lambda sql: sql)
    fake_rows = [
        {'term': 'foo', 'cui': 'C0001'}
    ]
    fake_result = mock.MagicMock()
    fake_result.mappings.return_value.all.return_value = fake_rows
    fake_session.execute.return_value = fake_result
    res = await chv_routes.chv_search('foo', 1, 'like', 0.3, fake_session)
    assert isinstance(res, list)
    assert res[0]['term'] == 'foo'

@pytest.mark.asyncio
async def test_chv_terms_for_cui_invalid(monkeypatch):
    fake_session = mock.MagicMock()
    monkeypatch.setattr(chv_routes, '_CUI_RX', mock.Mock(match=lambda x: False))
    with pytest.raises(chv_routes.HTTPException):
        await chv_routes.chv_terms_for_cui('bad', 1, fake_session)

@pytest.mark.asyncio
async def test_chv_stats_success(monkeypatch):
    fake_session = mock.MagicMock()
    monkeypatch.setattr(chv_routes, 'text', lambda sql: sql)
    fake_row = {'rows_total': 1, 'distinct_cui': 1, 'alpha_terms': 1}
    fake_result = mock.MagicMock()
    fake_result.mappings.return_value.first.return_value = fake_row
    fake_session.execute.return_value = fake_result
    res = await chv_routes.chv_stats(fake_session)
    assert res['rows_total'] == 1

@pytest.mark.asyncio
async def test_chv_map_terms_success(monkeypatch):
    fake_session = mock.MagicMock()
    monkeypatch.setattr(chv_routes, 'text', lambda sql: sql)
    payload = {'terms': ['foo'], 'mode': 'like', 'limit_per_term': 1}
    # Just check it runs (mock internals as needed)
    monkeypatch.setattr(chv_routes, 'map_terms_to_cui', lambda *a, **k: [{'term': 'foo', 'cui': 'C0001'}])
    res = await chv_routes.chv_map_terms(payload, fake_session)
    assert isinstance(res, list)

@pytest.mark.asyncio
async def test_search_ngrams_success(monkeypatch):
    fake_session = mock.MagicMock()
    monkeypatch.setattr(chv_routes, 'text', lambda sql: sql)
    fake_rows = [{'term': 'foo', 'meta': None, 'mod': None, 'disparaged': False, 'misspelled': False, 'comment': None}]
    fake_result = mock.MagicMock()
    fake_result.mappings.return_value.all.return_value = fake_rows
    fake_session.execute.return_value = fake_result
    monkeypatch.setattr(chv_routes, 'CHVNgramItem', lambda **kw: kw)
    monkeypatch.setattr(chv_routes, 'CHVNgramSearchResponse', lambda items, total: {'items': items, 'total': total})
    res = await chv_routes.search_ngrams('foo', 1, False, False, fake_session)
    assert res['total'] == 1

@pytest.mark.asyncio
async def test_map_ngrams_to_cui_success(monkeypatch):
    fake_session = mock.MagicMock()
    monkeypatch.setattr(chv_routes, 'text', lambda sql: sql)
    fake_rows = [{'term': 'foo', 'cuis': ['C0001']}]
    fake_result = mock.MagicMock()
    fake_result.mappings.return_value.all.return_value = fake_rows
    fake_session.execute.return_value = fake_result
    res = await chv_routes.map_ngrams_to_cui('foo', 1, fake_session)
    assert isinstance(res, list)
    assert res[0]['term'] == 'foo'

@pytest.mark.asyncio
async def test_suggest_ngrams_success(monkeypatch):
    fake_session = mock.MagicMock()
    monkeypatch.setattr(chv_routes, 'text', lambda sql: sql)
    fake_rows = [{'term': 'foo'}]
    fake_result = mock.MagicMock()
    fake_result.mappings.return_value.all.return_value = fake_rows
    fake_session.execute.return_value = fake_result
    res = await chv_routes.suggest_ngrams('fo', 1, fake_session)
    assert isinstance(res, list)

@pytest.mark.asyncio
async def test_ngrams_for_cui_invalid(monkeypatch):
    fake_session = mock.MagicMock()
    monkeypatch.setattr(chv_routes, '_CUI_RX', mock.Mock(match=lambda x: False))
    with pytest.raises(chv_routes.HTTPException):
        await chv_routes.ngrams_for_cui('bad', 1, fake_session)
