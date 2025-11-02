WITH has_chunks_tbl AS (
  SELECT to_regclass('public.rag_corpus_chunks') IS NOT NULL AS exists
),
docs AS (
  SELECT * FROM guidelines.docs WHERE source_key = 'nice'
),
sections AS (
  SELECT s.* FROM guidelines.sections s JOIN docs d ON d.id = s.doc_id
),
rag AS (
  SELECT * FROM public.rag_corpus WHERE source = 'nice'
),
chunks AS (
  SELECT * FROM public.rag_corpus_chunks WHERE source = 'nice'
),
by_source AS (
  SELECT d.source_key, COUNT(*)::bigint AS docs
  FROM guidelines.docs d GROUP BY 1 ORDER BY 1
),
top_docs AS (
  SELECT d.doc_key, COALESCE(d.title,'') AS title,
         COALESCE(length(d.text_full),0) AS text_full_len,
         (SELECT COUNT(*) FROM guidelines.sections s WHERE s.doc_id=d.id) AS n_sections
  FROM docs d
  ORDER BY n_sections DESC NULLS LAST, text_full_len DESC
  LIMIT 12
)
SELECT
  jsonb_build_object(
    'has_docs',        (SELECT COUNT(*)>0 FROM docs),
    'has_sections',    (SELECT COUNT(*)>0 FROM sections),
    'has_rag',         (SELECT COUNT(*)>0 FROM rag),
    'has_chunks',      CASE WHEN (SELECT exists FROM has_chunks_tbl)
                            THEN (SELECT COUNT(*)>0 FROM chunks)
                            ELSE false END
  )                         AS presence,
  jsonb_build_object(
    'docs',            (SELECT COUNT(*)         FROM docs),
    'docs_no_text',    (SELECT COUNT(*) FROM docs WHERE text_full IS NULL OR length(text_full)=0),
    'sections',        (SELECT COUNT(*)         FROM sections),
    'rag_rows',        (SELECT COUNT(*)         FROM rag),
    'rag_chunks',      CASE WHEN (SELECT exists FROM has_chunks_tbl)
                            THEN (SELECT COUNT(*) FROM chunks)
                            ELSE 0 END
  )                         AS totals,
  (SELECT jsonb_agg(x) FROM (SELECT source_key, docs FROM by_source) x) AS by_source,
  (SELECT jsonb_agg(x) FROM (SELECT doc_key, title, text_full_len, n_sections FROM top_docs) x) AS top_docs;
