#!/usr/bin/env python3
import os, csv, json, re, sys
import psycopg2
from psycopg2.extras import execute_values

# Env
DSN = os.environ.get("SYNC_DATABASE_URL")
TSV = os.environ.get("GWAS_TSV", "data/gwas/gwas_autoimmune.tsv")
if not DSN:
    raise SystemExit("SYNC_DATABASE_URL not set (server/.env).")

# Columns we’ll map if present in the TSV (others go into raw JSON)
FIELD_MAP = {
    "STUDY ACCESSION": "study_accession",
    "PUBMEDID": "pubmed_id",
    "DISEASE/TRAIT": "disease_trait",
    "MAPPED_TRAIT": "mapped_trait",
    "MAPPED_TRAIT URI": "mapped_trait_uri",
    "SNPS": "snps",
    "STRONGEST SNP-RISK ALLELE": "strongest_snp_risk_allele",
    "P-VALUE": "p_value",
    "OR or BETA": "or_beta",
    "95% CI (TEXT)": "ci_95",
    "RISK ALLELE FREQUENCY": "risk_allele_frequency",
    "REPORTED GENE(S)": "reported_genes",
    "MAPPED_GENE": "mapped_gene",
    "CHR_ID": "chr",
    "CHR_POS": "chr_pos",
    "INITIAL SAMPLE SIZE": "initial_sample_size",
    "REPLICATION SAMPLE SIZE": "replication_sample_size",
    "DATE ADDED TO CATALOG": "date_added",
}

def coerce_float(x):
    try:
        return float(x) if x not in (None, "", "NR") else None
    except Exception:
        return None

def coerce_int(x):
    try:
        return int(x) if x not in (None, "", "NR") else None
    except Exception:
        return None

def main():
    if not os.path.isfile(TSV) or os.path.getsize(TSV) == 0:
        raise SystemExit(f"Input TSV not found or empty: {TSV}")

    rows = []
    with open(TSV, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh, delimiter="\t")
        for r in reader:
            raw = {k: v for k, v in r.items()}
            out = {v: r.get(k, None) for k, v in FIELD_MAP.items()}

            # Coerce numeric fields
            out["p_value"] = coerce_float(out.get("p_value"))
            out["chr_pos"] = coerce_int(out.get("chr_pos"))

            # Normalize date_added (YYYY-MM-DD) if present
            da = (out.get("date_added") or "").strip()
            if da:
                # Keep as text; Postgres DATE will coerce
                pass

            out["raw"] = json.dumps(raw, ensure_ascii=False)
            rows.append(out)

    if not rows:
        print("No rows to import after filtering.")
        return

    cols = ("study_accession","pubmed_id","disease_trait","mapped_trait","mapped_trait_uri",
            "snps","strongest_snp_risk_allele","p_value","or_beta","ci_95",
            "risk_allele_frequency","reported_genes","mapped_gene","chr","chr_pos",
            "initial_sample_size","replication_sample_size","date_added","raw")

    sql = f"""
    INSERT INTO molecular.gwas_hits ({", ".join(cols)})
    VALUES %s
    ON CONFLICT DO NOTHING;
    """
    tpl = [
        tuple(r.get(c) for c in cols)
        for r in rows
    ]

    with psycopg2.connect(DSN) as conn, conn.cursor() as cur:
        # Add a natural uniqueness to avoid dupes if you run twice
        cur.execute("""
            DO $$
            BEGIN
              IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE schemaname='molecular' AND indexname='gwas_hits_nat_uniq'
              ) THEN
                CREATE UNIQUE INDEX gwas_hits_nat_uniq
                  ON molecular.gwas_hits (COALESCE(study_accession,''), COALESCE(snps,''), COALESCE(disease_trait,''));
              END IF;
            END$$;
        """)
        execute_values(cur, sql, tpl, page_size=5000)
        print(f"Imported {len(rows)} rows into molecular.gwas_hits")

if __name__ == "__main__":
    main()

