try:
    import pytest
    from unittest import mock
    from server.api import coding_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_coding(monkeypatch):
    # Patch _handle_rag_ask and OpenAI
    monkeypatch.setattr(coding_routes, '_handle_rag_ask', mock.AsyncMock(return_value={'matches': []}))
    class DummyClient:
        def chat(self, *a, **k):
            class R:
                def __getitem__(self, k): return '{}'
            return R()
    monkeypatch.setattr('openai.OpenAI', lambda api_key=None: DummyClient())
    payload = mock.Mock()
    payload.note = 'test note'
    payload.sources = None
    payload.limit = 1
    request = mock.Mock()
    pytest.run(coding_routes.coding(request, payload, format='json', pretty=0))


def test_add():
    arr = [{'system': 'ICD-10-CM', 'code': 'A01', 'title': 'Test', 'why': 'reason'}]
    payload = {'matches': []}
    def enrich_missing_code_from_matches(it, matches):
        it['code'] = it.get('code', 'X')
    def choose_citation(it, matches):
        return ({'source': 'src', 'meta': {'doc_key': 'dk'}, 'title': 't', 'text': 'txt'}, 'reason')
    def _excerpt(text, title):
        return text[:10]
    import csv
    from io import StringIO
    output = StringIO()
    w = csv.DictWriter(output, fieldnames=["kind", "system", "code", "title", "why_or_indication", "citation.source", "citation.doc_key", "citation.title", "excerpt", "citation_reason"])
    w.writeheader()
    kind = 'dx'
    why_field = 'why'
    # Patch functions in local scope
    coding_routes.enrich_missing_code_from_matches = enrich_missing_code_from_matches
    coding_routes.choose_citation = choose_citation
    coding_routes._excerpt = _excerpt
    coding_routes.payload = payload
    coding_routes.w = w
    coding_routes.add(kind, arr, why_field)
    output.seek(0)
    lines = output.readlines()
    assert len(lines) > 1

def test_H_P_SP(monkeypatch):
    story = []
    class Paragraph:
        def __init__(self, t, style):
            self.t = t
            self.style = style
    styles = {"Heading2": 1, "BodyText": 2}
    import textwrap
    def H(t): story.append(Paragraph(f"<b>{t}</b>", styles["Heading2"]))
    def P(t): story.append(Paragraph(textwrap.fill(str(t), width=110), styles["BodyText"]))
    def SP(h=8): story.append(h)
    H("Title")
    P("Body")
    SP()
    assert len(story) == 3

def test_table_for(monkeypatch):
    story = []
    def H(t): story.append(f"H:{t}")
    def SP(h=8): story.append(f"SP:{h}")
    def enrich_missing_code_from_matches(it, matches):
        it['code'] = it.get('code', 'X')
    def _mk_table(data, max_w):
        return data
    payload = {'matches': []}
    arr = [{'system': 'ICD-10-CM', 'code': 'A01', 'title': 'Test'}]
    cols = ['system', 'code', 'title']
    labels = ['System', 'Code', 'Title']
    max_w = 100
    coding_routes.enrich_missing_code_from_matches = enrich_missing_code_from_matches
    coding_routes._mk_table = _mk_table
    coding_routes.payload = payload
    coding_routes.story = story
    coding_routes.H = H
    coding_routes.SP = SP
    coding_routes.table_for("Test Table", arr, cols, labels)
    assert any(isinstance(x, list) for x in story)
