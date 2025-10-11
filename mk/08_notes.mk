# =========================
# 8) Notes (MIMIC-III & MIMIC-IV)
# =========================

# ---------- Defaults ----------
PSQL ?= psql -d 2ndopinionmd -v ON_ERROR_STOP=1
PY   ?= server/venv312/bin/python
REPORT_DIR ?= db_integrity_reports

HOURS ?= 48        # for backfill_mimiciv_notes_nearest()
MAP_HOURS ?= 168   # for map_mimiciv_notes_nearest_only()
AI ?=              # set AI=1 to enable AI box in PDF

# ---------- SQL file paths ----------
NOTES_MAP_SQL       ?= database/sql/notes_map_table.sql
NOTES_INDEXES_SQL   ?= database/sql/notes_indexes.sql
NOTES_FUNCS_SQL     ?= database/sql/notes_functions.sql

# ---------- Schema / loaders (already in your repo) ----------
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

# ---------- Our new: map table, indexes, functions ----------
notes-map-table:
	@$(PSQL) -f $(NOTES_MAP_SQL)

notes-indexes:
	@$(PSQL) -f $(NOTES_INDEXES_SQL)

notes-functions: notes-map-table
	@$(PSQL) -f $(NOTES_FUNCS_SQL)

# ---------- Backfills / mappings ----------
notes-backfill-window:
	@$(PSQL) -c "SELECT text.backfill_mimiciv_notes_within_window();"

notes-backfill-transfer:
	@$(PSQL) -c "SELECT text.backfill_mimiciv_notes_within_transfer();"

notes-backfill-nearest:
	@echo "Nearest window backfill with $(HOURS)h" 1>&2
	@$(PSQL) -c "SELECT text.backfill_mimiciv_notes_nearest($(HOURS));"

notes-map-nearest-only:
	@echo "Map-only nearest with $(MAP_HOURS)h" 1>&2
	@$(PSQL) -c "SELECT text.map_mimiciv_notes_nearest_only($(MAP_HOURS));"

# ---------- Audit ----------
notes-audit:
	@$(PSQL) -c "SELECT 'rows' AS what, COUNT(*) AS n FROM text.mimiciv_notes \
	              UNION ALL SELECT 'subjects', COUNT(DISTINCT subject_id) FROM text.mimiciv_notes \
	              UNION ALL SELECT 'hadm_null', COUNT(*) FROM text.mimiciv_notes WHERE hadm_id IS NULL \
	              UNION ALL SELECT 'hadm_nonnull', COUNT(*) FROM text.mimiciv_notes WHERE hadm_id IS NOT NULL;"
	@$(PSQL) -c "SELECT method, COUNT(*) AS mapped FROM text.mimiciv_notes_hadm_map GROUP BY 1 ORDER BY 1;"

# ---------- One-shot rollups ----------
notes-integrity-all: notes-map-table notes-indexes notes-functions \
                     notes-backfill-window notes-backfill-transfer \
                     notes-backfill-nearest notes-map-nearest-only \
                     notes-audit notes-report-pdf
	@echo "Wrote $(REPORT_DIR)/08_mimiciv_notes.pdf"

.PHONY: mimic3-notes-schema mimic3-notes-import mimiciv-note-schema mimiciv-note-import mimiciv-note-dry \
        notes-map-table notes-indexes notes-functions \
        notes-backfill-window notes-backfill-transfer notes-backfill-nearest notes-map-nearest-only \
        notes-audit notes-report-pdf notes-integrity-all
