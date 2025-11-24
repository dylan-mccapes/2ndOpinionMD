# =========================================================
# 13) NICE Guidelines PDFs/HTML (+ 18 CKS under guidelines)
# =========================================================
GUIDE_EMBED_MODEL ?= text-embedding-3-small

guidelines-schema:
	@$(PSQL) -f database/schemas/setup_guidelines_schema.sql

guidelines-load:
	@test -n "$(GUIDE_PDF)" || (echo "Set GUIDE_PDF=path/to/file.pdf"; exit 1)
	@$(PY) server/scripts/load_guideline_pdf.py \
	  --src "$(GUIDE_SRC_KEY)" \
	  --doc "$(GUIDE_DOC_KEY)" \
	  --title "$(GUIDE_TITLE)" \
	  --url "$(GUIDE_URL)" \
	  "$(GUIDE_PDF)"
	@$(MAKE) guidelines-fts
	@$(MAKE) guidelines-chunk GUIDE_DOC_KEY="$(GUIDE_DOC_KEY)"
	@$(MAKE) guidelines-fts
	@$(MAKE) guidelines-embed-chunks WHERE="doc_id IN (SELECT id FROM guidelines.docs WHERE doc_key='$(GUIDE_DOC_KEY)') AND embedding IS NULL"
	@$(MAKE) guidelines-stats

guidelines-fts:
	@$(PSQL) -c "\
		UPDATE public.rag_corpus \
		SET ts = to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(text,'')) \
		WHERE source IN ('nice','cks','who_eml','cdc_opioid','va_guidelines') AND ts IS NULL;"
	@$(PSQL) -c "\
		UPDATE public.rag_corpus_chunks \
		SET ts = to_tsvector('english', COALESCE(title,'') || ' ' || COALESCE(text,'')) \
		WHERE ts IS NULL;"

guidelines-chunk:
	@$(PY) server/scripts/chunk_guidelines.py --sources "nice,cks" --min-len 8000 --size 3000 --overlap 300 $(if $(GUIDE_DOC_KEY),--doc-key $(GUIDE_DOC_KEY),)

guidelines-embed-chunks:
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus_chunks --id-col id --text-col text \
	  --embedding-col embedding --model $(GUIDE_EMBED_MODEL) \
	  --batch 256 --where "$(if $(WHERE),$(WHERE),embedding IS NULL)"

guidelines-embed-corpus:
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus --id-col id --text-col text \
	  --embedding-col embedding --model $(GUIDE_EMBED_MODEL) \
	  --batch 256 --where "$(if $(WHERE),$(WHERE),source IN ('nice','cks') AND embedding IS NULL AND length(text) <= 20000)"

guidelines-stats:
	@$(PSQL) -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_emb FROM public.rag_corpus WHERE source IN ('nice','cks') GROUP BY 1 ORDER BY 2 DESC;"

guidelines-health:
	@$(PSQL) -c "SELECT id, LEFT(title,100) title, meta->>'doc_key' doc_key, source FROM public.rag_corpus WHERE source IN ('nice','cks') ORDER BY id DESC LIMIT 10;"

# handy presets
guidelines-load-ng220:
	@$(MAKE) guidelines-load GUIDE_SRC_KEY=nice GUIDE_DOC_KEY=NG220 \
	  GUIDE_TITLE="Multiple sclerosis in adults: management (NG220)" \
	  GUIDE_URL="https://www.nice.org.uk/guidance/ng220/resources" \
	  GUIDE_PDF="data/nice/multiple-sclerosis-in-adults-management-pdf-66143828948677.pdf"

guidelines-load-ng65:
	@$(MAKE) guidelines-load GUIDE_SRC_KEY=nice GUIDE_DOC_KEY=NG65 \
	  GUIDE_TITLE="Spondyloarthritis in over 16s: diagnosis and management (NG65)" \
	  GUIDE_URL="https://www.nice.org.uk/guidance/ng65/resources" \
	  GUIDE_PDF="data/nice/spondyloarthritis-in-over-16s-diagnosis-and-management-pdf-1837575441349.pdf"

