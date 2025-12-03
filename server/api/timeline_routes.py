"""
Timeline API Routes

Provides endpoints for:
- GET /api/timeline/{patient_id} - Timeline reconstruction
- GET /api/eoh/flarereport/{patient_id} - Flare prediction report
- POST /api/timeline/{patient_id}/events - Add timeline events
- GET /api/timeline/{patient_id}/search - Search timeline events

All outputs are probabilistic, transparent, and non-diagnostic per regulatory strategy.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_session
from server.timeline.engine import TimelineEngine
from server.timeline.models import (
    DiagnosticLandscape,
    DiagnosticProbability,
    EventSource,
    EventType,
    FlarePrecursor,
    FlarePrediction,
    FlareReport,
    TimelineContext,
    TimelineEvent,
    TimelineEventCreate,
    TimelineResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["timeline"])


# ============================================================================
# Request/Response Models
# ============================================================================

class TimelineEventRequest(BaseModel):
    """Request model for creating a timeline event."""
    ts: datetime
    event_type: str = Field(..., description="Event type: lab, symptom, medication, imaging, flare, note, self_report, visit, med_change")
    source: str = Field(default="patient_upload", description="Data source")
    structured: Optional[Dict[str, Any]] = None
    text: str
    meta: Dict[str, Any] = Field(default_factory=dict)


class TimelineEventsRequest(BaseModel):
    """Request model for creating multiple timeline events."""
    events: List[TimelineEventRequest]


class TimelineSearchRequest(BaseModel):
    """Request model for searching timeline events."""
    query: str
    limit: int = Field(default=10, ge=1, le=100)
    event_types: Optional[List[str]] = None


class TimelineSearchResult(BaseModel):
    """Search result with similarity score."""
    event: TimelineEvent
    similarity_score: float


class TimelineSearchResponse(BaseModel):
    """Response model for timeline search."""
    patient_id: str
    query: str
    results: List[TimelineSearchResult]
    total_results: int


class FlareReportResponse(BaseModel):
    """Response model for flare report endpoint."""
    patient_id: str
    report_timestamp: datetime
    flare_forecast: str
    differential_landscape: Dict[str, Any]
    key_precursors: List[Dict[str, Any]]
    contradictions: List[str]
    risk_drivers: List[str]
    protective_factors: List[str]
    timeline_summary: str
    timeline_event_count: int
    timeline_span_days: int
    guidance_for_clinician: List[str]
    model_version: str
    disclaimer: str


class DiagnosticLandscapeResponse(BaseModel):
    """Response model for diagnostic landscape endpoint."""
    patient_id: str
    analysis_timestamp: datetime
    diagnostic_probabilities: Dict[str, float]
    drivers: List[str]
    key_features: Dict[str, Any]
    disclaimer: str


class FlarePredictionResponse(BaseModel):
    """Response model for flare prediction endpoint."""
    patient_id: str
    prediction_timestamp: datetime
    flare_likelihood: str
    likelihood_score: float
    key_precursors: List[Dict[str, Any]]
    matched_signatures: List[Dict[str, Any]]
    risk_drivers: List[str]
    protective_factors: List[str]
    contradictions: List[str]
    disclaimer: str


class TimelineContextResponse(BaseModel):
    """Response model for timeline context (for EoH integration)."""
    patient_id: str
    context_text: str
    event_count: int
    span_days: int
    key_signals: List[str]
    flare_features: Optional[Dict[str, Any]] = None
    diagnostic_landscape: Optional[Dict[str, float]] = None


# ============================================================================
# Timeline Reconstruction Endpoint
# ============================================================================

@router.get("/timeline/{patient_id}", response_model=TimelineResponse)
async def get_patient_timeline(
    patient_id: str,
    limit: int = Query(default=100, ge=1, le=1000, description="Maximum events to return"),
    offset: int = Query(default=0, ge=0, description="Offset for pagination"),
    event_types: Optional[str] = Query(default=None, description="Comma-separated event types to filter"),
    start_date: Optional[datetime] = Query(default=None, description="Filter events after this date"),
    end_date: Optional[datetime] = Query(default=None, description="Filter events before this date"),
    session: AsyncSession = Depends(get_session),
) -> TimelineResponse:
    """
    Retrieve patient timeline events.
    
    Returns chronologically ordered, normalized timeline with structured + narrative elements.
    
    Args:
        patient_id: Patient identifier
        limit: Maximum number of events to return (default 100, max 1000)
        offset: Offset for pagination
        event_types: Comma-separated list of event types to filter
        start_date: Filter events after this date
        end_date: Filter events before this date
        
    Returns:
        TimelineResponse with events and metadata
    """
    engine = TimelineEngine()
    
    # Parse event types if provided
    event_type_list = None
    if event_types:
        event_type_list = [et.strip() for et in event_types.split(",")]
    
    try:
        timeline = await engine.get_timeline(
            session=session,
            patient_id=patient_id,
            limit=limit,
            offset=offset,
            event_types=event_type_list,
            start_date=start_date,
            end_date=end_date,
        )
        return timeline
    except Exception as e:
        logger.exception(f"Error retrieving timeline for patient {patient_id}")
        raise HTTPException(status_code=500, detail=f"Error retrieving timeline: {str(e)}")


# ============================================================================
# Timeline Event Creation Endpoint
# ============================================================================

@router.post("/timeline/{patient_id}/events", response_model=Dict[str, Any])
async def create_timeline_events(
    patient_id: str,
    request: TimelineEventsRequest,
    session: AsyncSession = Depends(get_session),
) -> Dict[str, Any]:
    """
    Create timeline events for a patient.
    
    Args:
        patient_id: Patient identifier
        request: List of events to create
        
    Returns:
        Dict with created event IDs and count
    """
    engine = TimelineEngine()
    
    created_ids = []
    errors = []
    
    for event_req in request.events:
        try:
            event = TimelineEventCreate(
                patient_id=patient_id,
                ts=event_req.ts,
                event_type=event_req.event_type,
                source=event_req.source,
                structured=event_req.structured,
                text=event_req.text,
                meta=event_req.meta,
            )
            event_id = await engine.store_event(session, event)
            created_ids.append(event_id)
        except Exception as e:
            errors.append(f"Error creating event: {str(e)}")
    
    return {
        "patient_id": patient_id,
        "created_count": len(created_ids),
        "created_ids": created_ids,
        "errors": errors,
    }


# ============================================================================
# Timeline Search Endpoint
# ============================================================================

@router.post("/timeline/{patient_id}/search", response_model=TimelineSearchResponse)
async def search_timeline(
    patient_id: str,
    request: TimelineSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> TimelineSearchResponse:
    """
    Search patient timeline using semantic similarity.
    
    Uses ANN search to find events similar to the query text.
    
    Args:
        patient_id: Patient identifier
        request: Search parameters
        
    Returns:
        TimelineSearchResponse with matching events and scores
    """
    engine = TimelineEngine()
    
    try:
        results = await engine.search_similar_events(
            session=session,
            query_text=request.query,
            patient_id=patient_id,
            limit=request.limit,
            event_types=request.event_types,
        )
        
        search_results = [
            TimelineSearchResult(event=event, similarity_score=score)
            for event, score in results
        ]
        
        return TimelineSearchResponse(
            patient_id=patient_id,
            query=request.query,
            results=search_results,
            total_results=len(search_results),
        )
    except Exception as e:
        logger.exception(f"Error searching timeline for patient {patient_id}")
        raise HTTPException(status_code=500, detail=f"Error searching timeline: {str(e)}")


# ============================================================================
# Flare Report Endpoint
# ============================================================================

@router.get("/eoh/flarereport/{patient_id}", response_model=FlareReportResponse)
async def get_flare_report(
    patient_id: str,
    session: AsyncSession = Depends(get_session),
) -> FlareReportResponse:
    """
    Generate complete flare prediction report for a patient.
    
    Returns a structured report with:
    - Qualitative flare forecast
    - Diagnostic landscape (probabilistic pattern similarities)
    - Key precursor events
    - Risk drivers and protective factors
    - Clinician guidance
    
    NOTE: This is NOT a diagnosis. All outputs are probabilistic and
    intended for clinician review only.
    
    Args:
        patient_id: Patient identifier
        
    Returns:
        FlareReportResponse with complete flare analysis
    """
    engine = TimelineEngine()
    
    try:
        report = await engine.generate_flare_report(session, patient_id)
        
        # Convert to response model
        return FlareReportResponse(
            patient_id=report.patient_id,
            report_timestamp=report.report_timestamp,
            flare_forecast=report.flare_forecast,
            differential_landscape={
                "patient_id": report.differential_landscape.patient_id,
                "analysis_timestamp": report.differential_landscape.analysis_timestamp.isoformat(),
                "diagnostic_probabilities": {
                    "ra_like": report.differential_landscape.diagnostic_probabilities.ra_like,
                    "sle_like": report.differential_landscape.diagnostic_probabilities.sle_like,
                    "psa_like": report.differential_landscape.diagnostic_probabilities.psa_like,
                    "sjogren_like": report.differential_landscape.diagnostic_probabilities.sjogren_like,
                    "mixed_ctd_like": report.differential_landscape.diagnostic_probabilities.mixed_ctd_like,
                    "vasculitis_like": report.differential_landscape.diagnostic_probabilities.vasculitis_like,
                    "other": report.differential_landscape.diagnostic_probabilities.other,
                },
                "drivers": report.differential_landscape.drivers,
            },
            key_precursors=[
                {
                    "event_id": p.event.id,
                    "event_ts": p.event.ts.isoformat(),
                    "event_type": p.event.event_type,
                    "event_text": p.event.text[:200] if p.event.text else "",
                    "similarity_score": p.similarity_score,
                    "precursor_type": p.precursor_type,
                    "explanation": p.explanation,
                }
                for p in report.key_precursors
            ],
            contradictions=report.contradictions,
            risk_drivers=report.risk_drivers,
            protective_factors=report.protective_factors,
            timeline_summary=report.timeline_summary,
            timeline_event_count=report.timeline_event_count,
            timeline_span_days=report.timeline_span_days,
            guidance_for_clinician=report.guidance_for_clinician,
            model_version=report.model_version,
            disclaimer=report.disclaimer,
        )
    except Exception as e:
        logger.exception(f"Error generating flare report for patient {patient_id}")
        raise HTTPException(status_code=500, detail=f"Error generating flare report: {str(e)}")


# ============================================================================
# Diagnostic Landscape Endpoint
# ============================================================================

@router.get("/eoh/landscape/{patient_id}", response_model=DiagnosticLandscapeResponse)
async def get_diagnostic_landscape(
    patient_id: str,
    session: AsyncSession = Depends(get_session),
) -> DiagnosticLandscapeResponse:
    """
    Get probabilistic diagnostic landscape for a patient.
    
    Returns pattern similarities to known autoimmune conditions.
    
    NOTE: This is NOT a diagnosis. It represents pattern similarities
    for clinician review.
    
    Args:
        patient_id: Patient identifier
        
    Returns:
        DiagnosticLandscapeResponse with probabilistic pattern similarities
    """
    engine = TimelineEngine()
    
    try:
        landscape = await engine.estimate_diagnostic_landscape(session, patient_id)
        
        return DiagnosticLandscapeResponse(
            patient_id=landscape.patient_id,
            analysis_timestamp=landscape.analysis_timestamp,
            diagnostic_probabilities={
                "ra_like": landscape.diagnostic_probabilities.ra_like,
                "sle_like": landscape.diagnostic_probabilities.sle_like,
                "psa_like": landscape.diagnostic_probabilities.psa_like,
                "sjogren_like": landscape.diagnostic_probabilities.sjogren_like,
                "mixed_ctd_like": landscape.diagnostic_probabilities.mixed_ctd_like,
                "vasculitis_like": landscape.diagnostic_probabilities.vasculitis_like,
                "other": landscape.diagnostic_probabilities.other,
            },
            drivers=landscape.drivers,
            key_features=landscape.key_features,
            disclaimer=landscape.disclaimer,
        )
    except Exception as e:
        logger.exception(f"Error estimating diagnostic landscape for patient {patient_id}")
        raise HTTPException(status_code=500, detail=f"Error estimating landscape: {str(e)}")


# ============================================================================
# Flare Prediction Endpoint
# ============================================================================

@router.get("/eoh/flareprediction/{patient_id}", response_model=FlarePredictionResponse)
async def get_flare_prediction(
    patient_id: str,
    window_days: int = Query(default=90, ge=7, le=365, description="Days to analyze"),
    session: AsyncSession = Depends(get_session),
) -> FlarePredictionResponse:
    """
    Get probabilistic flare prediction for a patient.
    
    Analyzes recent timeline events to predict flare likelihood.
    
    NOTE: This is NOT a diagnosis. All outputs are probabilistic and
    intended for clinician review only.
    
    Args:
        patient_id: Patient identifier
        window_days: Number of days to analyze (default 90)
        
    Returns:
        FlarePredictionResponse with probabilistic flare assessment
    """
    engine = TimelineEngine()
    
    try:
        prediction = await engine.predict_flare_likelihood(
            session, patient_id, window_days=window_days
        )
        
        return FlarePredictionResponse(
            patient_id=prediction.patient_id,
            prediction_timestamp=prediction.prediction_timestamp,
            flare_likelihood=prediction.flare_likelihood.value,
            likelihood_score=prediction.likelihood_score,
            key_precursors=[
                {
                    "event_id": p.event.id,
                    "event_ts": p.event.ts.isoformat(),
                    "event_type": p.event.event_type,
                    "event_text": p.event.text[:200] if p.event.text else "",
                    "similarity_score": p.similarity_score,
                    "precursor_type": p.precursor_type,
                    "explanation": p.explanation,
                }
                for p in prediction.key_precursors
            ],
            matched_signatures=prediction.matched_signatures,
            risk_drivers=prediction.risk_drivers,
            protective_factors=prediction.protective_factors,
            contradictions=prediction.contradictions,
            disclaimer=prediction.disclaimer,
        )
    except Exception as e:
        logger.exception(f"Error predicting flare for patient {patient_id}")
        raise HTTPException(status_code=500, detail=f"Error predicting flare: {str(e)}")


# ============================================================================
# Timeline Context Endpoint (for EoH Router Integration)
# ============================================================================

@router.get("/eoh/timeline-context/{patient_id}", response_model=TimelineContextResponse)
async def get_timeline_context(
    patient_id: str,
    session: AsyncSession = Depends(get_session),
) -> TimelineContextResponse:
    """
    Get timeline context document for EoH Router integration.
    
    Returns a structured context that can be injected into the EoH RAG system.
    
    Args:
        patient_id: Patient identifier
        
    Returns:
        TimelineContextResponse with context for EoH integration
    """
    engine = TimelineEngine()
    
    try:
        context = await engine.build_timeline_context(session, patient_id)
        
        return TimelineContextResponse(
            patient_id=context.patient_id,
            context_text=context.context_text,
            event_count=context.event_count,
            span_days=context.span_days,
            key_signals=context.key_signals,
            flare_features=context.flare_features,
            diagnostic_landscape={
                "ra_like": context.diagnostic_landscape.ra_like,
                "sle_like": context.diagnostic_landscape.sle_like,
                "psa_like": context.diagnostic_landscape.psa_like,
                "sjogren_like": context.diagnostic_landscape.sjogren_like,
                "mixed_ctd_like": context.diagnostic_landscape.mixed_ctd_like,
                "vasculitis_like": context.diagnostic_landscape.vasculitis_like,
                "other": context.diagnostic_landscape.other,
            } if context.diagnostic_landscape else None,
        )
    except Exception as e:
        logger.exception(f"Error building timeline context for patient {patient_id}")
        raise HTTPException(status_code=500, detail=f"Error building context: {str(e)}")
