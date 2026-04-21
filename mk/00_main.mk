# ===============================
# 2ndOpinionMD — 00_main.mk
# ===============================
# MakefileBook: imperative execution layer (data ingestion, integrity, reports, backend).
# SpellBook: 2opmd_spellbook.json — declarative build/UX spec. Cross-ref: SpellBook → MakefileBook (mk/); MakefileBook → SpellBook.

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
        db-audit api-openapi openapi-export rag-search rag-neighbors rag-backfill-meta

# ======================================
# Dev env helpers (brew, venv, deps)
# ======================================
help:
	@grep -E '^[a-zA-Z0-9_\-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-30s\033[0m %s\n", $$1, $$2}'

dev-setup:
	@set -euo pipefail; \
	ZRC="$$HOME/.zshrc"; \
	touch "$$ZRC"; \
	BREW=$$(command -v brew || true); \
	if [ -z "$$BREW" ]; then \
	  # fall back to the standard Apple Silicon path
	  if [ -x /opt/homebrew/bin/brew ]; then BREW=/opt/homebrew/bin/brew; else echo "❌ Homebrew not found. Install from https://brew.sh"; exit 1; fi; \
	fi; \
	BP=$$("$$BREW" --prefix 2>/dev/null || echo /opt/homebrew); \
	add_line() { grep -Fqx "$$1" "$$ZRC" || printf '%s\n' "$$1" >> "$$ZRC"; }; \
	add_line 'export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$$PATH"'; \
	add_line 'export PATH="$$PATH:/opt/homebrew/opt/libpq/bin"'; \
	add_line 'export LDFLAGS="-L/opt/homebrew/opt/libpq/lib"'; \
	add_line 'export CPPFLAGS="-I/opt/homebrew/opt/libpq/include"'; \
	add_line 'export PKG_CONFIG_PATH="/opt/homebrew/opt/libpq/lib/pkgconfig"'; \
	echo "✅ Updated $$ZRC. Run:  source $$ZRC"; \
	echo -n "psql -> "; /usr/bin/env PATH="/opt/homebrew/bin:/opt/homebrew/sbin:$$PATH" command -v psql || echo "missing"


env-doctor:
	@echo "=== ENV DOCTOR ==="; \
	echo -n "psql:      "; command -v psql || echo "missing"; \
	echo -n "pg_config: "; command -v pg_config || echo "missing"; \
	echo -n "python:    "; command -v server/venv312/bin/python || echo "missing"; \
	echo -n "SYNC_DATABASE_URL: "; \
	printf '%s\n' "$${SYNC_DATABASE_URL:-<unset>}" | sed 's,//[^:@]*:[^@]*@,//***:***@,'


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

openapi-export: ## Write docs/openapi.json via $(PY) (no running server)
	@cd "$(CURDIR)" && $(PY) -m server.scripts.export_openapi -o docs/openapi.json
	@echo "Wrote docs/openapi.json — commit or diff as needed."

rag-search:
	@curl -s "$(API_BASE)/api/rag/search?q=$(Q)&limit=$(LIMIT)&source=$(SOURCE)&probes=$(PROBES)" | jq .

rag-neighbors:
	@curl -s "$(API_BASE)/api/rag/neighbors/$(ID)?limit=$(LIMIT)&source=$(SOURCE)&probes=$(PROBES)" | jq .

# RAG backfill meta
rag-backfill-meta:
	@$(PY) server/scripts/rag_backfill_meta.py

rag-backfill-meta-dry:
	@$(PY) server/scripts/rag_backfill_meta.py --dry-run

DB ?= 2ndopinionmd

.PHONY: check-rag-sources
check-rag-sources:
	psql -d $(DB) -v ON_ERROR_STOP=1 -c "\
	  SELECT source, \
	         COUNT(*) AS n_rows, \
	         COUNT(*) FILTER (WHERE embedding IS NULL) AS no_embedding \
	  FROM rag_corpus \
	  GROUP BY source \
	  ORDER BY source;"

.PHONY: check-rag-guideline-sources
check-rag-guideline-sources:
	psql -d $(DB) -v ON_ERROR_STOP=1 -c "\
	  SELECT g.guideline_source AS source, \
	         COUNT(c.*) AS n_rows, \
	         COUNT(c.*) FILTER (WHERE c.embedding IS NULL) AS no_embedding \
	  FROM guideline_registry g \
	  LEFT JOIN rag_corpus c \
	    ON c.source = g.guideline_source \
	  GROUP BY g.guideline_source \
	  ORDER BY g.guideline_source;"

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
-include mk/20_cdc.mk
-include mk/21_va.mk
-include mk/22_integrity.mk
-include mk/23_pubmed.mk
-include mk/31_ethos_of_health.mk
-include mk/51_pubmd.mk
-include mk/90_reports.mk
-include mk/91_coding.mk
-include mk/95_b2b.mk
-include mk/98_backups.mk
-include mk/99_backend.mk
