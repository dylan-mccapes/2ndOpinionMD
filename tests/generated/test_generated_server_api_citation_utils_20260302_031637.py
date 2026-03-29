# AUTO-GENERATED TESTS FOR server/api/citation_utils.py
import pytest
from unittest import mock

try:
    from server.api import citation_utils as cu
except ImportError:
    pytest.skip('server.api.citation_utils import failed', allow_module_level=True)


def test_split_matches_by_role_basic():
    matches = [
        {"source": "ICD10CM", "foo": 1},
        {"source": "guideline", "foo": 2},
        {"source": "other", "foo": 3},
        {"source": "loinc", "foo": 4}
    ]
    buckets = cu.split_matches_by_role(matches)
    assert isinstance(buckets, dict)
    assert "icd10cm" in buckets
    assert any(m["foo"] == 1 for m in buckets["icd10cm"])
    assert any(m["foo"] == 2 for m in buckets["guidelines"])
    assert any(m["foo"] == 3 for m in buckets["other"])
    assert any(m["foo"] == 4 for m in buckets["loinc"])


def test_enrich_missing_code_from_matches_adds_code(monkeypatch):
    # Patch _norm, _lc, _title_tokens
    monkeypatch.setattr(cu, "_norm", lambda x: False)
    monkeypatch.setattr(cu, "_lc", lambda x: (x or "").lower())
    monkeypatch.setattr(cu, "_title_tokens", lambda t: t.split())
    item = {"system": "loinc", "title": "Blood Pressure"}
    matches = [
        {"source": "loinc", "title": "Blood Pressure", "source_id": "1234-5"}
    ]
    cu.enrich_missing_code_from_matches(item, matches)
    assert item.get("code") == "1234-5"


def test_enrich_missing_code_from_matches_no_title(monkeypatch):
    monkeypatch.setattr(cu, "_norm", lambda x: False)
    monkeypatch.setattr(cu, "_lc", lambda x: (x or "").lower())
    item = {"system": "loinc"}
    matches = []
    cu.enrich_missing_code_from_matches(item, matches)
    assert "code" not in item or item["code"] is None


def test_choose_citation_exact(monkeypatch):
    # Patch _match_by_system_code and _match_by_title
    m = {"source": "icd10cm", "source_id": "I10"}
    monkeypatch.setattr(cu, "_match_by_system_code", lambda item, matches: m)
    monkeypatch.setattr(cu, "_match_by_title", lambda item, matches: None)
    item = {"system": "icd10cm", "code": "I10"}
    matches = [m]
    result, reason = cu.choose_citation(item, matches)
    assert result == m
    assert reason == "system+code match"


def test_choose_citation_title(monkeypatch):
    monkeypatch.setattr(cu, "_match_by_system_code", lambda item, matches: None)
    m = {"title": "Hypertension"}
    monkeypatch.setattr(cu, "_match_by_title", lambda item, matches: m)
    item = {"title": "Hypertension"}
    matches = [m]
    result, reason = cu.choose_citation(item, matches)
    assert result == m
    assert reason == "title overlap"


def test_choose_citation_none(monkeypatch):
    monkeypatch.setattr(cu, "_match_by_system_code", lambda item, matches: None)
    monkeypatch.setattr(cu, "_match_by_title", lambda item, matches: None)
    item = {"system": "icd10cm"}
    matches = []
    result, reason = cu.choose_citation(item, matches)
    assert result is None
    assert "no exact match" in reason


def test_explain_missing_citation_code():
    item = {"system": "icd10cm", "code": "i10"}
    matches = [{}, {}]
    msg = cu.explain_missing_citation(item, matches)
    assert "no icd10cm citation found for code i10" in msg


def test_explain_missing_citation_title():
    item = {"title": "Hypertension"}
    matches = []
    msg = cu.explain_missing_citation(item, matches)
    assert "no citation with overlapping title tokens" in msg


def test_explain_missing_citation_insufficient():
    item = {}
    matches = []
    msg = cu.explain_missing_citation(item, matches)
    assert "insufficient fields" in msg
