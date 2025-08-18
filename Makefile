# 2ndOpinionMD – minimal local Makefile (frontend only)
# Build from frontend/react and deploy to local nginx docroot

FRONTEND_DIR := frontend/react
FRONTEND_DEPLOY_PATH := /opt/homebrew/var/www/2ndopinionmd
RELEASES_DIR := /opt/homebrew/var/www/2ndopinionmd_releases
HOST := 2ndopinionmd.ai

.PHONY: ship fe-build deploy-fe nginx-reload smoke verify-live rollback clean fe-clean loinc-import

ship: fe-build deploy-fe nginx-reload ## Build FE, deploy, reload nginx

fe-build: ## Build production bundle
	@echo ">>> Building frontend"
	cd $(FRONTEND_DIR) && yarn install && CI= yarn build
	@echo ">>> Build complete at $(FRONTEND_DIR)/build"

deploy-fe: ## Rsync build to live + timestamped release
	@echo ">>> Deploying to $(FRONTEND_DEPLOY_PATH)"
	TS=$$(date +%F-%H%M); \
	sudo mkdir -p $(RELEASES_DIR)/$$TS; \
	sudo rsync -a --delete $(FRONTEND_DIR)/build/ $(RELEASES_DIR)/$$TS/; \
	sudo rsync -a --delete $(FRONTEND_DIR)/build/ $(FRONTEND_DEPLOY_PATH)/
	@echo ">>> Frontend deployed."

nginx-reload: ## Reload nginx
	@echo ">>> Reloading nginx"
	sudo nginx -t && sudo nginx -s reload
	@echo ">>> nginx reloaded."

smoke: ## Quick check
	@curl -sI https://$(HOST)/ | sed -n '1p;/etag/Ip;/last-modified/Ip'
	@curl -sf https://$(HOST)/api/health | jq . || curl -sf https://$(HOST)/api/health

verify-live: ## Verify live bundle has AI Analysis strings
	@JS=$$(curl -s https://$(HOST)/asset-manifest.json | jq -r '.files["main.js"]'); \
	echo "main bundle: $$JS"; \
	curl -s "https://$(HOST)$$JS" | strings | egrep -o "AI Analysis|Diagnoses|Environmental Factors|Life Stressors|Pattern Observations|Journaling Recommendation" | sort -u || true

rollback: ## make rollback REL=YYYY-MM-DD-HHMM
	@test -n "$(REL)" || (echo "Usage: make rollback REL=YYYY-MM-DD-HHMM" ; exit 1)
	sudo rsync -a --delete $(RELEASES_DIR)/$(REL)/ $(FRONTEND_DEPLOY_PATH)/
	sudo nginx -s reload

clean: fe-clean
	@echo ">>> Clean complete."

fe-clean:
	@echo ">>> Cleaning frontend build artifacts"
	rm -rf $(FRONTEND_DIR)/build

loinc-import: ## Import LOINC data from hosted ZIP URL
	@echo ">>> LOINC import"
	@. server/venv312/bin/activate && \
	python server/scripts/ingest_loinc.py --zip-url $(ZIP_URL)
# Usage: make loinc-import ZIP_URL=https://2ndopinionmd.ai/private/loinc-34efcd3d8beb/loinc.zip

