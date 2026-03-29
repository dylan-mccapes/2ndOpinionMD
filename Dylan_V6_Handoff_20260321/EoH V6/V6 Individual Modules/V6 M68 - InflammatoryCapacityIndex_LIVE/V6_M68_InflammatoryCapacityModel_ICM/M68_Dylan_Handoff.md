# M68 ICM — Dylan Handoff Package

**Module:** M68 — Inflammatory Capacity Model (ICM)
**Version:** 1.1
**Date:** March 2026
**From:** Andras (Product/Architecture)
**To:** Dylan (CTO/Implementation)

---

## What This Is

M68 is a **new V6-only synthesis module** that computes a real-time "remaining headroom" metric for patients — how close they are to a flare or decompensation event, which specific factors are driving them toward overflow, and which intervention lever (inflow reduction, displacement shrinkage, outflow enhancement) would produce the largest improvement. Think of it as the missing bridge between M3 (how unstable you are now) and M66 (what wellness actions to try) — M68 answers "how much capacity do you have left and why is it draining."

The module consumes read-only inputs from M3, M4, M5, M12, M13, M21, M64, wearables, PROs, and labs. It produces ICI (Inflammatory Capacity Index) snapshots for M21, visualization data for M24, engagement signals for M11, activation prompts for M66, and a bidirectional advisory feed with M64. It does not modify any V5.2 logic. Zero backward contamination.

