# =========================
# 7) MIMIC-III / MIMIC-IV (structured)
# =========================

PSQL ?= psql -d "$(SYNC_DATABASE_URL)"
PY   ?= server/venv312/bin/python

mimic3-schema:
	@$(PSQL) -f database/schemas/ehr_mimic3.sql

mimic4-schema:
	@$(PSQL) -f database/schemas/ehr_mimic4.sql

mimic4-dry-run:
	@$(PY) server/scripts/ingest_mimic4.py --dir "data/mimic-iv-2.2" --dry-run

mimic4-import:
	@$(PY) server/scripts/ingest_mimic4.py --dir "data/mimic-iv-2.2"

mimic4-import-icu:
	@$(PSQL) -c "\copy ehr_mimic4.icustays FROM PROGRAM 'gzip -dc data/mimic-iv-2.2/icu/icustays.csv.gz' CSV HEADER"
	@$(PSQL) -c "\copy ehr_mimic4.d_items   FROM PROGRAM 'gzip -dc data/mimic-iv-2.2/icu/d_items.csv.gz'     CSV HEADER"
	@echo "Loaded ICU tables (icustays, d_items)."

api-m4-i50-hadm:
	@$(PSQL) -c "SELECT hadm_id, COUNT(*) AS n FROM ehr_mimic4.diagnoses_icd WHERE icd_version = 10 AND icd_code LIKE 'I50%%' GROUP BY 1 ORDER BY n DESC LIMIT $${LIMIT:-20};"

api-m4-any-hadm:
	@$(PSQL) -Atc "SELECT hadm_id FROM ehr_mimic4.diagnoses_icd ORDER BY random() LIMIT 1" \
	| xargs -I{} sh -c 'echo HADM={}; curl -s "$(API_BASE)/api/mimic4/diagnoses?hadm_id={}" | jq .'

mimic3-dry-run:
	@$(PY) server/scripts/ingest_mimic3.py --dir "data/MIMIC-III"

mimic3-import:
	@$(PY) server/scripts/ingest_mimic3.py --dir "data/MIMIC-III"

mimic3-stats:
	@$(PSQL) -c "SELECT 'patients' tbl, count(*) FROM ehr_mimic3.patients UNION ALL SELECT 'admissions', count(*) FROM ehr_mimic3.admissions UNION ALL SELECT 'icustays', count(*) FROM ehr_mimic3.icustays UNION ALL SELECT 'diagnoses_icd', count(*) FROM ehr_mimic3.diagnoses_icd UNION ALL SELECT 'procedures_icd', count(*) FROM ehr_mimic3.procedures_icd UNION ALL SELECT 'labevents', count(*) FROM ehr_mimic3.labevents" | column -t

mimic3-sanity:
	@$(PSQL) -c "SELECT hadm_id, count(*) labs FROM ehr_mimic3.labevents GROUP BY hadm_id ORDER BY labs DESC NULLS LAST LIMIT 5;"
	@$(PSQL) -c "SELECT d.icd9_code, di.long_title, count(*) n FROM ehr_mimic3.diagnoses_icd d LEFT JOIN ehr_mimic3.d_icd_diagnoses di USING(icd9_code) GROUP BY 1,2 ORDER BY n DESC LIMIT 10;"

# --- MIMIC-IV quick stats & sanity
mimic4-stats:
	@$(PSQL) -c "SELECT 'patients' tbl, count(*) FROM ehr_mimic4.patients \
		UNION ALL SELECT 'admissions', count(*) FROM ehr_mimic4.admissions \
		UNION ALL SELECT 'labevents', count(*) FROM ehr_mimic4.labevents \
		UNION ALL SELECT 'diagnoses_icd', count(*) FROM ehr_mimic4.diagnoses_icd \
		UNION ALL SELECT 'icustays', count(*) FROM ehr_mimic4.icustays" | column -t

mimic4-sanity:
	@$(PSQL) -c "SELECT COUNT(*) AS joined_rows FROM ehr_mimic4.admissions a \
		JOIN ehr_mimic4.labevents l USING (hadm_id) \
		WHERE l.charttime BETWEEN a.admittime AND a.dischtime;"

