from __future__ import annotations
import os
import json
import asyncio
from typing import Any, Dict, List, Tuple, Optional
from fastapi import APIRouter, Request, HTTPException
from starlette.responses import StreamingResponse
from integrations.valyu_retriever import search_valyu

import asyncpg

# If you have a central embeddings helper, import it here.
# It should return a list[float] vector for the query text.
# Fallback: define a no-op that returns [] (ts-only).
try:
    from .embeddings import embed_text as embed_query  # (text:str)->list[float]
except Exception:
    async def embed_query(_: str) -> List[float]:
        return []

router = APIRouter(prefix="/api/rag", tags=["rag"])

# ---------------------- Utilities ----------------------

def sse(event: str, data: Any) -> str:
    if isinstance(data, (dict, list)):
        payload = json.dumps(data, ensure_ascii=False)
    else:
        payload = str(data)
    return f"event: {event}\ndata: {payload}\n\n"

def _to_vector_literal(vec: List[float]) -> str:
    # asyncpg won’t auto-cast python list -> pgvector reliably; send as text + ::vector
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"

async def resolve_pg_pool(request: Request) -> Tuple[asyncpg.Pool, str]:
    # Try app.state.pg_pool first (your primary), then import fallback, then make one
    if getattr(request.app.state, "pg_pool", None):
        return request.app.state.pg_pool, "app.state.pg_pool"
    # lazy import fallback getter if present
    try:
        from .app_postgres import get_pool  # not imported at module top to avoid cycles
        pool = await get_pool()
        return pool, "import:get_pool"
    except Exception:
        pass
    dsn = os.getenv("POSTGRES_DSN", "postgresql://localhost/2ndopinionmd")
    max_size = int(os.getenv("PGPOOL_MAX", "10"))
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=max_size)
    request.app.state.pg_pool = pool
    return pool, "fallback:created_pg_pool"

# ---------------------- Retrieval ----------------------

async def ts_search(conn: asyncpg.Connection, q: str, source: str, k: int) -> List[Dict[str, Any]]:
    # Minimal text search placeholder; replace with your optimized query (tsvector/rum/etc.)
    rows = await conn.fetch(
        """
        SELECT id, source, title, 0.0 AS score
        FROM rag_corpus
        WHERE source = $1 AND (title ILIKE '%'||$2||'%' OR $2 = '')
        LIMIT $3
        """,
        source, q, k
    )
    return [{"id": r["id"], "source": r["source"], "title": r["title"], "score": float(r["score"])} for r in rows]

async def ann_search(conn: asyncpg.Connection, q_vec: List[float], source: str, k: int) -> List[Dict[str, Any]]:
    if not q_vec:
        return []
    qv = _to_vector_literal(q_vec)  # "[...]" then cast to ::vector in SQL
    rows = await conn.fetch(
        """
        SELECT id, source, title, (1 - (embedding <=> $1::vector)) AS sim
        FROM rag_corpus
        WHERE source = $2 AND embedding IS NOT NULL
        ORDER BY embedding <=> $1::vector
        LIMIT $3
        """,
        qv, source, k
    )
    return [{"id": r["id"], "source": r["source"], "title": r["title"], "score": float(r["sim"])} for r in rows]

async def phase_valyu(q, limit, inline_citations):
    yield sse_event("phase_start", j({"source":"valyu","method":"external"}))
    data = await search_valyu(q, k=limit, response_length="short", search_type="proprietary")
    matches = data["matches"]
    # Emit as regular matches so the UI “Sources” panel just works
    yield sse_event("matches", j({"source":"valyu_web","method":"external","rows":[
        {"id":m["id"],"source":"valyu_web","title":m["title"],"score":m["score"],"url":m["url"],"subtype":m["subtype"]}
        for m in matches
    ]}))
    # Optional: emit a citations block for UI
    yield sse_event("citations", j({"items":[
        {"id":m["id"],"source":"valyu_web","title":m["title"],"url":m["url"]}
        for m in matches
    ]}))
    yield sse_event("phase_end", j({"source":"valyu","method":"external"}))
    return matches  # can be fused with local TS/ANN

async def expand_edges(conn: asyncpg.Connection, cands: List[Tuple[str, str]], limit: int = 2000) -> List[Dict[str, Any]]:
    # cands: list of (source, id)
    if not cands:
        return []
    await conn.execute(
        "CREATE TEMP TABLE IF NOT EXISTS cand (source text, src_id text) ON COMMIT PRESERVE ROWS;"
    )
    await conn.execute("TRUNCATE cand;")
    await conn.executemany("INSERT INTO cand(source, src_id) VALUES($1, $2)", cands)
    rows = await conn.fetch(
        """
        SELECT e.dst_source AS source, e.dst_id::text AS id, MAX(e.weight) AS edge_w
        FROM cand c
        JOIN ontology_edges e
          ON e.src_source=c.source AND e.src_id=c.src_id
        GROUP BY 1,2
        ORDER BY MAX(e.weight) DESC
        LIMIT $1
        """,
        limit
    )
    # Enrich edge targets with titles
    if not rows:
        return []
    ids = [(r["source"], r["id"]) for r in rows]
    # build dynamic IN tuple query
    # safer to use temp table for lookups
    await conn.execute("CREATE TEMP TABLE IF NOT EXISTS dst (source text, id text) ON COMMIT PRESERVE ROWS;")
    await conn.execute("TRUNCATE dst;")
    await conn.executemany("INSERT INTO dst(source, id) VALUES($1, $2)", ids)
    info = await conn.fetch(
        """
        SELECT r.id::text AS id, r.source, r.title
        FROM rag_corpus r
        JOIN dst d ON d.source = r.source AND d.id::text = r.id::text
        """
    )
    title_map = {(r["source"], r["id"]): r["title"] for r in info}
    out = []
    for r in rows:
        key = (r["source"], r["id"])
        out.append({
            "id": r["id"],
            "source": r["source"],
            "title": title_map.get(key, None),
            "score": float(r["edge_w"]),
        })
    return out

