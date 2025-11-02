-- CHV n-grams: term-only list
CREATE SCHEMA IF NOT EXISTS ontology;

CREATE TABLE IF NOT EXISTS ontology.chv_ngrams (
  term TEXT PRIMARY KEY
);

-- fuzzy lookup helper
CREATE INDEX IF NOT EXISTS chv_ngrams_term_trgm
  ON ontology.chv_ngrams USING gin (term gin_trgm_ops);
