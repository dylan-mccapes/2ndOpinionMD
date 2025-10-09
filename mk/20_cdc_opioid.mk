# =========================
# 20) CDC — Opioid Prescribing
# =========================
.PHONY: cdc-opioid-schema cdc-opioid-xref-schema cdc-opioid-xref-seed \
        cdc-opioid-fetch cdc-opioid-parse cdc-opioid-rag-upsert \
        cdc-opioid-embed cdc-opioid-ann cdc-opioid-stats cdc-opioid-smoke \
        cdc-opioid-all cdc-sections-cols

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

cdc-opioid-stats:
	@$(PSQL) -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_embed FROM public.rag_corpus WHERE source='cdc_opioid' GROUP BY 1;"
	@$(PSQL) -c "SELECT COUNT(*) FROM guidelines.v_cdc_section_codes;"

cdc-opioid-smoke:
	@curl -s "$(API_BASE)/api/guidelines/cdc/opioid/health" | jq .
	@curl -s "$(API_BASE)/api/guidelines/cdc/opioid/stats"  | jq .
	@curl -s "$(API_BASE)/api/guidelines/cdc/opioid/search?q=PDMP&limit=3" | jq .

cdc-opioid-all: cdc-opioid-schema cdc-opioid-xref-schema cdc-opioid-fetch cdc-opioid-parse cdc-opioid-rag-upsert cdc-opioid-embed cdc-opioid-ann cdc-opioid-stats cdc-opioid-smoke

cdc-sections-cols:
	@$(PSQL) -c "SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='guidelines' AND table_name='cdc_sections' ORDER BY ordinal_position;"

