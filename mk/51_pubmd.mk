PUBMD_BASELINE_DIR := data/pubmd/baseline
PUBMD_DERIVED_DIR  := data/derived
PUBMD_DOCS_CSVGZ   := $(PUBMD_DERIVED_DIR)/pubmd_docs.csv.gz

.PHONY: pubmd-extract pubmd-load pubmd-rag-upsert pubmd-embed pubmd-index pubmd-report-pdf pubmd-all

pubmd-extract: $(PUBMD_DOCS_CSVGZ)

$(PUBMD_DOCS_CSVGZ): server/scripts/pubmd_extract_to_csv.py $(PUBMD_BASELINE_DIR)/pubmed25n*.xml.gz
	@mkdir -p $(PUBMD_DERIVED_DIR)
	@echo "➟ Extracting PubMed → $(PUBMD_DOCS_CSVGZ)"
	@python server/scripts/pubmd_extract_to_csv.py --out $@ $(PUBMD_BASELINE_DIR)/pubmed25n*.xml.gz

pubmd-load:
	@echo "➟ Creating staging.pubmd_docs"
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -f database/sql/pubmd_staging.sql
	@echo "➟ Loading CSV"
	@zcat $(PUBMD_DOCS_CSVGZ) | psql -d 2ndopinionmd -c "\copy staging.pubmd_docs(pmid,title,abstract,year,journal,mesh,text) from STDIN csv header"
	@psql -d 2ndopinionmd -c "ANALYZE staging.pubmd_docs;"


# Default DSN if not provided by env
DSN ?= postgresql:///2ndopinionmd
PYTHON ?= server/venv312/bin/python

pubmd-bootstrap:
	@echo "➟ Bootstrap pubmd (staging + upsert)"
	psql -d 2ndopinionmd -f database/sql/staging_pubmd.sql
	psql -d 2ndopinionmd -f database/sql/pubmd_rag_upsert.sql

pubmd-rag-upsert:
	@echo "➟ Upserting into rag_corpus (source=pubmd)"
	psql -d 2ndopinionmd -f database/sql/pubmd_rag_upsert.sql

pubmd-embed:
	@echo "➟ Embedding pubmd"
	$(PYTHON) server/scripts/embed_rag_source_async.py \
		--dsn "$(DSN)" \
		--model "text-embedding-3-large" \
		--source "pubmd" \
		--batch 2000 \
		--req-batch 256 \
		--concurrency 8 \
		--max-chars 8000 \
		--log-every 100


pubmd-index:
	@echo "➟ Building ANN indexes"
	@psql -d 2ndopinionmd -v ON_ERROR_STOP=1 -f database/sql/rag_indexes.sql

# Reuse your report pipeline if it accepts SOURCE=…
pubmd-report-pdf:
	@echo "➟ Generating PubMD integrity/RAG report"
	@AI=1 SOURCE=pubmd OUTPUT=db_integrity_reports/09_pubmd.pdf make rag-report-pdf || true

pubmd-all: pubmd-extract pubmd-load pubmd-rag-upsert pubmd-embed pubmd-index pubmd-report-pdf