# STUDY PROPOSAL — Longitudinal Graph Comparison of Treatment Pathways and Outcomes (LGC-TPO)

**Date:** 2026-04-21 (rev 2026-04-22: aligned to full-graph schema with populated arcs)
**Author:** 2ndOpinionMD Platform Team
**Status:** Draft for FORWARD / RISE review
**Classification:** On-premise, air-gapped, HIPAA-compliant (PortalNode-01)
**Reference graph (full schema):** `ptv_46860f06-e0a5-42d4-af9f-4dd8caa666f0_full_20260422T143255Z_pretty.json`

---

## 0. One-Line Summary

Use **100,000 PatientTimelineVision (PTV) graphs** as the unit of analysis and run **graph-to-graph comparison** at cohort scale — with `eoh-llama-8b` as the traversal/retrieval worker and `eoh-llama-70b` as the reviewer/synthesizer — to discover **trajectory–phenotype–outcome associations** that cross-sectional EHR studies structurally cannot see.

> Unit of analysis ≠ row in a table. Unit of analysis = **labeled, temporally-ordered graph** with provenance, connascence edges, and coded nodes (ICD, LOINC, RxNorm, NDC).

---

## 1. Background: what the full graph already gives us

Reference graph: `ptv_46860f06-e0a5-42d4-af9f-4dd8caa666f0_full_20260422T143255Z_pretty.json` (one patient, 632 events, **142 arcs**).

**Node composition (full schema):**

| event_type              | count |
|-------------------------|------:|
| diagnosis               |   229 |
| medication              |   137 |
| administrative          |   109 |
| procedure               |    48 |
| clinical_note           |    40 |
| symptom                 |    23 |
| lab                     |    22 |
| vital_signs             |    11 |
| imaging                 |     6 |
| visit                   |     4 |
| immunization            |     2 |
| chapter_administrative  |     1 |

**Edge (connascence) composition — now includes clinical-semantic edges:**

| edge kind         | count | nature                                          |
|-------------------|------:|-------------------------------------------------|
| same_chapter      |   625 | structural                                      |
| temporal          |   433 | structural                                      |
| same_day          |   411 | structural                                      |
| same_encounter    |   338 | structural                                      |
| same_drug         |   105 | structural                                      |
| same_icd          |    93 | structural                                      |
| **in_workup_for** |    51 | **clinical-semantic**                           |
| **caused_by**     |    20 | **clinical-semantic**                           |

**Arc composition (142 arcs populated):** each arc has `arc_id`, `name`, `status`, `summary`, `event_ids`, `date_range`, `open_questions`, `cross_arc_edges`. Arcs are seeded per ICD family (e.g. `arc_icd_E78 = "Lipid disorders"`, `arc_icd_J45` asthma, `arc_icd_I10` HTN, `arc_icd_I25` CAD). **Arc sizes:** min 1, max 46, mean 3.3 events/arc. **Reverse index** (`metadata.index.by_arc`) is pre-computed.

**Per-event annotations present in the full schema:**

- **`card`** on 632/632 events — compact `{ts, icd, drug, type, title, arc_ids, one_line, salience}` summary. *This is our pre-built 70B-ready node digest.*
- **`salience`** on 632/632 events — numeric priority score (observed range 1.69–8.04). *This is the native 8B pre-filter signal.*
- **`canonical_id`** on 632/632 events (575 unique) — cross-source deduplication handle; duplicates indicate the same clinical fact appearing from multiple sources.
- **`entity_keys`** on 307 events — normalized codes like `icd:k81_0`. *Cross-graph join key for cohort motif queries.*
- **`arc_ids`** on 367 events — arc membership (events can belong to multiple arcs).
- **`status_flags`** on 96 events — `continued` (50), `chronic` (22), `stopped` (16), `acute` (4), `worsening` (3), `flare` (2), `improving` (2). *Longitudinal state already labeled.*
- **`collapsed_into`** / **`suppressed_events`** — dedup/merge provenance.
- Previously present: `icd_code`, `drug_name`, `drug_dosage`, `drug_route`, `drug_norm_source`, `encounter_date`, `encounter_type`, `pdf_page`, `chapter_id`, `chapter_kind`, `section_header`, `heuristic_source`, `timestamp_source`, `edge_provenance`.

**Top-level `metadata`:** already carries `metadata.pro.source`, `metadata.pro.forward.patient_reported_outcomes_channel: true`, and `metadata.pro.mirrored_journal_ids: []` — **the FORWARD PRO / journal channel is wired at the metadata level.**

**Temporal coverage:** 464/632 (73.4 %) events carry a known timestamp; 168 are `unknown`.

