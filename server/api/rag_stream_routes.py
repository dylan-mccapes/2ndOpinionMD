# server/api/rag_stream_routes.py
from __future__ import annotations
import os, json, asyncio
from typing import Any, Dict, List, Tuple, Optional
from fastapi import APIRouter, Request, Query
from starlette.responses import StreamingResponse
import asyncpg

from .valyu_client import call_valyu

# -------------------------
# Module-level PG pool cache
# -------------------------
_PG_POOL: Optional[asyncpg.Pool] = None

async def resolve_pg_pool() -> asyncpg.Pool:
    global _PG_POOL
    if _PG_POOL is None:
        dsn = os.getenv("POSTGRES_DSN", "postgresql://localhost/2ndopinionmd")
        max_size = int(os.getenv("PGPOOL_MAX", "10"))
        _PG_POOL = await asyncpg.create_pool(dsn, min_size=1, max_size=max_size)
    return _PG_POOL

# -------------------------
# Embedding helper (optional)
# -------------------------
try:
    from .embeddings import embed_text as embed_query  # async (str) -> list[float]
except Exception:
    async def embed_query(_: str) -> List[float]:
        return []

# -------------------------
# Router & helpers
# -------------------------
router = APIRouter(prefix="/api", tags=["rag"])

def sse(event: str, data: Any) -> str:
    payload = json.dumps(data, ensure_ascii=False) if isinstance(data, (dict, list)) else str(data)
    return f"event: {event}\ndata: {payload}\n\n"

def _to_vector_literal(vec: List[float]) -> str:
    return "[" + ",".join(f"{float(x):.6f}" for x in vec) + "]"

# -------------------------
# Retrieval: local FTS + ANN
# -------------------------
async def ts_search(conn: asyncpg.Connection, q: str, source: str, k: int) -> List[Dict[str, Any]]:
    if not q.strip():
        return []
    rows = await conn.fetch(
        """
        SELECT id, source, title,
               ts_rank_cd(
                 to_tsvector('simple_unaccent', coalesce(title,'') || ' ' || coalesce(text,'')),
                 plainto_tsquery('simple_unaccent', $2)
               ) AS score,
               LEFT(
                 ts_headline(
                   'simple_unaccent',
                   coalesce(text,''),
                   plainto_tsquery('simple_unaccent', $2),
                   'StartSel=<<,StopSel=>>,MaxFragments=2,FragmentDelimiter=" … ",MinWords=5,MaxWords=20'
                 ), 400
               ) AS snippet,
               meta->>'section' AS section,
               meta->>'pmid'    AS pmid
        FROM rag_corpus
        WHERE source = $1
          AND to_tsvector('simple_unaccent', coalesce(title,'') || ' ' || coalesce(text,''))
              @@ plainto_tsquery('simple_unaccent', $2)
        ORDER BY score DESC
        LIMIT $3
        """,
        source, q, k
    )
    return [{
        "id": r["id"], "source": r["source"], "title": r["title"],
        "score": float(r["score"] or 0.0),
        "snippet": r["snippet"], "section": r["section"], "pmid": r["pmid"]
    } for r in rows]

async def ann_search(conn: asyncpg.Connection, *, source: str, q_text: str, q_vec: List[float], k: int = 10) -> List[Dict[str, Any]]:
    if not q_vec:
        return []
    vstr = _to_vector_literal(q_vec)
    rows = await conn.fetch(
        """
        SELECT id, source, title,
               (1 - (embedding <=> $1::vector)) AS sim,
               LEFT(
                 ts_headline('simple_unaccent', COALESCE(text,''),
                             plainto_tsquery('simple_unaccent',$2),
                             'StartSel=<<,StopSel=>>,MaxFragments=2,FragmentDelimiter=\" … \",MinWords=5,MaxWords=20'), 400
               ) AS snippet,
               meta->>'section' AS section,
               meta->>'pmid'    AS pmid
        FROM rag_corpus
        WHERE source=$3 AND embedding IS NOT NULL
        ORDER BY embedding <=> $1::vector
        LIMIT $4
        """,
        vstr, q_text, source, k
    )
    return [{
        "id": r["id"], "source": r["source"], "title": r["title"],
        "score": float(r["sim"] or 0.0),
        "snippet": r["snippet"], "section": r["section"], "pmid": r["pmid"]
    } for r in rows]

