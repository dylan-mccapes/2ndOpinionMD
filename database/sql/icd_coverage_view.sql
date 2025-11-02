-- Coverage of normalized map targets vs ontology.icd10cm

CREATE OR REPLACE VIEW ontology.v_map_icd10cm_coverage AS
WITH m AS (
  SELECT
    map_target_norm AS icd10cm_code,
    COUNT(*) AS snomed_mappings,
    (map_target_norm ~ '^[A-TV-Z][0-9][0-9A-Z](\.[0-9A-Z]{1,4})?$') AS is_valid_format
  FROM ontology.snomed_map_icd10cm
  WHERE map_target_norm IS NOT NULL
  GROUP BY 1
)
SELECT
  m.icd10cm_code,
  m.is_valid_format,
  m.snomed_mappings,
  (i.code IS NOT NULL) AS exists_in_icd10cm,
  i.title AS icd10cm_title
FROM m
LEFT JOIN ontology.icd10cm i
  ON i.code = m.icd10cm_code;

