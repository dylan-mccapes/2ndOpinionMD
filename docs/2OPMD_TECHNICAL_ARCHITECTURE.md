---
title: "2ndOpinionMD — Technical Architecture"
subtitle: "Medical Knowledge Engine · Ethos of Health · PatientTimelineVision · Privacy & Compliance"
author: "2ndOpinionMD Engineering"
date: "April 2026"
geometry: margin=1in
fontsize: 11pt
documentclass: report
toc: true
toc-depth: 3
numbersections: true
header-includes:
  - \usepackage{booktabs}
  - \usepackage{longtable}
  - \usepackage{hyperref}
  - \hypersetup{colorlinks=true, linkcolor=blue, urlcolor=blue}
  - \usepackage{fancyhdr}
  - \pagestyle{fancy}
  - \fancyhead[L]{2ndOpinionMD Technical Architecture}
  - \fancyhead[R]{\thepage}
  - \fancyfoot[C]{}
---

\newpage

# Executive Summary

2ndOpinionMD is an AI-powered clinical reasoning platform built for longitudinal patient health assessment, diagnostic support, and computable flare detection in autoimmune disease. The system is architected around three core subsystems:

1. **Medical Knowledge Engine (MKE)** — A unified medical knowledge graph with 500,000+ RAG-indexed documents spanning 15+ ontologies, clinical practice guidelines, genomic data, and EHR corpora.

2. **Ethos of Health (EoH)** — A modular clinical reasoning framework with 30+ modules covering terrain modeling, flare detection, escalation, care planning, and governance. EoH defines a formal patient state coordinate system (Stack Level × Stability Band × Time) and enforces strict safety invariants.

3. **PatientTimelineVision (PTV)** — A patient-specific knowledge graph that captures longitudinal clinical events, connascence edges, and temporal relationships from EHR data. PTV is the substrate on which EoH reasoning operates.

The platform is designed for **HIPAA-compliant on-premise deployment** via PortalNode-01, a purpose-built inference server running local eoh-llama models through Ollama. Every layer — from query anonymization to encrypted logging to provenance-tracked graph mutations — is built with clinical data privacy as a first-class architectural concern.

This document provides a comprehensive technical reference for the entire system.

\newpage

# System Architecture Overview

## High-Level Component Map

\small

```
+--------------------------------------------------------+
|                 2ndOpinionMD Platform                  |
+--------------------------------------------------------+
|                                                        |
|  +--------+   +----------------------------------+     |
|  | React  |   |       FastAPI Backend            |     |
|  | Front  |<=>|  50+ routers / SSE streaming     |     |
|  | (SPA)  |   |  Auth / RAG / EoH / Timeline     |     |
|  +--------+   +---------------+------------------+     |
|                               |                        |
|        +----------------------+---------------+        |
|        |                      |               |        |
|        v                      v               v        |
|  +------------+  +-------------+  +------------+       |
|  |    MKE     |  |    EoH      |  |    PTV     |       |
|  | Knowledge  |  |  Reasoning  |  |  Patient   |       |
|  |  Engine    |  |  Framework  |  |   Graph    |       |
|  +-----+------+  +------+------+  +-----+------+       |
|        |                |               |              |
|        +----------------+---------------+              |
|                         v                              |
|  +--------------------------------------------------+  |
|  |       PostgreSQL + pgvector Database             |  |
|  |  ontology / guidelines / molecular / ehr         |  |
|  |  rag_corpus (500K+ docs, 1536-dim vectors)       |  |
|  +--------------------------------------------------+  |
|  +--------------------------------------------------+  |
|  |       Ollama (eoh-llama models)                  |  |
|  |  3.2 (routing) / 8B (workhorse) / 70B (synth)    |  |
|  +--------------------------------------------------+  |
+--------------------------------------------------------+
```

\normalsize

\newpage

## Technology Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | React 18, TypeScript, Vite | SPA with SSE streaming, role-based routing |
| Backend | FastAPI, Python 3.12, Uvicorn | 50+ routers, async throughout |
| Database | PostgreSQL 16 + pgvector | Vector embeddings (1536-d, 384-d), HNSW/ivfflat indexes |
| LLM (Cloud) | OpenAI GPT-4o, GPT-4.1, GPT-4.1-mini | Multi-model tiering by task complexity |
| LLM (Local) | Ollama + eoh-llama (3.2, 8B, 70B) | HIPAA air-gapped, custom Modelfile |
| Proxy | Nginx | Reverse proxy, SSE support, gzip, static assets |
| Containerization | Docker Compose | API + Nginx services |
| Data Ingestion | GNU Make (MakefileBook) | 30+ domain-specific Makefile modules |
| Provenance | ProvenanceEngine (PyPI) | Lorenz-attractor-based graph lifecycle |

\newpage

# Medical Knowledge Engine (MKE)

## Overview

The Medical Knowledge Engine is the core intelligence layer. It integrates multiple medical ontologies, clinical practice guidelines, and genomic data into a unified knowledge graph with vector embeddings for semantic search. The MKE powers RAG (Retrieval-Augmented Generation) across all clinical reasoning endpoints.

