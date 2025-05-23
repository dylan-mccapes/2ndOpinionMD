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

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vectordb.query_engine import MedicalQueryEngine
from models.mongodb.database import ping_database
from models.mongodb.auth import get_current_user
from models.mongodb.models import UserInDB
from utils.rate_limiter import general_rate_limiter, get_client_ip
from utils.encrypted_logging import setup_encrypted_logging

from api.auth import router as auth_router
from api.journal import router as journal_router

load_dotenv()

setup_encrypted_logging(
    log_dir=os.environ.get('LOG_DIR', './logs'),
    log_level=logging.INFO,
    console_logging=True
)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="2ndOpinionMD API", description="API for 2ndOpinionMD medical diagnosis")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])
app.include_router(journal_router, prefix="/api/journal", tags=["journal"])

persist_directory = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
query_engine = MedicalQueryEngine(persist_directory)

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
        "/wp-login.php",  # Common WordPress attack vector
        "/wp-admin",      # Common WordPress attack vector
        "/admin",         # Common admin panel paths
        "/phpinfo.php",   # PHP info disclosure
        "/config.php",    # Common config files
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

@app.post("/api/diagnose", response_model=DiagnosisResponse)
async def diagnose(
    request: SymptomRequest = Body(...),
    current_user: UserInDB = Depends(get_current_user),
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
        
        response = query_engine.generate_rag_response(
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
    mongo_status = "ok" if await ping_database() else "error"
    
    return {
        "status": "ok",
        "services": {
            "api": "ok",
            "mongodb": mongo_status,
            "chroma": "ok" if query_engine.collections else "error"
        }
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
