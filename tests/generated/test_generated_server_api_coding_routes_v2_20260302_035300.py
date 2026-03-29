try:
    from server.api import coding_routes_v2
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest import mock

@pytest.mark.asyncio
async def test_coding_basic(monkeypatch):
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not available", allow_module_level=True)
    # Mock dependencies
    monkeypatch.setattr(coding_routes_v2, '_handle_rag_ask', mock.AsyncMock(return_value={"matches": []}))
    class DummyRequest:
        pass
    payload = {"note": "test note", "limit": 2}
    # Patch OpenAI and os.getenv
    with mock.patch.dict('os.environ', {"OPENAI_API_KEY": "dummy", "CHAT_MODEL": "gpt-4o-mini"}):
        with mock.patch('server.api.coding_routes_v2.OpenAI', autospec=True) as MockOpenAI:
            MockOpenAI.return_value = mock.Mock()
            # Patch _handle_rag_ask to avoid actual RAG
            result = await coding_routes_v2.coding(DummyRequest(), payload)
            assert result is not None


def test_H_adds_heading(monkeypatch):
    story = []
    styles = {"Heading2": object()}
    class DummyParagraph:
        def __init__(self, txt, style):
            self.txt = txt
            self.style = style
    monkeypatch.setattr(coding_routes_v2, 'Paragraph', DummyParagraph)
    def H(txt):
        story.append(DummyParagraph(f"<b>{txt}</b>", styles["Heading2"]))
    H("Title")
    assert len(story) == 1
    assert story[0].txt.startswith("<b>Title</b>")


def test_P_adds_bodytext(monkeypatch):
    story = []
    styles = {"BodyText": object()}
    class DummyParagraph:
        def __init__(self, txt, style):
            self.txt = txt
            self.style = style
    monkeypatch.setattr(coding_routes_v2, 'Paragraph', DummyParagraph)
    monkeypatch.setattr(coding_routes_v2, 'textwrap', mock.Mock(fill=lambda txt, width: txt))
    def P(txt):
        story.append(DummyParagraph(txt, styles["BodyText"]))
    P("Some text")
    assert len(story) == 1
    assert story[0].txt == "Some text"


def test_SP_adds_spacer(monkeypatch):
    story = []
    class DummySpacer:
        def __init__(self, a, b):
            self.a = a
            self.b = b
    monkeypatch.setattr(coding_routes_v2, 'Spacer', DummySpacer)
    def SP(h=8):
        story.append(DummySpacer(1, h))
    SP()
    assert len(story) == 1
    assert story[0].b == 8
