BEGIN;

DROP VIEW IF EXISTS public.icd10cm_targets;

CREATE VIEW public.icd10cm_targets AS
WITH have_icd AS (
  SELECT COUNT(*)::int AS c FROM ontology.icd10cm
),
codes AS (
  -- Preferred: full ICD-10-CM table
  SELECT
    code::text AS code,
    COALESCE(NULLIF(title_long,''), NULLIF(title_short,''), code) AS title
  FROM ontology.icd10cm
  WHERE (SELECT c FROM have_icd) > 0

  UNION ALL

  -- Fallback: distinct codes from the SNOMED->ICD10CM map when base table is absent
  SELECT
    DISTINCT NULLIF(trim(map_target),'') AS code,
    NULLIF(trim(map_target),'') AS title
  FROM ontology.snomed_map_icd10cm
  WHERE (SELECT c FROM have_icd) = 0
    AND NULLIF(trim(map_target),'') IS NOT NULL
)
SELECT
  code,
  title,
  NULL::text AS description
FROM codes;

COMMIT;
