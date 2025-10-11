#!/usr/bin/env python3
import sys, json, csv

raw = sys.stdin.read().strip()
if not raw:
    sys.exit(0)

obj = json.loads(raw)

# Normalize to a list of row dicts
rows = None
if isinstance(obj, list):
    rows = obj
elif isinstance(obj, dict):
    # Common paginated shapes
    for key in ("content", "results", "data", "items"):
        if isinstance(obj.get(key), list):
            rows = obj[key]
            break
    else:
        # Maybe it's a single record dict; treat as 1 row if it looks like one
        rows = [obj]
else:
    rows = []

if not rows:
    sys.exit(0)

# Stable column order (only include if present)
PREFERRED = [
    "source", "year", "associd", "assocId", "gene_ncbi_id", "geneSymbol", "gene_symbol",
    "disease_umls_cui", "diseaseId", "disease_name", "diseaseName",
    "score", "score_ltz", "gene_disease_pmids", "gene_disease_pubmeds",
    "el", "ei", "gene_name", "disease_class", "disease_semantic_type",
    "disease_mesh_id", "gene_uniprot", "gene_ensembl", "disease_do"
]

# Gather all keys across rows to avoid dropping fields
all_keys = []
seen = set()
for r in rows:
    if isinstance(r, dict):
        for k in r.keys():
            if k not in seen:
                seen.add(k); all_keys.append(k)

cols = [c for c in PREFERRED if c in seen] + [k for k in all_keys if k not in PREFERRED]

w = csv.writer(sys.stdout, delimiter='\t', lineterminator='\n')
w.writerow(cols)

def cell(val):
    if val is None:
        return ""
    if isinstance(val, (list, tuple)):
        return ",".join("" if v is None else str(v) for v in val)
    return str(val)

for r in rows:
    if not isinstance(r, dict):
        continue
    w.writerow([cell(r.get(c, "")) for c in cols])
