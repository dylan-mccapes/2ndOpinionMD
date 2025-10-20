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

diagrules-rag-upsert:
	@$(PY) server/scripts/diagrules_rag_upsert.py

diagrules-embed:
	@$(PY) server/scripts/embed_table.py \
	  --table public.rag_corpus --id-col id --text-col text --embedding-col embedding \
	  --model text-embedding-3-small --batch 256 \
	  --where "source='acr_eular' AND embedding IS NULL"

diagrules-rag: diagrules-rag-upsert diagrules-embed

# Quick health SQL
diagrules-smoke:
	@$(PSQL) -c "SELECT COUNT(*) rules FROM guidelines.diagnostic_rules;"
	@$(PSQL) -c "SELECT COUNT(*) tests FROM guidelines.diagnostic_rule_tests;"

# API smoke: list → pick a key → get → (optional) apply sample for McDonald 2017
api-diagrules-smoke:
	@set -e; \
	base="$(API_BASE)"; \
	echo "GET $$base/api/diagnostic_rules/list"; \
	k=$$(curl -sf "$$base/api/diagnostic_rules/list" | jq -r '.[0].rule_key'); \
	[ -n "$$k" ] || (echo "No rules in API list"; exit 2); \
	echo "Rule key -> $$k"; \
	echo "GET $$base/api/diagnostic_rules/$$k"; \
	curl -sf "$$base/api/diagnostic_rules/$$k" | jq -r '.rule_key' >/dev/null; \
	if [ "$$k" = "mcdonald_2017" ]; then \
	  echo "POST $$base/api/diagnostic_rules/$$k/apply"; \
	  curl -sf -X POST "$$base/api/diagnostic_rules/$$k/apply" \
	    -H 'Content-Type: application/json' \
	    -d '{"has_typical_cis":true,"mri_lesion_sites_positive":3,"new_t2_or_gad_on_followup":true}' \
	    | jq . >/dev/null; \
	fi; \
	echo "✓ API diagnostic_rules smoke passed"

diagrules-tests-seed:
	@$(PSQL) -c "INSERT INTO guidelines.diagnostic_rule_tests (rule_key, patient_facts, expected_label) \
	SELECT r.rule_key, '{}'::jsonb, 'n/a' \
	FROM guidelines.diagnostic_rules r \
	LEFT JOIN guidelines.diagnostic_rule_tests t USING (rule_key) \
	WHERE t.rule_key IS NULL;"

diagrules-report-all: diagrules-tests-seed diagrules-smoke
	@AI=1 $(MAKE) diagrules-report

diagrules-test:
	@PYTHONPATH=. $(PY) server/scripts/run_diagnostic_rule_tests.py --junit build/test-results/diagrules.xml
