# REPORT — Meeting Prep: FORWARD / Kaleb Michaud, PhD

**Date:** 2026-04-21
**Meeting:** 2026-04-22 (tomorrow) — Dr. Kaleb Michaud (Director, FORWARD Databank; UNMC Rheumatology)
**Topic:** Longitudinal study on Patient-Reported Outcomes (PROs) using the 2ndOpinionMD platform
**Companion docs already in repo:**
- `docs/TIMELINE_UPLOAD_GUIDE_FORWARD.md` (already branded for Kaleb — upload endpoint, bearer token, graph query API)
- `docs/2OPMD_TECHNICAL_ARCHITECTURE.md` (full technical reference)
- `docs/VC_DECK_RISE_ONPREM_20260411.md` (PortalNode-01 + tiered model narrative)
- `LLAMA_ROSTER.md` (eoh-llama model fleet)
- `REPORT_PATIENT_TIMELINE_VISION_ARCHITECTURE_20260301.md` (PTV internals)
- `receipts/PROPOSAL_JOURNAL_GRAPH_PSYCHOLOGICAL_STATE_20260401.md` (the journal/PRO substrate)

---

## 1. Elevator Speech (60–90 seconds)

> 2ndOpinionMD is a local-first clinical reasoning platform built around a living patient graph. Every patient has a **PatientTimelineVision** — a typed, connascence-edged graph of their longitudinal clinical events, derived from EHR PDFs, FHIR bundles, or structured exports. Running *underneath* that graph is a second layer we call the **journal graph**, which is where patient-reported outcomes, mood, sleep, pain perception, adherence, stress, and hope live. It already carries a `patient_reported_outcomes` JSON column on every journal entry; we have a working PROMIS-style payload fixture; and the decay, trend, and PTV-anchoring logic is specified end-to-end.
>
> The reasoning engine on top is the **Ethos of Health** — a modular, governance-gated framework of 30+ clinical reasoning modules (terrain state, flare detection, escalation, care planning, adversarial governance) that runs either in the cloud against GPT-4.1 or entirely air-gapped on our **eoh-llama** models (3.2 / 8B / 70B) via Ollama. Against the Medical Knowledge Graph — 500K+ RAG-indexed documents spanning SNOMED, ICD-10/11, HPO, LOINC, RxNorm, NICE, VA/DoD, WHO, CDC, and others — eoh-llama can retrieve guideline evidence on-premise with no API egress.
>
> The whole stack is designed to live inside a FORWARD data center on a single 4U appliance — **PortalNode-01**, ~$10.5k BOM, four RTX 4090s, air-gapped after model download. Your PRO data never leaves the building, our models never touch the open internet, and every AI decision is receipt-tracked via our open-source **ProvenanceEngine**.
>
> For this study, the proposal is straightforward: we stand up a **study-specific graph** — same OGrE (Opportunistic Graph Enrichment) mechanics as PTV, but with instrument-aware nodes for PROMIS, HAQ, RAPID3, PGA, pain VAS, whatever FORWARD is administering — and we let the 8B workhorse traverse, enrich, and correlate those PRO nodes against the clinical events, trends, and guideline retrievals in the background. What you get out is auditable longitudinal structure on your own hardware, in your own data center, with every inference receipted.

---

## 2. Where PROs Fit in the Existing Architecture (no hand-waving)

We are not building a PRO pipeline from scratch — we are **pointing the existing substrate at FORWARD’s instruments**.

| Layer | What already exists | What PROs plug into |
|-------|---------------------|---------------------|
| **Timeline ingest** | `POST /api/timeline/{patient_id}/infer` — accepts PDF or structured JSON; PII-scrubbed; heuristic pre-scan; 8B extraction; connascence edge inference | Add `event_type: "pro"` (or `"questionnaire"`) with instrument + score + domain in `structured` |
| **Graph substrate** | `PatientTimelineVision` — typed events (`lab`, `medication`, `diagnosis`, `symptom`, `flare`, `note`, …) with named connascence edges (`temporal`, `diagnostic`, `treatment`, `lab_trend`, `causal_*`, `co_variation`) | PROs become first-class nodes; `temporal` + `co_variation` edges auto-drawn against labs, flares, med changes |
| **Semantic retrieval** | `patient_graph_chart` — 384-d sentence-transformer embeddings per event, HNSW-indexed | PRO item text + domain goes into the same embedding space; free-text patient queries retrieve the right instrument responses |
| **PRO data model** | `journal_entries.patient_reported_outcomes` JSON column (Alembic migration `006_add_journal_patient_reported_outcomes.py`, shipped 2026-04-17) + `promis_style_stub.json` fixture | We already store `{instrument, domain, t_score, raw_score, note}`; trivial to expand to full FORWARD instrument panels |
| **Journal graph (proposal filed 2026-04-01)** | 8 psych dimensions (mood, stress, sleep, pain, energy, social, adherence, hope), slower decay than chat, `TrendLine` with slope/variance, auto co-variation edges to PTV | This is the right home for narrative PRO free-text + computed trend summaries; PROMIS domains map cleanly onto these dimensions |
| **Opportunistic Graph Enrichment (OGrE)** | `server/eoh/graph_enrichment.py` — 8B scans low-confidence nodes in idle cycles, proposes edges above 0.7 confidence, every mutation is provenance-tracked | For PROs: background agent can propose edges like “stress-domain PROMIS T-score rose 2 weeks before documented flare in 4/5 instances, coupling 0.72” as a typed `co_variation` connascence edge |
| **Guideline retrieval** | `public.rag_corpus` (500K+ docs) — NICE, VA/DoD, WHO, CDC, ACR/EULAR diagnostic rules — all embedded, all local, all retrievable by eoh-llama on the same box | 8B can cite ACR/EULAR guidance for a detected PRO-flare signature without an external API call |
| **Reasoning** | Ethos of Health modules: M13 Trend & Prognostic, M20 Early Warning, M5 PSI (psychosomatic index), M68 Inflammatory Capacity Model, M63/M67 governance (DerivationChain + adversarial falsification) | PRO trends are *designed* to feed M13 and M5; M68 is explicitly capacity-aware (allostatic headroom), which maps onto PROMIS fatigue/physical-function |
| **Audit** | ProvenanceEngine (PyPI, MIT-licensed) — Lorenz-attractor graph lifecycle scoring; every node gets retain/review/evict classification with confidence | Every PRO-derived edge is receipt-tracked by model, confidence, and reason — necessary for publication-grade reproducibility |

