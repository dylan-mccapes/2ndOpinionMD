from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from server.db.session import get_session

router = APIRouter(prefix="/api/loinc", tags=["loinc"])

@router.get("/search")
async def search_loinc(
    q: str = Query(..., min_length=2, description="Search query for LOINC terms"),
    system: Optional[str] = Query(None, description="Filter by system (e.g., 'Ser/Plas')"),
    scale_typ: Optional[str] = Query(None, description="Filter by scale type"),
    class_: Optional[str] = Query(None, alias="class", description="Filter by class"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results (1-100)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Search LOINC terms by name with optional filters.
    
    Returns LOINC terms matching the search query with ILIKE matching on
    shortname and long_common_name fields. Supports optional exact filters
    for system, scale_typ, and class.
    """
    try:
        clauses = ["(shortname ILIKE :q OR long_common_name ILIKE :q)"]
        params = {"q": f"%{q}%", "limit": limit}
        
        if system:
            clauses.append("system = :system")
            params["system"] = system
            
        if scale_typ:
            clauses.append("scale_typ = :scale_typ")
            params["scale_typ"] = scale_typ
            
        if class_:
            clauses.append("class = :class")
            params["class"] = class_
        
        sql = f"""
        SELECT 
            loinc_num, 
            long_common_name, 
            shortname, 
            component, 
            property, 
            time_aspct, 
            system, 
            scale_typ, 
            method_typ, 
            class
        FROM ontology.loinc_terms
        WHERE {" AND ".join(clauses)}
        ORDER BY 
            (shortname ILIKE :q) DESC, 
            (long_common_name ILIKE :q) DESC, 
            long_common_name
        LIMIT :limit
        """
        
        result = await session.execute(text(sql), params)
        rows = result.mappings().all()
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching LOINC terms: {str(e)}"
        )

@router.get("/term/{loinc_num}")
async def get_loinc_term(
    loinc_num: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get a specific LOINC term by its LOINC number.
    """
    try:
        sql = """
        SELECT 
            loinc_num, 
            long_common_name, 
            shortname, 
            component, 
            property, 
            time_aspct, 
            system, 
            scale_typ, 
            method_typ, 
            class,
            classtype,
            external_copyright_notice,
            status,
            version_first_released,
            version_last_changed,
            src_version,
            ingested_at
        FROM ontology.loinc_terms
        WHERE loinc_num = :loinc_num
        """
        
        result = await session.execute(text(sql), {"loinc_num": loinc_num})
        row = result.mappings().first()
        
        if not row:
            raise HTTPException(
                status_code=404,
                detail=f"LOINC term {loinc_num} not found"
            )
        
        return dict(row)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving LOINC term: {str(e)}"
        )

@router.get("/panel/{parent_loinc}")
async def get_loinc_panel(
    parent_loinc: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get panel members for a LOINC panel code.
    """
    try:
        sql = """
        SELECT 
            p.parent_loinc,
            p.child_loinc,
            p.sequence,
            p.display_text,
            p.observation_required,
            t.long_common_name as child_name,
            t.shortname as child_shortname
        FROM ontology.loinc_panels p
        LEFT JOIN ontology.loinc_terms t ON p.child_loinc = t.loinc_num
        WHERE p.parent_loinc = :parent_loinc
        ORDER BY p.sequence NULLS LAST, p.child_loinc
        """
        
        result = await session.execute(text(sql), {"parent_loinc": parent_loinc})
        rows = result.mappings().all()
        
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"LOINC panel {parent_loinc} not found"
            )
        
        return [dict(row) for row in rows]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving LOINC panel: {str(e)}"
        )
