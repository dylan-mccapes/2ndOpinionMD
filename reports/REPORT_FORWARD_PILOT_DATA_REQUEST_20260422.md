# REPORT — Is the Current PTV Graph Good Enough to Send Kaleb, and What Specifics to Ask For

**Date:** 2026-04-22 (same day as meeting)
**Author:** 2ndOpinionMD Platform Team
**Companion to:** `REPORT_FORWARD_KALEB_MICHAUD_PREP_20260421.md`, `STUDY_PROPOSAL_LONGITUDINAL_GRAPH_COMPARISON_20260421.md`
**Reference artifact:** `artifacts/ptv_46860f06-e0a5-42d4-af9f-4dd8caa666f0_full_20260422T143255Z_pretty.json` (632 events, 142 arcs)

---

## TL;DR

1. **Do not** send this graph *alone* as our "FORWARD example." It is a PDF-sourced EHR graph; FORWARD data is semi-annual PRO questionnaires. The mismatch is visible.
2. **Do** send this graph **with** an annotated one-page key (in §3 below) **plus** a **Data Request Specification** (§4 below) that tells Kaleb exactly what variables, patient subset, time window, and format we want for the pilot.
3. **Better**: spend 1–2 engineering days producing a small **FORWARD-shaped exemplar** PTV graph (scaffold in §5) and send *that* as the primary artifact, with this graph as the "here is the full engine on other data" reference.

---

## 1. Honest assessment of the current graph as a Kaleb artifact

### 1.1 What's strong

- **Production-shape JSON with full schema** — `events`, `arcs`, `metadata`, `patient_id` UUID, `built_at`, `session_only: false`.
- **142 clinical arcs seeded** at ICD-family level with `date_range`, `event_ids`, and an `arc.status` lifecycle (`seeded → enriched → reviewed → locked`).
- **Eight connascence edge kinds**, including the clinical-semantic **`in_workup_for`** (51) and **`caused_by`** (20).
- **Every event carries** `card`, `salience`, `canonical_id`, `entity_keys`, and (where known) `arc_ids`.
- **`status_flags`** on 96 events with clinically-meaningful states (`continued`, `chronic`, `stopped`, `acute`, `worsening`, `flare`, `improving`).
- **`metadata.pro.forward.patient_reported_outcomes_channel: true`** — the FORWARD PRO channel is a first-class metadata concept.
- **`metadata.index.by_arc`** pre-computed reverse index — zero-scan cohort access.
- **73.4 % temporal coverage** (464/632) — respectable for a PDF-extracted record.
- **107 unique event days** across the patient's history.

### 1.2 What's weak *for a FORWARD audience specifically*

| # | gap | observed value | Kaleb interpretation |
|---|---|---|---|
| G1 | **No PRO / journal events** | `pro`/`journal` event count = 0; `mirrored_journal_ids: []` | "You said FORWARD-ready but there are no PROs here." |
| G2 | **No RxNorm CUIs** | 0 events with `rxnorm_cui`; only `drug_name` strings | "You're still matching on drug names, not identifiers." |
| G3 | **No LOINC codes; no numeric lab values** | 0 `loinc` in `entity_keys`; 22 `lab` events with 0 numeric `value`s | Less relevant to FORWARD (no labs), but signals the MKG-enrichment pass hasn't completed. |
| G4 | **Arc slots empty** | 0/142 `summary`, 0/142 `open_questions`, 0/142 `cross_arc_edges` | The "clinical arc" story looks unfinished. |
| G5 | **Source is PDF, not questionnaire** | Every `event_id` is `pdf_p0003_e000`-style; `heuristic_source: regex_icd_code` | "This is a problem-list extraction, not FORWARD semi-annual data." |
| G6 | **Timestamp edge case** | Timestamp span 1947-08-17 → 2025-12-05 | The 1947 is almost certainly a birth/historical entry; needs a one-line explanation. |
| G7 | **ICD-dominated `entity_keys`** | `icd:*` is by far the dominant key prefix | Symmetry with LOINC / RxNorm / SNOMED is the next pass. |

### 1.3 Verdict

- **As a standalone FORWARD exemplar** — **no**, because G1, G5, and G4 will be the first things Kaleb notices, and his meeting question is specifically about PROs.
- **As a "here's our graph engine on real EHR data, plus the FORWARD-shaped adapter is the next graph family" demonstration** — **yes**, if sent with the one-page annotated key below.
- **As a conversation artifact for the call itself** — **yes, with spoken framing**: "This is a PDF-sourced EHR graph in our production schema. FORWARD graphs plug into the same schema via the PRO channel you see in `metadata.pro.forward`. Here's exactly what we'd need from you to generate a FORWARD-shaped graph — that's the Data Request."

