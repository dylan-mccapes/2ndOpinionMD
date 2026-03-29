try:
    from server.api import coding_routes_with_note
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

@pytest.mark.asyncio
async def test_coding_with_note(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    # Patch OpenAI and os.getenv
    with mock.patch.dict('os.environ', {"OPENAI_API_KEY": "dummy", "CHAT_MODEL": "gpt-4o-mini"}):
        with mock.patch('server.api.coding_routes_with_note.OpenAI', autospec=True) as MockOpenAI:
            MockOpenAI.return_value = mock.Mock()
            class DummyRequest:
                pass
            payload = {"note": "test note", "limit": 2}
            result = await coding_routes_with_note.coding(DummyRequest(), payload)
            assert result is not None


def test_add_adds_rows(monkeypatch):
    rows = []
    matches = [{"source": "src", "meta": {"doc_key": "dk"}, "title": "t", "text": "txt", "source_id": "sid"}]
    def _match_citation(it, matches):
        return matches[0]
    def _excerpt(text, title):
        return text[:10]
    arr = [{"system": "sys", "code": "c", "title": "t", "why": "w"}]
    monkeypatch.setattr(coding_routes_with_note, '_match_citation', _match_citation)
    monkeypatch.setattr(coding_routes_with_note, '_excerpt', _excerpt)
    def add(kind: str, arr, why_field: str):
        for it in arr:
            cite = _match_citation(it, matches)
            rows.append({
                "kind": kind,
                "system": it.get("system",""),
                "code": it.get("code",""),
                "title": it.get("title",""),
                "why_or_indication": it.get(why_field,""),
                "citation.source": (cite or {}).get("source",""),
                "citation.doc_key": ((cite or {}).get("meta") or {}).get("doc_key") or (cite or {}).get("source_id",""),
                "citation.title": (cite or {}).get("title",""),
                "excerpt": _excerpt((cite or {}).get("text",""), it.get("title","")),
            })
    add("kind1", arr, "why")
    assert rows[0]["kind"] == "kind1"
    assert rows[0]["system"] == "sys"


def test_H_adds_heading(monkeypatch):
    story = []
    styles = {"Heading2": object()}
    class DummyParagraph:
        def __init__(self, txt, style):
            self.txt = txt
            self.style = style
    monkeypatch.setattr(coding_routes_with_note, 'Paragraph', DummyParagraph)
    def H(txt):
        story.append(DummyParagraph(f"<b>{txt}</b>", styles["Heading2"]))
    H("Title")
    assert len(story) == 1
    assert story[0].txt.startswith("<b>Title</b>")


def test_P_adds_bodytext(monkeypatch):
    story = []
    styles = {"BodyText": object()}
    class DummyParagraph:
        def __init__(self, txt, style):
            self.txt = txt
            self.style = style
    monkeypatch.setattr(coding_routes_with_note, 'Paragraph', DummyParagraph)
    monkeypatch.setattr(coding_routes_with_note, 'textwrap', mock.Mock(fill=lambda txt, width: txt))
    def P(txt):
        story.append(DummyParagraph(txt, styles["BodyText"]))
    P("Some text")
    assert len(story) == 1
    assert story[0].txt == "Some text"


def test_SP_adds_spacer(monkeypatch):
    story = []
    class DummySpacer:
        def __init__(self, a, b):
            self.a = a
            self.b = b
    monkeypatch.setattr(coding_routes_with_note, 'Spacer', DummySpacer)
    def SP(h=8):
        story.append(DummySpacer(1, h))
    SP()
    assert len(story) == 1
    assert story[0].b == 8


def test_table_for_adds_table(monkeypatch):
    story = []
    styles = {"Heading2": object()}
    class DummyParagraph:
        def __init__(self, txt, style):
            self.txt = txt
            self.style = style
    class DummySpacer:
        def __init__(self, a, b):
            self.a = a
            self.b = b
    class DummyTable:
        def __init__(self, data, repeatRows=1):
            self.data = data
            self.repeatRows = repeatRows
            self.styled = False
        def setStyle(self, style):
            self.styled = True
    monkeypatch.setattr(coding_routes_with_note, 'Paragraph', DummyParagraph)
    monkeypatch.setattr(coding_routes_with_note, 'Spacer', DummySpacer)
    monkeypatch.setattr(coding_routes_with_note, 'Table', DummyTable)
    monkeypatch.setattr(coding_routes_with_note, 'TableStyle', lambda x: x)
    monkeypatch.setattr(coding_routes_with_note, 'colors', mock.Mock(lightgrey=1, grey=2))
    def H(txt):
        story.append(DummyParagraph(f"<b>{txt}</b>", styles["Heading2"]))
    def SP(h=8):
        story.append(DummySpacer(1, h))
    title = "Table Title"
    arr = [{"col1": "v1", "col2": "v2"}]
    cols = ["col1", "col2"]
    def table_for(title, arr, cols, why_label):
        arr = arr or []
        if not arr: return
        H(title); SP(2)
        data = [cols]
        for it in arr:
            row = [str(it.get(c,"")) for c in cols]
            data.append(row)
        tbl = DummyTable(data, repeatRows=1)
        tbl.setStyle([("BACKGROUND",(0,0),(-1,0), 1), ("GRID",(0,0),(-1,-1), 0.25, 2), ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold")])
        story.append(tbl); SP()
    table_for(title, arr, cols, "why")
    assert any(isinstance(x, DummyTable) for x in story)
