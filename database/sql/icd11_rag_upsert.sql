

WITH src AS (
  SELECT
    'icd11'::text                AS source,
    i.code                       AS source_id,
    COALESCE(i.title, i.code)    AS title,
    (COALESCE(i.title,'') || E'\n\n' || COALESCE(i.definition,''))::text AS content,
    jsonb_build_object(
      'release', i.release,
      'linearization', i.linearization,
      'parent_code', i.parent_code
    )::jsonb AS meta
  FROM ontology.icd11 i
  WHERE i.linearization = 'mms'
    AND COALESCE(i.title,'') <> ''
)
INSERT INTO public.rag_corpus (source, source_id, title, content, meta, ts)
SELECT s.source, s.source_id, s.title, s.content, s.meta,
       to_tsvector('english', s.content)
FROM src s
ON CONFLICT (source, source_id) DO UPDATE
SET title   = EXCLUDED.title,
    content = EXCLUDED.content,
    meta    = EXCLUDED.meta,
    ts      = EXCLUDED.ts
WHERE public.rag_corpus.title IS DISTINCT FROM EXCLUDED.title
   OR public.rag_corpus.content IS DISTINCT FROM EXCLUDED.content
   OR public.rag_corpus.meta IS DISTINCT FROM EXCLUDED.meta
   OR public.rag_corpus.ts IS DISTINCT FROM EXCLUDED.ts;
