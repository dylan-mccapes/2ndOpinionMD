"""
Pydantic models for RAG stream endpoints

Privacy: All endpoints use POST with JSON body (no query params in URL logs)
"""

from typing import Optional
from pydantic import BaseModel, Field


class AskStreamRequest(BaseModel):
    """Request body for /ask_stream endpoint"""
    q: str = Field(..., description="User clinical question")
    sources: Optional[str] = Field(
        None,
        description=(
            "Comma-separated internal sources. If omitted, all known "
            "guideline-ish sources (ACR/EULAR/NICE/ESMO/KDIGO/WHO/etc.) "
            "are used, discovered dynamically from the MKG."
        ),
    )
    limit: int = Field(12, ge=1, le=64)
    ctx_k: int = Field(24, ge=1, le=128)
    valyu_k: int = Field(4, ge=0, le=16)
    with_llm: int = Field(
        1,
        ge=0,
        le=1,
        description="1=run LLM, 0=return context only",
    )
    llm_mode: str = Field(
        "chunk",
        description="chunk=stream chunks, delta=tiny tokens (llm_delta), ctx=only context",
    )
    use_valyu: int = Field(
        0,
        ge=0,
        le=1,
        description="1=include Valyu matches, 0=disable",
    )
    valyu_mode: str = Field(
        "search",
        description="Valyu mode: 'search' (evidence) or 'answer'.",
    )
    valyu_raw: int = Field(
        0,
        description=(
            "1=request full contents from Valyu (stored in meta.full_text when "
            "supported); context still uses snippets."
        ),
    )
    valyu_sources: Optional[str] = Field(
        None,
        description="Optional CSV of Valyu sources (e.g. 'valyu/valyu-pubmed')",
    )
    valyu_boost: float = Field(
        1.0,
        description="Reserved for future tuning of Valyu weighting",
    )
    use_ethos: int = Field(
        0,
        description="1=include ethos_model rows and force-keep them in context",
    )


class CodingStreamRequest(BaseModel):
    """Request body for /coding_stream endpoint"""
    q: str = Field(..., description="Coding / abstraction query")
    sources: Optional[str] = Field(
        None,
        description=(
            "Comma-separated source list. If omitted, CODING_DEFAULT_SOURCES "
            "from stream_config is used."
        ),
    )
    limit: int = Field(12, ge=1, le=64)
    ctx_k: int = Field(24, ge=1, le=128)
    valyu_k: int = Field(4, ge=0, le=16)
    with_llm: int = Field(1, description="1=run LLM, 0=return context only")
    llm_mode: str = Field(
        "chunk",
        description="chunk=stream chunks, delta=tiny tokens (llm_delta), ctx=only context",
    )


class EohStreamRequest(BaseModel):
    """Request body for /eoh_stream endpoint"""
    q: str = Field(..., description="EoH / Ethos-of-Health grading/QA query")
    sources: Optional[str] = Field(
        None,
        description=(
            "Comma-separated internal sources. If omitted, uses guideline-ish "
            "sources plus the Ethos/EoH source."
        ),
    )
    limit: int = Field(10, ge=1, le=64)
    ctx_k: int = Field(32, ge=1, le=128)
    valyu_k: int = Field(
        3,
        ge=0,
        le=16,
        description="Default 0 for EoH mode (no Valyu); can be overridden."
    )
    with_llm: int = Field(
        1,
        ge=0,
        le=1,
        description="1=run LLM, 0=return context only",
    )
    llm_mode: str = Field(
        "chunk",
        description="chunk=stream chunks, delta=tiny tokens (llm_delta), ctx=only context",
    )
    use_valyu: int = Field(
        1,
        ge=0,
        le=1,
        description="1=include Valyu matches, 0=disable (default for EoH).",
    )
    valyu_mode: str = Field(
        "search",
        description="Valyu mode: 'search' (evidence) or 'answer'.",
    )
    valyu_raw: int = Field(
        0,
        description=(
            "1=request full contents from Valyu (stored in meta.full_text when "
            "supported); context still uses snippets."
        ),
    )
    valyu_sources: Optional[str] = Field(
        None,
        description="Optional CSV of Valyu sources (e.g. 'valyu/valyu-pubmed')",
    )
    valyu_boost: float = Field(
        1.0,
        description="Reserved for future tuning of Valyu weighting",
    )
    patient_state: Optional[str] = Field(
        None,
        description="Optional JSON string with patient state summary for EoH router",
    )
    debug: bool = Field(
        False,
        description="Emit extra debug events including fused context text (context_fused)",
    )
    use_timeline: int = Field(
        1,
        ge=0,
        le=1,
        description="1=load patient timeline from DB and inject into context, 0=disable (default).",
    )
    timeline_patient_id: Optional[str] = Field(
        None,
        description="Patient ID for timeline loading (required if use_timeline=1).",
    )
    research: int = Field(
        1,
        ge=0,
        le=1,
        description="1=enable case analogs (MIMIC-4 ICU notes) and optional research helpers for this query",
    )
    enable_gap: int = Field(
        1,
        ge=0,
        le=1,
        description="1=run EoH gap retrieval pass, 0=skip (for perf/debug).",
    )


class EohDetectiveStreamRequest(BaseModel):
    """Request body for /eoh_detective_stream endpoint"""
    # Canonical required inputs
    q: Optional[str] = Field(None, description="High-level detective question or focus")
    timeline_patient_id: Optional[str] = Field(None, description="Patient id in ehr.patient_timeline")
    
    # Aliases for nicer UX / backwards-compat
    question: Optional[str] = Field(None, description="Alias for q")
    patient_id: Optional[str] = Field(None, description="Alias for timeline_patient_id")
    
    # Run label / controls
    focus: Optional[str] = Field(None, description="Optional short label for this detective run")
    max_steps: int = Field(6, ge=1, le=12)
    
    # Source selection / retrieval knobs
    sources: Optional[str] = Field(
        None,
        description="Comma-separated internal sources (same semantics as /eoh_stream)",
    )
    limit: int = Field(10, ge=1, le=32)
    ctx_k: int = Field(32, ge=4, le=128)
    
    # Valyu knobs
    valyu_k: int = Field(3, ge=0, le=4)
    use_valyu: bool = Field(True)
    valyu_mode: str = Field("search")
    valyu_raw: bool = Field(True)
    valyu_sources: Optional[str] = Field(None)
    valyu_boost: float = Field(1.0)
    
    # LLM controls
    with_llm: bool = Field(True)
    llm_mode: str = Field("chunk")
    
    # Research + gap
    research: int = Field(0, ge=0, le=1)
    enable_gap: int = Field(1, ge=0, le=1)
    use_gap: Optional[int] = Field(None, description="Alias for enable_gap (0/1)")

