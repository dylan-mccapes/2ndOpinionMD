CREATE SCHEMA IF NOT EXISTS staging;

DROP TABLE IF EXISTS staging.pubmd_docs;
CREATE UNLOGGED TABLE staging.pubmd_docs (
  pmid     BIGINT PRIMARY KEY,
  title    TEXT,
  abstract TEXT,
  year     INT,
  journal  TEXT,
  mesh     TEXT,
  text     TEXT
);

-- Helpful for load perf
ALTER TABLE staging.pubmd_docs SET (autovacuum_enabled = false);

