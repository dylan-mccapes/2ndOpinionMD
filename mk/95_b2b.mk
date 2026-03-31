# =========================
# B2B API key infrastructure
# =========================
.PHONY: b2b-schema b2b-create-tenant b2b-create-key b2b-list-tenants b2b-list-keys b2b-revoke-key b2b-usage-report

b2b-schema: ## Apply B2B schema (tenants, api_keys, usage_events)
	@$(PSQL) -f database/sql/setup_b2b_schema.sql

b2b-create-tenant: ## TENANT_NAME=x EMAIL=x [PLAN=free] — create a B2B tenant
	@$(PY) -m server.b2b.manage_keys create-tenant --name "$(TENANT_NAME)" --email "$(EMAIL)" --plan "$(or $(PLAN),free)"

b2b-create-key: ## TENANT_ID=x SCOPES=mkg:read,mkg:evidence [NAME=label] — create API key
	@$(PY) -m server.b2b.manage_keys create-key --tenant-id "$(TENANT_ID)" --scopes "$(SCOPES)" $(if $(NAME),--name "$(NAME)",)

b2b-list-tenants: ## List all B2B tenants
	@$(PY) -m server.b2b.manage_keys list-tenants

b2b-list-keys: ## TENANT_ID=x — list API keys for a tenant
	@$(PY) -m server.b2b.manage_keys list-keys --tenant-id "$(TENANT_ID)"

b2b-revoke-key: ## KEY_ID=x — revoke an API key
	@$(PY) -m server.b2b.manage_keys revoke-key --key-id "$(KEY_ID)"

b2b-usage-report: ## Show B2B usage for last 24h
	@$(PSQL) -c "\
	  SELECT t.name AS tenant, k.key_last4, \
	         COUNT(*) AS requests, \
	         ROUND(AVG(u.response_ms)) AS avg_ms, \
	         SUM(u.tokens_used) AS tokens \
	  FROM b2b.usage_events u \
	  JOIN b2b.api_keys k ON k.id = u.api_key_id \
	  JOIN b2b.tenants t ON t.id = u.tenant_id \
	  WHERE u.created_at > NOW() - INTERVAL '24 hours' \
	  GROUP BY t.name, k.key_last4 \
	  ORDER BY requests DESC;"
