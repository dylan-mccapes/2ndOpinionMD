-- Core term table (if not already):
CREATE TABLE IF NOT EXISTS ontology.neurolex (
  ilx_id     text PRIMARY KEY,
  label      text NOT NULL,
  definition text,
  synonyms   text[] DEFAULT '{}',
  parents    text[] DEFAULT '{}',
  ancestors  text[] DEFAULT '{}',
  iri        text,
  xrefs      jsonb DEFAULT '{}'::jsonb,
  vec        vector(3072)
);

-- Annotations (1 row per property assertion)
CREATE TABLE IF NOT EXISTS ontology.neurolex_annotations (
  ilx_id        text NOT NULL,
  prop_label    text NOT NULL,     -- e.g., hasDbXref, hasExactSynonym
  value         text NOT NULL,     -- e.g., ICD10:G12.2
  prop_ilx      text,
  raw           jsonb DEFAULT '{}'::jsonb,
  created_at    timestamptz DEFAULT now(),
  PRIMARY KEY (ilx_id, prop_label, value),
  FOREIGN KEY (ilx_id) REFERENCES ontology.neurolex(ilx_id) ON DELETE CASCADE
);

-- Helpful functional index to slice by system prefix quickly
CREATE INDEX IF NOT EXISTS neurolex_ann_value_prefix_idx
  ON ontology.neurolex_annotations (split_part(value, ':', 1), prop_label);

-- Optional FTS for free-text value annotations (notes, citations)
CREATE INDEX IF NOT EXISTS neurolex_ann_value_gin
  ON ontology.neurolex_annotations USING gin (to_tsvector('english', value));

CREATE SCHEMA IF NOT EXISTS ontology;

CREATE TABLE IF NOT EXISTS ontology.neurolex (
  ilx_id     text PRIMARY KEY,
  iri        text,
  label      text NOT NULL,
  definition text,
  synonyms   text[] DEFAULT '{}',
  parents    text[] DEFAULT '{}',
  ancestors  text[] DEFAULT '{}',
  xrefs      jsonb  DEFAULT '{}'::jsonb,
  vec        vector(3072)
);

CREATE TABLE IF NOT EXISTS ontology.neurolex_annotations (
  ilx_id     text NOT NULL,
  prop_label text NOT NULL,
  value      text NOT NULL,
  prop_ilx   text,
  raw        jsonb DEFAULT '{}'::jsonb,
  created_at timestamptz DEFAULT now(),
  PRIMARY KEY (ilx_id, prop_label, value),
  FOREIGN KEY (ilx_id) REFERENCES ontology.neurolex(ilx_id) ON DELETE CASCADE
);

