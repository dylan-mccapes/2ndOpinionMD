try:
    import pytest
    from unittest import mock
    from server.api import anon_query_agent
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)

@pytest.mark.asyncio
async def test_anonymize_query_for_logging_success(monkeypatch):
    async def fake_chat_completion_async(**kwargs):
        class FakeResp:
            content = 'anonymized'
        return {'choices': [{'message': {'content': 'anonymized'}}]}
    monkeypatch.setattr(anon_query_agent, 'chat_completion_async', fake_chat_completion_async)
    monkeypatch.setattr(anon_query_agent, 'ANONYMIZATION_SYSTEM_PROMPT', 'prompt')
    result = await anon_query_agent.anonymize_query_for_logging('query')
    assert 'anonymized' in result

@pytest.mark.asyncio
async def test_anonymize_query_for_logging_timeout(monkeypatch):
    async def raise_timeout(*a, **kw):
        import asyncio
        raise asyncio.TimeoutError()
    monkeypatch.setattr(anon_query_agent, 'chat_completion_async', raise_timeout)
    monkeypatch.setattr(anon_query_agent, 'ANONYMIZATION_SYSTEM_PROMPT', 'prompt')
    result = await anon_query_agent.anonymize_query_for_logging('query')
    assert 'query_received' in result

def test_anonymize_query_sync_success(monkeypatch):
    monkeypatch.setattr(anon_query_agent, 'anonymize_query_for_logging', mock.AsyncMock(return_value='anon'))
    result = anon_query_agent.anonymize_query_sync('query')
    assert 'anon' in result

def test_anonymize_query_sync_exception(monkeypatch):
    monkeypatch.setattr(anon_query_agent, 'anonymize_query_for_logging', mock.AsyncMock(side_effect=Exception('fail')))
    monkeypatch.setattr(anon_query_agent, 'logger', mock.Mock())
    result = anon_query_agent.anonymize_query_sync('query')
    assert 'sync_anonymization_error' in result
