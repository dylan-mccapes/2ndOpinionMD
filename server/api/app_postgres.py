# server/api/app_postgres.py
import os
import json
import logging
import sys
import traceback
import re
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from pathlib import Path

from fastapi import FastAPI, HTTPException, Body, Depends, Request, status
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
import asyncpg
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from fastapi.middleware.cors import CORSMiddleware

# --- sys.path & env -----------------------------------------------------------
# Resolve project root (two levels up from this file: .../2ndOpinionMD-MVP)
project_root = Path(__file__).resolve().parents[2]
env_path = project_root / ".env"

APP_ENV = os.getenv("APP_ENV", "local")

# In Docker we set APP_ENV=production via .env.docker, so:
# - Local dev: load .env (if present)
# - Docker / production: DO NOT override Docker-provided env vars
if APP_ENV != "production" and env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)

# --- logging ------------------------------------------------------------------
from server.utils.encrypted_logging import setup_encrypted_logging
setup_encrypted_logging(
    log_dir=os.environ.get("LOG_DIR", "./logs"),
    log_level=logging.INFO,
    console_logging=True,
)
logger = logging.getLogger(__name__)

# --- async DB session factory (your existing stack) ---------------------------
from server.db.session import get_session, init_session_factory
from database.models.postgresql.models import User as UserInDB  # noqa: F401

# --- psycopg2 pool for sync endpoints (MIMIC routers) -------------------------
from server.api.db import init_pool

# --- rate limiting & helpers ---------------------------------------------------
from server.utils.rate_limiter import general_rate_limiter, diagnose_rate_limiter, get_client_ip

# --- RAG engine ---------------------------------------------------------------
from server.vectordb.postgresql_query_engine import PostgreSQLMedicalQueryEngine
query_engine: Optional[PostgreSQLMedicalQueryEngine] = None

# --- Routers ------------------------------------------------------------------
from server.api.journal import router as journal_router
from server.api.chat_graph_routes import router as chat_graph_router
from server.api.auth_routes_postgres import router as auth_router
from server.api.session_routes import router as session_router, timeline_router as session_timeline_router
from server.api.doctor_routes import router as doctor_router
from server.api.patient_routes import router as patient_router
from server.api.portal_routes import router as portal_router

from server.api.loinc_routes import router as loinc_router
from server.api.snomed_routes import router as snomed_router
from server.api.rxnorm_routes import router as rxnorm_router
from server.api.orphanet_routes import router as orphanet_router
from .chv_routes import router as chv_router
from server.api.hpo_routes import router as hpo_router
from server.api.clingen_actionability_routes import router as clingen_actionability_router
from server.api.mimic3_routes import router as mimic3_router
from server.api.mimic4_routes import router as mimic4_router
from server.api.notes_routes  import router as notes_router
from server.api.panelapp_routes import router as panelapp_router
from server.api.guidelines_routes import router as guidelines_router
from server.api import diagnostic_rules_routes
from .disgenet_routes import router as disgenet_router
from server.api.gwas_routes import router as gwas_router
from server.api.neurolex_routes import router as neurolex_router
from .neurolex_xref_routes import router as neurolex_xref_router
from .rag_routes import router as rag_router
from . import who_routes
from .guidelines_cdc_routes import router as cdc_opioid_router
from .guidelines_va_routes import router as va_router
from .coding_routes import router as coding_router
from .ask_eoh_v2 import router as ask_eoh_router
from .rag_ask_compat import router as rag_ask_router
from .coding_routes_v2 import router as coding_v2_router
from .rag_ask_compat_v2 import router as ask_compat_v2_router
from .rag_stream_routes import router as rag_stream_router
from .llm_stream_routes import router as llm_stream_router
from .rag_stream_custom_endpoints import router as rag_stream_custom_router
from .eoh_router_routes import router as eoh_router_router
from server.api import eoh_demo_routes
from server.api.timeline_routes import router as timeline_router
from server.api.timeline_analytics_routes import router as timeline_analytics_router
from server.api.ptv_analytics_routes import router as ptv_analytics_router
from server.api.timeline_infer_routes import router as timeline_infer_router, forward_router as forward_infer_router
from server.api.graph_query_routes import router as graph_query_router

from server.api.kg import router as kg_router

from PortalVision.printer_routes import router as printer_router
from PortalVision.audio_routes import router as audio_router

from server.api.schemas import DiagnoseResponse

