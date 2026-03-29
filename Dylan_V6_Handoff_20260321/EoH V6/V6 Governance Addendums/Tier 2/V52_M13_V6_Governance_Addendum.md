# Addendum: M13 — Trend & Prognostic Engine

**Template Version:** V5.2 → V6 Governance Addendum Template v1.0
**Validated Against:** M63 GBDC v1.0 (§2–§7)
**Upstream Reference:** Tier 1 Cross-Module Validation Report
**Status:** DRAFT — Emission Layer Only; No Core Logic Changes

---

## A. Module Identity & Addendum Scope

| Field | Value |
|---|---|
| Module ID | M13 |
| Module Name | Trend & Prognostic Engine |
| V5.2 Spec Version | V5.2 |
| Addendum Version | V6-A.1.0 |
| Addendum Type | Emission Layer |
| Core Logic Modified | No |
| M63 Contract Coverage | Trace Integrity, Support Disclosure, Uncertainty Preservation, Constraint Disclosure |

**Scope:** M13 produces the first PROBABILISTIC outputs in the EoH pipeline: `flare_probability`, `relapse_risk`, and `comorbidity_trajectory` are horizon-specific probability values. Per M63 §6.1.4, probabilistic/prognostic outputs require uncertainty carriers with status CARRIERS_PRESENT for GLASS_BOX eligibility. NOT_PROVIDED is **not acceptable** for M13's primary outputs — unlike upstream modules where scalar inputs may pass through without uncertainty metadata, M13 is the producing module for these probabilities and MUST emit bounds.

Additionally, M13 assembles the schema-stable `mpa_vector` (output_form_class: VECTOR) and `explainer_bundle` (output_form_class: COMPOSITE), both of which require per-component uncertainty evaluation per M63 §5.3.

---

## B. Input Artifact Pointer Table

| V5.2 Input | Source Module | Artifact Pointer Format | Status |
|---|---|---|---|
| `tags[]` | M4/M5 | `M4:obs:normalized-tags:{pid}:{ts}` | **MISSING** — M4 is unspecified; pointer format assumed from Tier 1 G-01 |
| `PSI` | M5 | `M5:obs:psi:{pid}:{ts}` | Pointer-backed (M5 produces PSI as a scored observation) |
| `symbolic_flags[]` | M5 | `M5:obs:symbolic-flags:{pid}:{ts}` | Pointer-backed |
| `stabilityBand` | M6 | `M6:obs:stability-band:{pid}:{ts}` | **MISSING** — M6 is unspecified; pointer format assumed from M3 post-suppression propagation chain |
| `drift` | M6 | `M6:obs:drift:{pid}:{ts}` | **MISSING** — M6 unspecified |
| `narrative_digest` | M12 | `M12:obs:narrative-digest:{pid}:{ts}` | Pointer-backed |
| `harmonized_labs[]` | M12 | `M12:obs:harmonized-labs:{pid}:{ts}` | Pointer-backed |
| `relapse_monitors` | M20/M21 | `M20:obs:relapse-monitors:{pid}:{ts}` | **MISSING** — M20 unspecified |
| `taper_monitors` | M20/M21 | `M20:obs:taper-monitors:{pid}:{ts}` | **MISSING** — M20 unspecified |
| `baselines` (including OHB) | M21 | `M21:obs:baselines:{pid}:{ts}` | Pointer-backed (M21 Vault is specified) |
| `inference_context` | M26A | `M26A:obs:inference-context:{pid}:{ts}` | Pointer-backed |
| `canonical_unified_MPA_vector` | M45 | `M45:obs:canonical-mpa-vector:{pid}:{ts}` | **MISSING** — M45 unspecified |
| `pauseFlag` | M8/M9 | `M8:obs:suppression-state:{pid}:{ts}` or `M9:obs:suppression-state:{pid}:{ts}` | Pointer-backed (M9 Tier 1 addendum resolves; M8 addendum in Tier 2 resolves) |
| `pauseReason` | M8/M9 | (carried within suppression state artifact) | Pointer-backed |

---

## C. Uncertainty Carrier Emissions

M13 is the **producing module** for probabilistic outputs. Per M63 §5.1, it MUST emit uncertainty carriers — it cannot pass NOT_PROVIDED for its own computed probabilities.

