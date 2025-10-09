from fastapi import APIRouter, Query, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from .db import get_pool  # adjust import to your project

router = APIRouter(prefix="/api/chv/ngrams", tags=["CHV ngrams"])

class NgramItem(BaseModel):
    term: str
    meta: bool
    mod: bool
    disparaged: bool
    misspelled: bool
    comment: Optional[str] = None

@router.get("/search", response_model=List[NgramItem])
async def ngram_search(q: str, limit: int = Query(10, ge=1, le=100)):
    sql = """
      SELECT term, meta, mod, disparaged, misspelled, comment
      FROM ontology.chv_ngrams
      WHERE term ILIKE '%' || $1 || '%'
      ORDER BY length(term), term
      LIMIT $2
    """
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, q.lower(), limit)
    return [NgramItem(**dict(r)) for r in rows]

