# -*- coding: utf-8 -*-
"""
CDC Opioid Prescribing & Care Journey routes
Prefix: /api/guidelines/cdc/opioid
Backed by: guidelines.cdc_docs / guidelines.cdc_sections (Postgres)
"""

import os
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, Query, HTTPException, Body
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

# ----------------------------- DB plumbing -----------------------------------

def _as_async_url(url: Optional[str]) -> str:
    default = "postgresql+asyncpg://2ndopinionmd@localhost:5432/2ndopinionmd"
    if not url:
        return default
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return default

DATABASE_URL = _as_async_url(os.getenv("DATABASE_URL"))
engine: AsyncEngine = create_async_engine(DATABASE_URL, pool_pre_ping=True, future=True)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session

# ----------------------------- Models ----------------------------------------

class SearchHit(BaseModel):
    section_id: int
    doc_slug: str
    doc_url: str
    doc_title: str
    heading: Optional[str] = None
    rec_number: Optional[str] = None
    tags: List[str] = []
    snippet: Optional[str] = None
    rank: float

class SectionOut(BaseModel):
    section_id: int
    doc_slug: str
    doc_url: str
    doc_title: str
    heading: Optional[str] = None
    rec_number: Optional[str] = None
    tags: List[str] = []
    text_html: Optional[str] = None
    text_plain: Optional[str] = None

class StatsOut(BaseModel):
    docs: int
    sections: int
    by_tag: List[Dict[str, Any]]
    by_recommendation: List[Dict[str, Any]]

# ----------------------------- Router ----------------------------------------

router = APIRouter()

@router.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1;"))
    return {"ok": True}

@router.get("/stats", response_model=StatsOut)
async def stats(db: AsyncSession = Depends(get_db)) -> StatsOut:
    q_docs = text("SELECT COUNT(*) FROM guidelines.cdc_docs;")
    q_secs = text("SELECT COUNT(*) FROM guidelines.cdc_sections;")
    q_tags = text("""
        SELECT tag, COUNT(*) AS n
        FROM (SELECT unnest(tags) AS tag FROM guidelines.cdc_sections) t
        GROUP BY tag
        ORDER BY n DESC, tag ASC;
    """)
    q_rec = text("""
        SELECT rec_number, COUNT(*) AS n
        FROM guidelines.cdc_sections
        WHERE rec_number IS NOT NULL AND rec_number <> ''
        GROUP BY rec_number ORDER BY rec_number ASC;
    """)
    docs = (await db.execute(q_docs)).scalar_one()
    secs = (await db.execute(q_secs)).scalar_one()
    tags = (await db.execute(q_tags)).mappings().all()
    recs = (await db.execute(q_rec)).mappings().all()
    return StatsOut(
        docs=int(docs),
        sections=int(secs),
        by_tag=[dict(r) for r in tags],
        by_recommendation=[dict(r) for r in recs],
    )

@router.get("/section/{section_id}", response_model=SectionOut)
async def get_section(section_id: int, db: AsyncSession = Depends(get_db)) -> SectionOut:
    q = text("""
        SELECT s.section_id, d.slug AS doc_slug, d.url AS doc_url, d.title AS doc_title,
               s.heading, s.rec_number, s.tags, s.text_html, s.text_plain
        FROM guidelines.cdc_sections s
        JOIN guidelines.cdc_docs d ON d.doc_id = s.doc_id
        WHERE s.section_id = :sid
        LIMIT 1;
    """)
    row = (await db.execute(q, {"sid": section_id})).mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Section not found")
    return SectionOut(**dict(row))

@router.get("/search", response_model=List[SearchHit])
async def search(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> List[SearchHit]:
    """
    Lexical full-text search over CDC sections with highlighted snippets.
    """
    sql = text("""
        WITH qry AS (SELECT plainto_tsquery('english', :q) AS tsq)
        SELECT
          s.section_id,
          d.slug AS doc_slug,
          d.url  AS doc_url,
          d.title AS doc_title,
          s.heading,
          s.rec_number,
          COALESCE(s.tags, '{}') AS tags,
          ts_headline(
            'english',
            s.text_plain,
            (SELECT tsq FROM qry),
            'StartSel=<b>,StopSel=</b>,MaxFragments=2,MinWords=5,MaxWords=25'
          ) AS snippet,
          ts_rank_cd(to_tsvector('english', s.text_plain), (SELECT tsq FROM qry)) AS rank
        FROM guidelines.cdc_sections s
        JOIN guidelines.cdc_docs d ON d.doc_id = s.doc_id
        WHERE to_tsvector('english', s.text_plain) @@ (SELECT tsq FROM qry)
        ORDER BY rank DESC, s.section_order ASC
        LIMIT :lim;
    """)
    rows = (await db.execute(sql, {"q": q, "lim": limit})).mappings().all()
    return [SearchHit(**dict(r)) for r in rows]

@router.get("/search_hybrid", response_model=List[SearchHit])
async def search_hybrid(
    q: str = Query(..., min_length=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    # 1) Lexical results (as before)
    sql_lex = text("""
      WITH qry AS (SELECT plainto_tsquery('english', :q) AS tsq)
      SELECT s.section_id, d.slug AS doc_slug, d.url AS doc_url, d.title AS doc_title,
             s.heading, s.rec_number, COALESCE(s.tags,'{}') AS tags,
             ts_headline('english', s.text_plain, (SELECT tsq FROM qry),
                         'StartSel=<b>,StopSel=</b>,MaxFragments=2,MinWords=5,MaxWords=25') AS snippet,
             ts_rank_cd(to_tsvector('english', s.text_plain), (SELECT tsq FROM qry)) AS rank
      FROM guidelines.cdc_sections s
      JOIN guidelines.cdc_docs d ON d.doc_id = s.doc_id
      WHERE to_tsvector('english', s.text_plain) @@ (SELECT tsq FROM qry)
      ORDER BY rank DESC, s.section_order ASC
      LIMIT :lim
    """)
    lex = (await db.execute(sql_lex, {"q": q, "lim": limit})).mappings().all()

    # 2) Vector results from rag_corpus (source='cdc_opioid')
    # Embed query on the app side and pass as :qvec (vector). If not available, skip.
    # Here we assume the caller hasn’t embedded; we fall back to lexical only.
    hits = [SearchHit(**dict(r)) for r in lex]
    return hits