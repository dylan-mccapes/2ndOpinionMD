try:
    import pytest
    from unittest import mock
    from server.api import chv_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

import sys

@pytest.mark.asyncio
async def test_chv_search_like(monkeypatch):
    if not hasattr(pytest, 'mark') or not hasattr(pytest.mark, 'asyncio'):
        pytest.skip("pytest-asyncio not available")
    mock_session = mock.AsyncMock()
    monkeypatch.setattr(chv_routes, 'get_session', lambda: mock_session)
    # Patch session.execute to return a mock result
    class MockResult:
        def mappings(self):
            class All:
                def all(self):
                    return [{"term": "pain", "cui": "C0000001"}]
            return All()
    mock_session.execute.return_value = MockResult()
    result = await chv_routes.chv_search(q="pain", limit=1, mode="like", threshold=0.3, session=mock_session)
    assert isinstance(result, list)
    assert result[0]["term"] == "pain"

@pytest.mark.asyncio
async def test_chv_terms_for_cui_valid(monkeypatch):
    mock_session = mock.AsyncMock()
    monkeypatch.setattr(chv_routes, 'get_session', lambda: mock_session)
    class MockResult:
        def mappings(self):
            class All:
                def all(self):
                    return [{"term": "pain", "cui": "C0000001"}]
            return All()
    mock_session.execute.return_value = MockResult()
    result = await chv_routes.chv_terms_for_cui(cui="C0000001", limit=1, session=mock_session)
    assert isinstance(result, list)
    assert result[0]["cui"] == "C0000001"

@pytest.mark.asyncio
async def test_chv_terms_for_cui_invalid():
    with pytest.raises(chv_routes.HTTPException) as exc:
        await chv_routes.chv_terms_for_cui(cui="INVALID", limit=1, session=mock.AsyncMock())
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_chv_stats(monkeypatch):
    mock_session = mock.AsyncMock()
    class MockResult:
        def mappings(self):
            class First:
                def first(self):
                    return {"rows_total": 100, "distinct_cui": 10, "alpha_terms": 80}
            return First()
    mock_session.execute.return_value = MockResult()
    result = await chv_routes.chv_stats(session=mock_session)
    assert result["rows_total"] == 100
    assert result["distinct_cui"] == 10
    assert result["alpha_terms"] == 80

@pytest.mark.asyncio
async def test_chv_map_terms(monkeypatch):
    mock_session = mock.AsyncMock()
    payload = {
        "terms": ["pain"],
        "mode": "like",
        "limit_per_term": 1,
        "threshold": 0.3,
        "use_best": True,
        "include_ngrams": True
    }
    # Patch session.execute to return a mock result
    class MockResult:
        def mappings(self):
            class All:
                def all(self):
                    return [{"term": "pain", "cui": "C0000001"}]
            return All()
    mock_session.execute.return_value = MockResult()
    monkeypatch.setattr(chv_routes, 'get_session', lambda: mock_session)
    # Patch any other required dependencies if needed
    # Here we just check that it runs and returns a list or dict
    result = await chv_routes.chv_map_terms(payload=payload, session=mock_session)
    assert isinstance(result, (list, dict))

@pytest.mark.asyncio
async def test_search_ngrams(monkeypatch):
    mock_session = mock.AsyncMock()
    class MockResult:
        def mappings(self):
            class All:
                def all(self):
                    return [{"term": "pain", "meta": None, "mod": None, "disparaged": False, "misspelled": False, "comment": None}]
            return All()
    mock_session.execute.return_value = MockResult()
    monkeypatch.setattr(chv_routes, 'CHVNgramItem', lambda **kwargs: mock.Mock(**kwargs))
    monkeypatch.setattr(chv_routes, 'CHVNgramSearchResponse', lambda items, total: mock.Mock(items=items, total=total))
    result = await chv_routes.search_ngrams(q="pain", limit=1, include_disparaged=False, include_misspelled=False, session=mock_session)
    assert hasattr(result, 'items')
    assert hasattr(result, 'total')

@pytest.mark.asyncio
async def test_map_ngrams_to_cui(monkeypatch):
    mock_session = mock.AsyncMock()
    class MockResult:
        def mappings(self):
            class All:
                def all(self):
                    return [{"term": "pain", "cuis": ["C0000001"]}]
            return All()
    mock_session.execute.return_value = MockResult()
    result = await chv_routes.map_ngrams_to_cui(q="pain", limit=1, session=mock_session)
    assert isinstance(result, list)
    assert result[0]["term"] == "pain"
    assert result[0]["cuis"] == ["C0000001"]

@pytest.mark.asyncio
async def test_suggest_ngrams(monkeypatch):
    mock_session = mock.AsyncMock()
    class MockResult:
        def mappings(self):
            class All:
                def all(self):
                    return [{"term": "pain"}]
            return All()
    mock_session.execute.return_value = MockResult()
    monkeypatch.setattr(chv_routes, 'CHVNgramSuggestResponse', lambda items, total: mock.Mock(items=items, total=total))
    result = await chv_routes.suggest_ngrams(q="pa", limit=1, session=mock_session)
    assert hasattr(result, 'items')
    assert hasattr(result, 'total')

@pytest.mark.asyncio
async def test_ngrams_for_cui(monkeypatch):
    mock_session = mock.AsyncMock()
    class MockResult:
        def mappings(self):
            class All:
                def all(self):
                    return [{"term": "pain"}]
            return All()
    mock_session.execute.return_value = MockResult()
    result = await chv_routes.ngrams_for_cui(cui="C0000001", limit=1, session=mock_session)
    assert isinstance(result, list)
    assert result[0] == "pain"

@pytest.mark.asyncio
async def test_ngrams_for_cui_invalid():
    with pytest.raises(chv_routes.HTTPException) as exc:
        await chv_routes.ngrams_for_cui(cui="INVALID", limit=1, session=mock.AsyncMock())
    assert exc.value.status_code == 400
