# =========================
# 20) CDC — Opioid Prescribing
# =========================

.PHONY: cdc-opioid-schema cdc-opioid-xref-schema cdc-opioid-xref-seed \
        cdc-opioid-fetch cdc-opioid-parse cdc-opioid-rag-upsert \
        cdc-opioid-embed cdc-opioid-ann cdc-indexes cdc-optimize \
        cdc-opioid-stats cdc-opioid-smoke cdc-fix-rec \
        cdc-audit-json cdc-audit-json-out cdc-audit cdc-audit-pdf \
        cdc-assert cdc-all

# --- Schemas / xref
cdc-opioid-schema:
	@$(PSQL) -f database/schemas/setup_cdc_opioid.sql

cdc-opioid-xref-schema:
	@$(PSQL) -f database/schemas/setup_cdc_opioid_xref.sql

cdc-opioid-xref-seed:
	@test -f data/cdc_opioid/seed_section_codes.csv
	@$(PSQL) -v ON_ERROR_STOP=1 -c "CREATE TEMP TABLE tmp_section_code_map (LIKE guidelines.section_code_map INCLUDING ALL);"
	@cat data/cdc_opioid/seed_section_codes.csv | $(PSQL) -c "\copy tmp_section_code_map(section_id,system,code,display,how_derived,confidence) FROM STDIN WITH CSV HEADER"
	@$(PSQL) -v ON_ERROR_STOP=1 -c "\
	  INSERT INTO guidelines.section_code_map(section_id,system,code,display,how_derived,confidence) \
	  SELECT section_id,system,code,display,how_derived,confidence FROM tmp_section_code_map \
	  ON CONFLICT (section_id, system, code) DO UPDATE \
	    SET display=EXCLUDED.display, how_derived=EXCLUDED.how_derived, confidence=EXCLUDED.confidence;"
	@$(PSQL) -c "SELECT COUNT(*) FROM guidelines.v_cdc_section_codes;"

# --- Ingest / RAG
cdc-opioid-fetch:
	@$(PY) server/scripts/cdc_opioid_fetch.py --out data/cdc_opioid

cdc-opioid-parse:
	@$(PY) server/scripts/cdc_opioid_parse.py --in data/cdc_opioid

cdc-opioid-rag-upsert:
	@$(PSQL) -f database/sql/cdc_opioid_rag_upsert.sql

cdc-opioid-embed:
	@SOURCE=cdc_opioid EMBED_MODEL=text-embedding-3-small $(PY) server/scripts/embed_rag_source.py
	@$(PSQL) -c "SELECT COUNT(*) total, COUNT(*) FILTER (WHERE embedding IS NULL) no_embed FROM public.rag_corpus WHERE source='cdc_opioid';"

cdc-opioid-ann:
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_cdc ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists = 64) WHERE source='cdc_opioid';"

cdc-indexes:
	@$(PSQL) -f database/sql/cdc_indexes.sql

cdc-optimize:
	@$(PSQL) -c "VACUUM ANALYZE public.rag_corpus;"

# --- Quick stats & smoke
cdc-opioid-stats:
	@$(PSQL) -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_embed FROM public.rag_corpus WHERE source='cdc_opioid' GROUP BY 1;"
	@$(PSQL) -c "SELECT COUNT(*) FROM guidelines.v_cdc_section_codes;"

cdc-opioid-smoke:
	@curl -s "$(API_BASE)/api/guidelines/cdc/opioid/health" | jq .
	@curl -s "$(API_BASE)/api/guidelines/cdc/opioid/stats"  | jq .
	@curl -s "$(API_BASE)/api/guidelines/cdc/opioid/search?q=PDMP&limit=3" | jq .

# --- Rec fixes
cdc-fix-rec:
	@$(PSQL) -f database/sql/cdc_fix_rec_numbers.sql

# --- Audits
cdc-audit-json:
	@$(PSQL) -f database/sql/20_cdc_audit.sql

cdc-audit-json-out:
	@mkdir -p server/reports
	@$(PSQL) -t -A -f database/sql/20_cdc_audit.sql > server/reports/cdc_audit.json && \
	echo "Wrote server/reports/cdc_audit.json"

cdc-audit:
	@$(PY) server/scripts/report_cdc_audit_pdf.py --brief --out db_integrity_reports/20_cdc_opioid.pdf
	@echo "Wrote db_integrity_reports/20_cdc_opioid.pdf (brief)"

cdc-audit-pdf:
	@AI=1 $(PY) server/scripts/report_cdc_audit_pdf.py --ai --out db_integrity_reports/20_cdc_opioid.pdf
	@echo "Wrote db_integrity_reports/20_cdc_opioid.pdf (AI analysis enabled)"

# --- CI-style assertions (fail make if not healthy)
cdc-assert:
	@$(PSQL) -v ON_ERROR_STOP=1 -f database/sql/cdc_assert.sql

# --- One-button
cdc-all: cdc-opioid-schema cdc-opioid-xref-schema cdc-opioid-fetch cdc-opioid-parse \
         cdc-opioid-rag-upsert cdc-opioid-embed cdc-opioid-ann cdc-indexes cdc-optimize \
         cdc-fix-rec cdc-audit-json-out cdc-audit-pdf cdc-assert

cdc-ci: cdc-audit-json-out cdc-assert