# --- B2B API infrastructure ---
from server.b2b.v1_mkg_router import mkg_router as b2b_mkg_router, evidence_router as b2b_evidence_router, health_router as b2b_health_router
from server.b2b.middleware import B2BUsageMiddleware
from server.b2b.usage import meter as b2b_meter
from server.b2b.auth import require_scope
from server.b2b.rate_limit import b2b_rate_limit

# Shared dependency lists for API-key gating on /api/ routes
_MKG_READ_AUTH = [Depends(require_scope("mkg:read")), Depends(b2b_rate_limit)]
_MKG_EVIDENCE_AUTH = [Depends(require_scope("mkg:evidence")), Depends(b2b_rate_limit)]
_PTV_READ_AUTH = [Depends(require_scope("ptv:read")), Depends(b2b_rate_limit)]
_PTV_EXTRACT_AUTH = [Depends(require_scope("ptv:extract")), Depends(b2b_rate_limit)]

# asyncpg pool for PTV / vault routes (session_routes, ptv_journal_bridge).  Kept in
# sync with SQLAlchemy URL — see lifespan() below.
_pool: Optional[Any] = None


def _asyncpg_dsn_for_pool(sqlalchemy_async_url: str) -> str:
    """Strip SQLAlchemy's +asyncpg driver suffix for native asyncpg.create_pool."""
    u = sqlalchemy_async_url.strip()
    if u.startswith("postgresql+asyncpg://"):
        return u.replace("postgresql+asyncpg://", "postgresql://", 1)
    if u.startswith("postgresql://"):
        return u
    return u


# --- lifespan: init async engine + session + RAG engine -----------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Prefer DATABASE_URL; fall back to SYNC_DATABASE_URL (used for rag_corpus; most important).
    # create_async_engine requires async driver: ensure postgresql+asyncpg://
    raw_url = os.getenv("DATABASE_URL") or os.getenv("SYNC_DATABASE_URL")
    if not raw_url:
        raise RuntimeError("No DATABASE_URL or SYNC_DATABASE_URL set in environment")
    if raw_url.startswith("postgresql://") and "+asyncpg" not in raw_url:
        raw_url = raw_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # Redact password for logs
    redacted = raw_url
    try:
        if "://" in raw_url and "@" in raw_url:
            scheme, rest = raw_url.split("://", 1)
            creds, tail = rest.split("@", 1)
            if ":" in creds:
                user, _pw = creds.split(":", 1)
                redacted = f"{scheme}://{user}:****@{tail}"
    except Exception:
        # best effort; don't crash on weird URL
        pass

    logger.info(f"Using async DATABASE_URL: {redacted}")

    engine = create_async_engine(
        raw_url,
        echo=False,
        pool_pre_ping=False,
        pool_recycle=1800,
    )
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    app.state.engine = engine
    app.state.session_maker = session_maker

    # Wire existing session factory to this engine
    init_session_factory(engine)

    # Initialize RAG engine lazily here (after env is loaded)
    global query_engine
    query_engine = PostgreSQLMedicalQueryEngine()

    # Bind B2B usage meter to the DB session factory
    b2b_meter.bind(session_maker)

    _dev_bypass = os.getenv("DEV_AUTH_BYPASS", "").lower() == "true" and APP_ENV != "production"

    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection initialized successfully")
        db_ok = True
    except Exception as _db_err:
        if _dev_bypass:
            logger.warning(
                "DEV_AUTH_BYPASS: DB unreachable (%s). "
                "Server starting without DB — DB-dependent endpoints will return 503.",
                _db_err,
            )
        else:
            raise

    # asyncpg pool for PTV / vault (must run in lifespan — legacy on_event("startup")
    # is not guaranteed to run before traffic when lifespan is configured).
    global _pool
    app.state.pool = None
    _pool = None
    if db_ok:
        pool_dsn = (os.getenv("POSTGRES_DSN") or "").strip() or _asyncpg_dsn_for_pool(raw_url)
        try:
            pool = await asyncpg.create_pool(
                dsn=pool_dsn,
                min_size=1,
                max_size=int(os.getenv("PGPOOL_MAX", "10")),
                command_timeout=60,
            )
            app.state.pool = pool
            _pool = pool
            logger.info("asyncpg pool attached for PTV / vault timeline routes")
        except Exception as pool_err:
            if _dev_bypass:
                logger.warning(
                    "asyncpg pool unavailable (%s). "
                    "Set POSTGRES_DSN or ensure DATABASE_URL is reachable by asyncpg. "
                    "PTV ingest will return 503 until fixed.",
                    pool_err,
                )
            else:
                raise

    try:
        await b2b_meter.start()
        logger.info("B2B usage meter started")
    except Exception as _meter_err:
        if _dev_bypass:
            logger.warning("DEV_AUTH_BYPASS: B2B meter skipped (%s).", _meter_err)
        else:
            raise

    try:
        yield
    finally:
        try:
            await b2b_meter.stop()
        except Exception:
            pass
        pool = getattr(app.state, "pool", None)
        if pool is not None:
            try:
                await pool.close()
            except Exception as close_err:
                logger.warning("asyncpg pool close: %s", close_err)
            app.state.pool = None
            _pool = None
            logger.info("asyncpg pool closed")
        await engine.dispose()
        logger.info("DB engine disposed")


