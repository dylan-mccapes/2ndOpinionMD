ICD11_FILE ?= data/who/icd11_eml_map.csv
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

who-indexes:
	@$(PSQL) -f server/scripts/who_indexes.sql
	@echo "[who-indexes] ok"

who-form-backfill:
	@$(PSQL) -f server/scripts/who_eml_form_backfill.sql
	@echo "[who_form_backfill] done"

ICD11_FILE ?= data/who/icd11_eml_map.csv

who-icd11-export-missing:
	@mkdir -p server/reports
	@$(PSQL) -v out="$(PWD)/server/reports/who_icd11_missing.csv" -f server/scripts/who_icd11_export_missing.psql
	@test -s server/reports/who_icd11_missing.csv || (echo "ERROR: export created empty CSV" >&2; exit 1)
	@echo "Wrote server/reports/who_icd11_missing.csv ($$(wc -l < server/reports/who_icd11_missing.csv) lines)"


who-icd11-backfill:
	@server/venv312/bin/python server/scripts/who_icd11_backfill.py "$(FILE)"

who-icd11-backfill-default:
	@$(MAKE) who-icd11-export-missing
	@cp server/reports/who_icd11_missing.csv $(ICD11_FILE)
	@$(MAKE) who-icd11-backfill FILE=$(ICD11_FILE)

# convenience
who-audit-json: who-audit


who-validate:
	@echo "[who-validate] null breakdown (route/form/strength):"
	@$(PSQL) -c "SELECT sum((COALESCE(route,'')='')::int) AS null_route, sum((COALESCE(dose_form,'')='')::int) AS null_form, sum((COALESCE(strength,'')='')::int) AS null_strength FROM guidelines.who_eml_formulations;"
	@echo "[who-validate] top 10 meds by missing formulations:"
	@$(PSQL) -c "SELECT m.inn, count(*) AS n_missing FROM guidelines.who_eml_medicines m JOIN guidelines.who_eml_formulations f USING (med_id) WHERE (COALESCE(f.route,'')='' OR COALESCE(f.dose_form,'')='' OR COALESCE(f.strength,'')='') GROUP BY m.inn ORDER BY n_missing DESC, m.inn LIMIT 10;"

who-audit: who-form-backfill who-indexes
	@server/venv312/bin/python server/scripts/who_audit_integrity.py --md server/reports/who_audit.md --json server/reports/who_audit.json
	@echo "Wrote server/reports/who_audit.md && server/reports/who_audit.json"

who-sweeps:
	@$(PSQL) -f server/scripts/who_eml_sweeps.sql
	@echo "[who_sweeps] done"
