# =========================
# 2) ICD-10-CM & ICD-11
# =========================

icd-schema:
	@echo ">> (optional) ensure ontology.icd schema exists (DDL not shown)"

# loader you added
icd10-import:
	@$(PY) server/scripts/load_icd10_data.py

icd11-import:
	@echo ">> TODO: add ICD-11 WHO API loader"; exit 0

icd-smoke:
	@echo ">> TODO: add quick ICD lookups"

# Integrity only
icd-stats:
	@psql "$(SYNC_DATABASE_URL)" -v ON_ERROR_STOP=1 -f database/sql/integrity_icd.sql

icd-stats-json:
	@psql -tA "$(SYNC_DATABASE_URL)" -v ON_ERROR_STOP=1 -f database/sql/integrity_icd_json.sql | jq .

# Handy focused map views (optional)
icd-map-top:
	@psql "$(SYNC_DATABASE_URL)" -v ON_ERROR_STOP=1 -c "\
	  SELECT NULLIF(trim(map_target),'') AS icd10cm_code, COUNT(*) snomed_mappings \
	  FROM ontology.snomed_map_icd10cm \
	  WHERE NULLIF(trim(map_target),'') IS NOT NULL \
	  GROUP BY 1 ORDER BY snomed_mappings DESC, icd10cm_code LIMIT 10;"

icd-map-counts:
	@psql "$(SYNC_DATABASE_URL)" -v ON_ERROR_STOP=1 -c "\
	  SELECT COUNT(*) rows_all, \
	         COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL) rows_with_target, \
	         COUNT(DISTINCT NULLIF(trim(map_target),'')) distinct_icd10cm_codes \
	  FROM ontology.snomed_map_icd10cm;"

# Manual integrity snapshot that never assumes ICD base tables exist.
# Uses only the SNOMED→ICD10CM map (which we know is present).
icd-verify-manual:
	@echo "== ICD (manual verification via SNOMED map) =="
	@$(PSQL) -v ON_ERROR_STOP=1 <<'SQL'
		SELECT COUNT(*) AS rows_all,
			COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL) AS rows_with_target,
			COUNT(DISTINCT NULLIF(trim(map_target),'')) AS distinct_icd10cm_codes
		FROM ontology.snomed_map_icd10cm;
		SQL
			@echo
			@echo "-- Validity buckets"
			@$(PSQL) -v ON_ERROR_STOP=1 <<'SQL'
		SELECT
		COUNT(*) FILTER (
			WHERE position('X' IN map_target) = 0
			AND position('?' IN map_target) = 0
			AND trim(map_target) <> ''
		) AS valid_plain,
		COUNT(*) FILTER (
			WHERE (position('X' IN map_target) > 0 OR position('?' IN map_target) > 0)
			AND trim(map_target) <> ''
		) AS valid_with_placeholders,
		COUNT(*) FILTER (WHERE trim(map_target) = '') AS truly_invalid
		FROM ontology.snomed_map_icd10cm;
		SQL
			@echo
			@echo "-- Most mapped ICD-10-CM codes"
			@$(PSQL) -v ON_ERROR_STOP=1 <<'SQL'
		SELECT NULLIF(trim(map_target),'') AS icd10cm_code,
			COUNT(*) AS snomed_mappings
		FROM ontology.snomed_map_icd10cm
		WHERE NULLIF(trim(map_target),'') IS NOT NULL
		GROUP BY 1
		ORDER BY snomed_mappings DESC, icd10cm_code
		LIMIT 15;
		SQL