| Output | Output Form Class (§2.1) | Uncertainty Carrier Type (§5.1) | Carrier Content | Artifact Pointer |
|---|---|---|---|---|
| `flare_probability` | SCALAR | **CONFIDENCE_INTERVAL** | Lower bound, point estimate, upper bound; horizon label; calibration method reference | `M13:unc:flare-probability-ci:{pid}:{ts}:{horizon}` |
| `relapse_risk` | SCALAR | **CONFIDENCE_INTERVAL** | Lower bound, point estimate, upper bound; horizon label; calibration method reference | `M13:unc:relapse-risk-ci:{pid}:{ts}:{horizon}` |
| `comorbidity_trajectory` | LANDSCAPE | **PROBABILITY_LANDSCAPE** | Multi-horizon probability surface with uncertainty bounds at each horizon point; dispersion metric | `M13:unc:comorbidity-landscape:{pid}:{ts}` |
| `mpa_vector` | VECTOR | **BOUNDS_OBJECT** | Per-component bounds for trajectory features, composites, and horizon outputs embedded in the vector | `M13:unc:mpa-vector-bounds:{pid}:{ts}` |
| `explainer_bundle` | COMPOSITE | Per-component evaluation: CONFIDENCE_INTERVAL for driver attributions; NOT_PROVIDED acceptable for visualization hooks and NL summaries (these are presentation, not probabilistic) | | `M13:unc:explainer-attributions:{pid}:{ts}` |
| (sparse/unstable input scenario) | — | **DEGRADATION_STATE** | Which inputs were missing/sparse/volatile; which trajectory computations degraded; widened-uncertainty indicator | `M13:unc:degradation:{pid}:{ts}` |

**Key enforcement:** If M13 emits `flare_probability` without an accompanying CONFIDENCE_INTERVAL carrier, M63 MUST set `uncertainty_disclosure.status = NOT_PROVIDED`, and the output is GLASS_BOX-ineligible per §6.1.4. This is the first module in the pipeline where this gate is load-bearing.

---

## D. Constraint Carrier Emissions

| Constraint Scenario | Constraint Type (§5.2) | Carrier Content | Artifact Pointer |
|---|---|---|---|
| Suppression active during trend computation (pauseFlag=true) | **SUPPRESSION** | Reference to upstream suppression state artifact; annotation that suppressed data was carried forward (not erased) per M13 Step 8 | `M13:constraint:suppression-carryforward:{pid}:{ts}` with `source_artifact_pointer -> M8:obs:suppression-state:{pid}:{ts}` or `M9:obs:suppression-state:{pid}:{ts}` |
| Vector governance rules applied (Appendix F.13) | **INVARIANT_ENFORCEMENT** | Reference to Appendix F.13 version; confirmation that vector versioning and idempotency invariants were enforced | `M13:constraint:vector-governance:{pid}:{ts}` with `source_artifact_pointer -> governance:appendix:F.13:{version}` |

---

## E. Process Step -> Transformation Record Mapping

