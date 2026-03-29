import pytest
from unittest import mock

try:
    import server.api.eoh_demo_routes as eoh_demo_routes
except ImportError:
    pytest.skip('server.api.eoh_demo_routes could not be imported', allow_module_level=True)

import pytest_asyncio

@pytest.mark.asyncio
async def test_list_patients(monkeypatch):
    dummy_list = [{'id': 'P1', 'label': 'Patient 1', 'summary': 'Demo'}]
    monkeypatch.setattr(eoh_demo_routes, 'get_patient_list', lambda: dummy_list)
    result = await eoh_demo_routes.list_patients()
    assert isinstance(result, list)
    assert result == dummy_list

@pytest.mark.asyncio
async def test_get_patient_state_found(monkeypatch):
    dummy_patient = {'das28_history': [1,2,3]}
    dummy_timeline = [
        {'kind': 'journal', 'ts': '2024-01-01T00:00:00Z', 'details': {'text': 'entry'}, 'summary': 'sum'}
    ]
    monkeypatch.setattr(eoh_demo_routes, 'get_patient', lambda pid: dummy_patient)
    monkeypatch.setattr(eoh_demo_routes, 'get_timeline', lambda pid: dummy_timeline)
    result = await eoh_demo_routes.get_patient_state('P1')
    assert isinstance(result, dict)
    assert 'das28_history' in result or 'recent_das28' in result

@pytest.mark.asyncio
async def test_get_patient_state_not_found(monkeypatch):
    monkeypatch.setattr(eoh_demo_routes, 'get_patient', lambda pid: None)
    with pytest.raises(eoh_demo_routes.HTTPException) as exc:
        await eoh_demo_routes.get_patient_state('P404')
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_get_patient_timeline_found(monkeypatch):
    monkeypatch.setattr(eoh_demo_routes, 'DEMO_PATIENTS', {'P1': {}})
    dummy_timeline = [{'kind': 'event'}]
    monkeypatch.setattr(eoh_demo_routes, 'get_timeline', lambda pid, max_events=200: dummy_timeline)
    result = await eoh_demo_routes.get_patient_timeline('P1')
    assert isinstance(result, list)
    assert result == dummy_timeline

@pytest.mark.asyncio
async def test_get_patient_timeline_not_found(monkeypatch):
    monkeypatch.setattr(eoh_demo_routes, 'DEMO_PATIENTS', {})
    with pytest.raises(eoh_demo_routes.HTTPException) as exc:
        await eoh_demo_routes.get_patient_timeline('P404')
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_create_hypothetical_found(monkeypatch):
    class DummyRequest:
        base_patient_id = 'P1'
        changes = [{'ts': '2025-09-01T08:00:00Z', 'kind': 'flare', 'severity': 'moderate', 'summary': 'New flare'}]
    dummy_patient = {'id': 'P1'}
    monkeypatch.setattr(eoh_demo_routes, 'get_patient', lambda pid: dummy_patient)
    monkeypatch.setattr(eoh_demo_routes, 'get_timeline', lambda pid: [])
    monkeypatch.setattr(eoh_demo_routes, 'apply_changes_to_patient', lambda p, c: {'changed': True})
    result = await eoh_demo_routes.create_hypothetical(DummyRequest())
    assert isinstance(result, dict)
    assert 'changed' in result

@pytest.mark.asyncio
async def test_create_hypothetical_not_found(monkeypatch):
    class DummyRequest:
        base_patient_id = 'P404'
        changes = []
    monkeypatch.setattr(eoh_demo_routes, 'get_patient', lambda pid: None)
    with pytest.raises(eoh_demo_routes.HTTPException) as exc:
        await eoh_demo_routes.create_hypothetical(DummyRequest())
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_get_legacy_patient_state(monkeypatch):
    async def dummy_get_patient_state(pid):
        return {'id': pid}
    monkeypatch.setattr(eoh_demo_routes, 'get_patient_state', dummy_get_patient_state)
    result = await eoh_demo_routes.get_legacy_patient_state()
    assert result['id'] == 'P1'

@pytest.mark.asyncio
async def test_get_legacy_timeline(monkeypatch):
    dummy_timeline = [{'kind': 'event'}]
    monkeypatch.setattr(eoh_demo_routes, 'get_timeline', lambda pid: dummy_timeline)
    result = await eoh_demo_routes.get_legacy_timeline()
    assert result == dummy_timeline

@pytest.mark.asyncio
async def test_get_timeline_flare_engine_analysis_found(monkeypatch):
    dummy_patient = {'id': 'P1'}
    monkeypatch.setattr(eoh_demo_routes, 'get_patient', lambda pid: dummy_patient)
    dummy_response = mock.Mock()
    monkeypatch.setattr(eoh_demo_routes, 'TimelineFlareEngineResponse', lambda **kwargs: dummy_response)
    monkeypatch.setattr(eoh_demo_routes, 'analyze_flare_engine', lambda pid, window_days: {'result': True})
    result = await eoh_demo_routes.get_timeline_flare_engine_analysis('P1')
    assert result is dummy_response

@pytest.mark.asyncio
async def test_get_timeline_flare_engine_analysis_not_found(monkeypatch):
    monkeypatch.setattr(eoh_demo_routes, 'get_patient', lambda pid: None)
    with pytest.raises(eoh_demo_routes.HTTPException) as exc:
        await eoh_demo_routes.get_timeline_flare_engine_analysis('P404')
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_list_demo_modes():
    result = await eoh_demo_routes.list_demo_modes()
    assert isinstance(result, list)
    assert any('id' in mode for mode in result)
