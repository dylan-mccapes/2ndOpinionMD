# server/api/rag_stream_routes.py

import asyncio
import json
import logging
import os
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional, Tuple

import asyncpg
import httpx
from fastapi import APIRouter, Depends, Query, Request
from openai import OpenAI
from sse_starlette.sse import EventSourceResponse

from . import valyu_client
from .stream_config import (
    BASE_RRF_K,
    CHAT_MODEL,
    CODING_DEFAULT_SOURCES,
    CODE_SOURCES,
    EMBED_MODEL,
    MAX_CONTEXT_CHARS,
    ETHOS_SOURCE_NAME,
    is_ra_query,
)

from .stream_gating import apply_code_row_filter, apply_source_gating

# Minimum per-source retrieval depth for code sources in coding_mode.
# If the incoming `limit` is smaller than this, code sources will use this instead.
CODE_MIN_LIMIT = int(os.getenv("CODE_MIN_LIMIT", "32"))

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag-stream"])

client = OpenAI()

# ---------------------------------------------------------------------------
# Group toggles and defaults
# ---------------------------------------------------------------------------

# Enable/disable internal groups via env flags
USE_CODE_SOURCES = os.getenv("RAG_USE_CODES", "1") != "0"
USE_GUIDELINE_SOURCES = os.getenv("RAG_USE_GUIDELINES", "1") != "0"
USE_REST_SOURCES = os.getenv("RAG_USE_REST", "1") != "0"

# Default k per group (can be overridden via env)
CODE_K_DEFAULT = int(os.getenv("RAG_K_CODES", "32"))
GUIDE_K_DEFAULT = int(os.getenv("RAG_K_GUIDELINES", "4"))
# Rest uses ctx_k passed into build_fused_context / _event_generator

# Very light-weight heuristic for guideline sources
_GUIDELINE_EXACT = {
    "acr_ra_2021",
    "acr_ild_2023",
    "eular_ra_2022",
    "va_guidelines",
    "nice",
    "who_eml",
    "who_committee",
}
_GUIDELINE_PREFIXES = ("acr_", "eular_", "nice_", "who_", "guideline_")


def _is_guideline_source(src: str) -> bool:
    s = (src or "").lower()
    if s in _GUIDELINE_EXACT:
        return True
    return any(s.startswith(pfx) for pfx in _GUIDELINE_PREFIXES)


def _classify_internal_source(src: str) -> str:
    """
    Classify internal (DB) sources into one of:
      - 'code'       : ICD, SNOMED, RxNorm, etc.
      - 'guideline'  : ACR/EULAR/VA/NICE/WHO-style docs
      - 'rest'       : everything else
    """
    if src in CODE_SOURCES:
        return "code"
    if _is_guideline_source(src):
        return "guideline"
    return "rest"


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------


def sse(event: str, payload: Dict[str, Any]) -> Dict[str, str]:
    return {
        "event": event,
        "data": json.dumps(payload, default=str),
    }


# ---------------------------------------------------------------------------
# Result normalization / fusion
# ---------------------------------------------------------------------------


def normalize_row(
    row: Dict[str, Any],
    source: Optional[str] = None,
    method: Optional[str] = None,
) -> Dict[str, Any]:
    rid = (
        row.get("id")
        or row.get("uid")
        or row.get("pmid")
        or row.get("pubmed_id")
        or row.get("doc_id")
    )

    if rid is None:
        rid = f"auto-{hash(json.dumps(row, default=str))}"

    src = source or row.get("source") or "unknown"

    return {
        "id": rid,
        "source": src,
        "source_id": row.get("source_id"),
        "title": row.get("title") or "",
        "text": row.get("text") or row.get("abstract") or "",
        "meta": row.get("meta") or row,
        "score": float(row.get("score", 0.0)),
        "method": method or row.get("method"),
    }