| V5.2 Step | step_index | owning_module_id | input_artifact_pointers[] | output_artifact_pointer | step_status |
|---|---|---|---|---|---|
| 1. Ingest inputs | 1 | M13 | `[M4:obs:normalized-tags:{pid}:{ts}`, `M5:obs:psi:{pid}:{ts}`, `M5:obs:symbolic-flags:{pid}:{ts}`, `M6:obs:stability-band:{pid}:{ts}`, `M6:obs:drift:{pid}:{ts}`, `M12:obs:narrative-digest:{pid}:{ts}`, `M12:obs:harmonized-labs:{pid}:{ts}`, `M20:obs:relapse-monitors:{pid}:{ts}`, `M20:obs:taper-monitors:{pid}:{ts}`, `M21:obs:baselines:{pid}:{ts}`, `M26A:obs:inference-context:{pid}:{ts}`, `M45:obs:canonical-mpa-vector:{pid}:{ts}`, `M8:obs:suppression-state:{pid}:{ts}`]` | `M13:internal:ingested-inputs:{pid}:{ts}` | POINTER_BACKED (for M5, M12, M21, M26A); MISSING (for M4, M6, M20, M45) |
| 2. Generate rolling window aggregates | 2 | M13 | `M13:internal:ingested-inputs:{pid}:{ts}` | `M13:internal:rolling-aggregates:{pid}:{ts}` | POINTER_BACKED |
| 3. Compute trajectory features vs OHB | 3 | M13 | `M13:internal:rolling-aggregates:{pid}:{ts}`, `M21:obs:baselines:{pid}:{ts}` | `M13:internal:trajectory-features:{pid}:{ts}` | POINTER_BACKED |
| 4. Compute composite metrics | 4 | M13 | `M13:internal:trajectory-features:{pid}:{ts}` | `M13:internal:composite-metrics:{pid}:{ts}` | POINTER_BACKED |
| 5. Generate horizon-specific probabilities | 5 | M13 | `M13:internal:trajectory-features:{pid}:{ts}`, `M13:internal:composite-metrics:{pid}:{ts}` | `M13:obs:prognostic-indices:{pid}:{ts}` | POINTER_BACKED |
| 6. Assemble mpa_vector | 6 | M13 | `M13:internal:trajectory-features:{pid}:{ts}`, `M13:internal:composite-metrics:{pid}:{ts}`, `M13:obs:prognostic-indices:{pid}:{ts}` | `M13:obs:mpa-vector:{pid}:{ts}` | POINTER_BACKED |
| 7. Create explainer bundle | 7 | M13 | `M13:obs:prognostic-indices:{pid}:{ts}`, `M13:internal:trajectory-features:{pid}:{ts}` | `M13:obs:explainer-bundle:{pid}:{ts}` | POINTER_BACKED |
| 8. Apply suppression as annotation | 8 | M13 | `M8:obs:suppression-state:{pid}:{ts}` or `M9:obs:suppression-state:{pid}:{ts}`, `M13:obs:mpa-vector:{pid}:{ts}` | `M13:obs:mpa-vector:{pid}:{ts}` (annotated), `M13:constraint:suppression-carryforward:{pid}:{ts}` | POINTER_BACKED |
| 9. Persist outputs | 9 | M13 | `M13:obs:mpa-vector:{pid}:{ts}`, `M13:obs:prognostic-indices:{pid}:{ts}`, `M13:obs:explainer-bundle:{pid}:{ts}` | `M13:fhir:observation:{pid}:{ts}`, `M13:fhir:risk-assessment:{pid}:{ts}`, `M13:fhir:document-reference:{pid}:{ts}`, `M21:obs:feature-snapshots:{pid}:{ts}` | POINTER_BACKED |

---

## F. Output Artifact Pointer Table

| V5.2 Output | Artifact Pointer Format | Output Form Class | Uncertainty Carrier Required? | Constraint Carrier Required? |
|---|---|---|---|---|
| `mpa_vector` | `M13:obs:mpa-vector:{pid}:{ts}` | VECTOR | Yes — BOUNDS_OBJECT | If suppression active: yes (SUPPRESSION) |
| `flare_probability` | `M13:obs:flare-probability:{pid}:{ts}:{horizon}` | SCALAR | Yes — CONFIDENCE_INTERVAL | If suppression active: yes |
| `relapse_risk` | `M13:obs:relapse-risk:{pid}:{ts}:{horizon}` | SCALAR | Yes — CONFIDENCE_INTERVAL | If suppression active: yes |
| `comorbidity_trajectory` | `M13:obs:comorbidity-trajectory:{pid}:{ts}` | LANDSCAPE | Yes — PROBABILITY_LANDSCAPE | If suppression active: yes |
| `feature_snapshots` (persisted to M21) | `M21:obs:feature-snapshots:{pid}:{ts}` | COMPOSITE | Per-component | No |
| `explainer_bundle` | `M13:obs:explainer-bundle:{pid}:{ts}` | COMPOSITE | Per-component (CONFIDENCE_INTERVAL for attributions; NOT_PROVIDED acceptable for presentation components) | No |
| FHIR Observation | `M13:fhir:observation:{pid}:{ts}` | — | — | — |
| FHIR RiskAssessment | `M13:fhir:risk-assessment:{pid}:{ts}` | — | — | — |
| FHIR DocumentReference | `M13:fhir:document-reference:{pid}:{ts}` | — | — | — |

---

## G. Cross-Module Pointer Validation

### G.1 — Do M13's output pointers match what M14 declares as inputs?

| M13 Output Pointer | M14 Declares as Input? | Match? |
|---|---|---|
| `M13:obs:prognostic-indices:{pid}:{ts}` -> M14 `risk_indices` | Yes — M14 Step 1 ingests `risk_indices` from M13 | **Match** |
| `M13:obs:mpa-vector:{pid}:{ts}` -> M14 `volatility_indices` | Yes — M14 Step 1 ingests `volatility_indices` from M13 | **Match** |
| `M13:internal:trajectory-features:{pid}:{ts}` -> M14 `trajectory_features` | Yes — M14 Step 1 ingests `trajectory_features` from M13 | **Match** |

### G.2 — Do M13's output pointers match what M15 declares as inputs?

| M13 Output Pointer | M15 Declares as Input? | Match? |
|---|---|---|
| `M13:obs:flare-probability:{pid}:{ts}:{horizon}` -> M15 `flare_risk_slopes` | Yes | **Match** |
| `M13:obs:relapse-risk:{pid}:{ts}:{horizon}` -> M15 `relapse_probability` | Yes | **Match** |
| `M13:internal:trajectory-features:{pid}:{ts}` -> M15 `recovery_vectors` | Yes | **Match** |

### G.3 — Do M13's uncertainty carriers use valid §5.1 enum types?

All uncertainty carriers (CONFIDENCE_INTERVAL, PROBABILITY_LANDSCAPE, BOUNDS_OBJECT, DEGRADATION_STATE) use valid §5.1 closed enum types. No enum expansion required.

---

## H. Gap Register

| Gap ID | V6 Requirement | Current Status | Resolution Tier | Blocking? |
|---|---|---|---|---|
| G-T2-01 | M4 `normalizedTags[]` input pointer | MISSING — M4 unspecified | Tier 3 (M4 addendum) — same as Tier 1 G-01 | Yes — blocks TRACE_COMPLETE for M13 Step 1 |
| G-T2-02 | M6 `stabilityBand` input pointer | MISSING — M6 unspecified | Tier 3 (M6 addendum) | Yes |
| G-T2-03 | M6 `drift` input pointer | MISSING — M6 unspecified | Tier 3 (M6 addendum) | Yes |
| G-T2-04 | M20 `relapse_monitors` input pointer | MISSING — M20 unspecified | Tier 3 (M20 addendum) | Yes |
| G-T2-05 | M20 `taper_monitors` input pointer | MISSING — M20 unspecified | Tier 3 (M20 addendum) | Yes |
| G-T2-06 | M45 `canonical_unified_MPA_vector` input pointer | MISSING — M45 unspecified | Tier 3 (M45 addendum) | Yes |

**No gap requires core logic change.**

---

## I. FHIR Anchor Mapping

| M13 Output | FHIR Resource | FHIR Profile Reference |
|---|---|---|
| `flare_probability`, `relapse_risk` per horizon | `RiskAssessment` | Appendix C.4 |
| `mpa_vector` components | `Observation` (component-level) | Appendix C.4 |
| `explainer_bundle` | `DocumentReference` | Appendix C.4 |
| `feature_snapshots` | Persisted via M21 (Vault) | — |
| Derivation audit trail | `AuditEvent` + `Provenance` | Appendix C.7/C.11 |

---

## J. Addendum Acceptance Tests

| Test ID | Test | Expected Result |
|---|---|---|
| M13-AT-01 | Run M13 with all inputs available; verify every output has a DerivationChain | Chain present for mpa_vector, each prognostic index, explainer_bundle |
| M13-AT-02 | Verify flare_probability output has CONFIDENCE_INTERVAL carrier | `uncertainty_disclosure.status = CARRIERS_PRESENT` |
| M13-AT-03 | Verify relapse_risk output has CONFIDENCE_INTERVAL carrier | Same as AT-02 |
| M13-AT-04 | Verify comorbidity_trajectory output has PROBABILITY_LANDSCAPE carrier | `uncertainty_disclosure.status = CARRIERS_PRESENT` |
| M13-AT-05 | Remove M6 input; verify chain status | `completeness_classification = TRACE_PARTIAL`; MISSING placeholder at Step 1 |
| M13-AT-06 | Run with suppression active; verify SUPPRESSION constraint carrier | `constraint_disclosure.status = CARRIERS_PRESENT` |
| M13-AT-07 | Run with sparse inputs; verify DEGRADATION_STATE carrier | Degradation record present |
| M13-AT-08 | Verify mpa_vector includes BOUNDS_OBJECT carrier | `uncertainty_disclosure.status = CARRIERS_PRESENT` |
| M13-AT-09 | Emit flare_probability WITHOUT confidence interval; verify GLASS_BOX denied | §6.1.4 failure; GLASS_BOX label not applied |
| M13-AT-10 | Replay identical inputs + versions; verify identical DerivationChain | Replay determinism confirmed per M63 §7 |
