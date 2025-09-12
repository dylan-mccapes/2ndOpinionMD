#!/usr/bin/env python3
import csv, argparse, os, sys, gzip, io
import psycopg2
from psycopg2 import sql

DDL = os.path.join(os.path.dirname(__file__), "setup_mimic3_schemas.sql")

FILES = {
    # file_name (case-insensitive) : (table, required)
    "PATIENTS.csv":             ("ehr_mimic3.patients", True),
    "ADMISSIONS.csv":           ("ehr_mimic3.admissions", True),
    "ICUSTAYS.csv":             ("ehr_mimic3.icustays", True),
    "D_ICD_DIAGNOSES.csv":      ("ehr_mimic3.d_icd_diagnoses", True),
    "DIAGNOSES_ICD.csv":        ("ehr_mimic3.diagnoses_icd", True),
    "D_ICD_PROCEDURES.csv":     ("ehr_mimic3.d_icd_procedures", False),
    "PROCEDURES_ICD.csv":       ("ehr_mimic3.procedures_icd", False),
    "D_LABITEMS.csv":           ("ehr_mimic3.d_labitems", True),
    "LABEVENTS.csv":            ("ehr_mimic3.labevents", True),
}

def get_db_url():
    return (os.getenv("DATABASE_URL") or "postgresql:///2ndopinionmd").replace("+asyncpg", "")

def find_file(root, name):
    """Return path to <name> or <name>.gz (case-insensitive) within root."""
    want = name.lower()
    for fn in os.listdir(root):
        lf = fn.lower()
        if lf == want or lf == want + ".gz":
            return os.path.join(root, fn)
    # Also accept exact .csv.gz naming
    gz = want.replace(".csv", ".csv.gz")
    for fn in os.listdir(root):
        if fn.lower() == gz:
            return os.path.join(root, fn)
    return None

def open_maybe_gz(path):
    if path.lower().endswith(".gz"):
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", newline="")
    return open(path, "r", encoding="utf-8", newline="")

def open_maybe_gz(path: str, mode: str = "rt", encoding: str = "utf-8"):
    """
    Open .gz in text mode via a TextIOWrapper to normalize newlines for COPY.
    """
    if path.endswith(".gz"):
        if "b" in mode:
            return gzip.open(path, mode)
        # open gzip in binary, wrap with text
        return io.TextIOWrapper(gzip.open(path, "rb"), encoding=encoding, newline="")
    return open(path, mode, encoding=encoding, newline="")

def read_header(path: str):
    """
    Read the first row using csv to honor quoting; return lower-cased column names.
    """
    with open_maybe_gz(path, "rt") as fh:
        rdr = csv.reader(fh)
        header = next(rdr)
    return [h.strip().lower() for h in header]

def copy_csv(cur, table_qualified: str, path: str):
    """
    COPY with an explicit column list taken from the file header so row_id and
    any column order mismatches don't break the load.
    """
    cols = read_header(path)                # e.g., ['row_id','subject_id',...]
    col_list = ", ".join(cols)              # unquoted → case-insensitive lower
    copy_sql = f"COPY {table_qualified} ({col_list}) FROM STDIN WITH (FORMAT csv, HEADER true)"
    with open_maybe_gz(path, "rt") as fh:
        cur.copy_expert(copy_sql, fh)

def main():
    ap = argparse.ArgumentParser(description="Ingest MIMIC-III v1.4 structured tables")
    ap.add_argument("--dir", required=True, help="Directory containing MIMIC-III CSV(.gz) files")
    ap.add_argument("--dry-run", action="store_true", help="Parse schema only; do not COPY data")
    args = ap.parse_args()

    root = args.dir
    present = {}
    missing_required = []

    # Resolve files
    for fname, (table, required) in FILES.items():
        p = find_file(root, fname)
        if p:
            present[fname] = (table, p)
        elif required:
            missing_required.append(fname)

    if missing_required:
        print("❌ Missing required files:", ", ".join(missing_required))
        sys.exit(2)

    print("Files found:")
    for k, (_, p) in present.items():
        print(f"  - {k}  ->  {os.path.basename(p)}")

    # Connect and ensure schema
    db = psycopg2.connect(get_db_url())
    try:
        with db, db.cursor() as cur:
            ddl = open(DDL, "r", encoding="utf-8").read()
            cur.execute(ddl)
            print("✅ Schema ready.")

        if args.dry_run:
            print("🔍 DRY RUN: not loading data.")
            return

        # Load small dims first
        order = [
            "PATIENTS.csv",
            "ADMISSIONS.csv",
            "ICUSTAYS.csv",
            "D_ICD_DIAGNOSES.csv",
            "D_ICD_PROCEDURES.csv",
            "D_LABITEMS.csv",
            "DIAGNOSES_ICD.csv",
            "PROCEDURES_ICD.csv",
            "LABEVENTS.csv",
        ]
        with db, db.cursor() as cur:
            for fname in order:
                if fname not in present:
                    continue
                table, path = present[fname]
                print(f"→ Loading {fname} into {table} ...")
                copy_csv(cur, table, path)
            print("✅ Load complete.")
    finally:
        db.close()

if __name__ == "__main__":
    main()

