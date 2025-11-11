# server/api/rag_stream_routes.py
from __future__ import annotations

import asyncio
import json
import os
import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Optional

import asyncpg
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

try:
    from openai import AsyncOpenAI
except Exception:
    AsyncOpenAI = None

router = APIRouter()

# ---------- Config ----------
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
POSTGRES_DSN = os.getenv("POSTGRES_DSN", "postgresql://localhost/2ndopinionmd")

MAX_PREVIEW = 5
RRF_C = 60
EDGE_BONUS = 0.15
SOURCE_BONUS = {"guidelines": 0.10, "va_guidelines": 0.10, "who_eml": 0.06}
DEFAULT_TOPK_TS = 20
DEFAULT_TOPK_ANN = 20
DEFAULT_CONTEXT_K = 12


# ---------- SSE helpers ----------
def sse(event: str, data: Dict[str, Any]) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")

def status(msg: str, **extra) -> bytes:
    d = {"status": msg}
    d.update(extra)
    return sse("status", d)

def _to_vector_literal(vec):
    # minimal, fast, no trailing space
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


# ---------- OpenAI helpers (sentence-buffered) ----------
async def embed_query(text: str) -> List[float]:
    if AsyncOpenAI is None:
        raise RuntimeError("openai package not available")
    client = AsyncOpenAI()
    resp = await client.embeddings.create(model=EMBED_MODEL, input=[text])
    return resp.data[0].embedding  # type: ignore


async def llm_stream_chunks(prompt: str):
    """
    Emits fewer, larger chunks (end of sentence or ~200 chars).
    """
    if AsyncOpenAI is None:
        yield "LLM unavailable on server."
        return
    client = AsyncOpenAI()
    sys = (
        "You are a careful clinical summarizer. "
        "Use the provided context to answer concisely with bullet points when useful. "
        "Cite facts using [source:id] tags from the context. "
        "If information is uncertain or missing, say so."
    )
    messages = [{"role": "system", "content": sys}, {"role": "user", "content": prompt}]
    buf = ""
    stream = await client.chat.completions.create(
        model=LLM_MODEL, messages=messages, temperature=0.2, stream=True
    )
    async for chunk in stream:
        delta = chunk.choices[0].delta.content or ""  # type: ignore[index]
        if not delta:
            continue
        buf += delta
        if re.search(r"[\.!\?]\s$", buf) or len(buf) >= 200:
            yield buf
            buf = ""
    if buf:
        yield buf


# ---------- Pool resolution (robust with fallback) ----------
async def _create_fallback_pool(app) -> asyncpg.Pool:
    pool = await asyncpg.create_pool(
        dsn=POSTGRES_DSN,
        min_size=int(os.getenv("PGPOOL_MIN", "1")),
        max_size=int(os.getenv("PGPOOL_MAX", "10")),
        command_timeout=60,
    )
    # stash for reuse
    if getattr(app, "state", None) is not None:
        setattr(app.state, "pg_pool", pool)
    return pool


async def resolve_pool_with_via(request: Request) -> Tuple[Optional[asyncpg.Pool], str]:
    app = getattr(request, "app", None)
    state = getattr(app, "state", None)

    # 1) Known state attributes
    if state:
        for name in ("pool", "db_pool", "pg_pool", "pgpool"):
            maybe = getattr(state, name, None)
            if isinstance(maybe, asyncpg.pool.Pool):
                return maybe, f"app.state.{name}"

    # 2) Lazy import of app_postgres.get_pool (no circular at import time)
    try:
        from .app_postgres import get_pool as _get_pool  # type: ignore
        pool = await _get_pool() if asyncio.iscoroutinefunction(_get_pool) else _get_pool()
        if asyncio.iscoroutine(pool):  # just in case
            pool = await pool
        if isinstance(pool, asyncpg.pool.Pool):
            # also cache on app.state for future calls
            if state and not getattr(state, "pool", None):
                setattr(state, "pool", pool)
            return pool, "import:get_pool"
    except Exception as e:
        # Fall through to 3), but surface the reason
        # We won't print() here; we'll return the reason to the caller via 'via'
        import_err = f"import:get_pool_failed:{e}"
    else:
        import_err = "import:get_pool_none"

    # 3) Fallback: create our own pool with DSN and stash
    try:
        pool = await _create_fallback_pool(app)
        return pool, "fallback:created_pg_pool"
    except Exception as e:
        return None, f"{import_err}|fallback_failed:{e}"


