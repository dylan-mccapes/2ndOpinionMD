# 2ndOpinionMD — Project Understanding Report

**Date:** 2026-03-29  
**Prepared by:** Cursor Agent (for Dylan)  
**Scope:** Full project audit — architecture, data pipeline, clinical modes, infrastructure

---

## Executive Summary

**2ndOpinionMD** is a HIPAA-forward AI platform for **autoimmune disease second-opinion reports**. It combines a massive clinical knowledge base (20+ medical ontologies, terminologies, and guideline corpora ingested into PostgreSQL/pgvector) with LLM-powered reasoning across four orthogonal clinical modes. The platform is built for a specific patient archetype: complex, multi-system autoimmune cases where diagnostic mysteries, treatment divergences, and internal contradictions in the medical record need to be surfaced and reasoned about.

The system is being actively developed by **Nate** (operator, nate@2ndopinionmd.ai) and **Dylan** (builder, dylan@2ndopinionmd.ai), with prior agent contributions from **Devin** (Cognition).

---

## 1. The Four Clinical Modes

| Mode | Purpose | Endpoint | State |
|------|---------|----------|-------|
| **ASK** | Read-only clinical Q&A. Stateless. Each query independent. | `GET /api/rag/ask_stream` (SSE) | Stateless |
| **CODING** | Medical coding & classification. ICD-10-CM, ICD-11, SNOMED CT, LOINC, RxNorm codes with confidence. | `POST /api/coding` | Stateless |
| **EoH** | Single Ethos-of-Health reasoning cycle. Hypothesis set + evidence weighting + suggested next steps. | `GET /api/rag/eoh_stream` (SSE) | Stateless |
| **EoHD** | Timeline-aware EoH Detective reasoning. Temporal hypothesis evolution and inflection points. | `GET /api/rag/eoh_stream` with `use_timeline=1` | Timeline-gated |

**Hard UX invariants:** Modes do not share state, do not auto-transition, have no session persistence, no "remembering preferences," no optimistic UI, no fake progress. Failures are surfaced honestly.

---

## 2. Architecture

### Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12 / FastAPI / Uvicorn |
| **Database** | PostgreSQL + pgvector (embeddings, ANN via ivfflat) |
| **Frontend** | React 18 + TypeScript + Vite + Tailwind (clinical terminal aesthetic) |
| **Mobile** | React Native (onboarding flow) |
| **LLM** | OpenAI (GPT-4.1 / GPT-4.1-mini) + Ollama (local llama3.1) |
| **Streaming** | Server-Sent Events (SSE) for ASK, EoH, EoHD; JSON REST for CODING |
| **Deploy** | Docker Compose (API + nginx), macOS M2 Ultra server, WSL2/RTX 4090 GPU worker |
| **venv** | `.BeatingHeart` (named for what the system protects) |

### Key Entry Points

- **Backend app:** `server/api/app_postgres.py` — FastAPI lifespan with async SQLAlchemy + `PostgreSQLMedicalQueryEngine`
- **Backend runner:** `server/scripts/run_postgres_app.py`
- **Build system:** `Makefile` → `mk/00_main.mk` → 30 domain-specific `.mk` files ("MakefileBook")
- **Declarative spec:** `2opmd_spellbook.json` ("SpellBook") — cross-references MakefileBook

---

## 3. The SpellBook (`2opmd_spellbook.json`)

The SpellBook is a declarative build/UX specification that serves as the single source of truth for:

- **Project identity and philosophy:** "Clinical terminal aesthetic. UX follows system truth, not user preference. Convenience is the primary entropy vector."
- **All API endpoints** (auth, journal, session, RAG/streaming, coding, timeline, EoH, terminologies, guidelines, genomics, utility)
- **Frontend buildout spec** (pages, components, routing, component contracts)
- **Security posture** (rate limits, JWT auth, email verification, HIPAA-forward)
- **Docker/deploy configuration**
- **Environment variables** and required dependencies
- **Devin agent instructions** — priority-ordered build plan for the React frontend

