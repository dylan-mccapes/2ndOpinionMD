import pytest
try:
    from server.api import embeddings
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

import sys
from unittest import mock

@pytest.mark.asyncio
async def test_embed_text_returns_embedding(monkeypatch):
    # Patch _client.embeddings.create to return a mock response
    class MockEmbedding:
        def __init__(self, embedding):
            self.embedding = embedding
    class MockResp:
        data = [MockEmbedding([0.1, 0.2, 0.3])]
    async def mock_create(model, input):
        return MockResp()
    monkeypatch.setattr(embeddings._client.embeddings, 'create', mock_create)
    result = await embeddings.embed_text("hello world")
    assert isinstance(result, list)
    assert result == [0.1, 0.2, 0.3]
