\set ON_ERROR_STOP on
-- Detect presence of normalized SNOMED tables
DO $$
DECLARE
  c bool := EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='ontology' AND table_name='concepts');
  d bool := EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='ontology' AND table_name='descriptions');
  r bool := EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='ontology' AND table_name='relationships');
BEGIN
  RAISE NOTICE 'has_concepts=% has_descriptions=% has_relationships=%', c, d, r;
END$$;

-- Table sizes (subset)
SELECT n.nspname AS schema, c.relname AS table_name,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS size,
       (SELECT reltuples::bigint FROM pg_class WHERE oid=c.oid) AS est_rows
FROM pg_class c
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='ontology' AND c.relkind='r' AND c.relname IN
      ('concepts','descriptions','relationships','refset_members','snomed_map_icd10cm')
ORDER BY 1,2;

-- Concepts/descriptions/relationships (if present)
SELECT 'concepts' AS tbl, COUNT(*) AS n FROM ontology.concepts;
SELECT 'descriptions' AS tbl, COUNT(*) AS n FROM ontology.descriptions;
SELECT 'relationships' AS tbl, COUNT(*) AS n FROM ontology.relationships;

-- Refset members (if present)
SELECT 'refset_members' AS tbl, COUNT(*) AS n
FROM ontology.refset_members;

-- ExtendedMap ICD-10-CM (if present)
SELECT 'snomed_map_icd10cm' AS tbl, COUNT(*) AS n
FROM ontology.snomed_map_icd10cm;

