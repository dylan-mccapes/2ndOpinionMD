-- setup_chv_synonyms.sql
CREATE SCHEMA IF NOT EXISTS ontology;

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE TABLE IF NOT EXISTS ontology.synonyms (
  term       TEXT NOT NULL,
  cui        TEXT NOT NULL,
  source     TEXT DEFAULT 'CHV',
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- case-insensitive de-dupe on (term, cui)
CREATE UNIQUE INDEX IF NOT EXISTS synonyms_unique_idx
  ON ontology.synonyms (lower(term), cui);

-- search helpers
CREATE INDEX IF NOT EXISTS synonyms_term_trgm
  ON ontology.synonyms USING gin (term gin_trgm_ops);

CREATE INDEX IF NOT EXISTS synonyms_cui_idx
  ON ontology.synonyms (cui);

