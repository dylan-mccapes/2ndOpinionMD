# STRATEGY: B2B API for MKG + PTV

**Date:** 2026-03-31
**Status:** Draft — awaiting review
**Scope:** Expose the Medical Knowledge Graph (MKG) and PatientTimelineVision (PTV) pipeline as B2B API products

---

## 1. What We're Selling

### Product A: MKG — Medical Knowledge Graph API

A unified, queryable medical knowledge graph backed by PostgreSQL, spanning 20+ authoritative sources:

| Layer | Sources |
|-------|---------|
| **Ontology core** | SNOMED CT (concepts, descriptions, relationships, refsets, ICD-10-CM crossmap), ICD-10/11, HPO (terms, disease links, edges, synonyms), LOINC, RxNorm, Orphanet |
| **Consumer health** | CHV (Consumer Health Vocabulary — ngrams, filters) |
| **Molecular/genomic** | ClinVar, ClinGen actionability, PanelApp, DisGeNET, GWAS catalog, Neurolex |
| **Clinical evidence** | NICE/CKS, WHO, CDC (opioid + general), VA guidelines, diagnostic rules (ACR/EULAR), PubMed abstracts |
| **EHR structural** | MIMIC-III/IV structured + notes (de-identified) |
| **RAG corpus** | Embedded guideline chunks, cross-referenced to ontology, with ANN index (ivfflat) |

**Value prop:** One API call to search, cross-reference, and retrieve evidence across all of these. No customer needs to ingest SNOMED + HPO + LOINC + guidelines themselves.

### Product B: PTV — PatientTimelineVision API

An end-to-end pipeline that takes a patient's longitudinal medical record (PDF) and produces:

1. **Event graph** — structured clinical events with timestamps, types, connascence edges
2. **Narrative summaries** — hierarchical map/reduce summaries (timeline, meds/labs, search signals)
3. **Enrichment** — gap analysis, synthesis, temporal connascence

**Value prop:** Drop in a PDF, get back a queryable patient graph and a clinical narrative. No customer needs to build an extraction pipeline, an LLM orchestrator, or a medical NLP stack.

---

## 2. Current State vs. What's Needed

### What Exists

| Component | Status |
|-----------|--------|
| MKG data in PostgreSQL | **Complete** — 20+ sources loaded, indexed, integrity-checked |
| MKG API endpoints | **Exist** — SNOMED search/concept/map, ICD, HPO, LOINC, RxNorm, Orphanet, CHV, ClinGen, PanelApp, DisGeNET, GWAS, Neurolex, guidelines, diagnostic rules, WHO, CDC, VA — all mounted in `app_postgres.py` |
| RAG search (BM25 + ANN fusion) | **Exists** — `POST /api/rag/ask`, `GET /api/rag/search` |
| PTV extraction pipeline | **Proven** — `run_ollama_extract.py` (local Ollama), `summarize_timeline_from_pdf()` |
| PTV summarization | **Proven** — GPT-4.1 hierarchical map/reduce + Opus synthesis |
| User auth (JWT/OAuth2) | **Exists** — for patient/doctor portal users |
| Rate limiting | **Exists (skeleton)** — in-memory, 3 limiters defined, only 1 wired |

### What's Missing

| Component | Priority | Effort |
|-----------|----------|--------|
| **API key infrastructure** (generation, storage, validation, rotation) | P0 | Medium |
| **B2B auth middleware** (API key → tenant context, separate from JWT user auth) | P0 | Medium |
| **Usage metering** (per-key request counts, token usage, billing events) | P0 | Medium |
| **PTV HTTP endpoint** (currently script-only, no REST API) | P0 | Low |
| **Tenant isolation** (scoped data, rate limits per key) | P1 | Medium |
| **API gateway / reverse proxy** | P1 | Low-Medium |
| **Async job queue for PTV** (PDF processing is long-running) | P1 | Medium |
| **Webhook / callback for PTV completion** | P1 | Low |
| **OpenAPI spec / developer docs** | P1 | Medium |
| **HIPAA BAA infrastructure** (PHI in PTV requests) | P0 (legal) | External |

---

## 3. API Surface Design

### 3.1 MKG Endpoints (expose existing routes under `/v1/mkg/`)

