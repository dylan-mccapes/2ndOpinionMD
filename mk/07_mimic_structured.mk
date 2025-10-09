# =========================
# 7) MIMIC-III / MIMIC-IV (structured)
# =========================
mimic3-schema:
	@$(PSQL) -f database/schemas/ehr_mimic3.sql

mimic4-schema:
	@$(PSQL) -f database/schemas/ehr_mimic4.sql

mimic4-dry-run:
	@$(PY) server/scripts/ingest_mimic4.py --dir "data/mimic-iv-2.2" --dry-run

mimic4-import:
	@$(PY) server/scripts/ingest_mimic4.py --dir "data/mimic-iv-2.2"

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