guidelines-load-ng193:
	@$(MAKE) guidelines-load GUIDE_SRC_KEY=nice GUIDE_DOC_KEY=NG193 \
	  GUIDE_TITLE="Chronic pain (NG193)" \
	  GUIDE_URL="https://www.nice.org.uk/guidance/ng193/resources" \
	  GUIDE_PDF="data/nice/chronic-pain-...-pdf-66142080468421.pdf"

guidelines-ingest-all-nice:
	@for f in data/nice/*.pdf; do \
	  dk=$$(basename "$$f" | sed -nE 's/.*(NG[0-9]{2,3}).*/\1/p'); \
	  [ -n "$$dk" ] && $(MAKE) guidelines-load GUIDE_SRC_KEY=nice GUIDE_DOC_KEY="$$dk" GUIDE_PDF="$$f"; \
	done

# ---------------- API smoke tests (Guidelines) ----------------
api-guidelines-ping:
	@echo "GET /api/guidelines/stats"
	@curl -sf "$(API_BASE)/api/guidelines/stats" | jq '.docs_by_source'
	@echo "GET /api/guidelines/docs?source=nice"
	@curl -sf "$(API_BASE)/api/guidelines/docs?source=nice" | jq '.[0]'

api-guidelines-doccheck:
	@docs=$$(curl -sf "$(API_BASE)/api/guidelines/docs?source=nice" | jq 'length'); \
	if [ "$$docs" -ge 1 ]; then echo "docs: OK ($$docs)"; else echo "!! docs: 0"; exit 4; fi

api-guidelines-sections:
	@test -n "$(DOC_KEY)" || (echo "Set DOC_KEY=NG220 (or similar)"; exit 2)
	@curl -sf "$(API_BASE)/api/guidelines/sections?doc_key=$(DOC_KEY)&limit=5" | jq '. | length'

api-guidelines-search:
	@q=$${Q:-relapse}; \
	lim=$${LIMIT:-5}; \
	curl -sf "$(API_BASE)/api/guidelines/search?q=$$q&limit=$$lim" | jq '. | length'

api-guidelines-smoke: api-guidelines-ping api-guidelines-doccheck
	@echo "✓ API guidelines smoke passed"

GUIDE_PY := server/scripts/ingest_guidelines_rheum.py

guidelines-rheum-ingest:
	$(PYTHON) $(GUIDE_PY)

guidelines-rheum-embed:
	# reuse your generic embed script to fill embeddings for each source
	$(PYTHON) server/scripts/embed_rag_source_async.py --source acr_ra_2021
	$(PYTHON) server/scripts/embed_rag_source_async.py --source eular_ra_2022
	$(PYTHON) server/scripts/embed_rag_source_async.py --source eular_acr_sle_2019
	$(PYTHON) server/scripts/embed_rag_source_async.py --source esc_ers_ph_2022
	$(PYTHON) server/scripts/embed_rag_source_async.py --source kdigo_gn_ln_2021
	$(PYTHON) server/scripts/embed_rag_source_async.py --source acr_ild_2023
	$(PYTHON) server/scripts/embed_rag_source_async.py --source nice_ta397_belimumab

