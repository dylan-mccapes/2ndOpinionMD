from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Optional
from server.db.session import get_session

router = APIRouter(prefix="/api/hpo", tags=["hpo"])

def to_underscore_id(h: str) -> str:
    """Normalize incoming HPO id to DB form: HP_0000000."""
    if not h:
        return h
    s = h.strip().upper().replace(":", "_")
    # HP0001250 -> HP_0001250
    if s.startswith("HP") and not s.startswith("HP_"):
        s = "HP_" + s[2:]
    # 0001250 -> HP_0001250
    if s.isdigit():
        s = f"HP_{s.zfill(7)}"
    return s

def to_colon_id(h: str) -> str:
    """Normalize outgoing HPO id to API form: HP:0000000."""
    if not h:
        return h
    s = h.strip().upper().replace("_", ":")
    if s.startswith("HP") and not s.startswith("HP:"):
        s = "HP:" + s[2:]
    return s

def colonize_list(xs):
    return [to_colon_id(x) for x in xs] if xs else []

@router.get("/search")
async def search_hpo(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """
    Search HPO terms (name + synonyms). Returns IDs in HP:NNNNNNN form.
    """
    try:
        sql = """
        SELECT hpo_id, name AS label
        FROM ontology.hpo_terms
        WHERE name ILIKE :q
           OR EXISTS (SELECT 1 FROM unnest(synonyms) s WHERE s ILIKE :q)
        ORDER BY name
        LIMIT :limit
        """
        rows = (await session.execute(text(sql), {"q": f"%{q}%", "limit": limit})).mappings().all()
        return [{"hpo_id": to_colon_id(r["hpo_id"]), "label": r["label"]} for r in rows]
    except Exception as e:
        raise HTTPException(500, f"Error searching HPO terms: {e}")

@router.get("/term/{hpo_id}")
async def get_hpo_term(
    hpo_id: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get HPO term by ID. Accepts HP:0001250 / HP_0001250 / HP0001250 / 0001250.
    Returns ID in HP:NNNNNNN form.
    """
    try:
        h_db = to_underscore_id(hpo_id)
        sql = """
        SELECT hpo_id, name AS label, definition, synonyms, parent_ids
        FROM ontology.hpo_terms
        WHERE hpo_id = :h
        """
        row = (await session.execute(text(sql), {"h": h_db})).mappings().first()
        if not row:
            raise HTTPException(404, f"HPO term {hpo_id} not found")

        data = dict(row)
        return {
            "hpo_id": to_colon_id(data["hpo_id"]),
            "label": data["label"],
            "definition": data.get("definition"),
            "synonyms": data.get("synonyms") or [],
            "parents": colonize_list(data.get("parent_ids")),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, f"Error retrieving HPO term: {e}")

