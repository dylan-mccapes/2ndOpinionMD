# REPORT — FORWARD Exemplar Cohort (5 patients × 5 years of PROs) for Kaleb Michaud

**Date:** 2026-04-22
**Prepared by:** 2ndOpinionMD Platform Team
**For:** Kaleb Michaud, PhD — FORWARD / UNMC
**Context:** Upcoming RA conference presentation and Congressional briefing, in which Kaleb will present our Uncertainty-Carrier governance paper (SSRN 6554940) and reference the 2ndOpinionMD system.
**Pilot scope (as agreed on the 2026-04-22 call):** **5 patients × 5 years × Patient-Reported Outcomes only.** No labs, no imaging, no biosamples, no -omics.

---

## 0. What you have received

A cohort of **five synthetic PatientTimelineVision (PTV) graphs**, one per patient, plus a manifest:

```
artifacts/forward_exemplar_5pt/
  MANIFEST.json
  ptv_synth_P1_early_responder.json              ~54 events / 14 arcs
  ptv_synth_P2_escalation_single_flare.json      ~56 events / 15 arcs
  ptv_synth_P3_cycler_multi_flare.json           ~64 events / 19 arcs
  ptv_synth_P4_subclinical_flare_uc_wins.json    ~58 events / 15 arcs   ← HERO
  ptv_synth_P5_honest_uncertainty_missing.json   ~48 events / 15 arcs   ← HERO
```

Every file has:
- `metadata.synthetic: true`
- `metadata.disclaimer: "SYNTHETIC demonstration cohort..."`
- `metadata.schema_version: "ptv.2.1-forward-exemplar"`
- `metadata.pro.source: "forward_synthetic"`
- `metadata.pro.forward.patient_reported_outcomes_channel: true`
- `metadata.pro.instruments`: HAQ-II, VAS Pain, VAS Patient Global, PAS-II, RDCI
- `metadata.generator.seed`: per-patient seed (artifacts are reproducible bit-for-bit)

The generator script lives at `server/scripts/gen_forward_exemplar.py`; the same pipeline that will ingest FORWARD's anonymized CSV/Parquet export emits these graphs.

---

## 1. Purpose of this exemplar (what it is; what it is not)

**It is** a precise, reproducible demonstration of the shape of a FORWARD-ingested patient graph in our system:

- Five-year longitudinal trajectories built from **PRO questionnaires only** (HAQ-II, VAS Pain, VAS Patient Global, PAS-II, RDCI), mirroring the FORWARD semi-annual structure.
- **Uncertainty-Carrier (UC) emissions** computed deterministically from the PRO composite, with calibrated 90 % bands and a `basis` list that cites the evidence events.
- **Clinical arcs** populated (not just seeded): `summary`, `open_questions`, and `cross_arc_edges` all carry content.
- **Provenance** on every node and edge (`extracted_by`, `canonical_id`, `discovered_by`, `generator.seed`).

**It is not** a real-patient dataset. No real patient records, FORWARD or otherwise, were used in generation. Trajectories are clinically plausible but entirely programmatic. The artifacts are intended for presentation and pilot-shape review, not clinical decision-making, and they are labeled as such in metadata.

---

## 2. The five patients, at a glance

| # | phenotype                                     | one-line headline |
|---|-----------------------------------------------|--------------------|
| P1 | Early MTX responder                          | Five-year improving trajectory; narrow UCs throughout. |
| P2 | MTX → TNFi escalation with one flare         | Single flare at year 2 triggers adalimumab add-on; trajectory returns to baseline. |
| P3 | Cycler with three flares                     | TNFi → TNFi → JAKi; wide UCs reflect disease volatility. |
| **P4** | **Subclinical flare predicted by UC (HERO)** | **UC elevated flare probability at rounds 3–4; overt flare at round 5.** |
| **P5** | **Honest uncertainty with missing data (HERO)** | **Rounds 4 and 6 questionnaires missing; UC widths widen and basis cites insufficient data.** |

Two "hero" patients (P4 and P5) carry the governance story; the three supporting patients (P1–P3) show heterogeneity of trajectory and provide a sense of cohort spread.

---

## 3. P4 — the subclinical-flare governance story (what we recommend leading with)

### 3.1 Trajectory

