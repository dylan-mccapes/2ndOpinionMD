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

# Ensure the Make shell has Homebrew paths
SHELL := /bin/zsh
.SHELLFLAGS := -lc
export PATH := /opt/homebrew/bin:/opt/homebrew/sbin:/opt/homebrew/opt/libpq/bin:$(PATH)

# Pick a psql (first that exists)
PSQL ?= $(firstword \
  $(wildcard /opt/homebrew/bin/psql) \
  $(wildcard /opt/homebrew/opt/libpq/bin/psql) \
  $(shell command -v psql))

.PHONY: \
	ship fe-build deploy-fe nginx-reload smoke verify-live rollback clean fe-clean \
	loinc-schema loinc-indexes loinc-import loinc-smoke \
	rxnorm-import api-rxnorm-search api-rxnorm-drug api-rxnorm-ndc \
	rxnorm-trgm-index rxnorm-indexes \
	chv-setup chv-import chv-dry-run chv-search chv-fuzzy \
	mimic3-schema mimic4-schema mimic4-dry-run mimic4-import \
	api-m4-i50-hadm api-m4-any-hadm \
	mimic3-dry-run mimic3-import mimic3-stats mimic3-sanity \
	mimic3-notes-schema mimic3-notes-import \
	mimiciv-note-schema mimiciv-note-import mimiciv-note-dry mimiciv-note-stats \
	n2c2-t3-sample-schema n2c2-t3-sample-import n2c2-t3-sample-qa n2c2-t3-sample-reset n2c2-t3-sample-context n2c2-t3-backfill \
	be-stop be-start be-restart be-hard-restart be-logs api-health api-openapi \
	api-loinc-search api-loinc-concept api-loinc-term api-loinc-panel \
	snomed-audit snomed-preview snomed-import snomed-trgm-index \
	api-snomed-search api-snomed-concept api-snomed-map api-snomed-stats \
	orphanet-import orphanet-indexes api-orphanet-search api-orphanet-disease api-orphanet-stats \
	hpo-import hpo-links-import api-hpo-search api-hpo-term \
	guidelines-schema guidelines-stats guidelines-fts guidelines-embed \
	guidelines-load guidelines-load-ng220 guidelines-load-ng65 guidelines-load-ng193 \
	guidelines-ingest-all-nice guidelines-health

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
loinc-schema:
	@echo ">>> Creating LOINC schema/tables"
	@psql -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/setup_loinc_schema.sql
	@echo ">>> LOINC schema ready."

loinc-indexes:
	@echo ">>> Ensuring LOINC trigram indexes (for fast ILIKE)"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS loinc_long_common_name_trgm ON ontology.loinc_terms USING gin (long_common_name gin_trgm_ops);"
	@psql -d $(DB_NAME) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS loinc_shortname_trgm        ON ontology.loinc_terms USING gin (shortname gin_trgm_ops);"

loinc-import:
	@echo ">>> LOINC import"
	@test -n "$(ZIP_URL)" || (echo "ERROR: set ZIP_URL=https://.../Loinc_YYYYMMDD.zip" ; exit 1)
	@$(MAKE) loinc-schema
	@$(PY) server/scripts/ingest_loinc.py --zip-url $(ZIP_URL)
	@$(MAKE) loinc-indexes

loinc-smoke:
	@psql -d $(DB_NAME) -c "SELECT loinc_num, shortname, system, scale_typ FROM ontology.loinc_terms WHERE loinc_num='2345-7';"
	@curl -s "http://localhost:8000/api/loinc/search?q=glucose&limit=5" | jq .
	@curl -s "http://localhost:8000/api/loinc/term/2345-7" | jq .
	@echo ">>> If the above calls return data, LOINC API wiring is good."

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

# convenience API smoketests
api-panelapp-stats:
	@curl -s "http://localhost:8000/api/panelapp/stats" | jq .

api-panelapp-search:
	@curl -s "http://localhost:8000/api/panelapp/search?q=$(Q)&only_green=$(GREEN)" | jq .

