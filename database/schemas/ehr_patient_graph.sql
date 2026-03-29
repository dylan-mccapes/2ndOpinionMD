-- database/schemas/ehr_patient_graph.sql
-- PatientTimelineVision graph + PatientTimelineChart embeddings
-- Prerequisite: pgvector extension, ehr schema

CREATE EXTENSION IF NOT EXISTS vector;
CREATE SCHEMA IF NOT EXISTS ehr;

-- Full graph stored as JSONB (one row per patient)
CREATE TABLE IF NOT EXISTS ehr.patient_graph_vision (
    patient_id  TEXT PRIMARY KEY,
    graph_json  JSONB NOT NULL,
    updated_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Per-event chart embeddings (384-dim sentence-transformers)
CREATE TABLE IF NOT EXISTS ehr.patient_graph_chart (
    id          BIGSERIAL PRIMARY KEY,
    patient_id  TEXT NOT NULL,
    event_id    TEXT NOT NULL,
    event_type  TEXT NOT NULL,
    ts_text     TEXT,
    preview     TEXT,
    embedding   VECTOR(384) NOT NULL,
    UNIQUE (patient_id, event_id)
);

CREATE INDEX IF NOT EXISTS idx_pgc_patient
    ON ehr.patient_graph_chart (patient_id);

CREATE INDEX IF NOT EXISTS idx_pgc_embedding_hnsw
    ON ehr.patient_graph_chart
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

CREATE INDEX IF NOT EXISTS idx_pgc_preview_fts
    ON ehr.patient_graph_chart
    USING gin (to_tsvector('english', COALESCE(preview, '')));

-- Readiness metadata (lightweight, checked at query time)
CREATE TABLE IF NOT EXISTS ehr.patient_graph_status (
    patient_id      TEXT PRIMARY KEY,
    is_ready        BOOLEAN DEFAULT FALSE,
    event_count     INTEGER DEFAULT 0,
    edge_count      INTEGER DEFAULT 0,
    chart_count     INTEGER DEFAULT 0,
    ts_coverage     REAL DEFAULT 0.0,
    built_at        TIMESTAMP WITH TIME ZONE,
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

COMMENT ON TABLE ehr.patient_graph_vision IS
    'Full PatientTimelineVision graph (events + connascence edges) as JSONB per patient';

COMMENT ON TABLE ehr.patient_graph_chart IS
    'PatientTimelineChart: 384-dim sentence-transformer embeddings per graph event';

COMMENT ON TABLE ehr.patient_graph_status IS
    'Readiness gate: is the graph built, validated, and ready for EoHD?';
