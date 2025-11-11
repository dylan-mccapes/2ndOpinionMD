-- database/sql/rxnorm_aspirin_statins.sql
SELECT source_id AS rxcui, title
FROM public.rag_corpus
WHERE LOWER(source)='rxnorm'
  AND (
      LOWER(title) LIKE 'aspirin%'
   OR LOWER(title) LIKE 'heparin%'
   OR LOWER(title) LIKE 'atorvastatin%'
   OR LOWER(title) LIKE 'rosuvastatin%'
  )
ORDER BY 1
LIMIT 50;

