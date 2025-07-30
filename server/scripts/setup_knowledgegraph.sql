
CREATE DATABASE knowledgegraph;

\c knowledgegraph;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA ontology;
CREATE SCHEMA ehr;
CREATE SCHEMA text;
CREATE SCHEMA molecular;
CREATE SCHEMA guidelines;


CREATE TABLE ontology.concepts (
  concept_id        BIGINT PRIMARY KEY,      -- SNOMED ID
  effective_time    DATE NOT NULL,
  active            BOOLEAN NOT NULL,
  module_id         BIGINT NOT NULL,
  definition_status SMALLINT,
  concept_status    SMALLINT
);
CREATE INDEX ON ontology.concepts(module_id);

CREATE TABLE ontology.descriptions (
  description_id    BIGINT PRIMARY KEY,
  concept_id        BIGINT REFERENCES ontology.concepts(concept_id),
  effective_time    DATE,
  active            BOOLEAN,
  module_id         BIGINT,
  language_code     VARCHAR(2),
  type_id           BIGINT,                  -- FSN / Synonym
  term              TEXT,
  case_significance SMALLINT,
  term_vec          vector(768)              -- PGVector embedding placeholder
);
CREATE INDEX desc_term_trgm ON ontology.descriptions USING GIN (term gin_trgm_ops);
CREATE INDEX desc_vec_cos ON ontology.descriptions USING ivfflat (term_vec vector_cosine_ops) WITH (lists = 100);

CREATE TABLE ontology.relationships (
  relationship_id        BIGINT PRIMARY KEY,
  source_id              BIGINT REFERENCES ontology.concepts(concept_id),
  destination_id         BIGINT REFERENCES ontology.concepts(concept_id),
  type_id                BIGINT,
  relationship_group     SMALLINT,
  characteristic_type_id BIGINT,
  modifier_id            BIGINT,
  effective_time         DATE,
  active                 BOOLEAN,
  module_id              BIGINT
);
CREATE INDEX rel_src_idx ON ontology.relationships(source_id);
CREATE INDEX rel_dst_idx ON ontology.relationships(destination_id);

CREATE TABLE ontology.refset_members (
  member_id              BIGINT PRIMARY KEY,
  refset_id              BIGINT,
  referenced_component_id BIGINT,
  value_id               BIGINT,
  effective_time         DATE,
  active                 BOOLEAN,
  module_id              BIGINT
);
CREATE INDEX refset_idx ON ontology.refset_members(refset_id);

CREATE TABLE ehr.patients (
  patient_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  sex        CHAR(1),
  yob        SMALLINT,
  yob_offset SMALLINT          -- for de-ID date shifting
);

CREATE TABLE ehr.encounters (
  encounter_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  patient_id   UUID REFERENCES ehr.patients(patient_id),
  admit_time   TIMESTAMP,
  discharge_time TIMESTAMP,
  encounter_type TEXT
);

CREATE TABLE ehr.diagnoses (
  diagnosis_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  encounter_id UUID REFERENCES ehr.encounters(encounter_id),
  concept_id   BIGINT REFERENCES ontology.concepts(concept_id),
  dx_time      TIMESTAMP
);

CREATE TABLE text.clinical_notes (
  note_id     UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  patient_id  UUID REFERENCES ehr.patients(patient_id),
  note_time   TIMESTAMP,
  note_text   TEXT,
  note_vec    vector(1536)     -- OpenAI text-embedding-3 size (example)
);
CREATE INDEX note_vec_cos ON text.clinical_notes USING ivfflat (note_vec vector_cosine_ops) WITH (lists = 200);

CREATE TABLE molecular.clinvar_variants (
  variation_id BIGINT PRIMARY KEY,
  gene         TEXT,
  snp_id       TEXT,
  significance TEXT,
  condition_id BIGINT REFERENCES ontology.concepts(concept_id)
);

CREATE TABLE guidelines.guideline_sets (
  guideline_id  SERIAL PRIMARY KEY,
  title         TEXT,
  source        TEXT,
  effective_date DATE
);

CREATE TABLE guidelines.rules (
  rule_id       SERIAL PRIMARY KEY,
  guideline_id  INT REFERENCES guidelines.guideline_sets(guideline_id),
  s_expression  TEXT,          -- machine-readable logic
  narrative     TEXT
);

ANALYZE;

\echo 'Knowledge graph database setup complete!'
