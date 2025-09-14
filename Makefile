# 2ndOpinionMD ??? minimal local Makefile (frontend only)
# Build from frontend/react and deploy to local nginx docroot

FRONTEND_DIR := frontend/react
FRONTEND_DEPLOY_PATH := /opt/homebrew/var/www/2ndopinionmd
RELEASES_DIR := /opt/homebrew/var/www/2ndopinionmd_releases
HOST := 2ndopinionmd.ai

.PHONY: ship fe-build deploy-fe nginx-reload smoke verify-live rollback clean fe-clean loinc-import

ship: fe-build deploy-fe nginx-reload ## Build FE, deploy, reload nginx

fe-build: ## Build production bundle
	@echo ">>> Building frontend"
	cd $(FRONTEND_DIR) && yarn install && CI= yarn build
	@echo ">>> Build complete at $(FRONTEND_DIR)/build"

deploy-fe: ## Rsync build to live + timestamped release
	@echo ">>> Deploying to $(FRONTEND_DEPLOY_PATH)"
	TS=$$(date +%F-%H%M); \
	sudo mkdir -p $(RELEASES_DIR)/$$TS; \
	sudo rsync -a --delete $(FRONTEND_DIR)/build/ $(RELEASES_DIR)/$$TS/; \
	sudo rsync -a --delete $(FRONTEND_DIR)/build/ $(FRONTEND_DEPLOY_PATH)/
	@echo ">>> Frontend deployed."

nginx-reload: ## Reload nginx
	@echo ">>> Reloading nginx"
	sudo nginx -t && sudo nginx -s reload
	@echo ">>> nginx reloaded."

smoke: ## Quick check
	@curl -sI https://$(HOST)/ | sed -n '1p;/etag/Ip;/last-modified/Ip'
	@curl -sf https://$(HOST)/api/health | jq . || curl -sf https://$(HOST)/api/health

