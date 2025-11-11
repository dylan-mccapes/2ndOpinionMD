-- database/sql/loinc_hs_troponin.sql
SELECT source_id AS loinc, title
FROM public.rag_corpus
WHERE LOWER(source)='loinc'
  AND LOWER(title) LIKE '%troponin%'
  AND (LOWER(title) LIKE '%high%' OR LOWER(title) LIKE '%hs%')
ORDER BY 1
LIMIT 25;

