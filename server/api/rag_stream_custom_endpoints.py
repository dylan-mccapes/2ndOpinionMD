# server/api/rag_stream_custom_endpoints.py

from typing import Optional, List, Any, AsyncIterator, Dict
import logging

from fastapi import APIRouter, Query, Request, Depends
from sse_starlette.sse import EventSourceResponse

from .stream_config import (
    GUIDELINE_SOURCES,
    ETHOS_SOURCE_NAME,
    CODING_DEFAULT_SOURCES,
    BASE_RRF_K,
)

from .rag_stream_routes import (
    sse,
    resolve_pg_pool,
    _event_generator,
    MAX_CODING_SOURCES,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag-custom"])

# Default ask_stream sources: all guideline-ish sources, but EXCLUDE Ethos by default.
ASK_STREAM_DEFAULT_SOURCES = sorted(
    [s for s in GUIDELINE_SOURCES if s != ETHOS_SOURCE_NAME]
)


def _send_large_request_warning(q: str, sources: List[str], limit: int):
    # simple heuristic: if more than 8 sources or limit > 10, warn user
    if len(sources) > 8 or limit > 10:
        return {
            "warning": (
                f"Large request: {len(sources)} sources and limit={limit}. "
                "This may lead to more noisy results. Consider reducing the number "
                "of sources or lowering the limit."
            ),
            "sources": sources,
            "limit": limit,
        }
    return None


# ---------------------------------------------------------------------------
# /ask_stream — uses the shared _event_generator (non-coding mode)
# ---------------------------------------------------------------------------


@router.get("/ask_stream")
async def ask_stream(
    request: Request,
    q: str = Query(..., description="User clinical question"),
    sources: Optional[str] = Query(
        None,
        description=(
            "Comma-separated internal sources. If omitted, guideline-ish "
            "ASK_STREAM_DEFAULT_SOURCES are used."
        ),
    ),
    limit: int = Query(12, ge=1, le=64),
    ctx_k: int = Query(24, ge=1, le=128),
    valyu_k: int = Query(4, ge=0, le=16),
    with_llm: int = Query(
        1,
        ge=0,
        le=1,
        description="1=run LLM, 0=return context only",
    ),
    llm_mode: str = Query(
        "chunk",
        description="chunk=stream chunks, delta=tiny tokens (llm_delta), ctx=only context",
    ),
    use_valyu: int = Query(
        0,
        ge=0,
        le=1,
        description="1=include Valyu matches, 0=disable",
    ),
    valyu_mode: str = Query(
        "search",
        description="Valyu mode: 'search' (evidence) or 'answer'.",
    ),
    valyu_raw: int = Query(
        0,
        description=(
            "1=request full contents from Valyu (stored in meta.full_text when "
            "supported); context still uses snippets."
        ),
    ),
    valyu_sources: Optional[str] = Query(
        None,
        description="Optional CSV of Valyu sources (e.g. 'valyu/valyu-pubmed')",
    ),
    valyu_boost: float = Query(
        1.0,
        description="Reserved for future tuning of Valyu weighting",
    ),
    use_ethos: int = Query(
        0,
        description="1=include ethos_model rows and force-keep them in context",
    ),
    pool: Any = Depends(resolve_pg_pool),
) -> EventSourceResponse:
    """
    Streamed clinical QA with MKG RAG plus optional Valyu evidence.

    This shares the same retrieval + fusion pipeline as /coding_stream
    via _event_generator, but with:

      - coding_mode=False
      - Default sources = guideline-ish ASK_STREAM_DEFAULT_SOURCES
      - Optional Valyu tail
    """

    # Parse sources list
    if sources:
        raw_sources = [s.strip() for s in sources.split(",") if s.strip()]
        # De-duplicate but preserve order
        seen = set()
        db_sources: List[str] = []
        for s in raw_sources:
            if s not in seen:
                seen.add(s)
                db_sources.append(s)
    else:
        db_sources = list(ASK_STREAM_DEFAULT_SOURCES)

    warning = _send_large_request_warning(q, db_sources, limit)

    async def event_gen() -> AsyncIterator[Dict[str, str]]:
        # Optional warning before the shared pipeline
        if warning:
            yield sse("warning", warning)

        async for ev in _event_generator(
            request=request,
            q=q,
            db_sources=db_sources,
            limit=limit,
            ctx_k=ctx_k,
            valyu_k=valyu_k,
            with_llm=bool(with_llm),
            llm_mode=llm_mode,
            use_valyu_bool=bool(use_valyu),
            valyu_mode=valyu_mode,
            valyu_raw_bool=bool(valyu_raw),   # <-- passes through as bool
            valyu_sources=valyu_sources,
            valyu_boost=valyu_boost,
            pool=pool,
            coding_mode=False,                 # 🔑 non-coding mode
            use_ethos_bool=bool(use_ethos),
        ):
            yield ev

    return EventSourceResponse(event_gen(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# /coding_stream — unchanged, still uses shared _event_generator
# ---------------------------------------------------------------------------


@router.get("/coding_stream")
async def coding_stream(
    request: Request,
    q: str = Query(..., description="Coding / abstraction query"),
    sources: Optional[str] = Query(
        None,
        description=(
            "Comma-separated source list. If omitted, CODING_DEFAULT_SOURCES "
            "from stream_config is used."
        ),
    ),
    limit: int = Query(8, ge=1, le=64),
    ctx_k: int = Query(
        max(BASE_RRF_K, 128),
        ge=1,
        le=128,
        description="Number of internal context chunks (pre-fusion)",
    ),
    valyu_k: int = Query(4, ge=0, le=16),
    with_llm: int = Query(1, description="1=run LLM, 0=return context only"),
    llm_mode: str = Query(
        "chunk",
        description="chunk=stream chunks, delta=tiny tokens (llm_delta), ctx=only context",
    ),
    use_valyu: int = Query(0, description="1=include Valyu matches, 0=disable"),
    valyu_mode: str = Query(
        "answer",
        description="Valyu mode: 'answer' or 'search'",
    ),
    valyu_raw: int = Query(0, description="1=include raw Valyu payload in SSE"),
    valyu_sources: Optional[str] = Query(
        None,
        description="Optional CSV of Valyu sources (e.g. 'valyu/valyu-pubmed')",
    ),
    valyu_boost: float = Query(1.0, description="Reserved for future tuning"),
    use_ethos: int = Query(0, description="1=include ethos_model rows"),
    pool: Any = Depends(resolve_pg_pool),
) -> EventSourceResponse:
    """
    SSE endpoint for coding/abstraction.

    Key differences from /ask_stream:
      - coding_mode=True (tighter code retrieval & context formatting)
      - Default sources = CODING_DEFAULT_SOURCES
      - Same core pipeline via _event_generator
      - PLUS: clamp source fan-out to MAX_CODING_SOURCES with a warning.
    """
    # Parse sources list
    if sources:
        raw_sources = [s.strip() for s in sources.split(",") if s.strip()]
        # De-duplicate but preserve order
        seen = set()
        db_sources: List[str] = []
        for s in raw_sources:
            if s not in seen:
                seen.add(s)
                db_sources.append(s)
    else:
        db_sources = list(CODING_DEFAULT_SOURCES)

    original_source_count = len(db_sources)
    clamped = False

    # Clamp fan-out to avoid hammering RAG with 20+ code sources.
    if original_source_count > MAX_CODING_SOURCES:
        clamped = True

        # Prefer default coding sources first, then fill with any remaining.
        preferred_order: List[str] = []

        # 1) Walk CODING_DEFAULT_SOURCES in order and include those that were requested
        for s in CODING_DEFAULT_SOURCES:
            if s in db_sources and s not in preferred_order:
                preferred_order.append(s)
                if len(preferred_order) >= MAX_CODING_SOURCES:
                    break

        # 2) If we still have room, fill with remaining requested sources in original order
        if len(preferred_order) < MAX_CODING_SOURCES:
            for s in db_sources:
                if s not in preferred_order:
                    preferred_order.append(s)
                    if len(preferred_order) >= MAX_CODING_SOURCES:
                        break

        db_sources = preferred_order[:MAX_CODING_SOURCES]

        logger.info(
            "coding_stream: clamped sources from %d to %d: %r",
            original_source_count,
            len(db_sources),
            db_sources,
        )

    async def event_gen():
        # If we had to clamp, emit a warning BEFORE the main pipeline events.
        if clamped:
            yield sse(
                "warning",
                {
                    "warning": (
                        f"Requested {original_source_count} coding sources; "
                        f"clamped to {len(db_sources)} to avoid noisy or slow retrieval."
                    ),
                    "max_sources": MAX_CODING_SOURCES,
                    "sources_used": db_sources,
                },
            )

        async for ev in _event_generator(
            request=request,
            q=q,
            db_sources=db_sources,
            limit=limit,
            ctx_k=ctx_k,
            valyu_k=valyu_k,
            with_llm=bool(with_llm),
            llm_mode=llm_mode,
            use_valyu_bool=bool(use_valyu),
            valyu_mode=valyu_mode,
            valyu_raw_bool=bool(valyu_raw),
            valyu_sources=valyu_sources,
            valyu_boost=valyu_boost,
            pool=pool,
            coding_mode=True,              # 🔑 coding mode
            use_ethos_bool=bool(use_ethos),
        ):
            yield ev

    return EventSourceResponse(event_gen(), media_type="text/event-stream")