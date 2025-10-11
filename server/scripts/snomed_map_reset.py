#!/usr/bin/env python3
import os, psycopg2, sys

DDL = """
CREATE SCHEMA IF NOT EXISTS ontology;

DROP TABLE IF EXISTS ontology.snomed_map_icd10cm CASCADE;
CREATE TABLE ontology.snomed_map_icd10cm (
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
"""

def main():
    dsn = os.environ.get("SYNC_DATABASE_URL", "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd")
    with psycopg2.connect(dsn) as conn, conn.cursor() as cur:
        cur.execute(DDL)
    print("✓ snomed_map_icd10cm reset (dropped, recreated, indexed).")

if __name__ == "__main__":
    sys.exit(main())

