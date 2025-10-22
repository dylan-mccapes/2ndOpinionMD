# 11) ClinGen Gene–Disease Validity
# =========================

PY   ?= server/venv312/bin/python
PSQL ?= psql -d 2ndopinionmd -v ON_ERROR_STOP=1
FILE ?= data/clingen/validity.ndjson

clingen-validity-schema:
	@$(PSQL) -f database/schemas/molecular_clingen_validity.sql

# Usage: make clingen-validity-import [FILE=data/clingen/validity.ndjson]
clingen-validity-import: clingen-validity-schema
	@test -n "$(FILE)" || (echo "Set FILE=path/to/ClinGen validity NDJSON"; exit 1)
	@$(PY) server/scripts/ingest_clingen_validity.py --file "$(FILE)"

clingen-validity-smoke:
	@$(PSQL) -c "SELECT COUNT(*) AS rows FROM molecular.clingen_validity;"
	@$(PSQL) -c "SELECT classification, COUNT(*) AS n FROM molecular.clingen_validity GROUP BY 1 ORDER BY 2 DESC NULLS LAST LIMIT 10;"
	@$(PSQL) -c "SELECT * FROM molecular.v_clingen_validity_core LIMIT 5;"

# The PDF rule itself lives in mk/90_reports.mk as 'clingen-validity-report-pdf'
clingen-validity-integrity-all: clingen-validity-smoke clingen-validity-report-pdf

.PHONY: clingen-validity-schema clingen-validity-import clingen-validity-smoke clingen-validity-integrity-all

# ---------- 11.A) ClinGen Actionability (Adult/Pediatric summaries) ----------
CLINGEN_DIR ?= data/clingen
ADULT_TSV   ?= $(CLINGEN_DIR)/actionability_adult.tsv
PED_TSV     ?= $(CLINGEN_DIR)/actionability_pediatric.tsv

clingen-actionability-fetch:
	@mkdir -p $(CLINGEN_DIR)
	@wget -q -O $(ADULT_TSV) 'https://actionability.clinicalgenome.org/ac/Adult/api/summ?format=tsv' && echo "Fetched Adult summary -> $(ADULT_TSV)"
	@wget -q -O $(PED_TSV)   'https://actionability.clinicalgenome.org/ac/Pediatric/api/summ?format=tsv' && echo "Fetched Pediatric summary -> $(PED_TSV)"

clingen-actionability-schema:
	@$(PSQL) -f database/schemas/clingen_actionability.sql

clingen-actionability-import: clingen-actionability-schema
	@$(PY) server/scripts/ingest_clingen_actionability.py $(ADULT_TSV) $(PED_TSV)

clingen-actionability-smoke:
	@$(PSQL) -c "SELECT cohort, COUNT(*) AS n FROM clingen.actionability_summary GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -c "SELECT gene_symbol, actionability_assertion, report_date FROM clingen.actionability_summary ORDER BY report_date DESC NULLS LAST LIMIT 10;"
	@$(PSQL) -c "SELECT COUNT(*) AS quick_rows FROM clingen.v_actionability_quick;"

clingen-actionability-all: clingen-actionability-fetch clingen-actionability-import clingen-actionability-smoke

.PHONY: clingen-actionability-fetch clingen-actionability-schema clingen-actionability-import clingen-actionability-smoke clingen-actionability-all

# ---------- 11.B) ClinGen ACI assertion/scores ----------
ACI_DIR      ?= data/clingen
ACI_ADULT    ?= $(ACI_DIR)/ACI-assertion-adult.tsv
ACI_PED      ?= $(ACI_DIR)/ACI-assertion-pediatric.tsv

clingen-aci-schema:
	@$(PSQL) -f database/schemas/clingen_aci.sql

clingen-aci-import: clingen-aci-schema
	@$(PY) server/scripts/ingest_clingen_aci.py $(ACI_ADULT) $(ACI_PED)

clingen-aci-smoke:
	@$(PSQL) -c "SELECT cohort, COUNT(*) AS n FROM clingen.actionability_assertions GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -c "SELECT cohort, gene_symbol, domain, score, report_date FROM clingen.v_actionability_latest ORDER BY report_date DESC NULLS LAST LIMIT 10;"

clingen-aci-all: clingen-aci-import clingen-aci-smoke

# ---------- 11.C) ClinGen Variant classifications ----------
VAR_TXT ?= $(CLINGEN_DIR)/variants.txt

clingen-variants-schema:
	@$(PSQL) -f database/schemas/clingen_variants.sql

clingen-variants-import: clingen-variants-schema
	@$(PY) server/scripts/ingest_clingen_variants.py $(VAR_TXT)

clingen-variants-smoke:
	@$(PSQL) -c "SELECT COUNT(*) AS n, COUNT(gene_symbol) AS with_gene FROM clingen.variant_classifications;"
	@$(PSQL) -c "SELECT gene_symbol, classification, last_evaluated FROM clingen.variant_classifications WHERE gene_symbol IS NOT NULL LIMIT 10;"

clingen-variants-all: clingen-variants-import clingen-variants-smoke