verify-live: ## Verify live bundle has AI Analysis strings
	@JS=$$(curl -s https://$(HOST)/asset-manifest.json | jq -r '.files["main.js"]'); \
	echo "main bundle: $$JS"; \
	curl -s "https://$(HOST)$$JS" | strings | egrep -o "AI Analysis|Diagnoses|Environmental Factors|Life Stressors|Pattern Observations|Journaling Recommendation" | sort -u || true

rollback: ## make rollback REL=YYYY-MM-DD-HHMM
	@test -n "$(REL)" || (echo "Usage: make rollback REL=YYYY-MM-DD-HHMM" ; exit 1)
	sudo rsync -a --delete $(RELEASES_DIR)/$(REL)/ $(FRONTEND_DEPLOY_PATH)/
	sudo nginx -s reload

clean: fe-clean
	@echo ">>> Clean complete."

fe-clean:
	@echo ">>> Cleaning frontend build artifacts"
	rm -rf $(FRONTEND_DIR)/build

loinc-import: ## Import LOINC data from hosted ZIP URL
	@echo ">>> LOINC import"
	@python server/scripts/ingest_loinc.py --zip-url $(ZIP_URL)
# Usage: make loinc-import ZIP_URL=https://2ndopinionmd.ai/private/loinc-34efcd3d8beb/loinc.zip

rxnorm-import: ## Import RxNorm data from hosted ZIP URL
	@echo ">>> RxNorm import"
	@python server/scripts/ingest_rxnorm.py --zip-url $(ZIP_URL)
# Usage: make rxnorm-import ZIP_URL=https://2ndopinionmd.ai/private/rxnorm-token/rxnorm.zip

api-rxnorm-search: ## Test RxNorm search API
	@curl -s "http://localhost:8000/api/rxnorm/search?q=$(Q)&tty=$(TTY)&limit=$(LIMIT)" | jq .

api-rxnorm-drug: ## Test RxNorm drug lookup API
	@curl -s "http://localhost:8000/api/rxnorm/drug/$(RXCUI)" | jq .

api-rxnorm-ndc: ## Test RxNorm NDC lookup API
	@curl -s "http://localhost:8000/api/rxnorm/ndc/$(NDC)" | jq .

rxnorm-trgm-index: ## Ensure pg_trgm index on rxnorm_conso.str
	@echo ">>> Ensuring RxNorm trigram index"
	@psql -d 2ndopinionmd -c "CREATE INDEX IF NOT EXISTS rxnorm_conso_str_gin_idx ON ontology.rxnorm_conso USING gin (str gin_trgm_ops);"

rxnorm-indexes: ## Ensure all RxNorm indexes exist
	@echo ">>> Ensuring RxNorm indexes"
	@psql -d 2ndopinionmd -c "CREATE INDEX IF NOT EXISTS rxnorm_ndc_norm_idx ON ontology.rxnorm_ndc (ndc_norm);"
	@psql -d 2ndopinionmd -c "CREATE INDEX IF NOT EXISTS rxnorm_ndc_rxcui_idx ON ontology.rxnorm_ndc (rxcui);"
	@psql -d 2ndopinionmd -c "CREATE INDEX IF NOT EXISTS rxnorm_conso_label_pick_idx ON ontology.rxnorm_conso (rxcui, sab, ispref, tty, str);"

# --- CHV (Consumer Health Vocabulary) ---
chv-setup:
	@psql -d 2ndopinionmd -f database/schemas/setup_chv_synonyms.sql

chv-import: chv-setup ## Import CHV terms into ontology.synonyms
	@python server/scripts/ingest_chv.py $(FILE)

chv-dry-run: ## Parse-only CHV to see counts
	@python server/scripts/ingest_chv.py --file $(FILE) --dry-run

chv-search: ## Grep-like CHV search
	@psql -d 2ndopinionmd -c "SELECT term, cui \
	FROM ontology.synonyms \
	WHERE source='CHV' AND term ILIKE '%$${Q}%' \
	ORDER BY term \
	LIMIT $${LIMIT:-20};"

chv-fuzzy: ## Fuzzy CHV search with trigram
	@psql -d 2ndopinionmd -c "SET pg_trgm.similarity_threshold = 0.3; \
	SELECT term, cui, similarity(term, '$$Q') AS sim \
	FROM ontology.synonyms \
	WHERE source='CHV' AND term % '$$Q' \
	ORDER BY sim DESC \
	LIMIT $${LIMIT:-20};"
# ---- MIMIC (schemas) ----
# at top (or wherever you keep DB vars)
DB_NAME ?= 2ndopinionmd

mimic3-schema:
        @psql -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/ehr_mimic3.sql

mimic4-schema:
	@psql -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/ehr_mimic4.sql

# MIMIC-IV (v2.2) import
MIMIC4_DIR ?= data/mimic-iv-2.2

mimic4-dry-run:
	@python server/scripts/ingest_mimic4.py --dir $(MIMIC4_DIR) --dry-run

mimic4-import:
	@python server/scripts/ingest_mimic4.py --dir $(MIMIC4_DIR)

# --- MIMIC-III (v1.4) ---
MIMIC3_DIR ?= data/MIMIC-III

mimic3-dry-run: ## Validate files + ensure schema (no data load)
	@python server/scripts/ingest_mimic3.py --dir "$(MIMIC3_DIR)" --dry-run

mimic3-import: ## Load core structured tables
	@python server/scripts/ingest_mimic3.py --dir "$(MIMIC3_DIR)"

mimic3-stats:
	@psql -d 2ndopinionmd -c "SELECT 'patients' tbl, count(*) FROM ehr_mimic3.patients UNION ALL \
	                           SELECT 'admissions', count(*) FROM ehr_mimic3.admissions UNION ALL \
	                           SELECT 'icustays', count(*) FROM ehr_mimic3.icustays UNION ALL \
	                           SELECT 'diagnoses_icd', count(*) FROM ehr_mimic3.diagnoses_icd UNION ALL \
	                           SELECT 'procedures_icd', count(*) FROM ehr_mimic3.procedures_icd UNION ALL \
	                           SELECT 'labevents', count(*) FROM ehr_mimic3.labevents \
	                          " | column -t

mimic3-sanity: ## A couple of quick checks
	@psql -d 2ndopinionmd -c "SELECT hadm_id, count(*) labs FROM ehr_mimic3.labevents GROUP BY hadm_id ORDER BY labs DESC NULLS LAST LIMIT 5;"
	@psql -d 2ndopinionmd -c "SELECT d.icd9_code, di.long_title, count(*) n FROM ehr_mimic3.diagnoses_icd d LEFT JOIN ehr_mimic3.d_icd_diagnoses di USING(icd9_code) GROUP BY 1,2 ORDER BY n DESC LIMIT 10;"

# --- MIMIC-III NOTEEVENTS -> text.mimic3_notes ---
mimic3-notes-schema:
	@psql -d 2ndopinionmd -c "\
CREATE SCHEMA IF NOT EXISTS text; \
CREATE TABLE IF NOT EXISTS text.mimic3_notes ( \
	row_id INTEGER PRIMARY KEY, subject_id INTEGER, hadm_id INTEGER, \
	chartdate DATE, charttime TIMESTAMP, storetime TIMESTAMP, \
	category TEXT, description TEXT, cgid INTEGER, iserror TEXT, text TEXT); \
CREATE INDEX IF NOT EXISTS mimic3_notes_hadm_idx    ON text.mimic3_notes(hadm_id); \
CREATE INDEX IF NOT EXISTS mimic3_notes_subject_idx ON text.mimic3_notes(subject_id);"

mimic3-notes-import: mimic3-notes-schema ## Load NOTEEVENTS.csv.gz into text.mimic3_notes
	@psql -d 2ndopinionmd -c "\copy text.mimic3_notes (row_id,subject_id,hadm_id,chartdate,charttime,storetime,category,description,cgid,iserror,text) \
FROM PROGRAM 'gzip -dc physionet.org/files/mimiciii/1.4/NOTEEVENTS.csv.gz' WITH (FORMAT csv, HEADER true)"

# --- MIMIC-IV Note (free-text) ---
MIMICIV_NOTE_DIR ?= physionet.org/files/mimic-iv-note/2.2

mimiciv-note-schema:
	@psql -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/text_mimiciv_notes.sql

mimiciv-note-import: mimiciv-note-schema
	@. server/venv312/bin/activate && python server/scripts/ingest_mimiciv_note.py --dir "$(MIMICIV_NOTE_DIR)"

mimiciv-note-stats:
	@psql -d $(DB_NAME) -c "SELECT domain, COUNT(*) AS n FROM text.mimiciv_notes GROUP BY 1 ORDER BY 1;"
	@psql -d $(DB_NAME) -c "SELECT COUNT(*) AS with_hadm, SUM((hadm_id IS NULL)::int) AS hadm_null FROM text.mimiciv_notes;"

# A&P extraction (silver) from MIMIC-III and MIMIC-IV
n2c2-ap-extract-m3:
	@. server/venv312/bin/activate && python server/scripts/extract_ap_pairs_from_mimiciv.py --source m3 --limit $${LIMIT:-20000}

n2c2-ap-extract-m4:
	@. server/venv312/bin/activate && python server/scripts/extract_ap_pairs_from_mimiciv.py --source m4 --limit $${LIMIT:-20000}

n2c2-ap-qa:
	@psql -d $(DB_NAME) -c "SELECT track, COUNT(*) notes FROM text.n2c2_notes GROUP BY 1 ORDER BY 1;"
	@psql -d $(DB_NAME) -c "SELECT section_name, COUNT(*) FROM text.n2c2_ap_sections GROUP BY 1 ORDER BY 1;"
	@psql -d $(DB_NAME) -c "SELECT label, COUNT(*) FROM text.n2c2_ap_relations GROUP BY 1 ORDER BY 2 DESC;"

# --- n2c2 Track 3 (A&P sample) ---
N2C2_T3_SAMPLE_DIR ?= data/n2c2/track3-sample

.PHONY: n2c2-t3-sample-schema n2c2-t3-sample-import n2c2-t3-sample-qa n2c2-t3-sample-reset n2c2-t3-sample-context

n2c2-t3-sample-schema: ## Ensure Track-3 schema is present
	@psql -v ON_ERROR_STOP=1 -d 2ndopinionmd -c "\i database/schemas/text_n2c2_track3.sql"

n2c2-t3-sample-import: n2c2-t3-sample-schema ## Import sample (raw notes + offsets)
	@$(PY) server/scripts/ingest_n2c2_t3_sample.py --base $(N2C2_T3_SAMPLE_DIR)

n2c2-t3-sample-qa: ## Counts for notes/sections/relations
	@psql -d 2ndopinionmd -c "SELECT COUNT(*) AS notes FROM text.n2c2_notes WHERE track='2022-T3';"
	@psql -d 2ndopinionmd -c "SELECT section_name, COUNT(*) FROM text.n2c2_ap_sections GROUP BY 1 ORDER BY 1;"
	@psql -d 2ndopinionmd -c "SELECT label, COUNT(*) FROM text.n2c2_ap_relations GROUP BY 1 ORDER BY 2 DESC;"

n2c2-t3-sample-reset: ## Remove only the sample rows so re-imports are clean
	@psql -d 2ndopinionmd -c "DELETE FROM text.n2c2_notes WHERE track='2022-T3' AND filename IN ('n2c2_sample_raw.csv','n2c2_sample.csv');"

n2c2-t3-sample-context: ## Show example A&P snippets
	@psql -d 2ndopinionmd -c "\
WITH r AS ( \
  SELECT r.rel_id, r.label, n.note_text, a.span_start a_s, a.span_end a_e, p.span_start p_s, p.span_end p_e \
  FROM text.n2c2_ap_relations r \
  JOIN text.n2c2_ap_sections a ON a.section_id=r.assess_id \
  JOIN text.n2c2_ap_sections p ON p.section_id=r.plan_id \
  JOIN text.n2c2_notes n ON n.note_id=r.note_id \
  LIMIT 5 \
) \
SELECT rel_id, label, \
       substr(note_text, a_s+1, a_e-a_s) AS assessment, \
       substr(note_text, p_s+1, p_e-p_s) AS plan_item \
FROM r;"

n2c2-t3-backfill: ## Fill 2022-T3 notes from mimic3 by ROW_ID
	@psql -d 2ndopinionmd -c "UPDATE text.n2c2_notes n SET note_text = m.text FROM text.mimic3_notes m WHERE n.track='2022-T3' AND n.external_id = m.row_id::text;"

# --- Backend control ---
be-stop: ## Stop backend server
	@pkill -f "uvicorn.*server.api.app_postgres:app" || true

be-start: ## Start backend server
	@mkdir -p /tmp
	@nohup python server/scripts/run_postgres_app.py > /tmp/uvicorn.out 2>&1 & \
	echo ">>> uvicorn started. Tail logs with: make be-logs"

be-restart: be-stop be-start ## Restart backend server
	@sleep 1
	@echo ">>> uvicorn restarted. Tail logs with: make be-logs"

be-hard-restart:
	@pkill -9 -f "uvicorn.*server.api.app_postgres:app" || true
	@find server -name "__pycache__" -type d -exec rm -rf {} +
	@find server -name "*.pyc" -delete
	@$(MAKE) be-start

be-logs: ## Tail backend logs
	@echo ">>> Tailing /tmp/uvicorn.out (Ctrl+C to stop)"
	@tail -n 200 -f /tmp/uvicorn.out

api-health: ## Test API health endpoint
	@curl -s http://localhost:8000/api/health | jq .

api-openapi: ## List API endpoints from OpenAPI spec
	@curl -s http://localhost:8000/api/openapi.json | jq '.paths | keys[]' | sed 's/^/  /'

api-loinc-search: ## Test LOINC search API
	@curl -s "http://localhost:8000/api/loinc/search?q=$(Q)&limit=$(LIMIT)" | jq .

api-loinc-concept: ## Test LOINC concept lookup API
	@curl -s "http://localhost:8000/api/loinc/concept/$(LOINC_NUM)" | jq .

# SNOMED CT targets
snomed-audit: ## Audit existing SNOMED schema
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -c "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema='ontology' AND (table_name ILIKE 'snomed%' OR table_name IN ('concepts', 'descriptions', 'relationships', 'refset_members')) ORDER BY 1,2;"

snomed-preview: ## Preview SNOMED import (dry run)
	@python server/scripts/ingest_snomed.py --root-dir data/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20250901T120000Z --dry-run

snomed-import: ## Import SNOMED data from RF2 files
	@python server/scripts/ingest_snomed.py --root-dir data/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20250901T120000Z

snomed-trgm-index: ## Ensure pg_trgm index on descriptions.term
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS desc_term_trgm ON ontology.descriptions USING gin (term gin_trgm_ops);"

api-snomed-search: ## Test SNOMED search API
	@curl -s "http://localhost:8000/api/snomed/search?q=diabetes&limit=5" | jq .

api-snomed-concept: ## Test SNOMED concept lookup API
	@curl -s "http://localhost:8000/api/snomed/concept/$(CID)" | jq .

api-snomed-map: ## Test SNOMED ICD-10-CM mapping API
	@curl -s "http://localhost:8000/api/snomed/map/icd10cm/$(CID)" | jq .

api-snomed-stats: ## Test SNOMED statistics API
	@curl -s "http://localhost:8000/api/snomed/stats" | jq .

# --- Orphanet ---
orphanet-import: ## Import Orphanet from ZIP or DIR: make orphanet-import ZIP=... | DIR=...
	@. server/venv312/bin/activate && \
	python server/scripts/ingest_orphanet.py $(if $(ZIP),--zip $(ZIP),) $(if $(DIR),--dir $(DIR),)

orphanet-indexes: ## Ensure Orphanet search indexes
	@psql -d 2ndopinionmd -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@psql -d 2ndopinionmd -c "CREATE INDEX IF NOT EXISTS orphanet_dis_name_trgm ON ontology.orphanet_diseases USING gin (name gin_trgm_ops);"
	@psql -d 2ndopinionmd -c "CREATE INDEX IF NOT EXISTS orphanet_syn_syn_trgm  ON ontology.orphanet_synonyms USING gin (synonym gin_trgm_ops);"
	@psql -d 2ndopinionmd -f server/scripts/add_orphanet_indexes.sql

api-orphanet-search: ## Test Orphanet search
	@curl -s "http://localhost:8000/api/orphanet/search?q=$(Q)&limit=$(LIMIT)" | jq .

api-orphanet-disease: ## Test Orphanet detail
	@curl -s "http://localhost:8000/api/orphanet/disease/$(ORPHA)" | jq .

api-orphanet-stats: ## Test Orphanet statistics API
	@curl -s "http://localhost:8000/api/orphanet/stats" | jq .

# --- HPO ---
hpo-import: ## Import HPO terms (hp.json)
	@python ontology_loaders/hpo/load_hpo_terms.py data/hpo/hp.json

hpo-links-import: ## Import HPO disease links if separate
	@python ontology_loaders/hpo/load_hpo_disease_links.py data/hpo/phenotype.hpoa

api-hpo-search: ## Test HPO search
	@curl -s "http://localhost:8000/api/hpo/search?q=$(Q)&limit=$(LIMIT)" | jq .

api-hpo-term: ## Test HPO term
	@curl -s "http://localhost:8000/api/hpo/term/$(HPO)" | jq .

