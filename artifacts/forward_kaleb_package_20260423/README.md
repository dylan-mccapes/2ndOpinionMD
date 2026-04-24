# FORWARD Pilot Bundle for Dr. Kaleb Michaud — 2026-04-23

This package contains everything needed for Dr. Michaud's conference presentation
and FORWARD pilot shape review following our 2026-04-22 meeting. It shows the
PatientTimelineVision (PTV) schema working on **two very different surfaces**:

1. A **clean, registry-shaped synthetic PRO cohort** (what FORWARD pilot patients
   will look like once ingested).
2. A **messy, real 200-page multi-source EHR** rendered into the same schema,
   with PII scrubbed, all arcs retired, and a flat `metadata.code_index` in
   their place.

The pairing is intentional: it demonstrates that one contract handles both
surfaces without structural changes.

---

## Contents

```
forward_kaleb_package_20260423/
├── README.md                                                         ← this file
├── MANIFEST.json                                                     ← machine-readable package manifest
├── PTV_REAL_EHR_20260423.json                 ← the real EHR PTV (PII-scrubbed, no arcs, indexed)
│
├── synthetic_pro_cohort/
│   ├── MANIFEST.json
│   ├── ptv_synth_P1_early_responder.json
│   ├── ptv_synth_P2_escalation_single_flare.json
│   ├── ptv_synth_P3_cycler_multi_flare.json
│   ├── ptv_synth_P4_subclinical_flare_uc_wins.json
│   └── ptv_synth_P5_honest_uncertainty_missing.json
│
└── reports/
    ├── REPORT_FORWARD_EXEMPLAR_5PT_FOR_KALEB_20260422.md
    ├── REPORT_FORWARD_EXEMPLAR_5PT_FOR_KALEB_20260422.pdf
    ├── HANDOUT_FORWARD_EXEMPLAR_KALEB_SLIDE_BULLETS_20260422.md
    └── REPORT_REAL_EHR_PTV_ANATOMY_20260423.pdf
```

The real-EHR PTV graph sits at the **package root** so it is the first thing a
reader sees; the reports describing both surfaces live in `reports/`.

---

## 1. The real EHR PTV (package root)

`PTV_REAL_EHR_INDEXED_NOARCS_SCRUBBED_20260423.json`

- Single real patient, 200-page EHR ingestion, rendered into the PTV schema.
- `patient_id`: internal 2ndOpinionMD UUID (random; not linkable to identity
  without our internal mapping — and the mapping is not shared in this bundle).
- Schema: `ptv.2.1-indexed-v1-noarcs` (all arcs retired; flat `metadata.code_index`
  at drugs / RxNorm / ICD / labs / LOINC).
- **632** clinical events (diagnoses, meds, labs, immunizations, POLST, etc.)
  with per-event annotations (salience, canonical_id, entity_keys,
  heuristic_source, status_flags) and connascence edges.
- `code_index` coverage:

  | bucket  | keys | entries |
  |---------|-----:|--------:|
  | drugs   |   63 |     157 |
  | rxnorm  |   48 |     139 |
  | icd     |   73 |     162 |
  | labs    |    6 |       6 |
  | loinc   |    6 |       6 |

### PII posture

- Scrubber: `server/scripts/scrub_real_ptv.py` — 27 deterministic rules.
- **740 replacements** across names, MRN, DOB (labeled / bare / ISO), phone,
  street, city/state/ZIP, facility, provider names, source filename, and
  structural metadata (collapsed `metadata.patient` to `{dob: [DOB_REDACTED]}`
  and purged any DOB-year index keys).
- Audit result: **CLEAN** — zero leftover hits on every audit pattern. The
  scrub provenance (scrubber path, date, rule count, replacement counts by
  rule) is **baked into `metadata.pii_scrubbed`** on the document itself, so
  the audit trail travels with the graph and does not need a sidecar file.

---

## 2. Synthetic PRO cohort (`synthetic_pro_cohort/`)

Five patients × five years × ten semi-annual FORWARD rounds, per the pilot scope
agreed with Kaleb on 2026-04-22:

- Instruments: HAQ-II, VAS Pain, VAS Patient Global, PAS-II, RDCI
- Out of scope for the pilot: labs, imaging, biosamples, -omics, DAS28
- Schema: `ptv.2.1-forward-exemplar`

| code | phenotype                     | headline                                                                 |
|------|-------------------------------|--------------------------------------------------------------------------|
| P1   | early_responder               | Early MTX responder; five-year improving trajectory; narrow UCs.         |
| P2   | escalation_single_flare       | One flare at year 2 triggers adalimumab add-on; trajectory returns.      |
| P3   | cycler_multi_flare            | Three flares over five years; TNFi → TNFi → JAKi; wide UCs.              |
| P4   | subclinical_flare_uc_wins     | UC elevated flare probability at rounds 3–4; overt flare at round 5.     |
| P5   | honest_uncertainty_missing    | Rounds 4 and 6 missing; UC widths widen with "insufficient data" basis.  |

See `synthetic_pro_cohort/MANIFEST.json` for full cohort metadata and per-patient
event / arc counts.

---

## 3. Reports (`reports/`)

- **`REPORT_FORWARD_EXEMPLAR_5PT_FOR_KALEB_20260422.{md,pdf}`** — narrative
  walkthrough of the five synthetic PRO graphs: what each phenotype shows,
  how Uncertainty Carriers behave, and what to say on stage.
- **`HANDOUT_FORWARD_EXEMPLAR_KALEB_SLIDE_BULLETS_20260422.md`** — one-page
  speaker bullets for the slide that introduces the PTV schema.
- **`REPORT_REAL_EHR_PTV_ANATOMY_20260423.pdf`** — anatomy of the real EHR
  graph sitting at the package root: why arcs were retired wholesale, what
  `metadata.code_index` adds, and how agents keep the index in sync via
  `code_index_ops.register_code_on_event`.

---

## 4. Why both graphs together

| surface                    | what it proves                                                              |
|----------------------------|------------------------------------------------------------------------------|
| Synthetic PRO cohort       | Schema works on pristine, registry-shaped FORWARD data with UCs and flare-anticipation arcs. |
| Real EHR PTV (scrubbed)    | Same schema handles noisy multi-source clinical timelines at scale — after arcs were retired and replaced by a flat code_index. |

Kaleb's slide narrative: **one contract, two surfaces.** The synthetic cohort is
what the FORWARD pilot will look like; the real EHR graph is what we already
ingest today.

---

## 5. Provenance & disclaimers

- Synthetic patients are programmatically generated for illustration of the
  PTV schema and the Uncertainty-Carrier governance framework
  (SSRN 6554940). No real patient records were used, referenced, or derived
  from for the synthetic cohort.
- The real EHR PTV is PII-scrubbed per a deterministic rule set audited to
  zero leftovers on known PII tokens. The original source filename is
  structurally replaced with `patient_record_redacted.pdf`. The full audit
  trail lives on the document under `metadata.pii_scrubbed`.
- Not for clinical decision-making. Intended use: conference presentation and
  FORWARD pilot shape review.
