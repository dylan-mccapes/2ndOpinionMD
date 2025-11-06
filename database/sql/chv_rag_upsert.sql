-- database/sql/chv_rag_upsert.sql
BEGIN;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

WITH src AS (
  SELECT
    'chv'::text                                AS source,
    (b.cui || '::' || b.term_lower)            AS source_id,
    b.term                                     AS title,
    -- Write into "text" (NOT NULL), not "content"
    (b.term || ' (UMLS ' || b.cui || ')')      AS text,
    jsonb_build_object(
      'cui', b.cui,
      'term', b.term,
      'term_lower', b.term_lower,
      'type', 'lay_term',
      'source', 'CHV',
      'method', b.method
    )                                           AS meta,
    to_tsvector('english', b.term || ' ' || b.cui) AS ts
  FROM ontology.chv_best b
),
upd AS (
  UPDATE public.rag_corpus r
  SET  title = s.title,
       text  = s.text,
       meta  = s.meta,
       ts    = s.ts
  FROM src s
  WHERE r.source='chv' AND r.source_id=s.source_id
  RETURNING r.source_id
)
INSERT INTO public.rag_corpus (source, source_id, title, text, meta, ts)
SELECT s.source, s.source_id, s.title, s.text, s.meta, s.ts
FROM src s
LEFT JOIN upd u ON u.source_id=s.source_id
LEFT JOIN public.rag_corpus r
       ON r.source='chv' AND r.source_id=s.source_id
WHERE u.source_id IS NULL AND r.source_id IS NULL;

COMMIT;
