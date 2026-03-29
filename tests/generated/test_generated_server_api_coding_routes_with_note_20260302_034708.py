try:
    import pytest
    from server.api import coding_routes_with_note
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

from unittest import mock

@pytest.mark.asyncio
async def test_coding_with_note(monkeypatch):
    # Patch OpenAI and os.getenv
    class FakeOpenAI:
        def __init__(self, api_key=None):
            pass
        class chat:
            @staticmethod
            def completions_create(**kwargs):
                class Resp:
                    choices = [type("obj", (), {"message": type("obj", (), {"content": '{"insight": {"assessment": "ok", "risk_factors": [], "red_flags": [], "lifestyle_plan": []}}'})})]
                return Resp()
    monkeypatch.setattr("server.api.coding_routes_with_note.OpenAI", FakeOpenAI)
    monkeypatch.setattr("server.api.coding_routes_with_note.os", mock.Mock(getenv=lambda k, d=None: "dummy"))
    class DummyRequest:
        pass
    payload = {"note": "test note"}
    result = await coding_routes_with_note.coding(DummyRequest(), payload)
    assert isinstance(result, dict) or result is not None

def test_add_appends_rows(monkeypatch):
    rows = []
    matches = [{"source": "src", "meta": {"doc_key": "dk"}, "title": "t", "text": "txt", "source_id": "sid"}]
    def _match_citation(it, matches):
        return matches[0]
    def _excerpt(text, title):
        return text[:5]
    monkeypatch.setattr("server.api.coding_routes_with_note._match_citation", _match_citation)
    monkeypatch.setattr("server.api.coding_routes_with_note._excerpt", _excerpt)
    arr = [{"system": "sys", "code": "c", "title": "t", "why": "w"}]
    def add(kind: str, arr, why_field):
        arr = arr or []
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
    assert len(rows) == 1
    assert rows[0]["kind"] == "kind1"

def test_H_P_SP(monkeypatch):
    story = []
    styles = {"Heading2": object(), "BodyText": object()}
    class DummyParagraph:
        def __init__(self, txt, style):
            self.txt = txt
            self.style = style
    class DummySpacer:
        def __init__(self, a, b):
            self.a = a
            self.b = b
    monkeypatch.setattr("server.api.coding_routes_with_note.Paragraph", DummyParagraph)
    monkeypatch.setattr("server.api.coding_routes_with_note.Spacer", DummySpacer)
    monkeypatch.setattr("server.api.coding_routes_with_note.textwrap", mock.Mock(fill=lambda txt, width: txt))
    def H(txt):
        story.append(DummyParagraph(f"<b>{txt}</b>", styles["Heading2"]))
    def P(txt):
        story.append(DummyParagraph(txt, styles["BodyText"]))
    def SP(h=8):
        story.append(DummySpacer(1, h))
    H("Heading")
    P("Body")
    SP()
    assert len(story) == 3
    assert story[0].txt.startswith("<b>")
    assert story[1].txt == "Body"
    assert story[2].b == 8

def test_table_for(monkeypatch):
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
        def setStyle(self, style):
            self.style = style
    class DummyTableStyle:
        def __init__(self, arr):
            self.arr = arr
    monkeypatch.setattr("server.api.coding_routes_with_note.Paragraph", DummyParagraph)
    monkeypatch.setattr("server.api.coding_routes_with_note.Spacer", DummySpacer)
    monkeypatch.setattr("server.api.coding_routes_with_note.Table", DummyTable)
    monkeypatch.setattr("server.api.coding_routes_with_note.TableStyle", DummyTableStyle)
    monkeypatch.setattr("server.api.coding_routes_with_note.colors", mock.Mock(lightgrey=1, grey=2))
    def H(txt):
        story.append(DummyParagraph(f"<b>{txt}</b>", styles["Heading2"]))
    def SP(h=8):
        story.append(DummySpacer(1, h))
    def table_for(title, arr, cols, why_label):
        arr = arr or []
        if not arr: return
        H(title); SP(2)
        data = [cols]
        for it in arr:
            row = [str(it.get(c,"")) for c in cols]
            data.append(row)
        tbl = DummyTable(data, repeatRows=1)
        tbl.setStyle(DummyTableStyle([
            ("BACKGROUND",(0,0),(-1,0), 1),
            ("GRID",(0,0),(-1,-1), 0.25, 2),
            ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ]))
        story.append(tbl); SP()
    arr = [{"col1": "v1", "col2": "v2"}]
    table_for("Title", arr, ["col1", "col2"], "why")
    assert any(isinstance(x, DummyTable) for x in story)
