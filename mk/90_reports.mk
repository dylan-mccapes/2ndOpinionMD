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

# -------- ClinGen ACI report (portable) --------
# Auto-detect a Python if $(PY) isn't set upstream
PY ?= $(shell [ -x server/venv312/bin/python ] && printf server/venv312/bin/python || (command -v python3 || command -v python))

clingen-aci-report:
	@mkdir -p db_integrity_reports
	@env PYTHONIOENCODING=utf-8 LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8 \
		$(PY) server/scripts/report_clingen_aci_pdf.py --out db_integrity_reports/11_clingen_aci.pdf
	@printf "📄 wrote %s\n" "db_integrity_reports/11_clingen_aci.pdf"

# 11) ClinGen Validity report
clingen-validity-report-pdf:
	@$(PY) server/scripts/report_clingen_validity_pdf.py --out db_integrity_reports/11_clingen_validity.pdf $(if $(AI),--ai,)

### -------- NICE Guidelines report --------

nice-report:
	@AI=$(AI) PYTHONPATH=. $(PY) server/scripts/report_nice_pdf.py $(if $(AI),--ai,)
	@echo "Wrote db_integrity_reports/18_nice.pdf"

nice-status:
	@$(PSQL) -c "\
		WITH t AS (SELECT to_regclass('guidelines.docs') IS NOT NULL AS has), \
		c AS (SELECT COUNT(*)::bigint AS n FROM guidelines.docs WHERE source_key='nice') \
		SELECT CASE WHEN NOT (SELECT has FROM t) THEN 'FAIL' \
					WHEN (SELECT n FROM c)=0 THEN 'WARN' \
					ELSE 'PASS' END AS status;"

# =========================
# 90) Integrity Reports
# =========================

# PanelApp integrity report (12_panelapp.pdf)
panelapp-report:
	@$(PY) server/scripts/report_panelapp_pdf.py --out db_integrity_reports/12_panelapp.pdf $(if $(AI),--ai,)

# (optional aggregator)
reports: panelapp-report

### -------- Diagnostic Rules (ACR/EULAR) --------
diagrules-report:
	@$(PY) server/scripts/report_diagrules_pdf.py $(if $(AI),--ai,)
	@echo "📄 wrote db_integrity_reports/14_diagnostic_rules.pdf"

diagrules-status:
	@$(PSQL) -c "\
WITH p AS ( \
  SELECT to_regclass('guidelines.diagnostic_rules') IS NOT NULL AS has_table, \
         COALESCE((SELECT COUNT(*) FROM guidelines.diagnostic_rules),0) AS rows \
) SELECT CASE \
  WHEN NOT has_table THEN 'FAIL' \
  WHEN rows=0       THEN 'WARN' \
  ELSE 'PASS' END AS status FROM p;"

# 15_disgenet.mk
disgenet-report:
	@AI=$(AI) $(PY) server/scripts/report_disgenet_pdf.py

gwas-report:
	@AI="$(AI)" BRIEF="$(BRIEF)" NO_HIST="$(NO_HIST)" $(PY) server/scripts/report_gwas_pdf.py

neurolex-report:
	@AI=$${AI:-0} PYTHONPATH=. $(PY) server/scripts/report_neurolex_pdf.py
	@echo "Wrote db_integrity_reports/17_neurolex.pdf"

reports-all: snomed-report-pdf icd-report-pdf hpo-report-pdf overall-report-pdf orphanet-report-pdf chv-report-pdf mimic-report-pdf n2c2-report-pdf clinvar-report-pdf clingen-aci-report clingen-validity-report-pdf
