import pytest
from unittest import mock

try:
    from server.api import citation_utils
except ImportError:
    pytest.skip('server.api.citation_utils not importable', allow_module_level=True)


def test_split_matches_by_role_basic():
    matches = [
        {'source': 'ICD10CM', 'foo': 1},
        {'source': 'loinc', 'foo': 2},
        {'source': 'guideline_xyz', 'foo': 3},
        {'source': 'unknown', 'foo': 4}
    ]
    out = citation_utils.split_matches_by_role(matches)
    assert isinstance(out, dict)
    assert out['icd10cm'][0]['foo'] == 1
    assert out['loinc'][0]['foo'] == 2
    assert out['guidelines'][0]['foo'] == 3
    assert out['other'][0]['foo'] == 4


def test_split_matches_by_role_empty():
    out = citation_utils.split_matches_by_role([])
    assert all(isinstance(v, list) for v in out.values())
    assert sum(len(v) for v in out.values()) == 0


def test_enrich_missing_code_from_matches_adds_code(monkeypatch):
    item = {'system': 'loinc', 'title': 'Glucose', 'code': ''}
    matches = [
        {'source': 'loinc', 'title': 'Glucose', 'source_id': '12345'}
    ]
    # Patch _norm, _lc, _title_tokens to identity/expected
    monkeypatch.setattr(citation_utils, '_norm', lambda x: x)
    monkeypatch.setattr(citation_utils, '_lc', lambda x: (x or '').lower())
    monkeypatch.setattr(citation_utils, '_title_tokens', lambda x: x.split())
    citation_utils.enrich_missing_code_from_matches(item, matches)
    assert item['code'] == '12345'


def test_enrich_missing_code_from_matches_no_title(monkeypatch):
    item = {'system': 'loinc', 'title': '', 'code': ''}
    matches = [{'source': 'loinc', 'title': 'Glucose', 'source_id': '12345'}]
    monkeypatch.setattr(citation_utils, '_norm', lambda x: x)
    monkeypatch.setattr(citation_utils, '_lc', lambda x: (x or '').lower())
    monkeypatch.setattr(citation_utils, '_title_tokens', lambda x: x.split())
    citation_utils.enrich_missing_code_from_matches(item, matches)
    assert item['code'] == ''


def test_choose_citation_system_code(monkeypatch):
    item = {'system': 'loinc', 'code': '123'}
    matches = [{'system': 'loinc', 'code': '123', 'foo': 'bar'}]
    monkeypatch.setattr(citation_utils, '_match_by_system_code', lambda i, m: m[0])
    monkeypatch.setattr(citation_utils, '_match_by_title', lambda i, m: None)
    result, reason = citation_utils.choose_citation(item, matches)
    assert result == matches[0]
    assert reason == 'system+code match'


def test_choose_citation_title_overlap(monkeypatch):
    item = {'system': 'loinc', 'code': 'notfound'}
    matches = [{'system': 'loinc', 'code': 'other', 'foo': 'bar'}]
    monkeypatch.setattr(citation_utils, '_match_by_system_code', lambda i, m: None)
    monkeypatch.setattr(citation_utils, '_match_by_title', lambda i, m: m[0])
    result, reason = citation_utils.choose_citation(item, matches)
    assert result == matches[0]
    assert reason == 'title overlap'


def test_choose_citation_none(monkeypatch):
    item = {'system': 'loinc', 'code': 'notfound'}
    matches = []
    monkeypatch.setattr(citation_utils, '_match_by_system_code', lambda i, m: None)
    monkeypatch.setattr(citation_utils, '_match_by_title', lambda i, m: None)
    result, reason = citation_utils.choose_citation(item, matches)
    assert result is None
    assert 'no exact match' in reason


def test_explain_missing_citation_system_code():
    item = {'system': 'loinc', 'code': '123', 'title': 'foo'}
    matches = [{}]
    msg = citation_utils.explain_missing_citation(item, matches)
    assert 'no loinc citation found for code 123' in msg


def test_explain_missing_citation_title():
    item = {'system': '', 'code': '', 'title': 'foo'}
    matches = [{}]
    msg = citation_utils.explain_missing_citation(item, matches)
    assert 'no citation with overlapping title tokens' in msg


def test_explain_missing_citation_insufficient():
    item = {'system': '', 'code': '', 'title': ''}
    matches = [{}]
    msg = citation_utils.explain_missing_citation(item, matches)
    assert 'insufficient fields' in msg
