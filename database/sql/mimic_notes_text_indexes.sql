-- database/sql/mimic_notes_text_indexes.sql
-- BM25/TS for MIMIC-III/IV note text so lexical matches are fast.

-- MIMIC-IV notes (your table already has tsv/ts columns; fill + index them)
UPDATE text.mimiciv_notes
SET tsv = to_tsvector('english', coalesce(note_text,'')),
    ts  = to_tsvector('simple',  coalesce(note_text,''))
WHERE (tsv IS NULL OR ts IS NULL);

CREATE INDEX IF NOT EXISTS mimiciv_notes_tsv_idx
  ON text.mimiciv_notes USING GIN (tsv);

CREATE INDEX IF NOT EXISTS mimiciv_notes_ts_idx
  ON text.mimiciv_notes USING GIN (ts);

-- Optional: MIMIC-III notes if present (same pattern)
-- UPDATE text.mimic3_notes SET tsv = to_tsvector('english', coalesce(text,'')) WHERE tsv IS NULL;
-- CREATE INDEX IF NOT EXISTS mimic3_notes_tsv_idx ON text.mimic3_notes USING GIN (tsv);

