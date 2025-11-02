\set ON_ERROR_STOP on
WITH present AS (
  SELECT
    EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='ontology' AND table_name='concepts')        AS has_concepts,
    EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='ontology' AND table_name='descriptions')    AS has_descriptions,
    EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='ontology' AND table_name='relationships')   AS has_relationships,
    EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='ontology' AND table_name='refset_members')  AS has_refsets,
    EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='ontology' AND table_name='snomed_map_icd10cm') AS has_map
),
counts AS (
  SELECT
    (SELECT COUNT(*) FROM ontology.concepts)        AS concepts,
    (SELECT COUNT(*) FROM ontology.descriptions)    AS descriptions,
    (SELECT COUNT(*) FROM ontology.relationships)   AS relationships,
    COALESCE((SELECT COUNT(*) FROM ontology.refset_members),0)       AS refset_members,
    COALESCE((SELECT COUNT(*) FROM ontology.snomed_map_icd10cm),0)   AS icd10cm_mappings
),
sizes AS (
  SELECT json_agg(json_build_object(
           'schema', n.nspname, 'table', c.relname,
           'size', pg_size_pretty(pg_total_relation_size(c.oid)),
           'est_rows', (SELECT reltuples::bigint FROM pg_class WHERE oid=c.oid)
         ) ORDER BY n.nspname, c.relname) AS tables
  FROM pg_class c
  JOIN pg_namespace n ON n.oid=c.relnamespace
  WHERE n.nspname='ontology' AND c.relkind='r' AND c.relname IN
        ('concepts','descriptions','relationships','refset_members','snomed_map_icd10cm')
)
SELECT json_build_object(
  'present', (SELECT row_to_json(present) FROM present),
  'counts',  (SELECT row_to_json(counts)  FROM counts),
  'tables',  (SELECT tables FROM sizes)
);

