# =========================
# 31) Ethos of Health model
# =========================

# Fallbacks – these are usually defined in the root Makefile, but we
# keep sane defaults here so this file works standalone too.
PY   ?= server/venv312/bin/python
PSQL ?= psql "$${SYNC_DATABASE_URL:-postgresql://2ndopinionmd@localhost:5432/2ndopinionmd}"

# -------------------------
# RAG ingestion
# -------------------------

ethos-rag-preview:
	@$(PY) server/scripts/ingest_ethos_of_health.py --dry-run

ethos-rag-upsert:
	@$(PY) server/scripts/ingest_ethos_of_health.py

ethos-rag-stats:
	@$(PSQL) -c "SELECT source, COUNT(*) AS n, COUNT(*) FILTER (WHERE embedding IS NOT NULL) AS n_emb FROM public.rag_corpus WHERE source='ethos_model' GROUP BY source;"

# -------------------------
# Embeddings for Ethos docs
# -------------------------

ethos-rag-embed-preview:
	@echo ">>> DRY RUN: Ethos of Health embedding"
	@$(PY) server/scripts/ethos_rag_embed.py --dry-run

ethos-rag-embed:
	@echo ">>> Embedding Ethos of Health docs into rag_corpus.embedding"
	@$(PY) server/scripts/ethos_rag_embed.py
	@$(MAKE) ethos-rag-stats

# Convenience aggregate
ethos-rag-all: ethos-rag-upsert ethos-rag-embed
	@echo "Ethos of Health RAG ingestion + embedding completed."