app = FastAPI(
    title="2ndOpinionMD API",
    description="API for 2ndOpinionMD medical diagnosis",
    lifespan=lifespan,
)


async def get_pool():
    """Return the shared asyncpg pool (created in lifespan)."""
    global _pool
    if _pool is None:
        dsn = (os.getenv("POSTGRES_DSN") or "").strip()
        if not dsn:
            raw = os.getenv("DATABASE_URL") or os.getenv("SYNC_DATABASE_URL") or ""
            if raw.startswith("postgresql://") and "+asyncpg" not in raw:
                raw = raw.replace("postgresql://", "postgresql+asyncpg://", 1)
            dsn = _asyncpg_dsn_for_pool(raw) if raw else "postgresql://localhost/2ndopinionmd"
        _pool = await asyncpg.create_pool(
            dsn=dsn,
            min_size=1,
            max_size=int(os.getenv("PGPOOL_MAX", "10")),
            command_timeout=60,
        )
    return _pool


# --- CORS (safe with credentials) ---------------------------------------------
# If you need wildcard origins, set allow_credentials=False.
_default_origins = ",".join([
    "https://2ndopinionmd.ai",
    "http://localhost:3000",       # existing
    "http://localhost:8010",       # demo UI
    "http://127.0.0.1:8010",       # demo UI
    "http://192.168.0.108:8010",   # replace with your actual LAN IP for others to connect
    # You can add "http://<your-public-ip>:8010" here if exposing publicly
])

