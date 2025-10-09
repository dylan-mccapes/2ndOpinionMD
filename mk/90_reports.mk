# ===============================
# 90_reports.mk — PDF reports
# ===============================

# All scripts will only call OpenAI when --ai is passed.
# You can enable that by running:  make reports-all AI=1

REPORTS_DIR ?= db_integrity_reports
SNOMED_OUT  ?= $(REPORTS_DIR)/01_snomed.pdf
ICD_OUT     ?= $(REPORTS_DIR)/02_icd.pdf
OVERALL_OUT ?= $(REPORTS_DIR)/00_overall.pdf

.PHONY: reports-dir snomed-report-pdf icd-report-pdf overall-report-pdf reports-all

reports-dir:
	@mkdir -p "$(REPORTS_DIR)"

snomed-report-pdf: reports-dir
	@$(PY) server/scripts/report_snomed_pdf.py --out "$(SNOMED_OUT)" $(if $(AI),--ai,)
	@ls -lh "$(SNOMED_OUT)" 2>/dev/null || true

icd-report-pdf: reports-dir
	@$(PY) server/scripts/report_icd_pdf.py --out "$(ICD_OUT)" $(if $(AI),--ai,)
	@ls -lh "$(ICD_OUT)" 2>/dev/null || true

# --- HPO report (03) ---
hpo-report-pdf: reports-dir
	@$(PY) server/scripts/report_hpo_pdf.py --out "db_integrity_reports/03_hpo.pdf" $(if $(AI),--ai,)
	@ls -lh "db_integrity_reports/03_hpo.pdf" 2>/dev/null || true

overall-report-pdf: reports-dir
	@$(PY) server/scripts/report_overall_pdf.py --out "$(OVERALL_OUT)" $(if $(AI),--ai,)
	@ls -lh "$(OVERALL_OUT)" 2>/dev/null || true

# Master target – runs each report independently (no cross-calling)
reports-all: reports-dir snomed-report-pdf icd-report-pdf hpo-report-pdf overall-report-pdf

