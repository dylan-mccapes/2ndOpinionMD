# ===============================
# 2ndOpinionMD  Makefile (clean)
# ===============================

# -------- Basic Vars --------

# ---------- Defaults & Environment ----------
SYNC_DATABASE_URL ?= postgresql://2ndopinionmd@localhost:5432/2ndopinionmd
PY ?= server/venv312/bin/python

.PHONY: cdc-opioid-schema cdc-opioid-xref-schema cdc-opioid-xref-seed \            cdc-opioid-fetch cdc-opioid-parse cdc-opioid-rag-upsert \            cdc-opioid-embed cdc-opioid-ann cdc-opioid-stats cdc-opioid-smoke \            cdc-opioid-all

SHELL := /bin/zsh
.ONESHELL:
.SHELLFLAGS := -lc

# Ensure Homebrew + libpq in PATH (macOS)
export PATH := /opt/homebrew/bin:/opt/homebrew/sbin:/opt/homebrew/opt/libpq/bin:$(PATH)

FRONTEND_DIR          := frontend/react
FRONTEND_DEPLOY_PATH  := /opt/homebrew/var/www/2ndopinionmd
RELEASES_DIR          := /opt/homebrew/var/www/2ndopinionmd_releases
HOST                  := 2ndopinionmd.ai
# Prefer the project venv; fall back to python3 on PATH
PY                    ?= $(shell [ -x server/venv312/bin/python ] && echo server/venv312/bin/python || which python3)
EMBED_MAX_CHARS       ?= 6000
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

LISTS ?= 200
PROBES ?= 8

# -------- PHONY --------
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
# Database helpers
# =========================

db-audit:
	@echo "-- RAG by source" && \
	psql -d 2ndopinionmd -c "\
	SELECT source, COUNT(*) AS n_rows,\
	       COUNT(*) FILTER (WHERE embedding IS NULL) AS no_embed\
	FROM public.rag_corpus\
	GROUP BY 1 ORDER BY n_rows DESC;" && \
	echo "\n-- All user tables (exact)" && \
	psql -d 2ndopinionmd <<'SQL' \
		DO $$
		DECLARE r record;
		BEGIN
		CREATE TEMP TABLE tmp_counts(schema_name text, table_name text, exact_count bigint) ON COMMIT DROP;
		FOR r IN SELECT schemaname, relname FROM pg_stat_user_tables LOOP
			EXECUTE format('INSERT INTO tmp_counts SELECT %L, %L, count(*) FROM %I.%I', r.schemaname, r.relname, r.schemaname, r.relname);
		END LOOP;
		END$$;
		TABLE tmp_counts ORDER BY schema_name, table_name;
		SQL
	&& echo "\n-- ANN indexes on rag_corpus" && \
	psql -d 2ndopinionmd -c "\
	SELECT indexname, indexdef FROM pg_indexes\
	WHERE tablename='rag_corpus' AND indexname ~ 'embedding.*ann'\
	ORDER BY 1;"