```
# Ontology search & lookup
GET  /v1/mkg/snomed/search?q={term}&limit=10
GET  /v1/mkg/snomed/concept/{concept_id}
GET  /v1/mkg/snomed/map/icd10cm/{concept_id}
GET  /v1/mkg/icd/search?q={term}
GET  /v1/mkg/hpo/search?q={term}
GET  /v1/mkg/loinc/search?q={term}
GET  /v1/mkg/rxnorm/search?q={term}
GET  /v1/mkg/orphanet/search?q={term}

# Cross-reference / evidence
GET  /v1/mkg/crossref?code={code}&system={snomed|icd10|hpo|loinc}
POST /v1/mkg/evidence/search          # RAG: BM25+ANN fusion over guidelines + corpus
GET  /v1/mkg/guidelines/search?q={term}&source={nice|cdc|va|who}
GET  /v1/mkg/diagnostic-rules?condition={condition}

# Genomic / molecular
GET  /v1/mkg/clinvar/search?gene={gene}
GET  /v1/mkg/clingen/actionability?gene={gene}
GET  /v1/mkg/disgenet/search?disease={disease}
GET  /v1/mkg/gwas/search?trait={trait}

# Meta
GET  /v1/mkg/sources                  # list all loaded sources + row counts
GET  /v1/mkg/health
```

**Implementation:** Thin versioned router that proxies to existing internal routes. No new logic — just namespacing, auth gating, and metering.

### 3.2 PTV Endpoints (new — async job model)

```
# Submit a PDF for processing
POST /v1/ptv/extract
  Content-Type: multipart/form-data
  Body: file (PDF), patient_id, question (optional), extraction_mode (lite|full)
  Response: { "job_id": "uuid", "status": "queued", "estimated_minutes": 15 }

# Check job status
GET  /v1/ptv/jobs/{job_id}
  Response: { "status": "running|completed|failed", "progress": 0.65, ... }

# Retrieve results (once completed)
GET  /v1/ptv/jobs/{job_id}/graph        # PatientTimelineVision JSON
GET  /v1/ptv/jobs/{job_id}/snapshot      # Compact structural summary
GET  /v1/ptv/jobs/{job_id}/summaries     # TimelineSummaries (narrative + meds/labs)

# Optional: webhook callback on completion
POST /v1/ptv/extract
  Body: { ..., "callback_url": "https://customer.com/webhook/ptv" }

# Meta
GET  /v1/ptv/health
GET  /v1/ptv/models                     # available extraction/summarization models
```

**Implementation:** New FastAPI router + async job queue (see Section 5).

### 3.3 Unified Meta

```
GET  /v1/health                         # global health
GET  /v1/usage                          # current billing period usage for this API key
GET  /v1/keys                           # list active keys (admin only)
POST /v1/keys                           # create new key (admin only)
DELETE /v1/keys/{key_id}                # revoke key
```

---

## 4. API Key Infrastructure

### 4.1 Key Format

```
2opmd_live_<32-char-random-hex>
2opmd_test_<32-char-random-hex>
```

Prefix identifies environment. The full key is shown once at creation, then only the last 4 chars are stored/displayed. Hash the key (SHA-256) for lookup.

### 4.2 Database Schema

```sql
CREATE TABLE b2b.api_keys (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES b2b.tenants(id),
    key_hash        TEXT NOT NULL UNIQUE,        -- SHA-256 of full key
    key_prefix      TEXT NOT NULL,               -- "2opmd_live_" or "2opmd_test_"
    key_last4       TEXT NOT NULL,               -- last 4 chars for display
    name            TEXT,                         -- human label ("Acme prod key")
    scopes          TEXT[] NOT NULL DEFAULT '{}', -- ["mkg:read", "ptv:write", ...]
    rate_limit_rpm  INT NOT NULL DEFAULT 60,     -- requests per minute
    rate_limit_rpd  INT NOT NULL DEFAULT 10000,  -- requests per day
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    expires_at      TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_used_at    TIMESTAMPTZ
);

CREATE TABLE b2b.tenants (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            TEXT NOT NULL,
    contact_email   TEXT NOT NULL,
    plan            TEXT NOT NULL DEFAULT 'free', -- free, starter, pro, enterprise
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata        JSONB DEFAULT '{}'
);

CREATE TABLE b2b.usage_events (
    id              BIGSERIAL PRIMARY KEY,
    api_key_id      UUID NOT NULL REFERENCES b2b.api_keys(id),
    tenant_id       UUID NOT NULL,
    endpoint        TEXT NOT NULL,                -- "/v1/mkg/snomed/search"
    method          TEXT NOT NULL,                -- "GET"
    status_code     INT,
    response_ms     INT,
    tokens_used     INT DEFAULT 0,               -- LLM tokens (PTV, RAG)
    cost_cents      INT DEFAULT 0,               -- computed downstream cost
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_usage_tenant_date ON b2b.usage_events (tenant_id, created_at);
CREATE INDEX idx_usage_key_date ON b2b.usage_events (api_key_id, created_at);
```

### 4.3 Key Scopes

| Scope | Grants |
|-------|--------|
| `mkg:read` | All `/v1/mkg/*` GET endpoints |
| `mkg:evidence` | `/v1/mkg/evidence/search` (RAG — uses LLM tokens) |
| `ptv:extract` | `POST /v1/ptv/extract` (creates jobs) |
| `ptv:read` | `GET /v1/ptv/jobs/*` (read results) |
| `admin` | Key management, usage export |

