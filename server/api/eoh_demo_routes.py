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
    # Call get_timeline() directly instead of the endpoint function,
    # because the Query() default on max_events is only resolved via HTTP dispatch.
    return get_timeline("P1")


# ---------------------------------------------------------------------------
# EoH + Timeline Flare Engine Mode Endpoints
# ---------------------------------------------------------------------------

class TimelineFlareEngineResponse(BaseModel):
    """Response model for the Timeline Flare Engine analysis."""
    patient_id: str
    mode: str = "timeline_flare_engine"
    timeline_summary: Dict[str, Any]
    flare_prediction: Dict[str, Any]
    diagnostic_landscape: Dict[str, Any]
    precursors: List[Dict[str, Any]]
    eoh_context: str


@router.get("/timeline_flare_engine/{patient_id}")
async def get_timeline_flare_engine_analysis(
    patient_id: str,
    window_days: int = Query(90, ge=30, le=365, description="Analysis window in days"),
) -> TimelineFlareEngineResponse:
    """
    EoH + Timeline Flare Engine Mode.
    
    This endpoint provides a comprehensive flare prediction analysis for a demo patient,
    combining:
    1. Timeline summary with key events
    2. Flare prediction with probabilistic likelihood
    3. Diagnostic landscape with pattern-based probabilities
    4. Precursor events that may indicate upcoming flares
    5. EoH context text for LLM reasoning
    
    All outputs are probabilistic and non-diagnostic per regulatory strategy.
    """
    patient = get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    
    timeline = get_timeline(patient_id)
    
    # Build timeline summary
    event_counts = {}
    for event in timeline:
        kind = event.get("kind", "unknown")
        event_counts[kind] = event_counts.get(kind, 0) + 1
    
    # Calculate timeline span
    if timeline:
        first_ts = timeline[0].get("ts", "")
        last_ts = timeline[-1].get("ts", "")
        try:
            first_date = datetime.fromisoformat(first_ts.replace("Z", "+00:00"))
            last_date = datetime.fromisoformat(last_ts.replace("Z", "+00:00"))
            span_days = (last_date - first_date).days
        except (ValueError, TypeError):
            span_days = 0
    else:
        span_days = 0
    
    timeline_summary = {
        "event_count": len(timeline),
        "span_days": span_days,
        "event_types": event_counts,
        "recent_events": timeline[-5:] if timeline else [],
    }
    
    # Build flare prediction (synthetic/mocked based on demo data patterns)
    flare_events = [e for e in timeline if e.get("kind") == "flare"]
    lab_events = [e for e in timeline if e.get("kind") == "lab"]
    
    # Analyze recent inflammatory markers
    recent_crp = None
    recent_esr = None
    for lab in reversed(lab_events):
        payload = lab.get("details", {}) or lab.get("payload", {})
        if payload.get("CRP") and recent_crp is None:
            recent_crp = payload["CRP"]
        if payload.get("ESR") and recent_esr is None:
            recent_esr = payload["ESR"]
        if recent_crp and recent_esr:
            break
    
    # Calculate flare likelihood based on patterns
    flare_count = len(flare_events)
    crp_elevated = recent_crp and recent_crp > 10
    esr_elevated = recent_esr and recent_esr > 30
    
    if crp_elevated and esr_elevated and flare_count >= 2:
        likelihood = "high"
        likelihood_score = 0.72
        explanation = "Elevated inflammatory markers (CRP, ESR) combined with history of multiple flares suggests increased flare probability."
    elif crp_elevated or esr_elevated or flare_count >= 1:
        likelihood = "moderate"
        likelihood_score = 0.45
        explanation = "Some inflammatory marker elevation or prior flare history suggests moderate flare probability."
    else:
        likelihood = "low"
        likelihood_score = 0.18
        explanation = "Inflammatory markers within acceptable range and limited flare history suggests lower flare probability."
    
    flare_prediction = {
        "likelihood": likelihood,
        "likelihood_score": likelihood_score,
        "explanation": explanation,
        "window_days": window_days,
        "recent_markers": {
            "CRP": recent_crp,
            "ESR": recent_esr,
        },
        "flare_history_count": flare_count,
        "regulatory_note": "This is a probabilistic assessment, not a diagnosis. Clinical judgment required.",
    }
    
    # Build diagnostic landscape (pattern-based probabilities)
    # Based on demo patient characteristics
    serostatus = patient.get("serostatus", "")
    diagnosis = patient.get("diagnosis", "")
    
    # Default probabilities based on RA-like patterns in demo data
    if "RA" in diagnosis or "rheumatoid" in diagnosis.lower():
        diagnostic_landscape = {
            "ra_like": 0.65,
            "sle_like": 0.08,
            "psa_like": 0.12,
            "sjogren_like": 0.05,
            "mixed_ctd_like": 0.07,
            "vasculitis_like": 0.01,
            "other": 0.02,
        }
        drivers = [
            "Symmetric small joint involvement pattern",
            "Seropositive status (RF+, anti-CCP+)" if "seropositive" in serostatus.lower() else "Joint-centric presentation",
            "Morning stiffness > 1 hour pattern",
            "CRP/ESR correlation with disease activity",
        ]
    else:
        # Generic autoimmune pattern
        diagnostic_landscape = {
            "ra_like": 0.30,
            "sle_like": 0.20,
            "psa_like": 0.15,
            "sjogren_like": 0.10,
            "mixed_ctd_like": 0.15,
            "vasculitis_like": 0.05,
            "other": 0.05,
        }
        drivers = [
            "Inflammatory arthritis pattern",
            "Autoimmune marker profile",
            "Symptom clustering analysis",
        ]
    
    diagnostic_landscape_response = {
        "probabilities": diagnostic_landscape,
        "drivers": drivers,
        "confidence": 0.75,
        "regulatory_note": "Pattern-based probabilities, not diagnostic. '_like' suffix indicates similarity to known patterns.",
    }
    
    # Build precursor list
    precursors = []
    
    # Look for rising inflammatory markers
    if crp_elevated:
        precursors.append({
            "type": "inflammatory_marker",
            "description": f"CRP elevated at {recent_crp} mg/L",
            "similarity_score": 0.82,
            "pattern": "Rising inflammatory markers often precede flares",
        })
    
    if esr_elevated:
        precursors.append({
            "type": "inflammatory_marker",
            "description": f"ESR elevated at {recent_esr} mm/hr",
            "similarity_score": 0.78,
            "pattern": "ESR elevation correlates with disease activity",
        })
    
    # Look for symptom patterns in journal entries
    journal_events = [e for e in timeline if e.get("kind") == "journal"]
    for journal in journal_events[-3:]:
        summary = journal.get("summary", "").lower()
        if any(word in summary for word in ["stiff", "ache", "pain", "fatigue"]):
            precursors.append({
                "type": "symptom_cluster",
                "description": journal.get("summary", ""),
                "similarity_score": 0.65,
                "pattern": "Symptom reports may indicate prodromal phase",
            })
    
    # Build EoH context text for LLM reasoning
    eoh_context_parts = [
        f"PATIENT TIMELINE CONTEXT (EoH + Timeline Flare Engine Mode)",
        f"Patient ID: {patient_id}",
        f"Diagnosis: {diagnosis}",
        f"Serostatus: {serostatus}",
        f"",
        f"TIMELINE SUMMARY:",
        f"- Total events: {len(timeline)}",
        f"- Timeline span: {span_days} days",
        f"- Flare events: {flare_count}",
        f"",
        f"FLARE PREDICTION:",
        f"- Likelihood: {likelihood} ({likelihood_score:.0%})",
        f"- {explanation}",
        f"",
        f"DIAGNOSTIC LANDSCAPE (probabilistic, non-diagnostic):",
    ]
    
    for pattern, prob in diagnostic_landscape.items():
        eoh_context_parts.append(f"- {pattern}: {prob:.0%}")
    
    eoh_context_parts.extend([
        f"",
        f"KEY DRIVERS:",
    ])
    for driver in drivers:
        eoh_context_parts.append(f"- {driver}")
    
    if precursors:
        eoh_context_parts.extend([
            f"",
            f"PRECURSOR SIGNALS ({len(precursors)} detected):",
        ])
        for p in precursors[:5]:
            eoh_context_parts.append(f"- {p['type']}: {p['description']} (similarity: {p['similarity_score']:.0%})")
    
    eoh_context_parts.extend([
        f"",
        f"REGULATORY NOTE: All outputs are probabilistic assessments based on pattern analysis.",
        f"This is NOT a diagnosis. Clinical judgment and professional evaluation required.",
    ])
    
    eoh_context = "\n".join(eoh_context_parts)
    
    return TimelineFlareEngineResponse(
        patient_id=patient_id,
        mode="timeline_flare_engine",
        timeline_summary=timeline_summary,
        flare_prediction=flare_prediction,
        diagnostic_landscape=diagnostic_landscape_response,
        precursors=precursors,
        eoh_context=eoh_context,
    )


@router.get("/modes")
async def list_demo_modes() -> List[Dict[str, Any]]:
    """
    List available demo modes for the EoH system.
    """
    return [
        {
            "id": "standard",
            "name": "Standard EoH Demo",
            "description": "Basic EoH reasoning with patient state context",
            "endpoint": "/api/eoh_demo/patient_state/{patient_id}",
        },
        {
            "id": "timeline_flare_engine",
            "name": "EoH + Timeline Flare Engine",
            "description": "Advanced flare prediction with ANN-based precursor detection and diagnostic landscape mapping",
            "endpoint": "/api/eoh_demo/timeline_flare_engine/{patient_id}",
            "features": [
                "Timeline event analysis",
                "Flare precursor detection",
                "Probabilistic diagnostic landscape",
                "EoH context generation for LLM reasoning",
            ],
        },
        {
            "id": "hypothetical",
            "name": "Hypothetical Scenario",
            "description": "Apply hypothetical changes to a patient and see predicted outcomes",
            "endpoint": "/api/eoh_demo/hypothetical",
        },
    ]
