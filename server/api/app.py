import os
import json
from typing import List, Dict, Any
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
from dotenv import load_dotenv
import uvicorn
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vectordb.query_engine import MedicalQueryEngine

load_dotenv()

app = FastAPI(title="2ndOpinionMD API", description="API for 2ndOpinionMD medical diagnosis")

persist_directory = os.getenv("CHROMA_PERSIST_DIR", "./chroma_db")
query_engine = MedicalQueryEngine(persist_directory)

class SymptomRequest(BaseModel):
    symptoms: List[str]
    model: str = "gpt-3.5-turbo"

class DiagnosisResponse(BaseModel):
    diagnoses: List[Dict[str, Any]]

@app.post("/api/diagnose", response_model=DiagnosisResponse)
async def diagnose(request: SymptomRequest = Body(...)):
    """
    Generate a diagnosis based on symptoms
    """
    try:
        response = query_engine.generate_rag_response(request.symptoms, request.model)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating diagnosis: {str(e)}")

@app.get("/api/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=3001, reload=True)
