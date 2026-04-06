-- database/schemas/ehr_chat_graph.sql
-- Patient Chat Graph — bounded conversational memory tied to PTV
-- Adapted from PortalVision chat_graph.py methodology
-- Prerequisite: ehr schema

CREATE SCHEMA IF NOT EXISTS ehr;

-- One chat graph state per patient (bounded, decaying, anchored to PTV nodes)
CREATE TABLE IF NOT EXISTS ehr.chat_graph (
    patient_id      TEXT NOT NULL,
    message_id      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    role            TEXT NOT NULL CHECK (role IN ('patient', 'doctor', 'system', 'agent')),
    content         TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_referenced TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decay_score     REAL NOT NULL DEFAULT 1.0,
    retention_reason TEXT NOT NULL DEFAULT 'new_message',

    -- PTV node anchoring: when a message clarifies or relates to a graph event
    anchored_event_ids TEXT[] DEFAULT '{}',

    -- Reference edges (typed, like PortalVision)
    -- journal_entry, detective_report, ptv_event, enrichment, clarification
    reference_edges JSONB NOT NULL DEFAULT '{}',

    -- Who authored (user_id from auth system, NULL for agent/system)
    author_id       UUID,

    -- Evicted messages are soft-deleted (preserved for audit)
    evicted_at      TIMESTAMPTZ,
    eviction_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_cg_patient_active
    ON ehr.chat_graph (patient_id, created_at)
    WHERE evicted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_cg_patient_decay
    ON ehr.chat_graph (patient_id, decay_score DESC)
    WHERE evicted_at IS NULL;

CREATE INDEX IF NOT EXISTS idx_cg_anchored_events
    ON ehr.chat_graph USING gin (anchored_event_ids)
    WHERE evicted_at IS NULL;

-- Per-patient budget metadata
CREATE TABLE IF NOT EXISTS ehr.chat_graph_budget (
    patient_id          TEXT PRIMARY KEY,
    max_total_chars     INTEGER NOT NULL DEFAULT 500000,
    current_total_chars INTEGER NOT NULL DEFAULT 0,
    total_messages      INTEGER NOT NULL DEFAULT 0,
    total_evictions     INTEGER NOT NULL DEFAULT 0,
    last_decay_run      TIMESTAMPTZ,
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE ehr.chat_graph IS
    'Patient chat graph: bounded conversational memory with logarithmic decay, '
    'PTV node anchoring, and provenance-tracked eviction. '
    'Adapted from PortalVision chat_graph.py — nothing persists without provenance.';

COMMENT ON TABLE ehr.chat_graph_budget IS
    'Per-patient character budget and eviction stats for chat graph.';
