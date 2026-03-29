import pytest
from unittest import mock

try:
    from server.api import embeddings
except ImportError:
    pytest.skip('server.api.embeddings could not be imported', allow_module_level=True)

import pytest_asyncio

@pytest.mark.asyncio
async def test_embed_text_returns_embedding(monkeypatch):
    class DummyResponse:
        class Data:
            embedding = [0.1, 0.2, 0.3]
        data = [Data()]
    async def dummy_create(model, input):
        return DummyResponse()
    dummy_client = mock.Mock()
    dummy_client.embeddings.create = dummy_create
    monkeypatch.setattr(embeddings, '_client', dummy_client)
    monkeypatch.setattr(embeddings, '_MODEL', 'test-model')
    result = await embeddings.embed_text('hello world')
    assert isinstance(result, list)
    assert result == [0.1, 0.2, 0.3]
