# =========================
# 9) n2c2 / i2b2 corpora
# =========================

# --- Tooling ---
PY   ?= server/venv312/bin/python
# psql works with your normal SYNC_DATABASE_URL (no +asyncpg)
PSQL ?= psql "$(SYNC_DATABASE_URL)"

REPORTS_DIR    ?= db_integrity_reports
N2C2_REPORT    ?= $(REPORTS_DIR)/09_n2c2.pdf

# Data roots (adjust if your layout differs)
N2C2_BASE      ?= data/n2c2
N2C2_T3_BASE   ?= $(N2C2_BASE)/2022/track3
N2C2_SAMPLE    ?= $(N2C2_BASE)/track3-sample

# Some python scripts use psycopg2 directly and choke on "+asyncpg".
# This ensures they see a psycopg-friendly DSN.
AP_ENV = SYNC_DATABASE_URL="$$(echo "$$SYNC_DATABASE_URL" | sed 's/+asyncpg//')"

.PHONY: \
 n2c2-schema n2c2-ann-schema n2c2-ann-import-brat \
 n2c2-t3-sample-schema n2c2-t3-sample-import n2c2-t3-sample-qa \
 n2c2-ap-extract-m3 n2c2-ap-extract-miv n2c2-ap-qa \
 n2c2-export-silver-m3 n2c2-export-silver-miv \
 n2c2-verify-all n2c2-report-pdf n2c2-integrity-all reports-dir

# -----------------------
# Schemas & sample import
# -----------------------
n2c2-schema:
	@$(PSQL) -v ON_ERROR_STOP=1 -f database/schemas/text_n2c2_track3.sql

# Optional: annotations schema (BRAT .ann ingestion)
n2c2-ann-schema:
	@$(PSQL) -v ON_ERROR_STOP=1 -f database/schemas/text_n2c2_annotations.sql

# If you have BRAT-style .ann files under $(N2C2_T3_BASE), load them
n2c2-ann-import-brat: n2c2-ann-schema
	@echo "✅ Importing BRAT annotations from $(N2C2_T3_BASE) (if any)..."
	@$(AP_ENV) $(PY) server/scripts/ingest_n2c2_annotations_brat.py --base "$(N2C2_T3_BASE)" || true
	@echo "✅ Annotations import complete."

# Sample data helper (from the public GitLab repo)
n2c2-t3-sample-schema: n2c2-schema
	@true

n2c2-t3-sample-import: n2c2-t3-sample-schema
	@$(AP_ENV) $(PY) server/scripts/ingest_n2c2_t3_sample.py --base "$(N2C2_SAMPLE)"

n2c2-t3-sample-qa:
	@$(PSQL) -c "SELECT COUNT(*) AS notes FROM text.n2c2_notes WHERE track='2022-T3';"
	@$(PSQL) -c "SELECT section_name, COUNT(*) FROM text.n2c2_ap_sections GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -c "SELECT label, COUNT(*) FROM text.n2c2_ap_relations GROUP BY 1 ORDER BY 2 DESC;"

# -----------------------
# Silver A&P pair creation
# -----------------------
# From MIMIC-III notes
n2c2-ap-extract-m3: n2c2-schema
	@$(AP_ENV) $(PY) server/scripts/extract_ap_pairs_from_mimic.py --source m3 --limit $${LIMIT:-20000} --track MIII-AP

# From MIMIC-IV (domain=discharge by default; tweak if desired)
n2c2-ap-extract-miv: n2c2-schema
	@$(AP_ENV) $(PY) server/scripts/extract_ap_pairs_from_mimic.py --source miv --domain discharge --limit $${LIMIT:-20000} --track MIV-AP

n2c2-ap-qa:
	@$(PSQL) -c "SELECT track, COUNT(*) AS notes FROM text.n2c2_notes GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -c "SELECT s.section_name, COUNT(*) FROM text.n2c2_ap_sections s GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -c "SELECT n.track, COUNT(*) AS rels FROM text.n2c2_ap_relations r JOIN text.n2c2_notes n USING (note_id) GROUP BY 1 ORDER BY 1;"

n2c2-export-silver-m3:
	@$(PSQL) -c "\copy (SELECT * FROM text.v_n2c2_ap_pairs WHERE track='MIII-AP') TO 'data/n2c2/train_silver_m3.csv' CSV HEADER"

n2c2-export-silver-miv:
	@$(PSQL) -c "\copy (SELECT * FROM text.v_n2c2_ap_pairs WHERE track='MIV-AP') TO 'data/n2c2/train_silver_miv.csv' CSV HEADER"

# ---------------
# Verification & report
# ---------------
n2c2-verify-all:
	@$(PSQL) -v ON_ERROR_STOP=1 -c "\
	  SELECT (to_regclass('text.n2c2_notes') IS NOT NULL)  AS has_notes,\
	         (to_regclass('text.n2c2_annotations') IS NOT NULL) AS has_annotations;"
	@$(PSQL) -v ON_ERROR_STOP=1 -c "\
	  SELECT 'notes' AS what, COUNT(*)::bigint AS n FROM text.n2c2_notes;"
	@$(PSQL) -v ON_ERROR_STOP=1 -c "\
	  SELECT track, split, COUNT(*)::bigint AS notes,\
	         SUM(length(coalesce(note_text,'')))::bigint AS total_chars\
	  FROM text.n2c2_notes GROUP BY 1,2 ORDER BY 1,2;"
	@# If you created the verification file, this will print orphan/span QC notices:
	@$(PSQL) -v ON_ERROR_STOP=1 -f database/sql/n2c2_verify_annotations.sql || true

# One-button orchestration (schema -> optional ann import -> verify -> PDF)
n2c2-integrity-all: n2c2-schema n2c2-ann-schema n2c2-ann-import-brat n2c2-verify-all n2c2-report-pdf
	@echo "Wrote $(N2C2_REPORT)"
