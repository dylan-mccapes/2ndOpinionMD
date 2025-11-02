-- Helpful indexes for joinability + search (all idempotent)

-- Notes table basics
CREATE INDEX IF NOT EXISTS mimiciv_notes_subject_idx        ON text.mimiciv_notes(subject_id);
CREATE INDEX IF NOT EXISTS mimiciv_notes_hadm_idx           ON text.mimiciv_notes(hadm_id);
CREATE INDEX IF NOT EXISTS mimiciv_notes_charttime_idx      ON text.mimiciv_notes(charttime);
CREATE INDEX IF NOT EXISTS mimiciv_notes_charttime_brin     ON text.mimiciv_notes USING brin (charttime) WITH (pages_per_range=32);
CREATE INDEX IF NOT EXISTS mimiciv_notes_subject_chartdate_idx ON text.mimiciv_notes(subject_id, DATE(charttime));

-- Admissions / Transfers for temporal matching
CREATE INDEX IF NOT EXISTS mimiciv_admissions_subject_time_idx ON ehr_mimic4.admissions(subject_id, admittime, dischtime);
CREATE INDEX IF NOT EXISTS transfers_subject_time_idx          ON ehr_mimic4.transfers(subject_id, intime, outtime);

-- Full-text / fuzzy search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS mimiciv_notes_note_text_trgm ON text.mimiciv_notes USING gin (note_text gin_trgm_ops);

ALTER TABLE text.mimiciv_notes
  ADD COLUMN IF NOT EXISTS ts tsvector;

-- Only compute ts for rows missing it (long tokens are fine to skip)
UPDATE text.mimiciv_notes
   SET ts = to_tsvector('english', coalesce(note_text,''))
 WHERE ts IS NULL;

CREATE INDEX IF NOT EXISTS mimiciv_notes_ts_idx ON text.mimiciv_notes USING gin (ts);

