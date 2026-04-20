"""
2OPMD Game Plan auth: Start Session / Close Session / Timeline Initialize.

Language: "Start Session" (not Login), "Close Session" (not Logout).
POST /api/session/instantiate -> { session_token, operator_type, timeline_id }
POST /api/session/close -> close current session
POST /api/timeline/initialize -> create patient timeline (requires patient session)
GET /api/timeline/status -> { has_timeline, timeline_id, event_count, last_updated } (JWT or vault session Bearer)
POST /api/timeline/import-pdf -> multipart PDF upload (JWT auth)
POST /api/timeline/artifact -> lightweight file metadata into PTV (session Bearer)
POST /api/timeline/mock-events -> append mock PTV events (session Bearer)
"""
import logging
import secrets
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, status, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.postgresql.models import User
from server.db.session import get_session
from server.api.auth_postgres import authenticate_user, get_current_user_postgres

logger = logging.getLogger(__name__)

router = APIRouter()


def _ollama_native_base_url() -> str:
    """
    Host root for Ollama's native POST /api/chat.
    OLLAMA_BASE_URL is often set to .../11434/v1 for OpenAI-compatible clients; strip a trailing /v1.
    """
    import os as _os

    raw = (_os.getenv("OLLAMA_BASE_URL") or "http://192.168.0.245:11434").strip().rstrip("/")
    if raw.lower().endswith("/v1"):
        raw = raw[:-3].rstrip("/")
    return raw or "http://127.0.0.1:11434"


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
    # Accept asyncpg pgproto.UUID, stdlib uuid.UUID, or plain str
    user_uuid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
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


async def get_vault_user_from_session(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> User:
    """Session Bearer user with email verified + PTV row (Epistemic Vault HTML)."""
    from server.eoh.ptv_journal_bridge import ensure_user_ptv_row, vision_row_exists

    token = await _get_bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer session_token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_uuid = await get_user_id_for_session(db, token)
    if not user_uuid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or closed session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    r = await db.execute(select(User).where(User.id == user_uuid))
    user = r.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found for session",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not getattr(user, "is_verified", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "email_not_verified",
                "message": "Please verify your email to continue.",
                "actions": {"resend_endpoint": "/api/auth/resend-verification"},
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    pool = getattr(request.app.state, "pool", None)
    if pool is not None:
        await ensure_user_ptv_row(pool, str(user.id))
        if not await vision_row_exists(pool, str(user.id)):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "ptv_not_initialized",
                    "message": "Your clinical graph could not be loaded. Please retry or contact support.",
                },
            )
    return user


class MockTimelineEventsRequest(BaseModel):
    events: List[Dict[str, Any]] = Field(default_factory=list)


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


async def get_user_for_timeline_status(
    request: Request,
    db: AsyncSession = Depends(get_session),
) -> Any:
    """
    Accept vault session Bearer or JWT. No PTV row gate — status is a read-only summary.
    Session is tried first so vault HTML does not mis-decode DB tokens as JWT.
    """
    import os as _os
    from jose import JWTError, jwt

    from server.api.auth_postgres import ALGORITHM, SECRET_KEY, get_user_by_email

    token = await _get_bearer_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization: Bearer",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if (
        token == "dev-bypass"
        and _os.getenv("DEV_AUTH_BYPASS", "").lower() == "true"
        and _os.getenv("APP_ENV", "local") != "production"
    ):
        from types import SimpleNamespace

        return SimpleNamespace(
            id="dev-user-id",
            email="dev@local",
            full_name="Dev User",
            hashed_password="",
            birthdate=None,
            subscription_tier="pro",
            user_type=_os.getenv("VITE_DEV_USER_TYPE", "patient"),
            created_at=datetime.utcnow(),
            last_login=None,
            is_verified=True,
            locked_until=None,
            ptv_ready=True,
        )

    user_uuid = await get_user_id_for_session(db, token)
    if user_uuid is not None:
        r = await db.execute(select(User).where(User.id == user_uuid))
        user = r.scalar_one_or_none()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found for session",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if not getattr(user, "is_verified", False):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "code": "email_not_verified",
                    "message": "Please verify your email to continue.",
                    "actions": {"resend_endpoint": "/api/auth/resend-verification"},
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    auth_user = await get_user_by_email(email=email, db=db)
    if auth_user is None:
        raise credentials_exception

    if auth_user.locked_until and auth_user.locked_until > datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Account locked until {auth_user.locked_until}",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not auth_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "email_not_verified",
                "message": "Please verify your email to continue.",
                "actions": {"resend_endpoint": "/api/auth/resend-verification"},
            },
            headers={"WWW-Authenticate": "Bearer"},
        )

    return auth_user


# --- Routes ---------------------------------------------------------------------