_allowed_origins = os.getenv(
    "CORS_ALLOW_ORIGINS",
    "https://2ndopinionmd.ai,http://upload.2ndopinionmd.ai:8000,http://localhost:3000,http://localhost:8080,http://127.0.0.1:8010,http://localhost:8010"
)
allow_origins = [o.strip() for o in _allowed_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Mount routers -------------------------------------------------------------
app.include_router(auth_router,   prefix="/api/auth",    tags=["authentication"])
app.include_router(session_router, prefix="/api/session", tags=["session"])
app.include_router(session_timeline_router, prefix="/api/timeline", tags=["timeline"])  # POST /api/timeline/initialize
app.include_router(doctor_router, prefix="/api/doctor", tags=["doctor"])
app.include_router(patient_router, prefix="/api/patient", tags=["patient"])
app.include_router(portal_router, prefix="/api/portal", tags=["portal"])
app.include_router(journal_router, prefix="/api/journal", tags=["journal"])
app.include_router(chat_graph_router, prefix="/api/chat", tags=["chat"])

# --- MKG ontology routers (API-key gated: mkg:read) --------------------------
app.include_router(loinc_router, dependencies=_MKG_READ_AUTH)
app.include_router(snomed_router, dependencies=_MKG_READ_AUTH)
app.include_router(rxnorm_router, dependencies=_MKG_READ_AUTH)
app.include_router(orphanet_router, dependencies=_MKG_READ_AUTH)
app.include_router(chv_router, dependencies=_MKG_READ_AUTH)
app.include_router(hpo_router, dependencies=_MKG_READ_AUTH)
app.include_router(clingen_actionability_router, dependencies=_MKG_READ_AUTH)
app.include_router(mimic3_router, dependencies=_MKG_READ_AUTH)
app.include_router(mimic4_router, dependencies=_MKG_READ_AUTH)
app.include_router(notes_router, dependencies=_MKG_READ_AUTH)
app.include_router(panelapp_router, dependencies=_MKG_READ_AUTH)
app.include_router(guidelines_router, dependencies=_MKG_READ_AUTH)
app.include_router(diagnostic_rules_routes.router, dependencies=_MKG_READ_AUTH)
app.include_router(disgenet_router, dependencies=_MKG_READ_AUTH)
app.include_router(gwas_router, dependencies=_MKG_READ_AUTH)
app.include_router(neurolex_router, dependencies=_MKG_READ_AUTH)
app.include_router(neurolex_xref_router, dependencies=_MKG_READ_AUTH)
app.include_router(who_routes.router, dependencies=_MKG_READ_AUTH)
app.include_router(cdc_opioid_router,
                    prefix="/api/guidelines/cdc/opioid",
                    tags=["guidelines.cdc.opioid"],
                    dependencies=_MKG_READ_AUTH)
app.include_router(va_router, dependencies=_MKG_READ_AUTH)
app.include_router(kg_router, dependencies=_MKG_READ_AUTH)

# --- Frontend-facing RAG/evidence/EoH routers (open — session auth where needed) ---
# These serve the web app at 2ndopinionmd.ai.  External programmatic access
# goes through /v1/mkg/evidence/ (B2B-gated via b2b_mkg_router above).
app.include_router(rag_router)
app.include_router(coding_router)
app.include_router(ask_eoh_router)
app.include_router(rag_ask_router)
app.include_router(ask_compat_v2_router)
app.include_router(coding_v2_router)
app.include_router(rag_stream_router)
app.include_router(llm_stream_router)
app.include_router(rag_stream_custom_router)
app.include_router(eoh_router_router)
app.include_router(eoh_demo_routes.router)

# --- Frontend-facing PTV/timeline routers (open — session auth where needed) ---
app.include_router(timeline_router)
app.include_router(timeline_analytics_router)
app.include_router(ptv_analytics_router)
app.include_router(timeline_infer_router)
app.include_router(graph_query_router)

# --- FORWARD (own bearer token auth, no B2B key) ----------------------------
app.include_router(forward_infer_router)

# --- Internal / utility (no API key) ----------------------------------------
app.include_router(printer_router)
app.include_router(audio_router)

# --- B2B /v1/ routers (API-key authenticated) ---------------------------------
app.include_router(b2b_mkg_router)
app.include_router(b2b_evidence_router)
app.include_router(b2b_health_router)

# --- B2B usage logging middleware (must be before other middleware) ------------
app.add_middleware(B2BUsageMiddleware)

# --- Middlewares---------------------------------------------------------------
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """First: log all requests and durations (even blocked ones below)."""
    import time
    start = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    except HTTPException:
        raise
    except Exception:
        logger.exception("Unhandled error")
        raise
    finally:
        dur_ms = (time.perf_counter() - start) * 1000
        logger.info("Request: %s %s -> %sms", request.method, request.url.path, f"{dur_ms:.2f}")


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """
    Block common sensitive paths (defensive hardening).
    Uses anchored regexes to avoid over-matching.
    """
    path = request.url.path
    blocked_patterns = [
        r"^/\.env$", r"^/\.git(/|$)", r"^/\.config(/|$)", r"^/\.aws(/|$)", r"^/\.ssh(/|$)",
        r"^/wp-login\.php$", r"^/wp-admin(/|$)", r"^/admin$", r"^/phpinfo\.php$", r"^/config\.php$",
    ]
    for pattern in blocked_patterns:
        if re.search(pattern, path, flags=re.IGNORECASE):
            client_ip = get_client_ip(request)
            logger.warning("Blocked suspicious request: %s %s from %s", request.method, request.url, client_ip)
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"},
            )
    return await call_next(request)


@app.exception_handler(status.HTTP_429_TOO_MANY_REQUESTS)
async def rate_limit_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": str(exc.detail)},
        headers={"Retry-After": request.headers.get("Retry-After", "60")},
    )


# --- Diagnose endpoints --------------------------------------------------------
class SymptomRequest(BaseModel):
    symptoms: List[str]
    demographics: Optional[Dict[str, Any]] = None
    model: str = "gpt-3.5-turbo"

class DiagnosisResponse(BaseModel):  # keep for the /api/diagnosis alias
    diagnoses: List[Dict[str, Any]]


