# =========================
# 4) LOINC & RxNorm
# =========================

LOINC_DIR ?= data/loinc
RXN_DIR   ?= data/rxnorm
PY        ?= $(CURDIR)/server/venv312/bin/python
# Resolve DB at shell time so we never pass an empty string to psql.
DB        ?= $(shell :; printf "%s" "$${SYNC_DATABASE_URL:-postgresql://2ndopinionmd@localhost:5432/2ndopinionmd}")
PSQL      ?= psql "$(DB)" -v ON_ERROR_STOP=1
API_BASE  ?= http://127.0.0.1:8000
BATCH ?= 512
CONC  ?= 8
# Big maintenance psql for ANN builds
PSQL_BIG ?= PGOPTIONS='-c maintenance_work_mem=512MB -c max_parallel_maintenance_workers=4' psql -d 2ndopinionmd -v ON_ERROR_STOP=1

# ----- Schemas
loinc-schema:
	$(PSQL) -f database/schemas/setup_loinc_schema.sql

rxnorm-schema:
	$(PSQL) -f database/schemas/setup_rxnorm_schema.sql

loinc-indexes:
	@$(PSQL) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm; \
	  CREATE INDEX IF NOT EXISTS loinc_long_common_name_trgm ON ontology.loinc_terms USING gin (long_common_name gin_trgm_ops); \
	  CREATE INDEX IF NOT EXISTS loinc_shortname_trgm        ON ontology.loinc_terms USING gin (shortname gin_trgm_ops);"

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
	@$(PSQL) -c "\
	  CREATE INDEX IF NOT EXISTS rxnorm_ndc_norm_idx         ON ontology.rxnorm_ndc (ndc_norm); \
	  CREATE INDEX IF NOT EXISTS rxnorm_ndc_rxcui_idx        ON ontology.rxnorm_ndc (rxcui); \
	  CREATE INDEX IF NOT EXISTS rxnorm_conso_label_pick_idx ON ontology.rxnorm_conso (rxcui, sab, ispref, tty, str);"

# =========================
# Integrity / Audit add-ons
# =========================
SNAPDIR  ?= snapshots

$(SNAPDIR):
	@mkdir -p $(SNAPDIR)

## ---------- LOINC integrity ----------
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
	@$(PSQL) -A -F $$'\t' -c "COPY (SELECT 'loinc_terms' AS what, COUNT(*) AS n FROM ontology.loinc_terms) TO STDOUT" > $(SNAPDIR)/loinc_counts.tsv
	@$(PSQL) -A -F $$'\t' -c "\
	  COPY ( \
	    SELECT class, COUNT(*) AS n \
	    FROM ontology.loinc_terms \
	    GROUP BY class \
	    ORDER BY n DESC, class \
	    LIMIT 50 \
	  ) TO STDOUT" > $(SNAPDIR)/loinc_top_classes.tsv
	@echo "LOINC snapshots written."

## ---------- RxNorm integrity ----------
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

loinc-rxnorm-report-pdf:
	@mkdir -p $(REPORT_DIR)
	@$(PY) server/scripts/report_loinc_rxnorm_pdf.py --out $(REPORT_DIR)/04_loinc_rxnorm.pdf $(if $(AI),--ai,)

# Convenience rollup: run audits + build PDF
loinc-rxnorm-integrity-all: loinc-rxnorm-integrity loinc-rxnorm-report-pdf

.PHONY: loinc-rxnorm-report-pdf loinc-rxnorm-integrity-all

# ----- Loaders (user must place files; these are gated)
loinc-assert:
	test -s "$(LOINC_DIR)/LoincTableCore.csv" || (echo "Missing $(LOINC_DIR)/LoincTableCore.csv"; exit 2)

rxnorm-assert:
	test -s "$(RXN_DIR)/RXNCONSO.RRF" || (echo "Missing $(RXN_DIR)/RXNCONSO.RRF"; exit 2)

loinc-load: loinc-schema loinc-assert
	@echo "Make will use: $(PY)"
	$(PY) server/scripts/loinc_load.py --dir "$(LOINC_DIR)" --dsn "$(DB)"
	@$(MAKE) loinc-indexes

rxnorm-load: rxnorm-schema rxnorm-assert
	@echo "Make will use: $(PY)"
	$(PY) server/scripts/rxnorm_load_rrf.py --dir "$(RXN_DIR)" --dsn "$(DB)"
	@$(MAKE) rxnorm-indexes

# ----- Ensure unique constraint for RAG upserts (idempotent)
.PHONY: rag-uniq-index
rag-uniq-index:
	@echo "Ensuring (source, source_id) uniqueness and index…"
	@$(PSQL) -c "\
	WITH d AS ( \
	  SELECT ctid, ROW_NUMBER() OVER (PARTITION BY source, source_id ORDER BY ctid) rn \
	  FROM public.rag_corpus \
	) \
	DELETE FROM public.rag_corpus rc USING d \
	WHERE rc.ctid = d.ctid AND d.rn > 1;"
	@$(PSQL) -c "CREATE UNIQUE INDEX CONCURRENTLY IF NOT EXISTS rag_corpus_source_id_uidx ON public.rag_corpus (source, source_id);"

# ----- RAG upserts
loinc-rag-upsert:
	$(MAKE) rag-uniq-index
	$(PSQL) -f database/sql/loinc_rag_upsert.sql