Ten semi-annual PRO rounds over five years. Stable HAQ-II and VAS scores at rounds 0–2. At rounds 3 and 4, scores **drift within each patient's own trajectory but stay below the HAQ-II and VAS-pain MCID thresholds** (0.22 and 20 points). At round 5, both thresholds are crossed and therapy escalation is recorded.

### 3.2 UC emissions (extracted from the graph)

| round | UC point estimate | 90 % band | confidence | anticipation? | key basis lines |
|------:|------------------:|:----------|:-----------|:-------------:|:----------------|
| 0 | 0.05 | [0.02, 0.15] | low | — | baseline; insufficient trajectory data |
| **3** | **0.22** | **[0.20, 0.24]** | **high** | **yes** | HAQ-II delta 0.50 MCID units; VAS pain delta 0.47 MCID units |
| **4** | **0.37** | **[0.34, 0.40]** | **high** | **yes** | HAQ-II delta 0.91 MCID units; VAS pain delta 0.92 MCID units |
| 5 | 0.87 | [0.78, 0.95] | high | — (overt flare) | HAQ-II delta 2.50 MCID units; VAS pain delta 2.17 MCID units |
| 9 | 0.32 | [0.24, 0.40] | high | — | post-escalation recovery trajectory |

### 3.3 The governance line

The UC emitted at **rounds 3 and 4** — two full semi-annual cycles before the overt flare at round 5 — is the governance artifact. It is:

- **Deterministic.** No LLM was consulted to produce it; it is a MCID-normalized composite over the PRO trajectory, with the UC width widening as variance grows.
- **Cited.** Every UC node carries `evidence_event_ids` pointing to the PRO events that drove the band, plus `governance_ref: "SSRN 6554940"`.
- **Honest.** Round 0 ships with `confidence: "low"` and the basis line "baseline round; insufficient trajectory data" — the system does not fake early certainty.
- **Graph-native.** `arc_flare_r05.cross_arc_edges` links the overt-flare arc to the study-epoch arcs at rounds 3 and 4 with `kind: "pre_flare_anticipation"` and `evidence_event_id` pointing to the anticipation UCs. The pre-flare signal is a first-class graph edge, not a footnote.
- **Open-question bearing.** `arc_flare_r05.open_questions` contains: *"Earlier UC-anticipated rounds 3–4 suggest a pre-flare signal; would earlier escalation have prevented this event?"* — the system authors its own agenda for follow-up review.

### 3.4 What this lets Kaleb say on stage

*"Here is a five-year FORWARD-shaped patient trajectory. The uncertainty-carrier framework emitted a flare probability of 0.22 at round 3 and 0.37 at round 4 — two full semi-annual cycles before the overt flare at round 5. The carrier cites the evidence events, states its confidence, and — when it has nothing to go on — says so explicitly. This is what clinical decision support looks like when you mandate uncertainty carriers. The alternative — a single point prediction with no basis — suppresses exactly the information a clinician needs."*

---

## 4. P5 — the honest-uncertainty backup story

### 4.1 Situation

Patient does not complete questionnaires at rounds 4 and 6. The graph records two `administrative` events labeled *"Questionnaire round N: not completed"* rather than interpolating or guessing.

### 4.2 UC behavior

| round | UC point estimate | 90 % band | confidence | basis |
|------:|------------------:|:----------|:-----------|:------|
| 0 | 0.05 | [0.02, 0.15] | low | baseline; insufficient trajectory data |
| **7** | **0.67** | **[0.54, 0.81]** | **moderate** | HAQ-II delta 2.09 MCID units; VAS pain delta 1.45 MCID units; **UC width widened due to missing recent questionnaire(s)** |
| 9 | 0.65 | [0.56, 0.75] | high | missingness cleared; band narrows |

### 4.3 The governance line

The UC width at round 7 is wider than the width at round 9 even though the point estimates are nearly identical — **because the information available is different**, and the framework refuses to paper over that difference. The basis line says so explicitly.

### 4.4 What this lets Kaleb say on stage

*"The system's job is not to maximize confidence. It is to communicate the confidence that the evidence supports. When a patient misses two questionnaires, the UC band widens and the basis line records the missingness. When the data returns, the band narrows. An output that pretends certainty it does not have is a patient-safety failure."*

