from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from server.db.session import get_session
import re

router = APIRouter(prefix="/api/rxnorm", tags=["rxnorm"])

def normalize_ndc(ndc: str) -> str:
    """
    Normalize NDC to 11-digit format following 5-4-2 segment structure.
    
    NDC format is typically: LLLLL-PPPP-SS where:
    - LLLLL: 5-digit labeler code
    - PPPP: 4-digit product code  
    - SS: 2-digit package code
    
    Examples:
    - "0009-3015-01" -> "00093015001"
    - "9-3015-1" -> "00093015001"
    """
    if '-' in ndc or ' ' in ndc:
        segments = re.split(r'[-\s]', ndc.strip())
        if len(segments) == 3:
            all_digits = ''.join(segments)
            return all_digits.zfill(11)
    
    digits_only = re.sub(r'[^0-9]', '', ndc)
    
    if len(digits_only) == 10:
        digits_only = '0' + digits_only
    
    if len(digits_only) == 11:
        return digits_only
    
    if len(digits_only) < 11:
        digits_only = digits_only.zfill(11)
    elif len(digits_only) > 11:
        digits_only = digits_only[:11]
    
    return digits_only

@router.get("/search")
async def search_rxnorm(
    q: str = Query(..., min_length=2, description="Search query for drug names"),
    tty: Optional[str] = Query(None, description="Filter by TTY (comma-separated list)"),
    limit: int = Query(20, ge=1, le=50, description="Maximum number of results (1-50)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Search RxNorm drugs by name with optional TTY filters.
    
    Returns distinct RXCUIs with preferred strings, ranked by relevance.
    """
    try:
        clauses = ["str ILIKE :q"]
        params = {"q": f"%{q}%", "limit": limit}
        
        if tty:
            tty_list = [t.strip() for t in tty.split(',')]
            clauses.append("tty = ANY(:tty_array)")
            params["tty_array"] = tty_list
        
        sql = f"""
        WITH ranked_results AS (
          SELECT DISTINCT ON (rxcui)
            rxcui,
            str,
            tty,
            CASE 
              WHEN ispref = 'Y' THEN 1
              WHEN tty IN ('SCD', 'SBD') THEN 2
              WHEN tty IN ('BPCK', 'GPCK') THEN 3
              WHEN tty IN ('IN', 'PIN') THEN 4
              ELSE 5
            END as tty_rank,
            CASE 
              WHEN str ILIKE :q THEN 1
              ELSE 2
            END as match_rank
          FROM ontology.rxnorm_conso
          WHERE {" AND ".join(clauses)}
          ORDER BY rxcui, tty_rank, match_rank, str
        )
        SELECT rxcui, str, tty
        FROM ranked_results
        ORDER BY match_rank, tty_rank, str
        LIMIT :limit
        """
        
        result = await session.execute(text(sql), params)
        rows = result.mappings().all()
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching RxNorm terms: {str(e)}"
        )

@router.get("/drug/{rxcui}")
async def get_rxnorm_drug(
    rxcui: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Get detailed information about a specific drug by RXCUI.
    
    Returns concept information, synonyms, relationships, and NDCs.
    """
    try:
        concept_sql = """
        WITH preferred AS (
          SELECT str, tty
          FROM ontology.rxnorm_conso
          WHERE rxcui = :rxcui AND ispref = 'Y'
          LIMIT 1
        ),
        synonyms AS (
          SELECT tty, str,
                 ROW_NUMBER() OVER (PARTITION BY tty ORDER BY str) as rn
          FROM ontology.rxnorm_conso
          WHERE rxcui = :rxcui AND ispref != 'Y'
        )
        SELECT 
          (SELECT str FROM preferred) as preferred_name,
          (SELECT tty FROM preferred) as preferred_tty,
          COALESCE(
            json_object_agg(
              tty, 
              json_agg(str ORDER BY str) 
              FILTER (WHERE rn <= 3)
            ) FILTER (WHERE tty IS NOT NULL),
            '{}'::json
          ) as synonyms_by_tty
        FROM synonyms
        """
        
        concept_result = await session.execute(text(concept_sql), {"rxcui": rxcui})
        concept_row = concept_result.mappings().first()
        
        if not concept_row or not concept_row.preferred_name:
            raise HTTPException(
                status_code=404,
                detail=f"Drug with RXCUI {rxcui} not found"
            )
        
        relations_sql = """
        SELECT 
          r.rel,
          r.rela,
          r.rxcui2,
          c.str as related_name,
          c.tty as related_tty
        FROM ontology.rxnorm_rel r
        LEFT JOIN ontology.rxnorm_conso c ON r.rxcui2 = c.rxcui AND c.ispref = 'Y'
        WHERE r.rxcui1 = :rxcui
        ORDER BY r.rel, r.rela, c.str
        LIMIT 50
        """
        
        relations_result = await session.execute(text(relations_sql), {"rxcui": rxcui})
        relations_rows = relations_result.mappings().all()
        
        ndcs_sql = """
        SELECT ndc_norm, ndc_raw, sab
        FROM ontology.rxnorm_ndc
        WHERE rxcui = :rxcui
        ORDER BY ndc_norm
        LIMIT 10
        """
        
        ndcs_result = await session.execute(text(ndcs_sql), {"rxcui": rxcui})
        ndcs_rows = ndcs_result.mappings().all()
        
        return {
            "rxcui": rxcui,
            "concept": {
                "preferred_name": concept_row.preferred_name,
                "preferred_tty": concept_row.preferred_tty,
                "synonyms_by_tty": concept_row.synonyms_by_tty or {}
            },
            "relations": [
                {
                    "rel": row.rel,
                    "rela": row.rela,
                    "rxcui2": row.rxcui2,
                    "related_name": row.related_name,
                    "related_tty": row.related_tty
                }
                for row in relations_rows
            ],
            "ndcs": [
                {
                    "ndc_norm": row.ndc_norm,
                    "ndc_raw": row.ndc_raw,
                    "sab": row.sab
                }
                for row in ndcs_rows
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving drug information: {str(e)}"
        )

@router.get("/ndc/{ndc}")
async def get_rxnorm_ndc(
    ndc: str,
    session: AsyncSession = Depends(get_session),
):
    """
    Look up drugs by NDC code.
    
    Returns normalized NDC and matching RXCUIs with drug names.
    """
    try:
        ndc_norm = normalize_ndc(ndc)
        
        sql = """
        SELECT 
          n.ndc_norm,
          n.ndc_raw,
          n.rxcui,
          c.str,
          c.tty,
          n.sab
        FROM ontology.rxnorm_ndc n
        LEFT JOIN ontology.rxnorm_conso c ON n.rxcui = c.rxcui AND c.ispref = 'Y'
        WHERE n.ndc_norm = :ndc_norm
        ORDER BY c.str
        """
        
        result = await session.execute(text(sql), {"ndc_norm": ndc_norm})
        rows = result.mappings().all()
        
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"NDC {ndc} (normalized: {ndc_norm}) not found"
            )
        
        return {
            "ndc_input": ndc,
            "ndc_norm": ndc_norm,
            "matches": [
                {
                    "rxcui": row.rxcui,
                    "str": row.str,
                    "tty": row.tty,
                    "ndc_raw": row.ndc_raw,
                    "sab": row.sab
                }
                for row in rows
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error looking up NDC: {str(e)}"
        )
