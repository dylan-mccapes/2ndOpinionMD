-- ============================================================
-- ICD-10-CM (ontology.icd10cm) -> rag_corpus
-- ============================================================
WITH src AS (
  SELECT
    'icd10cm'::text AS source,
    t.code          AS source_id,
    COALESCE(t.title_long, t.title_short, t.code) AS title,
    COALESCE(t.title_long, t.title_short, t.code) AS text,
    jsonb_build_object(
      'code',           t.code,
      'chapter',        t.chapter,
      'block',          t.block,
      'effective_year', t.effective_year,
      'source_file',    t.source_file
    ) AS meta
  FROM ontology.icd10cm t
)
INSERT INTO rag_corpus (
  source,
  source_id,
  title,
  text,
  meta,
  ts
)
SELECT
  source,
  source_id,
  title,
  text,
  meta,
  to_tsvector('english', text) AS ts
FROM src
ON CONFLICT (source, source_id) DO UPDATE
SET
  title = EXCLUDED.title,
  text  = EXCLUDED.text,
  meta  = rag_corpus.meta || EXCLUDED.meta,
  ts    = EXCLUDED.ts;
