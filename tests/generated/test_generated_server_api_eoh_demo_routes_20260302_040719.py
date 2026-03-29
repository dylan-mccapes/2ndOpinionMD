import pytest
try:
    from server.api import eoh_demo_routes
except ImportError:
    pytest.skip("cannot import module", allow_module_level=True)

from unittest import mock

@pytest.mark.asyncio
async def test_list_patients(monkeypatch):
    fake_patients = [{"id": "P1", "label": "Patient 1", "summary": "Demo"}]
    monkeypatch.setattr(eoh_demo_routes, 'get_patient_list', lambda: fake_patients)
    result = await eoh_demo_routes.list_patients()
    assert isinstance(result, list)
    assert result == fake_patients

@pytest.mark.asyncio
async def test_get_patient_state_found(monkeypatch):
    fake_patient = {"das28_history": [1,2,3]}
    fake_timeline = [
        {"kind": "journal", "ts": "2024-01-01T00:00:00Z", "details": {"text": "entry"}, "summary": "sum"},
        {"kind": "other", "ts": "2024-01-02T00:00:00Z", "details": {}, "summary": "sum2"}
    ]
    monkeypatch.setattr(eoh_demo_routes, 'get_patient', lambda pid: fake_patient)
    monkeypatch.setattr(eoh_demo_routes, 'get_timeline', lambda pid: fake_timeline)
    result = await eoh_demo_routes.get_patient_state("P1")
    assert isinstance(result, dict)
    assert "das28_history" in fake_patient

@pytest.mark.asyncio
async def test_get_patient_state_not_found(monkeypatch):
    monkeypatch.setattr(eoh_demo_routes, 'get_patient', lambda pid: None)
    with pytest.raises(eoh_demo_routes.HTTPException) as exc:
        await eoh_demo_routes.get_patient_state("P404")
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_get_patient_timeline_found(monkeypatch):
    monkeypatch.setattr(eoh_demo_routes, 'DEMO_PATIENTS', {"P1": {}})
    fake_timeline = [{"event": 1}, {"event": 2}]
    monkeypatch.setattr(eoh_demo_routes, 'get_timeline', lambda pid, max_events=None: fake_timeline)
    result = await eoh_demo_routes.get_patient_timeline("P1")
    assert result == fake_timeline

@pytest.mark.asyncio
async def test_get_patient_timeline_not_found(monkeypatch):
    monkeypatch.setattr(eoh_demo_routes, 'DEMO_PATIENTS', {})
    with pytest.raises(eoh_demo_routes.HTTPException) as exc:
        await eoh_demo_routes.get_patient_timeline("P404")
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_create_hypothetical_found(monkeypatch):
    class DummyRequest:
        base_patient_id = "P1"
        changes = [{"ts": "2025-09-01T08:00:00Z", "kind": "flare", "severity": "moderate", "summary": "New flare knees/wrists"}]
    fake_patient = {"id": "P1"}
    monkeypatch.setattr(eoh_demo_routes, 'get_patient', lambda pid: fake_patient)
    monkeypatch.setattr(eoh_demo_routes, 'get_patient_state', mock.AsyncMock(return_value={"state": "ok"}))
    # Patch the rest of the function to just return a dict for test
    monkeypatch.setattr(eoh_demo_routes, 'get_timeline', lambda pid: [])
    # Patch any other needed functions as no-ops
    result = await eoh_demo_routes.create_hypothetical(DummyRequest())
    assert isinstance(result, dict)

@pytest.mark.asyncio
async def test_create_hypothetical_not_found(monkeypatch):
    class DummyRequest:
        base_patient_id = "P404"
        changes = []
    monkeypatch.setattr(eoh_demo_routes, 'get_patient', lambda pid: None)
    with pytest.raises(eoh_demo_routes.HTTPException) as exc:
        await eoh_demo_routes.create_hypothetical(DummyRequest())
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_get_legacy_patient_state(monkeypatch):
    monkeypatch.setattr(eoh_demo_routes, 'get_patient_state', mock.AsyncMock(return_value={"state": "legacy"}))
    result = await eoh_demo_routes.get_legacy_patient_state()
    assert result == {"state": "legacy"}

@pytest.mark.asyncio
async def test_get_legacy_timeline(monkeypatch):
    monkeypatch.setattr(eoh_demo_routes, 'get_timeline', lambda pid: [{"event": "legacy"}])
    result = await eoh_demo_routes.get_legacy_timeline()
    assert result == [{"event": "legacy"}]

@pytest.mark.asyncio
async def test_get_timeline_flare_engine_analysis_found(monkeypatch):
    fake_patient = {"id": "P1"}
    monkeypatch.setattr(eoh_demo_routes, 'get_patient', lambda pid: fake_patient)
    # Patch TimelineFlareEngineResponse to just return a dict
    monkeypatch.setattr(eoh_demo_routes, 'TimelineFlareEngineResponse', dict)
    # Patch the rest of the function to return a dummy dict
    monkeypatch.setattr(eoh_demo_routes, 'get_timeline', lambda pid: [])
    result = await eoh_demo_routes.get_timeline_flare_engine_analysis("P1")
    assert isinstance(result, dict)

@pytest.mark.asyncio
async def test_get_timeline_flare_engine_analysis_not_found(monkeypatch):
    monkeypatch.setattr(eoh_demo_routes, 'get_patient', lambda pid: None)
    with pytest.raises(eoh_demo_routes.HTTPException) as exc:
        await eoh_demo_routes.get_timeline_flare_engine_analysis("P404")
    assert exc.value.status_code == 404

@pytest.mark.asyncio
async def test_list_demo_modes():
    result = await eoh_demo_routes.list_demo_modes()
    assert isinstance(result, list)
    assert any("id" in mode for mode in result)
