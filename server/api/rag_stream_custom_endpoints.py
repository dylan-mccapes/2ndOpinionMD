# rag_stream_custom_endpoints.py

from fastapi import APIRouter, Query, Request, Depends
from sse_starlette.sse import EventSourceResponse
from typing import Optional, List, Any
import json
import logging

# Import functions from your existing rag_stream_routes.py
# These should already exist in your project
from .rag_stream_routes import (
    search_source_ts,
    search_source_ann,
    fetch_valyu_results,
    apply_source_gating,
    build_fused_context,
    _event_generator,
    build_citations,
    rrf_fuse,
    format_context_for_llm,
    stream_llm_events,
    resolve_pg_pool,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag-custom"])

def _send_large_request_warning(q: str, sources: list[str], limit: int):
    # simple heuristic: if more than 8 sources or limit > 10, warn user
    if len(sources) > 8 or limit > 10:
        return {
            "warning": (
                f"Large request: {len(sources)} sources and limit={limit}. "
                "This may lead to more noisy results. Consider reducing the number of sources or lowering the limit."
            ),
            "sources": sources,
            "limit": limit,
        }
    return None

@router.get("/ask_stream")
async def ask_stream(
    request: Request,
    q: str = Query(..., description="User query"),
    sources: Optional[str] = Query(
        None,
        description="Comma-separated list of rag_corpus.source keys",
    ),
    limit: int = Query(5, ge=1, le=50),
    ctx_k: int = Query(24, ge=1, le=128, description="Number of internal context chunks"),
    valyu_k: int = Query(5, ge=0, le=32, description="Valyu tail size"),
    with_llm: int = Query(1, description="1 = run LLM, 0 = retrieval only"),
    llm_mode: str = Query("chunk"),
    use_valyu: int = Query(0, description="1 = include Valyu, 0 = skip"),
    valyu_mode: str = Query("answer"),
    valyu_raw: int = Query(0),
    valyu_sources: Optional[str] = Query(None),
    valyu_boost: float = Query(1.0),
    pool: Any = Depends(resolve_pg_pool),
):
    # Parse sources list
    if sources:
        db_sources = [s.strip() for s in sources.split(",") if s.strip()]
    else:
        db_sources = ["mimic4_note"]  # fallback to some default corpus

    # Emit a warning if many sources/large limit
    warning = _send_large_request_warning(q, db_sources, limit)
    async def event_gen():
        if warning:
            yield {"event": "warning", "data": json.dumps(warning)}
        async for ev in _event_generator(
            request=request,
            q=q,
            db_sources=db_sources,
            limit=limit,
            ctx_k=ctx_k,
            valyu_k=valyu_k,
            with_llm_bool=bool(with_llm),
            llm_mode=llm_mode,
            use_valyu_bool=bool(use_valyu),
            valyu_mode=valyu_mode,
            valyu_raw_bool=bool(valyu_raw),
            valyu_sources=valyu_sources,
            valyu_boost=valyu_boost,
            pool=pool,
            coding_mode=False,
        ):
            yield ev
    return EventSourceResponse(event_gen(), media_type="text/event-stream")

@router.get("/coding_stream")
async def coding_stream(
    request: Request,
    q: str = Query(..., description="Coding / abstraction query"),
    limit: int = Query(8, ge=1, le=50),
    ctx_k: int = Query(24, ge=1, le=128),
    valyu_k: int = Query(5, ge=0, le=32),
    with_llm: int = Query(1, description="1 = run LLM, 0 = retrieval only"),
    llm_mode: str = Query("chunk"),
    use_valyu: int = Query(1, description="1 = include Valyu, 0 = skip"),
    valyu_mode: str = Query("answer"),
    valyu_raw: int = Query(0),
    valyu_sources: Optional[str] = Query(None),
    valyu_boost: float = Query(1.0),
    pool: Any = Depends(resolve_pg_pool),
):
    # In coding mode we always use the fixed set of coding sources
    db_sources = [
        "acr_ra_2021", "eular_ra_2022", "acr_ild_2023",
        "icd11", "loinc", "rxnorm", "snomed", "va_guidelines"
    ]
    warning = _send_large_request_warning(q, db_sources, limit)
    async def event_gen():
        if warning:
            yield {"event": "warning", "data": json.dumps(warning)}
        async for ev in _event_generator(
            request=request,
            q=q,
            db_sources=db_sources,
            limit=limit,
            ctx_k=ctx_k,
            valyu_k=valyu_k,
            with_llm_bool=bool(with_llm),
            llm_mode=llm_mode,
            use_valyu_bool=bool(use_valyu),
            valyu_mode=valyu_mode,
            valyu_raw_bool=bool(valyu_raw),
            valyu_sources=valyu_sources,
            valyu_boost=valyu_boost,
            pool=pool,
            coding_mode=True,
        ):
            yield ev
    return EventSourceResponse(event_gen(), media_type="text/event-stream")
