# =====================================================
# 14) ACR / EULAR Diagnostic Criteria (rule objects)
# =====================================================
diagrules-schema:
	@$(PSQL) -f database/schemas/setup_diagnostic_rules.sql

diagrules-import: diagrules-schema
	@$(PY) server/scripts/ingest_diagnostic_rules.py --file data/diagnostic_rules_seed.json

diagrules-list:
	@curl -s "$(API_BASE)/api/diagnostic_rules/list?q=$(Q)" | jq .

diagrules-apply-sample:
	@curl -s -X POST "$(API_BASE)/api/diagnostic_rules/mcdonald_2017/apply" \
	  -H 'Content-Type: application/json' \
	  -d '{"has_typical_cis":true,"mri_lesion_sites_positive":3,"clinical_evidence_multiple_sites":false,"simultaneous_gad_non_gad":false,"new_t2_or_gad_on_followup":true,"csf_oligoclonal_bands":false,"better_diagnosis_present":false,"progression_1_year":false,"spinal_cord_lesions":0,"brain_mri_consistent":false}' | jq .

diagrules-test:
	@PYTHONPATH=. $(PY) server/scripts/run_diagnostic_rule_tests.py

diagrules-rag-upsert:
	@$(PY) server/scripts/diagrules_rag_upsert.py

diagrules-embed:
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus --id-col id --text-col text --embedding-col embedding \
	  --model text-embedding-3-small --batch 256 \
	  --where "source='acr_eular' AND embedding IS NULL"

diagrules-rag: diagrules-rag-upsert diagrules-embed

