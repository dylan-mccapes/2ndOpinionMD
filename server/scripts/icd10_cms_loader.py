#!/usr/bin/env python3
import os, io, csv, zipfile, argparse, requests, psycopg2, re

# Prefer local path; fallback to CMS ZIP if provided via env/flag.
# Example CMS page lists the "Code Descriptions in Tabular Order (ZIP)" for FY 2026.
# Set ICD10_CMS_ZIP_URL env to direct ZIP if you have it.
DEFAULT_LOCAL = "server/data/icd10/icd10cm-order.txt"


def get_dsn():
    dsn = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
    return dsn or "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"


def open_txt_from_zip(url: str) -> io.StringIO:
    r = requests.get(url, timeout=120)
    r.raise_for_status()
    z = zipfile.ZipFile(io.BytesIO(r.content))
    # pick first file that looks like icd10cm_order_*.txt
    name = next(
        (
            n
            for n in z.namelist()
            if "order" in n.lower() and n.lower().endswith(".txt")
        ),
        z.namelist()[0],
    )
    return io.StringIO(z.read(name).decode("utf-8", errors="replace"))


def open_txt(local_path: str, zip_url: str | None):
    if local_path and os.path.exists(local_path):
        return open(local_path, "r", encoding="utf-8", errors="replace")
    if zip_url:
        return open_txt_from_zip(zip_url)
    raise SystemExit(
        f"Missing ICD-10-CM order TXT. Provide a local file at {local_path} "
        "or set ICD10_CMS_ZIP_URL."
    )


def load_rows(fh):
    """
    Parse the CMS ICD-10-CM tabular-order file into (code, title_short, title_long).

    This is defensive and works with:
      - pipe-delimited
      - tab-delimited
      - comma-delimited
      - or plain whitespace / fixed-width lines like:
          A00.0 Cholera due to Vibrio cholerae 01, biovar cholerae
    """
    rows = []
    for raw in fh:
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue
        # Skip obvious comment lines if any
        if line.lstrip().startswith("#"):
            continue

        # Try to guess delimiter PER LINE
        parts = None

        if "|" in line:
            parts = [p.strip() for p in line.split("|")]
        elif "\t" in line:
            parts = [p.strip() for p in line.split("\t")]
        elif "," in line:
            # Only treat as comma-delimited if it clearly looks like CODE,<something>
            # (otherwise RA descriptions will have tons of commas)
            if re.match(r"^[A-Z0-9.]+,", line):
                parts = [p.strip() for p in line.split(",")]

        if parts:
            code = (parts[0] or "").strip()
            if not code:
                continue
            title_short = (parts[1] if len(parts) > 1 else None) or None
            title_long = (parts[-1] if len(parts) > 1 else None) or None
            rows.append((code, title_short, title_long))
            continue

        # Fallback: whitespace / fixed-width – assume "CODE<space>DESCRIPTION"
        m = re.match(r"^([A-Z0-9.]+)\s+(.+)$", line)
        if not m:
            # Give up on this line
            continue

        code = m.group(1).strip()
        desc = m.group(2).strip()
        if not code or not desc:
            continue

        title_short = None
        title_long = desc
        rows.append((code, title_short, title_long))

    return rows


def ensure_table(conn):
    """Ensure ontology.icd10cm matches the expected schema."""
    with conn, conn.cursor() as cur:
        cur.execute(
            """
            CREATE SCHEMA IF NOT EXISTS ontology;

            CREATE TABLE IF NOT EXISTS ontology.icd10cm(
                code           text PRIMARY KEY,
                title_long     text,
                title_short    text,
                parent_code    text,
                chapter        text,
                block          text,
                effective_year integer,
                source_file    text
            );
            """
        )


def upsert(conn, rows, source_file: str, effective_year: int | None):
    """
    Upsert (code, title_short, title_long, effective_year, source_file)
    into ontology.icd10cm, leaving parent_code/chapter/block alone.
    """
    ensure_table(conn)

    with conn, conn.cursor() as cur:
        # temp table with just the columns we know
        cur.execute(
            """
            CREATE TEMP TABLE _icd10(
                code           text,
                title_short    text,
                title_long     text,
                effective_year integer,
                source_file    text
            ) ON COMMIT DROP;
            """
        )

        args = [
            (code, t_short, t_long, effective_year, source_file)
            for (code, t_short, t_long) in rows
        ]
        cur.executemany(
            "INSERT INTO _icd10(code, title_short, title_long, effective_year, source_file) "
            "VALUES (%s,%s,%s,%s,%s);",
            args,
        )

        # merge into main table
        cur.execute(
            """
            INSERT INTO ontology.icd10cm AS dst
                (code, title_short, title_long, effective_year, source_file)
            SELECT
                code, title_short, title_long, effective_year, source_file
            FROM _icd10
            ON CONFLICT (code) DO UPDATE
            SET
                title_short = COALESCE(EXCLUDED.title_short, dst.title_short),
                title_long  = COALESCE(EXCLUDED.title_long,  dst.title_long),
                effective_year = COALESCE(EXCLUDED.effective_year, dst.effective_year),
                source_file    = COALESCE(EXCLUDED.source_file,    dst.source_file);
            """
        )

        cur.execute("SELECT COUNT(*) FROM ontology.icd10cm;")
        return cur.fetchone()[0]


def infer_year_from_path(path: str) -> int | None:
    """
    Try to pull a year like 2024/2025/2026 from the filename.
    Returns None if not found.
    """
    basename = os.path.basename(path)
    m = re.search(r"(20[0-9]{2})", basename)
    return int(m.group(1)) if m else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", default=DEFAULT_LOCAL)
    ap.add_argument(
        "--zip", dest="zip_url", default=os.getenv("ICD10_CMS_ZIP_URL")
    )
    args = ap.parse_args()

    local_path = args.local
    fh = open_txt(local_path, args.zip_url)

    rows = load_rows(fh)
    if not rows:
        raise SystemExit("No ICD-10-CM rows parsed from input file.")

    source_file = os.path.basename(local_path) if local_path else "icd10cm-order.txt"
    effective_year = infer_year_from_path(local_path) if local_path else None

    conn = psycopg2.connect(get_dsn())
    try:
        n = upsert(conn, rows, source_file=source_file, effective_year=effective_year)
    finally:
        conn.close()

    print(f"ICD-10-CM rows now: {n} (year={effective_year}, source_file={source_file})")


if __name__ == "__main__":
    main()
