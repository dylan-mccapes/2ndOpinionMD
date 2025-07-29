
CREATE DATABASE knowledgegraph;

\c knowledgegraph;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS vector;

CREATE SCHEMA ontology;
CREATE SCHEMA ehr;
CREATE SCHEMA text;
CREATE SCHEMA molecular;
CREATE SCHEMA guidelines;

CREATE TABLE ontology.concepts (
    concept_id SERIAL PRIMARY KEY,
    code VARCHAR(50) NOT NULL,
    name TEXT NOT NULL,
    system VARCHAR(50), -- SNOMED, ICD10, etc.
    description TEXT
);

CREATE TABLE ontology.relationships (
    relationship_id SERIAL PRIMARY KEY,
    source_id INT REFERENCES ontology.concepts(concept_id),
    target_id INT REFERENCES ontology.concepts(concept_id),
    type VARCHAR(50) -- e.g., "is_a", "part_of"
);

CREATE TABLE ehr.patients (
    patient_id UUID PRIMARY KEY,
    first_name TEXT,
    last_name TEXT,
    dob DATE,
    gender TEXT
);

CREATE TABLE ehr.encounters (
    encounter_id UUID PRIMARY KEY,
    patient_id UUID REFERENCES ehr.patients(patient_id),
    visit_date DATE,
    type TEXT -- inpatient, outpatient
);

CREATE TABLE ehr.diagnoses (
    diagnosis_id UUID PRIMARY KEY,
    encounter_id UUID REFERENCES ehr.encounters(encounter_id),
    concept_id INT REFERENCES ontology.concepts(concept_id),
    diagnosed_on DATE
);

CREATE TABLE ehr.medications (
    med_id UUID PRIMARY KEY,
    encounter_id UUID REFERENCES ehr.encounters(encounter_id),
    drug_name TEXT,
    dose TEXT,
    route TEXT
);

CREATE TABLE text.clinical_notes (
    note_id UUID PRIMARY KEY,
    patient_id UUID REFERENCES ehr.patients(patient_id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    note_text TEXT
);

CREATE TABLE molecular.biomarkers (
    biomarker_id SERIAL PRIMARY KEY,
    patient_id UUID REFERENCES ehr.patients(patient_id),
    name TEXT,
    value TEXT,
    units TEXT,
    measured_on DATE
);

CREATE TABLE molecular.genomic_variants (
    variant_id SERIAL PRIMARY KEY,
    patient_id UUID REFERENCES ehr.patients(patient_id),
    gene TEXT,
    variant TEXT,
    effect TEXT,
    clinical_significance TEXT
);

CREATE TABLE guidelines.guideline_sets (
    guideline_id SERIAL PRIMARY KEY,
    title TEXT,
    source TEXT,
    effective_date DATE
);

CREATE TABLE guidelines.rules (
    rule_id SERIAL PRIMARY KEY,
    guideline_id INT REFERENCES guidelines.guideline_sets(guideline_id),
    condition TEXT,  -- e.g., SQL/logic for triggering
    recommendation TEXT
);

GRANT ALL PRIVILEGES ON DATABASE knowledgegraph TO devin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ontology TO devin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ehr TO devin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA text TO devin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA molecular TO devin;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA guidelines TO devin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ontology TO devin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA ehr TO devin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA text TO devin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA molecular TO devin;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA guidelines TO devin;

CREATE INDEX idx_concepts_code ON ontology.concepts(code);
CREATE INDEX idx_concepts_system ON ontology.concepts(system);
CREATE INDEX idx_clinical_notes_text ON text.clinical_notes USING gin(to_tsvector('english', note_text));
CREATE INDEX idx_patients_name ON ehr.patients(last_name, first_name);
CREATE INDEX idx_encounters_date ON ehr.encounters(visit_date);
CREATE INDEX idx_biomarkers_name ON molecular.biomarkers(name);
CREATE INDEX idx_genomic_variants_gene ON molecular.genomic_variants(gene);

\echo 'Knowledge graph database setup complete!'
