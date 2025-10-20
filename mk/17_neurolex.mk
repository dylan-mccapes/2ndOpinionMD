# =========================
# 17) NeuroLex (InterLex)
# =========================

SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c

# Common helpers expected by your repo
PY      ?= server/venv312/bin/python
PSQL    ?= psql -d 2ndopinionmd
API_BASE?= http://localhost:8000

# ---- Schema ----
neurolex-schema:
	@$(PSQL) -v ON_ERROR_STOP=1 -f database/schemas/setup_neurolex_schema.sql

neurolex-core:
	@$(PSQL) -v ON_ERROR_STOP=1 -f database/sql/17_neurolex_core.sql

# ---- Indexes (safe to re-run) ----
# Notes:
# - Trigram on label (fast ILIKE)
# - Array-GIN on synonyms (good for @> contains; ILIKE on arrays will still seq-scan)
# - Trigram on annotation value (robust across PG versions; avoids IMMUTABLE expr issues)
# - Prefix btree index to slice xref “system:value” pairs quickly
neurolex-add-indexes:
	@$(PSQL) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS neurolex_label_trgm ON ontology.neurolex USING gin (label gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS neurolex_syn_arr_gin ON ontology.neurolex USING gin (synonyms);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS neurolex_ann_value_trgm ON ontology.neurolex_annotations USING gin (value gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS neurolex_ann_value_prefix_idx ON ontology.neurolex_annotations (split_part(value, ':', 1), prop_label);"

# ---- Ingest from InterLex API ----
# Usage:
#   make neurolex-import-api LABEL="neurological disorder" SIZE=1000 PAGES=50
#   or: make neurolex-import-api PARENT_ILX="ilx_0123456"
neurolex-import-api:
	@test -n "$(SCICRUNCH_API_KEY)" || (echo "export SCICRUNCH_API_KEY first"; exit 2)
	@$(PY) server/scripts/ingest_neurolex.py \
		$(if $(PARENT_ILX),--parent-ilx "$(PARENT_ILX)",) \
		$(if $(LABEL),--label "$(LABEL)",) \
		--size "$(if $(SIZE),$(SIZE),1000)" \
		--pages "$(if $(PAGES),$(PAGES),50)"

# ---- Ingest from local JSON/JSONL (each line = _source dict from InterLex) ----
# Example: make neurolex-import-file FILE=data/neurolex.jsonl
neurolex-import-file:
	@test -n "$(FILE)" || (echo "FILE=path/to/neurolex.jsonl"; exit 2)
	@$(PY) server/scripts/ingest_neurolex.py --mode file --file "$(FILE)"

# ---- RAG upsert & embeddings (optional) ----
neurolex-rag-upsert:
	@$(PY) server/scripts/neurolex_rag_upsert.py $(if $(LIMIT),--limit $(LIMIT),)

neurolex-embed:
	@$(PY) server/scripts/embed_table.py \
	  --table ontology.neurolex --id-col ilx_id --text-col label \
	  --extra-cols definition,synonyms --embedding-col vec \
	  --model $(if $(MODEL),$(MODEL),text-embedding-3-small) \
	  --batch 256 --where "vec IS NULL"

# ---- Quick stats / API smoke ----
neurolex-stats:
	@$(PSQL) -c "SELECT COUNT(*) AS terms FROM ontology.neurolex;"
	@$(PSQL) -c "SELECT prop_label, COUNT(*) n FROM ontology.neurolex_annotations GROUP BY 1 ORDER BY n DESC LIMIT 10;"

neurolex-api-smoke:
	@curl -s "$(API_BASE)/api/neurolex/stats" | jq .
	@curl -s "$(API_BASE)/api/neurolex/search?q=optic&limit=5" | jq .

# ---- JSON audit (for the report) ----
neurolex-audit-sql:
	@$(PSQL) -tA -f database/sql/17_neurolex_audit.sql | jq .
