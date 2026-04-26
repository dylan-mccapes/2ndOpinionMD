# HANDOFF: How to Ingest New Data Sources into the Medical Knowledge Graph (MKG)

**For:** Andras Hangyal (with Devin and/or Claude as agent assistants)  
**From:** Dylan McCapes  
**Date:** 2026-02-25  
**Purpose:** Step-by-step guide to adding new MakefileBook entries and ingesting new data sources into MKG  
**Prerequisites:** SSH access to `.BeatingHeart`, basic Terminal comfort, patience

---

## 0. What You're Working With

### The MakefileBook

The MakefileBook is the SpellBook applied to data ingestion. It lives at `2ndOpinionMD-MVP/mk/` — a collection of numbered `.mk` files, each responsible for one data source. They are included by the root `Makefile`:

```
2ndOpinionMD-MVP/
├── Makefile              ← Root. Includes mk/00_main.mk
└── mk/
    ├── 00_main.mk        ← Config: paths, DB URL, venv, frontend deploy, DB helpers
    ├── 01_snomed.mk      ← SNOMED-CT (ontology backbone)
    ├── 02_icd.mk         ← ICD-10-CM and ICD-11
    ├── 03_hpo.mk         ← Human Phenotype Ontology
    ├── 04_loinc_rxnorm.mk ← Lab codes + drug terminology
    ├── 05_orphanet.mk    ← Rare diseases
    ├── 06_chv.mk         ← Consumer Health Vocabulary
    ├── 07_mimic_structured.mk ← MIMIC clinical data
    ├── 08_notes.mk       ← MIMIC-IV clinical notes
    ├── 09_n2c2.mk        ← NLP challenge data
    ├── 10_clinvar.mk     ← Genetic variant classifications
    ├── 11_clingen.mk     ← Gene-disease associations
    ├── 12_panelapp.mk    ← Genomic panels
    ├── 13_guidelines.mk  ← Clinical guidelines (NICE, GOLD, SSC, AHA, KDIGO, etc.)
    ├── 14_diagrules.mk   ← Diagnostic classification rules (ACR/EULAR)
    ├── 15_disgenet.mk    ← Disease-gene associations
    ├── 16_gwas.mk        ← Genome-wide association studies
    ├── 17_neurolex.mk    ← Neuroscience lexicon
    ├── 18_nice.mk        ← NICE-specific guideline handling
    ├── 19_who.mk         ← WHO Essential Medicines List
    ├── 20_cdc.mk         ← CDC guidelines
    ├── 21_va.mk          ← VA clinical practice guidelines
    ├── 22_integrity.mk   ← Cross-source integrity checks
    ├── 23_pubmed.mk      ← PubMed baseline download
    ├── 31_ethos_of_health.mk ← 2OPMD's clinical reasoning model (EoH)
    ├── 51_pubmd.mk       ← PubMed enhanced targets
    ├── 90_reports.mk     ← PDF integrity reports for every source
    ├── 91_coding.mk      ← Coding-related targets
    ├── 98_backups.mk     ← Database backup targets
    └── 99_backend.mk     ← Server start/stop/restart, API health
```

### The Medical Knowledge Graph (MKG)

MKG is a PostgreSQL database (`2ndopinionmd`) with two main storage layers:

1. **Ontology tables** (`ontology.*`) — structured medical data (SNOMED concepts, ICD codes, HPO terms, gene-disease associations, etc.)
2. **RAG corpus** (`public.rag_corpus`) — text chunks with vector embeddings for retrieval-augmented generation

The RAG corpus is where most new data ultimately lands. It has this shape:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | serial | Primary key |
| `source` | text | Data source identifier (e.g., `'nice'`, `'icd10cm'`, `'ethos_model'`) |
| `title` | text | Human-readable title |
| `text` | text | The actual content (chunk of text) |
| `embedding` | vector(1536) | OpenAI `text-embedding-3-small` vector |
| `meta` | jsonb | Arbitrary metadata (doc_key, section_id, URLs, etc.) |
| `ts` | tsvector | Full-text search index |

---

## 1. The Universal Ingestion Pattern

Every data source follows the same 4-step pattern. This is the MakefileBook's core rhythm:

### Step 1: Download / Acquire Data

Get the raw data onto the machine. Could be:
- `wget` a PDF from a guideline publisher
- Download a ZIP from an FTP server (PubMed, SNOMED)
- Place a file manually that requires registration (ICD, MIMIC)
- Pull from an API (WHO ICD-11)