def rrf_fuse(groups: List[List[Dict[str, Any]]], k: int = 50, k_rrf: float = 60.0) -> List[Dict[str, Any]]:
    scores: Dict[Tuple[str, str], float] = {}
    keep: Dict[Tuple[str, str], Dict[str, Any]] = {}
    for g in groups:
        for rank, r in enumerate(g, start=1):
            key = (str(r.get("source","")), str(r.get("id","")))
            scores[key] = scores.get(key, 0.0) + 1.0 / (k_rrf + rank)
            keep.setdefault(key, {
                "id": str(r.get("id","")),
                "source": str(r.get("source","")),
                "title": r.get("title"),
                "snippet": r.get("snippet"),
                "pmid": r.get("pmid"),
                "section": r.get("section"),
            })
    fused = [{
        "id": v["id"], "source": v["source"], "title": v.get("title"),
        "score": scores[(v["source"], v["id"])],
        "snippet": v.get("snippet"), "pmid": v.get("pmid"), "section": v.get("section"),
    } for v in keep.values()]
    fused.sort(key=lambda x: x["score"], reverse=True)
    return fused[:k]

def to_url(item: Dict[str, Any]) -> Optional[str]:
    if item.get("source") == "pubmd" and item.get("pmid"):
        return f"https://pubmed.ncbi.nlm.nih.gov/{item['pmid']}/"
    return None

