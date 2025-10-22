#!/usr/bin/env python3
import os, sys, csv, re, json
from datetime import datetime
from report_common import connect

MAP = {
  'variation_id':   [r'variation\s*id', r'clinvar.*variation.*id'],
  'clingen_id':     [r'clingen.*id', r'cg.*id'],
  'gene_symbol':    [r'^(gene\b|gene\(s\))', r'\bgene\s*symbol\b'],
  'hgnc_id':        [r'\bhgnc\b', r'\bhgnc\s*id\b'],
  'condition':      [r'(condition|disease|phenotype)'],
  'mondo_id':       [r'^(mondo|mondo\s*id|mondo:)'],
  'classification': [r'(classification|pathogenicity|clinical\s*significance)'],
  'last_evaluated': [r'(date|last.*evaluat.*)'],
  'review_status':  [r'(review.*status|assertion.*method)'],
  'source_url':     [r'(url|link)'],
}

def pick(header, pats):
    for i, col in enumerate([c.strip().lower() for c in header]):
        for p in pats:
            if re.search(p, col):
                return i
    return None

def to_date(s):
    if not s: return None
    for fmt in ("%Y-%m-%d","%m/%d/%Y","%d-%b-%Y","%b %d, %Y"):
        try: return datetime.strptime(s.strip(), fmt).date()
        except Exception: pass
    return None

def main():
    if len(sys.argv) < 2:
        print("Usage: ingest_clingen_variants.py VARIANTS_TSV_OR_TXT", file=sys.stderr)
        sys.exit(2)
    path = sys.argv[1]
    conn = connect(); cur = conn.cursor()
    cur.execute("SET application_name = 'ingest_clingen_variants'")
    cur.execute("""
      CREATE TABLE IF NOT EXISTS clingen.variant_classifications (
        variation_id text, clingen_id text, gene_symbol text, hgnc_id text,
        condition text, mondo_id text, classification text, last_evaluated date,
        review_status text, source_url text, raw jsonb, loaded_at timestamptz default now()
      )
    """)
    cur.execute("TRUNCATE clingen.variant_classifications")

    with open(path, "rt", encoding="utf-8", newline="") as f:
        rdr = csv.reader(f, delimiter="\t")
        header = next(rdr, [])
        header_norm = [re.sub(r'[^a-z0-9]+','_', c.strip().lower()) for c in header]
        idx = {k: pick(header, v) for k, v in MAP.items()}
        n = 0
        for r in rdr:
            row = {header_norm[i]: r[i] for i in range(min(len(header_norm), len(r)))}
            at = lambda k: (r[idx[k]].strip() if idx.get(k) is not None and idx[k] < len(r) else None)
            cur.execute("""
              INSERT INTO clingen.variant_classifications
              (variation_id, clingen_id, gene_symbol, hgnc_id, condition, mondo_id, classification, last_evaluated, review_status, source_url, raw)
              VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
            """, (
              at('variation_id'),
              at('clingen_id'),
              at('gene_symbol'),
              at('hgnc_id'),
              at('condition'),
              at('mondo_id'),
              at('classification'),
              to_date(at('last_evaluated')),
              at('review_status'),
              at('source_url'),
              json.dumps(row),
            ))
            n += 1
    conn.commit(); conn.close()
    print(f"✅ Loaded {n:,} ClinGen variant classification rows")
if __name__ == "__main__":
    main()

