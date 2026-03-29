import pytest

try:
    import server.api.eoh_gap_retrieval as eoh_gap_retrieval
except ImportError:
    pytest.skip('server.api.eoh_gap_retrieval could not be imported', allow_module_level=True)

def test_build_compact_context_for_gap_basic():
    docs = [
        {'id': '1', 'source': 'src', 'title': 'Title', 'text': 'Text'*300},
        {'id': '2', 'source': 'src2', 'title': 'Title2', 'text': 'Text2'}
    ]
    result = eoh_gap_retrieval.build_compact_context_for_gap(docs, max_docs=2, max_chars_per_doc=10)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]['id'] == '1'
    assert len(result[0]['snippet']) <= 10

def test_build_compact_context_for_gap_skips_missing_id():
    docs = [{'source': 'src'}]
    result = eoh_gap_retrieval.build_compact_context_for_gap(docs)
    assert result == []

def test_build_eoh_gap_retrieval_payload(monkeypatch):
    def dummy_compact(final_ctx, max_docs=40, max_chars_per_doc=800):
        return [{'id': '1', 'source': 'src', 'title': 'T', 'snippet': 'S'}]
    monkeypatch.setattr(eoh_gap_retrieval, 'build_compact_context_for_gap', dummy_compact)
    final_ctx = [{'id': '1', 'source': 'src'}]
    router_plan = {'plan': True}
    payload = eoh_gap_retrieval.build_eoh_gap_retrieval_payload(
        question='Q', router_plan=router_plan, final_ctx=final_ctx, max_slots=3)
    assert payload['question'] == 'Q'
    assert payload['router_plan'] == router_plan
    assert payload['max_slots'] == 3
    assert isinstance(payload['context'], list)
    assert isinstance(payload['known_sources'], list)