The SpellBook/MakefileBook duality is central: SpellBook declares *what*; MakefileBook (mk/) executes *how*.

---

## 4. The MakefileBook — Data Ingestion Empire

The `mk/` directory contains **30 makefiles** that form the imperative execution layer for data ingestion, integrity checking, RAG embedding, and reporting. This is one of the most impressive aspects of the project — a systematic, reproducible pipeline for loading the world's major clinical knowledge bases into a unified PostgreSQL/pgvector RAG corpus.

### 4.1 Terminology & Ontology Sources

| Source | Makefile | DB Schema | RAG Source | Description |
|--------|----------|-----------|------------|-------------|
| **SNOMED CT US** | `01_snomed.mk` | `ontology.snomed_*` | — | Core clinical terminology, 350K+ concepts, ICD-10-CM crosswalk via ExtendedMap |
| **ICD-10-CM** (CMS) | `02_icd.mk` | `ontology.icd10cm_*` | `icd10cm` | Diagnosis codes |
| **ICD-11** (WHO API) | `02_icd.mk` | `ontology.icd11_*` | — | WHO classification, API-loaded |
| **HPO** | `03_hpo.mk` | `ontology.hpo_*` | — | Human Phenotype Ontology — phenotype-to-disease mapping |
| **LOINC** | `04_loinc_rxnorm.mk` | `ontology.loinc_*` | `loinc` | Lab/observation codes |
| **RxNorm** | `04_loinc_rxnorm.mk` | `ontology.rxnorm_*` | `rxnorm` | Drug terminology, NLM RRF |
| **Orphanet** | `05_orphanet.mk` | `ontology.orphanet_*` | `orphanet` | Rare diseases, gene links, phenotype links |
| **CHV** | `06_chv.mk` | `ontology.chv_*` | `chv` | Consumer Health Vocabulary — lay-language ↔ CUI mapping |
| **NeuroLex/InterLex** | `17_neurolex.mk` | `ontology.neurolex*` | `neurolex` | Neuroscience lexicon (SciCrunch API) |

### 4.2 Clinical Data / EHR

| Source | Makefile | DB Schema | RAG Sources | Description |
|--------|----------|-----------|-------------|-------------|
| **MIMIC-III** | `07_mimic_structured.mk` | `ehr_mimic3.*` | `mimic3_dx`, `mimic3_proc`, `mimic3_labitems` | De-identified critical care EHR |
| **MIMIC-IV** | `07_mimic_structured.mk` | `ehr_mimic4.*` | `mimic4_*` | Updated EHR dataset |
| **MIMIC Notes** (III + IV) | `08_notes.mk` | `text.mimiciv_notes*` | — | Free-text clinical notes |
| **n2c2/i2b2** | `09_n2c2.mk` | `n2c2.*` | — | Clinical NLP shared task corpora, silver A&P pairs from MIMIC |

### 4.3 Molecular / Genomic

| Source | Makefile | DB Schema | RAG Source | Description |
|--------|----------|-----------|------------|-------------|
| **ClinVar** | `10_clinvar.mk` | `molecular.clinvar_*` | — | NCBI variant pathogenicity |
| **ClinGen** | `11_clingen.mk` | `molecular.clingen_*` | — | Gene-disease validity, actionability, ACI, variant classifications |
| **PanelApp** | `12_panelapp.mk` | `molecular.gene_panels` | `panelapp` | Genomics England gene panels |
| **DisGeNET** | `15_disgenet.mk` | `molecular.disgenet_*` | — | Gene-disease associations (curated + ClinVar + literature) |
| **GWAS Catalog** | `16_gwas.mk` | `molecular.gwas_hits` | `gwas` | Genome-wide association study hits (autoimmune filter) |

### 4.4 Clinical Guidelines