# --- Roll-up audit (III + IV)
mimic-audit:
	@echo "== MIMIC-III counts ==" && \
	$(PSQL) -c "SELECT 'm3_patients', COUNT(*) FROM ehr_mimic3.patients \
		UNION ALL SELECT 'm3_admissions', COUNT(*) FROM ehr_mimic3.admissions \
		UNION ALL SELECT 'm3_labs', COUNT(*) FROM ehr_mimic3.labevents \
		UNION ALL SELECT 'm3_dx', COUNT(*) FROM ehr_mimic3.diagnoses_icd" | column -t && \
	echo "\n== MIMIC-IV counts ==" && \
	$(PSQL) -c "SELECT 'm4_patients', COUNT(*) FROM ehr_mimic4.patients \
		UNION ALL SELECT 'm4_admissions', COUNT(*) FROM ehr_mimic4.admissions \
		UNION ALL SELECT 'm4_labs', COUNT(*) FROM ehr_mimic4.labevents \
		UNION ALL SELECT 'm4_dx', COUNT(*) FROM ehr_mimic4.diagnoses_icd \
		UNION ALL SELECT 'm4_icustays', COUNT(*) FROM ehr_mimic4.icustays" | column -t && \
	echo "\n== IV stay-window sanity (labs inside admission window) ==" && \
	$(PSQL) -c "SELECT COUNT(*) AS joined_rows FROM ehr_mimic4.admissions a \
		JOIN ehr_mimic4.labevents l USING (hadm_id) \
		WHERE l.charttime BETWEEN a.admittime AND a.dischtime;"

mimic4-import-icu-safe:
	@$(PY) server/scripts/load_by_header.py --table ehr_mimic4.icustays --csv data/mimic-iv-2.2/icu/icustays.csv.gz --truncate
	@$(PY) server/scripts/load_by_header.py --table ehr_mimic4.d_items   --csv data/mimic-iv-2.2/icu/d_items.csv.gz   --truncate
	@echo "Loaded ICU tables (icustays, d_items) via header-aware loader."

# --- RAG corpus (dict-level) for MIMIC
mimic-rag-upsert:
	@$(PSQL) -f database/sql/mimic_rag_upsert.sql
	@$(PSQL) -At -c "COPY ( \
	  SELECT source, COUNT(*) AS total, COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS embedded, \
	         COUNT(*) FILTER (WHERE embedding IS NULL) AS pending \
	  FROM public.rag_corpus \
	  WHERE source IN ('mimic3_dx','mimic3_proc','mimic3_labitems','mimic4_dx','mimic4_proc','mimic4_labitems') \
	  GROUP BY source ORDER BY source \
	) TO STDOUT WITH (FORMAT csv, HEADER true)"

mimic-embed:
	@$(PY) server/scripts/embed_rag_source_async.py --source mimic3_dx
	@$(PY) server/scripts/embed_rag_source_async.py --source mimic3_proc
	@$(PY) server/scripts/embed_rag_source_async.py --source mimic3_labitems
	@$(PY) server/scripts/embed_rag_source_async.py --source mimic4_dx
	@$(PY) server/scripts/embed_rag_source_async.py --source mimic4_proc
	@$(PY) server/scripts/embed_rag_source_async.py --source mimic4_labitems

mimic-ann:
	@$(PSQL) -f database/sql/mimic_indexes.sql

mimic-bm25-rebuild:
	@$(PSQL) -c "UPDATE public.rag_corpus r \
SET ts = to_tsvector('english', coalesce(r.title,'')||' '||coalesce(r.text,'')) \
WHERE r.source IN ('mimic3_dx','mimic3_proc','mimic3_labitems','mimic4_dx','mimic4_proc','mimic4_labitems');"
	@$(PSQL) -c "ANALYZE public.rag_corpus;"

mimic-stats-json:
	@$(PSQL) -c "SELECT jsonb_pretty(jsonb_object_agg(source, jsonb_build_object('total', COUNT(*), 'embedded', COUNT(*) FILTER (WHERE embedding IS NOT NULL), 'pending', COUNT(*) FILTER (WHERE embedding IS NULL)))) \
FROM public.rag_corpus WHERE source LIKE 'mimic%%';"

mimic-integrity:
	@REPORT_AI=1 $(PY) server/scripts/report_mimic_pdf.py --out db_integrity_reports/07_mimic.pdf --ai
	@echo "Wrote db_integrity_reports/07_mimic.pdf"

mimic-watch:
	@server/venv312/bin/python server/scripts/watch_embeddings.py --like "mimic%%" --interval $${INTERVAL:-3} --wide

mimic-watch-m3:
	@server/venv312/bin/python server/scripts/watch_embeddings.py --like "mimic3%%" --interval $${INTERVAL:-3} --wide

mimic-watch-m4:
	@server/venv312/bin/python server/scripts/watch_embeddings.py --like "mimic4%%" --interval $${INTERVAL:-3} --wide
