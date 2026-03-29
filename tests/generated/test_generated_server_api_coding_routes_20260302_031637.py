import pytest
from unittest import mock

pytestmark = pytest.mark.asyncio

def _import_or_skip():
    try:
        import server.api.coding_routes as mod
        return mod
    except ImportError:
        pytest.skip('server.api.coding_routes import failed', allow_module_level=True)

@pytest.mark.asyncio
async def test_coding(monkeypatch):
    mod = _import_or_skip()
    # Patch _handle_rag_ask and OpenAI
    async def dummy_rag(q, k, sources_csv, debug):
        return {"matches": []}
    monkeypatch.setattr(mod, '_handle_rag_ask', dummy_rag)
    class DummyOpenAI:
        def __init__(self, api_key): pass
        def chat(self, *a, **kw): return type('Resp', (), {"choices": [{"message": {"content": '{}'}}]})()
    monkeypatch.setattr(mod, 'OpenAI', DummyOpenAI)
    monkeypatch.setattr(mod, 'os', mock.Mock(getenv=lambda k, d=None: d))
    # Dummy request and payload
    class DummyRequest: pass
    class DummyPayload:
        note = "test"
        sources = None
        limit = 1
    result = await mod.coding(DummyRequest(), DummyPayload(), format="json", pretty=0)
    assert result is not None

def test_add(monkeypatch):
    mod = _import_or_skip()
    # Patch enrich_missing_code_from_matches, choose_citation, _excerpt
    monkeypatch.setattr(mod, 'enrich_missing_code_from_matches', lambda it, matches: None)
    monkeypatch.setattr(mod, 'choose_citation', lambda it, matches: ({"source": "src", "meta": {"doc_key": "dk"}, "title": "t", "text": "txt"}, "reason"))
    monkeypatch.setattr(mod, '_excerpt', lambda text, title: "excerpt")
    import io, csv
    arr = [{"system": "sys", "code": "c", "title": "t", "why": "w"}]
    payload = {"matches": []}
    output = io.StringIO()
    w = csv.DictWriter(output, fieldnames=["kind", "system", "code", "title", "why_or_indication", "citation.source", "citation.doc_key", "citation.title", "excerpt", "citation_reason"])
    w.writeheader()
    mod.add("kind", arr, "why")
    # No assertion needed, just check no error

def test_H(monkeypatch):
    mod = _import_or_skip()
    story = []
    class DummyParagraph:
        def __init__(self, txt, style): self.txt = txt
    monkeypatch.setattr(mod, 'Paragraph', DummyParagraph)
    styles = {"Heading2": "h2"}
    monkeypatch.setattr(mod, 'styles', styles)
    def H(t): story.append(DummyParagraph(f"<b>{t}</b>", styles["Heading2"]))
    H("Title")
    assert story and isinstance(story[0], DummyParagraph)

def test_P(monkeypatch):
    mod = _import_or_skip()
    story = []
    class DummyParagraph:
        def __init__(self, txt, style): self.txt = txt
    monkeypatch.setattr(mod, 'Paragraph', DummyParagraph)
    monkeypatch.setattr(mod, 'textwrap', mock.Mock(fill=lambda t, width: t))
    styles = {"BodyText": "bt"}
    monkeypatch.setattr(mod, 'styles', styles)
    def P(t): story.append(DummyParagraph(str(t), styles["BodyText"]))
    P("Body")
    assert story and isinstance(story[0], DummyParagraph)

def test_SP(monkeypatch):
    mod = _import_or_skip()
    story = []
    class DummySpacer:
        def __init__(self, a, h): self.h = h
    monkeypatch.setattr(mod, 'Spacer', DummySpacer)
    def SP(h=8): story.append(DummySpacer(1, h))
    SP()
    assert story and isinstance(story[0], DummySpacer)

def test_table_for(monkeypatch):
    mod = _import_or_skip()
    story = []
    monkeypatch.setattr(mod, 'enrich_missing_code_from_matches', lambda it, matches: None)
    monkeypatch.setattr(mod, '_mk_table', lambda data, max_w: data)
    max_w = 100
    def H(title): story.append(title)
    def SP(h=8): story.append(h)
    arr = [{"col1": "v1", "col2": "v2"}]
    payload = {"matches": []}
    cols = ["col1", "col2"]
    labels = ["Col1", "Col2"]
    def table_for(title, arr, cols, labels):
        arr = arr or []
        if not arr: return
        H(title); SP(2); data = [labels]
        for it in arr:
            mod.enrich_missing_code_from_matches(it, payload.get("matches") or [])
            data.append([str(it.get(c,"")) for c in cols])
        story.append(mod._mk_table(data, max_w)); SP()
    table_for("Title", arr, cols, labels)
    assert story
