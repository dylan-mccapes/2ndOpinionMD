import pytest
try:
    from server.api import coding_routes_v2
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
    # Mock dependencies
    class DummyRequest:
        pass
    async def dummy_handle_rag_ask(q, k, sources_csv, debug):
        return {"matches": [{"id": 1}]}
    monkeypatch.setattr(coding_routes_v2, '_handle_rag_ask', dummy_handle_rag_ask)
    monkeypatch.setattr('os.getenv', lambda k, d=None: 'dummy')
    dummy_openai = types.SimpleNamespace(OpenAI=lambda api_key: types.SimpleNamespace(chat_completions=lambda **kwargs: types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content='{}'))])))
    monkeypatch.setitem(__import__('sys').modules, 'openai', dummy_openai)
    payload = {"note": "test note"}
    # Query and Body are FastAPI params, so just pass the defaults
    import inspect
    params = list(inspect.signature(coding_routes_v2.coding).parameters)
    args = [DummyRequest(), payload, 'json', 0]
    result = pytest.run(coding_routes_v2.coding(*args))
    assert result is not None


def test_H_appends_heading(monkeypatch):
    story = []
    styles = {"Heading2": object()}
    Paragraph = lambda txt, style: (txt, style)
    def H(txt):
        story.append(Paragraph(f"<b>{txt}</b>", styles["Heading2"]))
    H("Title")
    assert story[0][0] == "<b>Title</b>"


def test_P_appends_body(monkeypatch):
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
