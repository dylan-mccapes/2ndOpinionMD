#!/usr/bin/env python3
import argparse
import os
import sys
import gzip
import io
import csv
import tempfile
import psycopg2

# ---------------------------
# Config / helpers
# ---------------------------

REQUIRED_KEYS_IN_ORDER = [
    # hosp
    "patients",
    "admissions",
    "transfers",
    "d_labitems",
    "labevents",
    "d_icd_diagnoses",
    "diagnoses_icd",
    "d_icd_procedures",
    "procedures_icd",
    # icu
    "icustays",
    "d_items",
]

TABLE_FOR_KEY = {
    "patients":         "ehr_mimic4.patients",
    "admissions":       "ehr_mimic4.admissions",
    "transfers":        "ehr_mimic4.transfers",
    "d_labitems":       "ehr_mimic4.d_labitems",
    "labevents":        "ehr_mimic4.labevents",
    "d_icd_diagnoses":  "ehr_mimic4.d_icd_diagnoses",
    "diagnoses_icd":    "ehr_mimic4.diagnoses_icd",
    "d_icd_procedures": "ehr_mimic4.d_icd_procedures",
    "procedures_icd":   "ehr_mimic4.procedures_icd",
    "icustays":         "ehr_mimic4.icustays",
    "d_items":          "ehr_mimic4.d_items",
}

def get_db_url() -> str:
    url = os.getenv("DATABASE_URL") or "postgresql:///2ndopinionmd"
    return url.replace("+asyncpg", "")

def open_maybe_gz(path: str, mode: str = "rt"):
    if path.lower().endswith(".gz"):
        return gzip.open(path, mode, encoding="utf-8", newline="")
    return open(path, mode, encoding="utf-8", newline="")

def read_header(path: str):
    with open_maybe_gz(path, "rt") as fh:
        reader = csv.reader(fh)
        try:
            return next(reader)
        except StopIteration:
            return []

def locate_files(base_dir: str):
    """
    Find required MIMIC-IV v2.2 files under base_dir/{hosp,icu}.
    Accepts .csv or .csv.gz, case-insensitive filenames.
    Returns: (files_dict, missing_list)
    """
    def find_one(subdir: str, stem: str):
        candidates = []
        for name in (stem, stem.lower(), stem.upper(), stem.capitalize()):
            for ext in (".csv.gz", ".csv"):
                candidates.append(os.path.join(base_dir, subdir, f"{name}{ext}"))
        for p in candidates:
            if os.path.exists(p):
                return os.path.abspath(p)
        return None

    files = {
        # hosp
        "patients":         find_one("hosp", "patients"),
        "admissions":       find_one("hosp", "admissions"),
        "transfers":        find_one("hosp", "transfers"),
        "d_labitems":       find_one("hosp", "d_labitems"),
        "labevents":        find_one("hosp", "labevents"),
        "d_icd_diagnoses":  find_one("hosp", "d_icd_diagnoses"),
        "diagnoses_icd":    find_one("hosp", "diagnoses_icd"),
        "d_icd_procedures": find_one("hosp", "d_icd_procedures"),
        "procedures_icd":   find_one("hosp", "procedures_icd"),
        # icu
        "icustays":         find_one("icu", "icustays"),
        "d_items":          find_one("icu", "d_items"),
    }

    print("Files found:")
    for k in REQUIRED_KEYS_IN_ORDER:
        v = files.get(k)
        print(f"  - {k:<17} -> {os.path.basename(v) if v else 'MISSING'}")

    missing = [k for k, v in files.items() if v is None]
    if missing:
        print(f"❌ Missing required files: {', '.join(missing)}")
    return files, missing

def get_table_columns(conn, schema: str, table: str):
    """
    Returns table columns in physical order (ordinal_position).
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema=%s AND table_name=%s
            ORDER BY ordinal_position
            """,
            (schema, table)
        )
        return [r[0] for r in cur.fetchall()]

def split_qualified(name: str):
    # "ehr_mimic4.admissions" -> ("ehr_mimic4", "admissions")
    parts = name.split(".")
    if len(parts) != 2:
        raise ValueError(f"Expected schema.table, got: {name}")
    return parts[0], parts[1]