---

## 5. New Middleware

### 5.1 B2B Auth Middleware (must build)

```
Request flow:
  Client → [API Gateway] → B2B Auth Middleware → Rate Limiter → Route Handler → Usage Logger
```

The middleware:

1. Extracts `Authorization: Bearer 2opmd_live_...` header
2. Hashes the key, looks up in `b2b.api_keys` (cached in Redis or in-memory with 60s TTL)
3. Rejects if key not found, inactive, expired, or missing required scope
4. Attaches `request.state.tenant_id`, `request.state.api_key_id`, `request.state.scopes` to the request
5. Passes through to the next middleware

**This is separate from the existing JWT auth.** Internal routes (patient portal, doctor portal) continue to use JWT. B2B routes under `/v1/` use API key auth.

### 5.2 Rate Limiter (upgrade existing)

Current `server/utils/rate_limiter.py` is in-memory per-IP. Needs:

- **Per-key** rate limiting (not per-IP — B2B clients may share IPs or use proxies)
- **Sliding window** (current 60s fixed window is fine for MVP, but sliding is better)
- **Redis backend** for multi-process support (uvicorn workers)
- **Per-key configurable limits** from `api_keys.rate_limit_rpm` / `rate_limit_rpd`
- **429 response** with `Retry-After` header and `X-RateLimit-Remaining` / `X-RateLimit-Reset` headers

### 5.3 Usage Metering Middleware (must build)

After the response is sent, log to `b2b.usage_events`:
- Endpoint, method, status code, response time
- LLM token counts (for RAG evidence search and PTV extraction/summarization)
- Computed cost in cents (based on plan tier pricing)

**Implementation:** FastAPI middleware that wraps `response` and logs asynchronously (fire-and-forget to avoid latency). Batch inserts every 5s or 100 events.

### 5.4 PTV Job Queue (must build)

PTV extraction takes 5-60+ minutes. Cannot be synchronous HTTP.

**Options (ranked):**

| Option | Pros | Cons |
|--------|------|------|
| **Celery + Redis** | Battle-tested, retry logic, monitoring (Flower) | Dependency weight |
| **arq (async Redis queue)** | Lightweight, native async, fits existing stack | Less ecosystem |
| **PostgreSQL advisory locks + polling** | Zero new deps, already have Postgres | Crude, no built-in retry |
| **Background task + polling table** | Simplest possible | No worker isolation |

**Recommendation:** `arq` for MVP. Lightweight, async-native, Redis-backed. One worker process on the 4090 box (co-located with Ollama) for extraction, one on the M2 for summarization. Upgrade to Celery if/when job volume justifies it.

**Job lifecycle:**

```
POST /v1/ptv/extract → create row in b2b.ptv_jobs (status=queued) → enqueue to arq
Worker picks up → status=running, progress updates to DB
Extraction completes → status=extracting_done → summarization step
Summarization completes → status=completed, results stored to disk + paths in DB
Client polls GET /v1/ptv/jobs/{id} or receives webhook callback
```

```sql
CREATE TABLE b2b.ptv_jobs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL REFERENCES b2b.tenants(id),
    api_key_id      UUID NOT NULL REFERENCES b2b.api_keys(id),
    status          TEXT NOT NULL DEFAULT 'queued',  -- queued, running, completed, failed
    patient_id      TEXT,
    question        TEXT,
    extraction_mode TEXT NOT NULL DEFAULT 'full',
    progress        REAL DEFAULT 0.0,
    vision_path     TEXT,
    snapshot_path   TEXT,
    summaries_path  TEXT,
    error_message   TEXT,
    callback_url    TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ
);
```

---

## 6. Security & Compliance

### PHI Handling

PTV accepts patient medical records. This is PHI under HIPAA.

| Requirement | Approach |
|-------------|----------|
| **BAA with customers** | Required before any PHI crosses the API. Legal artifact, not code. |
| **Encryption in transit** | TLS 1.2+ on all endpoints (already in place for `2ndopinionmd.ai`) |
| **Encryption at rest** | PostgreSQL with encrypted volumes; PTV artifacts on encrypted disk |
| **Data isolation** | PTV results stored in tenant-scoped directories; no cross-tenant access |
| **Retention policy** | PTV job artifacts auto-deleted after configurable retention (default 30 days) |
| **Audit log** | `b2b.usage_events` serves as access log; add `b2b.audit_log` for key creation/deletion/scope changes |
| **De-identification option** | Offer a `deidentify=true` flag that strips PII before storage (stretch goal) |

### MKG Security

