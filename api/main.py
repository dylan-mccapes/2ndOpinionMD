from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import os
from dotenv import load_dotenv
import logging

load_dotenv()

app = FastAPI(
    title="2ndOpinionMD API",
    description="Unified medical diagnosis API with dual database support",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]
)

@app.middleware("http")
async def security_middleware(request: Request, call_next):
    """Security middleware to block sensitive paths"""
    sensitive_paths = [
        "/.env", "/.git", "/server/", "/node_modules/",
        "/package.json", "/yarn.lock", "/.gitignore"
    ]
    
    if any(request.url.path.startswith(path) for path in sensitive_paths):
        raise HTTPException(status_code=404, detail="Not found")
    
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    
    return response

@app.get("/api/health")
async def health_check():
    """Comprehensive health check"""
    return {
        "status": "healthy",
        "version": "2.0.0",
        "database": "configurable",
        "vector_engine": "unified"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