**Full spec:** `V6_M68_InflammatoryCapacityModel_ICM_v1.1.md` (attached)
**Deferred items:** `M68_v2.0_Roadmap.md` (attached — for awareness, not for v1.1 scope)
**M66 practice catalog extension:** `M66_Siddhi_Practice_Taxonomy_Fragment.md` (attached — M66 handoff, not Dylan's build)

---

## Architecture Summary

```
Inputs → Stressor Census → Three-Valve Computation → ICI → Threshold Logic → Outputs
           ↑                      ↑                           ↓
     M4/M5/M12/M64         Infrastructure Vars          M11/M21/M24/M66
     Wearables/PROs         (lymphatic, vagal,
     Labs                    viscosity, backpressure)
                                   ↑
                            Turbulence Regime
                            (non-linear amplification
                             when ICI < threshold)
```

**Core computation pipeline (5 stages):**
1. Ingest signals from 10+ upstream sources, build stressor census
2. Compute three valves (inflow, displacement, outflow) with infrastructure modifiers and turbulence
3. Generate attribution vector (which stressors contribute most to capacity loss)
4. Evaluate threshold crossings, emit engagement signals and M66 prompts
5. Persist to vault, track intervention outcomes, evaluate VWA promotions

**v1.1 additions over v1.0:** Turbulence regime (non-linear inflow amplification), 4 infrastructure variables (lymphatic_tone, vagal_tone, system_viscosity, backpressure), post-overflow hysteresis (temporary ICmax reduction after flare), M64↔M68 bidirectional feed, glymphatic-specific sleep decomposition.

---

## JIRA Epic: EOH-68 — Inflammatory Capacity Model

### Epic Description
Implement M68 ICM v1.1 as specified. Module computes ICI (Inflammatory Capacity Index) from upstream signals, produces threshold-triggered engagement outputs, and manages the VWA (Validated Wellness Action) lifecycle.

---

### Subtask 1: Data Model & Schema Implementation
**Size:** M (3–5 days)
**Dependencies:** None (schemas are self-contained)

Implement the five data schemas:
- D1: Stressor object (with `raw_magnitude` + `effective_magnitude` for turbulence)
- D2: OutflowFactor object (with `sub_factors` support for sleep decomposition)
- D3: ICISnapshot (with all v1.1 fields: infrastructure, turbulence, post-overflow penalty)
- D4: EWAActivationPrompt (with infrastructure deficit fields)
- D5: VWA record (with `infrastructure_target` field)

**ADR-68.1:** Schema storage — do we persist ICI snapshots as FHIR Observations in M21 or as a custom schema? Recommendation: custom schema with FHIR-compatible audit wrapper (Appendix C.11 pattern), since ICI has no natural FHIR resource mapping. Decision needed before subtask 5.

**Definition of Done:** All schemas implemented with validation, unit tests for field constraints (e.g., `raw_magnitude` must be 0.0–1.0, `effective_magnitude` may exceed 1.0 under turbulence).

---

### Subtask 2: Input Ingestion Pipeline
**Size:** L (5–8 days)
**Dependencies:** Existing M3, M4, M5, M12, M13, M21, M64 output contracts

Build the input consumption layer:
- Subscribe to M3 state changes (Band/Stack/pause)
- Subscribe to M5 PSI/persona emissions
- Subscribe to M13 trajectory vector updates
- Subscribe to M64 FUD flag emissions (with mechanism-type filtering for FUD-IR/FUD-GB → backpressure)
- Consume M4 normalized tags
- Consume M12 narrative digests
- Consume M21 historical ICI time-series and calibration data
- Ingest wearable data: sleep (total, deep sleep %, consistency), HRV (RMSSD), activity, sedentary time, breathing rate
- Ingest PRO inputs: stress, mood, energy, symptom severity
- Ingest lab events: CRP, IL-6, ESR, cortisol, tryptase (where available)

**Risk flag:** The wearable integration surface (sleep decomposition into deep sleep %, HRV RMSSD, breathing rate) depends on which wearable platform(s) we're targeting first. Oura and Apple Watch provide these metrics; Fitbit partially; others vary. **Decision needed:** Which wearable platform is the v1.1 target? This scopes the ingestion adapter work.

**Definition of Done:** All input channels operational, data arriving in stressor census format, integration tests covering each source.

---

### Subtask 3: Stressor Census Engine
**Size:** M (3–5 days)
**Dependencies:** Subtask 2

Implement:
- Stressor enumeration from all input channels
- INFLOW vs DISPLACEMENT classification (14-day temporal threshold with override capability)
- Magnitude scoring (weighted combination: direct measurement, self-report, M5 inference, M21 historical calibration)
- Modifiability classification (HIGH/MEDIUM/LOW/NONE with domain tagging)
- Latent stressor discovery pass (M5 inferred vs patient-reported comparison)
- Stressor tagging (`patient_aware`, `patient_confirmed`)

**Definition of Done:** Given a set of test inputs from all channels, census produces correctly classified, magnitude-scored, modifiability-tagged stressor list. Latent stressor discovery fires correctly on test scenarios (T-04).

---

### Subtask 4: Infrastructure Variable Computation
**Size:** M (3–5 days)
**Dependencies:** Subtask 2 (wearable data ingestion)

Implement four infrastructure variables:

**4a. Lymphatic tone** — four-pump decomposition:
- Skeletal muscle pump: f(activity_minutes, sedentary_time, movement_frequency)
- Respiratory pump: f(breathing_rate, depth_proxy)
- Lymphangion contraction: f(vagal_tone) — proxy
- Arterial pulsation: f(resting_HR, HRV)
- Weighted average with governed defaults (skeletal 0.40, respiratory 0.25, lymphangion 0.20, arterial 0.15)

**4b. Vagal tone** — Primary: HRV RMSSD normalized against population reference. Secondary: breathing rate, PRO recovery speed.

**4c. System viscosity** — Loaded from M21 calibration data (ICI recovery rate analysis). Population default 0.3 if insufficient history.

**4d. Backpressure** — f(FUD-IR count, FUD-GB count, FUD severity, medication count, inflammatory marker trajectory). Normalized 0.0–1.0.

**ADR-68.2:** Population reference ranges for vagal tone normalization — do we use age/sex-stratified HRV norms from published literature, or build our own from M21 population data as it accumulates? Recommendation: start with published norms (Shaffer & Ginsberg 2017 HRV reference ranges), switch to internal when N > 500 patients. Decision needed before deployment.

**Definition of Done:** All four variables computing, unit tests for edge cases (missing wearable data, no M21 history, zero FUD flags). T-14 passing.

---

### Subtask 5: Three-Valve Computation Engine with Turbulence
**Size:** L (5–8 days)
**Dependencies:** Subtasks 1, 3, 4

Core computation pipeline:
- Inflow rate aggregation with recency weighting
- Turbulence regime detection and coefficient computation
- Effective inflow = raw × turbulence_coefficient (per-stressor `effective_magnitude` update)
- Displacement volume with trajectory adjustment
- Raw outflow aggregation with factor class weights and sub-factor support
- Effective outflow = raw × (1 - backpressure) × (1 - viscosity) × infrastructure_modifier
- Post-overflow penalty application (ICmax reduction + decay)
- ICI computation, band assignment
- Overflow probability model (M21-calibrated)
- Time-to-overflow estimation

**Governed parameters (must be configurable, not hard-coded):**
- Turbulence threshold (default: 50%)
- Max turbulence gain (default: 0.8)
- Post-overflow penalty initial value (default: 0.15)
- Post-overflow recovery window (default: 14 days)
- ICI band thresholds (default: 65/50/35)
- Factor class weights (defaults in spec)
- Infrastructure modifier formula weights
- Inflow/displacement/outflow meta-weights (patient-calibrated via M48)

All governed parameters stored in Appendix F.68 configuration (to be created as config surface, not hard-coded).

**Definition of Done:** Complete ICI computation producing correct values for all test scenarios. T-01, T-02, T-03, T-11, T-12, T-13, T-14, T-15 all passing.

---

### Subtask 6: Attribution & Stressor Discovery
**Size:** S (2–3 days)
**Dependencies:** Subtask 5

- Attribution vector generation (per-stressor contribution to total capacity loss, including turbulence multiplier visibility)
- Top-5 stressor ranking by effective magnitude
- Top-3 outflow deficit identification
- Latent stressor surfacing pipeline (candidate stressors → M11/M24 with framing templates)

**Definition of Done:** Attribution vector accounts for ≥90% of capacity loss (T-04 variant). Latent stressor pipeline fires correctly on test scenario (T-04).

---

### Subtask 7: Threshold Logic & Output Routing
**Size:** M (3–5 days)
**Dependencies:** Subtask 5

- Band transition detection (GREEN→YELLOW→ORANGE→RED)
- Patient engagement signal emission to M11/M24 (band-appropriate messaging)
- Turbulence transparency messaging per Invariant I-G
- M66 Activation Prompt generation (D4) with valve context, infrastructure deficits, VWA-first priority
- M68→M64 advisory emission when backpressure > 0.6
- RED band clinician escalation via M6/M10 pathway

**Definition of Done:** T-05, T-07, T-08, T-09, T-15, T-16 all passing.

---

### Subtask 8: VWA Lifecycle Management
**Size:** M (3–5 days)
**Dependencies:** Subtasks 5, 7

- Intervention-outcome correlation tracking (action → ICI change, with timing and confounder control)
- VWA promotion gate evaluation per Invariant I-F (≥3 attempts, ≥2 correlated improvements, no adverse effects, no clinician contraindication)
- VWA maintenance cycle (90-day re-evaluation)
- VWA deprecation when correlation degrades (3+ consecutive non-correlated attempts)
- VWA-first recommendation priority in M66 activation prompts

**Definition of Done:** T-06, T-07, T-10 all passing.

---

### Subtask 9: Vault Persistence & Audit
**Size:** M (3–5 days)
**Dependencies:** Subtask 5

- ICISnapshot (D3) write to M21 with full provenance
- Audit event emission for all ICM events per spec (ICI computations, turbulence transitions, infrastructure changes, threshold crossings, M64/M66 activations, VWA promotions, overflow events, calibration updates)
- FHIR-compatible audit wrapper per Appendix C.11 pattern
- Post-overflow penalty initialization and decay tracking

**ADR-68.3:** ICI computation frequency — how often do we recompute? Options: (a) event-driven (recompute on any input change), (b) scheduled (every 4–6 hours), (c) hybrid (scheduled + triggered by significant input changes). Event-driven is most responsive but may create unnecessary computation load. Recommendation: hybrid — scheduled every 6 hours + triggered by M3 band change, M5 PSI change ≥1, new M64 FUD flag, or patient PRO submission.

**Definition of Done:** Full audit trail for all ICM events. Vault entries include complete provenance. Computation frequency implemented per ADR decision.

---

### Subtask 10: M24 Visualization Data Contract
**Size:** S–M (2–4 days)
**Dependencies:** Subtask 5

Define and implement the data contract M24 needs for the patient-facing ICI visualization:
- Current ICI value + band + trend arrow
- Top stressors (attribution vector, simplified for patient comprehension)
- Infrastructure gauges (lymphatic tone, vagal tone — simplified as "drainage efficiency" and "calm capacity")
- Turbulence indicator ("your system is more reactive right now")
- Time-to-overflow estimate (if applicable)
- VWA quick-access (top 3 validated actions)
- Outflow deficit highlights ("your sleep quality has dropped — this is reducing your recovery")

**Note:** M24 owns the actual visualization design and rendering. M68 provides the data contract only.

**Definition of Done:** Data contract documented, mock payloads generated for all ICI band states (GREEN/YELLOW/ORANGE/RED) including turbulence and post-overflow scenarios.

---

### Subtask 11: Calibration Telemetry Pipeline
**Size:** S (2–3 days)
**Dependencies:** Subtask 9

Wire calibration data to M48:
- Predicted vs actual overflow events (for overflow probability model calibration)
- Infrastructure variable stability metrics (CV across consecutive days)
- Turbulence threshold accuracy (does the current threshold predict turbulence-regime periods that precede overflows?)
- VWA correlation persistence (do validated actions stay validated?)

**Definition of Done:** Telemetry flowing to M48 intake. Metrics reportable.

---

### Subtask 12: Acceptance Tests & Metrics
**Size:** M (3–5 days)
**Dependencies:** All above

Stand up all 16 acceptance tests (T-01 through T-16) and tracked metrics. Create test fixtures for:
- Band-1-but-low-ICI patient (T-01)
- Three-valve isolation scenarios (T-02)
- Retrospective overflow validation (T-03, requires M21 test data)
- Latent stressor discovery (T-04)
- Turbulence amplification + type independence (T-11, T-12)
- Post-overflow hysteresis (T-13)
- Infrastructure variable isolation (T-14)
- M64 bidirectional feed (T-15, T-16)

**Definition of Done:** All 16 tests passing. Metrics pipeline operational.

---

## Dependency Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| **Wearable platform selection** — deep sleep %, RMSSD, breathing rate availability varies by platform | HIGH | ADR-68.2 decision needed upfront. Start with Oura (richest sleep data) or Apple Watch (largest market share). Abstract the wearable adapter so swapping platforms doesn't require engine changes. |
| **M21 cold-start** — system_viscosity and overflow probability require patient history that won't exist for new patients | MEDIUM | Population defaults with progressive personalization. Clearly document which outputs are population-derived vs. patient-calibrated in ICI provenance. |
| **M64 integration** — bidirectional feed requires M64 to emit mechanism-typed FUD flags (FUD-IR, FUD-GB). Verify M64 currently produces these. | MEDIUM | Check M64 v2.0 spec — mechanism typing exists in the signature registry. If not yet emitted in the output contract, this is a small M64 change. |
| **Turbulence calibration** — the max_turbulence_gain parameter (default 0.8) is a best guess. May need adjustment after real-world data. | LOW | Governed parameter, adjustable via M48. Log turbulence coefficient distributions for first 3 months to calibrate. |
| **Infrastructure variable data sparsity** — patients without wearables get no HRV, no deep sleep %, no breathing rate. Several infrastructure inputs go dark. | MEDIUM | Degrade gracefully: when wearable data is absent, use PRO-derived proxies (self-reported sleep quality, exercise frequency) and widen confidence intervals on infrastructure estimates. Document degraded-mode behavior. |
| **Computation cost** — 10+ input sources, 4 infrastructure variables, turbulence regime, attribution vector on every cycle. May be heavier than expected. | LOW | Profile early. The hybrid computation frequency (Subtask 9 ADR) limits cycles. Consider caching infrastructure variables (they change slowly) and only recomputing the fast-changing components (inflow, displacement) on trigger. |

---

## ADR Summary (Decisions Needed)

| ADR | Question | Recommendation | Decide By |
|-----|----------|----------------|-----------|
| **ADR-68.1** | ICI snapshot storage format (FHIR Observation vs custom schema) | Custom schema + FHIR audit wrapper | Before Subtask 5 |
| **ADR-68.2** | Population HRV reference ranges (published norms vs internal data) | Published norms initially, switch at N>500 | Before Subtask 4 |
| **ADR-68.3** | ICI computation frequency | Hybrid: 6h scheduled + event-triggered | Before Subtask 9 |
| **ADR-68.4** | Primary wearable platform target | Oura (richest data) or Apple Watch (largest reach) | Before Subtask 2 |

---

## Sizing Summary

| Subtask | Size | Est. Days | Dependencies |
|---------|------|-----------|--------------|
| 1. Data Model & Schemas | M | 3–5 | None |
| 2. Input Ingestion Pipeline | L | 5–8 | None (parallel with 1) |
| 3. Stressor Census Engine | M | 3–5 | 2 |
| 4. Infrastructure Variables | M | 3–5 | 2 |
| 5. Three-Valve Engine + Turbulence | L | 5–8 | 1, 3, 4 |
| 6. Attribution & Discovery | S | 2–3 | 5 |
| 7. Threshold Logic & Routing | M | 3–5 | 5 |
| 8. VWA Lifecycle | M | 3–5 | 5, 7 |
| 9. Vault Persistence & Audit | M | 3–5 | 5 |
| 10. M24 Visualization Contract | S–M | 2–4 | 5 |
| 11. Calibration Telemetry | S | 2–3 | 9 |
| 12. Acceptance Tests & Metrics | M | 3–5 | All |

**Total estimated range:** 40–60 dev-days
**Critical path:** Subtasks 1+2 (parallel) → 3+4 (parallel) → 5 → 6+7+8+9 (partially parallel) → 10+11 → 12

**Suggested sprint allocation:**
- Sprint 1: Subtasks 1, 2 (schemas + ingestion — foundation)
- Sprint 2: Subtasks 3, 4 (stressor census + infrastructure — the "what goes in")
- Sprint 3: Subtask 5 (the engine — this is the core; give it a full sprint)
- Sprint 4: Subtasks 6, 7, 8, 9 (the outputs — can partially parallelize)
- Sprint 5: Subtasks 10, 11, 12 (visualization, telemetry, tests — polish)

---

## Files Included in This Package

1. `V6_M68_InflammatoryCapacityModel_ICM_v1.1.md` — Full module specification (authoritative)
2. `M68_v2.0_Roadmap.md` — Deferred items with context (for awareness; not v1.1 scope)
3. `M66_Siddhi_Practice_Taxonomy_Fragment.md` — M66 practice catalog proposal (M66 scope, not Dylan's build for M68)
4. `M68_Dylan_Handoff.md` — This document

---

*Prepared by Andras — March 2026*
