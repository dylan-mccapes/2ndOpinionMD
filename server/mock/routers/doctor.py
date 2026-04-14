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
    entries = seed_entries()
    out = []
    for e in entries:
        symptoms = e.get("symptoms") or []
        sev_vals = []
        for s in symptoms:
            if isinstance(s, dict):
                try:
                    sev_vals.append(int(s.get("severity")))
                except Exception:
                    pass
        max_sev = max(sev_vals) if sev_vals else None
        symptom_list = ", ".join(str(s.get("symptom")) for s in symptoms if isinstance(s, dict) and s.get("symptom"))
        title = f"{e.get('date', '')} — {symptom_list}" if symptom_list else f"Journal entry {e.get('date', '')}"
        content_parts = [
            str(e.get("notes") or "").strip(),
            str(e.get("analysis") or "").strip(),
        ]
        content = "\n\n".join([p for p in content_parts if p]) or "No note content."
        out.append(
            {
                "id": e.get("id"),
                "title": title,
                "content": content,
                "severity": max_sev,
                "created_at": e.get("created_at") or f"{e.get('date', '2025-12-01')}T12:00:00Z",
            }
        )
    return out


@router.get("/patients/{patient_id}/timeline-status")
async def patient_timeline_status(patient_id: str):
    return {
        "has_timeline": True,
        "timeline_id": "norman-dev-timeline",
        "event_count": 247,
        "last_updated": "2025-12-05T00:00:00Z",
    }
