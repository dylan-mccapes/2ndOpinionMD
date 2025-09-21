from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from typing import Optional, Dict, Any
from server.db.session import get_session
from server.utils.diagnostic_rule_eval import evaluate

router = APIRouter(prefix="/api/diagnostic_rules", tags=["diagnostic_rules"])

@router.get("/list")
async def list_rules(q: Optional[str]=None, session: AsyncSession=Depends(get_session)):
    sql = "SELECT rule_key, title, org, condition, version, published_date, source_urls FROM guidelines.diagnostic_rules"
    params={}
    if q:
        sql += " WHERE to_tsvector('english', coalesce(title,'')||' '||coalesce(condition,'')) @@ plainto_tsquery(:q)"
        params["q"]=q
    sql += " ORDER BY condition, version DESC"
    res = await session.execute(text(sql), params)
    return [dict(r) for r in res.mappings().all()]

@router.get("/{rule_key}")
async def get_rule(rule_key: str, session: AsyncSession=Depends(get_session)):
    res = await session.execute(text("""
        SELECT rule_key, title, org, condition, version, published_date, rule_json, notes, source_urls
        FROM guidelines.diagnostic_rules WHERE rule_key=:k
    """), {"k": rule_key})
    row = res.mappings().first()
    if not row:
        raise HTTPException(404, f"Rule {rule_key} not found")
    return dict(row)

@router.post("/{rule_key}/apply")
async def apply_rule(rule_key: str, facts: Dict[str, Any], session: AsyncSession=Depends(get_session)):
    res = await session.execute(text("SELECT rule_json FROM guidelines.diagnostic_rules WHERE rule_key=:k"), {"k": rule_key})
    row = res.first()
    if not row:
        raise HTTPException(404, f"Rule {rule_key} not found")
    return evaluate(row[0], facts)

