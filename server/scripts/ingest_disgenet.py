#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DisGeNET TSV importer (robust for trial CSV/TSV headers)
- Reads a TSV with DisGeNET gda/summary columns
- Converts bracketed list fields like [FOO, BAR] to Python lists
- Upserts into molecular.disgenet_associations on assoc_id
Env:
  SYNC_DATABASE_URL  (postgresql://...  **sync** DSN, no +asyncpg)
  DISGENET_TSV       (path to TSV; or pass as argv[1])
"""

import os, sys, csv, math
import psycopg2
from psycopg2 import extras

TSV_PATH = os.environ.get("DISGENET_TSV") or (sys.argv[1] if len(sys.argv) > 1 else "data/disgenet_curated.tsv")
DSN      = os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL", "")
DSN      = DSN.replace("+asyncpg","")  # just in case

if not DSN:
    print("ERROR: set SYNC_DATABASE_URL=postgresql://user@host:5432/db", file=sys.stderr)
    sys.exit(2)

def to_int(s):
    if s is None: return None
    s = s.strip()
    if not s or s.lower() in ("null","nan"): return None
    try: return int(s)
    except ValueError: return None

def to_float(s):
    if s is None: return None
    s = s.strip()
    if not s or s.lower() in ("null","nan"): return None
    try: return float(s)
    except ValueError: return None

def parse_list(s):
    """
    Turn strings like:
      "[ENSG00000142192]" or "[MESH_D000544, ICD10_G30]"
    into Python lists. Handles quotes and spaces safely using csv parser.
    Returns [] for empty lists, None for missing.
    """
    if s is None: return None
    s = s.strip()
    if not s: return None
    # strip outer quotes if present (some TSVs quote each cell)
    if len(s) >= 2 and ((s[0] == '"' and s[-1] == '"') or (s[0] == "'" and s[-1] == "'")):
        s = s[1:-1]
    if s == "[]": return []
    if s.startswith("[") and s.endswith("]"):
        inner = s[1:-1]
        # use csv to split on commas respecting quotes
        row = next(csv.reader([inner], skipinitialspace=True))
        items = []
        for itm in row:
            itm = itm.strip().strip('"').strip("'")
            if itm != "":
                items.append(itm)
        return items
    # if not bracketed, return None or single-item list?
    return [s] if s else None

# Map DisGeNET headers to our DB columns
# We'll normalize headers by stripping quotes and using exact keys below.
FIELD_MAP = {
    "assocID":                              ("assoc_id", lambda s: s.strip() if s else None),
    "geneNcbiID":                           ("gene_ncbi_id", to_int),
    "symbolOfGene":                         ("gene_symbol", lambda s: s.strip() if s else None),
    "geneNcbiType":                         ("gene_ncbi_type", lambda s: s.strip() if s else None),
    "geneEnsemblIDs":                       ("gene_ensembl_ids", parse_list),
    "geneDSI":                              ("gene_dsi", to_float),
    "geneDPI":                              ("gene_dpi", to_float),
    "diseaseName":                          ("disease_name", lambda s: s.strip() if s else None),
    "diseaseType":                          ("disease_type", lambda s: s.strip() if s else None),
    "diseaseUMLSCUI":                       ("disease_umls_cui", lambda s: s.strip() if s else None),
    "diseaseVocabularies":                  ("disease_vocabularies", parse_list),
    "diseaseClasses_DO":                    ("disease_classes_do", parse_list),
    "diseaseClasses_HPO":                   ("disease_classes_hpo", parse_list),
    "diseaseClasses_MSH":                   ("disease_classes_msh", parse_list),
    "diseaseClasses_UMLS_ST":               ("disease_classes_umls_st", parse_list),
    "disease_inheritance":                  ("disease_inheritance", lambda s: s.strip() if s else None),
    "disease_prevalence_class":             ("disease_prevalence_class", lambda s: s.strip() if s else None),
    "disease_prevalence_geo_area":          ("disease_prevalence_geo_area", lambda s: s.strip() if s else None),
    "disease_prevalence_type":              ("disease_prevalence_type", lambda s: s.strip() if s else None),
    "score":                                ("score", to_float),
    "numPMIDs":                             ("num_pmids", to_int),
    "numCTsupportingAssociation":           ("num_ctsupporting_association", to_int),
    "numChemsIncludedInEvidences":          ("num_chems_included_in_evidences", to_int),
    "numPMIDsWithChemsIncludedInEvidences": ("num_pmids_with_chems_included_in_evidences", to_int),
    "numberChemsFiltered":                  ("number_chems_filtered", to_int),
    "numberPmidsWithChemsFiltered":         ("number_pmids_with_chems_filtered", to_int),
    "EI":                                   ("ei", to_float),
    "EL":                                   ("el", lambda s: s.strip() if s else None),
    "yearInitial":                          ("year_initial", to_int),
    "yearFinal":                            ("year_final", to_int),
}

DB_COLS = [v[0] for v in FIELD_MAP.values()]

def clean_key(k: str) -> str:
    # remove surrounding quotes/whitespace
    return k.strip().strip('"').strip("'")

def normalize_row_keys(row: dict) -> dict:
    return { clean_key(k): v for k, v in row.items() }

def ensure_unique_index(cur):
    cur.execute("""
    DO $$
    BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname='molecular' AND indexname='disgenet_assoc_id_uidx'
      ) THEN
        EXECUTE 'CREATE UNIQUE INDEX disgenet_assoc_id_uidx
                 ON molecular.disgenet_associations(assoc_id)
                 WHERE assoc_id IS NOT NULL';
      END IF;
    END $$;
    """)

def main():
    if not os.path.exists(TSV_PATH) or os.path.getsize(TSV_PATH) == 0:
        print(f"ERROR: TSV not found or empty at {TSV_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = psycopg2.connect(DSN)
    conn.set_session(autocommit=False)
    cur = conn.cursor()
    ensure_unique_index(cur)

    rows = []
    total = 0
    with open(TSV_PATH, "r", encoding="utf-8", newline="") as f:
        rdr = csv.DictReader(f, delimiter="\t")
        for raw in rdr:
            total += 1
            row = normalize_row_keys(raw)

            out = []
            for source_key, (colname, converter) in FIELD_MAP.items():
                val = row.get(source_key)
                out.append(converter(val))
            # required fields: assoc_id, gene_id, gene_symbol, disease_name
            if not out[0]:  # assoc_id
                continue
            req_idx = [1, 2, 7]  # gene_ncbi_id, gene_symbol, disease_name
            if any(out[i] is None for i in req_idx):
                continue
            rows.append(tuple(out))


    if not rows:
        print(f"No rows parsed from {TSV_PATH} (headers? delimiter?)")
        conn.rollback()
        conn.close()
        return

    cols_sql = ", ".join(DB_COLS)
    updates = ", ".join([f"{c}=EXCLUDED.{c}" for c in DB_COLS if c != "assoc_id"])
    upsert_sql = f"""
        INSERT INTO molecular.disgenet_associations ({cols_sql})
        VALUES %s
        ON CONFLICT (assoc_id) WHERE assoc_id IS NOT NULL
        DO UPDATE SET {updates};
    """

    # batch insert
    extras.execute_values(cur, upsert_sql, rows, page_size=1000)
    conn.commit()
    print(f"Upserted {len(rows)} rows (parsed {total}) from {TSV_PATH}")

    cur.close()
    conn.close()

if __name__ == "__main__":
    main()

