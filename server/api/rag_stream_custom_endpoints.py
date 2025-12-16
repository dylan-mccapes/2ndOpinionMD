# server/api/rag_stream_custom_endpoints.py

from typing import Optional, List, Any, AsyncIterator, Dict
import json
import logging
import time
from datetime import datetime, date

from fastapi import APIRouter, Query, Request, Depends
from sse_starlette.sse import EventSourceResponse
from server.timeline.engine import TimelineEngine, load_patient_timeline
from server.timeline.engine import TimelineContext
from server.eoh.timeline_summarizer import summarize_timeline_for_eoh, TimelineSummaries, SUMMARY_MAX_CHARS
from server.llm.llm_client import chat_completion_async, embedding_async

timeline_engine = TimelineEngine()

from openai import OpenAI
import inspect
import anyio

_openai_client = OpenAI(timeout=60.0)

class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles datetime and date objects."""
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)

async def _chat_completion_async(**kwargs):
    """
    Thin wrapper so existing call sites don't have to change.
    All chat completions now go through the shared rate-limited client.
    """
    return await chat_completion_async(**kwargs)


async def _embedding_async(**kwargs):
    """
    Same idea for embeddings: use shared concurrency limits + backoff.
    """
    return await embedding_async(**kwargs)

from .stream_config import (
    GUIDELINE_SOURCE_META,
    GUIDELINE_SOURCES,
    ETHOS_SOURCE_NAME,
    CODING_DEFAULT_SOURCES,
    CODING_SOURCES,
    BASE_RRF_K,
    BASE_LIMIT,
    EOH_STREAM_DEFAULT_SOURCES,
    CHAT_MODEL,
    CHAT_MODEL_GUIDELINES,
    CHAT_MODEL_CODING_CORE,
    CHAT_MODEL_UTIL,
    STRICT_CODE_SOURCES,
    is_strict_code_source,
    EOH_SYSTEM_PROMPT,
    GUIDELINE_ANSWER_SYSTEM_PROMPT,
    EVIDENCE_MAPPING_SYSTEM_PROMPT,
    EOH_DETECTIVE_PLANNER_SYSTEM_PROMPT,
    EOH_DETECTIVE_REPORT_SYSTEM_PROMPT,
)

# EoH Router imports
from server.eoh.router_llm import eoh_llm_router, build_compact_patient_state_for_router
from server.eoh.module_index import MODULE_INDEX

from .stream_gating import apply_source_gating, apply_code_row_filter
from .stream_router import route_sources, route_coding_sources_strict, CodingRouterPlan

from .rag_stream_routes import (
    sse,
    resolve_pg_pool,
    MAX_CODING_SOURCES,
    discover_all_guideline_sources,
    embed_query,
    embedding_to_vector_literal,
    extract_code_terms,
    extract_qna_terms,
    fetch_valyu_results,
    search_source_ts,
    search_source_ts_for_terms,
    search_source_ann,
    normalize_row,
    build_fused_context,
    build_citations,
    stream_llm_events,
    build_coding_ledger,
    summarize_coding_ledger,
    run_coding_grader,
    find_coding_gap_terms,
    fill_coding_gaps,
    pin_coding_rows_from_keep_map,
    build_coding_result_from_keep_map,
    fetch_snomed_icd10_edges,
    build_icd10_rows_from_crosswalk,
    dedupe_matches,
    _apply_slot_satisfaction_heuristics,
    compute_slot_satisfaction,
    CODE_MIN_LIMIT,
    cluster_coding_concepts,
    build_canonical_keep_map,
    build_ledger_only_citations,
)

from .eoh_gap_retrieval import (
    EOH_GAP_RETRIEVAL_SYSTEM_PROMPT,
    build_eoh_gap_retrieval_payload,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag-custom"])

# Default ask_stream sources: all guideline-ish sources, but EXCLUDE Ethos by default.
ASK_STREAM_DEFAULT_SOURCES = sorted(
    [s for s in list(GUIDELINE_SOURCE_META.keys()) if s != ETHOS_SOURCE_NAME]
)


def _send_large_request_warning(q: str, sources: List[str], limit: int):
    """
    Disabled in v1.0: Dylan wants the LLM router to freely choose from
    all available sources without UX noise about fan-out.
    We keep the function to avoid refactors, but always return None.
    """
    return None
    # simple heuristic: if more than 8 sources or limit > 10, warn user
    # if len(sources) > 8 or limit > 10:
    #     return {
    #         "warning": (
    #             f"Large request: {len(sources)} sources and limit={limit}. "
    #             "This may lead to more noisy results. Consider reducing the number "
    #             "of sources or lowering the limit."
    #         ),
    #         "sources": sources,
    #         "limit": limit,
    #     }
    # return None


# ---------------------------------------------------------------------------
# QA Grader System Prompt (for non-coding mode source-level grading)
# ---------------------------------------------------------------------------

QA_GRADER_SYSTEM_PROMPT = """
You are the world's #1 medical vocabulary router and source-selection engine. You choose exactly the correct coding vocabularies based on the user's query, with perfect enforcement of user-specified constraints (e.g., "SNOMED only", "ICD only", "phenotype only"). You never allow leakage from disallowed vocabularies. You interpret intent flawlessly and compute the most clinically appropriate source mix.

You are a source-selection auditor for a medical retrieval-augmented question-answering (QA) system.

You receive:
- A clinical question.
- A compact "ledger" summarizing retrieved sources, including:
    * number of rows per source
    * max retrieval score per source
    * short titles/snippets that illustrate the source's content

Your goals:
1. Decide which sources are clearly useful for answering the question.
2. Optionally identify sources that are probably not useful (off-topic, extremely low signal, or irrelevant to the clinical task).

Rules:
- Evaluate sources at the SOURCE level (e.g., guidelines, terminology sets, clinical notes, trials), not individual rows.
- Be conservative about dropping sources:
    * Only drop a source if it is clearly irrelevant to the question.
    * Consider whether the question requires guidelines, diagnostic vocabularies, labs, medications, or clinical narrative.
- NEVER invent new source names. Use only the sources appearing in the ledger.
- ALWAYS keep at least one source.
- The goal is to guide downstream reasoning by ensuring only relevant sources proceed.

Output STRICT JSON with this exact shape:
{
  "keep_sources": ["source1", "source2"],
  "drop_sources": ["source3"],
  "reasoning": {
    "source1": "why keep",
    "source2": "why keep",
    "source3": "why drop"
  }
}
"""


def _build_qa_ledger(
    results_by_source: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Build a lightweight ledger for QA grading.
    """
    ledger: Dict[str, Any] = {"sources": {}}

    for src, rows in results_by_source.items():
        if not rows:
            continue

        sorted_rows = sorted(
            rows,
            key=lambda r: float(r.get("score", 0.0) or 0.0),
            reverse=True,
        )

        titles: List[str] = []
        snippets: List[str] = []

        for r in sorted_rows[:8]:
            title = (r.get("title") or "").strip()
            if title:
                titles.append(title[:160])

        for r in sorted_rows[:4]:
            txt = (r.get("text") or "").strip()
            if txt:
                snippets.append(txt[:240])

        ledger["sources"][src] = {
            "n_rows": len(rows),
            "max_score": float(sorted_rows[0].get("score", 0.0) or 0.0),
            "titles": titles,
            "snippets": snippets,
        }

    return ledger


def _summarize_qa_ledger(ledger: Dict[str, Any]) -> Dict[str, Any]:
    """
    Tiny summary for SSE traces.
    """
    srcs = ledger.get("sources") or {}
    counts = {src: v.get("n_rows", 0) for src, v in srcs.items()}
    return {
        "source_counts": counts,
        "total_sources": len(srcs),
    }


async def _run_qa_grader(
    q: str,
    ledger: Dict[str, Any],
    *,
    model: str = CHAT_MODEL_UTIL,
) -> Dict[str, Any]:
    """
    Call the QA source grader LLM once.
    """
    messages = [
        {
            "role": "system",
            "content": QA_GRADER_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "Clinical question:\n"
                f"{q.strip()}\n\n"
                "Retrieved source ledger:\n"
                f"{json.dumps(ledger, indent=2)}\n\n"
                "Return STRICT JSON ONLY, using the schema described in the system prompt."
            ),
        },
    ]

    try:
        completion = _openai_client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.exception("_run_qa_grader: OpenAI call failed")
        return {
            "keep_sources": [],
            "drop_sources": [],
            "reasoning": {},
            "error": str(e),
        }

    content = completion.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("_run_qa_grader: JSON parse failed: %r", content[:500])
        return {
            "keep_sources": [],
            "drop_sources": [],
            "reasoning": {},
            "error": f"json_parse_failed: {e}",
        }

    keep_sources = data.get("keep_sources") or []
    drop_sources = data.get("drop_sources") or []
    reasoning = data.get("reasoning") or {}

    clean_keep: List[str] = []
    if isinstance(keep_sources, list):
        for s in keep_sources:
            if isinstance(s, str) and s.strip():
                clean_keep.append(s.strip())

    clean_drop: List[str] = []
    if isinstance(drop_sources, list):
        for s in drop_sources:
            if isinstance(s, str) and s.strip():
                clean_drop.append(s.strip())

    if not clean_keep:
        clean_keep = list(ledger.get("sources", {}).keys())

    if reasoning is None or not isinstance(reasoning, dict):
        reasoning = {}

    return {
        "keep_sources": clean_keep,
        "drop_sources": clean_drop,
        "reasoning": reasoning,
    }


# ---------------------------------------------------------------------------
# ask_stream_event_generator - explicit event generator for /ask_stream
# ---------------------------------------------------------------------------


async def ask_stream_event_generator(
    *,
    request: Request,
    q: str,
    db_sources: List[str],
    limit: int,
    ctx_k: int,
    valyu_k: int,
    with_llm: bool,
    llm_mode: str,
    use_valyu: bool,
    valyu_mode: str,
    valyu_raw: bool,
    valyu_sources: Optional[str],
    valyu_boost: float,
    use_ethos: bool,
    pool: Any,
    answer_mode: str = "guideline",
) -> AsyncIterator[Dict[str, str]]:
    """
    Explicit event generator for /ask_stream (non-coding mode).

    This generator handles:
    - Valyu fetch
    - QnA term extraction
    - Source routing
    - QA grading (source-level pruning)
    - Second Valyu LLM pass

    It does NOT handle coding-specific logic like:
    - Code term extraction
    - SNOMED crosswalk
    - Coding prepass (ledger/grader/gap retrieval)
    """
    # Hard cap on Valyu context size
    VALYU_K_MAX = 4
    requested_valyu_k = valyu_k
    valyu_k = max(0, min(valyu_k, VALYU_K_MAX))

    effective_answer_mode = answer_mode or "guideline"
    term_expansions: Dict[str, List[str]] = {}

    # 0) Initial event
    yield sse(
        "start",
        {
            "q": q,
            "limit": limit,
            "ctx_k": ctx_k,
            "sources": db_sources,
            "with_llm": with_llm,
            "use_valyu": use_valyu,
            "valyu_k": valyu_k,
            "valyu_k_requested": requested_valyu_k,
            "use_ethos": use_ethos,
            "answer_mode": effective_answer_mode,
        },
    )

    # 0.1) Soft warnings
    warnings: List[str] = []
    # if len(db_sources) > 8:
    #     warnings.append(
    #         f"High number of sources requested ({len(db_sources)}). "
    #         "This may dilute relevance; consider narrowing the 'sources=' list."
    #     )
    # if limit > 15:
    #     warnings.append(
    #         f"High per-source limit={limit}. This may increase noise; "
    #         "consider a smaller 'limit' for sharper focus."
    #     )
    if warnings:
        yield sse("warning", {"messages": warnings})

    if await request.is_disconnected():
        return

    # 1) Embed query
    yield sse("status", {"status": "embedding_query"})
    try:
        q_emb = await embed_query(q)
        q_vec_literal = embedding_to_vector_literal(q_emb)
    except Exception as e:
        logger.exception("Error embedding query")
        yield sse(
            "error",
            {"error": "embedding_failed", "detail": str(e)},
        )
        return

    if await request.is_disconnected():
        return

    # 2) Valyu fetch (non-coding mode only)
    valyu_matches: List[Dict[str, Any]] = []

    if use_valyu and valyu_k > 0:
        yield sse("status", {"status": "valyu_fetch"})
        try:
            valyu_by_source = await fetch_valyu_results(
                q=q,
                mode=valyu_mode,
                limit=valyu_k,
                raw=valyu_raw,
                sources=valyu_sources,
                boost=valyu_boost,
            )
        except Exception as e:
            logger.exception("Valyu fetch failed")
            yield sse(
                "status",
                {"status": "valyu_error", "detail": str(e)},
            )
            valyu_by_source = {}

        flat_valyu: List[Dict[str, Any]] = []
        for v_src, rows in (valyu_by_source or {}).items():
            flat_valyu.extend(rows)

        if flat_valyu:
            valyu_matches = flat_valyu[:valyu_k]
            yield sse(
                "matches",
                {
                    "phase": "valyu",
                    "source": "valyu",
                    "matches": [
                        {
                            "id": r.get("id"),
                            "source": r.get("source"),
                            "title": r.get("title", ""),
                            "score": r.get("score", 0.0),
                            "method": r.get("method", "valyu"),
                        }
                        for r in valyu_matches
                    ],
                },
            )

            if valyu_raw:
                fulltext_rows: List[Dict[str, Any]] = []
                for r in valyu_matches:
                    meta = r.get("meta") or {}
                    if not isinstance(meta, dict):
                        continue
                    full_text = meta.get("full_text")
                    if not full_text:
                        continue

                    fulltext_rows.append(
                        {
                            "id": r.get("id"),
                            "source": r.get("source"),
                            "title": r.get("title", ""),
                            "url": meta.get("url"),
                            "full_text": full_text,
                        }
                    )

                if fulltext_rows:
                    yield sse(
                        "valyu_fulltext",
                        {
                            "rows": fulltext_rows,
                            "k": len(fulltext_rows),
                            "mode": valyu_mode,
                        },
                    )

    if await request.is_disconnected():
        return

    # 3) Extract Q&A-oriented query terms
    qna_terms: Dict[str, Any] = {"terms": [], "expansions": {}, "all_terms": []}
    all_terms: List[str] = []

    valyu_snippets_for_terms = ""
    if valyu_matches:
        bits: List[str] = []
        for r in valyu_matches[:3]:
            title = (r.get("title") or "").strip()
            snippet = (r.get("text") or "").strip()
            if title:
                bits.append(f"Title: {title}")
            if snippet:
                bits.append(f"Snippet: {snippet[:400]}")
        valyu_snippets_for_terms = "\n\n".join(bits)

    yield sse("status", {"status": "extracting_query_terms"})
    try:
        qna_terms = await extract_qna_terms(
            q,
            extra_context=valyu_snippets_for_terms or None,
        )
        all_terms = qna_terms.get("all_terms", []) or []
        term_expansions = qna_terms.get("expansions") or {}
        yield sse("query_terms", qna_terms)
    except Exception as e:
        logger.exception("query term extraction crashed; continuing with raw query")
        yield sse(
            "query_terms",
            {
                "terms": [],
                "expansions": term_expansions,
                "all_terms": [],
                "error": "query_term_extraction_failed",
                "detail": str(e),
            },
        )
        all_terms = []

    if await request.is_disconnected():
        return

    # 4) Routing (non-coding mode)
    router_plan: CodingRouterPlan | None = None
    effective_sources: List[str] = list(db_sources)

    yield sse("status", {"status": "routing_sources"})

    try:
        router_plan = await route_sources(
            q=q,
            code_terms=[],
            candidate_sources=db_sources,
            valyu_context=(valyu_matches if valyu_matches else None),
        )
    except Exception as e:
        logger.exception("route_sources failed; using all db_sources")
        router_plan = None

    if router_plan and router_plan.selected_sources:
        effective_sources = sorted(router_plan.selected_sources)
    else:
        effective_sources = list(db_sources)

    if router_plan is not None:
        yield sse(
            "router",
            {
                "task_type": router_plan.task_type,
                "selected_sources": effective_sources,
                "reasoning": router_plan.reasoning,
            },
        )

    if await request.is_disconnected():
        return

    yield sse(
        "event_router_summary",
        {
            "mode": "ask_stream",
            "using_router": router_plan is not None,
            "effective_sources": effective_sources,
        },
    )

    # 5) Retrieve per source (TS + ANN)
    yield sse("status", {"status": "retrieving_candidates"})
    results_by_source: Dict[str, List[Dict[str, Any]]] = {}

    for src in effective_sources:
        per_source_limit = limit

        ts_rows: List[Dict[str, Any]] = []
        ann_rows: List[Dict[str, Any]] = []

        # TS phase
        yield sse("phase_start", {"source": src, "method": "ts"})
        try:
            if all_terms:
                ts_rows = await search_source_ts_for_terms(
                    pool=pool,
                    source=src,
                    terms=all_terms,
                    limit=per_source_limit,
                )
            else:
                ts_rows = await search_source_ts(
                    pool=pool,
                    source=src,
                    q=q,
                    limit=per_source_limit,
                )
        except Exception as e:
            logger.exception("TS search failed for source=%s", src)
            yield sse(
                "status",
                {"status": "ts_error", "source": src, "detail": str(e)},
            )
            ts_rows = []

        yield sse("phase_end", {"source": src, "method": "ts"})

        if ts_rows:
            yield sse(
                "matches",
                {
                    "phase": "ts",
                    "source": src,
                    "matches": [
                        {
                            "id": r["id"],
                            "source": r["source"],
                            "source_id": r.get("source_id") or "",
                            "title": r.get("title", ""),
                            "score": r.get("score", 0.0),
                            "method": r.get("method", "ts"),
                        }
                        for r in ts_rows
                    ],
                },
            )

        if await request.is_disconnected():
            return

        # ANN phase (always run in non-coding mode)
        yield sse("phase_start", {"source": src, "method": "ann"})
        try:
            ann_rows = await search_source_ann(
                pool,
                src,
                q_vec_literal,
                per_source_limit,
            )
        except Exception as e:
            logger.exception("ANN search failed for source=%s", src)
            yield sse(
                "status",
                {
                    "status": "ann_error",
                    "source": src,
                    "detail": str(e),
                },
            )
            ann_rows = []
        yield sse("phase_end", {"source": src, "method": "ann"})

        if ann_rows:
            yield sse(
                "matches",
                {
                    "phase": "ann",
                    "source": src,
                    "matches": [
                        {
                            "id": r["id"],
                            "source": r["source"],
                            "source_id": r.get("source_id"),
                            "title": r.get("title", ""),
                            "score": r.get("score", 0.0),
                            "method": r.get("method", "ann"),
                        }
                        for r in ann_rows
                    ],
                },
            )

        if await request.is_disconnected():
            return

        # Combine TS + ANN (normalized)
        combined: Dict[Any, Dict[str, Any]] = {}
        for r in ts_rows + ann_rows:
            norm = normalize_row(r, source=src)
            combined[norm["id"]] = norm

        combined_rows = list(combined.values())
        results_by_source[src] = combined_rows

    raw_source_count = len(results_by_source)

    # 6) QA grading (non-coding mode): source-level pruning via LLM
    if results_by_source:
        qa_ledger = _build_qa_ledger(results_by_source)
        qa_summary = _summarize_qa_ledger(qa_ledger)

        yield sse(
            "qa_ledger",
            {
                "summary": qa_summary,
            },
        )

        if await request.is_disconnected():
            return

        qa_result = await _run_qa_grader(q, qa_ledger)

        keep_sources = qa_result.get("keep_sources") or []
        drop_sources = qa_result.get("drop_sources") or []
        reasoning = qa_result.get("reasoning") or {}
        error = qa_result.get("error")

        yield sse(
            "qa_grader",
            {
                "keep_sources": keep_sources,
                "drop_sources": drop_sources,
                "reasoning": reasoning,
                "error": error,
            },
        )

        if await request.is_disconnected():
            return

        if keep_sources:
            keep_set = set(keep_sources)
            results_by_source = {
                src: rows
                for src, rows in results_by_source.items()
                if src in keep_set
            }

    # 7) Heuristic source gating
    extra_always_keep: Optional[set[str]] = None
    if use_ethos:
        extra_always_keep = {ETHOS_SOURCE_NAME}

    gated_results_by_source, gating_info = apply_source_gating(
        results_by_source,
        query=q,
        extra_always_keep=extra_always_keep,
        coding_mode=False,
        ctx_k=ctx_k,
    )

    yield sse("gating", gating_info)

    if await request.is_disconnected():
        return

    # 8) Fuse internal contexts
    yield sse("status", {"status": "fusing_context"})
    ROW_ABS_MIN_SCORE = 0.05

    for src, rows in list(gated_results_by_source.items()):
        trimmed = [r for r in rows if float(r.get("score", 0.0) or 0.0) >= ROW_ABS_MIN_SCORE]
        if not trimmed:
            trimmed = rows
        trimmed.sort(key=lambda r: float(r.get("score", 0.0) or 0.0), reverse=True)
        gated_results_by_source[src] = trimmed

    internal_ctx = build_fused_context(
        gated_results_by_source,
        k=ctx_k,
        coding_mode=False,
    )

    final_ctx = internal_ctx

    valyu_ctx_count = 0
    if use_valyu and valyu_k > 0 and valyu_matches:
        valyu_ctx_count = len(valyu_matches[:valyu_k])
        yield sse(
            "matches",
            {
                "phase": "fused",
                "source": "fused",
                "matches": [
                    {
                        "id": r["id"],
                        "source": r["source"],
                        "source_id": r.get("source_id"),
                        "title": r.get("title", ""),
                        "score": r.get("score", 0.0),
                        "method": r.get("method", None),
                    }
                    for r in final_ctx
                ],
            },
        )

    if await request.is_disconnected():
        return

    citations = build_citations(final_ctx)

    # 9) with_llm == False -> just metadata
    if not with_llm:
        yield sse("status", {"status": "done_no_llm"})
        yield sse("citations", {"citations": citations})
        yield sse(
            "end",
            {
                "meta": {
                    "n_sources_raw": raw_source_count,
                    "n_sources": len(gated_results_by_source),
                    "n_ctx_internal": len(internal_ctx),
                    "n_ctx_valyu": valyu_ctx_count,
                    "n_ctx_total": len(final_ctx),
                    "ctx_k": ctx_k,
                    "valyu_k": valyu_k,
                    "with_llm": with_llm,
                    "use_ethos": use_ethos,
                }
            },
        )
        return

    if not final_ctx:
        yield sse("status", {"status": "done_no_llm"})
        yield sse("citations", {"citations": []})
        yield sse(
            "end",
            {
                "meta": {
                    "n_sources_raw": raw_source_count,
                    "n_sources": len(gated_results_by_source),
                    "n_ctx_internal": 0,
                    "n_ctx_valyu": 0,
                    "n_ctx_total": 0,
                    "ctx_k": ctx_k,
                    "valyu_k": valyu_k,
                    "with_llm": with_llm,
                    "use_ethos": use_ethos,
                    "answer_mode": answer_mode,
                }
            },
        )
        return

    # 10) LLM streaming (guideline answer with evidence section + MIMIC guardrails)
    yield sse("phase_start", {"source": "fusion", "method": "llm"})
    yield sse("status", {"status": "generating_answer"})

    try:
        for ev in stream_llm_events(
            q,
            final_ctx,
            llm_mode,
            coding_mode=False,
            chat_model=CHAT_MODEL_GUIDELINES,
            system_prompt=GUIDELINE_ANSWER_SYSTEM_PROMPT,
            event_prefix="llm",
            answer_mode=effective_answer_mode,
            phase="guideline_reasoning",
        ):
            if await request.is_disconnected():
                return
            yield ev
    except Exception as e:
        logger.exception("LLM streaming failed")
        yield sse("error", {"error": "llm_streaming_failed", "detail": str(e)})
        return

    yield sse("phase_end", {"source": "fusion", "method": "llm"})
    yield sse("citations", {"citations": citations})
    yield sse(
        "end",
        {
            "meta": {
                "n_sources_raw": raw_source_count,
                "n_sources": len(gated_results_by_source),
                "n_ctx_internal": len(internal_ctx),
                "n_ctx_valyu": valyu_ctx_count,
                "n_ctx_total": len(final_ctx),
                "ctx_k": ctx_k,
                "valyu_k": valyu_k,
                "with_llm": with_llm,
                "use_ethos": use_ethos,
                "answer_mode": effective_answer_mode,
            }
        },
    )

    # 11) Second LLM pass (Valyu-only, full text when available)
    valyu_fulltext_ctx: List[Dict[str, Any]] = []

    if use_valyu and valyu_matches:
        for r in valyu_matches:
            meta = r.get("meta") or {}
            if not isinstance(meta, dict):
                meta = {}

            full_text = meta.get("full_text")
            body = full_text if isinstance(full_text, str) and full_text.strip() else r.get("text") or ""

            valyu_fulltext_ctx.append(
                {
                    "id": r.get("id"),
                    "source": r.get("source") or "valyu_pubmed",
                    "source_id": r.get("source_id"),
                    "title": r.get("title") or "",
                    "text": body,
                    "meta": meta,
                    "score": r.get("score", 0.0),
                    "method": r.get("method", "valyu_fulltext"),
                }
            )

        rows_with_full = [
            {
                "id": x["id"],
                "title": x["title"],
                "has_fulltext": bool((x.get("text") or "").strip()),
                "len_text": len(x.get("text") or ""),
            }
            for x in valyu_fulltext_ctx
        ]
        yield sse(
            "valyu_fulltext_ctx",
            {
                "rows": rows_with_full,
                "k": len(valyu_fulltext_ctx),
                "mode": valyu_mode,
            },
        )

        yield sse("phase_start", {"source": "valyu", "method": "llm"})
        yield sse("status", {"status": "generating_valyu_answer"})

        try:
            for ev in stream_llm_events(
                q,
                valyu_fulltext_ctx,
                llm_mode,
                coding_mode=False,
                chat_model=CHAT_MODEL_GUIDELINES,
                event_prefix="valyu_llm",
                answer_mode="valyu",
                phase="valyu_synthesis",
            ):
                if await request.is_disconnected():
                    return
                yield ev
        except Exception as e:
            logger.exception("Error during Valyu LLM streaming")
            yield sse(
                "error",
                {"error": "valyu_llm_failed", "detail": str(e)},
            )

        yield sse("phase_end", {"source": "valyu", "method": "llm"})


