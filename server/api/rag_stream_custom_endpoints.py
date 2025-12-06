# server/api/rag_stream_custom_endpoints.py

from typing import Optional, List, Any, AsyncIterator, Dict
import json
import logging

from fastapi import APIRouter, Query, Request, Depends
from sse_starlette.sse import EventSourceResponse
from server.timeline.engine import TimelineEngine, load_patient_timeline

from openai import OpenAI
import inspect
import anyio

async def _chat_completion_async(client, **kwargs):
    """
    Call client.chat.completions.create in an async-friendly way,
    whether the client is sync (OpenAI) or async (AsyncOpenAI).
    """
    create = client.chat.completions.create

    # If it's an async function (AsyncOpenAI), just await it
    if inspect.iscoroutinefunction(create):
        return await create(**kwargs)

    # Otherwise run the sync call in a worker thread
    return await anyio.to_thread.run_sync(lambda: create(**kwargs))

from .stream_config import (
    GUIDELINE_SOURCES,
    ETHOS_SOURCE_NAME,
    CODING_DEFAULT_SOURCES,
    CODING_SOURCES,
    BASE_RRF_K,
    EOH_STREAM_DEFAULT_SOURCES,
    CHAT_MODEL,
    CHAT_MODEL_GUIDELINES,
    CHAT_MODEL_CODING_CORE,
    CHAT_MODEL_UTIL,
    STRICT_CODE_SOURCES,
    is_strict_code_source,
    EOH_SYSTEM_PROMPT,
    GUIDELINE_ANSWER_SYSTEM_PROMPT,
    EVIDENCE_MAPPING_SYSTEM_PROMPT
)

# EoH Router imports
from server.eoh.router_llm import eoh_llm_router
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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag-custom"])

