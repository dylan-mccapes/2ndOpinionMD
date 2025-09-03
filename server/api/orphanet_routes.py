from fastapi import APIRouter, Query, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
from server.db.session import get_session

router = APIRouter(prefix="/api/orphanet", tags=["orphanet"])

@router.get("/search")
async def search_orphanet(
    q: str = Query(..., min_length=2, description="Search query for Orphanet diseases"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results (1-100)"),
    session: AsyncSession = Depends(get_session),
):
    """
    Search Orphanet diseases by name with ILIKE matching on disease names and synonyms.
    
    Returns diseases matching the search query, prioritizing exact name matches
    over synonym matches.
    """
    try:
        sql = """
        WITH hits AS (
          SELECT orpha_code, name, 1 AS rnk 
          FROM ontology.orphanet_diseases 
          WHERE name ILIKE :q
          UNION ALL
          SELECT s.orpha_code, d.name, 2 AS rnk
          FROM ontology.orphanet_synonyms s
          JOIN ontology.orphanet_diseases d USING (orpha_code)
          WHERE s.synonym ILIKE :q
        )
        SELECT orpha_code, name
        FROM hits
        ORDER BY rnk, name
        LIMIT :limit
        """
        
        params = {"q": f"%{q}%", "limit": limit}
        result = await session.execute(text(sql), params)
        rows = result.mappings().all()
        
        return [dict(r) for r in rows]
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error searching Orphanet diseases: {str(e)}"
        )

@router.get("/disease/{orpha_code}")
async def get_disease(
    orpha_code: int,
    session: AsyncSession = Depends(get_session),
):
    """
    Get comprehensive information for a specific Orphanet disease.
    
    Returns disease details including synonyms, external references,
    associated genes, and phenotypes.
    """
    try:
        dsql = """
        SELECT orpha_code, name, disorder_type, definition, ingested_at
        FROM ontology.orphanet_diseases 
        WHERE orpha_code = :oc
        """
        drow = (await session.execute(text(dsql), {"oc": orpha_code})).mappings().first()
        
        if not drow:
            raise HTTPException(404, f"Orphanet disease {orpha_code} not found")

        ssql = """
        SELECT synonym, lang 
        FROM ontology.orphanet_synonyms 
        WHERE orpha_code = :oc 
        ORDER BY synonym 
        LIMIT 50
        """
        syns = (await session.execute(text(ssql), {"oc": orpha_code})).mappings().all()

        xsql = """
        SELECT source, ref 
        FROM ontology.orphanet_external_refs 
        WHERE orpha_code = :oc 
        ORDER BY source, ref 
        LIMIT 100
        """
        xrefs = (await session.execute(text(xsql), {"oc": orpha_code})).mappings().all()

        gsql = """
        SELECT gene_symbol, entrez_id, ensembl_id, association, inheritance, evidence
        FROM ontology.orphanet_gene_links
        WHERE orpha_code = :oc
        ORDER BY gene_symbol NULLS LAST
        LIMIT 100
        """
        genes = (await session.execute(text(gsql), {"oc": orpha_code})).mappings().all()

        psql = """
        SELECT hpo_id, hpo_label, frequency, diagnostic, negated
        FROM ontology.orphanet_phenotype_links
        WHERE orpha_code = :oc
        ORDER BY hpo_label NULLS LAST
        LIMIT 200
        """
        phenos = (await session.execute(text(psql), {"oc": orpha_code})).mappings().all()

        return {
            "orpha_code": drow.orpha_code,
            "name": drow.name,
            "disorder_type": drow.disorder_type,
            "definition": drow.definition,
            "ingested_at": drow.ingested_at,
            "synonyms": [dict(s) for s in syns],
            "external_refs": [dict(x) for x in xrefs],
            "genes": [dict(g) for g in genes],
            "phenotypes": [dict(p) for p in phenos],
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving Orphanet disease: {str(e)}"
        )

@router.get("/stats")
async def get_orphanet_stats(session: AsyncSession = Depends(get_session)):
    """Get basic statistics about the Orphanet dataset."""
    try:
        sql = """
        SELECT 
            (SELECT COUNT(*) FROM ontology.orphanet_diseases) as diseases,
            (SELECT COUNT(*) FROM ontology.orphanet_synonyms) as synonyms,
            (SELECT COUNT(*) FROM ontology.orphanet_external_refs) as external_refs,
            (SELECT COUNT(*) FROM ontology.orphanet_gene_links) as gene_links,
            (SELECT COUNT(*) FROM ontology.orphanet_phenotype_links) as phenotype_links
        """
        
        result = await session.execute(text(sql))
        row = result.mappings().first()
        
        return dict(row)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving Orphanet statistics: {str(e)}"
        )