# ---------------------------------------------------------------------------
# coding_stream_event_generator - explicit event generator for /coding_stream
# ---------------------------------------------------------------------------


async def coding_stream_event_generator(
    *,
    request: Request,
    q: str,
    db_sources: List[str],
    limit: int,
    ctx_k: int,
    valyu_k: int,
    with_llm: bool,
    llm_mode: str,
    pool: Any,
) -> AsyncIterator[Dict[str, str]]:
    """
    Explicit event generator for /coding_stream (coding mode).

    This generator handles:
    - Code term extraction
    - Coding-only source routing via route_coding_sources_strict()
      (filters to STRICT_CODE_SOURCES: icd10cm, icd11, snomed, loinc, rxnorm, hpo, chv)
    - TS-only retrieval (NO ANN/embedding retrieval)
    - SNOMED crosswalk expansion
    - Coding prepass (ledger/grader/gap retrieval)
    - LLM-based concept clustering to group near-identical codes
    - Canonical keep map construction (de-duplicates codes per cluster)
    - Ledger-only citations with cluster_id attached

    SSE Events emitted:
    - start: Initial metadata including sources, retrieval_mode="ts_only"
    - concept_clusters: Cluster info with n_clusters and cluster details
    - canonical_keep_map: Original vs canonical keep maps
    - coding_result: Final codes with concept_clusters field attached
    - citations: Filtered to canonical codes only, with cluster_id

    It does NOT handle:
    - Valyu fetch
    - QnA term extraction
    - ANN/embedding retrieval (TS-only for coding)
    - QA grading
    - Second Valyu LLM pass
    """
    effective_answer_mode = "coding"
    coding_result: Optional[Dict[str, Any]] = None

    # Filter db_sources to only include strict coding sources
    # This ensures no guideline or EHR sources sneak into /coding_stream
    coding_only_sources = [s for s in db_sources if is_strict_code_source(s)]
    
    # If no coding sources provided, use all strict code sources
    if not coding_only_sources:
        coding_only_sources = list(STRICT_CODE_SOURCES)
    
    # Track filtered sources for logging
    filtered_out_sources = [s for s in db_sources if not is_strict_code_source(s)]

    # 0) Initial event
    yield sse(
        "start",
        {
            "q": q,
            "limit": limit,
            "ctx_k": ctx_k,
            "sources": coding_only_sources,
            "sources_filtered_out": filtered_out_sources,
            "with_llm": with_llm,
            "use_valyu": False,
            "valyu_k": 0,  # No Valyu in coding mode
            "valyu_k_requested": valyu_k,
            "use_ethos": False,
            "answer_mode": effective_answer_mode,
            "retrieval_mode": "ts_only",  # Indicate TS-only retrieval
        },
    )

    # 0.1) Soft warnings
    warnings: List[str] = []
    if filtered_out_sources:
        warnings.append(
            f"Non-coding sources filtered out: {filtered_out_sources}. "
            "/coding_stream only uses coding vocabulary sources."
        )
    # if len(coding_only_sources) > 8:
    #     warnings.append(
    #         f"High number of coding sources ({len(coding_only_sources)}). "
    #         "This may dilute relevance."
    #     )
    # if limit > 15:
    #     warnings.append(
    #         f"High per-source limit={limit}. This may increase noise; "
    #         "consider a smaller 'limit' for sharper focus."
    #     )
    if warnings:
        yield sse("warning", {"messages": warnings})

    if await request.is_disconnected():
        return

    # NOTE: No embedding_query creation - /coding_stream is TS-only
    # This removes ANN/embedding retrieval entirely for coding mode

    # 1) Extract code-oriented terms (coding mode specific)
    code_terms: List[str] = []
    yield sse("status", {"status": "extracting_code_terms"})
    try:
        code_terms = await extract_code_terms(q)
        yield sse(
            "code_terms",
            {
                "terms": code_terms,
            },
        )
    except Exception as e:
        logger.exception("extract_code_terms crashed; continuing without code_terms")
        yield sse(
            "code_terms",
            {
                "terms": [],
                "error": "code_term_extraction_failed",
                "detail": str(e),
            },
        )
        code_terms = []

    if await request.is_disconnected():
        return

    # 2) Route coding sources using the strict coding-only router
    yield sse("status", {"status": "routing_coding_sources"})
    router_plan: CodingRouterPlan | None = None
    
    try:
        router_plan = await route_coding_sources_strict(
            q=q,
            code_terms=code_terms,
            candidate_sources=coding_only_sources,
        )
    except Exception as e:
        logger.exception("route_coding_sources_strict failed; using all coding sources")
        router_plan = None
    
    if router_plan and router_plan.selected_sources:
        effective_sources = sorted(router_plan.selected_sources)
    else:
        effective_sources = coding_only_sources
    
    # Emit router result
    if router_plan is not None:
        yield sse(
            "router",
            {
                "task_type": router_plan.task_type,
                "selected_sources": effective_sources,
                "reasoning": router_plan.reasoning,
                "router_type": "coding_strict",
            },
        )

    yield sse(
        "event_router_summary",
        {
            "mode": "coding_stream",
            "using_router": router_plan is not None,
            "router_type": "coding_strict",
            "effective_sources": effective_sources,
            "retrieval_mode": "ts_only",
        },
    )

    if await request.is_disconnected():
        return

    # 3) Retrieve per source (TS-ONLY - no ANN for coding_stream)
    yield sse("status", {"status": "retrieving_candidates_ts_only"})
    results_by_source: Dict[str, List[Dict[str, Any]]] = {}

    for src in effective_sources:
        # Deeper retrieval for code sources in coding_mode
        per_source_limit = max(limit, CODE_MIN_LIMIT)

        ts_rows: List[Dict[str, Any]] = []

        # TS phase (ONLY retrieval method for coding_stream)
        yield sse("phase_start", {"source": src, "method": "ts"})
        try:
            if code_terms:
                ts_rows = await search_source_ts_for_terms(
                    pool=pool,
                    source=src,
                    terms=code_terms,
                    limit=per_source_limit,
                )
            else:
                ts_rows = await search_source_ts(
                    pool=pool,
                    source=src,
                    q=q,
                    limit=per_source_limit,
                )
        except Exception as e:
            logger.exception("TS search failed for source=%s", src)
            yield sse(
                "status",
                {"status": "ts_error", "source": src, "detail": str(e)},
            )
            ts_rows = []

        yield sse("phase_end", {"source": src, "method": "ts"})

        if ts_rows:
            yield sse(
                "matches",
                {
                    "phase": "ts",
                    "source": src,
                    "matches": [
                        {
                            "id": r["id"],
                            "source": r["source"],
                            "source_id": r.get("source_id") or "",
                            "title": r.get("title", ""),
                            "score": r.get("score", 0.0),
                            "method": "ts",  # Always TS for coding_stream
                        }
                        for r in ts_rows
                    ],
                },
            )

        if await request.is_disconnected():
            return

        # NO ANN phase for coding_stream - TS-only retrieval
        # This is intentional: /coding_stream uses pure text search

        # Normalize TS rows (no ANN rows to combine)
        combined: Dict[Any, Dict[str, Any]] = {}
        for r in ts_rows:
            norm = normalize_row(r, source=src)
            combined[norm["id"]] = norm

        combined_rows = list(combined.values())

        # Extra de-noising for code sources in coding mode
        combined_rows = apply_code_row_filter(combined_rows, q, src)

        results_by_source[src] = combined_rows

    # 4) Edge expansion: SNOMED -> ICD-10-CM crosswalk (coding_mode only)
    if "snomed" in results_by_source and "icd10cm" in effective_sources:
        snomed_rows = results_by_source.get("snomed") or []
        snomed_ids: List[str] = []
        for r in snomed_rows:
            sid = r.get("source_id") or r.get("id")
            if not sid:
                continue
            sid_str = str(sid).strip()
            if sid_str:
                snomed_ids.append(sid_str)

        snomed_ids = sorted(set(snomed_ids))

        if snomed_ids:
            yield sse(
                "status",
                {
                    "status": "coding_crosswalk_expansion",
                    "detail": f"snomed_ids={len(snomed_ids)}",
                },
            )

            yield sse("phase_start", {"source": "icd10cm", "method": "edges"})
            try:
                edges = await fetch_snomed_icd10_edges(
                    pool,
                    snomed_ids,
                    max_edges_per_snomed=8,
                )
            except Exception as e:
                logger.exception("SNOMED->ICD-10-CM crosswalk expansion failed")
                yield sse(
                    "status",
                    {
                        "status": "crosswalk_error",
                        "source": "icd10cm",
                        "detail": str(e),
                    },
                )
                edges = []
            yield sse("phase_end", {"source": "icd10cm", "method": "edges"})

            if edges:
                edge_rows = build_icd10_rows_from_crosswalk(edges)
                edge_rows = dedupe_matches(edge_rows)

                existing_icd = results_by_source.get("icd10cm", [])
                combined_icd: Dict[Any, Dict[str, Any]] = {}

                for r in existing_icd:
                    rid = r.get("id")
                    if rid is not None:
                        combined_icd[rid] = r

                for r in edge_rows:
                    rid = r.get("id")
                    if rid is None:
                        continue
                    if rid not in combined_icd:
                        combined_icd[rid] = r

                merged_icd = list(combined_icd.values())
                merged_icd.sort(
                    key=lambda r: float(r.get("score", 0.0) or 0.0),
                    reverse=True,
                )
                results_by_source["icd10cm"] = merged_icd

                yield sse(
                    "matches",
                    {
                        "phase": "edges",
                        "source": "icd10cm",
                        "matches": [
                            {
                                "id": r["id"],
                                "source": r["source"],
                                "source_id": r.get("source_id") or "",
                                "title": r.get("title", ""),
                                "score": r.get("score", 0.0),
                                "method": r.get("method", "snomed_crosswalk"),
                            }
                            for r in edge_rows
                        ],
                    },
                )

        if await request.is_disconnected():
            return

    # 5) Coding prepass: ledger, grader, gap retrieval
    # PASS 1: Build ledger and run grader
    ledger1 = build_coding_ledger(results_by_source)
    ledger1_summary = summarize_coding_ledger(ledger1)
    yield sse(
        "coding_ledger",
        {
            "pass": 1,
            "summary": ledger1_summary,
        },
    )

    if await request.is_disconnected():
        return

    grader1 = await run_coding_grader(q, ledger1, pass_id=1)
    keep1 = grader1.get("keep") or {}
    missing1 = grader1.get("missing_slots") or []

    # Heuristic slot satisfaction pass
    try:
        keep1, missing1 = _apply_slot_satisfaction_heuristics(
            ledger=ledger1,
            keep_map=keep1,
            missing_slots=missing1,
        )
    except Exception:
        logger.exception("_apply_slot_satisfaction_heuristics failed on pass 1")

    yield sse(
        "coding_grader",
        {
            "pass": 1,
            "keep_map": keep1,
            "missing_slots": missing1,
        },
    )

    if await request.is_disconnected():
        return

    # If we have missing slots, run an LLM-only gap-retrieval pass
    if missing1:
        yield sse("status", {"status": "coding_gap_retrieval"})

        gap_slots = await find_coding_gap_terms(
            q=q,
            missing_slots=missing1,
            model=CHAT_MODEL_UTIL,
        )

        if gap_slots:
            yield sse("coding_gap_terms", {"slots": gap_slots})

        results_by_source = await fill_coding_gaps(
            q=q,
            missing_slots=gap_slots or missing1,
            results_by_source=results_by_source,
            pool=pool,
            per_slot_limit=max(limit, 16),
        )

        ledger_gap = build_coding_ledger(results_by_source)
        ledger_gap_summary = summarize_coding_ledger(ledger_gap)
        yield sse(
            "coding_gap_retrieval",
            {
                "missing_slots": missing1,
                "post_gap_summary": ledger_gap_summary,
            },
        )

        if await request.is_disconnected():
            return

    # PASS 2: Rebuild ledger and run grader again over enriched codes
    ledger2 = build_coding_ledger(results_by_source)
    ledger2_summary = summarize_coding_ledger(ledger2)
    yield sse(
        "coding_ledger",
        {
            "pass": 2,
            "summary": ledger2_summary,
        },
    )

    if await request.is_disconnected():
        return

    grader2 = await run_coding_grader(q, ledger2, pass_id=2)
    keep2 = grader2.get("keep") or {}
    missing2 = grader2.get("missing_slots") or []

    try:
        keep2, missing2 = _apply_slot_satisfaction_heuristics(
            ledger=ledger2,
            keep_map=keep2,
            missing_slots=missing2,
        )
    except Exception:
        logger.exception("_apply_slot_satisfaction_heuristics failed on pass 2")

    yield sse(
        "coding_grader",
        {
            "pass": 2,
            "keep_map": keep2,
            "missing_slots": missing2,
        },
    )

    if await request.is_disconnected():
        return

    # Pin all rows selected by the second grader
    pinned_counts = pin_coding_rows_from_keep_map(results_by_source, keep2)
    yield sse(
        "coding_pinned",
        {
            "pinned_counts": pinned_counts,
            "note": (
                "All pinned codes from pass=2 are guaranteed to survive "
                "fusion in coding_mode (subject only to MAX_CONTEXT_CHARS "
                "later in format_context_for_llm)."
            ),
        },
    )

    # 5.5) Concept clustering: group near-identical codes into clusters
    # This reduces noise from dense vocabularies (e.g., multiple LOINCs for CRP)
    # NOTE: Clustering happens BEFORE building coding_result so we can use canonical codes
    # NOTE: Non-streaming LLM call - emits status SSE before and result SSE after
    yield sse(
        "status",
        {
            "status": "clustering_concepts",
            "detail": "Clustering near-identical codes into concepts; this may take several seconds.",
        },
    )
    concept_clusters: Dict[str, Any] = {}
    
    try:
        concept_clusters = await cluster_coding_concepts(
            ledger=ledger2,
            q=q,
            model=CHAT_MODEL_UTIL,
        )
        
        if concept_clusters.get("clusters"):
            yield sse(
                "concept_clusters",
                {
                    "n_clusters": len(concept_clusters.get("clusters", [])),
                    "clusters": concept_clusters.get("clusters", []),
                },
            )
    except Exception as e:
        logger.exception("cluster_coding_concepts failed; continuing without clustering")
        yield sse(
            "status",
            {
                "status": "clustering_error",
                "detail": str(e),
            },
        )
        concept_clusters = {"clusters": [], "source_cluster_map": {}}

    if await request.is_disconnected():
        return

    # 5.55) Compute slot satisfaction using LLM-driven helper
    # This determines which missing_slots are truly unsatisfied after gap retrieval
    # All semantic reasoning is done by the LLM, not Python heuristics
    yield sse("status", {"status": "computing_slot_satisfaction"})
    remaining_missing_slots: List[Dict[str, Any]] = missing2
    slot_status: Dict[str, Dict[str, Any]] = {}
    
    try:
        remaining_missing_slots, slot_status = await compute_slot_satisfaction(
            ledger=ledger2,
            clusters=concept_clusters,
            missing_slots=missing2,
            q=q,
            model=CHAT_MODEL_UTIL,
        )
        
        # Emit slot satisfaction status for debugging/inspection
        yield sse(
            "slot_satisfaction",
            {
                "original_missing_count": len(missing2),
                "remaining_missing_count": len(remaining_missing_slots),
                "satisfied_count": len(missing2) - len(remaining_missing_slots),
                "slot_status": slot_status,
            },
        )
        
        logger.debug(
            "compute_slot_satisfaction: %d -> %d missing slots",
            len(missing2),
            len(remaining_missing_slots),
        )
    except Exception as e:
        logger.exception("compute_slot_satisfaction failed; using original missing_slots")
        yield sse(
            "status",
            {
                "status": "slot_satisfaction_error",
                "detail": str(e),
            },
        )
        remaining_missing_slots = missing2
        slot_status = {}

    if await request.is_disconnected():
        return

    # 5.6) Build canonical_keep_map from concept_clusters
    # This filters keep2 to only include canonical codes from each cluster
    canonical_keep_map = build_canonical_keep_map(keep2, concept_clusters)
    
    yield sse(
        "canonical_keep_map",
        {
            "original_keep_map": keep2,
            "canonical_keep_map": canonical_keep_map,
            "n_clusters": len(concept_clusters.get("clusters", [])),
        },
    )

    # Filter ICD rows to only include canonical codes
    icd_keep = set((canonical_keep_map.get("icd10cm") or []))

    if icd_keep:
        icd_rows = results_by_source.get("icd10cm") or []
        filtered_icd_rows = []

        for row in icd_rows:
            code = (
                row.get("code")
                or row.get("id")
                or ""
            )
            code = str(code).upper().strip()
            if code in icd_keep:
                filtered_icd_rows.append(row)

        results_by_source["icd10cm"] = filtered_icd_rows

    # Build the final coding_result from canonical_keep_map (not keep2)
    # This ensures only canonical codes appear in the final result
    coding_result = build_coding_result_from_keep_map(canonical_keep_map)
    
    # Add concept_clusters to coding_result for downstream consumers
    coding_result["concept_clusters"] = concept_clusters.get("clusters", [])
    
    # Add remaining_missing_slots (truly unsatisfied) instead of raw missing_slots
    # This ensures only genuinely missing slots are reported
    coding_result["missing_slots"] = remaining_missing_slots
    
    yield sse("coding_result", coding_result)

    if await request.is_disconnected():
        return

    raw_source_count = len(results_by_source)

    # 6) Heuristic source gating with code sources force-kept
    extra_always_keep: set[str] = set(CODING_SOURCES)

    gated_results_by_source, gating_info = apply_source_gating(
        results_by_source,
        query=q,
        extra_always_keep=extra_always_keep,
        coding_mode=True,
        ctx_k=ctx_k,
    )

    yield sse("gating", gating_info)

    if await request.is_disconnected():
        return

    # 7) Fuse internal contexts
    yield sse("status", {"status": "fusing_context"})
    ROW_ABS_MIN_SCORE = 0.05

    for src, rows in list(gated_results_by_source.items()):
        trimmed = [r for r in rows if float(r.get("score", 0.0) or 0.0) >= ROW_ABS_MIN_SCORE]
        if not trimmed:
            trimmed = rows
        trimmed.sort(key=lambda r: float(r.get("score", 0.0) or 0.0), reverse=True)
        gated_results_by_source[src] = trimmed

    internal_ctx = build_fused_context(
        gated_results_by_source,
        k=ctx_k,
        coding_mode=True,
    )

    # Inject coding_result as a synthetic "document" at the top
    if coding_result:
        coding_summary_text = json.dumps(coding_result, indent=2)

        coding_ctx_row: Dict[str, Any] = {
            "id": "coding_result",
            "source": "coding_result",
            "source_id": None,
            "title": "Final coding result (ICD/LOINC/RxNorm/SNOMED ledger)",
            "text": coding_summary_text,
            "meta": {
                "kind": "coding_result",
            },
            "score": 1.0,
            "method": "coding_result",
        }

        internal_ctx = [coding_ctx_row, *internal_ctx]

    final_ctx = internal_ctx

    if await request.is_disconnected():
        return

    # Build citations constrained to canonical ledger codes only (Requirement 3)
    # This ensures citations only reference canonical codes in the final coding_result
    # Pass source_cluster_map to attach cluster_id to each citation
    citations = build_ledger_only_citations(
        final_ctx,
        canonical_keep_map,
        source_cluster_map=concept_clusters.get("source_cluster_map"),
    )

    # 8) with_llm == False -> just metadata
    if not with_llm:
        yield sse("status", {"status": "done_no_llm"})
        yield sse("citations", {"citations": citations})
        yield sse(
            "end",
            {
                "meta": {
                    "n_sources_raw": raw_source_count,
                    "n_sources": len(gated_results_by_source),
                    "n_ctx_internal": len(internal_ctx),
                    "n_ctx_valyu": 0,
                    "n_ctx_total": len(final_ctx),
                    "ctx_k": ctx_k,
                    "valyu_k": valyu_k,
                    "with_llm": with_llm,
                    "use_ethos": False,
                }
            },
        )
        return

    if not final_ctx:
        yield sse("status", {"status": "done_no_llm"})
        yield sse("citations", {"citations": []})
        yield sse(
            "end",
            {
                "meta": {
                    "n_sources_raw": raw_source_count,
                    "n_sources": len(gated_results_by_source),
                    "n_ctx_internal": 0,
                    "n_ctx_valyu": 0,
                    "n_ctx_total": 0,
                    "ctx_k": ctx_k,
                    "valyu_k": valyu_k,
                    "with_llm": with_llm,
                    "use_ethos": False,
                    "answer_mode": effective_answer_mode,
                }
            },
        )
        return

    # 9) LLM streaming
    yield sse("phase_start", {"source": "fusion", "method": "llm"})
    yield sse("status", {"status": "generating_answer"})

    try:
        for ev in stream_llm_events(
            q,
            final_ctx,
            llm_mode,
            coding_mode=True,
            chat_model=CHAT_MODEL_CODING_CORE,
            answer_mode="coding",
            phase="coding_reasoning",
        ):
            if await request.is_disconnected():
                return
            yield ev
    except Exception as e:
        logger.exception("Error during LLM streaming")
        yield sse(
            "error",
            {"error": "llm_failed", "detail": str(e)},
        )

    yield sse("phase_end", {"source": "fusion", "method": "llm"})
    yield sse("citations", {"citations": citations})
    yield sse(
        "end",
        {
            "meta": {
                "n_sources_raw": raw_source_count,
                "n_sources": len(gated_results_by_source),
                "n_ctx_internal": len(internal_ctx),
                "n_ctx_valyu": 0,
                "n_ctx_total": len(final_ctx),
                "ctx_k": ctx_k,
                "valyu_k": valyu_k,
                "with_llm": with_llm,
                "use_ethos": False,
                "answer_mode": effective_answer_mode,
                "retrieval_mode": "ts_only",
                "n_concept_clusters": len(concept_clusters.get("clusters", [])),
            }
        },
    )


