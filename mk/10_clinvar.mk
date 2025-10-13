# =========================
# 10) ClinVar
# =========================

PY   ?= server/venv312/bin/python
PSQL ?= psql -d 2ndopinionmd -v ON_ERROR_STOP=1
FILE ?= data/clinvar/variant_summary.txt.gz

clinvar-schema:
	@$(PSQL) -f database/schemas/molecular_clinvar.sql

clinvar-views:
	@$(PSQL) -f database/sql/clinvar_views.sql

# Usage: make clinvar-import [FILE=data/clinvar/variant_summary.txt.gz]
clinvar-import: clinvar-schema
	@echo "Loading $(FILE)"
	@$(PY) server/scripts/ingest_clinvar_variant_summary.py --file "$(FILE)"

clinvar-indexes:
	@$(PSQL) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS clinvar_signif_idx       ON molecular.clinvar_summary (clinicalsignificance);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS clinvar_gene_idx         ON molecular.clinvar_summary (genesymbol);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS clinvar_rcv_idx          ON molecular.clinvar_summary (rcvaccession);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS clinvar_gene_sig_idx     ON molecular.clinvar_summary (genesymbol, clinicalsignificance);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS clinvar_phenotype_trgm   ON molecular.clinvar_summary USING gin (phenotypelist gin_trgm_ops);"

clinvar-smoke:
	@$(PSQL) -c "SELECT COUNT(*) AS rows, MIN(source_version) AS ver_min, MAX(source_version) AS ver_max FROM molecular.clinvar_summary;"
	@$(PSQL) -c "SELECT * FROM molecular.v_clinvar_significance LIMIT 10;"
	@$(PSQL) -c "SELECT * FROM molecular.v_clinvar_by_gene LIMIT 10;"

# The PDF rule itself lives in mk/90_reports.mk as 'clinvar-report-pdf'
clinvar-integrity-all: clinvar-import clinvar-views clinvar-indexes clinvar-smoke clinvar-report-pdf

.PHONY: clinvar-schema clinvar-import clinvar-views clinvar-indexes clinvar-smoke clinvar-integrity-all