# =========================
# OpenAPI (quick list)
# =========================
api-openapi:
	@{ curl -sf http://localhost:8000/api/openapi.json || curl -sf http://localhost:8000/openapi.json; } \
	| jq -r '.paths | keys[]' | sed 's/^/  /'

rag-search:
	@echo ">>> RAG search: q='$(Q)', source='$(SOURCE)', limit=$(LIMIT), probes=$(PROBES)"
	@curl -s "http://localhost:8000/api/rag/search?q=$(Q)&limit=$(LIMIT)&source=$(SOURCE)&probes=$(PROBES)" | jq .

rag-neighbors:
	@echo ">>> RAG neighbors: id=$(ID), source='$(SOURCE)', limit=$(LIMIT), probes=$(PROBES)"
	@curl -s "http://localhost:8000/api/rag/neighbors/$(ID)?limit=$(LIMIT)&source=$(SOURCE)&probes=$(PROBES)" | jq .

### =========================
### CDC Opioid (Guidelines)
### =========================

DB_DSN ?= $(SYNC_DATABASE_URL)
PSQL   = psql "$(DB_DSN)"

# 0) Schemas
cdc-opioid-rag-delete:
	-$(PSQL) -f database/sql/cdc_opioid_rag_delete.sql

# 4) Embed (uses script provided earlier)
neurolex-schema:
	@echo ">>> Creating NeuroLex schema/tables"
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/setup_neurolex_schema.sql
	@echo ">>> NeuroLex schema ready."

neurolex-indexes:
	@echo ">>> Ensuring NeuroLex indexes"
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS neurolex_label_fts ON ontology.neurolex USING gin (to_tsvector('english', label));"
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS neurolex_synonyms_trgm ON ontology.neurolex USING gin (synonyms gin_trgm_ops);"
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS neurolex_ann_value_prefix_idx ON ontology.neurolex_annotations (split_part(value, ':', 1), prop_label);"
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS neurolex_ann_value_fts ON ontology.neurolex_annotations USING gin (to_tsvector('english', value));"
	@echo ">>> NeuroLex indexes ensured."

neurolex-import-api:  ## Usage: make neurolex-import-api PARENT_ILX=ilx_XXXXX  OR  LABEL="neurological disorder"
	@test -n "$(SCICRUNCH_API_KEY)" || (echo "ERROR: export SCICRUNCH_API_KEY first"; exit 2)
	@if [ -z "$(PARENT_ILX)$(LABEL)" ]; then echo "ERROR: set PARENT_ILX=ilx_... or LABEL=\"...\""; exit 2; fi
	@echo ">>> Importing NeuroLex from InterLex (parent=$(PARENT_ILX), label=$(LABEL), size=$(SIZE), pages=$(PAGES))"
	@$(PY) server/scripts/ingest_neurolex.py \
	  $(if $(PARENT_ILX),--parent-ilx "$(PARENT_ILX)",) \
	  $(if $(LABEL),--label "$(LABEL)",) \
	  --size "$(if $(SIZE),$(SIZE),1000)" \
	  --pages "$(if $(PAGES),$(PAGES),50)"


neurolex-import-file: ## Usage: make neurolex-import-file FILE=data/neurolex_branch.jsonl
	@test -n "$(FILE)" || (echo "ERROR: set FILE=path/to/neurolex.jsonl"; exit 2)
	@echo ">>> Importing NeuroLex from file: $(FILE)"
	@$(PY) server/scripts/ingest_neurolex.py --mode file --file "$(FILE)"

neurolex-embed:  ## Embeds label+definition+synonyms into vec
	@echo ">>> Embedding NeuroLex rows (vec)"
	@$(PY) server/scripts/embed_table.py \
	  --table ontology.neurolex \
	  --id-col ilx_id \
	  --text-col label \
	  --extra-cols definition,synonyms \
	  --embedding-col vec \
	  --model $(if $(MODEL),$(MODEL),text-embedding-3-small) \
	  --batch 256 \
	  --where "vec IS NULL"
	@echo ">>> Embedding pass complete."

neurolex-stats:
	@$(PSQL) -d $(DB_NAME) -c "SELECT COUNT(*) AS terms FROM ontology.neurolex;"
	@$(PSQL) -d $(DB_NAME) -c "SELECT prop_label, COUNT(*) n FROM ontology.neurolex_annotations GROUP BY 1 ORDER BY n DESC LIMIT 10;"
	@$(PSQL) -d $(DB_NAME) -c "SELECT split_part(value,':',1) AS system, COUNT(*) n FROM ontology.neurolex_annotations WHERE prop_label='hasDbXref' GROUP BY 1 ORDER BY n DESC LIMIT 10;"

# --- NeuroLex (query mode) ---
neurolex-import-query:
	@echo ">>> Importing NeuroLex by query: '$(Q)' (size=$(SIZE), pages=$(PAGES))"
	@$(PY) server/scripts/ingest_neurolex_query.py \
		--query '$(Q)' \
		--size $(if $(SIZE),$(SIZE),500) \
		--pages $(if $(PAGES),$(PAGES),20)

neurolex-reindex:
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "\
		UPDATE ontology.neurolex SET ts = to_tsvector('english', \
		coalesce(label,'')||' '||coalesce(definition,'')||' '||coalesce(array_to_string(synonyms,' '),'')); \
		CREATE INDEX IF NOT EXISTS neurolex_ts_gin ON ontology.neurolex USING gin (ts); \
		ANALYZE ontology.neurolex;"

# (Optional) RAG upsert so NeuroLex appears in /api/diagnose retrieval too
neurolex-rag-upsert:
	@echo ">>> Upserting NeuroLex into rag_corpus via script"
	@$(PY) server/scripts/neurolex_rag_upsert.py $(if $(LIMIT),--limit $(LIMIT),)

neurolex-rag-upsert-since:
	@echo ">>> Upserting NeuroLex into rag_corpus since $(SINCE)"
	@$(PY) server/scripts/neurolex_rag_upsert.py --since "$(SINCE)" $(if $(LIMIT),--limit $(LIMIT),)

neurolex-rag-upsert-dry:
	@echo ">>> DRY RUN: NeuroLex → rag_corpus"
	@$(PY) server/scripts/neurolex_rag_upsert.py --dry-run $(if $(LIMIT),--limit $(LIMIT),)

# (Once router is mounted)
api-neurolex-search:
	@curl -s "http://localhost:8000/api/neurolex/search?q=$(Q)&limit=$(LIMIT)" | jq .

api-neurolex-term:
	@curl -s "http://localhost:8000/api/neurolex/term/$(ILX)" | jq .


neurolex-api-smoke:
	@echo ">>> NeuroLex API smoke"
	@curl -s "http://localhost:8000/api/neurolex/stats" | jq .
	@curl -s "http://localhost:8000/api/neurolex/search?q=optic&limit=5" | jq .

neurolex-rag-semantic:
	@test -n "$(Q)" || (echo "Usage: make neurolex-rag-semantic Q='your query' [LIMIT=10] [PROBES=8]"; exit 2)
	@echo ">>> Semantic search (NeuroLex) for: '$(Q)'"
	@EMB=$$($(PY) - <<'PY'
		import os, sys
		from dotenv import load_dotenv
		load_dotenv('server/.env'); load_dotenv('.env')
		from openai import OpenAI
		client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
		q = os.environ.get("Q") or ""
		if not q:
			sys.exit("Missing Q")
		resp = client.embeddings.create(model="text-embedding-3-small", input=q)
		vec = resp.data[0].embedding
		print("[" + ",".join(f"{x:.6f}" for x in vec) + "]", end="")
		PY
	); \
	PROBES=$${PROBES:-8}; \
	LIMIT=$${LIMIT:-10}; \
	psql -d $(DB_NAME) -v ON_ERROR_STOP=1 <<SQL
		SET ivfflat.probes = $${PROBES};
		WITH q AS (SELECT '$$EMB'::vector AS e)
		SELECT id, source, LEFT(title,120) AS title,
			ROUND(1 - (embedding <=> q.e)::numeric, 4) AS cosine_sim
		FROM public.rag_corpus, q
		WHERE source='neurolex'
		ORDER BY embedding <=> q.e
		LIMIT $$LIMIT;
		SQL


# Build ANN index only for NeuroLex rows
neurolex-ann-index:
	@echo ">>> Creating ANN index for NeuroLex embeddings (lists=$(LISTS))"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "SET maintenance_work_mem='256MB';"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX CONCURRENTLY IF NOT EXISTS rag_corpus_embedding_ann_neurolex ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists = $(LISTS)) WHERE source='neurolex';"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "ANALYZE public.rag_corpus;"

