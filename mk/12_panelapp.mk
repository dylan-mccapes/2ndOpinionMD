# =========================
# 12) PanelApp Gene Panels
# =========================
# Conventions:
# - Schema file: database/schemas/molecular_panelapp_gene_panels.sql
# - Importer:    server/scripts/ingest_panelapp.py
#
# Env knobs:
#   PANELAPP_PANELS   = "Motor Neurone Disease,Multiple sclerosis susceptibility"
#   PANELAPP_IDS      = "127,20"              # optional: pin by ids instead of names
#   ALLOW_UNSIGNED    = 0|1                   # allow non-signed-off versions when necessary
#   PANELAPP_DEBUG    = 0|1
#   PANELAPP_VERIFY   = 1|0                   # 0 = allow insecure TLS (last resort)
#   API_BASE          = https://2ndopinionmd.ai (for api-* curl helpers)
#   GREEN             = true|false            # api filter toggle
#   Q                 = search terms          # api query for /search

# ---------- Schema ----------
panelapp-schema:
	@$(PSQL) -v ON_ERROR_STOP=1 -f database/schemas/molecular_panelapp_gene_panels.sql

# ---------- Import (names) ----------
panelapp-import:
	@PANELAPP_PANELS="$(PANELAPP_PANELS)" $(PY) server/scripts/ingest_panelapp.py
	@$(MAKE) panelapp-indexes

# ---------- Import (ids) ----------
panelapp-import-ids:
	@PANELAPP_ALLOW_UNSIGNED=$(ALLOW_UNSIGNED) PANELAPP_IDS="$(IDS)" $(PY) server/scripts/ingest_panelapp.py
	@$(MAKE) panelapp-indexes

