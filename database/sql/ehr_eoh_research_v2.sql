-- =========================================
-- SCHEMA: ehr, eoh, research
-- v2.0 – Synthetic timelines + EoH + research
-- =========================================

CREATE SCHEMA IF NOT EXISTS ehr;
CREATE SCHEMA IF NOT EXISTS eoh;
CREATE SCHEMA IF NOT EXISTS research;

-- 1. Core EHR tables
-- -------------------

-- 1.1 Patients
CREATE TABLE IF NOT EXISTS ehr.patient (
    id              TEXT PRIMARY KEY,           -- e.g. 'DEMO_RA_001'
    mrn             TEXT NULL,
    birth_date      DATE NULL,
    sex             TEXT NULL,                  -- 'female','male','other','unknown'
    race_ethnicity  TEXT NULL,
    created_at      TIMESTAMPTZ DEFAULT now(),
    meta            JSONB DEFAULT '{}'::jsonb
);

-- 1.2 Encounters
CREATE TABLE IF NOT EXISTS ehr.encounter (
    id              BIGSERIAL PRIMARY KEY,
    patient_id      TEXT NOT NULL REFERENCES ehr.patient(id),
    encounter_type  TEXT NOT NULL,          -- 'outpatient','inpatient','ed','telehealth'
    start_ts        TIMESTAMPTZ NOT NULL,
    end_ts          TIMESTAMPTZ NULL,
    location        TEXT NULL,
    clinician_id    TEXT NULL,
    meta            JSONB DEFAULT '{}'::jsonb
);

-- 1.3 Patient timeline spine
CREATE TABLE IF NOT EXISTS ehr.patient_timeline (
    id              BIGSERIAL PRIMARY KEY,
    patient_id      TEXT NOT NULL REFERENCES ehr.patient(id),
    ts              TIMESTAMPTZ NOT NULL,
    event_type      TEXT NOT NULL,          -- see taxonomy in code: 'visit','lab','note',...
    event_subtype   TEXT NULL,              -- 'cbc','hrct_chest','note_rheum', etc.
    encounter_id    BIGINT NULL REFERENCES ehr.encounter(id),
    source          TEXT NOT NULL,          -- 'synthetic_seed','mimic4','manual','guideline'
    structured      JSONB DEFAULT '{}'::jsonb,
    text            TEXT DEFAULT '',
    embedding       BYTEA NULL,
    meta            JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_timeline_patient_ts
    ON ehr.patient_timeline (patient_id, ts);

CREATE INDEX IF NOT EXISTS idx_timeline_structured_gin
    ON ehr.patient_timeline USING GIN (structured jsonb_path_ops);

-- 2. EoH-specific tables
-- -----------------------

-- 2.1 Diagnostic landscape snapshots (for drift over time)
CREATE TABLE IF NOT EXISTS eoh.diagnostic_landscape_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    patient_id      TEXT NOT NULL REFERENCES ehr.patient(id),
    ts              TIMESTAMPTZ NOT NULL,     -- snapshot time
    landscape       JSONB NOT NULL,           -- normalized dict: ra_like...other
    source          TEXT NOT NULL,            -- 'daily_batch','on_demand','seed'
    model_version   TEXT NULL,
    meta            JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_eoh_landscape_patient_ts
    ON eoh.diagnostic_landscape_snapshots (patient_id, ts);

-- 2.2 Flare / noise QA annotations
CREATE TABLE IF NOT EXISTS eoh.flare_annotation (
    id              BIGSERIAL PRIMARY KEY,
    patient_id      TEXT NOT NULL REFERENCES ehr.patient(id),
    timeline_id     BIGINT NOT NULL REFERENCES ehr.patient_timeline(id),
    label_source    TEXT NOT NULL,        -- 'clinician','patient','qa_reviewer'
    flare_label     TEXT NOT NULL,        -- 'flare','noise','uncertain'
    flare_type      TEXT NULL,            -- 'articular','systemic','pulmonary'
    severity        TEXT NULL,            -- 'mild','moderate','severe'
    rationale       TEXT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 2.3 EoH decision log (router + answer metadata)
CREATE TABLE IF NOT EXISTS eoh.decision_log (
    id              BIGSERIAL PRIMARY KEY,
    patient_id      TEXT NULL REFERENCES ehr.patient(id),
    timeline_ids    BIGINT[] NULL,                -- context events used
    q_text          TEXT NOT NULL,
    question_type   TEXT NOT NULL,                -- 'A','B','C','D','E','OTHER'
    router_plan     JSONB NOT NULL,
    eoh_answer_meta JSONB NOT NULL,
    model_version   TEXT NOT NULL,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 3. Research / evidence linkage
-- -------------------------------

CREATE TABLE IF NOT EXISTS research.evidence (
    id              TEXT PRIMARY KEY,     -- 'VALYU:123456' or hash
    title           TEXT NOT NULL,
    journal         TEXT NULL,
    year            INT NULL,
    doi             TEXT NULL,
    url             TEXT NULL,
    abstract        TEXT NULL,
    meta            JSONB DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS research.patient_evidence_link (
    id              BIGSERIAL PRIMARY KEY,
    patient_id      TEXT NOT NULL REFERENCES ehr.patient(id),
    evidence_id     TEXT NOT NULL REFERENCES research.evidence(id),
    ts              TIMESTAMPTZ NOT NULL,
    context         TEXT NULL,            -- why it was used
    relevance       REAL NULL,
    query_text      TEXT NULL,
    model_version   TEXT NULL
);
