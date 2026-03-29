try:
    from server.api import doctor_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.mark.asyncio
async def test_list_patients(monkeypatch):
    mock_user = MagicMock()
    mock_user.id = "docid"
    mock_user.user_type = "doctor"
    # Patch _require_doctor to do nothing
    monkeypatch.setattr(doctor_routes, "_require_doctor", lambda u: None)
    # Patch User and JournalEntry
    monkeypatch.setattr(doctor_routes, "User", MagicMock())
    monkeypatch.setattr(doctor_routes, "JournalEntry", MagicMock())
    # Patch select to return a dummy query
    monkeypatch.setattr(doctor_routes, "select", lambda *a, **k: "query")
    # Patch db.execute to return patients
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_patient = MagicMock()
    mock_patient.id = "patid"
    mock_patient.email = "pat@example.com"
    mock_patient.full_name = "Pat Name"
    mock_patient.user_type = "patient"
    mock_result.scalars.return_value.all.return_value = [mock_patient]
    mock_db.execute = AsyncMock(return_value=mock_result)
    # Patch func.max
    monkeypatch.setattr(doctor_routes, "func", MagicMock())
    # Patch JournalEntry.created_at
    monkeypatch.setattr(doctor_routes.JournalEntry, "created_at", MagicMock())
    # Patch db.execute for journal query
    mock_db.execute = AsyncMock(side_effect=[mock_result, mock_result])
    result = await doctor_routes.list_patients(current_user=mock_user, db=mock_db)
    assert isinstance(result, list)
    assert result[0]["email"] == "pat@example.com"

@pytest.mark.asyncio
async def test_get_patient_journal_not_found(monkeypatch):
    mock_user = MagicMock()
    mock_user.id = "docid"
    monkeypatch.setattr(doctor_routes, "_require_doctor", lambda u: None)
    monkeypatch.setattr(doctor_routes, "User", MagicMock())
    monkeypatch.setattr(doctor_routes, "select", lambda *a, **k: "query")
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    import uuid
    bad_id = "not-a-uuid"
    with pytest.raises(doctor_routes.HTTPException):
        await doctor_routes.get_patient_journal(patient_id=bad_id, current_user=mock_user, db=mock_db)

@pytest.mark.asyncio
async def test_get_patient_timeline_status_not_found(monkeypatch):
    mock_user = MagicMock()
    mock_user.id = "docid"
    monkeypatch.setattr(doctor_routes, "_require_doctor", lambda u: None)
    monkeypatch.setattr(doctor_routes, "User", MagicMock())
    monkeypatch.setattr(doctor_routes, "select", lambda *a, **k: "query")
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute = AsyncMock(return_value=mock_result)
    import uuid
    bad_id = "not-a-uuid"
    with pytest.raises(doctor_routes.HTTPException):
        await doctor_routes.get_patient_timeline_status(patient_id=bad_id, current_user=mock_user, db=mock_db)

@pytest.mark.asyncio
async def test_invite_patient_self(monkeypatch):
    mock_user = MagicMock()
    mock_user.id = "docid"
    mock_user.email = "doc@example.com"
    monkeypatch.setattr(doctor_routes, "_require_doctor", lambda u: None)
    body = MagicMock()
    body.email = "doc@example.com"
    mock_db = MagicMock()
    with pytest.raises(doctor_routes.HTTPException) as exc:
        await doctor_routes.invite_patient(body=body, background_tasks=None, request=None, current_user=mock_user, db=mock_db)
    assert exc.value.status_code == 400

@pytest.mark.asyncio
async def test_get_pending_invites(monkeypatch):
    mock_user = MagicMock()
    mock_user.id = "docid"
    monkeypatch.setattr(doctor_routes, "_require_doctor", lambda u: None)
    monkeypatch.setattr(doctor_routes, "DoctorPatientInvite", MagicMock())
    monkeypatch.setattr(doctor_routes, "select", lambda *a, **k: "query")
    mock_db = MagicMock()
    mock_result = MagicMock()
    mock_invite = MagicMock()
    mock_invite.id = "iid"
    mock_invite.to_email = "pat@example.com"
    mock_invite.status = "pending"
    mock_invite.created_at = None
    mock_result.scalars.return_value.all.return_value = [mock_invite]
    mock_db.execute = AsyncMock(return_value=mock_result)
    result = await doctor_routes.get_pending_invites(current_user=mock_user, db=mock_db)
    assert isinstance(result, list)
    assert result[0]["to_email"] == "pat@example.com"