**Key line for Kaleb:** *FORWARD doesn’t have to choose between “use their patient graph” and “keep our longitudinal PRO methodology.” The graph we stand up for this study is **study-specific** — same OGrE mechanics as PTV, but instrument-aware and scoped to whatever FORWARD is collecting.*

---

## 3. Two Possible Study Architectures

### Option A — PTV with PROs as journal/questionnaire nodes (minimum disruption)

- Patients already in FORWARD upload (or FORWARD exports) their longitudinal EHR.
- PTV ingests it → typed clinical event graph.
- PRO responses are added as `pro` nodes with instrument metadata.
- OGrE draws `co_variation` edges between PRO trends and clinical events (flares, med changes, lab shifts).
- Output: per-patient graph + longitudinal cohort-level correlation statistics.

**Pros:** Fastest to start. Reuses every existing endpoint. The upload guide we already sent you works today.
**Cons:** PTV’s event model was designed for clinical events. Instrument-level reasoning (item-response theory, ceiling effects, MCID) is shoehorned.

### Option B — Study-specific graph on the same OGrE substrate (recommended)

- A parallel graph schema tuned for PRO instruments: nodes are `InstrumentAdministration`, edges are `responded_to`, `maps_to_domain`, `t_score_regresses`, `mcid_crossed`, `co_variates_with_clinical_event`.
- Same OGrE loop — 8B scans and proposes typed edges in idle cycles.
- Shares the **embedding space** and the **Medical Knowledge Graph** with PTV (so a rheumatologist’s NICE RA guideline is retrievable by the PRO graph too).
- Shares the **PortalNode** infrastructure.

**Pros:** FORWARD gets a graph whose ontology matches FORWARD’s methodology. Still benefits from every primitive we’ve already built — chart index, OGrE, provenance, guideline retrieval, governance modules.
**Cons:** ~2–3 weeks of schema work before first ingest. Worth it for a multi-year longitudinal study.

**Recommendation to Kaleb:** start in Option A for the pilot (we can have a live graph on a sample FORWARD patient in under an hour today), and move to Option B once the instrument panel and outcome definitions are frozen.

---

## 4. PortalNode Data Center Infrastructure — the Physical Story

Kaleb will almost certainly ask *where the data lives*. This is the whole reason the VC deck exists, and it is why we already have the RISE on-prem 8B live today.

