#!/usr/bin/env python3
"""
Load ClinVar variant_summary.txt(.gz) into PostgreSQL (schema: molecular, table: clinvar_summary).

- Detects and normalizes TSV header to snake_case (e.g., "#AlleleID" -> "alleleid").
- Adds any missing columns to molecular.clinvar_summary as TEXT (safe default).
- Uses COPY with explicit, normalized column list so auxiliary cols (e.g., loaded_at) aren't parsed from file.
- Backfills source_path and source_version metadata.
- Best-effort creation of helpful indexes.

Usage:
  server/venv312/bin/python server/scripts/ingest_clinvar_variant_summary.py \
    --file data/clinvar/variant_summary.txt.gz [--truncate] [--source-version 20250819]

Environment:
  Uses SYNC_DATABASE_URL or DATABASE_URL if set; falls back to postgresql://2ndopinionmd@localhost:5432/2ndopinionmd
"""
from __future__ import annotations

import argparse
import gzip
import os
import re
import sys
from pathlib import Path
from typing import List

import psycopg2
from psycopg2.extensions import connection as PGConn

# ---------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------

def get_db_url() -> str:
    url = (
        os.getenv("SYNC_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"
    )
    # psycopg2 doesn't understand +asyncpg
    return url.replace("+asyncpg", "")


def ensure_base_table(db: PGConn) -> None:
    ddl = (
        """
        CREATE SCHEMA IF NOT EXISTS molecular;
        CREATE TABLE IF NOT EXISTS molecular.clinvar_summary (
            loaded_at      TIMESTAMPTZ DEFAULT NOW(),
            source_path    TEXT,
            source_version TEXT
        );
        """
    )
    with db.cursor() as cur:
        cur.execute(ddl)
    db.commit()


def column_exists(cur, table_schema: str, table_name: str, col: str) -> bool:
    cur.execute(
        """
        SELECT 1
        FROM information_schema.columns
        WHERE table_schema=%s AND table_name=%s AND column_name=%s
        """,
        (table_schema, table_name, col),
    )
    return cur.fetchone() is not None


def ensure_columns(cur, cols: List[str]) -> None:
    for c in cols:
        # skip if already present
        if column_exists(cur, "molecular", "clinvar_summary", c):
            continue
        # add as TEXT (ClinVar TSV is mostly strings; downstream views can cast if needed)
        cur.execute(f'ALTER TABLE molecular.clinvar_summary ADD COLUMN "{c}" TEXT')


# ---------------------------------------------------------------------
# File/header helpers
# ---------------------------------------------------------------------

def norm(name: str) -> str:
    """Normalize a ClinVar header to a safe SQL identifier (snake_case)."""
    s = name.lstrip("#").strip()
    s = s.replace(" ", "_").replace("-", "_").replace("/", "_")
    s = s.lower()
    # Keep only [a-z0-9_]
    s = "".join(ch for ch in s if ch.isalnum() or ch == "_")
    # Avoid empty names
    return s or "col"


def read_header(fh) -> List[str]:
    """Read the first line (header) from a text-mode handle and return raw column names."""
    pos = fh.tell()
    line = fh.readline()
    if line.startswith("\ufeff"):  # strip BOM if present
        line = line[1:]
    cols = line.rstrip("\n\r").split("\t")
    # rewind to start for COPY later
    fh.seek(pos)
    return cols


def detect_version(path: Path) -> str:
    """Extract an 8-digit version from filename if present; else fall back to file mtime (YYYYMMDD)."""
    m = re.search(r"(20\d{6})", path.name)
    if m:
        return m.group(1)
    try:
        from datetime import datetime

        return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y%m%d")
    except Exception:
        return "unknown"


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Load ClinVar variant_summary.txt(.gz) into molecular.clinvar_summary"
    )
    ap.add_argument("--file", required=True, help="Path to variant_summary.txt or .txt.gz")
    ap.add_argument("--source-version", help="Override source version label (e.g., 20250819)")
    ap.add_argument("--truncate", action="store_true", help="TRUNCATE table before load")
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        print(f"❌ Not found: {path}", file=sys.stderr)
        sys.exit(2)

    dsn = get_db_url()
    db = psycopg2.connect(dsn)
    try:
        ensure_base_table(db)

        # open as TEXT mode so COPY can read strings
        if path.suffix == ".gz":
            fh = gzip.open(path, mode="rt", encoding="utf-8", newline="")
        else:
            fh = open(path, mode="rt", encoding="utf-8", newline="")

        with fh as f:
            # 1) inspect header
            raw_cols = read_header(f)
            cols_norm = [norm(c) for c in raw_cols]

            # 2) ensure columns exist (+ metadata columns)
            with db.cursor() as cur:
                ensure_columns(cur, cols_norm + ["source_path", "source_version"])
                if args.truncate:
                    cur.execute("TRUNCATE molecular.clinvar_summary")
            db.commit()

            # 3) COPY using normalized, quoted column list in the same order as file header
            col_list = ", ".join(f'"{c}"' for c in cols_norm)
            copy_sql = f"""
                COPY molecular.clinvar_summary ({col_list})
                FROM STDIN
                WITH (FORMAT csv, HEADER true, DELIMITER E'\t', QUOTE E'\b', NULL '')
            """

            # rewind to file start for COPY
            f.seek(0)
            with db.cursor() as cur:
                cur.copy_expert(copy_sql, f)

                # Backfill helper columns once per load
                ver = args.source_version or detect_version(path)
                cur.execute(
                    """
                    UPDATE molecular.clinvar_summary
                    SET source_path = %s,
                        source_version = COALESCE(source_version, %s)
                    WHERE source_path IS NULL
                    """,
                    (str(path), ver),
                )
            db.commit()

        # 4) Helpful indexes (best-effort)
        with db.cursor() as cur:
            try:
                cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
            except Exception:
                pass
            for ddl in [
                "CREATE INDEX IF NOT EXISTS clinvar_signif_idx      ON molecular.clinvar_summary (clinicalsignificance)",
                "CREATE INDEX IF NOT EXISTS clinvar_gene_idx        ON molecular.clinvar_summary (genesymbol)",
                "CREATE INDEX IF NOT EXISTS clinvar_rcv_idx         ON molecular.clinvar_summary (rcvaccession)",
                "CREATE INDEX IF NOT EXISTS clinvar_condition_trgm  ON molecular.clinvar_summary USING gin (phenotypelist gin_trgm_ops)",
            ]:
                try:
                    cur.execute(ddl)
                except Exception:
                    # Some columns may not exist in this ClinVar drop; ignore.
                    pass
        db.commit()

        # 5) Final stats
        with db.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM molecular.clinvar_summary")
            n = cur.fetchone()[0]
        print(f"✅ Loaded {n:,} ClinVar rows from {path.name}")

    except Exception as e:
        db.rollback()
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
