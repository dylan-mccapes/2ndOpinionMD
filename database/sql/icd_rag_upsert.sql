-- Idempotent upsert for icd10cm that never touches existing embeddings.

BEGIN;

-- Normalize rag_corpus to a known shape (no-op if columns already exist)
ALTER TABLE public.rag_corpus
  ADD COLUMN IF NOT EXISTS source_id text,
  ADD COLUMN IF NOT EXISTS content  text,
  ADD COLUMN IF NOT EXISTS ts       tsvector;

-- Backfill source_id for icd10cm from meta if missing
UPDATE public.rag_corpus
SET source_id = COALESCE(source_id, meta->>'code')
WHERE source='icd10cm' AND source_id IS NULL;

-- 1) UPDATE existing icd10cm rows from the normalized targets view
WITH src AS (
  SELECT
    'icd10cm'::text AS source,
    t.code          AS source_id,
    t.title         AS title,
    t.title         AS content
  FROM public.icd10cm_targets t
)
UPDATE public.rag_corpus r
SET title   = s.title,
    content = s.content,
    ts      = to_tsvector('english', COALESCE(s.title,'') || ' ' || COALESCE(s.content,''))
FROM src s
WHERE r.source = s.source
  AND r.source_id = s.source_id;

-- 2) INSERT rows that don't exist yet
WITH src AS (
  SELECT
    'icd10cm'::text AS source,
    t.code          AS source_id,
    t.title         AS title,
    t.title         AS content
  FROM public.icd10cm_targets t
)
INSERT INTO public.rag_corpus (source, source_id, title, content, ts)
SELECT
  s.source, s.source_id, s.title, s.content,
  to_tsvector('english', COALESCE(s.title,'') || ' ' || COALESCE(s.content,''))
FROM src s
WHERE NOT EXISTS (
  SELECT 1
  FROM public.rag_corpus r
  WHERE r.source = s.source
    AND r.source_id = s.source_id
);

-- Safety: ensure ts exists for all icd10cm
UPDATE public.rag_corpus
SET ts = to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(content,''))
WHERE source='icd10cm' AND ts IS NULL;

COMMIT;
