-- database/sql/snomed_nstemi.sql
SELECT source_id AS concept_id, title
FROM public.rag_corpus
WHERE LOWER(source)='snomed'
  AND LOWER(title) LIKE '%non-st elevation myocardial infarction%'
LIMIT 25;

