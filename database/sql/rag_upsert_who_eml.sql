-- server/scripts/rag_upsert_who_eml.sql

-- 1) Remove previous WHO EML rows from RAG
DELETE FROM public.rag_corpus
WHERE source = 'who_eml';

-- 2) Re-insert one row per medicine from guidelines.who_eml_medicines
--    (we only depend on columns that are known to exist: inn, notes)
INSERT INTO public.rag_corpus (source, title, text, meta)
SELECT
  'who_eml' AS source,
  m.inn     AS title,
  concat_ws(
    E'\n',
    m.inn,
    coalesce(m.notes, '')
  ) AS text,
  jsonb_build_object(
    'source', 'who_eml',
    'inn',    m.inn
  ) AS meta
FROM guidelines.who_eml_medicines AS m;
