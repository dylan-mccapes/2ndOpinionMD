from fastapi import APIRouter, Query, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional
import time
import io
import csv
from datetime import datetime
from server.db.session import get_session

router = APIRouter(prefix="/api/clingen/actionability", tags=["clingen_actionability"])

@router.get("/summary")
async def get_summary(
    cohort: Optional[str] = Query(None, description="Filter by cohort (Adult/Pediatric)"),
    gene_symbol: Optional[str] = Query(None, description="Filter by gene symbol"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_session),
):
    """Get actionability summary data with optional filtering and pagination."""
    try:
        where_conditions = []
        params = {}
        
        if cohort:
            where_conditions.append("cohort = :cohort")
            params["cohort"] = cohort
        if gene_symbol:
            where_conditions.append("gene_symbol ILIKE :gene_symbol")
            params["gene_symbol"] = f"%{gene_symbol}%"
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        count_query = f"SELECT COUNT(*) FROM clingen.actionability_summary{where_clause}"
        count_result = await session.execute(text(count_query), params)
        total = count_result.scalar()
        
        data_query = f"""
        SELECT cohort, gene_symbol, hgnc_id, disease_name, disease_mondo_id, 
               actionability_assertion, report_date, source_url
        FROM clingen.actionability_summary
        {where_clause}
        ORDER BY cohort, gene_symbol, report_date DESC
        LIMIT :limit OFFSET :offset
        """
        params.update({"limit": limit, "offset": offset})
        
        result = await session.execute(text(data_query), params)
        items = [dict(row._mapping) for row in result]
        
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/summary/export")
async def export_summary_csv(
    cohort: Optional[str] = Query(None, description="Filter by cohort (Adult/Pediatric)"),
    gene_symbol: Optional[str] = Query(None, description="Filter by gene symbol"),
    session: AsyncSession = Depends(get_session),
):
    """Export actionability summary data as CSV."""
    try:
        where_conditions = []
        params = {}
        
        if cohort:
            where_conditions.append("cohort = :cohort")
            params["cohort"] = cohort
        if gene_symbol:
            where_conditions.append("gene_symbol ILIKE :gene_symbol")
            params["gene_symbol"] = f"%{gene_symbol}%"
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = f"""
        SELECT cohort, gene_symbol, hgnc_id, disease_name, disease_mondo_id, 
               actionability_assertion, report_date, source_url
        FROM clingen.actionability_summary
        {where_clause}
        ORDER BY cohort, gene_symbol, report_date DESC
        """
        
        result = await session.execute(text(query), params)
        rows = [dict(row._mapping) for row in result]
        
        output = io.StringIO()
        if rows:
            fieldnames = rows[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        output.seek(0)
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"clingen_summary_{today}.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

@router.get("/scoring")
async def get_scoring(
    cohort: Optional[str] = Query(None, description="Filter by cohort (Adult/Pediatric)"),
    gene_symbol: Optional[str] = Query(None, description="Filter by gene symbol"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_session),
):
    """Get actionability scoring data with optional filtering and pagination."""
    try:
        where_conditions = []
        params = {}
        
        if cohort:
            where_conditions.append("cohort = :cohort")
            params["cohort"] = cohort
        if gene_symbol:
            where_conditions.append("gene_symbol ILIKE :gene_symbol")
            params["gene_symbol"] = f"%{gene_symbol}%"
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        count_query = f"SELECT COUNT(*) FROM clingen.actionability_scoring{where_clause}"
        count_result = await session.execute(text(count_query), params)
        total = count_result.scalar()
        
        data_query = f"""
        SELECT cohort, gene_symbol, hgnc_id, disease_name, disease_mondo_id, 
               score, evidence_type
        FROM clingen.actionability_scoring
        {where_clause}
        ORDER BY cohort, gene_symbol, score DESC
        LIMIT :limit OFFSET :offset
        """
        params.update({"limit": limit, "offset": offset})
        
        result = await session.execute(text(data_query), params)
        items = [dict(row._mapping) for row in result]
        
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/scoring/export")
async def export_scoring_csv(
    cohort: Optional[str] = Query(None, description="Filter by cohort (Adult/Pediatric)"),
    gene_symbol: Optional[str] = Query(None, description="Filter by gene symbol"),
    session: AsyncSession = Depends(get_session),
):
    """Export actionability scoring data as CSV."""
    try:
        where_conditions = []
        params = {}
        
        if cohort:
            where_conditions.append("cohort = :cohort")
            params["cohort"] = cohort
        if gene_symbol:
            where_conditions.append("gene_symbol ILIKE :gene_symbol")
            params["gene_symbol"] = f"%{gene_symbol}%"
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = f"""
        SELECT cohort, gene_symbol, hgnc_id, disease_name, disease_mondo_id, 
               score, evidence_type
        FROM clingen.actionability_scoring
        {where_clause}
        ORDER BY cohort, gene_symbol, score DESC
        """
        
        result = await session.execute(text(query), params)
        rows = [dict(row._mapping) for row in result]
        
        output = io.StringIO()
        if rows:
            fieldnames = rows[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        output.seek(0)
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"clingen_scoring_{today}.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

@router.get("/assertions")
async def get_assertions(
    cohort: Optional[str] = Query(None, description="Filter by cohort (Adult/Pediatric)"),
    gene_symbol: Optional[str] = Query(None, description="Filter by gene symbol"),
    assertion_type: Optional[str] = Query(None, description="Filter by assertion type"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_session),
):
    """Get actionability assertions data with optional filtering and pagination."""
    try:
        where_conditions = []
        params = {}
        
        if cohort:
            where_conditions.append("cohort = :cohort")
            params["cohort"] = cohort
        if gene_symbol:
            where_conditions.append("gene_symbol ILIKE :gene_symbol")
            params["gene_symbol"] = f"%{gene_symbol}%"
        if assertion_type:
            where_conditions.append("assertion_type ILIKE :assertion_type")
            params["assertion_type"] = f"%{assertion_type}%"
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        count_query = f"SELECT COUNT(*) FROM clingen.actionability_assertions{where_clause}"
        count_result = await session.execute(text(count_query), params)
        total = count_result.scalar()
        
        data_query = f"""
        SELECT cohort, gene_symbol, hgnc_id, disease_name, disease_mondo_id, 
               assertion_type, assertion_description
        FROM clingen.actionability_assertions
        {where_clause}
        ORDER BY cohort, gene_symbol, assertion_type
        LIMIT :limit OFFSET :offset
        """
        params.update({"limit": limit, "offset": offset})
        
        result = await session.execute(text(data_query), params)
        items = [dict(row._mapping) for row in result]
        
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/assertions/export")
async def export_assertions_csv(
    cohort: Optional[str] = Query(None, description="Filter by cohort (Adult/Pediatric)"),
    gene_symbol: Optional[str] = Query(None, description="Filter by gene symbol"),
    assertion_type: Optional[str] = Query(None, description="Filter by assertion type"),
    session: AsyncSession = Depends(get_session),
):
    """Export actionability assertions data as CSV."""
    try:
        where_conditions = []
        params = {}
        
        if cohort:
            where_conditions.append("cohort = :cohort")
            params["cohort"] = cohort
        if gene_symbol:
            where_conditions.append("gene_symbol ILIKE :gene_symbol")
            params["gene_symbol"] = f"%{gene_symbol}%"
        if assertion_type:
            where_conditions.append("assertion_type ILIKE :assertion_type")
            params["assertion_type"] = f"%{assertion_type}%"
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        query = f"""
        SELECT cohort, gene_symbol, hgnc_id, disease_name, disease_mondo_id, 
               assertion_type, assertion_description
        FROM clingen.actionability_assertions
        {where_clause}
        ORDER BY cohort, gene_symbol, assertion_type
        """
        
        result = await session.execute(text(query), params)
        rows = [dict(row._mapping) for row in result]
        
        output = io.StringIO()
        if rows:
            fieldnames = rows[0].keys()
            writer = csv.DictWriter(output, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)
        
        output.seek(0)
        today = datetime.now().strftime("%Y-%m-%d")
        filename = f"clingen_assertions_{today}.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode('utf-8')),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")

@router.get("/variants")
async def get_variants(
    gene_symbol: Optional[str] = Query(None, description="Filter by gene symbol"),
    classification: Optional[str] = Query(None, description="Filter by classification"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_session),
):
    """Get variant pathogenicity data with optional filtering and pagination."""
    try:
        where_conditions = []
        params = {}
        
        if gene_symbol:
            where_conditions.append("gene_symbol ILIKE :gene_symbol")
            params["gene_symbol"] = f"%{gene_symbol}%"
        if classification:
            where_conditions.append("classification ILIKE :classification")
            params["classification"] = f"%{classification}%"
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        count_query = f"SELECT COUNT(*) FROM clingen.variant_pathogenicity{where_clause}"
        count_result = await session.execute(text(count_query), params)
        total = count_result.scalar()
        
        data_query = f"""
        SELECT gene_symbol, hgnc_id, variant_name, classification, last_evaluated, 
               review_status, condition_name, condition_identifiers
        FROM clingen.variant_pathogenicity
        {where_clause}
        ORDER BY gene_symbol, last_evaluated DESC
        LIMIT :limit OFFSET :offset
        """
        params.update({"limit": limit, "offset": offset})
        
        result = await session.execute(text(data_query), params)
        items = [dict(row._mapping) for row in result]
        
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.get("/quick")
async def get_quick(
    cohort: Optional[str] = Query(None, description="Filter by cohort (Adult/Pediatric)"),
    gene_symbol: Optional[str] = Query(None, description="Filter by gene symbol"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of results"),
    offset: int = Query(0, ge=0, description="Number of results to skip"),
    session: AsyncSession = Depends(get_session),
):
    """Get quick actionability data from materialized view with optional filtering and pagination."""
    try:
        where_conditions = []
        params = {}
        
        if cohort:
            where_conditions.append("cohort = :cohort")
            params["cohort"] = cohort
        if gene_symbol:
            where_conditions.append("gene_symbol ILIKE :gene_symbol")
            params["gene_symbol"] = f"%{gene_symbol}%"
        
        where_clause = " WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        count_query = f"SELECT COUNT(*) FROM clingen.v_actionability_quick{where_clause}"
        count_result = await session.execute(text(count_query), params)
        total = count_result.scalar()
        
        data_query = f"""
        SELECT cohort, gene_symbol, hgnc_id, disease_name, disease_mondo_id, 
               disease_key, actionability_assertion, score, evidence_type, report_date
        FROM clingen.v_actionability_quick
        {where_clause}
        ORDER BY cohort, gene_symbol, report_date DESC
        LIMIT :limit OFFSET :offset
        """
        params.update({"limit": limit, "offset": offset})
        
        result = await session.execute(text(data_query), params)
        items = [dict(row._mapping) for row in result]
        
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

@router.post("/refresh")
async def refresh_materialized_view(session: AsyncSession = Depends(get_session)):
    """Refresh the actionability quick materialized view with bulletproof concurrent/fallback logic."""
    start_time = time.perf_counter()
    mode = "concurrent"
    
    try:
        await session.execute(text("SET LOCAL statement_timeout = '60s'"))
        await session.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY clingen.v_actionability_quick"))
        await session.commit()
    except Exception as e:
        await session.rollback()
        error_str = str(e).lower()
        
        if any(phrase in error_str for phrase in [
            "requires a unique index", "cannot refresh", "deadlock", "timeout", "lock"
        ]):
            mode = "fallback"
            try:
                await session.execute(text("SET LOCAL statement_timeout = '120s'"))
                await session.execute(text("REFRESH MATERIALIZED VIEW clingen.v_actionability_quick"))
                await session.commit()
            except Exception as fallback_e:
                await session.rollback()
                try:
                    await session.execute(text("SET LOCAL statement_timeout = '180s'"))
                    await session.execute(text("REFRESH MATERIALIZED VIEW clingen.v_actionability_quick"))
                    await session.commit()
                except Exception as final_e:
                    await session.rollback()
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Failed to refresh materialized view: {str(final_e)}"
                    )
        else:
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to refresh materialized view: {str(e)}"
            )
    
    elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
    return {
        "ok": True,
        "mode": mode,
        "elapsed_ms": elapsed_ms
    }