# Explain a random NeuroLex semantic query to confirm ANN usage
neurolex-ann-explain:
	@echo ">>> EXPLAIN ANALYZE (probes=$(PROBES))"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "SET enable_seqscan=off; SET ivfflat.probes=$(PROBES); EXPLAIN ANALYZE WITH q AS (SELECT embedding e FROM public.rag_corpus WHERE source='neurolex' ORDER BY random() LIMIT 1) SELECT id, LEFT(title,120) AS title FROM public.rag_corpus rc, q WHERE rc.source='neurolex' ORDER BY rc.embedding <=> q.e LIMIT 5;"

# Quick smoke test for nearest neighbors among NeuroLex rows
neurolex-ann-smoke:
	@echo ">>> Semantic smoke test (probes=$(PROBES))"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "SET ivfflat.probes=$(PROBES); WITH q AS (SELECT embedding e FROM public.rag_corpus WHERE source='neurolex' ORDER BY random() LIMIT 1) SELECT id, LEFT(title,120) AS title, (rc.embedding <=> q.e) AS dist FROM public.rag_corpus rc, q WHERE rc.source='neurolex' ORDER BY rc.embedding <=> q.e LIMIT 5;"


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

# Expect:
#   PSQL ?= psql
#   DB_NAME ?= 2ndopinionmd
#   PY ?= server/venv312/bin/python
# Optional:
#   PIP ?= $(PY) -m pip

