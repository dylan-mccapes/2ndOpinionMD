try:
    from server.api import coding_citations
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

@pytest.mark.asyncio
async def test_enrich_coding_response_basic(monkeypatch):
    # Patch _get_conn and build_min_citation_bundle to avoid DB/network
    monkeypatch.setattr(coding_citations, '_get_conn', mock.AsyncMock(return_value='fake_conn'))
    monkeypatch.setattr(coding_citations, 'build_min_citation_bundle', mock.AsyncMock(return_value={'bundle': 1}))
    # Patch _names_list and _lab_hints to no-op
    monkeypatch.setattr(coding_citations, '_names_list', lambda meds: [])
    monkeypatch.setattr(coding_citations, '_lab_hints', lambda labs: [])
    # Input with one ICD-10-CM probable_dx
    resp = {
        'probable_dx': [
            {'system': 'ICD-10-CM', 'code': 'A00', 'why': 'test'}
        ],
        'medications': [],
        'labs': []
    }
    await coding_citations.enrich_coding_response(resp)
    # Should have attached 'justification_bundle' to the ICD-10-CM dx
    assert 'justification_bundle' in resp['probable_dx'][0]
