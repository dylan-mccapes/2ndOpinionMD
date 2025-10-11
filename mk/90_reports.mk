# ===============================
# 90_reports.mk — PDF reports
# ===============================

# All scripts will only call OpenAI when --ai is passed.
# You can enable that by running:  make reports-all AI=1

REPORTS_DIR ?= db_integrity_reports
SNOMED_OUT  ?= $(REPORTS_DIR)/01_snomed.pdf
ICD_OUT     ?= $(REPORTS_DIR)/02_icd.pdf
OVERALL_OUT ?= $(REPORTS_DIR)/00_overall.pdf

.PHONY: reports-dir snomed-report-pdf hpo-report-pd icd-report-pdf chv-report-pdf mimic-report-pdf overall-report-pdf notes-report-pdf n2c2-report-pdf reports-all

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

chv-report-pdf:
	@$(PY) server/scripts/report_chv_pdf.py --out db_integrity_reports/06_chv.pdf $(if $(AI),--ai,)

# 07) MIMIC report
mimic-report-pdf:
	@$(PY) server/scripts/report_mimic_pdf.py --out db_integrity_reports/07_mimic.pdf $(if $(AI),--ai,)

# 08) MIMIC-IV Notes
notes-report-pdf:
	@$(PY) server/scripts/report_mimiciv_notes_pdf.py --out db_integrity_reports/08_mimiciv_notes.pdf $(if $(AI),--ai,)

# 09) n2c2 / i2b2
n2c2-report-pdf:
	@$(PY) server/scripts/report_n2c2_pdf.py --out db_integrity_reports/09_n2c2.pdf $(if $(AI),--ai,)

clinvar-report-pdf:
	@$(PY) server/scripts/report_clinvar_pdf.py \
	  --out db_integrity_reports/10_clinvar.pdf $(if $(AI),--ai,)


reports-all: snomed-report-pdf icd-report-pdf hpo-report-pdf overall-report-pdf orphanet-report-pdf chv-report-pdf mimic-report-pdf n2c2-report-pdf clinvar-report-pdf
