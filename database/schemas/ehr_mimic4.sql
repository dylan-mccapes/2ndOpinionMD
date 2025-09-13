-- Schema
CREATE SCHEMA IF NOT EXISTS ehr_mimic4;

-- ======================
-- HOSP module
-- ======================
CREATE TABLE IF NOT EXISTS ehr_mimic4.patients (
  subject_id           BIGINT PRIMARY KEY,
  gender               TEXT,
  anchor_age           INT,
  anchor_year          INT,
  anchor_year_group    TEXT,
  dod                  TIMESTAMP NULL
);

CREATE TABLE IF NOT EXISTS ehr_mimic4.admissions (
  hadm_id              BIGINT PRIMARY KEY,
  subject_id           BIGINT NOT NULL,
  admittime            TIMESTAMP,
  dischtime            TIMESTAMP,
  deathtime            TIMESTAMP NULL,
  admission_type       TEXT,
  admit_provider_id    TEXT,
  insurance            TEXT,
  language             TEXT,
  marital_status       TEXT,
  race                 TEXT,
  edregtime            TIMESTAMP,
  edouttime            TIMESTAMP,
  hospital_expire_flag SMALLINT
);

CREATE TABLE IF NOT EXISTS ehr_mimic4.transfers (
  transfer_id          BIGINT PRIMARY KEY,
  subject_id           BIGINT,
  hadm_id              BIGINT,
  eventtype            TEXT,
  careunit             TEXT,
  intime               TIMESTAMP,
  outtime              TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ehr_mimic4.d_labitems (
  itemid               INT PRIMARY KEY,
  label                TEXT,
  fluid                TEXT,
  category             TEXT
  -- loinc_code intentionally omitted (removed in v2.0+)
);

CREATE TABLE IF NOT EXISTS ehr_mimic4.labevents (
  lab_row_id           BIGSERIAL PRIMARY KEY,         -- synthetic PK
  subject_id           BIGINT,
  hadm_id              BIGINT,
  specimen_id          BIGINT,
  itemid               INT,
  charttime            TIMESTAMP,
  storetime            TIMESTAMP,
  value                TEXT,
  valuenum             DOUBLE PRECISION,
  valueuom             TEXT,
  ref_range_lower      DOUBLE PRECISION,
  ref_range_upper      DOUBLE PRECISION,
  flag                 TEXT,
  priority             TEXT,
  comments             TEXT,
  order_provider_id    TEXT
);

CREATE TABLE IF NOT EXISTS ehr_mimic4.d_icd_diagnoses (
  icd_code             TEXT,
  icd_version          SMALLINT,
  long_title           TEXT,
  PRIMARY KEY (icd_code, icd_version)
);

CREATE TABLE IF NOT EXISTS ehr_mimic4.diagnoses_icd (
  row_id               BIGSERIAL PRIMARY KEY,
  subject_id           BIGINT,
  hadm_id              BIGINT,
  seq_num              INT,
  icd_code             TEXT,
  icd_version          SMALLINT
);
CREATE UNIQUE INDEX IF NOT EXISTS mimic4_dx_unique
  ON ehr_mimic4.diagnoses_icd(subject_id, hadm_id, seq_num);

CREATE TABLE IF NOT EXISTS ehr_mimic4.d_icd_procedures (
  icd_code             TEXT,
  icd_version          SMALLINT,
  long_title           TEXT,
  PRIMARY KEY (icd_code, icd_version)
);

CREATE TABLE IF NOT EXISTS ehr_mimic4.procedures_icd (
  row_id               BIGSERIAL PRIMARY KEY,
  subject_id           BIGINT,
  hadm_id              BIGINT,
  seq_num              INT,
  icd_code             TEXT,
  icd_version          SMALLINT
);
CREATE UNIQUE INDEX IF NOT EXISTS mimic4_proc_unique
  ON ehr_mimic4.procedures_icd(subject_id, hadm_id, seq_num);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS mimic4_adm_subject_idx ON ehr_mimic4.admissions(subject_id);
CREATE INDEX IF NOT EXISTS mimic4_transfers_subject_idx ON ehr_mimic4.transfers(subject_id);
CREATE INDEX IF NOT EXISTS mimic4_transfers_hadm_idx ON ehr_mimic4.transfers(hadm_id);
CREATE INDEX IF NOT EXISTS mimic4_lab_subject_idx ON ehr_mimic4.labevents(subject_id);
CREATE INDEX IF NOT EXISTS mimic4_lab_hadm_idx ON ehr_mimic4.labevents(hadm_id);
CREATE INDEX IF NOT EXISTS mimic4_lab_item_idx ON ehr_mimic4.labevents(itemid);
CREATE INDEX IF NOT EXISTS mimic4_lab_charttime_idx ON ehr_mimic4.labevents(charttime);

-- ======================
-- ICU module
-- ======================
CREATE TABLE IF NOT EXISTS ehr_mimic4.icustays (
  stay_id              BIGINT PRIMARY KEY,
  subject_id           BIGINT,
  hadm_id              BIGINT,
  first_careunit       TEXT,
  last_careunit        TEXT,
  intime               TIMESTAMP,
  outtime              TIMESTAMP,
  los                  DOUBLE PRECISION
);

CREATE TABLE IF NOT EXISTS ehr_mimic4.d_items (
  itemid               INT PRIMARY KEY,
  label                TEXT,
  linksto              TEXT,
  category             TEXT,
  unitname             TEXT,
  param_type           TEXT
);

CREATE INDEX IF NOT EXISTS mimic4_icu_subject_idx ON ehr_mimic4.icustays(subject_id);
CREATE INDEX IF NOT EXISTS mimic4_icu_hadm_idx    ON ehr_mimic4.icustays(hadm_id);

