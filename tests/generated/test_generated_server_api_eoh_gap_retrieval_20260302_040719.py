import pytest
try:
    from server.api import eoh_gap_retrieval
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

def test_build_compact_context_for_gap_basic():
    ctx = [
        {"id": "1", "source": "src", "title": "t", "text": "abc"},
        {"id": "2", "source": "src2", "title": "t2", "text": "def"},
        {"id": "", "source": "src3", "title": "t3", "text": "ghi"},  # should be skipped
    ]
    result = eoh_gap_retrieval.build_compact_context_for_gap(ctx, max_docs=2, max_chars_per_doc=2)
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["id"] == "1"
    assert result[0]["snippet"] == "ab"

def test_build_eoh_gap_retrieval_payload(monkeypatch):
    # Patch build_compact_context_for_gap to control output
    monkeypatch.setattr(eoh_gap_retrieval, 'build_compact_context_for_gap', lambda ctx: [{"id": "1"}])
    final_ctx = [{"source": "A"}, {"source": "B"}]
    payload = eoh_gap_retrieval.build_eoh_gap_retrieval_payload(
        question="What is the gap?",
        router_plan={"plan": 1},
        final_ctx=final_ctx,
        max_slots=3
    )
    assert payload["question"] == "What is the gap?"
    assert payload["router_plan"] == {"plan": 1}
    assert payload["context"] == [{"id": "1"}]
    assert payload["known_sources"] == ["A", "B"]
    assert payload["max_slots"] == 3
