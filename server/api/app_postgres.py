import os
import json
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Body, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
import sys
import traceback

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from server.vectordb.postgresql_query_engine import PostgreSQLMedicalQueryEngine
from database.models.postgresql.database import init_db, ping_database
from database.models.postgresql.models import User as UserInDB
from server.utils.rate_limiter import general_rate_limiter, get_client_ip
from server.utils.encrypted_logging import setup_encrypted_logging

from server.api.journal import router as journal_router
from server.api.auth_routes_postgres import router as auth_router
from server.api.auth_postgres import get_current_user_postgres
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

setup_encrypted_logging(
    log_dir=os.environ.get('LOG_DIR', './logs'),
    log_level=logging.INFO,
    console_logging=True
)
logger = logging.getLogger(__name__)

app = FastAPI(title="2ndOpinionMD API", description="API for 2ndOpinionMD medical diagnosis")

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
    demographics: Dict[str, Any] = None
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
    try:
        logger.info(f"Request: {request.method} {request.url}")
        
        response = await call_next(request)
        
        logger.info(f"Response: {response.status_code}")
        
        return response
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(traceback.format_exc())
        
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.exception_handler(status.HTTP_429_TOO_MANY_REQUESTS)
async def rate_limit_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": str(exc.detail)},
        headers={"Retry-After": request.headers.get("Retry-After", "60")}
    )

@app.on_event("startup")
async def startup_event():
    try:
        await init_db()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
        logger.info("Continuing without database initialization...")

@app.post("/api/diagnose", response_model=DiagnosisResponse)
async def diagnose(
    request: SymptomRequest = Body(...),
    current_user: UserInDB = Depends(get_current_user_postgres),
    _: None = Depends(general_rate_limiter)
):
    """
    Generate a diagnosis based on symptoms and optional demographics
    """
    try:
        logger.info(f"Diagnose request: symptoms={request.symptoms}")
        logger.info(f"Diagnose request: demographics={request.demographics}")
        logger.info(f"Diagnose request: model={request.model}")
        
        if not request.symptoms or not isinstance(request.symptoms, list):
            logger.error(f"Invalid symptoms format: {request.symptoms}")
            raise HTTPException(status_code=400, detail="Invalid symptoms format. Please provide a list of symptom strings.")
        
        response = await query_engine.generate_rag_response(
            symptoms=request.symptoms, 
            model=request.model,
            demographics=request.demographics
        )
        
        logger.info(f"Diagnose response: {response}")
        
        return response
    except Exception as e:
        logger.error(f"Error generating diagnosis: {str(e)}")
        logger.error(traceback.format_exc())
        
        raise HTTPException(status_code=500, detail=f"Error generating diagnosis: {str(e)}")

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint
    """
    postgres_status = "ok" if await ping_database() else "error"
    
    return {
        "status": "ok",
        "services": {
            "api": "ok",
            "postgresql": postgres_status,
            "pgvector": "ok" if query_engine else "error"
        }
    }

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("api.app_postgres:app", host=host, port=port, reload=True)
