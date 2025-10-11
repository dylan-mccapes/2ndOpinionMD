#!/usr/bin/env python3
import os, sys, argparse, glob, psycopg2

def dsn():
    return os.environ.get("SYNC_DATABASE_URL") or "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"

def find_root(root_arg):
    if root_arg and os.path.isdir(root_arg):
        return root_arg
    cands = sorted(glob.glob("data/SnomedCT_*"))
    if not cands:
        sys.exit("ERROR: No SNOMED root found under data/. Pass --root /path/to/SnomedCT_*")
    return cands[-1]

def find_map_file(root):
    for pat in (
        f"{root}/Snapshot/Refset/Map/der2_iisssccRefset_ExtendedMapSnapshot_*.txt",
        f"{root}/Snapshot/Refset/Map/*ExtendedMapSnapshot*.txt",
    ):
        files = sorted(glob.glob(pat))
        if files:
            return files[0]
    sys.exit(f"ERROR: ExtendedMapSnapshot file not found in {root}/Snapshot/Refset/Map/")

DDL = """
CREATE SCHEMA IF NOT EXISTS ontology;

CREATE TABLE IF NOT EXISTS ontology.snomed_map_icd10cm (
  referenced_component_id bigint NOT NULL,
  map_group int NOT NULL,
  map_priority int NOT NULL,
  map_target text NOT NULL,
  map_rule text,
  map_advice text,
  correlation_id bigint,
  map_category_id bigint,
  effective_time date,
  active boolean,
  module_id bigint,
  refset_id bigint,
  CONSTRAINT snomed_map_icd10cm_pk
    PRIMARY KEY (referenced_component_id, map_group, map_priority, map_target)
);

CREATE INDEX IF NOT EXISTS snomed_map_icd10cm_concept_idx ON ontology.snomed_map_icd10cm (referenced_component_id);
CREATE INDEX IF NOT EXISTS snomed_map_icd10cm_target_idx  ON ontology.snomed_map_icd10cm (map_target);

DROP TABLE IF EXISTS map_stage;
CREATE TEMP TABLE map_stage (
  id text,
  effectiveTime text,
  active text,
  moduleId text,
  refsetId text,
  referencedComponentId text,
  mapGroup text,
  mapPriority text,
  mapRule text,
  mapAdvice text,
  mapTarget text,
  correlationId text,
  mapCategoryId text
);
"""

COPY_CMD = """
COPY map_stage (id,effectiveTime,active,moduleId,refsetId,referencedComponentId,
                mapGroup,mapPriority,mapRule,mapAdvice,mapTarget,correlationId,mapCategoryId)
FROM STDIN WITH (FORMAT csv, DELIMITER E'\t', HEADER true)
"""

UPSERT = """
WITH ranked AS (
  SELECT
    NULLIF(referencedComponentId,'')::bigint AS referenced_component_id,
    NULLIF(mapGroup,'')::int                 AS map_group,
    NULLIF(mapPriority,'')::int              AS map_priority,
    NULLIF(mapTarget,'')                     AS map_target,
    NULLIF(mapRule,'')                       AS map_rule,
    NULLIF(mapAdvice,'')                     AS map_advice,
    NULLIF(correlationId,'')::bigint         AS correlation_id,
    NULLIF(mapCategoryId,'')::bigint         AS map_category_id,
    CASE WHEN effectiveTime ~ '^[0-9]{8}$'
         THEN to_date(effectiveTime,'YYYYMMDD') END AS effective_time,
    (active='1')                              AS active,
    NULLIF(moduleId,'')::bigint              AS module_id,
    NULLIF(refsetId,'')::bigint              AS refset_id,
    ROW_NUMBER() OVER (
      PARTITION BY NULLIF(referencedComponentId,'')::bigint,
                   NULLIF(mapGroup,'')::int,
                   NULLIF(mapPriority,'')::int,
                   NULLIF(mapTarget,'')
      ORDER BY (active='1') DESC,
               CASE WHEN effectiveTime ~ '^[0-9]{8}$'
                    THEN to_date(effectiveTime,'YYYYMMDD') END DESC
    ) rn
  FROM map_stage
  WHERE NULLIF(referencedComponentId,'') <> '' AND NULLIF(mapTarget,'') <> ''
)
INSERT INTO ontology.snomed_map_icd10cm (
  referenced_component_id, map_group, map_priority, map_target,
  map_rule, map_advice, correlation_id, map_category_id,
  effective_time, active, module_id, refset_id
)
SELECT referenced_component_id, map_group, map_priority, map_target,
       map_rule, map_advice, correlation_id, map_category_id,
       effective_time, active, module_id, refset_id
FROM ranked
WHERE rn = 1
ON CONFLICT (referenced_component_id, map_group, map_priority, map_target) DO UPDATE
SET map_rule       = EXCLUDED.map_rule,
    map_advice     = EXCLUDED.map_advice,
    correlation_id = EXCLUDED.correlation_id,
    map_category_id= EXCLUDED.map_category_id,
    effective_time = EXCLUDED.effective_time,
    active         = EXCLUDED.active,
    module_id      = EXCLUDED.module_id,
    refset_id      = EXCLUDED.refset_id;

ANALYZE ontology.snomed_map_icd10cm;
"""

def main():
    ap = argparse.ArgumentParser(description="Import SNOMED ExtendedMap (ICD-10-CM)")
    ap.add_argument("--root", help="SNOMED root dir (SnomedCT_*). Omit to auto-pick newest under data/")
    args = ap.parse_args()

    root = find_root(args.root)
    path = find_map_file(root)
    print(f">>> Using root: {root}")
    print(f">>> Map file:  {path}")

    with psycopg2.connect(dsn()) as conn, conn.cursor() as cur:
        cur.execute(DDL)
        with open(path, "r", encoding="utf-8", newline="") as f:
            cur.copy_expert(COPY_CMD, f)
        cur.execute(UPSERT)
    print("✓ ExtendedMap import complete.")

if __name__ == "__main__":
    main()

