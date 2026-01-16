-- NeuroLex tables (InterLex subset)
CREATE SCHEMA IF NOT EXISTS ontology;

CREATE TABLE IF NOT EXISTS ontology.neurolex (
  ilx_id      text PRIMARY KEY,
  iri         text,
  label       text,
  definition  text,
  synonyms    text[] DEFAULT '{}',
  parents     text[] DEFAULT '{}',     -- InterLex "superclasses"
  ancestors   text[] DEFAULT '{}',
  xrefs       jsonb  DEFAULT '[]'::jsonb,
  ts          tsvector
);

CREATE TABLE IF NOT EXISTS ontology.neurolex_annotations (
  ilx_id       text NOT NULL,
  prop_label   text NOT NULL,
  value        text NOT NULL,
  prop_ilx     text,
  raw          jsonb DEFAULT '{}'::jsonb,
  PRIMARY KEY (ilx_id, prop_label, value),
  FOREIGN KEY (ilx_id) REFERENCES ontology.neurolex (ilx_id) ON DELETE CASCADE
);

-- Indexes
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS neurolex_label_trgm     ON ontology.neurolex USING gin (label gin_trgm_ops);
CREATE INDEX IF NOT EXISTS neurolex_synonyms_gin   ON ontology.neurolex USING gin (synonyms);
CREATE INDEX IF NOT EXISTS neurolex_ts_gin         ON ontology.neurolex USING gin (ts);
CREATE INDEX IF NOT EXISTS neurolex_parents_gin    ON ontology.neurolex USING gin (parents);
CREATE INDEX IF NOT EXISTS neurolex_ancestors_gin  ON ontology.neurolex USING gin (ancestors);

-- Populate ts where missing (you can re-run safely)
UPDATE ontology.neurolex
SET ts = to_tsvector('english', coalesce(label,'') || ' ' || coalesce(definition,''))
WHERE ts IS NULL;


