CREATE SCHEMA IF NOT EXISTS ontology;

DROP TABLE IF EXISTS ontology.chv_ngrams;
CREATE TABLE ontology.chv_ngrams (
  term        TEXT PRIMARY KEY,
  meta        BOOLEAN DEFAULT false,
  mod         BOOLEAN DEFAULT false,
  disparaged  BOOLEAN DEFAULT false,
  misspelled  BOOLEAN DEFAULT false,
  comment     TEXT
);

CREATE INDEX IF NOT EXISTS chv_ngrams_term_trgm
  ON ontology.chv_ngrams USING gin (term gin_trgm_ops);
