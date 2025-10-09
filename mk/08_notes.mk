# =========================
# 8) Notes (MIMIC-III & MIMIC-IV)
# =========================
mimic3-notes-schema:
	@$(PSQL) -c "\
		CREATE SCHEMA IF NOT EXISTS text; \
		CREATE TABLE IF NOT EXISTS text.mimic3_notes ( \
		row_id INTEGER PRIMARY KEY, subject_id INTEGER, hadm_id INTEGER, \
		chartdate DATE, charttime TIMESTAMP, storetime TIMESTAMP, \
		category TEXT, description TEXT, cgid INTEGER, iserror TEXT, text TEXT); \
		CREATE INDEX IF NOT EXISTS mimic3_notes_hadm_idx    ON text.mimic3_notes(hadm_id); \
		CREATE INDEX IF NOT EXISTS mimic3_notes_subject_idx ON text.mimic3_notes(subject_id);"

mimic3-notes-import: mimic3-notes-schema
	@$(PSQL) -c "\
\copy text.mimic3_notes (row_id,subject_id,hadm_id,chartdate,charttime,storetime,category,description,cgid,iserror,text) \
FROM PROGRAM 'gzip -dc physionet.org/files/mimiciii/1.4/NOTEEVENTS.csv.gz' WITH (FORMAT csv, HEADER true)"

mimiciv-note-schema:
	@$(PSQL) -f database/schemas/text_mimiciv_notes.sql

mimiciv-note-import: mimiciv-note-schema
	@$(PY) server/scripts/ingest_mimiciv_notes.py --dir "physionet.org/files/mimic-iv-note/2.2"

mimiciv-note-dry: mimiciv-note-schema
	@$(PY) server/scripts/ingest_mimiciv_notes.py --dir "physionet.org/files/mimic-iv-note/2.2" --limit 500

mimiciv-note-stats:
	@$(PSQL) -c "SELECT domain, COUNT(*) AS n FROM text.mimiciv_notes GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -c "SELECT SUM((hadm_id IS NOT NULL AND a.hadm_id IS NULL)::int) AS hadm_not_in_admissions, SUM((hadm_id IS NULL)::int) AS hadm_null FROM text.mimiciv_notes n LEFT JOIN ehr_mimic4.admissions a USING (hadm_id);"

