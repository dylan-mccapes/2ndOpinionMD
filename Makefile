# ===============================
# 2ndOpinionMD  Makefile (clean)
# ===============================

# -------- Basic Vars --------
SHELL := /bin/zsh
.ONESHELL:
.SHELLFLAGS := -lc

# Ensure Homebrew + libpq in PATH (macOS)
export PATH := /opt/homebrew/bin:/opt/homebrew/sbin:/opt/homebrew/opt/libpq/bin:$(PATH)

FRONTEND_DIR          := frontend/react
FRONTEND_DEPLOY_PATH  := /opt/homebrew/var/www/2ndopinionmd
RELEASES_DIR          := /opt/homebrew/var/www/2ndopinionmd_releases
HOST                  := 2ndopinionmd.ai

PY                    ?= server/venv312/bin/python
DB_NAME               ?= 2ndopinionmd

# Pick a psql (first that exists)
PSQL ?= $(firstword \
  $(wildcard /opt/homebrew/bin/psql) \
  $(wildcard /opt/homebrew/opt/libpq/bin/psql) \
  $(shell command -v psql))

# -------- Data Dirs --------
MIMIC3_DIR        ?= data/MIMIC-III
MIMIC4_DIR        ?= data/mimic-iv-2.2
MIMICIV_NOTE_DIR  ?= physionet.org/files/mimic-iv-note/2.2
N2C2_T3_SAMPLE_DIR?= data/n2c2/track3-sample

# -------- PHONY --------
.PHONY: \
  dev-setup env-doctor py-venv deps-install deps-upgrade pip-check dev-setup-full \
  ship fe-build deploy-fe nginx-reload smoke verify-live rollback clean fe-clean \
  api-openapi \
  disgenet-schema disgenet-download-genes disgenet-import disgenet-smoke disgenet-auth-test \
  disgenet-ai-rank disgenet-ai-map disgenet-ai-pull \
  loinc-schema loinc-indexes loinc-import loinc-smoke \
  rxnorm-import api-rxnorm-search api-rxnorm-drug api-rxnorm-ndc rxnorm-trgm-index rxnorm-indexes \
  chv-setup chv-import chv-dry-run chv-search chv-fuzzy \
  mimic3-schema mimic4-schema mimic4-dry-run mimic4-import \
  api-m4-i50-hadm api-m4-any-hadm mimic3-dry-run mimic3-import mimic3-stats mimic3-sanity \
  mimic3-notes-schema mimic3-notes-import \
  mimiciv-note-schema mimiciv-note-import mimiciv-note-dry mimiciv-note-stats \
  n2c2-schema n2c2-t3-sample-schema n2c2-t3-sample-import n2c2-t3-sample-qa n2c2-t3-sample-reset n2c2-t3-sample-context n2c2-t3-backfill \
  n2c2-ap-extract-m3 n2c2-ap-extract-miv n2c2-ap-qa n2c2-export-gold n2c2-export-silver-m3 n2c2-export-silver-miv \
  panelapp-schema panelapp-import panelapp-import-ids panelapp-indexes \
  api-panelapp-search api-panelapp-panel api-panelapp-stats \
  panelapp-rag-upsert panelapp-embed panelapp-rag \
  guidelines-schema guidelines-fts guidelines-embed guidelines-stats guidelines-health \
  guidelines-load guidelines-load-ng220 guidelines-load-ng65 guidelines-load-ng193 guidelines-ingest-all-nice \
  diagrules-schema diagrules-import diagrules-list diagrules-apply-sample diagrules-test \
  diagrules-rag-upsert diagrules-embed diagrules-rag \
  be-stop be-start be-restart be-hard-restart be-logs api-health \
  api-loinc-search api-loinc-concept api-loinc-term api-loinc-panel \
  snomed-audit snomed-preview snomed-import snomed-trgm-index \
  api-snomed-search api-snomed-concept api-snomed-map api-snomed-stats \
  orphanet-import orphanet-indexes api-orphanet-search api-orphanet-disease api-orphanet-stats \
  hpo-import hpo-links-import api-hpo-search api-hpo-term \
  act.router.smoke act.mv.rebuild