**Immediate implications:**
- The graph already supports **arc-based cohorting** (ICD-family arcs are pre-seeded) — no new infrastructure needed to run cross-graph comparisons at the arc level.
- **Clinical-semantic edges (`in_workup_for`, `caused_by`) are already present** — enabling reasoning about workup-linked diagnoses and putative causation without inventing new edge types.
- **`salience` and `card` are a ready-made "pre-digest" layer** for the 8B → 70B handoff described in §7.
- **`canonical_id`** lets us measure cross-source agreement/disagreement *within* a single graph and **across graphs** (same concept occurring in 100 K graphs).
- **`entity_keys`** are the right substrate for motif queries — we can do `∃ v ∈ G with 'icd:m05' ∈ v.entity_keys` in one hop.
- **`status_flags`** (`flare`, `worsening`, `improving`, `stopped`, `continued`) provide a first longitudinal state label that Hypotheses 2 and 6 can build on immediately.
- What the graph *still* lacks explicitly and this proposal formalizes: numeric lab values with LOINC codes, RxNorm CUIs on every medication (`drug_norm_source` is present but CUI is not universally attached), PRO/journal **event nodes** (the PRO channel exists at metadata level but journal event nodes need to be emitted), adverse-event nodes, EoH-derived `flare` / `therapy_episode` nodes, and `cross_arc_edges` population (field exists but is empty in seeded arcs).

---

## 2. Study Title

**Longitudinal Graph Comparison of Treatment Pathways and Outcomes (LGC-TPO): Discovering Trajectory–Phenotype–Outcome Associations in a 100,000-Graph On-Premise Cohort.**

Companion substudies (FORWARD / RISE) reuse the same machinery:

- **LGC-TPO/RA-PRO** (FORWARD) — longitudinal PRO trajectories in rheumatoid arthritis; primary endpoint: PROMIS-HAQ and RAPID3 delta stratified by therapy pathway.
- **LGC-TPO/RISE-QM** (ACR RISE) — guideline-adherence footprint against ACR quality measures; endpoint: divergence–outcome coupling.

---

## 3. Primary Hypotheses (pre-registered)

1. **H1 — Trajectory ≫ cross-section.** Patients clustered by *graph trajectory* (node-type sequence + temporal density) predict 12-month PRO outcomes better than patients clustered by *baseline diagnosis codes alone* (AUC delta ≥ 0.05, DeLong test, two-sided).
2. **H2 — Guideline divergence signature.** Graphs that diverge from ACR/EULAR expected-next-step pathways show elevated flare rate and therapy-switch rate at 6 and 12 months (HR ≥ 1.3).
3. **H3 — Latency as phenotype.** *Time-to-DMARD*, *time-to-biologic*, and *time-to-PRO-improvement* are heritable trajectory features; graphs with shorter latencies cluster and associate with distinct comorbidity profiles.
4. **H4 — Missingness as signal.** Graphs with high `unknown` timestamp density or sparse lab coverage correlate with worse PRO trajectories — identifying populations for targeted data-capture outreach.
5. **H5 — Co-prescription graph risk.** Edges discovered by the `same_day` + `same_drug` + MKG-retrieved interaction pair encode latent adverse-event risk detectable before coded AE.
6. **H6 — Psychological (journal) nodes are leading indicators.** PROs captured as journal nodes precede flare-adjacent graph reconfiguration by a measurable lag (days-to-weeks).

All hypotheses are testable with **deterministic** graph computations + MKG retrieval + EoH modules; `eoh-llama-70b` is the **reviewer**, not the estimator.

---

## 4. Cohort Construction (graph-pattern queries)

Because the unit is a graph, cohort selection is a **subgraph motif**, not a SQL filter. With the full-schema primitives, motifs are expressed directly against `entity_keys`, `arc_ids`, and `status_flags`:

```text
cohort_FORWARD_RA = {
  G ∈ PTV
  | ∃ arc ∈ G.arcs with arc_id ∈ {arc_icd_M05, arc_icd_M06}          -- uses populated arcs
  ∧ ∃ v ∈ G.events with 'icd:m05' ∈ v.entity_keys                     -- uses entity_keys
  ∧ ∃ w ∈ G.events with rxnorm_cui ∈ DMARD_set                        -- to be added
  ∧ temporal(v) < temporal(w)
  ∧ coverage(G) ≥ τ                                                   -- timestamp/entity coverage
}
```

Practical execution per graph:
- `metadata.index.by_arc` gives O(1) access to every event in a clinical arc → the 8B does not walk blindly.
- `entity_keys` give a normalized, case-folded join key → cohort membership tests are set-membership, not regex.
- `arc.date_range` gives the arc's temporal envelope for free (no scan needed).
- `card.salience` + `status_flags` let us pre-rank candidate graphs before any 70B pass.

