# rag_stream_custom_endpoints.py

from fastapi import APIRouter, Query, Request, Depends
from .stream_config import GUIDELINE_SOURCES, ETHOS_SOURCE_NAME, CODING_DEFAULT_SOURCES
from sse_starlette.sse import EventSourceResponse
from typing import Optional, List, Any, AsyncIterator, Dict
import json
import logging

# Import functions from your existing rag_stream_routes.py
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
from .stream_config import (
    BASE_RRF_K,
    CHAT_MODEL,
    CODING_DEFAULT_SOURCES,
    CODE_SOURCES,
    EMBED_MODEL,
    MAX_CONTEXT_CHARS,
    ETHOS_SOURCE_NAME,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag-custom"])

# Default ask_stream sources: all guideline-ish sources, but EXCLUDE Ethos by default.
ASK_STREAM_DEFAULT_SOURCES = sorted(
    [s for s in GUIDELINE_SOURCES if s != ETHOS_SOURCE_NAME]
)

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

# server/api/rag_stream_custom_endpoints.py

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
    valyu_k: int = Query(4, ge=0, le=32, description="Valyu tail size"),
    with_llm: int = Query(1, description="1 = run LLM, 0 = retrieval only"),
    llm_mode: str = Query("chunk"),
    use_valyu: int = Query(0, description="1 = include Valyu, 0 = skip"),
    valyu_mode: str = Query("answer"),
    valyu_raw: int = Query(0),
    valyu_sources: Optional[str] = Query(None),
    valyu_boost: float = Query(1.0),
    use_ethos: int = Query(
        0,
        description="1 = force-keep ethos_model in gating, 0 = normal gating",
    ),
    pool: Any = Depends(resolve_pg_pool),
):
    # Parse sources list
    if sources:
        db_sources = [s.strip() for s in sources.split(",") if s.strip()]
    else:
        db_sources = ASK_STREAM_DEFAULT_SOURCES

    # If use_ethos is set, ensure ethos_model is included
    if use_ethos and ETHOS_SOURCE_NAME not in db_sources:
        db_sources.append(ETHOS_SOURCE_NAME)

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
            with_llm=bool(with_llm),
            llm_mode=llm_mode,
            use_valyu_bool=bool(use_valyu),
            valyu_mode=valyu_mode,
            valyu_raw_bool=bool(valyu_raw),
            valyu_sources=valyu_sources,
            valyu_boost=valyu_boost,
            pool=pool,
            coding_mode=False,
            use_ethos_bool=bool(use_ethos),
        ):
            yield ev
    return EventSourceResponse(event_gen(), media_type="text/event-stream")

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
    ctx_k: int = Query(BASE_RRF_K, ge=1, le=128),
    valyu_k: int = Query(4, ge=0, le=16),
    with_llm: int = Query(1, description="1=run LLM, 0=return context only"),
    llm_mode: str = Query(
        "chunk",
        description="chunk=stream chunks, answer=single answer, ctx=only context",
    ),
    use_valyu: int = Query(0, description="1=include Valyu matches, 0=disable"),
    valyu_mode: str = Query(
        "answer", description="Valyu mode: 'answer' or 'evidence_only'"
    ),
    valyu_raw: int = Query(0, description="1=include raw Valyu payload in SSE"),
    use_ethos: int = Query(0, description="1=include ethos_model rows"),
    pool: Any = Depends(resolve_pg_pool),
) -> EventSourceResponse:
    """
    Streaming endpoint tailored for *coding / abstraction* use cases.

    Key differences vs /ask_stream:
    - coding_mode=True to bias retrieval & formatting toward codes.
    - Default sources come from CODING_DEFAULT_SOURCES.
    """
    if sources:
        db_sources = [s.strip() for s in sources.split(",") if s.strip()]
    else:
        from .stream_config import CODING_DEFAULT_SOURCES

        db_sources = list(CODING_DEFAULT_SOURCES)

    with_llm_bool = bool(with_llm)
    use_valyu_bool = bool(use_valyu)
    valyu_raw_bool = bool(valyu_raw)
    use_ethos_bool = bool(use_ethos)

    async def gen() -> AsyncIterator[Dict[str, str]]:
        async for ev in _event_generator(
            request=request,
            q=q,
            db_sources=db_sources,
            limit=limit,
            ctx_k=ctx_k,
            valyu_k=valyu_k,
            with_llm=with_llm_bool,
            llm_mode=llm_mode,
            use_valyu_bool=use_valyu_bool,
            valyu_mode=valyu_mode,
            valyu_raw_bool=valyu_raw_bool,
            valyu_sources=None,
            valyu_boost=1.0,
            pool=pool,
            coding_mode=True,  # 👈 THIS is the only special sauce
            use_ethos_bool=use_ethos_bool,
        ):
            yield ev

    return EventSourceResponse(gen())

