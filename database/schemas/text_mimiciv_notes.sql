-- database/schemas/text_mimiciv_notes.sql
CREATE SCHEMA IF NOT EXISTS text;

CREATE TABLE IF NOT EXISTS text.mimiciv_notes (
  note_id    TEXT PRIMARY KEY,
  domain     TEXT NOT NULL,        -- 'discharge' | 'radiology'
  subject_id INTEGER,
  hadm_id    INTEGER,
  charttime  TIMESTAMP NULL,
  note_text  TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS mimiciv_notes_subject_idx   ON text.mimiciv_notes(subject_id);
CREATE INDEX IF NOT EXISTS mimiciv_notes_hadm_idx      ON text.mimiciv_notes(hadm_id);
CREATE INDEX IF NOT EXISTS mimiciv_notes_charttime_idx ON text.mimiciv_notes(charttime);
CREATE INDEX IF NOT EXISTS mimiciv_notes_domain_idx    ON text.mimiciv_notes(domain);

CREATE OR REPLACE VIEW text.v_mimiciv_progress_notes AS
SELECT
  note_id     AS ext_note_id,
  subject_id,
  hadm_id,
  charttime,
  domain      AS category,
  note_text
FROM text.mimiciv_notes
WHERE note_text IS NOT NULL AND length(note_text) > 200;