The same machinery serves FORWARD (RA), RISE (QM), and any future study — the motif changes, the engine does not.

**Enrichment classes (from regex at graph-build time):**

- `ICD-10` codes — already present (`regex_icd_code`).
- `LOINC` codes — new regex rule; attach `loinc_code` to every `lab` node plus numeric `value`, `unit`, `reference_range`.
- `RxNorm CUI` — new regex + RxNav lookup (locally-cached table) attached to every `medication` node.
- `NDC` — optional, when present in source notes.
- `CPT` — attached to `procedure` nodes.
- `SNOMED-CT` — attached to `symptom` and `clinical_note` nodes where mappable.

Hybrid retrieval (`TS/ANN fusion`) in MKG then resolves human-readable meaning, guideline citations, and interaction annotations for each code.

---

## 5. What We Seek to Find

### 5.1 Trajectory phenotypes (unsupervised)
- Cluster patients by **arc-sequence** (ordered list of arc openings with their status transitions), and by **node-type sequence** (dx → lab → med → PRO → lab …) using DTW or graph edit distance.
- `status_flags` (`acute → chronic`, `continued → stopped`, `improving / worsening / flare`) are first-class state-transition features.
- Label clusters post-hoc with EoH module outputs (M68 Inflammatory Capacity, flare detector, adherence).
- Report: *"Cluster 4 is an early-aggressive DMARD responder cohort with attenuated fatigue trajectory"* — a conclusion no ICD-level study can produce.

### 5.2 Latency and sequencing features
- Diagnosis → first DMARD (days).
- First DMARD → biologic escalation (days).
- Therapy start → PRO improvement (days to RAPID3 MCID).
- Therapy start → lab response (days to CRP normalization).
- Flare → therapy change (days).
- Encode each latency as a first-class patient attribute; test cluster separation.

### 5.3 Guideline-divergence ledger
- For each patient, project the graph **at the arc level** (not at the raw-event level) onto the nearest ACR/EULAR pathway retrieved from MKG.
- `eoh-llama-8b` uses `arc.open_questions` as the shortlist of "what this arc still needs" and pulls the candidate guideline nodes from MKG; `eoh-llama-70b` renders a per-patient "expected vs. observed" diff.
- **Output:** `guideline_divergence` node(s) attached to the PTV and written back into each arc's `open_questions` / `cross_arc_edges` with typed kinds (*skipped step*, *out-of-sequence*, *missing monitoring*, *dose out of range*).

### 5.4 Treatment-pathway effectiveness (quasi-experimental)
- Within a baseline-phenotype-matched sub-cohort, compare therapy orderings (e.g., MTX→TNFi vs. MTX→JAKi) on PRO delta.
- Matching is *graph-based* (graph kernels / propensity over graph features), not only on tabular covariates.
- Emit Kaplan-Meier and cumulative-incidence plots per pathway (deterministic Python).

### 5.5 Co-prescription and AE risk edges
- For every `same_day` + `same_drug` clique, query MKG (drug-interaction index) and flag interaction-pair coverage.
- Cross-check against existing `caused_by` edges — where AI disagrees with coded causality, open a review ticket.
- Emit a `suspected_ae_edge` between the drug pair and any subsequent abnormal lab / symptom within a 30-day window.
- Contrast AE incidence by flagged vs. unflagged cliques.

### 5.5b Workup coherence (new — exploits `in_workup_for`)
- The `in_workup_for` edge already links diagnoses to the procedures/labs that worked them up. Compare per-arc workup completeness (observed `in_workup_for` set vs. MKG-expected workup set) — a new, graph-native quality measure.
- Emit `missing_workup` entries to `arc.open_questions`.

### 5.5c Cross-source agreement (new — exploits `canonical_id`)
- A `canonical_id` collision (same id, multiple source documents) means the same fact was asserted from >1 source. Collisions are **confirmatory**; isolated canonicals in high-risk arcs are **review candidates**.
- Cohort-level statistic: fraction of canonical_ids with multi-source support per arc-type — a data-quality / trust signal tied to outcomes.

### 5.6 Lab-biomarker trajectories (LOINC)
- For each LOINC of interest (CRP, ESR, Hgb, ALT, AST, creatinine, platelets, lipids): fit per-patient slope and change-points; cluster.
- Correlate trajectory class with therapy and PRO class.

### 5.7 Missingness phenotypes
- Per graph: missingness vector over (lab panel, PRO instrument, visit cadence, dose/route completeness).
- Test H4; identify targetable populations.