| Source | Makefile | RAG Source(s) | Description |
|--------|----------|---------------|-------------|
| **NICE / CKS** | `13_guidelines.mk`, `18_nice.mk` | `nice`, `cks` | UK national guidelines, scraped PDFs |
| **ACR/EULAR** | `13_guidelines.mk`, `14_diagrules.mk` | `acr_eular`, `acr_ra_2021`, `eular_ra_2022`, etc. | Rheumatology diagnostic criteria & guidelines |
| **CDC Opioid** | `20_cdc.mk` | `cdc_opioid` | US opioid prescribing guideline |
| **VA/DoD** | `21_va.mk` | `va_guidelines` | Federal clinical practice guidelines |
| **WHO EML/AWaRe** | `19_who.mk` | `who_eml`, `who_committee` | Essential medicines, antibiotic stewardship |
| **GOLD COPD** | `13_guidelines.mk` | `gold_copd_2024` | COPD guidelines |
| **SSC Sepsis** | `13_guidelines.mk` | `ssc_sepsis_2021` | Surviving Sepsis Campaign |
| **AHA/ASA Stroke** | `13_guidelines.mk` | `aha_stroke_*` | Stroke management |
| **KDIGO CKD** | `13_guidelines.mk` | `kdigo_ckd_2024` | Kidney disease |
| **ACC/AHA/HFSA HF** | `13_guidelines.mk` | `hf_2022` | Heart failure |
| **ESMO** | `13_guidelines.mk` | `esmo_mzl_2020`, etc. | Oncology (marginal zone lymphoma, CLL) |

### 4.5 Literature

| Source | Makefile | RAG Source | Description |
|--------|----------|------------|-------------|
| **PubMed Baseline** | `23_pubmed.mk`, `51_pubmd.mk` | `pubmd` | Full PubMed baseline (FTP sync via aria2), XML → CSV → RAG |

### 4.6 Internal / Project

| Source | Makefile | RAG Source | Description |
|--------|----------|------------|-------------|
| **Ethos of Health** | `31_ethos_of_health.mk` | `ethos_model` | 2OPMD's internal reasoning framework |

### 4.7 Operations & Quality

| Makefile | Purpose |
|----------|---------|
| `22_integrity.mk` | Cross-source integrity, orphan detection, embedding coverage |
| `90_reports.mk` | PDF integrity reports per domain (optional AI-assisted narrative with `AI=1`) |
| `91_coding.mk` | CLI for medical coding API (`/api/rag/coding`) |
| `98_backups.mk` | pg_dump backup + verification |
| `99_backend.mk` | Uvicorn lifecycle (start/stop/restart/logs) |

---

## 5. The EoHD Timeline Pipeline (`run_eohd_timeline_pdf.py`)

This is the script that processes the **4,223-page patient timeline PDF** (Norman Eric Roberts). It represents the most compute-intensive and clinically significant workflow in the system.

### Pipeline Flow

```
PDF (4223 pages, decrypted)
    │
    ▼
[Text Extraction] ── PyPDF page-by-page
    │
    ▼
[PatientTimelineVision] ── Structured event extraction via LLM
    │                       (batch pages → extract clinical events)
    │
    ▼
[summarize_timeline_for_eoh] ── Narrative summarization
    │                            (timeline summary, meds & labs snapshot, Valyu signals)
    │
    ▼
[Graph Export] ── patient_timeline_graph_final.json
    │
    ▼
[Artifacts] ── vision snapshot, gap/synthesis sidecars, summaries JSON
```

### LLM Backend Options

| Backend | Event Extraction | Narrative Summarization | Key Required |
|---------|-----------------|------------------------|--------------|
| `openai` (default) | OpenAI (GPT-4.1) | OpenAI | OPENAI_API_KEY |
| `ollama` | Local Ollama (llama3.1:8b) | OpenAI | OPENAI_API_KEY |
| `ollama-full` | Local Ollama | Local Ollama | None |

### Extraction Modes

- **`lite`**: Head + tail + Monte Carlo sample (~800 pages, ~4-5 LLM calls)
- **`full`**: All pages (~23 calls for a 4K-page record)

### GPU Optimization

The script supports `--extraction-concurrency` for parallel PDF extraction batches. With an RTX 4090 + llama3.1:8b-instruct-q8_0 (~9GB), concurrency of 2-3 can saturate the GPU and roughly halve wall-clock time.

