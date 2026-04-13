from fastapi import APIRouter
from server.mock.fixtures.users import MOCK_DOCTOR

router = APIRouter(prefix="/api/patient", tags=["patient"])

_PENDING_INVITES: list[dict] = []
_invite_counter = 1


@router.get("/my-doctor")
async def my_doctor():
    return {"doctor": MOCK_DOCTOR}


@router.get("/pending-invites")
async def pending_invites():
    return _PENDING_INVITES


@router.post("/invite-doctor")
async def invite_doctor(body: dict = None):
    global _invite_counter
    email = (body or {}).get("email", "unknown@example.com")
    invite = {
        "id": f"inv-{_invite_counter}",
        "to_email": email,
        "status": "pending",
        "created_at": "2025-12-10T00:00:00Z",
        "expires_at": "2025-12-17T00:00:00Z",
    }
    _PENDING_INVITES.append(invite)
    _invite_counter += 1
    return invite
