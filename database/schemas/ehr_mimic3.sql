-- MIMIC-III v1.4: minimal structured core
CREATE SCHEMA IF NOT EXISTS ehr_mimic3;

-- --------------------------
-- Core identity / stays
-- --------------------------
CREATE TABLE IF NOT EXISTS ehr_mimic3.patients (
  subject_id        INT PRIMARY KEY,
  gender            TEXT,
  dob               TIMESTAMP,
  dod               TIMESTAMP,
  dod_hosp          TIMESTAMP,
  dod_ssn           TIMESTAMP,
  expire_flag       INT
);

CREATE TABLE IF NOT EXISTS ehr_mimic3.admissions (
  row_id            BIGINT,
  subject_id        INT NOT NULL,
  hadm_id           INT PRIMARY KEY,
  admittime         TIMESTAMP,
  dischtime         TIMESTAMP,
  deathtime         TIMESTAMP,
  admission_type    TEXT,
  admission_location TEXT,
  discharge_location TEXT,
  insurance         TEXT,
  language          TEXT,
  religion          TEXT,
  marital_status    TEXT,
  ethnicity         TEXT,
  edregtime         TIMESTAMP,
  edouttime         TIMESTAMP,
  diagnosis         TEXT,
  hospital_expire_flag INT,
  has_chartevents_data INT
);

CREATE TABLE IF NOT EXISTS ehr_mimic3.icustays (
  row_id            BIGINT,
  subject_id        INT NOT NULL,
  hadm_id           INT,
  icustay_id        INT PRIMARY KEY,
  dbsource          TEXT,
  first_careunit    TEXT,
  last_careunit     TEXT,
  first_wardid      INT,
  last_wardid       INT,
  intime            TIMESTAMP,
  outtime           TIMESTAMP,
  los               NUMERIC
);

-- --------------------------
-- Diagnoses / procedures
-- --------------------------
CREATE TABLE IF NOT EXISTS ehr_mimic3.d_icd_diagnoses (
  row_id      BIGINT,
  icd9_code   TEXT PRIMARY KEY,
  short_title TEXT,
  long_title  TEXT
);

CREATE TABLE IF NOT EXISTS ehr_mimic3.d_icd_procedures (
  row_id      BIGINT,
  icd9_code   TEXT PRIMARY KEY,
  short_title TEXT,
  long_title  TEXT
);

CREATE TABLE IF NOT EXISTS ehr_mimic3.diagnoses_icd (
  row_id    BIGINT,
  subject_id INT NOT NULL,
  hadm_id   INT NOT NULL,
  seq_num   INT,
  icd9_code TEXT
);

CREATE TABLE IF NOT EXISTS ehr_mimic3.procedures_icd (
  row_id    BIGINT,
  subject_id INT NOT NULL,
  hadm_id   INT NOT NULL,
  seq_num   INT,
  icd9_code TEXT
);

-- --------------------------
-- Labs
-- --------------------------
CREATE TABLE IF NOT EXISTS ehr_mimic3.d_labitems (
  row_id    BIGINT,
  itemid    INT PRIMARY KEY,
  label     TEXT,
  fluid     TEXT,
  category  TEXT,
  loinc_code TEXT
);

CREATE TABLE IF NOT EXISTS ehr_mimic3.labevents (
  row_id    BIGINT,
  subject_id INT NOT NULL,
  hadm_id   INT,
  itemid    INT NOT NULL,
  charttime TIMESTAMP,
  value     TEXT,
  valuenum  NUMERIC,
  valueuom  TEXT,
  flag      TEXT
);

-- --------------------------
-- Indexes for speed
-- --------------------------
CREATE INDEX IF NOT EXISTS mimic3_patients_gender_idx        ON ehr_mimic3.patients (gender);
CREATE INDEX IF NOT EXISTS mimic3_admissions_subject_idx     ON ehr_mimic3.admissions (subject_id);
CREATE INDEX IF NOT EXISTS mimic3_icustays_subject_idx       ON ehr_mimic3.icustays (subject_id);
CREATE INDEX IF NOT EXISTS mimic3_icustays_hadm_idx          ON ehr_mimic3.icustays (hadm_id);
CREATE INDEX IF NOT EXISTS mimic3_diag_hadm_idx              ON ehr_mimic3.diagnoses_icd (hadm_id);
CREATE INDEX IF NOT EXISTS mimic3_diag_icd9_idx              ON ehr_mimic3.diagnoses_icd (icd9_code);
CREATE INDEX IF NOT EXISTS mimic3_proc_hadm_idx              ON ehr_mimic3.procedures_icd (hadm_id);
CREATE INDEX IF NOT EXISTS mimic3_proc_icd9_idx              ON ehr_mimic3.procedures_icd (icd9_code);
CREATE INDEX IF NOT EXISTS mimic3_lab_subject_chart_idx      ON ehr_mimic3.labevents (subject_id, charttime);
CREATE INDEX IF NOT EXISTS mimic3_lab_item_idx               ON ehr_mimic3.labevents (itemid);
-- Optional (large tables): BRIN on time
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes WHERE schemaname='ehr_mimic3' AND indexname='mimic3_lab_charttime_brin'
  ) THEN
    EXECUTE 'CREATE INDEX mimic3_lab_charttime_brin ON ehr_mimic3.labevents USING brin (charttime)';
  END IF;
END$$;

