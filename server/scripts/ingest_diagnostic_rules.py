#!/usr/bin/env python3
import json
import argparse
import os
from datetime import datetime, date
import psycopg2
from psycopg2.extras import Json
from dotenv import load_dotenv

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

def dburl() -> str:
    url = os.getenv("DATABASE_URL") or "postgresql:///2ndopinionmd"
    return url.replace("+asyncpg", "")

def _coerce_date(d):
    if not d:
        return None
    if isinstance(d, date):
        return d
    if isinstance(d, str):
        # accept YYYY-MM-DD or any ISO dateish
        try:
            return datetime.fromisoformat(d).date()
        except Exception:
            for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"):
                try:
                    return datetime.strptime(d, fmt).date()
                except Exception:
                    pass
    return None

def _normalize_row(r: dict) -> dict:
    # ensure proper types for placeholders
    r = dict(r)  # shallow copy
    r["published_date"] = _coerce_date(r.get("published_date"))
    # source_urls: allow string/None/list
    su = r.get("source_urls")
    if su is None:
        r["source_urls"] = []
    elif isinstance(su, str):
        r["source_urls"] = [su]
    elif isinstance(su, (list, tuple)):
        r["source_urls"] = list(su)
    else:
        r["source_urls"] = [str(su)]

    # wrap rule_json dict as Json() for jsonb
    r["rule_json"] = Json(r.get("rule_json") or {})

    # ensure optional fields exist
    for k in ("notes", "org", "condition", "version", "title"):
        r.setdefault(k, None)

    return r

def upsert_rule(cur, r):
    cols = ("rule_key","title","org","condition","version","published_date","rule_json","notes","source_urls")
    sql = f"""
    INSERT INTO guidelines.diagnostic_rules ({",".join(cols)})
    VALUES (%(rule_key)s, %(title)s, %(org)s, %(condition)s, %(version)s, %(published_date)s, %(rule_json)s, %(notes)s, %(source_urls)s)
    ON CONFLICT (rule_key) DO UPDATE SET
      title=EXCLUDED.title,
      org=EXCLUDED.org,
      condition=EXCLUDED.condition,
      version=EXCLUDED.version,
      published_date=EXCLUDED.published_date,
      rule_json=EXCLUDED.rule_json,
      notes=EXCLUDED.notes,
      source_urls=EXCLUDED.source_urls,
      updated_at=NOW();
    """
    cur.execute(sql, _normalize_row(r))

def main():
    ap = argparse.ArgumentParser(description="Upsert diagnostic rules JSON into PostgreSQL")
    ap.add_argument("--file", required=True, help="Path to JSON array of rules")
    args = ap.parse_args()

    with open(args.file, "r", encoding="utf-8") as f:
        rules = json.load(f)
        if not isinstance(rules, list):
            raise ValueError("Top-level JSON must be an array of rule objects")

    conn = psycopg2.connect(dburl())
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            for r in rules:
                upsert_rule(cur, r)
        conn.commit()
        print(f" Upserted {len(rules)} rules.")
    finally:
        conn.close()

if __name__ == "__main__":
    main()

