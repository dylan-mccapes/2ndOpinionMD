from typing import Optional, List, Tuple
import asyncio
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel

from server.db.session import get_session
# import your existing models/helpers
# from .schemas import RAGSearchResponse, RAGItem
# from .emb import _embed_sync, _vec_literal
# from .pool import init_pool

router = APIRouter(prefix="/api/rag", tags=["rag"])

class RAGItem(BaseModel):
    id: str | int
    source: str
    title: str
    dist: float

class RAGSearchResponse(BaseModel):
    items: List[RAGItem]
    total_searched: int
    limit: int
    source: Optional[str] = None
    q: str

async def expand_with_chv(session, user_query: str, k_best: int = 10, k_fuzzy: int = 10, k_ngrams: int = 10) -> List[str]:
    """
    Returns unique lowercase expansions (strings). We avoid disparaged/misspelled n-grams.
    """
    sql = """
      WITH base AS (SELECT lower(:q) AS t),
      best AS (
        SELECT s.term
        FROM ontology.chv_best s, base b
        WHERE s.term_lower = b.t
        LIMIT :k_best
      ),
      fuzzy AS (
        SELECT s.term
        FROM ontology.synonyms s, base b
        WHERE s.source='CHV' AND s.term ILIKE '%'||b.t||'%'
        ORDER BY length(s.term) ASC
        LIMIT :k_fuzzy
      ),
      ngrams AS (
        SELECT n.term
        FROM ontology.chv_ngrams n, base b
        WHERE n.term ILIKE '%'||b.t||'%'
          AND NOT n.disparaged
          AND NOT n.misspelled
        ORDER BY length(n.term) ASC
        LIMIT :k_ngrams
      )
      SELECT lower(term) AS term FROM best
      UNION
      SELECT lower(term) FROM fuzzy
      UNION
      SELECT lower(term) FROM ngrams
    """
    rows = (await session.execute(
        text(sql),
        {"q": user_query, "k_best": k_best, "k_fuzzy": k_fuzzy, "k_ngrams": k_ngrams},
    )).scalars().all()
    # include the original query first
    out = [user_query.lower()] + [t for t in rows if t and t != user_query.lower()]
    # de-dupe preserving order
    seen, uniq = set(), []
    for t in out:
        if t not in seen:
            uniq.append(t); seen.add(t)
    return uniq[: (1 + k_best + k_fuzzy + k_ngrams)]

@router.get("/search", response_model=RAGSearchResponse)
async def semantic_search(
    q: str,
    source: Optional[str] = None,
    limit: int = Query(5, ge=1, le=50),
    probes: int = Query(8, ge=1, le=1000),
    expand: bool = Query(True, description="Expand with CHV best/raw + n-grams"),
):
    # 1) gather expansions
    exp_terms: list[str] = []
    pool = await init_pool()
    if expand:
        async with pool.acquire() as pg:
            # reuse your async session factory if you prefer
            async with get_session() as session:
                exp_terms = await expand_with_chv(session, q, k=8)

    # 2) build a small set of queries to embed
    variants = [q] + [f"{q} · {t}" for t in exp_terms[:8]]
    # embed each (sync helper in threadpool)
    try:
        loop = asyncio.get_event_loop()
        vecs = await asyncio.gather(*[
            loop.run_in_executor(None, _embed_sync, v) for v in variants
        ])
    except Exception as e:
        raise HTTPException(400, f"Embedding error: {e}")

    where = "TRUE"
    params: list = []
    if source:
        where = "rc.source = $1"
        params.append(source)

    # 3) query per embedding and keep the best (lowest dist) per doc
    # NOTE: ivfflat.probes set per statement
    async with pool.acquire() as conn:
        best: dict[int, tuple[float, str]] = {}  # id -> (dist, title)
        for vec, variant in zip(vecs, variants):
            vec_lit = _vec_literal(vec)
            sql = f"""
              WITH _set AS (SELECT set_config('ivfflat.probes', '{int(probes)}', true))
              , q AS (SELECT '{vec_lit}'::vector AS e)
              SELECT rc.id, rc.source, rc.title, (rc.embedding <=> q.e) AS dist
              FROM public.rag_corpus rc, q
              WHERE {where}
              ORDER BY rc.embedding <=> q.e
              LIMIT {int(limit)};
            """
            rows = await conn.fetch(sql, *params)
            for r in rows:
                rid = int(r["id"])
                dist = float(r["dist"])
                title = r["title"]
                if rid not in best or dist < best[rid][0]:
                    best[rid] = (dist, title)

    # 4) return top-N overall
    items_sorted = sorted(best.items(), key=lambda kv: kv[1][0])[:limit]
    items = [RAGItem(id=i, source=source or "mixed", title=t, dist=d) for i,(d,t) in items_sorted]
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