### Context Window Handling

- OpenAI: defaults to 1,048,576 tokens (GPT-4.1's 1M context)
- Ollama: defaults to 32,768 tokens (safe for 8B models — keeps KV cache under ~2GB)
- Override with `--ingestion-context-tokens`

---

## 6. The EoH Reasoning Engine

The `server/eoh/` directory contains the Ethos of Health reasoning system:

| Module | Role |
|--------|------|
| `router.py` | Main EoH router with timeline integration, SSE event ordering, regulatory guardrails |
| `router_llm.py` | LLM routing for EoH queries |
| `eoh_plans.py` | Disease-cluster bundles (RA, SLE, PsA, etc.) with `infer_disease_cluster()` heuristics |
| `fusion.py` | Timeline context fusion |
| `validators.py` | Safety validation |
| `graph_enrichment.py` | GPT-4.1 entity/relationship extraction into PatientTimelineVision |
| `patient_timeline_vision.py` | Core vision model for structured patient timeline |
| `timeline_summarizer.py` | PDF → structured timeline → narrative summary pipeline |
| `timeline_enrichment_*_agent.py` | Enrichment agents for gap analysis, synthesis |
| `modules/m13_flare_risk.py` | Flare risk prediction module |
| `modules/m17_diagnostic_landscape.py` | Diagnostic landscape analysis |
| `module_index.py` | Module registry |
| `features.py` | Feature computation |
| `recompute_state.py` | State recomputation |

### SSE Event Order (EoHD)

```
timeline_loaded → ... → timeline_probabilistic_differential
```

### Regulatory Guardrails

- No definitive diagnosis language
- All outputs framed as hypotheses with evidence weighting

---

## 7. Infrastructure — The Dual-Machine Setup

Based on the Cursor chat history, the current infrastructure is:

| Machine | Role | Specs | Network |
|---------|------|-------|---------|
| **M2 Ultra** (macOS) | Primary server, PostgreSQL, FastAPI backend | M2 Ultra (likely 192GB unified memory) | LAN, serves Ollama at `:11434` |
| **RTX 4090 PC** (Windows/WSL2) | GPU worker for heavy LLM inference | Ryzen + RTX 4090 (24GB VRAM) | `192.168.0.245`, Ollama at `:11434` via WSL2 portproxy |

### Ollama Configuration

- WSL2 Ubuntu 24.04 with CUDA runtime
- `OLLAMA_HOST=0.0.0.0:11434` (all interfaces)
- `OLLAMA_FLASH_ATTENTION=1` (faster attention)
- `OLLAMA_NUM_PARALLEL=2` (concurrent inference slots)
- Windows portproxy: `0.0.0.0:11434` → WSL IP `:11434`
- Firewall rule: `Ollama WSL` (inbound TCP 11434)

### Model Strategy

- **llama3.1:8b-instruct-q8_0** (~8.5GB, fits entirely in 4090 VRAM, 100% GPU) — for event extraction
- **llama3.1:70b-instruct-q4_K_M** (~42GB, partially offloads to RAM on 4090) — higher quality, slower
- M2 Ultra may serve the 70B better due to full unified memory fit

---

## 8. The Patient Case

The system is being exercised against a real patient case: **Norman Eric Roberts**.

- **Timeline:** 4,223 pages of medical records (PDF, was encrypted, now decrypted)
- **Patient ID:** `norman_eric_roberts`
- **Clinical focus:** Comprehensive diagnostic investigation — major clinical arcs, diagnostic mysteries, treatment divergences, internal contradictions
- **Processing goal:** Turn the unstructured 4223-page timeline into a structured graph with temporal hypothesis evolution

This is the EoHD mode's primary use case: ingest a massive medical record, extract every clinically relevant event, build a patient timeline graph, and then reason over it to surface what was missed, misdiagnosed, contradicted, or undertreated.

---

## 9. Frontend & Portal

### Patient-Facing (React)

Routes: Home, Ask, Coding, EoH, EoHD, Journal, Timeline (+ upload), Patient portal, Settings, full auth flow.

**Design philosophy:** Clinical terminal / ER-ICU instrument panel. High contrast, monospaced data, no gradients, no decorations, no gamification.

### Doctor Portal

- **Ambient transcription:** Real-time audio capture + Whisper transcription
- **Clinical coding overlay:** Live medical code suggestions from transcription stream
- Doctor patient detail views

### Ambient Note-Taking Pipeline

- `transcription_machine.py` — Audio → text via OpenAI Whisper
- `wave_modulation_machine.py` — Source separation + rhythm analysis
- `wave_modulation_agent.py` — GPT-4o qualitative analysis of audio metrics

---

## 10. Database Schema Map

| Schema | Domain | Key Tables |
|--------|--------|------------|
| `ontology` | Terminologies | `snomed_concepts`, `snomed_map_icd10cm`, `icd10cm_*`, `icd11_*`, `hpo_terms/edges/synonyms`, `loinc_*`, `rxnorm_*`, `orphanet_*`, `chv_*`, `neurolex*` |
| `molecular` | Genomics | `clinvar_summary`, `clingen_*`, `gene_panels`, `disgenet_associations`, `gwas_hits` |
| `guidelines` | Clinical guidelines | `guideline_registry`, `guideline_sections`, `diagnostic_rules`, `section_code_map` |
| `text` | Clinical notes | `mimiciv_notes*` |
| `ehr_mimic3` | MIMIC-III EHR | Structured ICU data |
| `ehr_mimic4` | MIMIC-IV EHR | Structured ICU data |
| `ehr` | Patient timelines | `patient_timeline` |
| `staging` | ETL staging | `pubmd_docs` |
| `public` | Core app | `users`, `journal_entries`, `rag_corpus` (with pgvector embeddings + ivfflat ANN) |

---

## 11. What You're Building — The Big Picture

**2ndOpinionMD is a clinical reasoning platform that does what no single doctor has the time or breadth to do:** cross-reference a patient's entire multi-thousand-page medical history against the world's major medical ontologies, genomic databases, clinical guidelines, and research literature — and surface the diagnostic signals that fall through the cracks of the healthcare system.

The four modes represent four cognitive styles:
- **ASK** = "What does the medical literature say about X?"
- **CODING** = "What codes apply to this clinical note?"
- **EoH** = "Given these symptoms and history, what hypotheses should we consider?"
- **EoHD** = "Given this entire 4,223-page medical record, what has everyone missed?"

The EoHD timeline pipeline is the crown jewel — turning thousands of pages of unstructured medical records into a structured, temporally-aware graph that an LLM can reason over to find diagnostic mysteries, treatment contradictions, and missed connections.

The MakefileBook + SpellBook architecture is the engine room: 20+ medical data sources systematically loaded, embedded, indexed, and integrity-checked so the RAG pipeline has comprehensive clinical knowledge to draw from.

The current focus is operationalizing the RTX 4090 as a GPU inference worker to accelerate the timeline processing pipeline, reducing what was estimated at 12+ hours down to something manageable through parallelism, flash attention, and model sizing strategy.

---

## 12. Key Files Reference

| File | Purpose |
|------|---------|
| `2opmd_spellbook.json` | Declarative system spec (the "what") |
| `mk/00_main.mk` | MakefileBook hub (the "how") |
| `server/scripts/run_eohd_timeline_pdf.py` | EoHD timeline processing pipeline |
| `server/eoh/router.py` | EoH reasoning router |
| `server/eoh/patient_timeline_vision.py` | Patient timeline graph model |
| `server/eoh/timeline_summarizer.py` | Timeline → structured summary |
| `server/eoh/graph_enrichment.py` | Entity/relationship extraction |
| `server/api/app_postgres.py` | FastAPI application entry point |
| `UX_INVARIANTS.md` | Non-negotiable interface constraints |
| `HANDOFF_MKG_INGESTION_ANDRAS.md` | MakefileBook guide |

---

*"Named for what the system is built around: the patient's beating heart."* — `.BeatingHeart` venv naming rationale
