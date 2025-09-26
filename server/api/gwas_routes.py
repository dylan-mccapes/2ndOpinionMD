# server/api/gwas_routes.py
from typing import Dict, Any
from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from server.db.session import get_session

router = APIRouter(prefix="/api/gwas", tags=["gwas"])

def row_to_dict(r) -> Dict[str, Any]:
    # works with SQLAlchemy RowMapping from .mappings()
    m = dict(r)
    return {
        "study_accession": m.get("study_accession"),
        "pubmed_id": m.get("pubmed_id"),
        "disease_trait": m.get("disease_trait"),
        "mapped_trait": m.get("mapped_trait"),
        "snps": m.get("snps"),
        "strongest_snp_risk_allele": m.get("strongest_snp_risk_allele"),
        "p_value": m.get("p_value"),
        "or_beta": m.get("or_beta"),
        "reported_genes": m.get("reported_genes"),
        "mapped_gene": m.get("mapped_gene"),
        "chr": m.get("chr"),
        "chr_pos": m.get("chr_pos"),
        "date_added": m.get("date_added"),
    }

@router.get("/search")
async def gwas_search(
    q: str = Query(..., min_length=2),
    limit: int = Query(25, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    """
    Search GWAS hits by trait/gene text (FTS) or rsID in SNPS field.
    Orders by p-value (ascending).
    """
    sql = text("""
        SELECT study_accession, pubmed_id, disease_trait, mapped_trait, snps,
               strongest_snp_risk_allele, p_value, or_beta, reported_genes,
               mapped_gene, chr, chr_pos, date_added
        FROM molecular.gwas_hits
        WHERE
          to_tsvector('english',
              coalesce(disease_trait,'') || ' ' ||
              coalesce(mapped_trait,'')  || ' ' ||
              coalesce(reported_genes,'')|| ' ' ||
              coalesce(mapped_gene,'')
          ) @@ plainto_tsquery('english', :q)
          OR snps ILIKE '%'||:q||'%'
        ORDER BY p_value ASC NULLS LAST
        LIMIT :limit
    """)
    rows = (await session.execute(sql, {"q": q, "limit": limit})).mappings().all()
    return {"items": [row_to_dict(r) for r in rows], "total": len(rows), "limit": limit, "q": q}

@router.get("/snp/{rsid}")
async def gwas_by_snp(
    rsid: str,
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    sql = text("""
        SELECT study_accession, pubmed_id, disease_trait, mapped_trait, snps,
               strongest_snp_risk_allele, p_value, or_beta, reported_genes,
               mapped_gene, chr, chr_pos, date_added
        FROM molecular.gwas_hits
        WHERE snps ILIKE ('%' || :rsid || '%')
        ORDER BY p_value ASC NULLS LAST
        LIMIT :limit
    """)
    rows = (await session.execute(sql, {"rsid": rsid, "limit": limit})).mappings().all()
    return {"items": [row_to_dict(r) for r in rows], "total": len(rows), "limit": limit, "rsid": rsid}

@router.get("/trait/{trait}")
async def gwas_by_trait(
    trait: str,
    limit: int = Query(50, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
):
    sql = text("""
        SELECT study_accession, pubmed_id, disease_trait, mapped_trait, snps,
               strongest_snp_risk_allele, p_value, or_beta, reported_genes,
               mapped_gene, chr, chr_pos, date_added
        FROM molecular.gwas_hits
        WHERE disease_trait ILIKE ('%' || :trait || '%')
           OR mapped_trait  ILIKE ('%' || :trait || '%')
        ORDER BY p_value ASC NULLS LAST
        LIMIT :limit
    """)
    rows = (await session.execute(sql, {"trait": trait, "limit": limit})).mappings().all()
    return {"items": [row_to_dict(r) for r in rows], "total": len(rows), "limit": limit, "trait": trait}

@router.get("/stats")
async def gwas_stats(session: AsyncSession = Depends(get_session)):
    sql = text("""
        SELECT
          COUNT(*)::int AS n_rows,
          MIN(p_value)  AS best_p,
          COUNT(*) FILTER (WHERE disease_trait ILIKE '%sclerosis%')::int AS n_sclerosis,
          COUNT(*) FILTER (WHERE disease_trait ~* 'spondyloarthritis|ankylosing spondylitis|psoriatic arthritis')::int AS n_spa
        FROM molecular.gwas_hits
    """)
    row = (await session.execute(sql)).mappings().first()
    return dict(row) if row else {}