Data lands in `data/` subdirectories:
```
data/
├── nice/              ← NICE guideline PDFs
├── guidelines/        ← Other guideline PDFs (GOLD, SSC, AHA, KDIGO)
├── icd10/             ← ICD-10-CM order file
├── SnomedCT_*/        ← SNOMED release
├── pubmd/baseline/    ← PubMed XML files
└── ra_guidelines/     ← Rheumatology guideline PDFs
```

### Step 2: Parse + Insert (Ingest)

A Python script in `server/scripts/` reads the raw data and inserts rows into the database. The script:
- Reads the file (PDF → PyMuPDF/pdfminer, XML → ElementTree, TSV → csv reader)
- Extracts meaningful chunks (sections, paragraphs, concepts)
- Writes rows to `public.rag_corpus` (or `ontology.*` tables for structured data)
- Sets `source` to the canonical source key (e.g., `'gold_copd_2024'`)

Common naming: `server/scripts/ingest_<source>.py`

### Step 3: Embed

A shared embedding script fills in the `embedding` column for rows that don't have one yet:

```bash
python server/scripts/embed_rag_source_async.py --source <source_key>
```

This calls OpenAI's `text-embedding-3-small` model in batches. It's idempotent — only embeds rows where `embedding IS NULL`.

**Environment needed:** `OPENAI_API_KEY` must be set (in `.env` or exported).

### Step 4: Verify

Check that rows landed and embeddings are complete:

```bash
psql -d 2ndopinionmd -c "
  SELECT source, COUNT(*) AS n,
         COUNT(*) FILTER (WHERE embedding IS NULL) AS no_emb
  FROM rag_corpus
  WHERE source = '<source_key>'
  GROUP BY source;"
```

---

## 2. How to Add a New Guideline (Most Common Task)

This is the most likely thing Andras will do. Here's the concrete workflow for adding a new clinical guideline PDF.

### 2.1 Choose a Source Key

Pick a short, lowercase, underscored identifier. Convention: `<society>_<topic>_<year>`.

Examples from existing sources:
- `gold_copd_2024` (GOLD 2024 COPD guideline)
- `ssc_sepsis_2021` (Surviving Sepsis Campaign 2021)
- `aha_asa_stroke_2023` (AHA/ASA Stroke 2023)
- `eular_sle_nephritis_2025` (EULAR SLE Nephritis 2025)
- `esmo_mzl_2020` (ESMO Marginal Zone Lymphoma 2020)

### 2.2 Get the PDF

Download or manually save the guideline PDF into `data/guidelines/`:

```bash
mkdir -p data/guidelines
wget -O data/guidelines/<your-guideline>.pdf "<URL>"
```

Some publishers block wget. If so, download via browser and `scp` to the server:
```bash
scp ~/Downloads/guideline.pdf 2ndopinionmd@<server>:~/2ndOpinionMD-MVP/data/guidelines/
```

### 2.3 Write the Ingest Script

Create `server/scripts/ingest_guidelines_<your_source>.py`. The simplest version uses the generic PDF ingester that already exists:

```bash
# If a generic PDF ingester exists, you can use it directly:
python server/scripts/ingest_guideline_pdf.py \
  --pdf-path data/guidelines/<your-guideline>.pdf \
  --source <your_source_key> \
  --guideline-title "Full Title of the Guideline" \
  --base-url "https://publisher.org/guideline-url" \
  --year 2024 \
  --topic <disease_topic> \
  --disease <disease_code> \
  --society <society_code>
```

Or write a dedicated script. **This is where Devin/Claude helps.** Tell the agent:
1. "Write a Python script that reads `data/guidelines/<file>.pdf`"
2. "Extract text by page or section"
3. "Insert each chunk into `public.rag_corpus` with `source='<key>'`"
4. "Use the same DB connection pattern as `ingest_guidelines_gold_copd_2024.py`"

The agent should be able to produce a working script by copying the pattern from an existing one.

### 2.4 Write the MakefileBook Entry

