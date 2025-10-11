# =========================
# 10) ClinVar  / 11) ClinGen Validity
# =========================

PY   ?= server/venv312/bin/python
PSQL ?= psql -d 2ndopinionmd -v ON_ERROR_STOP=1
REPORTS_DIR ?= db_integrity_reports
CLINVAR_FILE ?= data/clinvar/variant_summary.txt.gz

# ---- ClinVar schema / load / views / indexes ----
clinvar-schema:
	@$(PSQL) -f database/schemas/molecular_clinvar.sql

clinvar-import: clinvar-schema
	@echo "Loading $(CLINVAR_FILE)"
	@$(PY) server/scripts/ingest_clinvar_variant_summary.py --file "$(CLINVAR_FILE)"

clinvar-views:
	@$(PSQL) -f database/sql/clinvar_views.sql

clinvar-indexes:
	@$(PSQL) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS clinvar_signif_idx ON molecular.clinvar_summary (clinicalsignificance);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS clinvar_gene_idx   ON molecular.clinvar_summary (genesymbol);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS clinvar_rcv_idx    ON molecular.clinvar_summary (rcvaccession);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS clinvar_gene_sig_idx ON molecular.clinvar_summary (genesymbol, clinicalsignificance);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS clinvar_phenotype_trgm ON molecular.clinvar_summary USING gin (phenotypelist gin_trgm_ops);"

clinvar-smoke:
	@$(PSQL) -c "SELECT COUNT(*) AS rows, MIN(source_version) AS ver_min, MAX(source_version) AS ver_max FROM molecular.clinvar_summary;"
	@$(PSQL) -c "SELECT * FROM molecular.v_clinvar_significance LIMIT 10;"
	@$(PSQL) -c "SELECT * FROM molecular.v_clinvar_by_gene LIMIT 10;"

# Optional: create/refresh focused subsets
clinvar-focus:
	@$(PSQL) -c "DROP TABLE IF EXISTS molecular.clinvar_focus;"
	@$(PSQL) -c "CREATE TABLE molecular.clinvar_focus AS \
		SELECT * FROM molecular.v_clinvar_core \
		WHERE phenotypelist ILIKE ANY (ARRAY['%multiple sclerosis%','%amyotrophic lateral sclerosis%','%huntington%','%parkinson%']);"
	@$(PSQL) -c "ANALYZE molecular.clinvar_focus;"

clinvar-integrity-all: clinvar-import clinvar-views clinvar-indexes clinvar-smoke clinvar-report-pdf
	@echo "ClinVar integrity complete."

# ---- ClinGen (placeholder) ----
clingen-validity-import:
	@echo "TODO: add ClinGen gene–disease validity loader"; exit 0
clingen-validity-smoke:
	@echo "TODO: add ClinGen validity smoke"; exit 0

.PHONY: clinvar-schema clinvar-import clinvar-views clinvar-indexes clinvar-smoke clinvar-report-pdf clinvar-focus clinvar-integrity-all clingen-validity-import clingen-validity-smoke