async def fetch_citation_rows(conn: asyncpg.Connection, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not items:
        return []
    await conn.execute("CREATE TEMP TABLE IF NOT EXISTS cite (source text, id text) ON COMMIT PRESERVE ROWS;")
    await conn.execute("TRUNCATE cite;")
    await conn.executemany("INSERT INTO cite(source, id) VALUES($1, $2)",
                           [(str(i.get("source","")), str(i.get("id",""))) for i in items])
    rows = await conn.fetch(
        """
        SELECT r.id::text AS id, r.source, r.title, COALESCE(r.meta->>'url', NULL) AS url
        FROM rag_corpus r
        JOIN cite c ON c.source = r.source AND c.id::text = r.id::text
        """
    )
    seen, out = set(), []
    for r in rows:
        key = (r["source"], r["id"])
        if key in seen:
            continue
        seen.add(key)
        out.append({"id": r["id"], "source": r["source"], "title": r["title"], "url": r["url"]})
    return out

# -------------------------
# LLM streaming helpers (optional)
# -------------------------
async def llm_stream_yield(text_gen, llm_mode: str = "chunk"):
    if llm_mode == "delta":
        async for tok in text_gen:
            if tok:
                yield sse("llm_delta", {"text": tok})
        return
    buf, acc = [], 0
    async for tok in text_gen:
        if not tok:
            continue
        buf.append(tok); acc += len(tok)
        if any(ch in tok for ch in (".","!","?","\n")) or acc >= 500:
            chunk = "".join(buf).strip()
            buf, acc = [], 0
            if chunk:
                yield sse("llm_chunk", {"text": chunk})
    if buf:
        chunk = "".join(buf).strip()
        if chunk:
            yield sse("llm_chunk", {"text": chunk})

# -------------------------
# Routes
# -------------------------

@router.get("/rag/ask_stream")
async def ask_stream(
    request: Request,
    q: str = Query(..., min_length=2),
    limit: int = 10,
    # IMPORTANT: stop defaulting to local "pubmd"
    sources: str = "mimic4_note",
    with_llm: int = 0,
    ctx_k: int = 8,
    llm_mode: str = "chunk",
    # Valyu controls
    use_valyu: int = 1,
    valyu_mode: str = "search",  # "search" | "answer"  (default to search for fast evidence)
    valyu_raw: int = 0,
    # Comma-separated Valyu datasets; default is PubMed
    valyu_sources: str = "valyu/valyu-pubmed",
    valyu_fast: int = 0,
    valyu_return_contents: int = 0,
):
    """
    Streams: start/status/phase_start/matches/context/citations/llm_*/*done* as SSE.
    """
    K = max(1, min(limit, 50))
    srcs = [s.strip() for s in (sources.split(",") if sources else []) if s.strip()]
    v_sources = [s.strip() for s in (valyu_sources.split(",") if valyu_sources else []) if s.strip()]

    async def disconnected() -> bool:
        try:
            return await request.is_disconnected()
        except Exception:
            return False

    async def streamer():
        yield sse("start", {"q": q, "limit": limit, "sources": srcs})

        # DB pool (for local sources only)
        try:
            pool = await resolve_pg_pool()
            yield sse("status", {"status": "db_pool_ready"})
        except Exception as e:
            yield sse("phase_error", {"source": "db", "method": "pool", "error": str(e)})
            yield sse("done", {"q": q})
            return

        # optional ANN embed
        try:
            q_vec = await embed_query(q)
        except Exception:
            q_vec = []
        yield sse("status", {"status": "retrieving_candidates"})

        all_groups: List[List[Dict[str, Any]]] = []

        # ---------- Local retrieval ----------
        if srcs:
            async with pool.acquire() as conn:
                for src in srcs:
                    if await disconnected():
                        return
                    # TS
                    try:
                        yield sse("phase_start", {"source": src, "method": "ts"})
                        ts_rows = await ts_search(conn, q, src, K)
                        if ts_rows:
                            yield sse("matches", {"source": src, "method": "ts", "rows": ts_rows})
                            all_groups.append(ts_rows)
                    except Exception as e:
                        yield sse("phase_error", {"source": src, "method": "ts", "error": str(e)})
                    finally:
                        yield sse("phase_end", {"source": src, "method": "ts"})
                    # ANN
                    try:
                        yield sse("phase_start", {"source": src, "method": "ann"})
                        ann_rows = await ann_search(conn, source=src, q_text=q, q_vec=q_vec, k=K)
                        if ann_rows:
                            yield sse("matches", {"source": src, "method": "ann", "rows": ann_rows})
                            all_groups.append(ann_rows)
                    except Exception as e:
                        yield sse("phase_error", {"source": src, "method": "ann", "error": str(e)})
                    finally:
                        yield sse("phase_end", {"source": src, "method": "ann"})

        # ---------- Valyu pass (PubMed by default) ----------
        if use_valyu:
            try:
                yield sse("phase_start", {"source": "valyu_web", "method": valyu_mode, "sources": v_sources})
                vy = await call_valyu(
                    valyu_mode,
                    q,
                    k=K,
                    included_sources=v_sources,
                    fast_mode=bool(valyu_fast),
                    return_contents=bool(valyu_return_contents),
                    search_type="proprietary" if valyu_mode == "answer" else None,
                )
                if valyu_raw:
                    yield sse("valyu_raw", {"payload": vy})

                if not vy.get("success"):
                    yield sse("phase_error", {
                        "source": "valyu_web",
                        "method": valyu_mode,
                        "error": vy.get("error") or "valyu_error",
                        "status_code": vy.get("status_code"),
                        "body": vy.get("body"),
                    })
                else:
                    rows = vy.get("results") or []
                    if rows:
                        # Map to RAG row shape
                        out_rows = []
                        for r in rows:
                            out_rows.append({
                                "id": r.get("id"),
                                "source": "valyu_web",
                                "title": r.get("title"),
                                "score": r.get("score"),
                                "snippet": r.get("snippet"),
                                "pmid": None,
                                "section": None,
                                "url": r.get("url"),
                            })
                        yield sse("matches", {"source": "valyu_web", "method": valyu_mode, "rows": out_rows})
                        all_groups.append(out_rows)
                    else:
                        yield sse("phase_error", {
                            "source": "valyu_web",
                            "method": valyu_mode,
                            "error": "no_evidence_rows",
                            "hint": "Ensure included_sources=valyu/valyu-pubmed and valyu_mode=search or answer.",
                        })
                yield sse("phase_end", {"source": "valyu_web", "method": valyu_mode})
            except Exception as e:
                yield sse("phase_error", {"source": "valyu_web", "method": valyu_mode, "error": str(e)})

        # ---------- Fusion ----------
        yield sse("phase_start", {"source": "fusion", "method": "rrf"})
        try:
            fused = rrf_fuse(all_groups, k=max(K, ctx_k))
            yield sse("matches", {"source": "fusion", "method": "rrf", "rows": fused[:K]})
        except Exception as e:
            yield sse("phase_error", {"source": "fusion", "method": "rrf", "error": str(e)})
            fused = []
        finally:
            yield sse("phase_end", {"source": "fusion", "method": "rrf"})

        ctx = fused[:ctx_k]
        yield sse("context", {"items": [
            {k: v for k, v in item.items() if k in ("id","source","title","score","snippet","pmid","section")}
            for item in ctx
        ]})

        # Citations: DB (for local rows) + Valyu URLs
        citations: List[Dict[str, Any]] = []
        non_web_ctx = [it for it in ctx if it["source"] != "valyu_web"]
        try:
            if non_web_ctx:
                async with (await resolve_pg_pool()).acquire() as conn2:
                    db_cites = await fetch_citation_rows(conn2, non_web_ctx)
            else:
                db_cites = []
        except Exception:
            db_cites = [{"id": r["id"], "source": r["source"], "title": r.get("title")} for r in non_web_ctx]

        for c in db_cites:
            c["url"] = c.get("url") or to_url(c)
            citations.append(c)

        for it in ctx:
            if it["source"] == "valyu_web":
                citations.append({
                    "id": str(it["id"]), "source": "valyu_web",
                    "title": it.get("title"), "url": next((r.get("url") for r in all_groups[-1] if r.get("id")==it["id"]), None)
                })

        if citations:
            yield sse("phase_start", {"source": "fusion", "method": "citations"})
            yield sse("citations", {"items": citations})
            yield sse("phase_end", {"source": "fusion", "method": "citations"})

        # Optional LLM synthesis
        if with_llm:
            yield sse("phase_start", {"source": "fusion", "method": "llm"})
            # (left as-is; you can wire to openai if desired)
            yield sse("phase_end", {"source": "fusion", "method": "llm"})

        yield sse("done", {"q": q})

    return StreamingResponse(streamer(), media_type="text/event-stream")
