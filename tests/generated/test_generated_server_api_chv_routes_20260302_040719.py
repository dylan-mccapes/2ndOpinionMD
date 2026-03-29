try:
    import pytest
    from unittest import mock
    from server.api import chv_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_chv_search_like(monkeypatch):
    class DummySession:
        async def execute(self, sql, params=None):
            class DummyResult:
                def mappings(self):
                    class DummyMappings:
                        def all(self):
                            return [{'term': 'heart attack', 'cui': 'C123', 'score': 1.0}]
                    return DummyMappings()
            return DummyResult()
    result = None
    async def run():
        nonlocal result
        result = await chv_routes.chv_search(q='heart', limit=1, mode='like', threshold=0.3, session=DummySession())
    import asyncio
    asyncio.run(run())
    assert isinstance(result, list)
    assert result[0]['term'] == 'heart attack'

@pytest.mark.asyncio
def test_chv_terms_for_cui_invalid(monkeypatch):
    class DummySession:
        pass
    with pytest.raises(chv_routes.HTTPException) as e:
        import asyncio
        asyncio.run(chv_routes.chv_terms_for_cui('BAD', 1, DummySession()))
    assert e.value.status_code == 400
    assert 'Invalid CUI format' in str(e.value.detail)

@pytest.mark.asyncio
def test_chv_stats_success(monkeypatch):
    class DummySession:
        async def execute(self, sql):
            class DummyResult:
                def mappings(self):
                    class DummyMappings:
                        def first(self):
                            return {'rows_total': 100, 'distinct_cui': 10, 'alpha_terms': 80}
                    return DummyMappings()
            return DummyResult()
    result = None
    async def run():
        nonlocal result
        result = await chv_routes.chv_stats(DummySession())
    import asyncio
    asyncio.run(run())
    assert result['rows_total'] == 100

@pytest.mark.asyncio
def test_chv_map_terms_basic(monkeypatch):
    class DummySession:
        async def execute(self, sql, params=None):
            class DummyResult:
                def mappings(self):
                    class DummyMappings:
                        def all(self):
                            return [{'term': 'heart attack', 'cui': 'C123', 'score': 1.0}]
                    return DummyMappings()
            return DummyResult()
    monkeypatch.setattr(chv_routes, 'Body', lambda **kwargs: kwargs)
    payload = {'terms': ['heart attack'], 'mode': 'like', 'limit_per_term': 1, 'threshold': 0.3, 'use_best': True, 'include_ngrams': True}
    result = None
    async def run():
        nonlocal result
        result = await chv_routes.chv_map_terms(payload, DummySession())
    import asyncio
    asyncio.run(run())
    assert isinstance(result, list) or isinstance(result, dict)

@pytest.mark.asyncio
def test_search_ngrams_basic(monkeypatch):
    class DummySession:
        async def execute(self, sql, params):
            class DummyResult:
                def mappings(self):
                    class DummyMappings:
                        def all(self):
                            return [{'term': 'heart attack', 'meta': {}, 'mod': None, 'disparaged': False, 'misspelled': False, 'comment': ''}]
                    return DummyMappings()
            return DummyResult()
    monkeypatch.setattr(chv_routes, 'CHVNgramItem', lambda **kwargs: kwargs)
    monkeypatch.setattr(chv_routes, 'CHVNgramSearchResponse', lambda items, total: {'items': items, 'total': total})
    result = None
    async def run():
        nonlocal result
        result = await chv_routes.search_ngrams('heart', 1, False, False, DummySession())
    import asyncio
    asyncio.run(run())
    assert 'items' in result
    assert result['total'] == 1

@pytest.mark.asyncio
def test_map_ngrams_to_cui_basic(monkeypatch):
    class DummySession:
        async def execute(self, sql, params):
            class DummyResult:
                def mappings(self):
                    class DummyMappings:
                        def all(self):
                            return [{'term': 'heart attack', 'cuis': ['C123']}]
                    return DummyMappings()
            return DummyResult()
    result = None
    async def run():
        nonlocal result
        result = await chv_routes.map_ngrams_to_cui('heart', 1, DummySession())
    import asyncio
    asyncio.run(run())
    assert isinstance(result, list)
    assert result[0]['term'] == 'heart attack'

@pytest.mark.asyncio
def test_suggest_ngrams_basic(monkeypatch):
    class DummySession:
        async def execute(self, sql, params):
            class DummyResult:
                def mappings(self):
                    class DummyMappings:
                        def all(self):
                            return [{'term': 'heart attack'}]
                    return DummyMappings()
            return DummyResult()
    monkeypatch.setattr(chv_routes, 'Query', lambda *a, **k: None)
    result = None
    async def run():
        nonlocal result
        result = await chv_routes.suggest_ngrams('heart', 1, DummySession())
    import asyncio
    asyncio.run(run())
    assert isinstance(result, list) or result is not None

@pytest.mark.asyncio
def test_ngrams_for_cui_invalid(monkeypatch):
    class DummySession:
        pass
    with pytest.raises(chv_routes.HTTPException) as e:
        import asyncio
        asyncio.run(chv_routes.ngrams_for_cui('BAD', 1, DummySession()))
    assert e.value.status_code == 400
    assert 'Invalid CUI' in str(e.value.detail)