## Knowledge Graph Schema Architecture

The Medical Knowledge Graph (MKG) organizes data into domain-specific PostgreSQL schemas:

### Ontology Schema (`ontology.*`)

| Table | Records | Description |
|-------|---------|-------------|
| `icd10cm` | 100,000+ | ICD-10-CM diagnostic codes with hierarchy |
| `icd11` | 50,000+ | WHO ICD-11 classification |
| `snomed_map_icd10cm` | 400,000+ | SNOMED CT to ICD-10 mappings |
| `loinc_terms` | 90,000+ | LOINC laboratory test codes |
| `rxnorm_conso` | 200,000+ | RxNorm medication concepts with NDC |
| `orphanet_diseases` | 10,000+ | Rare disease catalog (prevalence, inheritance) |
| `hpo_terms` | 15,000+ | Human Phenotype Ontology |
| `neurolex` | 50,000+ | Neuroscience terminology (InterLex) |
| `chv` | — | Consumer Health Vocabulary |

### Guidelines Schema (`guidelines.*`)

| Source | Description | Ingestion |
|--------|-------------|-----------|
| VA/DoD | Clinical Practice Guidelines (PTSD, pain, diabetes, CVD) | PDF → chunked sections |
| CDC | Opioid prescribing, public health recommendations | Structured extraction |
| WHO | Essential Medicines List (AWaRe classification) | Import + committee reports |
| NICE | UK clinical recommendations with evidence levels | Scrape + parse |

Guidelines are chunked into 2000-character segments with 250-character overlap, preserving section boundaries and document hierarchy.

### Molecular/Genomic Schema (`molecular.*`)

| Table | Description |
|-------|-------------|
| `gwas_hits` | Genetic variant → disease trait associations (SNPs, p-values) |
| `disgenet_associations` | Gene → disease associations with evidence scores |
| `gene_panels` | PanelApp gene panels by clinical indication |

### ClinGen Schema (`clingen.*`)

| Table | Description |
|-------|-------------|
| `actionability_summary` | Clinical actionability assessments for genetic findings |

### EHR Schemas (`ehr_mimic3.*`, `ehr_mimic4.*`)

MIMIC-III and MIMIC-IV de-identified EHR corpora (40+ tables each): admissions, diagnoses, procedures, prescriptions, clinical notes, lab results.

## Unified RAG Corpus

All knowledge flows into `public.rag_corpus` — a single table optimized for hybrid retrieval:

| Column | Type | Purpose |
|--------|------|---------|
| `id` | UUID | Primary key |
| `source` | TEXT | Origin identifier (icd10cm, va, gwas, etc.) |
| `source_id` | TEXT | Original ID from source system |
| `title` | TEXT | Document/concept title |
| `text` | TEXT | Full text content |
| `embedding` | vector(1536) | OpenAI text-embedding-3-small |
| `ts` | tsvector | Full-text search index |
| `meta` | JSONB | Extensible metadata |

**Current corpus size:** 500,000+ documents across all sources.

## Hybrid Retrieval Pipeline

The RAG query pipeline implements a three-stage hybrid search:

1. **Term Extraction** — ICD-10 regex, LOINC patterns, SNOMED hints, drug names, symptom tokens parsed from the clinical query.

2. **Dual Retrieval**
   - **ANN Search**: pgvector cosine similarity (`<#>` operator) over 1536-dim embeddings with ivfflat indexing (200 lists, 8 probes).
   - **BM25 Search**: PostgreSQL tsvector full-text search with `ts_rank` scoring.

3. **RRF Fusion** — Reciprocal Rank Fusion combines both ranked lists with configurable weights (default 0.7 ANN, 0.3 BM25), deduplication, and source-gating heuristics.

**Performance:** Typical RAG queries complete in 200–500ms (embedding + search + fusion). End-to-end diagnosis requests complete in 3–5 seconds including LLM synthesis.

## MakefileBook — Data Ingestion System

The MakefileBook (`mk/`) is the imperative execution layer for all MKG data ingestion, embedding generation, and integrity auditing. The root `Makefile` includes `mk/00_main.mk`, which fans out to 30+ domain-specific modules:

\footnotesize

| Module | Domain | Targets |
|--------|--------|---------|
| 01\_snomed | SNOMED CT | load, rag-upsert, embed |
| 02\_icd | ICD-10-CM/11 | load, rag-upsert, embed |
| 03\_hpo | Phenotype Ontology | fetch, parse, embed |
| 04\_loinc\_rxnorm | Labs + Medications | load, embed |
| 13\_guidelines | Clinical Guidelines | fetch, parse, rag-upsert |
| 21\_va | VA/DoD Guidelines | ci (integrity audit) |
| 22\_integrity | Cross-source | rag-audit, check-sources |
| 31\_ethos\_of\_health | EoH Canon | ingest, embed |
| 90\_reports | Reporting | generation targets |
| 91\_coding | Clinical Coding | coding pipeline |
| 95\_b2b | B2B API | key mgmt, schema setup |
| 98\_backups | Database Backups | backup, restore |
| 99\_backend | Backend Ops | dev, prod, health |

