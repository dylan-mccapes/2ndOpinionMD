#!/usr/bin/env python3
"""
Backfill rag_corpus.meta with section_id + doc info for VA/DoD and CDC rows.

Usage:
  SYNC_DATABASE_URL=postgresql://... python server/scripts/rag_backfill_meta.py
  python server/scripts/rag_backfill_meta.py --dry-run
  python server/scripts/rag_backfill_meta.py --source va
  python server/scripts/rag_backfill_meta.py --source cdc
"""

import os, sys, argparse
import psycopg2
from psycopg2.extras import RealDictCursor

VA_UPSERT = r"""
WITH upd AS (
  UPDATE public.rag_corpus r
  SET meta = COALESCE(r.meta,'{}'::jsonb)
             || jsonb_build_object('section_id', s.section_id, 'doc_slug', s.doc_slug)
  FROM guidelines.va_sections s
  WHERE r.source = 'va_guidelines'
    AND r.title = s.heading
    AND (r.meta IS NULL OR NOT (r.meta ? 'section_id'))
  RETURNING 1
)
SELECT count(*) AS n FROM upd;
"""

CDC_UPSERT = r"""
WITH upd AS (
  UPDATE public.rag_corpus r
  SET meta = COALESCE(r.meta,'{}'::jsonb)
             || jsonb_build_object('section_id', s.section_id, 'doc_id', s.doc_id)
  FROM guidelines.cdc_sections s
  WHERE r.source = 'cdc_opioid'
    AND r.title = s.heading
    AND (r.meta IS NULL OR NOT (r.meta ? 'section_id'))
  RETURNING 1
)
SELECT count(*) AS n FROM upd;
"""

VA_PREVIEW = r"""
SELECT count(*) AS n
FROM public.rag_corpus r
JOIN guidelines.va_sections s ON r.title = s.heading
WHERE r.source='va_guidelines'
  AND (r.meta IS NULL OR NOT (r.meta ? 'section_id'));
"""

CDC_PREVIEW = r"""
SELECT count(*) AS n
FROM public.rag_corpus r
JOIN guidelines.cdc_sections s ON r.title = s.heading
WHERE r.source='cdc_opioid'
  AND (r.meta IS NULL OR NOT (r.meta ? 'section_id'));
"""

def dsn_from_env() -> str:
    dsn = os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR: set SYNC_DATABASE_URL (preferred) or DATABASE_URL", file=sys.stderr)
        sys.exit(2)
    # strip +asyncpg if present
    return dsn.replace("+asyncpg", "")

def run(conn, sql) -> int:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql)
        row = cur.fetchone()
        return int(row["n"]) if row and "n" in row else 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["va","cdc","all"], default="all",
                    help="Limit to one source (default: all)")
    ap.add_argument("--dry-run", action="store_true", help="Preview counts only, no writes")
    args = ap.parse_args()

    dsn = dsn_from_env()
    conn = psycopg2.connect(dsn)
    try:
        conn.autocommit = False
        # Optional: keep runaway queries in check
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '5min';")

        total = 0

        if args.source in ("va", "all"):
            if args.dry_run:
                n = run(conn, VA_PREVIEW)
                print(f"[DRY] va_guidelines would update: {n}")
            else:
                n = run(conn, VA_UPSERT)
                print(f"va_guidelines updated: {n}")
            total += n

        if args.source in ("cdc", "all"):
            if args.dry_run:
                n = run(conn, CDC_PREVIEW)
                print(f"[DRY] cdc_opioid would update: {n}")
            else:
                n = run(conn, CDC_UPSERT)
                print(f"cdc_opioid updated: {n}")
            total += n

        if args.dry_run:
            print(f"[DRY] total would update: {total}")
            conn.rollback()
        else:
            conn.commit()
            print(f"Total updated: {total}")

        print("Tip: run `make integrity-orphans` to re-check for unmatched sections.")

    except Exception as e:
        conn.rollback()
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

if __name__ == "__main__":
    main()

