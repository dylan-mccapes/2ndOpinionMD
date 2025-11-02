#!/usr/bin/env python3
import os, io, csv, zipfile, argparse, requests, psycopg2

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
    name = next((n for n in z.namelist() if "order" in n.lower() and n.lower().endswith(".txt")), z.namelist()[0])
    return io.StringIO(z.read(name).decode("utf-8", errors="replace"))

def open_txt(local_path: str, zip_url: str | None):
    if local_path and os.path.exists(local_path):
        return open(local_path, "r", encoding="utf-8", errors="replace")
    if zip_url:
        return open_txt_from_zip(zip_url)
    raise SystemExit(f"Missing ICD-10-CM order TXT. Provide a local file at {local_path} or set ICD10_CMS_ZIP_URL.")

def load_rows(fh):
    # The "order" file is usually pipe- or tab-delimited depending on year.
    sample = fh.read(4096)
    fh.seek(0)
    dialect = csv.Sniffer().sniff(sample, delimiters="|\t,")
    r = csv.reader(fh, dialect)
    rows = []
    for row in r:
        if not row: continue
        # Heuristic: code is first col, title maybe 2nd, long text near end
        code = (row[0] or "").strip()
        if not code or code.startswith("#"): 
            continue
        title = (row[1] if len(row) > 1 else "").strip()
        longd = (row[-1] if row else "").strip()
        rows.append((code, title, longd))
    return rows

def upsert(conn, rows):
    with conn, conn.cursor() as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS ontology.icd10cm(code text primary key, title text, long_description text)")
        cur.execute("CREATE INDEX IF NOT EXISTS icd10cm_code_idx ON ontology.icd10cm(code)")
        args = [(c,t or None,d or None) for c,t,d in rows]
        cur.execute("CREATE TEMP TABLE _icd10(cm_code text, title text, long_description text) ON COMMIT DROP;")
        cur.executemany("INSERT INTO _icd10 VALUES (%s,%s,%s);", args)
        cur.execute("""
            INSERT INTO ontology.icd10cm(code,title,long_description)
            SELECT cm_code,title,long_description FROM _icd10
            ON CONFLICT (code) DO UPDATE
              SET title=COALESCE(EXCLUDED.title, ontology.icd10cm.title),
                  long_description=COALESCE(EXCLUDED.long_description, ontology.icd10cm.long_description);
        """)
        cur.execute("SELECT COUNT(*) FROM ontology.icd10cm;")
        return cur.fetchone()[0]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--local", default=DEFAULT_LOCAL)
    ap.add_argument("--zip", dest="zip_url", default=os.getenv("ICD10_CMS_ZIP_URL"))
    args = ap.parse_args()

    fh = open_txt(args.local, args.zip_url)
    rows = load_rows(fh)
    conn = psycopg2.connect(get_dsn())
    n = upsert(conn, rows)
    conn.close()
    print(f"ICD-10-CM rows now: {n}")

if __name__ == "__main__":
    main()