MKG contains no PHI — it's public ontology data + published guidelines. Lower risk. API key auth + rate limiting is sufficient.

---

## 7. Implementation Phases

### Phase 1: Foundation (1-2 weeks)

- [ ] Create `b2b` schema in PostgreSQL (`tenants`, `api_keys`, `usage_events`)
- [ ] Build API key generation CLI tool (`python manage_keys.py create --tenant "Acme" --scopes mkg:read,mkg:evidence`)
- [ ] Build B2B auth middleware (`server/api/middleware/b2b_auth.py`)
- [ ] Wire rate limiter per-key (upgrade existing `rate_limiter.py`)
- [ ] Create `/v1/mkg/` versioned router proxying to existing internal routes
- [ ] Add usage logging middleware
- [ ] Smoke test: external client can query SNOMED, RAG search with API key

### Phase 2: PTV API (1-2 weeks)

- [ ] Create `/v1/ptv/` router with extract, jobs, results endpoints
- [ ] Build `b2b.ptv_jobs` table
- [ ] Set up `arq` worker for extraction (pointed at remote Ollama on 4090)
- [ ] Set up summarization step (GPT-4.1 + optional Opus)
- [ ] Implement job polling and result retrieval
- [ ] Webhook callback on completion
- [ ] Smoke test: upload PDF, poll for completion, retrieve graph + summaries

### Phase 3: Hardening (1-2 weeks)

- [ ] Redis-backed rate limiting (multi-worker safe)
- [ ] Key rotation (create new key, deprecation window on old key)
- [ ] OpenAPI spec generation for `/v1/` routes with examples
- [ ] Developer documentation (hosted or markdown)
- [ ] Tenant-scoped usage dashboard (`GET /v1/usage`)
- [ ] PTV artifact retention + auto-cleanup cron
- [ ] Integration tests (key auth, rate limits, PTV end-to-end)

### Phase 4: Scale & Monetize (ongoing)

- [ ] Plan tiers (free: 100 MKG req/day; starter: 10k MKG + 5 PTV/month; pro: unlimited MKG + 50 PTV; enterprise: custom)
- [ ] Stripe integration for metered billing
- [ ] API gateway (Kong, Caddy, or nginx with lua) for TLS termination, global rate limiting, analytics
- [ ] Multi-worker PTV (horizontal scaling on GPU nodes)
- [ ] SDKs (Python, TypeScript)

---

## 8. Cost Model

### MKG

All MKG queries hit PostgreSQL only. Cost is infrastructure (Postgres + server). Near-zero marginal cost per request.

Exception: `/v1/mkg/evidence/search` (RAG) uses OpenAI embeddings for query vectorization (~$0.0001 per search). Negligible but should be metered.

### PTV

PTV has real LLM costs per job:

| Step | Model | Est. Cost per 1000-page PDF |
|------|-------|-----------------------------|
| Extraction (Ollama local) | llama3.1:8b or 70b | $0.00 (self-hosted GPU) |
| Summarization (map/reduce) | GPT-4.1 | ~$0.50–$2.00 |
| Final synthesis (optional) | Claude Opus | ~$2.00–$5.00 |
| **Total** | | **$0.50–$7.00 per job** |

Pricing should be per-job with a healthy margin. Suggested: $25–$50 per PTV job at launch (covers cost + value of the structured output customers would otherwise spend weeks building).

---

## 9. What to Build First

**Minimum viable B2B launch = Phase 1 (MKG API with keys).**

MKG is the easier product to ship:
- All endpoints already exist
- No PHI, no HIPAA BAA needed
- Near-zero marginal cost
- Just needs: API keys, auth middleware, rate limiting, usage logging, versioned router

PTV is the higher-value product but requires:
- Async job infrastructure
- PHI handling + BAA
- LLM cost management
- More testing

**Ship MKG first. Add PTV when the key infrastructure is proven.**

---

## 10. Dependencies Summary

| Dependency | Purpose | New? |
|-----------|---------|------|
| PostgreSQL `b2b` schema | Keys, tenants, usage, jobs | **New** |
| Redis | Rate limiting, job queue (arq) | **New** (or reuse if already running) |
| `arq` | Async job queue for PTV | **New** |
| `cryptography` or `hashlib` | API key hashing | Already available (stdlib) |
| Stripe SDK | Billing (Phase 4) | **New** |
| FastAPI middleware | Auth + metering | **New code**, existing framework |
| Ollama on 4090 | PTV extraction | **Exists** |
| OpenAI API key | PTV summarization + RAG embedding | **Exists** |

---

*Filed 2026-03-31. B2B API strategy for MKG (Medical Knowledge Graph) and PTV (PatientTimelineVision). Phase 1: MKG with API keys. Phase 2: PTV with async jobs. Ship MKG first.*
