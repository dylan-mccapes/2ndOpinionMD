PY := server/venv312/bin/python
PSQL := psql "$${SYNC_DATABASE_URL:-postgresql://2ndopinionmd@localhost:5432/2ndopinionmd}"
SQL_DIR := database/sql
LOG_DIR := server/logs

.PHONY: icd11-probe icd11-load icd11-rag-upsert icd11-embed icd11-ann icd11-ci icd11-audit-pdf

icd11-probe:
	@$(PY) server/scripts/icd11_probe.py | tee $(LOG_DIR)/icd11_probe.log

icd11-load:
	@mkdir -p $(LOG_DIR)
	@$(PY) server/scripts/icd11_who_loader.py 2>&1 | tee $(LOG_DIR)/icd11_loader.log

icd11-rag-upsert:
	@$(PSQL) -f $(SQL_DIR)/icd11_rag_upsert.sql

icd11-embed:
	@$(PY) server/scripts/embed_rag_source_async.py --source icd11

icd11-ann:
	@$(PSQL) -f $(SQL_DIR)/icd_indexes.sql

icd11-ci:
	@$(PSQL) -tA -f $(SQL_DIR)/integrity_icd11_json.sql | tee $(LOG_DIR)/icd11_integrity.json

icd11-audit-pdf:
	@$(PY) server/scripts/report_icd_audit_pdf.py --source icd11 --release $${ICD11_RELEASE:-2024-01}
