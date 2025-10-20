# server/api/disgenet_routes.py
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

# pg_read should be a SYNC helper that returns List[Dict]
# signature: pg_read(sql: str, params: tuple | None = None) -> List[Dict[str, Any]]
from .db import pg_read

router = APIRouter(prefix="/api/disgenet", tags=["disgenet"])

@router.get("/stats")
def disgenet_stats():
    rows = pg_read("""
        SELECT COUNT(*)::int AS rows,
               COUNT(DISTINCT assoc_id)::int AS assoc_ids,
               COUNT(DISTINCT gene_symbol)::int AS genes,
               COUNT(DISTINCT disease_name)::int AS diseases
        FROM molecular.disgenet_associations
    """)
    return JSONResponse(jsonable_encoder(rows))

@router.get("/gene/{symbol}")
def disgenet_by_gene(
    symbol: str,
    limit: int = Query(10, ge=1, le=200),
):
    rows = pg_read("""
        SELECT assoc_id,
               gene_ncbi_id,
               gene_symbol,
               disease_name,
               disease_umls_cui,
               disease_type,
               score::float AS score,
               num_pmids::int AS num_pmids,
               year_initial::int AS year_initial,
               year_final::int   AS year_final
        FROM molecular.disgenet_associations
        WHERE UPPER(gene_symbol) = UPPER(%s)
        ORDER BY score DESC NULLS LAST, num_pmids DESC NULLS LAST
        LIMIT %s
    """, (symbol, limit))
    return JSONResponse(jsonable_encoder(rows))

@router.get("/search")
def disgenet_search(
    gene: Optional[str] = None,
    disease: Optional[str] = None,
    min_score: float = Query(0.0, ge=0.0, le=1.0),
    limit: int = Query(25, ge=1, le=200),
):
    where = ["score >= %s"]
    params: List[Any] = [min_score]

    if gene:
        where.append("gene_symbol ILIKE %s")
        params.append(f"%{gene}%")
    if disease:
        where.append("disease_name ILIKE %s")
        params.append(f"%{disease}%")

    sql = f"""
        SELECT assoc_id,
               gene_ncbi_id,
               gene_symbol,
               disease_name,
               disease_umls_cui,
               disease_type,
               score::float AS score,
               num_pmids::int AS num_pmids
        FROM molecular.disgenet_associations
        WHERE {' AND '.join(where)}
        ORDER BY score DESC NULLS LAST, num_pmids DESC NULLS LAST
        LIMIT %s
    """
    params.append(limit)
    rows = pg_read(sql, tuple(params))
    return JSONResponse(jsonable_encoder(rows))

@router.get("/disease/{name}")
def disgenet_by_disease(name: str, limit: int = Query(10, ge=1, le=200)):
    rows = pg_read("""
        SELECT assoc_id, gene_ncbi_id, gene_symbol, disease_name, disease_umls_cui,
               disease_type, score::float AS score, num_pmids::int AS num_pmids
        FROM molecular.disgenet_associations
        WHERE UPPER(disease_name) = UPPER(%s)
        ORDER BY score DESC NULLS LAST, num_pmids DESC NULLS LAST
        LIMIT %s
    """, (name, limit))
    return JSONResponse(jsonable_encoder(rows))

@router.get("/geneid/{ncbi_id}")
def disgenet_by_geneid(ncbi_id: int, limit: int = Query(10, ge=1, le=200)):
    rows = pg_read("""
        SELECT assoc_id, gene_ncbi_id, gene_symbol, disease_name, disease_umls_cui,
               disease_type, score::float AS score, num_pmids::int AS num_pmids
        FROM molecular.disgenet_associations
        WHERE gene_ncbi_id = %s
        ORDER BY score DESC NULLS LAST, num_pmids DESC NULLS LAST
        LIMIT %s
    """, (ncbi_id, limit))
    return JSONResponse(jsonable_encoder(rows))

