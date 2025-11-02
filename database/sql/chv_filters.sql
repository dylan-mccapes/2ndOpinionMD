-- chv_filters.sql (replace the incorrect_map part)
CREATE SCHEMA IF NOT EXISTS ontology;

-- STOP CUIs
CREATE TABLE IF NOT EXISTS ontology.chv_stop_cui (
  cui TEXT PRIMARY KEY
);

-- INCORRECT MAPPINGS  ← ensure both columns exist
DROP TABLE IF EXISTS ontology.chv_incorrect_map;
CREATE TABLE ontology.chv_incorrect_map (
  cui  TEXT NOT NULL,
  term TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  PRIMARY KEY (cui, term)
);
CREATE INDEX IF NOT EXISTS chv_incorrect_cui_idx ON ontology.chv_incorrect_map(cui);