# ---------- Index pack ----------
panelapp-indexes:
	@$(PSQL) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gp_panel_name_trgm       ON molecular.gene_panels USING gin (panel_name gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gp_gene_symbol_trgm      ON molecular.gene_panels USING gin (gene_symbol gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gp_ts_gin               ON molecular.gene_panels USING gin (ts);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gp_signedoff_idx        ON molecular.gene_panels (signed_off);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gp_panel_id_version_idx ON molecular.gene_panels (panel_id, panel_version);"

# ---------- RAG upsert + embed ----------
panelapp-rag-upsert:
	@$(PSQL) -c "\
		INSERT INTO public.rag_corpus (source, title, text, ts) \
		SELECT 'panelapp', 'Panel: '||panel_name||' ??? '||gene_symbol, \
		trim(both ' ' FROM concat_ws(' ', 'Panel:', panel_name, 'Gene:', gene_symbol, 'Confidence:', coalesce(confidence_level,''), \
		'MOI:', coalesce(mode_of_inheritance,''), 'Phenotypes:', coalesce(array_to_string(phenotypes,'; '),''), \
		'Evidence:', coalesce(array_to_string(evidence,'; '),''), 'Relevant disorders:', coalesce(array_to_string(relevant_disorders,' '),''))) AS text, \
		to_tsvector('english', coalesce(panel_name,'')||' '||coalesce(gene_symbol,'')||' '||coalesce(array_to_string(phenotypes,' '),'')||' '|| \
		coalesce(array_to_string(evidence,' '),'')||' '||coalesce(array_to_string(relevant_disorders,' '),'')) \
		FROM molecular.gene_panels gp \
		WHERE NOT EXISTS (SELECT 1 FROM public.rag_corpus rc WHERE rc.source='panelapp' AND rc.title='Panel: '||gp.panel_name||' ??? '||gp.gene_symbol); \
		UPDATE public.rag_corpus SET ts = to_tsvector('english', coalesce(title,'')||' '||coalesce(text,'')) WHERE source='panelapp';"

panelapp-embed:
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus --id-col id --text-col text \
	  --embedding-col embedding --model text-embedding-3-small \
	  --batch 256 --where "source='panelapp' AND embedding IS NULL"

panelapp-rag: panelapp-rag-upsert panelapp-embed

# ---------- Quick API helpers ----------
api-panelapp-stats:
	@curl -s "$(API_BASE)/api/panelapp/stats" | jq .

api-panelapp-search:
	@curl -s "$(API_BASE)/api/panelapp/search?q=$(Q)&only_green=$(GREEN)" | jq .

api-panelapp-panel:
	@curl -s "$(API_BASE)/api/panelapp/panel/$(PANEL_ID)?only_green=$(GREEN)" | jq .

# ---------- Sanity smoke ----------
panelapp-smoke:
	@$(PSQL) -c "SELECT to_regclass('molecular.gene_panels') AS has_table;"
	@$(PSQL) -c "SELECT COUNT(*) AS rows, COUNT(DISTINCT (panel_id, panel_version)) AS unique_panels, COUNT(DISTINCT gene_symbol) AS unique_genes FROM molecular.gene_panels;"
	@$(PSQL) -c "SELECT confidence_level, COUNT(*) AS n FROM molecular.gene_panels GROUP BY 1 ORDER BY 2 DESC;"
	@$(PSQL) -c "SELECT panel_name, panel_version, COUNT(*) AS genes FROM molecular.gene_panels GROUP BY 1,2 ORDER BY 3 DESC NULLS LAST LIMIT 10;"

# ---- Terminal verdict (PASS/WARN/FAIL)
# Defaults if not set upstreamPSQL ?= psql -d 2ndopinionmd

panelapp-status:
	@$(PSQL) -t -A -c "\
	WITH rows AS (SELECT COUNT(*) r FROM molecular.gene_panels), \
	crit AS ( \
	  SELECT \
	    COUNT(*) FILTER (WHERE COALESCE(NULLIF(gene_symbol,''),NULL) IS NULL) AS bg, \
	    COUNT(*) FILTER (WHERE COALESCE(NULLIF(confidence_level::text,''),NULL) IS NULL) AS bc \
	  FROM molecular.gene_panels \
	) \
	SELECT CASE \
	  WHEN (SELECT r FROM rows)=0 THEN 'WARN: empty table' \
	  WHEN ((SELECT bg+bc FROM crit)::float / NULLIF((SELECT r FROM rows),0)) > 0.05 THEN 'WARN: critical blanks >5%' \
	  ELSE 'PASS' END;"

# Minimal route smoke (requires API_BASE and a PANEL_ID from /stats)
api-panelapp-ping:
	@test -n "$(API_BASE)" || (echo "Set API_BASE=http://localhost:8000" && exit 2)
	@echo "GET /api/panelapp/stats"
	@curl -sf "$(API_BASE)/api/panelapp/stats" >/dev/null || (echo "!! API down?" && exit 4)
	@echo "GET /api/panelapp/search"
	@curl -sf "$(API_BASE)/api/panelapp/search?q=neuron&only_green=false" >/dev/null || (echo "!! /search failed" && exit 4)
	@echo "OK"

api-panelapp-panelcheck:
	@test -n "$(API_BASE)" || (echo "Set API_BASE=http://localhost:8000" && exit 2)
	@test -n "$(PANEL_ID)" || (echo "Set PANEL_ID=<id from stats>" && exit 2)
	@exp=$$( $(PSQL) -t -A -c "\
	  WITH latest AS ( \
	    SELECT panel_version FROM molecular.gene_panels \
	    WHERE panel_id=$(PANEL_ID) \
	    ORDER BY \
	      COALESCE(NULLIF(split_part(panel_version,'.',1), '')::int, 0) DESC, \
	      COALESCE(NULLIF(split_part(panel_version,'.',2), '')::int, 0) DESC, \
	      COALESCE(NULLIF(split_part(panel_version,'.',3), '')::int, 0) DESC, \
	      imported_at DESC \
	    LIMIT 1 \
	  ) \
	  SELECT COUNT(*) FROM molecular.gene_panels \
	  WHERE panel_id=$(PANEL_ID) AND panel_version=(SELECT panel_version FROM latest);" ); \
	n_api=$$(curl -sf "$(API_BASE)/api/panelapp/panel/$(PANEL_ID)?only_green=false" | jq -r '.panel.n_genes'); \
	test "$$n_api" = "$$exp" || (echo "!! n_genes $$n_api != $$exp" && exit 5); \
	echo "panel $(PANEL_ID): $$n_api genes (OK)"

# ---- Route smoke tests (set API_BASE and a valid PANEL_ID)
api-panelapp-test:
	@test -n "$(API_BASE)" || (echo "Set API_BASE=https://your-host" && exit 2)
	@echo "GET /api/panelapp/stats"
	@curl -sf "$(API_BASE)/api/panelapp/stats" | jq -e '.panels | type=="array"' >/dev/null
	@echo "GET /api/panelapp/search?q=neuron"
	@curl -sf "$(API_BASE)/api/panelapp/search?q=neuron&only_green=false" | jq -e '.count>=0 and (.results | type=="array")' >/dev/null

	@test -n "$(PANEL_ID)" || (echo "Set PANEL_ID=<an id from stats>" && exit 2)
	@echo "GET /api/panelapp/panel/$(PANEL_ID) (latest version)"
	@res=$$(curl -sf "$(API_BASE)/api/panelapp/panel/$(PANEL_ID)?only_green=false"); \
	  got=$$(echo "$$res" | jq -r '.panel.n_genes'); \
	  exp=$$(\
	    $(PSQL) -t -A -c " \
	      WITH latest AS ( \
	        SELECT panel_version FROM molecular.gene_panels \
	        WHERE panel_id=$(PANEL_ID) \
	        ORDER BY \
	          COALESCE(NULLIF(split_part(panel_version,'.',1), '')::int, 0) DESC, \
	          COALESCE(NULLIF(split_part(panel_version,'.',2), '')::int, 0) DESC, \
	          COALESCE(NULLIF(split_part(panel_version,'.',3), '')::int, 0) DESC, \
	          imported_at DESC \
	        LIMIT 1 \
	      ) \
	      SELECT COUNT(*) FROM molecular.gene_panels \
	      WHERE panel_id=$(PANEL_ID) AND panel_version=(SELECT panel_version FROM latest);" \
	  ); \
	  test "$$got" -eq "$$exp" || (echo "!! n_genes $$got != expected $$exp" && exit 1); \
	  echo "panel/$(PANEL_ID): n_genes = $$got (OK)"