def rrf_fuse(groups: List[List[Dict[str, Any]]], k: int = 50, k_rrf: float = 60.0) -> List[Dict[str, Any]]:
    # groups: list of ranked lists; returns fused, deduped ranking
    scores: Dict[Tuple[str, str], float] = {}
    keep: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for g in groups:
        for rank, r in enumerate(g, start=1):
            key = (r["source"], str(r["id"]))
            scores[key] = scores.get(key, 0.0) + 1.0 / (k_rrf + rank)
            if key not in keep:
                keep[key] = {"id": str(r["id"]), "source": r["source"], "title": r.get("title")}
    fused = [{"id": v["id"], "source": v["source"], "title": v.get("title"), "score": scores[(v["source"], v["id"])]}
             for v in keep.values()]
    fused.sort(key=lambda x: x["score"], reverse=True)
    return fused[:k]

async def fetch_citation_rows(conn: asyncpg.Connection, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not items:
        return []
    await conn.execute("CREATE TEMP TABLE IF NOT EXISTS cite (source text, id text) ON COMMIT PRESERVE ROWS;")
    await conn.execute("TRUNCATE cite;")
    await conn.executemany("INSERT INTO cite(source, id) VALUES($1, $2)", [(i["source"], str(i["id"])) for i in items])
    rows = await conn.fetch(
        """
        SELECT r.id::text AS id, r.source, r.title,
               COALESCE(r.payload->>'url', NULL) AS url
        FROM rag_corpus r
        JOIN cite c ON c.source=r.source AND c.id::text = r.id::text
        """
    )
    # Dedup stable order by (source,id)
    seen = set()
    out = []
    for r in rows:
        key = (r["source"], r["id"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": r["id"], "source": r["source"], "title": r["title"], "url": r["url"]})
    return out

# ---------------------- LLM streaming ----------------------

async def llm_stream_yield(text_gen, llm_mode: str = "chunk"):
    """
    text_gen must be an async generator yielding token deltas (strings).
    llm_mode:
      - 'delta' : forward model deltas as llm_delta
      - 'chunk' : sentence-buffered llm_chunk (quiet)
    """
    if llm_mode == "delta":
        async for tok in text_gen:
            if tok:
                yield sse("llm_delta", {"text": tok})
        return

    # chunk mode
    buf = []
    acc_len = 0
    flush_marks = {".", "!", "?", "\n"}
    async for tok in text_gen:
        if not tok:
            continue
        buf.append(tok)
        acc_len += len(tok)
        if any(ch in tok for ch in flush_marks) or acc_len >= 500:
            chunk = "".join(buf)
            buf, acc_len = [], 0
            if chunk.strip():
                yield sse("llm_chunk", {"text": chunk})
    # trailing
    if buf:
        chunk = "".join(buf)
        if chunk.strip():
            yield sse("llm_chunk", {"text": chunk})

# Replace with your OpenAI client; this is a skinny wrapper you can adapt.
async def openai_chat_stream(prompt: str, sys: Optional[str] = None):
    """
    Yields token deltas (strings). Plug your existing client here.
    """
    from openai import AsyncOpenAI
    client = AsyncOpenAI()
    msgs = []
    if sys:
        msgs.append({"role": "system", "content": sys})
    msgs.append({"role": "user", "content": prompt})
    stream = await client.chat.completions.create(
        model=os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini"),
        messages=msgs,
        temperature=0.2,
        stream=True,
    )
    async for event in stream:
        if hasattr(event, "choices") and event.choices:
            delta = event.choices[0].delta.content or ""
            if delta:
                yield delta

# ---------------------- Route ----------------------

@router.get("/ask_stream")
async def ask_stream(
    request: Request,
    q: str,
    limit: int = 10,
    sources: str = "",
    with_llm: int = 0,
    ctx_k: int = 8,
    use_edges: int = 1,
    llm_mode: str = "chunk",             # <-- NEW: 'chunk' (quiet) or 'delta' (raw)
    inline_citations: int = 1,           # keep inline [source:src:id] tags in LLM text
):
    async def streamer():
        # announce query
        yield sse("start", {"q": q, "limit": limit, "sources": sources or None})

        # resolve pool
        try:
            pool, via = await resolve_pg_pool(request)
            yield sse("status", {"status": "db_pool_resolved", "via": via})
        except Exception as e:
            yield sse("phase_error", {"source": "db", "method": "pool", "error": str(e)})
            yield sse("done", {"q": q})
            return

        # parse sources
        srcs = [s.strip() for s in (sources.split(",") if sources else []) if s.strip()]
        # embed once for ANN across sources
        try:
            q_vec: List[float] = await embed_query(q)
        except Exception:
            q_vec = []

        yield sse("status", {"status": "retrieving_candidates", "q": q})

        async with pool.acquire() as conn:
            # ts + ann per source
            all_groups: List[List[Dict[str, Any]]] = []
            base_cands: List[Tuple[str, str]] = []

            for src in srcs or []:
                # TS
                try:
                    yield sse("phase_start", {"source": src, "method": "ts"})
                    ts_rows = await ts_search(conn, q, src, limit)
                    if ts_rows:
                        yield sse("matches", {"source": src, "method": "ts", "rows": ts_rows})
                        all_groups.append(ts_rows)
                        base_cands.extend([(r["source"], str(r["id"])) for r in ts_rows])
                except Exception as e:
                    yield sse("phase_error", {"source": src, "method": "ts", "error": str(e)})
                finally:
                    yield sse("phase_end", {"source": src, "method": "ts"})

                # ANN
                try:
                    yield sse("phase_start", {"source": src, "method": "ann"})
                    ann_rows = await ann_search(conn, q_vec, src, limit)
                    if ann_rows:
                        yield sse("matches", {"source": src, "method": "ann", "rows": ann_rows})
                        all_groups.append(ann_rows)
                        base_cands.extend([(r["source"], str(r["id"])) for r in ann_rows])
                except Exception as e:
                    yield sse("phase_error", {"source": src, "method": "ann", "error": str(e)})
                finally:
                    yield sse("phase_end", {"source": src, "method": "ann"})

            # Edges expansion (optional)
            try:
                yield sse("phase_start", {"source": "edges", "method": "expand"})
                edge_rows = []
                if use_edges and base_cands:
                    edge_rows = await expand_edges(conn, base_cands, limit=2000)
                    if edge_rows:
                        yield sse("matches", {"source": "edges", "method": "expand", "rows": edge_rows[:min(50, len(edge_rows))]})
                        all_groups.append(edge_rows)
                yield sse("phase_end", {"source": "edges", "method": "expand"})
            except Exception as e:
                yield sse("phase_error", {"source": "edges", "method": "expand", "error": str(e)})
                yield sse("phase_end", {"source": "edges", "method": "expand"})

            # Fusion
            yield sse("status", {"status": "fusing_results"})
            try:
                yield sse("phase_start", {"source": "rag_fusion", "method": "rank"})
                fused = rrf_fuse(all_groups, k=max(limit, ctx_k))
                if fused:
                    yield sse("matches", {"source": "rag_fusion", "method": "rank", "rows": fused[:limit]})
                yield sse("phase_end", {"source": "rag_fusion", "method": "rank"})
            except Exception as e:
                yield sse("phase_error", {"source": "rag_fusion", "method": "rank", "error": str(e)})
                fused = []

            # Build context + citations
            ctx = fused[:ctx_k]
            try:
                citations = await fetch_citation_rows(conn, ctx)
            except Exception:
                citations = [{"id": r["id"], "source": r["source"], "title": r.get("title")} for r in ctx]

        # Ship citations as a dedicated event for the frontend Sources panel
        if citations:
            yield sse("phase_start", {"source": "rag_fusion", "method": "citations"})
            yield sse("citations", {"items": citations})
            yield sse("phase_end", {"source": "rag_fusion", "method": "citations"})

        # Optionally call LLM
        if with_llm:
            yield sse("status", {"status": "generating_summary"})
            yield sse("phase_start", {"source": "rag_fusion", "method": "llm"})

            # Construct a compact prompt w/ inline cite tokens if desired
            lines = []
            for r in ctx:
                tag = f"[{r['source']}:{r['id']}]"
                title = (r.get("title") or "").strip()
                if title:
                    lines.append(f"- {title} {tag}")
                else:
                    lines.append(f"- {tag}")

            sys_prompt = (
                "You are a clinical summarizer. Write concise, factual bullets. "
                "If inline citations are present like [source:id], leave them at the end of the relevant bullet. "
                "If a requested detail is not supported by the provided context, say it is not found."
            )
            user_prompt = (
                f"Query: {q}\nContext items (for citation):\n" + "\n".join(lines) +
                ("\n\nInclude a brief 'Sources:' section listing the tags used." if inline_citations else "")
            )

            async def gen():
                async for tok in openai_chat_stream(user_prompt, sys_prompt):
                    yield tok

            async for piece in llm_stream_yield(gen(), llm_mode=llm_mode):
                yield piece

            yield sse("phase_end", {"source": "rag_fusion", "method": "llm"})

        yield sse("done", {"q": q})

    return StreamingResponse(streamer(), media_type="text/event-stream")
