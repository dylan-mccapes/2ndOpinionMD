# =========================
# 17) NeuroLex (InterLex)
# =========================
neurolex-schema:
	@$(PSQL) -v ON_ERROR_STOP=1 -f database/schemas/setup_neurolex_schema.sql

neurolex-indexes:
	@$(PSQL) -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS neurolex_label_trgm ON ontology.neurolex USING gin (label gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS neurolex_synonyms_expr_trgm ON ontology.neurolex USING gin ((array_to_string(synonyms,' ')) gin_trgm_ops);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS neurolex_ann_value_prefix_idx ON ontology.neurolex_annotations (split_part(value, ':', 1), prop_label);"
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS neurolex_ann_value_fts ON ontology.neurolex_annotations USING gin (to_tsvector('english', value));"

neurolex-import-api:
	@test -n "$(SCICRUNCH_API_KEY)" || (echo "export SCICRUNCH_API_KEY first"; exit 2)
	@$(PY) server/scripts/ingest_neurolex.py $(if $(PARENT_ILX),--parent-ilx "$(PARENT_ILX)",) $(if $(LABEL),--label "$(LABEL)",) --size "$(if $(SIZE),$(SIZE),1000)" --pages "$(if $(PAGES),$(PAGES),50)"

neurolex-import-file:
	@test -n "$(FILE)" || (echo "FILE=path/to/neurolex.jsonl"; exit 2)
	@$(PY) server/scripts/ingest_neurolex.py --mode file --file "$(FILE)"

neurolex-embed:
	@$(PY) server/scripts/embed_table.py \
	  --table ontology.neurolex --id-col ilx_id --text-col label \
	  --extra-cols definition,synonyms --embedding-col vec \
	  --model $(if $(MODEL),$(MODEL),text-embedding-3-small) \
	  --batch 256 --where "vec IS NULL"

neurolex-stats:
	@$(PSQL) -c "SELECT COUNT(*) AS terms FROM ontology.neurolex;"
	@$(PSQL) -c "SELECT prop_label, COUNT(*) n FROM ontology.neurolex_annotations GROUP BY 1 ORDER BY n DESC LIMIT 10;"

neurolex-import-query:
	@$(PY) server/scripts/ingest_neurolex_query.py --query '$(Q)' --size $(if $(SIZE),$(SIZE),500) --pages $(if $(PAGES),$(PAGES),20)

neurolex-reindex:
	@$(PSQL) -c "UPDATE ontology.neurolex SET ts = to_tsvector('english', coalesce(label,'')||' '||coalesce(definition,'')||' '||coalesce(array_to_string(synonyms,' '),'')); CREATE INDEX IF NOT EXISTS neurolex_ts_gin ON ontology.neurolex USING gin (ts); ANALYZE ontology.neurolex;"

neurolex-rag-upsert:
	@$(PY) server/scripts/neurolex_rag_upsert.py $(if $(LIMIT),--limit $(LIMIT),)

neurolex-rag-upsert-since:
	@$(PY) server/scripts/neurolex_rag_upsert.py --since "$(SINCE)" $(if $(LIMIT),--limit $(LIMIT),)

neurolex-rag-upsert-dry:
	@$(PY) server/scripts/neurolex_rag_upsert.py --dry-run $(if $(LIMIT),--limit $(LIMIT),)

api-neurolex-search:
	@curl -s "$(API_BASE)/api/neurolex/search?q=$(Q)&limit=$(LIMIT)" | jq .

api-neurolex-term:
	@curl -s "$(API_BASE)/api/neurolex/term/$(ILX)" | jq .

neurolex-api-smoke:
	@curl -s "$${API_BASE}/api/neurolex/stats" | jq .
	@curl -s "$${API_BASE}/api/neurolex/search?q=optic&limit=5" | jq .

neurolex-rag-semantic:
	@test -n "$(Q)" || (echo "Usage: make neurolex-rag-semantic Q='query'"; exit 2)
	@EMB=$$($(PY) - <<'PY'
		from openai import OpenAI; import os,sys
		q=os.environ.get("Q",""); 
		if not q: sys.exit(1)
		client=OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
		vec=client.embeddings.create(model="text-embedding-3-small", input=q).data[0].embedding
		print("[" + ",".join(f"{x:.6f}" for x in vec) + "]", end="")
		PY
	); \
	$(PSQL) -v ON_ERROR_STOP=1 <<SQL
			SET ivfflat.probes = $(PROBES);
			WITH q AS (SELECT '$$EMB'::vector AS e)
			SELECT id, source, LEFT(title,120) AS title, ROUND(1 - (embedding <=> q.e)::numeric, 4) AS cosine_sim
			FROM public.rag_corpus, q
			WHERE source='neurolex'
			ORDER BY embedding <=> q.e
			LIMIT $${LIMIT:-10};
		SQL

neurolex-ann-index:
	@$(PSQL) -c "SET maintenance_work_mem='256MB'; CREATE INDEX CONCURRENTLY IF NOT EXISTS rag_corpus_embedding_ann_neurolex ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists = $(LISTS)) WHERE source='neurolex'; ANALYZE public.rag_corpus;"

neurolex-ann-explain:
	@$(PSQL) -c "SET enable_seqscan=off; SET ivfflat.probes=$(PROBES); EXPLAIN ANALYZE WITH q AS (SELECT embedding e FROM public.rag_corpus WHERE source='neurolex' ORDER BY random() LIMIT 1) SELECT id, LEFT(title,120) FROM public.rag_corpus rc, q WHERE rc.source='neurolex' ORDER BY rc.embedding <=> q.e LIMIT 5;"

neurolex-ann-smoke:
	@$(PSQL) -c "SET ivfflat.probes=$(PROBES); WITH q AS (SELECT embedding e FROM public.rag_corpus WHERE source='neurolex' ORDER BY random() LIMIT 1) SELECT id, LEFT(title,120), (rc.embedding <=> q.e) AS dist FROM public.rag_corpus rc, q WHERE rc.source='neurolex' ORDER BY rc.embedding <=> q.e LIMIT 5;"

neurolex-audit-sql:
	@psql -d $${DB_NAME:-2ndopinionmd} -tA -f database/sql/17_neurolex_audit.sql | jq .

neurolex-add-indexes:
	@$(PSQL) -v ON_ERROR_STOP=1 <<'SQL'
		-- trigram on label (ILIKE)
		CREATE EXTENSION IF NOT EXISTS pg_trgm;
		CREATE INDEX IF NOT EXISTS neurolex_label_trgm
		ON ontology.neurolex USING gin (label gin_trgm_ops);

		-- generated text for synonyms to accelerate ILIKE on any synonym
		ALTER TABLE ontology.neurolex
		ADD COLUMN IF NOT EXISTS synonyms_text text
		GENERATED ALWAYS AS (array_to_string(synonyms,' ')) STORED;
		CREATE INDEX IF NOT EXISTS neurolex_synonyms_text_trgm
		ON ontology.neurolex USING gin (synonyms_text gin_trgm_ops);

		-- annotation value prefix already exists in your schema; keep it
		ANALYZE ontology.neurolex;
		ANALYZE ontology.neurolex_annotations;
		SQL

neurolex-add-indexes:
	@$(PSQL) -v ON_ERROR_STOP=1 <<'SQL'
		CREATE EXTENSION IF NOT EXISTS pg_trgm;
		ALTER TABLE ontology.neurolex
		ADD COLUMN IF NOT EXISTS synonyms_text text
		GENERATED ALWAYS AS (array_to_string(synonyms,' ')) STORED;
		CREATE INDEX IF NOT EXISTS neurolex_label_trgm
		ON ontology.neurolex USING gin (label gin_trgm_ops);
		CREATE INDEX IF NOT EXISTS neurolex_synonyms_text_trgm
		ON ontology.neurolex USING gin (synonyms_text gin_trgm_ops);
		ANALYZE ontology.neurolex;
		ANALYZE ontology.neurolex_annotations;
		SQL

neurolex-audit-sql:
	@$(PSQL) -f database/sql/17_neurolex_audit.sql -tA | jq .
