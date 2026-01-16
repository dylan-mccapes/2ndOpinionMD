"""
Timeline Engine Data Models

Pydantic models for timeline events, flare signatures, and diagnostic landscapes.
All outputs are probabilistic, transparent, and non-diagnostic per regulatory strategy.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class EventType(str, Enum):
    """Classification of timeline events."""
    LAB = "lab"
    SYMPTOM = "symptom"
    MEDICATION = "medication"
    IMAGING = "imaging"
    FLARE = "flare"
    NOTE = "note"
    SELF_REPORT = "self_report"
    VISIT = "visit"
    MED_CHANGE = "med_change"
    JOURNAL = "journal"


class EventSource(str, Enum):
    """Data source for timeline events."""
    PATIENT_UPLOAD = "patient_upload"
    EHR = "EHR"
    SYNCED_DEVICE = "synced_device"
    CLINICIAN_NOTE = "clinician_note"
    JOURNAL = "journal"
    DEMO = "demo"


class FlareLikelihood(str, Enum):
    """Probabilistic flare likelihood levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ============================================================================
# Structured Data Models (for JSONB structured field)
# ============================================================================

class LabResult(BaseModel):
    """Structured lab result data."""
    test_name: str
    value: Optional[float] = None
    value_text: Optional[str] = None
    unit: Optional[str] = None
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    reference_range: Optional[str] = None  # Human-readable reference range (e.g., "<0.5", "0-20")
    flag: Optional[str] = None  # H, L, N, high, low, normal, borderline, positive, etc.
    qualitative: Optional[str] = None  # Qualitative result (e.g., "positive", "negative", "reactive")
    
    # Common autoimmune markers
    CRP: Optional[float] = None
    ESR: Optional[float] = None
    WBC: Optional[float] = None
    RF: Optional[float] = None
    anti_CCP: Optional[float] = None
    ANA: Optional[str] = None
    ANA_titer: Optional[str] = None
    complement_C3: Optional[float] = None
    complement_C4: Optional[float] = None


class SymptomData(BaseModel):
    """Structured symptom data."""
    symptom_name: str
    severity: Optional[int] = Field(None, ge=1, le=10)
    location: Optional[str] = None
    duration: Optional[str] = None
    frequency: Optional[str] = None
    pattern: Optional[str] = None  # Temporal pattern (e.g., "worse in morning", "improving", "stable")
    triggers: Optional[List[str]] = None
    relieving_factors: Optional[List[str]] = None
    associated_symptoms: Optional[List[str]] = None  # Related symptoms occurring together
    
    # Common autoimmune symptoms
    joint_pain: Optional[bool] = None
    joint_swelling: Optional[bool] = None
    morning_stiffness: Optional[bool] = None
    morning_stiffness_duration_min: Optional[int] = None
    fatigue: Optional[int] = Field(None, ge=1, le=10)
    skin_rash: Optional[bool] = None
    dry_eyes: Optional[bool] = None
    dry_mouth: Optional[bool] = None
    fever: Optional[bool] = None
    weight_change: Optional[str] = None


class MedicationData(BaseModel):
    """Structured medication data."""
    medication_name: str
    dose: Optional[str] = None
    frequency: Optional[str] = None
    route: Optional[str] = None
    action: Optional[str] = None  # started, stopped, changed, continued
    status: Optional[str] = None  # Alias for action (started, stopped, etc.)
    reason: Optional[str] = None
    indication: Optional[str] = None  # Medical indication for the medication
    adherence_gap_days: Optional[int] = None
    
    # Common autoimmune medications
    is_dmard: Optional[bool] = None
    is_biologic: Optional[bool] = None
    is_steroid: Optional[bool] = None
    is_nsaid: Optional[bool] = None


class FlareData(BaseModel):
    """Structured flare event data."""
    severity: Optional[int] = Field(None, ge=1, le=10)
    joints_involved: Optional[List[str]] = None
    duration_days: Optional[int] = None
    trigger: Optional[str] = None  # Primary/main trigger
    triggers: Optional[List[str]] = None  # Multiple triggers
    treatment_response: Optional[str] = None
    organ_involvement: Optional[List[str]] = None  # For systemic diseases like SLE
    
    # Disease activity scores
    das28: Optional[float] = None
    das28_crp: Optional[float] = None
    cdai: Optional[float] = None
    sdai: Optional[float] = None


