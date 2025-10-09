from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import List, Dict

# Use the same session dependency everywhere
from server.db.session import get_session

router = APIRouter(prefix="/api/snomed", tags=["snomed"])


@router.get("/search")
async def search_snomed(
    q: str = Query(..., min_length=2, description="Search query for SNOMED terms"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results (1-100)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Search SNOMED CT descriptions with ILIKE matching, preferring active synonym
    terms over FSNs, and active concepts over inactive.
    """
    try:
        sql = """
        WITH ranked_results AS (
          SELECT DISTINCT ON (d.concept_id)
            d.concept_id,
            d.term,
            d.type_id,
            c.active AS concept_active,
            d.active AS description_active,
            CASE 
              WHEN d.type_id = 900000000000013009 THEN 1  -- Synonym
              WHEN d.type_id = 900000000000003001 THEN 2  -- FSN
              ELSE 3
            END AS type_rank,
            CASE 
              WHEN d.term ILIKE :exact_q THEN 1
              WHEN d.term ILIKE :q THEN 2
              ELSE 3
            END AS match_rank
          FROM ontology.descriptions d
          JOIN ontology.concepts c ON d.concept_id = c.concept_id
          WHERE d.term ILIKE :q
            AND d.active = TRUE
            AND c.active = TRUE
          ORDER BY d.concept_id, type_rank, match_rank, d.term
        )
        SELECT concept_id, term, type_id, concept_active, description_active
        FROM ranked_results
        ORDER BY match_rank, type_rank, term
        LIMIT :limit;
        """
        params = {"q": f"%{q}%", "exact_q": q, "limit": limit}
        rows = (await session.execute(text(sql), params)).mappings().all()
        return [dict(r) for r in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error searching SNOMED terms: {e}")


@router.get("/concept/{concept_id}")
async def get_snomed_concept(
    concept_id: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Return concept metadata, a few synonyms, and some outgoing relationships.
    """
    try:
        concept_sql = """
        SELECT 
            c.concept_id,
            c.effective_time,
            c.active,
            c.module_id,
            c.definition_status,
            d.term AS preferred_term,
            d.type_id AS term_type_id
        FROM ontology.concepts c
        LEFT JOIN ontology.descriptions d
          ON d.concept_id = c.concept_id
         AND d.type_id = 900000000000013009  -- Synonym
         AND d.active = TRUE
        WHERE c.concept_id = :concept_id
        LIMIT 1;
        """
        concept_row = (
            await session.execute(text(concept_sql), {"concept_id": concept_id})
        ).mappings().first()
        if not concept_row:
            raise HTTPException(status_code=404, detail=f"SNOMED concept {concept_id} not found")
        concept = dict(concept_row)

        syn_sql = """
        SELECT term, type_id, active
        FROM ontology.descriptions
        WHERE concept_id = :concept_id
          AND active = TRUE
        ORDER BY 
          CASE WHEN type_id = 900000000000013009 THEN 1 ELSE 2 END,
          term
        LIMIT 10;
        """
        syn_rows = (
            await session.execute(text(syn_sql), {"concept_id": concept_id})
        ).mappings().all()
        concept["synonyms"] = [dict(r) for r in syn_rows]

        rel_sql = """
        SELECT 
          r.relationship_id,
          r.source_id,
          r.destination_id,
          r.type_id,
          r.active,
          d.term AS destination_term
        FROM ontology.relationships r
        LEFT JOIN ontology.descriptions d
          ON d.concept_id = r.destination_id
         AND d.type_id = 900000000000013009  -- Synonym
         AND d.active = TRUE
        WHERE r.source_id = :concept_id
          AND r.active = TRUE
        ORDER BY r.type_id, destination_term
        LIMIT 20;
        """
        rel_rows = (
            await session.execute(text(rel_sql), {"concept_id": concept_id})
        ).mappings().all()
        concept["relationships"] = [dict(r) for r in rel_rows]

        return concept

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving SNOMED concept: {e}")


@router.get("/map/icd10cm/{cid}")
async def snomed_map_icd10cm(
    cid: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Return active rows from ontology.snomed_map_icd10cm for a SNOMED concept.
    Uses SNOMED 'referenced_component_id' as the source concept column.
    """
    try:
        sql = text(
            """
            SELECT
              referenced_component_id AS concept_id,
              map_group,
              map_priority,
              map_target,
              map_category_id,
              active,
              effective_time
            FROM ontology.snomed_map_icd10cm
            WHERE referenced_component_id = :cid
              AND active = TRUE
            ORDER BY map_group, map_priority;
            """
        )
        rows = (await session.execute(sql, {"cid": cid})).mappings().all()
        return {"concept_id": cid, "mappings": rows}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving ICD-10-CM mappings: {e}")


@router.get("/stats")
async def get_snomed_stats(
    session: AsyncSession = Depends(get_session),
):
    """
    Count rows across the core SNOMED tables + refset + ICD-10-CM map.
    """
    try:
        stats: Dict[str, int | str] = {}
        tables: List[tuple[str, str]] = [
            ("concepts", "ontology.concepts"),
            ("descriptions", "ontology.descriptions"),
            ("relationships", "ontology.relationships"),
            ("refset_members", "ontology.refset_members"),
            ("icd10cm_mappings", "ontology.snomed_map_icd10cm"),
        ]
        for name, fq in tables:
            try:
                count = (await session.execute(text(f"SELECT COUNT(*) FROM {fq}"))).scalar()
                stats[name] = count
            except Exception as e:
                stats[name] = f"Error: {e}"
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving SNOMED statistics: {e}")
