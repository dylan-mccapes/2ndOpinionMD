-- database/sql/17_neurolex_core.sql
-- Define a "core" slice of NeuroLex terms (exclude CDE/forms + UI schema bits).
-- Idempotent: safe to re-run.

CREATE SCHEMA IF NOT EXISTS ontology;

-- Core subset (disease-ish terms)
CREATE OR REPLACE VIEW ontology.neurolex_core AS
SELECT n.*
FROM ontology.neurolex n
WHERE NOT (
  n.ilx_id LIKE 'cde\_%' ESCAPE '\'
  OR EXISTS (
    SELECT 1
    FROM ontology.neurolex_annotations a
    WHERE a.ilx_id = n.ilx_id
      AND a.prop_label IN ('required','allowedTypes','condition','size','allowedValues')
  )
);

-- API-facing convenience view (stable columns)
CREATE OR REPLACE VIEW ontology.neurolex_terms AS
SELECT
  n.ilx_id,
  n.label AS preferred_label,
  n.definition,
  n.synonyms,
  NULL::text      AS category,
  n.xrefs,
  n.parents,
  '{}'::text[]    AS children
FROM ontology.neurolex_core n;

