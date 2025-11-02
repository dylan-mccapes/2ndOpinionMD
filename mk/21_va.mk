# =========================
# 21) VA / DoD Guidelines
# =========================
.PHONY: va-schema va-fetch va-parse va-rag-delete va-rag-upsert va-embed va-ann \
        va-stats va-smoke va-all va-xref-schema va-xref-seed va-xref-preview va-xref-all

va-schema:
	@$(PSQL) -f database/schemas/setup_va_guidelines.sql

va-fetch:
	@$(PY) server/scripts/va_guidelines_fetch.py --out data/va

va-parse:
	@$(PY) server/scripts/va_guidelines_parse.py --in data/va

va-rag-delete:
	@$(PSQL) -f database/sql/va_guidelines_rag_delete.sql

va-rag-upsert:
	@$(PSQL) -f database/sql/va_guidelines_rag_upsert.sql

va-embed:
	@SOURCE=va_guidelines EMBED_MODEL=text-embedding-3-small $(PY) server/scripts/embed_rag_source.py
	@$(PSQL) -c "SELECT COUNT(*) total, COUNT(*) FILTER (WHERE embedding IS NULL) no_embed FROM public.rag_corpus WHERE source='va_guidelines';"

va-ann:
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_va ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists = 64) WHERE source='va_guidelines';"

va-stats:
	@$(PSQL) -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_embed FROM public.rag_corpus WHERE source='va_guidelines' GROUP BY 1;"
	@$(PSQL) -c "SELECT COUNT(*) FROM guidelines.va_docs;"
	@$(PSQL) -c "SELECT COUNT(*) FROM guidelines.va_sections;"

va-smoke:
	@curl -s "$(API_BASE)/api/guidelines/va/health" | jq .
	@curl -s "$(API_BASE)/api/guidelines/va/stats"  | jq .
	@curl -s "$(API_BASE)/api/guidelines/va/search?q=taper&limit=3" | jq .

va-all: va-schema va-xref-schema va-fetch va-parse va-rag-delete va-rag-upsert va-embed va-ann va-stats va-smoke
	@echo "VA/DoD ingestion complete."

# Cross-index view & seeds
va-xref-schema:
	@$(PSQL) -f database/schemas/setup_va_guidelines_xref.sql

va-xref-seed:
	@test -f data/va/seed_section_codes.csv || (echo "Missing data/va/seed_section_codes.csv. Headers: section_id,system,code,display,how_derived,confidence"; exit 1)
	@sed -i.bak '/^[[:space:]]*$$/d' data/va/seed_section_codes.csv
	@$(PSQL) -v ON_ERROR_STOP=1 -c "CREATE TABLE IF NOT EXISTS guidelines._va_codes_staging (LIKE guidelines.va_section_code_map INCLUDING DEFAULTS)"
	@$(PSQL) -v ON_ERROR_STOP=1 -c "TRUNCATE guidelines._va_codes_staging"
	@$(PSQL) -v ON_ERROR_STOP=1 -c "COPY guidelines._va_codes_staging(section_id,system,code,display,how_derived,confidence) FROM STDIN WITH CSV HEADER" < data/va/seed_section_codes.csv
	@$(PSQL) -v ON_ERROR_STOP=1 -c "\
	  INSERT INTO guidelines.va_section_code_map(section_id,system,code,display,how_derived,confidence) \
	  SELECT section_id, system, code, COALESCE(display,''), COALESCE(how_derived,'curated'), COALESCE(confidence,0.90) \
	  FROM guidelines._va_codes_staging \
	  ON CONFLICT (section_id, system, code) DO UPDATE \
	    SET display=EXCLUDED.display, how_derived=EXCLUDED.how_derived, confidence=EXCLUDED.confidence"

va-xref-preview:
	@$(PSQL) -c "SELECT * FROM guidelines.v_va_section_codes ORDER BY section_id LIMIT 10;"

va-xref-all: va-xref-schema va-xref-seed va-xref-preview

.PHONY: va-audit va-audit-pdf va-audit-json va-audit-json-out va-assert va-ci va-indexes

va-audit-json:
	@$(PSQL) -f database/sql/21_va_audit.sql

va-audit-json-out:
	@mkdir -p server/reports
	@$(PSQL) -t -A -f database/sql/21_va_audit.sql > server/reports/va_audit.json && \
	echo "Wrote server/reports/va_audit.json"

va-assert:
	@$(PSQL) -v ON_ERROR_STOP=1 -f database/sql/va_assert.sql

va-audit:
	@$(PY) server/scripts/report_va_audit_pdf.py --brief --out db_integrity_reports/21_va.pdf
	@echo "Wrote db_integrity_reports/21_va.pdf (brief)"

va-audit-pdf:
	@AI=1 $(PY) server/scripts/report_va_audit_pdf.py --ai --out db_integrity_reports/21_va.pdf
	@echo "Wrote db_integrity_reports/21_va.pdf (AI analysis enabled)"

# CI-style one-shot: write JSON and enforce invariants
va-ci: va-audit-json-out va-assert

va-indexes:
	@$(PSQL) -f database/sql/va_indexes.sql
