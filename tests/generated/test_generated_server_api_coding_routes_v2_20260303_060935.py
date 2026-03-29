try:
    from server.api import coding_routes_v2
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

@pytest.mark.asyncio
async def test_coding_minimal(monkeypatch):
    # Patch _handle_rag_ask and OpenAI
    monkeypatch.setattr(coding_routes_v2, '_handle_rag_ask', mock.AsyncMock(return_value={'matches': []}))
    class DummyClient:
        def chat(self, *a, **kw):
            class Resp: content = '{}'
            return Resp()
    monkeypatch.setattr('openai.OpenAI', lambda api_key=None: DummyClient())
    import os
    monkeypatch.setenv('OPENAI_API_KEY', 'dummy')
    monkeypatch.setenv('CHAT_MODEL', 'gpt-4o-mini')
    class DummyRequest: pass
    payload = {'note': 'test', 'sources': '', 'limit': 1}
    # Should not raise
    await coding_routes_v2.coding(DummyRequest(), payload)

def test_H_P_SP(monkeypatch):
    # Patch story and Paragraph/Spacer
    story = []
    monkeypatch.setattr(coding_routes_v2, 'story', story)
    class DummyParagraph:
        def __init__(self, text, style):
            self.text = text
            self.style = style
    class DummySpacer:
        def __init__(self, a, b):
            self.a = a
            self.b = b
    monkeypatch.setattr(coding_routes_v2, 'Paragraph', DummyParagraph)
    monkeypatch.setattr(coding_routes_v2, 'Spacer', DummySpacer)
    monkeypatch.setattr(coding_routes_v2, 'styles', {'Heading2': 'h2', 'BodyText': 'bt'})
    import textwrap
    monkeypatch.setattr(coding_routes_v2, 'textwrap', textwrap)
    coding_routes_v2.H('Header')
    coding_routes_v2.P('Body text')
    coding_routes_v2.SP(5)
    assert isinstance(story[0], DummyParagraph)
    assert isinstance(story[1], DummyParagraph)
    assert isinstance(story[2], DummySpacer)
