# ===============================
# 2ndOpinionMD  Makefile (clean)
# ===============================

# --- Vars ---
FRONTEND_DIR          := frontend/react
FRONTEND_DEPLOY_PATH  := /opt/homebrew/var/www/2ndopinionmd
RELEASES_DIR          := /opt/homebrew/var/www/2ndopinionmd_releases
HOST                  := 2ndopinionmd.ai
PY                    ?= server/venv312/bin/python
DB_NAME               ?= 2ndopinionmd

# MIMIC dirs
MIMIC3_DIR            ?= data/MIMIC-III
MIMIC4_DIR            ?= data/mimic-iv-2.2
MIMICIV_NOTE_DIR      ?= physionet.org/files/mimic-iv-note/2.2

# n2c2 sample
N2C2_T3_SAMPLE_DIR    ?= data/n2c2/track3-sample

.PHONY: \
	ship fe-build deploy-fe nginx-reload smoke verify-live rollback clean fe-clean \
	loinc-import rxnorm-import api-rxnorm-search api-rxnorm-drug api-rxnorm-ndc \
	rxnorm-trgm-index rxnorm-indexes \
	chv-setup chv-import chv-dry-run chv-search chv-fuzzy \
	mimic3-schema mimic4-schema mimic4-dry-run mimic4-import \
	api-m4-i50-hadm api-m4-any-hadm \
	mimic3-dry-run mimic3-import mimic3-stats mimic3-sanity \
	mimic3-notes-schema mimic3-notes-import \
	mimiciv-note-schema mimiciv-note-import mimiciv-note-dry mimiciv-note-stats \
	n2c2-t3-sample-schema n2c2-t3-sample-import n2c2-t3-sample-qa n2c2-t3-sample-reset n2c2-t3-sample-context n2c2-t3-backfill \
	be-stop be-start be-restart be-hard-restart be-logs api-health api-openapi \
	api-loinc-search api-loinc-concept \
	snomed-audit snomed-preview snomed-import snomed-trgm-index \
	api-snomed-search api-snomed-concept api-snomed-map api-snomed-stats \
	orphanet-import orphanet-indexes api-orphanet-search api-orphanet-disease api-orphanet-stats \
	hpo-import hpo-links-import api-hpo-search api-hpo-term

# -------------------------
# Frontend deploy helpers
# -------------------------
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

