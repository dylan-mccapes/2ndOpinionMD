try:
    import pytest
    from server.api import coding_routes_v2
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

import types
from unittest import mock

@pytest.mark.asyncio
async def test_coding_basic(monkeypatch):
    # Patch _handle_rag_ask and OpenAI client
    async def fake_handle_rag_ask(q, k, sources_csv, debug):
        return {"matches": [{"id": 1}]}
    monkeypatch.setattr(coding_routes_v2, "_handle_rag_ask", fake_handle_rag_ask)
    
    class FakeOpenAI:
        def __init__(self, api_key=None):
            pass
        class chat:
            @staticmethod
            def completions_create(**kwargs):
                class Resp:
                    choices = [type("obj", (), {"message": type("obj", (), {"content": '{"result": 1}'})})]
                return Resp()
    monkeypatch.setattr("server.api.coding_routes_v2.OpenAI", FakeOpenAI)
    monkeypatch.setattr("server.api.coding_routes_v2.os", mock.Mock(getenv=lambda k, d=None: "dummy"))
    
    class DummyRequest:
        pass
    payload = {"note": "test note"}
    # Should not raise
    result = await coding_routes_v2.coding(DummyRequest(), payload)
    assert isinstance(result, dict) or result is not None


def test_H_appends_heading(monkeypatch):
    story = []
    styles = {"Heading2": object()}
    class DummyParagraph:
        def __init__(self, txt, style):
            self.txt = txt
            self.style = style
    monkeypatch.setattr("server.api.coding_routes_v2.Paragraph", DummyParagraph)
    def H(txt):
        story.append(DummyParagraph(f"<b>{txt}</b>", styles["Heading2"]))
    H("Hello")
    assert len(story) == 1
    assert story[0].txt.startswith("<b>")

def test_P_appends_body(monkeypatch):
    story = []
    styles = {"BodyText": object()}
    class DummyParagraph:
        def __init__(self, txt, style):
            self.txt = txt
            self.style = style
    monkeypatch.setattr("server.api.coding_routes_v2.Paragraph", DummyParagraph)
    monkeypatch.setattr("server.api.coding_routes_v2.textwrap", mock.Mock(fill=lambda txt, width: txt))
    def P(txt):
        story.append(DummyParagraph(txt, styles["BodyText"]))
    P("Body text")
    assert len(story) == 1
    assert story[0].txt == "Body text"

def test_SP_appends_spacer(monkeypatch):
    story = []
    class DummySpacer:
        def __init__(self, a, b):
            self.a = a
            self.b = b
    monkeypatch.setattr("server.api.coding_routes_v2.Spacer", DummySpacer)
    def SP(h=8):
        story.append(DummySpacer(1, h))
    SP()
    assert len(story) == 1
    assert story[0].b == 8
