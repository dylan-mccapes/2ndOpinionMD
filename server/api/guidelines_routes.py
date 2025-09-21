# server/api/guidelines_routes.py
from typing import Optional, List, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel

from server.db.session import get_session

router = APIRouter(prefix="/api/guidelines", tags=["guidelines"])

# --- Models -------------------------------------------------------------------
class GuidelineDoc(BaseModel):
    id: int
    source_key: str
    doc_key: str
    title: Optional[str] = None
    url: Optional[str] = None
    published_at: Optional[str] = None
    fetched_at: Optional[str] = None
    text_full_len: int

class GuidelineSection(BaseModel):
    id: int
    doc_id: int
    heading: Optional[str] = None
    anchor: Optional[str] = None
    text: str

class GuidelinesSearchHit(BaseModel):
    id: int
    title: str
    doc_key: Optional[str] = None
    sect_id: Optional[int] = None
    rank: float
    preview: Optional[str] = None
    source: str = "nice"

# --- Endpoints ----------------------------------------------------------------

@router.get("/stats")
async def stats(session: AsyncSession = Depends(get_session)) -> Dict[str, Any]:
    q1 = text("""
      SELECT d.source_key, COUNT(*)::bigint AS docs
      FROM guidelines.docs d
      GROUP BY 1 ORDER BY 1
    """)
    q2 = text("""
      SELECT d.source_key, d.doc_key, COUNT(*)::bigint AS sections
      FROM guidelines.sections s JOIN guidelines.docs d ON d.id = s.doc_id
      GROUP BY 1,2 ORDER BY 1,2
    """)
    q3 = text("""
      SELECT
        'rag_corpus' AS tbl, COUNT(*)::bigint AS n,
        SUM((source='nice')::int)::bigint AS nice_n
      FROM public.rag_corpus
      UNION ALL
      SELECT
        'rag_corpus_chunks' AS tbl, COUNT(*)::bigint AS n,
        SUM((source='nice')::int)::bigint AS nice_n
      FROM public.rag_corpus_chunks
    """)

    r1 = [dict(row) for row in (await session.execute(q1)).mappings()]
    r2 = [dict(row) for row in (await session.execute(q2)).mappings()]
    r3 = [dict(row) for row in (await session.execute(q3)).mappings()]

    return {"docs_by_source": r1, "sections_by_doc": r2, "rag_tables": r3}

@router.get("/docs", response_model=List[GuidelineDoc])
async def list_docs(
    source: Optional[str] = Query(None, description="e.g., nice, cks, who_eml, cdc_opioid, va_dod"),
    session: AsyncSession = Depends(get_session),
):
    base = """
      SELECT id, source_key, doc_key, title, url,
             to_char(published_at,'YYYY-MM-DD') AS published_at,
             to_char(fetched_at,'YYYY-MM-DD"T"HH24:MI:SS') AS fetched_at,
             COALESCE(length(text_full),0) AS text_full_len
      FROM guidelines.docs
    """
    if source:
        q = text(base + " WHERE source_key = :src ORDER BY id DESC LIMIT :lim")
        rows = (await session.execute(q, {"src": source, "lim": 200})).mappings().all()
    else:
        q = text(base + " ORDER BY id DESC LIMIT :lim")
        rows = (await session.execute(q, {"lim": 200})).mappings().all()
    return [dict(r) for r in rows]

@router.get("/doc/{doc_key}")
async def get_doc(doc_key: str, session: AsyncSession = Depends(get_session)):
    q = text("""
      SELECT d.*, COALESCE(length(d.text_full),0) AS text_full_len
      FROM guidelines.docs d
      WHERE d.doc_key = :dk
    """)
    row = (await session.execute(q, {"dk": doc_key})).mappings().first()
    if not row:
        raise HTTPException(404, f"doc_key {doc_key} not found")
    return dict(row)

@router.get("/sections", response_model=List[GuidelineSection])
async def list_sections(
    doc_key: str,
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    q = text("""
      SELECT s.id, s.doc_id, s.heading, s.anchor, s.text
      FROM guidelines.sections s
      JOIN guidelines.docs d ON d.id = s.doc_id
      WHERE d.doc_key = :dk
      ORDER BY s.id
      LIMIT :lim
    """)
    rows = (await session.execute(q, {"dk": doc_key, "lim": limit})).mappings().all()
    return rows

@router.get("/search", response_model=List[GuidelinesSearchHit])
async def search_guidelines(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """
    Full-text search over NICE chunks (hits come from public.rag_corpus_chunks).
    """
    sql = text("""
      WITH qry AS (SELECT websearch_to_tsquery('english', :q) AS tsq)
      SELECT c.id,
             COALESCE(c.title,'') AS title,
             (c.meta->>'doc_key')::text AS doc_key,
             c.sect_id,
             ts_rank(c.ts, (SELECT tsq FROM qry)) AS rank,
             substring(c.text for 240) AS preview,
             c.source
      FROM public.rag_corpus_chunks c, qry
      WHERE c.source = 'nice' AND c.ts @@ tsq
      ORDER BY rank DESC
      LIMIT :lim
    """)
    rows = (await session.execute(sql, {"q": q, "lim": limit})).mappings().all()
    return rows

