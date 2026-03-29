import pytest
from unittest import mock

try:
    import asyncio
    import pytest_asyncio
    from server.api import coding_routes_v2
except ImportError:
    coding_routes_v2 = None

@pytest.mark.asyncio
@pytest.mark.skipif(coding_routes_v2 is None, reason="Module not importable")
async def test_coding_basic(monkeypatch):
    # Patch _handle_rag_ask and OpenAI
    async def fake_handle_rag_ask(q, k, sources_csv, debug):
        return {"matches": [{"id": 1}]}
    monkeypatch.setattr(coding_routes_v2, "_handle_rag_ask", fake_handle_rag_ask)
    class FakeOpenAI:
        def __init__(self, api_key): pass
        def chat_completions(self, *a, **kw):
            class Resp: choices = [{"message": {"content": '{}'}}]
            return Resp()
    monkeypatch.setattr("server.api.coding_routes_v2.OpenAI", FakeOpenAI)
    monkeypatch.setattr("server.api.coding_routes_v2.os", mock.Mock(getenv=lambda k, d=None: "fake"))
    class DummyRequest: pass
    payload = {"note": "test note"}
    # Should not raise
    result = await coding_routes_v2.coding(DummyRequest(), payload)
    assert result is not None

def test_H_appends_heading(monkeypatch):
    if coding_routes_v2 is None:
        pytest.skip("Module not importable")
    story = []
    styles = {"Heading2": object()}
    Paragraph = lambda txt, style: (txt, style)
    monkeypatch.setitem(globals(), "story", story)
    monkeypatch.setitem(globals(), "styles", styles)
    monkeypatch.setitem(globals(), "Paragraph", Paragraph)
    coding_routes_v2.H("Title")
    assert story and "<b>Title</b>" in story[0][0]

def test_P_appends_body(monkeypatch):
    if coding_routes_v2 is None:
        pytest.skip("Module not importable")
    story = []
    styles = {"BodyText": object()}
    Paragraph = lambda txt, style: (txt, style)
    import textwrap
    monkeypatch.setitem(globals(), "story", story)
    monkeypatch.setitem(globals(), "styles", styles)
    monkeypatch.setitem(globals(), "Paragraph", Paragraph)
    monkeypatch.setitem(globals(), "textwrap", textwrap)
    coding_routes_v2.P("body text")
    assert story and "body text" in story[0][0]

def test_SP_appends_spacer(monkeypatch):
    if coding_routes_v2 is None:
        pytest.skip("Module not importable")
    story = []
    Spacer = lambda a, h: (a, h)
    monkeypatch.setitem(globals(), "story", story)
    monkeypatch.setitem(globals(), "Spacer", Spacer)
    coding_routes_v2.SP(10)
    assert story and story[0][1] == 10
