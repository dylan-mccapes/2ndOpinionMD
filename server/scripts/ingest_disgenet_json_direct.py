#!/usr/bin/env python3
import sys, os, json, psycopg2
from psycopg2.extras import execute_values

# usage: ingest_disgenet_json_direct.py <json_file>
if len(sys.argv) != 2:
    print("usage: ingest_disgenet_json_direct.py <json_file>", file=sys.stderr)
    sys.exit(2)

json_path = sys.argv[1]
if not os.path.exists(json_path) or os.path.getsize(json_path) == 0:
    print(f"no JSON file or empty: {json_path}", file=sys.stderr)
    sys.exit(0)

dsn = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
if not dsn:
    print("missing SYNC_DATABASE_URL / DATABASE_URL", file=sys.stderr)
    sys.exit(2)

with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

# DisGeNET sometimes returns a list, sometimes {"content":[...]}
if isinstance(data, dict):
    rows = data.get("content") or data.get("result") or data.get("data") or []
elif isinstance(data, list):
    rows = data
else:
    rows = []

if not rows:
    # Nothing to ingest; not an error.
    sys.exit(0)

def pick(d, *keys, default=None):
    for k in keys:
        if k in d and d[k] is not None:
            return d[k]
    return default

batch = []
for r in rows:
    assoc_id = pick(r, "associationId", "assocID", "assocId", "association_id")
    gene_id  = pick(r, "gene_ncbi_id", "geneId", "geneIdNcbi", "gene_id")
    gsym     = pick(r, "gene_symbol", "geneSymbol", "symbol")
    dcui     = pick(r, "disease_umls_cui", "diseaseUmls", "diseaseId", "umls_cui", "disease_umls")
    dname    = pick(r, "disease_name", "diseaseName", "name")
    score    = pick(r, "score", "scoreValue", "gda_score")

    # hard requirements — mirror your existing SQL paths
    if not assoc_id or not gene_id or not gsym or not dname:
        continue

    try:
        gene_id = int(str(gene_id).strip())
    except Exception:
        continue

    # normalize strings
    assoc_id = str(assoc_id).strip().strip('"')
    gsym     = (str(gsym).strip() if gsym is not None else None)
    dcui     = (str(dcui).strip() if dcui is not None else None)
    dname    = (str(dname).strip() if dname is not None else None)
    try:
        score = float(score) if score is not None else None
    except Exception:
        score = None

    batch.append((assoc_id, gene_id, gsym, dcui, dname, score))

if not batch:
    sys.exit(0)

cols = "(assoc_id, gene_ncbi_id, gene_symbol, disease_umls_cui, disease_name, score)"
sql = f"""
INSERT INTO molecular.disgenet_associations {cols}
VALUES %s
ON CONFLICT (assoc_id) DO UPDATE SET
  gene_ncbi_id      = EXCLUDED.gene_ncbi_id,
  gene_symbol       = EXCLUDED.gene_symbol,
  disease_umls_cui  = EXCLUDED.disease_umls_cui,
  disease_name      = EXCLUDED.disease_name,
  score             = EXCLUDED.score;
"""

with psycopg2.connect(dsn) as conn:
    with conn.cursor() as cur:
        execute_values(cur, sql, batch, page_size=1000)
