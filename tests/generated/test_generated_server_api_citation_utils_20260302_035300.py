import pytest
try:
    from server.api import citation_utils
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

from unittest import mock

def test_split_matches_by_role_basic():
    matches = [
        {"source": "ICD10CM", "foo": 1},
        {"source": "loinc", "foo": 2},
        {"source": "guideline", "foo": 3},
        {"source": "unknown", "foo": 4}
    ]
    result = citation_utils.split_matches_by_role(matches)
    assert isinstance(result, dict)
    assert result["icd10cm"] == [{"source": "ICD10CM", "foo": 1}]
    assert result["loinc"] == [{"source": "loinc", "foo": 2}]
    assert result["guidelines"] == [{"source": "guideline", "foo": 3}]
    assert result["other"] == [{"source": "unknown", "foo": 4}]

def test_split_matches_by_role_empty():
    assert citation_utils.split_matches_by_role([]) == {k: [] for k in [
        "icd10cm", "icd11", "icd10pcs", "loinc", "rxnorm", "snomed", "guidelines", "nice", "acr_eular", "medical_knowledge", "hpo", "mimic4_dx", "mimic4_note", "other"]}


def test_enrich_missing_code_from_matches_sets_code(monkeypatch):
    item = {"system": "loinc", "title": "Blood Glucose", "code": ""}
    matches = [
        {"source": "loinc", "title": "Blood Glucose", "source_id": "12345"}
    ]
    # Patch _norm, _lc, _title_tokens to identity for simplicity
    monkeypatch.setattr(citation_utils, "_norm", lambda x: x)
    monkeypatch.setattr(citation_utils, "_lc", lambda x: (x or "").lower())
    monkeypatch.setattr(citation_utils, "_title_tokens", lambda x: x.split())
    citation_utils.enrich_missing_code_from_matches(item, matches)
    # Should set code to source_id of match
    assert item["code"] == "12345"


def test_enrich_missing_code_from_matches_no_title(monkeypatch):
    item = {"system": "loinc", "title": "", "code": ""}
    matches = []
    monkeypatch.setattr(citation_utils, "_norm", lambda x: x)
    monkeypatch.setattr(citation_utils, "_lc", lambda x: (x or "").lower())
    monkeypatch.setattr(citation_utils, "_title_tokens", lambda x: x.split())
    citation_utils.enrich_missing_code_from_matches(item, matches)
    assert item["code"] == ""


def test_choose_citation_exact(monkeypatch):
    item = {"system": "loinc", "code": "123"}
    matches = [{"system": "loinc", "code": "123", "foo": "bar"}]
    monkeypatch.setattr(citation_utils, "_match_by_system_code", lambda i, m: m[0])
    monkeypatch.setattr(citation_utils, "_match_by_title", lambda i, m: None)
    result, reason = citation_utils.choose_citation(item, matches)
    assert result == matches[0]
    assert reason == "system+code match"


def test_choose_citation_title(monkeypatch):
    item = {"system": "loinc", "code": "999"}
    matches = [{"system": "loinc", "code": "123", "foo": "bar"}]
    monkeypatch.setattr(citation_utils, "_match_by_system_code", lambda i, m: None)
    monkeypatch.setattr(citation_utils, "_match_by_title", lambda i, m: m[0])
    result, reason = citation_utils.choose_citation(item, matches)
    assert result == matches[0]
    assert reason == "title overlap"


def test_choose_citation_none(monkeypatch):
    item = {"system": "loinc", "code": "999"}
    matches = []
    monkeypatch.setattr(citation_utils, "_match_by_system_code", lambda i, m: None)
    monkeypatch.setattr(citation_utils, "_match_by_title", lambda i, m: None)
    result, reason = citation_utils.choose_citation(item, matches)
    assert result is None
    assert reason.startswith("no exact match")


def test_explain_missing_citation_system_code():
    item = {"system": "loinc", "code": "123", "title": "foo"}
    matches = [{}, {}]
    out = citation_utils.explain_missing_citation(item, matches)
    assert "no loinc citation found for code 123" in out
    assert "among 2 matches" in out


def test_explain_missing_citation_title():
    item = {"system": "", "code": "", "title": "foo bar"}
    matches = []
    out = citation_utils.explain_missing_citation(item, matches)
    assert "no citation with overlapping title tokens" in out
    assert "foo bar" in out


def test_explain_missing_citation_insufficient():
    item = {"system": "", "code": "", "title": ""}
    matches = []
    out = citation_utils.explain_missing_citation(item, matches)
    assert out == "insufficient fields to match a citation"
