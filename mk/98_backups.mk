# =========================
# Backups & DB reports
# =========================
.PHONY: db-backup db-backup-verify db-report db-report-json db-report-all \
        backup-now backup-verify

NOW ?= $(shell date +%Y%m%d_%H%M%S)

db-backup:
	@mkdir -p backups; chmod +x server/scripts/pg_backup.sh
	@JOBS=$(JOBS) server/scripts/pg_backup.sh "$$SYNC_DATABASE_URL"

db-backup-verify:
	@chmod +x server/scripts/pg_backup_verify.sh
	@JOBS=$(JOBS) server/scripts/pg_backup_verify.sh backups/latest

db-report:
	@mkdir -p reports
	@$(PSQL) -f database/sql/integrity_report.sql | tee reports/integrity_$(NOW).txt

db-report-json:
	@mkdir -p reports
	@$(PSQL) -tA -f database/sql/integrity_report_json.sql > reports/integrity_$(NOW).json
	@echo "wrote JSON report to reports/"

db-report-all: db-report db-report-json

backup-now:
	@bash server/scripts/pg_backup.sh

backup-verify:
	@bash server/scripts/pg_backup_verify.sh