class VisitData(BaseModel):
    """Structured clinical visit data."""
    visit_type: Optional[str] = None  # routine, urgent, follow-up, new_patient
    provider_type: Optional[str] = None  # rheumatologist, PCP, etc.
    provider: Optional[str] = None  # Provider name
    location: Optional[str] = None  # Clinic/facility name
    chief_complaint: Optional[str] = None  # Reason for visit
    diagnoses: Optional[List[str]] = None  # Diagnoses made/confirmed at visit
    
    # Physical exam findings
    swollen_joint_count: Optional[int] = None
    tender_joint_count: Optional[int] = None
    morning_stiffness_min: Optional[int] = None
    
    # Disease activity
    das28: Optional[float] = None
    patient_global_assessment: Optional[int] = Field(None, ge=0, le=100)
    physician_global_assessment: Optional[int] = Field(None, ge=0, le=100)


class ImagingData(BaseModel):
    """Structured imaging data."""
    modality: Optional[str] = None  # X-ray, MRI, ultrasound, CT
    body_part: Optional[str] = None
    impression: Optional[str] = None
    findings: Optional[List[str]] = None
    comparison: Optional[str] = None  # Comparison to prior imaging
    
    # Joint-specific findings
    erosions: Optional[bool] = None
    synovitis: Optional[bool] = None
    joint_space_narrowing: Optional[bool] = None


# ============================================================================
# Timeline Event Model
# ============================================================================

class TimelineEvent(BaseModel):
    """
    Normalized timeline event for storage and retrieval.
    
    This is the core data structure for the patient timeline.
    """
    id: Optional[int] = None
    patient_id: str
    ts: datetime
    event_type: EventType
    source: EventSource
    structured: Optional[Dict[str, Any]] = None
    text: str
    embedding: Optional[List[float]] = None
    meta: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        use_enum_values = True


class TimelineEventCreate(BaseModel):
    """Model for creating a new timeline event."""
    patient_id: str
    ts: datetime
    event_type: Union[EventType, str]
    source: Union[EventSource, str]
    structured: Optional[Dict[str, Any]] = None
    text: str
    meta: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        use_enum_values = True


# ============================================================================
# Flare Prediction Models
# ============================================================================

class FlarePrecursor(BaseModel):
    """A potential flare precursor event with similarity score."""
    event: TimelineEvent
    similarity_score: float = Field(ge=0.0, le=1.0)
    precursor_type: str  # e.g., "rising_inflammatory_marker", "symptom_cluster"
    explanation: str


class FlareSignature(BaseModel):
    """
    Synthetic flare signature for ANN comparison.
    
    These represent known patterns that precede autoimmune flares.
    """
    id: str
    name: str
    description: str
    pattern_type: str  # e.g., "ra_flare", "lupus_flare", "psa_flare"
    embedding: List[float]
    characteristic_events: List[str]
    typical_timeline_days: int = 14  # How many days before flare this pattern appears
    
    # Pattern components
    inflammatory_markers: Optional[Dict[str, str]] = None  # e.g., {"CRP": "rising", "ESR": "elevated"}
    symptom_patterns: Optional[List[str]] = None
    medication_patterns: Optional[List[str]] = None


class FlarePrediction(BaseModel):
    """
    Probabilistic flare prediction result.
    
    NOTE: This is NOT a diagnosis. All outputs are probabilistic and
    intended for clinician review only.
    """
    patient_id: str
    prediction_timestamp: datetime
    
    # Probabilistic likelihood (NOT diagnostic)
    flare_likelihood: FlareLikelihood
    likelihood_score: float = Field(ge=0.0, le=1.0)
    confidence_interval: Optional[tuple] = None
    
    # Supporting evidence
    key_precursors: List[FlarePrecursor]
    matched_signatures: List[Dict[str, Any]]  # Signature matches with scores
    
    # Explanations (for clinician audit)
    risk_drivers: List[str]
    protective_factors: List[str]
    contradictions: List[str]  # Evidence that contradicts flare prediction
    
    # Regulatory disclaimer
    disclaimer: str = (
        "This is a probabilistic assessment based on pattern matching. "
        "It is NOT a diagnosis and should be reviewed by a qualified clinician."
    )


# ============================================================================
# Diagnostic Landscape Models
# ============================================================================

