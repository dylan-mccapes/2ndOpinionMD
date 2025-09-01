from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, List, Dict, Any
from server.db.session import get_session

router = APIRouter(prefix="/api/snomed", tags=["snomed"])

@router.get("/search")
async def search_snomed(
    q: str = Query(..., min_length=2, description="Search query for SNOMED terms"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results (1-100)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Search SNOMED CT terms by description with preference for active preferred terms.
    
    Returns SNOMED concepts matching the search query with ILIKE matching on
    description terms, prioritizing preferred terms and active concepts.
    """
    try:
        sql = """
        WITH ranked_results AS (
          SELECT DISTINCT ON (d.concept_id)
            d.concept_id,
            d.term,
            d.type_id,
            c.active as concept_active,
            d.active as description_active,
            CASE 
              WHEN d.type_id = 900000000000013009 THEN 1  -- Synonym
              WHEN d.type_id = 900000000000003001 THEN 2  -- FSN
              ELSE 3
            END as type_rank,
            CASE 
              WHEN d.term ILIKE :exact_q THEN 1
              WHEN d.term ILIKE :q THEN 2
              ELSE 3
            END as match_rank
          FROM ontology.descriptions d
          JOIN ontology.concepts c ON d.concept_id = c.concept_id
          WHERE d.term ILIKE :q
            AND d.active = true
            AND c.active = true
          ORDER BY d.concept_id, type_rank, match_rank, d.term
        )
        SELECT concept_id, term, type_id, concept_active, description_active
        FROM ranked_results
        ORDER BY match_rank, type_rank, term
        LIMIT :limit
        """
        
        params = {
            "q": f"%{q}%",
            "exact_q": q,
            "limit": limit
        }
        
        result = await session.execute(text(sql), params)
        rows = result.mappings().all()
        
        return [dict(row) for row in rows]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching SNOMED terms: {str(e)}"
        )

@router.get("/concept/{concept_id}")
async def get_snomed_concept(
    concept_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Get detailed information about a specific SNOMED CT concept.
    
    Returns concept information, preferred term, synonyms, and relationships.
    """
    try:
        concept_sql = """
        SELECT 
            c.concept_id,
            c.effective_time,
            c.active,
            c.module_id,
            c.definition_status,
            d.term as preferred_term,
            d.type_id as term_type_id
        FROM ontology.concepts c
        LEFT JOIN ontology.descriptions d ON c.concept_id = d.concept_id 
            AND d.type_id = 900000000000013009  -- Synonym
            AND d.active = true
        WHERE c.concept_id = :concept_id
        LIMIT 1
        """
        
        concept_result = await session.execute(text(concept_sql), {"concept_id": concept_id})
        concept_row = concept_result.mappings().first()
        
        if not concept_row:
            raise HTTPException(
                status_code=404,
                detail=f"SNOMED concept {concept_id} not found"
            )
        
        concept_data = dict(concept_row)
        
        synonyms_sql = """
        SELECT term, type_id, active
        FROM ontology.descriptions
        WHERE concept_id = :concept_id AND active = true
        ORDER BY 
            CASE WHEN type_id = 900000000000013009 THEN 1 ELSE 2 END,
            term
        LIMIT 10
        """
        
        synonyms_result = await session.execute(text(synonyms_sql), {"concept_id": concept_id})
        synonyms_rows = synonyms_result.mappings().all()
        concept_data["synonyms"] = [dict(row) for row in synonyms_rows]
        
        relationships_sql = """
        SELECT 
            r.relationship_id,
            r.source_id,
            r.destination_id,
            r.type_id,
            r.active,
            d.term as destination_term
        FROM ontology.relationships r
        LEFT JOIN ontology.descriptions d ON r.destination_id = d.concept_id
            AND d.type_id = 900000000000013009  -- Synonym
            AND d.active = true
        WHERE r.source_id = :concept_id AND r.active = true
        ORDER BY r.type_id, d.term
        LIMIT 20
        """
        
        relationships_result = await session.execute(text(relationships_sql), {"concept_id": concept_id})
        relationships_rows = relationships_result.mappings().all()
        concept_data["relationships"] = [dict(row) for row in relationships_rows]
        
        return concept_data
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving SNOMED concept: {str(e)}"
        )

@router.get("/map/icd10cm/{concept_id}")
async def get_snomed_icd10cm_map(
    concept_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Get ICD-10-CM mappings for a SNOMED CT concept.
    
    Returns all active ICD-10-CM mappings with priority and group information.
    """
    try:
        sql = """
        SELECT 
            concept_id,
            map_group,
            map_priority,
            map_target,
            map_category_id,
            active,
            effective_time
        FROM ontology.snomed_map_icd10cm
        WHERE concept_id = :concept_id AND active = true
        ORDER BY map_group, map_priority
        """
        
        result = await session.execute(text(sql), {"concept_id": concept_id})
        rows = result.mappings().all()
        
        if not rows:
            raise HTTPException(
                status_code=404,
                detail=f"No ICD-10-CM mappings found for SNOMED concept {concept_id}"
            )
        
        return [dict(row) for row in rows]
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving ICD-10-CM mappings: {str(e)}"
        )

@router.get("/stats")
async def get_snomed_stats(
    session: AsyncSession = Depends(get_session),
):
    """
    Get SNOMED CT database statistics.
    
    Returns row counts for all SNOMED tables.
    """
    try:
        stats = {}
        
        tables = [
            ("concepts", "ontology.concepts"),
            ("descriptions", "ontology.descriptions"),
            ("relationships", "ontology.relationships"),
            ("refset_members", "ontology.refset_members"),
            ("icd10cm_mappings", "ontology.snomed_map_icd10cm")
        ]
        
        for table_name, table_path in tables:
            try:
                count_sql = f"SELECT COUNT(*) as count FROM {table_path}"
                result = await session.execute(text(count_sql))
                count = result.scalar()
                stats[table_name] = count
            except Exception as e:
                stats[table_name] = f"Error: {str(e)}"
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving SNOMED statistics: {str(e)}"
        )
