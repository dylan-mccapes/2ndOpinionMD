-- 1) Normalized library tables
CREATE SCHEMA IF NOT EXISTS library;

CREATE TABLE IF NOT EXISTS library.pubmd_article (
  pmid         BIGINT PRIMARY KEY,
  pmcid        TEXT,
  doi          TEXT,
  title        TEXT,
  abstract     TEXT,
  journal      TEXT,
  iso_journal  TEXT,
  pub_year     INT,
  pub_date     DATE,
  article_types TEXT[],
  languages     TEXT[],
  license       TEXT,
  url           TEXT,
  has_fulltext  BOOLEAN DEFAULT FALSE,
  mesh_terms    TEXT[],         -- denormalized convenience
  authors       TEXT[],         -- same; optional split table below
  affiliations  TEXT[],
  meta          JSONB DEFAULT '{}'::jsonb
);

-- Optional splits (only if you want full 3NF)
CREATE TABLE IF NOT EXISTS library.pubmd_author (
  pmid BIGINT REFERENCES library.pubmd_article(pmid) ON DELETE CASCADE,
  pos  INT,
  name TEXT,
  affiliation TEXT,
  PRIMARY KEY (pmid, pos)
);

CREATE TABLE IF NOT EXISTS library.pubmd_fulltext (
  pmcid TEXT PRIMARY KEY,
  pmid  BIGINT REFERENCES library.pubmd_article(pmid) ON DELETE CASCADE,
  body_plain  TEXT,           -- concatenated or raw section-less
  sections    JSONB           -- [{title, text, order}]
);

-- 2) RAG materialization (your existing table)
-- One row per chunk; ‘source=pubmd’
-- meta example: {"pmid":..., "pmcid":..., "doi":..., "year":2024, "journal":"Nature", "mesh":["Autoimmune"], "section":"Results"}
-- Make sure updated_at trigger already present (you added it)
CREATE INDEX IF NOT EXISTS rag_pubmd_source_idx ON rag_corpus(source) WHERE source='pubmd';
CREATE INDEX IF NOT EXISTS rag_pubmd_pubdate_idx ON rag_corpus((meta->>'pub_date'));
CREATE INDEX IF NOT EXISTS rag_pubmd_mesh_gin ON rag_corpus USING gin ((meta->'mesh'));

-- 3) ANN (HNSW) just for pubmd rows
CREATE INDEX CONCURRENTLY IF NOT EXISTS rag_pubmd_embedding_hnsw
ON rag_corpus USING hnsw (embedding vector_cosine_ops)
WITH (m=16, ef_construction=128)
WHERE source='pubmd' AND embedding IS NOT NULL;

