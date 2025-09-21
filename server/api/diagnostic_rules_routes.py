# server/api/diagnostic_rules_routes.py
import os, json
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from fastapi import APIRouter, Depends, HTTPException, Header, Body
from sqlalchemy import text, bindparam
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB

from server.db.session import get_session
from server.utils.diagnostic_rule_eval import evaluate

router = APIRouter(prefix="/api/diagnostic_rules", tags=["diagnostic_rules"])

# -------------------------
# Read-only endpoints
# -------------------------

@router.get("/list")
async def list_rules(
    q: Optional[str] = None,
    session: AsyncSession = Depends(get_session),
):
    sql = """
        SELECT rule_key, title, org, condition, version, published_date, source_urls
        FROM guidelines.diagnostic_rules
    """
    params: Dict[str, Any] = {}
    if q:
        sql += """
            WHERE to_tsvector('english', coalesce(title,'')||' '||coalesce(condition,'')) @@ plainto_tsquery(:q)
        """
        params["q"] = q
    sql += " ORDER BY condition, version DESC"
    res = await session.execute(text(sql), params)
    return [dict(r) for r in res.mappings().all()]


@router.get("/{rule_key}")
async def get_rule(
    rule_key: str,
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(
        text("""
            SELECT rule_key, title, org, condition, version, published_date, rule_json, notes, source_urls
            FROM guidelines.diagnostic_rules
            WHERE rule_key = :k
        """),
        {"k": rule_key},
    )
    row = res.mappings().first()
    if not row:
        raise HTTPException(404, f"Rule {rule_key} not found")
    return dict(row)


@router.post("/{rule_key}/apply")
async def apply_rule(
    rule_key: str,
    facts: Dict[str, Any] = Body(...),  # ensure body parsing
    session: AsyncSession = Depends(get_session),
):
    res = await session.execute(
        text("SELECT rule_json FROM guidelines.diagnostic_rules WHERE rule_key = :k"),
        {"k": rule_key},
    )
    row = res.first()
    if not row:
        raise HTTPException(404, f"Rule {rule_key} not found")
    return evaluate(row[0], facts)


# -------------------------
# Admin upsert (token-protected)
# -------------------------

ADMIN_TOKEN = os.getenv("ADMIN_TOKEN")  # set in .env

def _coerce_date(d):
    if not d:
        return None
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        try:
            return datetime.fromisoformat(d).date()
        except Exception:
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
                try:
                    return datetime.strptime(d, fmt).date()
                except Exception:
                    pass
    return None  # let DB constraints complain if needed


def _norm_rule(r: Dict[str, Any]) -> Dict[str, Any]:
    # source_urls -> list[str]
    su = r.get("source_urls")
    if su is None:
        r["source_urls"] = []
    elif isinstance(su, str):
        r["source_urls"] = [su]
    elif isinstance(su, (list, tuple)):
        r["source_urls"] = [str(x) for x in su]
    else:
        r["source_urls"] = [str(su)]

    # date normalization
    r["published_date"] = _coerce_date(r.get("published_date"))

    # ensure rule_json present
    if r.get("rule_json") is None:
        r["rule_json"] = {}

    # optional fields
    for k in ("notes", "org", "condition", "version", "title"):
        r.setdefault(k, None)

    # required key
    if not r.get("rule_key"):
        raise HTTPException(status_code=400, detail="rule_key is required")

    return r


@router.post("/upsert")
async def upsert_rules(
    payload: Any = Body(...),  # read from JSON body
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
    session: AsyncSession = Depends(get_session),
):
    if not ADMIN_TOKEN or x_admin_token != ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Unauthorized")

    rows: List[Dict[str, Any]] = payload if isinstance(payload, list) else [payload]

    # Bind rule_json as JSONB via SQLAlchemy (avoid inline ::jsonb which breaks asyncpg's $ binds)
    sql = text("""
        INSERT INTO guidelines.diagnostic_rules
            (rule_key, title, org, condition, version, published_date, rule_json, notes, source_urls)
        VALUES
            (:rule_key, :title, :org, :condition, :version, :published_date, :rule_json, :notes, :source_urls)
        ON CONFLICT (rule_key) DO UPDATE SET
            title = EXCLUDED.title,
            org = EXCLUDED.org,
            condition = EXCLUDED.condition,
            version = EXCLUDED.version,
            published_date = EXCLUDED.published_date,
            rule_json = EXCLUDED.rule_json,
            notes = EXCLUDED.notes,
            source_urls = EXCLUDED.source_urls,
            updated_at = NOW();
    """).bindparams(bindparam("rule_json", type_=JSONB))

    try:
        async with session.begin():
            for r in rows:
                params = _norm_rule(dict(r))
                # Ensure plain dict goes in (driver + type_ JSONB handles encoding)
                if not isinstance(params["rule_json"], (dict, list)):
                    # accept already-serialized string or other; try to coerce
                    try:
                        params["rule_json"] = json.loads(params["rule_json"])
                    except Exception:
                        params["rule_json"] = {"value": str(params["rule_json"])}
                await session.execute(sql, params)
        return {"upserted": len(rows)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Upsert failed: {e}")

