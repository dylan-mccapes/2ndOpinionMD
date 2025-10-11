#!/usr/bin/env python3
import argparse, os, sys, re, psycopg2
from psycopg2.extras import execute_batch

def parse_line(line: str):
    line = line.strip()
    if not line:
        return None
    # Support "CODE<TAB>TITLE" or "CODE  Title ..."
    if "\t" in line:
        code, title = line.split("\t", 1)
    else:
        m = re.match(r'^([A-TV-Z][0-9][0-9A-Z](?:\.[0-9A-Z]{1,4})?)\s+(.+)$', line, flags=re.I)
        if not m:
            return None
        code, title = m.group(1), m.group(2)
    return code.strip().upper(), title.strip()

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--file", required=True, help="Flat ICD-10-CM file (CODE<TAB>TITLE) or whitespace 'CODE  Title'")
    p.add_argument("--dsn",  required=True, help="Postgres DSN")
    args = p.parse_args()

    if not os.path.exists(args.file):
        print(f"ERROR: file not found: {args.file}", file=sys.stderr)
        sys.exit(2)

    rows = []
    with open(args.file, "r", encoding="utf-8") as f:
        for ln, line in enumerate(f, 1):
            if not line.strip(): 
                continue
            parsed = parse_line(line)
            if not parsed:
                # tolerate junk header lines
                continue
            rows.append(parsed)

    if not rows:
        print("No rows parsed; nothing to import.")
        return

    sql = """
        INSERT INTO ontology.icd10cm(code, title)
        VALUES (%s, %s)
        ON CONFLICT (code) DO UPDATE SET title = EXCLUDED.title
    """
    conn = psycopg2.connect(args.dsn)
    conn.autocommit = False
    with conn, conn.cursor() as cur:
        execute_batch(cur, sql, rows, page_size=1000)
    conn.close()
    print(f"Imported/updated {len(rows)} ICD-10-CM rows into ontology.icd10cm")

if __name__ == "__main__":
    main()

