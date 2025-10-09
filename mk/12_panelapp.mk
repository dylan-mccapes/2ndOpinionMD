# =========================
# 12) PanelApp Gene Panels
# =========================
panelapp-schema:
	@$(PSQL) -v ON_ERROR_STOP=1 -f database/schemas/012_panelapp_gene_panels.sql

panelapp-import:
	@PANELAPP_PANELS="$(PANELAPP_PANELS)" $(PY) server/scripts/panelapp_import.py
	@$(MAKE) panelapp-indexes

panelapp-import-ids:
	@PANELAPP_ALLOW_UNSIGNED=$(ALLOW_UNSIGNED) PANELAPP_IDS="$(IDS)" $(PY) server/scripts/panelapp_import.py
	@$(MAKE) panelapp-indexes

panelapp-indexes:
	@$(PSQL) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gp_panel_name_trgm    ON molecular.gene_panels USING gin (panel_name gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gp_gene_symbol_trgm   ON molecular.gene_panels USING gin (gene_symbol gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gp_ts_gin            ON molecular.gene_panels USING gin (ts);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gp_signedoff_idx     ON molecular.gene_panels (signed_off);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS gp_panel_id_version_idx ON molecular.gene_panels (panel_id, panel_version);"

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

api-panelapp-stats:
	@curl -s "$(API_BASE)/api/panelapp/stats" | jq .

api-panelapp-search:
	@curl -s "$(API_BASE)/api/panelapp/search?q=$(Q)&only_green=$(GREEN)" | jq .

api-panelapp-panel:
	@curl -s "$(API_BASE)/api/panelapp/panel/$(PANEL_ID)?only_green=$(GREEN)" | jq .