@router.post("/instantiate", response_model=SessionInstantiateResponse)
async def session_instantiate(
    request: Request,
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
    pool = getattr(request.app.state, "pool", None)
    if pool is not None:
        from server.eoh.ptv_journal_bridge import ensure_user_ptv_row

        try:
            await ensure_user_ptv_row(pool, str(user.id))
        except Exception:
            logger.exception("PTV bootstrap on session instantiate failed for user %s", user.id)
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


# --- GET /api/timeline/status (JWT or session Bearer) ---------------------------

@timeline_router.get("/status")
async def timeline_status(
    request: Request,
    current_user: Any = Depends(get_user_for_timeline_status),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """
    Return whether the current user has a timeline, event count, and the most
    recent events so the UI can render a list without a second round-trip.

    Source of truth is PTV (``ehr.patient_graph_vision``), keyed by ``user.id``.
    Every vault upload path mirrors into PTV (``add_patient_artifact_event`` +
    ``add_events_from_pdf_page``), so PTV reflects artifacts *and* extracted
    clinical events. The legacy ``ehr.patient_timeline`` table is retained as a
    fallback for the JWT ``/api/timeline/import-pdf`` flow and compliance
    reads — if PTV has no events we return the legacy count.

    Auth: JWT Bearer (React app) or vault session Bearer (Epistemic Vault HTML).
    """
    from server.dev_fixtures import get_timeline_status as _dev_status, is_active as _dev_active
    if _dev_active():
        return _dev_status()

    _uid = getattr(current_user, "id", None)
    user_id = str(_uid) if _uid is not None else None
    if not user_id:
        return {
            "has_timeline": False,
            "timeline_id": None,
            "event_count": 0,
            "last_updated": None,
            "recent_events": [],
        }

    # ── 1. PTV vision (canonical for the vault flow) ────────────────────────
    pool = getattr(request.app.state, "pool", None)
    vision = None
    if pool is not None:
        try:
            from server.eoh.patient_timeline_vision import load_timeline_vision_pg
            vision = await load_timeline_vision_pg(pool, user_id)
        except Exception as e:
            logger.warning("timeline_status: load_timeline_vision_pg failed: %s", e)

    if vision is not None and vision.events:
        # Sort events by ISO timestamp desc; empty/invalid timestamps sink to bottom
        evs_sorted = sorted(
            vision.events.values(),
            key=lambda e: (e.timestamp or "", e.event_id),
            reverse=True,
        )
        recent_events: List[dict] = []
        for ev in evs_sorted[:50]:
            ann = ev.annotations or {}
            recent_events.append({
                "event_id":    ev.event_id,
                "event_type":  ev.event_type or "event",
                "ts":          ev.timestamp or "",
                "timestamp":   ev.timestamp or "",
                "text":        (ev.preview or "")[:500],
                "artifact_id": ann.get("artifact_id"),
                "filename":    ann.get("filename") or ann.get("artifact_filename"),
                "source":      ",".join(ev.discovered_by) if ev.discovered_by else "ptv",
            })
        last_updated = recent_events[0]["ts"] if recent_events and recent_events[0]["ts"] else None
        return {
            "has_timeline": True,
            "timeline_id": user_id,
            "event_count": len(vision.events),
            "edge_count":  vision.count_edges(),
            "last_updated": last_updated,
            "recent_events": recent_events,
            "source": "ptv",
        }

    # ── 2. Legacy fallback: ehr.patient_timeline (JWT import-pdf flow) ─────
    operator_id = await get_or_create_operator(db, user_id, operator_type="patient", sovereignty_level="full")
    timeline_id = await get_timeline_id_for_operator(db, operator_id)
    if not timeline_id:
        return {
            "has_timeline": False,
            "timeline_id": None,
            "event_count": 0,
            "last_updated": None,
            "recent_events": [],
            "source": "none",
        }

    # Historical bug: ingest paths wrote rows under both user_id and
    # timeline_id. Query both so we do not under-count during migration.
    candidate_pids = list({str(timeline_id), user_id})
    count = 0
    last_ts = None
    recent_events = []
    try:
        r = await db.execute(
            text(
                """
                SELECT COUNT(*) AS n, MAX(ts) AS last_ts
                FROM ehr.patient_timeline
                WHERE patient_id = ANY(:pids)
                """
            ),
            {"pids": candidate_pids},
        )
        row = r.fetchone()
        count = row[0] or 0
        last_ts = row[1]

        r2 = await db.execute(
            text(
                """
                SELECT event_id, event_type, ts, text
                FROM ehr.patient_timeline
                WHERE patient_id = ANY(:pids)
                ORDER BY ts DESC NULLS LAST
                LIMIT 50
                """
            ),
            {"pids": candidate_pids},
        )
        for row2 in r2.fetchall():
            ts_iso = row2[2].isoformat() + "Z" if row2[2] else ""
            recent_events.append({
                "event_id":   str(row2[0]) if row2[0] is not None else "",
                "event_type": row2[1] or "event",
                "ts":         ts_iso,
                "timestamp":  ts_iso,
                "text":       (row2[3] or "")[:500],
                "source":     "ehr.patient_timeline",
            })
    except Exception as e:
        logger.warning("timeline_status: ehr.patient_timeline query failed: %s", e)

    last_updated = last_ts.isoformat() + "Z" if last_ts else None
    return {
        "has_timeline": count > 0,
        "timeline_id": timeline_id,
        "event_count": count,
        "last_updated": last_updated,
        "recent_events": recent_events,
        "source": "ehr.patient_timeline",
    }


# --- POST /api/timeline/import-pdf (JWT auth) ----------------------------------

@timeline_router.post("/import-pdf")
async def timeline_import_pdf(
    file: UploadFile = File(...),
    password: Optional[str] = Form(None),
    current_user: Any = Depends(get_user_for_timeline_status),
    db: AsyncSession = Depends(get_session),
) -> dict:
    """
    Accept PDF upload, extract text, ingest into ehr.patient_timeline.
    Auth: session Bearer or JWT. Returns timeline_id, event_count, status.
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="PDF file required")

    # Resolve user -> operator -> timeline
    # Stringify user_id — asyncpg returns pgproto.UUID objects which uuid.UUID() cannot accept directly
    user_id = str(current_user.id) if hasattr(current_user, "id") else None
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    operator_id = await get_or_create_operator(db, user_id, operator_type="patient", sovereignty_level="full")
    timeline_id = await get_timeline_id_for_operator(db, operator_id)
    if not timeline_id:
        # Auto-initialize timeline for first upload
        new_tid = uuid.uuid4()
        operator_uuid = uuid.UUID(operator_id)
        await db.execute(
            text(
                "INSERT INTO patient_timelines (timeline_id, patient_operator_id, timeline_name, anonymization_consent) "
                "VALUES (:tid, :oid, :name, :consent)"
            ),
            {"tid": new_tid, "oid": operator_uuid, "name": "Patient Timeline", "consent": False},
        )
        await db.commit()
        timeline_id = str(new_tid)
    else:
        timeline_id = str(timeline_id)

    # Read and process PDF (minimal: extract text, parse, insert)
    try:
        contents = await file.read()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to read file: {e}")

    if len(contents) > 200 * 1024 * 1024:  # 200MB — large patient record PDFs can be 185MB+
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="File too large (max 200MB)")

    # Delegate to timeline ingest module
    from server.timeline.ingest import run_ingest_from_pdf_bytes

    try:
        event_count = await run_ingest_from_pdf_bytes(
            db=db,
            pdf_bytes=contents,
            patient_id=str(timeline_id),
            password=password,
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF ingestion pipeline not yet wired. Use server/scripts/import_timeline_pdf.py for now.",
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception("timeline_import_pdf failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return {
        "timeline_id": str(timeline_id),
        "patient_id": str(timeline_id),
        "event_count": event_count,
        "status": "ready",
        "message": "Timeline ingested successfully",
    }


# --- Lightweight vault upload + mock PTV (session Bearer, Epistemic index.html) ---

_MAX_ARTIFACT_BYTES = 8 * 1024 * 1024


@timeline_router.post("/artifact")
async def timeline_vault_artifact(
    request: Request,
    file: UploadFile = File(...),
    document_type: str = Form("other"),
    document_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    user: User = Depends(get_vault_user_from_session),
):
    """
    Store a small file as a ``patient_artifact`` node on the user's PTV graph.
    Does **not** run the full timeline PDF / RAG pipeline — metadata + optional text snippet only.
    Returns is_duplicate=true if the same bytes were already uploaded.
    """
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database pool unavailable",
        )
    try:
        data = await file.read()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Failed to read file: {e}")
    if len(data) > _MAX_ARTIFACT_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large (max {_MAX_ARTIFACT_BYTES // (1024 * 1024)} MB for vault artifact)",
        )
    fn = file.filename or "upload"
    ct = file.content_type
    text_snippet: Optional[str] = None
    if ct and "text" in ct.lower():
        text_snippet = data.decode("utf-8", errors="replace")[:8000]

    from server.eoh.event_dedup import artifact_sha256 as _sha256
    from server.eoh.ptv_journal_bridge import add_patient_artifact_event

    sha = _sha256(data)
    try:
        result = await add_patient_artifact_event(
            pool,
            str(user.id),
            filename=fn,
            content_type=ct,
            size_bytes=len(data),
            document_type=document_type,
            document_date=document_date,
            notes=notes,
            text_snippet=text_snippet,
            content_sha256=sha,
            raw_bytes=data,
        )
    except Exception as e:
        logger.exception("timeline_vault_artifact failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    # Embed artifact (non-fatal)
    try:
        from server.eoh.artifact_embeddings import embed_and_store_artifact, ensure_embeddings_table
        await ensure_embeddings_table(pool)
        await embed_and_store_artifact(
            pool,
            str(user.id),
            artifact_id=result["artifact_id"],
            filename=fn,
            document_type=document_type,
            document_date=document_date,
            text_content=text_snippet or data.decode("utf-8", errors="replace")[:4000],
        )
    except Exception as _emb_err:
        logger.warning("vault_artifact embedding failed (non-fatal): %s", _emb_err)

    return {
        "event_id":    result["event_id"],
        "artifact_id": result["artifact_id"],
        "patient_id":  str(user.id),
        "status":      "artifact_stored_in_ptv",
        "filename":    fn,
        "is_duplicate": result["is_duplicate"],
    }


@timeline_router.post("/mock-events")
async def timeline_mock_ptv_events(
    request: Request,
    body: MockTimelineEventsRequest,
    user: User = Depends(get_vault_user_from_session),
):
    """Append mock clinical events to PTV for manual / HTML vault testing."""
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database pool unavailable",
        )
    if len(body.events) > 20:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Maximum 20 mock events per request")
    from server.eoh.ptv_journal_bridge import add_mock_timeline_events

    try:
        n = await add_mock_timeline_events(pool, str(user.id), body.events)
    except Exception as e:
        logger.exception("timeline_mock_ptv_events failed")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return {"added": n, "patient_id": str(user.id)}


# ---------------------------------------------------------------------------
# POST /api/timeline/artifacts/ingest  — multi-file eoh-llama 8B ingest
# Session Bearer auth; SSE stream; up to 20 files per call.
# ---------------------------------------------------------------------------

_INGEST_MAX_FILES = 20
_INGEST_MAX_BYTES_PER_FILE = 500 * 1024 * 1024  # 500 MB (matches /infer limit)

# Supported MIME types for 8B extraction (everything else → Tier A only)
_8B_EXTRACTABLE_MIMES = {
    "application/pdf",
    "text/plain",
    "text/csv",
    "text/html",
    "application/json",
    "application/hl7-v2",
}
_8B_EXTRACTABLE_EXTS = {".pdf", ".txt", ".csv", ".json", ".hl7"}


def _mime_supports_8b(filename: str, content_type: Optional[str]) -> bool:
    import os
    ext = os.path.splitext(filename or "")[1].lower()
    if ext in _8B_EXTRACTABLE_EXTS:
        return True
    if content_type:
        base = content_type.split(";")[0].strip().lower()
        return base in _8B_EXTRACTABLE_MIMES or "text" in base
    return False


def _sse_bytes(event: str, data: dict) -> bytes:
    import json as _json
    return f"event: {event}\ndata: {_json.dumps(data, ensure_ascii=False)}\n\n".encode()


@timeline_router.post("/artifacts/ingest")
async def timeline_artifacts_ingest(
    request: Request,
    files: List[UploadFile] = File(...),
    document_type: str = Form("other"),
    document_date: Optional[str] = Form(None),
    notes: Optional[str] = Form(None),
    model: str = Form("eoh-llama3.1:8b"),
    store_results: bool = Form(True),
    build_graph: bool = Form(True),
    user: User = Depends(get_vault_user_from_session),
    db: AsyncSession = Depends(get_session),
):
    """
    Multi-file Tier B ingest (session Bearer).

    Accepts up to 20 files in one call. Each file is:
    1. Sha256-checked against ``vision.metadata.artifacts`` — duplicate → skip.
    2. Stored as a Tier A ``patient_artifact`` node immediately so the vault
       list is always up to date.
    3. If the mime/extension is PDF/text/JSON: run through eoh-llama 8B
       (via the existing ``_infer_lock`` GPU single-flight).
       Other formats stay as Tier A only.

    Returns an SSE stream with per-file progress events:
      artifact_accepted, (pdf_read | text_extracted), pre_scan_done,
      batch_start, batch_done, graph_update, artifact_done, complete.
    """
    from server.api.timeline_infer_routes import (
        _infer_lock,
        _infer_active,
        _extract_pdf_pages,
        _chunk_pages,
        _call_ollama_8b,
        _parse_extraction_response,
        _INFER_SYSTEM_PROMPT,
        _DEFAULT_NUM_CTX,
        _BATCH_MAX_INPUT_CHARS,
        _OLLAMA_POOL_LIMITS,
        _OLLAMA_TIMEOUT,
    )
    from server.eoh.event_dedup import (
        artifact_sha256 as _sha256,
        artifact_id_from_bytes,
        canonical_event_id,
        artifact_catalog_entry,
    )
    from server.eoh.ptv_journal_bridge import add_patient_artifact_event
    from server.eoh.patient_timeline_vision import (
        load_timeline_vision_pg,
        save_timeline_vision_pg,
        add_events_from_pdf_page,
        _infer_temporal_connascence,
        PatientTimelineVision,
    )
    from server.utils.pii_scrub import scrub_pages, extract_patient_names_from_header, scrub_pii

    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Database pool unavailable")

    if len(files) > _INGEST_MAX_FILES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {_INGEST_MAX_FILES} files per call",
        )

    # Read all file bytes eagerly before acquiring the GPU lock
    file_items: List[dict] = []
    for upload in files:
        try:
            data = await upload.read()
        except Exception as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Could not read {upload.filename}: {exc}")
        if len(data) > _INGEST_MAX_BYTES_PER_FILE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"{upload.filename} exceeds {_INGEST_MAX_BYTES_PER_FILE // (1024 * 1024)} MB limit",
            )
        file_items.append({
            "filename": upload.filename or "upload",
            "content_type": upload.content_type,
            "data": data,
            "sha": _sha256(data),
        })

    patient_id = str(user.id)

    async def _generate():
        import asyncio
        import hashlib

        totals = {"extracted": 0, "merged": 0, "duplicates": 0}

        # Hold GPU lock across ALL files so no other inference can interleave
        if _infer_lock.locked():
            yield _sse_bytes("error", {
                "message": "Inference already in progress. Try again shortly.",
                "active_job": _infer_active.copy(),
            })
            return

        async with _infer_lock:
            _infer_active.update({
                "patient_id": patient_id,
                "model": model,
                "files": len(file_items),
                "source": "artifacts_ingest",
            })
            try:
                for fi in file_items:
                    fn = fi["filename"]
                    data = fi["data"]
                    sha = fi["sha"]
                    ct = fi["content_type"]
                    art_id = f"art_{sha[:16]}"

                    # ── Artifact-level dedup check ──────────────────────────
                    vision = await load_timeline_vision_pg(pool, patient_id)
                    if vision is None:
                        from server.eoh.ptv_journal_bridge import empty_user_vision
                        vision = empty_user_vision(patient_id)
                    artifacts_catalog = vision.metadata.setdefault("artifacts", [])
                    is_dup = any(a.get("artifact_id") == art_id for a in artifacts_catalog)

                    yield _sse_bytes("artifact_accepted", {
                        "artifact_id": art_id,
                        "filename": fn,
                        "size_bytes": len(data),
                        "sha256": sha,
                        "is_duplicate": is_dup,
                    })

                    if is_dup:
                        # Touch last_seen_at and move on
                        for a in artifacts_catalog:
                            if a.get("artifact_id") == art_id:
                                from datetime import datetime, timezone
                                a["last_seen_at"] = datetime.now(timezone.utc).isoformat()
                        await save_timeline_vision_pg(pool, vision)
                        totals["duplicates"] += 1
                        yield _sse_bytes("artifact_done", {
                            "artifact_id": art_id,
                            "filename": fn,
                            "events_extracted": 0,
                            "events_merged": 0,
                            "reason": "duplicate",
                        })
                        continue

                    # ── Tier A registration (always) ─────────────────────
                    text_snippet: Optional[str] = None
                    if ct and "text" in ct.lower():
                        text_snippet = data.decode("utf-8", errors="replace")[:8000]

                    tier_a_result = await add_patient_artifact_event(
                        pool,
                        patient_id,
                        filename=fn,
                        content_type=ct,
                        size_bytes=len(data),
                        document_type=document_type,
                        document_date=document_date,
                        notes=notes,
                        text_snippet=text_snippet,
                        content_sha256=sha,
                        raw_bytes=data,
                    )

                    # ── Decide if 8B extraction is possible ──────────────
                    if not _mime_supports_8b(fn, ct):
                        yield _sse_bytes("artifact_done", {
                            "artifact_id": art_id,
                            "filename": fn,
                            "events_extracted": 0,
                            "events_merged": 0,
                            "reason": "unsupported_for_8b",
                        })
                        continue

                    # ── Extract text ─────────────────────────────────────
                    loop = asyncio.get_running_loop()
                    pages = None
                    raw_text = None
                    is_pdf = (ct == "application/pdf" or fn.lower().endswith(".pdf"))

                    if is_pdf:
                        yield _sse_bytes("status", {"phase": "pdf_extracting", "filename": fn})
                        try:
                            pages = await loop.run_in_executor(None, _extract_pdf_pages, data, None)
                        except Exception as exc:
                            yield _sse_bytes("batch_error", {"filename": fn, "message": f"PDF extraction failed: {exc}"})
                            continue
                        if not pages:
                            yield _sse_bytes("batch_error", {"filename": fn, "message": "No text extracted from PDF"})
                            continue
                        total_chars = sum(len(t) for _, t in pages)
                        yield _sse_bytes("pdf_read", {
                            "filename": fn,
                            "pages": max(p for p, _ in pages),
                            "chars": total_chars,
                        })
                        # PII scrub
                        known_names = await loop.run_in_executor(None, extract_patient_names_from_header, pages)
                        pages = await loop.run_in_executor(None, scrub_pages, pages, known_names)
                    else:
                        raw_text = data.decode("utf-8", errors="replace")
                        raw_text = scrub_pii(raw_text)
                        yield _sse_bytes("text_extracted", {"filename": fn, "chars": len(raw_text)})

                    # ── Update patient_artifacts with extracted text ───────
                    full_text: Optional[str] = None
                    if pages is not None:
                        full_text = "\n\n".join(t for _, t in pages)
                    elif raw_text:
                        full_text = raw_text
                    if full_text and tier_a_result and not tier_a_result.get("is_duplicate"):
                        try:
                            async with pool.acquire() as _conn:
                                await _conn.execute(
                                    """
                                    UPDATE ehr.patient_artifacts
                                    SET text_content = $1
                                    WHERE patient_id = $2 AND artifact_id = $3
                                    """,
                                    full_text[:500_000],
                                    patient_id,
                                    tier_a_result["artifact_id"],
                                )
                        except Exception as _upd_err:
                            logger.warning("patient_artifacts text update failed (non-fatal): %s", _upd_err)

                        # ── Embed artifact ────────────────────────────────────
                        try:
                            from server.eoh.artifact_embeddings import (
                                embed_and_store_artifact, ensure_embeddings_table
                            )
                            await ensure_embeddings_table(pool)
                            await embed_and_store_artifact(
                                pool,
                                patient_id,
                                artifact_id=tier_a_result["artifact_id"],
                                filename=fn,
                                document_type=document_type,
                                document_date=document_date,
                                text_content=full_text[:4000],
                            )
                        except Exception as _emb_err:
                            logger.warning("artifact embedding failed (non-fatal): %s", _emb_err)

                    # ── Heuristic pre-scan (PDF only) ─────────────────────
                    prescan_events_total = 0
                    prescan_by_page: dict = {}
                    if pages is not None:
                        from server.eoh.heuristic_page_extract import heuristic_extract_batch
                        prescan_results = await loop.run_in_executor(None, heuristic_extract_batch, pages)
                        prescan_by_page = prescan_results
                        for pr in prescan_results.values():
                            prescan_events_total += len(pr.events)
                        yield _sse_bytes("pre_scan_done", {
                            "filename": fn,
                            "events": prescan_events_total,
                        })

                    # ── Batch text for 8B ─────────────────────────────────
                    if pages is not None:
                        from server.api.timeline_infer_routes import _chunk_pages
                        batches = _chunk_pages(pages)
                    else:
                        # Text: one flat batch
                        batches = [[(1, raw_text)]]

                    total_batches = len(batches)
                    events_this_file: List[dict] = []
                    total_elapsed = 0.0

                    import httpx as _httpx
                    async with _httpx.AsyncClient(limits=_OLLAMA_POOL_LIMITS, timeout=_OLLAMA_TIMEOUT) as http:
                        for bidx, batch in enumerate(batches, 1):
                            if pages is not None:
                                sections = []
                                for pn, txt in batch:
                                    sec = f"=== Page {pn} ===\n{txt}"
                                    pr = prescan_by_page.get(pn)
                                    if pr is not None:
                                        from server.eoh.heuristic_page_extract import skeleton_for_llm
                                        skel = skeleton_for_llm(pn, txt, pr)
                                        if skel:
                                            sec += f"\n\n--- PRE-SCAN SKELETON ---\n{skel}"
                                    sections.append(sec)
                                batch_text = "\n\n".join(sections)
                            else:
                                batch_text = raw_text[:_BATCH_MAX_INPUT_CHARS]

                            yield _sse_bytes("batch_start", {"filename": fn, "batch": bidx, "total": total_batches, "chars": len(batch_text)})

                            try:
                                raw_resp, elapsed = await _call_ollama_8b(
                                    http=http,
                                    batch_text=batch_text,
                                    question="Extract all clinically significant events as a JSON array.",
                                    model=model,
                                    num_ctx=_DEFAULT_NUM_CTX,
                                )
                                total_elapsed += elapsed
                                extracted = _parse_extraction_response(raw_resp)

                                for ev in extracted:
                                    if ev.get("text"):
                                        ev["text"] = scrub_pii(ev["text"])
                                    ev["_batch"] = bidx
                                    ev["_model"] = model
                                    ev["_artifact_id"] = art_id
                                    ev["_filename"] = fn

                                # Persist to ehr.patient_timeline (dedup-safe)
                                if store_results:
                                    from server.api.timeline_infer_routes import _store_extracted_events
                                    await _store_extracted_events(db, patient_id, extracted, bidx, model, artifact_id=art_id)

                                # Merge into PTV graph
                                if build_graph:
                                    vision_now = await load_timeline_vision_pg(pool, patient_id)
                                    if vision_now is None:
                                        from server.eoh.ptv_journal_bridge import empty_user_vision
                                        vision_now = empty_user_vision(patient_id)
                                    pn = batch[0][0] if pages is not None else bidx
                                    add_events_from_pdf_page(vision_now, pn, extracted)
                                    await save_timeline_vision_pg(pool, vision_now)
                                    yield _sse_bytes("graph_update", {
                                        "filename": fn,
                                        "total_events": len(vision_now.events),
                                        "total_edges": vision_now.count_edges(),
                                    })

                                events_this_file.extend(extracted)
                                yield _sse_bytes("batch_done", {
                                    "filename": fn,
                                    "batch": bidx,
                                    "extracted": len(extracted),
                                    "elapsed_ms": int(elapsed * 1000),
                                })
                            except Exception as exc:
                                logger.exception("artifacts/ingest batch %d failed for %s", bidx, fn)
                                yield _sse_bytes("batch_error", {"filename": fn, "batch": bidx, "message": str(exc)})

                    # ── Final temporal connascence + update catalog ────────
                    if build_graph:
                        vision_final = await load_timeline_vision_pg(pool, patient_id)
                        if vision_final:
                            _infer_temporal_connascence(vision_final, window_days=7)
                            # Update the artifact catalog entry with extraction counts
                            for a in vision_final.metadata.get("artifacts", []):
                                if a.get("artifact_id") == art_id:
                                    a["ingest_tier"] = "B"
                                    a["events_extracted"] = len(events_this_file)
                                    if pages:
                                        a["pages"] = max(p for p, _ in pages)
                            await save_timeline_vision_pg(pool, vision_final)

                    n_extracted = len(events_this_file)
                    totals["extracted"] += n_extracted
                    yield _sse_bytes("artifact_done", {
                        "artifact_id": art_id,
                        "filename": fn,
                        "events_extracted": n_extracted,
                        "events_merged": n_extracted,
                        "elapsed_ms": int(total_elapsed * 1000),
                    })

            finally:
                _infer_active.clear()

        yield _sse_bytes("complete", {
            "patient_id": patient_id,
            "artifacts": len(file_items),
            "events_extracted_total": totals["extracted"],
            "events_duplicated_total": totals["duplicates"],
        })

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# GET /api/timeline/artifacts/list — list stored artifacts for the patient
# ---------------------------------------------------------------------------

@timeline_router.get("/artifacts/list")
async def timeline_artifacts_list(
    request: Request,
    user: User = Depends(get_vault_user_from_session),
):
    """Return metadata for all artifacts stored in ehr.patient_artifacts."""
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database pool unavailable")
    patient_id = str(user.id)
    rows = await pool.fetch(
        """
        SELECT artifact_id, filename, mime_type, size_bytes, document_type,
               document_date, user_notes, content_sha, uploaded_at,
               LEFT(text_content, 400) AS snippet
        FROM ehr.patient_artifacts
        WHERE patient_id = $1
        ORDER BY uploaded_at DESC
        """,
        patient_id,
    )
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# GET /api/timeline/artifacts/{artifact_id}/content — full text for modal
# ---------------------------------------------------------------------------

@timeline_router.get("/artifacts/{artifact_id}/content")
async def timeline_artifact_content(
    artifact_id: str,
    request: Request,
    user: User = Depends(get_vault_user_from_session),
):
    """Return the full extracted text_content for a single artifact."""
    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database pool unavailable")
    row = await pool.fetchrow(
        """
        SELECT artifact_id, filename, mime_type, document_type,
               document_date, user_notes, uploaded_at, text_content
        FROM ehr.patient_artifacts
        WHERE patient_id = $1 AND artifact_id = $2
        """,
        str(user.id), artifact_id,
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Artifact not found")
    return dict(row)


# ---------------------------------------------------------------------------
# POST /api/timeline/artifacts/recall — multi-source recall + eoh-llama answer
# ---------------------------------------------------------------------------

@timeline_router.post("/artifacts/recall")
async def timeline_artifacts_recall(
    request: Request,
    user: User = Depends(get_vault_user_from_session),
):
    """
    Artifact Recall — three retrieval sources fused:
      1. eoh-llama keyword extraction → FTS + ILIKE
      2. sentence-transformers semantic search
      3. Union ranked: top 4 returned with snippet, next 8 as titles only.

    Body JSON: { "query": "...", "model": "eoh-llama3.1:8b" }
    Returns: {
        "preview":  [{artifact_id, filename, document_type, document_date, snippet, score, source}, ...],  # up to 4
        "titles":   [{artifact_id, filename, document_type, document_date, score}, ...],                   # up to 8
        "answer":   "...",   # eoh-llama answer grounded on top-4 previews
        "keywords": [...]    # extracted by eoh-llama
    }
    """
    import re as _re, json as _json
    body = await request.json()
    query: str = (body.get("query") or "").strip()
    model: str = body.get("model") or "eoh-llama3.1:8b"
    ollama_base = _ollama_native_base_url()

    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database pool unavailable")
    patient_id = str(user.id)

    # ── 1. eoh-llama keyword extraction ──────────────────────────────────────
    keywords: List[str] = []
    try:
        import httpx as _httpx
        kw_prompt = (
            f"Extract 3–6 medical search keywords from the following patient query.\n"
            f"Return ONLY a JSON array of lowercase strings, e.g. [\"creatinine\",\"kidney\"].\n\n"
            f"QUERY: {query}"
        )
        async with _httpx.AsyncClient(timeout=15) as http:
            resp = await http.post(
                f"{ollama_base}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": kw_prompt}],
                    "stream": False,
                    "options": {"num_ctx": 512, "temperature": 0},
                },
            )
            resp.raise_for_status()
            raw_kw = (resp.json().get("message") or {}).get("content", "")
            bracket = raw_kw.find("[")
            if bracket >= 0:
                candidate = raw_kw[bracket:raw_kw.rfind("]") + 1]
                parsed = _json.loads(candidate)
                keywords = [str(k).lower().strip() for k in parsed if k][:8]
    except Exception as _kw_err:
        logger.warning("keyword extraction failed (%s) — falling back to simple tokenisation", _kw_err)
    if not keywords:
        keywords = list(dict.fromkeys(_re.findall(r"\b[a-z]{4,}\b", query.lower())))[:8]

    # ── 2. FTS + ILIKE retrieval ──────────────────────────────────────────────
    fts_hits: List[dict] = []
    fts_query_str = " | ".join(keywords) if keywords else query

    try:
        rows = await pool.fetch(
            """
            SELECT artifact_id, filename, mime_type, document_type, document_date, uploaded_at,
                   ts_headline('english', text_content,
                       to_tsquery('english', $2),
                       'MaxFragments=2, MaxWords=30, MinWords=8') AS snippet,
                   ts_rank_cd(
                       to_tsvector('english', coalesce(text_content,'') || ' ' || coalesce(filename,'')),
                       to_tsquery('english', $2)
                   ) AS rank
            FROM ehr.patient_artifacts
            WHERE patient_id = $1
              AND to_tsvector('english', coalesce(text_content,'') || ' ' || coalesce(filename,''))
                  @@ to_tsquery('english', $2)
            ORDER BY rank DESC
            LIMIT 16
            """,
            patient_id, fts_query_str,
        )
        fts_hits = [dict(r) for r in rows]
    except Exception:
        pass

    # ILIKE sweep for any keyword not caught by FTS
    ilike_seen = {h["artifact_id"] for h in fts_hits}
    for kw in keywords[:4]:
        if len(fts_hits) >= 16:
            break
        try:
            rows = await pool.fetch(
                """
                SELECT artifact_id, filename, mime_type, document_type, document_date, uploaded_at,
                       LEFT(text_content, 300) AS snippet,
                       0.05::float AS rank
                FROM ehr.patient_artifacts
                WHERE patient_id = $1
                  AND (text_content ILIKE $2 OR filename ILIKE $2)
                  AND artifact_id <> ALL($3::text[])
                LIMIT 8
                """,
                patient_id, f"%{kw}%", list(ilike_seen),
            )
            for r in rows:
                d = dict(r)
                ilike_seen.add(d["artifact_id"])
                fts_hits.append(d)
        except Exception:
            pass

    # ── 3. Semantic search ────────────────────────────────────────────────────
    from server.eoh.artifact_embeddings import semantic_search
    sem_hits = await semantic_search(pool, patient_id, query, top_k=16)

    # ── 4. Fuse results ───────────────────────────────────────────────────────
    # Build a score map; semantic score on [0,1], FTS rank scaled to same range
    max_fts_rank = max((h.get("rank", 0) or 0 for h in fts_hits), default=1) or 1
    combined: dict[str, dict] = {}

    for h in fts_hits:
        aid = h["artifact_id"]
        norm_rank = (h.get("rank") or 0) / max_fts_rank
        combined[aid] = {
            "artifact_id": aid,
            "filename": h.get("filename", ""),
            "document_type": h.get("document_type", ""),
            "document_date": str(h.get("document_date") or ""),
            "uploaded_at": str(h.get("uploaded_at") or ""),
            "snippet": h.get("snippet") or "",
            "score": norm_rank,
            "source": "fts",
        }

    for s in sem_hits:
        aid = s["artifact_id"]
        sem_score = s.get("score", 0)
        if aid in combined:
            # boost: take max, tag as combined
            existing = combined[aid]
            combined[aid]["score"] = max(existing["score"], sem_score) + 0.1
            combined[aid]["source"] = "combined"
            if not existing.get("snippet") and s.get("snippet"):
                combined[aid]["snippet"] = s["snippet"]
        else:
            combined[aid] = {
                "artifact_id": aid,
                "filename": s.get("filename", ""),
                "document_type": s.get("document_type", ""),
                "document_date": str(s.get("document_date") or ""),
                "uploaded_at": "",
                "snippet": s.get("snippet") or "",
                "score": sem_score,
                "source": "semantic",
            }

    ranked = sorted(combined.values(), key=lambda x: -x["score"])

    preview = ranked[:4]
    titles = [
        {k: v for k, v in r.items() if k != "snippet"}
        for r in ranked[4:12]
    ]

    # ── 5. eoh-llama answer grounded on top-4 ────────────────────────────────
    answer: Optional[str] = None
    if preview:
        ctx_parts = []
        for h in preview:
            ctx_parts.append(
                f"[{h['filename']} | {h.get('document_type','')} | {h.get('document_date','')}]\n"
                f"{h.get('snippet','')}"
            )
        context_text = "\n\n---\n\n".join(ctx_parts)
        answer_prompt = (
            f"You are a medical assistant reviewing a patient's uploaded documents.\n"
            f"Answer the question using ONLY the context below.\n"
            f"Be concise (2–4 sentences). If the answer is not in the context, say so.\n\n"
            f"QUESTION: {query}\n\n"
            f"CONTEXT:\n{context_text}\n\n"
            f"ANSWER:"
        )
        try:
            import httpx as _httpx
            async with _httpx.AsyncClient(timeout=45) as http:
                resp = await http.post(
                    f"{ollama_base}/api/chat",
                    json={
                        "model": model,
                        "messages": [{"role": "user", "content": answer_prompt}],
                        "stream": False,
                        "options": {"num_ctx": 4096, "temperature": 0.1},
                    },
                )
                resp.raise_for_status()
                answer = (resp.json().get("message") or {}).get("content", "").strip()
        except Exception as exc:
            logger.warning("recall answer generation failed: %s", exc)

    return {
        "preview": preview,
        "titles": titles,
        "answer": answer,
        "keywords": keywords,
    }


# ---------------------------------------------------------------------------
# POST /api/timeline/query — BFS graph query via eoh-llama 8B
# ---------------------------------------------------------------------------

@timeline_router.post("/query")
async def timeline_query(
    request: Request,
    user: User = Depends(get_vault_user_from_session),
):
    """
    Ask a free-form question against the patient's PTV timeline graph.

    Body: { "query": "...", "top_k": 20, "model": "eoh-llama3.1:8b" }

    Seeds up to top_k PTV events by keyword match, then answers with
    eoh-llama 8B.
    """
    import json as _json, re
    body = await request.json()
    query: str = (body.get("query") or "").strip()
    top_k: int = min(int(body.get("top_k", 20)), 50)
    model: str = body.get("model") or "eoh-llama3.1:8b"

    if not query:
        raise HTTPException(status_code=400, detail="query is required")

    pool = getattr(request.app.state, "pool", None)
    if pool is None:
        raise HTTPException(status_code=503, detail="Database pool unavailable")
    patient_id = str(user.id)

    # Load PTV vision
    from server.eoh.patient_timeline_vision import load_timeline_vision_pg
    vision = await load_timeline_vision_pg(pool, patient_id)
    if vision is None:
        raise HTTPException(status_code=404, detail="No timeline found. Upload documents first.")

    # Keyword-BFS seed: score each event by how many query tokens appear in
    # preview/type/annotations. PatientTimelineVision stores events in
    # ``vision.events`` (not ``vision.nodes``).
    q_tokens = set(re.findall(r"\w+", query.lower()))
    scored: List[tuple] = []
    for eid, node in vision.events.items():
        text_blob = (
            (getattr(node, "preview", "") or "") + " " +
            (getattr(node, "event_type", "") or "") + " " +
            _json.dumps(getattr(node, "annotations", {}) or {})
        ).lower()
        score = sum(1 for t in q_tokens if t in text_blob)
        if score > 0:
            scored.append((score, eid, node))

    scored.sort(key=lambda x: -x[0])
    seeds = scored[:top_k]

    if not seeds:
        # Fall back: return most recent events
        all_nodes = sorted(
            vision.events.items(),
            key=lambda kv: getattr(kv[1], "timestamp", "") or "",
            reverse=True,
        )
        seeds = [(0, eid, node) for eid, node in all_nodes[:top_k]]

    # Build context
    context_parts = []
    for _, eid, node in seeds:
        ts = getattr(node, "timestamp", "") or "unknown"
        et = getattr(node, "event_type", "") or "event"
        txt = (getattr(node, "preview", "") or "")[:400]
        context_parts.append(f"[{ts[:10]} | {et}] {txt}")
    context_text = "\n".join(context_parts)

    prompt = (
        f"You are a medical assistant reviewing a patient's timeline.\n"
        f"Answer the question using ONLY the context below.\n\n"
        f"QUESTION: {query}\n\n"
        f"TIMELINE CONTEXT ({len(seeds)} events):\n{context_text}\n\n"
        f"Answer concisely and factually (3-5 sentences):"
    )

    try:
        import httpx as _httpx
        ollama_base = _ollama_native_base_url()
        async with _httpx.AsyncClient(timeout=90) as http:
            resp = await http.post(
                f"{ollama_base}/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"num_ctx": 8192, "temperature": 0.1},
                },
            )
            resp.raise_for_status()
            data = resp.json()
            answer = (data.get("message") or {}).get("content", "").strip()
    except Exception as exc:
        logger.exception("timeline/query ollama call failed")
        raise HTTPException(status_code=502, detail=f"eoh-llama unavailable: {exc}")

    return {
        "query": query,
        "seeds_used": len(seeds),
        "total_events": len(vision.events),
        "answer": answer,
    }