\normalsize

Each domain module follows a standard pipeline: **Fetch → Parse → Load → RAG Upsert → Embed → ANN Index → Integrity Audit**.

The MakefileBook is cross-referenced by the SpellBook (`2opmd_spellbook.json`), a declarative build/UX specification that maps UI features to their data dependencies.

\newpage

# Ethos of Health (EoH) Reasoning Framework

## Overview

The Ethos of Health is a modular clinical reasoning framework that implements structured, safety-gated health assessment. EoH is not a single model — it is a layered system of 30+ modules, each responsible for a specific aspect of clinical reasoning, connected by typed data contracts and enforced invariants.

EoH is embodied in two forms:

1. **Cloud LLM prompt system** — The EoH module index, question routing, and governance rules are injected into cloud LLM prompts (GPT-4o, GPT-4.1) as structured system instructions.

2. **Local eoh-llama models** — Custom Ollama Modelfiles bake the entire EoH framework into the model's system prompt, enabling air-gapped clinical reasoning.

## Core Terrain Model (M1–M3)

EoH represents patient health as a three-dimensional coordinate system:

$$\text{Patient State} = \text{Stack Level} \times \text{Stability Band} \times \text{Time}$$

- **Stack Level** (integer 0..N): Count of confirmed chronic conditions. Stack 0 = no chronic diagnoses (OHB intact). Each confirmed diagnosis adds +1. Stack changes require confirmed diagnosis lifecycle — no auto-promotion from symptom escalation alone.

- **Stability Band** (0–5): Per-stack-level instability score.
  - Band 0–1: Well-compensated, stable
  - Band 2–3: Early/moderate instability, rising flare risk
  - Band 4–5: Decompensation / imminent collapse

- **OHB (Original Healthy Baseline)**: The patient's best-attainable pre-chronic state. Baseline Integrity Score (0–100) measures how much OHB remains intact.

- **CBM (Chronic Baseline Mode)**: The patient's stable day-to-day state with chronic illness. Deviation from CBM triggers acute-phase evaluation.

**Key Invariant:** Band shifts NEVER auto-increment Stack. Stack changes require confirmed diagnosis only.

## Module Architecture

### Signal Tagging & Interpretation

| Module | Name | Function |
|--------|------|----------|
| M4 | Reflex Suppression Audit | Classifies suppression reasons (Overshoot, Healing Pain, Symbolic Flare, Lab Error) |
| M5 | Symbolic Interpreter (PSI) | Psychosomatic Index (0–3); factors narrative distortion into flare risk |
| M7A | Data Quality | Trust assessment for individual data points; handles missingness, contradictions |
| M9 | Suppression Core | Single suppression channel with pauseFlag, pauseReason, priority ladder, TTLs |
| M12 | Narrative Engine | Compresses free-text patient reporting into structured digest + findings |

### Flare Detection & Escalation

| Module | Name | Function |
|--------|------|----------|
| M6 | Escalation Router | Converts state transitions into tiered alerts (T0–T3) |
| M10 | Crisis Engine | Tier-4 protocol — Zone-5 persistence, collapse language, suicidality, sepsis cues |
| M13 | Trend & Prognostic | Flare probabilities and risk trajectories over days/months |
| M14 | Action & Escalation | Concrete next steps for patient and clinician per risk tier |
| M20 | Early Warning | Pre-flare signal detection; streaming anomaly detection for subtle shifts |
| M68 | Inflammatory Capacity Model | Real-time allostatic headroom via three-valve dynamics (inflow, outflow, capacity) |

### Care Planning

| Module | Name | Function |
|--------|------|----------|
| M7B | Care Plan Orchestrator | Translates risk tiers into Tasks, ServiceRequests, CarePlan adjustments |
| M15 | Consolidation Report | Multi-condition, capacity-aware CarePlan timeline |
| M22 | Adaptive Plan Modulation | Intensity adjustments — tighten vs. loosen monitoring/therapy |
| M23 | Tapering | Governs safe taper from active treatment to CBM/OHB |
| M59 | Plan Co-Creation | Human input shapes plans via confirmation-gated, draft-only artifacts |
| M66 | EWA (Exploratory Wellness Actions) | Low-risk, reversible lifestyle actions; non-diagnostic, non-prescriptive |

### V6 Advanced Detection

| Module | Name | Function |
|--------|------|----------|
| M64 | FUDD | Functional Utilization Discordance Detector — detects when "normal" labs mask impaired tissue utilization |
| M65 | Dark Passenger | Detects longitudinal voice identity drift in patient journal text; classifies persona type and etiology |

### Governance & Reasoning Quality

| Module | Name | Function |
|--------|------|----------|
| M57 | Clinical Invariants | Non-negotiable constraints that shape reasoning flow (ordering, gating, eligibility) |
| M63 | Derivation Transparency | Every output requires a DerivationChain (inputs, transformations, assumptions) |
| M67 | ARGL | Adversarial Reasoning Governance — evidence provenance, validity rebinding, mandatory falsification |

