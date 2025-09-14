-- database/schemas/text_mimiciv_notes.sql

CREATE SCHEMA IF NOT EXISTS text;

-- Unified notes table for MIMIC-IV-Note (discharge + radiology)
CREATE TABLE IF NOT EXISTS text.mimiciv_notes (
  note_id    TEXT PRIMARY KEY,     -- from CSV
  domain     TEXT NOT NULL,        -- 'discharge' | 'radiology' (or other)
  subject_id INTEGER,
  hadm_id    INTEGER,
  study_id   INTEGER,              -- present for radiology
  charttime  TIMESTAMP NULL,
  note_text  TEXT NOT NULL
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS mimiciv_notes_subject_idx   ON text.mimiciv_notes(subject_id);
CREATE INDEX IF NOT EXISTS mimiciv_notes_hadm_idx      ON text.mimiciv_notes(hadm_id);
CREATE INDEX IF NOT EXISTS mimiciv_notes_charttime_idx ON text.mimiciv_notes(charttime);
CREATE INDEX IF NOT EXISTS mimiciv_notes_domain_idx    ON text.mimiciv_notes(domain);

-- Optional: full-text search (comment out if you don't want it)
-- CREATE EXTENSION IF NOT EXISTS unaccent;
-- CREATE INDEX IF NOT EXISTS mimiciv_notes_fts_idx
--   ON text.mimiciv_notes USING GIN (to_tsvector('english', unaccent(note_text)));

-- View the extractor reads (aliased "category" for compatibility)
CREATE OR REPLACE VIEW text.v_mimiciv_progress_notes AS
SELECT
  note_id AS ext_note_id,
  subject_id,
  hadm_id,
  charttime,
  COALESCE(domain,'Unknown') AS category,
  note_text
FROM text.mimiciv_notes
WHERE note_text IS NOT NULL
  AND length(note_text) > 200
  AND lower(COALESCE(domain,'')) IN ('discharge','radiology');

