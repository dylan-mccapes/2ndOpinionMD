try:
    import pytest
    from server.api import citation_governance as cg
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import re
from unittest import mock

def test_norm_sys_basic():
    assert cg.norm_sys('ICD-10-CM') == 'icd10-cm'
    assert cg.norm_sys('icd10cm') == 'icd10-cm'
    assert cg.norm_sys('ICD-11') == 'icd11'
    assert cg.norm_sys('SNOMED CT') == 'snomed'
    assert cg.norm_sys('other') == 'other'
    assert cg.norm_sys(None) == ''

def test_is_authoritative(monkeypatch):
    monkeypatch.setattr(cg, 'AUTHORITATIVE', {'icd10-cm', 'snomed'})
    assert cg.is_authoritative('ICD-10-CM') is True
    assert cg.is_authoritative('SNOMED') is True
    assert cg.is_authoritative('loinc') is False

def test_is_lexical(monkeypatch):
    monkeypatch.setattr(cg, 'LEXICAL_ONLY', {'chv', 'hpo'})
    assert cg.is_lexical('chv') is True
    assert cg.is_lexical('HPO') is True
    assert cg.is_lexical('icd10cm') is False

def test_is_guideline_src(monkeypatch):
    monkeypatch.setattr(cg, 'GUIDELINE_SOURCES', ['nice', 'acr', 'guideline'])
    assert cg.is_guideline_src('NICE guideline') is True
    assert cg.is_guideline_src('ACR_EULAR') is True
    assert cg.is_guideline_src('random') is False
    assert cg.is_guideline_src('') is False

def test_now_iso_format():
    iso = cg.now_iso()
    assert isinstance(iso, str)
    assert re.match(r"\d{4}-\d{2}-\d{2}T", iso)

def test_best_citation_for_exact_code_and_system():
    item = {'title': 'Hypertension', 'code': 'I10', 'system': 'ICD-10-CM'}
    matches = [
        {'source': 'ICD-10-CM', 'source_id': 'I10', 'title': 'Hypertension'},
        {'source': 'ICD-10-CM', 'source_id': 'I11', 'title': 'Other'}
    ]
    result = cg.best_citation_for(item, matches)
    assert result == matches[0]

def test_best_citation_for_title_match():
    item = {'title': 'Hypertension', 'code': '', 'system': 'ICD-10-CM'}
    matches = [
        {'source': 'ICD-10-CM', 'source_id': 'I11', 'title': 'Hypertension'},
        {'source': 'ICD-10-CM', 'source_id': 'I12', 'title': 'Other'}
    ]
    result = cg.best_citation_for(item, matches)
    assert result == matches[0]

def test_best_citation_for_any_authoritative(monkeypatch):
    item = {'title': 'Hypertension', 'code': '', 'system': 'ICD-10-CM'}
    matches = [
        {'source': 'SNOMED', 'source_id': '123', 'title': 'Hypertension'},
        {'source': 'CHV', 'source_id': '456', 'title': 'Hypertension'}
    ]
    monkeypatch.setattr(cg, 'AUTHORITATIVE', {'snomed'})
    result = cg.best_citation_for(item, matches)
    assert result == matches[0]

def test_best_citation_for_none():
    item = {'title': '', 'code': '', 'system': 'ICD-10-CM'}
    matches = []
    assert cg.best_citation_for(item, matches) is None

def test_compute_col_widths_basic():
    table = [['A', 'B'], ['Longer', 'Short']]
    widths = cg.compute_col_widths(table, max_width=200)
    assert isinstance(widths, list)
    assert len(widths) == 2
    assert all(isinstance(w, float) for w in widths)

def test_compute_col_widths_empty():
    assert cg.compute_col_widths([], 100) == []

def test_compute_col_widths_scale():
    table = [['A', 'B'], ['Longer', 'Short']]
    widths = cg.compute_col_widths(table, max_width=60, min_width=10)
    assert all(w >= 10 for w in widths)

def test_excerpt_no_needle():
    text = 'This is a long text for excerpt testing.'
    result = cg.excerpt(text, '', limit=10)
    assert result == text[:10]

def test_excerpt_with_needle():
    text = 'This is a long text for excerpt testing.'
    result = cg.excerpt(text, 'long', limit=20)
    assert 'long' in result
    assert len(result) <= 20

def test_excerpt_needle_not_found():
    text = 'This is a long text for excerpt testing.'
    result = cg.excerpt(text, 'missing', limit=10)
    assert result == text[:10]

def test_excerpt_empty_text():
    assert cg.excerpt('', 'needle') == ''

def test_compose_claim_bundle_basic(monkeypatch):
    monkeypatch.setattr(cg, 'norm_sys', lambda s: 'icd10-cm')
    item = {'system': 'ICD-10-CM', 'code': 'I10', 'title': 'Hypertension'}
    matches = [
        {'source': 'ICD-10-CM', 'source_id': 'I10', 'title': 'Hypertension', 'meta': {}}
    ]
    bundle = cg.compose_claim_bundle('diagnosis', item, matches)
    assert isinstance(bundle, dict)
    assert bundle['kind'] == 'diagnosis'
    assert 'codes' in bundle