who-reqs:
	@$(PY) -m pip install --upgrade pandas openpyxl pypdf psycopg2-binary python-calamine

# ===== WHO EML (adults) =====
who-eml: who-eml-schema who-eml-import who-eml-rag who-eml-ann who-eml-api-smoke
	@echo ">>> WHO EML pipeline complete."

who-eml-schema:
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/guidelines_who_eml.sql

who-eml-import:
	@FILE="$${FILE:-data/who/eml_2025.xlsx}"; \
	echo ">>> Importing $$FILE"; \
	$(PY) server/scripts/who_eml_import.py --file "$$FILE"

who-eml-rag: who-eml-rag-upsert who-eml-embed
	@echo ">>> WHO EML → RAG complete."

who-eml-rag-upsert:
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f server/scripts/rag_upsert_who_eml.sql

who-eml-embed:
	@$(PY) server/scripts/embed_table.py \
		--table public.rag_corpus --id-col id --text-col text \
		--embedding-col embedding --model text-embedding-3-small \
		--batch 256 --where "source='who_eml' AND embedding IS NULL"

who-eml-ann:
	@$(PSQL) -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_who_eml ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists=200) WHERE source='who_eml'; ANALYZE public.rag_corpus;"

who-eml-api-smoke:
	@echo ">>> WHO EML endpoints"
	@curl -s http://localhost:8000/api/openapi.json | jq -r '.paths | keys[] | select(test("^/api/who"))'
	@echo ">>> Stats"
	@curl -s "http://localhost:8000/api/who/eml/stats" | jq .
	@echo ">>> Search amoxicillin (5)"
	@curl -s "http://localhost:8000/api/who/eml/search?q=amoxicillin&limit=5" | jq -c 'length'

# ===== WHO Expert Committee (executive summary PDF) =====
who-committee: who-committee-import who-committee-rag who-committee-ann who-committee-api-smoke
	@echo ">>> WHO Committee pipeline complete."

who-committee-import:
	@PDF="$${FILE:-data/who/expert_committee_2025_execsum.pdf}"; \
	echo ">>> Parsing $$PDF"; \
	$(PY) server/scripts/who_committee_import.py \
		--pdf "$$PDF" --year "$${YEAR:-2025}" --eml "$${EML:-24}" --emlc "$${EMLC:-10}" \
		--title "$${TITLE:-The selection and use of essential medicines, 2025: report of the 25th WHO Expert Committee}"

who-committee-rag: who-committee-rag-upsert who-committee-embed
	@echo ">>> WHO Committee → RAG complete."

who-committee-rag-upsert:
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f server/scripts/rag_upsert_who_committee.sql

who-committee-embed:
	@$(PY) server/scripts/embed_table.py \
		--table public.rag_corpus --id-col id --text-col text \
		--embedding-col embedding --model text-embedding-3-small \
		--batch 256 --where "source='who_committee' AND embedding IS NULL"

who-eml-embed-missing:
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus --id-col id --text-col text \
	  --embedding-col embedding --model text-embedding-3-small \
	  --batch 256 --where "source='who_eml' AND embedding IS NULL"


# ==== WHO AWaRe ====

PY?=server/venv312/bin/python

who-aware-import:
	$(PY) server/scripts/who_aware_import.py --file $(FILE) $(if $(SHEET),--sheet '$(SHEET)',)


who-aware-apply:
	psql "$(SYNC_DATABASE_URL)" -f server/scripts/who_eml_apply_aware.sql

who-aware-smoke:
	@echo ">>> AWaRe stats (J01 only)"
	curl -s "http://localhost:8000/api/who/aware/stats" | jq .
	@echo ">>> Access sample"
	curl -s "http://localhost:8000/api/who/eml/by-aware/Access?limit=10" | jq .

who-eml-smoke:
	@echo ">>> EML stats"
	curl -s http://localhost:8000/api/who/eml/stats | jq .
	@echo ">>> Search amoxicillin (aware=Access)"
	curl -s "http://localhost:8000/api/who/eml/search?q=amoxicillin&aware=Access&limit=5" | jq .

who-committee-chunk:
	psql "$(SYNC_DATABASE_URL)" -f server/scripts/rag_upsert_who_committee_chunked.sql

who-committee-embed-safe:
	env EMBED_MAX_CHARS=$(EMBED_MAX_CHARS) \
	$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus --id-col id --text-col text \
	  --embedding-col embedding --model text-embedding-3-small \
	  --batch $(BATCH) --where "source='who_committee' AND embedding IS NULL"

