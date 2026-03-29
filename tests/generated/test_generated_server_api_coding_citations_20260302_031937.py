import pytest
from unittest import mock

try:
    from server.api import coding_citations
except ImportError:
    pytest.skip('server.api.coding_citations not importable', allow_module_level=True)

import pytest_asyncio

@pytest.mark.asyncio
async def test_enrich_coding_response(monkeypatch):
    resp = {
        'medications': [{'name': 'Aspirin'}],
        'labs': [{'name': 'Glucose'}],
        'probable_dx': [
            {'system': 'ICD-10-CM', 'code': 'E11', 'why': 'Diabetes'}
        ]
    }
    monkeypatch.setattr(coding_citations, '_names_list', lambda x: ['Aspirin'])
    monkeypatch.setattr(coding_citations, '_lab_hints', lambda x: ['Glucose'])
    class DummyConn:
        pass
    async def fake_get_conn():
        return DummyConn()
    monkeypatch.setattr(coding_citations, '_get_conn', fake_get_conn)
    async def fake_build_min_citation_bundle(conn, claim, code):
        return {'bundle': 'ok'}
    monkeypatch.setattr(coding_citations, 'build_min_citation_bundle', fake_build_min_citation_bundle)
    await coding_citations.enrich_coding_response(resp)
    assert 'probable_dx' in resp
    assert isinstance(resp['probable_dx'], list)
