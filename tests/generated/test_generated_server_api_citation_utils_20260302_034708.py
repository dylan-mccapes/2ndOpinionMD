try:
    import pytest
    from server.api import citation_utils
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

def test_split_matches_by_role():
    matches = [
        {"source": "ICD10CM"},
        {"source": "loinc"},
        {"source": "guideline"},
        {"source": "other"},
        {"source": "unknown"}
    ]
    buckets = citation_utils.split_matches_by_role(matches)
    assert "icd10cm" in buckets
    assert "loinc" in buckets
    assert "guidelines" in buckets
    assert "other" in buckets
    assert any(isinstance(v, list) for v in buckets.values())

def test_enrich_missing_code_from_matches(monkeypatch):
    # Patch _norm, _lc, _title_tokens
    monkeypatch.setattr(citation_utils, '_norm', lambda x: False)
    monkeypatch.setattr(citation_utils, '_lc', lambda x: (x or '').lower())
    monkeypatch.setattr(citation_utils, '_title_tokens', lambda x: x.split())
    item = {"system": "loinc", "title": "Pain", "code": None}
    matches = [{"source": "loinc", "title": "Pain", "source_id": "123"}]
    citation_utils.enrich_missing_code_from_matches(item, matches)
    assert item["code"] == "123"

def test_choose_citation(monkeypatch):
    monkeypatch.setattr(citation_utils, '_match_by_system_code', lambda item, matches: matches[0] if matches else None)
    monkeypatch.setattr(citation_utils, '_match_by_title', lambda item, matches: None)
    item = {"system": "loinc", "code": "123", "title": "Pain"}
    matches = [{"source": "loinc", "source_id": "123", "title": "Pain"}]
    result, reason = citation_utils.choose_citation(item, matches)
    assert result == matches[0]
    assert reason == "system+code match"

def test_explain_missing_citation():
    item = {"system": "loinc", "code": "123", "title": "Pain"}
    matches = []
    msg = citation_utils.explain_missing_citation(item, matches)
    assert "no loinc citation found for code 123" in msg or "no citation with overlapping title tokens" in msg
