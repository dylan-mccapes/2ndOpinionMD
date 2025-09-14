# server/api/notes_routes.py
from typing import Optional, Literal, Dict, Any, List
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import conint
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text as sql_text, bindparam
import sqlalchemy as sa

from server.db.session import get_session

router = APIRouter()
log = logging.getLogger(__name__)

Domain = Literal["discharge", "radiology"]

def _binds(params: Dict[str, Any]):
    """Type binds so asyncpg never guesses."""
    b = []
    for k, v in params.items():
        if k in ("limit", "sid", "hid", "hadm_id"):
            b.append(bindparam(k, type_=sa.Integer()))
        elif k in ("domain", "q", "track"):
            b.append(bindparam(k, type_=sa.String()))
        else:
            b.append(bindparam(k))
    return b

async def _run(session: AsyncSession, sql: str, params: Dict[str, Any]):
    try:
        stmt = sql_text(sql).bindparams(*_binds(params))
        res = await session.execute(stmt, params)
        return res.mappings().all()
    except Exception as e:
        log.exception("Notes route SQL error: %s", e)
        raise HTTPException(status_code=500, detail="Database error")

# -------------------------------
# MIMIC-IV notes (discharge / radiology)
# -------------------------------

@router.get("/api/notes/miv/random")
async def miv_random(
    domain: Optional[Domain] = Query(None, description="discharge|radiology"),
    limit: conint(ge=1, le=100) = Query(10),
    session: AsyncSession = Depends(get_session),
):
    params: Dict[str, Any] = {"limit": int(limit)}
    conds: List[str] = []
    if domain:
        params["domain"] = domain.lower()
        conds.append("lower(domain) = lower(:domain)")

    where = f"WHERE {' AND '.join(conds)}" if conds else ""
    sql = f"""
        SELECT note_id, domain, subject_id, hadm_id, charttime,
               LEFT(COALESCE(note_text,''), 1000) AS preview
          FROM text.mimiciv_notes
          {where}
         ORDER BY random()
         LIMIT :limit
    """
    return await _run(session, sql, params)

@router.get("/api/notes/miv/by-subject/{subject_id}")
async def miv_by_subject(
    subject_id: int,
    domain: Optional[Domain] = Query(None),
    limit: conint(ge=1, le=100) = Query(10),
    session: AsyncSession = Depends(get_session),
):
    params: Dict[str, Any] = {"sid": subject_id, "limit": int(limit)}
    conds: List[str] = ["subject_id = :sid"]
    if domain:
        params["domain"] = domain.lower()
        conds.append("lower(domain) = lower(:domain)")

    sql = f"""
        SELECT note_id, domain, subject_id, hadm_id, charttime,
               LEFT(COALESCE(note_text,''), 1000) AS preview
          FROM text.mimiciv_notes
         WHERE {' AND '.join(conds)}
         ORDER BY charttime DESC
         LIMIT :limit
    """
    return await _run(session, sql, params)

@router.get("/api/notes/miv/by-hadm/{hadm_id}")
async def miv_by_hadm(
    hadm_id: int,
    domain: Optional[Domain] = Query(None),
    limit: conint(ge=1, le=100) = Query(10),
    session: AsyncSession = Depends(get_session),
):
    params: Dict[str, Any] = {"hid": hadm_id, "limit": int(limit)}
    conds: List[str] = ["hadm_id = :hid"]
    if domain:
        params["domain"] = domain.lower()
        conds.append("lower(domain) = lower(:domain)")

    sql = f"""
        SELECT note_id, domain, subject_id, hadm_id, charttime,
               LEFT(COALESCE(note_text,''), 1000) AS preview
          FROM text.mimiciv_notes
         WHERE {' AND '.join(conds)}
         ORDER BY charttime DESC
         LIMIT :limit
    """
    return await _run(session, sql, params)

