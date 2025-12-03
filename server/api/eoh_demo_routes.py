# server/api/eoh_demo_routes.py
"""
FastAPI router for EoH demo endpoints.
Provides access to synthetic RA patient data for the EoH demo UI.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from server.api.eoh_demo_data import (
    DEMO_PATIENTS,
    DEMO_TIMELINES,
    get_patient,
    get_patient_list,
    get_timeline,
)

router = APIRouter(prefix="/api/eoh_demo", tags=["eoh-demo"])


class HypotheticalChange(BaseModel):
    ts: str
    kind: str
    severity: Optional[str] = None
    summary: str
    details: Optional[Dict[str, Any]] = None


class HypotheticalRequest(BaseModel):
    base_patient_id: str
    changes: List[HypotheticalChange]


@router.get("/patients")
async def list_patients() -> List[Dict[str, str]]:
    """
    Return a list of {id, label, summary} for all demo patients.
    """
    return get_patient_list()


@router.get("/patient_state/{patient_id}")
async def get_patient_state(patient_id: str) -> Dict[str, Any]:
    """
    Return a patient_state JSON suitable for EoH questions.
    
    The patient_state includes:
    - Basic demographics (age, sex, diagnosis)
    - Current medications
    - Recent flare history
    - Recent DAS28 scores
    - Recent labs
    - Recent journal entries
    """
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    
    timeline = get_timeline(patient_id)
    
    recent_journal = [
        {"date": e["ts"][:10], "text": e["details"].get("text", e["summary"])}
        for e in timeline
        if e["kind"] == "journal"
    ][-5:]
    
    recent_das28 = patient.get("das28_history", [])[:3]
    
    return {
        "patient_id": patient["id"],
        "age": patient["age"],
        "sex": patient["sex"],
        "diagnosis": patient["diagnosis"],
        "terrain": "chronic autoimmune inflammatory arthritis",
        "serostatus": patient["serostatus"],
        "current_meds": patient["meds"],
        "recent_flare_history": patient["recent_flares"],
        "recent_das28": recent_das28[0] if recent_das28 else None,
        "das28_trend": recent_das28,
        "recent_labs": patient["recent_labs"][:3],
        "recent_journal": recent_journal,
        "journal_highlights": patient["journal_highlights"],
        "summary": patient["summary"],
    }


@router.get("/timeline/{patient_id}")
async def get_patient_timeline(
    patient_id: str,
    max_events: int = Query(200, ge=1, le=500, description="Maximum number of events to return"),
) -> List[Dict[str, Any]]:
    """
    Return the full chronological list of events for a patient.
    Events are returned in chronological order (oldest first).
    """
    if patient_id not in DEMO_PATIENTS:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    
    timeline = get_timeline(patient_id, max_events)
    return timeline


@router.post("/hypothetical")
async def create_hypothetical(request: HypotheticalRequest) -> Dict[str, Any]:
    """
    Create a hypothetical patient_state by applying changes to a base patient.
    
    This endpoint accepts a base_patient_id and a list of changes (e.g., a new flare),
    then returns a derived patient_state that reflects those changes.
    
    Example request:
    {
        "base_patient_id": "P1",
        "changes": [
            {
                "ts": "2025-09-01T08:00:00Z",
                "kind": "flare",
                "severity": "moderate",
                "summary": "New flare knees/wrists"
            }
        ]
    }
    """
    patient = get_patient(request.base_patient_id)
    if not patient:
        raise HTTPException(
            status_code=404, 
            detail=f"Base patient {request.base_patient_id} not found"
        )
    
    timeline = get_timeline(request.base_patient_id)
    
    recent_journal = [
        {"date": e["ts"][:10], "text": e["details"].get("text", e["summary"])}
        for e in timeline
        if e["kind"] == "journal"
    ][-5:]
    
    recent_das28 = patient.get("das28_history", [])[:3]
    
    modified_flares = list(patient["recent_flares"])
    modified_labs = list(patient["recent_labs"])
    modified_das28 = list(recent_das28)
    
    for change in request.changes:
        if change.kind == "flare":
            new_flare = {
                "date": change.ts[:10],
                "severity": change.severity or "moderate",
                "joints": change.details.get("joints", ["unspecified"]) if change.details else ["unspecified"],
                "duration_days": change.details.get("duration_days", 7) if change.details else 7,
                "hypothetical": True,
            }
            modified_flares.insert(0, new_flare)
            
            if modified_labs:
                latest_lab = dict(modified_labs[0])
                latest_lab["date"] = change.ts[:10]
                latest_lab["CRP"] = min(latest_lab.get("CRP", 10) * 2.5, 60)
                latest_lab["ESR"] = min(latest_lab.get("ESR", 20) * 2, 80)
                latest_lab["hypothetical"] = True
                modified_labs.insert(0, latest_lab)
            
            if modified_das28:
                latest_das28 = dict(modified_das28[0])
                latest_das28["date"] = change.ts[:10]
                severity_bump = {"mild": 0.5, "moderate": 1.2, "severe": 2.0}.get(
                    change.severity or "moderate", 1.0
                )
                latest_das28["das28"] = min(latest_das28.get("das28", 3.0) + severity_bump, 7.0)
                if latest_das28["das28"] >= 5.1:
                    latest_das28["category"] = "high_activity"
                elif latest_das28["das28"] >= 3.2:
                    latest_das28["category"] = "moderate_activity"
                elif latest_das28["das28"] >= 2.6:
                    latest_das28["category"] = "low_activity"
                else:
                    latest_das28["category"] = "remission"
                latest_das28["hypothetical"] = True
                modified_das28.insert(0, latest_das28)
    
    return {
        "patient_id": patient["id"],
        "hypothetical": True,
        "changes_applied": [
            {"ts": c.ts, "kind": c.kind, "summary": c.summary}
            for c in request.changes
        ],
        "age": patient["age"],
        "sex": patient["sex"],
        "diagnosis": patient["diagnosis"],
        "terrain": "chronic autoimmune inflammatory arthritis",
        "serostatus": patient["serostatus"],
        "current_meds": patient["meds"],
        "recent_flare_history": modified_flares[:5],
        "recent_das28": modified_das28[0] if modified_das28 else None,
        "das28_trend": modified_das28[:5],
        "recent_labs": modified_labs[:3],
        "recent_journal": recent_journal,
        "journal_highlights": patient["journal_highlights"],
        "summary": f"[HYPOTHETICAL] {patient['summary']} + {len(request.changes)} change(s) applied",
    }


@router.get("/patient_state")
async def get_legacy_patient_state(as_of: Optional[str] = Query(None)) -> Dict[str, Any]:
    """
    Legacy endpoint for backward compatibility.
    Returns patient state for P1 (the original demo patient).
    """
    return await get_patient_state("P1")


@router.get("/timeline")
async def get_legacy_timeline() -> List[Dict[str, Any]]:
    """
    Legacy endpoint for backward compatibility.
    Returns timeline for P1 (the original demo patient).
    """
    return await get_patient_timeline("P1")
