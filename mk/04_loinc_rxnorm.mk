# =========================
# 4) LOINC & RxNorm
# =========================
loinc-schema:
	@$(PSQL) -f database/schemas/setup_loinc_schema.sql

loinc-indexes:
	@$(PSQL) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm; CREATE INDEX IF NOT EXISTS loinc_long_common_name_trgm ON ontology.loinc_terms USING gin (long_common_name gin_trgm_ops); CREATE INDEX IF NOT EXISTS loinc_shortname_trgm ON ontology.loinc_terms USING gin (shortname gin_trgm_ops);"

loinc-import:
	@test -n "$(ZIP_URL)" || (echo "Set ZIP_URL=https://.../Loinc_YYYYMMDD.zip"; exit 1)
	@$(MAKE) loinc-schema
	@$(PY) server/scripts/ingest_loinc.py --zip-url $(ZIP_URL)
	@$(MAKE) loinc-indexes

loinc-smoke:
	@$(PSQL) -c "SELECT loinc_num, shortname FROM ontology.loinc_terms ORDER BY loinc_num LIMIT 3;"
	@curl -s "$(API_BASE)/api/loinc/search?q=glucose&limit=5" | jq .

rxnorm-import:
	@$(PY) server/scripts/ingest_rxnorm.py --zip-url $(ZIP_URL)

api-rxnorm-search:
	@curl -s "$(API_BASE)/api/rxnorm/search?q=$(Q)&tty=$(TTY)&limit=$(LIMIT)" | jq .

api-rxnorm-drug:
	@curl -s "$(API_BASE)/api/rxnorm/drug/$(RXCUI)" | jq .

api-rxnorm-ndc:
	@curl -s "$(API_BASE)/api/rxnorm/ndc/$(NDC)" | jq .

rxnorm-trgm-index:
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS rxnorm_conso_str_gin_idx ON ontology.rxnorm_conso USING gin (str gin_trgm_ops);"

rxnorm-indexes:
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS rxnorm_ndc_norm_idx ON ontology.rxnorm_ndc (ndc_norm); CREATE INDEX IF NOT EXISTS rxnorm_ndc_rxcui_idx ON ontology.rxnorm_ndc (rxcui); CREATE INDEX IF NOT EXISTS rxnorm_conso_label_pick_idx ON ontology.rxnorm_conso (rxcui, sab, ispref, tty, str);"

# =========================
# Integrity / Audit add-ons
# =========================
PSQL     ?= psql -d 2ndopinionmd -v ON_ERROR_STOP=1
SNAPDIR  ?= snapshots

$(SNAPDIR):
	@mkdir -p $(SNAPDIR)

## ---------- LOINC integrity (schema: ontology.loinc_terms) ----------

loinc-audit:
	@echo "== LOINC — core counts =="
	@$(PSQL) -c "SELECT 'loinc_terms' AS what, COUNT(*) AS n FROM ontology.loinc_terms;"
	@echo "== LOINC — top classes =="
	@$(PSQL) -A -F $$'\t' -c "\
	  SELECT class, COUNT(*) AS n \
	  FROM ontology.loinc_terms \
	  GROUP BY class \
	  ORDER BY n DESC, class \
	  LIMIT 15;"

loinc-snapshots: | $(SNAPDIR)
	@echo "Writing LOINC snapshots to $(SNAPDIR)/"
	@$(PSQL) -A -F $$'\t' -c "\
	  COPY ( \
	    SELECT 'loinc_terms' AS what, COUNT(*) AS n FROM ontology.loinc_terms \
	  ) TO STDOUT" > $(SNAPDIR)/loinc_counts.tsv
	@$(PSQL) -A -F $$'\t' -c "\
	  COPY ( \
	    SELECT class, COUNT(*) AS n \
	    FROM ontology.loinc_terms \
	    GROUP BY class \
	    ORDER BY n DESC, class \
	    LIMIT 50 \
	  ) TO STDOUT" > $(SNAPDIR)/loinc_top_classes.tsv
	@echo "LOINC snapshots written."

## ---------- RxNorm integrity (schemas: ontology.rxnorm_conso, ontology.rxnorm_ndc) ----------

rxnorm-audit:
	@echo "== RxNorm — core counts =="
	@$(PSQL) -c "SELECT 'rxnorm_conso' AS what, COUNT(*) AS n FROM ontology.rxnorm_conso;"
	@$(PSQL) -c "SELECT 'rxnorm_distinct_rxcui' AS what, COUNT(DISTINCT rxcui) AS n FROM ontology.rxnorm_conso;"
	@$(PSQL) -c "SELECT 'rxnorm_ndc' AS what, COUNT(*) AS n FROM ontology.rxnorm_ndc;"
	@echo "== RxNorm — quality checks =="
	@$(PSQL) -c "\
	  SELECT 'conso_blank_str' AS what, COUNT(*) AS n \
	  FROM ontology.rxnorm_conso \
	  WHERE COALESCE(NULLIF(str,''), NULL) IS NULL;"
	@$(PSQL) -A -F $$'\t' -c "\
	  SELECT tty, COUNT(*) AS n \
	  FROM ontology.rxnorm_conso \
	  GROUP BY tty \
	  ORDER BY n DESC, tty \
	  LIMIT 15;"

rxnorm-snapshots: | $(SNAPDIR)
	@echo "Writing RxNorm snapshots to $(SNAPDIR)/"
	@$(PSQL) -A -F $$'\t' -c "\
	  COPY ( \
	    SELECT 'rxnorm_conso' AS what, COUNT(*) AS n FROM ontology.rxnorm_conso \
	    UNION ALL \
	    SELECT 'rxnorm_distinct_rxcui', COUNT(DISTINCT rxcui) FROM ontology.rxnorm_conso \
	    UNION ALL \
	    SELECT 'rxnorm_ndc', COUNT(*) FROM ontology.rxnorm_ndc \
	  ) TO STDOUT" > $(SNAPDIR)/rxnorm_counts.tsv
	@$(PSQL) -A -F $$'\t' -c "\
	  COPY ( \
	    SELECT tty, COUNT(*) AS n \
	    FROM ontology.rxnorm_conso \
	    GROUP BY tty \
	    ORDER BY n DESC, tty \
	    LIMIT 50 \
	  ) TO STDOUT" > $(SNAPDIR)/rxnorm_top_tty.tsv
	@echo "RxNorm snapshots written."

## ---------- Rollups ----------
loinc-integrity-all: loinc-audit loinc-snapshots
rxnorm-integrity-all: rxnorm-audit rxnorm-snapshots
loinc-rxnorm-integrity: loinc-integrity-all rxnorm-integrity-all

.PHONY: loinc-audit loinc-snapshots rxnorm-audit rxnorm-snapshots \
        loinc-integrity-all rxnorm-integrity-all loinc-rxnorm-integrity

# ---------- PDF Integrity Report ----------
REPORT_DIR ?= db_integrity_reports
PY        ?= server/venv312/bin/python

loinc-rxnorm-report-pdf:
	@mkdir -p $(REPORT_DIR)
	@$(PY) server/scripts/report_loinc_rxnorm_pdf.py --out $(REPORT_DIR)/04_loinc_rxnorm.pdf $(if $(AI),--ai,)

# Convenience rollup: run audits + build PDF
loinc-rxnorm-integrity-all: loinc-rxnorm-integrity loinc-rxnorm-report-pdf

.PHONY: loinc-rxnorm-report-pdf loinc-rxnorm-integrity-all

