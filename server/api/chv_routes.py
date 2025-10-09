# server/api/chv_routes.py
from __future__ import annotations

import re
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Query, Depends, HTTPException, Body
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from server.db.session import get_session

router = APIRouter(prefix="/api/chv", tags=["CHV"])

_CUI_RX = re.compile(r"^C\d{7}$")


# ---------- Pydantic models ----------
class CHVNgramItem(BaseModel):
    term: str
    meta: bool
    mod: bool
    disparaged: bool
    misspelled: bool
    comment: Optional[str] = None


class CHVNgramSearchResponse(BaseModel):
    items: List[CHVNgramItem]
    total: int
    q: str
    limit: int


class CHVNgramMapItem(BaseModel):
    term: str
    cuis: List[str]


# ---------- CHV term search ----------
@router.get("/search")
async def chv_search(
    q: str = Query(..., min_length=2, description="Search text"),
    limit: int = Query(20, ge=1, le=100, description="Max rows"),
    mode: str = Query(
        "like",
        regex="^(like|prefix|fuzzy)$",
        description="Search mode: like | prefix | fuzzy",
    ),
    threshold: float = Query(
        0.3, ge=0.0, le=1.0, description="Similarity threshold (fuzzy only)"
    ),
    session: AsyncSession = Depends(get_session),
):
    """
    Search CHV lay terms → CUIs.

    - **like**: ILIKE %q%
    - **prefix**: ILIKE q%
    - **fuzzy**: trigram similarity(term, q) >= threshold (returns score)
    """
    try:
        if mode == "fuzzy":
            sql = """
                SELECT term, cui, similarity(term, :q) AS score
                FROM ontology.synonyms
                WHERE source='CHV' AND similarity(term, :q) >= :th
                ORDER BY score DESC, term
                LIMIT :limit
            """
            params = {"q": q, "th": float(threshold), "limit": limit}

        elif mode == "prefix":
            sql = """
                SELECT term, cui, NULL::float AS score
                FROM ontology.synonyms
                WHERE source='CHV' AND term ILIKE :q
                ORDER BY term
                LIMIT :limit
            """
            params = {"q": f"{q}%", "limit": limit}

        else:  # like
            sql = """
                SELECT term, cui, NULL::float AS score
                FROM ontology.synonyms
                WHERE source='CHV' AND term ILIKE :q
                ORDER BY term
                LIMIT :limit
            """
            params = {"q": f"%{q}%", "limit": limit}

        rows = (await session.execute(text(sql), params)).mappings().all()
        return [dict(r) for r in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"CHV search failed: {e}")


# ---------- Terms for a given CUI ----------
@router.get("/cui/{cui}")
async def chv_terms_for_cui(
    cui: str,
    limit: int = Query(200, ge=1, le=1000),
    session: AsyncSession = Depends(get_session),
):
    """List CHV terms for a given UMLS CUI."""
    if not _CUI_RX.match(cui):
        raise HTTPException(status_code=400, detail=f"Invalid CUI format: {cui}")

    try:
        sql = """
            SELECT term, cui
            FROM ontology.synonyms
            WHERE cui=:cui AND source='CHV'
            ORDER BY term
            LIMIT :limit
        """
        rows = (await session.execute(text(sql), {"cui": cui.upper(), "limit": limit})).mappings().all()
        return [dict(r) for r in rows]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lookup failed: {e}")


# ---------- Basic CHV stats ----------
@router.get("/stats")
async def chv_stats(session: AsyncSession = Depends(get_session)):
    """Basic CHV dataset stats."""
    try:
        sql = """
        SELECT
          (SELECT COUNT(*) FROM ontology.synonyms WHERE source='CHV') AS rows_total,
          (SELECT COUNT(DISTINCT cui) FROM ontology.synonyms WHERE source='CHV') AS distinct_cui,
          (SELECT COUNT(*) FROM ontology.synonyms WHERE source='CHV' AND term ~ '^[A-Za-z].*') AS alpha_terms
        """
        row = (await session.execute(text(sql))).mappings().first()
        return dict(row)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stats failed: {e}")


