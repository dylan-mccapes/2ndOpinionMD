CREATE DATABASE knowledgegraph;

\c knowledgegraph;

CREATE SCHEMA IF NOT EXISTS ontology;

CREATE TABLE ontology.icd (
    code         TEXT PRIMARY KEY,
    title        TEXT,
    definition   TEXT,
    version      TEXT,
    parent_code  TEXT,
    chapter      TEXT,
    section      TEXT,
    full_path    TEXT,
    FOREIGN KEY (parent_code) REFERENCES ontology.icd(code)
);

CREATE INDEX idx_icd_parent_code ON ontology.icd(parent_code);
CREATE INDEX idx_icd_version ON ontology.icd(version);
CREATE INDEX idx_icd_full_path ON ontology.icd(full_path);

GRANT ALL PRIVILEGES ON SCHEMA ontology TO postgres;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA ontology TO postgres;