| Component | Specification |
|-----------|--------------|
| Chassis | Rosewill RSV-L4500U 4U rack-mount (standard 19") |
| CPU | Intel Xeon w5-2465X (16C/32T, 112 PCIe 5.0 lanes) |
| RAM | 128 GB DDR5-4800 ECC (4×32 GB) |
| GPUs | **4× NVIDIA RTX 4090 (96 GB VRAM total)** |
| Storage | 2 TB NVMe (OS/logs) + 8 TB NVMe (models + graph) |
| PSU | Corsair AX1600i (1600W, 80+ Titanium) |
| Network | Dual 10 GbE + IPMI management |
| OS | Ubuntu 24.04 LTS + Docker + Ollama + FastAPI |
| Power | ~2.2 kW under full load, single 30A circuit |
| BOM | **~$10,500** (one-time) |

**GPU allocation (always-on / on-demand):**
- **GPU 0** — `eoh-llama 3.2` (~2 GB) + `eoh-llama 8B` (~5 GB) share one 4090. Routing, triage, and ~82% of traffic.
- **GPUs 1+2** — `eoh-llama 70B` q4_K_M tensor-parallel across 48 GB. Deep synthesis, final flare prediction, probe-gap reasoning. ~8% of traffic.
- **GPU 3** — hot spare / 70B burst capacity.

**Live today:** 8B q8_0 on a single 4090 at RISE on-prem, bearer-token-protected upload endpoint, benchmarked on a 4,223-page Kaiser record (~2.1 hours end-to-end, 3,556 events extracted).

**After model download, the appliance requires zero internet connectivity.** All inference, retrieval, graph mutation, and audit logging is local. This is the single most important sentence in the pitch for a registry holding PHI — and FORWARD is, of course, a registry holding PHI.

---

## 5. Likely Questions — Talking Points

Organized roughly by who asks them first. Kaleb runs a registry with 50,000+ patients, co-leads VARA and RAIN, has built RISE. He will ask sharper questions than a typical investor.

### Q1. "How do you ingest FORWARD data without us rebuilding our export pipeline?"
- Two paths live today: **PDF** (any size, Cloudflare fallback for >100 MB) and **structured JSON** (bare array or `{events: [...]}` wrapper).
- JSON event shape is forgiving: `ts`, `event_type`, `source`, `text`, `structured`, `meta`. Already documented in `TIMELINE_UPLOAD_GUIDE_FORWARD.md`.
- Anything FORWARD can serialize — PROMIS domain scores, HAQ, RAPID3, med lists, visit dates, flare flags — maps 1:1.
- Batches auto-size to the 8B context window (~48 k chars per batch). No upstream pre-chunking needed from FORWARD.

### Q2. "What models are you running and why should I trust them for PROs?"
- **Not a frontier model.** The production workhorse is a 3.1 8B q8_0 with 32 k context, parameterized deterministically (temperature 0.2, top_p 0.9), system-prompted with the entire EoH framework (~4 k tokens).
- **We do not expect the 8B to diagnose.** Its job is to normalize, classify, propose edges, and retrieve. Final synthesis is either GPT-4.1 (cloud mode) or 70B (on-prem, planned).
- PROs are structured data to begin with — they barely need an LLM, but the LLM is what connects a PROMIS fatigue T-score to the patient narrative four days earlier.
- Benchmark: full 8-round EoHD pipeline runs in ~9.5 min on Lucifer dev box (4050), ~1.5–2 min on the 4090 production node.

### Q3. "How do you handle PHI? What’s the privacy story?"
Eight layers, auditable top to bottom:
1. **PII scrubbing** on every upload (MRN, SSN, DOB, phones, emails, addresses, detected names) — happens *before* LLM inference and *again* on LLM output.
2. **Query anonymization agent** (`server/api/anon_query_agent.py`) — 2-second timeout; falls back to category-only logging if it fails.
3. **Encrypted logging** (Fernet at rest, rotating 10 MB files, separate key file).
4. **Security middleware** — blocks `/.env`, `/.git`, config paths.
5. **Chat graph audit trail** — soft-delete with `evicted_at` + `eviction_reason`; nothing is silently dropped.
6. **Anonymization consent tracking** on `patient_timelines`.
7. **B2B scoped API keys** (`b2b.api_keys` schema) — per-key rate limits, scoped permissions (`mkg:read`, `ptv:extract`, etc).
8. **Local-first inference** — on PortalNode, no patient data leaves the network after model download.

### Q4. "Is this a graph database? If so, which one?"
- **PostgreSQL + pgvector**, not Neo4j.
- Per-patient JSONB graph in `ehr.patient_graph_vision` (whole graph in one row for single-patient-per-query workloads).
- Per-event embeddings in `ehr.patient_graph_chart` (384-d, HNSW).
- Readiness gate in `ehr.patient_graph_status` (`is_ready`, `event_count`, `edge_count`, `ts_coverage`).
- **Why:** clinicians and registries run Postgres. Nobody wants to operationalize Neo4j inside a hospital data center. pgvector + HNSW gives us sub-ms semantic search without a new RDBMS.

### Q5. "What is OGrE? Opportunistic Graph Enrichment — I want details."
- Background job on the 8B model. When the GPU is idle, it picks low-confidence nodes and scans their 2-hop neighborhoods.
- If it finds a plausible edge above **0.7 confidence**, it proposes the mutation. The mutation is applied with full provenance: `model`, `confidence`, `reason`.
- Each proposed edge can be **escalated to the 70B** if the 8B flags the pattern as high-stakes (e.g., a causal claim).
- 24/7. The graph gets *richer* the longer it sits on the appliance. This is the difference between a dataset and a living graph.
- For PROs specifically, the overnight OGrE pass can compute rolling instrument-to-clinical-event correlations across an entire cohort and write those correlations as typed edges the next morning.

### Q6. "Your VC deck mentions RISE. Where does FORWARD fit?"
- RISE is a different partnership track — **live clinical infrastructure** at ACR, 3.9M patients, focused on flare detection in RA.
- FORWARD is **longitudinal observational**, PRO-rich, 50K+ patients, different clinical questions (pharmacoepidemiology, mortality, DMARD adherence, smartphone outcomes — all your published interests).
- The **same appliance** serves both. Different graphs on the same hardware. The MKG and guideline retrieval are shared; the patient graphs are scoped.
- Q4 2026 milestone in the VC deck explicitly calls out "approach additional registries (CorEvitas, FORWARD)" — this meeting is ahead of schedule by design.

### Q7. "What happens when your 8B hallucinates a PRO correlation?"
- **Nothing gets written to the graph without a provenance receipt** — `model`, `confidence`, `proposed_at`, `reason`.
- Every OGrE mutation is reviewable and reversible.
- The **ARGL module (M67 — Adversarial Reasoning Governance Layer)** mandates falsification: every claim must be checkable against a counter-claim derived from graph evidence. If the 8B proposes "stress predicts flare," M67 requires it to also surface the instances where stress rose and no flare followed.
- **DerivationChain (M63)** means every output traces back to its inputs. No black-box numbers.
- This is not theoretical — it is live code in `server/eoh/` today.

### Q8. "Can you handle validated instrument metadata? PROMIS, HAQ-II, RAPID3, PGA, MDHAQ?"
- Yes. Instrument is a field on the PRO node (`structured.instrument`, `structured.domain`, `structured.t_score`, `structured.raw_score`).
- The Medical Knowledge Graph already carries ACR/EULAR diagnostic rules, NICE, VA/DoD guidelines — adding instrument crosswalks is a `mk/` module, same pattern as SNOMED and LOINC.
- Plan: one `mk/XX_pro_instruments.mk` module that ingests instrument definitions + normative T-score tables + MCID thresholds into the `ontology` schema. ~2 days of work.

### Q9. "What do you want from FORWARD and what do we get?"
**What we want:**
- A de-identified longitudinal cohort slice (sample N=100–500 patients to start) with clinical events + PRO administrations.
- Agreement on instrument panel and outcome definitions.
- Governance/IRB path (we have a template from the RISE proposal).
- Andras Perl is our clinical advisor; Ted Mikuls / VARA overlap is a conversation-starter if relevant.

**What FORWARD gets:**
- A study-specific graph running on an appliance in your data center (air-gapped after setup).
- Free use of the MKG + guideline retrieval for that cohort.
- Receipt-grade provenance on every derived correlation — publication-ready audit trail.
- Open-source ProvenanceEngine (MIT) so the methodology is independently reproducible.
- Co-authorship on the methods paper; FORWARD retains all data and publication authority.

### Q10. "What if we just want to evaluate you without deploying hardware?"
- Cloud evaluation mode is fully supported (GPT-4o / GPT-4.1 tiers via OpenAI, same EoH framework, same PTV pipeline).
- Minimum viable test: upload one de-identified patient’s EHR JSON to the bearer-token-protected endpoint; get back a graph, snapshot, topology, and a structured answer to a free-text question — all in ~3–8 minutes.
- Documented in `docs/TIMELINE_UPLOAD_GUIDE_FORWARD.md` Section 6 (*FORWARD Convenience Endpoint*).
- Production PortalNode deployment is the Q2/Q3 milestone, not the evaluation gate.

### Q11. "How does this compare to Metriport / Datavant / Redox / FHIR ingestion tools?"
- Those products **move** data. We **reason** over it.
- Datavant actually appears upstream of us in the RISE pipeline (tokenization/de-identification). Complementary, not competitive.
- Closest analog is probably a rheumatology-specific version of an EHR-overlay AI (Abridge, Nabla) — but nobody else is operating an on-prem, receipt-graded, graph-native, local-LLM stack with a native PRO-aware journal layer.
- Competitive writeup exists: `reports/REPORT_METRIPORT_COMPETITIVE_ANALYSIS_20260331.md`.

### Q12. "Can a patient see their own PRO-derived trend line?"
- Yes — by design. The React SPA has a `/journal` patient view (`frontend/src/pages/`), an `/eohd` detective view for clinicians, and the journal graph was *proposed on April 1, 2026* specifically to surface dimension trends (mood, stress, sleep, pain, adherence, hope) to both patient and clinician.
- **Paying attention is our form of love** — that is literally the repo’s operating tagline and it is why the journal/PRO substrate exists.

### Q13. "What’s the honest state of the code? What’s shipped vs. specified?"

**Shipped and in production today:**
- PDF + JSON timeline upload endpoint, PII scrubbing, heuristic pre-scan, 8B extraction, graph construction, graph query API (topology, negative-space, gaps, traverse, ask).
- MKG (500K+ docs, 20+ sources) with hybrid retrieval (BM25 + ANN + RRF fusion).
- EoH routing + EoH Detective streaming (SSE).
- Chat Graph (bounded memory with decay, PTV anchoring, soft-delete audit).
- `journal_entries.patient_reported_outcomes` JSON column (Alembic 006).
- PortalNode-01 spec complete; 8B deployed on RISE on-prem (single 4090).
- ProvenanceEngine published to PyPI under MIT.
- Encrypted logging, query anonymization agent, B2B API key infrastructure.

**Specified, partially implemented:**
- `journal_graph` full schema + trend engine + PTV co-variation edges (proposal filed 2026-04-01; SQL schema drafted; integration with EoHD specified).
- 70B tensor-parallel deployment (Modelfile not yet cut; 2x4090 hardware not yet racked).
- Study-specific graph ontology for PROs (this meeting will inform it).

**We will not pretend otherwise.** If Kaleb asks "is the PRO study graph running today?" the honest answer is: the substrate, endpoints, ingestion, 8B extraction, OGrE, and PRO storage column are all live. The PRO-specific node schema and the cohort-scale cross-patient correlation loop are the next ~2–3 weeks of work once we know FORWARD’s instrument panel.

---

## 6. One-Slide Summary (if you need to draw it on a napkin)

```
          ┌──────────────────────────────────────────────────┐
          │   FORWARD DATA CENTER  · PortalNode-01 · 4U      │
          │   4× RTX 4090 · 128 GB ECC · air-gapped          │
          │                                                  │
          │   ┌──────────────┐   ┌────────────────────────┐  │
          │   │ eoh-llama 8B │   │    eoh-llama 70B       │  │
          │   │ always-on    │   │    on-demand, tensor-// │  │
          │   │ OGrE agent   │   │    final synthesis      │  │
          │   └─────┬────────┘   └────────┬────────────────┘  │
          │         │                     │                   │
          │         └──────────┬──────────┘                   │
          │                    ▼                              │
          │   ┌─────────────────────────────────────────┐     │
          │   │  POSTGRES + PGVECTOR                    │     │
          │   │  ─────────────────────────────────────  │     │
          │   │  MKG (500K docs, 20+ ontologies)        │     │
          │   │  PTV (clinical events + connascence)    │     │
          │   │  Journal graph (8 PRO dimensions)       │     │
          │   │  Study-specific PRO graph (per FORWARD) │     │
          │   │  Chat graph (bounded memory)            │     │
          │   │  ProvenanceEngine (receipts)            │     │
          │   └─────────────────────────────────────────┘     │
          │                                                   │
          │   Patient data never leaves the building.         │
          │   Every inference has a receipt.                  │
          └───────────────────────────────────────────────────┘
```

---

## 7. What to Say First (the 30-second version)

> Kaleb, you already know the clinical problem — you wrote the papers. We built the infrastructure to let you instrument it at scale without sending a single PRO response off-premise. We have a live upload endpoint, a typed patient graph, an on-prem 8B doing background enrichment, a 70B on deck for synthesis, and a $10.5k appliance that drops into your data center. The journal graph we designed in April already has a patient-reported-outcomes column shipped. Tell us what instruments FORWARD is administering and what outcome you want correlated, and we can show you a graph on a real cohort slice this quarter.

---

## 8. If He Pushes on Funding / Timeline

The VC deck (`docs/VC_DECK_RISE_ONPREM_20260411.md`) frames the **$500k seed** milestones:
- Q2 2026 — PortalNode-01 deployed, RISE proposal submitted.
- Q3 2026 — First flare detection results on de-identified RISE data.
- Q4 2026 — Publication-ready study, approach **CorEvitas, FORWARD**.
- Q1 2027 — Series A readiness.

This meeting is Kaleb giving us the opportunity to pull FORWARD forward by one quarter. Frame the ask accordingly — a small pilot now, a formal study scoped with FORWARD’s governance, full deployment alongside the Series A milestone.

---

## 9. Who to Name-Drop (and in what order)

1. **Andras Perl** — clinical advisor; rheumatology/immunology/metabolic; UC Davis; overlaps with Kaleb’s network. He was on a call last night; Kaleb will recognize the credibility.
2. **Nate Roberts** — co-founder, RISE relationship, registry-side business development.
3. **Dylan McCapes** — CTO, built the stack end-to-end, author of ProvenanceEngine on PyPI. (That’s you.)
4. **RISE (ACR)** — live partner; proof we can land a registry.
5. **Ted Mikuls / VARA** — if the conversation touches VA research or RA registries, Kaleb has collaborated with Ted; worth surfacing as a potential cross-registry methods conversation.

---

## 10. What NOT to Oversell

- **Do not** claim a 70B is running on our production stack today. It is specified, hardware is in the BOM, Modelfile is planned. 8B is what’s live.
- **Do not** claim the journal graph + trend engine is shipped. It is specified (2026-04-01), SQL schema is drafted, integration is laid out end-to-end — but the trend/slope computation and the UI dashboard are ~10 working days of focused work.
- **Do not** promise IRB timelines. We have a template, not a filing.
- **Do** claim everything in `docs/TIMELINE_UPLOAD_GUIDE_FORWARD.md` — that document is already prepared for Kaleb, was written against working endpoints, and any line in it can be demo’d on a call.

---

*Prepared 2026-04-21 for the 2026-04-22 FORWARD meeting. Report is non-executable; it summarizes live code, deployed infrastructure, and filed proposals. All claims are traceable to specific repo files cited above.*

---

## Appendix A (added 2026-04-22) — Cross-reference with Andras's pre-call packet

Three additional PDFs have been checked into the workspace root (`01_agenda_sent_to_kaleb.pdf`, `2OPMD_Kaleb_Prep_April22_2026.pdf`, `2OPMD_Kaleb_Reference_for_Dylan.pdf`). They change nothing architecturally but **sharpen the positioning, narrow the first paper's scope, and reset a few expectations** that §1–§10 above did not fully reflect. This appendix is the delta.

### A.1 Summary of the three PDFs

**1. `01_agenda_sent_to_kaleb.pdf` — the external-facing agenda Andras already sent**

- **Duration:** 30 minutes.
- **Context sent in advance:** (a) *Uncertainty Carriers* paper on SSRN (abstract **6554940**) attached, framing governance: mandatory uncertainty carriers, glass-box derivation chains, "suppressing diagnostic uncertainty in CDS is a patient-safety failure"; (b) **PRO-based flare proxy framework** designed around FORWARD's data model — longitudinal HAQ, pain VAS, patient global assessment, treatment timestamps from semi-annual questionnaires.
- **Research question (locked):** *"Can longitudinal PRO trajectories in FORWARD be used to develop a probabilistic flare-risk stratification model that preserves uncertainty for CDS?"* Positioned as the **governance extension of Mollard et al. 2026** — "we are not predicting flares; we are stratifying risk with calibrated confidence intervals and mandatory uncertainty carriers."
- **Two decisions to align on:** (i) disease focus — **RA first** (largest FORWARD cohort; strongest PRO instruments) vs. SLE (higher unmet need); (ii) flare definition — **PRO-based composite**: meaningful worsening in ≥ 2 domains relative to each patient's own trajectory, anchored to a treatment escalation or documented behavior change.
- **Data access ask:** scope a first data pull; prefer **anonymized data path**; both UC Davis and UNMC are SMART IRB members as backstop.
- **Publication plan:**
  - **Paper 1 (perspective, near-term)** — *"Mandatory Uncertainty Carriers in Rheumatic Disease CDS: A Governance Framework"* (SSRN adaptation). Targets: *Arthritis & Rheumatology* or *Annals of the Rheumatic Diseases*. Submittable **summer 2026**.
  - **Paper 2 (validation, primary)** — FORWARD analysis; first author **Hangyal**, senior author **Michaud**; target *Arthritis Care & Research*; submission **Q1 2027**.
- **Asks to close the meeting:** day-to-day data contact name, FORWARD internal-review process, standard DUA template to review in parallel.

**2. `2OPMD_Kaleb_Prep_April22_2026.pdf` — Andras-only pre-call prep** (`Confidential | Andras Only`, explicitly "do not send to Kaleb")

- **Lp(a) 60-second demo** as the MKE tangibility shot. Setup: normal LDL 98, Lp(a) 220 nmol/L; MKE surfaces the discordance with an uncertainty carrier ("Lp(a)-driven residual ASCVD risk elevated despite statin-controlled LDL — Confidence: moderate — Basis: Lp(a) > 150 nmol/L, no prior ASCVD event, no PCSK9i"). FORWARD relevance: in RA, Lp(a) is often elevated independent of traditional CV factors; layered with HAQ/CRP trajectories → a paper.
- **DUA signatory — three options, Option B is lead:**
  - **A. UC Davis affiliation (slow backstop)** — only if Kaleb requires institutional cover.
  - **B. Anonymized data / Kaleb's discretion (lead path)** — UNMC's FORWARD DUA for anonymized datasets signed by Kaleb (PI) and Andras (receiving investigator); **2OPMD LLC as receiving entity; Andras as PI**. Ask: "Can you share UNMC's standard DUA template for anonymized dataset access?"
  - **C. Independent researcher agreement** — less likely at FORWARD; worth confirming.
- **Epic answer (if asked):** SMART-on-FHIR, FHIR R4, app launches inside the Epic workflow; not at Connection Hub listing stage yet (that needs a live customer connection); **Connection Hub = $500/yr** (old App Orchard revenue share is gone), not a cost barrier; integration is weeks once a deployment partner exists — *research validation is the bottleneck, not the integration*.
- **Quick-call map** (likely question → anchor): MKE → Lp(a) demo; DUA → Option B; Epic → SMART-on-FHIR; first analysis → RA + HAQ + pain VAS + treatment timestamps + flare risk stratification with UCs; what's needed → DUA template + variable list + patient-subset definition.

**3. `2OPMD_Kaleb_Reference_for_Dylan.pdf` — vocabulary + Mollard positioning**

- **Part 1 — Acronym cheat sheet.** Salient items:
  - FORWARD PRO instruments: **HAQ / HAQ-II (MCID 0.22)**, **RADAI**, **PAS-II**, **VAS pain (MCID 20 / 100)**, EQ-5D, SF-36, RDCI. **DAS28 is NOT in FORWARD** (clinician-measured).
  - Cohort sizes: **RA 35–40 K in FORWARD** (largest), **SLE 5 K+**. JRA is Kaleb's own diagnosis (age 3).
  - Adjacent registries: **RISE** (ACR, EHR-based, already invited us), **CorEvitas** (ex-CORRONA, pharma), **RAIN** (Kaleb's UNMC db), **VARA** (VA RA), **SLICC**, **AMP RA/SLE** (open-access via ImmPort), **UK Biobank**, **BioMe**.
  - Process: SMART IRB covers UC Davis + UNMC; UC Davis uses IRBNet.
  - Our vocabulary to use verbatim: **CDS** (not "diagnostic"), **UC** = Uncertainty Carrier, **MKG / MKE**.
  - Lp(a) demo: **> 150 nmol/L = elevated residual CV risk**; 2026 ACC/AHA class I.
  - Funding doors: **NIAMS** is our grant home; **R43 = SBIR Phase I**; **RRF** and **ANRF** as non-NIH.
  - Journal targets (to reuse Andras's words): *Arthritis Care & Research* (Paper 2), *Annals of the Rheumatic Diseases* (aspirational), *Arthritis & Rheumatology*.
- **Part 2 — Mollard et al. 2026 (ACR Open Rheumatology).** Kaleb likely **senior/corresponding**. Passive smartphone data + app-based PROs → behavioral signatures associated with RA flares. Predecessor: 2022 FORWARD smartphone pilot (**PMC9188241**, 446 participants), retention **78 % at 6 mo / 64 % at 1 yr**. **Kaleb is not a deep-learning researcher — methodological ML only (LASSO, mixed-effects).** Unknown: exact sample size, features, model class, effect sizes, flare operationalization → **do not fabricate**. Safe line: *"Your Mollard paper established that behavioral signatures in FORWARD's smartphone data track flares. What's missing between that and clinical deployment is the governance layer — uncertainty carriers, glass-box derivation, CDS-compliant output. You built the input. We're proposing the output wrapper."* Pivot question back to him if he goes deep: *"Remind me which signal you found most predictive — I want to make sure the validation framework handles that one cleanly."*
- **Ceiling reminder (critical — changes my study proposal):** **FORWARD does not collect labs, imaging, biosamples, or -omics.** The ceiling of available data is **PRO trajectories + treatment timestamps + behavioral signals from smartphones**. Every architecture claim must respect this.

### A.2 What this changes vs. §1–§10 above

1. **Scope of the first FORWARD paper is narrower than my §6 menu suggested.** It's specifically a **PRO-based probabilistic flare-risk stratifier** with uncertainty carriers — an extension of Mollard 2026 into governance. Keep my broader study proposal (`STUDY_PROPOSAL_LONGITUDINAL_GRAPH_COMPARISON_*`) as the umbrella; present the FORWARD paper as its first deliverable.
2. **Labs / LOINC / imaging are not FORWARD signals.** My proposal's LOINC-trajectory hypotheses (H1 for lab biomarkers) apply to RISE / CorEvitas / AMP, *not* FORWARD. For FORWARD, collapse to **HAQ-II, pain VAS, patient-global VAS, RADAI or PAS-II, treatment timestamps**, plus smartphone-behavioral signals if the Mollard substudy is included.
3. **Flare = PRO composite, not lab-driven.** Replace "EoH flare detector emission" language (graph-generic) with **"worsening ≥ 2 PRO domains relative to each patient's own trajectory, anchored to treatment escalation or documented behavior change"** when speaking about FORWARD specifically.
4. **DUA path is pre-chosen.** 2OPMD LLC as receiving entity, Andras as PI, anonymized dataset track via Kaleb. UC Davis is the backstop. Do not open with the UC Davis path.
5. **Lp(a) demo is the tangibility shot**, not a FORWARD analysis proposal (FORWARD lacks labs). Keep it cleanly separate: "Lp(a) is how we make the MKE concrete in 60 seconds; FORWARD analysis is strictly PRO-based."
6. **Kaleb's ML is methodological (LASSO, mixed-effects).** Don't lead with transformer graphs or frontier ML. Lead with uncertainty carriers, glass-box derivation, calibration — things aligned with his methods.
7. **Publication asks are pre-structured.** Don't negotiate authorship on the call; it's already proposed (Paper 2: Hangyal first, Michaud senior). Our job is to confirm the frame, not re-open it.
8. **Dylan should not assert Mollard specifics.** If the Mollard paper comes up, use the safe line above or pivot back to Kaleb.

### A.3 Concise responses — extension of §6

The following are tight, one-to-three-sentence answers optimized for the questions actually anticipated in the three PDFs. They supplement (do not replace) §6.

| # | Question / cue | Concise response |
|---|---|---|
| A1 | *"Remind me what the MKE does."* | "It holds discordant evidence side-by-side and emits a probability band with an uncertainty carrier — the basis for the output is inline, so clinicians see the reasoning, not just a number. The Lp(a) case makes it tangible: normal LDL, Lp(a) 220 nmol/L, MKE surfaces the residual-risk discordance with a moderate-confidence band and the basis line." |
| A2 | *"RA or SLE first?"* | "RA first. Largest FORWARD cohort, strongest PRO instrument base (HAQ-II, pain VAS, PAS-II), and the Mollard signal is RA. SLE becomes Paper 3." |
| A3 | *"How would you define a flare in FORWARD?"* | "PRO-based composite: meaningful worsening in two or more domains relative to the patient's own trajectory, anchored to a treatment escalation or documented behavior change. MCID-anchored thresholds — HAQ-II ≥ 0.22, pain VAS ≥ 20/100." |
| A4 | *"Who signs the DUA on your end?"* | "2OPMD LLC as the receiving organization, I sign as principal investigator. We're pursuing UC Davis affiliation as a parallel backstop, but we'd rather not wait on that if the anonymized path is available. Can you share your standard DUA template so we can review in parallel?" |
| A5 | *"What level of de-identification does the anonymized dataset carry?"* | "That's exactly what we want to scope with you today — the de-id level, the patient subset, the time window, and the variable list for a first pull. Whatever de-id level you can provide, we'll build to." |
| A6 | *"Does this work with Epic?"* | "Yes — SMART-on-FHIR, FHIR R4, launches inside the workflow. Connection Hub listing is $500/yr and we'll do it after we have a deployment partner. The research validation is the bottleneck, not the integration — which is why this collaboration matters." |
| A7 | *"What do you need from us to start?"* | "Three things: DUA template so we can review in parallel, scope for the first data pull (variables, patient subset, time window), and your day-to-day contact for the data request." |
| A8 | *"What's the first analysis look like?"* | "RA cohort, HAQ-II + pain VAS + patient-global VAS + treatment timestamps over time. PRO-composite flare definition. Probabilistic risk stratification with calibrated confidence bands and mandatory uncertainty carriers. Target: Paper 2 to *Arthritis Care & Research*, Q1 2027 submission." |
| A9 | *"How does this relate to the Mollard paper?"* | "Your Mollard paper established that behavioral signatures in FORWARD's smartphone data track flares — you built the input layer. What's missing between that and clinical deployment is the governance layer: uncertainty carriers, glass-box derivation, CDS-compliant output. We're proposing the output wrapper on top of your input." |
| A10 | *"Which smartphone signal was most predictive in Mollard?"* | "Remind me which signal you found most predictive — I want to make sure our validation framework handles that one cleanly." *(Pivot back to Kaleb. Do not guess.)* |
| A11 | *"What ML will you use?"* | "Methodological, not deep. Mixed-effects for the longitudinal PRO trajectories, LASSO or elastic-net for variable selection, isotonic or Platt calibration, and the uncertainty carrier is emitted from a conformal / Bayesian layer on top. Glass-box end to end. Aligned with the methods you already use." |
| A12 | *"Why 'CDS' and not 'diagnostic'?"* | "Language choice on purpose. 'Diagnostic' is an FDA device term; 'decision support' is what we actually do. It also aligns with the governance argument in the Uncertainty Carriers paper — CDS with mandatory UCs is a patient-safety position, not a device-class claim." |
| A13 | *"Can you publish Paper 1 without FORWARD data?"* | "Yes — Paper 1 is the perspective piece adapting SSRN 6554940 for a rheumatology audience; submittable summer 2026. Paper 2 is the FORWARD-data validation, Q1 2027, Hangyal first, Michaud senior." |
| A14 | *"What about labs or imaging?"* | "Out of scope for FORWARD — we respect that ceiling. Labs/imaging live in our parallel RISE, AMP, and CorEvitas conversations. FORWARD is the PRO-trajectory + treatment-timestamp + behavioral-signal registry for us." |
| A15 | *"What's the internal review process for anonymized access on your side?"* | "That's a question for you — whatever your committee, timeline, and reporting structure look like, we'll work to it. We'll have the DUA template, our IRB posture, and the variable list ready the moment you need them." |
| A16 | *"Can we align on timeline?"* | "Paper 1 perspective, summer 2026. Paper 2 validation, Q1 2027 submission. First data pull scoping: this call. DUA review: two-week target once we have the template. First analytic deliverable back to you: eight weeks post-DUA." |
| A17 | *"Who's the day-to-day contact on your end?"* | "Dylan Gunn on the engineering side for data intake and pipeline; me (Andras) on methods, writing, and the governance framing. You'll have direct access to both." *(Dylan: if Kaleb asks you directly, same answer — you handle intake, Andras handles methods/writing.)* |
| A18 | *"What does 2OPMD bring that FORWARD doesn't already have?"* | "Three things: the governance layer (uncertainty carriers, glass-box derivation), an on-premise inference and knowledge-graph stack that's HIPAA-closed from day one, and a publication frame that positions FORWARD data as the first peer-reviewed validation of mandatory-UC CDS. Your registry, our output wrapper, joint paper." |
| A19 | *"Where do the uncertainty carriers come from mathematically?"* | "Conformal prediction for coverage guarantees, Bayesian or isotonic calibration for the probability band, and the UC text is a structured rendering of the retrieval set and the evidence basis — never a free-text summary. Every carrier is replayable from model hash, prompt hash, and retrieval ids." |
| A20 | *"Is any of this running today?"* | "The 8B reasoning stack, MKG hybrid retrieval, PatientTimelineVision ingestion, and the graph chart for semantic search — yes, on PortalNode-01. The 70B reviewer is specified and hardware-budgeted; the Modelfile is drafted. UC governance layer is published on SSRN. FORWARD-specific analysis is exactly what this call scopes." |

### A.4 For Dylan specifically (from PDF 3's "For Dylan" section)

- **Get the Mollard 2026 PDF before any build work.** ACR Open Rheumatology is open access. The paper drives the input contract for anything we build on FORWARD data.
- **Respect the FORWARD ceiling in code.** PRO trajectories, treatment timestamps, smartphone-behavioral signals. No labs, no imaging, no biosamples, no -omics. Feature builders for FORWARD should fail fast if asked for a LOINC.
- **If Kaleb asks you anything methodological, pivot to Andras.** You're intake + pipeline. Methods and publication live with Andras.

### A.5 What NOT to say (additions to §10)

- Do **not** cite Mollard 2026 specifics (sample size, features, model class, effect sizes, flare operationalization) unless the paper is in hand. Kaleb is a co-author.
- Do **not** propose labs / imaging / biosamples as FORWARD signals.
- Do **not** lead with UC Davis as the signatory path — it's the backstop, not the lead.
- Do **not** open the authorship question. It is pre-agreed: Hangyal first, Michaud senior on Paper 2.
- Do **not** promise Epic Connection Hub status. Integration path is clear; listing comes after a deployment partner.
- Do **not** oversell "deep learning" or frontier ML when describing methods. Kaleb's lane is methodological (mixed-effects, LASSO); match it.

### A.6 Close-of-meeting checklist (what to walk out with)

1. DUA template (file or pointer).
2. Day-to-day data contact name and email.
3. Internal-review process description (one sentence, anonymized-data track).
4. Agreement on RA-first scope and PRO-composite flare definition — or a clean note of disagreement.
5. A tentative date for the first-data-pull scoping call.
6. Kaleb's preferred form of the Paper 1 perspective draft (he sees it first? he reviews? he doesn't touch it until Paper 2 drafts circulate?).

*Appendix A compiled 2026-04-22 from the three Kaleb-related PDFs checked into the workspace root. All quoted language is Andras's; my job here was to line up the three documents with §1–§10 and surface the deltas.*