# ---------- Map a list of lay terms to candidate CUIs ----------
@router.post("/map")
async def chv_map_terms(
    payload: Dict[str, Any] = Body(
        ...,
        example={
            "terms": ["heart attack", "blood sugar", "pain med"],
            "mode": "fuzzy",
            "limit_per_term": 5,
            "threshold": 0.35,
            "use_best": True,
            "include_ngrams": True,
        },
    ),
    session: AsyncSession = Depends(get_session),
):
    """
    Map a list of lay terms to candidate CUIs.

    Body:
    - terms: list[str] (required)
    - mode: "like" | "prefix" | "fuzzy" (default: "fuzzy")
    - limit_per_term: int (default: 5)
    - threshold: float (only for fuzzy; default: 0.3)
    - use_best: bool (use ontology.chv_best for exact matches; default: true)
    - include_ngrams: bool (also return CHV n-gram→CUI expansions; default: true)
    """
    terms: List[str] = payload.get("terms") or []
    mode: str = str(payload.get("mode", "fuzzy")).lower()
    k: int = int(payload.get("limit_per_term", 5))
    th: float = float(payload.get("threshold", 0.3))
    use_best: bool = bool(payload.get("use_best", True))
    include_ngrams: bool = bool(payload.get("include_ngrams", True))

    if not terms or not isinstance(terms, list):
        raise HTTPException(status_code=400, detail="Provide a non-empty 'terms' list.")
    if mode not in {"like", "prefix", "fuzzy"}:
        raise HTTPException(status_code=400, detail="mode must be one of: like, prefix, fuzzy")

    try:
        results: Dict[str, List[Dict[str, Any]]] = {}

        for t in terms:
            t = (t or "").strip()
            if not t:
                results[t] = []
                continue

            out: List[Dict[str, Any]] = []

            # Exact match via chv_best if enabled
            if use_best:
                sql_best = """
                    SELECT term, cui, 1.0 AS score
                    FROM ontology.chv_best
                    WHERE term_lower = lower(:t)
                    ORDER BY term
                    LIMIT :k
                """
                rows_best = (await session.execute(text(sql_best), {"t": t, "k": k})).mappings().all()
                out.extend([dict(r) for r in rows_best])

            # Fallbacks via synonyms (CHV source)
            if mode == "fuzzy":
                sql_syn = """
                    SELECT term, cui, similarity(term, :q) AS score
                    FROM ontology.synonyms
                    WHERE source='CHV' AND similarity(term, :q) >= :th
                    ORDER BY score DESC, term
                    LIMIT :k
                """
                params_syn = {"q": t, "th": th, "k": k}
            elif mode == "prefix":
                sql_syn = """
                    SELECT term, cui, 0.8::float AS score
                    FROM ontology.synonyms
                    WHERE source='CHV' AND term ILIKE :q
                    ORDER BY term
                    LIMIT :k
                """
                params_syn = {"q": f"{t}%", "k": k}
            else:
                sql_syn = """
                    SELECT term, cui, 0.8::float AS score
                    FROM ontology.synonyms
                    WHERE source='CHV' AND term ILIKE :q
                    ORDER BY term
                    LIMIT :k
                """
                params_syn = {"q": f"%{t}%", "k": k}

            rows_syn = (await session.execute(text(sql_syn), params_syn)).mappings().all()
            out.extend([dict(r) for r in rows_syn])

            # Optional CHV n-gram expansions (map n-gram→CUI via chv_best)
            if include_ngrams:
                sql_ng = """
                    SELECT n.term, b.cui, 0.6::float AS score
                    FROM ontology.chv_ngrams n
                    LEFT JOIN ontology.chv_best b ON b.term_lower = n.term
                    WHERE n.term ILIKE :like
                    ORDER BY n.term
                    LIMIT :k
                """
                rows_ng = (await session.execute(
                    text(sql_ng),
                    {"like": f"%{t}%", "k": k},
                )).mappings().all()
                out.extend([dict(r) for r in rows_ng if r["cui"]])

            # De-duplicate by (term_lower, cui), keep highest score
            best: Dict[tuple, Dict[str, Any]] = {}
            for r in out:
                key = (r["term"].lower(), r["cui"])
                if key not in best or float(r["score"]) > float(best[key]["score"]):
                    best[key] = r

            results[t] = sorted(best.values(), key=lambda x: (-float(x["score"]), x["term"]))[:k]

        return {
            "results": results,
            "mode": mode,
            "limit_per_term": k,
            "threshold": th if mode == "fuzzy" else None,
            "include_ngrams": include_ngrams,
            "use_best": use_best,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Mapping failed: {e}")


# ---------- CHV n-grams: search (flags only) ----------
@router.get("/ngrams/search", response_model=CHVNgramSearchResponse)
async def search_ngrams(
    q: str,
    limit: int = Query(20, ge=1, le=200),
    include_disparaged: bool = False,
    include_misspelled: bool = False,
    session: AsyncSession = Depends(get_session),
):
    sql = """
      SELECT term, meta, mod, disparaged, misspelled, comment
      FROM ontology.chv_ngrams
      WHERE term ILIKE :q
        AND (:inc_disp OR NOT disparaged)
        AND (:inc_misp OR NOT misspelled)
      ORDER BY term
      LIMIT :limit
    """
    params = {
        "q": f"%{q}%",
        "limit": limit,
        "inc_disp": include_disparaged,
        "inc_misp": include_misspelled,
    }
    rows = (await session.execute(text(sql), params)).mappings().all()
    items = [CHVNgramItem(**r) for r in rows]
    return CHVNgramSearchResponse(items=items, total=len(items), q=q, limit=limit)


# ---------- CHV n-grams: map n-gram → CUIs via chv_best ----------
@router.get("/ngrams/map")
async def map_ngrams_to_cui(
    q: str,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    sql = """
      SELECT n.term, array_remove(array_agg(DISTINCT b.cui), NULL) AS cuis
      FROM ontology.chv_ngrams n
      LEFT JOIN ontology.chv_best b ON b.term_lower = n.term
      WHERE n.term ILIKE :q
      GROUP BY n.term
      ORDER BY n.term
      LIMIT :limit
    """
    rows = (await session.execute(text(sql), {"q": f"%{q}%", "limit": limit})).mappings().all()
    return [{"term": r["term"], "cuis": (r["cuis"] or [])} for r in rows]


# ---------- CHV n-grams: suggest (fuzzy/prefix) ----------
@router.get("/ngrams")
async def suggest_ngrams(
    q: str = Query(..., min_length=2, description="Substring to search in CHV n-grams"),
    limit: int = Query(10, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
):
    """
    Suggest CHV n-grams similar to q (uses pg_trgm). Single-statement variant
    so asyncpg/SQLAlchemy don't complain about multiple commands.
    """
    try:
        sql = """
        WITH _cfg AS (
            SELECT set_config('pg_trgm.similarity_threshold', :th, true)
        )
        SELECT term
        FROM ontology.chv_ngrams
        WHERE term % :q OR term ILIKE :like
        ORDER BY similarity(term, :q) DESC, length(term)
        LIMIT :limit
        """
        params = {"q": q, "like": f"%{q}%", "limit": limit, "th": "0.3"}
        rows = (await session.execute(text(sql), params)).mappings().all()
        return [r["term"] for r in rows]
    except Exception as e:
        raise HTTPException(500, f"Error searching CHV n-grams: {e}")

# ---------- CHV n-grams for a given CUI (via chv_best) ----------
@router.get("/ngrams/cui/{cui}")
async def ngrams_for_cui(
    cui: str,
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
):
    if not _CUI_RX.match(cui.upper()):
        raise HTTPException(status_code=400, detail=f"Invalid CUI: {cui}")

    sql = """
      SELECT n.term
      FROM ontology.chv_ngrams n
      JOIN ontology.chv_best b ON b.term_lower = n.term
      WHERE b.cui = :cui
      ORDER BY n.term
      LIMIT :limit
    """
    rows = (await session.execute(text(sql), {"cui": cui.upper(), "limit": limit})).mappings().all()
    return [r["term"] for r in rows]
