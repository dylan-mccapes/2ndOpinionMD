# ==========================================================
# 19) WHO — EML, AWARE, Expert Committee (exec summary)
# ==========================================================
who-reqs:
	@$(PY) -m pip install --upgrade pandas openpyxl pypdf psycopg2-binary python-calamine

who-eml: who-eml-schema who-eml-import who-eml-rag who-eml-ann who-eml-api-smoke
who-eml-schema:
	@$(PSQL) -f database/schemas/guidelines_who_eml.sql
who-eml-import:
	@FILE="$${FILE:-data/who/eml_2025.xlsx}"; $(PY) server/scripts/who_eml_import.py --file "$$FILE"
who-eml-rag: who-eml-rag-upsert who-eml-embed
who-eml-rag-upsert:
	@$(PSQL) -f server/scripts/rag_upsert_who_eml.sql
who-eml-embed:
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus --id-col id --text-col text --embedding-col embedding \
	  --model text-embedding-3-small --batch 256 --where "source='who_eml' AND embedding IS NULL"
who-eml-ann:
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_who_eml ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists=200) WHERE source='who_eml'; ANALYZE public.rag_corpus;"
who-eml-api-smoke:
	@curl -s "$(API_BASE)/api/who/eml/stats" | jq .

# Committee (exec summary PDF)
who-committee: who-committee-import who-committee-rag who-committee-ann who-committee-api-smoke
who-committee-import:
	@PDF="$${FILE:-data/who/expert_committee_2025_execsum.pdf}"; \
	$(PY) server/scripts/who_committee_import.py --pdf "$$PDF" --year "$${YEAR:-2025}" --eml "$${EML:-24}" --emlc "$${EMLC:-10}" \
	  --title "$${TITLE:-The selection and use of essential medicines, 2025: report of the 25th WHO Expert Committee}"
who-committee-rag: who-committee-rag-upsert who-committee-embed
who-committee-rag-upsert:
	@$(PSQL) -f server/scripts/rag_upsert_who_committee.sql
who-committee-embed:
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus --id-col id --text-col text --embedding-col embedding \
	  --model text-embedding-3-small --batch 256 --where "source='who_committee' AND embedding IS NULL"
who-committee-ann:
	@$(PSQL) -c "CREATE INDEX IF NOT EXISTS rag_corpus_embedding_ann_who_committee ON public.rag_corpus USING ivfflat (embedding vector_cosine_ops) WITH (lists=200) WHERE source='who_committee'; ANALYZE public.rag_corpus;"
who-committee-api-smoke:
	@curl -s "$(API_BASE)/api/who/committee/stats" | jq .

# WHO AWaRe → EML linkage
who-aware-import:
	@$(PY) server/scripts/who_aware_import.py --file $(FILE) $(if $(SHEET),--sheet '$(SHEET)',)
who-aware-apply:
	@$(PSQL) -f server/scripts/who_eml_apply_aware.sql
who-aware-smoke:
	@curl -s "$(API_BASE)/api/who/aware/stats" | jq .

# --- Audit & Integrity ---
who-audit:
	@$(PY) server/scripts/who_audit_integrity.py --md server/reports/who_audit.md
	@echo "Wrote server/reports/who_audit.md"; tail -n +1 server/reports/who_audit.md | sed -n '1,80p'

who-audit-json:
	@$(PY) server/scripts/who_audit_integrity.py --md server/reports/who_audit.md --json server/reports/who_audit.json
	@jq . server/reports/who_audit.json | sed -n '1,80p'

who-audit-api-smoke:
	@curl -s "$(API_BASE)/api/who/audit" | jq .
