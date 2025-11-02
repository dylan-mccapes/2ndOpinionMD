\echo '-- ICD presence flags'
SELECT
  (to_regclass('ontology.icd10cm') IS NOT NULL)  AS has_icd10cm,
  (to_regclass('ontology.icd11')  IS NOT NULL)   AS has_icd11,
  (to_regclass('ontology.snomed_map_icd10cm') IS NOT NULL) AS has_snomed_map;

\echo '-- Table sizes (estimated rows via pg_class)'
SELECT n.nspname AS schema,
       c.relname AS table_name,
       pg_size_pretty(pg_total_relation_size(c.oid)) AS size,
       COALESCE(NULLIF(c.reltuples,0),0)::bigint AS est_rows
FROM pg_class c
JOIN pg_namespace n ON n.oid=c.relnamespace
WHERE n.nspname='ontology'
  AND c.relname IN ('icd10cm','icd11','snomed_map_icd10cm')
ORDER BY c.relname;

\echo '-- SNOMED ExtendedMap coverage (ICD-10-CM targets)'
-- Safe even if ICD tables are missing
WITH m AS (
  SELECT *
  FROM ontology.snomed_map_icd10cm
),
mt AS (
  SELECT COUNT(*) AS rows_all,
         COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL) AS rows_with_target,
         COUNT(DISTINCT NULLIF(trim(map_target),'')) AS distinct_icd10cm_codes
  FROM m
)
SELECT * FROM mt;

\echo '-- Top 10 ICD-10-CM targets by number of SNOMED concepts (from ExtendedMap)'
SELECT NULLIF(trim(map_target),'') AS icd10cm_code,
       COUNT(*) AS snomed_mappings
FROM ontology.snomed_map_icd10cm
WHERE NULLIF(trim(map_target),'') IS NOT NULL
GROUP BY 1
ORDER BY snomed_mappings DESC, icd10cm_code
LIMIT 10;

\echo '-- If ontology.icd10cm exists: coverage of icd10cm codes that appear in ExtendedMap'
DO $$
DECLARE ok boolean;
BEGIN
  ok := to_regclass('ontology.icd10cm') IS NOT NULL;
  IF ok THEN
    -- total icd10 rows
    PERFORM 1;
    RAISE NOTICE 'icd10cm_total=%', (SELECT COUNT(*) FROM ontology.icd10cm);
    -- how many icd10 codes are mapped by ExtendedMap
    RAISE NOTICE 'icd10cm_mapped_codes=%',
      (SELECT COUNT(*) FROM ontology.icd10cm i
         WHERE EXISTS (
           SELECT 1 FROM ontology.snomed_map_icd10cm m
           WHERE NULLIF(trim(m.map_target),'') = i.code));
    -- sample of icd10 codes without a map target
    RAISE NOTICE 'icd10cm_unmapped_sample: %',
      (SELECT string_agg(code, ', ')
         FROM (
           SELECT i.code
           FROM ontology.icd10cm i
           WHERE NOT EXISTS (
             SELECT 1 FROM ontology.snomed_map_icd10cm m
             WHERE NULLIF(trim(m.map_target),'') = i.code)
           ORDER BY i.code
           LIMIT 10
         ) s);
  ELSE
    RAISE NOTICE 'icd10cm table not present; skipping join coverage.';
  END IF;
END$$;

\echo '-- If ontology.icd11 exists: orphan parent checks'
DO $$
DECLARE ok boolean;
BEGIN
  ok := to_regclass('ontology.icd11') IS NOT NULL;
  IF ok THEN
    RAISE NOTICE 'icd11_total=%', (SELECT COUNT(*) FROM ontology.icd11);
    RAISE NOTICE 'icd11_missing_parents=%',
      (SELECT COUNT(*) FROM ontology.icd11 c
         LEFT JOIN ontology.icd11 p ON p.code=c.parent_code
       WHERE c.parent_code IS NOT NULL AND p.code IS NULL);
  ELSE
    RAISE NOTICE 'icd11 table not present; skipping parent checks.';
  END IF;
END$$;

