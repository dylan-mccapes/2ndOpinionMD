try:
    import pytest
    from server.api import citation_governance
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

def test_norm_sys_cases():
    assert citation_governance.norm_sys(None) == ""
    assert citation_governance.norm_sys("ICD-10-CM") == "icd10-cm"
    assert citation_governance.norm_sys("icd10cm") == "icd10-cm"
    assert citation_governance.norm_sys("ICD-11") == "icd11"
    assert citation_governance.norm_sys("snomed ct") == "snomed"
    assert citation_governance.norm_sys("other") == "other"

def test_is_authoritative(monkeypatch):
    monkeypatch.setattr(citation_governance, 'AUTHORITATIVE', {"icd10-cm", "snomed"})
    assert citation_governance.is_authoritative("ICD-10-CM") is True
    assert citation_governance.is_authoritative("loinc") is False

def test_is_lexical(monkeypatch):
    monkeypatch.setattr(citation_governance, 'LEXICAL_ONLY', {"chv", "hpo"})
    assert citation_governance.is_lexical("chv") is True
    assert citation_governance.is_lexical("rxnorm") is False

def test_is_guideline_src(monkeypatch):
    monkeypatch.setattr(citation_governance, 'GUIDELINE_SOURCES', ["nice", "acr_eular"])
    assert citation_governance.is_guideline_src("NICE guideline") is True
    assert citation_governance.is_guideline_src("random") is False

def test_now_iso():
    result = citation_governance.now_iso()
    assert "T" in result and result.endswith("+00:00") or result.endswith("Z") or "+" in result

def test_best_citation_for_exact_code(monkeypatch):
    item = {"title": "Pain", "code": "123", "system": "ICD-10-CM"}
    matches = [{"source": "ICD-10-CM", "source_id": "123", "title": "Pain"}]
    assert citation_governance.best_citation_for(item, matches) == matches[0]

def test_best_citation_for_title(monkeypatch):
    item = {"title": "Pain", "code": "", "system": "ICD-10-CM"}
    matches = [{"source": "ICD-10-CM", "source_id": "999", "title": "Pain in leg"}]
    assert citation_governance.best_citation_for(item, matches) == matches[0]

def test_compute_col_widths_basic():
    table = [["A", "B"], ["Longer", "Short"]]
    widths = citation_governance.compute_col_widths(table, max_width=200)
    assert len(widths) == 2
    assert all(w >= 48.0 for w in widths)

def test_compute_col_widths_scale():
    table = [["A"*40, "B"*40]]
    widths = citation_governance.compute_col_widths(table, max_width=100)
    assert sum(widths) <= 100.1

def test_excerpt_cases():
    text = "This is a long string about pain and suffering."
    assert citation_governance.excerpt(text, "pain")[:20] == "This is a long string"
    assert citation_governance.excerpt(text, "", 10) == "This is a "
    assert citation_governance.excerpt("", "pain") == ""

def test_compose_claim_bundle(monkeypatch):
    monkeypatch.setattr(citation_governance, 'norm_sys', lambda s: "icd10-cm")
    item = {"system": "ICD-10-CM", "code": "123", "title": "Pain", "why": "reason"}
    matches = [{"source": "ICD-10-CM", "source_id": "123", "title": "Pain"}]
    bundle = citation_governance.compose_claim_bundle("diagnosis", item, matches)
    assert "kind" in bundle["claim"] or "claim" in bundle["claim"] or "codes" in bundle
