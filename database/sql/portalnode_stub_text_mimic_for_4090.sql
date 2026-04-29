-- 4090 / pilot MKG restore (run before 02_patient_substrate_schema.sql.gz).
-- Schema dump includes ehr.v_timeline_note_events, which references
-- text.mimiciv_notes_resolved. Full MIMIC text tables are not shipped in the pilot slice.
-- This empty stub satisfies CREATE VIEW; LEFT JOIN columns stay NULL without MIMIC data.

CREATE SCHEMA IF NOT EXISTS text;

CREATE TABLE IF NOT EXISTS text.mimiciv_notes_resolved (
    note_id text NOT NULL,
    domain text,
    note_text text
);

COMMENT ON TABLE text.mimiciv_notes_resolved IS 'Pilot stub: MIMIC text not in forward_pilot_dump; see portalnode4090_restore_mkg.sh.';
