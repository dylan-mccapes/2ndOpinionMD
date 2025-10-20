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
	  --batch 256 --where "$(if $(WHERE),$(WHERE),source IN ('nice','cks') AND embedding IS NULL)"

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