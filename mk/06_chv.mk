# ---------- CHV file defaults ----------
STOP   ?= data/chv/stop_concepts.tsv
INCOR  ?= data/chv/incorrect_mappings.tsv
NGRAMS ?= data/chv/ngrams.tsv

PSQL ?= psql -d 2ndopinionmd -v ON_ERROR_STOP=1
CHV_DIR ?= data/chv

# ---------- CHV filters & ngrams: tables ----------
chv-filters-schema:
	@$(PSQL) -f database/sql/chv_filters.sql
	@$(PSQL) -f database/sql/chv_ngrams.sql

chv-load-stop: chv-filters-schema
	@$(PSQL) -v PROJECT_ROOT='$(PROJECT_ROOT)' -v STOP='$(STOP)' -f database/sql/chv_loaders.sql

chv-load-incorrect: chv-filters-schema
	@$(PSQL) -v PROJECT_ROOT='$(PROJECT_ROOT)' -v INCOR='$(INCOR)' -f database/sql/chv_loaders.sql

chv-load-ngrams: chv-filters-schema
	@$(PSQL) -v PROJECT_ROOT='$(PROJECT_ROOT)' -v NGRAMS='$(NGRAMS)' -f database/sql/chv_loaders.sql

# ---------- One-shot loader ----------
# Usage: make chv-filters-load-all STOP=... INCOR=... NGRAMS=...
chv-filters-load-all: chv-filters-schema
	@$(PSQL) -v PROJECT_ROOT='$(PROJECT_ROOT)' -v STOP='$(STOP)' -v INCOR='$(INCOR)' -v NGRAMS='$(NGRAMS)' -f database/sql/chv_loaders.sql
	@$(PSQL) -c "SELECT 'stop_cuis' AS what, COUNT(*) FROM ontology.chv_stop_cui \
	             UNION ALL SELECT 'incorrect', COUNT(*) FROM ontology.chv_incorrect_map \
	             UNION ALL SELECT 'ngrams', COUNT(*) FROM ontology.chv_ngrams;"

# Rebuild the disambiguated map (table), not a matview
chv-build-best:
	@$(PSQL) -f database/sql/chv_best.sql
	@echo "Rebuilt ontology.chv_best"

# Basic CHV counts
chv-audit:
	@echo
	@echo "== CHV — core counts =="
	@$(PSQL) -c "SELECT 'rows_total'   AS what, COUNT(*)                    AS n FROM ontology.synonyms WHERE source='CHV'"
	@$(PSQL) -c "SELECT 'distinct_cui' AS what, COUNT(DISTINCT cui)         AS n FROM ontology.synonyms WHERE source='CHV'"
	@$(PSQL) -c "SELECT 'distinct_term'AS what, COUNT(DISTINCT lower(term)) AS n FROM ontology.synonyms WHERE source='CHV'"
	@echo
	@echo "== CHV — quality checks =="
	@$(PSQL) -c "SELECT 'blank_terms' AS what, COUNT(*) AS n FROM ontology.synonyms WHERE source='CHV' AND (term IS NULL OR btrim(term)='')"
	@$(PSQL) -c "SELECT 'invalid_cui' AS what, COUNT(*) AS n FROM ontology.synonyms WHERE source='CHV' AND NOT (cui ~ '^C[0-9]{7}$$')"
	@$(PSQL) -c "SELECT 'dup_pairs'   AS what, COUNT(*) AS n FROM (SELECT lower(term), cui FROM ontology.synonyms WHERE source='CHV' GROUP BY 1,2 HAVING COUNT(*)>1) d"
	@echo
	@echo "== CHV — ambiguous terms (same lay term → multiple CUIs) =="
	@$(PSQL) -c "SELECT term, COUNT(DISTINCT cui) AS n_cui FROM ontology.synonyms WHERE source='CHV' GROUP BY term HAVING COUNT(DISTINCT cui)>1 ORDER BY n_cui DESC, term LIMIT 15"
	@echo
	@echo "== CHV — top CUIs by term count =="
	@$(PSQL) -c "SELECT cui, COUNT(*) AS n FROM ontology.synonyms WHERE source='CHV' GROUP BY cui ORDER BY n DESC, cui LIMIT 15"

