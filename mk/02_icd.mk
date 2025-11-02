# =========================
# 2) ICD-10-CM & ICD-11
# =========================

PSQL    := psql "$${SYNC_DATABASE_URL:-postgresql://2ndopinionmd@localhost:5432/2ndopinionmd}"
PY      := server/venv312/bin/python
PYTHON  := $(PY)   # keep both names to avoid drift

.PHONY: icd-schema icd10-download icd10-load icd11-load icd-rag-upsert icd-embed icd-ann \
        icd-stats icd-ci icd-audit-json-out icd-audit-pdf icd-map-top icd-map-counts icd-verify-manual icd-stats-json

# --- Quick map stats (SNOMED -> ICD10CM) ------------------------------

icd-map-top:
	@$(PSQL) -v ON_ERROR_STOP=1 -c "\
	  SELECT NULLIF(trim(map_target),'') AS icd10cm_code, COUNT(*) snomed_mappings \
	  FROM ontology.snomed_map_icd10cm \
	  WHERE NULLIF(trim(map_target),'') IS NOT NULL \
	  GROUP BY 1 ORDER BY snomed_mappings DESC, icd10cm_code LIMIT 10;"

icd-map-counts:
	@$(PSQL) -v ON_ERROR_STOP=1 -c "\
	  SELECT COUNT(*) rows_all, \
	         COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL) rows_with_target, \
	         COUNT(DISTINCT NULLIF(trim(map_target),'')) distinct_icd10cm_codes \
	  FROM ontology.snomed_map_icd10cm;"

icd-stats-json:
	@$(PSQL) -tA -v ON_ERROR_STOP=1 -f database/sql/integrity_icd_json.sql | jq .

icd-verify-manual:
	@echo "== ICD (manual verification via SNOMED map) =="
	@$(PSQL) -v ON_ERROR_STOP=1 -c "SELECT COUNT(*) AS rows_all, \
	    COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL) AS rows_with_target, \
	    COUNT(DISTINCT NULLIF(trim(map_target),'')) AS distinct_icd10cm_codes \
	  FROM ontology.snomed_map_icd10cm;"
	@echo
	@echo "-- Validity buckets"
	@$(PSQL) -v ON_ERROR_STOP=1 -c "SELECT \
	    COUNT(*) FILTER ( \
	      WHERE position('X' IN map_target)=0 \
	        AND position('?' IN map_target)=0 \
	        AND trim(map_target)<>'' \
	    ) AS valid_plain, \
	    COUNT(*) FILTER ( \
	      WHERE (position('X' IN map_target)>0 OR position('?' IN map_target)>0) \
	        AND trim(map_target)<>'' \
	    ) AS valid_with_placeholders, \
	    COUNT(*) FILTER (WHERE trim(map_target)='') AS truly_invalid \
	  FROM ontology.snomed_map_icd10cm;"
	@echo
	@echo "-- Most mapped ICD-10-CM codes"
	@$(PSQL) -v ON_ERROR_STOP=1 -c "SELECT NULLIF(trim(map_target),'') AS icd10cm_code, \
	    COUNT(*) AS snomed_mappings \
	  FROM ontology.snomed_map_icd10cm \
	  WHERE NULLIF(trim(map_target),'') IS NOT NULL \
	  GROUP BY 1 ORDER BY snomed_mappings DESC, icd10cm_code \
	  LIMIT 15;"

# --- ICD base loads ----------------------------------------------------

icd-schema:
	@$(PSQL) -f database/schemas/icd_minimal.sql

icd10-download:
	@echo "Place order TXT at server/data/icd10/icd10cm-order.txt or set ICD10_CMS_ZIP_URL."

icd10-load: icd-schema
	@$(PYTHON) server/scripts/icd10_cms_loader.py --local server/data/icd10/icd10cm-order.txt

# --- RAG: targets view + idempotent upsert + embedding/index -----------

icd-rag-upsert:
	@$(PSQL) -f database/sql/icd_targets_alias.sql
	@$(PSQL) -f database/sql/icd_rag_upsert.sql

icd-embed:
	@remaining=$$(psql -tA "$${SYNC_DATABASE_URL:-postgresql://2ndopinionmd@localhost:5432/2ndopinionmd}" -c \
	  "SELECT COUNT(*) FROM public.rag_corpus WHERE source='icd10cm' AND embedding IS NULL"); \
	if [ "$$remaining" -eq 0 ]; then \
	  echo "Embeddings already complete for icd10cm. Skipping."; \
	else \
	  echo "Embedding $$remaining icd10cm rows..."; \
	  CONC=$${CONC:-6} BATCH=$${BATCH:-256} CHUNK=$${CHUNK:-96} SOURCE=icd10cm \
	    $(PYTHON) server/scripts/embed_rag_source_async.py; \
	fi

icd-ann:
	@$(PSQL) -f database/sql/icd_indexes.sql

# --- CI report (JSON + PDF) -------------------------------------------

icd-ci: icd-audit-json-out

icd-audit-json-out:
	@$(PYTHON) server/scripts/report_icd_audit_json.py --out server/reports/icd_audit.json

icd-audit-pdf: icd-audit-json-out
	@$(PYTHON) server/scripts/report_icd_audit_pdf.py --in server/reports/icd_audit.json --out db_integrity_reports/02_icd.pdf

# --- ICD-11 (WHO) ---
# --- diagnostics for ICD-11 ---
icd11-probe:
	@mkdir -p server/logs
	@$(PY) server/scripts/icd11_probe.py

icd11-load:
	@mkdir -p server/logs
	@echo ">> Loading ICD-11 (REL=$${ICD11_RELEASE:-2024-01}) ..." | tee server/logs/icd11_loader.log
	@WHO_CLIENT_ID="$$WHO_CLIENT_ID" WHO_CLIENT_SECRET="$$WHO_CLIENT_SECRET" \
	  ICD11_RELEASE="$$ICD11_RELEASE" ICD11_TICK="$$ICD11_TICK" ICD11_MAX="$$ICD11_MAX" ICD11_PAGE="$$ICD11_PAGE" \
	  $(PY) server/scripts/icd11_who_loader.py 2>> server/logs/icd11_loader.log | tee -a server/logs/icd11_loader.log
	@$(PSQL) -c "SELECT COUNT(*) AS icd11_rows FROM ontology.icd11;"

icd11-log-tail:
	@tail -f server/logs/icd11_loader.log

icd11-wipe:
	@$(PSQL) -c "TRUNCATE ontology.icd11;"
