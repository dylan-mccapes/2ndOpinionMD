# server/api/rag_stream_custom_endpoints.py

from typing import Optional, List, Any, AsyncIterator, Dict
import json
import logging

from fastapi import APIRouter, Query, Request, Depends
from sse_starlette.sse import EventSourceResponse

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
)

from .stream_gating import apply_source_gating, apply_code_row_filter
from .stream_router import route_coding_sources, route_coding_sources_strict, CodingRouterPlan

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
    if len(db_sources) > 8:
        warnings.append(
            f"High number of sources requested ({len(db_sources)}). "
            "This may dilute relevance; consider narrowing the 'sources=' list."
        )
    if limit > 15:
        warnings.append(
            f"High per-source limit={limit}. This may increase noise; "
            "consider a smaller 'limit' for sharper focus."
        )
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
        router_plan = await route_coding_sources(
            q=q,
            code_terms=[],
            candidate_sources=db_sources,
            valyu_context=(valyu_matches if valyu_matches else None),
        )
    except Exception as e:
        logger.exception("route_coding_sources failed; using all db_sources")
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

    # 10) LLM streaming
    yield sse("phase_start", {"source": "fusion", "method": "llm"})
    yield sse("status", {"status": "generating_answer"})

    try:
        for ev in stream_llm_events(
            q,
            final_ctx,
            llm_mode,
            coding_mode=False,
            chat_model=CHAT_MODEL_GUIDELINES,
            answer_mode=answer_mode,
            phase="reasoning",
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
    if len(coding_only_sources) > 8:
        warnings.append(
            f"High number of coding sources ({len(coding_only_sources)}). "
            "This may dilute relevance."
        )
    if limit > 15:
        warnings.append(
            f"High per-source limit={limit}. This may increase noise; "
            "consider a smaller 'limit' for sharper focus."
        )
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

# ---------------------------------------------------------------------------
# /eoh_stream — thin wrapper around ask_stream_event_generator with EoH mode
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
    pool: Any = Depends(resolve_pg_pool),
) -> EventSourceResponse:
    """
    EoH / Ethos-of-Health mode.

    Thin wrapper around ask_stream_event_generator with:
      - Forces Ethos source into context via use_ethos=True
      - Uses answer_mode="eoh" for EoH-specific system prompt
      - Defaults to guideline-ish sources + ETHOS_SOURCE_NAME
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
            use_ethos=True,
            pool=pool,
            answer_mode="eoh",
        ):
            yield ev

    return EventSourceResponse(event_gen(), media_type="text/event-stream")
