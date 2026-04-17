# 2ndOpinionMD — On-Premise AI for Computable Flare Detection

**Prepared for**: Investor Overview — April 2026
**Presented by**: Nate Roberts, Co-Founder & CEO
**Confidential**

---

## The Opportunity

Autoimmune disease affects 24 million Americans. Rheumatoid arthritis alone costs the U.S. healthcare system **$19.3 billion annually**. The central clinical problem: **flare prediction is subjective, inconsistent, and late**.

2ndOpinionMD is building the system that makes flare detection computable — structured, auditable, and early.

---

## What We Have

### RISE Registry Access

We are building on the **largest EHR-enabled rheumatology registry in the United States**, operated by the American College of Rheumatology:

| Metric | Scale |
|--------|-------|
| Total patients | **3,904,717** |
| Total encounters | **42,605,000** |
| Active practices | 179 |
| Active providers | 999 |
| RA patients (ICD-10 M05/M06) | **416,720** |
| FHIR-enabled | Yes |
| Tokenized/de-identified (Datavant) | Yes, as of April 2026 |

This is not a research dataset. This is **live clinical infrastructure** powering 200 practices.

### Working Software

2ndOpinionMD is not a pitch deck. It is a deployed system:

- **PatientTimelineVision (PTV)** — Ingests EHR records (including scanned PDFs), extracts structured clinical events, builds a navigable patient timeline graph
- **EoH Detective** — AI investigation engine that traverses the timeline, identifies flare signals, and produces scored, auditable reports
- **Chat Graph** — Patient-doctor-agent messaging with decay-scored retention and event anchoring
- **Heuristic Pre-Extraction** — Regex-first pipeline that extracts dates, ICD codes, medications, and labs **before** the LLM touches anything, saving 40-60% of inference cost
- **ProvenanceEngine** — Open-source graph lifecycle manager (published on PyPI) that ensures every AI decision is logged with a receipt

### Proven Pipeline

Recent test run on synthetic patient data (Norman Eric Roberts):
- 4,000+ page PDF ingested and structured
- Heuristic pass: ~1ms/page, extracted dates, ICD codes, medications
- LLM enrichment: structured clinical events with timestamps and confidence scores
- Full timeline built with graph-based flare signal detection

---

## Why On-Premise

### The Problem with Cloud AI in Healthcare

Every cloud LLM call sends patient data to a third party. Even with BAAs, this creates:
- **Regulatory risk** — HIPAA compliance is a liability, not a feature
- **Vendor lock-in** — OpenAI's pricing and model changes are outside your control
- **Latency variance** — Network-dependent inference is unpredictable
- **Audit gaps** — You cannot fully audit what happens to data on someone else's server

### Our Solution: PortalNode-01

A single rack-mount server that a health system or registry can drop into their data center. No internet after initial setup. Total estimated cost: **$12–15k**.

| Component | Spec |
|-----------|------|
| CPU | Intel i5-14600K / i7-14700K |
| RAM | 128 GB DDR5-6000 ECC |
| GPUs | 4× NVIDIA RTX 4090 (96 GB VRAM total) |
| Storage | 2 TB NVMe (OS/logs) + 8 TB NVMe (models/graph) |
| Power | 2000W redundant PSU, single 30A circuit |
| Network | Dual 10 GbE + IPMI management |
| Chassis | 4U rack-mount, standard 19" |
| Stack | Ubuntu 24.04 + Docker + Ollama + FastAPI |

### Three-Tier Model Strategy

We run three sizes of the same model architecture, routed by task complexity:

| Model | Role | Latency | % of Traffic |
|-------|------|---------|-------------|
| **eoh-llama 3.2** (2 GB) | Routing, triage, keyword extraction | < 300ms | ~10% |
| **eoh-llama 8B** (5 GB) | Core inference — flare scoring, timeline enrichment, queries | < 1.2s | **80–90%** |
| **eoh-llama 70B** (40 GB) | Deep synthesis — final flare predictions, differential reasoning | < 4s | ~5–10% |

A lightweight FastAPI router on the CPU classifies each request by intent and routes to the smallest sufficient model. Every routing decision is logged with a receipt. If the 70B is busy, the system degrades gracefully to 8B and flags for human review.

