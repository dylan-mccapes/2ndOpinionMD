try:
    import pytest
    from unittest import mock
    from server.api import anon_query_agent
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
async def test_anonymize_query_for_logging_success(monkeypatch):
    async def fake_chat_completion_async(**kwargs):
        return {'choices': [{'message': {'content': 'anonymized'}}]}
    monkeypatch.setattr(anon_query_agent, 'chat_completion_async', fake_chat_completion_async)
    result = await anon_query_agent.anonymize_query_for_logging('my query', timeout=0.1)
    assert result == 'anonymized'

@pytest.mark.asyncio
async def test_anonymize_query_for_logging_timeout(monkeypatch):
    import asyncio
    async def slow_chat_completion_async(**kwargs):
        await asyncio.sleep(0.2)
        return {'choices': [{'message': {'content': 'should not get here'}}]}
    monkeypatch.setattr(anon_query_agent, 'chat_completion_async', slow_chat_completion_async)
    result = await anon_query_agent.anonymize_query_for_logging('my query', timeout=0.01)
    assert result.startswith('query_received')

def test_anonymize_query_sync_success(monkeypatch):
    def fake_run(coro):
        return 'anonymized_sync'
    monkeypatch.setattr(anon_query_agent.asyncio, 'run', fake_run)
    result = anon_query_agent.anonymize_query_sync('my query')
    assert result == 'anonymized_sync'

def test_anonymize_query_sync_error(monkeypatch):
    def fake_run(coro):
        raise RuntimeError('fail')
    monkeypatch.setattr(anon_query_agent.asyncio, 'run', fake_run)
    result = anon_query_agent.anonymize_query_sync('my query')
    assert result.startswith('query_received')
