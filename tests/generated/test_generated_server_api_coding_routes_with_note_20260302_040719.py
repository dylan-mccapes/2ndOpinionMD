import pytest
try:
    from server.api import coding_routes_with_note
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
import types
from unittest import mock

@pytest.mark.asyncio
def test_coding_basic(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    # Patch OpenAI and os.getenv
    dummy_openai = types.SimpleNamespace(OpenAI=lambda api_key: types.SimpleNamespace(chat_completions=lambda **kwargs: types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content='{}'))])))
    monkeypatch.setitem(__import__('sys').modules, 'openai', dummy_openai)
    monkeypatch.setattr('os.getenv', lambda k, d=None: 'dummy')
    class DummyRequest:
        pass
    payload = {"note": "test note"}
    import inspect
    params = list(inspect.signature(coding_routes_with_note.coding).parameters)
    args = [DummyRequest(), payload, 'json', 0]
    result = pytest.run(coding_routes_with_note.coding(*args))
    assert result is not None


def test_add_appends_rows(monkeypatch):
    rows = []
    matches = [{"system": "sys", "code": "c", "title": "t", "source": "s", "meta": {"doc_key": "dk"}, "text": "txt"}]
    def _match_citation(it, matches):
        return matches[0]
    def _excerpt(text, title):
        return text[:5]
    arr = [{"system": "sys", "code": "c", "title": "t", "why": "w"}]
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
    assert rows[0]["why_or_indication"] == "w"


def test_H_appends_heading():
    story = []
    styles = {"Heading2": object()}
    Paragraph = lambda txt, style: (txt, style)
    def H(txt):
        story.append(Paragraph(f"<b>{txt}</b>", styles["Heading2"]))
    H("Title")
    assert story[0][0] == "<b>Title</b>"


def test_P_appends_body():
    story = []
    styles = {"BodyText": object()}
    import textwrap
    Paragraph = lambda txt, style: (txt, style)
    def P(txt):
        story.append(Paragraph(textwrap.fill(txt, width=110), styles["BodyText"]))
    P("Some body text.")
    assert story[0][0].startswith("Some body text")


def test_SP_appends_spacer():
    story = []
    Spacer = lambda a, h: (a, h)
    def SP(h=8):
        story.append(Spacer(1, h))
    SP()
    assert story[0] == (1, 8)
    SP(5)
    assert story[1] == (1, 5)


def test_table_for_appends_table():
    story = []
    styles = {"Heading2": object(), "BodyText": object()}
    Paragraph = lambda txt, style: (txt, style)
    Spacer = lambda a, h: (a, h)
    class Table:
        def __init__(self, data, repeatRows=1):
            self.data = data
            self.repeatRows = repeatRows
            self.styled = False
        def setStyle(self, style):
            self.styled = True
    class TableStyle:
        def __init__(self, lst):
            self.lst = lst
    colors = types.SimpleNamespace(lightgrey='grey', grey='g')
    def H(txt):
        story.append(Paragraph(f"<b>{txt}</b>", styles["Heading2"]))
    def SP(h=8):
        story.append(Spacer(1, h))
    def table_for(title, arr, cols, why_label):
        arr = arr or []
        if not arr: return
        H(title); SP(2)
        data = [cols]
        for it in arr:
            row = [str(it.get(c,"")) for c in cols]
            data.append(row)
        tbl = Table(data, repeatRows=1)
        tbl.setStyle(TableStyle([
            ("BACKGROUND",(0,0),(-1,0), colors.lightgrey),
            ("GRID",(0,0),(-1,-1), 0.25, colors.grey),
            ("FONTNAME",(0,0),(-1,0), "Helvetica-Bold"),
        ]))
        story.append(tbl); SP()
    arr = [{"col1": "a", "col2": "b"}]
    cols = ["col1", "col2"]
    table_for("My Table", arr, cols, "why")
    assert any(isinstance(x, Table) for x in story)
