WITH map AS (
  SELECT
    COUNT(*)                           AS rows_all,
    COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL) AS rows_with_target,
    COUNT(DISTINCT NULLIF(trim(map_target),'')) AS distinct_icd10cm_codes,
    -- Validity buckets from your earlier logic
    COUNT(*) FILTER (
      WHERE position('X' IN map_target) = 0
        AND position('?' IN map_target) = 0
        AND trim(map_target) <> ''
    ) AS valid_plain,
    COUNT(*) FILTER (
      WHERE (position('X' IN map_target) > 0 OR position('?' IN map_target) > 0)
        AND trim(map_target) <> ''
    ) AS valid_with_placeholders,
    COUNT(*) FILTER (WHERE trim(map_target) = '') AS truly_invalid
  FROM ontology.snomed_map_icd10cm
)
SELECT json_build_object(
  'map_rows_all', m.rows_all,
  'map_rows_with_target', m.rows_with_target,
  'map_distinct_icd10cm_codes', m.distinct_icd10cm_codes,
  'map_valid_plain', m.valid_plain,
  'map_valid_with_placeholders', m.valid_with_placeholders,
  'map_truly_invalid', m.truly_invalid
) AS json
FROM map m;