who-committee-ann:
	psql "$(SYNC_DATABASE_URL)" -c "CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_who_committee ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists=200) WHERE source='who_committee'; ANALYZE public.rag_corpus;"

who-committee-api-smoke:
	@echo ">>> Sections count"
	curl -s http://localhost:8000/api/who/committee/stats | jq .
	@echo ">>> Search insulin (3)"
	curl -s "http://localhost:8000/api/who/committee/search?q=insulin&limit=3" | jq .


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

disgenet-finish:
	@server/scripts/disgenet_finish.sh data/autoimmune_gene_ids.clean

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

# ---------- CDC Opioid: fetch → parse → RAG upsert → embed → ANN → stats ----------

cdc-opioid-schema:
	psql "$${SYNC_DATABASE_URL}" -f database/schemas/setup_cdc_opioid.sql

cdc-opioid-xref-schema:
	psql "$${SYNC_DATABASE_URL}" -f database/schemas/setup_cdc_opioid_xref.sql

cdc-opioid-xref-seed:
	test -f data/cdc_opioid/seed_section_codes.csv
	psql "$${SYNC_DATABASE_URL}" -v ON_ERROR_STOP=1 -c "CREATE TEMP TABLE tmp_section_code_map (LIKE guidelines.section_code_map INCLUDING ALL);"
	cat data/cdc_opioid/seed_section_codes.csv | psql "$${SYNC_DATABASE_URL}" -c "\copy tmp_section_code_map(section_id,system,code,display,how_derived,confidence) FROM STDIN WITH CSV HEADER"
	psql "$${SYNC_DATABASE_URL}" -v ON_ERROR_STOP=1 -c "\
	  INSERT INTO guidelines.section_code_map(section_id,system,code,display,how_derived,confidence) \
	  SELECT section_id,system,code,display,how_derived,confidence FROM tmp_section_code_map \
	  ON CONFLICT (section_id, system, code) DO UPDATE \
	    SET display=EXCLUDED.display, how_derived=EXCLUDED.how_derived, confidence=EXCLUDED.confidence;"
	psql "$${SYNC_DATABASE_URL}" -c "SELECT COUNT(*) FROM guidelines.v_cdc_section_codes;"

cdc-opioid-fetch:
	$(PY) server/scripts/cdc_opioid_fetch.py --out data/cdc_opioid

cdc-opioid-parse:
	$(PY) server/scripts/cdc_opioid_parse.py --in data/cdc_opioid

cdc-opioid-rag-upsert:
	psql "$${SYNC_DATABASE_URL}" -f database/sql/cdc_opioid_rag_upsert.sql

cdc-opioid-embed:
	SOURCE=cdc_opioid EMBED_MODEL=text-embedding-3-small $(PY) server/scripts/embed_rag_source.py
	psql "$${SYNC_DATABASE_URL}" -c "SELECT COUNT(*) total, COUNT(*) FILTER (WHERE embedding IS NULL) no_embed FROM public.rag_corpus WHERE source='cdc_opioid';"

cdc-opioid-ann:
	psql "$${SYNC_DATABASE_URL}" -c "CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_cdc \
	  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) \
	  WITH (lists = 64) WHERE source='cdc_opioid';"

cdc-opioid-stats:
	psql "$${SYNC_DATABASE_URL}" -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_embed FROM public.rag_corpus WHERE source='cdc_opioid' GROUP BY 1;"
	psql "$${SYNC_DATABASE_URL}" -c "SELECT COUNT(*) FROM guidelines.v_cdc_section_codes;"

cdc-opioid-smoke:
	curl -s http://localhost:8000/api/guidelines/cdc/opioid/health | jq .
	curl -s http://localhost:8000/api/guidelines/cdc/opioid/stats  | jq .
	curl -s "http://localhost:8000/api/guidelines/cdc/opioid/search?q=PDMP&limit=3" | jq .

# Full pipeline
cdc-opioid-all: cdc-opioid-schema cdc-opioid-xref-schema cdc-opioid-fetch cdc-opioid-parse cdc-opioid-rag-upsert cdc-opioid-embed cdc-opioid-ann cdc-opioid-stats cdc-opioid-smoke