**Result**: Full-stack AI inference at **$0.00/query** after hardware cost. No API keys, no metered billing, no data leaving the building.

---

## Why This Investment

### 1. Market Timing

Healthcare AI is a **$45B market by 2030** (Grand View Research), but adoption is stalled by a single objection: **data leaves the building**. Every health system, payer, and registry we talk to asks the same question first. On-premise inference eliminates it. The companies that solve local-first clinical AI own the next decade of deployments.

### 2. Clinical Impact

Autoimmune flare management is reactive, subjective, and expensive. Earlier, more accurate flare detection means:
- Fewer ER visits from unmanaged flares ($2,500–$15,000 per avoidable admission)
- Earlier treatment escalation (biologics before irreversible joint damage)
- Reduced long-term disability and total cost of care
- Better patient outcomes — measurable, publishable, replicable

### 3. Defensible Moat

- **RISE registry access** — 3.9M patients, exclusive partnership with ACR
- **On-premise deployment** — eliminates the "data risk" objection that kills healthcare AI deals
- **Open-source core** — ProvenanceEngine is MIT-licensed, building community and trust
- **Receipt-grade provenance** — every AI decision has an auditable trail, a requirement for clinical adoption

### 4. Unit Economics

| Item | Cloud AI | PortalNode-01 |
|------|----------|---------------|
| Hardware | $0 | $12–15k (one-time) |
| Per-query cost | $0.01–0.15 | **$0.00** |
| 100k queries/month | $1,000–15,000/mo | **$0/mo** |
| Annual at scale | $12k–180k | **Electricity only (~$200/mo)** |
| Data leaves building? | Yes | **No** |
| HIPAA audit burden | High | **Minimal** |

At 100,000 queries/month across RISE practices, the hardware pays for itself in **1–2 months** versus cloud inference.

### 5. Scalability Path

- **Phase 1** (now): Single PortalNode-01 for RISE pilot — $15k
- **Phase 2**: Modular Node A + Node B split — easier maintenance, ~$20k
- **Phase 3**: Multi-node deployment across RISE data centers — replicable appliance model
- **Phase 4**: BloomForge (CuPy GPU acceleration) for real-time simulation over patient graphs

Each node is built from consumer-grade parts. No enterprise GPU contracts. No NVIDIA DGX pricing. Replaceable, auditable, upgradeable.

---

## The Team

**Nate Roberts** — Co-Founder & CEO. Former fintech/healthtech. Business development, RISE relationship, fundraising.

**Dylan McCapes** — Co-Founder & CTO. Former IoT/ML engineer (August Home → ASSA ABLOY). Built the entire technical stack: PTV, EoH, ProvenanceEngine, on-prem inference architecture. Published ProvenanceEngine as open-source on PyPI. Designed the tiered model strategy and PortalNode hardware spec.

**Vincent** — Advisor. Construction industry operator bringing build-discipline to hardware deployment: right tool for the job, no shortcuts, full provenance.

**Dr. Andras Perl** — Clinical Advisor. Rheumatology, immunology, metabolic research. UC Davis. RISE research network.

---

## The Ask

**$500K seed round** to:
1. Build and deploy PortalNode-01 to RISE data center ($15k hardware + $35k integration)
2. Complete RISE analytic project proposal and IRB process ($50k)
3. Run computable flare detection study on 416,720 RA patients ($100k — 6 months)
4. Hire one ML engineer to harden the pipeline for multi-site deployment ($150k)
5. 12-month runway for founders ($150k)

**Milestones for investors**:
- Q2 2026: PortalNode-01 deployed, RISE proposal submitted
- Q3 2026: First flare detection results on de-identified RISE data
- Q4 2026: Publication-ready study, approach additional registries (CorEvitas, FORWARD)
- Q1 2027: Series A readiness with clinical validation data

---

## Summary

2ndOpinionMD is not building another cloud AI wrapper. We are building a **local-first, receipt-grade, clinically validated flare detection system** that runs entirely on hardware you can touch, in a data center you control, on the largest rheumatology dataset in the country.

The models are local. The data is local. The decisions are auditable. The cost is zero per query.

**This is what responsible healthcare AI looks like.**

---

*2ndOpinionMD — Paying attention is our form of love.*