Add targets to `mk/13_guidelines.mk` (or create a new mk file if it's a different source category):

```makefile
# =========================================================
# <SOCIETY> <YEAR> — <Guideline Name>
# =========================================================

<SOURCE>_PDF  := data/guidelines/<your-guideline>.pdf
<SOURCE>_URL  := https://publisher.org/guideline.pdf
<SOURCE>_SRC  := <your_source_key>

.PHONY: guidelines-<short>-download
guidelines-<short>-download:
	@mkdir -p data/guidelines
	@if [ ! -f "$(<SOURCE>_PDF)" ]; then \
	  echo "Downloading <Guideline Name>..."; \
	  wget -O "$(<SOURCE>_PDF)" "$(<SOURCE>_URL)"; \
	else \
	  echo "<Guideline> PDF already present at $(<SOURCE>_PDF)"; \
	fi

.PHONY: guidelines-<short>-ingest
guidelines-<short>-ingest:
	@test -f "$(<SOURCE>_PDF)" || (echo "Missing $(<SOURCE>_PDF)"; exit 1)
	@$(PYTHON) server/scripts/ingest_guidelines_<your_source>.py

.PHONY: guidelines-<short>-embed
guidelines-<short>-embed:
	@$(PYTHON) server/scripts/embed_rag_source_async.py --source $(<SOURCE>_SRC)

.PHONY: guidelines-<short>-stats
guidelines-<short>-stats:
	@$(PSQL) -c "SELECT source, COUNT(*) n, COUNT(*) FILTER (WHERE embedding IS NULL) no_emb \
	             FROM rag_corpus WHERE source = '$(<SOURCE>_SRC)' GROUP BY 1;"

.PHONY: guidelines-<short>-all
guidelines-<short>-all: guidelines-<short>-ingest guidelines-<short>-embed guidelines-<short>-stats
	@echo "✓ <Guideline Name> ingestion + embeddings complete"
```

### 2.5 Run It

```bash
cd 2ndOpinionMD-MVP

# Download (if wget works for this publisher)
make guidelines-<short>-download

# Ingest (parse PDF → insert into rag_corpus)
make guidelines-<short>-ingest

# Embed (fill embedding column via OpenAI)
make guidelines-<short>-embed

# Verify
make guidelines-<short>-stats
```

### 2.6 Verify via API

```bash
# Check it's searchable
curl -s "http://localhost:8000/api/rag/search?q=<relevant query>&source=<source_key>&limit=3" | jq .
```

---

## 3. Tooling Split: Devin vs Claude

| Task | Who | Why |
|------|-----|-----|
| Write ingest script from existing pattern | **Devin** | Pattern copying, code generation. Devin is good at this. Cheaper. |
| Debug a script that fails on execution | **Andras + Terminal** | You need to see the error, read the traceback, understand what happened. This is practice. |
| Write the `.mk` entry | **Devin** or **copy-paste from above** | Boilerplate. Follow the template. |
| Run `make` targets | **Andras (Terminal)** | Terminal practice. You type `make guidelines-<short>-ingest` and watch the output. |
| Fix credential / env issues | **Andras + Dylan (call)** | `.env` files, API keys, database URLs. Sometimes you need to `export OPENAI_API_KEY=...` or edit a `.env`. |
| Write a new source category (not a guideline) | **Claude (local, Cursor)** | More expensive but Claude can read the codebase, run commands, and iterate. For complex new sources (new schema, new parser). |
| Verify integrity | **Andras (Terminal)** | Run `make integrity-all` or source-specific stats. Read the output. |
| Generate PDF integrity report | **Andras (Terminal)** | `make <source>-report-pdf`. The reports auto-generate. |

---

## 4. Environment Setup (One-Time)

### 4.1 SSH Access

```bash
ssh 2ndopinionmd@<server-ip>
cd 2ndOpinionMD-MVP
```

### 4.2 Activate the Python Environment

```bash
source server/venv312/bin/activate
```

### 4.3 Check Environment Health

```bash
make env-doctor
```

Should show: `psql`, `pg_config`, `python` all found, `SYNC_DATABASE_URL` set.

### 4.4 Required Environment Variables

| Variable | Where | Purpose |
|----------|-------|---------|
| `SYNC_DATABASE_URL` | `.env` or shell | PostgreSQL connection string |
| `OPENAI_API_KEY` | `.env` or shell | For embedding generation |
| `WHO_CLIENT_ID` / `WHO_CLIENT_SECRET` | `.env` or shell | Only for ICD-11 WHO API |

If variables aren't set, check `.env` in the project root or export them:
```bash
export OPENAI_API_KEY="sk-..."
```

### 4.5 Check What's Already in MKG

```bash
make check-rag-sources
```

This shows every source in `rag_corpus` with row counts and embedding status.

---

## 5. Existing Sources and Their Numbers (MakefileBook Index)

| # | Source | mk file | Key targets |
|---|--------|---------|-------------|
| 01 | SNOMED-CT | `01_snomed.mk` | `snomed-import`, `snomed-all` |
| 02 | ICD-10-CM/ICD-11 | `02_icd.mk` | `icd10-load`, `icd-rag-upsert`, `icd-embed` |
| 03 | HPO | `03_hpo.mk` | `hpo-load`, `hpo-embed` |
| 04 | LOINC/RxNorm | `04_loinc_rxnorm.mk` | `loinc-load`, `rxnorm-load` |
| 05 | Orphanet | `05_orphanet.mk` | `orphanet-load` |
| 06 | CHV | `06_chv.mk` | `chv-load` |
| 07 | MIMIC | `07_mimic_structured.mk` | `mimic-load` |
| 08 | MIMIC-IV Notes | `08_notes.mk` | `notes-load` |
| 09 | n2c2/i2b2 | `09_n2c2.mk` | `n2c2-load` |
| 10 | ClinVar | `10_clinvar.mk` | `clinvar-load` |
| 11 | ClinGen | `11_clingen.mk` | `clingen-load` |
| 12 | PanelApp | `12_panelapp.mk` | `panelapp-load` |
| 13 | Guidelines (many) | `13_guidelines.mk` | `guidelines-load`, `guidelines-*-all` |
| 14 | Diagnostic Rules | `14_diagrules.mk` | `diagrules-load` |
| 15 | DisGeNET | `15_disgenet.mk` | `disgenet-load` |
| 16 | GWAS | `16_gwas.mk` | `gwas-load` |
| 17 | NeuroLex | `17_neurolex.mk` | `neurolex-load` |
| 18 | NICE | `18_nice.mk` | `nice-load` |
| 19 | WHO EML | `19_who.mk` | `who-load` |
| 20 | CDC | `20_cdc.mk` | `cdc-load` |
| 21 | VA | `21_va.mk` | `va-load` |
| 23 | PubMed Baseline | `23_pubmed.mk` | `pubmed-baseline-sync` |
| 31 | Ethos of Health | `31_ethos_of_health.mk` | `ethos-rag-all` |
| 90 | Reports | `90_reports.mk` | `reports-all` |
| 98 | Backups | `98_backups.mk` | backup targets |
| 99 | Backend | `99_backend.mk` | `be-start`, `be-restart`, `api-health` |

---

## 6. First Session Plan (For the Call)

### Goal: Ingest one new guideline together

1. **Pick a guideline** — Andras picks a guideline PDF relevant to autoimmune/metabolic work
2. **Choose source key** — Follow the naming convention together
3. **Download the PDF** — `wget` or browser download + `scp`
4. **Copy an existing ingest script** — Devin copies pattern from `ingest_guidelines_gold_copd_2024.py`
5. **Run it** — Andras types `python server/scripts/ingest_guidelines_<new>.py` in Terminal
6. **Fix any errors** — Read tracebacks, adjust, re-run (this is the learning)
7. **Embed** — `make guidelines-<short>-embed`
8. **Verify** — `make guidelines-<short>-stats` and `make check-rag-sources`
9. **Add the `.mk` entry** — Copy the template, fill in the blanks
10. **Test the full loop** — `make guidelines-<short>-all` from scratch

### Time estimate: 60-90 minutes for the first one. 15 minutes for each subsequent one.

---

## 7. What Andras Gets Out of This

| Outcome | Type |
|---------|------|
| Terminal proficiency with Make, psql, Python, SSH | **Education** |
| Understanding of MKG architecture (ontology + RAG) | **Domain knowledge** |
| His guideline additions permanently locked into MKG | **Production contribution** |
| Content expertise for Substack/X posts (he read the guidelines to ingest them) | **Content pipeline fuel** |
| Demonstrable technical work for founders' equity narrative | **Business value** |

The education IS the production work. There is no separate "training" phase. Andras learns by adding real data to the real system, and his additions become permanent parts of the Medical Knowledge Graph that 2ndOpinionMD serves to users.

---

**Filed:** 2026-02-25  
**Location:** `2ndOpinionMD-MVP/HANDOFF_MKG_INGESTION_ANDRAS.md`  
**To be reviewed on call:** Dylan + Andras  
**Agent support:** Devin (code generation, pattern copying) + Claude/Cursor (complex debugging, new schema work)
