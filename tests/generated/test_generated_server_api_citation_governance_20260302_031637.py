# AUTO-GENERATED TESTS FOR server/api/citation_governance.py
import pytest
import sys
from unittest import mock

try:
    from server.api import citation_governance as cg
except ImportError:
    pytest.skip('server.api.citation_governance import failed', allow_module_level=True)


def test_norm_sys_basic():
    assert cg.norm_sys(None) == ""
    assert cg.norm_sys("") == ""
    assert cg.norm_sys("ICD-10-CM") == "icd10-cm"
    assert cg.norm_sys("icd10cm") == "icd10-cm"
    assert cg.norm_sys("ICD-11") == "icd11"
    assert cg.norm_sys("snomed ct") == "snomed"
    assert cg.norm_sys("random_system") == "random-system"


def test_is_authoritative(monkeypatch):
    monkeypatch.setattr(cg, "AUTHORITATIVE", {"icd10-cm", "snomed"})
    assert cg.is_authoritative("ICD-10-CM") is True
    assert cg.is_authoritative("SNOMED CT") is True
    assert cg.is_authoritative("loinc") is False


def test_is_lexical(monkeypatch):
    monkeypatch.setattr(cg, "LEXICAL_ONLY", {"chv", "other"})
    assert cg.is_lexical("chv") is True
    assert cg.is_lexical("other") is True
    assert cg.is_lexical("icd10cm") is False


def test_is_guideline_src(monkeypatch):
    monkeypatch.setattr(cg, "GUIDELINE_SOURCES", ["nice", "acr", "guideline"])
    assert cg.is_guideline_src("NICE guideline") is True
    assert cg.is_guideline_src("ACR recommendation") is True
    assert cg.is_guideline_src("random source") is False


def test_now_iso_format():
    import datetime
    iso = cg.now_iso()
    # Should parse as ISO format
    dt = datetime.datetime.fromisoformat(iso)
    assert dt.tzinfo is not None


def test_best_citation_for_exact_code_system():
    item = {"title": "Hypertension", "code": "I10", "system": "ICD-10-CM"}
    matches = [
        {"source": "ICD-10-CM", "source_id": "I10", "title": "Hypertension"},
        {"source": "ICD-10-CM", "source_id": "I11", "title": "Other"}
    ]
    result = cg.best_citation_for(item, matches)
    assert result == matches[0]


def test_best_citation_for_title_match():
    item = {"title": "Hypertension", "system": "ICD-10-CM"}
    matches = [
        {"source": "ICD-10-CM", "title": "Essential hypertension"},
        {"source": "ICD-10-CM", "title": "Other"}
    ]
    result = cg.best_citation_for(item, matches)
    assert result == matches[0]


def test_best_citation_for_none():
    item = {"title": "Unknown", "system": "ICD-10-CM"}
    matches = [
        {"source": "ICD-10-CM", "title": "Hypertension"}
    ]
    result = cg.best_citation_for(item, matches)
    assert result is None


def test_compute_col_widths_basic():
    table = [["A", "B"], ["LongerText", "Short"]]
    widths = cg.compute_col_widths(table, max_width=200.0, min_width=48.0)
    assert len(widths) == 2
    assert all(w >= 48.0 for w in widths)
    assert sum(widths) <= 200.0


def test_compute_col_widths_empty():
    assert cg.compute_col_widths([], 100.0) == []


def test_excerpt_no_needle():
    text = "This is a test string with lots of words."
    out = cg.excerpt(text, "", limit=10)
    assert out == text[:10]


def test_excerpt_with_needle():
    text = "This is a test string with hypertension and more text."
    out = cg.excerpt(text, "hypertension", limit=50)
    assert "hypertension" in out.lower()
    assert len(out) <= 50


def test_excerpt_needle_not_found():
    text = "This is a test string."
    out = cg.excerpt(text, "notfound", limit=10)
    assert out == text[:10]


def test_compose_claim_bundle_minimal(monkeypatch):
    # Patch norm_sys to identity for simplicity
    monkeypatch.setattr(cg, "norm_sys", lambda s: s or "")
    item = {"system": "icd10-cm", "code": "I10", "title": "Hypertension", "why": "diagnosis"}
    matches = [
        {"source": "icd10-cm", "source_id": "I10", "title": "Hypertension"}
    ]
    # Patch any other dependencies if needed
    bundle = cg.compose_claim_bundle("diagnosis", item, matches)
    assert isinstance(bundle, dict)
    assert bundle["kind"] == "diagnosis"
    assert "claim" in bundle
