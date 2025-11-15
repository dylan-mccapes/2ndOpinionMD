# PubMed Baseline (aria2c-based) ----------------------------------------------

ROOT ?= $(shell git rev-parse --show-toplevel 2>/dev/null || pwd)
PUBMED_SCRIPT := server/scripts/pubmed_baseline_sync.sh
PUBMED_DIR    ?= data/pubmd/baseline
PUBMED_JOBS   ?= 8
PUBMED_PREFIX ?= pubmed25n
PUBMED_REMOTE ?= https://ftp.ncbi.nlm.nih.gov/pubmed/baseline

.PHONY: pubmed-baseline-sync pubmed-baseline-verify pubmed-baseline-list pubmed-baseline-refresh

pubmed-baseline-sync:
	@PUBMED_BASELINE_DIR="$(PUBMED_DIR)" \
	 PUBMED_JOBS="$(PUBMED_JOBS)" \
	 PUBMED_BASELINE_PREFIX="$(PUBMED_PREFIX)" \
	 PUBMED_BASELINE_REMOTE="$(PUBMED_REMOTE)" \
	 bash "$(PUBMED_SCRIPT)" sync

pubmed-baseline-list:
	@echo "(pwd: $(abspath $(BASELINE_DIR)))"
	@echo -n "Local .gz count matching pubmed25n*: "
	@cd $(BASELINE_DIR) && ls -1 pubmed25n*.xml.gz | wc -l
	@echo "Sample:"
	@cd $(BASELINE_DIR) && ls -1 pubmed25n*.xml.gz | head -n 10 || true

pubmed-baseline-verify:
	@cd $(BASELINE_DIR) && { \
	  curl -fsSL -o md5checksums.txt $(PUBMED_BASE)/md5checksums.txt ; \
	  awk '{print tolower($$1), $$2}' md5checksums.txt | sort > remote.md5sum ; \
	  md5 -r pubmed25n*.xml.gz | awk '{print tolower($$1), $$2}' | sort > local.md5sum ; \
	  if diff -u remote.md5sum local.md5sum ; then \
	    echo "✅ All MD5 checks matched"; \
	  else \
	    echo "❌ MD5 mismatches found"; exit 1; \
	  fi ; \
	}

# If you prefer per-file sidecars instead of md5checksums.txt:
pubmed-baseline-verify-sidecars:
	@cd $(BASELINE_DIR) && { \
	  fails=0; \
	  for f in pubmed25n*.xml.gz; do \
	    want=$$(tr -d '\r' < $$f.md5 | head -n1 | grep -Eo '[0-9A-Fa-f]{32}' | head -n1 | tr A-F a-f); \
	    got=$$(md5 -q $$f | tr A-F a-f); \
	    if [ -z "$$want" ] || [ "$$got" != "$$want" ]; then \
	      echo "FAIL $$f (got $$got want $$want)"; fails=$$((fails+1)); \
	    fi; \
	  done; \
	  [ $$fails -eq 0 ] && echo "✅ All MD5 checks passed" || (echo "❌ $$fails mismatches"; exit 1); \
	}

pubmed-baseline-refresh:
	@PUBMED_BASELINE_DIR="$(PUBMED_DIR)" \
	 PUBMED_BASELINE_PREFIX="$(PUBMED_PREFIX)" \
	 PUBMED_BASELINE_REMOTE="$(PUBMED_REMOTE)" \
	 bash "$(PUBMED_SCRIPT)" refresh
