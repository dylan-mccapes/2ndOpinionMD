# Auto-generated tests for server.api.diagnostic_rules_routes
import pytest
import sys
from unittest import mock

try:
    import asyncio
    import pytest_asyncio
    from server.api import diagnostic_rules_routes as mod
except ImportError:
    mod = None

pytestmark = pytest.mark.asyncio

@pytest.mark.asyncio
async def test_list_rules(monkeypatch):
    if mod is None:
        pytest.skip('server.api.diagnostic_rules_routes not importable')
    # Mock session.execute to return a dummy result
    class DummyResult:
        def mappings(self):
            class DummyMappings:
                def all(self):
                    return [{
                        'rule_key': 'rk', 'title': 't', 'org': 'o', 'condition': 'c',
                        'version': 1, 'published_date': '2020-01-01', 'source_urls': []
                    }]
            return DummyMappings()
    async def dummy_execute(sql, params=None):
        return DummyResult()
    monkeypatch.setattr(mod, 'text', lambda x: x)
    session = mock.Mock()
    session.execute = dummy_execute
    result = await mod.list_rules(q=None, session=session)
    assert isinstance(result, list)
    assert 'rule_key' in result[0]

@pytest.mark.asyncio
async def test_list_rules_with_q(monkeypatch):
    if mod is None:
        pytest.skip('server.api.diagnostic_rules_routes not importable')
    class DummyResult:
        def mappings(self):
            class DummyMappings:
                def all(self):
                    return [{
                        'rule_key': 'rk2', 'title': 't2', 'org': 'o2', 'condition': 'c2',
                        'version': 2, 'published_date': '2021-01-01', 'source_urls': ['url']
                    }]
            return DummyMappings()
    async def dummy_execute(sql, params=None):
        return DummyResult()
    monkeypatch.setattr(mod, 'text', lambda x: x)
    session = mock.Mock()
    session.execute = dummy_execute
    result = await mod.list_rules(q='test', session=session)
    assert isinstance(result, list)
    assert result[0]['rule_key'] == 'rk2'

@pytest.mark.asyncio
async def test_get_rule_found(monkeypatch):
    if mod is None:
        pytest.skip('server.api.diagnostic_rules_routes not importable')
    class DummyResult:
        def mappings(self):
            class DummyMappings:
                def first(self):
                    return {
                        'rule_key': 'rk', 'title': 't', 'org': 'o', 'condition': 'c',
                        'version': 1, 'published_date': '2020-01-01', 'rule_json': {},
                        'notes': '', 'source_urls': []
                    }
            return DummyMappings()
    async def dummy_execute(sql, params=None):
        return DummyResult()
    monkeypatch.setattr(mod, 'text', lambda x: x)
    session = mock.Mock()
    session.execute = dummy_execute
    result = await mod.get_rule(rule_key='rk', session=session)
    assert isinstance(result, dict)
    assert result['rule_key'] == 'rk'

@pytest.mark.asyncio
async def test_get_rule_not_found(monkeypatch):
    if mod is None:
        pytest.skip('server.api.diagnostic_rules_routes not importable')
    class DummyResult:
        def mappings(self):
            class DummyMappings:
                def first(self):
                    return None
            return DummyMappings()
    async def dummy_execute(sql, params=None):
        return DummyResult()
    monkeypatch.setattr(mod, 'text', lambda x: x)
    session = mock.Mock()
    session.execute = dummy_execute
    with pytest.raises(mod.HTTPException) as exc:
        await mod.get_rule(rule_key='notfound', session=session)
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_apply_rule_found(monkeypatch):
    if mod is None:
        pytest.skip('server.api.diagnostic_rules_routes not importable')
    class DummyResult:
        def first(self):
            return [{'rule_json': {'a': 1}}][0]
    async def dummy_execute(sql, params=None):
        return DummyResult()
    monkeypatch.setattr(mod, 'text', lambda x: x)
    session = mock.Mock()
    session.execute = dummy_execute
    monkeypatch.setattr(mod, 'evaluate', lambda rule_json, facts: {'result': 42})
    result = await mod.apply_rule(rule_key='rk', facts={'x': 1}, session=session)
    assert result == {'result': 42}

@pytest.mark.asyncio
async def test_apply_rule_not_found(monkeypatch):
    if mod is None:
        pytest.skip('server.api.diagnostic_rules_routes not importable')
    class DummyResult:
        def first(self):
            return None
    async def dummy_execute(sql, params=None):
        return DummyResult()
    monkeypatch.setattr(mod, 'text', lambda x: x)
    session = mock.Mock()
    session.execute = dummy_execute
    with pytest.raises(mod.HTTPException) as exc:
        await mod.apply_rule(rule_key='notfound', facts={}, session=session)
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_upsert_rules_authorized(monkeypatch):
    if mod is None:
        pytest.skip('server.api.diagnostic_rules_routes not importable')
    # Patch ADMIN_TOKEN
    monkeypatch.setattr(mod, 'ADMIN_TOKEN', 'admintoken')
    # Patch session.execute and session.commit
    async def dummy_execute(sql, params=None):
        class DummyResult:
            def rowcount(self):
                return 1
        return DummyResult()
    async def dummy_commit():
        return None
    session = mock.Mock()
    session.execute = dummy_execute
    session.commit = dummy_commit
    monkeypatch.setattr(mod, 'text', lambda x: x)
    # Patch Body to just pass through
    monkeypatch.setattr(mod, 'Body', lambda x: x)
    # Provide minimal payload
    payload = [{
        'rule_key': 'rk', 'title': 't', 'org': 'o', 'condition': 'c',
        'version': 1, 'published_date': '2020-01-01', 'rule_json': {},
        'notes': '', 'source_urls': []
    }]
    # Patch Header to just pass through
    monkeypatch.setattr(mod, 'Header', lambda **kwargs: kwargs.get('default', None))
    # Should not raise
    try:
        await mod.upsert_rules(payload=payload, x_admin_token='admintoken', session=session)
    except Exception as e:
        pytest.fail(f'upsert_rules raised: {e}')

@pytest.mark.asyncio
async def test_upsert_rules_unauthorized(monkeypatch):
    if mod is None:
        pytest.skip('server.api.diagnostic_rules_routes not importable')
    monkeypatch.setattr(mod, 'ADMIN_TOKEN', 'admintoken')
    session = mock.Mock()
    monkeypatch.setattr(mod, 'Body', lambda x: x)
    monkeypatch.setattr(mod, 'Header', lambda **kwargs: kwargs.get('default', None))
    with pytest.raises(mod.HTTPException) as exc:
        await mod.upsert_rules(payload={}, x_admin_token='wrongtoken', session=session)
    assert exc.value.status_code == 401
