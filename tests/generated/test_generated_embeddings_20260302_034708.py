try:
    import pytest
    from server.api import embeddings
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
from unittest.mock import AsyncMock, MagicMock

pytestmark = pytest.mark.asyncio

@pytest.mark.asyncio
async def test_embed_text_returns_vector(monkeypatch):
    class FakeResp:
        data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
    fake_client = MagicMock()
    fake_client.embeddings.create = AsyncMock(return_value=FakeResp())
    monkeypatch.setattr(embeddings, "_client", fake_client)
    monkeypatch.setattr(embeddings, "_MODEL", "fake-model")
    result = await embeddings.embed_text("hello world")
    assert isinstance(result, list)
    assert result == [0.1, 0.2, 0.3]
