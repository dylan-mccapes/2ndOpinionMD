-- database/sql/cdc_opioid_rag_upsert.sql
INSERT INTO public.rag_corpus (source, title, text, ts)
SELECT
  'cdc_opioid',
  d.title || COALESCE(' — ' || s.heading, ''),
  s.text_plain,
  to_tsvector('english', s.text_plain)
FROM guidelines.cdc_sections s
JOIN guidelines.cdc_docs d ON d.doc_id = s.doc_id
WHERE s.text_plain IS NOT NULL AND btrim(s.text_plain) <> ''
ON CONFLICT DO NOTHING;
