-- database/schemas/ehr_detective_runs.sql
-- Persists EoHD detective run results (plan, step reports, final report, PDF)

CREATE SCHEMA IF NOT EXISTS ehr;

CREATE TABLE IF NOT EXISTS ehr.detective_runs (
    run_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      TEXT NOT NULL,
    question        TEXT NOT NULL,
    focus           TEXT,
    plan_json       JSONB,
    steps_json      JSONB NOT NULL,
    final_report    TEXT,
    graph_events    INTEGER,
    graph_edges     INTEGER,
    elapsed_ms      INTEGER,
    pdf_path        TEXT,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_dr_patient
    ON ehr.detective_runs (patient_id, created_at DESC);

COMMENT ON TABLE ehr.detective_runs IS
    'Persisted EoHD detective run results: plan, per-step answers/evidence, final synthesis report, and PDF path';
