# =========================
# 5) Orphanet / Orphadata
# =========================

# ---------- Paths / helpers ----------
REPORT_DIR ?= db_integrity_reports
PY        ?= server/venv312/bin/python
PSQL      ?= psql -d 2ndopinionmd -v ON_ERROR_STOP=1

# Prefer SYNC_DATABASE_URL when set; otherwise fall back to local DSN.
DB := $(if $(SYNC_DATABASE_URL),$(SYNC_DATABASE_URL),postgresql://2ndopinionmd@localhost:5432/2ndopinionmd)

# Embedding defaults (overridable: BATCH=, CONC= when invoking make)
BATCH ?= 256
CONC  ?= 6

# ======================
# Ingestion & Indexing
# ======================
orphanet-ddl:
	@$(PSQL) -f database/sql/ddl_orphanet.sql

orphanet-import:
	@$(PY) server/scripts/ingest_orphanet.py $(if $(ZIP),--zip $(ZIP),) $(if $(DIR),--dir $(DIR),)

# TRGM/GIN indexes (keep canonical + legacy names to avoid drift)
orphanet-indexes:
	@$(PSQL) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS orphanet_diseases_name_trgm ON ontology.orphanet_diseases USING gin (name gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS orphanet_synonyms_syn_trgm ON ontology.orphanet_synonyms USING gin (synonym gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS orphanet_dis_name_trgm ON ontology.orphanet_diseases USING gin (name gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS orphanet_syn_syn_trgm ON ontology.orphanet_synonyms USING gin (synonym gin_trgm_ops);"
	@$(PSQL) -f database/sql/add_orphanet_indexes.sql

# Optional fetch (pass ZIP_URL=...)
orphanet-fetch:
	@test -n "$(ZIP_URL)" || (echo "Set ZIP_URL=https://.../orphanet_latest.zip"; exit 1)
	@mkdir -p data/orphanet
	@curl -fL "$(ZIP_URL)" -o data/orphanet/orphanet_latest.zip
	@echo "Downloaded → data/orphanet/orphanet_latest.zip"

# ======================
# API smoke tests
# ======================
api-orphanet-search:
	@curl -s "$(API_BASE)/api/orphanet/search?q=$(Q)&limit=$(LIMIT)" | jq .

api-orphanet-disease:
	@curl -s "$(API_BASE)/api/orphanet/disease/$(ORPHA)" | jq .

api-orphanet-stats:
	@curl -s "$(API_BASE)/api/orphanet/stats" | jq .

api-orphanet-smoke:
	@curl -s "$(API_BASE)/api/orphanet/smoke" | jq .

# ======================
# Core audits & snapshots
# ======================
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

orphanet-snapshots:
	@echo "Writing Orphanet snapshots to snapshots/"
	@mkdir -p snapshots
	@$(PSQL) -A -F $$'\t' -c "COPY (SELECT orpha, name, disorder_type, prevalence FROM ontology.orphanet_diseases ORDER BY orpha) TO STDOUT" > snapshots/orphanet_diseases.tsv
	@$(PSQL) -A -F $$'\t' -c "COPY (SELECT orpha, synonym FROM ontology.orphanet_synonyms ORDER BY orpha, synonym) TO STDOUT" > snapshots/orphanet_synonyms.tsv
	@$(PSQL) -A -F $$'\t' -c "COPY (SELECT orpha, gene_symbol, gene_ncbi_id FROM ontology.orphanet_gene_links ORDER BY orpha, gene_symbol) TO STDOUT" > snapshots/orphanet_gene_links.tsv
	@$(PSQL) -A -F $$'\t' -c "COPY (SELECT orpha, hpo_id FROM ontology.orphanet_phenotype_links ORDER BY orpha, hpo_id) TO STDOUT" > snapshots/orphanet_phenotype_links.tsv
	@echo "Orphanet snapshots written."

# ======================
# RAG + Embeddings + ANN
# ======================
# Upsert Orphanet into public.rag_corpus (title/text/url/ts)
orphanet-rag-upsert:
	@psql "$(DB)" -v ON_ERROR_STOP=1 -f database/sql/orphanet_rag_upsert.sql

# Embeddings (async). Use: BATCH=256 CONC=6 make orphanet-embed
orphanet-embed:
	@echo "Embedding source: orphanet"
	SOURCE=orphanet BATCH=$(BATCH) CONC=$(CONC) DSN="$(DB)" $(PY) server/scripts/embed_rag_source_async.py --source orphanet

# ANN (ivfflat) — tune lists as needed
orphanet-ann:
	@psql "$(DB)" -v ON_ERROR_STOP=1 -c "CREATE INDEX CONCURRENTLY IF NOT EXISTS rag_corpus_embedding_ann_orphanet ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists=150) WHERE source='orphanet';"

# Progress snapshot
orphanet-progress:
	@$(PSQL) -c "\
	  SELECT source, COUNT(*) AS total, \
	         COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS done, \
	         COUNT(*) FILTER (WHERE embedding IS NULL) AS pending, \
	         ROUND(100.0 * COUNT(*) FILTER (WHERE embedding IS NOT NULL) / NULLIF(COUNT(*),0), 2) AS pct \
	  FROM rag_corpus WHERE source='orphanet' GROUP BY source ORDER BY source;"

# Watch progress every 10s
orphanet-embed-watch:
	@while true; do \
	  date; $(MAKE) orphanet-progress; sleep 10; \
	done

# Validate ANN index presence/health
orphanet-ann-check:
	@psql -d 2ndopinionmd -A -F $$'\t' -c "\
	  SELECT i.indexname, x.indisvalid, x.indisready, \
	         COALESCE( (SELECT option_value::int FROM pg_options_to_table(c.reloptions) WHERE option_name='lists'), 0) AS lists, \
	         pg_size_pretty(pg_relation_size(x.indexrelid)) AS size \
	  FROM pg_index x \
	  JOIN pg_class c ON c.oid = x.indexrelid \
	  JOIN pg_namespace n ON n.oid = c.relnamespace \
	  JOIN pg_indexes i ON i.indexname = c.relname \
	  WHERE i.tablename='rag_corpus' AND i.indexname='rag_corpus_embedding_ann_orphanet' \
	  ORDER BY i.indexname;"

# ======================
# Integrity PDF
# ======================
orphanet-report-pdf:
	@$(PY) server/scripts/report_orphanet_pdf.py --out $(REPORT_DIR)/05_orphanet.pdf $(if $(AI),--ai,)

# Rollups
orphanet-integrity: orphanet-audit orphanet-snapshots
orphanet-integrity-all: orphanet-audit orphanet-report-pdf

# Full pipeline (load → rag → embed → ann → lexical → report)
orphanet-all: orphanet-import orphanet-rag-upsert orphanet-embed orphanet-ann orphanet-indexes orphanet-report-pdf

.PHONY: orphanet-import orphanet-indexes orphanet-fetch \
	api-orphanet-search api-orphanet-disease api-orphanet-stats \
	orphanet-audit orphanet-snapshots orphanet-rag-upsert orphanet-embed \
	orphanet-ann orphanet-progress orphanet-embed-watch orphanet-ann-check \
	orphanet-report-pdf orphanet-integrity orphanet-integrity-all orphanet-all \
	api-rag-ask-orphanet api-rag-ask-mixed


api-rag-ask-orphanet:
	@curl -s "$(API_BASE)/api/rag/ask?q=$(Q)&k=$(or K,8)&sources=orphanet" | jq .

api-rag-ask-mixed:
	@curl -s "$(API_BASE)/api/rag/ask?q=$(Q)&k=$(or K,8)" | jq .
