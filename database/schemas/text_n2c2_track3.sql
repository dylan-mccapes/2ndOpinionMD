-- text_n2c2_track3.sql
-- Idempotent DDL for n2c2 Track 3 (Assessment & Plan) storage + views

CREATE SCHEMA IF NOT EXISTS text;

-- ---------------------------------------------------------------------------
-- NOTES (raw note text and metadata for any n2c2 track/source)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS text.n2c2_notes (
  note_id     BIGSERIAL PRIMARY KEY,
  track       TEXT NOT NULL DEFAULT '2022-T3',
  filename    TEXT,
  external_id TEXT,              -- e.g., MIMIC row_id or file UID
  subject_id  INTEGER,
  hadm_id     INTEGER,
  charttime   TIMESTAMP,
  note_text   TEXT
);

-- Bring older tables up to spec (safe on repeat runs)
ALTER TABLE text.n2c2_notes
  ADD COLUMN IF NOT EXISTS track       TEXT NOT NULL DEFAULT '2022-T3',
  ADD COLUMN IF NOT EXISTS filename    TEXT,
  ADD COLUMN IF NOT EXISTS external_id TEXT,
  ADD COLUMN IF NOT EXISTS subject_id  INTEGER,
  ADD COLUMN IF NOT EXISTS hadm_id     INTEGER,
  ADD COLUMN IF NOT EXISTS charttime   TIMESTAMP,
  ADD COLUMN IF NOT EXISTS note_text   TEXT;

-- Unique note identity within a track if external_id is present
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='text' AND indexname='n2c2_notes_track_external_id_uniq'
  ) THEN
    EXECUTE 'CREATE UNIQUE INDEX n2c2_notes_track_external_id_uniq
             ON text.n2c2_notes (track, external_id)
             WHERE external_id IS NOT NULL';
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS n2c2_notes_track_idx    ON text.n2c2_notes(track);
CREATE INDEX IF NOT EXISTS n2c2_notes_hadm_idx     ON text.n2c2_notes(hadm_id);
CREATE INDEX IF NOT EXISTS n2c2_notes_charttime_idx ON text.n2c2_notes(charttime);

-- ---------------------------------------------------------------------------
-- AP SECTIONS (spans into note_text)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS text.n2c2_ap_sections (
  section_id   BIGSERIAL PRIMARY KEY,
  note_id      BIGINT NOT NULL REFERENCES text.n2c2_notes(note_id) ON DELETE CASCADE,
  section_name TEXT    NOT NULL, -- 'ASSESSMENT' | 'PLAN_ITEM'
  span_start   INTEGER NOT NULL,
  span_end     INTEGER NOT NULL
);

-- keep duplicates out
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_indexes
    WHERE schemaname='text' AND indexname='n2c2_ap_sections_uniq'
  ) THEN
    EXECUTE 'CREATE UNIQUE INDEX n2c2_ap_sections_uniq
             ON text.n2c2_ap_sections (note_id, section_name, span_start, span_end)';
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS n2c2_ap_sections_note_idx ON text.n2c2_ap_sections(note_id);
CREATE INDEX IF NOT EXISTS n2c2_ap_sections_name_idx ON text.n2c2_ap_sections(section_name);

-- ---------------------------------------------------------------------------
-- AP RELATIONS (Assessment  Plan, labeled)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS text.n2c2_ap_relations (
  rel_id    BIGSERIAL PRIMARY KEY,
  note_id   BIGINT NOT NULL REFERENCES text.n2c2_notes(note_id) ON DELETE CASCADE,
  assess_id BIGINT NOT NULL REFERENCES text.n2c2_ap_sections(section_id) ON DELETE CASCADE,
  plan_id   BIGINT NOT NULL REFERENCES text.n2c2_ap_sections(section_id) ON DELETE CASCADE,
  label     TEXT   NOT NULL  -- 'Direct' | 'Indirect' | 'Neither' | 'Not Relevant'
);

CREATE INDEX IF NOT EXISTS n2c2_ap_relations_note_idx  ON text.n2c2_ap_relations(note_id);
CREATE INDEX IF NOT EXISTS n2c2_ap_relations_label_idx ON text.n2c2_ap_relations(label);

-- ---------------------------------------------------------------------------
-- VIEW: Flat A&P pairs with extracted snippets
-- Uses n.track (do NOT reference r.track; that column does not exist)
-- ---------------------------------------------------------------------------
CREATE OR REPLACE VIEW text.v_n2c2_ap_pairs AS
SELECT
  r.rel_id,
  n.track,
  r.label,
  -- Extract snippets from the raw note using recorded offsets
  substr(n.note_text, a.span_start + 1, a.span_end - a.span_start) AS assessment,
  substr(n.note_text, p.span_start + 1, p.span_end - p.span_start) AS plan_item,
  n.note_id,
  n.hadm_id,
  n.subject_id,
  n.charttime
FROM text.n2c2_ap_relations r
JOIN text.n2c2_ap_sections  a ON a.section_id = r.assess_id
JOIN text.n2c2_ap_sections  p ON p.section_id = r.plan_id
JOIN text.n2c2_notes        n ON n.note_id   = r.note_id;

-- Optional helper view for quick QA
-- Fix: rebuild counts view without ungrouped outer columns
DROP VIEW IF EXISTS text.v_n2c2_ap_counts;

CREATE VIEW text.v_n2c2_ap_counts AS
WITH rel_by_track AS (
  SELECT n.track, COUNT(*) AS relations_total
  FROM text.n2c2_ap_relations r
  JOIN text.n2c2_notes n ON n.note_id = r.note_id
  GROUP BY n.track
),
sections_by_track AS (
  SELECT n.track,
         COUNT(*) FILTER (WHERE s.section_name = 'ASSESSMENT') AS assessments,
         COUNT(*) FILTER (WHERE s.section_name = 'PLAN_ITEM')  AS plan_items
  FROM text.n2c2_notes n
  LEFT JOIN text.n2c2_ap_sections s ON s.note_id = n.note_id
  GROUP BY n.track
),
notes_by_track AS (
  SELECT track, COUNT(DISTINCT note_id) AS notes
  FROM text.n2c2_notes
  GROUP BY track
)
SELECT nt.track,
       nt.notes,
       st.assessments,
       st.plan_items,
       COALESCE(rt.relations_total, 0) AS relations_total,
       CASE WHEN nt.notes > 0
            THEN COALESCE(rt.relations_total, 0)::numeric / nt.notes
            ELSE 0 END AS relations_per_note_avg
FROM notes_by_track nt
LEFT JOIN sections_by_track st ON st.track = nt.track
LEFT JOIN rel_by_track     rt ON rt.track = nt.track;

