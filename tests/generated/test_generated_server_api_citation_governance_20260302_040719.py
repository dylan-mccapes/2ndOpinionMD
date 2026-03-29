try:
    import pytest
    from server.api import citation_governance as cg
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

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
    monkeypatch.setattr(cg, "LEXICAL_ONLY", {"chv", "mimic4_note"})
    assert cg.is_lexical("chv") is True
    assert cg.is_lexical("mimic4_note") is True
    assert cg.is_lexical("icd10cm") is False

def test_is_guideline_src(monkeypatch):
    monkeypatch.setattr(cg, "GUIDELINE_SOURCES", ["nice", "acr", "guideline"]) 
    assert cg.is_guideline_src("NICE Guideline 123") is True
    assert cg.is_guideline_src("ACR/EULAR recommendation") is True
    assert cg.is_guideline_src("random source") is False
    assert cg.is_guideline_src("") is False

def test_now_iso_format():
    import datetime
    iso = cg.now_iso()
    # Should be ISO format and end with 'Z' or '+00:00' for UTC
    assert "T" in iso
    assert iso.endswith("+00:00") or iso.endswith("Z") or "+00:00" in iso

def test_best_citation_for_exact_code_and_system():
    item = {"title": "Hypertension", "code": "I10", "system": "ICD-10-CM"}
    matches = [
        {"source": "ICD-10-CM", "source_id": "I10", "title": "Hypertension"},
        {"source": "ICD-10-CM", "source_id": "E11", "title": "Diabetes"}
    ]
    result = cg.best_citation_for(item, matches)
    assert result == matches[0]

def test_best_citation_for_title_match():
    item = {"title": "Hypertension", "system": "ICD-10-CM"}
    matches = [
        {"source": "ICD-10-CM", "title": "Essential hypertension"},
        {"source": "ICD-10-CM", "title": "Diabetes"}
    ]
    result = cg.best_citation_for(item, matches)
    assert result == matches[0]

def test_best_citation_for_no_match():
    item = {"title": "Unknown", "system": "ICD-10-CM"}
    matches = [
        {"source": "ICD-10-CM", "title": "Hypertension"}
    ]
    result = cg.best_citation_for(item, matches)
    assert result is None

def test_compute_col_widths_empty():
    assert cg.compute_col_widths([], 400) == []

def test_compute_col_widths_basic():
    table = [["A", "B"], ["LongerText", "Short"]]
    widths = cg.compute_col_widths(table, 400)
    assert len(widths) == 2
    assert all(w >= 48.0 for w in widths)
    assert sum(widths) <= 400

def test_compute_col_widths_scale_down():
    table = [["A"*50, "B"*50]]
    widths = cg.compute_col_widths(table, 100)
    assert len(widths) == 2
    assert all(w >= 48.0 for w in widths)
    assert sum(widths) <= 100.1

def test_excerpt_no_text():
    assert cg.excerpt("", "needle") == ""

def test_excerpt_no_needle():
    text = "This is a test string."
    assert cg.excerpt(text, "") == text[:360]

def test_excerpt_needle_found():
    text = "A"*100 + "needle" + "B"*200
    out = cg.excerpt(text, "needle")
    assert "needle" in out
    assert len(out) <= 360

def test_excerpt_needle_not_found():
    text = "A"*400
    out = cg.excerpt(text, "notfound")
    assert out == text[:360]

def test_compose_claim_bundle_min(monkeypatch):
    # Patch norm_sys to identity for simplicity
    monkeypatch.setattr(cg, "norm_sys", lambda s: s or "")
    item = {"system": "ICD-10-CM", "code": "I10", "title": "Hypertension", "why": "Diagnosis"}
    matches = [
        {"source": "ICD-10-CM", "source_id": "I10", "title": "Hypertension"}
    ]
    # Patch is_authoritative to True
    monkeypatch.setattr(cg, "is_authoritative", lambda s: True)
    # Patch best_citation_for to return first match
    monkeypatch.setattr(cg, "best_citation_for", lambda item, matches: matches[0] if matches else None)
    bundle = cg.compose_claim_bundle("diagnosis", item, matches)
    assert isinstance(bundle, dict)
    assert bundle["kind"] == "diagnosis"
    assert "codes" in bundle
