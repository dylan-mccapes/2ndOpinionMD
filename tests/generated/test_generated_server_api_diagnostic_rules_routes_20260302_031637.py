import pytest
import sys
from unittest import mock

try:
    import pytest_asyncio
    from server.api import diagnostic_rules_routes as dr
except ImportError:
    pytest.skip("server.api.diagnostic_rules_routes not importable", allow_module_level=True)

@pytest.mark.asyncio
async def test_list_rules_basic(monkeypatch):
    class DummySession:
        async def execute(self, sql, params=None):
            class DummyRes:
                def mappings(self):
                    class DummyMap:
                        def all(self):
                            return [{"rule_key": "rk1", "title": "t1", "org": "o", "condition": "c", "version": 1, "published_date": "2024-01-01", "source_urls": []}]
                    return DummyMap()
            return DummyRes()
    result = await dr.list_rules(q=None, session=DummySession())
    assert isinstance(result, list)
    assert result[0]["rule_key"] == "rk1"

@pytest.mark.asyncio
async def test_list_rules_with_q(monkeypatch):
    class DummySession:
        async def execute(self, sql, params=None):
            class DummyRes:
                def mappings(self):
                    class DummyMap:
                        def all(self):
                            return [{"rule_key": "rk2"}]
                    return DummyMap()
            return DummyRes()
    result = await dr.list_rules(q="test", session=DummySession())
    assert result[0]["rule_key"] == "rk2"

@pytest.mark.asyncio
async def test_get_rule_found(monkeypatch):
    class DummySession:
        async def execute(self, sql, params):
            class DummyRes:
                def mappings(self):
                    class DummyMap:
                        def first(self):
                            return {"rule_key": "rk1", "title": "t1"}
                    return DummyMap()
            return DummyRes()
    result = await dr.get_rule(rule_key="rk1", session=DummySession())
    assert result["rule_key"] == "rk1"

@pytest.mark.asyncio
async def test_get_rule_not_found(monkeypatch):
    class DummySession:
        async def execute(self, sql, params):
            class DummyRes:
                def mappings(self):
                    class DummyMap:
                        def first(self):
                            return None
                    return DummyMap()
            return DummyRes()
    with pytest.raises(dr.HTTPException) as e:
        await dr.get_rule(rule_key="missing", session=DummySession())
    assert e.value.status_code == 404

@pytest.mark.asyncio
async def test_apply_rule_found(monkeypatch):
    class DummySession:
        async def execute(self, sql, params):
            class DummyRes:
                def first(self):
                    return ["rule_json_data"]
            return DummyRes()
    monkeypatch.setattr(dr, "evaluate", lambda rule_json, facts: {"result": "ok", "input": facts})
    result = await dr.apply_rule(rule_key="rk1", facts={"a": 1}, session=DummySession())
    assert result["input"] == {"a": 1}

@pytest.mark.asyncio
async def test_apply_rule_not_found(monkeypatch):
    class DummySession:
        async def execute(self, sql, params):
            class DummyRes:
                def first(self):
                    return None
            return DummyRes()
    with pytest.raises(dr.HTTPException) as e:
        await dr.apply_rule(rule_key="missing", facts={}, session=DummySession())
    assert e.value.status_code == 404

@pytest.mark.asyncio
async def test_upsert_rules_unauthorized(monkeypatch):
    monkeypatch.setattr(dr, "ADMIN_TOKEN", "SECRET")
    class DummySession:
        pass
    with pytest.raises(dr.HTTPException) as e:
        await dr.upsert_rules(payload={}, x_admin_token="WRONG", session=DummySession())
    assert e.value.status_code == 401
