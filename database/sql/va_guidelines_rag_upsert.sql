-- Insert all VA sections into rag_corpus (idempotent after prior delete)
INSERT INTO public.rag_corpus (source, title, text, ts)
SELECT
  'va_guidelines' AS source,
  COALESCE(s.heading, d.title) AS title,
  s.text_plain AS text,
  to_tsvector('english', s.text_plain) AS ts
FROM guidelines.va_sections s
JOIN guidelines.va_docs d ON d.slug = s.doc_slug;