## Question Routing

The EoH LLM router (`eoh_llm_router`) classifies incoming questions into types:

| Type | Question Pattern | Modules Activated |
|------|-----------------|-------------------|
| A | "What is this patient's flare risk?" | M13, M68, M6, M20 |
| B | "Is this a real flare or symbolic/overshoot?" | M4, M5, M7A, M9 |
| C | "Why did the system predict/escalate?" | M63, M67, M57 |
| D | "How should we adjust the plan?" | M7B, M22, M23, M59 |
| E | "Is the model calibrated?" | M67, performance analytics |

The router produces a JSON execution plan specifying which modules and document handles to activate, without executing any clinical logic itself.

## Guardrails

The following invariants are enforced across all EoH operations:

- NEVER auto-diagnose. Diagnosis requires confirmed dx lifecycle.
- NEVER escalate Stack from Band shifts alone.
- NEVER bypass suppression semantics or consent enforcement.
- NEVER claim certainty beyond what evidence supports.
- ALWAYS trace outputs to inputs via DerivationChain.
- ALWAYS distinguish CBM-expected variation from true acute deviation.
- EWA actions are NEVER diagnostic or prescriptive.
- FUDD detections require clinician authority for intervention activation.

\newpage

# PatientTimelineVision (PTV)

## Overview

PatientTimelineVision is the patient-specific knowledge graph. Unlike the MKG (which stores medical knowledge), PTV stores a patient's longitudinal clinical history as a graph of events connected by typed edges representing temporal, causal, and clinical relationships.

## Graph Schema

### PostgreSQL Tables

**`ehr.patient_graph_vision`** — Full graph stored as JSONB (one row per patient):

| Column | Type | Purpose |
|--------|------|---------|
| `patient_id` | TEXT | Primary key |
| `graph_json` | JSONB | Complete event graph (events + connascence edges) |
| `updated_at` | TIMESTAMPTZ | Last modification timestamp |

**`ehr.patient_graph_chart`** — Per-event embeddings for hybrid retrieval:

| Column | Type | Purpose |
|--------|------|---------|
| `patient_id` | TEXT | FK to patient |
| `event_id` | TEXT | Unique event identifier |
| `event_type` | TEXT | Event classification |
| `preview` | TEXT | Human-readable event text |
| `embedding` | vector(384) | Sentence-transformer embedding (HNSW indexed) |

**`ehr.patient_graph_status`** — Readiness gate:

| Column | Type | Purpose |
|--------|------|---------|
| `is_ready` | BOOLEAN | Graph built, validated, ready for EoHD |
| `event_count` | INTEGER | Total events in graph |
| `edge_count` | INTEGER | Total edges in graph |
| `chart_count` | INTEGER | Embedded events available for retrieval |
| `ts_coverage` | REAL | Temporal coverage fraction |

## Graph Construction Pipeline

PTV graphs are built from EHR data (PDF timelines, FHIR bundles, structured records) through a multi-stage pipeline:

### Stage 1: Heuristic Pre-Extraction

`server/eoh/heuristic_page_extract.py` runs fast regex and pattern-matching over raw page text before any LLM call. This produces a "skeleton" of dates, medication names, lab values, and encounter markers. The skeleton is passed to the LLM so it can focus token budget on interpretation rather than extraction.

### Stage 2: LLM-Powered Summarization

`server/eoh/timeline_summarizer.py` processes each artifact through either cloud (GPT-4o) or local (eoh-llama via Ollama) models:

- Entity extraction (conditions, medications, procedures, labs)
- Temporal alignment (date normalization, sequence ordering)
- Flare-signal scoring
- Structured node/edge emission with provenance metadata

### Stage 3: Graph Assembly

`server/eoh/patient_timeline_vision.py` assembles extracted events into the `PatientTimelineVision` graph:

- **`TimelineEventVision`**: Individual clinical events with type, date, structured data
- **`ClinicalArc`**: Named arcs grouping related events (e.g., "RA Diagnosis Arc")
- **Connascence edges**: Typed temporal and clinical relationships inferred between events

The graph supports both file-based persistence (JSON) and PostgreSQL persistence (`save_timeline_vision_pg` / `load_timeline_vision_pg`).

### Stage 4: Embedding & Indexing

`server/eoh/patient_timeline_chart.py` generates 384-dim sentence-transformer embeddings for each event and stores them in `ehr.patient_graph_chart` with HNSW indexing for sub-millisecond nearest-neighbor search.

## Graph Retrieval

PTV supports hybrid retrieval for context assembly:

- **`graph_ts_search`**: Full-text search over event previews
- **`graph_traverse`**: Multi-hop graph traversal following connascence edges
- **`reciprocal_rank_fusion`**: Combines text and traversal results
- **`build_graph_context_docs`**: Assembles LLM-ready context from graph search results
- **`build_arc_context_docs`**: Retrieves context scoped to specific clinical arcs
- **`build_cross_arc_context_docs`**: Cross-arc reasoning context

## Opportunistic Graph Enrichment (OGrE)