# =========================
# Dev bootstrap & Python env
# =========================
dev-setup:
	@echo ">>> Detecting Homebrew..."
	@BP=$$( (brew --prefix 2>/dev/null) || echo /opt/homebrew ); \
	echo "    brew prefix: $$BP"; \
	ZRC="$$HOME/.zshrc"; \
	echo ">>> Ensuring Homebrew PATHs in $$ZRC"; \
	grep -q 'export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$$PATH"' "$$ZRC" 2>/dev/null || printf '%s\n' 'export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$$PATH"' >> "$$ZRC"; \
	LPQ_BIN="$$BP/opt/libpq/bin"; \
	if [ -d "$$LPQ_BIN" ]; then \
	  echo "    libpq bin: $$LPQ_BIN"; \
	  grep -q 'export PATH=".*/opt/libpq/bin:$$PATH"' "$$ZRC" 2>/dev/null || printf '%s\n' 'export PATH="'"$$LPQ_BIN"':$$PATH"' >> "$$ZRC"; \
	else \
	  echo "    (libpq not found under $$BP/opt/libpq; run: brew install libpq && brew info libpq)"; \
	fi; \
	echo ">>> Adding 2OMD env loader to $$ZRC (if missing)"; \
	if ! grep -q '# 2ndOpinionMD env loader' "$$ZRC" 2>/dev/null; then \
	  { \
	    printf '%s\n' '# 2ndOpinionMD env loader'; \
	    printf '%s\n' '2omd_env() {'; \
	    printf '%s\n' '  if [ -f "'"$(PWD)/server/.env"'" ]; then'; \
	    printf '%s\n' '    set -a; . "'"$(PWD)/server/.env"'" ; set +a;'; \
	    printf '%s\n' '    echo "[2OMD] Loaded env from server/.env"'; \
	    printf '%s\n' '  else'; \
	    printf '%s\n' '    echo "[2OMD] server/.env not found"'; \
	    printf '%s\n' '  fi'; \
	    printf '%s\n' '}'; \
	    printf '%s\n' 'alias 2omd='\''cd '"$(PWD)"'\'''; \
	  } >> "$$ZRC"; \
	else \
	  echo "    (env loader already present)"; \
	fi; \
	echo ">>> Done. Open a new shell OR run: source $$ZRC"

env-doctor:
	@echo "=== ENV DOCTOR ==="
	@echo "Shell: $$SHELL"
	@echo "Homebrew: $$(command -v brew 2>/dev/null || echo '(not found)')"
	@echo "brew --prefix: $$( (brew --prefix 2>/dev/null) || echo '(n/a)')"
	@echo "psql: $$(command -v psql 2>/dev/null || echo '(not found)')"
	@echo "psql --version: $$( (psql --version 2>/dev/null) || echo '(n/a)')"
	@echo "Python: $$(command -v $(PY) 2>/dev/null || echo '(not found)')"
	@echo "Python ver: $$( ($(PY) -V 2>/dev/null) || echo '(n/a)')"
	@echo "DATABASE_URL: $${DATABASE_URL:+***$${DATABASE_URL: -12}}"
	@echo "OPENAI_API_KEY: $${OPENAI_API_KEY:+***$${OPENAI_API_KEY: -6}}"
	@echo "PATH sample: $$(echo $$PATH | tr ':' '\n' | sed -n '1,6p') ..."
	@echo "Tip: run 'source $$HOME/.zshrc' then '2omd_env' to load server/.env"

py-venv:
	@if [ ! -x server/venv312/bin/python ]; then \
	  echo ">>> Creating Python venv at server/venv312"; \
	  if command -v python3.12 >/dev/null 2>&1; then python3.12 -m venv server/venv312; \
	  else python3 -m venv server/venv312; fi; \
	else echo ">>> venv exists at server/venv312"; fi

deps-install: py-venv
	@echo ">>> Upgrading pip/setuptools/wheel"
	@$(PY) -m pip install --upgrade pip setuptools wheel
	@echo ">>> Installing server/requirements.txt"
	@$(PY) -m pip install -r server/requirements.txt

deps-upgrade:
	@echo ">>> Upgrading to match server/requirements.txt"
	@$(PY) -m pip install --upgrade -r server/requirements.txt

pip-check:
	@$(PY) -c "import psycopg2, asyncpg, sqlalchemy, fastapi, httpx, requests; print('OK')"

dev-setup-full: dev-setup py-venv deps-install
	@echo ">>> dev-setup-full complete."

# =========================
# Frontend deploy helpers
# =========================
ship: fe-build deploy-fe nginx-reload

fe-build:
	@echo ">>> Building frontend"
	cd $(FRONTEND_DIR) && yarn install && CI= yarn build
	@echo ">>> Build complete at $(FRONTEND_DIR)/build"

deploy-fe:
	@echo ">>> Deploying to $(FRONTEND_DEPLOY_PATH)"
	TS=$$(date +%F-%H%M); \
	sudo mkdir -p $(RELEASES_DIR)/$$TS; \
	sudo rsync -a --delete $(FRONTEND_DIR)/build/ $(RELEASES_DIR)/$$TS/; \
	sudo rsync -a --delete $(FRONTEND_DIR)/build/ $(FRONTEND_DEPLOY_PATH)/
	@echo ">>> Frontend deployed."

nginx-reload:
	@echo ">>> Reloading nginx"
	sudo nginx -t && sudo nginx -s reload
	@echo ">>> nginx reloaded."

smoke:
	@curl -sI https://$(HOST)/ | sed -n '1p;/etag/Ip;/last-modified/Ip'
	@curl -sf https://$(HOST)/api/health | jq . || curl -sf https://$(HOST)/api/health

verify-live:
	@JS=$$(curl -s https://$(HOST)/asset-manifest.json | jq -r '.files["main.js"]'); \
	echo "main bundle: $$JS"; \
	curl -s "https://$(HOST)$$JS" | strings | egrep -o "AI Analysis|Diagnoses|Environmental Factors|Life Stressors|Pattern Observations|Journaling Recommendation" | sort -u || true

rollback: ## Usage: make rollback REL=YYYY-MM-DD-HHMM
	@test -n "$(REL)" || (echo "Usage: make rollback REL=YYYY-MM-DD-HHMM" ; exit 1)
	sudo rsync -a --delete $(RELEASES_DIR)/$(REL)/ $(FRONTEND_DEPLOY_PATH)/
	sudo nginx -s reload

clean: fe-clean
	@echo ">>> Clean complete."

fe-clean:
	@echo ">>> Cleaning frontend build artifacts"
	rm -rf $(FRONTEND_DIR)/build

# =========================
# OpenAPI (quick list)
# =========================
api-openapi:
	@{ curl -sf http://localhost:8000/api/openapi.json || curl -sf http://localhost:8000/openapi.json; } \
	| jq -r '.paths | keys[]' | sed 's/^/  /'

# -------- GWAS Catalog (autoimmune traits) --------
GWAS_DIR              ?= data/gwas
GWAS_ALL_TSV          ?= $(GWAS_DIR)/gwas_catalog.tsv
GWAS_AUTO_TSV         ?= $(GWAS_DIR)/gwas_autoimmune.tsv
GWAS_URL              ?= https://www.ebi.ac.uk/gwas/api/search/downloads/alternative
GWAS_KEYWORDS         ?= multiple sclerosis|spondyloarthritis|ankylosing spondylitis|psoriatic arthritis|autoimmune

.PHONY: gwas-schema gwas-download gwas-filter-autoimmune gwas-import gwas-indexes gwas-smoke

gwas-schema:
	@echo ">>> Applying GWAS schema DDL"
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/molecular_gwas_schema.sql

gwas-download:
	@echo ">>> Downloading latest GWAS Catalog TSV to $(GWAS_ALL_TSV)"
	@mkdir -p $(GWAS_DIR)
	@curl -fsSL "$(GWAS_URL)" -o "$(GWAS_ALL_TSV)"
	@echo ">>> File size:" && ls -lh "$(GWAS_ALL_TSV)"

gwas-filter-autoimmune:
	@echo ">>> Filtering autoimmune traits to $(GWAS_AUTO_TSV)"
	@test -s "$(GWAS_ALL_TSV)" || (echo "ERROR: $(GWAS_ALL_TSV) missing. Run: make gwas-download"; exit 2)
	@( \
	set -e; \
	head -n 1 "$(GWAS_ALL_TSV)" > "$(GWAS_AUTO_TSV)"; \
	tail -n +2 "$(GWAS_ALL_TSV)" | \
	awk 'BEGIN{IGNORECASE=1} $$0 ~ /($(GWAS_KEYWORDS))/ {print}' >> "$(GWAS_AUTO_TSV)"; \
	echo ">>> Rows:" $$(wc -l < "$(GWAS_AUTO_TSV)"); \
	)

gwas-import:
	@echo ">>> Importing $(GWAS_AUTO_TSV) into molecular.gwas_hits"
	@test -s "$(GWAS_AUTO_TSV)" || (echo "ERROR: $(GWAS_AUTO_TSV) missing. Run: make gwas-filter-autoimmune"; exit 2)
	# Prefer SYNC_DATABASE_URL (psycopg2) with fallback to DATABASE_URL stripped of +asyncpg
	@DSN_PG="$$(grep -E '^SYNC_DATABASE_URL=' server/.env | cut -d= -f2-)"; \
	if [ -z "$$DSN_PG" ]; then \
	DSN_PG="$$(grep -E '^DATABASE_URL=' server/.env | cut -d= -f2- | sed 's/+asyncpg//')"; \
	fi; \
	echo "DSN selected for import: $${DSN_PG:+***$${DSN_PG: -12}}"; \
	SYNC_DATABASE_URL="$$DSN_PG" GWAS_TSV="$(GWAS_AUTO_TSV)" \
	$(PY) server/scripts/ingest_gwas_catalog.py

gwas-indexes:
	@echo ">>> Creating indexes for fast lookup"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gwas_trait_trgm   ON molecular.gwas_hits USING gin (disease_trait gin_trgm_ops);"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gwas_mapped_trait ON molecular.gwas_hits USING gin (mapped_trait gin_trgm_ops);"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gwas_snps_idx     ON molecular.gwas_hits (snps);"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gwas_pval_idx     ON molecular.gwas_hits (p_value);"

gwas-smoke:
	@echo ">>> Counts by keyword"
	@$(PSQL) -d $(DB_NAME) -c "SELECT COUNT(*) AS rows, MIN(p_value) AS best_p FROM molecular.gwas_hits;"
	@$(PSQL) -d $(DB_NAME) -c "SELECT disease_trait, COUNT(*) n FROM molecular.gwas_hits GROUP BY 1 ORDER BY n DESC LIMIT 10;"
	@$(PSQL) -d $(DB_NAME) -c "SELECT snps, p_value, disease_trait, study_accession FROM molecular.gwas_hits WHERE disease_trait ILIKE '%sclerosis%' ORDER BY p_value ASC NULLS LAST LIMIT 10;"

rag-ann-index:
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "DROP INDEX IF EXISTS rag_corpus_embedding_ann;"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX CONCURRENTLY rag_corpus_embedding_ann ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists = 800);"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "ANALYZE public.rag_corpus;"

# -------- GWAS → RAG (scripted) --------
gwas-rag-upsert:
	@echo ">>> Upserting GWAS into rag_corpus via script"
	@DSN_PG="$$(grep -E '^SYNC_DATABASE_URL=' server/.env | cut -d= -f2-)"; \
	if [ -z "$$DSN_PG" ]; then \
	  DSN_PG="$$(grep -E '^DATABASE_URL=' server/.env | cut -d= -f2- | sed 's/+asyncpg//')"; \
	fi; \
	SYNC_DATABASE_URL="$$DSN_PG" $(PY) server/scripts/gwas_rag_upsert.py $(if $(SINCE),--since $(SINCE),)

gwas-embed:
	@echo ">>> Embedding GWAS rows in rag_corpus"
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus \
	  --id-col id \
	  --text-col text \
	  --embedding-col embedding \
	  --model text-embedding-3-small \
	  --batch 256 \
	  --where "source='gwas' AND embedding IS NULL"

gwas-rag: gwas-rag-upsert gwas-embed
	@echo ">>> GWAS → RAG complete."

gwas-api-smoke:
	@echo ">>> OpenAPI lists GWAS endpoints"
	@curl -s http://localhost:8000/api/openapi.json | jq -r '.paths | keys[] | select(test("^/api/gwas"))'
	@echo ">>> Stats"
	@curl -s "http://localhost:8000/api/gwas/stats" | jq .
	@echo ">>> Search sclerosis (5)"
	@curl -s "http://localhost:8000/api/gwas/search?q=sclerosis&limit=5" | jq -c '.items | length'
	@echo ">>> SNP rs9271366 (top 3)"
	@curl -s "http://localhost:8000/api/gwas/snp/rs9271366?limit=3" | jq -c '.items | length'
	@echo ">>> Trait multiple sclerosis (3)"
	@curl -s "http://localhost:8000/api/gwas/trait/multiple%20sclerosis?limit=3" | jq -c '.items | length'

rag-sql-smoke:
	@$(PSQL) -d $(DB_NAME) -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_emb FROM public.rag_corpus GROUP BY 1 ORDER BY n DESC;"
	@$(PSQL) -d $(DB_NAME) -c "SELECT COUNT(*) AS ts_missing FROM public.rag_corpus WHERE ts IS NULL;"
	@$(PSQL) -d $(DB_NAME) -c "WITH q AS (SELECT plainto_tsquery('english','multiple sclerosis') AS tsq) SELECT id, source, LEFT(title,100) AS title, ts_rank_cd(ts,(SELECT tsq FROM q)) AS rank FROM public.rag_corpus WHERE ts @@ (SELECT tsq FROM q) ORDER BY rank DESC LIMIT 10;"

rag-ann-probe:
	@$(PSQL) -d $(DB_NAME) -c "WITH seed AS (SELECT id, source, title, embedding FROM public.rag_corpus WHERE source='gwas' AND embedding IS NOT NULL ORDER BY random() LIMIT 1) SELECT r.id, r.source, LEFT(r.title,80) AS title, 1 - (r.embedding <=> s.embedding) AS cosine_sim FROM public.rag_corpus r CROSS JOIN seed s WHERE r.embedding IS NOT NULL ORDER BY r.embedding <=> s.embedding LIMIT 10;"

kg-api-smoke:
	@curl -s http://localhost:8000/api/health | jq .
	@curl -s "http://localhost:8000/api/guidelines/search?q=spondyloarthritis&limit=3" | jq .
	@curl -s "http://localhost:8000/api/panelapp/stats" | jq .
	@curl -s "http://localhost:8000/api/diagnostic_rules/list" | jq .
	@curl -s "http://localhost:8000/api/gwas/stats" | jq .
	@curl -s -X POST "http://localhost:8000/api/diagnose" -H 'Content-Type: application/json' \
		-d '{"symptoms":["optic neuritis","numbness in legs","fatigue","gait imbalance"],"demographics":{"sex":"female","age":34},"model":"gpt-3.5-turbo"}' | jq .


# =========================
# DisGeNET: schema + pulls
# =========================
# Requirements:
# - server/scripts/download_disgenet_by_genes.py
# - server/scripts/ingest_disgenet.py
# - server/scripts/symbols_to_entrez.py
# Env:
#   DISGENET_TOKEN=<trial/paid key>
#   SYNC_DATABASE_URL=postgresql://user@localhost:5432/2ndopinionmd  (no +asyncpg)

disgenet-schema:
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/setup_disgenet_schema.sql

disgenet-download-genes:
	@set -euo pipefail; \
	: $$DISGENET_TOKEN; \
	BASE="$${DISGENET_API_BASE:-https://api.disgenet.com/api/v1}"; \
	export DISGENET_API_BASE="$$BASE"; \
	export DISGENET_ENDPOINT="$${DISGENET_ENDPOINT:-gda/summary}"; \
	export DISGENET_FILTER_KEY="$${DISGENET_FILTER_KEY:-source}"; \
	export DISGENET_FILTER_VALUE="$${DISGENET_FILTER_VALUE:-CURATED}"; \
	export DISGENET_TSV="$${DISGENET_TSV:-data/disgenet_curated.tsv.new}"; \
	export DISGENET_AUTH_MODE="$${DISGENET_AUTH_MODE:-bare}"; \
	GENES_ARG=""; \
	if [ -n "$${GENES-}" ]; then GENES_ARG="GENES=$$GENES"; fi; \
	if [ -n "$${GENES_FILE-}" ]; then GENES_ARG="GENES_FILE=$$GENES_FILE"; fi; \
	$(PY) server/scripts/download_disgenet_by_genes.py $$GENES_ARG; \
	echo ">>> Output: $$DISGENET_TSV"

disgenet-import:
	@set -euo pipefail; \
	TSV_PATH="$${TSV:-data/disgenet_curated.tsv}"; \
	test -s "$$TSV_PATH" || { echo "ERROR: TSV missing/empty at $$TSV_PATH"; exit 1; }; \
	DSN="$${SYNC_DATABASE_URL:-$${DATABASE_URL-}}"; \
	DSN="$${DSN/+asyncpg/}"; \
	test -n "$$DSN" || { echo "ERROR: Set SYNC_DATABASE_URL (sync psycopg2 DSN)"; exit 1; }; \
	SYNC_DATABASE_URL="$$DSN" DISGENET_TSV="$$TSV_PATH" $(PY) server/scripts/ingest_disgenet.py

disgenet-smoke:
	@$(PSQL) -d $(DB_NAME) -c "SELECT COUNT(*) AS n FROM molecular.disgenet_associations;"
	@$(PSQL) -d $(DB_NAME) -c "SELECT gene_symbol, disease_name, score FROM molecular.disgenet_associations ORDER BY score DESC NULLS LAST LIMIT 10;"

disgenet-auth-test:
	@set -e; \
	BASE="$${DISGENET_API_BASE:-https://api.disgenet.com/api/v1}"; \
	echo ">>> Version:"; curl -sS "$$BASE/public/version" | jq .; \
	echo ">>> Single-gene CSV head:"; \
	curl -sS -H "Authorization: $$DISGENET_TOKEN" -H 'accept: application/csv' \
	  "$$BASE/gda/summary?gene_ncbi_id=351&page_number=0&source=CURATED" | head

# ---- Autoimmune-first pipeline (trial-safe) ----
disgenet-ai-rank:  ## Build symbol + ranked lists (no heredocs)
	@mkdir -p data
	@$(PSQL) -d $(DB_NAME) -At    -f sql/autoimmune_symbols.sql    > data/autoimmune_gene_symbols.txt
	@$(PSQL) -d $(DB_NAME) -F $$'\t' -At -f sql/autoimmune_ranked.sql > data/autoimmune_genes_ranked.tsv
	@echo ">>> Wrote data/autoimmune_gene_symbols.txt and data/autoimmune_genes_ranked.tsv"

disgenet-ai-map:
	@set -e; \
	IN="data/autoimmune_genes_ranked.tsv"; OUT="data/autoimmune_gene_ids.tsv"; \
	test -s "$$IN" || { echo "ERROR: $$IN missing/empty. Run: make disgenet-ai-rank"; exit 1; }; \
	TMP="data/autoimmune_genes_ranked.top.tsv"; \
	if [ -n "$${N-}" ]; then awk 'NR==1{print;next}{print}' "$$IN" | head -n $$(( $${N}+1 )) > "$$TMP"; IN="$$TMP"; fi; \
	$(PY) server/scripts/symbols_to_entrez.py "$$IN" "$$OUT"; \
	cut -f2 "$$OUT" | tail -n +2 > data/autoimmune_gene_ids.txt; \
	echo ">>> IDs -> data/autoimmune_gene_ids.txt"

disgenet-ai-pull:
	@set -e; \
	test -s "data/autoimmune_gene_ids.txt" || { echo "ERROR: data/autoimmune_gene_ids.txt missing. Run: make disgenet-ai-map"; exit 1; }; \
	DISGENET_TOKEN="$$DISGENET_TOKEN" $(PY) server/scripts/disgenet_pull_batches.py \
	  --ids-file data/autoimmune_gene_ids.txt \
	  --out-tsv data/disgenet_curated.tsv \
	  --batch-size $${BATCH_SIZE:-10} \
	  --filter-key $${DISGENET_FILTER_KEY:-source} \
	  --filter-value $${DISGENET_FILTER_VALUE:-CURATED} \
	  --endpoint $${DISGENET_ENDPOINT:-gda/summary} \
	  --auth-mode $${DISGENET_AUTH_MODE:-bare} \
	  --sleep $${DISGENET_SLEEP:-0}

# =========================
# LOINC / RxNorm
# =========================
loinc-schema:
	@echo ">>> Creating LOINC schema/tables"
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/setup_loinc_schema.sql
	@echo ">>> LOINC schema ready."

loinc-indexes:
	@echo ">>> Ensuring LOINC trigram indexes"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS loinc_long_common_name_trgm ON ontology.loinc_terms USING gin (long_common_name gin_trgm_ops);"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS loinc_shortname_trgm        ON ontology.loinc_terms USING gin (shortname gin_trgm_ops);"

loinc-import:
	@echo ">>> LOINC import"
	@test -n "$(ZIP_URL)" || (echo "ERROR: set ZIP_URL=https://.../Loinc_YYYYMMDD.zip" ; exit 1)
	@$(MAKE) loinc-schema
	@$(PY) server/scripts/ingest_loinc.py --zip-url $(ZIP_URL)
	@$(MAKE) loinc-indexes

loinc-smoke:
	@$(PSQL) -d $(DB_NAME) -c "SELECT loinc_num, shortname, system, scale_typ FROM ontology.loinc_terms WHERE loinc_num='2345-7';"
	@curl -s "http://localhost:8000/api/loinc/search?q=glucose&limit=5" | jq .
	@curl -s "http://localhost:8000/api/loinc/term/2345-7" | jq .

rxnorm-import:
	@echo ">>> RxNorm import"
	@$(PY) server/scripts/ingest_rxnorm.py --zip-url $(ZIP_URL)

api-rxnorm-search:
	@curl -s "http://localhost:8000/api/rxnorm/search?q=$(Q)&tty=$(TTY)&limit=$(LIMIT)" | jq .

api-rxnorm-drug:
	@curl -s "http://localhost:8000/api/rxnorm/drug/$(RXCUI)" | jq .

api-rxnorm-ndc:
	@curl -s "http://localhost:8000/api/rxnorm/ndc/$(NDC)" | jq .

rxnorm-trgm-index:
	@$(PSQL) -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS rxnorm_conso_str_gin_idx ON ontology.rxnorm_conso USING gin (str gin_trgm_ops);"

rxnorm-indexes:
	@$(PSQL) -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS rxnorm_ndc_norm_idx ON ontology.rxnorm_ndc (ndc_norm);"
	@$(PSQL) -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS rxnorm_ndc_rxcui_idx ON ontology.rxnorm_ndc (rxcui);"
	@$(PSQL) -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS rxnorm_conso_label_pick_idx ON ontology.rxnorm_conso (rxcui, sab, ispref, tty, str);"

# =========================
# CHV
# =========================
chv-setup:
	@$(PSQL) -d $(DB_NAME) -f database/schemas/setup_chv_synonyms.sql

chv-import: chv-setup
	@$(PY) server/scripts/ingest_chv.py $(FILE)

chv-dry-run:
	@$(PY) server/scripts/ingest_chv.py --file $(FILE) --dry-run

chv-search:
	@$(PSQL) -d $(DB_NAME) -c "SELECT term, cui FROM ontology.synonyms WHERE source='CHV' AND term ILIKE '%$${Q}%' ORDER BY term LIMIT $${LIMIT:-20};"

chv-fuzzy:
	@$(PSQL) -d $(DB_NAME) -c "SET pg_trgm.similarity_threshold = 0.3; SELECT term, cui, similarity(term, '$$Q') AS sim FROM ontology.synonyms WHERE source='CHV' AND term % '$$Q' ORDER BY sim DESC LIMIT $${LIMIT:-20};"

# =========================
# MIMIC schemas + loads
# =========================
mimic3-schema:
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/ehr_mimic3.sql

mimic4-schema:
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/ehr_mimic4.sql

mimic4-dry-run:
	@$(PY) server/scripts/ingest_mimic4.py --dir "$(MIMIC4_DIR)" --dry-run

mimic4-import:
	@$(PY) server/scripts/ingest_mimic4.py --dir "$(MIMIC4_DIR)"

api-m4-i50-hadm:
	@$(PSQL) -d $(DB_NAME) -c "SELECT hadm_id, COUNT(*) AS n FROM ehr_mimic4.diagnoses_icd WHERE icd_version = 10 AND icd_code LIKE 'I50%%' GROUP BY 1 ORDER BY n DESC LIMIT $${LIMIT:-20};"

api-m4-any-hadm:
	@$(PSQL) -d $(DB_NAME) -Atc "SELECT hadm_id FROM ehr_mimic4.diagnoses_icd ORDER BY random() LIMIT 1" \
	| xargs -I{} sh -c 'echo HADM={}; curl -s "http://localhost:8000/api/mimic4/diagnoses?hadm_id={}" | jq .'

mimic3-dry-run:
	@$(PY) server/scripts/ingest_mimic3.py --dir "$(MIMIC3_DIR)"

mimic3-import:
	@$(PY) server/scripts/ingest_mimic3.py --dir "$(MIMIC3_DIR)"

mimic3-stats:
	@$(PSQL) -d $(DB_NAME) -c "SELECT 'patients' tbl, count(*) FROM ehr_mimic3.patients UNION ALL SELECT 'admissions', count(*) FROM ehr_mimic3.admissions UNION ALL SELECT 'icustays', count(*) FROM ehr_mimic3.icustays UNION ALL SELECT 'diagnoses_icd', count(*) FROM ehr_mimic3.diagnoses_icd UNION ALL SELECT 'procedures_icd', count(*) FROM ehr_mimic3.procedures_icd UNION ALL SELECT 'labevents', count(*) FROM ehr_mimic3.labevents" | column -t

mimic3-sanity:
	@$(PSQL) -d $(DB_NAME) -c "SELECT hadm_id, count(*) labs FROM ehr_mimic3.labevents GROUP BY hadm_id ORDER BY labs DESC NULLS LAST LIMIT 5;"
	@$(PSQL) -d $(DB_NAME) -c "SELECT d.icd9_code, di.long_title, count(*) n FROM ehr_mimic3.diagnoses_icd d LEFT JOIN ehr_mimic3.d_icd_diagnoses di USING(icd9_code) GROUP BY 1,2 ORDER BY n DESC LIMIT 10;"

# ================ Notes =================
mimic3-notes-schema:
	@$(PSQL) -d $(DB_NAME) -c "\
CREATE SCHEMA IF NOT EXISTS text; \
CREATE TABLE IF NOT EXISTS text.mimic3_notes ( \
  row_id INTEGER PRIMARY KEY, subject_id INTEGER, hadm_id INTEGER, \
  chartdate DATE, charttime TIMESTAMP, storetime TIMESTAMP, \
  category TEXT, description TEXT, cgid INTEGER, iserror TEXT, text TEXT); \
CREATE INDEX IF NOT EXISTS mimic3_notes_hadm_idx    ON text.mimic3_notes(hadm_id); \
CREATE INDEX IF NOT EXISTS mimic3_notes_subject_idx ON text.mimic3_notes(subject_id);"

mimic3-notes-import: mimic3-notes-schema
	@$(PSQL) -d $(DB_NAME) -c "\
\copy text.mimic3_notes (row_id,subject_id,hadm_id,chartdate,charttime,storetime,category,description,cgid,iserror,text) \
FROM PROGRAM 'gzip -dc physionet.org/files/mimiciii/1.4/NOTEEVENTS.csv.gz' WITH (FORMAT csv, HEADER true)"

mimiciv-note-schema:
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/text_mimiciv_notes.sql

mimiciv-note-import: mimiciv-note-schema
	@$(PY) server/scripts/ingest_mimiciv_notes.py --dir "$(MIMICIV_NOTE_DIR)"

mimiciv-note-dry: mimiciv-note-schema
	@$(PY) server/scripts/ingest_mimiciv_notes.py --dir "$(MIMICIV_NOTE_DIR)" --limit 500

mimiciv-note-stats:
	@$(PSQL) -d $(DB_NAME) -c "SELECT domain, COUNT(*) AS n FROM text.mimiciv_notes GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -d $(DB_NAME) -c "SELECT SUM((hadm_id IS NOT NULL AND a.hadm_id IS NULL)::int) AS hadm_not_in_admissions, SUM((hadm_id IS NULL)::int) AS hadm_null FROM text.mimiciv_notes n LEFT JOIN ehr_mimic4.admissions a USING (hadm_id);"

# =========================
# n2c2 Track 3
# =========================
n2c2-schema:
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/text_n2c2_track3.sql

n2c2-t3-sample-schema: n2c2-schema
	@true

n2c2-t3-sample-import:
	@$(PY) server/scripts/ingest_n2c2_t3_sample.py --base $(N2C2_T3_SAMPLE_DIR)

n2c2-t3-sample-qa:
	@$(PSQL) -d $(DB_NAME) -c "SELECT COUNT(*) AS notes FROM text.n2c2_notes WHERE track='2022-T3';"
	@$(PSQL) -d $(DB_NAME) -c "SELECT section_name, COUNT(*) FROM text.n2c2_ap_sections GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -d $(DB_NAME) -c "SELECT label, COUNT(*) FROM text.n2c2_ap_relations GROUP BY 1 ORDER BY 2 DESC;"

n2c2-t3-sample-reset:
	@$(PSQL) -d $(DB_NAME) -c "DELETE FROM text.n2c2_notes WHERE track='2022-T3' AND filename IN ('n2c2_sample_raw.csv','n2c2_sample.csv');"

n2c2-t3-backfill:
	@$(PSQL) -d $(DB_NAME) -c "UPDATE text.n2c2_notes n SET note_text = m.text FROM text.mimic3_notes m WHERE n.track='2022-T3' AND n.external_id = m.row_id::text;"

n2c2-ap-extract-m3: n2c2-schema
	@$(PY) server/scripts/extract_ap_pairs_from_mimic.py --source m3 --limit $${LIMIT:-20000} --track MIII-AP

n2c2-ap-extract-miv: n2c2-schema
	@$(PY) server/scripts/extract_ap_pairs_from_mimic.py --source miv --domain discharge --limit $${LIMIT:-20000} --track MIV-AP

n2c2-ap-qa:
	@$(PSQL) -d $(DB_NAME) -c "SELECT track, COUNT(*) AS notes FROM text.n2c2_notes GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -d $(DB_NAME) -c "SELECT s.section_name, COUNT(*) FROM text.n2c2_ap_sections s GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -d $(DB_NAME) -c "SELECT n.track, COUNT(*) AS rels FROM text.n2c2_ap_relations r JOIN text.n2c2_notes n USING (note_id) GROUP BY 1 ORDER BY 1;"

n2c2-export-gold:
	@$(PSQL) -d $(DB_NAME) -c "\copy (SELECT * FROM text.v_n2c2_ap_pairs WHERE track='2022-T3') TO 'data/n2c2/train_gold.csv' CSV HEADER"

n2c2-export-silver-m3:
	@$(PSQL) -d $(DB_NAME) -c "\copy (SELECT * FROM text.v_n2c2_ap_pairs WHERE track='MIII-AP') TO 'data/n2c2/train_silver_m3.csv' CSV HEADER"

n2c2-export-silver-miv:
	@$(PSQL) -d $(DB_NAME) -c "\copy (SELECT * FROM text.v_n2c2_ap_pairs WHERE track='MIV-AP') TO 'data/n2c2/train_silver_miv.csv' CSV HEADER"

# =========================
# PanelApp
# =========================
panelapp-schema:
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -f database/schemas/012_panelapp_gene_panels.sql

panelapp-import:
	@echo ">>> Importing PanelApp signed-off targets ($(PANELAPP_PANELS))"
	@PANELAPP_PANELS="$(PANELAPP_PANELS)" $(PY) server/scripts/panelapp_import.py
	@$(MAKE) panelapp-indexes

panelapp-import-ids:
	@echo ">>> Importing PanelApp by IDs: $(IDS)"
	@PANELAPP_ALLOW_UNSIGNED=$(ALLOW_UNSIGNED) PANELAPP_IDS="$(IDS)" $(PY) server/scripts/panelapp_import.py
	@$(MAKE) panelapp-indexes

panelapp-indexes:
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gp_panel_name_trgm    ON molecular.gene_panels USING gin (panel_name gin_trgm_ops);"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gp_gene_symbol_trgm    ON molecular.gene_panels USING gin (gene_symbol gin_trgm_ops);"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gp_ts_gin             ON molecular.gene_panels USING gin (ts);"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gp_signedoff_idx      ON molecular.gene_panels (signed_off);"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gp_panel_id_version_idx ON molecular.gene_panels (panel_id, panel_version);"

panelapp-rag-upsert:
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "\
INSERT INTO public.rag_corpus (source, title, text, ts) \
SELECT 'panelapp', \
       'Panel: '||panel_name||' ??? '||gene_symbol, \
       trim(both ' ' FROM concat_ws(' ', 'Panel:', panel_name, 'Gene:', gene_symbol, \
           'Confidence:', coalesce(confidence_level,''), \
           'MOI:', coalesce(mode_of_inheritance,''), \
           'Phenotypes:', coalesce(array_to_string(phenotypes,'; '),''), \
           'Evidence:',   coalesce(array_to_string(evidence,'; '),''), \
           'Relevant disorders:', coalesce(array_to_string(relevant_disorders,'; '),''))) AS text, \
       to_tsvector('english', coalesce(panel_name,'')||' '||coalesce(gene_symbol,'')||' '|| \
           coalesce(array_to_string(phenotypes,' '),'')||' '|| \
           coalesce(array_to_string(evidence,' '),'')||' '|| \
           coalesce(array_to_string(relevant_disorders,' '),'')) \
FROM molecular.gene_panels gp \
WHERE NOT EXISTS ( \
  SELECT 1 FROM public.rag_corpus rc \
  WHERE rc.source='panelapp' AND rc.title='Panel: '||gp.panel_name||' ??? '||gp.gene_symbol); \
UPDATE public.rag_corpus SET ts = to_tsvector('english', coalesce(title,'')||' '||coalesce(text,'')) WHERE source='panelapp';"

panelapp-embed:
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus \
	  --id-col id \
	  --text-col text \
	  --embedding-col embedding \
	  --model text-embedding-3-small \
	  --batch 256 \
	  --where "source='panelapp' AND embedding IS NULL"

panelapp-rag: panelapp-rag-upsert panelapp-embed

api-panelapp-stats:
	@curl -s "http://localhost:8000/api/panelapp/stats" | jq .

api-panelapp-search:
	@curl -s "http://localhost:8000/api/panelapp/search?q=$(Q)&only_green=$(GREEN)" | jq .

api-panelapp-panel:
	@curl -sf "http://localhost:8000/api/panelapp/panel/$(PANEL_ID)?only_green=$(GREEN)" | jq .

# =========================
# Guidelines (NICE / CKS / WHO / CDC / VA-DoD)
# =========================
GUIDE_SRC_KEY     ?= nice
GUIDE_DOC_KEY     ?= NG220
GUIDE_TITLE       ?=
GUIDE_URL         ?=
GUIDE_PDF         ?=
GUIDE_DATA_DIR    ?= data/nice
GUIDE_EMBED_MODEL ?= text-embedding-3-small

guidelines-schema:
	@echo ">>> Creating guidelines schema + provenance columns"
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/setup_guidelines_schema.sql
	@echo ">>> Done."

guidelines-load:
	@test -n "$(GUIDE_PDF)" || (echo "ERROR: set GUIDE_PDF=path/to/file.pdf" ; exit 1)
	@echo ">>> Loading $(GUIDE_SRC_KEY):$(GUIDE_DOC_KEY) from $(GUIDE_PDF)"
	@$(PY) server/scripts/load_guideline_pdf.py \
		SRC_KEY="$(GUIDE_SRC_KEY)" \
		DOC_KEY="$(GUIDE_DOC_KEY)" \
		TITLE="$(GUIDE_TITLE)" \
		URL="$(GUIDE_URL)" \
		PDF="$(GUIDE_PDF)"
	@$(MAKE) guidelines-fts
	@$(MAKE) guidelines-embed WHERE="source='$(GUIDE_SRC_KEY)' AND (meta->>'doc_key')='$(GUIDE_DOC_KEY)' AND embedding IS NULL"
	@$(MAKE) guidelines-stats

guidelines-fts:
	@echo ">>> Refreshing FTS (ts) for guideline rows missing ts"
	@$(PSQL) -d $(DB_NAME) -c "\
UPDATE public.rag_corpus \
SET ts = to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(text,'')) \
WHERE source IN ('nice','cks','who_eml','cdc_opioid','va_dod') AND ts IS NULL;"

guidelines-embed:
	@echo ">>> Embedding guideline rows ($(GUIDE_EMBED_MODEL))"
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus \
	  --id-col id \
	  --text-col text \
	  --embedding-col embedding \
	  --model $(GUIDE_EMBED_MODEL) \
	  --batch 256 \
	  --where "$(if $(WHERE),$(WHERE),source IN ('nice','cks','who_eml','cdc_opioid','va_dod') AND embedding IS NULL)"
	@echo ">>> Embedding pass complete."

guidelines-stats:
	@$(PSQL) -d $(DB_NAME) -c "\
SELECT source, COUNT(*) AS n, \
       COUNT(*) FILTER (WHERE embedding IS NULL) AS no_emb \
FROM public.rag_corpus \
WHERE source IN ('nice','cks','who_eml','cdc_opioid','va_dod') \
GROUP BY 1 ORDER BY 2 DESC;"

guidelines-health:
	@$(PSQL) -d $(DB_NAME) -c "\
SELECT id, LEFT(title,100) AS title, meta->>'doc_key' AS doc_key, source \
FROM public.rag_corpus \
WHERE source IN ('nice','cks','who_eml','cdc_opioid','va_dod') \
ORDER BY id DESC LIMIT 10;"

guidelines-load-ng220:
	@$(MAKE) guidelines-load \
	  GUIDE_SRC_KEY=nice \
	  GUIDE_DOC_KEY=NG220 \
	  GUIDE_TITLE="Multiple sclerosis in adults: management (NG220)" \
	  GUIDE_URL="https://www.nice.org.uk/guidance/ng220/resources" \
	  GUIDE_PDF="$(GUIDE_DATA_DIR)/multiple-sclerosis-in-adults-management-pdf-66143828948677.pdf"

guidelines-load-ng65:
	@$(MAKE) guidelines-load \
	  GUIDE_SRC_KEY=nice \
	  GUIDE_DOC_KEY=NG65 \
	  GUIDE_TITLE="Spondyloarthritis in over 16s: diagnosis and management (NG65)" \
	  GUIDE_URL="https://www.nice.org.uk/guidance/ng65/resources" \
	  GUIDE_PDF="$(GUIDE_DATA_DIR)/spondyloarthritis-in-over-16s-diagnosis-and-management-pdf-1837575441349.pdf"

guidelines-load-ng193:
	@$(MAKE) guidelines-load \
	  GUIDE_SRC_KEY=nice \
	  GUIDE_DOC_KEY=NG193 \
	  GUIDE_TITLE="Chronic pain (primary/secondary) in over 16s: assessment & management (NG193)" \
	  GUIDE_URL="https://www.nice.org.uk/guidance/ng193/resources" \
	  GUIDE_PDF="$(GUIDE_DATA_DIR)/chronic-pain-primary-and-secondary-in-over-16s-assessment-of-all-chronic-pain-and-management-of-chronic-primary-pain-pdf-66142080468421.pdf"

guidelines-ingest-all-nice:
	@echo ">>> Batch ingest: $(GUIDE_DATA_DIR)/*.pdf"
	@set -e; \
	for f in $(GUIDE_DATA_DIR)/*.pdf; do \
	  dk=$$(basename "$$f" | sed -nE 's/.*(NG[0-9]{2,3}).*/\1/p'); \
	  if [ -z "$$dk" ]; then echo "!! Skip (no NG key): $$f"; continue; fi; \
	  echo ">>> Ingest $$dk  $$f"; \
	  $(MAKE) guidelines-load GUIDE_SRC_KEY=nice GUIDE_DOC_KEY="$$dk" GUIDE_PDF="$$f"; \
	done

# =========================
# Diagnostic Rules (ACR/EULAR)
# =========================
diagrules-schema:
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/setup_diagnostic_rules.sql

diagrules-import: diagrules-schema
	@$(PY) server/scripts/ingest_diagnostic_rules.py --file data/diagnostic_rules_seed.json

diagrules-list:
	@curl -s "http://localhost:8000/api/diagnostic_rules/list?q=$(Q)" | jq .

diagrules-apply-sample:
	@curl -s -X POST "http://localhost:8000/api/diagnostic_rules/mcdonald_2017/apply" \
	  -H 'Content-Type: application/json' \
	  -d '{"has_typical_cis":true,"mri_lesion_sites_positive":3,"clinical_evidence_multiple_sites":false,"simultaneous_gad_non_gad":false,"new_t2_or_gad_on_followup":true,"csf_oligoclonal_bands":false,"better_diagnosis_present":false,"progression_1_year":false,"spinal_cord_lesions":0,"brain_mri_consistent":false}' | jq .

diagrules-test:
	@PYTHONPATH=. $(PY) server/scripts/run_diagnostic_rule_tests.py

diagrules-rag-upsert:
	@$(PY) server/scripts/diagrules_rag_upsert.py

diagrules-embed:
	@echo ">>> Embedding ACR/EULAR rows"
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus --id-col id --text-col text --embedding-col embedding \
	  --model $(if $(GUIDE_EMBED_MODEL),$(GUIDE_EMBED_MODEL),text-embedding-3-small) \
	  --batch 256 \
	  --where "source='acr_eular' AND embedding IS NULL"
	@echo ">>> Embeddings up to date for ACR/EULAR"

diagrules-rag: diagrules-rag-upsert diagrules-embed

# =========================
# Backend control
# =========================
be-stop:
	@pkill -f "uvicorn.*server.api.app_postgres:app" || true

be-start:
	@mkdir -p /tmp
	@nohup $(PY) server/scripts/run_postgres_app.py > /tmp/uvicorn.out 2>&1 & \
	echo ">>> uvicorn started. Tail logs with: make be-logs"

be-restart: be-stop be-start
	@sleep 1
	@echo ">>> uvicorn restarted. Tail logs with: make be-logs"

be-hard-restart:
	@pkill -9 -f "uvicorn.*server.api.app_postgres:app" || true
	@pkill -9 -f "uvicorn.*api.app_postgres:app" || true
	@pkill -9 -f "uvicorn.*app_postgres:app" || true
	@pkill -9 -f "python .*run_postgres_app.py" || true
	@find server -name "__pycache__" -type d -exec rm -rf {} +
	@find server -name "*.pyc" -delete
	@$(MAKE) be-start

be-logs:
	@echo ">>> Tailing /tmp/uvicorn.out (Ctrl+C to stop)"
	@tail -n 200 -f /tmp/uvicorn.out

api-health:
	@curl -s http://localhost:8000/api/health | jq .

# =========================
# SNOMED, Orphanet, HPO
# =========================
api-loinc-search:
	@curl -s "http://localhost:8000/api/loinc/search?q=$(Q)&limit=$(LIMIT)" | jq .

api-loinc-concept:
	@curl -s "http://localhost:8000/api/loinc/term/$(LOINC_NUM)" | jq .

api-loinc-term:
	@curl -s "http://localhost:8000/api/loinc/term/$(LOINC_NUM)" | jq .

api-loinc-panel:
	@curl -s "http://localhost:8000/api/loinc/panel/$(LOINC_NUM)" | jq .

snomed-audit:
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema='ontology' AND (table_name ILIKE 'snomed%' OR table_name IN ('concepts', 'descriptions', 'relationships', 'refset_members')) ORDER BY 1,2;"

snomed-preview:
	@$(PY) server/scripts/ingest_snomed.py --root-dir data/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20250901T120000Z --dry-run

snomed-import:
	@$(PY) server/scripts/ingest_snomed.py --root-dir data/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20250901T120000Z

snomed-trgm-index:
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS desc_term_trgm ON ontology.descriptions USING gin (term gin_trgm_ops);"

api-snomed-search:
	@curl -s "http://localhost:8000/api/snomed/search?q=diabetes&limit=5" | jq .

api-snomed-concept:
	@curl -s "http://localhost:8000/api/snomed/concept/$(CID)" | jq .

api-snomed-map:
	@curl -s "http://localhost:8000/api/snomed/map/icd10cm/$(CID)" | jq .

api-snomed-stats:
	@curl -s "http://localhost:8000/api/snomed/stats" | jq .

orphanet-import:
	@. server/venv312/bin/activate && $(PY) server/scripts/ingest_orphanet.py $(if $(ZIP),--zip $(ZIP),) $(if $(DIR),--dir $(DIR),)

orphanet-indexes:
	@$(PSQL) -d $(DB_NAME) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS orphanet_dis_name_trgm ON ontology.orphanet_diseases USING gin (name gin_trgm_ops);"
	@$(PSQL) -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS orphanet_syn_syn_trgm  ON ontology.orphanet_synonyms USING gin (synonym gin_trgm_ops);"
	@$(PSQL) -d $(DB_NAME) -f server/scripts/add_orphanet_indexes.sql

api-orphanet-search:
	@curl -s "http://localhost:8000/api/orphanet/search?q=$(Q)&limit=$(LIMIT)" | jq .

api-orphanet-disease:
	@curl -s "http://localhost:8000/api/orphanet/disease/$(ORPHA)" | jq .

api-orphanet-stats:
	@curl -s "http://localhost:8000/api/orphanet/stats" | jq .

hpo-import:
	@$(PY) ontology_loaders/hpo/load_hpo_terms.py data/hpo/hp.json

hpo-links-import:
	@$(PY) ontology_loaders/hpo/load_hpo_disease_links.py data/hpo/phenotype.hpoa

api-hpo-search:
	@curl -s "http://localhost:8000/api/hpo/search?q=$(Q)&limit=$(LIMIT)" | jq .

api-hpo-term:
	@curl -s "http://localhost:8000/api/hpo/term/$(HPO)" | jq .

# =========================
# ClinGen Actionability
# =========================
act.router.smoke:
	@echo "??? Router smoke tests"
	@curl -s -H 'Accept: application/json' "http://localhost:8000/api/clingen/actionability/summary?limit=5" | head -c 400; echo
	@curl -s -H 'Accept: application/json' "http://localhost:8000/api/clingen/actionability/quick?limit=5" | head -c 400; echo

act.mv.rebuild:
	@echo "??? Rebuilding materialized view"
	@python server/scripts/setup_clingen_actionability.py

