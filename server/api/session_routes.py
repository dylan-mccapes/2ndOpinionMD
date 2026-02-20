"""
2OPMD Game Plan auth: Start Session / Close Session / Timeline Initialize.

Language: "Start Session" (not Login), "Close Session" (not Logout).
POST /api/session/instantiate -> { session_token, operator_type, timeline_id }
POST /api/session/close -> close current session
POST /api/timeline/initialize -> create patient timeline (requires patient session)
"""
import logging
import secrets
import uuid
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_session
from server.api.auth_postgres import authenticate_user

logger = logging.getLogger(__name__)

router = APIRouter()


# --- Request/Response models (game plan) ---------------------------------------

class SessionInstantiateRequest(BaseModel):
    """Start Session: email + credentials (same as login, different semantics)."""
    email: EmailStr
    password: str


class SessionInstantiateResponse(BaseModel):
    """Response: session_token, operator_type, timeline_id (null if not yet initialized)."""
    session_token: str
    operator_type: str
    timeline_id: Optional[str] = None


class SessionCloseResponse(BaseModel):
    """Close Session: state persisted."""
    detail: str = "Session closed"


class TimelineInitializeRequest(BaseModel):
    """First-time patient: name timeline + optional patient_info."""
    timeline_name: str
    patient_info: Optional[dict] = None  # date_of_birth, gender, anonymization_consent


class TimelineInitializeResponse(BaseModel):
    """Timeline created."""
    timeline_id: str
    created_at: str
    status: str = "initialized"


# --- Helpers (raw SQL vs new tables; no ORM models in database.models) ---------

async def get_or_create_operator(
    db: AsyncSession, user_id: str, operator_type: str = "patient", sovereignty_level: str = "full"
) -> str:
    """Get existing operator for user_id or create one. Returns operator_id (UUID str)."""
    user_uuid = uuid.UUID(user_id)
    r = await db.execute(
        text("SELECT operator_id FROM operators WHERE user_id = :uid"),
        {"uid": user_uuid},
    )
    row = r.fetchone()
    if row:
        return str(row[0])
    operator_id = uuid.uuid4()
    await db.execute(
        text(
            "INSERT INTO operators (operator_id, user_id, operator_type, sovereignty_level) "
            "VALUES (:oid, :uid, :otype, :level)"
        ),
        {"oid": operator_id, "uid": user_uuid, "otype": operator_type, "level": sovereignty_level},
    )
    await db.commit()
    return str(operator_id)


async def create_session_for_operator(db: AsyncSession, operator_id: str) -> tuple[str, str]:
    """Create session row; return (session_token, session_id)."""
    session_id = uuid.uuid4()
    session_token = secrets.token_urlsafe(32)
    operator_uuid = uuid.UUID(operator_id)
    await db.execute(
        text(
            "INSERT INTO sessions (session_id, operator_id, session_token) "
            "VALUES (:sid, :oid, :token)"
        ),
        {"sid": session_id, "oid": operator_uuid, "token": session_token},
    )
    await db.execute(
        text("UPDATE operators SET last_session_at = :now WHERE operator_id = :oid"),
        {"now": datetime.utcnow(), "oid": operator_uuid},
    )
    await db.commit()
    return session_token, str(session_id)


async def get_timeline_id_for_operator(db: AsyncSession, operator_id: str) -> Optional[str]:
    """Return timeline_id for patient operator or None."""
    r = await db.execute(
        text(
            "SELECT timeline_id FROM patient_timelines WHERE patient_operator_id = :oid"
        ),
        {"oid": uuid.UUID(operator_id)},
    )
    row = r.fetchone()
    return str(row[0]) if row else None


async def get_session_by_token(
    db: AsyncSession, session_token: str
) -> Optional[dict[str, Any]]:
    """Return session + operator info if token valid and not closed."""
    r = await db.execute(
        text(
            "SELECT s.session_id, s.operator_id, o.operator_type "
            "FROM sessions s JOIN operators o ON s.operator_id = o.operator_id "
            "WHERE s.session_token = :token AND s.closed_at IS NULL"
        ),
        {"token": session_token},
    )
    row = r.fetchone()
    if not row:
        return None
    return {
        "session_id": str(row[0]),
        "operator_id": str(row[1]),
        "operator_type": row[2],
    }


async def get_user_id_for_session(
    db: AsyncSession, session_token: str
) -> Optional[UUID]:
    """Return user_id for valid session token (for POC journal/auth by session)."""
    r = await db.execute(
        text(
            "SELECT o.user_id FROM sessions s JOIN operators o ON s.operator_id = o.operator_id "
            "WHERE s.session_token = :token AND s.closed_at IS NULL"
        ),
        {"token": session_token},
    )
    row = r.fetchone()
    return row[0] if row else None


