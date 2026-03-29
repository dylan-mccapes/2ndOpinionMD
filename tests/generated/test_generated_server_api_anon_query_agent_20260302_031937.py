import pytest
import sys
from unittest import mock

try:
    from server.api import anon_query_agent
except ImportError:
    pytest.skip('server.api.anon_query_agent not importable', allow_module_level=True)

import asyncio

@pytest.mark.asyncio
async def test_anonymize_query_for_logging_success(monkeypatch):
    async def fake_chat_completion_async(**kwargs):
        return {'choices': [{'message': {'content': 'anonymized'}}]}
    monkeypatch.setattr(anon_query_agent, 'chat_completion_async', fake_chat_completion_async)
    result = await anon_query_agent.anonymize_query_for_logging('Sensitive info', timeout=0.1)
    assert result == 'anonymized'

@pytest.mark.asyncio
async def test_anonymize_query_for_logging_timeout(monkeypatch):
    async def slow_chat_completion_async(**kwargs):
        await asyncio.sleep(0.2)
        return {'choices': [{'message': {'content': 'anonymized'}}]}
    monkeypatch.setattr(anon_query_agent, 'chat_completion_async', slow_chat_completion_async)
    result = await anon_query_agent.anonymize_query_for_logging('Sensitive info', timeout=0.01)
    assert result == 'query_received: anonymization_timeout'

def test_anonymize_query_sync_success(monkeypatch):
    async def fake_anonymize_query_for_logging(query, timeout=2.0):
        return 'anonymized_sync'
    monkeypatch.setattr(anon_query_agent, 'anonymize_query_for_logging', fake_anonymize_query_for_logging)
    result = anon_query_agent.anonymize_query_sync('Sensitive info')
    assert result == 'anonymized_sync'

def test_anonymize_query_sync_exception(monkeypatch):
    def fake_run(coro):
        raise RuntimeError('fail')
    monkeypatch.setattr(anon_query_agent.asyncio, 'run', fake_run)
    result = anon_query_agent.anonymize_query_sync('Sensitive info')
    assert result.startswith('query_received: sync_anonymization_error')
