# ===============================
# 2ndOpinionMD — 00_main.mk
# ===============================

# ---------- Shell & PATH ----------
SHELL := /bin/zsh
.ONESHELL:
.SHELLFLAGS := -lc
export PATH := /opt/homebrew/bin:/opt/homebrew/sbin:/opt/homebrew/opt/libpq/bin:$(PATH)

# ---------- Core Vars ----------
export SYNC_DATABASE_URL ?= postgresql://2ndopinionmd@localhost:5432/2ndopinionmd
DB_NAME        ?= 2ndopinionmd
PY             ?= server/venv312/bin/python
PSQL           := psql "$$SYNC_DATABASE_URL"

# ---------- Common knobs ----------
API_BASE ?= http://localhost:8000
LISTS    ?= 200        # ivfflat lists for ANN
PROBES   ?= 8          # ivfflat probes
NOW      := $(shell date +%Y%m%d_%H%M%S)
EMBED_MAX_CHARS ?= 6000
JOBS ?= 0              # parallelism for backup scripts (0 = auto)

# ---------- Frontend ----------
FRONTEND_DIR         ?= frontend/react
FRONTEND_DEPLOY_PATH ?= /opt/homebrew/var/www/2ndopinionmd
RELEASES_DIR         ?= /opt/homebrew/var/www/2ndopinionmd_releases
HOST                 ?= 2ndopinionmd.ai

# ---------- PHONY ----------
.PHONY: help dev-setup env-doctor py-venv deps-install deps-upgrade pip-check \
        ship fe-build deploy-fe nginx-reload smoke verify-live rollback clean fe-clean \
        db-audit api-openapi rag-search rag-neighbors rag-backfill-meta

# ======================================
# Dev env helpers (brew, venv, deps)
# ======================================
help:
	@grep -E '^[a-zA-Z0-9_\-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}'

dev-setup:
	@echo ">>> Ensuring brew/libpq PATHs in ~/.zshrc and env loader (2omd_env)"
	BP=$$(brew --prefix 2>/dev/null || echo /opt/homebrew)
	ZRC="$$HOME/.zshrc"
	grep -q 'export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$$PATH"' "$$ZRC" 2>/dev/null || \
	  printf '%s\n' 'export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$$PATH"' >> "$$ZRC"
	LPQ_BIN="$$BP/opt/libpq/bin"
	[ -d "$$LPQ_BIN" ] && grep -q "$$LPQ_BIN" "$$ZRC" 2>/dev/null || printf '%s\n' 'export PATH='"$$LPQ_BIN"':$$PATH' >> "$$ZRC"
	if ! grep -q '# 2ndOpinionMD env loader' "$$ZRC" 2>/dev/null; then \
	  { \
	    echo '# 2ndOpinionMD env loader'; \
	    echo '2omd_env(){ if [ -f "server/.env" ]; then set -a; . server/.env; set +a; echo "[2OMD] Loaded server/.env"; else echo "[2OMD] server/.env not found"; fi }'; \
	    echo "alias 2omd='cd $(PWD)'"; \
	  } >> "$$ZRC"; \
	fi
	@echo ">>> dev-setup done. Run: source $$HOME/.zshrc && 2omd_env"

env-doctor:
	@echo "=== ENV DOCTOR ==="
	@echo "psql: $$(command -v psql || echo '(not found)')"
	@echo "python: $$(command -v $(PY) || echo '(not found)')"
	@echo "SYNC_DATABASE_URL: $${SYNC_DATABASE_URL:+***$${SYNC_DATABASE_URL: -12}}"

py-venv:
	@[ -x server/venv312/bin/python ] || { echo ">>> creating venv"; python3 -m venv server/venv312; }

deps-install: py-venv
	@$(PY) -m pip install --upgrade pip setuptools wheel
	@$(PY) -m pip install -r server/requirements.txt

deps-upgrade:
	@$(PY) -m pip install --upgrade -r server/requirements.txt

