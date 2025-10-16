-- database/schemas/setup_diagnostic_rules.sql
CREATE SCHEMA IF NOT EXISTS guidelines;

-- Main rules table: one row per named rule set (e.g., "McDonald 2017")
CREATE TABLE IF NOT EXISTS guidelines.diagnostic_rules (
  rule_id           SERIAL PRIMARY KEY,
  rule_key          TEXT UNIQUE NOT NULL,     -- e.g., 'mcdonald_2017', 'asas_axspa_2009', 'acr_fm_2016'
  title             TEXT NOT NULL,
  org               TEXT,                     -- 'ACR', 'EULAR', 'ASAS', 'ACR/EULAR', etc.
  condition         TEXT,                     -- 'Multiple Sclerosis', 'Axial Spondyloarthritis', ...
  version           TEXT,                     -- '2017', '2009', '2016', ...
  published_date    DATE,                     -- publication date if known
  rule_json         JSONB NOT NULL,           -- the executable rule object (see examples below)
  notes             TEXT,
  source_urls       TEXT[],                   -- provenance URLs (UI can render)
  created_at        TIMESTAMPTZ DEFAULT NOW(),
  updated_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Optional: curated test cases to regression-check rules
CREATE TABLE IF NOT EXISTS guidelines.diagnostic_rule_tests (
  test_id           SERIAL PRIMARY KEY,
  rule_key          TEXT NOT NULL REFERENCES guidelines.diagnostic_rules(rule_key) ON DELETE CASCADE,
  patient_facts     JSONB NOT NULL,           -- features to evaluate (see examples)
  expected_label    TEXT NOT NULL,            -- e.g., 'meets', 'does_not_meet', 'possible', etc.
  expected_details  JSONB,                    -- optional reason breakdown expectation
  created_at        TIMESTAMPTZ DEFAULT NOW()
);

-- Lookup speed helpers
CREATE INDEX IF NOT EXISTS diagnostic_rules_key_idx   ON guidelines.diagnostic_rules(rule_key);
CREATE INDEX IF NOT EXISTS diagnostic_rules_title_idx ON guidelines.diagnostic_rules USING gin (to_tsvector('english', title));

-- Fast filter/sort
CREATE INDEX IF NOT EXISTS diag_rules_org_idx       ON guidelines.diagnostic_rules (org);
CREATE INDEX IF NOT EXISTS diag_rules_condition_idx ON guidelines.diagnostic_rules (condition);
CREATE INDEX IF NOT EXISTS diag_rules_version_idx   ON guidelines.diagnostic_rules (version);
CREATE INDEX IF NOT EXISTS diag_rules_date_idx      ON guidelines.diagnostic_rules (published_date);

-- JSONB and array search
CREATE INDEX IF NOT EXISTS diag_rules_rulejson_gin  ON guidelines.diagnostic_rules USING gin (rule_json jsonb_path_ops);
CREATE INDEX IF NOT EXISTS diag_rules_sources_gin   ON guidelines.diagnostic_rules USING gin (source_urls);
