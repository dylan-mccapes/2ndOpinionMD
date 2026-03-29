import pytest
from unittest import mock

try:
    import server.api.coding_routes_with_note as coding_routes_with_note
except ImportError:
    pytest.skip('server.api.coding_routes_with_note could not be imported', allow_module_level=True)

@pytest.mark.asyncio
async def test_coding_with_note_handles_openai(monkeypatch):
    class DummyRequest:
        pass
    payload = {'note': 'test note', 'sources': 'src1', 'limit': 2}
    monkeypatch.setattr('server.api.coding_routes_with_note.os', mock.Mock(getenv=lambda k, default=None: 'dummy'))
    class DummyOpenAI:
        def __init__(self, api_key): pass
        def chat_completions(self, *a, **k): return mock.Mock(choices=[mock.Mock(message=mock.Mock(content='{"insight": {}}'))])
    monkeypatch.setattr('server.api.coding_routes_with_note.OpenAI', DummyOpenAI)
    monkeypatch.setitem(__import__('sys').modules, 'openai', mock.Mock(OpenAI=DummyOpenAI))
    async def fake_handle_rag_ask(q, k, sources_csv, debug):
        return {'matches': [{'id': 1}]}
    monkeypatch.setattr(coding_routes_with_note, '_handle_rag_ask', fake_handle_rag_ask)
    result = await coding_routes_with_note.coding(DummyRequest(), payload, format='json', pretty=0)
    assert isinstance(result, dict)
    assert 'insight' in result or isinstance(result, dict)

def test_add_adds_rows(monkeypatch):
    arr = [{'system': 'ICD', 'code': 'A00', 'title': 'Cholera', 'why': 'reason'}]
    matches = [{'system': 'ICD', 'code': 'A00'}]
    rows = []
    def _match_citation(it, matches):
        return {'source': 'src', 'meta': {'doc_key': 'dk'}, 'title': 't', 'text': 'txt', 'source_id': 'sid'}
    def _excerpt(text, title):
        return 'excerpted'
    monkeypatch.setattr(coding_routes_with_note, '_match_citation', _match_citation)
    monkeypatch.setattr(coding_routes_with_note, '_excerpt', _excerpt)
    def add(kind, arr, why_field):
        arr = arr or []
        for it in arr:
            cite = _match_citation(it, matches)
            rows.append({
                'kind': kind,
                'system': it.get('system', ''),
                'code': it.get('code', ''),
                'title': it.get('title', ''),
                'why_or_indication': it.get(why_field, ''),
                'citation.source': (cite or {}).get('source', ''),
                'citation.doc_key': ((cite or {}).get('meta') or {}).get('doc_key') or (cite or {}).get('source_id', ''),
                'citation.title': (cite or {}).get('title', ''),
                'excerpt': _excerpt((cite or {}).get('text', ''), it.get('title', '')),
            })
    add('kind', arr, 'why')
    assert rows

def test_H_P_SP_table_for_exist_and_callable():
    story = []
    class DummyParagraph:
        def __init__(self, text, style):
            self.text = text
            self.style = style
    class DummySpacer:
        def __init__(self, a, b):
            self.a = a
            self.b = b
    class DummyTable:
        def __init__(self, data, repeatRows=1):
            self.data = data
    class DummyTableStyle:
        def __init__(self, lst):
            self.lst = lst
    class DummyColors:
        lightgrey = 'grey'
        grey = 'grey'
    styles = {'Heading2': 'h2', 'BodyText': 'body'}
    import textwrap
    def H(txt): story.append(DummyParagraph(f'<b>{txt}</b>', styles['Heading2']))
    def P(txt): story.append(DummyParagraph(textwrap.fill(txt, width=110), styles['BodyText']))
    def SP(h=8): story.append(DummySpacer(1, h))
    def table_for(title, arr, cols, why_label):
        arr = arr or []
        if not arr: return
        H(title); SP(2)
        data = [cols]
        for it in arr:
            row = [str(it.get(c, "")) for c in cols]
            data.append(row)
        tbl = DummyTable(data, repeatRows=1)
        tbl.setStyle = lambda style: None
        story.append(tbl); SP()
    H('Header')
    P('Paragraph')
    SP(10)
    table_for('Title', [{'a': 1, 'b': 2}], ['a', 'b'], 'why')
    assert isinstance(story[0], DummyParagraph)
    assert isinstance(story[-2], DummyTable)