---

## 5. Schema cheat sheet (for any slide that shows JSON)

| field | meaning |
|---|---|
| `arcs[*].status` | `seeded → enriched → reviewed → locked` — lifecycle state |
| `arcs[*].summary` | human-readable arc synthesis, cited |
| `arcs[*].open_questions` | agenda items the system flags for review |
| `arcs[*].cross_arc_edges` | typed inter-arc relations (`treated_by`, `initiated_in_response_to`, `pre_flare_anticipation`) |
| `events[*].card` | 100–200 token per-event digest |
| `events[*].salience` | numeric priority score |
| `events[*].canonical_id` | cross-source dedup handle |
| `events[*].entity_keys` | normalized codes (`icd:*`, `rxnorm:*`, `instrument:haq2`, `round:3`) |
| `events[*].annotations.kind` | for `derived_metric` nodes, identifies the carrier class (`uncertainty_carrier`) |
| `events[*].annotations.basis` | UC's cited evidence list |
| `events[*].annotations.governance_ref` | pointer to SSRN 6554940 |

Screenshotting a slice (e.g. a single UC node plus the flare arc it attaches to) is sufficient for a slide — the compact `card` and the cited `basis` together read as a self-contained governance artifact.

---

## 6. What changes when real FORWARD data replaces synthetic

Essentially nothing structural. The same generator-free ingestion pipeline emits identically-shaped graphs; real trajectories replace programmatic ones; `metadata.synthetic` flips to `false`; RxNorm CUIs come from our local RxNav snapshot rather than the generator's compact map. All UC computation, arc enrichment, and cross-arc edge inference are the same deterministic code paths.

### 6.1 Pilot-data shape we would like (recap of the DRS)

- **n = 5 patients** with RA (ICD-10 M05.* or M06.*), anonymized track
- **5 years** of follow-up, ~10 semi-annual questionnaires per patient
- **Primary variables:** HAQ-II raw, VAS Pain (0–100), VAS Patient Global (0–100), PAS-II, RDCI components
- **Treatment:** start/stop dates for DMARDs, biologics, JAKi, steroids; dose where recorded
- **Format:** CSV or Parquet; long format (one row per patient × round × instrument); ISO-8601 dates; explicit units in column names
- **Out of scope (confirmed):** labs, imaging, biosamples, -omics, DAS28

### 6.2 Turnaround once data is in hand

Pilot ingest → 5 production (non-synthetic) FORWARD PTV graphs: **≤ 48 hours** from receipt. UC emission, arc enrichment, manifest regeneration included.

---

## 7. How we suggest Kaleb uses these artifacts

1. **Lead with P4** on the governance slide. One JSON snippet of the `P4_uc_r03` node plus the `arc_flare_r05` arc summary, side by side, is the one-slide version of the whole UC argument.
2. **Use P5 on the "what happens when we don't know" slide.** Show the widened band at round 7 plus its basis list; show the narrowed band at round 9 once data returns.
3. **Show the cohort as a table** (P1–P5, phenotype, # flares, mean UC width) on the "heterogeneity, honestly reported" slide — the manifest file has these values.
4. **Cite SSRN 6554940** on every slide that shows a UC node; the graphs do this automatically via `governance_ref`.
5. **If asked "is this real data?"**, the answer is in `metadata.synthetic` and in every filename. No ambiguity.

---

## 8. Reproducibility and attribution

- Every artifact is reproducible bit-for-bit from `server/scripts/gen_forward_exemplar.py` at git HEAD on 2026-04-22.
- Seeds are fixed per patient and recorded in `metadata.generator.seed`.
- RxNorm CUIs are listed by ingredient in the generator source and should be validated against the local RxNav snapshot prior to any production use.
- For any public rendering, a footer of the form *"Synthetic exemplar cohort; 2ndOpinionMD + FORWARD pilot preview; generator seed {seed}; SSRN 6554940"* is sufficient attribution.

---

*Prepared 2026-04-22 in preparation for Andras's 2026-04-24 (Friday) email to Kaleb Michaud. The companion one-page slide-ready handout is at `HANDOUT_FORWARD_EXEMPLAR_KALEB_SLIDE_BULLETS_20260422.md`.*
