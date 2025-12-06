CREATE SCHEMA IF NOT EXISTS eoh;

CREATE TABLE IF NOT EXISTS eoh.patient_state (
    patient_id       text PRIMARY KEY,
    updated_at       timestamptz NOT NULL DEFAULT now(),

    -- high-level stability (placeholder fields you can refine later)
    stability_band   int,
    flare_tendency   double precision,

    -- RA / SLE flare risk examples (you can extend for other diseases)
    ra_flare_30d_prob   double precision,
    ra_flare_90d_prob   double precision,
    sle_flare_90d_prob  double precision,

    -- diagnostic landscape: conceptual probabilities / weights
    p_ra           double precision,
    p_sle          double precision,
    p_psa          double precision,
    p_sjogren      double precision,
    p_mctd         double precision,
    p_vasculitis   double precision,
    p_other        double precision,

    -- free-form JSON for future modules / features
    raw            jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS eoh.module_run (
    id              bigserial PRIMARY KEY,
    patient_id      text NOT NULL,
    module_name     text NOT NULL,      -- e.g. 'M13_flare_risk'
    module_version  text NOT NULL,
    started_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz,
    status          text NOT NULL,      -- 'success' | 'error'
    input_hash      text,
    output_json     jsonb,
    error_message   text
);

CREATE INDEX IF NOT EXISTS idx_eoh_module_run_patient
    ON eoh.module_run (patient_id, module_name, started_at DESC);