### 5.8 Journal-node leading indicators
- For patients with journal nodes (PROMIS, HAQ, Pain, Fatigue, PASS, RAPID3), compute lead-lag between PRO shift and graph reconfiguration (new med, new symptom, new lab).
- Report median lag, 95 % CI; test against null.

### 5.9 Social / administrative context
- Use `administrative` (75 nodes in prototype) and `visit` nodes for care-utilization fingerprints; contrast with PRO outcomes.

### 5.10 EoH module emissions as outcomes
- Treat **M68 Inflammatory Capacity**, **flare detector**, **adherence estimator** outputs as derived longitudinal signals.
- These become cohort-comparable trajectories themselves.

---

## 6. How to Update the Graph to Accommodate More

Below each item is tagged **[present]** (already in the full schema — we just use it), **[extend]** (primitive exists; we add fields or populate empty slots), or **[new]** (genuine addition). All additions remain **non-breaking** — existing graphs keep working; new graphs gain capability.

### 6.1 Event_types

| event_type                | status   | purpose                                                                 |
|---------------------------|----------|-------------------------------------------------------------------------|
| `diagnosis`               | present  | —                                                                       |
| `medication`              | present  | —                                                                       |
| `procedure`               | present  | —                                                                       |
| `lab`                     | present  | —                                                                       |
| `symptom`                 | present  | —                                                                       |
| `clinical_note`           | present  | —                                                                       |
| `visit`                   | present  | —                                                                       |
| `imaging`                 | present  | —                                                                       |
| `vital_signs`             | present  | —                                                                       |
| `immunization`            | present  | —                                                                       |
| `administrative`          | present  | —                                                                       |
| `chapter_administrative`  | present  | —                                                                       |
| `pro`                     | **new**  | Patient-Reported Outcomes (PROMIS-HAQ, RAPID3, Pain, Fatigue, PASS)     |
| `journal`                 | **new**  | Free-text patient journal (psychological state, SDOH)                   |
| `adverse_event`           | **new**  | Coded or AI-flagged AE                                                  |
| `flare`                   | **new**  | EoH flare-detector emission (complements `status_flags:['flare']`)      |
| `therapy_episode`         | **new**  | Start → stop of a medication course with `reason_for_stop`              |
| `goal`                    | **new**  | Shared-decision-making goal node                                        |
| `consent`                 | **new**  | Study/data-sharing consent state                                        |
| `derived_metric`          | **new**  | EoH or math-script output (M68, slopes, PRO deltas)                     |
| `guideline_expected`      | **new**  | MKG-projected expected next step                                        |
| `divergence`              | **new**  | Observed vs. expected guideline delta                                   |

### 6.2 Annotations

On **all** nodes — **already present:** `card`, `salience`, `canonical_id`, `entity_keys`, `arc_ids`, `chapter_id`, `chapter_kind`, `pdf_page`, `edge_provenance`, `status_flags`, `heuristic_source`, `timestamp_source`, `collapsed_into`, `suppressed_events`.

**[extend]** `entity_keys`: ensure every node emits the full set — `icd:*`, `loinc:*`, `rxnorm:*`, `snomed:*`, `cpt:*`, `ndc:*` (currently dominated by `icd:*`).

**[extend]** `card`: add `coverage: {has_dose, has_value, has_date, has_code}` so the 70B sees "what's present" in one glance.

**[extend]** `status_flags`: broaden the vocabulary to include `dose_changed`, `held`, `titrating`, `rechallenged`, `ineffective`, `intolerance`. Current values observed: `continued`, `chronic`, `stopped`, `acute`, `worsening`, `flare`, `improving`.

**[new]** on **all** nodes:
- `code_confidence: 0.0..1.0` per code in `entity_keys`
- `extracted_by: {regex|mkg|eoh|llm|curated}`
- `provenance_run_id` (joins ProvenanceEngine)

**[new]** on **lab** nodes: `value`, `unit`, `reference_low`, `reference_high`, `abnormal_flag`, `collected_at`.

**[new]** on **medication** nodes: `rxnorm_cui`, `ingredient`, `dose_mg`, `dose_unit`, `frequency_per_day`, `route`, `start_date`, `stop_date`, `reason_for_stop`, `prescriber_role` (note: `drug_name`/`drug_dosage`/`drug_route` are already present).

**[new]** on **pro / journal** nodes: `instrument`, `subscale`, `raw_score`, `t_score`, `mcid_met: bool`, `self_reported_at`.

### 6.3 Connascence (edge) kinds

**Already present:** `same_chapter`, `temporal`, `same_day`, `same_encounter`, `same_drug`, `same_icd`, **`in_workup_for`**, **`caused_by`**.

**[new]** edges:

