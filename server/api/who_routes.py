from fastapi import APIRouter, Query, HTTPException
import os, asyncpg

router = APIRouter(prefix="/api/who", tags=["WHO"])
_DSN = (os.environ.get("DATABASE_URL") or os.environ.get("SYNC_DATABASE_URL") or "").replace("+asyncpg","")

async def _fetch(query: str, args: dict | None = None):
    if not _DSN:
        raise RuntimeError("DATABASE_URL or SYNC_DATABASE_URL not set")
    conn = await asyncpg.connect(_DSN)
    try:
        return await conn.fetch(query, *([] if not args else list(args.values())))
    finally:
        await conn.close()

@router.get("/eml/stats")
async def eml_stats():
    rows = await _fetch("""
        SELECT count(*) FILTER (WHERE list_type='EML')  AS n_eml,
               count(*) FILTER (WHERE list_type='EMLc') AS n_emlc
        FROM guidelines.who_eml_medicines
    """)
    return dict(rows[0]) if rows else {"n_eml":0,"n_emlc":0}

@router.get("/eml/search")
async def eml_search(
    q: str = Query(..., min_length=2),
    atc: str | None = None,
    icd11: str | None = None,
    aware: str | None = None,
    limit: int = Query(20, ge=1, le=100),
    prefix: bool = False,
):
    """
    Search WHO EML medicines by free text, with optional filters:
      - atc: ATC code prefix (e.g., J01)
      - icd11: ICD-11 code prefix
      - aware: Access | Watch | Reserve
      - prefix: when true, use prefix FTS (to_tsquery with :*)
    """
    # Build FTS condition
    if prefix:
        # to_tsquery with prefix tokens, e.g. "amoxi:* & clavulanic:*"
        terms = re.findall(r"\w+", q)
        tsq = " & ".join(f"{t}:*" for t in terms) if terms else q
        conds = ["m.ts @@ to_tsquery('english', $1)"]
        params: list[object] = [tsq]
    else:
        conds = ["m.ts @@ plainto_tsquery('english', $1)"]
        params = [q]

    pi = 2  # next $-param index

    if atc:
        conds.append(
            f"EXISTS (SELECT 1 FROM guidelines.who_eml_atc a "
            f"        WHERE a.med_id = m.med_id AND a.atc_code ILIKE ${pi})"
        )
        params.append(atc.strip().upper().replace(" ", "") + "%")
        pi += 1

    if icd11:
        conds.append(
            f"EXISTS (SELECT 1 FROM guidelines.who_eml_icd11 i "
            f"        WHERE i.med_id = m.med_id AND i.icd11_code ILIKE ${pi})"
        )
        params.append(icd11.strip().upper().replace(" ", "") + "%")
        pi += 1

    if aware:
        conds.append(f"m.antibiotic_group = ${pi}")
        params.append(aware.strip().title())
        pi += 1

    params.append(limit)
    sql = f"""
      SELECT m.med_id, m.inn, m.list_type, m.section_path, m.antibiotic_group
      FROM guidelines.who_eml_medicines m
      WHERE {' AND '.join(conds)}
      ORDER BY m.inn
      LIMIT ${pi}
    """

    conn = await asyncpg.connect(_DSN)
    try:
        rows = await conn.fetch(sql, *params)
    finally:
        await conn.close()

    return [dict(r) for r in rows]

@router.get("/eml/medicine/{med_id}")
async def eml_medicine(med_id: int):
    rows = await _fetch("""
        SELECT m.*,
               ARRAY(SELECT atc_code FROM guidelines.who_eml_atc a WHERE a.med_id=m.med_id) AS atc,
               ARRAY(SELECT icd11_code FROM guidelines.who_eml_icd11 i WHERE i.med_id=m.med_id) AS icd11,
               ARRAY(SELECT dose_form FROM guidelines.who_eml_formulations f WHERE f.med_id=m.med_id) AS forms,
               ARRAY(SELECT alt_inn   FROM guidelines.who_eml_alternatives al WHERE al.med_id=m.med_id) AS alts
        FROM guidelines.who_eml_medicines m
        WHERE m.med_id=$1
    """, {"med_id": med_id})
    return dict(rows[0]) if rows else {}

@router.get("/eml/medicine/by-inn/{inn}")
async def eml_medicine_by_inn(inn: str):
    rows = await _fetch("""
        SELECT m.*,
               ARRAY(SELECT atc_code FROM guidelines.who_eml_atc a WHERE a.med_id=m.med_id) AS atc,
               ARRAY(SELECT icd11_code FROM guidelines.who_eml_icd11 i WHERE i.med_id=m.med_id) AS icd11
        FROM guidelines.who_eml_medicines m
        WHERE m.inn ILIKE $1
        ORDER BY list_type DESC, inn
        LIMIT 5
    """, {"inn": inn})
    return [dict(r) for r in rows]

@router.get("/aware/stats")
async def aware_stats(antibacterials_only: bool = True):
    where = "WHERE EXISTS (SELECT 1 FROM guidelines.who_eml_atc a WHERE a.med_id=m.med_id AND a.atc_code ILIKE 'J01%')" if antibacterials_only else ""
    rows = await _fetch(f"""
        SELECT COALESCE(NULLIF(m.antibiotic_group,''),'(Unlabeled)') AS group_name,
               COUNT(*)::int AS n
        FROM guidelines.who_eml_medicines m
        {where}
        GROUP BY 1
        ORDER BY 1
    """)
    return [dict(r) for r in rows]

@router.get("/eml/by-aware/{group}")
async def eml_by_aware(group: str, limit: int = 100):
    g = group.strip().title()
    if g not in ("Access","Watch","Reserve"):
        raise HTTPException(status_code=400, detail="group must be Access, Watch, or Reserve")
    rows = await _fetch("""
      SELECT med_id, inn, section_path, antibiotic_group
      FROM guidelines.who_eml_medicines
      WHERE antibiotic_group = $1
      ORDER BY inn
      LIMIT $2
    """, {"group": g, "limit": limit})
    return [dict(r) for r in rows]

# Committee
@router.get("/committee/stats")
async def committee_stats():
    rows = await _fetch("""
        SELECT (SELECT count(*) FROM guidelines.who_committee_reports)  AS n_reports,
               (SELECT count(*) FROM guidelines.who_committee_sections) AS n_sections
    """)
    return dict(rows[0]) if rows else {"n_reports":0,"n_sections":0}

@router.get("/committee/search")
async def committee_search(q: str = Query(..., min_length=2), limit: int = 10):
    rows = await _fetch("""
        SELECT section_id, heading,
               ts_headline('english', text, plainto_tsquery('english', $1),
                           'StartSel=<b>,StopSel=</b>,MaxFragments=2,MinWords=5,MaxWords=25') AS preview
        FROM guidelines.who_committee_sections
        WHERE ts @@ plainto_tsquery('english', $1)
        ORDER BY section_id
        LIMIT $2
    """, {"q": q, "limit": limit})
    return [dict(r) for r in rows]
