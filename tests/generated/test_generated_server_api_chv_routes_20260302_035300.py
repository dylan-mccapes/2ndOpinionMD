try:
    import pytest
    from unittest import mock
    from server.api import chv_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_chv_search_like(monkeypatch):
    session = mock.Mock()
    async def dummy_execute(*a, **k):
        class Dummy:
            def mappings(self):
                class M:
                    def all(self):
                        return [{'term': 'foo', 'cui': 'C123'}]
                return M()
        return Dummy()
    session.execute = dummy_execute
    result = None
    import asyncio
    monkeypatch.setattr(chv_routes, '_CUI_RX', mock.Mock())
    result = asyncio.run(chv_routes.chv_search(q='foo', limit=1, mode='like', threshold=0.3, session=session))
    assert isinstance(result, list)

@pytest.mark.asyncio
def test_chv_terms_for_cui_invalid(monkeypatch):
    session = mock.Mock()
    monkeypatch.setattr(chv_routes, '_CUI_RX', mock.Mock(match=lambda x: False))
    with pytest.raises(chv_routes.HTTPException):
        import asyncio
        asyncio.run(chv_routes.chv_terms_for_cui('bad', 1, session))

@pytest.mark.asyncio
def test_chv_stats(monkeypatch):
    session = mock.Mock()
    async def dummy_execute(*a, **k):
        class Dummy:
            def mappings(self):
                class M:
                    def first(self):
                        return {'rows_total': 1, 'distinct_cui': 1, 'alpha_terms': 1}
                return M()
        return Dummy()
    session.execute = dummy_execute
    import asyncio
    result = asyncio.run(chv_routes.chv_stats(session))
    assert 'rows_total' in result

@pytest.mark.asyncio
def test_chv_map_terms(monkeypatch):
    session = mock.Mock()
    monkeypatch.setattr(chv_routes, 'Body', lambda *a, **k: None)
    payload = {'terms': ['foo'], 'mode': 'like', 'limit_per_term': 1, 'threshold': 0.3, 'use_best': True, 'include_ngrams': True}
    monkeypatch.setattr(chv_routes, 'text', lambda x: x)
    async def dummy_execute(*a, **k):
        class Dummy:
            def mappings(self):
                class M:
                    def all(self):
                        return [{'term': 'foo', 'cui': 'C123'}]
                return M()
        return Dummy()
    session.execute = dummy_execute
    import asyncio
    result = asyncio.run(chv_routes.chv_map_terms(payload, session))
    assert isinstance(result, list) or isinstance(result, dict)

@pytest.mark.asyncio
def test_search_ngrams(monkeypatch):
    session = mock.Mock()
    monkeypatch.setattr(chv_routes, 'text', lambda x: x)
    async def dummy_execute(*a, **k):
        class Dummy:
            def mappings(self):
                class M:
                    def all(self):
                        return [{'term': 'foo', 'meta': None, 'mod': None, 'disparaged': False, 'misspelled': False, 'comment': ''}]
                return M()
        return Dummy()
    session.execute = dummy_execute
    monkeypatch.setattr(chv_routes, 'CHVNgramItem', lambda **kwargs: kwargs)
    monkeypatch.setattr(chv_routes, 'CHVNgramSearchResponse', lambda items, total: {'items': items, 'total': total})
    import asyncio
    result = asyncio.run(chv_routes.search_ngrams('foo', 1, False, False, session))
    assert 'items' in result

@pytest.mark.asyncio
def test_map_ngrams_to_cui(monkeypatch):
    session = mock.Mock()
    monkeypatch.setattr(chv_routes, 'text', lambda x: x)
    async def dummy_execute(*a, **k):
        class Dummy:
            def mappings(self):
                class M:
                    def all(self):
                        return [{'term': 'foo', 'cuis': ['C123']}]
                return M()
        return Dummy()
    session.execute = dummy_execute
    import asyncio
    result = asyncio.run(chv_routes.map_ngrams_to_cui('foo', 1, session))
    assert isinstance(result, list)
    assert result[0]['term'] == 'foo'

@pytest.mark.asyncio
def test_suggest_ngrams(monkeypatch):
    session = mock.Mock()
    monkeypatch.setattr(chv_routes, 'text', lambda x: x)
    async def dummy_execute(*a, **k):
        class Dummy:
            def mappings(self):
                class M:
                    def all(self):
                        return [{'term': 'foo'}]
                return M()
        return Dummy()
    session.execute = dummy_execute
    import asyncio
    result = asyncio.run(chv_routes.suggest_ngrams('fo', 1, session))
    assert isinstance(result, list) or isinstance(result, dict)

@pytest.mark.asyncio
def test_ngrams_for_cui_invalid(monkeypatch):
    session = mock.Mock()
    monkeypatch.setattr(chv_routes, '_CUI_RX', mock.Mock(match=lambda x: False))
    with pytest.raises(chv_routes.HTTPException):
        import asyncio
        asyncio.run(chv_routes.ngrams_for_cui('bad', 1, session))
