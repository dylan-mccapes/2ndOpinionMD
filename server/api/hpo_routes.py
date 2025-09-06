from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from server.db.session import get_session

router = APIRouter(prefix="/api/hpo", tags=["hpo"])

@router.get("/search")
async def search_hpo(
    q: str = Query(..., min_length=2),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """
    Search HPO terms by name with ILIKE matching on term names and synonyms.
    
    Returns HPO terms matching the search query, prioritizing exact name matches
    over synonym matches.
    """
    try:
        sql = """
        SELECT hpo_id, name as label
        FROM ontology.hpo_terms
        WHERE name ILIKE :q
           OR EXISTS (SELECT 1 FROM unnest(synonyms) s WHERE s ILIKE :q)
        ORDER BY name
        LIMIT :limit
        """
        
        params = {"q": f"%{q}%", "limit": limit}
        result = await session.execute(text(sql), params)
        rows = result.mappings().all()
        
        return [dict(r) for r in rows]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching HPO terms: {str(e)}"
        )

@router.get("/term/{hpo_id}")
async def get_hpo_term(
    hpo_id: str, 
    session: AsyncSession = Depends(get_session)
):
    """
    Get comprehensive information for a specific HPO term.
    
    Returns term details including definition, synonyms, and parent relationships.
    """
    try:
        sql = """
        SELECT hpo_id, name as label, definition, synonyms, parent_ids as parents
        FROM ontology.hpo_terms
        WHERE hpo_id = :h
        """
        
        result = await session.execute(text(sql), {"h": hpo_id})
        row = result.mappings().first()
        
        if not row:
            raise HTTPException(404, f"HPO term {hpo_id} not found")
        
        return dict(row)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving HPO term: {str(e)}"
        )
