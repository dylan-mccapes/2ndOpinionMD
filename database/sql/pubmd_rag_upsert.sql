-- database/sql/pubmd_rag_upsert.sql

-- Ensure JSONB meta exists
ALTER TABLE rag_corpus
  ADD COLUMN IF NOT EXISTS meta JSONB DEFAULT '{}'::jsonb;

-- Helpful indexes
CREATE INDEX IF NOT EXISTS rag_corpus_meta_gin ON rag_corpus USING gin (meta);
CREATE INDEX IF NOT EXISTS idx_rag_pubmd_meta_pmid
  ON rag_corpus ((meta->>'pmid')) WHERE source='pubmd';

WITH src AS (
  SELECT
    s.pmid,
    NULLIF(s.title,'')     AS title,
    COALESCE(s.abstract,'') AS abstract,
    s.year
  FROM staging.pubmd_docs s
),

upd AS (
  UPDATE rag_corpus t
  SET
    title = src.title,
    text  = TRIM(BOTH FROM COALESCE(src.title,'') || E'\n\n' || src.abstract),
    ts    = to_tsvector('simple_unaccent', COALESCE(src.title,'') || ' ' || src.abstract),
    meta  = jsonb_strip_nulls(
              (t.meta || jsonb_build_object(
                 'pmid', src.pmid,
                 'url',  'https://pubmed.ncbi.nlm.nih.gov/' || src.pmid || '/',
                 'year', src.year,
                 'source_table','staging.pubmd_docs'
              ))::jsonb
            )
  FROM src
  WHERE t.source='pubmd'
    AND t.meta->>'pmid' = src.pmid
  RETURNING t.id
)

INSERT INTO rag_corpus (source, title, text, ts, meta)
SELECT
  'pubmd',
  s.title,
  TRIM(BOTH FROM COALESCE(s.title,'') || E'\n\n' || s.abstract),
  to_tsvector('simple_unaccent', COALESCE(s.title,'') || ' ' || s.abstract),
  jsonb_strip_nulls(jsonb_build_object(
    'pmid', s.pmid,
    'url',  'https://pubmed.ncbi.nlm.nih.gov/' || s.pmid || '/',
    'year', s.year,
    'source_table','staging.pubmd_docs'
  ))
FROM src s
LEFT JOIN rag_corpus t
  ON t.source='pubmd' AND t.meta->>'pmid' = s.pmid
WHERE t.id IS NULL;