| edge kind                 | semantics                                                  |
|---------------------------|------------------------------------------------------------|
| `causal_hypothesis`       | AI-proposed causal link (distinct from coded `caused_by`)  |
| `guideline_expected_next` | what ACR/EULAR would suggest next given graph state        |
| `observed_vs_expected`    | divergence edge between observed and expected              |
| `flare_window`            | events within an EoH-declared flare window                 |
| `therapy_episode`         | medication start→stop with reason                          |
| `lab_response_window`     | therapy start → post-therapy lab trajectory                |
| `ae_suspected`            | co-prescription / drug-drug interaction risk               |
| `pro_shift`               | measurable PRO delta; lead/lag anchor                      |
| `cohort_peer`             | nearest-neighbor peers in phenotype space (on-prem only)   |

All edges carry the existing `edge_provenance` pattern (`by`, `kind`, `peer`, `group`, `strength`).

### 6.4 Arcs — already populated; three targeted extensions

**[present]** `arcs: {arc_id → {name, status, summary, event_ids, date_range, open_questions, cross_arc_edges}}`. 142 arcs in the reference graph, mostly ICD-family (`arc_icd_*`). Reverse index in `metadata.index.by_arc`.

**[extend]** Populate the currently-empty slots:
- `cross_arc_edges`: emit typed edges between arcs — `triggers` (arc A's exacerbation triggers arc B), `contraindicates`, `shares_therapy`, `shares_symptom`, `confounds` (for causal analyses). These are the graph-theoretic equivalent of comorbidity networks and are the structure we compare across 100 K graphs.
- `summary`: LLM-authored *only after* deterministic fill is complete, with every fact cited to event ids.
- `status`: move from `seeded` → `enriched` → `reviewed` → `locked` per OGrE lifecycle.
- `open_questions`: populated by the 8B (missing workup, missing monitoring, missing response assessment) and **consumed** by the 70B as its agenda.

**[new]** Additional arc families beyond ICD:
- `arc_therapy_{rxnorm}` — one arc per therapy course (groups `therapy_episode` events).
- `arc_flare_{yyyy_mm}` — one arc per detected flare window.
- `arc_study_epoch_{name}` — baseline / m6 / m12 for outcome locking.
- `arc_workup_{target_icd}` — groups `in_workup_for` cliques.

**[new]** Graph-level `arc_features` cache: `{arc_density_by_kind, mean_salience_per_arc, time_to_first_therapy_per_arc, arc_overlap_matrix_hash}`.

### 6.5 Study-scope tags per graph

**[extend]** top-level `metadata` — already carries `metadata.pro.*`; add:
- `metadata.study_cohorts: ["FORWARD_RA_2026", "RISE_QM_2026"]`
- `metadata.consent: { scope, irb_id, date, withdrawable: true }`
- `metadata.deid_level`, `metadata.site_id`, `metadata.enrollment_date`
- `metadata.schema_version` (bump)

### 6.6 Graph-level derived features (cached)

**[new]** `features: { ... }` at graph root (cheap to re-compute, expensive to re-scan for):

- `node_type_counts`, `node_type_entropy`
- `salience_distribution` (already computable from per-event `salience`)
- `temporal_density` (events per day in active span)
- `unknown_timestamp_frac` (reference graph: 0.266)
- `unique_icd_count`, `unique_rxnorm_count`, `unique_loinc_count`
- `canonical_id_multiplicity` (mean + max duplicate count → source-redundancy signal)
- `entity_key_coverage_by_type` (e.g. fraction of meds with `rxnorm:` key)
- `arc_count_by_family`, `arcs_open_questions_count`
- `status_flag_distribution` (`%flare`, `%worsening`, `%stopped`, …)
- `latency_profile: { dx_to_dmard_days, dmard_to_biologic_days, therapy_to_lab_response_days, ... }`
- `eoh_emissions: { m68_last, flare_count_12m, adherence_est }`

These compress a 632-event graph to <2 KB of highly-informative priors — **the fields the 70B reviews first**, and the fields used for fast cohort-level filtering across 100 K graphs.

### 6.7 Versioning and lifecycle

- Every schema change bumps `metadata.schema_version`.
- OGrE runs record which schema they upgraded to and leave a migration trail.
- Per-arc `status` machine (`seeded → enriched → reviewed → locked`) gives us the lifecycle hook OGrE needs to know what to work on next.
- Old graphs remain queryable; new fields are optional.

---

## 7. Agent / EoH Pipeline per Graph

The full-schema primitives (`card`, `salience`, `entity_keys`, `arc_ids`, `canonical_id`, `status_flags`, `metadata.index.by_arc`, `in_workup_for`, `caused_by`) let each stage be described in terms of graph operations rather than LLM prompts.

```
┌──────────────────────────── PTV graph (ehr.patient_graph_vision) ───────────────────────────────────────┐
│                                                                                                          │
│  0. OGrE enrichment (runs continuously)                                                                   │
│     - regex LOINC/RxNorm/NDC → extend entity_keys                                                         │
│     - code_confidence + extracted_by tagging                                                              │
│     - canonical_id de-dup; populate collapsed_into / suppressed_events                                    │
│     - arc status: seeded → enriched (fills summary, open_questions, cross_arc_edges)                      │
│                                                                                                          │
│  1. Python pre-pass (deterministic, no LLM)                                                               │
│     - compute graph-level features (§6.6)                                                                 │
│     - emit derived arcs: therapy_episode_*, flare_*, study_epoch_* (§6.4)                                 │
│     - run EoH modules: M68 ICM, flare detector, adherence                                                 │
│     - run math scripts: latencies, slopes, change-points, KM on-the-fly                                   │
│                                                                                                          │
│  2. eoh-llama-8b workers (parallel, one per graph or per arc)                                             │
│     - iterate arcs via metadata.index.by_arc — arcs are the unit of work, not raw events                  │
│     - within each arc, rank events by `salience` descending; take top-N that fit budget                   │
│     - for each kept event, send only its `card` (not the full event) to the context pack                  │
│     - for each entity_key (icd:*, loinc:*, rxnorm:*), call MKG hybrid TS/ANN fusion; attach citations     │
│     - read arc.open_questions → targeted MKG queries; write findings back to open_questions               │
│     - check in_workup_for / caused_by edges against MKG-expected workup and causality                     │
│     - assemble a context pack: ≤ 20 k tokens of cards + MKG snippets + EoH emissions + math outputs       │
│                                                                                                          │
│  3. eoh-llama-70b reviewer — one pass per cohort-slice of ~20–50 graphs (100 k ctx, cap)                  │
│     - receives: context packs, EoH module docs (Modelfile), guideline snippets, math outputs              │
│     - emits per graph: { findings[], arc_diffs[], guideline_divergences[], missing_data[],                │
│                          confidence, evidence_ids[], citations[] }                                        │
│     - never invents facts; may flag "missing data" and stop                                               │
│                                                                                                          │
│  4. Aggregator (deterministic)                                                                            │
│     - cohort-level statistics, KM curves, divergence ledgers                                              │
│     - writes arc.status = reviewed (or locked after clinician sign-off)                                   │
│     - provenance: every output traceable to model + prompt + retrieval set                                │
└──────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

Key framing:
- **The arc is the atomic unit of review**, not the event. 142 arcs per reference graph × ~3.3 events/arc is tractable even at 100 K graphs.
- **`salience` is the native priority signal** — the 8B does not re-invent what to pay attention to; it uses the score already on each event.
- **`card` is the native compact representation** — ~100–200 tokens per event vs. ~400–800 for the raw event block; this alone roughly halves the 70B's context burn.
- **`arc.open_questions` is the bidirectional todo list** between 8B and 70B — the 8B writes what it couldn't resolve; the 70B reads it first.

The **8B is the retrieval worker**; the **70B is the reviewer**; **no fact is generated without retrieval citation** (enforced by the Modelfile system prompt).

---

## 8. Execution Plan at 100 K Graphs

- **Index**: `pgvector` on `ehr.patient_graph_chart` + a materialized view `ptv_features` for graph-level features (§6.6). Motif queries run in SQL first to down-select candidate graphs.
- **Worker fanout**: 8B instance pool (3 Ollama workers on PortalNode-01 per existing `LLM_ROSTER`) processes graphs in parallel; throughput target ≥ 60 graphs/hour/instance → 100 K graphs in ~23 worker-days or ~8 calendar-days with parallelism.
- **70B batching**: group 20–50 graphs per 100 k-context review pass; ≤ 4 passes/hour → ~80 K graphs covered per month of continuous 70B time, or 100 K graphs in ~5–6 weeks. (Acceptable for a longitudinal study.)
- **Incremental / OGrE**: new evidence triggers re-review only of affected graphs; the provenance layer determines what is stale.

---

## 9. Statistical Plan (deterministic, not LLM)

- **Primary endpoints**: 12-month PRO delta (PROMIS-HAQ, RAPID3); flare-free survival; therapy persistence.
- **Models**: mixed-effects for repeated PRO; Cox for time-to-event; causal-forest or targeted-learning for pathway comparisons (pre-registered).
- **Graph-structure features**: node-type entropy, edge-kind distribution, arc-count profile, graph edit distance to cohort centroid.
- **Trajectory clustering**: DTW over node-type sequences; HDBSCAN over feature vectors.
- **Sensitivity**: re-run with stricter timestamp completeness thresholds; re-run with MKG-citation coverage ≥ 0.8.
- **Multiple testing**: FDR (BH) across pre-registered hypotheses; exploratory findings reported separately.

All statistical code is Python/R, deterministic, with fixed seeds. No LLM participates in effect-size estimation.

---

## 10. Provenance, Reproducibility, Privacy

- Every graph mutation, every MKG query, every agent call is recorded by **ProvenanceEngine** with `(run_id, model, prompt_hash, retrieval_ids, timestamp, operator)`.
- `eoh-llama-*` calls are **temperature = 0, fixed seed**; model weights hashed and version-pinned.
- All PHI stays on PortalNode-01; only de-identified aggregate results leave the box.
- IRB: umbrella protocol + site amendments for FORWARD and RISE.
- Data-deletion path: cascade on consent withdrawal via `consent_scope`.

---

## 11. Deliverables

1. **Cohort dashboard** (on-prem) — per-cohort counts, trajectory class distributions, KM curves, divergence ledger heatmaps.
2. **Per-patient report** — graph snapshot + divergence diff + recommended actions (clinician-reviewed).
3. **Study dataset** — feature-level, de-identified, export-ready.
4. **Agent/model cards** — for `eoh-llama-8b`, `eoh-llama-70b`, EoH modules used, with eval metrics.
5. **Pre-registration document** (this file is the skeleton).
6. **Publication package** — methods, results, data-sharing appendix.

---

## 12. Study-Specific Instantiations

### 12.1 FORWARD — LGC-TPO/RA-PRO
- Target codes: ICD-10 M05.*, M06.*; RxNorm DMARD/biologic/JAKi/TNFi classes; LOINC CRP/ESR/Hgb/ALT/Cr/platelets.
- PRO instruments: PROMIS-HAQ, RAPID3, Pain-intensity, Fatigue-SF, PASS (Patient Acceptable Symptom State).
- Primary endpoint: 12-month PROMIS-HAQ delta by therapy pathway × baseline trajectory phenotype.

### 12.2 RISE — LGC-TPO/RISE-QM
- Target measures: ACR quality measures (disease activity documented, functional-status documented, TB screening before biologic, glucocorticoid management).
- Primary endpoint: divergence footprint vs. guideline + downstream outcome coupling.

Both studies reuse **the same ingestion, the same enrichment, the same agent stack**. Only the motif + the endpoint differs.

---

## 13. Risks, Limitations, Open Questions

- **Unknown-timestamp fraction (~27 % in the reference graph; ~36 % in the earlier prototype)**: impacts latency analyses; H4 turns this into a signal, but it still caps precision.
- **Arc coverage is presently ICD-family-dominated**: 142 arcs but almost all `arc_icd_*`. Therapy, flare, workup, and study-epoch arc families (§6.4) are needed before H3/H5/H6 can be tested at full resolution.
- **Arc slots currently empty**: `summary`, `open_questions`, `cross_arc_edges` are present as fields but unpopulated in seeded arcs. The 8B agent must be the primary author of `open_questions`, and `cross_arc_edges` is where cohort-level graph comparisons will live.
- **Regex-derived codes**: will have false positives/negatives; MKG confirmation + EoH module review required; we track `code_confidence` explicitly.
- **`entity_keys` coverage is uneven**: ICD keys are broad; LOINC/RxNorm/SNOMED need the same enrichment pass before motif queries are symmetric.
- **RxNorm normalization**: local RxNav snapshot must be versioned; interaction tables are date-stamped.
- **Guideline drift**: MKG guideline nodes have `valid_from`/`valid_to`; divergence is always computed against guideline-of-record at event time.
- **Selection bias**: graphs come from the data sources available to FORWARD/RISE; we describe the sampling explicitly and report external validity limits.
- **Open question**: how much of the 100 K corpus has sufficient PRO density to support journal-node analyses? The first deliverable is a feasibility audit (one week).

---

## 14. Milestones (from LOI → results)

| week | milestone                                                                 |
|-----:|---------------------------------------------------------------------------|
|   0  | IRB/DUA drafts; this proposal locked                                      |
|   1  | feasibility audit over existing 100 K graphs (features, missingness)      |
|   2  | schema v+1 shipped (§6); new fields available; back-compatible            |
|   3  | LOINC/RxNorm regex + MKG enrichment pass at scale                         |
|   5  | 8B + 70B pipeline live against study cohort; per-graph output validated   |
|   8  | first cohort-level results; divergence ledger v1                          |
|  12  | interim analysis; pre-registered hypotheses tested                        |
|  20  | final readout; manuscript draft                                           |

---

## 15. Appendix — Full-Schema → Study-v1 Schema Diff (informal)

Reference graph (baseline, **already present**):
```
events["..."].annotations.card                  = {ts, icd, drug, type, title, arc_ids, one_line, salience}
events["..."].annotations.salience              = float
events["..."].annotations.canonical_id          = "ev_..."
events["..."].annotations.entity_keys           = ["icd:k81_0", ...]
events["..."].annotations.arc_ids               = ["arc_icd_...", ...]
events["..."].annotations.status_flags          = ["continued" | "chronic" | "stopped" | "acute"
                                                   | "worsening" | "flare" | "improving"]
events["..."].annotations.collapsed_into        = [...]
events["..."].annotations.suppressed_events     = [...]
events["..."].connascence.in_workup_for         = [...]
events["..."].connascence.caused_by             = [...]
arcs["arc_..."]                                  = {name, arc_id, status, summary, event_ids,
                                                    date_range, open_questions, cross_arc_edges}
metadata.index.by_arc                            = {arc_id: [event_ids]}
metadata.pro                                     = {source, forward.patient_reported_outcomes_channel,
                                                    mirrored_journal_ids}
```

Study-v1 additions (all **non-breaking**):
```
+ events["..."].annotations.entity_keys          # extend to universal coverage for loinc/rxnorm/snomed/cpt/ndc
+ events["..."].annotations.code_confidence      # 0..1 per code
+ events["..."].annotations.extracted_by         # {regex|mkg|eoh|llm|curated}
+ events["..."].annotations.provenance_run_id

+ events["..."].annotations.value / unit / reference_low / reference_high / abnormal_flag / collected_at   # lab
+ events["..."].annotations.rxnorm_cui / ingredient / dose_mg / dose_unit / frequency_per_day /
                              start_date / stop_date / reason_for_stop / prescriber_role                   # medication
+ events["..."].annotations.instrument / subscale / raw_score / t_score / mcid_met / self_reported_at      # pro/journal

+ events["..."].annotations.card.coverage        # {has_dose, has_value, has_date, has_code}
+ events["..."].annotations.status_flags          # broaden vocab: dose_changed, held, titrating, rechallenged,
                                                   #                ineffective, intolerance

+ events["..."].connascence.causal_hypothesis
+ events["..."].connascence.guideline_expected_next
+ events["..."].connascence.observed_vs_expected
+ events["..."].connascence.flare_window
+ events["..."].connascence.therapy_episode
+ events["..."].connascence.lab_response_window
+ events["..."].connascence.ae_suspected
+ events["..."].connascence.pro_shift
+ events["..."].connascence.cohort_peer

+ events["pro_*"]          = { event_type: "pro",          ... }
+ events["journal_*"]      = { event_type: "journal",      ... }
+ events["flare_*"]        = { event_type: "flare",        ... }
+ events["ae_*"]           = { event_type: "adverse_event",... }
+ events["tepi_*"]         = { event_type: "therapy_episode", ... }
+ events["divergence_*"]   = { event_type: "divergence",   ... }
+ events["goal_*"]         = { event_type: "goal",         ... }
+ events["consent_*"]      = { event_type: "consent",      ... }
+ events["derived_*"]      = { event_type: "derived_metric", ... }

+ arcs["arc_therapy_*"]    = {...}                         # therapy-course arc family
+ arcs["arc_flare_*"]      = {...}                         # flare-window arc family
+ arcs["arc_workup_*"]     = {...}                         # workup arc family
+ arcs["arc_study_epoch_*"]= {...}                         # outcome epochs
+ arcs["arc_..."].summary              # populated by 8B, cited, locked by clinician
+ arcs["arc_..."].open_questions       # populated by 8B, consumed by 70B
+ arcs["arc_..."].cross_arc_edges      # {peer_arc_id, kind: triggers|contraindicates|shares_therapy|...}
+ arcs["arc_..."].status               # machine: seeded → enriched → reviewed → locked

+ features = { node_type_counts, temporal_density, unknown_timestamp_frac,
               unique_{icd,rxnorm,loinc}_count, canonical_id_multiplicity,
               entity_key_coverage_by_type, arc_count_by_family, arcs_open_questions_count,
               status_flag_distribution, latency_profile, eoh_emissions }

+ metadata.schema_version
+ metadata.study_cohorts = ["FORWARD_RA_2026", "RISE_QM_2026"]
+ metadata.consent       = { scope, irb_id, date, withdrawable }
+ metadata.deid_level, metadata.site_id, metadata.enrollment_date
```

All additions are **opt-in** and do not break the current reader.

---

**End of proposal. Ready for FORWARD / RISE review.**