def rrf_fuse(
    results_by_source: Dict[str, List[Dict[str, Any]]],
    k: int,
    base: float = 60.0,
) -> List[Dict[str, Any]]:
    scores: Dict[Tuple[str, Any], float] = {}
    rows_for_key: Dict[Tuple[str, Any], Dict[str, Any]] = {}

    for src, rows in results_by_source.items():
        for rank, row in enumerate(rows):
            norm = normalize_row(row, source=src)
            key = (norm["source"], norm["id"])
            rrf_score = 1.0 / (base + rank)
            scores[key] = scores.get(key, 0.0) + rrf_score
            rows_for_key[key] = norm

    fused = sorted(
        rows_for_key.values(),
        key=lambda r: scores[(r["source"], r["id"])],
        reverse=True,
    )
    return fused[:k]


def build_fused_context(
    results_by_source: Dict[str, List[Dict[str, Any]]],
    k: int,
    coding_mode: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fuse internal sources for final context using 3 groups:

      - codes      : CODE_SOURCES (ICD, SNOMED, RxNorm, LOINC, etc.)
      - guidelines : ACR/EULAR/VA/NICE/WHO, etc.
      - rest       : everything else (notes, lab items, etc.)

    Defaults:
      - codes      : k = CODE_K_DEFAULT (env RAG_K_CODES, default 8)
      - guidelines : k = GUIDE_K_DEFAULT (env RAG_K_GUIDELINES, default 4)
      - rest       : k = ctx_k (the 'k' argument)

    Groups can be toggled via env flags:
      - RAG_USE_CODES
      - RAG_USE_GUIDELINES
      - RAG_USE_REST

    Final order is always:
      1) codes (if enabled)
      2) guidelines (if enabled)
      3) rest (if enabled)

    'coding_mode' is still honored upstream via apply_code_row_filter
    and downstream by format_context_for_llm for labeling, but the
    group k logic applies regardless.
    """
    if not results_by_source:
        return []

    code_by_source: Dict[str, List[Dict[str, Any]]] = {}
    guideline_by_source: Dict[str, List[Dict[str, Any]]] = {}
    rest_by_source: Dict[str, List[Dict[str, Any]]] = {}

    for src, rows in results_by_source.items():
        kind = _classify_internal_source(src)
        if kind == "code":
            code_by_source[src] = rows
        elif kind == "guideline":
            guideline_by_source[src] = rows
        else:
            rest_by_source[src] = rows

    # Per-group k (with env overrides)
    k_codes = max(0, CODE_K_DEFAULT)
    k_guidelines = max(0, GUIDE_K_DEFAULT)
    k_rest = max(0, k)

    fused_codes: List[Dict[str, Any]] = []
    fused_guidelines: List[Dict[str, Any]] = []
    fused_rest: List[Dict[str, Any]] = []

    if USE_CODE_SOURCES and code_by_source:
        fused_codes = rrf_fuse(code_by_source, k=k_codes)

    if USE_GUIDELINE_SOURCES and guideline_by_source:
        fused_guidelines = rrf_fuse(guideline_by_source, k=k_guidelines)

    if USE_REST_SOURCES and rest_by_source and k_rest > 0:
        fused_rest = rrf_fuse(rest_by_source, k=k_rest)

    fused = fused_codes + fused_guidelines + fused_rest

    logger.info(
        "FUSED_CONTEXT sizes: codes=%d, guidelines=%d, rest=%d, total=%d",
        len(fused_codes),
        len(fused_guidelines),
        len(fused_rest),
        len(fused),
    )

    return fused


def format_context_for_llm(
    ctx: Iterable[Dict[str, Any]],
    coding_mode: bool = False,
) -> str:
    """
    Build a compact text context for the LLM.

    In coding_mode:
      - Code sources come first, then guidelines, then rest.
      - Code IDs are made explicit (RxNorm CUI=..., ICD-10-CM=..., etc.).
      - Truncation by MAX_CONTEXT_CHARS happens *after* reordering so
        code rows are maximally preserved.

    In non-coding mode:
      - Rows keep their incoming order; we still enforce MAX_CONTEXT_CHARS.
    """
    from .stream_config import CODE_SOURCES as _CODE_SOURCES

    rows = list(ctx)

    # 1) In coding_mode, put code sources first, then guidelines, then rest.
    if coding_mode:
        code_rows: List[Dict[str, Any]] = []
        guideline_rows: List[Dict[str, Any]] = []
        rest_rows: List[Dict[str, Any]] = []

        for r in rows:
            src = r.get("source") or "unknown"
            if src in _CODE_SOURCES:
                code_rows.append(r)
            elif _is_guideline_source(src):
                guideline_rows.append(r)
            else:
                rest_rows.append(r)

        ordered_rows = code_rows + guideline_rows + rest_rows
    else:
        ordered_rows = rows

    blocks: List[str] = []
    total_len = 0
    max_chars = MAX_CONTEXT_CHARS

    for i, row in enumerate(ordered_rows, start=1):
        src = row.get("source", "unknown")
        title = row.get("title") or ""
        text = (row.get("text") or "").strip()
        source_id = row.get("source_id")

        source_id_str = f" ({source_id})" if source_id else ""

        if coding_mode:
            # Label context kind for the model
            kind = "CODE_CONTEXT" if src in _CODE_SOURCES else "CLINICAL_CONTEXT"

            # Make codes *very* explicit for the model
            if src == "rxnorm" and source_id:
                code_label = f"RxNorm CUI={source_id}"
            elif src == "icd11" and source_id:
                code_label = f"ICD-11={source_id}"
            elif src == "icd10cm" and source_id:
                code_label = f"ICD-10-CM={source_id}"
            elif src == "snomed" and source_id:
                code_label = f"SNOMED CT={source_id}"
            else:
                code_label = source_id_str.strip(" ()") if source_id else ""

            code_suffix = f" [{code_label}]" if code_label else ""

            block = (
                f"[{i}] kind={kind} {src}{source_id_str}{code_suffix} | "
                f"{title} | {text}"
            )
        else:
            block = f"[{i}] {src}{source_id_str} | {title} | {text}"

        # +2 for the separating "\n\n"
        if total_len + len(block) + 2 > max_chars:
            blocks.append("[truncated]")
            break

        blocks.append(block)
        total_len += len(block) + 2

    context_str = "\n\n".join(blocks)

    # Debug logging to confirm RxNorm / codes really made it in
    logger.info("LLM CONTEXT FINAL LEN=%s", len(context_str))
    logger.info(
        "LLM CONTEXT FINAL TAIL:\n%s",
        "\n".join(context_str.splitlines()[-20:]),
    )

    return context_str


# ---------------------------------------------------------------------------
# Embedding helpers & PG pool
# ---------------------------------------------------------------------------


async def embed_query(q: str) -> List[float]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=[q])
    return resp.data[0].embedding  # type: ignore[no-any-return]


def embedding_to_vector_literal(vec: List[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


_PG_POOL: Optional[asyncpg.Pool] = None


def _get_pg_dsn() -> str:
    sync_url = os.getenv("SYNC_DATABASE_URL")
    if sync_url:
        return sync_url

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        if "+asyncpg" in db_url:
            return db_url.replace("+asyncpg", "")
        if "+psycopg" in db_url:
            return db_url.replace("+psycopg", "")
        return db_url

    return "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"


async def resolve_pg_pool() -> asyncpg.Pool:
    global _PG_POOL
    if _PG_POOL is None:
        dsn = _get_pg_dsn()
        max_size = int(os.getenv("PGPOOL_MAX", "10"))
        logger.info("Creating asyncpg pool dsn=%s max_size=%s", dsn, max_size)
        _PG_POOL = await asyncpg.create_pool(dsn, min_size=1, max_size=max_size)
    return _PG_POOL


# ---------------------------------------------------------------------------
# DB Search Helpers (TS + ANN)
# ---------------------------------------------------------------------------


async def search_source_ts(
    pool: asyncpg.Pool,
    source: str,
    q: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Text-search retrieval.
    Uses rag_corpus.ts GIN index (ts) and filters by source.
    """
    sql = """
        SELECT id, source, source_id, title, text, meta,
               ts_rank(ts, plainto_tsquery($1)) AS score
        FROM rag_corpus
        WHERE source = $2
          AND ts @@ plainto_tsquery($1)
        ORDER BY score DESC
        LIMIT $3;
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, q, source, limit)

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "source": r["source"],
                "source_id": r["source_id"],
                "title": r["title"],
                "text": r["text"],
                "meta": r["meta"],
                "score": float(r["score"] or 0.0),
                "method": "ts",
            }
        )
    return out

async def search_source_ts_for_terms(
    pool: asyncpg.Pool,
    source: str,
    terms: List[str],
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Variant of text-search retrieval for code sources.

    Instead of plainto_tsquery(full_question), we run several smaller
    tsqueries (one per term) and then merge + re-rank results.

    This dramatically cuts noise for huge code corpora like RxNorm/SNOMED.
    """
    # Fallback: if we somehow have no terms, just behave like the normal TS.
    if not terms:
        return await search_source_ts(pool, source, " ".join(terms) or "", limit)

    sql = """
        SELECT id, source, source_id, title, text, meta,
               ts_rank(ts, plainto_tsquery($1)) AS score
        FROM rag_corpus
        WHERE source = $2
          AND ts @@ plainto_tsquery($1)
        ORDER BY score DESC
        LIMIT $3;
    """

    combined: Dict[Any, Dict[str, Any]] = {}

    # Simple heuristic: distribute the overall limit across terms
    per_term_limit = max(3, limit // max(1, len(terms)))

    async with pool.acquire() as conn:
        for term in terms:
            t = term.strip()
            if not t:
                continue
            rows = await conn.fetch(sql, t, source, per_term_limit)
            for r in rows:
                rid = r["id"]
                score = float(r["score"] or 0.0)
                existing = combined.get(rid)
                if existing is None or score > existing["score"]:
                    combined[rid] = {
                        "id": r["id"],
                        "source": r["source"],
                        "source_id": r["source_id"],
                        "title": r["title"],
                        "text": r["text"],
                        "meta": r["meta"],
                        "score": score,
                        "method": "ts_terms",
                    }

    merged = sorted(
        combined.values(),
        key=lambda r: r.get("score", 0.0),
        reverse=True,
    )
    return merged[:limit]

async def search_source_ann(
    pool: asyncpg.Pool,
    source: str,
    q_vec_literal: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """
    HNSW / ivfflat vector ANN search for the given source.
    Assumes partial index:
        CREATE INDEX ... WHERE source='xyz' AND embedding IS NOT NULL;
    """
    sql = """
        SELECT id, source, source_id, title, text, meta,
               1 - (embedding <=> $1::vector) AS score
        FROM rag_corpus
        WHERE source = $2
          AND embedding IS NOT NULL
        ORDER BY embedding <=> $1::vector
        LIMIT $3;
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, q_vec_literal, source, limit)

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "source": r["source"],
                "source_id": r["source_id"],
                "title": r["title"],
                "text": r["text"],
                "meta": r["meta"],
                "score": float(r["score"] or 0.0),
                "method": "ann",
            }
        )
    return out


# ---------------------------------------------------------------------------
# Valyu integration
# ---------------------------------------------------------------------------


async def fetch_valyu_results(
    q: str,
    mode: str,
    limit: int,
    raw: bool,
    sources: Optional[str],
    boost: float,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Bridge between ask_stream/coding_stream and server/api/valyu_client.py.

    - mode: "search" or "answer"
    - limit: how many results to retrieve from Valyu
    - raw: if true, ask Valyu to include full contents (when supported)
    - sources: optional CSV like "valyu/valyu-pubmed,valyu/another-set"
    - boost: currently unused here, but kept in signature for future tuning
    """
    # Parse included_sources into the shape valyu_client expects
    included_sources: Optional[List[str]] = None
    if sources:
        included_sources = [s.strip() for s in sources.split(",") if s.strip()]

    try:
        vy = await valyu_client.call_valyu(
            mode=mode or "search",
            q=q,
            k=limit,
            included_sources=included_sources,
            # These map onto the valyu_client.search / answer options
            return_contents=bool(raw),
            fast_mode=(mode == "search"),
        )
    except Exception as e:
        logger.exception("Valyu call failed")
        return {}

    # valyu_client._post already normalizes errors into {"success": False, ...}
    if not vy.get("success"):
        logger.warning("Valyu returned error payload: %r", vy)
        return {}

    hits = vy.get("results", [])
    if not isinstance(hits, list):
        logger.warning("Unexpected Valyu results shape: %r", type(hits))
        return {}

    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for h in hits:
        src_key = "valyu_pubmed"

        base = {
            "id": h.get("id"),
            "source": src_key,
            "title": h.get("title") or "",
            "text": h.get("snippet") or "",
            "meta": h,
            "score": float(h.get("score", 0.0) or 0.0),
        }

        norm = normalize_row(base, source=src_key, method="valyu")
        grouped.setdefault(src_key, []).append(norm)

    # Sort high→low and cap per-source limit
    for src, rows in grouped.items():
        rows.sort(key=lambda r: r.get("score", 0.0), reverse=True)
        grouped[src] = rows[:limit]

    return grouped


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------


def build_llm_messages(q: str, ctx_str: str) -> List[Dict[str, Any]]:
    """
    Swap this to your existing 2ndOpinionMD system prompt as needed.
    """
    return [
        {
            "role": "system",
            "content": (
                "You are 2ndOpinionMD's retrieval-augmented medical assistant. "
                "Use ONLY the provided context to answer, citing sections by index "
                "like [1], [2], etc. If the answer is not clearly supported, say "
                "you don't know and suggest follow-up questions or tests."
            ),
        },
        {
            "role": "user",
            "content": f"Question:\n{q.strip()}",
        },
        {
            "role": "assistant",
            "content": (
                "Here is the retrieved context from medical corpora and guidelines:\n\n"
                f"{ctx_str}\n\n"
                "Now I will answer the question strictly based on this context."
            ),
        },
    ]

async def extract_code_terms(q: str) -> List[str]:
    """
    Use the chat model to extract a small list of code-oriented keywords
    (diagnoses, meds, labs, procedures) from the user's question.

    The goal is to drive ts-search over code sources (ICD, SNOMED, RxNorm, LOINC)
    with focused terms instead of the entire natural-language question.

    RA queries get a conservative fallback seed list to stabilize retrieval.
    """
    system_msg = {
        "role": "system",
        "content": (
            "You are assisting a medical coding system.\n"
            "Given a clinician's question, extract at most 8 short keywords "
            "or phrases that are best suited to search structured code systems "
            "such as ICD-10-CM, ICD-11, SNOMED CT, RxNorm, and LOINC.\n\n"
            "Focus on:\n"
            "- diseases and syndromes\n"
            "- medications (generic names only)\n"
            "- lab tests / measurements\n"
            "- procedures or major clinical entities\n\n"
            "Return a JSON object of the form:\n"
            "{ \"terms\": [\"term1\", \"term2\", ...] }\n"
            "Do not include commentary or any other keys."
        ),
    }
    user_msg = {
        "role": "user",
        "content": q.strip(),
    }

    out: List[str] = []
    seen: set[str] = set()

    try:
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[system_msg, user_msg],
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        if raw:
            data = json.loads(raw)
            terms = data.get("terms") or []
            for t in terms:
                if not isinstance(t, str):
                    continue
                tt = t.strip()
                if not tt:
                    continue
                key = tt.lower()
                if key in seen:
                    continue
                seen.add(key)
                out.append(tt)
    except Exception:
        logger.exception("extract_code_terms failed")

    # RA-specific conservative fallback: make sure RA queries always have
    # strong seed terms for code vocabularies even if the model was weak.
    try:
        if is_ra_query(q):
            ra_seeds = [
                "rheumatoid arthritis",
                "seropositive rheumatoid arthritis",
                "erosive rheumatoid arthritis",
            ]
            for seed in ra_seeds:
                key = seed.lower()
                if key not in seen:
                    seen.add(key)
                    out.append(seed)
    except Exception:
        # Never let RA detection explode the whole pipeline
        logger.exception("RA fallback seeds in extract_code_terms failed")

    return out

def stream_llm_events(
    q: str,
    context_items: List[Dict[str, Any]],
    llm_mode: str,
    coding_mode: bool = False,
) -> Iterable[Dict[str, str]]:
    """
    Stream LLM output as SSE events.

    Modes:
      - llm_mode == "delta":
          event: llm_delta  { "text": "<small token-ish piece>" }
      - llm_mode == "chunk" (default):
          event: llm_chunk  { "text": "<sentence-ish chunk>" }

    In BOTH modes, we also emit:
      event: llm_done { "text": "<full answer>" }

    NOTE:
      - coding_mode is passed through to format_context_for_llm so that
        CODE_CONTEXT vs CLINICAL_CONTEXT labels are preserved for /coding_stream.
    """
    ctx_str = format_context_for_llm(context_items, coding_mode=coding_mode)
    messages = build_llm_messages(q, ctx_str)

    mode = (llm_mode or "chunk").lower()
    if mode not in ("chunk", "delta"):
        mode = "chunk"

    stream = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        stream=True,
    )

    full_pieces: List[str] = []
    buf = ""

    def flush_chunk():
        nonlocal buf
        text = buf.strip()
        if text:
            yield sse("llm_chunk", {"text": text})
        buf = ""

    for chunk in stream:
        choice = chunk.choices[0]
        delta = choice.delta
        content = getattr(delta, "content", None)
        if not content:
            continue

        if isinstance(content, str):
            pieces = [content]
        else:
            pieces = []
            try:
                for part in content:
                    text = getattr(part, "text", None) or getattr(part, "value", None)
                    if text:
                        pieces.append(text)
            except TypeError:
                continue

        for piece in pieces:
            full_pieces.append(piece)

            if mode == "delta":
                yield sse("llm_delta", {"text": piece})
            else:
                buf += piece
                if any(
                    buf.endswith(end)
                    for end in [". ", ".\n", "?\n", "!\n", ".\n\n"]
                ):
                    for ev in flush_chunk():
                        yield ev
                elif len(buf) > 600:
                    for ev in flush_chunk():
                        yield ev

    if mode == "chunk" and buf.strip():
        for ev in flush_chunk():
            yield ev

    full_text = "".join(full_pieces).strip()
    yield sse("llm_done", {"text": full_text})


# ---------------------------------------------------------------------------
# Citations helpers
# ---------------------------------------------------------------------------


def _classify_citation_kind(row: Dict[str, Any]) -> str:
    """
    Classify a context row into a citation kind:
      - 'valyu'     : Valyu PubMed-style hits
      - 'ethos'     : Ethos of Health model / preprint chunks
      - 'guideline' : everything else (guidelines, codes, ontologies, etc.)
    """
    source = (row.get("source") or "").lower()
    method = (row.get("method") or "").lower()

    if source.startswith("valyu") or method == "valyu":
        return "valyu"
    if source in {"ethos_model", "ethos"}:
        return "ethos"
    return "guideline"


def build_citations(context_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build a citations list from the final context:

    - Each context block [i] becomes a citation with index = i.
    - Valyu citations are grouped first, then Ethos, then guidelines/other.
    - `extra.meta` carries through the row's meta so codes/etc. can be surfaced
      by the UI or report generator.
    """
    raw_citations: List[Dict[str, Any]] = []

    for i, row in enumerate(context_items, start=1):
        kind = _classify_citation_kind(row)
        src = row.get("source", "unknown")
        meta = row.get("meta") or {}
        method = row.get("method")

        if kind == "valyu":
            key = (
                meta.get("pmcid")
                or meta.get("pmid")
                or meta.get("pubmed_id")
                or meta.get("id")
                or row.get("id")
            )
        elif kind == "ethos":
            key = f"{src}:{row.get('id')}"
        else:
            key = f"{src}:{row.get('id')}"

        raw_citations.append(
            {
                "index": i,
                "kind": kind,
                "source": src,
                "key": str(key),
                "title": row.get("title") or "",
                "extra": {
                    "method": method,
                    "meta": meta,
                },
            }
        )

    kind_order = {"valyu": 0, "ethos": 1, "guideline": 2}
    raw_citations.sort(key=lambda c: (kind_order.get(c["kind"], 99), c["index"]))
    return raw_citations


# ---------------------------------------------------------------------------
# Core event generator (used by /ask_stream and /coding_stream)
# ---------------------------------------------------------------------------


async def _event_generator(
    request: Request,
    q: str,
    db_sources: List[str],
    limit: int,
    ctx_k: int,
    valyu_k: int,
    with_llm: bool,
    llm_mode: str,
    use_valyu_bool: bool,
    valyu_mode: str,
    valyu_raw_bool: bool,
    valyu_sources: Optional[str],
    valyu_boost: float,
    pool: Any,
    coding_mode: bool = False,
    use_ethos_bool: bool = False,
) -> AsyncIterator[Dict[str, str]]:
    # Hard cap on Valyu context size
    VALYU_K_MAX = 4
    requested_valyu_k = valyu_k
    valyu_k = max(0, min(valyu_k, VALYU_K_MAX))

    # 0) Initial event
    yield sse(
        "start",
        {
            "q": q,
            "limit": limit,
            "ctx_k": ctx_k,
            "sources": db_sources,
            "with_llm": with_llm,
            "use_valyu": use_valyu_bool,
            "valyu_k": valyu_k,
            "valyu_k_requested": requested_valyu_k,
            "use_ethos": use_ethos_bool,
        },
    )

    # 0.1) Soft warning if the query is "wide"
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

    # 1.1) In coding_mode, extract code-oriented terms once, for use by all code sources.
    code_terms: List[str] = []
    if coding_mode:
        yield sse("status", {"status": "extracting_code_terms"})
        code_terms = await extract_code_terms(q)
        if code_terms:
            yield sse("code_terms", {"terms": code_terms})
    
    # RA-aware heuristic to support rheumatoid arthritis coding queries.
    # This flag is reused for TS fallbacks per code source.
    try:
        is_ra = is_ra_query(q)
    except Exception:
        logger.exception("is_ra_query failed; defaulting to False")
        is_ra = False

    # 2) Retrieve per source (TS + ANN)
    yield sse("status", {"status": "retrieving_candidates"})
    results_by_source: Dict[str, List[Dict[str, Any]]] = {}
    valyu_matches: List[Dict[str, Any]] = []

    for src in db_sources:
        # Allow deeper retrieval for code sources in coding_mode
        per_source_limit = limit
        if coding_mode and src in CODE_SOURCES:
            per_source_limit = max(limit, CODE_MIN_LIMIT)

        # TS phase
        yield sse("phase_start", {"source": src, "method": "ts"})
        try:
            if coding_mode and src in CODE_SOURCES:
                # Prefer focused code_terms when available.
                if code_terms:
                    ts_rows = await search_source_ts_for_terms(
                        pool,
                        source=src,
                        terms=code_terms,
                        limit=per_source_limit,
                    )
                # RA-specific fallback for code sources when we have no code_terms.
                elif is_ra:
                    ra_terms = [
                        "rheumatoid arthritis",
                        "rheumatoid",
                        "arthritis",
                    ]
                    ts_rows = await search_source_ts_for_terms(
                        pool,
                        source=src,
                        terms=ra_terms,
                        limit=per_source_limit,
                    )
                else:
                    # Fail back to the full-question TS only if not clearly RA.
                    ts_rows = await search_source_ts(pool, src, q, per_source_limit)
            else:
                ts_rows = await search_source_ts(pool, src, q, per_source_limit)
        except Exception as e:
            logger.exception("TS search failed for source=%s", src)
            ts_rows = []
            yield sse(
                "status",
                {"status": "ts_error", "source": src, "detail": str(e)},
            )
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

        # ANN phase
        yield sse("phase_start", {"source": src, "method": "ann"})
        try:
            ann_rows = await search_source_ann(pool, src, q_vec_literal, per_source_limit)
        except Exception as e:
            logger.exception("ANN search failed for source=%s", src)
            ann_rows = []
            yield sse(
                "status",
                {"status": "ann_error", "source": src, "detail": str(e)},
            )
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

        combined: Dict[Any, Dict[str, Any]] = {}
        for r in ts_rows + ann_rows:
            norm = normalize_row(r, source=src)
            combined[norm["id"]] = norm

        combined_rows = list(combined.values())

        # Extra de-noising for code sources in coding mode
        if coding_mode:
            combined_rows = apply_code_row_filter(combined_rows, q, src)

        results_by_source[src] = combined_rows

        if await request.is_disconnected():
            return

    raw_source_count = len(results_by_source)

    # 3) Heuristic source gating, with optional Ethos + Code force-keep.
    extra_always_keep: Optional[set[str]] = None
    if use_ethos_bool:
        extra_always_keep = {ETHOS_SOURCE_NAME}

    # In coding_mode, never allow gating to drop authoritative code sources.
    if coding_mode:
        code_keep = set(CODE_SOURCES)
        if extra_always_keep is None:
            extra_always_keep = code_keep
        else:
            extra_always_keep |= code_keep

    gated_results_by_source, gating_info = apply_source_gating(
        results_by_source,
        query=q,
        extra_always_keep=extra_always_keep,
    )

    yield sse("gating", gating_info)

    if await request.is_disconnected():
        return

    # 4) Valyu (optional, guaranteed tail, but hard-capped by valyu_k <= 4)
    if use_valyu_bool and valyu_k > 0:
        yield sse("status", {"status": "valyu_fetch"})
        try:
            valyu_limit = valyu_k
            valyu_by_source = await fetch_valyu_results(
                q=q,
                mode=valyu_mode,
                limit=valyu_limit,
                raw=valyu_raw_bool,
                sources=valyu_sources,
                boost=valyu_boost,
            )
        except Exception as e:
            logger.exception("Valyu fetch failed")
            valyu_by_source = {}
            yield sse(
                "status",
                {"status": "valyu_error", "detail": str(e)},
            )

        if valyu_by_source:
            flat_matches: List[Dict[str, Any]] = []
            for v_src, rows in valyu_by_source.items():
                flat_matches.extend(rows)
                valyu_matches.extend(rows)

            yield sse(
                "matches",
                {
                    "phase": "valyu",
                    "source": "valyu",
                    "matches": [
                        {
                            "id": r["id"],
                            "source": r["source"],
                            "title": r.get("title", ""),
                            "score": r.get("score", 0.0),
                            "method": r.get("method", "valyu"),
                        }
                        for r in flat_matches
                    ],
                },
            )

        if await request.is_disconnected():
            return

    # 5) Fuse internal contexts and append Valyu tail
    yield sse("status", {"status": "fusing_context"})

    internal_ctx = build_fused_context(
        gated_results_by_source,
        k=ctx_k,
        coding_mode=coding_mode,
    )

    # Valyu tail: always appended independently of internal gating / RRF.
    if use_valyu_bool and valyu_k > 0 and valyu_matches:
        valyu_tail = valyu_matches[:valyu_k]
    else:
        valyu_tail = []

    final_ctx = internal_ctx + valyu_tail
    valyu_ctx_count = len(valyu_tail)

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

    # 6) LLM streaming (optional)
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
                    "with_llm": with_llm_bool,
                    "use_ethos": use_ethos_bool,
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
                    "with_llm": with_llm_bool,
                    "use_ethos": use_ethos_bool,
                }
            },
        )
        return

    yield sse("phase_start", {"source": "fusion", "method": "llm"})
    yield sse("status", {"status": "generating_answer"})

    try:
        for ev in stream_llm_events(q, final_ctx, llm_mode, coding_mode=coding_mode):
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
                    "use_ethos": use_ethos_bool,
                }
            },
        )
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
                "use_ethos": use_ethos_bool,
            }
        },
    )