pip-check:
	@$(PY) - <<'PY'
		import importlib,sys
		mods="psycopg2 asyncpg sqlalchemy fastapi httpx requests".split()
		missing=[m for m in mods if importlib.util.find_spec(m) is None]
		print("OK" if not missing else "Missing: "+", ".join(missing))
		PY

# =========================
# Frontend deploy helpers
# =========================
ship: fe-build deploy-fe nginx-reload

fe-build:
	cd $(FRONTEND_DIR) && yarn install && CI= yarn build

deploy-fe:
	TS=$$(date +%F-%H%M)
	sudo mkdir -p $(RELEASES_DIR)/$$TS
	sudo rsync -a --delete $(FRONTEND_DIR)/build/ $(RELEASES_DIR)/$$TS/
	sudo rsync -a --delete $(FRONTEND_DIR)/build/ $(FRONTEND_DEPLOY_PATH)/

nginx-reload:
	sudo nginx -t && sudo nginx -s reload

smoke:
	@curl -sf https://$(HOST)/api/health | jq . || true

verify-live:
	@JS=$$(curl -s https://$(HOST)/asset-manifest.json | jq -r '.files["main.js"]'); \
	curl -s "https://$(HOST)$$JS" | strings | egrep -o "AI Analysis|Diagnoses|Environmental Factors|Life Stressors|Pattern Observations|Journaling Recommendation" | sort -u || true

rollback: ## REL=YYYY-MM-DD-HHMM
	@test -n "$(REL)" || (echo "Usage: make rollback REL=YYYY-MM-DD-HHMM"; exit 1)
	sudo rsync -a --delete $(RELEASES_DIR)/$(REL)/ $(FRONTEND_DEPLOY_PATH)/
	sudo nginx -s reload

clean: fe-clean
fe-clean:
	rm -rf $(FRONTEND_DIR)/build

# =========================
# Database helpers
# =========================
db-audit:
	@echo "-- RAG by source"
	@$(PSQL) -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_emb FROM public.rag_corpus GROUP BY 1 ORDER BY n DESC;"
	@echo "-- ANN indexes"
	@$(PSQL) -c "SELECT indexname FROM pg_indexes WHERE tablename='rag_corpus' AND indexname LIKE 'rag_corpus_embedding_ann_%';"

api-openapi:
	@{ curl -sf http://localhost:8000/api/openapi.json || curl -sf http://localhost:8000/openapi.json; } \
	| jq -r '.paths | keys[]' | sed 's/^/  /'

rag-search:
	@curl -s "$(API_BASE)/api/rag/search?q=$(Q)&limit=$(LIMIT)&source=$(SOURCE)&probes=$(PROBES)" | jq .

rag-neighbors:
	@curl -s "$(API_BASE)/api/rag/neighbors/$(ID)?limit=$(LIMIT)&source=$(SOURCE)&probes=$(PROBES)" | jq .

# RAG backfill meta
rag-backfill-meta:
	@$(PY) server/scripts/rag_backfill_meta.py

rag-backfill-meta-dry:
	@$(PY) server/scripts/rag_backfill_meta.py --dry-run

# =========================
# Include per-domain targets (single fan-out point)
# =========================
-include mk/01_snomed.mk
-include mk/02_icd.mk
-include mk/03_hpo.mk
-include mk/04_loinc_rxnorm.mk
-include mk/05_orphanet.mk
-include mk/06_chv.mk
-include mk/07_mimic_structured.mk
-include mk/08_notes.mk
-include mk/09_n2c2.mk
-include mk/10_clinvar.mk
-include mk/11_clingen.mk
-include mk/12_panelapp.mk
-include mk/13_guidelines.mk
-include mk/14_diagrules.mk
-include mk/15_disgenet.mk
-include mk/16_gwas.mk
-include mk/17_neurolex.mk
-include mk/18_nice.mk
-include mk/19_who.mk
-include mk/20_cdc_opioid.mk
-include mk/21_va.mk
-include mk/22_integrity.mk
-include mk/90_reports.mk
-include mk/98_backups.mk
-include mk/99_backend.mk
