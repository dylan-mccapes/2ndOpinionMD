-- setup_guidelines_schema.sql
-- Creates guidelines.* tables and ensures rag_corpus has provenance columns + indexes.
-- Idempotent; safe to re-run.

-- 1) Ensure base schema(s)
CREATE SCHEMA IF NOT EXISTS guidelines;

-- 2) Try to enable pgvector (optional, non-fatal if unavailable)
DO $$
BEGIN
    CREATE EXTENSION IF NOT EXISTS vector;
EXCEPTION WHEN OTHERS THEN
    RAISE NOTICE 'pgvector extension not available, continuing without vector support';
END
$$;

-- 3) guidelines.sources
CREATE TABLE IF NOT EXISTS guidelines.sources (
    id          SERIAL PRIMARY KEY,
    key         TEXT UNIQUE NOT NULL,    -- 'nice', 'cks', 'who_eml', 'cdc_opioid', 'va_dod'
    name        TEXT NOT NULL,
    homepage    TEXT,
    license     TEXT,
    created_at  TIMESTAMP DEFAULT NOW()
);

-- 4) guidelines.docs (one row per PDF/HTML snapshot)
CREATE TABLE IF NOT EXISTS guidelines.docs (
    id            BIGSERIAL PRIMARY KEY,
    source_key    TEXT REFERENCES guidelines.sources(key) ON UPDATE CASCADE,
    doc_key       TEXT NOT NULL,     -- e.g., 'NG220', 'NG65', 'NG193', or page slug
    version       TEXT,
    title         TEXT,
    url           TEXT,
    published_at  DATE,
    fetched_at    TIMESTAMP DEFAULT NOW(),
    sha256        TEXT,
    mime_type     TEXT,
    bytes         BYTEA,             -- optional: store file inline for smaller PDFs
    storage_path  TEXT,              -- alternative to bytes (filesystem path)
    text_full     TEXT,              -- full extracted text
    meta          JSONB DEFAULT '{}'::jsonb,
    UNIQUE (source_key, doc_key, version)
);

-- 5) guidelines.sections (structured chunking for RAG)
CREATE TABLE IF NOT EXISTS guidelines.sections (
    id        BIGSERIAL PRIMARY KEY,
    doc_id    BIGINT REFERENCES guidelines.docs(id) ON DELETE CASCADE,
    ord       INTEGER,         -- section order in document
    heading   TEXT,
    anchor    TEXT,
    text      TEXT,
    meta      JSONB DEFAULT '{}'::jsonb
);

-- 6) (Optional) Normalized citations
CREATE TABLE IF NOT EXISTS guidelines.citations (
    id        BIGSERIAL PRIMARY KEY,
    doc_id    BIGINT REFERENCES guidelines.docs(id) ON DELETE CASCADE,
    sect_id   BIGINT REFERENCES guidelines.sections(id) ON DELETE CASCADE,
    ref_label TEXT,
    ref_text  TEXT,
    meta      JSONB DEFAULT '{}'::jsonb
);

-- 7) Ensure public.rag_corpus has provenance columns + ts + indexes
--    (We do not alter existing vector dims/indices; just add missing columns/indexes.)
DO $$
BEGIN
    PERFORM 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'rag_corpus' AND column_name = 'meta';
    IF NOT FOUND THEN
        EXECUTE 'ALTER TABLE public.rag_corpus ADD COLUMN meta JSONB DEFAULT ''{}''::jsonb';
    END IF;

    PERFORM 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'rag_corpus' AND column_name = 'doc_id';
    IF NOT FOUND THEN
        EXECUTE 'ALTER TABLE public.rag_corpus ADD COLUMN doc_id BIGINT';
    END IF;

    PERFORM 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'rag_corpus' AND column_name = 'sect_id';
    IF NOT FOUND THEN
        EXECUTE 'ALTER TABLE public.rag_corpus ADD COLUMN sect_id BIGINT';
    END IF;

    PERFORM 1
    FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'rag_corpus' AND column_name = 'ts';
    IF NOT FOUND THEN
        EXECUTE 'ALTER TABLE public.rag_corpus ADD COLUMN ts TSVECTOR';
    END IF;
END
$$;

-- 8) Helpful indexes for RAG + provenance lookups
CREATE INDEX IF NOT EXISTS rag_meta_gin  ON public.rag_corpus USING GIN (meta);
CREATE INDEX IF NOT EXISTS rag_doc_idx   ON public.rag_corpus (doc_id);
CREATE INDEX IF NOT EXISTS rag_sect_idx  ON public.rag_corpus (sect_id);
CREATE INDEX IF NOT EXISTS rag_ts_idx    ON public.rag_corpus USING GIN (ts);

-- 9) Vector ANN index hint (only if embedding column exists & pgvector present).
--    Adjust lists as needed in runtime (probes via SET ivfflat.probes = N).
DO $$
BEGIN
    -- Check for embedding column existence
    PERFORM 1
    FROM information_schema.columns
    WHERE table_schema='public' AND table_name='rag_corpus' AND column_name='embedding';
    IF FOUND THEN
        BEGIN
            -- Attempt to create ivfflat index; ignore if extension missing
            EXECUTE 'CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann
                     ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists = 800)';
        EXCEPTION WHEN OTHERS THEN
            RAISE NOTICE 'Vector index not created (pgvector or operator class not available)';
        END;
    END IF;
END
$$;

-- 10) Minimal privileges (align with your pattern)
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA guidelines TO postgres;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA guidelines TO postgres;

-- 11) Convenience: initialize known sources (idempotent)
INSERT INTO guidelines.sources (key, name, homepage)
VALUES
  ('nice',      'NICE Guidance', 'https://www.nice.org.uk/guidance'),
  ('cks',       'NICE Clinical Knowledge Summaries', 'https://cks.nice.org.uk/'),
  ('who_eml',   'WHO Model List of Essential Medicines', 'https://list.essentialmeds.org/'),
  ('cdc_opioid','CDC Opioid Prescribing Guidance', 'https://www.cdc.gov/overdose-prevention/hcp/clinical-guidance/'),
  ('va_dod',    'VA/DoD Clinical Practice Guidelines', 'https://www.healthquality.va.gov/')
ON CONFLICT (key) DO NOTHING;

-- 12) (Optional) one-time FTS refresh for existing rows lacking ts
--     Keep lightweight; you can run a targeted refresh after loading guidelines.
UPDATE public.rag_corpus
SET ts = to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(text,''))
WHERE ts IS NULL;