---

## 2. Recommended framing language (verbatim options)

Pick the one that matches Andras's delivery style.

**Framing 1 (direct):**
> "Attached is a production PatientTimelineVision graph from a PDF-sourced EHR record — 632 events, 142 clinical arcs, full schema. The FORWARD PRO channel is wired at the metadata level (see `metadata.pro.forward`) but this particular graph has no PRO nodes because the source wasn't FORWARD. To generate a FORWARD-shaped graph, we need the Data Request Specification below — once we have that, the same pipeline emits a FORWARD graph with PROMIS-HAQ, pain VAS, and patient-global trajectories as native event nodes."

**Framing 2 (with exemplar):**
> "Two attachments. First: a production PTV graph from a PDF-sourced EHR record, 632 events and 142 clinical arcs, so you can see the schema and the arc structure. Second: a compact FORWARD-shaped exemplar we built from synthetic PRO data with a known flare sequence, showing how the same pipeline represents semi-annual HAQ and VAS trajectories. The Data Request Specification in the document tells us exactly what variables, patient subset, and time window to pull to replace the synthetic data with real FORWARD data."

**Framing 3 (if sending only the DRS):**
> "Before we send any graph, here is our Data Request Specification — the exact variables, subset, time window, and format we would use for the pilot. If this matches what your anonymized track can provide, we can generate a FORWARD-shaped PTV graph from the first pull within days of receiving it."

---

## 3. One-page annotated key to ship alongside this graph

Drop this as a sidecar markdown file or a paragraph in the email body.

```
PTV SCHEMA KEY — ptv_46860f06-..._full_20260422T143255Z

  patient_id              anonymized UUID (one graph = one patient)
  built_at                UTC build timestamp
  session_only: false     this graph is persisted, not ephemeral
  metadata.pro.forward    FORWARD PRO channel hook (wired; empty in this graph
                          because the source is an EHR PDF, not FORWARD)
  metadata.index.by_arc   pre-computed reverse index (arc_id -> event_ids)

  events (632 in this graph)
    event_type            diagnosis / medication / lab / symptom / procedure /
                          clinical_note / imaging / vital_signs / visit /
                          immunization / administrative
                          [future: pro / journal / flare / therapy_episode /
                                   adverse_event / goal / derived_metric]
    card                  compact 100-200 token digest, the 70B-ready view
    salience              priority score (this graph: 1.69 - 8.04)
    canonical_id          cross-source dedup handle (collisions = confirmation)
    entity_keys           normalized codes, e.g. 'icd:k81_0'
    arc_ids               membership in one or more clinical arcs
    status_flags          continued / chronic / stopped / acute /
                          worsening / flare / improving
    connascence           same_chapter / temporal / same_day / same_encounter /
                          same_drug / same_icd / in_workup_for / caused_by

  arcs (142 in this graph)
    arc_id                e.g. arc_icd_M10 = gout arc
    status                seeded | enriched | reviewed | locked
    date_range            [first, last] event date in the arc
    event_ids             member events
    summary               LLM-authored after enrichment (empty here)
    open_questions        what this arc still needs (empty here - 8B writes these)
    cross_arc_edges       typed inter-arc relationships (empty here -
                          triggers / contraindicates / shares_therapy / confounds)

  NOTE ON THIS EXAMPLE
    - 1947 timestamp is a historical/birth entry; 99% of events are 2016-2025.
    - PDF-sourced; FORWARD graphs use the same schema with pro/journal
      events replacing the pdf_p*_e* events.
    - No PROs, no RxNorm CUIs, no numeric lab values in THIS graph because
      the source record did not include them. The pipeline emits them when
      the source provides them.
```

---

## 4. Data Request Specification (DRS) — what to ask Kaleb for

This is the **document Kaleb actually wants**. One page. Concrete. Matches the FORWARD questionnaire structure exactly.

### 4.1 Cohort (primary)

- **Disease:** Rheumatoid arthritis
- **Inclusion:** ≥ 1 FORWARD questionnaire with ICD-10 M05.\* or M06.\* documented; ≥ 3 semi-annual questionnaires completed; ≥ 2 years of follow-up
- **Exclusion:** Primary diagnosis SLE, OA, PsA, JIA, axSpA (these remain in separate substudies)
- **Target n:** 500–1,500 patients (pilot), scalable to 5,000–10,000 for Paper 2
- **Time window:** Lookback ≥ 5 years from most recent questionnaire; forward-12-month outcome window