# -------------------------
# OpenAPI (single, robust)
# -------------------------
api-openapi:
	@{ curl -sf http://localhost:8000/api/openapi.json || curl -sf http://localhost:8000/openapi.json; } \
	| jq -r '.paths | keys[]' | sed 's/^/  /'

# -------------------------
# LOINC / RxNorm
# -------------------------
loinc-import:
	@echo ">>> LOINC import"
	@$(PY) server/scripts/ingest_loinc.py --zip-url $(ZIP_URL)

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
	@psql -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS rxnorm_conso_str_gin_idx ON ontology.rxnorm_conso USING gin (str gin_trgm_ops);"

rxnorm-indexes:
	@psql -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS rxnorm_ndc_norm_idx ON ontology.rxnorm_ndc (ndc_norm);"
	@psql -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS rxnorm_ndc_rxcui_idx ON ontology.rxnorm_ndc (rxcui);"
	@psql -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS rxnorm_conso_label_pick_idx ON ontology.rxnorm_conso (rxcui, sab, ispref, tty, str);"

# -------------------------
# CHV
# -------------------------
chv-setup:
	@psql -d $(DB_NAME) -f database/schemas/setup_chv_synonyms.sql

chv-import: chv-setup
	@$(PY) server/scripts/ingest_chv.py $(FILE)

chv-dry-run:
	@$(PY) server/scripts/ingest_chv.py --file $(FILE) --dry-run

chv-search:
	@psql -d $(DB_NAME) -c "SELECT term, cui \
	FROM ontology.synonyms \
	WHERE source='CHV' AND term ILIKE '%$${Q}%' \
	ORDER BY term \
	LIMIT $${LIMIT:-20};"

chv-fuzzy:
	@psql -d $(DB_NAME) -c "SET pg_trgm.similarity_threshold = 0.3; \
	SELECT term, cui, similarity(term, '$$Q') AS sim \
	FROM ontology.synonyms \
	WHERE source='CHV' AND term % '$$Q' \
	ORDER BY sim DESC \
	LIMIT $${LIMIT:-20};"

# -------------------------
# MIMIC schemas + loads
# -------------------------
mimic3-schema:
	@psql -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/ehr_mimic3.sql

mimic4-schema:
	@psql -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/ehr_mimic4.sql

mimic4-dry-run:
	@$(PY) server/scripts/ingest_mimic4.py --dir "$(MIMIC4_DIR)" --dry-run

mimic4-import:
	@$(PY) server/scripts/ingest_mimic4.py --dir "$(MIMIC4_DIR)"

# Valid MIMIC-IV HADM helpers
api-m4-i50-hadm:
	@psql -d $(DB_NAME) -c " \
	  SELECT hadm_id, COUNT(*) AS n \
	  FROM ehr_mimic4.diagnoses_icd \
	  WHERE icd_version = 10 AND icd_code LIKE 'I50%%' \
	  GROUP BY 1 ORDER BY n DESC \
	  LIMIT $${LIMIT:-20};"

api-m4-any-hadm:
	@psql -d $(DB_NAME) -Atc "SELECT hadm_id FROM ehr_mimic4.diagnoses_icd ORDER BY random() LIMIT 1" \
	| xargs -I{} sh -c 'echo HADM={}; curl -s "http://localhost:8000/api/mimic4/diagnoses?hadm_id={}" | jq .'

# --- MIMIC-III core ---
mimic3-dry-run:
	@$(PY) server/scripts/ingest_mimic3.py --dir "$(MIMIC3_DIR)" --dry-run

mimic3-import:
	@$(PY) server/scripts/ingest_mimic3.py --dir "$(MIMIC3_DIR)"

mimic3-stats:
	@psql -d $(DB_NAME) -c "SELECT 'patients' tbl, count(*) FROM ehr_mimic3.patients UNION ALL \
	                         SELECT 'admissions', count(*) FROM ehr_mimic3.admissions UNION ALL \
	                         SELECT 'icustays', count(*) FROM ehr_mimic3.icustays UNION ALL \
	                         SELECT 'diagnoses_icd', count(*) FROM ehr_mimic3.diagnoses_icd UNION ALL \
	                         SELECT 'procedures_icd', count(*) FROM ehr_mimic3.procedures_icd UNION ALL \
	                         SELECT 'labevents', count(*) FROM ehr_mimic3.labevents" | column -t

mimic3-sanity:
	@psql -d $(DB_NAME) -c "SELECT hadm_id, count(*) labs FROM ehr_mimic3.labevents GROUP BY hadm_id ORDER BY labs DESC NULLS LAST LIMIT 5;"
	@psql -d $(DB_NAME) -c "SELECT d.icd9_code, di.long_title, count(*) n FROM ehr_mimic3.diagnoses_icd d LEFT JOIN ehr_mimic3.d_icd_diagnoses di USING(icd9_code) GROUP BY 1,2 ORDER BY n DESC LIMIT 10;"

# --- MIMIC-III NOTEEVENTS -> text.mimic3_notes ---
mimic3-notes-schema:
	@psql -d $(DB_NAME) -c "\
CREATE SCHEMA IF NOT EXISTS text; \
CREATE TABLE IF NOT EXISTS text.mimic3_notes ( \
  row_id INTEGER PRIMARY KEY, subject_id INTEGER, hadm_id INTEGER, \
  chartdate DATE, charttime TIMESTAMP, storetime TIMESTAMP, \
  category TEXT, description TEXT, cgid INTEGER, iserror TEXT, text TEXT); \
CREATE INDEX IF NOT EXISTS mimic3_notes_hadm_idx    ON text.mimic3_notes(hadm_id); \
CREATE INDEX IF NOT EXISTS mimic3_notes_subject_idx ON text.mimic3_notes(subject_id);"

mimic3-notes-import: mimic3-notes-schema
	@psql -d $(DB_NAME) -c "\copy text.mimic3_notes (row_id,subject_id,hadm_id,chartdate,charttime,storetime,category,description,cgid,iserror,text) \
FROM PROGRAM 'gzip -dc physionet.org/files/mimiciii/1.4/NOTEEVENTS.csv.gz' WITH (FORMAT csv, HEADER true)"

# --- MIMIC-IV-Note (v2.2) ---
mimiciv-note-schema:
	@psql -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/text_mimiciv_notes.sql

mimiciv-note-import: mimiciv-note-schema
	@$(PY) server/scripts/ingest_mimiciv_notes.py --dir "$(MIMICIV_NOTE_DIR)"

mimiciv-note-dry: mimiciv-note-schema
	@$(PY) server/scripts/ingest_mimiciv_notes.py --dir "$(MIMICIV_NOTE_DIR)" --limit 500

mimiciv-note-stats:
	@psql -d $(DB_NAME) -c "SELECT domain, COUNT(*) AS n FROM text.mimiciv_notes GROUP BY 1 ORDER BY 1;"
	@psql -d $(DB_NAME) -c "SELECT SUM((hadm_id IS NOT NULL AND a.hadm_id IS NULL)::int) AS hadm_not_in_admissions, SUM((hadm_id IS NULL)::int) AS hadm_null FROM text.mimiciv_notes n LEFT JOIN ehr_mimic4.admissions a USING (hadm_id);"

# --- n2c2 Track 3 (sample) ---
n2c2-t3-sample-schema:
	@psql -v ON_ERROR_STOP=1 -d $(DB_NAME) -c "\i database/schemas/text_n2c2_track3.sql"

n2c2-t3-sample-reset:
	@psql -d $(DB_NAME) -c "DELETE FROM text.n2c2_notes WHERE track='2022-T3' AND filename IN ('n2c2_sample_raw.csv','n2c2_sample.csv');"

n2c2-t3-backfill:
	@psql -d $(DB_NAME) -c "UPDATE text.n2c2_notes n SET note_text = m.text FROM text.mimic3_notes m WHERE n.track='2022-T3' AND n.external_id = m.row_id::text;"

# --- n2c2 Track3 (schema + sample + silver) -----------------------------------

N2C2_T3_SAMPLE_DIR ?= data/n2c2/track3-sample

n2c2-schema:
	@psql -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/text_n2c2_track3.sql

n2c2-t3-sample-import: n2c2-schema
	@$(PY) server/scripts/ingest_n2c2_t3_sample.py --base $(N2C2_T3_SAMPLE_DIR)

n2c2-t3-sample-qa:
	@psql -d $(DB_NAME) -c "SELECT COUNT(*) AS notes FROM text.n2c2_notes WHERE track='2022-T3';"
	@psql -d $(DB_NAME) -c "SELECT section_name, COUNT(*) FROM text.n2c2_ap_sections GROUP BY 1 ORDER BY 1;"
	@psql -d $(DB_NAME) -c "SELECT label, COUNT(*) FROM text.n2c2_ap_relations GROUP BY 1 ORDER BY 2 DESC;"

n2c2-t3-sample-context: ## Show example A&P snippets
	@psql -d $(DB_NAME) -c "\
SELECT rel_id, label, assessment, plan_item \
FROM text.v_n2c2_ap_pairs \
WHERE track = '2022-T3' \
LIMIT 5;"

# Silver extraction from MIMIC-III / MIMIC-IV-Note
n2c2-ap-extract-m3: n2c2-schema
	@$(PY) server/scripts/extract_ap_pairs_from_mimic.py --source m3 --limit $${LIMIT:-20000} --track MIII-AP

n2c2-ap-extract-miv: n2c2-schema
	@$(PY) server/scripts/extract_ap_pairs_from_mimic.py --source miv --domain discharge --limit $${LIMIT:-20000} --track MIV-AP

# Quick QA + export
# --- A&P extraction QA ---
n2c2-ap-qa: ## Counts for notes/sections/relations (by track)
	@psql -d $(DB_NAME) -c "SELECT track, COUNT(*) AS notes FROM text.n2c2_notes GROUP BY 1 ORDER BY 1;"
	@psql -d $(DB_NAME) -c "SELECT s.section_name, COUNT(*) FROM text.n2c2_ap_sections s GROUP BY 1 ORDER BY 1;"
	@psql -d $(DB_NAME) -c "\
SELECT n.track, COUNT(*) AS rels \
FROM text.n2c2_ap_relations r \
JOIN text.n2c2_notes n USING (note_id) \
GROUP BY 1 ORDER BY 1;"

n2c2-export-gold:
	@psql -d $(DB_NAME) -c "\copy (SELECT * FROM text.v_n2c2_ap_pairs WHERE track='2022-T3') TO 'data/n2c2/train_gold.csv' CSV HEADER"

n2c2-export-silver-m3:
	@psql -d $(DB_NAME) -c "\copy (SELECT * FROM text.v_n2c2_ap_pairs WHERE track='MIII-AP') TO 'data/n2c2/train_silver_m3.csv' CSV HEADER"

n2c2-export-silver-miv:
	@psql -d $(DB_NAME) -c "\copy (SELECT * FROM text.v_n2c2_ap_pairs WHERE track='MIV-AP') TO 'data/n2c2/train_silver_miv.csv' CSV HEADER"

.PHONY: panelapp-schema panelapp-indexes panelapp-import \
        api-panelapp-search api-panelapp-panel api-panelapp-stats

# --- PanelApp schema + indexes ---
panelapp-schema:
	@psql -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/012_panelapp_gene_panels.sql

panelapp-indexes:  ## (schema already creates these; safe to re-run)
	@psql -d $(DB_NAME) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@psql -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS gp_panel_name_trgm ON molecular.gene_panels USING gin (panel_name gin_trgm_ops);"
	@psql -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS gp_gene_symbol_trgm ON molecular.gene_panels USING gin (gene_symbol gin_trgm_ops);"
	@psql -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS gp_ts_gin ON molecular.gene_panels USING gin (ts);"
	@psql -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS gp_signedoff_idx ON molecular.gene_panels (signed_off);"
	@psql -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS gp_panel_id_version_idx ON molecular.gene_panels (panel_id, panel_version);"

# --- PanelApp ingest ---
panelapp-import: panelapp-schema
	@echo ">>> Importing PanelApp signed-off panels (Motor Neuron Disease, MS Susceptibility)"
	@$(PY) server/scripts/panelapp_import.py
	@$(MAKE) panelapp-indexes

# --- API helpers ---
api-panelapp-search:
	@curl -s "http://localhost:8000/api/panelapp/search?q=$(Q)&limit=$(LIMIT)&only_green=$(GREEN)" | jq .

api-panelapp-panel:
	@curl -s "http://localhost:8000/api/panelapp/panel/$(PANEL_ID)?version=$(VERSION)&only_green=$(GREEN)" | jq .

api-panelapp-stats:
	@curl -s "http://localhost:8000/api/panelapp/stats" | jq .

panelapp-import-ids: panelapp-schema
	@echo ">>> Importing PanelApp by IDs: $(IDS)"
	@PANELAPP_VERIFY=$(VERIFY) PANELAPP_IDS="$(IDS)" PANELAPP_ALLOW_UNSIGNED=1 $(PY) server/scripts/panelapp_import.py
	@$(MAKE) panelapp-indexes

# --- PanelApp pipeline --------------------------------------------------------
panelapp-schema:
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -f database/schemas/012_panelapp_gene_panels.sql

panelapp-import:
	@echo ">>> Importing PanelApp signed-off targets ($(PANELAPP_PANELS))"
	@PANELAPP_PANELS="$(PANELAPP_PANELS)" $(PY) server/scripts/panelapp_import.py
	@$(MAKE) panelapp-indexes

panelapp-import-ids:
	@echo ">>> Importing PanelApp by IDs: $(IDS)"
	@PANELAPP_ALLOW_UNSIGNED=$(ALLOW_UNSIGNED) PANELAPP_IDS="$(IDS)" $(PY) server/scripts/panelapp_import.py
	@$(MAKE) panelapp-indexes

panelapp-indexes:
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gp_panel_name_trgm    ON molecular.gene_panels USING gin (panel_name gin_trgm_ops);"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gp_gene_symbol_trgm    ON molecular.gene_panels USING gin (gene_symbol gin_trgm_ops);"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gp_ts_gin             ON molecular.gene_panels USING gin (ts);"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gp_signedoff_idx      ON molecular.gene_panels (signed_off);"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS gp_panel_id_version_idx ON molecular.gene_panels (panel_id, panel_version);"

panelapp-rag-upsert:
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "\
INSERT INTO public.rag_corpus (source, title, text, ts) \
SELECT 'panelapp', \
       'Panel: '||panel_name||' — '||gene_symbol, \
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
  WHERE rc.source='panelapp' AND rc.title='Panel: '||gp.panel_name||' — '||gp.gene_symbol); \
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

