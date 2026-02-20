"""
Patient portal API (Phase 6.0).
POST /api/patient/invite-doctor - patient invites a doctor by email
GET /api/patient/my-doctor - get the linked doctor for current patient
GET /api/patient/pending-invites - list pending invites sent by this patient
"""
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, List

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.postgresql.models import User, DoctorPatientInvite
from server.api.auth_postgres import get_current_user_postgres
from server.db.session import get_session
from server.utils.email.verification import send_invite_email

logger = logging.getLogger(__name__)

router = APIRouter()


class InviteDoctorRequest(BaseModel):
    email: EmailStr


def _require_patient(current_user: Any) -> Any:
    """Ensure current user is a patient; raise 403 otherwise."""
    ut = getattr(current_user, "user_type", "patient")
    if ut != "patient":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Patient access required")
    return current_user


@router.post("/invite-doctor")
async def invite_doctor(
    body: InviteDoctorRequest,
    background_tasks: BackgroundTasks,
    current_user: Any = Depends(get_current_user_postgres),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """
    Patient invites a doctor by email. Creates a pending invite and sends an email.
    """
    _require_patient(current_user)

    if body.email.lower() == current_user.email.lower():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot invite yourself")

    if current_user.doctor_id is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You already have a linked doctor. Disconnect first to link a new one.",
        )

    pending = await db.execute(
        select(DoctorPatientInvite).where(
            DoctorPatientInvite.from_user_id == current_user.id,
            DoctorPatientInvite.to_email == body.email.lower(),
            DoctorPatientInvite.invite_type == "patient_invites_doctor",
            DoctorPatientInvite.status == "pending",
        )
    )
    if pending.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invite already pending for this email")

    invite_token = str(uuid.uuid4())
    invite = DoctorPatientInvite(
        from_user_id=current_user.id,
        to_email=body.email.lower(),
        invite_type="patient_invites_doctor",
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
        from_role="patient",
        invite_type="patient_invites_doctor",
        token=invite_token,
    )

    return {
        "id": str(invite.id),
        "to_email": invite.to_email,
        "status": invite.status,
        "created_at": invite.created_at.isoformat() if invite.created_at else None,
    }


@router.get("/my-doctor")
async def get_my_doctor(
    current_user: Any = Depends(get_current_user_postgres),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """Return the linked doctor for the current patient, or null if none."""
    _require_patient(current_user)

    if current_user.doctor_id is None:
        return {"doctor": None}

    result = await db.execute(select(User).where(User.id == current_user.doctor_id))
    doctor = result.scalar_one_or_none()
    if not doctor:
        return {"doctor": None}

    return {
        "doctor": {
            "id": str(doctor.id),
            "email": doctor.email,
            "full_name": doctor.full_name,
        }
    }


@router.get("/pending-invites")
async def get_patient_pending_invites(
    current_user: Any = Depends(get_current_user_postgres),
    db: AsyncSession = Depends(get_session),
) -> List[dict]:
    """List pending invites sent by this patient (to doctors)."""
    _require_patient(current_user)

    q = select(DoctorPatientInvite).where(
        DoctorPatientInvite.from_user_id == current_user.id,
        DoctorPatientInvite.invite_type == "patient_invites_doctor",
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
