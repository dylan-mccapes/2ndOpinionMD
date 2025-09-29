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
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

# --- sys.path & env -----------------------------------------------------------
server_dir = Path(__file__).resolve().parent.parent
env_path = server_dir / ".env"
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
from server.api.auth_routes_postgres import router as auth_router

from server.api.loinc_routes import router as loinc_router
from server.api.snomed_routes import router as snomed_router
from server.api.rxnorm_routes import router as rxnorm_router
from server.api.orphanet_routes import router as orphanet_router
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

from server.api.kg import router as kg_router

from server.api.schemas import DiagnoseResponse


# --- lifespan: init async engine + session + RAG engine -----------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    from server.db.session import DATABASE_URL
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=False,
        pool_recycle=1800,
    )
    session_maker = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)
    app.state.engine = engine
    app.state.session_maker = session_maker
    init_session_factory(engine)

    # Initialize RAG engine lazily here (after env is loaded)
    global query_engine
    query_engine = PostgreSQLMedicalQueryEngine()

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection initialized successfully")
        yield
    finally:
        await engine.dispose()
        logger.info("DB engine disposed")


app = FastAPI(
    title="2ndOpinionMD API",
    description="API for 2ndOpinionMD medical diagnosis",
    lifespan=lifespan,
)

# psycopg2 pool for sync endpoints
@app.on_event("startup")
def _startup():
    init_pool(minconn=1, maxconn=8)


# --- CORS (safe with credentials) ---------------------------------------------
# If you need wildcard origins, set allow_credentials=False.
_allowed_origins = os.getenv("CORS_ALLOW_ORIGINS", "https://2ndopinionmd.ai,http://localhost:3000")
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
app.include_router(journal_router, prefix="/api/journal", tags=["journal"])

app.include_router(loinc_router)
app.include_router(snomed_router)
app.include_router(rxnorm_router)
app.include_router(orphanet_router)
app.include_router(hpo_router)
app.include_router(clingen_actionability_router)

app.include_router(mimic3_router)
app.include_router(mimic4_router)
app.include_router(notes_router)
app.include_router(panelapp_router)
app.include_router(guidelines_router)
app.include_router(diagnostic_rules_routes.router)
app.include_router(disgenet_router)
app.include_router(gwas_router)
app.include_router(neurolex_router)
app.include_router(neurolex_xref_router)
app.include_router(rag_router)
app.include_router(who_routes.router)

app.include_router(kg_router)

# --- Middlewares ---------------------------------------------------------------
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

