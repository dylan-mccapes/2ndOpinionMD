from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Any, Dict
from server.db.session import get_session

router = APIRouter(prefix="/api/nice", tags=["nice"])

@router.get("/docs")
async def docs(limit: int = Query(100, ge=1, le=500),
               session: AsyncSession = Depends(get_session)):
    sql = text("""
      SELECT id, source_key, doc_key, title, url,
             to_char(published_at,'YYYY-MM-DD') AS published_at,
             to_char(fetched_at,'YYYY-MM-DD"T"HH24:MI:SS') AS fetched_at,
             COALESCE(length(text_full),0) AS text_full_len
      FROM guidelines.docs
      WHERE source_key='nice'
      ORDER BY id DESC LIMIT :lim
    """)
    rows = (await session.execute(sql, {"lim": limit})).mappings().all()
    return [dict(r) for r in rows]

@router.get("/sections")
async def sections(doc_key: str,
                   limit: int = Query(100, ge=1, le=1000),
                   session: AsyncSession = Depends(get_session)):
    sql = text("""
      SELECT s.id, s.doc_id, s.heading, s.anchor, s.text
      FROM guidelines.sections s
      JOIN guidelines.docs d ON d.id = s.doc_id
      WHERE d.source_key='nice' AND d.doc_key=:dk
      ORDER BY s.ord NULLS LAST, s.id
      LIMIT :lim
    """)
    rows = (await session.execute(sql, {"dk": doc_key, "lim": limit})).mappings().all()
    return rows

@router.get("/search")
async def search(q: str = Query(..., min_length=2),
                 limit: int = Query(20, ge=1, le=100),
                 session: AsyncSession = Depends(get_session)):
    sql = text("""
      WITH qry AS (SELECT websearch_to_tsquery('english', :q) AS tsq)
      SELECT c.id, COALESCE(c.title,'') AS title,
             (c.meta->>'doc_key')::text AS doc_key,
             c.sect_id,
             ts_rank(c.ts, (SELECT tsq FROM qry)) AS rank,
             substring(c.text for 240) AS preview,
             c.source
      FROM public.rag_corpus_chunks c, qry
      WHERE c.source='nice' AND c.ts @@ tsq
      ORDER BY rank DESC LIMIT :lim
    """)
    rows = (await session.execute(sql, {"q": q, "lim": limit})).mappings().all()
    return rows

