try:
    import pytest
    from server.api import citation_utils as cu
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

def test_split_matches_by_role_basic():
    matches = [
        {"source": "ICD10CM", "foo": 1},
        {"source": "loinc", "foo": 2},
        {"source": "guideline", "foo": 3},
        {"source": "unknown", "foo": 4}
    ]
    buckets = cu.split_matches_by_role(matches)
    assert buckets["icd10cm"] == [matches[0]]
    assert buckets["loinc"] == [matches[1]]
    assert buckets["guidelines"] == [matches[2]]
    assert matches[3] in buckets["other"]

def test_split_matches_by_role_empty():
    assert cu.split_matches_by_role([])["other"] == []

def test_enrich_missing_code_from_matches_adds_code(monkeypatch):
    # Patch _norm, _lc, _title_tokens
    monkeypatch.setattr(cu, "_norm", lambda x: "" if not x else x)
    monkeypatch.setattr(cu, "_lc", lambda x: (x or "").lower())
    monkeypatch.setattr(cu, "_title_tokens", lambda x: (x or "").split())
    item = {"system": "loinc", "title": "Glucose", "code": None}
    matches = [
        {"source": "loinc", "title": "Glucose", "source_id": "1234-5"}
    ]
    cu.enrich_missing_code_from_matches(item, matches)
    assert item["code"] == "1234-5"

def test_enrich_missing_code_from_matches_no_title(monkeypatch):
    monkeypatch.setattr(cu, "_norm", lambda x: "" if not x else x)
    item = {"system": "loinc", "title": None, "code": None}
    matches = []
    cu.enrich_missing_code_from_matches(item, matches)
    assert item["code"] is None

def test_choose_citation_exact(monkeypatch):
    # Patch _match_by_system_code and _match_by_title
    monkeypatch.setattr(cu, "_match_by_system_code", lambda item, matches: (matches[0] if matches else None))
    monkeypatch.setattr(cu, "_match_by_title", lambda item, matches: None)
    item = {"system": "icd10cm", "code": "I10"}
    matches = [{"source": "icd10cm", "source_id": "I10"}]
    cite, reason = cu.choose_citation(item, matches)
    assert cite == matches[0]
    assert "system+code" in reason

def test_choose_citation_title(monkeypatch):
    monkeypatch.setattr(cu, "_match_by_system_code", lambda item, matches: None)
    monkeypatch.setattr(cu, "_match_by_title", lambda item, matches: (matches[0] if matches else None))
    item = {"title": "Hypertension"}
    matches = [{"title": "Hypertension"}]
    cite, reason = cu.choose_citation(item, matches)
    assert cite == matches[0]
    assert "title" in reason

def test_choose_citation_none(monkeypatch):
    monkeypatch.setattr(cu, "_match_by_system_code", lambda item, matches: None)
    monkeypatch.setattr(cu, "_match_by_title", lambda item, matches: None)
    cite, reason = cu.choose_citation({}, [])
    assert cite is None
    assert "no exact match" in reason

def test_explain_missing_citation_code_and_system():
    item = {"system": "icd10cm", "code": "I10"}
    matches = [{}, {}]
    msg = cu.explain_missing_citation(item, matches)
    assert "no icd10cm citation found for code i10" in msg

def test_explain_missing_citation_title():
    item = {"title": "Hypertension"}
    matches = []
    msg = cu.explain_missing_citation(item, matches)
    assert "overlapping title tokens" in msg

def test_explain_missing_citation_insufficient():
    item = {}
    matches = []
    msg = cu.explain_missing_citation(item, matches)
    assert "insufficient fields" in msg
