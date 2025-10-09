# =========================
# 15) DisGeNET (academic subset)
# =========================
disgenet-schema:
	@$(PSQL) -f database/schemas/setup_disgenet_schema.sql

disgenet-download-genes:
	@$(PY) server/scripts/download_disgenet_by_genes.py $(if $(GENES),GENES='$(GENES)',) $(if $(GENES_FILE),GENES_FILE='$(GENES_FILE)',)

disgenet-import:
	@DSN="$${SYNC_DATABASE_URL}"; \
	SYNC_DATABASE_URL="$$DSN" DISGENET_TSV="$${TSV:-data/disgenet_curated.tsv}" $(PY) server/scripts/ingest_disgenet.py

disgenet-smoke:
	@$(PSQL) -c "SELECT COUNT(*) AS n FROM molecular.disgenet_associations;"
	@$(PSQL) -c "SELECT gene_symbol, disease_name, score FROM molecular.disgenet_associations ORDER BY score DESC NULLS LAST LIMIT 10;"

disgenet-auth-test:
	@echo ">> optional: call API endpoints for token check"

disgenet-ai-rank:
	@mkdir -p data
	@$(PSQL) -At    -f sql/autoimmune_symbols.sql    > data/autoimmune_gene_symbols.txt
	@$(PSQL) -F $$'\t' -At -f sql/autoimmune_ranked.sql > data/autoimmune_genes_ranked.tsv

disgenet-ai-map:
	@$(PY) server/scripts/symbols_to_entrez.py data/autoimmune_genes_ranked.tsv data/autoimmune_gene_ids.tsv

disgenet-ai-pull:
	@$(PY) server/scripts/disgenet_pull_batches.py --ids-file data/autoimmune_gene_ids.txt --out-tsv data/disgenet_curated.tsv --batch-size $${BATCH_SIZE:-10}

disgenet-finish:
	@server/scripts/disgenet_finish.sh data/autoimmune_gene_ids.clean

DISGENET_TSV ?= data/disgenet_curated.tsv

disgenet-audit-tsv:
	@awk -F'\t' 'NR>1&&$$3!=""{print $$3}' $(DISGENET_TSV) | sort -u | wc -l

disgenet-audit-db:
	@psql -d 2ndopinionmd -Atc "SELECT COUNT(DISTINCT assoc_id) FROM molecular.disgenet_associations WHERE assoc_id IS NOT NULL"

disgenet-diff:
	@awk -F'\t' 'NR>1&&$$3!=""{print $$3}' $(DISGENET_TSV) | sort -u > /tmp/tsv_assoc_ids.txt
	@psql -d 2ndopinionmd -Atc "SELECT assoc_id FROM molecular.disgenet_associations WHERE assoc_id IS NOT NULL ORDER BY 1" > /tmp/db_assoc_ids.txt
	@echo "TSV→DB (need import):"; comm -23 /tmp/tsv_assoc_ids.txt /tmp/db_assoc_ids.txt | head -50 || true
	@echo "DB→TSV (direct ingests):"; comm -13 /tmp/tsv_assoc_ids.txt /tmp/db_assoc_ids.txt | head -50 || true

disgenet-import-tsv:
	@cp -v $(DISGENET_TSV){,.bak.$(shell date +%F-%H%M)}
	@awk -F'\t' 'NR==1{print;next}!seen[$$3]++' $(DISGENET_TSV) > $(DISGENET_TSV).tmp && mv $(DISGENET_TSV).tmp $(DISGENET_TSV)
	@$(MAKE) disgenet-import TSV=$(DISGENET_TSV)

disgenet-export-db-to-tsv:
	@psql -d 2ndopinionmd -A -F $$'\t' -c "COPY (SELECT * FROM molecular.disgenet_associations) TO STDOUT" > /tmp/disgenet_from_db.tsv

SHELL := /bin/bash
.SHELLFLAGS := -eo pipefail -c

