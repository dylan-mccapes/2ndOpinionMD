# =========================
# Human Phenotype Ontology (HPO) — ops targets
# =========================

# Ensure bash + fail-fast for recipes
SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c

# ------- Existing API helpers (keep as-is) -------
hpo-import:
	@$(PY) ontology_loaders/hpo/load_hpo_terms.py data/hpo/hp.json

hpo-links-import:
	@$(PY) ontology_loaders/hpo/load_hpo_disease_links.py data/hpo/phenotype.hpoa

api-hpo-search:
	@curl -s "$(API_BASE)/api/hpo/search?q=$(Q)&limit=$(LIMIT)" | jq .

api-hpo-term:
	@curl -s "$(API_BASE)/api/hpo/term/$(HPO)" | jq .

# ------- Config -------
HPO_DIR          ?= data/hpo
HPO_JSON         ?= $(HPO_DIR)/hp.json
# Primary OBOGraphs JSON PURL (preferred)
HPO_JSON_PURL    ?= https://purl.obolibrary.org/obo/hp.json
# Fallback JSON (sometimes not OG-json) + OWL for local convert
HPO_JSON_FALLBACK?= https://purl.obolibrary.org/obo/hp/hp-international.json
HPO_OWL_PURL     ?= https://purl.obolibrary.org/obo/hp.owl

HPO_SCHEMA       ?= ontology
HPO_TERMS        ?= hpo_terms
HPO_EDGES        ?= hpo_edges
HPO_SYNONYMS     ?= hpo_synonyms
HPO_ID_COL       ?= hpo_id        # change to term_id or id if your terms use that

# ------- Fetch / Schema -------
hpo-dirs:
	@mkdir -p "$(HPO_DIR)"

# Try hp.json (OBOGraphs). If it lacks edges, try hp-international.json; if still bad and ROBOT is available, convert hp.owl -> hp.json (OG-json)
hpo-fetch-json: hpo-dirs
	@echo "Downloading (primary) $(HPO_JSON_PURL) → $(HPO_JSON)"
	@curl -fsSL "$(HPO_JSON_PURL)" -o "$(HPO_JSON)" || true
	@server/venv312/bin/python server/scripts/hpo_json_summary.py --json "$(HPO_JSON)" --require-graphs --min-edges 1000 || { \
		echo "Primary file missing edges; trying fallback JSON…"; \
		curl -fsSL "$(HPO_JSON_FALLBACK)" -o "$(HPO_JSON).tmp" || true; \
		server/venv312/bin/python server/scripts/hpo_json_summary.py --json "$(HPO_JSON).tmp" --require-graphs --min-edges 1000 && mv "$(HPO_JSON).tmp" "$(HPO_JSON)" || { \
			echo "Fallback still missing edges; trying ROBOT convert from OWL…"; \
			curl -fsSL "$(HPO_OWL_PURL)" -o "$(HPO_DIR)/hp.owl"; \
			if command -v robot >/dev/null 2>&1; then \
				robot convert -i "$(HPO_DIR)/hp.owl" --format json -o "$(HPO_JSON)"; \
				server/venv312/bin/python server/scripts/hpo_json_summary.py --json "$(HPO_JSON)" --require-graphs --min-edges 1000; \
			else \
				echo "ERROR: ROBOT CLI not found (see https://robot.obolibrary.org/ for install instructions)."; \
				exit 1; \
			fi; \
		}; \
	}
	@echo "OK: $(HPO_JSON)"

hpo-schema:
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -f database/schemas/ontology.hpo_edges.sql
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -f database/schemas/ontology.hpo_synonyms.sql

# ------- Import / Index / Stats -------
hpo-import-edges-syns:
	@server/venv312/bin/python server/scripts/ingest_hpo_json.py \
		--json "$(HPO_JSON)" --schema "$(HPO_SCHEMA)" \
		--terms "$(HPO_TERMS)" --edges "$(HPO_EDGES)" --synonyms "$(HPO_SYNONYMS)" \
		--truncate

hpo-indexes:
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS hpo_edges_child_idx  ON $(HPO_SCHEMA).$(HPO_EDGES)(child_id);"
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS hpo_edges_parent_idx ON $(HPO_SCHEMA).$(HPO_EDGES)(parent_id);"
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS hpo_synonyms_trgm ON $(HPO_SCHEMA).$(HPO_SYNONYMS) USING gin (synonym gin_trgm_ops);"
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -c "CREATE INDEX IF NOT EXISTS hpo_synonyms_id   ON $(HPO_SCHEMA).$(HPO_SYNONYMS)(hpo_id);"

