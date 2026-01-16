-- database/schemas/ehr_timeline.sql
-- EoH Timeline Engine: Patient Timeline Schema
-- 
-- This schema stores normalized patient timeline events for:
-- - Autoimmune flare prediction
-- - Probabilistic diagnostic landscape mapping
-- - Trajectory analysis & symptom/lab clustering
-- - Clinician-auditable EoH reasoning

-- Create the ehr schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS ehr;

-- Patient Timeline Table
-- Stores normalized timeline events with embeddings for ANN search
CREATE TABLE IF NOT EXISTS ehr.patient_timeline (
    id BIGSERIAL PRIMARY KEY,
    
    -- Patient identifier (external reference)
    patient_id TEXT NOT NULL,
    
    -- Event timestamp (when the event occurred)
    ts TIMESTAMP WITH TIME ZONE NOT NULL,
    
    -- Event classification
    -- Values: lab, symptom, medication, imaging, flare, note, self_report, visit, med_change
    event_type TEXT NOT NULL,
    
    -- Data source
    -- Values: patient_upload, EHR, synced_device, clinician_note, journal, demo
    source TEXT NOT NULL,
    
    -- Parsed structured fields (lab values, meds, vitals, etc.)
    -- Schema varies by event_type:
    -- - lab: {CRP, ESR, WBC, RF, anti_CCP, units, flags, ...}
    -- - symptom: {severity, location, duration, ...}
    -- - medication: {name, dose, frequency, action, ...}
    -- - flare: {severity, joints, duration_days, trigger, ...}
    -- - visit: {das28, swollen_joints, tender_joints, morning_stiffness_min, ...}
    structured JSONB,
    
    -- Final normalized narrative text (for embedding and display)
    text TEXT,
    
    -- Vector embedding for ANN search (OpenAI text-embedding-3-small)
    embedding VECTOR(1536),
    
    -- Additional metadata
    -- Can include: original_filename, processing_notes, confidence_scores, etc.
    meta JSONB DEFAULT '{}'::jsonb,
    
    -- Audit timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for efficient patient timeline queries (most recent first)
CREATE INDEX IF NOT EXISTS idx_patient_timeline_patient_ts 
    ON ehr.patient_timeline (patient_id, ts DESC);

-- Index for event type filtering
CREATE INDEX IF NOT EXISTS idx_patient_timeline_event_type 
    ON ehr.patient_timeline (event_type);

-- Index for source filtering
CREATE INDEX IF NOT EXISTS idx_patient_timeline_source 
    ON ehr.patient_timeline (source);

-- HNSW index for fast approximate nearest neighbor search on embeddings
-- Using cosine distance operator for semantic similarity
-- Note: Requires pgvector >= 0.5.0 for HNSW support
CREATE INDEX IF NOT EXISTS idx_patient_timeline_embedding_hnsw 
    ON ehr.patient_timeline 
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);

-- GIN index for JSONB structured field queries
CREATE INDEX IF NOT EXISTS idx_patient_timeline_structured 
    ON ehr.patient_timeline 
    USING gin (structured jsonb_path_ops);

-- GIN index for JSONB meta field queries
CREATE INDEX IF NOT EXISTS idx_patient_timeline_meta 
    ON ehr.patient_timeline 
    USING gin (meta jsonb_path_ops);

-- Full-text search index on narrative text
CREATE INDEX IF NOT EXISTS idx_patient_timeline_text_fts 
    ON ehr.patient_timeline 
    USING gin (to_tsvector('english', COALESCE(text, '')));

-- Composite index for common query patterns
CREATE INDEX IF NOT EXISTS idx_patient_timeline_patient_type_ts 
    ON ehr.patient_timeline (patient_id, event_type, ts DESC);

-- Add comments for documentation
COMMENT ON TABLE ehr.patient_timeline IS 
    'Normalized patient timeline events for EoH flare prediction and diagnostic landscape mapping';

COMMENT ON COLUMN ehr.patient_timeline.patient_id IS 
    'External patient identifier';

COMMENT ON COLUMN ehr.patient_timeline.ts IS 
    'Timestamp when the event occurred';

COMMENT ON COLUMN ehr.patient_timeline.event_type IS 
    'Event classification: lab, symptom, medication, imaging, flare, note, self_report, visit, med_change';

COMMENT ON COLUMN ehr.patient_timeline.source IS 
    'Data source: patient_upload, EHR, synced_device, clinician_note, journal, demo';

COMMENT ON COLUMN ehr.patient_timeline.structured IS 
    'Parsed structured fields as JSONB (schema varies by event_type)';

COMMENT ON COLUMN ehr.patient_timeline.text IS 
    'Final normalized narrative text for embedding and display';

COMMENT ON COLUMN ehr.patient_timeline.embedding IS 
    'Vector embedding (1536 dimensions) for ANN search using text-embedding-3-small';

COMMENT ON COLUMN ehr.patient_timeline.meta IS 
    'Additional metadata: original_filename, processing_notes, confidence_scores, etc.';
