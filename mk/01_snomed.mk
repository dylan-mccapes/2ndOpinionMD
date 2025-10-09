# =========================
# 1) SNOMED
# =========================

PSQL_URL := psql "$${SYNC_DATABASE_URL:-postgresql://2ndopinionmd@localhost:5432/2ndopinionmd}"

snomed-audit:
	@$(PSQL) -c "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema='ontology' AND (table_name ILIKE 'snomed%' OR table_name IN ('concepts','descriptions','relationships','refset_members')) ORDER BY 1,2;"

snomed-preview:
	@$(PY) server/scripts/ingest_snomed.py --root-dir data/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20250901T120000Z --dry-run

snomed-import:
	@$(PY) server/scripts/ingest_snomed.py --root-dir data/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20250901T120000Z

snomed-trgm-index:
	@$(PSQL) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm; CREATE INDEX IF NOT EXISTS desc_term_trgm ON ontology.descriptions USING gin (term gin_trgm_ops);"

api-snomed-search:
	@curl -s "$(API_BASE)/api/snomed/search?q=diabetes&limit=5" | jq .

api-snomed-concept:
	@curl -s "$(API_BASE)/api/snomed/concept/$(CID)" | jq .

api-snomed-map:
	@curl -s "$(API_BASE)/api/snomed/map/icd10cm/$(CID)" | jq .

api-snomed-stats:
	@curl -s "$(API_BASE)/api/snomed/stats" | jq .

# integrity scripts
snomed-stats:
	@$(PSQL) -f database/sql/integrity_snomed.sql

snomed-stats-json:
	@$(PSQL) -tA -f database/sql/integrity_snomed_json.sql | jq .

snomed-indexes:
	@$(PSQL) -f database/sql/snomed_add_indexes.sql

snomed-all: snomed-indexes snomed-stats snomed-stats-json
	@echo "SNOMED integrity checks completed."

# ---------- SNOMED: ExtendedMap (ICD-10-CM) ----------
SNOMED_MAP_FILE ?= data/SnomedCT_ManagedServiceUS_PRODUCTION_US1000124_20250901T120000Z/Snapshot/Refset/Map/der2_iisssccRefset_ExtendedMapSnapshot_US1000124_20250901.txt

.PHONY: snomed-map-import snomed-map-stats snomed-refset-alias

snomed-map-reset:
	@$(PY) server/scripts/snomed_map_reset.py

snomed-map-import:
	@echo ">>> SNOMED ExtendedMap import (auto)"
	@$(PY) server/scripts/snomed_map_import.py

snomed-refset-import:
	@echo ">>> SNOMED Language Refset import (auto)"
	@$(PY) server/scripts/snomed_refset_import.py

snomed-map-stats:
	@$(PSQL_URL) -c "SELECT COUNT(*) AS icd10cm_mappings FROM ontology.snomed_map_icd10cm;"

snomed-refset-stats:
	@$(PSQL_URL) -c "SELECT COUNT(*) AS refset_members FROM ontology.refset_members;"

# API compatibility if it expects ontology.snomed_refset_members
snomed-refset-alias:
	@$(PSQL_URL) -v ON_ERROR_STOP=1 -c \
	  "CREATE OR REPLACE VIEW ontology.snomed_refset_members AS SELECT * FROM ontology.refset_members;"

snomed-root:
	@ROOT=$$(ls -d data/SnomedCT_* 2>/dev/null | sort | tail -1); \
	[ -n "$$ROOT" ] && echo "$$ROOT" || (echo "No SNOMED root under data/"; exit 1)

