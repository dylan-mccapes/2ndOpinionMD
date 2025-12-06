CREATE SCHEMA IF NOT EXISTS ontology;

CREATE TABLE IF NOT EXISTS ontology.hpo_synonyms (
  hpo_id   text NOT NULL,
  synonym  text NOT NULL,
  scope    text,
  lang     text,
  xrefs    text[] DEFAULT NULL,
  source   text NOT NULL DEFAULT 'hpo',
  PRIMARY KEY (hpo_id, synonym)
);

CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS hpo_synonyms_trgm ON ontology.hpo_synonyms USING gin (synonym gin_trgm_ops);
CREATE INDEX IF NOT EXISTS hpo_synonyms_id   ON ontology.hpo_synonyms(hpo_id);