# ---------- Retrieval ----------
async def ts_search(conn: asyncpg.Connection, q: str, source: str, k: int) -> List[Dict[str, Any]]:
    rows = await conn.fetch(
        """
        SELECT id, source, title
        FROM rag_corpus
        WHERE source = $1
          AND (
            title ILIKE '%' || $2 || '%'
            OR to_tsvector('simple', coalesce(title,'')) @@ plainto_tsquery('simple', $2)
          )
        ORDER BY
          CASE WHEN position(lower($2) in lower(title)) > 0 THEN 0 ELSE 1 END,
          id
        LIMIT $3
        """,
        source, q, k,
    )
    return [{"id": r["id"], "source": r["source"], "title": r["title"], "score": 0.0} for r in rows]


async def source_has_embeddings(conn: asyncpg.Connection, source: str) -> bool:
    r = await conn.fetchval(
        "SELECT EXISTS(SELECT 1 FROM rag_corpus WHERE source=$1 AND embedding IS NOT NULL LIMIT 1)", source
    )
    return bool(r)


async def ann_search(conn, q_vec, source: str, k: int):
    if not q_vec:
        return []
    qv = _to_vector_literal(q_vec)  # -> "[0.123,-0.456,...]"
    rows = await conn.fetch(
        """
        SELECT id, source, title, (1 - (embedding <=> $1::vector)) AS sim
        FROM rag_corpus
        WHERE source = $2 AND embedding IS NOT NULL
        ORDER BY embedding <=> $1::vector
        LIMIT $3
        """,
        qv, source, k,
    )
    return [{"id": r["id"], "source": r["source"], "title": r["title"], "score": float(r["sim"])} for r in rows]

async def expand_edges(conn: asyncpg.Connection, cands: List[Tuple[str, str]], limit: int = 2000) -> List[Dict[str, Any]]:
    if not cands:
        return []
    await conn.execute(
        "CREATE TEMP TABLE IF NOT EXISTS cand (source text, src_id text) ON COMMIT PRESERVE ROWS;"
    )
    await conn.execute("TRUNCATE cand;")
    await conn.executemany("INSERT INTO cand(source, src_id) VALUES($1, $2)", cands)

    edges = await conn.fetch(
        """
        WITH x AS (
          SELECT e.dst_source, e.dst_id, MAX(e.weight) AS edge_w
          FROM cand c
          JOIN ontology_edges e
            ON e.src_source=c.source AND e.src_id=c.src_id
          GROUP BY 1,2
          LIMIT $1
        )
        SELECT r.id, r.source, r.title, x.edge_w
        FROM x
        JOIN rag_corpus r
          ON r.source = x.dst_source AND r.id::text = x.dst_id
        """,
        limit,
    )
    return [{"id": r["id"], "source": r["source"], "title": r["title"], "edge_w": float(r["edge_w"])} for r in edges]