@app.post("/api/diagnose", response_model=DiagnoseResponse)
async def diagnose(
    request: SymptomRequest = Body(...),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(diagnose_rate_limiter),
):
    """
    Generate a diagnosis based on symptoms and optional demographics
    """
    import time
    start_time = time.perf_counter()
    try:
        logger.info("Diagnose request: symptoms=%s demographics=%s model=%s",
                    len(request.symptoms) if request.symptoms else 0,
                    bool(request.demographics), request.model)

        if not request.symptoms or not isinstance(request.symptoms, list):
            raise HTTPException(
                status_code=400,
                detail={"code": "invalid_symptoms", "message": "Invalid symptoms format. Provide a list of strings."},
            )
        if len(request.symptoms) > 50:
            raise HTTPException(
                status_code=400,
                detail={"code": "too_many_symptoms", "message": "Maximum 50 symptoms allowed per request."},
            )
        for i, s in enumerate(request.symptoms):
            if not isinstance(s, str):
                raise HTTPException(400, {"code": "invalid_symptom_type", "message": f"Symptom {i} must be a string."})
            if len(s) > 500:
                raise HTTPException(400, {"code": "symptom_too_long", "message": f"Symptom {i} exceeds 500 chars."})
            if not s.strip():
                raise HTTPException(400, {"code": "empty_symptom", "message": f"Symptom {i} is empty."})

        # Generate RAG response (engine created in lifespan)
        global query_engine
        if query_engine is None:
            raise HTTPException(500, {"code": "engine_not_ready", "message": "Query engine not initialized."})

        response = await query_engine.generate_rag_response(
            symptoms=request.symptoms,
            session=session,
            model=request.model,
            demographics=request.demographics,
        )

        if isinstance(response, str):
            try:
                response_data = json.loads(response)
            except json.JSONDecodeError:
                response_data = {
                    "diagnoses": [{
                        "diagnosis": response,
                        "confidence_score": None,
                        "icd_10_code": None,
                        "recommendations": None,
                    }]
                }
        else:
            response_data = response

        if "diagnoses" not in response_data:
            response_data = {"diagnoses": []}

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info("Diagnose response generated successfully in %.2fms", duration_ms)

        validated = DiagnoseResponse.model_validate(response_data)
        return validated.model_dump(by_alias=False)

    except HTTPException:
        raise
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error("Error generating diagnosis in %.2fms: %s", duration_ms, str(e))
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail={"code": "diagnosis_error", "message": f"Error generating diagnosis: {str(e)}"},
        )


@app.post("/api/diagnosis", response_model=DiagnosisResponse, include_in_schema=False)
async def diagnose_alias(
    request: SymptomRequest = Body(...),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(diagnose_rate_limiter),
):
    """
    Deprecated alias for /api/diagnose
    """
    logger.warning("Deprecated path hit: /api/diagnosis (use /api/diagnose)")
    # Delegate to /api/diagnose implementation
    resp = await diagnose(request, session, None)  # type: ignore[arg-type]
    # Normalize to DiagnosisResponse shape if needed
    if isinstance(resp, dict) and "diagnoses" in resp:
        return resp
    return {"diagnoses": []}


# --- Health & OpenAPI compatibility -------------------------------------------
@app.get("/", include_in_schema=False)
async def serve_epistemic_vault_root():
    """Serve the Epistemic Vault single-page HTML (not the React SPA)."""
    path = project_root / "index.html"
    if path.is_file():
        return FileResponse(path, media_type="text/html; charset=utf-8")
    raise HTTPException(status_code=404, detail="index.html not found")


@app.get("/index.html", include_in_schema=False)
async def serve_epistemic_vault_index_named():
    path = project_root / "index.html"
    if path.is_file():
        return FileResponse(path, media_type="text/html; charset=utf-8")
    raise HTTPException(status_code=404, detail="index.html not found")


@app.get("/patient_portal.html", include_in_schema=False)
async def patient_portal_redirect_to_vault():
    """Legacy URL: patient UX now lives on ``/`` (Epistemic Vault ``index.html``)."""
    return RedirectResponse(url="/", status_code=302)


@app.get("/api/health")
async def health_check(session: AsyncSession = Depends(get_session)):
    """
    Health check endpoint
    """
    try:
        await session.execute(text("SELECT 1"))
        postgres_status = "ok"
    except Exception as e:
        logger.warning("Health check DB connection failed: %s", e)
        postgres_status = "error"

    return {
        "status": "ok",
        "services": {
            "api": "ok",
            "postgresql": postgres_status,
            "pgvector": "ok" if query_engine else "error",
        },
    }

@app.get("/api/meta/ping")
async def ping():
    return {"status": "pong"}

# IMPORTANT: expose OpenAPI also under /api/openapi.json for your Makefile target
@app.get("/api/openapi.json", include_in_schema=False)
async def openapi_json():
    return app.openapi()


# --- Entrypoint ---------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    # Run with direct app reference to avoid import string mistakes
    uvicorn.run(app, host=host, port=port, reload=True)

