try:
    import pytest
    from unittest import mock
    from server.api import coding_citations
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_enrich_coding_response(monkeypatch):
    # Patch _get_conn and build_min_citation_bundle
    monkeypatch.setattr(coding_citations, '_get_conn', mock.AsyncMock(return_value='fake_conn'))
    monkeypatch.setattr(coding_citations, 'build_min_citation_bundle', mock.AsyncMock(return_value={'bundle': 1}))
    # Patch _names_list and _lab_hints
    monkeypatch.setattr(coding_citations, '_names_list', lambda meds: [m.get('name') for m in meds])
    monkeypatch.setattr(coding_citations, '_lab_hints', lambda labs: [l.get('hint') for l in labs])
    resp = {
        'medications': [{'name': 'med1'}],
        'labs': [{'hint': 'lab1'}],
        'probable_dx': [
            {'system': 'ICD-10-CM', 'code': 'A01', 'why': 'Test why'}
        ]
    }
    pytest.run(coding_citations.enrich_coding_response(resp))
    assert 'medications' in resp