RA_GUIDELINES_PDFS := $(wildcard data/ra_guidelines/*.pdf)

.PHONY: ra_guidelines.ingest
ra_guidelines.ingest: $(RA_GUIDELINES_PDFS)
	$(PYTHON) server/scripts/ingest_ra_guidelines.py

.PHONY: ra_guidelines.embed
ra_guidelines.embed:
	$(PYTHON) server/scripts/embed_rag_source_async.py --source ra_guidelines

# =========================================================
# GOLD 2024 – COPD guideline ingestion + embedding
# =========================================================

GOLD_PDF  := data/guidelines/gold-2024-report.pdf
GOLD_URL  := https://goldcopd.org/wp-content/uploads/2023/12/GOLD-2024_v1.1-1Dec2023_WMV.pdf
GOLD_SRC  := gold_copd_2024

.PHONY: guidelines-gold-download
guidelines-gold-download:
	@mkdir -p data/guidelines
	@if [ ! -f "$(GOLD_PDF)" ]; then \
	  echo "Downloading GOLD 2024 PDF..."; \
	  wget -O "$(GOLD_PDF)" "$(GOLD_URL)"; \
	else \
	  echo "GOLD 2024 PDF already present at $(GOLD_PDF)"; \
	fi

.PHONY: guidelines-gold-ingest
guidelines-gold-ingest:
	@test -f "$(GOLD_PDF)" || (echo "Missing $(GOLD_PDF) – run: make guidelines-gold-download"; exit 1)
	@$(PYTHON) server/scripts/ingest_guidelines_gold_copd_2024.py

.PHONY: guidelines-gold-embed
guidelines-gold-embed:
	@$(PYTHON) server/scripts/embed_rag_source_async.py --source $(GOLD_SRC)

.PHONY: guidelines-gold-stats
guidelines-gold-stats:
	@$(PSQL) -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_emb \
	             FROM rag_corpus WHERE source = '$(GOLD_SRC)' GROUP BY 1;"

.PHONY: guidelines-gold-all
guidelines-gold-all: guidelines-gold-ingest guidelines-gold-embed guidelines-gold-stats
	@echo "✓ GOLD 2024 ingestion + embeddings complete"

# =========================================================
# SSC 2021 – Sepsis guideline ingestion + embedding
# =========================================================

SSC_PDF  := data/guidelines/ssc-2021-sepsis.pdf
SSC_URL  := https://sepsis.ch/wp-content/uploads/2024/09/Surviving-Sepsis-Campaign_International-Guidelines-for-Management-of-Sepsis-and-Septic-Shock-2021.pdf
SSC_SRC  := ssc_sepsis_2021

.PHONY: guidelines-ssc-download
guidelines-ssc-download:
	@mkdir -p data/guidelines
	@if [ ! -f "$(SSC_PDF)" ]; then \
	  echo "Downloading SSC 2021 sepsis guideline PDF..."; \
	  wget -O "$(SSC_PDF)" "$(SSC_URL)"; \
	else \
	  echo "SSC 2021 PDF already present at $(SSC_PDF)"; \
	fi

.PHONY: guidelines-ssc-ingest
guidelines-ssc-ingest:
	@test -f "$(SSC_PDF)" || (echo "Missing $(SSC_PDF) – run: make guidelines-ssc-download"; exit 1)
	@$(PYTHON) server/scripts/ingest_guidelines_ssc_sepsis_2021.py

.PHONY: guidelines-ssc-embed
guidelines-ssc-embed:
	@$(PYTHON) server/scripts/embed_rag_source_async.py --source $(SSC_SRC)

.PHONY: guidelines-ssc-stats
guidelines-ssc-stats:
	@$(PSQL) -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_emb \
	             FROM rag_corpus WHERE source = '$(SSC_SRC)' GROUP BY 1;"

.PHONY: guidelines-ssc-all
guidelines-ssc-all: guidelines-ssc-ingest guidelines-ssc-embed guidelines-ssc-stats
	@echo "✓ SSC 2021 sepsis ingestion + embeddings complete"

# =========================================================
# AHA/ASA – Acute Ischemic Stroke guideline ingestion + embedding
# =========================================================

STROKE_PDF  := data/guidelines/aha-asa-stroke-2023.pdf
STROKE_URL  := https://www.ahajournals.org/doi/pdf/10.1161/STR.0000000000000406
STROKE_SRC  := aha_asa_stroke_2023

.PHONY: guidelines-stroke-download
guidelines-stroke-download:
	@mkdir -p data/guidelines
	@if [ ! -f "$(STROKE_PDF)" ]; then \
	  echo "Downloading AHA/ASA stroke guideline PDF..."; \
	  wget -O "$(STROKE_PDF)" "$(STROKE_URL)"; \
	else \
	  echo "AHA/ASA stroke PDF already present at $(STROKE_PDF)"; \
	fi

.PHONY: guidelines-stroke-ingest
guidelines-stroke-ingest:
	@test -f "$(STROKE_PDF)" || (echo "Missing $(STROKE_PDF) – run: make guidelines-stroke-download"; exit 1)
	@$(PYTHON) server/scripts/ingest_guidelines_aha_asa_stroke_2023.py

.PHONY: guidelines-stroke-embed
guidelines-stroke-embed:
	@$(PYTHON) server/scripts/embed_rag_source_async.py --source $(STROKE_SRC)

.PHONY: guidelines-stroke-stats
guidelines-stroke-stats:
	@$(PSQL) -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_emb \
	             FROM rag_corpus WHERE source = '$(STROKE_SRC)' GROUP BY 1;"

.PHONY: guidelines-stroke-all
guidelines-stroke-all: guidelines-stroke-ingest guidelines-stroke-embed guidelines-stroke-stats
	@echo "✓ AHA/ASA stroke ingestion + embeddings complete"

# ---------------- KDIGO 2024 CKD ----------------

guidelines-kdigo-ckd-download:
	@echo "Downloading KDIGO 2024 CKD guideline PDF..."
	@mkdir -p data/guidelines
	@wget -O data/guidelines/kdigo-2024-ckd.pdf \
	  "https://kdigo.org/wp-content/uploads/2024/03/KDIGO-2024-CKD-Guideline.pdf" || \
	  (echo "wget failed (likely 403). Download manually via browser as data/guidelines/kdigo-2024-ckd.pdf"; exit 0)

guidelines-kdigo-ckd-ingest:
	@$(PY) server/scripts/ingest_guidelines_kdigo_ckd_2024.py

guidelines-kdigo-ckd-embed:
	@$(PY) server/scripts/embed_rag_source_async.py --source kdigo_ckd_2024

guidelines-kdigo-ckd-stats:
	@$(PSQL) -c "\
	  SELECT source, COUNT(*) AS n, \
	         COUNT(*) FILTER (WHERE embedding IS NULL) AS no_emb \
	  FROM public.rag_corpus \
	  WHERE source = 'kdigo_ckd_2024' \
	  GROUP BY source;"


# =========================================================
# ACC/AHA/HFSA HF 2022 – Heart Failure guideline ingestion + embedding
# =========================================================

HF_2022_PDF = data/guidelines/acc-aha-hfsa-hf-2022.pdf

guidelines-hf-2022-download:
	@echo "Downloading 2022 ACC/AHA/HFSA HF guideline PDF..."
	@curl -L "https://www.ahajournals.org/doi/pdf/10.1161/CIR.0000000000001062" \
	  -D /tmp/hf2022_headers.txt \
	  -o data/guidelines/acc-aha-hfsa-hf-2022.pdf
	@grep -qi "^content-type: application/pdf" /tmp/hf2022_headers.txt || \
	  (echo "Download did not return a PDF (likely HTML / 403). Use browser download and save as data/guidelines/acc-aha-hfsa-hf-2022.pdf"; exit 1)

guidelines-hf-2022-ingest: $(HF_2022_PDF)
	python server/scripts/ingest_guidelines_acc_aha_hfsa_hf_2022.py

guidelines-hf-2022-embed:
	python server/scripts/embed_rag_source_async.py --source acc_aha_hfsa_hf_2022

guidelines-hf-2022-stats:
	psql -d 2ndopinionmd -c "SELECT source, COUNT(*) AS n, COUNT(*) FILTER (WHERE embedding IS NULL) AS no_emb FROM rag_corpus WHERE source = 'acc_aha_hfsa_hf_2022' GROUP BY source;"



guidelines-stroke2019-download:
	wget -O data/guidelines/aha_asa_stroke_2019_acute.pdf "https://stroke.ahajournals.org/content/strokeaha/50/12/e344.full.pdf" || true

guidelines-stroke2019-ingest:
	python server/scripts/ingest_guidelines_aha_asa_stroke_2019.py

guidelines-stroke2019-embed:
	python server/scripts/embed_rag_source_async.py --source aha_asa_stroke_2019_acute

guidelines-stroke2019-stats:
	psql -d 2ndopinionmd -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_emb FROM rag_corpus WHERE source='aha_asa_stroke_2019_acute' GROUP BY source;"


guidelines-sleln2025-ingest:
	python server/scripts/ingest_guidelines_eular_sle_nephritis_2025.py

guidelines-sleln2025-embed:
	python server/scripts/embed_rag_source_async.py --source eular_sle_nephritis_2025

guidelines-sleln2025-stats:
	psql -d 2ndopinionmd -c "SELECT source, COUNT(*) AS n, COUNT(*) FILTER (WHERE embedding IS NULL) AS no_emb FROM rag_corpus WHERE source='eular_sle_nephritis_2025' GROUP BY source;"