### =========================
### VA/DoD GUIDELINES (Item 21)
### =========================
PY ?= server/venv312/bin/python
SYNC_DATABASE_URL ?= postgresql://2ndopinionmd@localhost:5432/2ndopinionmd

va-schema:
	psql "${SYNC_DATABASE_URL}" -f database/schemas/setup_va_guidelines.sql

# Seed mapping for VA (optional). Create a CSV at data/va/seed_section_codes.csv
va-fetch:
	${PY} server/scripts/va_guidelines_fetch.py --out data/va

va-parse:
	${PY} server/scripts/va_guidelines_parse.py --in data/va

va-rag-delete:
	psql "${SYNC_DATABASE_URL}" -f database/sql/va_guidelines_rag_delete.sql

va-rag-upsert:
	psql "${SYNC_DATABASE_URL}" -f database/sql/va_guidelines_rag_upsert.sql

va-embed:
	SOURCE=va_guidelines EMBED_MODEL=text-embedding-3-small ${PY} server/scripts/embed_rag_source.py
	psql "${SYNC_DATABASE_URL}" -c "SELECT COUNT(*) total, COUNT(*) FILTER (WHERE embedding IS NULL) no_embed FROM public.rag_corpus WHERE source='va_guidelines';"

va-ann:
	psql "${SYNC_DATABASE_URL}" -c "CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_va \
	  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) \
	  WITH (lists = 64) WHERE source='va_guidelines';"

va-stats:
	psql "${SYNC_DATABASE_URL}" -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_embed FROM public.rag_corpus WHERE source='va_guidelines' GROUP BY 1;"
	psql "${SYNC_DATABASE_URL}" -c "SELECT COUNT(*) FROM guidelines.va_docs;"
	psql "${SYNC_DATABASE_URL}" -c "SELECT COUNT(*) FROM guidelines.va_sections;"

va-smoke:
	curl -s http://localhost:8000/api/guidelines/va/health | jq .
	curl -s http://localhost:8000/api/guidelines/va/stats  | jq .
	curl -s "http://localhost:8000/api/guidelines/va/search?q=taper&limit=3" | jq .

va-all: va-schema va-xref-schema va-fetch va-parse va-rag-delete va-rag-upsert va-embed va-ann va-stats va-smoke
	@echo "VA/DoD ingestion complete."

