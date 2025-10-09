# =========================
# 22) Final integrity checks
# =========================
.PHONY: integrity-report integrity-report-json integrity-embeddings integrity-all \
        integrity-orphans smoke-cdc smoke-va smoke-all

integrity-report:
	@echo "== Integrity report (human-readable) =="; $(PSQL) -f database/sql/integrity_report.sql

integrity-report-json:
	@echo "== Integrity report (JSON) =="; $(PSQL) -f database/sql/integrity_report_json.sql

integrity-embeddings:
	@$(PSQL) -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_embed FROM public.rag_corpus GROUP BY 1 ORDER BY 1;"
	@$(PSQL) -c "SELECT indexname, indexdef FROM pg_indexes WHERE tablename='rag_corpus' AND indexname LIKE 'rag_corpus_embedding_ann_%';"

integrity-orphans:
	@echo "== CDC sections without rag rows =="
	psql "$${SYNC_DATABASE_URL}" -c "\
	  SELECT s.section_id, left(s.heading,120) AS heading \
	  FROM guidelines.cdc_sections s \
	  LEFT JOIN public.rag_corpus r \
	    ON r.source='cdc_opioid' AND (r.meta->>'section_id') = s.section_id::text \
	  WHERE r.id IS NULL \
	  ORDER BY s.section_id \
	  LIMIT 10;"

	@echo "== VA sections without rag rows =="
	psql "$${SYNC_DATABASE_URL}" -c "\
	  SELECT s.section_id, s.doc_slug, left(s.heading,120) AS heading \
	  FROM guidelines.va_sections s \
	  LEFT JOIN public.rag_corpus r \
	    ON r.source='va_guidelines' AND (r.meta->>'section_id') = s.section_id::text \
	  WHERE r.id IS NULL \
	  ORDER BY s.section_id \
	  LIMIT 10;"

integrity-all: integrity-report integrity-report-json integrity-embeddings integrity-orphans

# -------- quick API smoke --------
smoke-cdc:
	@echo "== CDC =="; $(MAKE) -s cdc-opioid-smoke

smoke-va:
	@echo "== VA =="; $(MAKE) -s va-smoke

smoke-all: smoke-cdc smoke-va