rxnorm-rag-upsert:
	$(MAKE) rag-uniq-index
	$(PSQL) -f database/sql/rxnorm_rag_upsert.sql

# ----- Embeddings
rag-embed:
	@echo "Embedding SOURCE=$(SOURCE) BATCH=$${BATCH:-512} CONC=$${CONC:-8}"
	SOURCE=$${SOURCE:?set SOURCE} \
	BATCH=$${BATCH:-512} \
	CONC=$${CONC:-8} \
	DSN="$(DB)" \
	$(PY) server/scripts/embed_rag_source_async.py --source "$$SOURCE"


loinc-embed:
	@echo "Embedding source: loinc"
	SOURCE=loinc $(MAKE) rag-embed

rxnorm-embed:
	@echo "Embedding source: rxnorm"
	SOURCE=rxnorm $(MAKE) rag-embed

# ----- ANN indexes (per-source; adjust lists as needed)
loinc-ann:
	PGOPTIONS="-c maintenance_work_mem=256MB" $(PSQL) -c "CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_loinc  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists=100)  WHERE source='loinc';"

rxnorm-ann:
	PGOPTIONS="-c maintenance_work_mem=256MB" $(PSQL) -c "CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_rxnorm ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists=200) WHERE source='rxnorm';"

# ----- Report
loinc-rxnorm-report:
	@mkdir -p db_integrity_reports
	$(PY) server/scripts/report_loinc_rxnorm_pdf.py --out db_integrity_reports/04_loinc_rxnorm.pdf $(if $(AI),--ai,)

# ----- One-shots
loinc-all:   loinc-load   loinc-rag-upsert   loinc-embed   loinc-ann   loinc-rxnorm-report
rxnorm-all:  rxnorm-load  rxnorm-rag-upsert  rxnorm-embed  rxnorm-ann  loinc-rxnorm-report

# ===== Progress & ANN checks =====

# One-shot progress snapshot
loinc-rxnorm-progress:
	@psql "$(DB)" -A -F $$'\t' -c "\
	  SELECT source,\
	         COUNT(*) AS total,\
	         COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS done,\
	         COUNT(*) FILTER (WHERE embedding IS NULL)  AS pending,\
	         to_char(100.0 * COUNT(*) FILTER (WHERE embedding IS NOT NULL) / NULLIF(COUNT(*),0), 'FM990D00') AS pct\
	  FROM rag_corpus\
	  WHERE source IN ('loinc','rxnorm')\
	  GROUP BY source\
	  ORDER BY source;"

# 10s watch (press ^C to stop)
loinc-rxnorm-watch:
	@while true; do \
	  date; echo; \
	  $(MAKE) --no-print-directory loinc-rxnorm-progress; \
	  echo; sleep 10; \
	done

# Accurate ANN status (lists/size/ready/valid)
loinc-rxnorm-ann-check:
	@psql "$(DB)" -A -F $$'\t' -c "\
	  SELECT i.indexname, x.indisvalid, x.indisready,\
	         COALESCE((SELECT option_value::int FROM pg_options_to_table(c.reloptions) WHERE option_name='lists'),0) AS lists,\
	         pg_size_pretty(pg_relation_size(x.indexrelid)) AS size\
	  FROM pg_index x\
	  JOIN pg_class c ON c.oid = x.indexrelid\
	  JOIN pg_namespace n ON n.oid = c.relnamespace\
	  JOIN pg_indexes i ON i.indexname = c.relname\
	  WHERE i.tablename='rag_corpus'\
	    AND i.indexname IN ('rag_corpus_embedding_ann_loinc','rag_corpus_embedding_ann_rxnorm')\
	  ORDER BY i.indexname;"

# ===== Rebuilds with tunables =====
# Tune with: LISTS_LOINC=100 LISTS_RXN=200 MAINT_MB=512 PAR_MAINT=4
LISTS_LOINC ?= 100
LISTS_RXN   ?= 200
MAINT_MB    ?= 512
PAR_MAINT   ?= 4

loinc-ann-rebuild:
	@echo "Rebuilding LOINC ANN (lists=$(LISTS_LOINC))…"
	@psql "$(DB)" -v ON_ERROR_STOP=1 -c "DROP INDEX IF EXISTS rag_corpus_embedding_ann_loinc;"
	@PGOPTIONS="-c maintenance_work_mem=$(MAINT_MB)MB -c max_parallel_maintenance_workers=$(PAR_MAINT)" \
	psql "$(DB)" -v ON_ERROR_STOP=1 -c "\
	  CREATE INDEX CONCURRENTLY rag_corpus_embedding_ann_loinc\
	  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops)\
	  WITH (lists=$(LISTS_LOINC)) WHERE source='loinc';"

rxnorm-ann-rebuild:
	@echo "Rebuilding RxNorm ANN (lists=$(LISTS_RXN))…"
	@psql "$(DB)" -v ON_ERROR_STOP=1 -c "DROP INDEX IF EXISTS rag_corpus_embedding_ann_rxnorm;"
	@PGOPTIONS="-c maintenance_work_mem=$(MAINT_MB)MB -c max_parallel_maintenance_workers=$(PAR_MAINT)" \
	psql "$(DB)" -v ON_ERROR_STOP=1 -c "\
	  CREATE INDEX CONCURRENTLY rag_corpus_embedding_ann_rxnorm\
	  ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops)\
	  WITH (lists=$(LISTS_RXN)) WHERE source='rxnorm';"
