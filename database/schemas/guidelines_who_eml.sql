-- WHO Essential Medicines (EML + EMLc) + AWaRe + Committee Executive Summary
CREATE SCHEMA IF NOT EXISTS guidelines;

-- ===== Medicines master =====
CREATE TABLE IF NOT EXISTS guidelines.who_eml_medicines (
  med_id           BIGSERIAL PRIMARY KEY,
  med_key          TEXT UNIQUE NOT NULL,      -- md5(edition|inn|list_type)
  inn              TEXT NOT NULL,             -- International Nonproprietary Name
  list_type        TEXT NOT NULL CHECK (list_type IN ('EML','EMLc')),
  section_path     TEXT,                      -- e.g., '1.1 Analgesics ...'
  antibiotic_group TEXT,                      -- AWaRe: Access / Watch / Reserve
  first_added_year INT,
  edition          INT NOT NULL,              -- 24 for EML 2025; 10 for EMLc 2025
  year             INT NOT NULL,              -- e.g., 2025
  notes            TEXT,
  raw              JSONB DEFAULT '{}'::jsonb,
  ts               TSVECTOR
);

CREATE INDEX IF NOT EXISTS who_eml_medicines_key_idx ON guidelines.who_eml_medicines(med_key);
CREATE INDEX IF NOT EXISTS who_eml_medicines_inn_trgm ON guidelines.who_eml_medicines USING gin (inn gin_trgm_ops);
CREATE INDEX IF NOT EXISTS who_eml_medicines_ts_gin  ON guidelines.who_eml_medicines USING gin (ts);

-- ===== ATC links =====
CREATE TABLE IF NOT EXISTS guidelines.who_eml_atc (
  med_id   BIGINT REFERENCES guidelines.who_eml_medicines(med_id) ON DELETE CASCADE,
  atc_code TEXT NOT NULL,
  PRIMARY KEY (med_id, atc_code)
);
CREATE INDEX IF NOT EXISTS who_eml_atc_code_idx ON guidelines.who_eml_atc(atc_code);

-- ===== ICD-11 indications =====
CREATE TABLE IF NOT EXISTS guidelines.who_eml_icd11 (
  med_id     BIGINT REFERENCES guidelines.who_eml_medicines(med_id) ON DELETE CASCADE,
  icd11_code TEXT NOT NULL,
  indication TEXT,
  PRIMARY KEY (med_id, icd11_code)
);
CREATE INDEX IF NOT EXISTS who_eml_icd11_code_idx ON guidelines.who_eml_icd11(icd11_code);

-- ===== Formulations =====
CREATE TABLE IF NOT EXISTS guidelines.who_eml_formulations (
  form_id            BIGSERIAL PRIMARY KEY,
  med_id             BIGINT REFERENCES guidelines.who_eml_medicines(med_id) ON DELETE CASCADE,
  route              TEXT,
  dose_form          TEXT,
  strength           TEXT,
  age_restriction    TEXT,
  sex                TEXT,
  weight_restriction TEXT
);

-- ===== Therapeutic alternatives =====
CREATE TABLE IF NOT EXISTS guidelines.who_eml_alternatives (
  alt_id  BIGSERIAL PRIMARY KEY,
  med_id  BIGINT REFERENCES guidelines.who_eml_medicines(med_id) ON DELETE CASCADE,
  alt_inn TEXT NOT NULL,
  note    TEXT
);

-- ===== Footnotes & justifications =====
CREATE TABLE IF NOT EXISTS guidelines.who_eml_footnotes (
  med_id BIGINT REFERENCES guidelines.who_eml_medicines(med_id) ON DELETE CASCADE,
  n      TEXT,
  text   TEXT,
  PRIMARY KEY (med_id, n)
);

CREATE TABLE IF NOT EXISTS guidelines.who_eml_justifications (
  med_id BIGINT REFERENCES guidelines.who_eml_medicines(med_id) ON DELETE CASCADE,
  text   TEXT,
  PRIMARY KEY (med_id, text)
);

