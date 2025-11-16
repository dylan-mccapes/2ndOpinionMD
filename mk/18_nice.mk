# =========================
# 18) NICE Guidelines & CKS
# =========================
# Conventions:
# - Source keys live in guidelines.* tables: 'nice' (Guidance), 'cks' (CKS)
# - Targets use "nice-*" even when SRC=cks (override NICE_SRC)
#
# Common vars expected in your repo:
#   PSQL ?= psql -d $(DB_NAME)
#   PY   ?= python3
#   API_BASE ?= http://localhost:8000
#
# Example doc keys:
#   NICE guidance: NG220, NG193, CG173, QS214, etc.
#   CKS pages use slugs (e.g., "hypertension")
#
# Quickstart:
#   make nice-setup
#   make nice-scrape DOC=NG220
#   make nice-load   DOC=NG220
#   make nice-fts
#   make nice-embed
#   make nice-api-smoke

NICE_SRC ?= nice
NICE_OUT ?= data/nice
NICE_LIST ?= docs/nice_doc_keys.txt
EMB_MODEL ?= text-embedding-3-small
ANN_LISTS ?= 800
PROBES    ?= 10
LIMIT     ?= 10

nice-setup:
	@mkdir -p $(NICE_OUT)
	@$(PSQL) -v ON_ERROR_STOP=1 -f database/schemas/setup_guidelines_schema.sql

# Discover & download a single PDF for DOC (e.g., DOC=NG220)
nice-scrape:
	@test -n "$(DOC)" || (echo "Usage: make nice-scrape DOC=NG220 [SRC=nice|cks]"; exit 2)
	@$(PY) server/scripts/scrape_nice_pdf.py --doc "$(DOC)" --src "$(NICE_SRC)" --out "$(NICE_OUT)"
	@latest=$$(ls -t "$(NICE_OUT)"/*.pdf | head -n1); \
	  cp "$$latest" "$(NICE_OUT)/$(DOC).pdf"; \
	  echo "Aliased $$latest -> $(NICE_OUT)/$(DOC).pdf"

# Load a single already-downloaded PDF into guidelines.* + rag_corpus
nice-load:
	@test -n "$(DOC)" || (echo "Usage: make nice-load DOC=NG220 [SRC=nice|cks]"; exit 2)
	@test -f "$(NICE_OUT)/$(DOC).pdf" || (echo "Missing $(NICE_OUT)/$(DOC).pdf. Run: make nice-scrape DOC=$(DOC)"; exit 3)
	@GUIDE_SRC_KEY="$(NICE_SRC)" GUIDE_DOC_KEY="$(DOC)" GUIDE_URL="https://www.nice.org.uk/guidance/$(shell echo $(DOC) | tr A-Z a-z)/resources" \
	  GUIDE_PDF="$(NICE_OUT)/$(DOC).pdf" \
	  $(PY) server/scripts/load_guideline_pdf.py

# End-to-end for one DOC: scrape → load
nice-ingest: nice-scrape nice-load

# Bulk from a newline-separated list (NICE_LIST)
nice-bulk:
	@test -f "$(NICE_LIST)" || (echo "Put doc keys (e.g., NG220) in $(NICE_LIST)"; exit 2)
	@while IFS= read -r d; do \
		[ -z "$$d" ] && continue; \
		echo "=== $$d ==="; \
		$(MAKE) -s nice-scrape DOC="$$d" NICE_SRC="$(NICE_SRC)" NICE_OUT="$(NICE_OUT)"; \
		$(MAKE) -s nice-load   DOC="$$d" NICE_SRC="$(NICE_SRC)" NICE_OUT="$(NICE_OUT)"; \
	done < "$(NICE_LIST)"

# Refresh FTS for NICE rows in rag_corpus
nice-fts:
	@$(PSQL) -v ON_ERROR_STOP=1 -c "UPDATE public.rag_corpus \
	  SET ts = to_tsvector('english', COALESCE(title,'')||' '||COALESCE(text,'')) \
	  WHERE source='$(NICE_SRC)' AND ts IS NULL; \
	  ANALYZE public.rag_corpus;"

# Embed NICE rows (requires embedding column on rag_corpus)
nice-embed:
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus --id-col id --text-col text \
	  --embedding-col embedding --model $(EMB_MODEL) --batch 256 \
	  --where "source='$(NICE_SRC)' AND embedding IS NULL"

nice-embed-safe:
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus --id-col id --text-col text \
	  --embedding-col embedding --model $(EMB_MODEL) --batch 128 \
	  --where "source='$(NICE_SRC)' AND embedding IS NULL AND length(text) <= 20000"

# ANN index scoped to NICE (optional; requires pgvector)
nice-ann-index:
	@$(PSQL) -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_$(NICE_SRC) \
	  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) \
	  WITH (lists = $(ANN_LISTS)) WHERE source='$(NICE_SRC)'; \
	  ANALYZE public.rag_corpus;"

# Quick sanity/API smoke
nice-api-smoke:
	@curl -s "$(API_BASE)/api/guidelines/stats" | jq .
	@curl -s "$(API_BASE)/api/guidelines/docs?source=$(NICE_SRC)" | jq '.[0:3]'
	@curl -s "$(API_BASE)/api/guidelines/search?q=hypertension&limit=$(LIMIT)" | jq .

# === Audit & Report ===
nice-audit-sql:
	@psql -d $${DB_NAME:-2ndopinionmd} -tA -f database/sql/18_nice_audit.sql | jq .

NICE_DIR              := data/guidelines/nice
NICE_NG106_PDF        := $(NICE_DIR)/nice_ng106_full.pdf
NICE_NG28_PDF         := $(NICE_DIR)/nice_ng28_full.pdf

rag_nice_ng106: $(NICE_NG106_PDF)
	$(PYTHON) server/scripts/ingest_nice_guidelines.py \
	  --pdf-path $(NICE_NG106_PDF) \
	  --guideline-id NG106 \
	  --guideline-title "NICE NG106 Chronic heart failure in adults: diagnosis and management"

rag_nice_ng28: $(NICE_NG28_PDF)
	$(PYTHON) server/scripts/ingest_nice_guidelines.py \
	  --pdf-path $(NICE_NG28_PDF) \
	  --guideline-id NG28 \
	  --guideline-title "NICE NG28 Type 2 diabetes in adults: management"

rag_nice: rag_nice_ng106 rag_nice_ng28
