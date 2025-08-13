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

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from nlp_engines.vector_stores.postgresql_query_engine import PostgreSQLMedicalQueryEngine
from server.utils.rate_limiter import general_rate_limiter, get_client_ip
from server.utils.encrypted_logging import setup_encrypted_logging

from server.api.auth import router as auth_router
from server.api.journal import router as journal_router

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize encrypted logging
setup_encrypted_logging()

app = FastAPI(
    title="2ndOpinionMD API",
    description="AI-powered second opinion platform for autoimmune disease diagnosis",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://2ndopinionmd.ai"],
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
    """Security middleware to block suspicious requests"""
    path = request.url.path
    
    # Block access to sensitive files and paths
    blocked_paths = [
        "/.env", "/.git", "/.htaccess", "/wp-config.php", "/config.php",
        "/admin", "/administrator", "/phpmyadmin", "/mysql", "/sql",
        "/.well-known", "/robots.txt", "/sitemap.xml"
    ]
    
    for blocked_path in blocked_paths:
        if blocked_path in path:
            logger.warning(f"Blocked access to sensitive path: {path} from {request.client.host}")
            return JSONResponse(
                status_code=403,
                content={"detail": "Access forbidden"}
            )
    
    # Block common scanning patterns
    user_agent = request.headers.get("user-agent", "").lower()
    if any(pattern in user_agent for pattern in ["bot", "crawler", "spider", "scanner"]):
        logger.warning(f"Blocked bot/crawler access: {user_agent} from {request.client.host}")
        return JSONResponse(
            status_code=403,
            content={"detail": "Access forbidden"}
        )
    
    response = await call_next(request)
    return response

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests for monitoring"""
    client_ip = get_client_ip(request)
    logger.info(f"Request: {request.method} {request.url.path} from {client_ip}")
    
    response = await call_next(request)
    
    logger.info(f"Response: {response.status_code} for {request.method} {request.url.path}")
    return response

@app.exception_handler(status.HTTP_429_TOO_MANY_REQUESTS)
async def rate_limit_exception_handler(request: Request, exc: HTTPException):
    """Handle rate limit exceeded responses"""
    retry_after = exc.headers.get("Retry-After", "60")
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Rate limit exceeded. Please try again later.",
            "retry_after": retry_after
        },
        headers={"Retry-After": retry_after}
    )

@app.post("/api/diagnose", response_model=DiagnosisResponse)
async def diagnose(
    request: SymptomRequest = Body(...),
    _: None = Depends(general_rate_limiter)
):
    """
    Generate a diagnosis based on symptoms and optional demographics
    """
    try:
        # Log the request
        logger.info(f"Diagnosis request received with {len(request.symptoms)} symptoms")
        
        # Query the medical database
        query_text = " ".join(request.symptoms)
        if request.demographics:
            query_text += f" {json.dumps(request.demographics)}"
        
        # Get results from the query engine
        results = await query_engine.query_all_collections(query_text)
        
        # Process and format the results
        diagnoses = []
        if results:
            for collection_name, collection_results in results.items():
                for result in collection_results[:5]:  # Limit to top 5 results per collection
                    diagnoses.append({
                        "name": result.get("name", "Unknown Condition"),
                        "confidence": result.get("confidence", 50),
                        "description": result.get("text", ""),
                        "source": collection_name,
                        "recommendations": result.get("recommendations", []),
                        "red_flags": result.get("red_flags", [])
                    })
        
        # Sort by confidence
        diagnoses.sort(key=lambda x: x["confidence"], reverse=True)
        
        logger.info(f"Generated {len(diagnoses)} diagnoses")
        return DiagnosisResponse(diagnoses=diagnoses)
        
    except Exception as e:
        logger.error(f"Error in diagnosis endpoint: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail="Internal server error during diagnosis generation"
        )

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint
    """
    return {
        "status": "ok",
        "services": {
            "api": "ok",
            "postgresql": "ok"
        }
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=3001)
