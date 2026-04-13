from fastapi import APIRouter
from server.mock.fixtures.users import MOCK_PATIENT
from server.mock.fixtures.journal import seed_entries

router = APIRouter(prefix="/api/doctor", tags=["doctor"])

_PENDING_INVITES: list[dict] = []
_invite_counter = 1


@router.get("/patients")
async def list_patients():
    return [MOCK_PATIENT]


@router.get("/pending-invites")
async def pending_invites():
    return _PENDING_INVITES


@router.post("/invite-patient")
async def invite_patient(body: dict = None):
    global _invite_counter
    email = (body or {}).get("email", "unknown@example.com")
    invite = {
        "id": f"dinv-{_invite_counter}",
        "to_email": email,
        "status": "pending",
        "created_at": "2025-12-10T00:00:00Z",
        "expires_at": "2025-12-17T00:00:00Z",
    }
    _PENDING_INVITES.append(invite)
    _invite_counter += 1
    return invite


@router.get("/patients/{patient_id}/journal")
async def patient_journal(patient_id: str):
    return seed_entries()


@router.get("/patients/{patient_id}/timeline-status")
async def patient_timeline_status(patient_id: str):
    return {
        "has_timeline": True,
        "timeline_id": "norman-dev-timeline",
        "event_count": 247,
        "last_updated": "2025-12-05T00:00:00Z",
    }
