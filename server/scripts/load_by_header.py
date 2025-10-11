#!/usr/bin/env python3
import argparse, os, csv, gzip, io, tempfile, psycopg2
def open_maybe_gz(path, mode="rt"):
    return io.TextIOWrapper(gzip.open(path, "rb"), encoding="utf-8", newline="") if path.endswith(".gz") \
           else open(path, mode, encoding="utf-8", newline="")
def get_db_url():
    return (os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL") or "postgresql:///2ndopinionmd").replace("+asyncpg","")
def get_table_cols(conn, schema, table):
    with conn.cursor() as cur:
        cur.execute("""SELECT column_name FROM information_schema.columns
                       WHERE table_schema=%s AND table_name=%s ORDER BY ordinal_position""", (schema, table))
        return [r[0] for r in cur.fetchall()]
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", required=True)
    ap.add_argument("--csv", required=True)
    ap.add_argument("--truncate", action="store_true")
    args = ap.parse_args()
    schema, table = args.table.split(".", 1)
    conn = psycopg2.connect(get_db_url())
    try:
        with conn, conn.cursor() as cur:
            if args.truncate:
                cur.execute(f"TRUNCATE {args.table}")
        tbl_cols = get_table_cols(conn, schema, table)
        with open_maybe_gz(args.csv, "rt") as fh:
            reader = csv.DictReader(fh)
            csv_cols = reader.fieldnames or []
        use_cols = [c for c in csv_cols if c in tbl_cols]
        if not use_cols:
            raise SystemExit(f"No overlapping columns between CSV and {args.table}")
        with tempfile.NamedTemporaryFile("w+", delete=False, newline="") as tf:
            tmp = tf.name
            w = csv.DictWriter(tf, fieldnames=use_cols, lineterminator="\n")
            w.writeheader()
            with open_maybe_gz(args.csv, "rt") as fh:
                r = csv.DictReader(fh)
                for row in r:
                    w.writerow({k: row.get(k, "") for k in use_cols})
        with conn, conn.cursor() as cur:
            copy_sql = f"COPY {args.table} ({', '.join(use_cols)}) FROM STDIN WITH (FORMAT csv, HEADER true)"
            with open(tmp, "r", encoding="utf-8", newline="") as tfh:
                cur.copy_expert(copy_sql, tfh)
        os.remove(tmp)
        print(f"Loaded {args.table} from {os.path.basename(args.csv)} with {len(use_cols)} columns.")
    finally:
        conn.close()
if __name__ == "__main__":
    main()