### 4.2 Variables (primary, required)

| domain | instrument / field | purpose |
|---|---|---|
| Functional status | **HAQ-II** (preferred) or HAQ; raw score + MCID flag | primary trajectory |
| Pain | **VAS Pain** (0–100) | primary trajectory |
| Global assessment | **VAS Patient Global** (0–100) | primary trajectory |
| Disease activity (patient) | **RADAI** or **PAS-II** | composite anchor |
| Quality of life | **EQ-5D** or **SF-36** | secondary outcome |
| Comorbidity | **RDCI** score and component flags | model covariate |
| Demographics | age-band, sex, race/ethnicity (to the de-ID level FORWARD supports) | stratification |
| Smoking status | current / former / never / unknown | covariate |
| Treatment timestamps | start/stop date per DMARD / biologic / JAKi / steroid; dose if recorded | flare anchor |
| Concomitant medications | class-level rollup (NSAIDs, steroids, antidepressants) | covariate |
| Questionnaire metadata | date, round number, mode of completion | temporal grounding |

### 4.3 Variables (secondary, if available)

- PROMIS short forms (fatigue, sleep, depression, physical function) — T-scores
- PASS — yes/no per round
- Flare self-report question (if included in that round)
- Work status (employed / disabled / retired)
- Smartphone substudy data (Mollard-2026 cohort) — passive signals if the subset is included and cleared for this pilot
- Hospitalization events (count + reason categories)
- Adverse event reports (self-reported, class-level)

### 4.4 Variables (**confirmed out of scope for FORWARD**)

- Labs / LOINC values — confirmed not collected
- Imaging reports — confirmed not collected
- Biosamples / -omics — confirmed not collected
- Clinician-measured DAS28, SDAI, CDAI — confirmed not in FORWARD

### 4.5 Format

- **Preferred:** Parquet or CSV, one row per (patient × questionnaire round) for PROs; one row per (patient × medication event) for treatment timeline; long-format for instrument subscales.
- **Acceptable:** JSON-lines at the same granularity.
- **Encoding:** UTF-8, ISO-8601 dates, explicit units in column names (`vas_pain_0_100`, `haq2_raw`).
- **Missing data:** explicit `NA` or null, never blank string; questionnaire-level `completion_flag` column.

### 4.6 De-identification

- Accept the **FORWARD anonymized dataset** track at whatever de-ID level it provides (Safe Harbor / Limited Dataset / Expert Determination).
- We hold PHI *only if* the track requires a Limited Dataset DUA; otherwise we accept Safe Harbor.
- No re-identification attempts; no linkage to external PHI.

### 4.7 Data security posture on our side

- Storage: PortalNode-01 on-premise, HIPAA-compliant, air-gapped.
- No cloud LLM calls for FORWARD data. All inference via `eoh-llama-*` locally.
- Access: named researcher list (Hangyal PI; Gunn engineering).
- Data-deletion path: cascade on consent withdrawal via the `metadata.consent` field.

### 4.8 Pilot deliverables (what we return)

1. **Ingest report:** n patients, n questionnaires, variable coverage matrix, missingness audit.
2. **FORWARD-shaped PTV graphs:** one per patient; PRO trajectories as `pro` event nodes; treatment timeline as `therapy_episode` arcs; PRO-composite flare as a `flare` arc where definition is met.
3. **Cohort dashboard:** trajectory clusters, flare-arc incidence, baseline phenotype stratification.
4. **Uncertainty-carrier emission samples:** 20 de-identified example outputs with calibration metadata.
5. **Methods note:** draft statistical plan for Paper 2.

### 4.9 Asks to Kaleb on the call

1. **Does 4.1–4.4 match what your anonymized track can provide?**
2. **What is the de-identification level** (4.6)?
3. **Who is the day-to-day data contact**?
4. **Standard DUA template** — can we get it to review in parallel?
5. **Internal review process** for anonymized access — one sentence on steps/timeline?
6. **First-pull scope**: can we lock variables, cohort filter, and time window on a follow-up call within 2 weeks?

---

## 5. Optional: FORWARD-shaped exemplar (1–2 engineering days)

If we want to hand Kaleb a *more convincing* exemplar than the PDF-sourced graph, here's the minimum scaffold. Synthetic data only; clearly labeled.

### 5.1 Shape

- **1 synthetic patient**, de-identified, 8-year follow-up, 16 semi-annual questionnaires.
- RA diagnosis (M05.9) in year 1.
- Treatment trajectory: MTX start → MTX+HCQ → MTX + adalimumab → switch to TNFi #2 → add low-dose prednisone during a flare.
- Two flare events, one subclinical (by PRO-composite), one prompting therapy escalation.