`server/eoh/graph_enrichment.py` implements continuous background enrichment:

- **`enrich_graph_opportunistic`**: During idle cycles, the 8B model scans low-confidence nodes and their 2-hop neighborhoods, proposing new edges above a 0.7 confidence threshold.
- **`enrich_graph_from_batch`**: Batch enrichment from LLM outputs during detective runs.

Every graph mutation is provenance-tracked with model name, confidence score, and enrichment reason.

\newpage

# Chat Graph — Bounded Conversational Memory

## Design

The Chat Graph (`ehr.chat_graph`) provides bounded conversational memory aligned to PTV events. Unlike unbounded chat history, the Chat Graph implements:

- **Logarithmic decay**: Message relevance scores decay over time
- **PTV anchoring**: Messages can be anchored to specific graph events, increasing their retention
- **Budget enforcement**: Per-patient character limits with automatic eviction
- **Soft-delete audit**: Evicted messages are preserved with `evicted_at` and `eviction_reason`

## Schema

| Column | Type | Purpose |
|--------|------|---------|
| `patient_id` | TEXT | Patient identifier |
| `message_id` | UUID | Primary key |
| `role` | TEXT | `patient`, `doctor`, `system`, or `agent` |
| `content` | TEXT | Message content |
| `decay_score` | REAL | Current relevance (1.0 = fresh, decays logarithmically) |
| `retention_reason` | TEXT | Why this message is retained |
| `anchored_event_ids` | TEXT[] | PTV event IDs this message relates to |
| `reference_edges` | JSONB | Typed references (journal_entry, detective_report, ptv_event, etc.) |
| `evicted_at` | TIMESTAMPTZ | Soft-delete timestamp (NULL = active) |
| `eviction_reason` | TEXT | Why the message was evicted |

## Budget Table

| Column | Type | Purpose |
|--------|------|---------|
| `max_total_chars` | INTEGER | Per-patient limit (default 500,000) |
| `current_total_chars` | INTEGER | Current usage |
| `total_evictions` | INTEGER | Lifetime eviction count |
| `last_decay_run` | TIMESTAMPTZ | Last decay computation |

\newpage

# EoH Detective (EoHD)

## Overview

The EoH Detective is the system's deep investigation mode. It performs multi-step clinical reasoning over a patient's PTV graph, executing a planned sequence of EoH-guided analysis steps with full provenance.

## Execution Flow

1. **Graph Load** — Load or build the patient's PTV graph from PostgreSQL
2. **Planner** — `eoh_detective_planner` generates a JSON execution plan (which EoH modules and question types to evaluate)
3. **Per-Step Execution** — Each plan step runs `eoh_stream_event_generator` (shared with EoH streaming), producing SSE events with clinical findings
4. **Graph Enrichment** — `enrich_graph_opportunistic` adds discovered edges back to the PTV graph
5. **Synthesis** — `detective_report_llm` produces a comprehensive narrative report via Claude or GPT-4o
6. **Figures** — `generate_all_figures` creates event density heatmaps, connascence chord diagrams, temporal coverage charts, medication burden timelines, and diagnostic arc visualizations
7. **PDF Generation** — `build_detective_pdf` assembles the report, figures, and provenance metadata into a downloadable PDF
8. **Persistence** — Results are saved to `ehr.detective_runs` and optionally to the Chat Graph

## SSE Event Contract

The detective stream emits Server-Sent Events in a mandatory order:

```
timeline_loaded → signals → flare_features → probabilistic_differential
  → per_step_results → enrichment_summary → report → figures → pdf_ready
```

This ordering is validated by `server/eoh/validators.py` to ensure clinical reasoning follows the correct sequence.

\newpage

# HIPAA Compliance & Privacy Architecture

## Design Philosophy

Privacy in 2ndOpinionMD is not a bolt-on module — it is a layered architectural concern woven into every subsystem. The system is designed for deployment in HIPAA-regulated environments, with the ability to run fully air-gapped on PortalNode-01 hardware.

## Privacy Layers

### Layer 1: Query Anonymization Agent

**File:** `server/api/anon_query_agent.py`

Every clinical query that enters the system is anonymized in parallel before logging. The anonymization agent converts queries containing PHI into categorical summaries:

- **Input:** `"34 year old male with chest pain and shortness of breath for 3 days"`
- **Output:** `"symptom_query: cardiopulmonary_assessment adult"`

The agent runs non-blocking (2-second timeout) alongside the main retrieval path. If it fails or times out, the system falls back to `"query_received: anonymization_timeout"` — never logging the raw query.

**Categories:** `symptom_query`, `condition_query`, `treatment_query`, `diagnostic_query`, `guideline_query`, `coding_query`, `research_query`, `general_query`.

### Layer 2: Encrypted Logging

**File:** `server/utils/encrypted_logging.py`

All server logs are encrypted at rest using Fernet symmetric encryption:

- Log records are serialized to JSON (timestamp, level, logger, message)
- JSON is encrypted with a Fernet key stored separately from log files
- Encrypted logs are base64-encoded and written to rotating files (10 MB max, 5 backups)
- Decryption requires the key file — logs are unreadable without it