# ---------- VA XREF ----------
# Fallback DB URL if SYNC_DATABASE_URL is not set
DB_URL := $${SYNC_DATABASE_URL:-postgresql://2ndopinionmd@localhost:5432/2ndopinionmd}

va-xref-schema:
	psql "$(DB_URL)" -f database/schemas/setup_va_guidelines_xref.sql

va-xref-seed:
	@test -f data/va/seed_section_codes.csv || (echo "Missing data/va/seed_section_codes.csv. Headers: section_id,system,code,display,how_derived,confidence" ; exit 1)
	# strip blank lines to avoid COPY empty-row errors
	sed -i.bak '/^[[:space:]]*$$/d' data/va/seed_section_codes.csv
	# persistent staging table so we can use multiple psql invocations
	psql "$(DB_URL)" -v ON_ERROR_STOP=1 -c "CREATE TABLE IF NOT EXISTS guidelines._va_codes_staging (LIKE guidelines.va_section_code_map INCLUDING DEFAULTS)"
	psql "$(DB_URL)" -v ON_ERROR_STOP=1 -c "TRUNCATE guidelines._va_codes_staging"
	# server-side COPY from STDIN (no \copy or heredoc headaches)
	psql "$(DB_URL)" -v ON_ERROR_STOP=1 -c "COPY guidelines._va_codes_staging(section_id,system,code,display,how_derived,confidence) FROM STDIN WITH CSV HEADER" < data/va/seed_section_codes.csv
	psql "$(DB_URL)" -v ON_ERROR_STOP=1 -c "INSERT INTO guidelines.va_section_code_map(section_id,system,code,display,how_derived,confidence) SELECT section_id, system, code, COALESCE(display,''), COALESCE(how_derived,'curated'), COALESCE(confidence,0.90) FROM guidelines._va_codes_staging ON CONFLICT (section_id, system, code) DO UPDATE SET display=EXCLUDED.display, how_derived=EXCLUDED.how_derived, confidence=EXCLUDED.confidence"

va-xref-preview:
	psql "$(DB_URL)" -c "SELECT * FROM guidelines.v_va_section_codes ORDER BY section_id LIMIT 10;"

va-xref-all: va-xref-schema va-xref-seed va-xref-preview

# ---- API smoke ---------------------------------------------------------------
API_BASE ?= http://localhost:8000

smoke-cdc:
	@echo "== CDC health =="
	curl -s "$(API_BASE)/api/guidelines/cdc/opioid/health" | jq .
	@echo "== CDC stats =="
	curl -s "$(API_BASE)/api/guidelines/cdc/opioid/stats" | jq .
	@echo "== CDC search: PDMP =="
	curl -s "$(API_BASE)/api/guidelines/cdc/opioid/search?q=PDMP&limit=3" | jq .

smoke-va:
	@echo "== VA health =="
	curl -s "$(API_BASE)/api/guidelines/va/health" | jq .
	@echo "== VA stats =="
	curl -s "$(API_BASE)/api/guidelines/va/stats" | jq .
	@echo "== VA search: taper =="
	curl -s "$(API_BASE)/api/guidelines/va/search?q=taper&limit=3" | jq .

smoke-all: smoke-cdc smoke-va


# ---------- DB Backup & Integrity ----------

DB_URL = $${SYNC_DATABASE_URL:-postgresql://2ndopinionmd@localhost:5432/2ndopinionmd}
JOBS ?= 0  # 0 means "auto" (script chooses ~ half cores)

.PHONY: db-backup db-backup-verify db-report db-report-json db-report-all

db-backup:
	@mkdir -p backups
	@chmod +x server/scripts/pg_backup.sh
	@JOBS=$(JOBS) server/scripts/pg_backup.sh "$(DB_URL)"

db-backup-verify:
	@chmod +x server/scripts/pg_backup_verify.sh
	@JOBS=$(JOBS) server/scripts/pg_backup_verify.sh backups/latest

db-report:
	@mkdir -p reports
	@psql "$(DB_URL)" -f database/sql/integrity_report.sql | tee reports/integrity_$$(date +%Y%m%d_%H%M%S).txt

db-report-json:
	@mkdir -p reports
	@psql -tA "$(DB_URL)" -f database/sql/integrity_report_json.sql > reports/integrity_$$(date +%Y%m%d_%H%M%S).json
	@echo "wrote JSON report to reports/"

db-report-all: db-report db-report-json

# ---- Integrity & Backup ------------------------------------------------------
SYNC_DATABASE_URL ?= postgresql://2ndopinionmd@localhost:5432/2ndopinionmd
PY ?= server/venv312/bin/python
NOW := $(shell date +%Y%m%d_%H%M%S)

integrity-report:
	@echo "== Integrity report (human-readable) =="
	psql "${SYNC_DATABASE_URL}" -f database/sql/integrity_report.sql

integrity-report-json:
	@echo "== Integrity report (JSON) =="
	psql "${SYNC_DATABASE_URL}" -f database/sql/integrity_report_json.sql

# quick embedded sanity checks
integrity-embeddings:
	@echo "== Embedding sanity =="
	psql "${SYNC_DATABASE_URL}" -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_embed FROM public.rag_corpus GROUP BY 1 ORDER BY 1;"
	psql "${SYNC_DATABASE_URL}" -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename='rag_corpus' AND indexname LIKE 'rag_corpus_embedding_ann_%';"

# orphan checks (sections without RAG rows) – CDC + VA
integrity-orphans:
	@echo "== CDC sections without rag rows =="
	psql "${SYNC_DATABASE_URL}" -c "SELECT s.section_id, s.doc_slug, s.heading FROM guidelines.cdc_sections s LEFT JOIN public.rag_corpus r ON r.source='cdc_opioid' AND r.external_id = s.section_id::text WHERE r.external_id IS NULL LIMIT 10;"
	@echo "== VA sections without rag rows =="
	psql "${SYNC_DATABASE_URL}" -c "SELECT s.section_id, s.doc_slug, s.heading FROM guidelines.va_sections s LEFT JOIN public.rag_corpus r ON r.source='va_guidelines' AND r.external_id = s.section_id::text WHERE r.external_id IS NULL LIMIT 10;"

integrity-all: integrity-report integrity-report-json integrity-embeddings integrity-orphans

# Backups (scripts you wrote)
backup-now:
	bash server/scripts/pg_backup.sh

backup-verify:
	bash server/scripts/pg_backup_verify.sh

post-launch-checks: integrity-all backup-verify
	@echo "✅ Post-launch checks complete."
