from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from server.db.session import get_session

router = APIRouter(prefix="/api/neurolex", tags=["neurolex"])

@router.get("/stats")
async def stats(session: AsyncSession = Depends(get_session)):
    row = (await session.execute(text("""
      SELECT COUNT(*)::int AS n_terms,
             COUNT(*) FILTER (WHERE array_length(synonyms,1) > 0)::int AS with_synonyms
      FROM ontology.neurolex_terms
    """))).mappings().one()
    return row

@router.get("/core_stats")
async def core_stats(session: AsyncSession = Depends(get_session)):
    row = (await session.execute(text("""
      SELECT COUNT(*)::int AS terms_core,
             COUNT(*) FILTER (WHERE definition IS NULL OR definition='')::int AS null_defs_core,
             COUNT(*) FILTER (WHERE (synonyms IS NULL OR array_length(synonyms,1)=0))::int AS no_syns_core
      FROM ontology.neurolex_terms
    """))).mappings().one()
    return row

@router.get("/term/{ilx_id}")
async def term(ilx_id: str, session: AsyncSession = Depends(get_session)):
    row = (await session.execute(text("""
      SELECT ilx_id, preferred_label, definition, synonyms, category, xrefs, parents, children
      FROM ontology.neurolex_terms WHERE ilx_id=:ilx
    """), {"ilx": ilx_id})).mappings().first()
    if not row:
        raise HTTPException(404, detail="Not found")
    return row

@router.get("/search")
async def search(q: str = Query(min_length=2),
                 limit: int = Query(25, ge=1, le=100),
                 session: AsyncSession = Depends(get_session)):
    rs = (await session.execute(text("""
      SELECT ilx_id, preferred_label, definition, synonyms, category
      FROM ontology.neurolex_terms
      WHERE preferred_label ILIKE :pat
         OR EXISTS (SELECT 1 FROM unnest(synonyms) s WHERE s ILIKE :pat)
      ORDER BY preferred_label
      LIMIT :lim
    """), {"pat": f"%{q}%", "lim": limit})).mappings().all()
    return {"items": rs, "total": len(rs), "limit": limit, "q": q}
