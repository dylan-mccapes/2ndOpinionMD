try:
    import pytest
    from unittest import mock
    from server.api import anon_query_agent
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
def test_anonymize_query_for_logging_success(monkeypatch):
    async def fake_chat_completion_async(*a, **k):
        return {'choices': [{'message': {'content': 'anonymized'}}]}
    monkeypatch.setattr(anon_query_agent, 'chat_completion_async', fake_chat_completion_async)
    monkeypatch.setattr(anon_query_agent, 'ANONYMIZATION_SYSTEM_PROMPT', 'prompt')
    result = pytest.run(anon_query_agent.anonymize_query_for_logging('query'))
    import asyncio
    res = asyncio.get_event_loop().run_until_complete(anon_query_agent.anonymize_query_for_logging('query'))
    assert res == 'anonymized'

@pytest.mark.asyncio
def test_anonymize_query_for_logging_timeout(monkeypatch):
    async def fake_chat_completion_async(*a, **k):
        import asyncio
        await asyncio.sleep(0.1)
        raise asyncio.TimeoutError()
    monkeypatch.setattr(anon_query_agent, 'chat_completion_async', fake_chat_completion_async)
    monkeypatch.setattr(anon_query_agent, 'ANONYMIZATION_SYSTEM_PROMPT', 'prompt')
    import asyncio
    res = asyncio.get_event_loop().run_until_complete(anon_query_agent.anonymize_query_for_logging('query', timeout=0.01))
    assert res.startswith('query_received')

def test_anonymize_query_sync_success(monkeypatch):
    monkeypatch.setattr(anon_query_agent, 'anonymize_query_for_logging', mock.AsyncMock(return_value='anon'))
    res = anon_query_agent.anonymize_query_sync('query')
    assert res == 'anon'

def test_anonymize_query_sync_error(monkeypatch):
    def raise_exc(*a, **k):
        raise Exception('fail')
    monkeypatch.setattr(anon_query_agent, 'anonymize_query_for_logging', raise_exc)
    res = anon_query_agent.anonymize_query_sync('query')
    assert res.startswith('query_received')
