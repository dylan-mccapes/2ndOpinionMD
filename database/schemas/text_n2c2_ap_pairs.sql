-- text_n2c2_track3.sql  (idempotent)
CREATE SCHEMA IF NOT EXISTS text;

CREATE TABLE IF NOT EXISTS text.n2c2_notes (
  note_id       BIGSERIAL PRIMARY KEY,
  dataset       TEXT NOT NULL DEFAULT 'n2c2',
  track         TEXT NOT NULL,           -- e.g., '2022-T3'
  split         TEXT NOT NULL,           -- train|dev|test|sample
  source_system TEXT,
  external_id   TEXT,
  filename      TEXT,
  note_text     TEXT NOT NULL,
  char_count    INT GENERATED ALWAYS AS (length(note_text)) STORED,
  loaded_at     TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE IF NOT EXISTS text.n2c2_ap_sections (
  section_id   BIGSERIAL PRIMARY KEY,
  note_id      BIGINT NOT NULL REFERENCES text.n2c2_notes(note_id) ON DELETE CASCADE,
  section_name TEXT NOT NULL,            -- 'ASSESSMENT' | 'PLAN_ITEM'
  span_start   INT NOT NULL,
  span_end     INT NOT NULL,
  text         TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS text.n2c2_ap_relations (
  rel_id     BIGSERIAL PRIMARY KEY,
  note_id    BIGINT NOT NULL REFERENCES text.n2c2_notes(note_id) ON DELETE CASCADE,
  assess_id  BIGINT NOT NULL REFERENCES text.n2c2_ap_sections(section_id) ON DELETE CASCADE,
  plan_id    BIGINT NOT NULL REFERENCES text.n2c2_ap_sections(section_id) ON DELETE CASCADE,
  label      TEXT NOT NULL,              -- Direct|Indirect|Neither|Not Relevant
  loaded_at  TIMESTAMPTZ DEFAULT now()
);

-- Helpful indexes + uniqueness to prevent dup inserts on re-runs
CREATE INDEX IF NOT EXISTS n2c2_ap_sections_note_span_idx
  ON text.n2c2_ap_sections(note_id, section_name, span_start, span_end);
CREATE INDEX IF NOT EXISTS n2c2_ap_rel_note_idx
  ON text.n2c2_ap_relations(note_id);

CREATE UNIQUE INDEX IF NOT EXISTS n2c2_ap_sections_uniq
  ON text.n2c2_ap_sections(note_id, section_name, span_start, span_end);
CREATE UNIQUE INDEX IF NOT EXISTS n2c2_ap_rel_uniq
  ON text.n2c2_ap_relations(note_id, assess_id, plan_id, label);

