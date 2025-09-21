-- database/schemas/setup_loinc_schema.sql
CREATE SCHEMA IF NOT EXISTS ontology;

-- 1) Core terms
CREATE TABLE IF NOT EXISTS ontology.loinc_terms (
  loinc_num TEXT PRIMARY KEY,
  component TEXT,
  property TEXT,
  time_aspct TEXT,
  system TEXT,
  scale_typ TEXT,
  method_typ TEXT,
  class TEXT,
  classtype INT,
  long_common_name TEXT,
  shortname TEXT,
  external_copyright_notice TEXT,
  status TEXT,
  version_first_released TEXT,
  version_last_changed TEXT,
  src_version TEXT,
  ingested_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS loinc_terms_component_system_idx ON ontology.loinc_terms (component, system);
CREATE INDEX IF NOT EXISTS loinc_terms_class_idx ON ontology.loinc_terms (class);
-- Helpful text search/fuzzy indexes
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS loinc_long_common_name_trgm ON ontology.loinc_terms USING gin (long_common_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS loinc_shortname_trgm        ON ontology.loinc_terms USING gin (shortname gin_trgm_ops);

-- 2) Panels
CREATE TABLE IF NOT EXISTS ontology.loinc_panels (
  parent_loinc TEXT NOT NULL,
  child_loinc  TEXT NOT NULL,
  sequence     INT,
  display_text TEXT,
  observation_required TEXT,
  PRIMARY KEY (parent_loinc, child_loinc)
);
CREATE INDEX IF NOT EXISTS loinc_panels_parent_idx ON ontology.loinc_panels (parent_loinc);

-- 3) Answer lists
CREATE TABLE IF NOT EXISTS ontology.loinc_answer_list (
  answer_list_id   TEXT PRIMARY KEY,
  answer_list_name TEXT,
  answer_list_oid  TEXT,
  ext_defined_yn   TEXT
);

CREATE TABLE IF NOT EXISTS ontology.loinc_answer_link (
  loinc_num       TEXT NOT NULL,
  answer_list_id  TEXT NOT NULL,
  link_type       TEXT,
  applicable_context TEXT,
  PRIMARY KEY (loinc_num, answer_list_id)
);

-- 4) Parts & links
CREATE TABLE IF NOT EXISTS ontology.loinc_parts (
  part_number       TEXT PRIMARY KEY,
  part_type_name    TEXT,
  part_name         TEXT,
  part_display_name TEXT,
  status            TEXT
);

CREATE TABLE IF NOT EXISTS ontology.loinc_part_link (
  loinc_num      TEXT NOT NULL,
  part_number    TEXT NOT NULL,
  part_name      TEXT,
  part_code_system TEXT,
  part_type_name TEXT NOT NULL,
  PRIMARY KEY (loinc_num, part_number, part_type_name)
);

