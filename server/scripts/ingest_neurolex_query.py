#!/usr/bin/env python3
import os, sys, time, json, argparse
from pathlib import Path
from typing import Any, Dict, Iterable, List

import requests, psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# --- env (server/.env first, then project .env) -------------------------------
root = Path(__file__).resolve().parents[2]
for envp in (root/"server/.env", root/".env"):
    if envp.exists(): load_dotenv(dotenv_path=envp)

API = "https://api.scicrunch.io/elastic/v1/Interlex_pr/_search"
HEADERS = {"Content-Type":"application/json", "apikey": os.environ.get("SCICRUNCH_API_KEY","")}

def dburl() -> str:
    dsn = os.environ.get("SYNC_DATABASE_URL")
    if dsn: return dsn
    dsn = os.environ.get("DATABASE_URL","")
    return dsn.replace("+asyncpg","") if dsn else "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"

def es_post(payload: Dict[str, Any]) -> Dict[str, Any]:
    r = requests.post(API, headers=HEADERS, data=json.dumps(payload), timeout=30)
    if r.status_code != 200:
        raise RuntimeError(f"InterLex API {r.status_code}: {r.text[:200]}")
    return r.json()

def normalize_synonyms(src):
    raw = src.get('synonyms') or []
    out = []
    for s in raw:
        if isinstance(s, str):
            out.append(s)
        elif isinstance(s, dict):
            lit = s.get('literal') or s.get('label') or s.get('value')
            if lit: out.append(lit)
    return sorted({x.strip() for x in out if x and isinstance(x, str)})

def row_from_source(src):
    ilx_id = src.get('ilx') or src.get('id')
    iri = None
    for eid in src.get('existing_ids') or []:
        if isinstance(eid, dict) and (eid.get('curie') or '').startswith('ILX:'):
            iri = eid.get('iri') or f"http://uri.interlex.org/base/{ilx_id}"
            break
    label = src.get('label') or ''
    definition = src.get('definition') or ''
    synonyms = normalize_synonyms(src)
    return (ilx_id, iri, label, definition, synonyms)

def fetch_query_terms(q: str, size: int, pages: int) -> Iterable[Dict[str,Any]]:
    base = {
        "size": size,
        "_source": ["ilx","label","definition","synonyms","existing_ids","annotations"],
        "query": {
            "simple_query_string": {
                "query": q,
                "fields": ["label^3","definition","synonyms.literal"]
            }
        }
    }
    for p in range(pages):
        payload = dict(base)
        payload["from"] = p*size
        j = es_post(payload)
        hits = j.get("hits",{}).get("hits",[])
        if not hits: break
        for h in hits:
            yield h["_source"]
        time.sleep(0.25)

def upsert_batch(conn, rows: List[Dict[str,Any]]):
    term_sql = """
        INSERT INTO ontology.neurolex (ilx_id, iri, label, definition, synonyms)
        VALUES %s
        ON CONFLICT (ilx_id) DO UPDATE SET
            iri = EXCLUDED.iri,
            label = EXCLUDED.label,
            definition = EXCLUDED.definition,
            synonyms = EXCLUDED.synonyms
    """
    ann_sql = """
        INSERT INTO ontology.neurolex_annotations (ilx_id, prop_label, value, prop_ilx, raw)
        VALUES %s
        ON CONFLICT (ilx_id, prop_label, value) DO NOTHING
    """
    term_values = [row_from_source(s) for s in rows]
    ann_values  = []
    for s in rows:
        for a in s.get("annotations") or []:
            ann_values.append((
                s.get("ilx"),
                a.get("annotation_term_label") or "",
                a.get("value") or "",
                a.get("annotation_term_ilx"),
                json.dumps(a)
            ))

    with conn.cursor() as cur:
        if term_values:
            execute_values(cur, term_sql, term_values, page_size=500)
        if ann_values:
            execute_values(cur, ann_sql, ann_values, page_size=1000)
    conn.commit()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--query", required=True, help="simple_query_string (e.g. 'sclerosis | demyelinating')")
    ap.add_argument("--size", type=int, default=500)
    ap.add_argument("--pages", type=int, default=20)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.environ.get("SCICRUNCH_API_KEY"):
        print("ERROR: export SCICRUNCH_API_KEY first", file=sys.stderr); sys.exit(2)

    print(f"[neurolex:query] q='{args.query}' size={args.size} pages={args.pages}")
    conn = None
    try:
        if not args.dry_run:
            conn = psycopg2.connect(dburl())
        batch, n = [], 0
        for src in fetch_query_terms(args.query, args.size, args.pages):
            batch.append(src); n += 1
            if len(batch) >= 500 and not args.dry_run:
                upsert_batch(conn, batch); batch.clear()
        if batch and not args.dry_run:
            upsert_batch(conn, batch)
        print(f"[neurolex:query] upserted ~{n}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    main()