def rrf_fuse(
    ts_by_source: Dict[str, List[Dict[str, Any]]],
    ann_by_source: Dict[str, List[Dict[str, Any]]],
    edge_rows: List[Dict[str, Any]],
    k_final: int,
) -> List[Dict[str, Any]]:
    ts_rank, ann_rank = {}, {}
    for s, rows in ts_by_source.items():
        for i, r in enumerate(rows):
            ts_rank[(s, r["id"])] = i
    for s, rows in ann_by_source.items():
        for i, r in enumerate(rows):
            ann_rank[(s, r["id"])] = i

    edge_bonus = defaultdict(float)
    for r in edge_rows:
        edge_bonus[(r["source"], r["id"])] = max(edge_bonus[(r["source"], r["id"])], r.get("edge_w", 0.0))

    keys = set(ts_rank) | set(ann_rank) | set(edge_bonus)
    fused: List[Tuple[float, Tuple[str, Any]]] = []
    for key in keys:
        s, _doc_id = key
        score = 0.0
        if (rk := ts_rank.get(key)) is not None:
            score += 1.0 / (RRF_C + rk)
        if (rk := ann_rank.get(key)) is not None:
            score += 1.0 / (RRF_C + rk)
        score += EDGE_BONUS * edge_bonus.get(key, 0.0)
        score += SOURCE_BONUS.get(s, 0.0)
        fused.append((score, key))

    fused.sort(key=lambda x: x[0], reverse=True)

    idx: Dict[Tuple[str, Any], Dict[str, Any]] = {}
    for d in ts_by_source.values():
        for r in d:
            idx[(r["source"], r["id"])] = r
    for d in ann_by_source.values():
        for r in d:
            idx.setdefault((r["source"], r["id"]), r)
    for r in edge_rows:
        idx.setdefault((r["source"], r["id"]), {"id": r["id"], "source": r["source"], "title": r["title"]})

    out: List[Dict[str, Any]] = []
    seen_titles = set()
    for sc, key in fused:
        s, _ = key
        row = idx.get(key)
        if not row:
            continue
        t = (s, (row.get("title") or "").strip().lower())
        if t in seen_titles:
            continue
        seen_titles.add(t)
        out.append({"id": row["id"], "source": s, "title": row.get("title"), "score": sc})
        if len(out) >= k_final:
            break
    return out


def build_prompt(user_q: str, ctx_rows: List[Dict[str, Any]]) -> str:
    lines = [f"Question: {user_q}", "", "Context:"]
    for r in ctx_rows:
        tag = f"[{r['source']}:{r['id']}]"
        title = (r.get("title") or "").strip()
        lines.append(f"{tag} {title}")
    lines.append("")
    lines.append("Answer succinctly. Cite with the same [source:id] tags inline where relevant.")
    return "\n".join(lines)


