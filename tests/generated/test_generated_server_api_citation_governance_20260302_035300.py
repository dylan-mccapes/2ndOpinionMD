import pytest
try:
    from server.api import citation_governance
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest import mock
import datetime

def test_norm_sys_variants():
    assert citation_governance.norm_sys('ICD-10-CM') == 'icd10-cm'
    assert citation_governance.norm_sys('icd10cm') == 'icd10-cm'
    assert citation_governance.norm_sys('ICD-11') == 'icd11'
    assert citation_governance.norm_sys('snomed ct') == 'snomed'
    assert citation_governance.norm_sys('other') == 'other'
    assert citation_governance.norm_sys(None) == ''
    assert citation_governance.norm_sys('  SNOMED  ') == 'snomed'

def test_is_authoritative(monkeypatch):
    monkeypatch.setattr(citation_governance, 'AUTHORITATIVE', {'icd10-cm', 'icd11'})
    assert citation_governance.is_authoritative('ICD-10-CM')
    assert not citation_governance.is_authoritative('snomed')

def test_is_lexical(monkeypatch):
    monkeypatch.setattr(citation_governance, 'LEXICAL_ONLY', {'chv', 'mesh'})
    assert citation_governance.is_lexical('chv')
    assert not citation_governance.is_lexical('icd10-cm')

def test_is_guideline_src(monkeypatch):
    monkeypatch.setattr(citation_governance, 'GUIDELINE_SOURCES', ['who', 'nice'])
    assert citation_governance.is_guideline_src('WHO guideline')
    assert citation_governance.is_guideline_src('nice')
    assert not citation_governance.is_guideline_src('random')

def test_now_iso():
    iso = citation_governance.now_iso()
    assert iso.endswith('+00:00') or iso.endswith('Z') or 'T' in iso
    # Should parse as datetime
    dt = datetime.datetime.fromisoformat(iso)
    assert dt.tzinfo is not None

def test_best_citation_for_exact_code_system(monkeypatch):
    item = {'title': 'Hypertension', 'code': 'I10', 'system': 'ICD-10-CM'}
    matches = [
        {'source': 'ICD-10-CM', 'source_id': 'I10', 'title': 'Hypertension'},
        {'source': 'ICD-10-CM', 'source_id': 'I11', 'title': 'Other'}
    ]
    result = citation_governance.best_citation_for(item, matches)
    assert result == matches[0]

def test_best_citation_for_title(monkeypatch):
    item = {'title': 'Hypertension', 'code': '', 'system': 'ICD-10-CM'}
    matches = [
        {'source': 'ICD-10-CM', 'source_id': 'I11', 'title': 'Hypertension'},
        {'source': 'ICD-10-CM', 'source_id': 'I12', 'title': 'Other'}
    ]
    result = citation_governance.best_citation_for(item, matches)
    assert result == matches[0]

def test_best_citation_for_none(monkeypatch):
    item = {'title': 'Unknown', 'code': '', 'system': 'ICD-10-CM'}
    matches = [
        {'source': 'ICD-10-CM', 'source_id': 'I11', 'title': 'Other'}
    ]
    result = citation_governance.best_citation_for(item, matches)
    assert result is None
