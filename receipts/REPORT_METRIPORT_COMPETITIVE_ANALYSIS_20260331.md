# REPORT: Metriport — Work With, Compete Against, or Ignore

**Date:** 2026-03-31
**Author:** Claude (Opus 4.6, Cursor agent)
**Source:** [Metriport Medical API Docs](https://docs.metriport.com/medical-api/getting-started/quickstart)
**Context:** Evaluating Metriport's Medical API against 2ndOpinionMD-MVP's current architecture and B2B strategy

---

## What Metriport Is

Metriport is a **medical data interoperability API**. It connects healthcare applications to Health Information Exchange (HIE) networks, pharmacies, and laboratories. The core value proposition:

1. **Data retrieval:** Query HIE networks for a patient's medical records (C-CDA documents, FHIR resources, PDFs, images)
2. **Data normalization:** Auto-convert C-CDA XML to FHIR R4 JSON, deduplicate, standardize, enrich with medical code crosswalks (ICD-10-CM, SNOMED, LOINC via CCSR)
3. **Data contribution:** Bidirectional — customers must contribute data back to HIE networks (mandatory, not optional)
4. **Medical Record Summary:** Consolidate all records into a single HTML/PDF document
5. **Analytics:** Care gap detection (HEDIS measures), suspect condition identification
6. **Real-time notifications:** ADT events (admit/transfer/discharge) via webhooks
7. **EHR integrations:** Pre-built connectors for Epic, Athena, Elation, Canvas, Healthie, Practice Fusion, Salesforce

**Business model:** API-as-a-service. Single API key per customer (`x-api-key` header). Requires a covered entity with an NPI number and a valid Treatment purpose of use. Sandbox environment with de-identified test patients.

**Open-source component:** Metriport is open-source ([github.com/metriport/metriport](https://github.com/metriport/metriport)). The converter API (C-CDA → FHIR) is available standalone.

---

## What 2ndOpinionMD Is (For Comparison)

| Capability | Metriport | 2ndOpinionMD |
|-----------|-----------|-------------|
| **Data source** | HIE networks, pharmacies, labs (live, national) | Uploaded PDFs (patient-provided medical records) |
| **Ingestion** | C-CDA/FHIR auto-conversion | LLM-powered extraction (Ollama/GPT-4.1) from raw PDF text |
| **Data model** | FHIR R4 resources (standard) | PatientTimelineVision graph (custom, connascence-edged) |
| **Normalization** | FHIR standard + CCSR crosswalks | RxNorm medication normalization, SNOMED/ICD via MKG |
| **Knowledge graph** | None (data store, not a knowledge graph) | MKG — 20+ ontology sources, 81 endpoints |
| **Analysis** | Care gaps (HEDIS), suspect conditions | EoH Detective — multi-step LLM investigation with graph traversal |
| **Output** | Consolidated FHIR bundle, Medical Record Summary (PDF/HTML) | Streaming diagnostic narrative with citations and graph context |
| **Embedding/navigation** | None | PatientTimelineChart (384d sentence-transformer embeddings) |
| **Enrichment** | Static — data comes in, gets normalized, sits there | Opportunistic — graph grows during every traversal |
| **Auth/B2B** | Single API key, `x-api-key` header | `Authorization: Bearer 2opmd_{env}_{token}`, scoped, rate-limited (just built) |

---

## Three Postures

### 1. Work With Metriport (RECOMMENDED for Phase 1)

**Metriport solves a problem 2OPMD does not want to solve: getting the data in the first place.**

Right now, 2OPMD's ingestion pipeline starts with "the patient or doctor uploads a PDF." That works for Andras's use case (reviewing a specific patient's records). It does not scale to B2B customers who want to plug in and have data flow automatically.

**Integration architecture:**

```
Customer's EHR → Metriport API → FHIR R4 Bundle (webhook) →
2OPMD ingestion adapter (FHIR → PatientTimelineVision) →
Graph enrichment → PatientTimelineChart embedding →
EoH Detective / B2B API
```

What this buys:

- **Automated data acquisition.** Instead of manual PDF upload, a customer registers their facility and patients in Metriport. Metriport queries HIE networks and sends FHIR bundles via webhook. 2OPMD receives structured data instead of raw PDF pages.
- **No HIE compliance burden.** Metriport handles the HIE network contracts, data contribution requirements, NPI validation, and patient matching. 2OPMD does not need to become an HIE-connected entity.
- **Richer input data.** FHIR resources come with coded diagnoses (ICD-10-CM, SNOMED), coded medications (RxNorm), coded labs (LOINC), and encounter metadata. This is higher quality input than OCR'd PDF text for the PTV extraction pipeline.
- **National coverage.** Metriport connects to Carequality, CommonWell, eHealth Exchange, Surescripts (pharmacy), and Quest/Labcorp (labs). 2OPMD gets access to the national health data network without building the plumbing.

**What 2OPMD brings that Metriport does not have:**

- **The graph.** Metriport stores FHIR resources as flat collections. 2OPMD builds a connascence-edged graph with temporal, causal, diagnostic, treatment, and confounder relationships. The graph is the product.
- **The detective.** Metriport can generate a Medical Record Summary (a formatted rendering of FHIR data). 2OPMD runs a multi-step LLM investigation that traverses the graph, discovers patterns, and produces a diagnostic narrative. Metriport shows you the data. 2OPMD investigates it.
- **The knowledge graph.** MKG's 81 endpoints (SNOMED hierarchy, HPO-disease links, RxNorm interactions, guideline search, PubMed evidence, Orphanet rare diseases, ClinVar variants) provide clinical intelligence that Metriport does not offer. Metriport normalizes codes. 2OPMD explains them.
- **Opportunistic enrichment.** Every time the detective runs, the graph gets better. Metriport's data is static once ingested.

**Effort to integrate:**

| Component | Work Required |
|-----------|---------------|
| FHIR → PTV adapter | New module: parse FHIR Bundle, map resources to TimelineEventVision nodes, infer connascence edges from FHIR references. Medium effort (~2-3 days). |
| Webhook receiver | New FastAPI endpoint to receive Metriport webhooks, validate signature, download consolidated data from presigned S3 URL. Small effort (~1 day). |
| Metriport client | Register facilities/patients, trigger network queries. Use their Node SDK or raw HTTP. Small effort. |
| Data contribution | 2OPMD would need to contribute back (mandatory). The detective's findings could be formatted as FHIR Observations and pushed back via Create Patient Consolidated. Medium effort. |

**Cost:** Metriport pricing is not public on their docs. Requires a sales call. Budget for per-patient-query fees.

---

### 2. Compete Against Metriport (NOT RECOMMENDED)

Metriport solves the data acquisition and normalization layer. Building an equivalent would require:

- HIE network contracts (Carequality, CommonWell, eHealth Exchange) — legal and compliance effort measured in months
- Pharmacy data feeds (Surescripts) — requires DEA and NCPDP registration
- C-CDA → FHIR converter — Metriport's is open-source, so this specific component is free
- Patient matching across networks — probabilistic matching on demographics
- HIPAA BAA infrastructure for every customer
- Bidirectional data contribution compliance

None of this is 2OPMD's competitive advantage. 2OPMD's advantage is what happens *after* the data arrives: the graph, the detective, the knowledge graph, the enrichment loop. Competing with Metriport on data plumbing is competing on someone else's strength.

The only scenario where competition makes sense: if Metriport's pricing is predatory or their API is unreliable, and a customer demands a self-hosted alternative. In that case, the C-CDA → FHIR converter is open-source and can be self-hosted. But the HIE network access cannot be self-hosted — that requires institutional agreements.

---

### 3. Ignore Metriport (ACCEPTABLE for now)

If the immediate customer is Andras and the workflow remains PDF upload → PTV extraction → detective, Metriport is irrelevant today. The current pipeline works: patient or doctor uploads PDFs, Ollama/GPT-4.1 extracts events, graph gets built.

**When ignoring stops being viable:**

- When a B2B customer says "I want to connect my EHR and have data flow automatically"
- When a B2B customer says "I don't have PDFs, my data is in Epic/Athena/Cerner"
- When scale exceeds what manual PDF upload can support (>10 patients/day)

At that point, Metriport (or a competitor: Flexpa, Particle Health, Zus Health) becomes necessary infrastructure.

---

## Recommendation

**Phase 1 (now → first B2B customer): Ignore.** Keep the PDF pipeline. Ship MKG API. Ship PTV API. Get the first paying customer. Metriport is overhead until there is revenue.

**Phase 2 (first B2B customer → 10 customers): Evaluate.** When a customer asks for EHR integration, evaluate Metriport vs. Flexpa vs. Particle Health. The FHIR → PTV adapter is the same regardless of which interoperability vendor you choose. Build the adapter generically.

**Phase 3 (10+ customers): Integrate.** At this scale, manual PDF upload is a bottleneck. Metriport or equivalent becomes infrastructure. The integration is clean because 2OPMD's value is downstream of data acquisition — graph construction, enrichment, investigation, knowledge graph. The data source is pluggable.

---

## Architectural Note: FHIR → PTV Is Graph Enrichment

The conversion from FHIR R4 resources to PatientTimelineVision is itself an instance of the twelfth wonder. A FHIR Bundle is a flat collection of resources with reference pointers (`"subject": {"reference": "Patient/123"}`). Converting it to a PTV graph means:

1. Each FHIR resource becomes a TimelineEventVision node
2. FHIR references become connascence edges (temporal, diagnostic, treatment)
3. Coded concepts (SNOMED, ICD, RxNorm, LOINC) become MKG lookup keys for enrichment
4. The conversion itself is enrichment — you are traversing a structure, noticing relationships, and recording them as graph edges

This is the same operation as PDF extraction, just with cleaner input. FHIR resources are pre-structured. PDF text is unstructured. The enrichment loop is identical: traverse, notice, record, merge.

---

## Key Metriport Capabilities to Note

| Capability | Relevance to 2OPMD |
|-----------|-------------------|
| **C-CDA → FHIR converter** (open-source) | Could use standalone for customers who have C-CDA documents but not full EHR integration. Free. |
| **Care gap detection** (HEDIS measures) | See detailed analysis below. |
| **AI Summaries** | See detailed analysis below. |
| **Suspecting** (condition identification) | See detailed analysis below. |
| **Real-time ADT notifications** | Useful for monitoring — could trigger re-runs of the detective when a patient is admitted/transferred/discharged. |
| **Data analytics / warehouse** | See detailed analysis below. |
| **Sandbox with de-identified patients** | Useful for development and demos. Free to test against. |
| **Data contribution requirement** | Non-trivial — if 2OPMD integrates Metriport, it must contribute data back. The detective's findings (new diagnoses, treatment recommendations, identified confounders) could be the contribution. |

---

## Deep Comparison: Where Capabilities Overlap

*Updated 2026-04-01 after full API documentation review.*

### AI Summaries — Shallow Overlap

Metriport's AI Summaries produce "one cohesive paragraph" of a patient's most relevant medical history. It's a premium feature, delivered as a Base64-encoded text blob in a FHIR Binary resource. Available via API, dashboard, or data warehouse.

**How 2OPMD differs:** The EoH Detective produces a multi-step diagnostic *investigation*, not a summary. It traverses the PTV graph with priority-weighted edges, runs gap analysis, queries MKG for evidence, and produces a narrative with citations, confidence bands, and open questions. The detective doesn't summarize — it investigates. A summary is a compression. An investigation is an expansion.

**Competitive risk:** Low. Any customer sophisticated enough to want graph-based investigation will not confuse it with a one-paragraph brief. The brief is useful as a *triage* tool. The detective is a *diagnostic reasoning* tool. They serve different moments in the clinical workflow.

**B2B opportunity:** Use Metriport's AI Summary as the "quick look" tier of the 2OPMD API. Customers who only need a brief get it from Metriport's layer. Customers who need investigation escalate to the detective. Two tiers, one pipeline.

---

### Care Gaps (HEDIS) — Moderate Overlap, Strong Complement

Metriport implements the full [HEDIS measure set](https://www.ncqa.org/hedis/) published by NCQA. This includes 80+ quality measures across:

- **Prevention/Screening:** Breast cancer (BCS-E), cervical cancer (CCS-E), colorectal cancer (COL-E), immunization status
- **Chronic disease management:** Diabetes (eye exams, kidney health, glycemic status, BP control), cardiovascular (statin therapy, BP control, cardiac rehab), COPD, asthma
- **Behavioral health:** ADHD follow-up, depression screening/remission, substance use treatment
- **Overuse/appropriateness:** High-risk medications in elderly, opioid monitoring, unnecessary imaging, antibiotic overuse
- **Risk-adjusted utilization:** Readmissions, preventable hospitalizations, ED utilization

Each care gap is a FHIR MeasureReport with population membership (initial population, denominator, numerator, exclusions). A gap exists when a patient is in the denominator but not the numerator and not excluded.

**How 2OPMD differs:** The detective's gap detection is *exploratory*, not *protocol-based*. It finds gaps the graph reveals — missing timestamps, zero-edge clinical nodes, unexplained medication changes, diagnostic mysteries. These are structural gaps in the patient's story. HEDIS measures are *compliance* gaps — did the patient get their mammogram, their A1C check, their eye exam? Different question. Metriport asks "did we follow the protocol?" 2OPMD asks "what did we miss in the story?"

**Competitive risk:** Moderate for compliance-focused B2B customers (health plans, ACOs, risk adjustment). These customers *need* HEDIS scoring. 2OPMD does not implement HEDIS. Building it would be a major effort with no differentiation — HEDIS is a specification, not an insight.

**B2B opportunity:** Strong complement. Metriport provides the HEDIS compliance layer. 2OPMD provides the "what else?" layer. A care gap report says "this patient is overdue for a mammogram." The detective says "this patient's iron deficiency anemia has been unexplained for 18 months and the GI workup was never completed." One is regulatory. The other is clinical intelligence. Sell them together.

---

### Suspecting — Highest Overlap, Key Differentiator

Metriport's Suspecting feature automatically identifies patients with *undiagnosed or under-coded conditions* based on clinical evidence patterns. Two modes:

1. **Suspect:** Patient has clinical evidence (e.g., two fasting glucose >126 mg/dL) but no diagnosis code for diabetes
2. **Recapture:** Patient had a diagnosis in a prior year, not captured in the current year, with supporting evidence

Currently supports ~50 condition groups: heart failure, hypertension, CAD, diabetes, CKD, COPD, depression, dementia, morbid obesity, cirrhosis, various cancers, retinopathy, amputation, ostomy, etc.

Each suspect is a FHIR Condition with `verificationStatus: unconfirmed`, supporting evidence resources, and the clinical rules that triggered it.

**How 2OPMD differs:** This is the closest Metriport gets to what the detective does. But the implementation is fundamentally different:

| Dimension | Metriport Suspecting | 2OPMD Detective |
|-----------|---------------------|-----------------|
| **Detection method** | Rule-based: predefined clinical logic per condition group | Graph-based: connascence traversal + LLM reasoning |
| **Condition scope** | ~50 defined groups, must be explicitly implemented | Open-ended: finds whatever the graph reveals |
| **Evidence model** | FHIR resources as supporting evidence | Connascence edges with provenance, strength, and confounders |
| **Novelty** | Finds known unknowns (conditions in the ruleset that are missing) | Finds unknown unknowns (patterns the ruleset doesn't cover) |
| **Temporal reasoning** | Limited to "prior year" recapture logic | Full temporal connascence: gaps, sequences, impossible orderings |
| **Confounder awareness** | None documented | Explicit confounder edges and disambiguation |
| **Enrichment** | Static — rules fire once per analytics cycle | Cumulative — graph improves with every traversal |

**Competitive risk:** High for risk adjustment customers. Health plans doing HCC coding need exactly what Suspecting provides. 2OPMD's detective is overkill for "did we code the diabetes?"

**B2B opportunity:** The detective *subsumes* Suspecting but isn't constrained to it. Position the detective as the next tier: "Metriport tells you the patient probably has undiagnosed diabetes. 2OPMD tells you *why* the diabetes was missed — the A1C trend started 3 years ago, the PCP noted glucose concerns but never ordered confirmatory testing, and the specialist assumed the PCP was managing it. That's a confounder chain, not a missing code."

For risk adjustment: Metriport Suspecting is sufficient and cheaper. For clinical decision support: the detective is necessary. Different buyer, different price point.

---

### Data Analytics / Warehouse — No Overlap, Complementary Layer

Metriport pipes FHIR data into Snowflake, Redshift, or BigQuery via:
- **Managed:** Direct Snowflake Secure Data Sharing (zero-copy, near real-time)
- **Manual:** [Tuva data model](https://thetuvaproject.com/) (open-source healthcare analytics model)

Flat table schema (v100) covers all FHIR resource types with computed columns for easier querying.

**How 2OPMD differs:** 2OPMD's data model is a graph, not flat tables. Population analytics on a graph requires different tooling (graph queries, embedding-based cohort clustering, connascence pattern mining). 2OPMD doesn't have a warehouse integration story yet.

**B2B opportunity:** Metriport handles the "flat analytics" tier (how many patients have diabetes, what's our HEDIS compliance rate, what's our readmission rate). 2OPMD handles the "graph analytics" tier (which patients have unexplained comorbidity patterns, where are the treatment contradictions, which diagnostic arcs are incomplete). Different questions, same data, different shapes.

---

### Data Contribution — Obligation, Not Opportunity

If 2OPMD integrates Metriport, data contribution back to HIE networks is **mandatory**. Failure to comply = access revoked.

What 2OPMD could contribute:
- **Encounter resources** from detective sessions (a patient was "seen" by the system)
- **Condition resources** from detective findings (suspected diagnoses, diagnostic mysteries)
- **Observation resources** from gap analysis (identified care gaps, confounder assessments)

This is non-trivial engineering: the detective's output is narrative + graph, not FHIR resources. A PTV → FHIR serializer is needed. But the detective's findings *are* clinically meaningful data that other providers would benefit from — this is the rare case where the contribution requirement is also a product feature.

---

### Patient Monitoring — Trigger Layer for Detective

Real-time ADT notifications (admit/discharge/transfer) + pharmacy + lab alerts via webhook. Scheduled queries on configurable intervals.

**B2B opportunity:** ADT events become detective triggers. Patient admitted? Re-run the detective with new encounter context. Patient discharged? Run gap analysis against the discharge plan. This turns the detective from a pull-based tool (doctor requests investigation) into a push-based service (system alerts when something needs attention).

---

## Updated Competitive Summary

```
┌─────────────────────────┬───────────────┬──────────────┬─────────────────┐
│ Capability              │ Metriport     │ 2OPMD        │ Relationship    │
├─────────────────────────┼───────────────┼──────────────┼─────────────────┤
│ Data acquisition (HIE)  │ ███████████   │              │ Metriport only  │
│ C-CDA → FHIR            │ ███████████   │              │ Metriport only  │
│ FHIR normalization      │ ███████████   │ ███          │ Metriport leads │
│ AI Summary (brief)      │ ██████        │ ███████████  │ 2OPMD deeper    │
│ Care gaps (HEDIS)       │ ███████████   │              │ Metriport only  │
│ Suspecting (dx coding)  │ ████████      │ ███████████  │ 2OPMD deeper    │
│ Graph construction      │               │ ███████████  │ 2OPMD only      │
│ Knowledge graph (MKG)   │               │ ███████████  │ 2OPMD only      │
│ Diagnostic investigation│               │ ███████████  │ 2OPMD only      │
│ Opportunistic enrichment│               │ ███████████  │ 2OPMD only      │
│ Embedding navigation    │               │ ███████████  │ 2OPMD only      │
│ Population analytics    │ ██████████    │              │ Metriport only  │
│ Data warehouse piping   │ ██████████    │              │ Metriport only  │
│ EHR integrations        │ ███████████   │              │ Metriport only  │
│ Real-time monitoring    │ ████████      │              │ Metriport only  │
│ B2B API auth            │ ██████        │ ██████       │ Parity          │
└─────────────────────────┴───────────────┴──────────────┴─────────────────┘
```

---

## Bottom Line (Revised)

The original thesis holds: **Metriport is plumbing. 2OPMD is the building.** But Metriport is building a second floor on their plumbing (Suspecting, Care Gaps, AI Summaries, population analytics). That second floor competes with 2OPMD's ground floor on *compliance-grade* clinical intelligence.

The differentiation is depth:
- Metriport's analytics are **rule-based, protocol-driven, and compliance-focused** (HEDIS, HCC coding, risk adjustment)
- 2OPMD's detective is **graph-based, exploratory, and clinically-focused** (diagnostic mysteries, confounder chains, temporal reasoning)

For health plans doing risk adjustment → Metriport is sufficient.
For clinicians doing diagnostic reasoning → 2OPMD is necessary.
For customers who need both → integrate.

**Don't build the plumbing. Don't rebuild HEDIS. Build the graph deeper.** The graph is what Metriport cannot replicate because their data model is flat FHIR resources, not connascence-edged graphs with opportunistic enrichment.

The integration point remains a FHIR → PTV adapter — which is itself just another instance of opportunistic graph enrichment.

---

*Filed 2026-03-31. Updated 2026-04-01 with deep capability comparison.*
*Metriport is plumbing with a compliance analytics floor. The graph is the product.*
