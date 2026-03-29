import pytest
import sys
from unittest import mock

try:
    from server.api import anon_query_agent
except ImportError:
    pytest.skip('server.api.anon_query_agent not importable', allow_module_level=True)

@pytest.mark.asyncio
async def test_anonymize_query_for_logging_success(monkeypatch):
    async def fake_chat_completion_async(*a, **k):
        return {'choices': [{'message': {'content': 'anonymized'}}]}
    monkeypatch.setattr(anon_query_agent, 'chat_completion_async', fake_chat_completion_async)
    monkeypatch.setattr(anon_query_agent, 'ANONYMIZATION_SYSTEM_PROMPT', 'prompt')
    result = await anon_query_agent.anonymize_query_for_logging('my query')
    assert result == 'anonymized'

@pytest.mark.asyncio
async def test_anonymize_query_for_logging_timeout(monkeypatch):
    async def raise_timeout(*a, **k):
        raise Exception('timeout')
    monkeypatch.setattr(anon_query_agent, 'chat_completion_async', raise_timeout)
    monkeypatch.setattr(anon_query_agent, 'ANONYMIZATION_SYSTEM_PROMPT', 'prompt')
    result = await anon_query_agent.anonymize_query_for_logging('my query')
    assert result.startswith('query_received')

def test_anonymize_query_sync_success(monkeypatch):
    monkeypatch.setattr(anon_query_agent, 'anonymize_query_for_logging', mock.AsyncMock(return_value='anon'))
    result = anon_query_agent.anonymize_query_sync('my query')
    assert result == 'anon'

def test_anonymize_query_sync_exception(monkeypatch):
    monkeypatch.setattr(anon_query_agent, 'anonymize_query_for_logging', mock.AsyncMock(side_effect=Exception('fail')))
    monkeypatch.setattr(anon_query_agent, 'logger', mock.Mock())
    result = anon_query_agent.anonymize_query_sync('my query')
    assert result.startswith('query_received')
