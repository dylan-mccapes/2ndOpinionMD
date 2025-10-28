#!/usr/bin/env python3
import os, csv, sys, psycopg2

DSN = (os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL") or "").replace("+asyncpg","")
if not DSN:
    print("Set DATABASE_URL or SYNC_DATABASE_URL", file=sys.stderr); sys.exit(2)

def main(path):
    conn = psycopg2.connect(DSN)
    try:
        cur = conn.cursor()
        # match by INN against the loaded EML for current edition/year
        cur.execute("SELECT DISTINCT edition, year FROM guidelines.who_eml_medicines ORDER BY year DESC, edition DESC LIMIT 1")
        edition, year = cur.fetchone()
        with open(path, newline='', encoding='utf-8') as f:
            r = csv.DictReader(f)
            n_ins = n_skipped = 0
            for row in r:
                inn = (row.get("inn") or "").strip()
                code = (row.get("icd11_code") or "").strip()
                ind  = (row.get("indication") or "").strip() or None
                if not (inn and code): 
                    n_skipped += 1; continue
                # find med_id(s) for this INN in the current edition/year
                cur.execute("""
                    SELECT med_id FROM guidelines.who_eml_medicines
                    WHERE inn ILIKE %s AND edition=%s AND year=%s
                """, (inn, edition, year))
                meds = cur.fetchall()
                if not meds:
                    n_skipped += 1; continue
                for (med_id,) in meds:
                    cur.execute("""
                        INSERT INTO guidelines.who_eml_icd11(med_id, icd11_code, indication)
                        VALUES (%s,%s,%s)
                        ON CONFLICT (med_id, icd11_code) DO NOTHING
                    """, (med_id, code, ind))
                    n_ins += 1
        conn.commit()
        print(f"[who_icd11_backfill] inserted {n_ins}, skipped {n_skipped}")
    finally:
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: who_icd11_backfill.py data/who/icd11_eml_map.csv", file=sys.stderr)
        sys.exit(2)
    main(sys.argv[1])
