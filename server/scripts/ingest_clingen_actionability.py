#!/usr/bin/env python3
import os, sys, csv, gzip, re
from datetime import datetime
from report_common import connect, q

# Map various header spellings to our canonical columns
HEADER_MAP = {
  'gene_symbol':        [r'^(gene\b|gene\(s\))', r'\bgene\s*symbol\b'],
  'hgnc_id':            [r'\bhgnc\b', r'\bhgnc\s*id\b'],
  'disease_name':       [r'^(condition|phenotype|disease)'],
  'disease_mondo_id':   [r'^(mondo|mondo\s*id|mondo:)'],
  'actionability_assertion':[r'(assertion|classification)'],
  'report_date':        [r'(date|report\s*date)'],
  'source_url':         [r'(url|report|link)'],
}

def pick(colnames, patterns):
    colnames_l = [c.strip() for c in colnames]
    for i,c in enumerate(colnames_l):
        c_lower = c.lower()
        for p in patterns:
            if re.search(p, c_lower):
                return i
    return None

def parse_date(s):
    if not s: return None
    for fmt in ("%Y-%m-%d","%m/%d/%Y","%d-%b-%Y","%b %d, %Y"):
        try: return datetime.strptime(s.strip(), fmt).date()
        except Exception: pass
    return None

def rows_from_file(path, cohort):
    open_fn = gzip.open if path.endswith(".gz") else open
    with open_fn(path, "rt", encoding="utf-8", newline="") as f:
        rdr = csv.reader(f, delimiter='\t')
        header = next(rdr, [])
        idx = {}
        for key, pats in HEADER_MAP.items():
            idx[key] = pick(header, pats)
        # require at least gene + disease to consider a row
        for r in rdr:
            def at(k):
                j = idx.get(k)
                return r[j].strip() if (j is not None and j < len(r)) else None
            gene   = at('gene_symbol')
            dis    = at('disease_name')
            if not (gene or dis):
                continue
            yield {
              "cohort": cohort,
              "gene_symbol": gene,
              "hgnc_id": at('hgnc_id'),
              "disease_name": dis,
              "disease_mondo_id": at('disease_mondo_id'),
              "actionability_assertion": at('actionability_assertion'),
              "report_date": parse_date(at('report_date')),
              "source_url": at('source_url'),
            }

def main():
    if len(sys.argv) < 3:
        print("Usage: ingest_clingen_actionability.py ADULT_TSV PEDIATRIC_TSV", file=sys.stderr)
        sys.exit(2)
    adult, ped = sys.argv[1], sys.argv[2]
    conn = connect()
    cur = conn.cursor()
    cur.execute("SET application_name = 'ingest_clingen_actionability'")
    cur.execute("CREATE SCHEMA IF NOT EXISTS clingen")
    cur.execute("""
      CREATE TABLE IF NOT EXISTS clingen.actionability_summary(
        cohort text, gene_symbol text, hgnc_id text, disease_name text, disease_mondo_id text,
        actionability_assertion text, report_date date, source_url text, loaded_at timestamptz default now()
      )
    """)
    cur.execute("TRUNCATE clingen.actionability_summary")
    rows = 0
    for path, cohort in [(adult, "Adult"), (ped, "Pediatric")]:
        for rec in rows_from_file(path, cohort):
            cur.execute("""
              INSERT INTO clingen.actionability_summary
              (cohort,gene_symbol,hgnc_id,disease_name,disease_mondo_id,actionability_assertion,report_date,source_url)
              VALUES (%(cohort)s,%(gene_symbol)s,%(hgnc_id)s,%(disease_name)s,%(disease_mondo_id)s,%(actionability_assertion)s,%(report_date)s,%(source_url)s)
            """, rec)
            rows += 1
    conn.commit()
    # (Re)build quick matview
    cur.execute("REFRESH MATERIALIZED VIEW clingen.v_actionability_quick")
    conn.commit()
    conn.close()
    print(f"✅ Loaded {rows:,} ClinGen Actionability summary rows into clingen.actionability_summary")

if __name__ == "__main__":
    main()
