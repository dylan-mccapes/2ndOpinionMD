-- Normalize SNOMED → ICD-10-CM map targets into map_target_norm
-- - trim & uppercase
-- - drop trailing '?' or '-' placeholders
-- - KEEP 'X' (valid ICD-10-CM wildcard character)

BEGIN;

-- Ensure column
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema='ontology'
      AND table_name='snomed_map_icd10cm'
      AND column_name='map_target_norm'
  ) THEN
    EXECUTE 'ALTER TABLE ontology.snomed_map_icd10cm ADD COLUMN map_target_norm text';
  END IF;
END$$;

-- Normalize
UPDATE ontology.snomed_map_icd10cm
SET map_target_norm = NULLIF(
      regexp_replace(upper(trim(map_target)), '[\?\-]+$',''),
      ''
    )
WHERE map_target IS NOT NULL;

-- Index
CREATE INDEX IF NOT EXISTS snomed_map_icd10cm_target_norm_idx
  ON ontology.snomed_map_icd10cm (map_target_norm);

COMMIT;

