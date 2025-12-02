# Machine Knowledge Engine (MKE) Architecture

**2ndOpinionMD Medical Knowledge Platform**

*Last Updated: December 02, 2025*

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [RAG Architecture](#rag-architecture)
4. [MKG Architecture](#mkg-architecture)
5. [Guidelines Ingestion](#guidelines-ingestion)
6. [Coding/Abstraction System](#codingabstraction-system)
7. [API Endpoints](#api-endpoints)
8. [Docker Deployment](#docker-deployment)
9. [AWS Readiness](#aws-readiness)
10. [Data Sizes and Performance](#data-sizes-and-performance)

---

## Overview

The Machine Knowledge Engine (MKE) is the core intelligence layer of 2ndOpinionMD, providing AI-powered medical diagnostic support through a combination of structured medical knowledge and retrieval-augmented generation. The system is designed to assist patients and healthcare providers in understanding complex symptom patterns, particularly for autoimmune diseases where misdiagnosis is common.

The MKE integrates multiple medical ontologies (ICD-10-CM, ICD-11, SNOMED CT, LOINC, RxNorm, Orphanet, HPO), clinical practice guidelines (VA/DoD, CDC, WHO, NICE), and genomic data (GWAS, DisGeNET, PanelApp) into a unified knowledge graph with vector embeddings for semantic search.

---

## System Architecture

```
+-----------------------------------------------------------------------------------+
|                              2ndOpinionMD Platform                                 |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +-------------+     +------------------+     +------------------+                |
|  |   React     |     |     Nginx        |     |    FastAPI       |                |
|  |   Frontend  |<--->|  Reverse Proxy   |<--->|    Backend       |                |
|  |  (Port 3000)|     |   (Port 80/443)  |     |   (Port 8000)    |                |
|  +-------------+     +------------------+     +------------------+                |
|                                                       |                           |
|                                                       v                           |
|  +----------------------------------------------------------------+              |
|  |                    Machine Knowledge Engine                     |              |
|  |  +------------------+  +------------------+  +----------------+ |              |
|  |  | RAG Query Engine |  | Hybrid Search    |  | LLM Synthesis  | |              |
|  |  | (postgresql_     |  | (TS + ANN +      |  | (OpenAI GPT-4) | |              |
|  |  |  query_engine.py)|  |  RRF Fusion)     |  |                | |              |
|  |  +------------------+  +------------------+  +----------------+ |              |
|  +----------------------------------------------------------------+              |
|                                    |                                              |
|                                    v                                              |
|  +----------------------------------------------------------------+              |
|  |                PostgreSQL + pgvector Database                   |              |
|  |  +------------------+  +------------------+  +----------------+ |              |
|  |  | ontology.*       |  | guidelines.*     |  | molecular.*    | |              |
|  |  | (ICD, SNOMED,    |  | (VA, CDC, WHO,   |  | (GWAS,         | |              |
|  |  |  LOINC, RxNorm,  |  |  NICE sections)  |  |  DisGeNET,     | |              |
|  |  |  Orphanet, HPO)  |  |                  |  |  PanelApp)     | |              |
|  |  +------------------+  +------------------+  +----------------+ |              |
|  |                                                                 |              |
|  |  +----------------------------------------------------------+  |              |
|  |  |                    public.rag_corpus                      |  |              |
|  |  |  Unified RAG table with embeddings (vector 1536)          |  |              |
|  |  |  Full-text search (tsvector), metadata (jsonb)            |  |              |
|  |  +----------------------------------------------------------+  |              |
|  +----------------------------------------------------------------+              |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### Component Overview

The platform consists of three main layers. The presentation layer includes a React single-page application that provides the user interface for symptom intake, health journaling, and diagnosis display. The application layer is built on FastAPI with 50+ API routers handling authentication, diagnosis, RAG retrieval, ontology search, and clinical coding. The data layer uses PostgreSQL with the pgvector extension for storing medical knowledge, embeddings, and user data.

---

## RAG Architecture

The Retrieval-Augmented Generation system combines structured knowledge graph lookups with hybrid vector and text search to provide contextually relevant medical information for LLM synthesis.

```
+-----------------------------------------------------------------------------------+
|                              RAG Query Pipeline                                    |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  INPUT: Clinical Query (symptoms, notes, questions)                               |
|                          |                                                        |
|                          v                                                        |
|  +-------------------+   +-------------------+   +-------------------+            |
|  | Term Extraction   |   | Code Detection    |   | Keyword Parsing   |            |
|  | - ICD-10 regex    |   | - LOINC patterns  |   | - Drug names      |            |
|  | - SNOMED hints    |   | - RxNorm hints    |   | - Symptom tokens  |            |
|  +-------------------+   +-------------------+   +-------------------+            |
|           |                       |                       |                       |
|           +-----------------------------------------------+                       |
|                                   |                                               |
|                                   v                                               |
|  +----------------------------------------------------------------+              |
|  |                     Source Routing (MKG-First)                  |              |
|  |  - ehr_mimic4.d_icd_diagnoses for ICD labels                   |              |
|  |  - rag_corpus by source (loinc, rxnorm, snomed, hpo)           |              |
|  |  - Symptom dictionary lookups                                   |              |
|  +----------------------------------------------------------------+              |
|                                   |                                               |
|                                   v                                               |
|  +---------------------------+   +---------------------------+                    |
|  |     Text Search (TS)      |   |   ANN Search (Dense)      |                    |
|  |  - plainto_tsquery        |   |  - OpenAI embeddings      |                    |
|  |  - ts_rank scoring        |   |  - pgvector cosine (<#>)  |                    |
|  |  - BM25-style ranking     |   |  - ivfflat index          |                    |
|  +---------------------------+   +---------------------------+                    |
|           |                               |                                       |
|           +---------------+---------------+                                       |
|                           |                                                       |
|                           v                                                       |
|  +----------------------------------------------------------------+              |
|  |                    RRF Fusion Layer                             |              |
|  |  - Reciprocal Rank Fusion scoring                              |              |
|  |  - Configurable weights (0.7 ANN, 0.3 BM25)                    |              |
|  |  - Deduplication and ranking                                    |              |
|  +----------------------------------------------------------------+              |
|                           |                                                       |
|                           v                                                       |
|  +----------------------------------------------------------------+              |
|  |                    LLM Synthesis                                |              |
|  |  - Context assembly from top-k matches                         |              |
|  |  - OpenAI GPT-4 / GPT-4o-mini                                  |              |
|  |  - Structured JSON output                                       |              |
|  +----------------------------------------------------------------+              |
|                           |                                                       |
|                           v                                                       |
|  +----------------------------------------------------------------+              |
|  |                    Citation Governance                          |              |
|  |  - Evidence title matching                                      |              |
|  |  - Code enrichment from matches                                 |              |
|  |  - Missing citation explanation                                 |              |
|  +----------------------------------------------------------------+              |
|                           |                                                       |
|                           v                                                       |
|  OUTPUT: Structured response with diagnoses, codes, citations                     |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### Hybrid Query Implementation

The hybrid query system in `server/vectordb/hybrid_query.py` implements three core functions. The `ann_query` function performs approximate nearest neighbor search using pgvector's cosine similarity operator, returning documents ranked by dense embedding similarity. The `bm25_query` function performs full-text search using PostgreSQL's tsvector and ts_rank functions for lexical matching. The `fuse` function combines results using Reciprocal Rank Fusion (RRF), which merges ranked lists from both retrieval methods with configurable weights.

### Embedding Configuration

The system uses OpenAI's text-embedding-3-small model producing 1536-dimensional vectors. Embeddings are generated in batches of 256 documents with a maximum of 6000 characters per document. The ivfflat index is configured with 200 lists and 8 probes for optimal recall-latency tradeoff.

---

## MKG Architecture

The Medical Knowledge Graph organizes medical knowledge into domain-specific PostgreSQL schemas with cross-references and unified access through the RAG corpus.

```
+-----------------------------------------------------------------------------------+
|                         Medical Knowledge Graph Schemas                            |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +---------------------------+   +---------------------------+                    |
|  |      ontology.*           |   |      guidelines.*         |                    |
|  +---------------------------+   +---------------------------+                    |
|  | icd10cm (100K+ codes)     |   | va_docs (documents)       |                    |
|  | icd11 (50K+ codes)        |   | va_sections (chunks)      |                    |
|  | snomed_map_icd10cm        |   | cdc_sections              |                    |
|  | loinc_terms (90K+)        |   | who_eml_medicines         |                    |
|  | rxnorm_conso (200K+)      |   | who_committee_sections    |                    |
|  | orphanet_diseases (10K+)  |   | nice_sections             |                    |
|  | hpo_terms (15K+)          |   +---------------------------+                    |
|  | neurolex (50K+)           |                                                    |
|  | chv (consumer vocab)      |   +---------------------------+                    |
|  +---------------------------+   |      molecular.*          |                    |
|                                  +---------------------------+                    |
|  +---------------------------+   | gwas_hits                 |                    |
|  |      ehr_mimic3.*         |   | disgenet_associations     |                    |
|  +---------------------------+   | gene_panels               |                    |
|  | admissions, patients      |   +---------------------------+                    |
|  | diagnoses_icd, procedures |                                                    |
|  | prescriptions, notes      |   +---------------------------+                    |
|  | (40+ tables)              |   |      clingen.*            |                    |
|  +---------------------------+   +---------------------------+                    |
|                                  | actionability_summary     |                    |
|  +---------------------------+   +---------------------------+                    |
|  |      ehr_mimic4.*         |                                                    |
|  +---------------------------+   +---------------------------+                    |
|  | (40+ tables, similar      |   |      text.*               |                    |
|  |  structure to MIMIC-III)  |   +---------------------------+                    |
|  +---------------------------+   | mimiciv_notes             |                    |
|                                  | n2c2_* (NLP challenge)    |                    |
|                                  +---------------------------+                    |
|                                                                                   |
|  +-----------------------------------------------------------------------+        |
|  |                        public.rag_corpus                               |        |
|  +-----------------------------------------------------------------------+        |
|  | id          | UUID primary key                                        |        |
|  | source      | Source identifier (icd10cm, va, gwas, etc.)            |        |
|  | source_id   | Original ID from source system                          |        |
|  | title       | Document/concept title                                  |        |
|  | text        | Full text content                                       |        |
|  | embedding   | vector(1536) - OpenAI embeddings                        |        |
|  | ts          | tsvector - Full-text search index                       |        |
|  | meta        | jsonb - Extensible metadata                             |        |
|  +-----------------------------------------------------------------------+        |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### Schema Details

The ontology schema contains medical terminologies and code systems. ICD-10-CM and ICD-11 tables store diagnostic codes with hierarchical relationships (parent_code, full_path). SNOMED CT mappings link SNOMED concepts to ICD-10 codes. LOINC stores laboratory test codes with component, property, and system attributes. RxNorm contains medication concepts with NDC mappings. Orphanet catalogs rare diseases with prevalence and inheritance patterns. HPO provides phenotype terms for genetic conditions. NeuroLex contains neuroscience terminology from the InterLex API.

The guidelines schema stores clinical practice guidelines parsed into searchable sections. Documents are chunked with 2000-character segments and 250-character overlap to preserve context across boundaries. Each section maintains references to its parent document and position within the guideline.

The molecular schema contains genomic and genetic data. GWAS hits link genetic variants (SNPs) to disease traits with p-values and effect sizes. DisGeNET associations connect genes to diseases with evidence scores. PanelApp gene panels group genes by clinical indication.

### Embedding Flow

Data flows into the RAG corpus through a standardized pipeline. First, source data is loaded into domain-specific schemas using ingest scripts. Then, RAG upsert scripts transform and copy relevant fields to rag_corpus with appropriate source tags. The embed_table.py script generates OpenAI embeddings in batches for records with null embedding columns. Finally, ivfflat indexes are created or rebuilt for efficient ANN search.

---

## Guidelines Ingestion

Clinical practice guidelines are ingested from multiple authoritative sources and made searchable through the RAG system.

```
+-----------------------------------------------------------------------------------+
|                        Guidelines Ingestion Pipeline                               |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +-------------+     +-------------+     +-------------+     +-------------+      |
|  |   Fetch     |     |   Parse     |     |   Load      |     |   Index     |      |
|  |  (Download) | --> | (Extract)   | --> | (Database)  | --> | (Embed+ANN) |      |
|  +-------------+     +-------------+     +-------------+     +-------------+      |
|                                                                                   |
|  Sources:                                                                         |
|  +---------------------------+   +---------------------------+                    |
|  | VA/DoD Guidelines         |   | CDC Guidelines            |                    |
|  | - va_guidelines_fetch.py  |   | - cdc_opioid_fetch.py     |                    |
|  | - va_guidelines_parse.py  |   | - cdc_opioid_parse.py     |                    |
|  +---------------------------+   +---------------------------+                    |
|                                                                                   |
|  +---------------------------+   +---------------------------+                    |
|  | WHO Guidelines            |   | NICE Guidelines           |                    |
|  | - who_eml_import.py       |   | - ingest_nice_guidelines  |                    |
|  | - who_committee_import.py |   | - scrape_nice_pdf.py      |                    |
|  +---------------------------+   +---------------------------+                    |
|                                                                                   |
|  Chunking Strategy:                                                               |
|  - Chunk size: 2000 characters                                                    |
|  - Overlap: 250 characters                                                        |
|  - Preserve section boundaries where possible                                     |
|  - Maintain document hierarchy (doc -> section -> chunk)                          |
|                                                                                   |
|  Make Targets (example for VA):                                                   |
|  - make va-fetch           # Download PDFs from VA website                        |
|  - make va-parse           # Extract and chunk sections                           |
|  - make va-rag-upsert      # Copy to rag_corpus                                   |
|  - make va-embed           # Generate embeddings                                  |
|  - make va-ann             # Create/rebuild ANN index                             |
|  - make va-ci              # Run integrity audit                                  |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### Guideline Sources

VA/DoD Clinical Practice Guidelines cover conditions including PTSD, chronic pain, diabetes, hypertension, and cardiovascular disease. These are downloaded as PDFs, parsed into sections, and stored with metadata including publication date, condition, and recommendation strength.

CDC Guidelines include opioid prescribing guidelines and other public health recommendations. The ingestion process extracts structured recommendations with evidence grades.

WHO Essential Medicines List catalogs medications with indications, dosing, and AWaRe classification (Access, Watch, Reserve). WHO Expert Committee reports provide additional clinical guidance.

NICE Guidelines from the UK National Institute for Health and Care Excellence are scraped and parsed to extract recommendations with evidence levels.

---

## Coding/Abstraction System

The clinical coding system extracts structured medical codes from clinical notes using RAG retrieval and LLM analysis.

```
+-----------------------------------------------------------------------------------+
|                        Coding/Abstraction Pipeline                                 |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  INPUT: Clinical Note Text                                                        |
|         |                                                                         |
|         v                                                                         |
|  +----------------------------------------------------------------+              |
|  |                    RAG Retrieval                                |              |
|  |  - Hybrid search (TS + ANN)                                    |              |
|  |  - Source filtering (icd10cm, loinc, rxnorm, snomed)           |              |
|  |  - Top-k matches with scores                                    |              |
|  +----------------------------------------------------------------+              |
|         |                                                                         |
|         v                                                                         |
|  +----------------------------------------------------------------+              |
|  |                    LLM Analysis                                 |              |
|  |  - Structured prompt with evidence snippets                    |              |
|  |  - JSON output schema enforcement                              |              |
|  |  - Model: GPT-4o-mini (configurable)                           |              |
|  +----------------------------------------------------------------+              |
|         |                                                                         |
|         v                                                                         |
|  +----------------------------------------------------------------+              |
|  |                    Code Enrichment                              |              |
|  |  - Match codes to RAG results                                  |              |
|  |  - Fill missing system/code from matches                       |              |
|  |  - Validate code formats                                        |              |
|  +----------------------------------------------------------------+              |
|         |                                                                         |
|         v                                                                         |
|  +----------------------------------------------------------------+              |
|  |                    Citation Governance                          |              |
|  |  - Link codes to evidence documents                            |              |
|  |  - Extract relevant excerpts                                    |              |
|  |  - Explain missing citations                                    |              |
|  +----------------------------------------------------------------+              |
|         |                                                                         |
|         v                                                                         |
|  OUTPUT: Structured Response                                                      |
|  +----------------------------------------------------------------+              |
|  | {                                                               |              |
|  |   "insight": {                                                  |              |
|  |     "assessment": "Clinical summary...",                       |              |
|  |     "risk_factors": [...],                                      |              |
|  |     "red_flags": [...]                                          |              |
|  |   },                                                            |              |
|  |   "probable_dx": [                                              |              |
|  |     {"system": "ICD-10-CM", "code": "I21.4", "title": "...",   |              |
|  |      "why": "...", "evidence_titles": [...]}                   |              |
|  |   ],                                                            |              |
|  |   "differential_dx": [...],                                     |              |
|  |   "procedures": [{"system": "ICD-10-PCS", ...}],               |              |
|  |   "labs": [{"system": "LOINC", ...}],                          |              |
|  |   "medications": [{"system": "RxNorm", ...}]                   |              |
|  | }                                                               |              |
|  +----------------------------------------------------------------+              |
|                                                                                   |
|  Output Formats: JSON, CSV, PDF                                                   |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### Code Systems

The coding system supports multiple medical code systems. ICD-10-CM provides diagnostic codes with format validation (e.g., I21.4 for NSTEMI). ICD-10-PCS provides procedure codes. LOINC codes identify laboratory tests (e.g., 2345-7 for glucose). RxNorm codes identify medications with NDC mappings. SNOMED CT concepts provide additional clinical terminology.

### Endpoint Details

The POST /api/rag/coding endpoint accepts a clinical note and returns structured codes. The request includes the note text, optional source filters, and result limit. The response includes clinical insight, probable and differential diagnoses, recommended procedures, labs, and medications, each with evidence citations.

---

## API Endpoints

The FastAPI backend exposes 50+ routers organized by domain.

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/health | GET | Health check with service status |
| /api/diagnose | POST | AI-powered diagnosis from symptoms |
| /api/rag/ask | POST | RAG retrieval with hybrid search |
| /api/rag/coding | POST | Clinical coding abstraction |

### Authentication

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/auth/register | POST | User registration with email verification |
| /api/auth/login | POST | JWT-based authentication |
| /api/auth/verify-email | POST | Email verification |
| /api/auth/reset-password | POST | Password reset flow |

### Journal

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/journal/ | GET | List user's journal entries |
| /api/journal/ | POST | Create entry with AI analysis |
| /api/journal/{id} | GET | Get specific entry |
| /api/journal/analytics | GET | Trend analysis over time |

### Ontology Search

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/loinc/search | GET | Search LOINC lab codes |
| /api/snomed/search | GET | Search SNOMED CT concepts |
| /api/rxnorm/search | GET | Search RxNorm medications |
| /api/orphanet/search | GET | Search rare diseases |
| /api/hpo/search | GET | Search phenotype terms |
| /api/neurolex/search | GET | Search neuroscience terms |
| /api/chv/search | GET | Search consumer health vocabulary |

### Guidelines

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/guidelines/search | GET | Search all guidelines |
| /api/guidelines/va/* | GET | VA/DoD guidelines |
| /api/guidelines/cdc/* | GET | CDC guidelines |
| /api/who/* | GET | WHO guidelines |

### Molecular/Genomic

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/gwas/search | GET | Search GWAS catalog |
| /api/disgenet/search | GET | Search gene-disease associations |
| /api/panelapp/search | GET | Search gene panels |
| /api/clingen/* | GET | ClinGen actionability data |

### EHR Data

| Endpoint | Method | Description |
|----------|--------|-------------|
| /api/mimic3/* | GET | MIMIC-III queries |
| /api/mimic4/* | GET | MIMIC-IV queries |
| /api/notes/* | GET | Clinical notes search |

---

## Docker Deployment

The application is containerized for consistent deployment across environments.

```
+-----------------------------------------------------------------------------------+
|                           Docker Deployment Architecture                           |
+-----------------------------------------------------------------------------------+
|                                                                                   |
|  +---------------------------+     +---------------------------+                  |
|  |      nginx container      |     |       api container       |                  |
|  +---------------------------+     +---------------------------+                  |
|  | Dockerfile.nginx          |     | Dockerfile.api            |                  |
|  | - nginx:alpine base       |     | - python:3.12-slim base   |                  |
|  | - Reverse proxy config    |     | - FastAPI application     |                  |
|  | - SSE support             |     | - Uvicorn server          |                  |
|  | - Gzip compression        |     | - Port 8000               |                  |
|  | - Static asset serving    |     |                           |                  |
|  | - Ports 80/443            |     |                           |                  |
|  +---------------------------+     +---------------------------+                  |
|              |                                   |                                |
|              +-----------------------------------+                                |
|                              |                                                    |
|                              v                                                    |
|  +-----------------------------------------------------------------------+        |
|  |                    PostgreSQL + pgvector                               |        |
|  |  - External database (not containerized in production)                |        |
|  |  - Connection via DATABASE_URL environment variable                   |        |
|  +-----------------------------------------------------------------------+        |
|                                                                                   |
+-----------------------------------------------------------------------------------+
```

### Container Configuration

The API container is based on python:3.12-slim with system dependencies for psycopg2 (build-essential, libpq-dev). The application is started via `python -m server.scripts.run_postgres_app` and exposes port 8000. Environment variables are loaded from .env.docker in production mode (APP_ENV=production).

The Nginx container provides reverse proxy functionality with SSE support (proxy_buffering off), gzip compression for static assets, and configuration includes from conf.d directory.

### Deployment Commands

The Makefile provides deployment targets. `make ship` builds the frontend, deploys to the production path, and reloads Nginx. `make fe-build` builds the React application with yarn. `make deploy-fe` copies build artifacts to /opt/homebrew/var/www/2ndopinionmd with timestamped archival for rollback. `make nginx-reload` tests and reloads the Nginx configuration. `make smoke` performs a health check against the production API. `make rollback REL=YYYY-MM-DD-HHMM` restores a previous release.

---

## AWS Readiness

The system is designed for migration to AWS infrastructure with minimal changes.

### Current State

The application currently runs on local PostgreSQL with the pgvector extension installed. The database connection is configured via DATABASE_URL and SYNC_DATABASE_URL environment variables. All data is stored in PostgreSQL schemas with vector embeddings in the rag_corpus table.

### Target Architecture

The target AWS deployment uses RDS PostgreSQL with pgvector extension (available in RDS). The migration path involves creating an RDS instance with pgvector enabled, performing database migration via pg_dump/pg_restore, updating environment variables to point to RDS endpoint, and verifying ANN indexes are recreated.

### Considerations

RDS supports the pgvector extension in PostgreSQL 15+. The ivfflat indexes may need tuning based on RDS instance size and query patterns. Connection pooling via RDS Proxy is recommended for production workloads. The application code requires no changes as it uses standard PostgreSQL connections.

---

## Data Sizes and Performance

### Data Volumes

| Source | Records | Notes |
|--------|---------|-------|
| ICD-10-CM | 100,000+ | Diagnostic codes |
| ICD-11 | 50,000+ | WHO classification |
| SNOMED CT | 400,000+ | Clinical concepts |
| LOINC | 90,000+ | Lab test codes |
| RxNorm | 200,000+ | Medication concepts |
| Orphanet | 10,000+ | Rare diseases |
| HPO | 15,000+ | Phenotype terms |
| NeuroLex | 50,000+ | Neuroscience terms |
| VA Guidelines | 10,000+ | Guideline sections |
| MIMIC-III/IV | Millions | EHR records |
| RAG Corpus | 500,000+ | Unified documents |

### Performance Configuration

Database connection pooling uses pool_size=20 with max_overflow=30. Pool pre-ping is enabled for connection health checks. Pool recycle is set to 3600 seconds.

Vector search uses ivfflat indexes with lists=200 and probes=8. The cosine similarity operator (<#>) is used for distance calculations. Hybrid fusion combines ANN and BM25 results with configurable weights.

Rate limiting protects the API with 5 requests/minute for authentication endpoints, 10 requests/minute for diagnosis endpoints, and 60 requests/minute for general endpoints.

Embedding generation uses batch size of 256 documents with maximum 6000 characters per document. The text-embedding-3-small model produces 1536-dimensional vectors.

### Query Performance

Typical RAG queries complete in 200-500ms including embedding generation, hybrid search, and result fusion. LLM synthesis adds 1-3 seconds depending on model and context size. End-to-end diagnosis requests typically complete in 3-5 seconds.

---

## Appendix: Key Files Reference

### Backend Core
- `server/api/app_postgres.py` - Main FastAPI application
- `server/api/rag_routes.py` - RAG retrieval endpoints
- `server/api/coding_routes.py` - Clinical coding abstraction
- `server/api/journal.py` - Health journaling with AI analysis
- `server/vectordb/postgresql_query_engine.py` - RAG query engine
- `server/vectordb/hybrid_query.py` - Hybrid TS + ANN fusion

### Database
- `database/schemas/*.sql` - Schema DDL files
- `database/sql/*.sql` - Queries, indexes, audits

### Data Ingestion
- `server/scripts/embed_table.py` - Generic embedding generator
- `server/scripts/ingest_*.py` - Source-specific loaders
- `server/scripts/*_rag_upsert.py` - RAG corpus population

### Makefile System
- `Makefile` - Root entry point
- `mk/00_main.mk` - Core targets and includes
- `mk/*.mk` - Domain-specific targets

### Docker
- `docker/api/Dockerfile.api` - API container
- `docker/nginx/nginx.conf` - Nginx configuration

---

*This document is maintained as part of the 2ndOpinionMD-MVP repository. For questions or updates, contact the development team.*
