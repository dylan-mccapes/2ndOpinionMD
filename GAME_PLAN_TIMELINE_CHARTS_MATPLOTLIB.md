# Game Plan: Timeline Graph Analytics + Matplotlib Charts

**Date:** 2026-02-20  
**Status:** Proposed  
**Owner:** Product + Andras + Devin  

---

## What This Is

This plan adds clinically honest, graph-grounded timeline analytics and chart exports for patient and doctor portals.

Positioning: **decision support / visualization**, not diagnosis.

Data sources are explicitly tied to existing 2OPMD structures:
- `ehr.patient_timeline` (events, timestamps, structured JSONB, embeddings)
- `PatientTimelineVision` connascence edges (`temporal`, `diagnostic`, `treatment`, `lab_trend`; with reserved `causal`, `symptom_cluster`)
- Diagnostic landscape outputs from timeline/EoH routes (`/api/eoh/landscape/{patient_id}`, timeline context)

---

## Graph Model (Grounded in Current Repo)

### Event Nodes

From `ehr.patient_timeline`:
- `id`, `patient_id`, `ts`, `event_type`, `source`, `structured`, `text`, `meta`

Typical node classes in current timeline:
- `symptom`, `lab`, `medication`, `flare`, `visit`, `journal`, `note`, `imaging`, `med_change`

### Edge Types (Connascence)

From `server/eoh/patient_timeline_vision.py` and connascence rubric:
- `temporal`
- `diagnostic`
- `treatment`
- `lab_trend`
- (reserved/future) `causal`, `symptom_cluster`

### Terrain / Landscape

From timeline engine and EoH:
- Diagnostic landscape probabilities from event-derived signals
- Longitudinal trajectory snapshots where available

---

## 1) What To Model From The Timeline Graph

### A. Stability and turbulence

Goal: show when a patient is stable vs volatile.

Compute:
- Event-rate intensity per window (day/week)
- Edge-load intensity per window (sum of weighted connascence edges)
- Change-point detection over feature windows (phase shifts)
- Coherence score (pattern recurrence vs fragmentation)

Outputs:
- Stability band timeline (`stable`, `transition`, `volatile`)
- Phase-shift markers with evidence bundles

### B. Flares vs noise

Goal: separate meaningful episodes from background chatter.

Compute:
- Event cluster density + persistence
- Symptom/lab co-movement persistence across adjacent windows
- Burstiness score (dispersion over Poisson baseline)

Outputs:
- Flare episodes (start/end, confidence, supporting events)
- Noise-floor estimate

### C. Causal-ish sequencing (without causal claims)

Goal: show what tends to precede what.

Compute:
- Lagged association edges: A precedes B within delta t
- Predictive-correlation heuristics (Granger-style language as "predictive", not causal)
- Hazard-style conditional rates (after X, Y in next N days)

Outputs:
- Precedence map with lag distributions and confidence intervals

### D. Diagnostic terrain embedding

Goal: map case movement through diagnostic space.

Compute:
- Feature vector per time window from graph events/edges
- Dimensionality reduction (PCA first; optional UMAP later)
- Zone overlays (stable/transition/flare-like regions)

Outputs:
- Patient trajectory path in 2D
- "Distance traveled" metric

---

## 2) Core Interpretable Metrics

Use explicit, auditable metrics:

1. Drift / velocity  
`v_t = ||x_t - x_(t-1)||`

2. Curvature  
`k_t = ||(x_t - x_(t-1)) - (x_(t-1) - x_(t-2))||`

3. Connascence load  
`L_t = sum(w(e)) for e in E_t`

4. Stability score  
`S_t = 1 / (1 + a*v_t + b*k_t + c*L_t_norm)`

All derived metrics must store provenance:
- window bounds
- contributing event ids
- contributing edge ids/types
- parameter values (`a`, `b`, `c`, smoothing span, thresholds)

---

## 3) What To Render In Portals

