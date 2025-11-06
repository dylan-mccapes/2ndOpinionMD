# =========================
# Backend control / Health
# =========================
.PHONY: be-stop be-start be-restart be-hard-restart be-logs api-health post-launch-checks

be-stop:
	@pkill -f "uvicorn.*server.api.app_postgres:app" || true

be-start:
	@nohup $(PY) server/scripts/run_postgres_app.py > /tmp/uvicorn.out 2>&1 & echo ">>> uvicorn started (tail with make be-logs)"

be-restart: be-stop be-start

be-hard-restart:
	@pkill -9 -f "uvicorn.*app_postgres:app" || true; pkill -9 -f "python .*run_postgres_app.py" || true
	@find server -name "__pycache__" -type d -exec rm -rf {} +; find server -name "*.pyc" -delete
	@$(MAKE) be-start

be-logs:
	@tail -n 200 -f /tmp/uvicorn.out

api-health:
	@curl -s "$(API_BASE)/api/health" | jq .

post-launch-checks: integrity-all backup-verify
	@echo "✅ Post-launch checks complete."

clear-users:
	@read -p "This WILL DELETE all users + journals. Type 'yes' to continue: " ans; \
	[ "$$ans" = "yes" ] || { echo "Cancelled."; exit 1; }; \
	psql "$(DB)" -v ON_ERROR_STOP=1 -c "TRUNCATE TABLE public.journal_entries, public.users RESTART IDENTITY CASCADE;"; \
	psql "$(DB)" -v ON_ERROR_STOP=1 -c "SELECT COUNT(*) AS users FROM public.users;"; \
	psql "$(DB)" -v ON_ERROR_STOP=1 -c "SELECT COUNT(*) AS journals FROM public.journal_entries;"