# convenience API smoketests
api-panelapp-stats:
	@curl -s "http://localhost:8000/api/panelapp/stats" | jq .

api-panelapp-search:
	@curl -s "http://localhost:8000/api/panelapp/search?q=$(Q)&only_green=$(GREEN)" | jq .

api-panelapp-panel:
	@curl -sf "http://localhost:8000/api/panelapp/panel/$(PANEL_ID)?only_green=$(GREEN)" | jq .

# -------------------------
# Backend control
# -------------------------
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

# -------------------------
# SNOMED, Orphanet, HPO
# -------------------------
api-loinc-search:
	@curl -s "http://localhost:8000/api/loinc/search?q=$(Q)&limit=$(LIMIT)" | jq .

api-loinc-concept:
	@curl -s "http://localhost:8000/api/loinc/concept/$(LOINC_NUM)" | jq .

snomed-audit:
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema='ontology' AND (table_name ILIKE 'snomed%' OR table_name IN ('concepts', 'descriptions', 'relationships', 'refset_members')) ORDER BY 1,2;"

snomed-preview:
	@$(PY) server/scripts/ingest_snomed.py --root-dir data/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20250901T120000Z --dry-run

snomed-import:
	@$(PY) server/scripts/ingest_snomed.py --root-dir data/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20250901T120000Z

snomed-trgm-index:
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS desc_term_trgm ON ontology.descriptions USING gin (term gin_trgm_ops);"

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
	@psql -d $(DB_NAME) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@psql -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS orphanet_dis_name_trgm ON ontology.orphanet_diseases USING gin (name gin_trgm_ops);"
	@psql -d $(DB_NAME) -c "CREATE INDEX IF NOT EXISTS orphanet_syn_syn_trgm  ON ontology.orphanet_synonyms USING gin (synonym gin_trgm_ops);"
	@psql -d $(DB_NAME) -f server/scripts/add_orphanet_indexes.sql

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

