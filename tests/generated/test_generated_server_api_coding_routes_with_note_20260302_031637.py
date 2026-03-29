import pytest
from unittest import mock

try:
    import asyncio
    import pytest_asyncio
    from server.api import coding_routes_with_note
except ImportError:
    coding_routes_with_note = None

@pytest.mark.asyncio
@pytest.mark.skipif(coding_routes_with_note is None, reason="Module not importable")
async def test_coding_basic(monkeypatch):
    # Patch OpenAI and os.getenv
    class FakeOpenAI:
        def __init__(self, api_key): pass
        def chat_completions(self, *a, **kw):
            class Resp: choices = [{"message": {"content": '{}'}}]
            return Resp()
    monkeypatch.setattr("server.api.coding_routes_with_note.OpenAI", FakeOpenAI)
    monkeypatch.setattr("server.api.coding_routes_with_note.os", mock.Mock(getenv=lambda k, d=None: "fake"))
    class DummyRequest: pass
    payload = {"note": "test note"}
    # Should not raise
    result = await coding_routes_with_note.coding(DummyRequest(), payload)
    assert result is not None

def test_add_appends_rows(monkeypatch):
    if coding_routes_with_note is None:
        pytest.skip("Module not importable")
    rows = []
    matches = [{"source": "src", "meta": {"doc_key": "dk"}, "title": "t", "text": "txt", "source_id": "sid"}]
    def _match_citation(it, matches): return matches[0]
    def _excerpt(text, title): return text[:10]
    arr = [{"system": "sys", "code": "c", "title": "t", "why": "w"}]
    monkeypatch.setitem(globals(), "rows", rows)
    monkeypatch.setitem(globals(), "matches", matches)
    monkeypatch.setitem(globals(), "_match_citation", _match_citation)
    monkeypatch.setitem(globals(), "_excerpt", _excerpt)
    coding_routes_with_note.add("kind", arr, "why")
    assert rows and rows[0]["kind"] == "kind"

def test_H_appends_heading(monkeypatch):
    if coding_routes_with_note is None:
        pytest.skip("Module not importable")
    story = []
    styles = {"Heading2": object()}
    Paragraph = lambda txt, style: (txt, style)
    monkeypatch.setitem(globals(), "story", story)
    monkeypatch.setitem(globals(), "styles", styles)
    monkeypatch.setitem(globals(), "Paragraph", Paragraph)
    coding_routes_with_note.H("Title")
    assert story and "<b>Title</b>" in story[0][0]

def test_P_appends_body(monkeypatch):
    if coding_routes_with_note is None:
        pytest.skip("Module not importable")
    story = []
    styles = {"BodyText": object()}
    Paragraph = lambda txt, style: (txt, style)
    import textwrap
    monkeypatch.setitem(globals(), "story", story)
    monkeypatch.setitem(globals(), "styles", styles)
    monkeypatch.setitem(globals(), "Paragraph", Paragraph)
    monkeypatch.setitem(globals(), "textwrap", textwrap)
    coding_routes_with_note.P("body text")
    assert story and "body text" in story[0][0]

def test_SP_appends_spacer(monkeypatch):
    if coding_routes_with_note is None:
        pytest.skip("Module not importable")
    story = []
    Spacer = lambda a, h: (a, h)
    monkeypatch.setitem(globals(), "story", story)
    monkeypatch.setitem(globals(), "Spacer", Spacer)
    coding_routes_with_note.SP(10)
    assert story and story[0][1] == 10

def test_table_for_appends_table(monkeypatch):
    if coding_routes_with_note is None:
        pytest.skip("Module not importable")
    story = []
    def H(title): story.append(f"H:{title}")
    def SP(h=8): story.append(f"SP:{h}")
    Table = lambda data, repeatRows=1: [data, repeatRows]
    TableStyle = lambda style: style
    colors = mock.Mock(lightgrey="grey", grey="grey")
    monkeypatch.setitem(globals(), "story", story)
    monkeypatch.setitem(globals(), "H", H)
    monkeypatch.setitem(globals(), "SP", SP)
    monkeypatch.setitem(globals(), "Table", Table)
    monkeypatch.setitem(globals(), "TableStyle", TableStyle)
    monkeypatch.setitem(globals(), "colors", colors)
    arr = [{"a": 1, "b": 2}]
    cols = ["a", "b"]
    coding_routes_with_note.table_for("Title", arr, cols, "why")
    assert any(isinstance(x, list) for x in story)
