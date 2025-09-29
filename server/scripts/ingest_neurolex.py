#!/usr/bin/env python3
import os, sys, time, json, argparse
from typing import Dict, Any, Iterable, List
import requests, psycopg2
from psycopg2.extras import execute_values, execute_batch
from dotenv import load_dotenv
from pathlib import Path

# Load env from server/.env then project .env (matches other scripts)
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

def find_parent_ilx_by_label(label: str) -> str:
    j = es_post({"size":1, "query":{"match_phrase":{"label":label}}})
    hits = j.get("hits",{}).get("hits",[])
    if not hits: raise RuntimeError(f"No ILX found for label='{label}'")
    return hits[0]["_source"]["ilx"]

def fetch_descendants(parent_ilx: str, size: int, pages: int) -> Iterable[Dict[str,Any]]:
    # Use OR over ancestors/superclasses for broader coverage
    query = {
        "size": size,
        "_source": ["ilx","label","definition","synonyms","existing_ids","superclasses","ancestors","annotations"],
        "query": {
            "bool": {
                "should": [
                    {"term": {"ancestors.keyword": parent_ilx}},
                    {"term": {"superclasses.keyword": parent_ilx}},
                    {"term": {"ilx": parent_ilx}}  # include the parent record
                ],
                "minimum_should_match": 1
            }
        }
    }
    for p in range(pages):
        payload = dict(query)
        payload["from"] = p*size
        j = es_post(payload)
        hits = j.get("hits",{}).get("hits",[])
        if not hits: break
        for h in hits:
            yield h["_source"]
        # small backoff to be polite
        time.sleep(0.25)

def normalize_synonyms(src):
    raw = src.get('synonyms') or []
    out = []
    for s in raw:
        # API sometimes returns a list[str], other times list[{"literal": "..."}]
        if isinstance(s, str):
            out.append(s)
        elif isinstance(s, dict):
            lit = s.get('literal') or s.get('label') or s.get('value')
            if lit:
                out.append(lit)
    # unique + trimmed
    return sorted({x.strip() for x in out if x and isinstance(x, str)})

def row_from_source(src):
    ilx_id = src.get('ilx') or src.get('id')  # e.g. "ilx_0737472"
    iri = None
    # try to derive a stable IRI if they provide it
    ex_ids = src.get('existing_ids') or []
    for eid in ex_ids:
        if isinstance(eid, dict) and eid.get('curie', '').startswith('ILX:'):
            # "ILX:0737472" → "http://uri.interlex.org/base/ilx_0737472"
            iri = eid.get('iri') or f"http://uri.interlex.org/base/{ilx_id}"
            break
    label = src.get('label') or ''
    definition = src.get('definition') or ''
    synonyms = normalize_synonyms(src)
    return (ilx_id, iri, label, definition, synonyms)

def ilx_iri(src: Dict[str,Any]) -> str:
    # Try existing_ids first
    for eid in src.get("existing_ids") or []:
        curie = (eid.get("curie") or "")
        if curie.startswith("ILX:"):
            return eid.get("iri") or f"http://uri.interlex.org/base/{src['ilx']}"
    return f"http://uri.interlex.org/base/{src['ilx']}"

def upsert_batch(conn, rows: List[Dict[str,Any]]):
    """
    rows: list of _source dicts from InterLex
    - Insert normalized term tuples via execute_values
    - Insert flattened annotations via execute_batch (tuples)
    """
    with conn.cursor() as cur:
        # --- terms ---
        term_values = [row_from_source(src) for src in rows]  # tuples (ilx_id, iri, label, definition, synonyms)

        term_sql = """
            INSERT INTO ontology.neurolex (ilx_id, iri, label, definition, synonyms)
            VALUES %s
            ON CONFLICT (ilx_id) DO UPDATE SET
              iri = EXCLUDED.iri,
              label = EXCLUDED.label,
              definition = EXCLUDED.definition,
              synonyms = EXCLUDED.synonyms;
        """
        if term_values:
            execute_values(cur, term_sql, term_values, page_size=500)

        # --- annotations ---
        ann_sql = """
            INSERT INTO ontology.neurolex_annotations (ilx_id, prop_label, value, prop_ilx, raw)
            VALUES (%s,%s,%s,%s,%s)
            ON CONFLICT (ilx_id, prop_label, value) DO NOTHING;
        """

        ann_params = []
        for s in rows:
            for a in (s.get("annotations") or []):
                ann_params.append((
                    s.get("ilx"),
                    a.get("annotation_term_label") or "",
                    a.get("value") or "",
                    a.get("annotation_term_ilx"),
                    json.dumps(a)
                ))
        if ann_params:
            execute_batch(cur, ann_sql, ann_params, page_size=1000)

    conn.commit()

def fetch_by_query(q: str, size: int, pages: int) -> Iterable[Dict[str,Any]]:
    query = {
        "size": size,
        "_source": ["ilx","label","definition","synonyms","existing_ids","superclasses","ancestors","annotations"],
        "query": {
            "simple_query_string": {
                "query": q,
                "fields": ["label^3","definition","synonyms.literal"]
            }
        }
    }
    for p in range(pages):
        payload = dict(query); payload["from"] = p*size
        j = es_post(payload)
        hits = j.get("hits",{}).get("hits",[])
        if not hits: break
        for h in hits:
            yield h["_source"]
        time.sleep(0.25)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parent-ilx", help="Root ILX to traverse (preferred)")
    ap.add_argument("--label", help="If parent ILX unknown, search by label (e.g., 'neurological disorder')")
    ap.add_argument("--size", type=int, default=500)
    ap.add_argument("--pages", type=int, default=50)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--query", help="Text query to ingest terms (alternative to --parent-ilx/--label)")
    args = ap.parse_args()

    if not os.environ.get("SCICRUNCH_API_KEY"):
        print("ERROR: export SCICRUNCH_API_KEY first", file=sys.stderr); sys.exit(2)

    parent = args.parent_ilx or (find_parent_ilx_by_label(args.label) if args.label else None)
    if not parent:
        print("ERROR: provide --parent-ilx or --label", file=sys.stderr); sys.exit(2)
    
    if args.query:
        src_iter = fetch_by_query(args.query, args.size, args.pages)
        print(f"[neurolex] query='{args.query}' size={args.size} pages={args.pages}")
    else:
        parent = args.parent_ilx or (find_parent_ilx_by_label(args.label) if args.label else None)
        if not parent:
            print("ERROR: provide --query OR (--parent-ilx or --label)", file=sys.stderr); sys.exit(2)
        print(f"[neurolex] parent={parent} size={args.size} pages={args.pages}")
        src_iter = fetch_descendants(parent, args.size, args.pages)

    conn = None
    try:
        conn = psycopg2.connect(dburl())
        batch, n = [], 0
        for src in fetch_descendants(parent, args.size, args.pages):
            batch.append(src); n += 1
            if len(batch) >= 500:
                if not args.dry_run:
                    upsert_batch(conn, batch)
                batch.clear()
        if batch and not args.dry_run:
            upsert_batch(conn, batch)

        print(f"[neurolex] upserted terms ~{n}")
    finally:
        if conn: conn.close()

if __name__ == "__main__":
    main()

