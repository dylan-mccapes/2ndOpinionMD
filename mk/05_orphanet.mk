# =========================
# 5) Orphanet / Orphadata
# =========================
orphanet-import:
	@$(PY) server/scripts/ingest_orphanet.py $(if $(ZIP),--zip $(ZIP),) $(if $(DIR),--dir $(DIR),)

orphanet-indexes:
	@$(PSQL) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS orphanet_dis_name_trgm ON ontology.orphanet_diseases USING gin (name gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS orphanet_syn_syn_trgm ON ontology.orphanet_synonyms USING gin (synonym gin_trgm_ops);"
	@$(PSQL) -f database/sql/add_orphanet_indexes.sql

api-orphanet-search:
	@curl -s "$(API_BASE)/api/orphanet/search?q=$(Q)&limit=$(LIMIT)" | jq .

api-orphanet-disease:
	@curl -s "$(API_BASE)/api/orphanet/disease/$(ORPHA)" | jq .

api-orphanet-stats:
	@curl -s "$(API_BASE)/api/orphanet/stats" | jq .

# ---------- Paths / helpers ----------
REPORT_DIR ?= db_integrity_reports
PY        ?= server/venv312/bin/python
PSQL      ?= psql -d 2ndopinionmd -v ON_ERROR_STOP=1

# Optional fetch (you can pass ZIP= or DIR= to orphanet-import already)
# Example: make orphanet-fetch ZIP_URL=https://www.orphadata.com/data/xml/en_product1.xml.zip
orphanet-fetch:
	@test -n "$(ZIP_URL)" || (echo "Set ZIP_URL=https://.../orphanet_latest.zip"; exit 1)
	@mkdir -p data/orphanet
	@curl -fL "$(ZIP_URL)" -o data/orphanet/orphanet_latest.zip
	@echo "Downloaded → data/orphanet/orphanet_latest.zip"

# ---------- Core audits ----------
ORPHANET_DIR ?= data/Orphadata
ORPHANET_DDL ?= database/sql/ddl_orphanet.sql

orphanet-audit:
	@$(PSQL) -c "SELECT 'diseases' AS what, COUNT(*) AS n FROM ontology.orphanet_diseases \
		UNION ALL SELECT 'synonyms', COUNT(*) FROM ontology.orphanet_synonyms \
		UNION ALL SELECT 'external_refs', COUNT(*) FROM ontology.orphanet_external_refs \
		UNION ALL SELECT 'gene_links', COUNT(*) FROM ontology.orphanet_gene_links \
		UNION ALL SELECT 'phenotype_links', COUNT(*) FROM ontology.orphanet_phenotype_links \
		UNION ALL SELECT 'hpo_links_view', COUNT(*) FROM ontology.orphanet_hpo_links;"
	@$(PSQL) -c "SELECT 'gene_orphans' AS what, COUNT(*) AS n \
		FROM ontology.orphanet_gene_links g \
		LEFT JOIN ontology.orphanet_diseases d ON d.orpha_code=g.orpha_code \
		WHERE d.orpha_code IS NULL;"
	@$(PSQL) -c "SELECT 'phenotype_orphans' AS what, COUNT(*) AS n \
		FROM ontology.orphanet_phenotype_links p \
		LEFT JOIN ontology.orphanet_diseases d ON d.orpha_code=p.orpha_code \
		WHERE d.orpha_code IS NULL;"

# ---------- Snapshots (TSV) ----------
orphanet-snapshots:
	@echo "Writing Orphanet snapshots to snapshots/"
	@mkdir -p snapshots
	@$(PSQL) -A -F $$'\t' -c "COPY (SELECT orpha, name, disorder_type, prevalence FROM ontology.orphanet_diseases ORDER BY orpha) TO STDOUT" > snapshots/orphanet_diseases.tsv
	@$(PSQL) -A -F $$'\t' -c "COPY (SELECT orpha, synonym FROM ontology.orphanet_synonyms ORDER BY orpha, synonym) TO STDOUT" > snapshots/orphanet_synonyms.tsv
	@$(PSQL) -A -F $$'\t' -c "COPY (SELECT orpha, gene_symbol, gene_ncbi_id FROM ontology.orphanet_gene_links ORDER BY orpha, gene_symbol) TO STDOUT" > snapshots/orphanet_gene_links.tsv
	@$(PSQL) -A -F $$'\t' -c "COPY (SELECT orpha, hpo_id FROM ontology.orphanet_phenotype_links ORDER BY orpha, hpo_id) TO STDOUT" > snapshots/orphanet_phenotype_links.tsv
	@echo "Orphanet snapshots written."

# ---------- Integrity PDF ----------
orphanet-report-pdf:
	@$(PY) server/scripts/report_orphanet_pdf.py --out db_integrity_reports/05_orphanet.pdf $(if $(AI),--ai,)

# Rollup helpers
orphanet-integrity: orphanet-audit orphanet-snapshots
orphanet-integrity-all: orphanet-audit orphanet-report-pdf

.PHONY: orphanet-fetch orphanet-audit orphanet-snapshots orphanet-report-pdf orphanet-integrity orphanet-integrity-all
