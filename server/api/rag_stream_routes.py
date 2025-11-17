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

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag-stream"])

# ---------------------------------------------------------------------------
# Constants / config knobs
# ---------------------------------------------------------------------------

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-4.1-mini"  # adjust to your current default

# How many total context chunks to give the LLM (internal corpora only)
BASE_RRF_K = 24

# Hard cap on context size passed to LLM (chars; rough guard vs token overflows)
MAX_CONTEXT_CHARS = 32_000

# Valyu configuration via environment (used by valyu_client)
VALYU_BASE_URL = os.getenv("VALYU_BASE_URL", "").strip()
VALYU_API_KEY = os.getenv("VALYU_API_KEY", "").strip()
VALYU_TIMEOUT = float(os.getenv("VALYU_TIMEOUT", "20.0"))

# Heuristic source-gating config
# These are intentionally conservative and fail-open if they drop everything.
SOURCE_GATING_ENABLED = bool(int(os.getenv("RAG_SOURCE_GATING_ENABLED", "1")))
MIN_DOCS_PER_SOURCE = int(os.getenv("RAG_MIN_DOCS_PER_SOURCE", "1"))
REL_SCORE_CUTOFF = float(os.getenv("RAG_REL_SCORE_CUTOFF", "0.35"))
ABS_SCORE_CUTOFF = float(os.getenv("RAG_ABS_SCORE_CUTOFF", "0.0"))
ALWAYS_KEEP_SOURCES = {
    s.strip()
    for s in os.getenv("RAG_ALWAYS_KEEP_SOURCES", "").split(",")
    if s.strip()
}

client = OpenAI()

# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------


def sse(event: str, payload: Dict[str, Any]) -> Dict[str, str]:
    """Helper to emit SSE events in the format EventSourceResponse expects."""
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
    """
    Normalize a DB row or external hit (e.g., Valyu) into a common shape.
    Expected keys:
      - id (or uid/pmid/pubmed_id/doc_id for Valyu-like rows)
      - source
      - title
      - text
      - meta (dict)
      - score (float, optional)
      - method ("ts" / "ann" / "valyu" for debugging)
    """
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
    """
    Reciprocal Rank Fusion across sources.

    Input:
      results_by_source: { source_key: [ranked rows...] }
    Output:
      top-k items across all sources.
    """
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
) -> List[Dict[str, Any]]:
    """
    Fuse all *internal* sources with RRF.

    IMPORTANT:
      - Valyu results are NOT included here.
      - They are appended later as an independent tail of size `valyu_k`
        using Valyu's own heuristic score / ranking.
    """
    if not results_by_source:
        return []
    return rrf_fuse(results_by_source, k=k)


def format_context_for_llm(ctx: Iterable[Dict[str, Any]]) -> str:
    """
    Turn fused context rows into a single prompt string.

    Each block is numbered [1], [2], ... in the same order as `final_ctx`,
    which is the same numbering used for citations (`index` field).
    """
    blocks: List[str] = []
    for i, row in enumerate(ctx, start=1):
        src = row.get("source", "unknown")
        title = row.get("title") or ""
        text = row.get("text") or ""
        blocks.append(
            f"[{i}] source={src} title={title!r}\n{text.strip()}\n"
            f"--- END [{i}] ---"
        )
    context_str = "\n\n".join(blocks)

    if len(context_str) > MAX_CONTEXT_CHARS:
        context_str = context_str[:MAX_CONTEXT_CHARS] + "\n[truncated]"
    return context_str


# ---------------------------------------------------------------------------
# Heuristic-based source gating
# ---------------------------------------------------------------------------