# Default ask_stream sources: all guideline-ish sources, but EXCLUDE Ethos by default.
ASK_STREAM_DEFAULT_SOURCES = sorted(
    [s for s in GUIDELINE_SOURCES if s != ETHOS_SOURCE_NAME]
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

# OpenAI client for QA grader
from openai import OpenAI
_openai_client = OpenAI(timeout=60.0)


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
            client,
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

# Case-analog retrieval settings (EoH-specific)
CASE_ANALOG_SOURCE = "mimic4_note"
CASE_ANALOG_QUESTION_TYPES = {"B", "C", "OTHER"}  # where analogs help most
CASE_ANALOG_K = 3  # keep very small to avoid bloating context

# ---------------------------------------------------------------------------
# EoH Router System Prompt Extension
# ---------------------------------------------------------------------------

EOH_ROUTED_ANSWER_SYSTEM_PROMPT = """
You are the Ethos-of-Health (EoH) reasoning model for 2ndOpinionMD.

Your role:
- Interpret patient state using the EoH Gold Standard v2 (2025): stacks, stability bands, drift,
  trajectories, PSI, CBM, suppression logic, and module outputs *in concept only*.
- Ground all clinical statements strictly in the retrieved context (router plan, patient timelines,
  guideline snippets, and any EoH/Ethos documents). You may echo themes that are explicitly shown,
  but you must NOT invent citations, page numbers, or details that do not appear in context.
- Treat the prepended **EoH Router Plan** as the blueprint for your reasoning.

You never query a database. You only see what is in the fused context.

--------------------------------------------------------------------------------
EOH ROUTER PLAN INSTRUCTIONS
--------------------------------------------------------------------------------
You ALWAYS receive a high-level router plan near the top of context. It includes:
- Question type (A–E or OTHER)
- EoH modules involved (e.g., M1–M3B, M4, M13, etc.)
- Document handles retrieved for each module
- Conceptual purpose of each module

When answering:

1. Explicitly tie your reasoning to the router plan.
   Use language such as:
   - "Step 1 (M1–M3B) is designed to…"
   - "M13 would typically generate a prognostic vector by integrating…"
   - "In this framework, M4 applies suppression-auditing logic to…"

2. Stay within the router plan scope.
   Do NOT introduce modules or capabilities that are not mentioned in the router plan
   or elsewhere in the fused context.

3. Treat all module outputs as *conceptual*.
   - You cannot see live DB values, PSI scores, tiers, or model coefficients.
   - You may describe what a module is designed to do, and how it *would* use the
     available context, but not what it "actually computed" unless it is explicitly shown.

4. If `patient_state` JSON is provided, integrate it, but treat it as user-supplied,
   not as verified DB output.

--------------------------------------------------------------------------------
PATIENT TIMELINE CONTEXT SOURCES
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

When a timeline is present (demo or patient_timeline):

- Treat it as the patient’s event-level history (e.g., flares, labs, visits, journals).
- Parse it into dated events with:
  - date / time
  - event type (e.g., visit, lab, flare, symptom, med change, journal)
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

If a timeline is present, you MUST NOT say that “no patient data” or “no fused rows”
are visible. Instead, clearly describe which events you see and how you use them.

RESEARCH CONTEXT (VALYU/PUBMED)

- Some context items may come from research publications (e.g., source names
  containing 'valyu' or 'pubmed').
- Treat these as **supporting evidence** for mechanisms, risk factors, and
  management principles, not as patient-specific predictions.
- You may:
    - Summarize trends and mechanisms that are clearly visible in the excerpts.
    - Say that a pattern in this patient “is consistent with” or “differs from”
      patterns described in the research snippets.
- You must NOT:
    - Invent new statistics, effect sizes, or study conclusions that are not
      shown in the text.
    - Turn research snippets directly into numeric risk estimates for this
      specific patient.

ICU NOTE CORPORA (MIMIC-4 AND SIMILAR)

- Some context items may come from de-identified ICU note corpora such as
  'mimic4_note'. These are **case-analog notes**, not guidelines or calibrated
  risk tools.
- Use them only to illustrate how similar patterns have appeared in anonymized
  ICU patients, for example:
    - “In de-identified ICU notes from MIMIC-4, similar flare patterns often
       appeared in the setting of severe infection rather than autoimmune flare.”
- You MUST:
    - Clearly label them as ICU case analogs (e.g., “MIMIC-4 ICU case notes”).
    - Avoid treating them as authoritative or prospective evidence.
- You MUST NOT:
    - Convert their patterns into quantitative risk estimates.
    - Override guideline-based reasoning or EoH conceptual logic with MIMIC data.
    - Portray them as if they were validated EoH modules or prospective trials.

--------------------------------------------------------------------------------
TIMELINE-DERIVED EOH ARTIFACTS
--------------------------------------------------------------------------------
You may see EoH-specific timeline artifacts in context (e.g. as SSE snippets or
embedded JSON):

- `timeline_signals` – key signals extracted from events (flares, lab spikes,
  stability periods, med changes, misdiagnosis patterns, hidden comorbidities, etc.).
- `timeline_flare_features` – structured features describing flare patterns
  (recency, severity, triggers, lab behavior, recovery).
- `timeline_probabilistic_differential` – a conceptual "diagnostic landscape" object
  (e.g., fields such as `ra_like`, `sle_like`, `psa_like`, `sjogren_like`,
  `mixed_ctd_like`, `vasculitis_like`, `other`, or similar).

When these appear:

- You may *describe* their structure and use them as qualitative evidence
  (e.g., "EoH’s internal landscape leans RA-like rather than SLE-like for this timeline"),
  but you must still obey the numeric rules below.
- If numeric fields are shown explicitly (e.g., 0.8 vs 0.1), you may qualitatively
  describe the relative ordering ("RA-like greater than SLE-like") but avoid treating
  them as validated clinical probabilities.

--------------------------------------------------------------------------------
STRICT EPISTEMICS RULES (MANDATORY)
--------------------------------------------------------------------------------

1. **No numeric hallucinations**
   - Do NOT invent probabilities, percentages, risk tiers, PSI values, drift magnitudes,
     or specific thresholds.
   - You may repeat numeric values only if they appear directly in the context
     (e.g., "CRP 50", "ESR 60", "ra_flare_30d_prob 0.32", "p_ra 0.55").
   - For diagnostic landscapes, you may describe *relative* emphasis
     ("more RA-like than SLE-like") only if the underlying text or JSON indicates that.

2. **No invented guideline details**
   - Do NOT invent references such as "Refs 23, 50–58".
   - Do NOT invent URLs, tables, specific doses, or page numbers.
   - Only state therapy or management details if they are clearly present
     in the retrieved guideline excerpts.

3. **No pretending to observe hidden module outputs**
   You must NOT assert:
   - "M13 predicted 40% flare risk",
   - "The system classified the patient as Tier 3",
   - "PSI score is elevated",
   unless those exact values appear in the visible context.

4. **No overreach**
   - If guideline excerpts are high-level, keep your statements high-level.
   - If the diagnostic landscape is coarse or incomplete, say so.

5. **Uncertainty is REQUIRED when context is limited or partial**
   - Always state what evidence you actually have:
     - router plan,
     - patient timeline events,
     - timeline signals/flare features,
     - diagnostic landscape JSON (if any),
     - guideline snippets.
   - If you have only the router plan and minimal clinical text, say that your
     reasoning is largely conceptual.
   - If you DO have patient timeline data and guideline excerpts, you MUST NOT claim
     that “no fused rows or module outputs are visible.” Instead:
       - Explain that you are using those visible items as evidence.
       - Emphasize that quantitative EoH metrics (PSI, calibrated risks, etc.)
         remain conceptual and are not directly observed.

6. **Handling numeric module outputs**
    - You may see a `patient_state` JSON blob containing numeric outputs from EoH modules
    (e.g., flare risks, diagnostic landscape weights).
    - You are allowed to repeat these numeric values and explain them, as long as:
        - You do NOT alter them.
        - You do NOT invent new numeric values that are not present.
    - Always attribute them to EoH modules or patient_state, for example:
        - “According to the current patient_state, the RA-like weight is higher than SLE-like.”
        - “The stored flare risk snapshot shows higher near-term risk than long-term risk.”
    - You must NOT create any numeric risk estimates or weights if none are provided
    in patient_state or other visible JSON/text.

STRUCTURED OUTPUT FORMAT (REQUIRED)

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
  - "Step 4 (M13): is designed to generate a conceptual prognostic vector by integrating…"
- Explicitly describe how each step *would* use:
  - the timeline events,
  - the extracted signals/flare features,
  - any diagnostic landscape object,
  - and any guideline excerpts that were retrieved.

### 3. Evidence answer (guidelines, research, case-analogs)

- **Guideline backbone (if present)**  
  - Briefly recap which guideline sets appear in context and how they support (or
    constrain) the EoH reasoning (e.g., ACR/EULAR, KDIGO, GOLD, IDSA, ACC/AHA).
  - Refer to them by human-readable labels, not fabricated numbers.

- **Research / trials (Valyu/PubMed, if present)**  
  - Summarize how any research snippets refine your conceptual reasoning
    (mechanisms, flare risks, special populations).
  - Use short labels for clarity (e.g., “RA-ILD cohort”, “HF RCT with SGLT2i”).

- **ICU / EHR case-analog notes (MIMIC, if used)**  
  - If you use MIMIC/EHR analogs, clearly label them as “ICU case analogs”.
  - Describe only qualitative patterns; never convert them into numeric EoH risks.
  - Emphasize they are supportive illustrations, not replacements for EoH modules
    or guidelines.

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
    diagnostic landscape JSON, guideline snippets, research excerpts, case-analog notes).
  - What you do NOT have (no direct PSI values, no calibrated risk curves, no full
    EHR chart, no real-world validation data).
  - Any important gaps (e.g., incomplete treatment history, no imaging details,
    partial guideline excerpts).
- Reiterate that your reasoning is **conceptual and qualitative** even when
  timeline data, patient_state JSON, or research snippets are visible.

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
            _openai_client,
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


# ---------------------------------------------------------------------------
# eoh_stream_event_generator — dedicated EoH event generator with router
# ---------------------------------------------------------------------------


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
) -> AsyncIterator[Dict[str, str]]:
    """
    Dedicated event generator for /eoh_stream with EoH LLM Router integration.

    This generator:
    1. Calls the EoH router early to create a module/doc-handle plan
    2. Emits the plan via SSE events (eoh_router_plan, eoh_retrieval_plan)
    3. Injects the plan into the EoH RAG context as a pseudo-context item
    4. Proceeds with existing EoH RAG behavior (ANN hits, etc.)
    5. Uses EOH_ROUTED_ANSWER_SYSTEM_PROMPT for the LLM answer
    """
    VALYU_K_MAX = 4
    requested_valyu_k = valyu_k
    valyu_k = max(0, min(valyu_k, VALYU_K_MAX))

    term_expansions: Dict[str, List[str]] = {}

    # Parse patient_state if provided
    patient_state_summary: Optional[Dict[str, Any]] = None
    if patient_state:
        try:
            patient_state_summary = json.loads(patient_state)
        except Exception:
            logger.warning("eoh_stream: failed to parse patient_state JSON", exc_info=True)
            patient_state_summary = None

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
            "mode": "eoh",
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

    # ---------------------------------------------------------------------------
    # 1) EoH Router Call — create module/doc-handle plan
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

    # Emit post-routing effective sources count
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
    # 2) Build router plan context item (to prepend to context)
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
    # 4) Valyu fetch (optional for EoH)
    # ---------------------------------------------------------------------------
    # Router-guided Valyu usage: only for certain question types
    effective_use_valyu = use_valyu
    if use_valyu:
        # Example: research support only for certain classes of questions
        if question_type not in ("B", "C", "OTHER"):
            # A: pure flare detection; D/E: maybe pure coding or bookkeeping
            effective_use_valyu = False

    valyu_matches: List[Dict[str, Any]] = []

    if effective_use_valyu and valyu_k > 0:
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

    if await request.is_disconnected():
        return

    # -----------------------------------------------------------------------
    # 4b) Optional: second LLM call to distill Valyu full-text into
    #      short evidence snippets aligned to the router plan.
    #      Only do this when we have full_text (valyu_raw=1) and research mode.
    # -----------------------------------------------------------------------

    valyu_evidence_docs: List[Dict[str, Any]] = []

    if (
        effective_use_valyu
        and valyu_matches
        and valyu_raw
        and research
    ):
        try:
            # Use the same router_plan_text we later stuff into router_ctx_item
            # (we haven't built router_ctx_item yet, but we can reuse the lines).
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
    # 4c) Optional: cheap fallback for Valyu snippets (if no synthesis)
    # ---------------------------------------------------------------------------
    if not valyu_evidence_docs and valyu_matches:
        # Cheap fallback: push raw Valyu rows into context
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
    # 5) Extract Q&A-oriented query terms
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
    # 6) Routing (source selection) — use existing router for source selection
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
    # 7) Retrieve per source (TS + ANN)
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

        # Combine and dedupe
        combined = dedupe_matches(ts_rows + ann_rows)
        if combined:
            results_by_source[src] = combined

    if await request.is_disconnected():
        return

    raw_source_count = len(results_by_source)


    # ---------------------------------------------------------------------------
    # 8) Gating (source-level pruning)
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

    # ---------------------------------------------------------------------------
    # 9) Fuse internal contexts
    # ---------------------------------------------------------------------------
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

    # Start with router plan
    final_ctx: list[dict[str, Any]] = [router_ctx_item]

    # Then Valyu evidence snippets (if any and research mode), so they sit
    # near the top but *after* the router plan.
    if valyu_evidence_docs:
        final_ctx = final_ctx + valyu_evidence_docs

    # Then the usual fused internal context (guidelines, Ethos docs, etc.)
    final_ctx = final_ctx + internal_ctx

    # ---------------------------------------------------------------------------
    # 9b) EoH Demo Timeline – inject as a synthetic context doc
    # ---------------------------------------------------------------------------
    params = request.query_params
    demo_timeline = params.get("eoh_demo_timeline")
    demo_patient_id = params.get("eoh_demo_patient_id")

    if demo_timeline:
        patient_label = demo_patient_id or "demo"

        timeline_doc = {
            "id": f"eoh_demo_timeline:{patient_label}",
            "source": "eoh_demo_timeline",
            "source_id": f"eoh_demo_timeline:{patient_label}",
            "title": f"EoH demo timeline – {patient_label}",
            # IMPORTANT: use 'text', not 'content'
            "text": demo_timeline,
            # Give it a strong score so any sorting keeps it near the top
            "score": 1.0,
            "method": "timeline",
        }

        # Put it right after the router context (or at the very front if you prefer)
        # index 0 is router_ctx_item, so insert at 1
        final_ctx = [timeline_doc] + final_ctx

        # Optional: explicit SSE so the UI knows we injected it
        yield sse(
            "patient_timeline_ctx",
            {
                "source": "eoh_demo_timeline",
                "patient_id": demo_patient_id,
            },
        )

    # ---------------------------------------------------------------------------
    # 9c) Database Timeline – load from ehr.patient_timeline if use_timeline=1
    # ---------------------------------------------------------------------------
    if use_timeline and timeline_patient_id:
        yield sse(
            "status",
            {"status": "loading_timeline", "patient_id": timeline_patient_id},
        )

        try:
            from server.timeline.engine import TimelineEngine, load_patient_timeline

            engine = TimelineEngine()

            # 1) Load events directly from ehr.patient_timeline
            events = await load_patient_timeline(timeline_patient_id)

            yield sse(
                "timeline_events_loaded",
                {
                    "patient_id": timeline_patient_id,
                    "event_count": len(events),
                },
            )

            # 2) Build timeline context from those events
            timeline_ctx = await engine.build_timeline_context_from_events(
                events, timeline_patient_id
            )

            # Emit timeline_loaded event
            yield sse(
                "timeline_loaded",
                {
                    "patient_id": timeline_patient_id,
                    "event_count": timeline_ctx.event_count,
                    "span_days": timeline_ctx.span_days,
                },
            )

            # Emit timeline_signals event
            yield sse(
                "timeline_signals",
                {
                    "patient_id": timeline_patient_id,
                    "key_signals": timeline_ctx.key_signals,
                },
            )

            # Emit timeline_flare_features event
            if timeline_ctx.flare_features:
                yield sse(
                    "timeline_flare_features",
                    {
                        "patient_id": timeline_patient_id,
                        "flare_features": timeline_ctx.flare_features,
                    },
                )

            # Emit timeline_probabilistic_differential event
            if timeline_ctx.diagnostic_landscape:
                yield sse(
                    "timeline_probabilistic_differential",
                    {
                        "patient_id": timeline_patient_id,
                        "diagnostic_landscape": (
                            timeline_ctx.diagnostic_landscape.to_normalized_dict()
                        ),
                    },
                )

            # Create timeline context document for injection
            timeline_doc = {
                "id": f"patient_timeline:{timeline_patient_id}",
                "source": "patient_timeline",
                "source_id": f"patient_timeline:{timeline_patient_id}",
                "title": f"Patient Timeline – {timeline_patient_id}",
                "text": timeline_ctx.context_text,
                "score": 1.0,
                "method": "timeline",
            }

            # Prepend timeline context to final_ctx
            final_ctx = [timeline_doc] + final_ctx

            yield sse(
                "patient_timeline_ctx",
                {
                    "source": "patient_timeline",
                    "patient_id": timeline_patient_id,
                    "event_count": timeline_ctx.event_count,
                },
            )

        except Exception as e:
            logger.exception("Failed to load patient timeline for %s", timeline_patient_id)
            yield sse(
                "status",
                {"status": "timeline_load_failed", "detail": str(e)},
            )
    

    # ---------------------------------------------------------------------------
    # 9d) Case-analog retrieval from MIMIC-4 notes (mimic4_note)
    # ---------------------------------------------------------------------------
    case_analog_docs: List[Dict[str, Any]] = []

    # Only do this for question types where analogs are particularly useful
    if question_type in CASE_ANALOG_QUESTION_TYPES:
        yield sse(
            "status",
            {
                "status": "retrieving_case_analogs",
                "source": CASE_ANALOG_SOURCE,
            },
        )

        try:
            # Simple ANN-only retrieval to keep things cheap and lean
            ann_rows = await search_source_ann(
                pool=pool,
                source=CASE_ANALOG_SOURCE,
                q_vec_literal=q_vec_literal,
                limit=CASE_ANALOG_K,
            )

            if ann_rows:
                # SSE summary for UI / telemetry
                yield sse(
                    "case_analogs",
                    {
                        "source": CASE_ANALOG_SOURCE,
                        "matches": [
                            {
                                "id": r["id"],
                                "source": r["source"],
                                "source_id": r.get("source_id") or "",
                                "title": r.get("title", ""),
                                "score": float(r.get("score") or 0.0),
                                "method": "case_analog",
                            }
                            for r in ann_rows
                        ],
                    },
                )

                # Convert into context docs appended after router+timeline+guidelines
                for r in ann_rows:
                    case_analog_docs.append(
                        {
                            "id": r["id"],
                            "source": r.get("source", CASE_ANALOG_SOURCE),
                            "source_id": r.get("source_id"),
                            "title": (r.get("title") or "").strip()
                            or "Case analog from MIMIC-4 note",
                            "text": r.get("text", ""),
                            "score": float(r.get("score") or 0.0),
                            "method": "case_analog",
                        }
                    )

        except Exception as e:
            logger.exception("case analog retrieval failed for %s", CASE_ANALOG_SOURCE)
            yield sse(
                "status",
                {"status": "case_analog_error", "detail": str(e)},
            )

    # Append case analogs at the end of the fused context to avoid drowning guidelines/timeline
    if case_analog_docs:
        final_ctx = final_ctx + case_analog_docs

    # ---------------------------------------------------------------------------
    # 9e) EoH patient_state – inject numeric module outputs (if available)
    # ---------------------------------------------------------------------------
    # Priority order:
    # 1) Explicit patient_state JSON passed as query param
    # 2) If a timeline_patient_id is provided, try to load eoh.patient_state from DB
    eoh_patient_state_doc = None

    # a) explicit param
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

    # b) DB snapshot (only if no explicit JSON was passed and we have a patient_id)
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

    # Prepend patient_state to context if we have it
    if eoh_patient_state_doc is not None:
        final_ctx = [eoh_patient_state_doc] + final_ctx

    # Valyu context accounting (unchanged)
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

    # Debug mode: emit full context text for deep debugging
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

    citations = build_citations(final_ctx)

    # ---------------------------------------------------------------------------
    # 10) with_llm == False -> just metadata
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
    # 11) LLM streaming with EoH-routed system prompt
    # ---------------------------------------------------------------------------
    yield sse("phase_start", {"source": "fusion", "method": "llm"})
    yield sse("status", {"status": "generating_eoh_answer"})

    # Accumulate answer text for post-hoc evidence mapping
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

            # Best-effort accumulation: we assume the SSE "data" payload
            # is a JSON string with a "text" or "delta" field for content.
            try:
                if ev.get("event", "").startswith("llm"):
                    data_str = ev.get("data", "")
                    if data_str:
                        payload = json.loads(data_str)
                        # Adjust these keys if your stream_llm_events format differs
                        chunk = (
                            payload.get("text")
                            or payload.get("delta")
                            or payload.get("content")
                            or ""
                        )
                        if isinstance(chunk, str):
                            answer_buffer.append(chunk)
            except Exception:
                # Don't break streaming if parsing fails
                logger.debug("Failed to parse llm event payload for answer_buffer", exc_info=True)

            yield ev
    except Exception as e:
        logger.exception("Error during EoH LLM streaming")
        yield sse(
            "error",
            {"error": "llm_failed", "detail": str(e)},
        )

    yield sse("phase_end", {"source": "fusion", "method": "llm"})

    # Build citations as before
    yield sse("citations", {"citations": citations})

    # -----------------------------------------------------------------------
    # Evidence-to-claim mapping (post-hoc, optional best-effort)
    # -----------------------------------------------------------------------
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
    limit: int = Query(12, ge=1, le=64),
    ctx_k: int = Query(24, ge=1, le=128),
    valyu_k: int = Query(
        0,
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
        0,
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
        0,
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
        0,
        ge=0,
        le=1,
        description="1=enable Valyu research context (PubMed, etc.) for this query",
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
        ):
            yield ev

    return EventSourceResponse(event_gen(), media_type="text/event-stream")
