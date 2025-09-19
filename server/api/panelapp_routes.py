# server/api/panelapp_routes.py
from fastapi import APIRouter, Query, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, bindparam
from typing import Optional
from server.db.session import get_session

router = APIRouter(prefix="/api/panelapp", tags=["panelapp"])

@router.get("/search")
async def search_panelapp(
    q: str = Query(..., min_length=1, max_length=200),
    limit: int = Query(25, ge=1, le=200),
    only_green: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    sql = """
    SELECT panel_id, panel_name, panel_version, gene_symbol, confidence_level
    FROM molecular.gene_panels
    WHERE ts @@ websearch_to_tsquery('english', :q)
      AND (:only_green::bool IS FALSE OR confidence_level ILIKE 'High')
    ORDER BY panel_name, gene_symbol
    LIMIT :limit
    """
    rows = (await session.execute(
        text(sql).bindparams(
            bindparam("q", q),
            bindparam("limit", limit),
            bindparam("only_green", only_green),
        )
    )).mappings().all()
    return {"q": q, "count": len(rows), "results": list(rows)}

@router.get("/panel/{panel_id}")
async def panel_detail(
    panel_id: int,
    version: Optional[str] = Query(None, description="If omitted, returns latest version"),
    only_green: bool = Query(False),
    session: AsyncSession = Depends(get_session),
):
    if version:
        where = "panel_id = :panel_id AND panel_version = :version"
    else:
        where = """
        panel_id = :panel_id AND panel_version = (
            SELECT panel_version FROM molecular.gene_panels
            WHERE panel_id = :panel_id
            ORDER BY panel_version DESC
            LIMIT 1
        )"""

    sql = f"""
    SELECT panel_id, panel_name, panel_version, gene_symbol, confidence_level,
           mode_of_inheritance, hgnc_id, ensembl_gene_id_grch37, ensembl_gene_id_grch38
    FROM molecular.gene_panels
    WHERE {where}
      AND (:only_green::bool IS FALSE OR confidence_level ILIKE 'High')
    ORDER BY gene_symbol
    """
    params = {"panel_id": panel_id, "version": version, "only_green": only_green}
    rows = (await session.execute(text(sql), params)).mappings().all()
    if not rows:
        raise HTTPException(404, detail="Panel not found")
    header = {
        "panel_id": rows[0]["panel_id"],
        "panel_name": rows[0]["panel_name"],
        "panel_version": rows[0]["panel_version"],
        "n_genes": len(rows),
    }
    return {"panel": header, "genes": list(rows)}

@router.get("/stats")
async def panelapp_stats(session: AsyncSession = Depends(get_session)):
    sql = """
    SELECT panel_id, panel_name, panel_version, signed_off, COUNT(*) AS genes
    FROM molecular.gene_panels
    GROUP BY 1,2,3,4
    ORDER BY panel_name, panel_version DESC;
    """
    rows = (await session.execute(text(sql))).mappings().all()
    return {"panels": list(rows)}