```python
setup_encrypted_logging(
    log_dir="./logs",
    max_bytes=10 * 1024 * 1024,  # 10 MB rotation
    backup_count=5,
    key_path="log_encryption.key"
)
```

A `decrypt_log_file()` utility is provided for authorized audit access.

### Layer 3: Security Middleware

**File:** `server/api/app_postgres.py`

The FastAPI application includes defensive middleware:

- Blocks access to sensitive paths (`/.env`, `/.git`, internal config files)
- CORS origin restriction via `CORS_ALLOW_ORIGINS` environment variable
- Request logging with anonymized queries only

### Layer 4: Chat Graph Audit Trail

Evicted chat messages are soft-deleted — never physically removed from the database. Each eviction is recorded with:

- `evicted_at` timestamp
- `eviction_reason` (e.g., `"budget_exceeded"`, `"decay_threshold"`)
- Full message content preserved for audit

### Layer 5: Anonymization Consent Tracking

The `patient_timelines` table includes an `anonymization_consent` field (set during session initialization) that records whether the patient has consented to de-identified data use.

### Layer 6: B2B Access Control

**Files:** `server/b2b/auth.py`, `api_keys.py`, `key_store.py`

External API access (`/v1/mkg/*`) is governed by:

- API key authentication with scoped permissions (`mkg:read`, `mkg:evidence`)
- Per-key rate limiting via `B2BUsageMiddleware`
- Request logging with key identity (not query content)

### Layer 7: Local-First LLM Inference

When deployed on PortalNode-01, all LLM inference runs locally through Ollama:

- **No patient data leaves the network** after initial model download
- eoh-llama models bake the entire EoH framework into their system prompt
- `OLLAMA_BASE_URL` defaults to `http://localhost:11434/v1`
- Cloud LLM (OpenAI) is an optional, configurable upgrade — not a dependency

### Layer 8: Provenance Tracking

Every significant system action is receipt-tracked:

- PTV graph mutations include model name, confidence, and reason
- Detective runs are persisted with full execution trace
- Chat Graph messages include typed `reference_edges` for traceability
- ProvenanceEngine (PyPI) provides Lorenz-attractor-based lifecycle scoring for graph nodes

\newpage

# eoh-llama — Local Model Architecture

## Model Tiering

The system defines three local model tiers, each built from a base Llama model with custom EoH system prompts via Ollama Modelfiles:

| Model | VRAM | Latency | Traffic | Use Cases |
|-------|------|---------|---------|-----------|
| eoh-llama 3.2 | 2 GB | < 300 ms | ~10% | Routing, triage, keyword extraction, quick replies |
| eoh-llama 8B | 5 GB | < 1.2 s | ~82% | OGrE traversal, flare scoring, medical coding, most queries |
| eoh-llama 70B | 40 GB | < 4 s | ~8% | Deep synthesis, final flare prediction, gap/probe agents, RISE validation |

## Modelfile (eoh-llama 8B example)

```
FROM llama3.1:8b-instruct-q8_0

PARAMETER temperature 0.2
PARAMETER top_p 0.9
PARAMETER num_ctx 32768
PARAMETER stop "<|eot_id|>"

SYSTEM """You are an Ethos-of-Health (EoH) clinical reasoning
assistant. You operate within the EoH framework — a layered,
modular system for longitudinal patient health assessment,
flare detection, care planning, and governance..."""
```

The system prompt embeds the complete EoH framework specification (~4000 tokens), including terrain model definitions, all module descriptions, question routing taxonomy, and safety guardrails.

## GPU Allocation (PortalNode-01)

| GPU | Assignment | Models |
|-----|-----------|--------|
| GPU 0 (always-on) | RTX 4090 #1, 24 GB | eoh-llama 3.2 + 8B (shared VRAM, 7 GB total) |
| GPU 1+2 (on-demand) | RTX 4090 #2 & #3, 48 GB combined | eoh-llama 70B (tensor-parallel) |
| GPU 3 (standby) | RTX 4090 #4, 24 GB | Hot spare / burst 70B capacity |

## Routing Logic

A lightweight FastAPI router on CPU inspects each request's intent tag and routes to the lightest sufficient model. ProvenanceEngine logs every routing decision:

```
model=8b reason=complexity_score>0.4 latency_ms=890
```

Fallback: if 70B is busy, requests degrade gracefully to 8B with a `REVIEW` flag for later 70B re-evaluation.

\newpage

# Multi-Model Cloud Architecture

## Model Tiers (Cloud Configuration)

The cloud deployment uses three OpenAI model tiers, configurable via environment variables:

| Tier | Default Model | Config Variable | Use Cases |
|------|--------------|-----------------|-----------|
| Guidelines | GPT-4o | `CHAT_MODEL_GUIDELINES` | Guideline reasoning, EoH streaming, long-form synthesis |
| Coding Core | GPT-4.1 | `CHAT_MODEL_CODING_CORE` | Code extraction, ledger building, clinically important inference |
| Utility | GPT-4.1-mini | `CHAT_MODEL_UTIL` | Routing, grading, clustering, JSON-only tasks |

