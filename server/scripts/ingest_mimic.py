#!/usr/bin/env python3
import argparse, csv, gzip, io, os, sys, re
import psycopg2
from psycopg2.extras import execute_values

# -----------------------------
# DB helpers
# -----------------------------
def get_db_url():
    url = os.getenv("DATABASE_URL") or "postgresql:///2ndopinionmd"
    return url.replace("+asyncpg", "")

def psql(conn, sql, params=None):
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
    conn.commit()

def table_exists(conn, schema, table):
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM information_schema.tables
            WHERE table_schema=%s AND table_name=%s
        """, (schema, table))
        return bool(cur.fetchone())

# -----------------------------
# I/O helpers
# -----------------------------
def open_maybe_gz(path):
    # text mode (utf-8) for csv
    if path.endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", errors="ignore", newline="")
    return open(path, "r", encoding="utf-8", errors="ignore", newline="")

def sniff_file(path_candidates):
    """Return the first existing path from a list of candidates (str)."""
    for p in path_candidates:
        if os.path.exists(p):
            return p
    return None

def norm_col(name: str) -> str:
    """Normalize CSV header -> postgres identifier."""
    n = name.strip().strip('"').strip("'")
    n = re.sub(r"\s+", "_", n)
    n = n.replace(".", "_").replace("-", "_").replace("/", "_")
    n = re.sub(r"[^A-Za-z0-9_]", "", n)
    n = n.lower()
    if n == "class":  # reserved-ish
        n = "class_"
    if not n:
        n = "col"
    return n

# known typed columns (others default to TEXT)
INT_COLS = {
    "subject_id","hadm_id","stay_id","seq_num","icd_version","specimen_id","itemid",
    "hospital_expire_flag","anchor_age","anchor_year"
}
FLOAT_COLS = {"valuenum","ref_range_lower","ref_range_upper"}
TS_COLS = {
    "admittime","dischtime","edregtime","edouttime",
    "charttime","storetime","intime","outtime","dod"
}
BOOL_COLS = set()  # (add if needed)

def sql_type_for(col):
    if col in INT_COLS:
        return "INTEGER"
    if col in FLOAT_COLS:
        return "DOUBLE PRECISION"
    if col in TS_COLS:
        return "TIMESTAMP"
    if col in BOOL_COLS:
        return "BOOLEAN"
    return "TEXT"

def ensure_table(conn, schema, table, header_cols):
    cols_sql = ", ".join([f'"{c}" {sql_type_for(c)}' for c in header_cols])
    psql(conn, f'CREATE TABLE IF NOT EXISTS "{schema}"."{table}" ({cols_sql});')

def truncate_table(conn, schema, table):
    psql(conn, f'TRUNCATE TABLE "{schema}"."{table}";')

def copy_csv(conn, schema, table, path, header_cols):
    copy_cols = ", ".join([f'"{c}"' for c in header_cols])
    with conn.cursor() as cur, open_maybe_gz(path) as fh:
        # Empty string -> NULL, keep CSV header
        sql = f'COPY "{schema}"."{table}" ({copy_cols}) FROM STDIN WITH (FORMAT csv, HEADER true, NULL \'\', QUOTE \'"\');'
        cur.copy_expert(sql, fh)
    conn.commit()

# -----------------------------
# File mappings (present/realistic)
# -----------------------------
MIMICIV_MAP = {
    "patients":      ["hosp/patients.csv.gz", "hosp/patients.csv"],
    "admissions":    ["hosp/admissions.csv.gz", "hosp/admissions.csv"],
    "diagnoses_icd": ["hosp/diagnoses_icd.csv.gz", "hosp/diagnoses_icd.csv"],
    "labevents":     ["hosp/labevents.csv.gz", "hosp/labevents.csv"],
    # Optional ICU:
    "icustays":      ["icu/icustays.csv.gz", "icu/icustays.csv"],
}

MIMICIII_MAP = {
    "patients":      ["PATIENTS.csv.gz", "PATIENTS.csv"],
    "admissions":    ["ADMISSIONS.csv.gz", "ADMISSIONS.csv"],
    "diagnoses_icd": ["DIAGNOSES_ICD.csv.gz", "DIAGNOSES_ICD.csv"],
    "labevents":     ["LABEVENTS.csv.gz", "LABEVENTS.csv"],
    # Optional ICU:
    "icustays":      ["ICUSTAYS.csv.gz", "ICUSTAYS.csv"],
}

NOTES_MAP_IV = {
    "notes": ["note/noteevents.csv.gz", "note/noteevents.csv"]
}

# -----------------------------
# Loading logic
# -----------------------------
def load_csv_to_table(conn, dataset_dir, mapping, schema, table_prefix, keys, replace=True, sample=None):
    """
    keys: list of logical names to load (e.g. ["patients","admissions",...])
    """
    loaded = []
    for k in keys:
        path = sniff_file([os.path.join(dataset_dir, c) for c in mapping[k]])
        if not path:
            print(f"⚠️  Missing file for {k}: {mapping[k]}")
            continue

        print(f"→ {k}: {os.path.relpath(path, dataset_dir)}")
        # Grab header, normalize
        with open_maybe_gz(path) as fh:
            reader = csv.reader(fh)
            hdr = next(reader)
        cols = [norm_col(c) for c in hdr]

        table = f"{table_prefix}_{k}"
        ensure_table(conn, schema, table, cols)
        if replace:
            truncate_table(conn, schema, table)

        if sample:
            # Create temp file with header + first N rows
            tmp = io.StringIO()
            tmp.write(",".join(hdr) + "\n")
            with open_maybe_gz(path) as fh:
                next(fh)  # skip header
                for i, line in enumerate(fh, 1):
                    if i > sample: break
                    tmp.write(line)
            tmp.seek(0)
            with conn.cursor() as cur:
                copy_cols = ", ".join([f'"{c}"' for c in cols])
                sql = f'COPY "{schema}"."{table}" ({copy_cols}) FROM STDIN WITH (FORMAT csv, HEADER true, NULL \'\', QUOTE \'"\');'
                cur.copy_expert(sql, tmp)
            conn.commit()
        else:
            copy_csv(conn, schema, table, path, cols)

        loaded.append((table, len(cols)))
    return loaded

def create_basic_indexes(conn):
    idx_sql = [
        # MIMIC-IV
        'CREATE INDEX IF NOT EXISTS mimiciv_patients_subject_idx    ON ehr.mimiciv_patients (subject_id);',
        'CREATE INDEX IF NOT EXISTS mimiciv_admissions_hadm_idx     ON ehr.mimiciv_admissions (hadm_id);',
        'CREATE INDEX IF NOT EXISTS mimiciv_admissions_subject_idx  ON ehr.mimiciv_admissions (subject_id);',
        'CREATE INDEX IF NOT EXISTS mimiciv_diagnoses_hadm_idx      ON ehr.mimiciv_diagnoses_icd (hadm_id);',
        'CREATE INDEX IF NOT EXISTS mimiciv_diagnoses_subject_idx   ON ehr.mimiciv_diagnoses_icd (subject_id);',
        'CREATE INDEX IF NOT EXISTS mimiciv_labs_subject_idx        ON ehr.mimiciv_labevents (subject_id);',
        'CREATE INDEX IF NOT EXISTS mimiciv_labs_hadm_idx           ON ehr.mimiciv_labevents (hadm_id);',
        'CREATE INDEX IF NOT EXISTS mimiciv_labs_charttime_idx      ON ehr.mimiciv_labevents (charttime);',
        'CREATE INDEX IF NOT EXISTS mimiciv_icu_stay_idx            ON ehr.mimiciv_icustays (stay_id);',

        # MIMIC-III
        'CREATE INDEX IF NOT EXISTS mimiciii_patients_subject_idx   ON ehr.mimiciii_patients (subject_id);',
        'CREATE INDEX IF NOT EXISTS mimiciii_admissions_hadm_idx    ON ehr.mimiciii_admissions (hadm_id);',
        'CREATE INDEX IF NOT EXISTS mimiciii_admissions_subject_idx ON ehr.mimiciii_admissions (subject_id);',
        'CREATE INDEX IF NOT EXISTS mimiciii_diagnoses_hadm_idx     ON ehr.mimiciii_diagnoses_icd (hadm_id);',
        'CREATE INDEX IF NOT EXISTS mimiciii_diagnoses_subject_idx  ON ehr.mimiciii_diagnoses_icd (subject_id);',
        'CREATE INDEX IF NOT EXISTS mimiciii_labs_subject_idx       ON ehr.mimiciii_labevents (subject_id);',
        'CREATE INDEX IF NOT EXISTS mimiciii_labs_hadm_idx          ON ehr.mimiciii_labevents (hadm_id);',
        'CREATE INDEX IF NOT EXISTS mimiciii_labs_charttime_idx     ON ehr.mimiciii_labevents (charttime);',

        # Notes
        'CREATE INDEX IF NOT EXISTS mimiciv_notes_subject_idx       ON text.mimiciv_notes (subject_id);',
        'CREATE INDEX IF NOT EXISTS mimiciv_notes_hadm_idx          ON text.mimiciv_notes (hadm_id);',
        'CREATE INDEX IF NOT EXISTS mimiciv_notes_charttime_idx     ON text.mimiciv_notes (charttime);',
    ]
    with conn.cursor() as cur:
        for sql in idx_sql:
            try:
                cur.execute(sql)
            except Exception as e:
                # Some tables may be absent if the user didn't load them—skip.
                pass
    conn.commit()

def ensure_notes_table(conn, header_cols):
    cols_sql = ", ".join([f'"{c}" {sql_type_for(c)}' for c in header_cols])
    psql(conn, f'CREATE TABLE IF NOT EXISTS text.mimiciv_notes ({cols_sql});')

# -----------------------------
# Main
# -----------------------------
def main():
    ap = argparse.ArgumentParser(description="MIMIC-III/MIMIC-IV loader (structured + notes)")
    ap.add_argument("--dir", required=True, help="Path to extracted MIMIC directory (e.g., mimic-iv-2.2 or MIMIC-III)")
    ap.add_argument("--version", choices=["iv","iii"], required=True, help="Which dataset layout to expect")
    ap.add_argument("--modules", default="patients,admissions,diagnoses_icd,labevents", help="Comma list; add 'icustays' if desired")
    ap.add_argument("--replace", action="store_true", help="TRUNCATE tables before load")
    ap.add_argument("--notes", action="store_true", help="Load MIMIC-IV notes (noteevents.csv[.gz]) into text.mimiciv_notes")
    ap.add_argument("--sample", type=int, help="Load only first N rows of each file (for smoke tests)")
    args = ap.parse_args()

    conn = psycopg2.connect(get_db_url())
    try:
        # Ensure schemas exist
        with conn.cursor() as cur:
            cur.execute("CREATE SCHEMA IF NOT EXISTS ehr;")
            cur.execute("CREATE SCHEMA IF NOT EXISTS text;")
        conn.commit()

        modules = [m.strip() for m in args.modules.split(",") if m.strip()]
        if args.version == "iv":
            loaded = load_csv_to_table(conn, args.dir, MIMICIV_MAP, "ehr", "mimiciv", modules, replace=args.replace, sample=args.sample)
        else:
            loaded = load_csv_to_table(conn, args.dir, MIMICIII_MAP, "ehr", "mimiciii", modules, replace=args.replace, sample=args.sample)

        if args.notes:
            if args.version != "iv":
                print("⚠️  Notes loading is only implemented for MIMIC-IV.", file=sys.stderr)
            else:
                p = sniff_file([os.path.join(args.dir, c) for c in NOTES_MAP_IV["notes"]])
                if not p:
                    print("⚠️  Could not find note/noteevents.csv(.gz)", file=sys.stderr)
                else:
                    with open_maybe_gz(p) as fh:
                        reader = csv.reader(fh)
                        hdr = next(reader)
                    cols = [norm_col(c) for c in hdr]
                    ensure_notes_table(conn, cols)
                    if args.replace:
                        truncate_table(conn, "text", "mimiciv_notes")
                    copy_csv(conn, "text", "mimiciv_notes", p, cols)
                    print(f"→ notes: {os.path.relpath(p, args.dir)}")

        create_basic_indexes(conn)

        # Quick stats
        with conn.cursor() as cur:
            def count(schema, table):
                try:
                    cur.execute(f'SELECT COUNT(*) FROM "{schema}"."{table}"')
                    return cur.fetchone()[0]
                except Exception:
                    return 0
            if args.version == "iv":
                print({
                    "patients":   count("ehr","mimiciv_patients"),
                    "admissions": count("ehr","mimiciv_admissions"),
                    "diagnoses":  count("ehr","mimiciv_diagnoses_icd"),
                    "labevents":  count("ehr","mimiciv_labevents"),
                    "notes":      count("text","mimiciv_notes")
                })
            else:
                print({
                    "patients":   count("ehr","mimiciii_patients"),
                    "admissions": count("ehr","mimiciii_admissions"),
                    "diagnoses":  count("ehr","mimiciii_diagnoses_icd"),
                    "labevents":  count("ehr","mimiciii_labevents")
                })

    finally:
        conn.close()

if __name__ == "__main__":
    main()

