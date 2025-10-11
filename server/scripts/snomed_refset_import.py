#!/usr/bin/env python3
import os, re, sys
import psycopg2
from contextlib import closing

LANG_PATTERNS = [
    r"der2_cRefset_LanguageSnapshot-en_US.*\.txt$",
    r"der2_cRefset_LanguageSnapshot-.*\.txt$",
]

DDL_FIX = """
-- Ensure base table & columns exist (idempotent)
CREATE TABLE IF NOT EXISTS ontology.refset_members (
  member_id text,
  effective_time date,
  active boolean,
  module_id bigint,
  refset_id bigint,
  referenced_component_id bigint,
  acceptability_id bigint
);
ALTER TABLE ontology.refset_members
  ADD COLUMN IF NOT EXISTS member_id text,
  ADD COLUMN IF NOT EXISTS effective_time date,
  ADD COLUMN IF NOT EXISTS active boolean,
  ADD COLUMN IF NOT EXISTS module_id bigint,
  ADD COLUMN IF NOT EXISTS refset_id bigint,
  ADD COLUMN IF NOT EXISTS referenced_component_id bigint,
  ADD COLUMN IF NOT EXISTS acceptability_id bigint;

-- Useful/unique indexes
CREATE UNIQUE INDEX IF NOT EXISTS refset_members_uniq_triplet
  ON ontology.refset_members (referenced_component_id, refset_id, acceptability_id);
CREATE INDEX IF NOT EXISTS refset_members_ref_comp_idx
  ON ontology.refset_members (referenced_component_id);
"""

# TEMP staging table must NOT be schema-qualified
DDL_STAGE = """
CREATE TEMP TABLE IF NOT EXISTS _snomed_lang_stage(
  member_id                text,
  effective_time_raw       text,
  active_raw               text,
  module_id                bigint,
  refset_id                bigint,
  referenced_component_id  bigint,
  acceptability_id         bigint
) ON COMMIT DROP;
TRUNCATE _snomed_lang_stage;
"""

UPSERT_DEDUP = """
WITH ranked AS (
  SELECT
    member_id,
    to_date(effective_time_raw,'YYYYMMDD') AS effective_time,
    (active_raw IN ('1','t','true','T','TRUE')) AS active,
    module_id,
    refset_id,
    referenced_component_id,
    acceptability_id,
    ROW_NUMBER() OVER (
      PARTITION BY referenced_component_id, refset_id, acceptability_id
      ORDER BY to_date(effective_time_raw,'YYYYMMDD') DESC NULLS LAST,
               (active_raw IN ('1','t','true','T','TRUE')) DESC,
               member_id DESC
    ) rn
  FROM _snomed_lang_stage
)
INSERT INTO ontology.refset_members
  (member_id, effective_time, active, module_id, refset_id,
   referenced_component_id, acceptability_id)
SELECT member_id, effective_time, active, module_id, refset_id,
       referenced_component_id, acceptability_id
FROM ranked
WHERE rn = 1
ON CONFLICT (referenced_component_id, refset_id, acceptability_id)
DO UPDATE SET
  member_id      = EXCLUDED.member_id,
  effective_time = EXCLUDED.effective_time,
  active         = EXCLUDED.active,
  module_id      = EXCLUDED.module_id;
"""

ALIAS_VIEW_DROP   = "DROP VIEW IF EXISTS ontology.snomed_refset_members;"
ALIAS_VIEW_CREATE = "CREATE OR REPLACE VIEW ontology.snomed_refset_members AS SELECT * FROM ontology.refset_members;"

def find_lang_file(root: str) -> str:
    for dirpath, _, files in os.walk(root):
        for fn in files:
            path = os.path.join(dirpath, fn)
            if any(re.search(pat, path) for pat in LANG_PATTERNS):
                return path
    return ""

def dsn():
    url = os.environ.get("SYNC_DATABASE_URL") or os.environ.get("DATABASE_URL") or "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"
    return url.replace("+asyncpg", "")

def main():
    root = os.environ.get("SNOMED_ROOT", "data")
    lang_file = os.environ.get("SNOMED_LANG_FILE") or find_lang_file(root)
    print(">>> SNOMED Language Refset import (auto)")
    print(f">>> Using root: {root}")
    if not lang_file:
        print("ERROR: Could not locate der2_cRefset_LanguageSnapshot*.txt under", root, file=sys.stderr)
        sys.exit(2)
    print(">>> Language file:", lang_file)

    with closing(psycopg2.connect(dsn())) as conn, conn, conn.cursor() as cur:
        # Ensure table/columns/indexes exist
        cur.execute(DDL_FIX)
        # Stage table
        cur.execute(DDL_STAGE)

        # COPY RF2 (tab-delimited with header); booleans are '1'/'0'; date is yyyymmdd
        with open(lang_file, "r", encoding="utf-8", newline="") as f:
            cur.copy_expert(
                """
                COPY _snomed_lang_stage
                (member_id,effective_time_raw,active_raw,module_id,refset_id,referenced_component_id,acceptability_id)
                FROM STDIN WITH (FORMAT csv, HEADER true, DELIMITER E'\t', QUOTE E'\b', ESCAPE E'\b')
                """,
                f,
            )

        # Refresh helper view (if your API uses it)
        cur.execute(ALIAS_VIEW_DROP)
        cur.execute(ALIAS_VIEW_CREATE)

        # De-dup + upsert
        cur.execute(UPSERT_DEDUP)

        # Count
        cur.execute("SELECT COUNT(*) FROM ontology.refset_members;")
        n = cur.fetchone()[0]
        print(f"✓ Language refset import complete. Rows in ontology.refset_members: {n}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("DB ERROR:", e, file=sys.stderr)
        sys.exit(3)