hpo-stats:
	@psql -d 2ndopinionmd -c "SELECT COUNT(*) AS terms    FROM $(HPO_SCHEMA).$(HPO_TERMS);"
	@psql -d 2ndopinionmd -c "SELECT COUNT(*) AS edges    FROM $(HPO_SCHEMA).$(HPO_EDGES);"
	@psql -d 2ndopinionmd -c "SELECT COUNT(*) AS synonyms FROM $(HPO_SCHEMA).$(HPO_SYNONYMS);"
	@psql -d 2ndopinionmd -c "SELECT child_id, COUNT(*) AS deg_out FROM $(HPO_SCHEMA).$(HPO_EDGES) GROUP BY 1 ORDER BY deg_out DESC LIMIT 10;"

# ------- Fixups / Sanity -------
hpo-fix-ids:
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -c "UPDATE ontology.hpo_edges SET child_id=replace(upper(child_id),'HP_','HP:'), parent_id=replace(upper(parent_id),'HP_','HP:') WHERE child_id~*'hp[_:]' OR parent_id~*'hp[_:]';"
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -c "UPDATE ontology.hpo_synonyms SET hpo_id=replace(upper(hpo_id),'HP_','HP:') WHERE hpo_id~*'hp[_:]';"

hpo-dedupe-synonyms:
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -c "CREATE UNIQUE INDEX IF NOT EXISTS hpo_synonyms_norm_uniq ON ontology.hpo_synonyms (hpo_id, lower(regexp_replace(synonym,'[[:space:]]+',' ','g')));"
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -c "DELETE FROM ontology.hpo_synonyms a USING ontology.hpo_synonyms b WHERE a.ctid<b.ctid AND a.hpo_id=b.hpo_id AND lower(regexp_replace(a.synonym,'[[:space:]]+',' ','g'))=lower(regexp_replace(b.synonym,'[[:space:]]+',' ','g'));"

hpo-sanity:
	@echo "== Counters ==" && \
	psql -d 2ndopinionmd -c "SELECT COUNT(*) terms     FROM $(HPO_SCHEMA).$(HPO_TERMS);" && \
	psql -d 2ndopinionmd -c "SELECT COUNT(*) edges     FROM $(HPO_SCHEMA).$(HPO_EDGES);" && \
	psql -d 2ndopinionmd -c "SELECT COUNT(*) synonyms  FROM $(HPO_SCHEMA).$(HPO_SYNONYMS);"
	@echo "== Orphans =="
	@psql -d 2ndopinionmd -c "WITH t AS (SELECT $(HPO_ID_COL) AS id FROM $(HPO_SCHEMA).$(HPO_TERMS)) SELECT 'edges_child_orphans' AS what, COUNT(*) AS n FROM $(HPO_SCHEMA).$(HPO_EDGES) e LEFT JOIN t ON t.id=e.child_id WHERE t.id IS NULL UNION ALL SELECT 'edges_parent_orphans', COUNT(*) FROM $(HPO_SCHEMA).$(HPO_EDGES) e LEFT JOIN t ON t.id=e.parent_id WHERE t.id IS NULL UNION ALL SELECT 'syn_orphans', COUNT(*) FROM $(HPO_SCHEMA).$(HPO_SYNONYMS) s LEFT JOIN t ON t.id=s.hpo_id WHERE t.id IS NULL;"

# ------- Diagnostics -------
hpo-json-summary:
	@server/venv312/bin/python server/scripts/hpo_json_summary.py --json "$(HPO_JSON)" -v

# ------- Report -------
hpo-rebuild-report:
	@$(MAKE) hpo-report-pdf AI=1

hpo-drop-syn-uniq:
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -c "DROP INDEX IF EXISTS hpo_synonyms_norm_uniq;"

hpo-fix-terms-ids:
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 <<-SQL
		-- 1) HP_0000118 -> HP:0000118
		UPDATE $(HPO_SCHEMA).$(HPO_TERMS)
		   SET $(HPO_ID_COL) = replace(upper($(HPO_ID_COL)),'HP_','HP:')
		 WHERE $(HPO_ID_COL) ~* 'hp[_:]';

		-- 2) http(s)://purl.obolibrary.org/obo/HP_0000118 -> HP:0000118
		UPDATE $(HPO_SCHEMA).$(HPO_TERMS)
		   SET $(HPO_ID_COL) = regexp_replace($(HPO_ID_COL),
		     '^https?://purl\\.obolibrary\\.org/obo/HP_([0-9]+)$','HP:\\1')
		 WHERE $(HPO_ID_COL) ~ '^https?://purl\\.obolibrary\\.org/obo/HP_';
	SQL


# One-shot end-to-end
hpo-all: hpo-schema hpo-fetch-json hpo-import-edges-syns hpo-indexes hpo-fix-ids hpo-dedupe-synonyms hpo-drop-syn-uniq hpo-fix-terms-ids hpo-sanity hpo-rebuild-report

.PHONY: hpo-dirs hpo-fetch-json hpo-schema hpo-import-edges-syns hpo-indexes hpo-stats \
        hpo-fix-ids hpo-dedupe-synonyms hpo-sanity hpo-json-summary hpo-drop-syn-uniq \
        hpo-rebuild-report hpo-all hpo-import hpo-links-import api-hpo-search api-hpo-term