api-panelapp-panel:
	@curl -sf "http://localhost:8000/api/panelapp/panel/$(PANEL_ID)?only_green=$(GREEN)" | jq .

# -------------------------
# Guidelines (NICE / CKS / WHO / CDC / VA-DoD)
# -------------------------

GUIDE_SRC_KEY        ?= nice           # one of: nice, cks, who_eml, cdc_opioid, va_dod
GUIDE_DOC_KEY        ?= NG220          # e.g., NG220, NG65, NG193, or slug
GUIDE_TITLE          ?=                # optional override
GUIDE_URL            ?=                # optional override
GUIDE_PDF            ?=                # required for guidelines-load (path to local PDF)
GUIDE_DATA_DIR       ?= data/nice      # where you scp'd PDFs
GUIDE_EMBED_MODEL    ?= text-embedding-3-small

# 1) Schema (idempotent)
guidelines-schema:
	@echo ">>> Creating guidelines schema + provenance columns"
	@$(PSQL) -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/setup_guidelines_schema.sql
	@echo ">>> Done."

# 2) Load a single PDF into rag_corpus (and embed)
guidelines-load: ## Load one guideline PDF
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

# 3) Refresh FTS
guidelines-fts:
	@echo ">>> Refreshing FTS (ts) for guideline rows missing ts"
	@psql -d $(DB_NAME) -c "\
UPDATE public.rag_corpus \
SET ts = to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(text,'')) \
WHERE source IN ('nice','cks','who_eml','cdc_opioid','va_dod') AND ts IS NULL;"
	@echo ">>> FTS refresh complete."

# 4) Embed guideline rows
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

# 5) Stats / sanity
guidelines-stats:
	@psql -d $(DB_NAME) -c "\
SELECT source, COUNT(*) AS n, \
       COUNT(*) FILTER (WHERE embedding IS NULL) AS no_emb \
FROM public.rag_corpus \
WHERE source IN ('nice','cks','who_eml','cdc_opioid','va_dod') \
GROUP BY 1 ORDER BY 2 DESC;"

guidelines-health: ## sample rows
	@psql -d $(DB_NAME) -c "\
SELECT id, LEFT(title,100) AS title, meta->>'doc_key' AS doc_key, source \
FROM public.rag_corpus \
WHERE source IN ('nice','cks','who_eml','cdc_opioid','va_dod') \
ORDER BY id DESC LIMIT 10;"

# 6) Convenience: load your three NICE PDFs
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

# 7) Batch helper: ingest all PDFs in data/nice
guidelines-ingest-all-nice:
	@echo ">>> Batch ingest: $(GUIDE_DATA_DIR)/*.pdf"
	@set -e; \
	for f in $(GUIDE_DATA_DIR)/*.pdf; do \
	  dk=$$(basename "$$f" | sed -nE 's/.*(NG[0-9]{2,3}).*/\1/p'); \
	  if [ -z "$$dk" ]; then echo "!! Skip (no NG key): $$f"; continue; fi; \
	  echo ">>> Ingest $$dk  $$f"; \
	  $(MAKE) guidelines-load GUIDE_SRC_KEY=nice GUIDE_DOC_KEY="$$dk" GUIDE_PDF="$$f"; \
	done

.PHONY: diagrules-schema diagrules-import diagrules-list diagrules-apply-sample

diagrules-schema:
	@psql -v ON_ERROR_STOP=1 -d $(DB_NAME) -f database/schemas/setup_diagnostic_rules.sql

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

api-loinc-concept: ## kept for backward compat; calls /term under the hood
	@curl -s "http://localhost:8000/api/loinc/term/$(LOINC_NUM)" | jq .

api-loinc-term:
	@curl -s "http://localhost:8000/api/loinc/term/$(LOINC_NUM)" | jq .

api-loinc-panel:
	@curl -s "http://localhost:8000/api/loinc/panel/$(LOINC_NUM)" | jq .

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