# ---------- Main SSE route ----------
@router.get("/api/rag/ask_stream")
async def rag_ask_stream(
    request: Request,
    q: str,
    limit: int = 10,
    sources: str = "mimic4_dx",
    pings: int = 1,
    with_llm: int = 0,
    topk_ts: int = DEFAULT_TOPK_TS,
    topk_ann: int = DEFAULT_TOPK_ANN,
    ctx_k: int = DEFAULT_CONTEXT_K,
):
    async def gen():
        src_list = [s.strip() for s in sources.split(",") if s.strip()]
        yield sse("start", {"q": q, "limit": max(1, min(100, limit)), "sources": ",".join(src_list)})

        pool, via = await resolve_pool_with_via(request)
        if pool is None:
            yield sse("phase_error", {"source": "db", "method": "pool", "error": "DB pool unavailable", "via": via})
            yield sse("done", {"q": q})
            return
        else:
            yield status("db_pool_resolved", via=via)

        yield status("retrieving_candidates", q=q)

        topk_ts_clamped = max(1, min(200, topk_ts))
        topk_ann_clamped = max(1, min(200, topk_ann))
        ctx_k_clamped = max(1, min(30, ctx_k))

        async with pool.acquire() as conn:
            # Embed once (optional)
            try:
                q_vec = await embed_query(q)
            except Exception as e:
                q_vec = None
                yield status("embed_query_failed", error=str(e))

            ts_by_source: Dict[str, List[Dict[str, Any]]] = {}
            ann_by_source: Dict[str, List[Dict[str, Any]]] = {}

            for src in src_list:
                # TS
                yield sse("phase_start", {"source": src, "method": "ts"})
                try:
                    ts_rows = await ts_search(conn, q=q, source=src, k=topk_ts_clamped)
                except Exception as e:
                    ts_rows = []
                    yield sse("phase_error", {"source": src, "method": "ts", "error": str(e)})
                ts_by_source[src] = ts_rows
                if ts_rows:
                    yield sse("matches", {"source": src, "method": "ts", "rows": ts_rows[:MAX_PREVIEW]})
                yield sse("phase_end", {"source": src, "method": "ts"})

                # ANN
                yield sse("phase_start", {"source": src, "method": "ann"})
                ann_rows: List[Dict[str, Any]] = []
                try:
                    if q_vec is not None and await source_has_embeddings(conn, src):
                        ann_rows = await ann_search(conn, q_vec=q_vec, source=src, k=topk_ann_clamped)
                except Exception as e:
                    yield sse("phase_error", {"source": src, "method": "ann", "error": str(e)})
                ann_by_source[src] = ann_rows
                if ann_rows:
                    yield sse("matches", {"source": src, "method": "ann", "rows": ann_rows[:MAX_PREVIEW]})
                yield sse("phase_end", {"source": src, "method": "ann"})

            # Edge expansion
            yield sse("phase_start", {"source": "edges", "method": "expand"})
            base_keys: List[Tuple[str, str]] = []
            for s, rows in ts_by_source.items():
                for r in rows[:5]:
                    base_keys.append((s, str(r["id"])))
            for s, rows in ann_by_source.items():
                for r in rows[:5]:
                    base_keys.append((s, str(r["id"])))
            base_keys = list({(s, i) for (s, i) in base_keys})
            try:
                edge_rows = await expand_edges(conn, base_keys, limit=2000)
                if edge_rows:
                    yield sse("matches", {"source": "edges", "method": "expand", "rows": edge_rows[:MAX_PREVIEW]})
            except Exception as e:
                edge_rows = []
                yield sse("phase_error", {"source": "edges", "method": "expand", "error": str(e)})
            yield sse("phase_end", {"source": "edges", "method": "expand"})

            # Fusion
            yield status("fusing_results")
            fused = rrf_fuse(ts_by_source, ann_by_source, edge_rows, k_final=limit)
            yield sse("phase_start", {"source": "rag_fusion", "method": "rank"})
            yield sse("matches", {"source": "rag_fusion", "method": "rank", "rows": fused[:MAX_PREVIEW]})
            yield sse("phase_end", {"source": "rag_fusion", "method": "rank"})

            # Optional LLM
            if with_llm:
                yield status("generating_summary")
                yield sse("phase_start", {"source": "rag_fusion", "method": "llm"})
                prompt = build_prompt(q, fused[:ctx_k_clamped])
                try:
                    async for chunk in llm_stream_chunks(prompt):
                        yield sse("llm_chunk", {"text": chunk})
                except Exception as e:
                    yield sse("phase_error", {"source": "rag_fusion", "method": "llm", "error": str(e)})
                yield sse("phase_end", {"source": "rag_fusion", "method": "llm"})

        yield sse("done", {"q": q})

    return StreamingResponse(gen(), media_type="text/event-stream")


# ---------- Health: helps confirm pool wiring ----------
@router.get("/api/health/db")
async def health_db(request: Request):
    async def gen():
        pool, via = await resolve_pool_with_via(request)
        if pool is None:
            yield sse("db", {"ok": False, "via": via})
            return
        try:
            async with pool.acquire() as conn:
                v = await conn.fetchval("select version()")
            yield sse("db", {"ok": True, "via": via, "version": v})
        except Exception as e:
            yield sse("db", {"ok": False, "via": via, "error": str(e)})
    return StreamingResponse(gen(), media_type="text/event-stream")
