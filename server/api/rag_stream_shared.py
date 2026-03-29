# server/api/rag_stream_shared.py — shared infrastructure for all 4 streaming modes
# Imported by rag_stream_ask, rag_stream_coding, rag_stream_eoh, rag_stream_detective.
# DO NOT add route handlers here.

# server/api/rag_stream_shared.py
# Shared infrastructure: imports, constants, QA grader, router object.
# All mode modules import from here. No route handlers.

from typing import Optional, List, Any, AsyncIterator, Dict
import json
import logging
import time
import asyncio
import os
from datetime import datetime, date

from fastapi import APIRouter, Query, Request, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse

# Privacy: Request models + anonymization agent
from .rag_stream_models import (
    AskStreamRequest,
    CodingStreamRequest,
    EohStreamRequest,
    EohDetectiveStreamRequest,
)
from .anon_query_agent import anonymize_query_for_logging
from server.timeline.engine import TimelineEngine, load_patient_timeline
from server.timeline.engine import TimelineContext
from server.eoh.timeline_summarizer import summarize_timeline_for_eoh, TimelineSummaries, SUMMARY_MAX_CHARS
from server.eoh.graph_enrichment import enrich_graph_opportunistic
from server.eoh.patient_timeline_vision import (
    PatientTimelineVision,
    load_timeline_vision,
    save_timeline_vision,
    load_timeline_vision_pg,
    save_timeline_vision_pg,
    is_graph_ready_pg,
)
from server.eoh.patient_timeline_chart import (
    PatientTimelineChart,
    build_graph_context,
)
from server.llm.llm_client import chat_completion_async, embedding_async

timeline_engine = TimelineEngine()

from openai import OpenAI
import inspect
import anyio

_openai_client = OpenAI(timeout=60.0)

# Detective hardening defaults (override via env if needed)
DETECTIVE_PLANNER_TIMEOUT_S = int(os.getenv("DETECTIVE_PLANNER_TIMEOUT_S", "90"))
DETECTIVE_SUMMARIZER_TIMEOUT_S = int(os.getenv("DETECTIVE_SUMMARIZER_TIMEOUT_S", "180"))
DETECTIVE_STEP_IDLE_TIMEOUT_S = int(os.getenv("DETECTIVE_STEP_IDLE_TIMEOUT_S", "45"))
DETECTIVE_STEP_MAX_TIMEOUT_S = int(os.getenv("DETECTIVE_STEP_MAX_TIMEOUT_S", "900"))
DETECTIVE_ENRICH_TIMEOUT_S = int(os.getenv("DETECTIVE_ENRICH_TIMEOUT_S", "120"))
DETECTIVE_REPORT_TIMEOUT_S = int(os.getenv("DETECTIVE_REPORT_TIMEOUT_S", "180"))

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