async def close_session_by_token(db: AsyncSession, session_token: str) -> bool:
    """Set closed_at = now() for session with token. Returns True if updated."""
    r = await db.execute(
        text(
            "UPDATE sessions SET closed_at = :now WHERE session_token = :token AND closed_at IS NULL"
        ),
        {"now": datetime.utcnow(), "token": session_token},
    )
    await db.commit()
    return r.rowcount > 0


# --- Dependency: current session from Bearer token -----------------------------

async def get_session_token_from_header(
    authorization: Optional[str] = None,
) -> Optional[str]:
    """Extract Bearer token from Authorization header."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    return authorization[7:].strip()


async def get_current_session(
    session_token: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
) -> Optional[dict[str, Any]]:
    """Optional dependency: current session info if valid Bearer token provided."""
    if not session_token:
        return None
    return await get_session_by_token(db, session_token)


def require_session_token(authorization: Optional[str] = None) -> str:
    """Dependency that requires Authorization Bearer token; raises 401 if missing."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header (Bearer session_token)",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return authorization[7:].strip()


async def _get_bearer_token(request: Request) -> Optional[str]:
    """Extract Bearer token from request Authorization header."""
    return await get_session_token_from_header(request.headers.get("Authorization"))


# --- Routes ---------------------------------------------------------------------

@router.post("/instantiate", response_model=SessionInstantiateResponse)
async def session_instantiate(
    body: SessionInstantiateRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Start Session (system instantiation).
    Email + password; creates or reuses operator, creates session, returns session_token
    and timeline_id if patient already has a timeline.
    """
    from fastapi.security import OAuth2PasswordRequestForm
    form = OAuth2PasswordRequestForm(username=body.email, password=body.password)
    user = await authenticate_user(form.username, form.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "bad_credentials", "message": "Incorrect email or password"},
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not getattr(user, "is_verified", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "email_not_verified",
                "message": "Please verify your email to continue.",
                "actions": {"resend_endpoint": "/api/auth/resend-verification"},
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    operator_id = await get_or_create_operator(db, user.id, operator_type="patient", sovereignty_level="full")
    session_token, _ = await create_session_for_operator(db, operator_id)
    timeline_id = await get_timeline_id_for_operator(db, operator_id)
    return SessionInstantiateResponse(
        session_token=session_token,
        operator_type="patient",
        timeline_id=timeline_id,
    )


@router.post("/close", response_model=SessionCloseResponse)
async def session_close(
    request: Request,
    db: AsyncSession = Depends(get_session),
):
    """Close Session (termination). Requires Authorization: Bearer <session_token>."""
    token = await _get_bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer session_token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    closed = await close_session_by_token(db, token)
    if not closed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found or already closed",
        )
    return SessionCloseResponse()


# --- Timeline router (game plan: POST /api/timeline/initialize) ------------------

timeline_router = APIRouter()


@timeline_router.post("/initialize", response_model=TimelineInitializeResponse)
async def timeline_initialize(
    request: Request,
    body: TimelineInitializeRequest,
    db: AsyncSession = Depends(get_session),
):
    """
    Timeline Initialization (first-time patient).
    Requires Authorization: Bearer <session_token> (patient session).
    Creates patient_timelines row; returns timeline_id.
    """
    token = await _get_bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer session_token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    session_info = await get_session_by_token(db, token)
    if not session_info:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or closed session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if session_info["operator_type"] != "patient":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Timeline initialization is only for patient operators",
        )
    operator_id = session_info["operator_id"]
    # Check not already initialized
    existing = await get_timeline_id_for_operator(db, operator_id)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Timeline already initialized for this operator",
        )
    patient_info = body.patient_info or {}
    anonymization_consent = patient_info.get("anonymization_consent", False)
    timeline_id = uuid.uuid4()
    operator_uuid = uuid.UUID(operator_id)
    await db.execute(
        text(
            "INSERT INTO patient_timelines (timeline_id, patient_operator_id, timeline_name, anonymization_consent) "
            "VALUES (:tid, :oid, :name, :consent)"
        ),
        {"tid": timeline_id, "oid": operator_uuid, "name": body.timeline_name, "consent": anonymization_consent},
    )
    await db.commit()
    now = datetime.utcnow().isoformat() + "Z"
    return TimelineInitializeResponse(
        timeline_id=str(timeline_id),
        created_at=now,
        status="initialized",
    )