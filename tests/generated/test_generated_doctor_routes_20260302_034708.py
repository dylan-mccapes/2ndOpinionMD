try:
    import pytest
    from server.api import doctor_routes
except ImportError:
    import pytest; pytest.skip("cannot import module", allow_module_level=True)
from unittest.mock import AsyncMock, MagicMock, patch
import sys

pytestmark = pytest.mark.asyncio

@pytest.fixture(autouse=True)
def skip_if_no_asyncio():
    try:
        import pytest_asyncio
    except ImportError:
        pytest.skip("pytest-asyncio not installed", allow_module_level=True)

# list_patients
@pytest.mark.asyncio
async def test_list_patients_returns_list(monkeypatch):
    fake_user = MagicMock()
    fake_user.id = "doctorid"
    fake_user.user_type = "doctor"
    fake_db = MagicMock()
    fake_patient = MagicMock()
    fake_patient.id = "pid"
    fake_patient.email = "p@x.com"
    fake_patient.full_name = "Pat X"
    fake_patient.user_type = "patient"
    fake_patient.doctor_id = fake_user.id
    fake_db.execute = AsyncMock(side_effect=[MagicMock(scalars=lambda: MagicMock(all=lambda: [fake_patient])), MagicMock(scalars=lambda: MagicMock(all=lambda: [None]))])
    monkeypatch.setattr(doctor_routes, "_require_doctor", lambda u: None)
    monkeypatch.setattr(doctor_routes, "select", lambda *a, **k: None)
    monkeypatch.setattr(doctor_routes, "User", MagicMock())
    monkeypatch.setattr(doctor_routes, "JournalEntry", MagicMock())
    monkeypatch.setattr(doctor_routes, "func", MagicMock())
    result = await doctor_routes.list_patients(current_user=fake_user, db=fake_db)
    assert isinstance(result, list)

# get_patient_journal
@pytest.mark.asyncio
async def test_get_patient_journal_not_found(monkeypatch):
    fake_user = MagicMock()
    fake_user.id = "doctorid"
    fake_user.user_type = "doctor"
    fake_db = MagicMock()
    monkeypatch.setattr(doctor_routes, "_require_doctor", lambda u: None)
    monkeypatch.setattr(doctor_routes, "select", lambda *a, **k: None)
    monkeypatch.setattr(doctor_routes, "User", MagicMock())
    import uuid
    # Patch db.execute to return .scalar_one_or_none() as None
    fake_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
    with pytest.raises(doctor_routes.HTTPException) as e:
        await doctor_routes.get_patient_journal(str(uuid.uuid4()), current_user=fake_user, db=fake_db)
    assert e.value.status_code == 404

# get_patient_timeline_status
@pytest.mark.asyncio
async def test_get_patient_timeline_status_not_found(monkeypatch):
    fake_user = MagicMock()
    fake_user.id = "doctorid"
    fake_user.user_type = "doctor"
    fake_db = MagicMock()
    monkeypatch.setattr(doctor_routes, "_require_doctor", lambda u: None)
    monkeypatch.setattr(doctor_routes, "select", lambda *a, **k: None)
    monkeypatch.setattr(doctor_routes, "User", MagicMock())
    import uuid
    fake_db.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
    with pytest.raises(doctor_routes.HTTPException) as e:
        await doctor_routes.get_patient_timeline_status(str(uuid.uuid4()), current_user=fake_user, db=fake_db)
    assert e.value.status_code == 404

# invite_patient
@pytest.mark.asyncio
async def test_invite_patient_cannot_invite_self(monkeypatch):
    fake_user = MagicMock()
    fake_user.id = "doctorid"
    fake_user.user_type = "doctor"
    fake_user.email = "doc@x.com"
    fake_body = MagicMock()
    fake_body.email = "doc@x.com"
    monkeypatch.setattr(doctor_routes, "_require_doctor", lambda u: None)
    with pytest.raises(doctor_routes.HTTPException) as e:
        await doctor_routes.invite_patient(body=fake_body, background_tasks=None, request=None, current_user=fake_user, db=None)
    assert e.value.status_code == 400

# get_pending_invites
@pytest.mark.asyncio
async def test_get_pending_invites_returns_list(monkeypatch):
    fake_user = MagicMock()
    fake_user.id = "doctorid"
    fake_user.user_type = "doctor"
    fake_db = MagicMock()
    fake_invite = MagicMock()
    fake_invite.id = "iid"
    fake_invite.to_email = "p@x.com"
    fake_invite.status = "pending"
    fake_invite.created_at = None
    fake_invite.expires_at = None
    fake_db.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [fake_invite])))
    monkeypatch.setattr(doctor_routes, "_require_doctor", lambda u: None)
    monkeypatch.setattr(doctor_routes, "select", lambda *a, **k: None)
    monkeypatch.setattr(doctor_routes, "DoctorPatientInvite", MagicMock())
    result = await doctor_routes.get_pending_invites(current_user=fake_user, db=fake_db)
    assert isinstance(result, list)
    assert result[0]["id"] == "iid"