def copy_csv_direct(cur, table: str, path: str):
    copy_sql = f"""COPY {table}
FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER ',', QUOTE '"', ESCAPE '"', NULL '')"""
    with open_maybe_gz(path, "rt") as fh:
        cur.copy_expert(copy_sql, fh)

def copy_csv_projected(cur, table: str, path: str, cols_to_use: list[str]):
    """
    Read the CSV and write only the selected columns (in that order)
    to a temp file, then COPY from that temp file.
    """
    # Write a projected CSV to a temp file (on disk to avoid RAM blowups)
    with tempfile.NamedTemporaryFile("w+", delete=True, newline="") as tf:
        writer = csv.writer(tf, lineterminator="\n")
        # header
        writer.writerow(cols_to_use)

        with open_maybe_gz(path, "rt") as fh:
            reader = csv.DictReader(fh)
            # Ensure case-sensitive exact match with reader.fieldnames
            # We only select those present both in table and file.
            for row in reader:
                writer.writerow([row.get(col, "") for col in cols_to_use])

        tf.flush()
        tf.seek(0)

        copy_sql = f"""COPY {table} ({", ".join(cols_to_use)})
FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER ',', QUOTE '"', ESCAPE '"', NULL '')"""
        cur.copy_expert(copy_sql, tf)

def needs_projection(csv_header: list[str], table_cols: list[str]):
    """
    Decide fast path vs projected path.
    We ignore a trailing 'row_id' or any identity/serial col in the table.
    Fast path if csv_header == table_cols OR csv_header == table_cols without the trailing row_id.
    """
    # Exclude common synthetic PKs if present
    tbl_cols_no_rowid = [c for c in table_cols if c != "row_id"]

    if csv_header == table_cols:
        return False
    if csv_header == tbl_cols_no_rowid:
        return False
    return True

def common_cols_in_csv_order(csv_header: list[str], table_cols: list[str]):
    """
    Return the list of columns that are present in BOTH csv_header and table_cols,
    preserving the CSV order, and skipping 'row_id' if present in the table.
    """
    table_set = set(table_cols) - {"row_id"}
    return [c for c in csv_header if c in table_set]

# ---------------------------
# Main
# ---------------------------

def main():
    ap = argparse.ArgumentParser(description="Import MIMIC-IV v2.2 (hosp + icu) into Postgres schema ehr_mimic4")
    ap.add_argument("--dir", required=True, help="Path to root MIMIC-IV directory (contains hosp/ and icu/)")
    ap.add_argument("--dry-run", action="store_true", help="Only validate file discovery and headers; do not load")
    ap.add_argument("--limit", type=int, default=None, help="(Optional) Not used now; kept for symmetry.")
    args = ap.parse_args()

    base_dir = args.dir
    files, missing = locate_files(base_dir)
    if missing:
        sys.exit(1)

    # Header checks
    print("\nHeader checks:")
    headers = {}
    for key in REQUIRED_KEYS_IN_ORDER:
        path = files[key]
        hdr = read_header(path)
        headers[key] = hdr
        print(f"  {key:<17} : {len(hdr)} columns")

    if args.dry_run:
        print("\n🔍 DRY RUN: not loading data.")
        return

    db_url = get_db_url()
    conn = psycopg2.connect(db_url)
    try:
        conn.autocommit = False
        with conn.cursor() as cur:
            for key in REQUIRED_KEYS_IN_ORDER:
                table = TABLE_FOR_KEY[key]
                path = files[key]
                schema, tbl = split_qualified(table)
                table_cols = get_table_columns(conn, schema, tbl)
                csv_header = headers[key]

                print(f"→ Loading {os.path.basename(path)} into {table} ...")
                if not csv_header:
                    # Empty file or no header; still try direct COPY (it will error if malformed)
                    copy_csv_direct(cur, table, path)
                    conn.commit()
                    continue

                if needs_projection(csv_header, table_cols):
                    # Project only the intersecting columns, in CSV order
                    cols_to_use = common_cols_in_csv_order(csv_header, table_cols)
                    if not cols_to_use:
                        raise RuntimeError(f"No overlapping columns between CSV and table for {table}")
                    copy_csv_projected(cur, table, path, cols_to_use)
                else:
                    # Orders match (or row_id is only extra in table) -> direct, fast path
                    copy_csv_direct(cur, table, path)

                conn.commit()  # commit per table to bound the transaction

        print("✅ Load complete.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error during load: {e}")
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()

