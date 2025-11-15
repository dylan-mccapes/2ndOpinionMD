-- Ensure staging schema
CREATE SCHEMA IF NOT EXISTS staging;

-- Minimal staging table for PubMed docs
-- Add/extend columns as you like — these are the ones we’ll map into rag_corpus.
CREATE TABLE IF NOT EXISTS staging.pubmd_docs (
  pmid           TEXT PRIMARY KEY,
  doi            TEXT,
  title          TEXT,
  abstract       TEXT,
  url            TEXT,
  journal        TEXT,
  year           INT,
  authors        TEXT[],
  mesh_terms     TEXT[],
  published_at   TIMESTAMPTZ,
  meta           JSONB DEFAULT '{}'::jsonb
);

-- Optional: index for quick refreshes
CREATE INDEX IF NOT EXISTS idx_pubmd_year ON staging.pubmd_docs (year);