@router.get("/api/notes/miv/search")
async def miv_search(
    q: str = Query(..., min_length=1, description="plainto_tsquery text"),
    domain: Optional[Domain] = Query(None),
    limit: conint(ge=1, le=100) = Query(20),
    session: AsyncSession = Depends(get_session),
):
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    params: Dict[str, Any] = {"q": q, "limit": int(limit)}
    conds: List[str] = ["tsv @@ plainto_tsquery('english', :q)"]
    if domain:
        params["domain"] = domain.lower()
        conds.append("lower(domain) = lower(:domain)")

    sql = f"""
        SELECT note_id, domain, subject_id, hadm_id, charttime,
               ts_headline(
                 'english',
                 COALESCE(note_text,''),
                 plainto_tsquery('english', :q),
                 'StartSel=<b>,StopSel=</b>,MaxFragments=2,MinWords=5,MaxWords=25'
               ) AS preview
          FROM text.mimiciv_notes
         WHERE {' AND '.join(conds)}
         ORDER BY charttime DESC
         LIMIT :limit
    """
    return await _run(session, sql, params)

# -------------------------------
# A&P (n2c2-style sample)
# -------------------------------

@router.get("/api/notes/ap/random")
async def ap_random(
    track: str = Query("MIII-AP"),
    limit: conint(ge=1, le=100) = Query(3),
    session: AsyncSession = Depends(get_session),
):
    params = {"track": track, "limit": int(limit)}
    sql = """
        WITH r AS (
            SELECT r.rel_id, r.label, r.note_id, n.note_text,
                   a.span_start AS a_s, a.span_end AS a_e,
                   p.span_start AS p_s, p.span_end AS p_e,
                   n.hadm_id, n.subject_id
              FROM text.n2c2_ap_relations r
              JOIN text.n2c2_ap_sections a ON a.section_id = r.assess_id
              JOIN text.n2c2_ap_sections p ON p.section_id = r.plan_id
              JOIN text.n2c2_notes n       ON n.note_id    = r.note_id
             WHERE r.track = :track
             ORDER BY random()
             LIMIT :limit
        )
        SELECT rel_id,
               :track AS track,
               label,
               substr(note_text, a_s+1, a_e - a_s) AS assessment,
               substr(note_text, p_s+1, p_e - p_s) AS plan_item,
               note_id, hadm_id, subject_id
          FROM r
    """
    return await _run(session, sql, params)

@router.get("/api/notes/ap/by-hadm/{hadm_id}")
async def ap_by_hadm(
    hadm_id: int,
    track: Optional[str] = Query(None),
    limit: conint(ge=1, le=200) = Query(25),
    session: AsyncSession = Depends(get_session),
):
    params: Dict[str, Any] = {"hadm_id": hadm_id, "limit": int(limit)}
    cond_track = ""
    if track:
        params["track"] = track
        cond_track = "AND r.track = :track"

    sql = f"""
        WITH r AS (
            SELECT r.rel_id, r.label, r.note_id, n.note_text,
                   a.span_start AS a_s, a.span_end AS a_e,
                   p.span_start AS p_s, p.span_end AS p_e,
                   n.hadm_id, n.subject_id
              FROM text.n2c2_ap_relations r
              JOIN text.n2c2_ap_sections a ON a.section_id = r.assess_id
              JOIN text.n2c2_ap_sections p ON p.section_id = r.plan_id
              JOIN text.n2c2_notes n       ON n.note_id    = r.note_id
             WHERE n.hadm_id = :hadm_id
               {cond_track}
             ORDER BY r.rel_id DESC
             LIMIT :limit
        )
        SELECT rel_id,
               COALESCE(:track, 'unknown') AS track,
               label,
               substr(note_text, a_s+1, a_e - a_s) AS assessment,
               substr(note_text, p_s+1, p_e - p_s) AS plan_item,
               note_id, hadm_id, subject_id
          FROM r
    """
    return await _run(session, sql, params)

