
WITH counts AS (
  SELECT
    (SELECT COUNT(*) FROM ontology.icd11 WHERE linearization='mms') AS icd11_rows,
    (SELECT COUNT(*) FROM public.rag_corpus WHERE source='icd11') AS rag_rows,
    (SELECT COUNT(*) FROM public.rag_corpus WHERE source='icd11' AND ts IS NULL) AS rag_missing_ts,
    (SELECT COUNT(*) FROM public.rag_corpus WHERE source='icd11' AND embedding IS NULL) AS rag_missing_emb
)
SELECT jsonb_build_object(
  'icd11_rows', icd11_rows,
  'rag_rows', rag_rows,
  'rag_missing_ts', rag_missing_ts,
  'rag_missing_emb', rag_missing_emb
) AS integrity;
