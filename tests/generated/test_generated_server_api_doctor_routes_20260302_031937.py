# Auto-generated tests for server.api.doctor_routes
import pytest
import sys
from unittest import mock

try:
    import asyncio
    import pytest_asyncio
    from server.api import doctor_routes as mod
except ImportError:
    mod = None

pytestmark = pytest.mark.asyncio

@pytest.mark.asyncio
async def test_list_patients(monkeypatch):
    if mod is None:
        pytest.skip('server.api.doctor_routes not importable')
    # Patch _require_doctor to do nothing
    monkeypatch.setattr(mod, '_require_doctor', lambda user: None)
    # Patch select and User
    monkeypatch.setattr(mod, 'select', lambda *a, **kw: 'query')
    monkeypatch.setattr(mod, 'User', type('User', (), {'doctor_id': 1, 'user_type': 'patient'}) )
    # Patch db.execute to return dummy patients
    class DummyResult:
        def scalars(self):
            class DummyScalars:
                def all(self):
                    class DummyPatient:
                        id = 'pid1'
                        email = 'pat@example.com'
                        full_name = 'Pat Example'
                        user_type = 'patient'
                        doctor_id = 1
                    return [DummyPatient()]
            return DummyScalars()
    async def dummy_execute(q):
        return DummyResult()
    db = mock.Mock()
    db.execute = dummy_execute
    # Patch func.max and JournalEntry
    monkeypatch.setattr(mod, 'func', mock.Mock())
    monkeypatch.setattr(mod, 'JournalEntry', type('JournalEntry', (), {'created_at': None, 'user_id': None}))
    # Patch journal query
    class DummyJr:
        def scalars(self):
            class DummyScalars:
                def first(self):
                    return None
            return DummyScalars()
    async def dummy_journal_execute(q):
        return DummyJr()
    db.execute = mock.AsyncMock(side_effect=[DummyResult(), DummyJr()])
    current_user = type('User', (), {'id': 1})()
    result = await mod.list_patients(current_user=current_user, db=db)
    assert isinstance(result, list)
    assert 'email' in result[0]

@pytest.mark.asyncio
async def test_get_patient_journal_not_found(monkeypatch):
    if mod is None:
        pytest.skip('server.api.doctor_routes not importable')
    monkeypatch.setattr(mod, '_require_doctor', lambda user: None)
    # Patch select and User
    monkeypatch.setattr(mod, 'select', lambda *a, **kw: 'query')
    monkeypatch.setattr(mod, 'User', type('User', (), {'id': 'pid1', 'user_type': 'patient', 'doctor_id': 1}))
    db = mock.Mock()
    async def dummy_execute(q):
        class DummyResult:
            def scalar_one_or_none(self):
                return None
        return DummyResult()
    db.execute = dummy_execute
    current_user = type('User', (), {'id': 1})()
    with pytest.raises(mod.HTTPException):
        await mod.get_patient_journal(patient_id='badid', current_user=current_user, db=db)

@pytest.mark.asyncio
async def test_get_patient_timeline_status_not_found(monkeypatch):
    if mod is None:
        pytest.skip('server.api.doctor_routes not importable')
    monkeypatch.setattr(mod, '_require_doctor', lambda user: None)
    monkeypatch.setattr(mod, 'select', lambda *a, **kw: 'query')
    monkeypatch.setattr(mod, 'User', type('User', (), {'id': 'pid1', 'user_type': 'patient', 'doctor_id': 1}))
    db = mock.Mock()
    async def dummy_execute(q):
        class DummyResult:
            def scalar_one_or_none(self):
                return None
        return DummyResult()
    db.execute = dummy_execute
    current_user = type('User', (), {'id': 1})()
    with pytest.raises(mod.HTTPException):
        await mod.get_patient_timeline_status(patient_id='badid', current_user=current_user, db=db)

@pytest.mark.asyncio
async def test_invite_patient_self(monkeypatch):
    if mod is None:
        pytest.skip('server.api.doctor_routes not importable')
    monkeypatch.setattr(mod, '_require_doctor', lambda user: None)
    body = type('Body', (), {'email': 'doc@example.com'})()
    current_user = type('User', (), {'id': 1, 'email': 'doc@example.com'})()
    background_tasks = mock.Mock()
    request = mock.Mock()
    db = mock.Mock()
    with pytest.raises(mod.HTTPException):
        await mod.invite_patient(body=body, background_tasks=background_tasks, request=request, current_user=current_user, db=db)

@pytest.mark.asyncio
async def test_get_pending_invites(monkeypatch):
    if mod is None:
        pytest.skip('server.api.doctor_routes not importable')
    monkeypatch.setattr(mod, '_require_doctor', lambda user: None)
    # Patch select and DoctorPatientInvite
    monkeypatch.setattr(mod, 'select', lambda *a, **kw: 'query')
    monkeypatch.setattr(mod, 'DoctorPatientInvite', type('DoctorPatientInvite', (), {'from_user_id': 1, 'invite_type': 'doctor_invites_patient', 'status': 'pending', 'created_at': None}))
    db = mock.Mock()
    class DummyResult:
        def scalars(self):
            class DummyScalars:
                def all(self):
                    class DummyInvite:
                        id = 'iid1'
                        to_email = 'pat@example.com'
                        status = 'pending'
                        created_at = None
                    return [DummyInvite()]
            return DummyScalars()
    async def dummy_execute(q):
        return DummyResult()
    db.execute = dummy_execute
    current_user = type('User', (), {'id': 1})()
    result = await mod.get_pending_invites(current_user=current_user, db=db)
    assert isinstance(result, list)
    assert 'to_email' in result[0]