def summarize_source_scores(
    rows: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Compute simple statistics over scores for a source, for gating.

    Returns:
      {
        "n": <count>,
        "top1": <best score>,
        "top3_mean": <mean of up to top-3 scores>,
        "median": <median score>,
      }
    or None if rows empty.
    """
    if not rows:
        return None

    scores = sorted(
        [float(r.get("score", 0.0) or 0.0) for r in rows],
        reverse=True,
    )
    n = len(scores)
    top1 = scores[0]
    top3_mean = sum(scores[:3]) / min(3, n)
    median = scores[n // 2]
    return {
        "n": n,
        "top1": top1,
        "top3_mean": top3_mean,
        "median": median,
    }


def apply_source_gating(
    results_by_source: Dict[str, List[Dict[str, Any]]],
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """
    Apply simple heuristics to drop obviously off-topic / weak sources.

    Heuristics (tunable by env):
      - If SOURCE_GATING_ENABLED == 0: keep everything, just report stats.
      - Require at least MIN_DOCS_PER_SOURCE rows for a source to be considered,
        unless the source is in ALWAYS_KEEP_SOURCES.
      - Compute per-source top1 score and global max(top1).
      - Keep a source if:
          * source in ALWAYS_KEEP_SOURCES, OR
          * (top1 / global_top1) >= REL_SCORE_CUTOFF, OR
          * (ABS_SCORE_CUTOFF > 0 and top1 >= ABS_SCORE_CUTOFF).
      - If all sources would be dropped, we fail-open and keep everything.

    Returns:
      (filtered_results_by_source, gating_info_dict)
      where gating_info_dict is suitable for logging / SSE debugging.
    """
    gating_info: Dict[str, Any] = {
        "enabled": SOURCE_GATING_ENABLED,
        "min_docs": MIN_DOCS_PER_SOURCE,
        "rel_cutoff": REL_SCORE_CUTOFF,
        "abs_cutoff": ABS_SCORE_CUTOFF,
        "always_keep": sorted(list(ALWAYS_KEEP_SOURCES)),
        "sources": {},
    }

    # Pre-compute stats
    stats_by_src: Dict[str, Optional[Dict[str, Any]]] = {
        src: summarize_source_scores(rows) for src, rows in results_by_source.items()
    }

    nonempty_stats = {
        src: st for src, st in stats_by_src.items() if st is not None and st["n"] > 0
    }

    if not nonempty_stats:
        gating_info["n_sources_before"] = len(results_by_source)
        gating_info["n_sources_after"] = len(results_by_source)
        gating_info["global_top1"] = None
        gating_info["fail_open"] = True
        return results_by_source, gating_info

    global_top1 = max(st["top1"] for st in nonempty_stats.values())
    gating_info["global_top1"] = global_top1

    # If gating explicitly disabled, keep everything but still report stats.
    if not SOURCE_GATING_ENABLED:
        kept = dict(results_by_source)
        for src, rows in results_by_source.items():
            gating_info["sources"][src] = {
                "decision": "keep",
                "reason": "gating_disabled",
                "stats": stats_by_src[src],
            }
        gating_info["n_sources_before"] = len(results_by_source)
        gating_info["n_sources_after"] = len(kept)
        gating_info["fail_open"] = False
        return kept, gating_info

    kept: Dict[str, List[Dict[str, Any]]] = {}

    for src, rows in results_by_source.items():
        stats = stats_by_src[src]
        if stats is None or stats["n"] == 0:
            decision = "drop"
            reason = "no_rows"
        elif src in ALWAYS_KEEP_SOURCES:
            decision = "keep"
            reason = "always_keep"
        elif stats["n"] < MIN_DOCS_PER_SOURCE:
            decision = "drop"
            reason = f"too_few_docs({stats['n']})"
        else:
            rel = stats["top1"] / global_top1 if global_top1 > 0 else 0.0
            meets_rel = rel >= REL_SCORE_CUTOFF
            meets_abs = ABS_SCORE_CUTOFF > 0.0 and stats["top1"] >= ABS_SCORE_CUTOFF

            if meets_rel or meets_abs:
                decision = "keep"
                reason = f"score_ok(rel={rel:.3f})"
            else:
                decision = "drop"
                reason = f"weak_score(rel={rel:.3f})"

        gating_info["sources"][src] = {
            "decision": decision,
            "reason": reason,
            "stats": stats,
        }

        if decision == "keep":
            kept[src] = rows

    # If we dropped everything, fail-open as a safety valve.
    if not kept:
        gating_info["fail_open"] = True
        kept = dict(results_by_source)
    else:
        gating_info["fail_open"] = False

    gating_info["n_sources_before"] = len(results_by_source)
    gating_info["n_sources_after"] = len(kept)

    return kept, gating_info


# ---------------------------------------------------------------------------
# Embedding helpers
# ---------------------------------------------------------------------------


async def embed_query(q: str) -> List[float]:
    """Embed the user query with the same model as rag_corpus."""
    resp = client.embeddings.create(model=EMBED_MODEL, input=[q])
    return resp.data[0].embedding  # type: ignore[no-any-return]


def embedding_to_vector_literal(vec: List[float]) -> str:
    """
    Serialize a Python list[float] into pgvector's text literal format,
    e.g. '[0.1,0.2,...]'. We always cast it to ::vector in SQL.
    """
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


# ---------------------------------------------------------------------------
# PG pool cache
# ---------------------------------------------------------------------------

_PG_POOL: Optional[asyncpg.Pool] = None


def _get_pg_dsn() -> str:
    """
    Resolve a DSN usable by asyncpg.

    Priority:
      1) SYNC_DATABASE_URL (psql / psycopg-style)
      2) DATABASE_URL      (strip SQLAlchemy driver suffixes like +asyncpg)
      3) Hard-coded local default
    """
    sync_url = os.getenv("SYNC_DATABASE_URL")
    if sync_url:
        return sync_url

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        # DATABASE_URL is SQLAlchemy-style; asyncpg doesn't understand the +driver part
        if "+asyncpg" in db_url:
            return db_url.replace("+asyncpg", "")
        if "+psycopg" in db_url:
            return db_url.replace("+psycopg", "")
        return db_url

    # Fallback to local dev default (matches your .env)
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
# DB search (TS + ANN)
# ---------------------------------------------------------------------------


async def search_source_ts(
    pool: Any,
    source: str,
    q: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Full-text search over rag_corpus for a given source.
    Assumes:
      - rag_corpus(ts tsvector, source text, title text, text text, meta jsonb)
      - websearch_to_tsquery('english', q) available
    """
    sql = """
        SELECT id, source, title, text, meta,
               ts_rank_cd(ts, websearch_to_tsquery('english', $1)) AS score
        FROM public.rag_corpus
        WHERE source = $2
          AND ts @@ websearch_to_tsquery('english', $1)
        ORDER BY score DESC
        LIMIT $3;
    """
    rows = await pool.fetch(sql, q, source, limit)
    return [normalize_row(dict(r), source=source, method="ts") for r in rows]