-- ===== AWaRe mapping (optional XLSX) =====
CREATE TABLE IF NOT EXISTS guidelines.who_aware_map (
  aware_id  BIGSERIAL PRIMARY KEY,
  atc_code  TEXT,
  inn       TEXT,
  "group"   TEXT CHECK ("group" IN ('Access','Watch','Reserve')),
  raw       JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS who_aware_atc_idx  ON guidelines.who_aware_map(atc_code);
CREATE INDEX IF NOT EXISTS who_aware_inn_trgm ON guidelines.who_aware_map USING gin (inn gin_trgm_ops);

-- ===== FTS triggers =====
CREATE OR REPLACE FUNCTION guidelines.who_eml_tsv_update() RETURNS trigger AS $$
BEGIN
  NEW.ts := to_tsvector('english',
            coalesce(NEW.inn,'') || ' ' ||
            coalesce(NEW.section_path,'') || ' ' ||
            coalesce(NEW.notes,''));
  RETURN NEW;
END;$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_who_eml_tsv ON guidelines.who_eml_medicines;
CREATE TRIGGER trg_who_eml_tsv
BEFORE INSERT OR UPDATE ON guidelines.who_eml_medicines
FOR EACH ROW EXECUTE FUNCTION guidelines.who_eml_tsv_update();

-- ===== Committee Executive Summary =====
CREATE TABLE IF NOT EXISTS guidelines.who_committee_reports (
  report_id     BIGSERIAL PRIMARY KEY,
  title         TEXT,
  year          INT,
  edition_eml   INT,
  edition_emlc  INT,
  doc_type      TEXT DEFAULT 'executive_summary',
  url           TEXT,
  file_path     TEXT,
  published_on  DATE,
  raw           JSONB DEFAULT '{}'::jsonb,
  ts            TSVECTOR
);
CREATE INDEX IF NOT EXISTS who_committee_reports_year_idx ON guidelines.who_committee_reports(year);
CREATE INDEX IF NOT EXISTS who_committee_reports_ts_gin  ON guidelines.who_committee_reports USING gin(ts);

CREATE TABLE IF NOT EXISTS guidelines.who_committee_sections (
  section_id   BIGSERIAL PRIMARY KEY,
  report_id    BIGINT REFERENCES guidelines.who_committee_reports(report_id) ON DELETE CASCADE,
  heading      TEXT,
  page_start   INT,
  page_end     INT,
  text         TEXT,
  ts           TSVECTOR
);
CREATE INDEX IF NOT EXISTS who_committee_sections_ts_gin ON guidelines.who_committee_sections USING gin(ts);

CREATE OR REPLACE FUNCTION guidelines.who_committee_reports_tsv_update() RETURNS trigger AS $$
BEGIN
  NEW.ts := to_tsvector('english', coalesce(NEW.title,'')||' '||coalesce(NEW.doc_type,''));
  RETURN NEW;
END;$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION guidelines.who_committee_sections_tsv_update() RETURNS trigger AS $$
BEGIN
  NEW.ts := to_tsvector('english', coalesce(NEW.heading,'')||' '||coalesce(NEW.text,''));
  RETURN NEW;
END;$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_who_committee_reports_tsv ON guidelines.who_committee_reports;
CREATE TRIGGER trg_who_committee_reports_tsv
BEFORE INSERT OR UPDATE ON guidelines.who_committee_reports
FOR EACH ROW EXECUTE FUNCTION guidelines.who_committee_reports_tsv_update();

DROP TRIGGER IF EXISTS trg_who_committee_sections_tsv ON guidelines.who_committee_sections;
CREATE TRIGGER trg_who_committee_sections_tsv
BEFORE INSERT OR UPDATE ON guidelines.who_committee_sections
FOR EACH ROW EXECUTE FUNCTION guidelines.who_committee_sections_tsv_update();

