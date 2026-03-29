import pytest
try:
    from server.api import anon_query_agent
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)
from unittest.mock import patch, AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_anonymize_query_for_logging_success(monkeypatch):
    # Patch chat_completion_async to return a dummy response
    dummy_response = MagicMock()
    dummy_response.choices = [MagicMock(message={"content": "anonymized"})]
    monkeypatch.setattr(anon_query_agent, 'chat_completion_async', AsyncMock(return_value=dummy_response))
    # Patch ANONYMIZATION_SYSTEM_PROMPT if needed
    if not hasattr(anon_query_agent, 'ANONYMIZATION_SYSTEM_PROMPT'):
        monkeypatch.setattr(anon_query_agent, 'ANONYMIZATION_SYSTEM_PROMPT', 'prompt')
    result = await anon_query_agent.anonymize_query_for_logging("Sensitive query", timeout=0.1)
    assert isinstance(result, str)
    assert result == "anonymized"

@pytest.mark.asyncio
async def test_anonymize_query_for_logging_timeout(monkeypatch):
    # Patch chat_completion_async to never return
    import asyncio
    async def never_return(*a, **kw):
        await asyncio.sleep(0.2)
    monkeypatch.setattr(anon_query_agent, 'chat_completion_async', never_return)
    if not hasattr(anon_query_agent, 'ANONYMIZATION_SYSTEM_PROMPT'):
        monkeypatch.setattr(anon_query_agent, 'ANONYMIZATION_SYSTEM_PROMPT', 'prompt')
    result = await anon_query_agent.anonymize_query_for_logging("Sensitive query", timeout=0.01)
    assert result.startswith("query_received")


def test_anonymize_query_sync_success(monkeypatch):
    monkeypatch.setattr(anon_query_agent, 'anonymize_query_for_logging', AsyncMock(return_value="anon"))
    result = anon_query_agent.anonymize_query_sync("Sensitive query")
    assert result == "anon"

def test_anonymize_query_sync_exception(monkeypatch):
    def raise_exc(q):
        raise RuntimeError("fail")
    monkeypatch.setattr(anon_query_agent, 'anonymize_query_for_logging', raise_exc)
    # Patch logger
    monkeypatch.setattr(anon_query_agent, 'logger', MagicMock())
    result = anon_query_agent.anonymize_query_sync("Sensitive query")
    assert result.startswith("query_received")