# ---------------------------------------------------------------------------
# /ask_stream — uses ask_stream_event_generator (non-coding mode)
# ---------------------------------------------------------------------------


@router.get("/ask_stream")
async def ask_stream(
    request: Request,
    q: str = Query(..., description="User clinical question"),
    sources: Optional[str] = Query(
        None,
        description=(
            "Comma-separated internal sources. If omitted, all known "
            "guideline-ish sources (ACR/EULAR/NICE/ESMO/KDIGO/WHO/etc.) "
            "are used, discovered dynamically from the MKG."
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

    Uses the explicit ask_stream_event_generator (non-coding mode) with:
      - Default sources = guideline-ish ASK_STREAM_DEFAULT_SOURCES
      - Optional Valyu tail
    """

    # Parse sources list
    if sources:
        raw_sources = [s.strip() for s in sources.split(",") if s.strip()]
        seen = set()
        db_sources: List[str] = []
        for s in raw_sources:
            if s not in seen:
                seen.add(s)
                db_sources.append(s)
    else:
        discovered = await discover_all_guideline_sources(pool)

        merged: List[str] = []
        seen: set[str] = set()

        for s in ASK_STREAM_DEFAULT_SOURCES:
            if s not in seen:
                seen.add(s)
                merged.append(s)

        for s in discovered:
            if s not in seen:
                seen.add(s)
                merged.append(s)

        db_sources = merged

    warning = _send_large_request_warning(q, db_sources, limit)

    async def event_gen() -> AsyncIterator[Dict[str, str]]:
        if warning:
            yield sse("warning", warning)

        async for ev in ask_stream_event_generator(
            request=request,
            q=q,
            db_sources=db_sources,
            limit=limit,
            ctx_k=ctx_k,
            valyu_k=valyu_k,
            with_llm=bool(with_llm),
            llm_mode=llm_mode,
            use_valyu=bool(use_valyu),
            valyu_mode=valyu_mode,
            valyu_raw=bool(valyu_raw),
            valyu_sources=valyu_sources,
            valyu_boost=valyu_boost,
            use_ethos=bool(use_ethos),
            pool=pool,
            answer_mode="guideline",
        ):
            yield ev

    return EventSourceResponse(event_gen(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# /coding_stream — uses coding_stream_event_generator (coding mode)
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
    limit: int = Query(BASE_LIMIT, ge=1, le=64),
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
    pool: Any = Depends(resolve_pg_pool),
) -> EventSourceResponse:
    """
    SSE endpoint for coding/abstraction.

    Uses the explicit coding_stream_event_generator (coding mode) with:
      - Default sources = CODING_DEFAULT_SOURCES
      - Clamp source fan-out to MAX_CODING_SOURCES with a warning
    """
    if sources:
        raw_sources = [s.strip() for s in sources.split(",") if s.strip()]
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

    if original_source_count > MAX_CODING_SOURCES:
        clamped = True

        preferred_order: List[str] = []

        for s in CODING_DEFAULT_SOURCES:
            if s in db_sources and s not in preferred_order:
                preferred_order.append(s)
                if len(preferred_order) >= MAX_CODING_SOURCES:
                    break

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

        async for ev in coding_stream_event_generator(
            request=request,
            q=q,
            db_sources=db_sources,
            limit=limit,
            ctx_k=ctx_k,
            valyu_k=valyu_k,
            with_llm=bool(with_llm),
            llm_mode=llm_mode,
            pool=pool,
        ):
            yield ev

    return EventSourceResponse(event_gen(), media_type="text/event-stream")


VALYU_EVIDENCE_MODEL = CHAT_MODEL_GUIDELINES  # or a separate lightweight model

VALYU_EVIDENCE_SYSTEM_PROMPT = """
You are a clinical evidence summarizer working inside 2ndOpinionMD's Ethos-of-Health (EoH) pipeline.

Your inputs:
- The EoH router plan text (describes question type and modules).
- A small set of full-text research articles from Valyu/PubMed (title + body).

Your job:
- Select the most relevant passages to the router plan and clinical question.
- Produce SHORT, citation-ready excerpts with clear study titles / labels.
- Do NOT invent statistics, effect sizes, or conclusions that are not present.
- You may repeat numeric values that appear in the text (e.g. hazard ratios, %),
  but you must not fabricate new numbers.

Output:
- A single JSON object with this exact schema:

{
  "evidence": [
    {
      "id": "string-short-id",
      "title": "Article title or short label",
      "snippet": "Short excerpt (1–4 sentences) directly from or tightly summarizing the article.",
      "citation": "Free-text citation label, e.g. 'BeSt RA trial (10-year follow-up)' or 'DBS CRP flare study'",
      "source": "valyu_pubmed"  // or similar
    }
  ]
}

Constraints:
- Max 5 evidence items.
- Each snippet should be < 700 characters.
- Focus on mechanisms, flare/diagnosis relationships, and high-yield patterns
  relevant to the question type (A–E) described by the router plan.
"""


async def synthesize_valyu_evidence(
    *,
    client: OpenAI,
    router_plan_text: str,
    valyu_matches: list[dict[str, object]],
    max_articles: int = 3,
    max_chars_per_article: int = 6000,
) -> list[dict[str, object]]:
    """
    Given the router plan text and Valyu matches (with full_text in meta),
    call an LLM once to distill a handful of short evidence snippets.

    Returns a list of docs ready to inject into final_ctx.
    """
    # Build compact article payload for the LLM
    articles_payload: list[dict[str, str]] = []
    for r in valyu_matches[:max_articles]:
        meta = (r.get("meta") or {}) if isinstance(r, dict) else {}
        full_text = (meta.get("full_text") or "") if isinstance(meta, dict) else ""
        snippet = (
            r.get("text")
            or (r.get("abstract") if isinstance(r, dict) else "")
            or (r.get("snippet") if isinstance(r, dict) else "")
            or ""
        )
        title = (r.get("title") or "") if isinstance(r, dict) else ""
        source = (r.get("source") or "valyu_pubmed") if isinstance(r, dict) else "valyu_pubmed"

        text_body = (full_text or snippet or "").strip()
        if not text_body:
            continue

        articles_payload.append(
            {
                "id": str(r.get("id")),
                "title": title[:300],
                "source": source,
                "text": text_body[:max_chars_per_article],
            }
        )

    if not articles_payload:
        logger.warning("Valyu evidence: no full_text/snippet found in valyu_matches")
        return []

    import json

    messages = [
        {
            "role": "system",
            "content": VALYU_EVIDENCE_SYSTEM_PROMPT.strip(),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "router_plan_text": router_plan_text,
                    "articles": articles_payload,
                },
                ensure_ascii=False,
            ),
        },
    ]

    try:
        resp = await _chat_completion_async(
            model=VALYU_EVIDENCE_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
    except Exception:
        logger.exception("Valyu evidence summarizer LLM call failed")
        return []

    evidence_items = data.get("evidence") or []
    docs: list[dict[str, object]] = []

    for ev in evidence_items:
        try:
            ev_id = str(ev.get("id") or "")
            title = (ev.get("title") or "").strip()
            snippet = (ev.get("snippet") or "").strip()
            citation_label = (ev.get("citation") or "").strip()
            source = (ev.get("source") or "valyu_pubmed").strip() or "valyu_pubmed"

            if not snippet:
                continue

            # Each item becomes a RAG doc
            docs.append(
                {
                    "id": f"valyu_evidence:{ev_id or title[:50]}",
                    "source": source,
                    "source_id": citation_label or ev_id or title,
                    "title": title or citation_label or "Valyu evidence snippet",
                    "text": snippet,
                    "score": 1.0,
                    "method": "valyu_evidence",
                }
            )
        except Exception:
            logger.exception("Failed to convert Valyu evidence item: %r", ev)
            continue

    return docs

# ---------------------------------------------------------------------------
# EoH helper: fetch ethos_module_doc policy text from rag_corpus
# ---------------------------------------------------------------------------

async def _fetch_ethos_module_docs_text(
    pool,
    router_plan: Dict[str, Any],
) -> str:
    """
    Look at doc_retrieval_plan for any handles with kind == 'ethos_module_doc'
    and pull their policy text from rag_corpus.

    Handle names are of the form 'source:source_id_suffix', e.g.:
      'eoh_gold_2025:mod_50'

    We use:
      source      = left of ':'
      source_id   = full handle name
    """
    handles: List[Dict[str, str]] = []
    for item in router_plan.get("doc_retrieval_plan", []):
        for h in item.get("handles", []):
            if h.get("kind") == "ethos_module_doc":
                handles.append(h)

    if not handles:
        return ""

    texts: List[str] = []
    async with pool.acquire() as conn:
        for h in handles:
            name = h.get("name")
            if not name:
                continue
            try:
                source, _ = name.split(":", 1)
            except ValueError:
                logger.warning("Invalid ethos_module_doc handle name: %r", name)
                continue

            row = await conn.fetchrow(
                """
                SELECT title, text
                FROM rag_corpus
                WHERE source = $1
                  AND source_id = $2
                """,
                source,
                name,
            )
            if not row:
                logger.warning(
                    "No rag_corpus row found for ethos_module_doc source=%s source_id=%s",
                    source,
                    name,
                )
                continue

            title, text = row["title"], row["text"]
            title_str = title or name
            texts.append(f"### Ethos Module Policy – {title_str}\n\n{text}")

    return "\n\n".join(texts)

# Helper: load EoH patient_state snapshot from DB via asyncpg pool
async def load_eoh_patient_state_from_db(pool: Any, patient_id: str) -> Dict[str, Any]:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT patient_id,
                   updated_at,
                   stability_band,
                   flare_tendency,
                   ra_flare_30d_prob,
                   ra_flare_90d_prob,
                   sle_flare_90d_prob,
                   p_ra,
                   p_sle,
                   p_psa,
                   p_sjogren,
                   p_mctd,
                   p_vasculitis,
                   p_other,
                   raw
            FROM eoh.patient_state
            WHERE patient_id = $1
            """,
            patient_id,
        )
        if not row:
            return {}

        d = dict(row)
        # raw may contain extra fields; you can merge or keep separate
        raw = d.pop("raw", {}) or {}
        d["raw"] = raw
        return d

async def get_timeline_context_for_patient(patient_id: str) -> Optional[TimelineContext]:
    """
    Load all timeline events for a patient and build a TimelineContext.

    We keep this separate so we can reuse it for EoH, case-analog
    retrieval, etc.
    """
    patient_id = (patient_id or "").strip()
    if not patient_id:
        return None

    # 1) Load events (sync via to_thread inside load_patient_timeline)
    events = await load_patient_timeline(patient_id)
    if not events:
        return None

    # 2) Build TimelineContext (diagnostic landscape + context_text, etc.)
    ctx = await timeline_engine.build_timeline_context_from_events(
        events=events,
        patient_id=patient_id,
    )
    return ctx


def build_timeline_router_summary(timeline_ctx: Any, patient_id: str) -> str:
    """
    Build a compact, router-friendly summary of a patient's timeline.
    Keep this short and high-signal so it fits comfortably in the router prompt.
    """
    lines: List[str] = []

    lines.append(f"Patient: {patient_id}")
    lines.append(f"Event_count: {getattr(timeline_ctx, 'event_count', 'unknown')}")
    lines.append(f"Span_days: {getattr(timeline_ctx, 'span_days', 'unknown')}")

    key_signals = getattr(timeline_ctx, "key_signals", None)
    if key_signals:
        lines.append("Key_signals (high-level):")
        # Trim to keep under control
        try:
            snippet = json.dumps(key_signals, ensure_ascii=False, cls=DateTimeJSONEncoder)
            if len(snippet) > 800:
                snippet = snippet[:800] + " ..."
            lines.append(snippet)
        except Exception:
            pass

    diag = getattr(timeline_ctx, "diagnostic_landscape", None)
    if diag:
        try:
            # Prefer normalized dict if available
            if hasattr(diag, "to_normalized_dict") and callable(diag.to_normalized_dict):
                diag_dict = diag.to_normalized_dict()
            elif isinstance(diag, dict):
                diag_dict = diag
            else:
                diag_dict = None

            if diag_dict:
                diag_snippet = json.dumps(diag_dict, ensure_ascii=False, cls=DateTimeJSONEncoder)
                if len(diag_snippet) > 600:
                    diag_snippet = diag_snippet[:600] + " ..."
                lines.append("Diagnostic_landscape (weights, truncated):")
                lines.append(diag_snippet)
        except Exception:
            pass

    return "\n".join(lines)

CASE_ANALOG_SOURCE = "mimic4_note"
# Keep analogs for flare-vs-noise and "other" exploratory questions only
CASE_ANALOG_QUESTION_TYPES = {"B", "OTHER"}
CASE_ANALOG_K = 3

# New: TS/ANN fusion tuning for case analogs
CASE_ANALOG_TS_MULTIPLIER = 3   # how many TS rows to grab per K
CASE_ANALOG_MIN_TS_SCORE = 0.0  # optional floor, can raise later
CASE_ANALOG_MIN_ANN_SCORE = 0.0

# ---------------------------------------------------------------------------
# EoH Router System Prompt Extension
# ---------------------------------------------------------------------------

EOH_ROUTED_ANSWER_SYSTEM_PROMPT = """
You are the Ethos-of-Health (EoH) reasoning model for 2ndOpinionMD.

Your role:
- Interpret patient state using the EoH Gold Standard v2 (2025): stacks, stability bands, drift,
  trajectories, PSI, CBM, suppression logic, and module outputs *in concept only*.
- Ground all clinical statements strictly in the retrieved context (router plan, patient timelines,
  guideline snippets, EoH/Ethos documents, and any diagnostic landscape artifacts).
- Treat the prepended **EoH Router Plan** as the blueprint for your reasoning.

You never query a database. You only see what is in the fused context.

You receive:
- A clinical question.
- A fused context of documents from multiple sources (guidelines, Ethos/EoH internal docs, patient timeline, diagnostic landscape, Valyu research, etc.).

When using context:
- Treat guideline and Ethos/EoH sources as primary normative references.
- Treat patient timeline and diagnostic landscape as the ground truth about this specific patient.
- Treat Valyu research sources (source names beginning with 'valyu/' or method containing 'valyu') as:
  - Secondary research evidence that can support or challenge internal guidelines.
  - Never the sole basis for a clinical recommendation when it conflicts with strong guideline consensus.
- When you rely on Valyu research for a key claim, make that clear in your reasoning (e.g., "external research suggests...").


--------------------------------------------------------------------------------
EOH ROUTER PLAN INSTRUCTIONS
--------------------------------------------------------------------------------
You ALWAYS receive a high-level router plan near the top of context. It includes:
- Question type (A–E or OTHER)
- EoH modules involved (e.g., M1–M3B, M4, M13, M48, M48B, M48C, etc.)
- Document handles retrieved for each module
- Conceptual purpose of each module

When answering:

1. Explicitly tie your reasoning to the router plan.
   Use language such as:
   - "Step 1 (M1–M3B) is designed to…"
   - "M13 would typically generate a prognostic landscape weight vector by integrating…"
   - "In this framework, M4 applies suppression-auditing logic to…"

2. Stay within the router plan scope.
   Do NOT introduce modules or capabilities that are not mentioned in the router plan
   or elsewhere in the fused context.

3. Treat all module outputs as *conceptual*.
   - You cannot see live DB values, PSI scores, tiers, or model coefficients unless they
     appear explicitly in a patient_state JSON or another visible artifact.
   - You may describe what a module is designed to do, and how it *would* use the
     available context, but not what it "actually computed" unless it is explicitly shown.

4. If `patient_state` JSON is provided, integrate it, but treat it as user- or system-supplied
   metadata that may be partial. Never infer hidden fields.

--------------------------------------------------------------------------------
QUESTION TYPE (A–E) INTERPRETATION
--------------------------------------------------------------------------------

The router plan always includes a "question_type" field. You MUST use it to shape your answer:

- Type A (Flare risk / baseline & trajectory)
  Focus on where the patient sits in stability bands / stacks and their near-term
  flare risk and trajectory. Emphasize temporal patterns in the timeline and
  how those patterns conceptually map into higher vs lower risk ranges.

- Type B (Flare vs noise / artefact)  **(HARD CONSTRAINT + TAGGING)**
  Focus on whether a specific episode looks like a true flare vs fibro/symbolic
  pain, lab artefact, infection, or other noise. Explicitly weigh flare features
  vs suppression logic.

  HARD CONSTRAINT:
  - You MUST provide a machine-readable tag line of the form:
      `TypeB_event_tag: flare_likely`
      or `TypeB_event_tag: noise_likely`
      or `TypeB_event_tag: indeterminate`
    This tag MUST appear once, on its own line, in Section 2 or Section 5.

  - Even when you are uncertain, you must still pick ONE of these three tags,
    and then explain the uncertainty in natural language.

- Type C (Explainability / diagnostic landscape)
  Focus on explaining WHY the EoH view (terrain/landscape) leans toward certain
  diagnoses or tiers. Use diagnostic landscape objects and features explicitly.
  You must describe which disease labels have non-zero or non-negligible weights,
  and which labels conceptually dominate (e.g., "RA-like clearly outweighs SLE-like").

  STANDARDIZED SHAPE (Type C):
  - You MUST include a subsection explicitly titled:
      `### Diagnostic Landscape Snapshot (Type C)`
    containing a bullet list or mini-table that:
      * Lists each visible label (e.g., RA-like, SLE-like, PsA-like, other).
      * States its qualitative level using words like "dominant", "secondary",
        "minor", or "background".
      * Optionally quotes numeric values or ranges *only if present* in the context.

- Type D (Plan adjustment)
  Focus on how to adjust care intensity, maintenance therapy, or monitoring over
  the next 3–12+ months, grounded in the timeline and any guideline snippets.
  Describe adjustments using *ranges* of frequency or intensity when those are
  clearly implied (e.g., "closer to the high-frequency monitoring end" vs "at the low end").

- Type E (Meta / calibration / QA)
  Focus on calibration, missed flares vs false positives, and landscape drift.
  Use governance modules (e.g., M19, M41, M48, M48B, M48C) conceptually to
  talk about under- or over-sensitivity and suppression patterns.

  For Type E you should, where possible:
  - Relate at least one concrete flare episode and its visible features to the
    intended behavior of the calibration/suppression stack.
  - If diagnostic landscape history is present, comment qualitatively on how the
    weights appear to have shifted over time (e.g., "RA-like has gradually become
    more prominent while SLE-like has faded").

If question_type is OTHER, still apply EoH concepts where reasonable, but you
may lean more on plain guideline Q&A using the retrieved guideline snippets.
Use the timeline and any diagnostic landscape artifacts if they are present.

--------------------------------------------------------------------------------
GOVERNANCE / QA MODULES (M48, M48B, M48C)
--------------------------------------------------------------------------------

When modules such as M48, M48B, or M48C appear in the router plan, interpret them as:

- M48: global calibration and suppression governance across the whole system.
- M48B: condition-level calibration and flare suppression audit for specific
  diseases/phenotypes (e.g. RA, SLE, IBD).
- M48C: diagnostic landscape stability and drift over time (e.g. shifting weights
  between RA-like, SLE-like, PsA-like, etc.).

In Type E questions (and sometimes Type C), use these modules conceptually to talk
about:
- whether EoH might be over-suppressing or under-detecting flares in this condition,
- whether the diagnostic landscape appears stable vs drifting based on the
  visible history,
- and what kinds of QA questions a board or safety committee should be asking.

You MUST NOT call the landscape or governance vectors "probability vectors".
Refer to them as "diagnostic landscape weight vectors" or "weight maps", and
treat them as conceptual, calibrated weightings rather than literal probabilities.

--------------------------------------------------------------------------------
PATIENT TIMELINE CONTEXT SOURCES (MANDATORY USE WHEN PRESENT)
--------------------------------------------------------------------------------

You may see patient timeline data in two forms:

1. **Demo timeline**
   A context item with `source = "eoh_demo_timeline"` contains a synthetic but canonical
   patient event log for this demo.

2. **Database-backed timeline**
   A context item with `source = "patient_timeline"` (or an SSE summary such as
   `timeline_loaded`, `timeline_signals`, `timeline_flare_features`,
   `timeline_probabilistic_differential`) represents events loaded from
   `ehr.patient_timeline` and summarized for you in text/JSON.

When ANY timeline is present (demo or patient_timeline):

- Treat it as the patient’s event-level history (e.g., flares, labs, visits, journals).
- Parse it into dated events with:
  - date / time (approximate phrases like "early 2019" are fine),
  - event type (e.g., visit, lab, flare, symptom, med change, journal),
  - key details (e.g., "CRP 50 and ESR 60 during knee flare", "labs near normal",
    "feeling stable", "missed methotrexate doses for 2 weeks").

- Explicitly reference these events in your reasoning, for example:
  - "A moderate flare involving knees with very high CRP/ESR in April 2019
     followed by near-normal inflammatory markers and improved symptoms by mid-2019."
  - "A high-severity Crohn’s flare in early 2021 with bloody diarrhea and weight loss
     followed by improved maintenance status later that year."

- Use the timeline, together with the router plan and any guidelines, as the primary
  evidence for describing:
  - stability vs instability,
  - flare trajectories and precursors,
  - conceptual flare risk and disease control,
  - misdiagnosis patterns or hidden comorbidities when those are explicitly described.

MANDATORY TIMELINE USE (WHEN PRESENT)

If you see ANY context items whose `source` is `"patient_timeline"` or `"eoh_demo_timeline"`:

- In **Section 1 (High-Signal Summary)** or **Section 2 (Router-Aligned EoH Reasoning)** you MUST
  explicitly describe at least **2–3 concrete timeline events** in natural language, for example:
  - approximate date or phase (e.g., "early 2019", "around day 165–180"),
  - event type (flare, visit, lab, med change, journal entry),
  - and 1–2 key details (e.g., "CRP 50 / ESR 60 during knee flare", "missed MTX for 2 weeks",
    "bloody diarrhea with weight loss", "near-normal labs with good function").

- When both earlier and more recent events are visible, you should **contrast them** to show trajectory:
  - e.g., "A severe flare in early 2021 with high inflammatory markers, followed by a more stable
    period later with near-normal labs and fewer symptoms."

- You MUST treat these timeline events as the **primary evidence** for:
  - stability vs instability,
  - flare vs noise,
  - near-term vs longer-term trajectory,
  - adherence versus non-adherence patterns,
  whenever such patterns are explicitly visible in the text.

--------------------------------------------------------------------------------
TIMELINE-DERIVED EOH ARTIFACTS & HISTORY
--------------------------------------------------------------------------------

You may see EoH-specific timeline artifacts in context (e.g. as SSE snippets or
embedded JSON):

- `timeline_signals` – key signals extracted from events (flares, lab spikes,
  stability periods, med changes, misdiagnosis patterns, hidden comorbidities, etc.).
- `timeline_flare_features` – structured features describing flare patterns
  (recency, severity, triggers, lab behavior, recovery).
- `timeline_probabilistic_differential` – a conceptual diagnostic landscape weight object
  (e.g., fields such as `ra_like`, `sle_like`, `psa_like`, `sjogren_like`,
  `mixed_ctd_like`, `vasculitis_like`, `other`, or similar).
- `patient_diagnostic_landscape_history` – a history of diagnostic landscape snapshots
  over time for this patient.

When these appear:

- You may *describe* their structure and use them as qualitative evidence
  (e.g., "EoH’s internal landscape currently leans RA-like rather than SLE-like"),
  but you must still obey the numeric rules below.
- If numeric fields are shown explicitly (e.g., 0.8 vs 0.1), you may qualitatively
  describe the relative ordering ("RA-like greater than SLE-like") and, if helpful,
  refer to the visible numbers or ranges. You must NOT invent new numbers.

When a dedicated context document with `source = "patient_timeline_diagnostic_landscape"`
is present, treat it as the canonical representation of the current diagnostic
landscape snapshot for this answer.

When a `patient_diagnostic_landscape_history` document is present:

- Treat it as a time series of diagnostic landscape weight vectors.
- Describe the *direction* of change qualitatively, such as:
  - "RA-like weights have gradually risen relative to SLE-like and PsA-like",
  - "The landscape has moved from mixed to more clearly RA-dominant."
- You must still avoid inventing numeric probabilities or trajectories.

--------------------------------------------------------------------------------
NUMERIC RANGES & STRICT EPISTEMICS (MANDATORY)
--------------------------------------------------------------------------------

1. **Use numeric ranges when possible but NEVER hallucinate them**
   - When the context provides explicit numeric values (e.g., 0.21, 0.34, 0.55)
     or obvious bands, you should prefer summarizing them as ranges or relative levels:
       * "low-to-moderate range around 0.2–0.3 (per the visible fields)".
   - You may aggregate closely related values into a range **only using the values
     you actually see**. Do NOT invent new endpoints.
   - You may also express relative comparisons without numbers:
       * "clearly higher than", "slightly lower than", "in the upper tier of what is shown".

2. **No numeric hallucinations**
   - Do NOT invent probabilities, percentages, risk tiers, PSI values, drift magnitudes,
     or specific thresholds.
   - You may repeat numeric values only if they appear directly in the context
     (e.g., "CRP 50", "ESR 60", "ra_flare_30d_prob 0.32", "p_ra 0.55").
   - For diagnostic landscapes, you may describe *relative* emphasis
     ("more RA-like than SLE-like") only if the underlying text or JSON indicates that.

3. **No invented guideline details**
   - Do NOT invent references such as "Refs 23, 50–58".
   - Do NOT invent URLs, tables, specific doses, or page numbers.
   - Only state therapy or management details if they are clearly present
     in the retrieved guideline excerpts.

4. **No pretending to observe hidden module outputs**
   You must NOT assert:
   - "M13 predicted 40% flare risk",
   - "The system classified the patient as Tier 3",
   - "PSI score is elevated",
   unless those exact values appear in the visible context.

5. **No overreach**
   - If guideline excerpts are high-level, keep your statements high-level.
   - If the diagnostic landscape is coarse or incomplete, say so.

6. **Uncertainty is REQUIRED when context is limited or partial**
   - Always state what evidence you actually have:
     - router plan,
     - patient timeline events,
     - timeline signals/flare features,
     - diagnostic landscape JSON or history (if any),
     - patient_state JSON (if any),
     - guideline snippets,
     - research excerpts or ICU case-analog notes (if any).
   - If you have only the router plan and minimal clinical text, say that your
     reasoning is largely conceptual.
   - If you DO have patient timeline data and guideline excerpts, you MUST NOT claim
     that “no fused rows or module outputs are visible.” Instead:
       - Explain that you are using those visible items as evidence.
       - Emphasize that quantitative EoH metrics (PSI, calibrated risks, etc.)
         remain conceptual and are not directly observed.

7. **Handling numeric module outputs**
   - You may see a `patient_state` JSON blob containing numeric outputs from EoH modules
     (e.g., flare risks, diagnostic landscape weights).
   - You are allowed to repeat these numeric values and explain them, as long as:
       - You do NOT alter them.
       - You do NOT invent new numeric values that are not present.
   - Always attribute them to EoH modules or patient_state, for example:
       - “According to the current patient_state, the RA-like weight is higher than SLE-like.”
       - “The stored flare risk snapshot shows higher near-term risk than long-term risk.”
   - Prefer describing them as ranges or relative levels when appropriate, e.g.,
       - "near the upper part of the non-zero range for this patient."
   - You must NOT create any numeric risk estimates or weights if none are provided
     in patient_state or other visible JSON/text.

8. **No false "no data" claims**
   - You must NOT say that there is "no patient data", "no patient timeline", "no timeline events", "no fused rows", or "no module outputs visible" if you can see ANY of the following in context:
     - a `patient_timeline` or `eoh_demo_timeline` context item,
     - `timeline_signals`, `timeline_flare_features`, or `timeline_probabilistic_differential` snippets,
     - a diagnostic landscape or history document,
     - an `eoh_patient_state` JSON blob.

   - When such artifacts ARE present but feel incomplete, you must instead say things like:
     - "There is some timeline data, but it appears partial or summarized."
     - "There is a stored patient_state snapshot, but the visible fields are limited."

--------------------------------------------------------------------------------
TYPE-SPECIFIC BEHAVIOR (MANDATORY)
--------------------------------------------------------------------------------

- For question_type = "A" (Flare risk / baseline & trajectory):
  - Emphasize:
      * phases of stability vs instability,
      * near-term vs longer-term flare patterns,
      * how the trajectory would conceptually place the patient in low / moderate / higher
        risk bands, without inventing numerical thresholds.
  - Always anchor your discussion to specific timeline events and phases.

- For question_type = "B" (Flare vs noise / artefact):
  - Focus on:
      * timeline-aligned flare features (recency, severity, lab behavior),
      * noise features (infection, fibro, isolated lab blips, measurement artefact),
      * how suppression logic (M4, M48*) is designed to handle ambiguous spikes.
  - You MUST output a single machine tag line:
      `TypeB_event_tag: flare_likely` or `TypeB_event_tag: noise_likely` or `TypeB_event_tag: indeterminate`.
    This tag is required even when uncertainty is high; explain your uncertainty
    in natural language separately.

- For question_type = "C" (Explainability / diagnostic landscape):
  - You MUST inspect any visible diagnostic landscape object or history and describe:
      * which disease labels are present,
      * which labels dominate (e.g., "RA-like > SLE-like > PsA-like"),
      * whether you see ONE snapshot vs MULTIPLE timepoints.
  - You MUST include a subsection titled:
      `### Diagnostic Landscape Snapshot (Type C)`
    that presents a bullet list or simple table summarizing the landscape.
  - If you only see a single snapshot, you MUST NOT claim that the
    landscape is "stable over time" or "drifting"; instead say that
    stability vs drift cannot be directly observed and that your
    comments about stability are conceptual.
  - If multiple timepoints are visible, you may describe the *direction*
    of change, but still avoid numeric extrapolation beyond what you
    see (no invented probabilities or trajectories).

- For question_type = "D" (Plan adjustment):
  - Focus on:
      * how the current timeline and landscape argue for more vs less intensive
        therapy, monitoring, and safety checks,
      * how guideline excerpts constrain or support those adjustments.
  - Use qualitative ranges (e.g., "closer to the high-intensity monitoring end")
    rather than invented numbers.

- For question_type = "E" (Meta / calibration):
  - You must explicitly state whether you see any calibration- or
    suppression-related rows (e.g., from eoh_m48*, patient_state, diagnostic
    landscape history).
  - If none are visible, say so clearly and frame your answer as
    conceptual meta reasoning only.
  - If some numeric values are visible (e.g., flare probabilities,
    stability_band, landscape weights), you may repeat them and comment on whether
    they seem internally coherent, but you MUST NOT invent new numbers.
  - When timeline_flare_features are present, you MUST connect at least
    one concrete flare episode (severity, triggers, recovery) to your
    calibration/suppression reasoning.

--------------------------------------------------------------------------------
STRUCTURED OUTPUT FORMAT (REQUIRED)
--------------------------------------------------------------------------------

Your output MUST follow this structure:

### 1. High-Signal Summary (2–4 sentences)
- Provide a direct qualitative interpretation using EoH concepts and the router plan.
- If a patient timeline is present, clearly mention the key events:
  - recent flares,
  - instability vs stability phases,
  - notable labs or med changes,
  - any obvious misdiagnosis or hidden comorbidity pattern that is explicitly described.

### 2. Router-Aligned EoH Reasoning
- Use bullets aligned to router plan steps, for example:
  - "Step 1 (M1–M3B): would typically assess terrain, stability band, and stack level…"
  - "Step 2 (M4): would apply suppression/auditing to avoid overreacting to noisy spikes…"
  - "Step 4 (M13): is designed to assemble a diagnostic landscape weight vector by integrating…"
- Explicitly describe how each step *would* use:
  - the timeline events,
  - the extracted signals/flare features,
  - any diagnostic landscape object or history,
  - and any guideline excerpts that were retrieved.
- For question_type = "B", include the `TypeB_event_tag: ...` line somewhere in this section.
- For question_type = "C", you may also place the diagnostic landscape snapshot here,
  but you must still include the dedicated subsection below.

### 3. Evidence answer (guidelines, research, case-analogs)
- **Guideline backbone (if present)**
  - Briefly recap which guideline sets appear in context and how they support (or
    constrain) the EoH reasoning (e.g., ACR/EULAR, KDIGO, GOLD, IDSA, ACC/AHA).
  - Refer to them by human-readable labels, not fabricated numbers.

- **Diagnostic Landscape Snapshot (Type C)** (MANDATORY for Type C; optional but allowed for others)
  - A short, structured summary of the diagnostic landscape using the title:
      `### Diagnostic Landscape Snapshot (Type C)`
  - Include:
      * A list or table of labels and their qualitative levels.
      * Any visible numeric values or ranges, quoted exactly when used.

- **Research / trials (Valyu/PubMed, if present)**
  - Summarize how any research snippets refine your conceptual reasoning
    (mechanisms, flare risks, special populations).
  - Use short labels for clarity (e.g., “RA-ILD cohort”, “HF RCT with SGLT2i”).

- **ICU / EHR case-analog notes (MIMIC, if used)**
  - If you use MIMIC/EHR analogs, clearly label them as “ICU case analogs”.
  - Describe only qualitative patterns; never convert them into numeric EoH risks.
  - Emphasize they are supportive illustrations, not replacements for EoH modules
    or guidelines.
  - When a patient_timeline or timeline-derived features are present,
    you must treat them as PRIMARY evidence. ICU case analogs are optional
    supporting examples only and must not dominate your reasoning.

If a category is absent in context, state briefly that there is no retrieved content of that type.

### 4. Safety Context (only if guidelines appear)
- Summarize the guideline themes that are clearly visible in the context:
  - e.g., first-line RA csDMARD principles, pregnancy/ILD considerations, sepsis bundles,
    or COPD step-up therapy — but only if those are explicitly shown.
- Keep statements high-level when the excerpts are high-level; do not extrapolate
  beyond what you actually see.

### 5. Limits & Uncertainty
- Explicitly state:
  - What evidence you DO have (router plan, timeline events, signals, flare features,
    diagnostic landscape snapshot and/or history, patient_state JSON, guideline snippets,
    research excerpts, case-analog notes).
  - What you do NOT have (no direct PSI values unless shown, no calibrated risk curves
    beyond what is visible, no full EHR chart, no real-world validation data).
  - Any important gaps (e.g., incomplete treatment history, no imaging details,
    partial guideline excerpts).
- For Type B, you may reiterate why you chose the specific `TypeB_event_tag`.
- For Type E calibration questions, you must explicitly state:
  - Whether any calibration / suppression tables or views (e.g. eoh_m48*, patient_state,
    diagnostic landscape history) are visible.
  - If they are visible:
      * Mention at least one concrete numeric value or range (as-is from context)
        and how it fits your qualitative assessment (e.g., "RA-like weight
        consistently higher than SLE-like across the visible history").
  - If they are not visible:
      * Say that no direct calibration tables are available and that your
        reasoning is purely conceptual based on module design, timelines, and any
        visible landscapes.

--------------------------------------------------------------------------------
ABSOLUTE PROHIBITIONS
--------------------------------------------------------------------------------
❌ No invented citations  
❌ No invented guideline details  
❌ No invented modules  
❌ No numeric risk estimates or tiers not shown in context  
❌ No fabricated alerts or system outputs  
❌ No pretending you saw DB rows or metrics that are not in the text/JSON you were given  

--------------------------------------------------------------------------------
STYLE & TONE
--------------------------------------------------------------------------------
You are precise, grounded, and clinician-friendly.

All reasoning uses modal language:
- "would likely"
- "EoH would treat this as…"
- "is designed to…"
- "in this framework…"

Begin by acknowledging the router plan in 1–2 sentences, showing that you followed it.
"""

async def _run_evidence_mapping(
    answer_text: str,
    q: str,
    ctx_docs: List[Dict[str, Any]],
    *,
    model: str = CHAT_MODEL_UTIL,
) -> Dict[str, Any]:
    """
    Post-hoc evidence-to-claim mapping.

    Inputs:
    - answer_text: final EoH answer as a single string.
    - q: original question.
    - ctx_docs: list of context docs with minimally:
        { "id": str, "source": str, "title": str, "text": str }

    Returns:
    - JSON dict with a "claims" array, per EVIDENCE_MAPPING_SYSTEM_PROMPT.
    """
    # Compress context to keep payload reasonable
    compact_docs: List[Dict[str, str]] = []
    for d in ctx_docs:
        doc_id = str(d.get("id") or "")
        if not doc_id:
            continue
        compact_docs.append(
            {
                "id": doc_id,
                "source": str(d.get("source") or ""),
                "title": (d.get("title") or "")[:200],
                "snippet": (d.get("text") or "")[:800],
            }
        )

    payload = {
        "question": q,
        "answer": answer_text,
        "context_docs": compact_docs,
    }

    messages = [
        {
            "role": "system",
            "content": EVIDENCE_MAPPING_SYSTEM_PROMPT.strip(),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False),
        },
    ]

    try:
        resp = await _chat_completion_async(
            model=model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        content = resp.choices[0].message.content or "{}"
        data = json.loads(content)
    except Exception as e:
        logger.exception("evidence mapping LLM call failed")
        return {"claims": [], "error": str(e)}

    claims = data.get("claims")
    if not isinstance(claims, list):
        return {"claims": [], "error": "invalid_response_shape"}

    # Light cleanup
    clean_claims: List[Dict[str, Any]] = []
    for idx, c in enumerate(claims, start=1):
        if not isinstance(c, dict):
            continue
        text = (c.get("text") or "").strip()
        if not text:
            continue
        cid = c.get("id") or f"c{idx}"
        cat = c.get("category") or "other"
        ev_ids = c.get("supporting_evidence_ids") or []
        strength = c.get("support_strength") or "moderate"
        clean_claims.append(
            {
                "id": str(cid),
                "text": text,
                "category": str(cat),
                "supporting_evidence_ids": [
                    str(x) for x in ev_ids if isinstance(x, (str, int))
                ],
                "support_strength": str(strength),
            }
        )

    return {"claims": clean_claims}

# Heuristic: does this context already include any Valyu research docs?
def _has_valyu_doc(ctx: List[Dict[str, Any]]) -> bool:
    for d in ctx:
        src = str(d.get("source") or "").lower()
        # Adjust if your Valyu sources use different names
        if src.startswith("valyu") or src in ("valyu_default", "valyu_guideline", "valyu_research"):
            return True
    return False


def _pick_top_valyu_doc(valyu_docs: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    if not valyu_docs:
        return None
    # Prefer highest score if available, else just first
    sorted_docs = sorted(
        valyu_docs,
        key=lambda d: float(d.get("score") or 0.0),
        reverse=True,
    )
    return sorted_docs[0]


def _timeline_summaries_from_patient_state(
    ps: Dict[str, Any],
) -> Optional[TimelineSummaries]:
    """
    Build a TimelineSummaries instance from compact patient_state JSON.

    Expected keys (all optional):
      - timeline_summary
      - meds_and_labs_snapshot
      - valyu_summary
    """
    summary = (ps.get("timeline_summary") or "").strip()
    meds = (ps.get("meds_and_labs_snapshot") or ps.get("meds_andlabs_snapshot") or "").strip()
    valyu = (ps.get("valyu_summary") or "").strip()

    if not summary and not meds and not valyu:
        return None

    return TimelineSummaries(
        timeline_summary=summary,
        meds_and_labs_snapshot=meds,
        valyu_summary=valyu,
    )


# ---------------------------------------------------------------------------
# eoh_stream_event_generator — dedicated EoH event generator with router
# ---------------------------------------------------------------------------


# server/api/rag_stream_routes.py

async def eoh_stream_event_generator(
    *,
    request: Request,
    q: str,
    db_sources: List[str],
    limit: int,
    ctx_k: int,
    valyu_k: int,
    with_llm: bool,
    llm_mode: str,
    use_valyu: bool,
    valyu_mode: str,
    valyu_raw: bool,
    valyu_sources: Optional[str],
    valyu_boost: float,
    pool: Any,
    patient_state: Optional[str] = None,
    debug: bool = False,
    use_timeline: bool = False,
    timeline_patient_id: Optional[str] = None,
    research: int = 0,
    enable_gap: int = 1,
) -> AsyncIterator[Dict[str, str]]:
    """
    Dedicated event generator for /eoh_stream with EoH LLM Router integration.

    High-level phases:

    0) Initial events / warnings
    1) Parse patient_state + timeline flags
    2) EoH router (module/doc-handle plan)
    3) Embed query
    4) Valyu fetch + (optional) evidence synthesis
    5) Extract Q&A query terms
    6) Timeline load (single pass: signals, landscape, router summary)
    7) Guideline/EoH source routing (stream_router.route_sources)
    8) Per-source retrieval (TS + ANN)
    9) Gating, fused internal context
    10) Assemble final_ctx (router, ethos, timeline, Valyu, internal, case analogs, patient_state)
    11) Optional EoH gap retrieval
    12) LLM answer (or metadata-only mode)
    """
    t0 = time.perf_counter()

    VALYU_K_MAX = 4
    requested_valyu_k = valyu_k
    valyu_k = max(0, min(valyu_k, VALYU_K_MAX))

    term_expansions: Dict[str, List[str]] = {}

    # Will hold an ethos_module_doc context item if router requests any:
    ethos_module_docs_ctx_item: Optional[Dict[str, Any]] = None

    # Timeline-related state (single load used for both routing + context)
    timeline_ctx: Optional[TimelineContext] = None
    timeline_summary_for_router: Optional[str] = None
    timeline_diag_doc: Optional[Dict[str, Any]] = None
    timeline_history_doc: Optional[Dict[str, Any]] = None
    timeline_doc: Optional[Dict[str, Any]] = None
    timeline_summaries: Optional[TimelineSummaries] = None

    # Patient state doc (for later context injection)
    eoh_patient_state_doc: Optional[Dict[str, Any]] = None

    # Case analog docs (for later context injection)
    case_analog_docs: List[Dict[str, Any]] = []

    # ---------------------------------------------------------------------------
    # 1) Parse patient_state JSON + timeline flags
    # ---------------------------------------------------------------------------
    patient_state_summary: Optional[Dict[str, Any]] = None
    if patient_state:
        try:
            patient_state_summary = json.loads(patient_state)
        except Exception:
            logger.warning("eoh_stream: failed to parse patient_state JSON", exc_info=True)
            patient_state_summary = None
    
    if patient_state_summary:
        try:
            ps_summaries = _timeline_summaries_from_patient_state(patient_state_summary)
        except Exception:
            logger.exception("eoh_stream: failed to build TimelineSummaries from patient_state")
            ps_summaries = None

        if ps_summaries is not None:
            timeline_summaries = ps_summaries
            if ps_summaries.timeline_summary:
                timeline_summary_for_router = ps_summaries.timeline_summary

    if use_timeline and timeline_patient_id:
        if patient_state_summary is None:
            patient_state_summary = {}
        # Do not overwrite if the caller already supplied explicit flags
        patient_state_summary.setdefault("eoh_has_timeline", True)
        patient_state_summary.setdefault("eoh_timeline_patient_id", timeline_patient_id)

    # ---------------------------------------------------------------------------
    # 0) Initial SSE event + soft warnings (kept as phase 0 in SSE)
    # ---------------------------------------------------------------------------
    yield sse(
        "start",
        {
            "q": q,
            "limit": limit,
            "ctx_k": ctx_k,
            "sources": db_sources,
            "with_llm": with_llm,
            "use_valyu": use_valyu,
            "valyu_k": valyu_k,
            "valyu_k_requested": requested_valyu_k,
            "mode": "eoh",
        },
    )

    warnings: List[str] = []
    # (optional tuning warnings can live here if you want to re-enable them)
    if warnings:
        yield sse("warning", {"messages": warnings})

    if await request.is_disconnected():
        return

    # ---------------------------------------------------------------------------
    # 2) EoH Router Call — create module/doc-handle plan
    #     (uses patient_state_summary, not yet dependent on Valyu/timeline)
    # ---------------------------------------------------------------------------
    yield sse(
        "status",
        {"status": "routing_eoh", "detail": "Routing question to EoH modules via LLM router."},
    )

    router_plan: Dict[str, Any] = {
        "question_type": "OTHER",
        "question_type_explanation": "",
        "module_plan": [],
        "doc_retrieval_plan": [],
    }

    try:
        router_plan = await eoh_llm_router(
            client=_openai_client,
            question=q,
            patient_state_summary=patient_state_summary,
            module_index=MODULE_INDEX,
        )
        logger.info(
            "eoh_stream: router returned question_type=%s, n_modules=%d, n_handles=%d",
            router_plan.get("question_type", "OTHER"),
            sum(len(step.get("modules", [])) for step in router_plan.get("module_plan", [])),
            sum(len(item.get("handles", [])) for item in router_plan.get("doc_retrieval_plan", [])),
        )
    except Exception as e:
        logger.exception("eoh_stream: EoH router call failed, using fallback plan")
        yield sse(
            "status",
            {"status": "routing_eoh_failed", "detail": str(e)},
        )
        router_plan = {
            "question_type": "OTHER",
            "question_type_explanation": "Router call failed; using fallback.",
            "module_plan": [],
            "doc_retrieval_plan": [],
        }

    # Emit the full router plan
    yield sse("eoh_router_plan", router_plan)

    # Emit a compact retrieval summary
    doc_plan_summary = [
        {
            "module": item.get("module"),
            "handles": [h.get("name") for h in item.get("handles", [])],
            "purpose": item.get("purpose", ""),
        }
        for item in router_plan.get("doc_retrieval_plan", [])
    ]

    yield sse(
        "eoh_retrieval_plan",
        {
            "question_type": router_plan.get("question_type"),
            "doc_retrieval_plan": doc_plan_summary,
        },
    )

    n_effective_modules = len(doc_plan_summary)
    n_effective_handles = sum(len(item.get("handles", [])) for item in doc_plan_summary)
    yield sse(
        "status",
        {
            "status": "post_routing_sources",
            "n_effective_modules": n_effective_modules,
            "n_effective_handles": n_effective_handles,
            "detail": f"Router narrowed to {n_effective_modules} modules with {n_effective_handles} doc handles.",
        },
    )

    if await request.is_disconnected():
        return

    # ---------------------------------------------------------------------------
    # 2b) Build router plan context item (to prepend to context later)
    # ---------------------------------------------------------------------------
    question_type = router_plan.get("question_type", "OTHER")
    qt_expl = router_plan.get("question_type_explanation", "")

    router_plan_text_lines = [
        f"EoH question type: {question_type}",
        f"Explanation: {qt_expl}",
        "",
        "Module plan:",
    ]
    for step in router_plan.get("module_plan", []):
        step_num = step.get("step")
        goal = step.get("goal", "")
        modules = ", ".join(step.get("modules", []))
        why = step.get("why", "")
        router_plan_text_lines.append(
            f"- Step {step_num}: {goal} | modules: [{modules}] | why: {why}"
        )

    router_plan_text_lines.append("")
    router_plan_text_lines.append("Doc retrieval plan:")
    for item in router_plan.get("doc_retrieval_plan", []):
        module_id = item.get("module", "")
        handles = ", ".join(
            f"{h.get('kind')}:{h.get('name')}" for h in item.get("handles", [])
        )
        purpose = item.get("purpose", "")
        router_plan_text_lines.append(
            f"- Module {module_id}: {handles} | purpose: {purpose}"
        )

    router_plan_text = "\n".join(router_plan_text_lines)

    router_ctx_item: Dict[str, Any] = {
        "source": "eoh_router",
        "source_id": f"eoh_plan:{question_type}",
        "id": f"eoh_router_plan_{question_type}",
        "title": "EoH Router plan (modules + doc handles)",
        "text": router_plan_text,
        "score": 1.0,
        "method": "eoh_router",
    }

    # ---------------------------------------------------------------------------
    # 2c) Fetch Ethos module policy docs requested by router (ethos_module_doc)
    # ---------------------------------------------------------------------------
    ethos_module_docs_text = await _fetch_ethos_module_docs_text(pool, router_plan)

    if ethos_module_docs_text:
        ethos_module_docs_ctx_item = {
            "id": "ethos_module_docs:eoh_gold_2025",
            "source": "ethos_module_doc",
            "source_id": "eoh_gold_2025",
            "title": "Ethos module governance / policy text (EoH Gold 2025)",
            "text": ethos_module_docs_text,
            "score": 1.0,
            "method": "ethos_module_doc",
        }

        ethos_handles: List[str] = []
        for item in router_plan.get("doc_retrieval_plan", []):
            for h in item.get("handles", []):
                if h.get("kind") == "ethos_module_doc":
                    name = h.get("name")
                    if name:
                        ethos_handles.append(name)

        yield sse(
            "ethos_module_docs",
            {
                "handles": ethos_handles,
                "count": len(ethos_handles),
                "note": "Loaded ethos_module_doc policy text from rag_corpus.",
            },
        )

    # ---------------------------------------------------------------------------
    # 3) Embed query
    # ---------------------------------------------------------------------------
    yield sse("status", {"status": "embedding_query"})
    try:
        q_emb = await embed_query(q)
        q_vec_literal = embedding_to_vector_literal(q_emb)
    except Exception as e:
        logger.exception("Error embedding query")
        yield sse(
            "error",
            {"error": "embedding_failed", "detail": str(e)},
        )
        return

    if await request.is_disconnected():
        return
    

    # ---------------------------------------------------------------------------
    # 4) Timeline load (single pass) – signals + diagnostic landscape + summary
    #     Used both for context and to influence guideline routing / Valyu.
    # ---------------------------------------------------------------------------
    if use_timeline and timeline_patient_id:
        yield sse(
            "status",
            {"status": "loading_timeline", "patient_id": timeline_patient_id},
        )

        try:
            events = await load_patient_timeline(timeline_patient_id)

            yield sse(
                "timeline_events_loaded",
                {
                    "patient_id": timeline_patient_id,
                    "event_count": len(events),
                },
            )

            timeline_ctx_local = await timeline_engine.build_timeline_context_from_events(
                events, timeline_patient_id
            )

            yield sse(
                "timeline_loaded",
                {
                    "patient_id": timeline_patient_id,
                    "event_count": timeline_ctx_local.event_count,
                    "span_days": timeline_ctx_local.span_days,
                },
            )

            # Signals
            yield sse(
                "timeline_signals_summary",
                {
                    "patient_id": timeline_patient_id,
                    "n_signals": len(timeline_ctx_local.key_signals or []),
                    "sample_signals": (timeline_ctx_local.key_signals or [])[:5],
                },
            )

            if debug:
                yield sse(
                    "timeline_signals",
                    {
                        "patient_id": timeline_patient_id,
                        "key_signals": timeline_ctx_local.key_signals,
                    },
                )

            if timeline_ctx_local.flare_features:
                yield sse(
                    "timeline_flare_features",
                    {
                        "patient_id": timeline_patient_id,
                        "flare_features": timeline_ctx_local.flare_features,
                    },
                )

            # Diagnostic landscape + history
            if timeline_ctx_local.diagnostic_landscape:
                try:
                    dl = timeline_ctx_local.diagnostic_landscape

                    if hasattr(dl, "to_payload") and callable(dl.to_payload):
                        diag_payload = dl.to_payload()
                    elif hasattr(dl, "to_normalized_dict") and callable(dl.to_normalized_dict):
                        diag_payload = {"weights": dl.to_normalized_dict()}
                    elif isinstance(dl, dict):
                        diag_payload = dl
                    else:
                        diag_payload = None

                    if diag_payload is not None:
                        yield sse(
                            "timeline_probabilistic_differential",
                            {
                                "patient_id": timeline_patient_id,
                                "diagnostic_landscape": diag_payload,
                            },
                        )

                        timeline_diag_doc = {
                            "id": f"patient_timeline_diagnostic_landscape:{timeline_patient_id}",
                            "source": "patient_timeline_diagnostic_landscape",
                            "source_id": f"patient_timeline_diagnostic_landscape:{timeline_patient_id}",
                            "title": f"Diagnostic landscape – {timeline_patient_id}",
                            "text": json.dumps(diag_payload, ensure_ascii=False, cls=DateTimeJSONEncoder),
                            "score": 1.0,
                            "method": "timeline_diagnostic_landscape",
                        }

                        history = timeline_engine.compute_landscape_history_from_events(
                            events, timeline_patient_id
                        )
                        if history:
                            timeline_history_doc = {
                                "id": f"patient_diagnostic_landscape_history:{timeline_patient_id}",
                                "source": "patient_diagnostic_landscape_history",
                                "source_id": f"patient_diagnostic_landscape_history:{timeline_patient_id}",
                                "title": f"Diagnostic landscape history – {timeline_patient_id}",
                                "text": json.dumps(history, ensure_ascii=False, cls=DateTimeJSONEncoder),
                                "score": 1.0,
                                "method": "timeline_diagnostic_landscape_history",
                            }

                            yield sse(
                                "timeline_diagnostic_landscape_history",
                                {
                                    "patient_id": timeline_patient_id,
                                    "history_length": len(history),
                                },
                            )

                except Exception:
                    logger.exception(
                        "Failed to serialize diagnostic_landscape for %s",
                        timeline_patient_id,
                    )

            # -------------------------------------------------------------------
            # 4a) Timeline summarizer LLM – compress raw context for all downstream LLMs
            #      BUT if detective already gave us a canonical summary in patient_state,
            #      reuse it and DO NOT re-call the LLM.
            # -------------------------------------------------------------------
            try:
                # If no precomputed summary, call the summarizer once here
                if timeline_summaries is None:
                    timeline_summaries = await summarize_timeline_for_eoh(
                        client=_openai_client,
                        question=q,
                        timeline_text=timeline_ctx_local.context_text,
                        pool=pool,
                        patient_id=timeline_patient_id,
                    )

                if timeline_summaries and timeline_summaries.timeline_summary:
                    logger.info(
                        "EoH: using timeline_summary (len=%d) instead of raw timeline (len=%d)",
                        len(timeline_summaries.timeline_summary),
                        len(timeline_ctx_local.context_text or ""),
                    )
                    # compress raw timeline for downstream LLMs
                    timeline_ctx_local.context_text = timeline_summaries.timeline_summary

                # Router summary: canonical summary or fallback
                timeline_summary_for_router = (
                    (timeline_summaries.timeline_summary if timeline_summaries else None)
                    or build_timeline_router_summary(timeline_ctx_local, timeline_patient_id)
                )

                if timeline_summary_for_router:
                    yield sse(
                        "timeline_router_summary",
                        {
                            "patient_id": timeline_patient_id,
                            "summary": timeline_summary_for_router[:1200],
                        },
                    )

                # Emit meds/labs snapshot for debugging / UI if present
                if timeline_summaries and timeline_summaries.meds_and_labs_snapshot:
                    yield sse(
                        "timeline_meds_labs_snapshot",
                        {
                            "patient_id": timeline_patient_id,
                            "snapshot": timeline_summaries.meds_and_labs_snapshot[:1600],
                        },
                    )

            except Exception:
                logger.exception("EoH: timeline summarizer failed; using raw timeline context.")
                # Fall back to old router summary helper
                try:
                    timeline_summary_for_router = build_timeline_router_summary(
                        timeline_ctx_local,
                        timeline_patient_id,
                    )
                    if timeline_summary_for_router:
                        yield sse(
                            "timeline_router_summary",
                            {
                                "patient_id": timeline_patient_id,
                                "summary": timeline_summary_for_router[:1200],
                            },
                        )
                except Exception:
                    logger.exception(
                        "Failed to build timeline summary for router for %s",
                        timeline_patient_id,
                    )
                    timeline_summary_for_router = None

            # -------------------------------------------------------------------
            # 4b) Timeline context doc – now uses compressed context_text
            # -------------------------------------------------------------------
            timeline_doc = {
                "id": f"patient_timeline:{timeline_patient_id}",
                "source": "patient_timeline",
                "source_id": f"patient_timeline:{timeline_patient_id}",
                "title": f"Patient Timeline – {timeline_patient_id}",
                "text": timeline_ctx_local.context_text,
                "meds_and_labs": timeline_summaries.meds_and_labs_snapshot,
                "score": 1.0,
                "method": "timeline",
            }

            yield sse(
                "patient_timeline_ctx",
                {
                    "source": "patient_timeline",
                    "patient_id": timeline_patient_id,
                    "event_count": timeline_ctx_local.event_count,
                },
            )

        except Exception as e:
            logger.exception("Failed to load patient timeline for %s", timeline_patient_id)
            yield sse(
                "status",
                {"status": "timeline_load_failed", "detail": str(e)},
            )

    if await request.is_disconnected():
        return

    # ---------------------------------------------------------------------------
    # 5) Valyu fetch (optional for EoH)
    # ---------------------------------------------------------------------------
    effective_use_valyu = bool(use_valyu or research)
    valyu_matches: List[Dict[str, Any]] = []

    # Build an augmented query for Valyu using *compact* valyu_summary if available.
    # Fallback to meds/labs snapshot, then to plain question.
    valyu_query = q.strip()
    valyu_signals = ""

    if timeline_summaries:
        if timeline_summaries.valyu_summary:
            valyu_signals = timeline_summaries.valyu_summary
        elif timeline_summaries.meds_and_labs_snapshot:
            valyu_signals = timeline_summaries.meds_and_labs_snapshot

    if valyu_signals:
        # Hard cap length so we don't trip Valyu query limits
        MAX_VALYU_SIGNALS_CHARS = 1200
        valyu_signals = valyu_signals[:MAX_VALYU_SIGNALS_CHARS]

        valyu_query = (
            f"{q.strip()}\n\n"
            "PATIENT_VALYU_SIGNAL_SUMMARY (meds/labs/diagnoses, compressed):\n"
            f"{valyu_signals}"
        )

    if effective_use_valyu and valyu_k > 0:
        yield sse("status", {"status": "valyu_fetch"})
        try:
            t0 = time.perf_counter()
            logger.info("Valyu: calling fetch_valyu_results(q=%r, mode=%r, limit=%r, sources=%r)",
                        valyu_query[:200], valyu_mode, valyu_k, valyu_sources)

            valyu_by_source = await fetch_valyu_results(
                q=valyu_query,
                mode=valyu_mode,
                limit=valyu_k,
                raw=valyu_raw,
                sources=valyu_sources,
                boost=valyu_boost,
            )

            elapsed_ms = int((time.perf_counter() - t0) * 1000)
            logger.info("Valyu: fetch returned sources=%s in %d ms",
                        list((valyu_by_source or {}).keys()), elapsed_ms)

            yield sse("timing", {"phase": "valyu_fetch", "elapsed_ms": elapsed_ms})

        except Exception as e:
            logger.exception("Valyu fetch failed")
            yield sse(
                "status",
                {"status": "valyu_error", "detail": str(e)},
            )
            valyu_by_source = {}

        flat_valyu: List[Dict[str, Any]] = []
        for v_src, rows in (valyu_by_source or {}).items():
            flat_valyu.extend(rows)

        if flat_valyu:
            valyu_matches = flat_valyu[:valyu_k]
            yield sse(
                "matches",
                {
                    "phase": "valyu",
                    "source": "valyu",
                    "matches": [
                        {
                            "id": r.get("id"),
                            "source": r.get("source"),
                            "title": r.get("title", ""),
                            "score": r.get("score", 0.0),
                            "method": r.get("method", "valyu"),
                        }
                        for r in valyu_matches
                    ],
                },
            )

    if await request.is_disconnected():
        return

    # ---------------------------------------------------------------------------
    # 5b) Optional Valyu evidence synthesis aligned to router plan
    # ---------------------------------------------------------------------------
    valyu_evidence_docs: List[Dict[str, Any]] = []

    if (
        effective_use_valyu
        and valyu_matches
        and valyu_raw
        and research
    ):
        try:
            question_type = router_plan.get("question_type", "OTHER")
            qt_expl = router_plan.get("question_type_explanation", "")

            router_plan_text_lines = [
                f"EoH question type: {question_type}",
                f"Explanation: {qt_expl}",
                "",
                "Module plan:",
            ]
            for step in router_plan.get("module_plan", []):
                step_num = step.get("step")
                goal = step.get("goal", "")
                modules = ", ".join(step.get("modules", []))
                why = step.get("why", "")
                router_plan_text_lines.append(
                    f"- Step {step_num}: {goal} | modules: [{modules}] | why: {why}"
                )

            router_plan_text_lines.append("")
            router_plan_text_lines.append("Doc retrieval plan:")
            for item in router_plan.get("doc_retrieval_plan", []):
                module_id = item.get("module", "")
                handles = ", ".join(
                    f"{h.get('kind')}:{h.get('name')}" for h in item.get("handles", [])
                )
                purpose = item.get("purpose", "")
                router_plan_text_lines.append(
                    f"- Module {module_id}: {handles} | purpose: {purpose}"
                )

            router_plan_text_for_valyu = "\n".join(router_plan_text_lines)

            valyu_evidence_docs = await synthesize_valyu_evidence(
                client=_openai_client,
                router_plan_text=router_plan_text_for_valyu,
                valyu_matches=valyu_matches,
            )

            if valyu_evidence_docs:
                yield sse(
                    "valyu_evidence",
                    {
                        "count": len(valyu_evidence_docs),
                        "mode": valyu_mode,
                        "note": "Derived evidence snippets from Valyu full-text articles.",
                    },
                )
        except Exception as e:
            logger.exception("Valyu evidence synthesis failed")
            yield sse(
                "status",
                {"status": "valyu_evidence_error", "detail": str(e)},
            )

    # ---------------------------------------------------------------------------
    # 5c) Cheap fallback for Valyu snippets (if no synthesis)
    # ---------------------------------------------------------------------------
    if not valyu_evidence_docs and valyu_matches:
        fallback_docs: List[Dict[str, Any]] = []
        for r in valyu_matches:
            text = (r.get("text") or "") or ((r.get("meta") or {}).get("snippet") or "")
            if not text:
                continue
            fallback_docs.append(
                {
                    "id": f"valyu_raw:{r.get('id')}",
                    "source": r.get("source", "valyu_pubmed"),
                    "source_id": r.get("id"),
                    "title": (r.get("title") or "Valyu article").strip(),
                    "text": text,
                    "score": float(r.get("score") or 0.0),
                    "method": "valyu_raw",
                }
            )

        if fallback_docs:
            valyu_evidence_docs = fallback_docs
            yield sse(
                "valyu_evidence",
                {
                    "count": len(valyu_evidence_docs),
                    "mode": valyu_mode,
                    "note": "Using raw Valyu snippets as fallback evidence.",
                },
            )

    # ---------------------------------------------------------------------------
    # 6) Extract query terms (optionally using Valyu snippets)
    # ---------------------------------------------------------------------------
    qna_terms: Dict[str, Any] = {"terms": [], "expansions": {}, "all_terms": []}
    all_terms: List[str] = []

    valyu_snippets_for_terms = ""
    if valyu_matches:
        bits: List[str] = []
        for r in valyu_matches[:3]:
            title = (r.get("title") or "").strip()
            snippet = (r.get("text") or "").strip()
            if title:
                bits.append(f"Title: {title}")
            if snippet:
                bits.append(f"Snippet: {snippet[:400]}")
        valyu_snippets_for_terms = "\n\n".join(bits)

    yield sse("status", {"status": "extracting_query_terms"})
    try:
        qna_terms = await extract_qna_terms(
            q,
            extra_context=valyu_snippets_for_terms or None,
        )
        all_terms = qna_terms.get("all_terms", []) or []
        term_expansions = qna_terms.get("expansions") or {}
        yield sse("query_terms", qna_terms)
    except Exception as e:
        logger.exception("query term extraction crashed; continuing with raw query")
        yield sse(
            "query_terms",
            {
                "terms": [],
                "expansions": term_expansions,
                "all_terms": [],
                "error": "query_term_extraction_failed",
                "detail": str(e),
            },
        )
        all_terms = []

    if await request.is_disconnected():
        return


    # ---------------------------------------------------------------------------
    # 7) Guideline/EoH source routing – use Valyu + timeline summary to bias
    # ---------------------------------------------------------------------------
    router_plan_sources: CodingRouterPlan | None = None
    effective_sources: List[str] = list(db_sources)

    yield sse("status", {"status": "routing_sources"})

    try:
        router_plan_sources = await route_sources(
            q=q,
            code_terms=[],
            candidate_sources=db_sources,
            valyu_context=(valyu_matches if valyu_matches else None),
            timeline_summary=timeline_summary_for_router,
        )
    except Exception as e:
        logger.exception("route_sources failed; using all db_sources")
        router_plan_sources = None

    if router_plan_sources and router_plan_sources.selected_sources:
        effective_sources = sorted(router_plan_sources.selected_sources)
    else:
        effective_sources = list(db_sources)

    if router_plan_sources is not None:
        yield sse(
            "router",
            {
                "task_type": router_plan_sources.task_type,
                "selected_sources": effective_sources,
                "reasoning": router_plan_sources.reasoning,
            },
        )

    if await request.is_disconnected():
        return

    yield sse(
        "event_router_summary",
        {
            "mode": "eoh_stream",
            "using_router": router_plan_sources is not None,
            "effective_sources": effective_sources,
            "eoh_question_type": question_type,
        },
    )

    # ---------------------------------------------------------------------------
    # 8) Retrieve per source (TS + ANN)
    # ---------------------------------------------------------------------------
    yield sse("status", {"status": "retrieving_candidates"})
    results_by_source: Dict[str, List[Dict[str, Any]]] = {}

    for src in effective_sources:
        per_source_limit = limit

        ts_rows: List[Dict[str, Any]] = []
        ann_rows: List[Dict[str, Any]] = []

        # TS phase
        yield sse("phase_start", {"source": src, "method": "ts"})
        try:
            if all_terms:
                ts_rows = await search_source_ts_for_terms(
                    pool=pool,
                    source=src,
                    terms=all_terms,
                    limit=per_source_limit,
                )
            else:
                ts_rows = await search_source_ts(
                    pool=pool,
                    source=src,
                    q=q,
                    limit=per_source_limit,
                )
        except Exception as e:
            logger.exception("TS search failed for source=%s", src)
            yield sse(
                "status",
                {"status": "ts_error", "source": src, "detail": str(e)},
            )
            ts_rows = []

        yield sse("phase_end", {"source": src, "method": "ts"})

        if ts_rows:
            yield sse(
                "matches",
                {
                    "phase": "ts",
                    "source": src,
                    "matches": [
                        {
                            "id": r["id"],
                            "source": r["source"],
                            "source_id": r.get("source_id") or "",
                            "title": r.get("title", ""),
                            "score": r.get("score", 0.0),
                            "method": r.get("method", "ts"),
                        }
                        for r in ts_rows
                    ],
                },
            )

        # ANN phase
        yield sse("phase_start", {"source": src, "method": "ann"})
        try:
            ann_rows = await search_source_ann(
                pool=pool,
                source=src,
                q_vec_literal=q_vec_literal,
                limit=per_source_limit,
            )
        except Exception as e:
            logger.exception("ANN search failed for source=%s", src)
            yield sse(
                "status",
                {"status": "ann_error", "source": src, "detail": str(e)},
            )
            ann_rows = []

        yield sse("phase_end", {"source": src, "method": "ann"})

        if ann_rows:
            yield sse(
                "matches",
                {
                    "phase": "ann",
                    "source": src,
                    "matches": [
                        {
                            "id": r["id"],
                            "source": r["source"],
                            "source_id": r.get("source_id") or "",
                            "title": r.get("title", ""),
                            "score": r.get("score", 0.0),
                            "method": r.get("method", "ann"),
                        }
                        for r in ann_rows
                    ],
                },
            )

        combined = dedupe_matches(ts_rows + ann_rows)
        if combined:
            results_by_source[src] = combined

    if await request.is_disconnected():
        return

    raw_source_count = len(results_by_source)

    # ---------------------------------------------------------------------------
    # 9) Gating (source-level pruning) + fused internal context
    # ---------------------------------------------------------------------------
    yield sse("status", {"status": "gating_sources"})
    gated_results_by_source, gating_info = apply_source_gating(
        results_by_source,
        query=q,
        coding_mode=False,
        ctx_k=ctx_k,
    )

    yield sse("gating", gating_info)

    if await request.is_disconnected():
        return

    yield sse("status", {"status": "fusing_context"})
    ROW_ABS_MIN_SCORE = 0.05

    for src, rows in list(gated_results_by_source.items()):
        trimmed = [r for r in rows if float(r.get("score", 0.0) or 0.0) >= ROW_ABS_MIN_SCORE]
        if not trimmed:
            trimmed = rows
        trimmed.sort(key=lambda r: float(r.get("score", 0.0) or 0.0), reverse=True)
        gated_results_by_source[src] = trimmed

    internal_ctx = build_fused_context(
        gated_results_by_source,
        k=ctx_k,
        coding_mode=False,
    )

    # ---------------------------------------------------------------------------
    # 10) Case-analog retrieval from MIMIC-4 notes (ANN-only)
    # ---------------------------------------------------------------------------
    use_case_analogs = (
        question_type in CASE_ANALOG_QUESTION_TYPES
        and research
    )

    if use_case_analogs:
        yield sse(
            "status",
            {
                "status": "retrieving_case_analogs",
                "source": CASE_ANALOG_SOURCE,
            },
        )

        try:
            ann_rows: List[Dict[str, Any]] = []
            try:
                ann_rows = await search_source_ann(
                    pool=pool,
                    source=CASE_ANALOG_SOURCE,
                    q_vec_literal=q_vec_literal,
                    limit=CASE_ANALOG_K,
                )
            except Exception as e:
                logger.exception("case analog ANN search failed for %s", CASE_ANALOG_SOURCE)
                ann_rows = []

            if ann_rows:
                yield sse(
                    "case_analogs",
                    {
                        "source": CASE_ANALOG_SOURCE,
                        "matches": [
                            {
                                "id": r["id"],
                                "source": r["source"],
                                "source_id": r.get("source_id") or "",
                                "title": (r.get("title") or "") or "ICU case analog from MIMIC-4 note",
                                "score": float(r.get("score") or 0.0),
                                "method": "case_analog",
                            }
                            for r in ann_rows[:CASE_ANALOG_K]
                        ],
                    },
                )

                for r in ann_rows[:CASE_ANALOG_K]:
                    ann_score = float(r.get("score") or 0.0)
                    capped_score = min(ann_score, 0.30)  # keep them below core evidence

                    case_analog_docs.append(
                        {
                            "id": r["id"],
                            "source": r.get("source", CASE_ANALOG_SOURCE),
                            "source_id": r.get("source_id"),
                            "title": (r.get("title") or "").strip()
                            or "ICU case analog from MIMIC-4 note",
                            "text": r.get("text", ""),
                            "score": capped_score,
                            "method": "case_analog",
                        }
                    )

        except Exception as e:
            logger.exception("case analog retrieval failed for %s", CASE_ANALOG_SOURCE)
            yield sse(
                "status",
                {"status": "case_analog_error", "detail": str(e)},
            )

    # ---------------------------------------------------------------------------
    # 11) EoH patient_state – inject numeric module outputs (if available)
    # ---------------------------------------------------------------------------
    # Priority:
    #  1) explicit patient_state JSON param
    #  2) snapshot from eoh.patient_state in DB
    if patient_state_summary:
        eoh_patient_state_doc = {
            "id": f"eoh_patient_state_param:{timeline_patient_id or 'unknown'}",
            "source": "eoh_patient_state",
            "source_id": f"eoh_patient_state_param:{timeline_patient_id or 'unknown'}",
            "title": "EoH patient_state (from request parameter)",
            "text": json.dumps(patient_state_summary, ensure_ascii=False),
            "score": 1.0,
            "method": "eoh_patient_state",
        }
        yield sse(
            "eoh_patient_state",
            {
                "source": "param",
                "patient_id": timeline_patient_id,
                "fields": list(patient_state_summary.keys()),
            },
        )

    elif timeline_patient_id:
        try:
            db_state = await load_eoh_patient_state_from_db(pool, timeline_patient_id)
        except Exception:
            logger.exception("Failed to load eoh.patient_state for %s", timeline_patient_id)
            db_state = {}

        if db_state:
            eoh_patient_state_doc = {
                "id": f"eoh_patient_state:{timeline_patient_id}",
                "source": "eoh_patient_state",
                "source_id": f"eoh_patient_state:{timeline_patient_id}",
                "title": f"EoH patient_state – {timeline_patient_id}",
                "text": json.dumps(db_state, ensure_ascii=False),
                "score": 1.0,
                "method": "eoh_patient_state",
            }
            yield sse(
                "eoh_patient_state",
                {
                    "source": "db",
                    "patient_id": timeline_patient_id,
                    "fields": [k for k in db_state.keys() if k not in ("raw",)],
                },
            )

    # ---------------------------------------------------------------------------
    # 12) Assemble final_ctx in a coherent order
    # ---------------------------------------------------------------------------
    final_ctx: List[Dict[str, Any]] = []

    # 1) EoH router plan always present
    final_ctx.append(router_ctx_item)

    # 2) Ethos module governance/policy if requested
    if ethos_module_docs_ctx_item is not None:
        final_ctx.append(ethos_module_docs_ctx_item)

    # 3) Patient state snapshot at the very front (if present)
    if eoh_patient_state_doc is not None:
        final_ctx.insert(0, eoh_patient_state_doc)

    # 4) Valyu evidence (if any)
    if valyu_evidence_docs:
        final_ctx.extend(valyu_evidence_docs)

    # 5) Fused internal guideline/EoH context
    final_ctx.extend(internal_ctx)

    # 6) Demo timeline (query param) – highest precedence if present
    params = request.query_params
    demo_timeline = params.get("eoh_demo_timeline")
    demo_patient_id = params.get("eoh_demo_patient_id")

    if demo_timeline:
        patient_label = demo_patient_id or "demo"

        demo_timeline_doc = {
            "id": f"eoh_demo_timeline:{patient_label}",
            "source": "eoh_demo_timeline",
            "source_id": f"eoh_demo_timeline:{patient_label}",
            "title": f"EoH demo timeline – {patient_label}",
            "text": demo_timeline,
            "score": 1.0,
            "method": "timeline",
        }

        final_ctx.insert(0, demo_timeline_doc)

        yield sse(
            "patient_timeline_ctx",
            {
                "source": "eoh_demo_timeline",
                "patient_id": demo_patient_id,
            },
        )

    # 7) Database-backed timeline docs (history, landscape, full timeline)
    #    Injected near the very top, but after any explicit demo_timeline.
    if timeline_doc is not None:
        final_ctx.insert(0, timeline_doc)

    if timeline_diag_doc is not None:
        final_ctx.insert(0, timeline_diag_doc)

    if timeline_history_doc is not None:
        final_ctx.insert(0, timeline_history_doc)

    # 8) Case analog docs at the tail to avoid drowning core guideline/timeline
    if case_analog_docs:
        final_ctx.extend(case_analog_docs)

    # Valyu context accounting
    valyu_ctx_count = 0
    if use_valyu and valyu_k > 0 and valyu_matches:
        valyu_ctx_count = len(valyu_matches[:valyu_k])

    # Emit fused context matches for debugging / UI
    if final_ctx:
        yield sse(
            "matches",
            {
                "phase": "fused",
                "source": "fused",
                "matches": [
                    {
                        "id": r["id"],
                        "source": r["source"],
                        "source_id": r.get("source_id"),
                        "title": r.get("title", ""),
                        "score": r.get("score", 0.0),
                        "method": r.get("method", None),
                    }
                    for r in final_ctx
                ],
            },
        )

    # Debug: emit full context text
    if debug and final_ctx:
        yield sse(
            "context_fused",
            {
                "items": [
                    {
                        "id": r["id"],
                        "source": r["source"],
                        "source_id": r.get("source_id"),
                        "title": r.get("title", "")[:200],
                        "text": r.get("text", "")[:1000],
                        "score": r.get("score", 0.0),
                        "method": r.get("method", None),
                    }
                    for r in final_ctx
                ]
            },
        )

    if await request.is_disconnected():
        return

    # ---------------------------------------------------------------------------
    # 13) EoH gap retrieval LLM pass — refine context before final answer
    # ---------------------------------------------------------------------------
    if enable_gap and final_ctx:
        extra_gap_docs: List[Dict[str, Any]] = []
        gap_plan: Dict[str, Any] = {}
        t0 = time.perf_counter()

        try:
            gap_payload = build_eoh_gap_retrieval_payload(
                question=q,
                router_plan=router_plan,
                final_ctx=final_ctx,
                max_slots=6,
            )

            gap_messages = [
                {
                    "role": "system",
                    "content": EOH_GAP_RETRIEVAL_SYSTEM_PROMPT.strip(),
                },
                {
                    "role": "user",
                    "content": json.dumps(gap_payload, ensure_ascii=False),
                },
            ]

            yield sse(
                "status",
                {"status": "eoh_gap_planning", "detail": "LLM planning targeted gap retrievals."},
            )

            gap_resp = await _chat_completion_async(
                model=CHAT_MODEL_UTIL,
                messages=gap_messages,
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            gap_raw = gap_resp.choices[0].message.content or "{}"

            try:
                gap_plan = json.loads(gap_raw)
            except Exception:
                logger.exception("Failed to parse EoH gap plan JSON")
                gap_plan = {}

            if gap_plan.get("needs_gap_retrieval"):
                slots = gap_plan.get("slots") or []

                yield sse(
                    "eoh_gap_plan",
                    {
                        "reason": gap_plan.get("reason", ""),
                        "slot_count": len(slots),
                        "slots": slots,
                    },
                )

                for slot in slots:
                    kind = str(slot.get("kind") or "other")
                    slot_id = str(slot.get("slot_id") or "")
                    suggested_sources = slot.get("suggested_sources") or []
                    terms = slot.get("terms") or []
                    per_slot_limit = int(slot.get("limit") or 2)

                    if per_slot_limit < 1:
                        per_slot_limit = 1
                    if per_slot_limit > 4:
                        per_slot_limit = 4

                    if not suggested_sources:
                        continue

                    for src in suggested_sources:
                        src = str(src or "").strip()
                        if not src:
                            continue

                        if src not in db_sources and src not in [d["source"] for d in final_ctx]:
                            continue

                        yield sse(
                            "status",
                            {
                                "status": "eoh_gap_retrieving",
                                "slot_id": slot_id,
                                "kind": kind,
                                "source": src,
                            },
                        )

                        try:
                            if kind == "case_analog" and src == CASE_ANALOG_SOURCE:
                                ann_rows = await search_source_ann(
                                    pool=pool,
                                    source=CASE_ANALOG_SOURCE,
                                    q_vec_literal=q_vec_literal,
                                    limit=per_slot_limit,
                                )
                                for r in ann_rows:
                                    ann_score = float(r.get("score") or 0.0)
                                    capped_score = min(ann_score, 0.30)
                                    extra_gap_docs.append(
                                        {
                                            "id": f"gap:{slot_id}:{r['id']}",
                                            "source": r.get("source", CASE_ANALOG_SOURCE),
                                            "source_id": r.get("source_id"),
                                            "title": (r.get("title") or "").strip()
                                            or "ICU case analog from MIMIC-4 note (gap)",
                                            "text": r.get("text", ""),
                                            "score": capped_score,
                                            "method": "gap_case_analog",
                                        }
                                    )

                            else:
                                query_text = q
                                if terms:
                                    query_text = " ".join(terms)

                                ts_rows = await search_source_ts(
                                    pool=pool,
                                    source=src,
                                    q=query_text,
                                    limit=per_slot_limit,
                                )

                                if not ts_rows:
                                    ann_rows = await search_source_ann(
                                        pool=pool,
                                        source=src,
                                        q_vec_literal=q_vec_literal,
                                        limit=per_slot_limit,
                                    )
                                    ts_rows = ann_rows

                                for r in ts_rows:
                                    extra_gap_docs.append(
                                        {
                                            "id": f"gap:{slot_id}:{r['id']}",
                                            "source": r.get("source", src),
                                            "source_id": r.get("source_id"),
                                            "title": (r.get("title") or "").strip()
                                            or f"Gap retrieval from {src}",
                                            "text": r.get("text", ""),
                                            "score": float(r.get("score") or 0.0),
                                            "method": f"gap_{kind}",
                                        }
                                    )

                        except Exception:
                            logger.exception("EoH gap retrieval failed for slot=%r source=%r", slot_id, src)
                            continue

            if extra_gap_docs:
                yield sse(
                    "timing",
                    {
                        "phase": "gap_retrieval",
                        "elapsed_ms": int((time.perf_counter() - t0) * 1000),
                    },
                )
                seen_keys = {
                    (d["id"], d["source"])
                    for d in final_ctx
                }
                deduped: List[Dict[str, Any]] = []
                for d in extra_gap_docs:
                    key = (d["id"], d["source"])
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    deduped.append(d)

                extra_gap_docs = deduped
                final_ctx = final_ctx + extra_gap_docs

                yield sse(
                    "eoh_gap_retrieval",
                    {
                        "added_docs": len(extra_gap_docs),
                        "slots_used": len(gap_plan.get("slots") or []),
                    },
                )

        except Exception:
            logger.exception("EoH gap retrieval planning or execution failed")


    # ---------------------------------------------------------------------------
    # 13b) Ensure Valyu research docs are present in final_ctx when research=1
    # ---------------------------------------------------------------------------
    try:
        # research is usually an int flag (0/1) in the query params
        if research and use_valyu and final_ctx:
            has_valyu = _has_valyu_doc(final_ctx)

            # If we have Valyu evidence at all, we want it in final_ctx.
            # In research mode we bias toward including *all* Valyu docs (deduped),
            # but you can cap this if context ever gets too big.
            if valyu_evidence_docs:
                # Deduplicate against existing context
                seen_keys = {(d["id"], d["source"]) for d in final_ctx}
                backfilled: List[Dict[str, Any]] = []
                for doc in valyu_evidence_docs[:3]:
                    key = (doc.get("id"), doc.get("source"))
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)

                    # Tag explicitly as Valyu research so prompts can treat them correctly
                    d = dict(doc)
                    if not d.get("id"):
                        d["id"] = f"valyu_doc:{len(seen_keys)}"
                    d["method"] = (d.get("method") or "valyu") + "+valyu_research"
                    backfilled.append(d)

                if backfilled:
                    final_ctx = final_ctx + backfilled
                    yield sse(
                        "status",
                        {
                            "status": "valyu_backfill",
                            "detail": (
                                "Added Valyu research docs to final context "
                                "(research=1, use_valyu=1)."
                            ),
                            "added_docs": len(backfilled),
                            "had_valyu_before": bool(has_valyu),
                        },
                    )

            # If we somehow have no valyu_evidence_docs but we do have raw Valyu matches,
            # fall back to at least the best 1–2.
            elif valyu_matches:
                # sort/clip if needed – for now just take top 2 by score
                sorted_matches = sorted(
                    valyu_matches,
                    key=lambda r: float(r.get("score") or 0.0),
                    reverse=True,
                )[:2]

                seen_keys = {(d["id"], d["source"]) for d in final_ctx}
                backfilled: List[Dict[str, Any]] = []
                for r in sorted_matches:
                    key = (r.get("id"), r.get("source", "valyu_pubmed"))
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                    text = (r.get("text") or "") or ((r.get("meta") or {}).get("snippet") or "")
                    if not text:
                        continue
                    backfilled.append(
                        {
                            "id": f"valyu_backfill:{r.get('id')}",
                            "source": r.get("source", "valyu_pubmed"),
                            "source_id": r.get("id"),
                            "title": (r.get("title") or "Valyu article").strip(),
                            "text": text,
                            "score": float(r.get("score") or 0.0),
                            "method": "valyu_raw+valyu_backfill",
                        }
                    )

                if backfilled:
                    final_ctx = final_ctx + backfilled
                    yield sse(
                        "status",
                        {
                            "status": "valyu_backfill_raw",
                            "detail": (
                                "Backfilled top Valyu raw snippets into context "
                                "(research=1, use_valyu=1, no synthesized evidence)."
                            ),
                            "added_docs": len(backfilled),
                        },
                    )

    except Exception:
        logger.exception("EoH: failed to backfill Valyu doc(s) into final_ctx")
    
    if await request.is_disconnected():
        return

    citations = build_citations(final_ctx)

    # ---------------------------------------------------------------------------
    # 14) with_llm == False -> just metadata
    # ---------------------------------------------------------------------------
    if not with_llm:
        yield sse("status", {"status": "done_no_llm"})
        yield sse("citations", {"citations": citations})
        yield sse(
            "end",
            {
                "meta": {
                    "mode": "eoh",
                    "question_type": question_type,
                    "n_modules": sum(len(step.get("modules", [])) for step in router_plan.get("module_plan", [])),
                    "n_handles": sum(len(item.get("handles", [])) for item in router_plan.get("doc_retrieval_plan", [])),
                    "n_sources_raw": raw_source_count,
                    "n_sources": len(gated_results_by_source),
                    "n_ctx_internal": len(internal_ctx),
                    "n_ctx_valyu": valyu_ctx_count,
                    "n_ctx_total": len(final_ctx),
                    "ctx_k": ctx_k,
                    "valyu_k": valyu_k,
                    "with_llm": with_llm,
                }
            },
        )
        return

    if not final_ctx:
        yield sse("status", {"status": "done_no_llm"})
        yield sse("citations", {"citations": []})
        yield sse(
            "end",
            {
                "meta": {
                    "mode": "eoh",
                    "question_type": question_type,
                    "n_modules": 0,
                    "n_handles": 0,
                    "n_sources_raw": raw_source_count,
                    "n_sources": len(gated_results_by_source),
                    "n_ctx_internal": 0,
                    "n_ctx_valyu": 0,
                    "n_ctx_total": 0,
                    "ctx_k": ctx_k,
                    "valyu_k": valyu_k,
                    "with_llm": with_llm,
                }
            },
        )
        return

    # ---------------------------------------------------------------------------
    # 15) LLM streaming with EoH-routed system prompt
    # ---------------------------------------------------------------------------
    yield sse("phase_start", {"source": "fusion", "method": "llm"})
    yield sse("status", {"status": "generating_eoh_answer"})

    answer_buffer: List[str] = []

    try:
        for ev in stream_llm_events(
            q,
            final_ctx,
            llm_mode,
            coding_mode=False,
            chat_model=CHAT_MODEL_GUIDELINES,
            system_prompt=EOH_ROUTED_ANSWER_SYSTEM_PROMPT,
            event_prefix="llm",
            answer_mode="eoh",
            phase="eoh_reasoning",
        ):
            if await request.is_disconnected():
                return

            try:
                if ev.get("event", "").startswith("llm"):
                    data_str = ev.get("data", "")
                    if data_str:
                        payload = json.loads(data_str)
                        chunk = (
                            payload.get("text")
                            or payload.get("delta")
                            or payload.get("content")
                            or ""
                        )
                        if isinstance(chunk, str):
                            answer_buffer.append(chunk)
            except Exception:
                logger.debug("Failed to parse llm event payload for answer_buffer", exc_info=True)

            yield ev
    except Exception as e:
        logger.exception("Error during EoH LLM streaming")
        yield sse(
            "error",
            {"error": "llm_failed", "detail": str(e)},
        )

    yield sse("phase_end", {"source": "fusion", "method": "llm"})
    yield sse("citations", {"citations": citations})

    # ---------------------------------------------------------------------------
    # 16) Evidence-to-claim mapping (optional)
    # ---------------------------------------------------------------------------
    try:
        answer_text = "".join(answer_buffer).strip()
        if answer_text:
            evidence_map = await _run_evidence_mapping(
                answer_text=answer_text,
                q=q,
                ctx_docs=final_ctx,
                model=CHAT_MODEL_UTIL,
            )
            yield sse("evidence_map", evidence_map)
    except Exception:
        logger.exception("Failed to build evidence_map; continuing without it")

    yield sse(
        "end",
        {
            "meta": {
                "mode": "eoh",
                "question_type": question_type,
                "n_modules": sum(len(step.get("modules", [])) for step in router_plan.get("module_plan", [])),
                "n_handles": sum(len(item.get("handles", [])) for item in router_plan.get("doc_retrieval_plan", [])),
                "n_sources_raw": raw_source_count,
                "n_sources": len(gated_results_by_source),
                "n_ctx_internal": len(internal_ctx),
                "n_ctx_valyu": valyu_ctx_count,
                "n_ctx_total": len(final_ctx),
                "ctx_k": ctx_k,
                "valyu_k": valyu_k,
                "with_llm": with_llm,
            }
        },
    )


# ---------------------------------------------------------------------------
# /eoh_stream — EoH mode with LLM router integration
# ---------------------------------------------------------------------------


@router.get("/eoh_stream")
async def eoh_stream(
    request: Request,
    q: str = Query(..., description="EoH / Ethos-of-Health grading/QA query"),
    sources: Optional[str] = Query(
        None,
        description=(
            "Comma-separated internal sources. If omitted, uses guideline-ish "
            "sources plus the Ethos/EoH source."
        ),
    ),
    limit: int = Query(10, ge=1, le=64),
    ctx_k: int = Query(32, ge=1, le=128),
    valyu_k: int = Query(
        3,
        ge=0,
        le=16,
        description="Default 0 for EoH mode (no Valyu); can be overridden."
    ),
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
        1,
        ge=0,
        le=1,
        description="1=include Valyu matches, 0=disable (default for EoH).",
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
    patient_state: Optional[str] = Query(
        None,
        description="Optional JSON string with patient state summary for EoH router",
    ),
    debug: bool = Query(
        False,
        description="Emit extra debug events including fused context text (context_fused)",
    ),
    use_timeline: int = Query(
        1,
        ge=0,
        le=1,
        description="1=load patient timeline from DB and inject into context, 0=disable (default).",
    ),
    timeline_patient_id: Optional[str] = Query(
        None,
        description="Patient ID for timeline loading (required if use_timeline=1).",
    ),
    pool: Any = Depends(resolve_pg_pool),
    research: int = Query(
        1,
        ge=0,
        le=1,
        description="1=enable case analogs (MIMIC-4 ICU notes) and optional research helpers for this query",
    ),
    enable_gap: int = Query(
        1,
        ge=0,
        le=1,
        description="1=run EoH gap retrieval pass, 0=skip (for perf/debug).",
    ),
) -> EventSourceResponse:
    """
    EoH / Ethos-of-Health mode with LLM router integration.

    This endpoint is now planner-first:
    1. Calls the EoH LLM router to create a module/doc-handle plan
    2. Emits the plan via SSE events (eoh_router_plan, eoh_retrieval_plan)
    3. Injects the plan into the EoH RAG context
    4. Proceeds with existing EoH RAG behavior (ANN hits, etc.)
    5. Uses EOH_ROUTED_ANSWER_SYSTEM_PROMPT for the LLM answer

    New SSE events emitted:
    - eoh_router_plan: Full router plan JSON
    - eoh_retrieval_plan: Compact retrieval summary with question_type and handles
    """
    if sources:
        raw_sources = [s.strip() for s in sources.split(",") if s.strip()]
        seen = set()
        db_sources: List[str] = []
        for s in raw_sources:
            if s not in seen:
                seen.add(s)
                db_sources.append(s)
    else:
        discovered = await discover_all_guideline_sources(pool)

        merged: List[str] = []
        seen: set[str] = set()

        for s in EOH_STREAM_DEFAULT_SOURCES:
            if s not in seen:
                seen.add(s)
                merged.append(s)

        for s in discovered:
            if s not in seen:
                seen.add(s)
                merged.append(s)

        db_sources = merged

    warning = _send_large_request_warning(q, db_sources, limit)

    async def event_gen() -> AsyncIterator[Dict[str, str]]:
        if warning:
            yield sse("warning", warning)

        async for ev in eoh_stream_event_generator(
            request=request,
            q=q,
            db_sources=db_sources,
            limit=limit,
            ctx_k=ctx_k,
            valyu_k=valyu_k or 2,
            with_llm=bool(with_llm),
            llm_mode=llm_mode,
            use_valyu=bool(use_valyu or research),
            valyu_mode=valyu_mode,
            valyu_raw=bool(valyu_raw),
            valyu_sources=valyu_sources,
            valyu_boost=valyu_boost,
            pool=pool,
            patient_state=patient_state,
            debug=debug,
            use_timeline=bool(use_timeline),
            timeline_patient_id=timeline_patient_id,
            research=research,
            enable_gap=enable_gap,
        ):
            yield ev

    return EventSourceResponse(event_gen(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# EoH Detective Helper Functions
# ---------------------------------------------------------------------------

async def eoh_detective_planner(
    *,
    client: Optional[OpenAI] = None,
    patient_id: str,
    focus: str,
    high_level_question: str,
    max_steps: int = 6,
    patient_snapshot: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    LLM-based planner for EoH Detective.

    Now timeline-aware via `patient_snapshot`, which may contain:
      - key_signals
      - diagnostic_landscape
      - diagnostic_landscape_history
      - span_days
      - timeline_summary (if available)

    Returns a JSON plan with:
    - patient_id
    - focus
    - steps: list of {step_id, kind, question_type, q, debug}
    """
    if client is None:
        client = OpenAI(timeout=60.0)

    # Payload sent to the planner LLM
    planner_input = {
        "patient_id": patient_id,
        "focus": focus,
        "high_level_question": high_level_question,
        "max_steps": max_steps,
        "patient_snapshot": patient_snapshot or {},
    }

    messages = [
        {
            "role": "system",
            "content": EOH_DETECTIVE_PLANNER_SYSTEM_PROMPT.strip(),
        },
        {
            "role": "user",
            "content": json.dumps(
                planner_input,
                ensure_ascii=False,
                cls=DateTimeJSONEncoder,
            ),
        },
    ]

    try:
        resp = await _chat_completion_async(
            model=CHAT_MODEL_UTIL,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        raw = resp.choices[0].message.content or "{}"
        plan = json.loads(raw)
    except Exception as e:
        logger.exception("eoh_detective_planner: LLM planning failed, using fallback plan")
        plan = {
            "patient_id": patient_id,
            "focus": focus,
            "steps": [
                {
                    "step_id": "A1",
                    "kind": "terrain_risk",
                    "question_type": "A",
                    "q": (
                        "Using this patient's entire timeline, summarize their major "
                        "clinical arcs and current Ethos-of-Health terrain. What were "
                        "the main inflection points (new diagnoses, major complications, "
                        "ICU transfers, surgeries, code events), and what are the 3–5 "
                        "dominant problems now? Ground your answer in the timeline, "
                        "including approximate dates and key labs/vitals/events. Do NOT "
                        "propose management yet; focus on mapping the terrain."
                    ),
                    "debug": False,
                }
            ],
            "planner_error": str(e),
        }

    # Normalize steps
    steps = plan.get("steps") or []
    normalized_steps: List[Dict[str, Any]] = []

    for i, step in enumerate(steps, start=1):
        sid = str(step.get("step_id") or f"S{i}")
        q = (step.get("q") or "").strip()
        if not q:
            continue
        normalized_steps.append(
            {
                "step_id": sid,
                "kind": str(step.get("kind") or "other"),
                "question_type": str(step.get("question_type") or "OTHER"),
                "q": q,
                "debug": bool(step.get("debug", False)),
            }
        )

    # Ensure A1 terrain step exists; if not, prepend one
    has_terrain = any(
        s.get("kind") == "terrain_risk" or s.get("step_id") == "A1"
        for s in normalized_steps
    )
    if not has_terrain:
        terrain_q = (
            "Using this patient's entire timeline, summarize their major "
            "clinical arcs and current Ethos-of-Health terrain. What were "
            "the main inflection points (new diagnoses, major complications, "
            "ICU transfers, surgeries, code events), and what are the 3–5 "
            "dominant problems now? Ground your answer in the timeline, "
            "including approximate dates and key labs/vitals/events. Do NOT "
            "propose management yet; focus on mapping the terrain."
        )
        normalized_steps.insert(
            0,
            {
                "step_id": "A1",
                "kind": "terrain_risk",
                "question_type": "A",
                "q": terrain_q,
                "debug": False,
            },
        )

    # Respect max_steps (planner is encouraged to use up to this, but we hard-cap here)
    if len(normalized_steps) > max_steps:
        normalized_steps = normalized_steps[:max_steps]

    plan["patient_id"] = patient_id
    plan["focus"] = plan.get("focus") or focus
    plan["steps"] = normalized_steps

    return plan


async def detective_report_llm(
    client: OpenAI,
    report_payload: Dict[str, Any],
) -> str:
    """
    Final EoH Detective report LLM.

    Input:
      - report_payload: {
          "high_level_question": str,
          "patient_id": str,
          "focus": str,
          "timeline_snapshot": {...},
          "steps": [ {step_summaries...} ],
        }

    Returns:
      - report_text: markdown-like string following EOH_DETECTIVE_REPORT_SYSTEM_PROMPT
    """
    resp = await _chat_completion_async(
        model=CHAT_MODEL_GUIDELINES,
        messages=[
            {
                "role": "system",
                "content": EOH_DETECTIVE_REPORT_SYSTEM_PROMPT.strip(),
            },
            {
                "role": "user",
                "content": json.dumps(
                    report_payload,
                    ensure_ascii=False,
                    cls=DateTimeJSONEncoder,
                ),
            },
        ],
        temperature=0.2,
    )

    return (resp.choices[0].message.content or "").strip()

# ---------------------------------------------------------------------------
# EoH Detective – over-arching multi-step stream
# ---------------------------------------------------------------------------

async def eoh_detective_stream_event_generator(
    *,
    request: Request,
    q: str,
    timeline_patient_id: str,
    pool: Any,
    focus: Optional[str] = None,
    max_steps: int = 6,
    # you can pass through flags that will be used for each step
    db_sources: Optional[List[str]] = None,
    limit: int = 10,
    ctx_k: int = 32,
    valyu_k: int = 3,
    with_llm: bool = True,
    llm_mode: str = "chunk",
    use_valyu: bool = True,
    valyu_mode: str = "search",
    valyu_raw: bool = True,
    valyu_sources: Optional[str] = None,
    valyu_boost: float = 1.0,
    research: int = 0,
    enable_gap: int = 1,
) -> AsyncIterator[Dict[str, str]]:
    """
    Over-arching detective stream:
      1. Create a multi-step investigation plan via eoh_detective_planner.
      2. Execute each step by calling eoh_stream_event_generator internally.
      3. Stream all intermediate SSE with step_ids embedded in data payloads,
         plus final meta and a top-level EoH Detective report.

    NOTE: This is a thin orchestrator. It delegates heavy lifting to /eoh_stream
    and only adds planning + step-level + final-report structure.
    """

    t0 = time.perf_counter()

    if not timeline_patient_id:
        yield sse(
            "error",
            {"error": "missing_timeline_patient_id", "detail": "timeline_patient_id is required"},
        )
        return

    # If db_sources not provided, fall back to your usual EoH default sources
    if db_sources is None:
        db_sources = list(EOH_STREAM_DEFAULT_SOURCES)

    # -----------------------------------------------------------------------
    # 0) Start event
    # -----------------------------------------------------------------------
    yield sse(
        "start",
        {
            "mode": "eoh_detective",
            "q": q,
            "patient_id": timeline_patient_id,
            "max_steps": max_steps,
            "db_sources": db_sources,
        },
    )

    if await request.is_disconnected():
        return

    # -----------------------------------------------------------------------
    # 1) Build timeline snapshot for planner + final report
    #     (Detective is the owner of the one-time timeline summarizer call.)
    # -----------------------------------------------------------------------
    timeline_snapshot: Optional[Dict[str, Any]] = None
    diag_payload: Optional[Dict[str, Any]] = None
    timeline_summary_for_planner: Optional[str] = None

    try:
        events = await load_patient_timeline(timeline_patient_id)
        timeline_ctx_local = await timeline_engine.build_timeline_context_from_events(
            events, timeline_patient_id
        )

        # Diagnostic landscape payload
        if timeline_ctx_local.diagnostic_landscape:
            dl = timeline_ctx_local.diagnostic_landscape
            if hasattr(dl, "to_payload") and callable(dl.to_payload):
                diag_payload = dl.to_payload()
            elif hasattr(dl, "to_normalized_dict") and callable(dl.to_normalized_dict):
                diag_payload = {"weights": dl.to_normalized_dict()}
            elif isinstance(dl, dict):
                diag_payload = dl
            else:
                diag_payload = None
        else:
            diag_payload = None

        # Landscape history
        history = timeline_engine.compute_landscape_history_from_events(
            events, timeline_patient_id
        )

        # -------------------------------------------------------------------
        # 1a) One-time timeline summarizer LLM (Detective owns this)
        # -------------------------------------------------------------------
        timeline_summaries: Optional[TimelineSummaries] = None
        try:
            # Emit a status event before we call the summarizer
            try:
                yield sse(
                    "status",
                    {
                        "status": "timeline_summarizer_start",
                        "detail": "Running timeline summarizer (PROBE+RAG or hierarchical, depending on size and flags).",
                        "patient_id": timeline_patient_id,
                        "timeline_chars": len(timeline_ctx_local.context_text or ""),
                        "event_count": len(events or []),
                    },
                )
            except Exception:
                logger.debug(
                    "eoh_detective: failed to emit timeline_summarizer_start SSE",
                    exc_info=True,
                )

            timeline_summaries = await summarize_timeline_for_eoh(
                client=_openai_client,
                question=q,
                timeline_text=timeline_ctx_local.context_text,
                pool=pool,
                patient_id=timeline_patient_id,
            )
        except Exception:
            logger.exception("eoh_detective: timeline summarizer failed")
            timeline_summaries = None

        # Emit SSE describing what the summarizer produced
        try:
            if timeline_summaries is not None:
                full_len = len(timeline_summaries.timeline_summary or "")
                router_len = len(timeline_summaries.timeline_summary or "")
                valyu_len = len(timeline_summaries.valyu_summary or "")
                query_terms_len = len(
                    timeline_summaries.timeline_summary or ""
                )
                meds_labs_len = len(
                    timeline_summaries.meds_and_labs_snapshot or ""
                )

                # High-level meta event
                yield sse(
                    "timeline_summarizer_result",
                    {
                        "patient_id": timeline_patient_id,
                        "full_len": full_len,
                        "router_len": router_len,
                        "valyu_len": valyu_len,
                        "query_terms_len": query_terms_len,
                        "meds_and_labs_len": meds_labs_len,
                        "has_full": bool(full_len),
                        "has_router": bool(router_len),
                        "has_valyu": bool(valyu_len),
                        "has_query_terms": bool(query_terms_len),
                        "has_meds_and_labs": bool(meds_labs_len),
                    },
                )

                # Optional: send a compact view of query-term helper text
                if timeline_summaries.timeline_summary:
                    yield sse(
                        "timeline_summarizer_query_terms",
                        {
                            "patient_id": timeline_patient_id,
                            # Trim so we don’t blow up the stream; this is for UI/debug.
                            "summary": timeline_summaries.timeline_summary[
                                :4000
                            ],
                        },
                    )

                # Optional: send meds/labs snapshot as its own event
                if timeline_summaries.meds_and_labs_snapshot:
                    yield sse(
                        "timeline_summarizer_meds_labs_snapshot",
                        {
                            "patient_id": timeline_patient_id,
                            "snapshot": timeline_summaries.meds_and_labs_snapshot[
                                :4000
                            ],
                        },
                    )

                # Small status marker so UI can show "timeline summarizer done"
                yield sse(
                    "status",
                    {
                        "status": "timeline_summarizer_done",
                        "detail": "Timeline summarizer completed.",
                        "patient_id": timeline_patient_id,
                    },
                )

        except Exception:
            logger.debug(
                "eoh_detective: failed to emit timeline summarizer SSE events",
                exc_info=True,
            )

        if await request.is_disconnected():
            return

        # Router-style summary for planner / router (fallback-safe)
        try:
            # Canonical summary for ALL downstream LLMs (router, Valyu, EoH steps)
            # TimelineSummaries already gives you a single canonical story, but we
            # defensively fall back if needed.
            canonical_summary = (
                (timeline_summaries.timeline_summary if timeline_summaries else None)
                or timeline_summary_for_planner
                or timeline_ctx_local.context_text
                or ""
            )

            if len(canonical_summary) > SUMMARY_MAX_CHARS:
                canonical_summary = canonical_summary[:SUMMARY_MAX_CHARS]

            if not canonical_summary:
                canonical_summary = timeline_ctx_local.context_text or ""

            probe_debug = getattr(timeline_summaries, "probe_debug", None) if timeline_summaries else None

            timeline_snapshot = {
                "patient_id": timeline_patient_id,
                "span_days": timeline_ctx_local.span_days,
                "key_signals": timeline_ctx_local.key_signals,
                "flare_features": timeline_ctx_local.flare_features,
                "diagnostic_landscape": diag_payload,
                "diagnostic_landscape_history": history,
                "timeline_summary": canonical_summary,
                "timeline_meds_and_labs_snapshot": (
                    timeline_summaries.meds_and_labs_snapshot if timeline_summaries else ""
                ),
            }

            if probe_debug is not None:
                timeline_snapshot["timeline_probe"] = probe_debug

            # Optional SSE for detective UI
            yield sse(
                "detective_timeline_snapshot",
                {
                    "patient_id": timeline_patient_id,
                    "span_days": timeline_ctx_local.span_days,
                    "has_diag_landscape": bool(diag_payload),
                    "has_timeline_summary": bool(canonical_summary),
                    "key_signals": timeline_ctx_local.key_signals,
                },
            )

        except Exception:
            logger.exception("eoh_detective: failed to build router-style summary for timeline snapshot")
            # Fallback: use raw context_text if available
            if timeline_ctx_local:
                canonical_summary = timeline_ctx_local.context_text or ""
                timeline_snapshot = {
                    "patient_id": timeline_patient_id,
                    "span_days": timeline_ctx_local.span_days,
                    "key_signals": timeline_ctx_local.key_signals,
                    "flare_features": timeline_ctx_local.flare_features,
                    "diagnostic_landscape": diag_payload,
                    "diagnostic_landscape_history": history,
                    "timeline_summary": canonical_summary,
                }
            else:
                timeline_snapshot = None

    except Exception:
        logger.exception("eoh_detective: failed to build timeline snapshot")
        timeline_snapshot = None
        diag_payload = None
        timeline_summary_for_planner = None

    # -----------------------------------------------------------------------
    # 2) Plan creation (planner sees timeline snapshot)
    # -----------------------------------------------------------------------
    focus_label = focus or "eoh_detective_run"

    yield sse(
        "status",
        {
            "status": "planning",
            "detail": "Creating EoH detective plan",
            "patient_id": timeline_patient_id,
        },
    )

    try:
        plan = await eoh_detective_planner(
            client=_openai_client,
            patient_id=timeline_patient_id,
            focus=focus_label,
            high_level_question=q,
            max_steps=max_steps,
            patient_snapshot=timeline_snapshot,
        )
    except Exception as e:
        logger.exception("eoh_detective: planner failed")
        yield sse(
            "error",
            {"error": "planner_failed", "detail": str(e)},
        )
        return

    steps = plan.get("steps") or []

    yield sse(
        "detective_plan",
        {
            "patient_id": plan.get("patient_id"),
            "focus": plan.get("focus"),
            "steps": [
                {
                    "step_id": s["step_id"],
                    "kind": s["kind"],
                    "question_type": s["question_type"],
                    "debug": s.get("debug", False),
                }
                for s in steps
            ],
        },
    )

    if await request.is_disconnected():
        return

    # -----------------------------------------------------------------------
    # 3) Execute steps sequentially
    # -----------------------------------------------------------------------
    detective_meta: Dict[str, Any] = {
        "patient_id": timeline_patient_id,
        "focus": plan.get("focus"),
        "n_steps": len(steps),
        "step_summaries": [],
    }

    for step in steps:
        step_id = step["step_id"]
        step_q = step["q"]
        step_debug = bool(step.get("debug", False))

        # Step start marker (top-level SSE from detective)
        yield sse(
            "detective_step_start",
            {
                "step_id": step_id,
                "kind": step["kind"],
                "question_type": step["question_type"],
                "q": step_q,
            },
        )

        if await request.is_disconnected():
            return

        step_citations = None
        step_meta = None

        # Build a compact, router-safe patient_state JSON
        compact_patient_state = (
            build_compact_patient_state_for_router(timeline_snapshot)
            if timeline_snapshot
            else None
        )

        # Inner EoH stream generator
        inner_gen = eoh_stream_event_generator(
            request=request,
            q=step_q,
            db_sources=db_sources,
            limit=limit,
            ctx_k=ctx_k,
            valyu_k=valyu_k,
            with_llm=with_llm,
            llm_mode=llm_mode,
            use_valyu=use_valyu,
            valyu_mode=valyu_mode,
            valyu_raw=valyu_raw,
            valyu_sources=valyu_sources,
            valyu_boost=valyu_boost,
            pool=pool,
            patient_state=compact_patient_state,
            debug=step_debug,
            use_timeline=True,
            timeline_patient_id=timeline_patient_id,
            research=research,
            enable_gap=enable_gap,
        )

        async for ev in inner_gen:
            # ev is {"event": ..., "data": "..."} from sse()
            wrapped_ev = dict(ev)
            wrapped_ev.setdefault("event", "")
            wrapped_ev.setdefault("data", "")

            # Try to read data as JSON once so we can both intercept and annotate it
            data_obj = None
            data_str = wrapped_ev["data"]

            if isinstance(data_str, str) and data_str:
                try:
                    data_obj = json.loads(data_str)
                except Exception:
                    data_obj = None

            # Intercept citations/meta for detective summary
            try:
                if wrapped_ev["event"] == "citations" and isinstance(data_obj, dict):
                    step_citations = data_obj.get("citations")
                elif wrapped_ev["event"] == "end" and isinstance(data_obj, dict):
                    step_meta = data_obj.get("meta")
            except Exception:
                logger.debug(
                    "eoh_detective: failed to parse inner event for summary",
                    exc_info=True,
                )

            # Inject step_id into *data payload*, not as top-level SSE kwarg
            if isinstance(data_obj, dict):
                data_obj.setdefault("step_id", step_id)
                wrapped_ev["data"] = json.dumps(data_obj, ensure_ascii=False)

            # IMPORTANT: do NOT add wrapped_ev["step_id"] – that breaks ServerSentEvent
            # Only event/data/id/retry/comment are allowed at this level.

            yield wrapped_ev

            if await request.is_disconnected():
                return

        # Per-step detective summary
        detective_meta["step_summaries"].append(
            {
                "step_id": step_id,
                "kind": step["kind"],
                # planner’s guess
                "planner_question_type": step["question_type"],
                # router’s actual classification, if present in meta
                "router_question_type": (step_meta or {}).get("question_type"),
                "q": step_q,
                "citations": step_citations,
                "meta": step_meta,
            }
        )

        # Step end marker (top-level SSE)
        yield sse(
            "detective_step_end",
            {
                "step_id": step_id,
                "citations_present": bool(step_citations),
                "has_meta": step_meta is not None,
            },
        )

        if await request.is_disconnected():
            return

    # -----------------------------------------------------------------------
    # 4) Final detective meta + timing
    # -----------------------------------------------------------------------
    elapsed_ms = int((time.perf_counter() - t0) * 1000)

    yield sse(
        "detective_summary",
        {
            "patient_id": detective_meta["patient_id"],
            "focus": detective_meta["focus"],
            "n_steps": detective_meta["n_steps"],
            "elapsed_ms": elapsed_ms,
            "steps": detective_meta["step_summaries"],
        },
    )

    if await request.is_disconnected():
        return

    # -----------------------------------------------------------------------
    # 5) Generate final detective report (final EoH Detective LLM)
    # -----------------------------------------------------------------------
    if with_llm:
        try:
            report_payload = {
                "high_level_question": q,
                "patient_id": timeline_patient_id,
                "focus": detective_meta["focus"],
                "timeline_snapshot": timeline_snapshot,
                "steps": detective_meta["step_summaries"],
            }

            yield sse(
                "status",
                {
                    "status": "detective_llm_reporting",
                    "detail": "Generating final EoH Detective report",
                    "patient_id": timeline_patient_id,
                },
            )

            report_text = await detective_report_llm(
                _openai_client,
                report_payload,
            )

            yield sse(
                "detective_report",
                {
                    "patient_id": timeline_patient_id,
                    "focus": detective_meta["focus"],
                    "report": report_text,
                },
            )

        except Exception:
            logger.exception("eoh_detective: final report generation failed")
            yield sse(
                "status",
                {
                    "status": "detective_llm_error",
                    "detail": "Failed to generate final detective report",
                },
            )

    # Final end marker
    yield sse(
        "end",
        {
            "meta": {
                "mode": "eoh_detective",
                "patient_id": timeline_patient_id,
                "focus": detective_meta["focus"],
                "n_steps": detective_meta["n_steps"],
                "elapsed_ms": elapsed_ms,
            }
        },
    )

# ---------------------------------------------------------------------------
# EoH Detective Stream
# ---------------------------------------------------------------------------

@router.get("/eoh_detective_stream")
async def eoh_detective_stream(
    request: Request,

    # ----------------------------
    # Canonical required inputs
    # ----------------------------
    q: Optional[str] = Query(None, description="High-level detective question or focus"),
    timeline_patient_id: Optional[str] = Query(None, description="Patient id in ehr.patient_timeline"),

    # ----------------------------
    # Aliases for nicer UX / backwards-compat
    # ----------------------------
    question: Optional[str] = Query(None, description="Alias for q"),
    patient_id: Optional[str] = Query(None, description="Alias for timeline_patient_id"),

    # ----------------------------
    # Run label / controls
    # ----------------------------
    focus: Optional[str] = Query(None, description="Optional short label for this detective run"),
    max_steps: int = Query(6, ge=1, le=12),

    # ----------------------------
    # Source selection / retrieval knobs
    # ----------------------------
    sources: Optional[str] = Query(
        None,
        description="Comma-separated internal sources (same semantics as /eoh_stream)",
    ),
    limit: int = Query(10, ge=1, le=32),
    ctx_k: int = Query(32, ge=4, le=128),

    # ----------------------------
    # Valyu knobs
    # ----------------------------
    valyu_k: int = Query(3, ge=0, le=4),
    use_valyu: bool = Query(True),
    valyu_mode: str = Query("search"),
    valyu_raw: bool = Query(True),
    valyu_sources: Optional[str] = Query(None),
    valyu_boost: float = Query(1.0),

    # ----------------------------
    # LLM controls
    # ----------------------------
    with_llm: bool = Query(True),
    llm_mode: str = Query("chunk"),

    # ----------------------------
    # Research + gap
    # ----------------------------
    research: int = Query(0, ge=0, le=1),
    enable_gap: int = Query(1, ge=0, le=1),

    # alias for enable_gap (so old curls keep working)
    use_gap: Optional[int] = Query(None, description="Alias for enable_gap (0/1)"),

    # ----------------------------
    # Dependencies
    # ----------------------------
    pool: Any = Depends(resolve_pg_pool),  # noqa: F821 (keep your existing import)
):
    """
    Detective wrapper endpoint.
    Supports both canonical params:
      - q, timeline_patient_id
    and friendly aliases:
      - question, patient_id
    """

    # ----------------------------
    # Normalize aliases
    # ----------------------------
    q_final = (q or question or "").strip()
    pid_final = (timeline_patient_id or patient_id or "").strip()

    # allow old "use_gap" param to override enable_gap
    if use_gap is not None:
        enable_gap = int(use_gap)

    if not q_final:
        raise HTTPException(
            status_code=422,
            detail="Missing required query param: q (or alias question)",
        )
    if not pid_final:
        raise HTTPException(
            status_code=422,
            detail="Missing required query param: timeline_patient_id (or alias patient_id)",
        )
    focus = (focus or "").strip() or None
    sources = (sources or "").strip() or None
    valyu_mode = (valyu_mode or "search").strip()
    llm_mode = (llm_mode or "chunk").strip()
    # Parse sources similar to your existing eoh_stream route
    if sources:
        db_sources = [s.strip() for s in sources.split(",") if s.strip()]
    else:
        db_sources = list(EOH_STREAM_DEFAULT_SOURCES)

    gen = eoh_detective_stream_event_generator(
        request=request,
        q=q,
        timeline_patient_id=timeline_patient_id,
        pool=pool,
        focus=focus,
        max_steps=max_steps,
        db_sources=db_sources,
        limit=limit,
        ctx_k=ctx_k,
        valyu_k=valyu_k,
        with_llm=with_llm,
        llm_mode=llm_mode,
        use_valyu=use_valyu,
        valyu_mode=valyu_mode,
        valyu_raw=valyu_raw,
        valyu_sources=valyu_sources,
        valyu_boost=valyu_boost,
        research=research,
        enable_gap=enable_gap,
    )
    return EventSourceResponse(gen)