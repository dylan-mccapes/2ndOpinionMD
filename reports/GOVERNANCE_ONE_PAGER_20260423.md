# 2ndOpinionMD — Governance One-Pager

**Context:** FORWARD / RISE longitudinal PRO study collaboration  
**Date:** April 2026  
**Audience:** Partner society leadership, IRB, data-governance reviewers

---

## 1) Architecture at a Glance

2ndOpinionMD is an **on-premise, air-gapped clinical reasoning platform** that pairs a Medical Knowledge Engine (MKE; **million+** RAG-indexed documents across 15+ ontologies, guidelines, and EHR-note corpora including MIMIC shards), the Ethos of Health (EoH) reasoning framework (30+ governance-first modules), and **PatientTimelineVision (PTV)** — a per-patient longitudinal graph.

- **Hardware (pilot):** Apple M2 Ultra + Intel i7 workstation with RTX-4090 (PortalNode prototype profile). Full multi-GPU PortalNodes require separate funding.
- **Models:** local `eoh-llama` tiers (3.2 routing, 8B workhorse, 70B synthesis); cloud LLM is optional and off by default for regulated workloads
- **Substrate:** PostgreSQL 16 + pgvector; FastAPI backend; React SPA; nginx reverse proxy
- **Provenance:** every graph mutation, model routing decision, and detective run is receipt-tracked (ProvenanceEngine)

**Partner-visible surface:** scoped B2B API (`/v1/mkg/*`) with key-based authentication and per-key rate limits. Patient identifiers never traverse this surface.

---

## 2) HIPAA Posture (Operational Today)

Privacy is a **layered architectural concern**, not a bolt-on. All eight layers below are implemented and running in the platform today; any partner cohort is processed through the same pipeline.

| # | Layer | Guarantee |
|---|-------|-----------|
| 1 | **Ingestion-time PII scrub** (pre-DB) | `ehr.patient_timeline` and `ehr.artifacts` rows are **scrubbed of direct identifiers before insert**. Raw source files are never retained after scrub + extraction. |
| 2 | **OGrE agent-driven scrub** | Opportunistic Graph Enrichment agents re-scan events during idle cycles; **any PII the 8B agent encounters is redacted with provenance** and the code index is re-synchronized. |
| 3 | **Query anonymization agent** | Every clinical query is converted to a categorical summary (e.g. `"symptom_query: cardiopulmonary_assessment adult"`) **before it reaches any log**. Non-blocking with a safe fallback. |
| 4 | **Encrypted logging at rest** | Fernet-encrypted, rotated, key-isolated (`log_encryption.key`). Logs are unreadable without the key; a decrypt utility is reserved for authorized audit. |
| 5 | **Security middleware** | Sensitive-path blocking (`/.env`, `/.git`), CORS allow-list, request logging with anonymized payloads only. |
| 6 | **Consent + audit trails** | `anonymization_consent` is set at session initialization. Chat-graph evictions are **soft-deleted** with `evicted_at` / `eviction_reason` for full audit reconstruction. |
| 7 | **Local-first inference** | All LLM inference runs locally through Ollama on the pilot on-prem stack (M2 Ultra + i7/RTX-4090) and scales to the PortalNode prototype profile as funding allows. **No patient data leaves the network** in the on-premise configuration. |
| 8 | **Provenance tracking** | PTV mutations, detective runs, chat references, and B2B usage are receipt-tracked. Every output is traceable via a `DerivationChain`. |

**Air-gapped operation** is the default posture for any partner pilot or longitudinal study. Cloud LLMs are disabled at deployment time for regulated cohorts.

**De-identification standard:** Safe Harbor by default (18 HIPAA identifiers), with optional Expert Determination review for partner-specific risk thresholds.

**Sub-processors:** none for the air-gapped configuration. The on-premise deployment is fully self-contained after initial model/corpus load.

**BAA:** 2ndOpinionMD will execute a Business Associate Agreement with any covered entity or research partner prior to handling identifiable PHI. The partner society itself, acting as a data steward, governs release of de-identified cohort data to the platform.

---

## 3) Non-Commercial Research Terms

For the FORWARD / RISE longitudinal study and comparable academic collaborations, 2ndOpinionMD agrees to the following default terms:

- **Non-commercial use only.** Graph artifacts, PTV outputs, and any derived indices produced under the study are used **solely for research and publication**, not for commercial product offerings, without a separately negotiated written agreement.
- **No model training on partner data** without explicit, study-specific written consent. Partner-supplied corpora are used for **inference, retrieval, and reasoning** only; they are not ingested into general training pipelines.
- **Cohort data residency.** Partner-supplied data remains on the pilot on-prem stack / PortalNode prototype (or partner-designated infrastructure) and is not copied off-premise.
- **Scoped access.** Partner investigators receive scoped B2B API keys (`mkg:read`, `mkg:evidence`) limited to the study cohort; key provisioning is logged and revocable.
- **Deletion on request.** On study conclusion or partner request, study-scoped artifacts (PTV graphs, embeddings, detective runs, chat graphs) are **purged on a defined timeline** (30 days default) with a cryptographic deletion receipt.
- **Intellectual-property boundary.** 2ndOpinionMD retains ownership of the platform, models, MKG, and EoH framework. Partners retain ownership of their source data and co-own derived research outputs per study agreement.

These terms are the starting point for a formal research-collaboration agreement; partner-specific amendments are expected.

---

## 4) Publication-First Commitment

This collaboration is explicitly **publication-first**. 2ndOpinionMD commits to:

- **Support partner publication priorities.** Primary study findings are published by the partner society (or joint authorship as agreed). 2ndOpinionMD will not publish overlapping primary findings ahead of the partner.
- **Methods transparency.** Platform methods, PTV schema, toolkit interfaces, and governance controls used in the study are documented for reviewer-facing methods sections. Relevant Modelfiles, harness specifications, and ingest pipelines are made available on request for method review under confidentiality.
- **Open reproducibility on non-patient artifacts.** Synthetic PTV graphs used in the study (e.g. the 5-patient exemplar set), harness questions, and scoring rubrics are shareable so external reviewers can replicate the evaluation **without partner PHI**.
- **Honest-uncertainty reporting.** Clinical outputs carry Uncertainty Carriers (posterior means + 90% credible intervals + evidence event IDs + method tag). Publications report both estimates and bands; we do not report point estimates without their associated uncertainty.
- **Reasonable embargo.** A standard publication embargo window (typically 6–12 months from study conclusion, per partner policy) is honored before any 2ndOpinionMD marketing, blog, or white-paper reuse of study findings.

---

## 5) Points of Contact

- **Technical / Engineering:** Dylan McCapes (2ndOpinionMD Engineering)
- **Clinical / Scientific:** Dr. Andras Hanyal, PharmMD
- **Governance / Compliance:** via the same engineering contact; BAA and DUA drafts provided on request

---

*This one-pager is a governance summary intended for partner review. It is not a legal instrument. Binding terms are set in the executed research-collaboration agreement, DUA, and BAA applicable to each study.*
