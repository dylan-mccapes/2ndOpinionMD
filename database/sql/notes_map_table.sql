-- Creates the mapping table used by all backfills (idempotent).
CREATE SCHEMA IF NOT EXISTS text;

CREATE TABLE IF NOT EXISTS text.mimiciv_notes_hadm_map (
  note_id    text,
  hadm_id    bigint,
  method     text,
  dt_seconds integer,
  PRIMARY KEY (note_id, method)
);