class DiagnosticProbability(BaseModel):
    """
    Probabilistic similarity to known autoimmune patterns.
    
    NOTE: These are pattern similarities, NOT diagnoses.
    Uses "_like" suffix to emphasize probabilistic nature.
    """
    ra_like: float = Field(ge=0.0, le=1.0, description="Similarity to RA patterns")
    sle_like: float = Field(ge=0.0, le=1.0, description="Similarity to SLE patterns")
    psa_like: float = Field(ge=0.0, le=1.0, description="Similarity to PsA patterns")
    sjogren_like: float = Field(ge=0.0, le=1.0, description="Similarity to Sjogren's patterns")
    mixed_ctd_like: float = Field(ge=0.0, le=1.0, description="Similarity to MCTD patterns")
    vasculitis_like: float = Field(ge=0.0, le=1.0, description="Similarity to vasculitis patterns")
    other: float = Field(ge=0.0, le=1.0, description="Other/unclassified patterns")
    
    def normalize(self) -> "DiagnosticProbability":
        """Normalize probabilities to sum to 1.0."""
        total = (
            self.ra_like + self.sle_like + self.psa_like + 
            self.sjogren_like + self.mixed_ctd_like + 
            self.vasculitis_like + self.other
        )
        if total == 0:
            return self
        return DiagnosticProbability(
            ra_like=self.ra_like / total,
            sle_like=self.sle_like / total,
            psa_like=self.psa_like / total,
            sjogren_like=self.sjogren_like / total,
            mixed_ctd_like=self.mixed_ctd_like / total,
            vasculitis_like=self.vasculitis_like / total,
            other=self.other / total,
        )


class DiagnosticLandscape(BaseModel):
    """
    Probabilistic diagnostic landscape based on timeline patterns.
    
    NOTE: This is NOT a diagnosis. It represents pattern similarities
    to known autoimmune conditions for clinician review.
    """
    patient_id: str
    analysis_timestamp: datetime
    
    # Probabilistic pattern similarities
    diagnostic_probabilities: DiagnosticProbability
    
    # Pattern drivers (what contributed to each probability)
    drivers: List[str]
    
    # Key timeline features
    key_features: Dict[str, Any] = Field(default_factory=dict)
    
    # Cluster analysis results
    cluster_assignments: Optional[Dict[str, float]] = None
    
    # Regulatory disclaimer
    disclaimer: str = (
        "This diagnostic landscape represents pattern similarities, NOT diagnoses. "
        "Probabilities indicate how closely the patient's timeline matches known "
        "autoimmune patterns. Clinical correlation is required."
    )


# ============================================================================
# Flare Report Model
# ============================================================================

class FlareReport(BaseModel):
    """
    Complete structured flare prediction report.
    
    This is the main output for the /api/eoh/flarereport/{patient_id} endpoint.
    """
    patient_id: str
    report_timestamp: datetime
    
    # Qualitative flare forecast
    flare_forecast: str
    
    # Diagnostic landscape
    differential_landscape: DiagnosticLandscape
    
    # Precursor analysis
    key_precursors: List[FlarePrecursor]
    
    # Evidence analysis
    contradictions: List[str]
    risk_drivers: List[str]
    protective_factors: List[str]
    
    # Timeline summary
    timeline_summary: str
    timeline_event_count: int
    timeline_span_days: int
    
    # Clinician guidance
    guidance_for_clinician: List[str]
    
    # Metadata
    engine_version: str = "1.0.0"  # Renamed from model_version to avoid Pydantic protected namespace
    
    # Regulatory disclaimer
    disclaimer: str = (
        "This report provides probabilistic pattern analysis for clinician review. "
        "It does NOT constitute a medical diagnosis. All findings should be "
        "interpreted in clinical context by a qualified healthcare provider."
    )


# ============================================================================
# API Response Models
# ============================================================================

class TimelineResponse(BaseModel):
    """Response model for timeline reconstruction endpoint."""
    patient_id: str
    events: List[TimelineEvent]
    total_count: int
    span_days: Optional[int] = None
    event_type_counts: Dict[str, int] = Field(default_factory=dict)


class TimelineSignals(BaseModel):
    """Timeline signals for EoH Router integration."""
    patient_id: str
    signal_type: str  # timeline_loaded, timeline_signals, timeline_flare_features, etc.
    data: Dict[str, Any]


class TimelineContext(BaseModel):
    """Timeline context document for injection into EoH RAG."""
    patient_id: str
    context_text: str
    event_count: int
    span_days: int
    key_signals: List[str]
    flare_features: Optional[Dict[str, Any]] = None
    diagnostic_landscape: Optional[DiagnosticProbability] = None
