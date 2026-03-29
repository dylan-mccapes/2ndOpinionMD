# AUTO-GENERATED TESTS FOR server/api/diagnostic_rules_routes.py
import pytest
try:
    from server.api import diagnostic_rules_routes
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

import sys
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.mark.asyncio
def test_list_rules_basic(monkeypatch):
    async def fake_execute(sql, params=None):
        class FakeResult:
            def mappings(self):
                class Mappings:
                    def all(self):
                        return [{"rule_key": "rk1", "title": "t1", "org": "o1", "condition": "c1", "version": 1, "published_date": "2020-01-01", "source_urls": []}]
                return Mappings()
        return FakeResult()
    session = MagicMock()
    session.execute = AsyncMock(side_effect=fake_execute)
    result = pytest.run(asyncio=True)(diagnostic_rules_routes.list_rules)(q=None, session=session)
    assert isinstance(result, list)
    assert result[0]["rule_key"] == "rk1"

@pytest.mark.asyncio
def test_list_rules_with_q(monkeypatch):
    async def fake_execute(sql, params=None):
        class FakeResult:
            def mappings(self):
                class Mappings:
                    def all(self):
                        return [{"rule_key": "rk2", "title": "t2", "org": "o2", "condition": "c2", "version": 2, "published_date": "2021-01-01", "source_urls": []}]
                return Mappings()
        return FakeResult()
    session = MagicMock()
    session.execute = AsyncMock(side_effect=fake_execute)
    result = pytest.run(asyncio=True)(diagnostic_rules_routes.list_rules)(q="test", session=session)
    assert isinstance(result, list)
    assert result[0]["rule_key"] == "rk2"

@pytest.mark.asyncio
def test_get_rule_found(monkeypatch):
    async def fake_execute(sql, params=None):
        class FakeResult:
            def mappings(self):
                class Mappings:
                    def first(self):
                        return {"rule_key": "rk1", "title": "t1", "org": "o1", "condition": "c1", "version": 1, "published_date": "2020-01-01", "rule_json": {}, "notes": "", "source_urls": []}
                return Mappings()
        return FakeResult()
    session = MagicMock()
    session.execute = AsyncMock(side_effect=fake_execute)
    result = pytest.run(asyncio=True)(diagnostic_rules_routes.get_rule)(rule_key="rk1", session=session)
    assert result["rule_key"] == "rk1"

@pytest.mark.asyncio
def test_get_rule_not_found(monkeypatch):
    async def fake_execute(sql, params=None):
        class FakeResult:
            def mappings(self):
                class Mappings:
                    def first(self):
                        return None
                return Mappings()
        return FakeResult()
    session = MagicMock()
    session.execute = AsyncMock(side_effect=fake_execute)
    with pytest.raises(Exception) as exc:
        pytest.run(asyncio=True)(diagnostic_rules_routes.get_rule)(rule_key="notfound", session=session)
    assert "not found" in str(exc.value).lower()

@pytest.mark.asyncio
def test_apply_rule_found(monkeypatch):
    async def fake_execute(sql, params=None):
        class FakeResult:
            def first(self):
                return ["rule_json_data"]
        return FakeResult()
    session = MagicMock()
    session.execute = AsyncMock(side_effect=fake_execute)
    monkeypatch.setattr(diagnostic_rules_routes, "evaluate", lambda rule_json, facts: {"result": True})
    result = pytest.run(asyncio=True)(diagnostic_rules_routes.apply_rule)(rule_key="rk1", facts={"a": 1}, session=session)
    assert result["result"] is True

@pytest.mark.asyncio
def test_apply_rule_not_found(monkeypatch):
    async def fake_execute(sql, params=None):
        class FakeResult:
            def first(self):
                return None
        return FakeResult()
    session = MagicMock()
    session.execute = AsyncMock(side_effect=fake_execute)
    with pytest.raises(Exception) as exc:
        pytest.run(asyncio=True)(diagnostic_rules_routes.apply_rule)(rule_key="notfound", facts={}, session=session)
    assert "not found" in str(exc.value).lower()

@pytest.mark.asyncio
def test_upsert_rules_authorized(monkeypatch):
    # Patch ADMIN_TOKEN and DB session
    monkeypatch.setattr(diagnostic_rules_routes, "ADMIN_TOKEN", "tok123")
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    payload = [{"rule_key": "rk1", "title": "t1", "org": "o1", "condition": "c1", "version": 1, "published_date": "2020-01-01", "rule_json": {}, "notes": "", "source_urls": []}]
    # Patch text to just return the SQL string
    monkeypatch.setattr(diagnostic_rules_routes, "text", lambda sql: sql)
    # Patch Body and Header to identity
    monkeypatch.setattr(diagnostic_rules_routes, "Body", lambda x: x)
    monkeypatch.setattr(diagnostic_rules_routes, "Header", lambda **kwargs: "tok123")
    # Patch HTTPException to raise
    monkeypatch.setattr(diagnostic_rules_routes, "HTTPException", Exception)
    # Patch get_session to return our session
    monkeypatch.setattr(diagnostic_rules_routes, "get_session", lambda: session)
    # Patch Depends to identity
    monkeypatch.setattr(diagnostic_rules_routes, "Depends", lambda x: x)
    # Call function
    try:
        pytest.run(asyncio=True)(diagnostic_rules_routes.upsert_rules)(payload=payload, x_admin_token="tok123", session=session)
    except Exception as e:
        # Should not raise
        assert False, f"Unexpected exception: {e}"

@pytest.mark.asyncio
def test_upsert_rules_unauthorized(monkeypatch):
    monkeypatch.setattr(diagnostic_rules_routes, "ADMIN_TOKEN", "tok123")
    session = MagicMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    payload = [{"rule_key": "rk1"}]
    monkeypatch.setattr(diagnostic_rules_routes, "Body", lambda x: x)
    monkeypatch.setattr(diagnostic_rules_routes, "Header", lambda **kwargs: "wrong")
    monkeypatch.setattr(diagnostic_rules_routes, "HTTPException", Exception)
    monkeypatch.setattr(diagnostic_rules_routes, "get_session", lambda: session)
    monkeypatch.setattr(diagnostic_rules_routes, "Depends", lambda x: x)
    with pytest.raises(Exception):
        pytest.run(asyncio=True)(diagnostic_rules_routes.upsert_rules)(payload=payload, x_admin_token="wrong", session=session)
