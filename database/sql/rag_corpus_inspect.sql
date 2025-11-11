-- File: server/sql/rag_corpus_inspect.sql
-- Count by source in the current RAG corpus
SELECT LOWER(source) AS src, COUNT(*) AS n
FROM public.rag_corpus
GROUP BY 1
ORDER BY n DESC;

-- Peek a few rows per source you care about (adjust the IN() list)
SELECT id, source, source_id, title
FROM public.rag_corpus
WHERE LOWER(source) IN ('icd10cm','icd11','icd10pcs','rxnorm','loinc','snomed','guidelines','chv','mimic4_dx')
ORDER BY source
LIMIT 50;

