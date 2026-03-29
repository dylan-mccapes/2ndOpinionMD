try:
    from server.api import coding_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

@pytest.mark.asyncio
async def test_coding_minimal(monkeypatch):
    # Patch _handle_rag_ask and OpenAI
    monkeypatch.setattr(coding_routes, '_handle_rag_ask', mock.AsyncMock(return_value={'matches': []}))
    class DummyClient:
        def chat(self, *a, **kw):
            class Resp: content = '{}'
            return Resp()
    monkeypatch.setattr('openai.OpenAI', lambda api_key=None: DummyClient())
    import os
    monkeypatch.setenv('OPENAI_API_KEY', 'dummy')
    monkeypatch.setenv('CHAT_MODEL', 'gpt-4o-mini')
    class DummyRequest: pass
    class DummyPayload:
        note = 'test note'
        sources = ''
        limit = 1
    # Should not raise
    await coding_routes.coding(DummyRequest(), DummyPayload())

def test_add_basic(monkeypatch):
    # Patch enrich_missing_code_from_matches and choose_citation
    monkeypatch.setattr(coding_routes, 'enrich_missing_code_from_matches', lambda it, matches: None)
    monkeypatch.setattr(coding_routes, 'choose_citation', lambda it, matches: ({'source': 'src', 'meta': {'doc_key': 'dk'}, 'title': 't', 'text': 'txt'}, 'reason'))
    monkeypatch.setattr(coding_routes, '_excerpt', lambda text, title: 'excerpt')
    import io
    import csv
    payload = {'matches': []}
    arr = [{'system': 'ICD-10-CM', 'code': 'A00', 'title': 'Cholera', 'why': 'test'}]
    output = io.StringIO()
    w = csv.DictWriter(output, fieldnames=["kind","system","code","title","why_or_indication","citation.source","citation.doc_key","citation.title","excerpt","citation_reason"])
    w.writeheader()
    # Should not raise
    coding_routes.add('dx', arr, 'why')

def test_H_P_SP(monkeypatch):
    # Patch story and Paragraph/Spacer
    story = []
    monkeypatch.setattr(coding_routes, 'story', story)
    class DummyParagraph:
        def __init__(self, text, style):
            self.text = text
            self.style = style
    class DummySpacer:
        def __init__(self, a, b):
            self.a = a
            self.b = b
    monkeypatch.setattr(coding_routes, 'Paragraph', DummyParagraph)
    monkeypatch.setattr(coding_routes, 'Spacer', DummySpacer)
    monkeypatch.setattr(coding_routes, 'styles', {'Heading2': 'h2', 'BodyText': 'bt'})
    import textwrap
    monkeypatch.setattr(coding_routes, 'textwrap', textwrap)
    coding_routes.H('Header')
    coding_routes.P('Body text')
    coding_routes.SP(5)
    assert isinstance(story[0], DummyParagraph)
    assert isinstance(story[1], DummyParagraph)
    assert isinstance(story[2], DummySpacer)

def test_table_for(monkeypatch):
    # Patch story, H, SP, enrich_missing_code_from_matches, _mk_table
    story = []
    monkeypatch.setattr(coding_routes, 'story', story)
    monkeypatch.setattr(coding_routes, 'H', lambda t: story.append(f'H:{t}'))
    monkeypatch.setattr(coding_routes, 'SP', lambda h=8: story.append(f'SP:{h}'))
    monkeypatch.setattr(coding_routes, 'enrich_missing_code_from_matches', lambda it, matches: None)
    monkeypatch.setattr(coding_routes, 'payload', {'matches': []})
    monkeypatch.setattr(coding_routes, '_mk_table', lambda data, max_w: ('table', data))
    monkeypatch.setattr(coding_routes, 'max_w', 100)
    arr = [{'col1': 'a', 'col2': 'b'}]
    coding_routes.table_for('Title', arr, ['col1', 'col2'], ['Col1', 'Col2'])
    assert any(isinstance(x, tuple) and x[0] == 'table' for x in story)
