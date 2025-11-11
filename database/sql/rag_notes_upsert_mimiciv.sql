-- database/sql/rag_notes_upsert_mimiciv.sql
-- Upsert MIMIC-IV notes into public.rag_corpus with de-dup safe insert.
-- Fixes "ON CONFLICT DO UPDATE ... affect row a second time" by DISTINCT ON(note_id).

CREATE EXTENSION IF NOT EXISTS vector;
ALTER TABLE public.rag_corpus
  ADD COLUMN IF NOT EXISTS embedding vector(1536);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='public' AND indexname='rag_corpus_uq_source_source_id'
  ) THEN
    CREATE UNIQUE INDEX rag_corpus_uq_source_source_id
      ON public.rag_corpus(source, source_id);
  END IF;
END$$;

WITH base AS (
  SELECT DISTINCT ON (n.note_id)
      n.note_id,
      COALESCE(n.hadm_id::bigint, m.hadm_id::bigint)               AS hadm_id,
      n.subject_id::bigint                                         AS subject_id,
      n.charttime,
      n.domain,
      n.note_text
  FROM text.mimiciv_notes n
  LEFT JOIN text.mimiciv_notes_hadm_map m USING (note_id)
  WHERE n.note_text IS NOT NULL AND length(n.note_text) > 100
  -- prefer rows with a native hadm_id; else earliest mapper row
  ORDER BY n.note_id, (n.hadm_id IS NULL), m.dt_seconds NULLS LAST
),
prepared AS (
  SELECT
      'mimic4_note'                                                AS source,
      'mimic4_note::' || note_id                                   AS source_id,
      COALESCE(domain,'note')                                      AS title,
      note_text                                                    AS text,
      jsonb_strip_nulls(jsonb_build_object(
        'hadm_id', hadm_id, 'subject_id', subject_id,
        'charttime', charttime, 'domain', domain
      ))                                                           AS meta
  FROM base
)
INSERT INTO public.rag_corpus (source, source_id, title, text, meta)
SELECT p.source, p.source_id, p.title, p.text, p.meta
FROM prepared p
ON CONFLICT (source, source_id)
DO UPDATE SET title = EXCLUDED.title, text = EXCLUDED.text, meta = EXCLUDED.meta;

-- quick sanity
SELECT source, COUNT(*) AS n FROM public.rag_corpus WHERE source='mimic4_note' GROUP BY 1;