## Embedding Configuration

- **Model:** `text-embedding-3-small` (1536 dimensions)
- **Batch size:** 256 documents
- **Max chars per document:** 6000
- **Index:** ivfflat (200 lists, 8 probes)
- **Distance metric:** Cosine similarity (`<#>` operator)

## Fallback Chain

The system supports Claude (Anthropic) as a fallback for detective report synthesis when available, with automatic degradation to GPT-4o if Claude is unavailable.

\newpage

# API Surface

## Core Endpoints

\footnotesize

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/health | GET | Service health check |
| /api/diagnose | POST | AI diagnosis from symptoms |
| /api/rag/ask\_stream | POST | RAG retrieval, SSE streaming |
| /api/rag/coding\_stream | POST | Clinical coding (streaming) |
| /api/rag/eoh\_stream | POST | EoH reasoning (streaming) |
| /api/rag/eoh\_detective\_stream | POST | Full EoHD investigation |
| /api/chat/send | POST | Send message to chat graph |
| /api/chat/history/\{patient\_id\} | GET | Chat history with decay scores |
| /api/chat/anchor | POST | Anchor message to PTV event |
| /api/eoh/router\_plan | POST | EoH module routing (plan only) |

\normalsize

## Timeline Endpoints

\footnotesize

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/timeline/\{patient\_id\} | GET | Patient timeline events |
| /api/timeline/\{id\}/events | POST | Add events to timeline |
| /api/timeline/\{id\}/search | POST | Hybrid search over timeline |
| /api/timeline/\{id\}/analytics/summary | GET | Timeline analytics summary |

\normalsize

## Ontology Endpoints (15+ routers)

Each medical ontology has dedicated search endpoints:

`/api/loinc`, `/api/snomed`, `/api/rxnorm`, `/api/orphanet`, `/api/hpo`, `/api/neurolex`, `/api/chv`, `/api/gwas`, `/api/disgenet`, `/api/clingen`, `/api/guidelines`, `/api/who`, `/api/mimic3`, `/api/mimic4`, `/api/notes`

## B2B API

| Endpoint | Method | Scope | Description |
|----------|--------|-------|-------------|
| `/v1/mkg/*` | GET | `mkg:read` | Scoped mirror of ontology search |
| `/v1/mkg/evidence` | POST | `mkg:evidence` | RAG evidence retrieval |
| `/v1/health` | GET | — | B2B health check |

\newpage

# Frontend Architecture

## Routing

The React SPA implements role-based routing:

| Route | Page | Access |
|-------|------|--------|
| `/` | Home | Public |
| `/ask` | RAG Query | Authenticated |
| `/coding` | Clinical Coding | Authenticated |
| `/eoh` | Ethos of Health | Authenticated |
| `/eohd` | EoH Detective | Authenticated |
| `/chat` | Chat Graph | Authenticated |
| `/journal` | Health Journal | Patient |
| `/timeline` | Patient Timeline | Doctor |
| `/timeline/upload` | Timeline Upload | Doctor |
| `/patient` | Patient Portal | Patient |
| `/doctor` | Doctor Portal | Doctor |
| `/doctor/patients/:id` | Patient Detail | Doctor |
| `/settings` | User Settings | Authenticated |

## Key Libraries

- **SSE Streaming**: Custom hooks for Server-Sent Event consumption (`useChatGraph.ts`, `useTimelineStatus.ts`)
- **API Client**: Centralized fetch wrapper (`lib/api.ts`)
- **Receipt Cache**: Client-side provenance caching (`lib/receiptCache.ts`)

\newpage

# Deployment Architecture

## Docker Compose

The production deployment consists of two containers:

```yaml
services:
  api:
    build: docker/api/Dockerfile.api
    ports: ["8000:8000"]
    env_file: .env.docker
    environment:
      APP_ENV: production
      PYTHONPATH: /app

  nginx:
    image: nginx:alpine
    ports: ["80:80"]
    volumes:
      - ./docker/nginx/nginx.conf:/etc/nginx/nginx.conf
      - ./rag-demo-ui/index.html:/usr/share/nginx/html/index.html
```

## PortalNode-01 (On-Premise)

For HIPAA-regulated deployments, the system runs on PortalNode-01:

| Component | Specification |
|-----------|--------------|
| Chassis | Rosewill RSV-L4500U (4U rack-mount) |
| CPU | Intel Xeon w5-2465X (16C/32T, 112 PCIe 5.0 lanes) |
| RAM | 128 GB DDR5-4800 ECC (4×32 GB) |
| GPUs | 4× NVIDIA RTX 4090 (96 GB VRAM total) |
| Storage | 2 TB NVMe (OS) + 8 TB NVMe (models + data) |
| PSU | Corsair AX1600i (1600W, 80+ Titanium) |
| Network | Dual 10 GbE + IPMI |
| OS | Ubuntu 24.04 LTS + Docker + Ollama |
| Power | ~2.2 kW under full load |
| Cost | ~$10,500 BOM |

