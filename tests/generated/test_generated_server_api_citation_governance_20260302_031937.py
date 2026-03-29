# Auto-generated tests for server.api.citation_governance
import pytest
import sys

try:
    from server.api import citation_governance as cg
except ImportError:
    pytest.skip('server.api.citation_governance not importable', allow_module_level=True)

from unittest import mock
import datetime

# norm_sys
@pytest.mark.parametrize("input_val,expected", [
    (None, ""),
    ("", ""),
    ("ICD-10-CM", "icd10-cm"),
    ("icd10cm", "icd10-cm"),
    ("ICD-11", "icd11"),
    ("snomed ct", "snomed"),
    ("SNOMED", "snomed"),
    ("loinc", "loinc"),
    ("other_system", "other-system"),
])
def test_norm_sys(input_val, expected):
    assert cg.norm_sys(input_val) == expected

# is_authoritative
@pytest.mark.parametrize("system,authoritative_set,expected", [
    ("ICD-10-CM", {"icd10-cm"}, True),
    ("ICD-11", {"icd10-cm"}, False),
    ("snomed", {"snomed"}, True),
    ("loinc", set(), False),
])
def test_is_authoritative(system, authoritative_set, expected, monkeypatch):
    monkeypatch.setattr(cg, "AUTHORITATIVE", authoritative_set)
    assert cg.is_authoritative(system) == expected

# is_lexical
@pytest.mark.parametrize("system,lexical_set,expected", [
    ("CHV", {"chv"}, True),
    ("ICD-10-CM", {"chv"}, False),
    ("loinc", {"loinc"}, True),
])
def test_is_lexical(system, lexical_set, expected, monkeypatch):
    monkeypatch.setattr(cg, "LEXICAL_ONLY", lexical_set)
    assert cg.is_lexical(system) == expected

# is_guideline_src
@pytest.mark.parametrize("src,guideline_sources,expected", [
    ("NICE guideline", ["nice"], True),
    ("ACR guideline", ["nice"], False),
    ("", ["nice"], False),
    ("guideline", ["guideline"], True),
])
def test_is_guideline_src(src, guideline_sources, expected, monkeypatch):
    monkeypatch.setattr(cg, "GUIDELINE_SOURCES", guideline_sources)
    assert cg.is_guideline_src(src) == expected

# now_iso
def test_now_iso(monkeypatch):
    class FakeDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2024, 3, 2, 3, 19, 37, tzinfo=datetime.timezone.utc)
    monkeypatch.setattr(cg.datetime, "datetime", FakeDatetime)
    result = cg.now_iso()
    assert result.startswith("2024-03-02T03:19:37")
    assert result.endswith("+00:00")

# best_citation_for
@pytest.mark.parametrize("item,matches,expected", [
    # exact code+system match
    ({"title": "Hypertension", "code": "I10", "system": "ICD-10-CM"},
     [{"source": "ICD-10-CM", "source_id": "I10", "title": "Hypertension"}],
     {"source": "ICD-10-CM", "source_id": "I10", "title": "Hypertension"}),
    # same-system title match
    ({"title": "Hypertension", "code": "", "system": "ICD-10-CM"},
     [{"source": "ICD-10-CM", "source_id": "I11", "title": "Hypertension"}],
     {"source": "ICD-10-CM", "source_id": "I11", "title": "Hypertension"}),
    # no match
    ({"title": "Diabetes", "code": "", "system": "ICD-10-CM"},
     [{"source": "ICD-10-CM", "source_id": "E11", "title": "Hypertension"}],
     None),
])
def test_best_citation_for(item, matches, expected):
    result = cg.best_citation_for(item, matches)
    assert result == expected

# compute_col_widths
@pytest.mark.parametrize("table,max_width,min_width,expected_len", [
    ([['a', 'bb'], ['ccc', 'dddd']], 200.0, 48.0, 2),
    ([], 200.0, 48.0, 0),
])
def test_compute_col_widths(table, max_width, min_width, expected_len):
    result = cg.compute_col_widths(table, max_width, min_width)
    assert isinstance(result, list)
    assert len(result) == expected_len
    if table:
        # Each width should be at least min_width
        assert all(w >= min_width for w in result)

# excerpt
@pytest.mark.parametrize("text,needle,limit,expected", [
    ("This is a test string for excerpt function.", "test", 360, "This is a test string for excerpt function."),
    ("", "needle", 360, ""),
    ("Some long text here", "absent", 10, "Some long "),
    ("Some long text here", "long", 360, "Some long text here"),
])
def test_excerpt(text, needle, limit, expected):
    result = cg.excerpt(text, needle, limit)
    assert isinstance(result, str)
    # Should not exceed limit
    assert len(result) <= limit
    # If needle is present, result should contain needle (case-insensitive)
    if needle and needle.lower() in text.lower():
        assert needle.lower() in result.lower()

# compose_claim_bundle
@pytest.mark.parametrize("kind,item,matches,authoritative,expected_keys", [
    ("diagnosis",
     {"system": "ICD-10-CM", "code": "I10", "title": "Hypertension", "why": "Clinical diagnosis"},
     [{"source": "ICD-10-CM", "source_id": "I10", "title": "Hypertension"}],
     {"icd10-cm"},
     ["kind", "claim", "codes"]),
    ("diagnosis",
     {"system": "CHV", "code": "", "title": "Hypertension", "why": ""},
     [],
     set(),
     ["kind", "claim", "codes"]),
])
def test_compose_claim_bundle(kind, item, matches, authoritative, expected_keys, monkeypatch):
    monkeypatch.setattr(cg, "AUTHORITATIVE", authoritative)
    # Compose bundle should always return a dict with at least the expected keys
    result = cg.compose_claim_bundle(kind, item, matches)
    for k in expected_keys:
        assert k in result
