# server/api/rag_routes.py
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import os, asyncio
from openai import OpenAI
from .db import init_pool

router = APIRouter(prefix="/api/rag", tags=["RAG"])

EMBED_MODEL = os.getenv("GUIDE_EMBED_MODEL", "text-embedding-3-small")
client = OpenAI(timeout=float(os.getenv("OPENAI_TIMEOUT", "30")))

class RAGItem(BaseModel):
    id: int
    source: Optional[str] = None
    title: str
    dist: Optional[float] = None

class RAGSearchResponse(BaseModel):
    items: List[RAGItem]
    total_searched: int
    limit: int
    source: Optional[str] = None
    q: str

def _vec_literal(v: list[float]) -> str:
    return "[" + ",".join(str(x) for x in v) + "]"  # pgvector text format

def _embed_sync(text: str) -> list[float]:
    return client.embeddings.create(model=EMBED_MODEL, input=text).data[0].embedding

@router.get("/search", response_model=RAGSearchResponse)
async def semantic_search(
    q: str,
    source: Optional[str] = None,
    limit: int = Query(5, ge=1, le=50),
    probes: int = Query(8, ge=1, le=1000),
):
    try:
        vec = await asyncio.get_event_loop().run_in_executor(None, _embed_sync, q)
    except Exception as e:
        raise HTTPException(400, f"Embedding error: {e}")
    vec_lit = _vec_literal(vec)

    where = "TRUE"
    params: list = []
    if source:
        where = "rc.source = $1"
        params.append(source)

    # Single statement: set ivfflat.probes via set_config() inside a CTE
    sql = f"""
      WITH _set AS (
        SELECT set_config('ivfflat.probes', '{int(probes)}', true)
      ),
      q AS (SELECT '{vec_lit}'::vector AS e)
      SELECT rc.id, rc.source, rc.title, (rc.embedding <=> q.e) AS dist
      FROM public.rag_corpus rc, q
      WHERE {where}
      ORDER BY rc.embedding <=> q.e
      LIMIT {int(limit)};
    """

    pool = await init_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
    except Exception as e:
        raise HTTPException(500, f"DB error: {e}")

    items = [RAGItem(id=r["id"], source=r["source"], title=r["title"], dist=float(r["dist"])) for r in rows]
    return RAGSearchResponse(items=items, total_searched=len(items), limit=limit, source=source, q=q)

@router.get("/neighbors/{id}", response_model=List[RAGItem])
async def neighbors(
    id: int,
    source: Optional[str] = None,
    limit: int = Query(5, ge=1, le=50),
    probes: int = Query(8, ge=1, le=1000),
):
    if source:
        where = "rc.source = $2 AND rc.id <> $1"
        params = [id, source]
    else:
        where = "rc.id <> $1"
        params = [id]

    sql = f"""
      WITH _set AS (
        SELECT set_config('ivfflat.probes', '{int(probes)}', true)
      ),
      q AS (
        SELECT embedding AS e FROM public.rag_corpus WHERE id = $1
      )
      SELECT rc.id, rc.source, rc.title, (rc.embedding <=> q.e) AS dist
      FROM public.rag_corpus rc, q
      WHERE {where}
      ORDER BY rc.embedding <=> q.e
      LIMIT {int(limit)};
    """

    pool = await init_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(sql, *params)
    except Exception as e:
        raise HTTPException(500, f"DB error: {e}")

    return [RAGItem(id=r["id"], source=r["source"], title=r["title"], dist=float(r["dist"])) for r in rows]
