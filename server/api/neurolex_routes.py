# server/api/neurolex_routes.py
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from server.db.session import get_session

router = APIRouter(prefix="/api/neurolex", tags=["neurolex"])

@router.get("/stats")
async def stats(session: AsyncSession = Depends(get_session)):
    row = (await session.execute(text("""
      SELECT
        COUNT(*)::int AS n_terms,
        COUNT(*) FILTER (WHERE array_length(synonyms,1) > 0)::int AS with_synonyms,
        (SELECT COUNT(*)::int FROM ontology.neurolex_annotations) AS n_annotations
      FROM ontology.neurolex
    """))).mappings().one()
    return dict(row)

@router.get("/term/{ilx_id}")
async def term(ilx_id: str, session: AsyncSession = Depends(get_session)):
    row = (await session.execute(text("""
      SELECT ilx_id, iri, label, definition, synonyms, parents, ancestors, xrefs
      FROM ontology.neurolex WHERE ilx_id=:ilx
    """), {"ilx": ilx_id})).mappings().first()
    if not row:
        raise HTTPException(404, detail="Not found")
    return dict(row)

@router.get("/search")
async def search(q: str = Query(min_length=2),
                 limit: int = Query(25, ge=1, le=100),
                 session: AsyncSession = Depends(get_session)):
    # Use trigram on label and an expression index on array_to_string(synonyms,' ')
    rs = (await session.execute(text("""
      SELECT ilx_id, label, definition, synonyms, iri
      FROM ontology.neurolex
      WHERE label ILIKE :pat
         OR array_to_string(synonyms,' ') ILIKE :pat
      ORDER BY label
      LIMIT :lim
    """), {"pat": f"%{q}%", "lim": limit})).mappings().all()
    return {"items": [dict(r) for r in rs], "total": len(rs), "limit": limit, "q": q}
