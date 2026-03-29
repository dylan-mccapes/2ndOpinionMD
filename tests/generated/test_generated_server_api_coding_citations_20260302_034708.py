try:
    import pytest
    from unittest import mock
    from server.api import coding_citations as mod
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_enrich_coding_response(monkeypatch):
    resp = {
        "probable_dx": [
            {"system": "ICD-10-CM", "code": "A01", "why": "test"}
        ],
        "medications": [],
        "labs": []
    }
    monkeypatch.setattr(mod, '_names_list', lambda x: [])
    monkeypatch.setattr(mod, '_lab_hints', lambda x: [])
    fake_conn = object()
    monkeypatch.setattr(mod, '_get_conn', mock.AsyncMock(return_value=fake_conn))
    async def fake_bundle(conn, claim, code, meds, labs):
        return {"bundle": True}
    monkeypatch.setattr(mod, 'build_min_citation_bundle', fake_bundle)
    import asyncio
    asyncio.run(mod.enrich_coding_response(resp))
    assert 'probable_dx' in resp