### Patient portal (calming view)
- Timeline summary card
- Stability band over time
- Health-map trajectory (plain language)
- "Questions for your doctor" generated from phase-shift evidence

### Doctor portal (high-signal view)
- Phase-shift markers with evidence bundles
- Flare-vs-noise attribution panel
- Precedence map (predictive associations only)
- Differential-friendly event clusters (symptom/lab/med bundles)

---

## 4) Matplotlib Chart Set (MVP)

Server-side chart generation (Matplotlib `Agg`) for deterministic export:

1. `stability_band.png`
- X: time
- Y: normalized stability score
- color bands for stable/transition/volatile
- annotated phase-shift points

2. `event_edge_intensity.png`
- dual axis: event count vs connascence load
- rolling window overlays

3. `precedence_map.png`
- directed graph figure with top lagged associations
- edge labels: median lag + support count

4. `terrain_trajectory.png`
- 2D PCA trajectory with segment coloring by stability class

5. `flare_noise_panel.png`
- episode ribbons + confidence bars + noise floor baseline

All charts include:
- patient_id
- date range
- metric definitions footer
- "decision support, not diagnosis" watermark in export footer

---

## 5) API + Backend Additions

### New analytics endpoints (doctor/patient authorized)

1. `GET /api/timeline/{patient_id}/analytics/summary`
- Returns window metrics (`v_t`, `k_t`, `L_t`, `S_t`) + phase shifts + flare/noise episodes

2. `GET /api/timeline/{patient_id}/analytics/precedence`
- Returns lagged association edges + support stats

3. `GET /api/timeline/{patient_id}/analytics/trajectory`
- Returns embedding points (PCA MVP) + zone labels

4. `POST /api/timeline/{patient_id}/analytics/export`
- Generates doctor-ready PDF package with Matplotlib figures

### Reuse existing modules
- `server/timeline/engine.py` for event loading and landscape primitives
- `server/api/timeline_routes.py` as routing base
- `server/eoh/patient_timeline_vision.py` for connascence edge model
- `server/eoh/PATIENT_TIMELINE_CONNASCENCE_RUBRIC.md` for edge semantics

---

## 6) DALL-E / Visual Assets (Optional, After MVP)

Use only as explainability overlays derived from computed data:
- Health-map poster
- Connascence constellation
- Before/During/After phase storyboard

No clinical claims from generated art.

---

## 7) Minimal Implementation Plan

### Phase 5d.1: Canonical weekly feature vector
- [ ] Build windowing utility over `ehr.patient_timeline`
- [ ] Add connascence aggregation from `PatientTimelineVision`
- [ ] Persist computed vectors in cache table or materialized view (TBD)

### Phase 5d.2: Metric computation
- [ ] Compute `v_t`, `k_t`, `L_t`, `S_t`
- [ ] Change-point detection and phase labeling
- [ ] Flare/noise episode extraction

### Phase 5d.3: Chart renderer (Matplotlib)
- [ ] Add server chart module (`server/timeline/charts.py`)
- [ ] Generate deterministic PNG/SVG outputs
- [ ] Add provenance footer and definition legends

### Phase 5d.4: Portal integration
- [ ] Patient-facing simplified chart cards
- [ ] Doctor-facing detailed analytics panels
- [ ] "View evidence" drill-down to event ids/edge ids

### Phase 5d.5: Export package
- [ ] Doctor-ready PDF summary + charts
- [ ] Include evidence appendix (events, edges, lags, assumptions)

---

## Clinical Safety & Language Guardrails

Required language constraints in UI/API docs:
- Use "predictive association", never "caused by"
- Use "decision support", never "diagnosis"
- Surface confidence and missing-data caveats
- Keep raw evidence traceable to timeline events

---

## Success Criteria

- Charts are generated directly from existing graph/timeline structures
- Every plotted signal is traceable to event and edge provenance
- Patient portal shows calming, non-alarming summary views
- Doctor portal shows high-signal, evidence-linked analytics
- Exports are clinically useful and reproducible

---

**End of Game Plan**
