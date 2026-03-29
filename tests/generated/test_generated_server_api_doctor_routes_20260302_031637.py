import pytest
import sys
from unittest import mock

try:
    import pytest_asyncio
    from server.api import doctor_routes as dr
except ImportError:
    pytest.skip("server.api.doctor_routes not importable", allow_module_level=True)

@pytest.mark.asyncio
async def test_list_patients(monkeypatch):
    class DummyUser:
        id = 1
    class DummyPatient:
        id = 2
        email = "p@x.com"
        full_name = "Pat X"
        user_type = "patient"
    class DummyResult:
        def scalars(self):
            class DummyScalars:
                def all(self):
                    return [DummyPatient()]
            return DummyScalars()
    class DummyDB:
        async def execute(self, q):
            if hasattr(q, 'where'):
                return DummyResult()
            class DummyJr:
                def scalars(self):
                    class DummyScalars:
                        def first(self):
                            return None
                    return DummyScalars()
            return DummyJr()
    monkeypatch.setattr(dr, "_require_doctor", lambda u: None)
    monkeypatch.setattr(dr, "select", lambda *a, **k: mock.Mock(where=lambda *a, **k: mock.Mock()))
    monkeypatch.setattr(dr, "User", mock.Mock())
    monkeypatch.setattr(dr, "JournalEntry", mock.Mock())
    monkeypatch.setattr(dr, "func", mock.Mock())
    result = await dr.list_patients(current_user=DummyUser(), db=DummyDB())
    assert isinstance(result, list)

@pytest.mark.asyncio
async def test_get_patient_journal_not_found(monkeypatch):
    class DummyUser:
        id = 1
    class DummyDB:
        async def execute(self, q):
            class DummyResult:
                def scalar_one_or_none(self):
                    return None
            return DummyResult()
    monkeypatch.setattr(dr, "_require_doctor", lambda u: None)
    monkeypatch.setattr(dr, "select", lambda *a, **k: mock.Mock(where=lambda *a, **k: mock.Mock()))
    monkeypatch.setattr(dr, "User", mock.Mock())
    import uuid
    with pytest.raises(dr.HTTPException):
        await dr.get_patient_journal(patient_id=str(uuid.uuid4()), current_user=DummyUser(), db=DummyDB())

@pytest.mark.asyncio
async def test_get_patient_timeline_status_not_found(monkeypatch):
    class DummyUser:
        id = 1
    class DummyDB:
        async def execute(self, q):
            class DummyResult:
                def scalar_one_or_none(self):
                    return None
            return DummyResult()
    monkeypatch.setattr(dr, "_require_doctor", lambda u: None)
    monkeypatch.setattr(dr, "select", lambda *a, **k: mock.Mock(where=lambda *a, **k: mock.Mock()))
    monkeypatch.setattr(dr, "User", mock.Mock())
    import uuid
    with pytest.raises(dr.HTTPException):
        await dr.get_patient_timeline_status(patient_id=str(uuid.uuid4()), current_user=DummyUser(), db=DummyDB())

@pytest.mark.asyncio
async def test_invite_patient_self(monkeypatch):
    class DummyUser:
        id = 1
        email = "doc@x.com"
    class DummyBody:
        email = "doc@x.com"
    class DummyDB:
        pass
    monkeypatch.setattr(dr, "_require_doctor", lambda u: None)
    with pytest.raises(dr.HTTPException) as e:
        await dr.invite_patient(body=DummyBody(), background_tasks=None, request=None, current_user=DummyUser(), db=DummyDB())
    assert e.value.status_code == dr.status.HTTP_400_BAD_REQUEST

@pytest.mark.asyncio
async def test_get_pending_invites(monkeypatch):
    class DummyUser:
        id = 1
    class DummyInvite:
        id = 2
        to_email = "p@x.com"
        status = "pending"
        created_at = None
    class DummyResult:
        def scalars(self):
            class DummyScalars:
                def all(self):
                    return [DummyInvite()]
            return DummyScalars()
    class DummyDB:
        async def execute(self, q):
            return DummyResult()
    monkeypatch.setattr(dr, "_require_doctor", lambda u: None)
    monkeypatch.setattr(dr, "select", lambda *a, **k: mock.Mock(where=lambda *a, **k: mock.Mock(order_by=lambda *a, **k: mock.Mock())))
    monkeypatch.setattr(dr, "DoctorPatientInvite", mock.Mock())
    result = await dr.get_pending_invites(current_user=DummyUser(), db=DummyDB())
    assert isinstance(result, list)
    assert result[0]["to_email"] == "p@x.com"
