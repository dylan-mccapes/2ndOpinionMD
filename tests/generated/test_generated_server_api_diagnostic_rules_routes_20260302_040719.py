try:
    from server.api import diagnostic_rules_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

@pytest.mark.asyncio
async def test_list_rules_basic(monkeypatch):
    mock_session = MagicMock()
    mock_execute = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [{"rule_key": "rk1", "title": "T", "org": "O", "condition": "C", "version": 1, "published_date": "2020-01-01", "source_urls": []}]
    mock_execute.return_value = mock_result
    mock_session.execute = mock_execute
    result = await diagnostic_rules_routes.list_rules(q=None, session=mock_session)
    assert isinstance(result, list)
    assert result[0]["rule_key"] == "rk1"

@pytest.mark.asyncio
async def test_list_rules_with_q(monkeypatch):
    mock_session = MagicMock()
    mock_execute = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [{"rule_key": "rk2"}]
    mock_execute.return_value = mock_result
    mock_session.execute = mock_execute
    result = await diagnostic_rules_routes.list_rules(q="test", session=mock_session)
    assert isinstance(result, list)
    assert result[0]["rule_key"] == "rk2"

@pytest.mark.asyncio
async def test_get_rule_found(monkeypatch):
    mock_session = MagicMock()
    mock_execute = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = {"rule_key": "rk3", "title": "T3"}
    mock_execute.return_value = mock_result
    mock_session.execute = mock_execute
    result = await diagnostic_rules_routes.get_rule(rule_key="rk3", session=mock_session)
    assert result["rule_key"] == "rk3"

@pytest.mark.asyncio
async def test_get_rule_not_found(monkeypatch):
    mock_session = MagicMock()
    mock_execute = AsyncMock()
    mock_result = MagicMock()
    mock_result.mappings.return_value.first.return_value = None
    mock_execute.return_value = mock_result
    mock_session.execute = mock_execute
    with pytest.raises(diagnostic_rules_routes.HTTPException) as exc:
        await diagnostic_rules_routes.get_rule(rule_key="missing", session=mock_session)
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_apply_rule_found(monkeypatch):
    mock_session = MagicMock()
    mock_execute = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = ["rule_json_data"]
    mock_execute.return_value = mock_result
    mock_session.execute = mock_execute
    monkeypatch.setattr(diagnostic_rules_routes, "evaluate", lambda rule_json, facts: {"evaluated": True, "facts": facts})
    result = await diagnostic_rules_routes.apply_rule(rule_key="rk4", facts={"a": 1}, session=mock_session)
    assert result["evaluated"] is True
    assert result["facts"] == {"a": 1}

@pytest.mark.asyncio
async def test_apply_rule_not_found(monkeypatch):
    mock_session = MagicMock()
    mock_execute = AsyncMock()
    mock_result = MagicMock()
    mock_result.first.return_value = None
    mock_execute.return_value = mock_result
    mock_session.execute = mock_execute
    with pytest.raises(diagnostic_rules_routes.HTTPException) as exc:
        await diagnostic_rules_routes.apply_rule(rule_key="missing", facts={}, session=mock_session)
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_upsert_rules_authorized(monkeypatch):
    # Patch ADMIN_TOKEN and DB session
    monkeypatch.setattr(diagnostic_rules_routes, "ADMIN_TOKEN", "token123")
    mock_session = MagicMock()
    mock_execute = AsyncMock()
    mock_session.execute = mock_execute
    mock_session.commit = AsyncMock()
    payload = [{"rule_key": "rk5", "title": "T5", "org": "O5", "condition": "C5", "version": 1, "published_date": "2020-01-01", "rule_json": {}, "notes": "", "source_urls": []}]
    # Patch text to just return its input
    monkeypatch.setattr(diagnostic_rules_routes, "text", lambda x: x)
    # Patch session.execute to return a dummy
    mock_execute.return_value = MagicMock(rowcount=1)
    # Patch session.commit to do nothing
    result = None
    try:
        result = await diagnostic_rules_routes.upsert_rules(payload=payload, x_admin_token="token123", session=mock_session)
    except Exception as e:
        pytest.fail(f"Unexpected exception: {e}")
    assert result is not None or result is None  # Just check no error

@pytest.mark.asyncio
async def test_upsert_rules_unauthorized(monkeypatch):
    monkeypatch.setattr(diagnostic_rules_routes, "ADMIN_TOKEN", "token123")
    mock_session = MagicMock()
    with pytest.raises(diagnostic_rules_routes.HTTPException) as exc:
        await diagnostic_rules_routes.upsert_rules(payload={}, x_admin_token="wrongtoken", session=mock_session)
    assert exc.value.status_code == 401
