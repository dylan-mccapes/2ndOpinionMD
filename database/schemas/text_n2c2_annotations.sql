-- database/schemas/text_n2c2_annotations.sql
CREATE SCHEMA IF NOT EXISTS text;

-- Generic standoff table that can hold BRAT and i2b2/n2c2 styles.
CREATE TABLE IF NOT EXISTS text.n2c2_annotations (
  ann_id      text PRIMARY KEY,                 -- e.g., T42, R3, A9 (keep original ids)
  note_id     text NOT NULL,                    -- matches text.n2c2_notes.note_id
  kind        text NOT NULL                     -- 'entity' | 'relation' | 'attribute'
             CHECK (kind IN ('entity','relation','attribute')),
  label       text,                              -- e.g., PROBLEM, TREATMENT, SDOH category, relation label
  span_start  integer,                           -- for entities; NULL for relations/attrs
  span_end    integer,                           -- for entities; NULL for relations/attrs
  span_text   text,                              -- optional original text for entities
  arg1        text,                              -- for relations: Arg1 id (e.g., T1)
  arg2        text,                              -- for relations: Arg2 id (e.g., T2)
  attr_target text,                              -- for attributes: target id (e.g., T1)
  attr_value  text,                              -- for attributes: boolean/value
  source_file text                               -- which .ann/.con file it came from
);

-- Helpful indexes
CREATE INDEX IF NOT EXISTS n2c2_ann_note_idx   ON text.n2c2_annotations (note_id);
CREATE INDEX IF NOT EXISTS n2c2_ann_kind_idx   ON text.n2c2_annotations (kind, label);
CREATE INDEX IF NOT EXISTS n2c2_ann_span_idx   ON text.n2c2_annotations (note_id, span_start, span_end)
  WHERE kind = 'entity';

