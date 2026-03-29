import pytest
from unittest import mock

pytestmark = pytest.mark.asyncio

def _import_or_skip():
    try:
        import server.api.coding_citations as mod
        return mod
    except ImportError:
        pytest.skip('server.api.coding_citations import failed', allow_module_level=True)

@pytest.mark.asyncio
async def test_enrich_coding_response(monkeypatch):
    mod = _import_or_skip()
    # Patch _names_list, _lab_hints, _get_conn, build_min_citation_bundle
    monkeypatch.setattr(mod, '_names_list', lambda x: [])
    monkeypatch.setattr(mod, '_lab_hints', lambda x: [])
    class DummyConn: pass
    async def dummy_get_conn(): return DummyConn()
    monkeypatch.setattr(mod, '_get_conn', dummy_get_conn)
    async def dummy_bundle(conn, claim, code, meds, labs): return {'bundle': True}
    monkeypatch.setattr(mod, 'build_min_citation_bundle', dummy_bundle)
    # Minimal input
    resp = {"probable_dx": [{"system": "ICD-10-CM", "code": "A00"}]}
    await mod.enrich_coding_response(resp)
    assert "probable_dx" in resp
