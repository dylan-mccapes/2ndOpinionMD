try:
    import pytest
    from server.api import citation_utils as cu
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

def test_split_matches_by_role_basic():
    matches = [
        {'source': 'ICD10CM'},
        {'source': 'loinc'},
        {'source': 'guideline'},
        {'source': 'unknown'}
    ]
    buckets = cu.split_matches_by_role(matches)
    assert 'icd10cm' in buckets
    assert 'loinc' in buckets
    assert 'guidelines' in buckets
    assert 'other' in buckets
    assert matches[0] in buckets['icd10cm']
    assert matches[1] in buckets['loinc']
    assert matches[2] in buckets['guidelines']
    assert matches[3] in buckets['other']

def test_split_matches_by_role_empty():
    buckets = cu.split_matches_by_role([])
    assert isinstance(buckets, dict)
    assert all(isinstance(v, list) for v in buckets.values())

def test_enrich_missing_code_from_matches_adds_code(monkeypatch):
    # Patch _norm, _lc, _title_tokens to minimal versions
    monkeypatch.setattr(cu, '_norm', lambda x: False)
    monkeypatch.setattr(cu, '_lc', lambda x: (x or '').lower())
    monkeypatch.setattr(cu, '_title_tokens', lambda x: x.split())
    item = {'system': 'loinc', 'code': '', 'title': 'Blood Pressure'}
    matches = [
        {'source': 'loinc', 'title': 'Blood Pressure', 'source_id': '12345-6'}
    ]
    cu.enrich_missing_code_from_matches(item, matches)
    assert item['code'] == '12345-6'

def test_enrich_missing_code_from_matches_no_title(monkeypatch):
    monkeypatch.setattr(cu, '_norm', lambda x: False)
    monkeypatch.setattr(cu, '_lc', lambda x: (x or '').lower())
    item = {'system': 'loinc', 'code': '', 'title': ''}
    matches = []
    cu.enrich_missing_code_from_matches(item, matches)
    assert item['code'] == ''

def test_enrich_missing_code_from_matches_existing_code(monkeypatch):
    monkeypatch.setattr(cu, '_norm', lambda x: True)
    item = {'system': 'loinc', 'code': '12345-6', 'title': 'Blood Pressure'}
    matches = []
    cu.enrich_missing_code_from_matches(item, matches)
    assert item['code'] == '12345-6'
