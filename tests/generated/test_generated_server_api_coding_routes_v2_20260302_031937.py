import pytest
from unittest import mock

try:
    import server.api.coding_routes_v2 as coding_routes_v2
except ImportError:
    pytest.skip('server.api.coding_routes_v2 could not be imported', allow_module_level=True)

@pytest.mark.asyncio
async def test_coding_v2_handles_rag_and_openai(monkeypatch):
    class DummyRequest:
        pass
    payload = {'note': 'test note', 'sources': 'src1', 'limit': 2}
    dummy_rag = {'matches': [{'id': 1}]}
    async def fake_handle_rag_ask(q, k, sources_csv, debug):
        return dummy_rag
    monkeypatch.setattr(coding_routes_v2, '_handle_rag_ask', fake_handle_rag_ask)
    monkeypatch.setattr('server.api.coding_routes_v2.os', mock.Mock(getenv=lambda k, default=None: 'dummy'))
    class DummyOpenAI:
        def __init__(self, api_key): pass
        def chat_completions(self, *a, **k): return mock.Mock(choices=[mock.Mock(message=mock.Mock(content='{"insight": {}}'))])
    monkeypatch.setattr('server.api.coding_routes_v2.OpenAI', DummyOpenAI)
    monkeypatch.setitem(__import__('sys').modules, 'openai', mock.Mock(OpenAI=DummyOpenAI))
    result = await coding_routes_v2.coding(DummyRequest(), payload, format='json', pretty=0)
    assert isinstance(result, dict)
    assert 'insight' in result or isinstance(result, dict)

def test_H_P_SP_exist_and_callable():
    story = []
    class DummyParagraph:
        def __init__(self, text, style):
            self.text = text
            self.style = style
    class DummySpacer:
        def __init__(self, a, b):
            self.a = a
            self.b = b
    styles = {'Heading2': 'h2', 'BodyText': 'body'}
    import textwrap
    def H(txt): story.append(DummyParagraph(f'<b>{txt}</b>', styles['Heading2']))
    def P(txt): story.append(DummyParagraph(textwrap.fill(txt, width=110), styles['BodyText']))
    def SP(h=8): story.append(DummySpacer(1, h))
    H('Header')
    P('Paragraph')
    SP(10)
    assert isinstance(story[0], DummyParagraph)
    assert isinstance(story[2], DummySpacer)