async def search_source_ann(
    pool: Any,
    source: str,
    q_vec_literal: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Vector ANN search over rag_corpus for a given source.

    For NICE we:
      1) Use a hard-coded source filter ('nice') to avoid param issues.
      2) Try proper ANN.
      3) If that returns 0 rows (for any reason), fall back to a simple
         "give me some NICE rows" query so we at least see NICE in matches.
    """

    # Special, fool-proof path for NICE
    if source == "nice":
        # 1) Try proper ANN with a hard-coded source filter
        sql_ann = """
            SELECT id, source, title, text, meta,
                   1.0 - (embedding <=> $1::vector) AS score
            FROM public.rag_corpus
            WHERE source = 'nice'
              AND embedding IS NOT NULL
            ORDER BY embedding <=> $1::vector
            LIMIT $2;
        """
        rows = await pool.fetch(sql_ann, q_vec_literal, limit)

        # 2) If for ANY reason that comes back empty, fall back to a
        #    non-vector query that *must* return some NICE rows.
        if not rows:
            sql_fallback = """
                SELECT id, source, title, text, meta,
                       1.0 AS score
                FROM public.rag_corpus
                WHERE source = 'nice'
                  AND embedding IS NOT NULL
                ORDER BY id
                LIMIT $1;
            """
            rows = await pool.fetch(sql_fallback, limit)

        return [normalize_row(dict(r), source="nice", method="ann") for r in rows]

    # Default path for all other sources
    sql = """
        SELECT id, source, title, text, meta,
               1.0 - (embedding <=> $1::vector) AS score
        FROM public.rag_corpus
        WHERE source = $2
          AND embedding IS NOT NULL
        ORDER BY embedding <=> $1::vector
        LIMIT $3;
    """
    rows = await pool.fetch(sql, q_vec_literal, source, limit)
    return [normalize_row(dict(r), source=source, method="ann") for r in rows]


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
    Bridge between ask_stream and server/api/valyu_client.py.

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
        # For now, treat everything as coming from the PubMed-like corpus.
        # If Valyu exposes finer-grained corpus IDs, you can branch here.
        src_key = "valyu_pubmed"

        base = {
            "id": h.get("id"),
            "source": src_key,
            "title": h.get("title") or "",
            # Use snippet as the context text for the LLM
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


def stream_llm_events(
    q: str,
    context_items: List[Dict[str, Any]],
    llm_mode: str,
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
    """
    ctx_str = format_context_for_llm(context_items)
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

        # New client: content is usually a string
        if isinstance(content, str):
            pieces = [content]
        else:
            # Fallback: try to iterate parts
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
                # Fine-grained streaming
                yield sse("llm_delta", {"text": piece})
            else:
                # Buffered sentence-ish chunks
                buf += piece
                # Heuristic: flush when we see sentence-ending punctuation
                if any(
                    buf.endswith(end)
                    for end in [". ", ".\n", "?\n", "!\n", ".\n\n"]
                ):
                    for ev in flush_chunk():
                        yield ev
                elif len(buf) > 600:
                    # Failsafe: don't let buffer grow unbounded
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

        # Derive a stable-ish key
        if kind == "valyu":
            key = (
                meta.get("pmcid")
                or meta.get("pmid")
                or meta.get("pubmed_id")
                or meta.get("id")
                or row.get("id")
            )
        elif kind == "ethos":
            # Cite Ethos by chunk (more specific to sections)
            key = f"{src}:{row.get('id')}"
        else:
            # Guidelines/other: source + row id
            key = f"{src}:{row.get('id')}"

        raw_citations.append(
            {
                "index": i,  # matches [i] in the answer/context
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
# Main streaming endpoint
# ---------------------------------------------------------------------------


@router.get("/ask_stream")
async def ask_stream(
    request: Request,
    q: str = Query(..., description="User query"),
    limit: int = Query(5, ge=1, le=50),
    # context size for LLM (vs per-source limit)
    ctx_k: int = Query(
        BASE_RRF_K,
        ge=1,
        le=128,
        description="How many fused internal context chunks to send to the LLM",
    ),
    # how many Valyu docs to append (by Valyu's own heuristic ranking)
    valyu_k: int = Query(
        5,
        ge=0,
        le=32,
        description="How many Valyu documents to append to the LLM context",
    ),
    # LLM controls
    with_llm: int = Query(1, description="1 = run LLM, 0 = retrieval only"),
    llm_mode: str = Query(
        "chunk",
        description="LLM streaming mode: 'chunk' (sentence-ish) or 'delta' (token-ish)",
    ),
    # Valyu controls
    use_valyu: int = Query(0, description="1 = include Valyu, 0 = skip"),
    valyu_mode: str = Query("answer"),
    valyu_raw: int = Query(0),
    valyu_sources: Optional[str] = Query(
        None,
        description="Optional Valyu source spec, e.g. 'valyu/valyu-pubmed'",
    ),
    valyu_boost: float = Query(
        1.0,
        description="Optional Valyu boost factor (used upstream by Valyu, not in local fusion)",
    ),
    # optional CSV: sources=mimic4_note,nice,who_eml,cdc_opioid,va_guidelines
    sources: Optional[str] = Query(
        None,
        description="Comma-separated list of rag_corpus.source keys",
    ),
    pool: Any = Depends(resolve_pg_pool),
):
    """
    Streaming RAG endpoint using SSE.

    SSE events (in order-ish):

      - start:
          { "q", "limit", "sources", "ctx_k", "with_llm", "use_valyu", "valyu_k" }

      - status:
          { "status": "embedding_query" | "retrieving_candidates"
                      | "valyu_fetch" | "fusing_context"
                      | "generating_answer" | "done_no_llm"
                      | "ts_error" | "ann_error" | "valyu_error" }

      - phase_start / phase_end:
          For retrieval:
            { "source": "<src>", "method": "ts" | "ann" }
          For LLM:
            { "source": "fusion", "method": "llm" }

      - matches:
          - TS:
              { "phase": "ts", "source": "<src>", "matches": [...] }
          - ANN:
              { "phase": "ann", "source": "<src>", "matches": [...] }
          - Valyu:
              { "phase": "valyu", "source": "valyu", "matches": [...] }
          - Fused (internal + Valyu tail that will be sent to the LLM):
              { "phase": "fused", "source": "fused", "matches": [...] }

      - gating:
          { "enabled", "global_top1", "rel_cutoff", "abs_cutoff",
            "n_sources_before", "n_sources_after", "fail_open",
            "sources": { "<src>": { "decision", "reason", "stats" } } }

      - llm_chunk (llm_mode=chunk):
          { "text": "<sentence-ish chunk>" }

      - llm_delta (llm_mode=delta):
          { "text": "<small token-ish fragment>" }

      - llm_done:
          { "text": "<full answer>" }

      - citations:
          { "citations": [
              {
                "index": <int>,       # matches [index] in the answer/context
                "kind": "valyu" | "ethos" | "guideline",
                "source": "<source>",
                "key": "<stable-ish key>",
                "title": "<title>",
                "extra": {
                  "method": "<ts|ann|valyu|...>",
                  "meta": { ... }     # includes codes/etc. if present
                }
              }, ...
            ]
          }

      - error:
          { "error": "...", "detail": "..." }

      - end:
          { "meta": { "n_sources_raw", "n_sources",
                      "n_ctx_internal", "n_ctx_valyu",
                      "n_ctx_total", "ctx_k", "valyu_k", "with_llm" } }
    """

    # Parse RAG sources: default to mimic4_note if nothing specified
    if sources:
        db_sources = [s.strip() for s in sources.split(",") if s.strip()]
    else:
        db_sources = ["mimic4_note"]

    use_valyu_bool = bool(use_valyu)
    valyu_raw_bool = bool(valyu_raw)
    with_llm_bool = bool(with_llm)

    async def event_generator() -> AsyncIterator[Dict[str, str]]:
        # 0) Initial event
        yield sse(
            "start",
            {
                "q": q,
                "limit": limit,
                "ctx_k": ctx_k,
                "sources": db_sources,
                "with_llm": with_llm_bool,
                "use_valyu": use_valyu_bool,
                "valyu_k": valyu_k,
            },
        )

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

        # 2) Retrieve per source (TS + ANN)
        yield sse("status", {"status": "retrieving_candidates"})
        results_by_source: Dict[str, List[Dict[str, Any]]] = {}
        valyu_matches: List[Dict[str, Any]] = []

        for src in db_sources:
            # --- TS phase ---
            yield sse("phase_start", {"source": src, "method": "ts"})
            try:
                ts_rows = await search_source_ts(pool, src, q, limit)
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

            # --- ANN phase ---
            yield sse("phase_start", {"source": src, "method": "ann"})
            try:
                ann_rows = await search_source_ann(pool, src, q_vec_literal, limit)
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

            results_by_source[src] = list(combined.values())

            if await request.is_disconnected():
                return

        raw_source_count = len(results_by_source)

        # 3) Apply heuristic source gating on internal results
        gated_results_by_source, gating_info = apply_source_gating(results_by_source)
        yield sse("gating", gating_info)

        if await request.is_disconnected():
            return

        # 4) Valyu (optional, kept separate from internal fusion)
        if use_valyu_bool:
            yield sse("status", {"status": "valyu_fetch"})
            try:
                # We may want more raw Valyu hits than we actually send to the LLM,
                # so request up to max(limit, valyu_k)
                valyu_limit = max(limit, valyu_k) if valyu_k > 0 else limit
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
        internal_ctx = build_fused_context(gated_results_by_source, k=ctx_k)

        # Valyu tail: independent of internal heuristics, purely Valyu's ranking
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

        # Build citations from the final context (internal + Valyu tail).
        citations = build_citations(final_ctx)

        # 6) LLM streaming (optional)
        if not with_llm_bool:
            yield sse("status", {"status": "done_no_llm"})
            # Citations still make sense even in retrieval-only mode
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
                    }
                },
            )
            return

        # Old-style LLM phase markers
        yield sse("phase_start", {"source": "fusion", "method": "llm"})
        yield sse("status", {"status": "generating_answer"})

        try:
            for ev in stream_llm_events(q, final_ctx, llm_mode):
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
            # Even if LLM fails, it's still useful to see which sources were used.
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
                    }
                },
            )
            return

        yield sse("phase_end", {"source": "fusion", "method": "llm"})

        # 7) Citations AFTER the answer, so the UI/report can render a clean References section
        yield sse("citations", {"citations": citations})

        # 8) End
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
                }
            },
        )

    return EventSourceResponse(
        event_generator(),
        media_type="text/event-stream",
    )