DISGENET_DIR    ?= data/disgenet_batches
UNIVERSE        ?= data/autoimmune_gene_ids.clean
ALL_IDS         ?= data/all_ids.sorted
DONE_IDS        ?= data/disgenet_done.ids
TODAY_IDS       ?= $(DISGENET_DIR)/today_100.ids

disgenet-expand-universe:
	@server/venv312/bin/python server/scripts/symbols_to_entrez.py data/seed_additions_symbols.txt > /tmp/seed_ids.txt
	@LC_ALL=C awk 'NF && $$0~/^[0-9]+$$/' /tmp/seed_ids.txt >> $(UNIVERSE)
	@LC_ALL=C tr -d '\r' < $(UNIVERSE) | awk 'NF&&$$0~/^[0-9]+$$/' | sort -u > $(ALL_IDS)
	@echo "Universe now:" && wc -l $(ALL_IDS)

disgenet-build-todo:
	@mkdir -p $(DISGENET_DIR)
	@psql -d 2ndopinionmd -Atc "SELECT gene_ncbi_id::text FROM molecular.disgenet_associations WHERE gene_ncbi_id IS NOT NULL GROUP BY 1 ORDER BY 1" > $(DONE_IDS)
	@comm -23 $(ALL_IDS) $(DONE_IDS) > $(DISGENET_DIR)/todo.ids
	@echo "Missing:" && wc -l $(DISGENET_DIR)/todo.ids

disgenet-plan-100: disgenet-build-todo
	@head -100 $(DISGENET_DIR)/todo.ids > $(TODAY_IDS)
	@split -a 3 -d -l 10 $(TODAY_IDS) $(DISGENET_DIR)/.tmp_ids_
	@for f in $(DISGENET_DIR)/.tmp_ids_*; do n=$$(basename $$f | sed 's/.tmp_ids_//'); paste -sd, $$f > "$(DISGENET_DIR)/genes_$${n}"; rm -f $$f; done
	@ls -1 $(DISGENET_DIR)/genes_*

# 9 calls × 10 ids = 90 genes today
disgenet-fetch-direct-today:
	@MAX_CALLS=9 bash server/scripts/disgenet_fetch_today.sh $(DISGENET_DIR)

DISGENET_SOURCES ?= CURATED,CLINVAR,LITERATURE
DISGENET_MAX_CALLS ?= 9

disgenet-rebuild-todo-safe:
	@psql -d 2ndopinionmd -Atc "SELECT gene_ncbi_id::text FROM molecular.disgenet_associations WHERE gene_ncbi_id IS NOT NULL GROUP BY 1 ORDER BY 1" > data/disgenet_done.ids
	@mkdir -p data/disgenet_batches && : > data/disgenet_batches/no_curated.ids || true
	@comm -23 data/all_ids.sorted data/disgenet_done.ids > data/disgenet_batches/todo.ids

# split safe TODO into 10-ID batches
disgenet-plan-safe:
	@mkdir -p data/disgenet_batches
	@awk 'NF' data/disgenet_batches/todo.ids | head -100 > data/disgenet_batches/today_100.ids
	@split -a 3 -d -l 10 data/disgenet_batches/today_100.ids data/disgenet_batches/.ids_
	@for f in data/disgenet_batches/.ids_*; do n=$$(basename $$f | sed 's/.ids_//'); paste -sd, $$f > data/disgenet_batches/genes_$$n; rm -f $$f; done
	@ls -1 data/disgenet_batches/genes_* 2>/dev/null || true

disgenet-fetch-direct-fast:
	@SOURCES="$(DISGENET_SOURCES)" MAX_CALLS="$(DISGENET_MAX_CALLS)" bash server/scripts/disgenet_fetch_direct_fast.sh

disgenet-audit:
	@echo 'DB assoc rows:' && psql -d 2ndopinionmd -Atc "SELECT COUNT(*) FROM molecular.disgenet_associations"
	@echo 'DB distinct genes:' && psql -d 2ndopinionmd -Atc "SELECT COUNT(DISTINCT gene_ncbi_id) FROM molecular.disgenet_associations"

