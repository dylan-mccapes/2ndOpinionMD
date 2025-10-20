# =========================
# 16) GWAS Catalog (autoimmune)
# =========================
GWAS_DIR       ?= data/gwas
GWAS_ALL_TSV   ?= $(GWAS_DIR)/gwas_catalog.tsv
GWAS_AUTO_TSV  ?= $(GWAS_DIR)/gwas_autoimmune.tsv
GWAS_URL       ?= https://www.ebi.ac.uk/gwas/api/search/downloads/alternative
GWAS_KEYWORDS  ?= multiple sclerosis|spondyloarthritis|ankylosing spondylitis|psoriatic arthritis|autoimmune

gwas-schema:
	@$(PSQL) -f database/schemas/molecular_gwas_schema.sql

gwas-download:
	@mkdir -p $(GWAS_DIR)
	@curl -fsSL "$(GWAS_URL)" -o "$(GWAS_ALL_TSV)"
	@ls -lh "$(GWAS_ALL_TSV)"

gwas-filter-autoimmune:
	@head -n 1 "$(GWAS_ALL_TSV)" > "$(GWAS_AUTO_TSV)"
	@tail -n +2 "$(GWAS_ALL_TSV)" | awk 'BEGIN{IGNORECASE=1} $$0 ~ /($(GWAS_KEYWORDS))/ {print}' >> "$(GWAS_AUTO_TSV)"
	@wc -l "$(GWAS_AUTO_TSV)"

gwas-import:
	@SYNC_DATABASE_URL="$$SYNC_DATABASE_URL" GWAS_TSV="$(GWAS_AUTO_TSV)" $(PY) server/scripts/ingest_gwas_catalog.py

gwas-indexes:
	@$(PSQL) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gwas_trait_trgm   ON molecular.gwas_hits USING gin (disease_trait gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gwas_mapped_trait ON molecular.gwas_hits USING gin (mapped_trait gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gwas_snps_idx     ON molecular.gwas_hits (snps);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gwas_pval_idx     ON molecular.gwas_hits (p_value);"

gwas-smoke:
	@$(PSQL) -c "SELECT COUNT(*) AS rows, MIN(p_value) AS best_p FROM molecular.gwas_hits;"
	@$(PSQL) -c "SELECT disease_trait, COUNT(*) n FROM molecular.gwas_hits GROUP BY 1 ORDER BY n DESC LIMIT 10;"

gwas-rag-upsert:
	@SYNC_DATABASE_URL="$$SYNC_DATABASE_URL" $(PY) server/scripts/gwas_rag_upsert.py $(if $(SINCE),--since $(SINCE),)

gwas-embed:
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus --id-col id --text-col text --embedding-col embedding \
	  --model text-embedding-3-small --batch 256 \
	  --where "source='gwas' AND embedding IS NULL"

gwas-rag: gwas-rag-upsert gwas-embed

gwas-api-smoke:
	@curl -s "$(API_BASE)/api/gwas/stats" | jq .

gwas-audit-sql:
	@$(PSQL) -f database/sql/16_gwas_audit.sql -tA | jq .

# optional: beefier FTS index (generated column)
gwas-add-indexes:
	@$(PSQL) -c "ALTER TABLE molecular.gwas_hits \
	  ADD COLUMN IF NOT EXISTS fts tsvector \
	  GENERATED ALWAYS AS (to_tsvector('english', \
	    coalesce(disease_trait,'') || ' ' || coalesce(mapped_trait,'') || ' ' || \
	    coalesce(reported_genes,'') || ' ' || coalesce(mapped_gene,''))) STORED;"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gwas_fts_gin ON molecular.gwas_hits USING gin (fts);"