**Air-gapped operation:** After initial model download and MKG loading, the system requires no internet connectivity. All inference, retrieval, and graph operations run locally.

\newpage

# ProvenanceEngine Integration

## Overview

ProvenanceEngine is a standalone Python package (published to PyPI) that implements Lorenz-attractor-based graph lifecycle management. It provides the mathematical framework for deciding which graph nodes to retain, review, or evict based on their trajectory through a chaotic dynamical system.

## Integration Points

| System | How ProvenanceEngine Is Used |
|--------|------------------------------|
| PTV Graph | Node lifecycle scoring (retain/review/evict classification) |
| Chat Graph | Decay computation and eviction candidate selection |
| Detective Runs | Execution trace receipting |
| OGrE Enrichment | Confidence-gated mutation provenance |
| MakefileBook | Ingestion receipt tracking |

## Key Concepts

- **Portal GC (Garbage Collection)**: RK4 integration of node trajectories through the Lorenz attractor. Trajectories that converge to stable wings are classified; those that remain chaotic are flagged for review.
- **Classification confidence**: A 0.0–1.0 score based on wing residence time and trajectory stability.
- **x0 provenance**: Every initial condition is tagged as `"direct"` (explicitly set) or `"degree_inferred"` (computed from graph degree).
- **Report metadata**: All ProvenanceEngine reports include `schema_version`, `package_version`, `source_hash` (SHA-256), and `generated_by`.

\newpage

# Appendix A: Database Schema Summary

| Schema | Table | Purpose |
|--------|-------|---------|
| `public` | `users` | User accounts (patients, doctors) |
| `public` | `journal_entries` | Health journal entries with AI analysis |
| `public` | `medical_knowledge` | Legacy knowledge store with 1536-d embeddings |
| `public` | `rag_corpus` | Unified RAG table (500K+ docs, vector + tsvector) |
| `ontology` | `icd10cm`, `icd11`, `snomed_map_icd10cm`, `loinc_terms`, `rxnorm_conso`, `orphanet_diseases`, `hpo_terms`, `neurolex`, `chv` | Medical terminologies |
| `guidelines` | `va_docs`, `va_sections`, `cdc_sections`, `who_eml_medicines`, `nice_sections` | Clinical practice guidelines |
| `molecular` | `gwas_hits`, `disgenet_associations`, `gene_panels` | Genomic/genetic data |
| `clingen` | `actionability_summary` | Clinical actionability |
| `ehr_mimic3` | 40+ tables | MIMIC-III de-identified EHR |
| `ehr_mimic4` | 40+ tables | MIMIC-IV de-identified EHR |
| `ehr` | `patient_graph_vision` | PTV graph (JSONB per patient) |
| `ehr` | `patient_graph_chart` | PTV event embeddings (384-d, HNSW) |
| `ehr` | `patient_graph_status` | Graph readiness gate |
| `ehr` | `patient_timeline` | Patient timeline events (1536-d embeddings) |
| `ehr` | `chat_graph` | Bounded chat memory with decay |
| `ehr` | `chat_graph_budget` | Per-patient eviction budget |
| `ehr` | `detective_runs` | EoHD execution traces |
| `eoh` | `patient_state` | Persisted EoH state per patient |
| `eoh` | `module_run` | EoH module execution log |

# Appendix B: Key File Reference

| File | Purpose |
|------|---------|
| `server/api/app_postgres.py` | Main FastAPI application, middleware, router mounting |
| `server/api/stream_config.py` | Central model/env configuration, prompts, knobs |
| `server/api/rag_stream_detective.py` | EoH Detective streaming orchestrator |
| `server/api/rag_stream_eoh.py` | EoH reasoning streaming |
| `server/api/anon_query_agent.py` | Query anonymization for logging |
| `server/api/chat_graph_routes.py` | Chat Graph API endpoints |
| `server/eoh/router_llm.py` | EoH LLM router (question classification → execution plan) |
| `server/eoh/patient_timeline_vision.py` | PTV graph model and persistence |
| `server/eoh/patient_timeline_chart.py` | PTV hybrid retrieval |
| `server/eoh/timeline_summarizer.py` | PDF/EHR → PTV pipeline (Ollama + cloud) |
| `server/eoh/heuristic_page_extract.py` | Pre-LLM heuristic extraction |
| `server/eoh/graph_enrichment.py` | OGrE background enrichment |
| `server/eoh/chat_graph.py` | Chat decay, eviction, anchoring logic |
| `server/eoh/validators.py` | Safety and schema validation |
| `server/llm/llm_client.py` | LLM abstraction (OpenAI, Ollama, Anthropic) |
| `server/utils/encrypted_logging.py` | Fernet-encrypted log rotation |
| `server/vectordb/hybrid_query.py` | ANN + BM25 + RRF fusion |
| `server/ollama/eoh-llama3.1-8b.Modelfile` | Custom EoH model definition |
| `mk/00_main.mk` | MakefileBook hub (30+ domain modules) |

---

*This document is part of the 2ndOpinionMD-MVP repository. Generated April 2026.*
