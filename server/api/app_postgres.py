import os
import json
import logging
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Body, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
import sys
import traceback
from sqlalchemy import text

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.vectordb.postgresql_query_engine import PostgreSQLMedicalQueryEngine
from server.db.session import SessionLocal, engine
from database.models.postgresql.models import User as UserInDB
from server.utils.rate_limiter import general_rate_limiter, diagnose_rate_limiter, get_client_ip
from server.utils.encrypted_logging import setup_encrypted_logging
from sqlalchemy.ext.asyncio import AsyncSession
from server.db.session import get_session

from server.api.journal import router as journal_router
from server.api.auth_routes_postgres import router as auth_router
from server.api.auth_postgres import get_current_user_postgres
from server.api.schemas import DiagnoseResponse
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

setup_encrypted_logging(
    log_dir=os.environ.get('LOG_DIR', './logs'),
    log_level=logging.INFO,
    console_logging=True
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("DB warmup OK")
    except Exception:
        logger.exception("DB warmup failed")
    yield
    try:
        await engine.dispose()
        logger.info("DB engine disposed")
    except Exception:
        logger.exception("DB dispose failed")

app = FastAPI(
    title="2ndOpinionMD API", 
    description="API for 2ndOpinionMD medical diagnosis",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])
app.include_router(journal_router, prefix="/api/journal", tags=["journal"])

query_engine = PostgreSQLMedicalQueryEngine()

class SymptomRequest(BaseModel):
    symptoms: List[str]
    demographics: Optional[Dict[str, Any]] = None
    model: str = "gpt-3.5-turbo"

class DiagnosisResponse(BaseModel):
    diagnoses: List[Dict[str, Any]]

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """
    Middleware to block access to sensitive files and paths
    """
    path = request.url.path.lower()
    
    blocked_patterns = [
        "/.env", 
        "/.git", 
        "/.config", 
        "/.aws", 
        "/.ssh",
        "/wp-login.php",
        "/wp-admin",
        "/admin",
        "/phpinfo.php",
        "/config.php",
    ]
    
    for pattern in blocked_patterns:
        if pattern in path:
            client_ip = get_client_ip(request)
            logger.warning(f"Blocked suspicious request: {request.method} {request.url} from {client_ip}")
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "Access denied"}
            )
    
    return await call_next(request)

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Middleware to log all requests and handle exceptions
    """
    import time
    start = time.perf_counter()
    try:
        response = await call_next(request)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Unhandled error")
        raise
    finally:
        dur_ms = (time.perf_counter() - start) * 1000
        logger.info("Request: %s %s -> %sms", request.method, request.url.path, f"{dur_ms:.2f}")

@app.exception_handler(status.HTTP_429_TOO_MANY_REQUESTS)
async def rate_limit_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": str(exc.detail)},
        headers={"Retry-After": request.headers.get("Retry-After", "60")}
    )


@app.post("/api/diagnose", response_model=DiagnoseResponse)
async def diagnose(
    request: SymptomRequest = Body(...),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(diagnose_rate_limiter)
):
    """
    Generate a diagnosis based on symptoms and optional demographics
    """
    return await _diagnose_handler(request, session)

@app.post("/api/diagnosis", response_model=DiagnosisResponse, include_in_schema=False)
async def diagnose_alias(
    request: SymptomRequest = Body(...),
    session: AsyncSession = Depends(get_session),
    _: None = Depends(diagnose_rate_limiter)
):
    """
    Deprecated alias for /api/diagnose
    """
    logger.warning("Deprecated path hit: /api/diagnosis (use /api/diagnose)")
    return await _diagnose_handler(request, session)

async def _diagnose_handler(
    request: SymptomRequest,
    session: AsyncSession
):
    """
    Generate a diagnosis based on symptoms and optional demographics
    """
    import time
    start_time = time.perf_counter()
    
    try:
        logger.info(f"Diagnose request: symptoms={len(request.symptoms) if request.symptoms else 0} symptoms")
        logger.info(f"Diagnose request: demographics={bool(request.demographics)}")
        logger.info(f"Diagnose request: model={request.model}")
        
        if not request.symptoms or not isinstance(request.symptoms, list):
            logger.error(f"Invalid symptoms format: {type(request.symptoms)}")
            raise HTTPException(
                status_code=400, 
                detail={"code": "invalid_symptoms", "message": "Invalid symptoms format. Please provide a list of symptom strings."}
            )
        
        if len(request.symptoms) > 50:
            logger.error(f"Too many symptoms: {len(request.symptoms)}")
            raise HTTPException(
                status_code=400,
                detail={"code": "too_many_symptoms", "message": "Maximum 50 symptoms allowed per request."}
            )
        
        for i, symptom in enumerate(request.symptoms):
            if not isinstance(symptom, str):
                logger.error(f"Invalid symptom type at index {i}: {type(symptom)}")
                raise HTTPException(
                    status_code=400,
                    detail={"code": "invalid_symptom_type", "message": "All symptoms must be strings."}
                )
            if len(symptom) > 500:
                logger.error(f"Symptom too long at index {i}: {len(symptom)} chars")
                raise HTTPException(
                    status_code=400,
                    detail={"code": "symptom_too_long", "message": "Each symptom must be 500 characters or less."}
                )
            if len(symptom.strip()) == 0:
                logger.error(f"Empty symptom at index {i}")
                raise HTTPException(
                    status_code=400,
                    detail={"code": "empty_symptom", "message": "Symptoms cannot be empty."}
                )
        
        response = await query_engine.generate_rag_response(
            symptoms=request.symptoms, 
            session=session,
            model=request.model,
            demographics=request.demographics
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
                        "recommendations": None
                    }]
                }
        else:
            response_data = response
            
        if "diagnoses" not in response_data:
            response_data = {"diagnoses": []}
            
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info(f"Diagnose response generated successfully in {duration_ms:.2f}ms")
        
        validated_response = DiagnoseResponse.model_validate(response_data)
        logger.info(f"Validated response: {validated_response.model_dump()}")
        
        return validated_response.model_dump(by_alias=False)
    except HTTPException as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        error_code = e.detail.get("code", "unknown") if isinstance(e.detail, dict) else "http_error"
        logger.error(f"Diagnose request failed with {e.status_code} ({error_code}) in {duration_ms:.2f}ms")
        raise
    except Exception as e:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(f"Error generating diagnosis in {duration_ms:.2f}ms: {str(e)}")
        logger.error(traceback.format_exc())
        
        raise HTTPException(
            status_code=500, 
            detail={"code": "diagnosis_error", "message": f"Error generating diagnosis: {str(e)}"}
        )

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint
    """
    try:
        async with SessionLocal() as session:
            await session.execute(text("SELECT 1"))
        postgres_status = "ok"
    except Exception as e:
        logger.warning(f"Health check DB connection failed: {e}")
        postgres_status = "error"
    
    return {
        "status": "ok",
        "services": {
            "api": "ok",
            "postgresql": postgres_status,
            "pgvector": "ok" if query_engine else "error"
        }
    }

@app.get("/api/meta/ping")
async def ping():
    """
    Simple ping endpoint
    """
    return {"status": "pong"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("api.app_postgres:app", host=host, port=port, reload=True)
