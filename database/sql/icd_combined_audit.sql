SET search_path = public, ontology;
\pset tuples_only on

WITH rag_icd AS (
  SELECT source, source_id, meta, embedding
  FROM public.rag_corpus
  WHERE source = 'icd10cm'
),
codes_from_table(n) AS (
  SELECT COUNT(*) FROM ontology.icd10cm
),
codes_fallback(n) AS (
  SELECT COUNT(DISTINCT COALESCE(source_id, meta->>'code')) FROM rag_icd
),
icd10cm_codes(n) AS (
  SELECT CASE
           WHEN (SELECT n FROM codes_from_table) > 0
             THEN (SELECT n FROM codes_from_table)
           ELSE (SELECT n FROM codes_fallback)
         END
),
targets(n) AS (
  -- Targets == distinct codes for this audit
  SELECT (SELECT n FROM icd10cm_codes)
),
rag AS (
  SELECT
    COUNT(*)                                          AS rag_rows,
    COUNT(*) FILTER (WHERE embedding IS NULL)         AS rag_missing,
    COUNT(*) FILTER (WHERE embedding IS NOT NULL)     AS rag_embedded
  FROM rag_icd
)
SELECT json_build_object(
  'icd10cm_codes', (SELECT n FROM icd10cm_codes),
  'icd10cm_targets', (SELECT n FROM targets),
  'rag_rows', (SELECT rag_rows FROM rag),
  'rag_missing', (SELECT rag_missing FROM rag),
  'rag_embedded', (SELECT rag_embedded FROM rag)
)::text;
