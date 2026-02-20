"""
Doctor portal API (Phase 5c + Phase 6.0).
GET /api/doctor/patients - list patients linked to current doctor
GET /api/doctor/patients/{id}/journal - journal entries for patient
GET /api/doctor/patients/{id}/timeline-status - timeline status for patient
POST /api/doctor/invite-patient - invite a patient by email
GET /api/doctor/pending-invites - list pending invites sent by this doctor
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy import select, text, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.postgresql.models import User, JournalEntry, DoctorPatientInvite
from server.api.auth_postgres import get_current_user_postgres
from server.db.session import get_session
from server.api.session_routes import get_or_create_operator, get_timeline_id_for_operator
from server.utils.email.verification import send_invite_email

logger = logging.getLogger(__name__)

router = APIRouter()


class InvitePatientRequest(BaseModel):
    email: EmailStr


def _require_doctor(current_user: Any) -> Any:
    """Ensure current user is a doctor; raise 403 otherwise."""
    ut = getattr(current_user, "user_type", "patient")
    if ut != "doctor":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Doctor access required")
    return current_user


@router.get("/patients")
async def list_patients(
    current_user: Any = Depends(get_current_user_postgres),
    db: AsyncSession = Depends(get_session),
) -> List[dict]:
    """
    List patients linked to the current doctor (doctor_id = current_user.id).
    Returns: [{ id, email, full_name, last_journal_date, has_timeline }]
    """
    _require_doctor(current_user)
    doctor_id = current_user.id

    # Query patients where doctor_id = current doctor
    q = select(User).where(User.doctor_id == doctor_id, User.user_type == "patient")
    result = await db.execute(q)
    patients = result.scalars().all()

    out: List[dict] = []
    for p in patients:
        # Last journal date
        jq = select(func.max(JournalEntry.created_at)).where(JournalEntry.user_id == p.id)
        jr = await db.execute(jq)
        last_journal_date = jr.scalar()
        last_journal_str = last_journal_date.isoformat() if last_journal_date else None

        # Timeline status (operator -> patient_timelines -> ehr.patient_timeline)
        has_timeline = False
        try:
            operator_id = await get_or_create_operator(db, str(p.id), operator_type="patient", sovereignty_level="full")
            timeline_id = await get_timeline_id_for_operator(db, operator_id)
            if timeline_id:
                r = await db.execute(
                    text(
                        "SELECT COUNT(*) FROM ehr.patient_timeline WHERE patient_id = :pid"
                    ),
                    {"pid": str(timeline_id)},
                )
                count = r.scalar() or 0
                has_timeline = count > 0
        except Exception as e:
            logger.warning("list_patients: timeline check failed for %s: %s", p.id, e)

        out.append({
            "id": str(p.id),
            "email": p.email,
            "full_name": p.full_name,
            "last_journal_date": last_journal_str,
            "has_timeline": has_timeline,
        })

    return out


@router.get("/patients/{patient_id}/journal")
async def get_patient_journal(
    patient_id: str,
    current_user: Any = Depends(get_current_user_postgres),
    db: AsyncSession = Depends(get_session),
) -> List[dict]:
    """
    Return journal entries for a patient. Doctor must own this patient (patient.doctor_id = current_user.id).
    Frontend expects: [{ id, title, content, severity, created_at }]
    """
    _require_doctor(current_user)
    try:
        pid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    # Verify patient exists and belongs to this doctor
    pq = select(User).where(User.id == pid, User.user_type == "patient", User.doctor_id == current_user.id)
    pr = await db.execute(pq)
    patient = pr.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    jq = select(JournalEntry).where(JournalEntry.user_id == pid).order_by(JournalEntry.created_at.desc())
    jr = await db.execute(jq)
    entries = jr.scalars().all()

    return [
        {
            "id": str(e.id),
            "title": (e.created_at or e.date).strftime("%B %d, %Y") if (e.created_at or e.date) else "Entry",
            "content": (e.notes or "") or (e.analysis or ""),
            "severity": e.stress_level,
            "created_at": (e.created_at or e.date).isoformat() if (e.created_at or e.date) else "",
        }
        for e in entries
    ]


@router.get("/patients/{patient_id}/timeline-status")
async def get_patient_timeline_status(
    patient_id: str,
    current_user: Any = Depends(get_current_user_postgres),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """
    Return timeline status for a patient. Doctor must own this patient.
    Returns: { has_timeline, timeline_id, event_count, last_updated }
    """
    _require_doctor(current_user)
    try:
        pid = uuid.UUID(patient_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    pq = select(User).where(User.id == pid, User.user_type == "patient", User.doctor_id == current_user.id)
    pr = await db.execute(pq)
    patient = pr.scalar_one_or_none()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")

    operator_id = await get_or_create_operator(db, str(pid), operator_type="patient", sovereignty_level="full")
    timeline_id = await get_timeline_id_for_operator(db, operator_id)
    if not timeline_id:
        return {"has_timeline": False, "timeline_id": None, "event_count": 0, "last_updated": None}

    pid_str = str(timeline_id)
    try:
        r = await db.execute(
            text(
                "SELECT COUNT(*) AS n, MAX(ts) AS last_ts FROM ehr.patient_timeline WHERE patient_id = :pid"
            ),
            {"pid": pid_str},
        )
        row = r.fetchone()
        count = row[0] or 0
        last_ts = row[1]
        last_updated = last_ts.isoformat() + "Z" if last_ts else None
    except Exception as e:
        logger.warning("get_patient_timeline_status: query failed: %s", e)
        count = 0
        last_updated = None

    return {
        "has_timeline": count > 0,
        "timeline_id": timeline_id,
        "event_count": count,
        "last_updated": last_updated,
    }


@router.post("/invite-patient")
async def invite_patient(
    body: InvitePatientRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: Any = Depends(get_current_user_postgres),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """
    Doctor invites a patient by email. Creates a pending invite and sends an email.
    If the patient already exists and is already linked, returns an error.
    """
    _require_doctor(current_user)

    if body.email.lower() == current_user.email.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot invite yourself")

    existing = await db.execute(
        select(User).where(User.email == body.email.lower(), User.doctor_id == current_user.id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Patient already linked to your account")

    pending = await db.execute(
        select(DoctorPatientInvite).where(
            DoctorPatientInvite.from_user_id == current_user.id,
            DoctorPatientInvite.to_email == body.email.lower(),
            DoctorPatientInvite.invite_type == "doctor_invites_patient",
            DoctorPatientInvite.status == "pending",
        )
    )
    if pending.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invite already pending for this email")

    invite_token = str(uuid.uuid4())
    invite = DoctorPatientInvite(
        from_user_id=current_user.id,
        to_email=body.email.lower(),
        invite_type="doctor_invites_patient",
        token=invite_token,
        status="pending",
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    from_name = current_user.full_name or current_user.email
    background_tasks.add_task(
        send_invite_email,
        to_email=body.email,
        from_name=from_name,
        from_role="doctor",
        invite_type="doctor_invites_patient",
        token=invite_token,
        frontend_origin=request.headers.get("origin"),
    )

    return {
        "id": str(invite.id),
        "to_email": invite.to_email,
        "status": invite.status,
        "created_at": invite.created_at.isoformat() if invite.created_at else None,
    }


@router.get("/pending-invites")
async def get_pending_invites(
    current_user: Any = Depends(get_current_user_postgres),
    db: AsyncSession = Depends(get_session),
) -> List[dict]:
    """List pending invites sent by this doctor."""
    _require_doctor(current_user)

    q = select(DoctorPatientInvite).where(
        DoctorPatientInvite.from_user_id == current_user.id,
        DoctorPatientInvite.invite_type == "doctor_invites_patient",
        DoctorPatientInvite.status == "pending",
    ).order_by(DoctorPatientInvite.created_at.desc())
    result = await db.execute(q)
    invites = result.scalars().all()

    return [
        {
            "id": str(inv.id),
            "to_email": inv.to_email,
            "status": inv.status,
            "created_at": inv.created_at.isoformat() if inv.created_at else None,
            "expires_at": inv.expires_at.isoformat() if inv.expires_at else None,
        }
        for inv in invites
    ]