# Snapshots (CSV with today’s date)
chv-snapshots:
	@mkdir -p snapshots
	@$(PSQL) -At -c "COPY ( \
	  SELECT 'rows_total'  , COUNT(*)                    FROM ontology.synonyms WHERE source='CHV' UNION ALL \
	  SELECT 'distinct_cui', COUNT(DISTINCT cui)         FROM ontology.synonyms WHERE source='CHV' UNION ALL \
	  SELECT 'distinct_term',COUNT(DISTINCT lower(term)) FROM ontology.synonyms WHERE source='CHV' UNION ALL \
	  SELECT 'blank_terms' , COUNT(*)                    FROM ontology.synonyms WHERE source='CHV' AND (term IS NULL OR btrim(term)='') UNION ALL \
	  SELECT 'invalid_cui' , COUNT(*)                    FROM ontology.synonyms WHERE source='CHV' AND NOT (cui ~ '^C[0-9]{7}$$') \
	) TO STDOUT WITH (FORMAT csv)" > snapshots/CHV_`date +%Y-%m-%d`.csv
	@echo "CHV snapshots written."

# Ambiguity metric (raw vs post-best)
chv-ambig-metrics:
	@$(PSQL) -At -c "WITH \
	raw AS (SELECT COUNT(*)::float AS n FROM (SELECT lower(term) tl FROM ontology.synonyms WHERE source='CHV' GROUP BY tl HAVING COUNT(DISTINCT cui)>1) s), \
	post AS (SELECT COUNT(*)::float AS n FROM (SELECT term_lower FROM ontology.chv_best GROUP BY term_lower HAVING COUNT(*)>1) s), \
	den AS (SELECT COUNT(DISTINCT lower(term))::float AS n FROM ontology.synonyms WHERE source='CHV') \
	SELECT 'raw_rate|'||(raw.n/den.n)||'|post_rate|'||(post.n/den.n) FROM raw,post,den"
	
# Full integrity pass + PDF
chv-integrity-all: chv-audit chv-build-best chv-ambig-metrics chv-snapshots
	@$(PY) server/scripts/report_chv_pdf.py --out db_integrity_reports/06_chv.pdf $(if $(AI),--ai,)
	@echo "Wrote db_integrity_reports/06_chv.pdf"

api-chv-stats:
	@echo
	@echo "GET $(API_BASE)/api/chv/stats"
	@curl -s "$(API_BASE)/api/chv/stats" | jq .

api-chv-ngrams-search:
	@echo "GET $(BASE_URL)/api/chv/ngrams/search?q=$${Q:-pain}&limit=$${LIMIT:-10}"
	@curl -sS "$(BASE_URL)/api/chv/ngrams/search?q=$${Q:-pain}&limit=$${LIMIT:-10}" | jq .

api-chv-ngrams-cui:
	@echo "GET $(BASE_URL)/api/chv/ngrams/cui/$${CUI:-C0011849}?limit=$${LIMIT:-10}"
	@curl -sS "$(BASE_URL)/api/chv/ngrams/cui/$${CUI:-C0011849}?limit=$${LIMIT:-10}" | jq .

.PHONY: api-chv-ngrams api-chv-ngrams-map

api-chv-ngrams:
	@echo "GET /api/chv/ngrams/search?q=$(Q)&limit=$(LIMIT)" 1>&2
	@curl -sS "http://localhost:8000/api/chv/ngrams/search?q=$(Q)&limit=$(LIMIT)" | jq .

api-chv-ngrams-map:
	@echo "GET /api/chv/ngrams/map?q=$(Q)&limit=$(LIMIT)" 1>&2
	@curl -sS "http://localhost:8000/api/chv/ngrams/map?q=$(Q)&limit=$(LIMIT)" | jq .