### 5.2 Event inventory (~60 events, compact)

- 16 `pro` events (PROMIS-HAQ raw + t-score, VAS pain, VAS global, PAS-II, RDCI)
- 6 `medication` events with `rxnorm_cui` populated (MTX, HCQ, adalimumab, etanercept, prednisone, folic acid)
- 6 `therapy_episode` events (one per course)
- 2 `flare` events (one subclinical, one escalation-anchored)
- 3 `clinical_note` events (annual visits, brief)
- 4 `symptom` events around flare windows
- Connascence: `temporal`, `same_encounter`, **`pro_shift`** (new), **`therapy_episode`** edges, **`flare_window`** edges

### 5.3 Arc inventory

- `arc_icd_M05` — the RA diagnosis arc
- `arc_therapy_mtx_2019_2021`, `arc_therapy_adalimumab_2022_present`
- `arc_flare_2022_q3`, `arc_flare_2024_q1`
- `arc_study_epoch_baseline`, `arc_study_epoch_m24`, `arc_study_epoch_m48`
- At least one arc with a **populated** `summary`, `open_questions: ["Is the 2022-Q3 flare a PRO-composite true positive?"]`, and one `cross_arc_edges` link (therapy_adalimumab → flare_2024_q1, `kind: shares_therapy`).

### 5.4 Metadata

- `metadata.pro.source: "forward_synthetic"`
- `metadata.pro.forward.patient_reported_outcomes_channel: true`
- `metadata.pro.mirrored_journal_ids: [...]` — populated list
- `metadata.schema_version: "ptv.2.1-forward"`
- `metadata.study_cohorts: ["FORWARD_RA_2026"]`
- Clearly labeled: `metadata.synthetic: true` with a `disclaimer` field

### 5.5 What this demo proves

- The schema cleanly represents FORWARD-style semi-annual PRO trajectories.
- Arcs carry therapy episodes and flare windows as first-class cohort-comparable objects.
- PRO-composite flare definition is computable from the graph (deterministic, not LLM).
- UC emission is attached as a `derived_metric` node citing the PRO events and EoH flare module.
- The same pipeline that produced the PDF-sourced graph produces this one.

### 5.6 Build plan

| step | owner | effort |
|---|---|---|
| Synthetic PRO trajectory generator | engineering | 2 hours |
| RxNorm lookup for the 6 meds (local RxNav snapshot) | engineering | 1 hour |
| PTV builder extension: `pro` and `therapy_episode` event types | engineering | 4 hours |
| PRO-composite flare detector (deterministic, HAQ-II ≥ 0.22 + VAS pain ≥ 20 + anchor) | engineering / Andras methods review | 3 hours |
| Arc enrichment: `summary`, `open_questions`, `cross_arc_edges` populated | 8B + manual review | 2 hours |
| UC sample emission on one flare arc | platform | 1 hour |
| One-page annotated key for the exemplar | Dylan | 1 hour |
| **Total** | | **~1.5 engineering days** |

This lives as `artifacts/ptv_forward_exemplar_synthetic_20260423.json` and is never confused with real patient data by virtue of `metadata.synthetic: true`.

---

## 6. Recommendation

**For the 2026-04-22 call (today):**
- Send this graph as a **secondary** attachment with the annotated key from §3.
- Send the **Data Request Specification** from §4 as the **primary** attachment — that is what Kaleb is asking for.
- Use Framing 1 or 3 from §2 in the email.
- In the call, if Kaleb asks to see PROs in the graph, pivot with: *"The PRO channel is in the schema — here's `metadata.pro.forward`. We'll build a FORWARD-shaped exemplar from your first pull, or synthetically if you want to see it before the DUA is signed. Takes us a day."*

**For the follow-up within 72 hours:**
- Build the §5 exemplar and send it with a short "as promised" note.
- It's cheap, it directly answers the objection, and it's the more compelling artifact.

**Do not:**
- Hand over the current graph as "here's what FORWARD data looks like in our system" without framing.
- Promise PRO trajectories are populated in this specific graph — they are not.
- Overstate arc enrichment — `summary`, `open_questions`, and `cross_arc_edges` are empty and Kaleb can `ctrl-F` for them.

---

*Prepared 2026-04-22 for the 2026-04-22 FORWARD meeting with Kaleb Michaud. Verdict and DRS are traceable to the referenced artifact and to `REPORT_FORWARD_KALEB_MICHAUD_PREP_20260421.md`.*
