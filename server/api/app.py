import os
import json
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vectordb.query_engine import MedicalQueryEngine
from models.mongodb.database import ping_database
from models.mongodb.auth import get_current_user
from models.mongodb.models import UserInDB

from api.auth import router as auth_router
from api.journal import router as journal_router

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

@app.post("/api/diagnose", response_model=DiagnosisResponse)
async def diagnose(
    request: SymptomRequest = Body(...),
    current_user: UserInDB = Depends(get_current_user)
):
    """
    Generate a diagnosis based on symptoms and optional demographics
    """
    try:
        response = query_engine.generate_rag_response(
            symptoms=request.symptoms, 
            model=request.model,
            demographics=request.demographics
        )
        return response
    except Exception as e:
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
            "mongodb": mongo_status
        }
    }

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=3001, reload=True)
