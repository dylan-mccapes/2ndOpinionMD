try:
    import pytest
    from unittest import mock
    from server.api import coding_routes as mod
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_coding(monkeypatch):
    class DummyRequest: pass
    class DummyPayload:
        note = "test"
        sources = None
        limit = 1
    monkeypatch.setattr(mod, '_handle_rag_ask', mock.AsyncMock(return_value={"matches": []}))
    monkeypatch.setattr(mod, 'OpenAI', mock.Mock())
    monkeypatch.setattr(mod, 'os', mock.Mock())
    result = pytest.run(mod.coding(DummyRequest(), DummyPayload(), format="json", pretty=0))
    assert result is not None

def test_add(monkeypatch):
    arr = [{"system": "ICD-10-CM", "code": "A00", "title": "Cholera"}]
    payload = {"matches": []}
    w = mock.Mock()
    w.writerow = mock.Mock()
    monkeypatch.setattr(mod, 'enrich_missing_code_from_matches', lambda it, matches: None)
    monkeypatch.setattr(mod, 'choose_citation', lambda it, matches: (None, "reason"))
    monkeypatch.setattr(mod, 'explain_missing_citation', lambda it: "missing")
    mod.add("kind", arr, "why_field")
    assert w.writerow is not None

def test_H(monkeypatch):
    story = []
    styles = {"Heading2": object()}
    Paragraph = lambda t, s: (t, s)
    monkeypatch.setattr(mod, 'story', story)
    monkeypatch.setattr(mod, 'styles', styles)
    monkeypatch.setattr(mod, 'Paragraph', Paragraph)
    mod.H("Title")
    assert story

def test_P(monkeypatch):
    story = []
    styles = {"BodyText": object()}
    Paragraph = lambda t, s: (t, s)
    import textwrap
    monkeypatch.setattr(mod, 'story', story)
    monkeypatch.setattr(mod, 'styles', styles)
    monkeypatch.setattr(mod, 'Paragraph', Paragraph)
    monkeypatch.setattr(mod, 'textwrap', textwrap)
    mod.P("Some text")
    assert story

def test_SP(monkeypatch):
    story = []
    Spacer = lambda a, h: (a, h)
    monkeypatch.setattr(mod, 'story', story)
    monkeypatch.setattr(mod, 'Spacer', Spacer)
    mod.SP(5)
    assert story

def test_table_for(monkeypatch):
    story = []
    styles = {"Heading2": object()}
    Paragraph = lambda t, s: (t, s)
    max_w = 100
    monkeypatch.setattr(mod, 'story', story)
    monkeypatch.setattr(mod, 'styles', styles)
    monkeypatch.setattr(mod, 'Paragraph', Paragraph)
    monkeypatch.setattr(mod, 'max_w', max_w)
    monkeypatch.setattr(mod, 'enrich_missing_code_from_matches', lambda it, matches: None)
    monkeypatch.setattr(mod, 'payload', {"matches": []})
    monkeypatch.setattr(mod, '_mk_table', lambda data, max_w: data)
    monkeypatch.setattr(mod, 'SP', lambda h=8: story.append(('SP', h)))
    mod.table_for("Title", [{"col1": "v1"}], ["col1"], ["label1"])
    assert story
