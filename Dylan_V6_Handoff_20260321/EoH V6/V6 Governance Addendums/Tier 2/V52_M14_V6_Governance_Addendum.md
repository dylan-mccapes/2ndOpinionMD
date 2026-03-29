# Addendum: M14 — Action & Escalation Engine

**Template Version:** V5.2 -> V6 Governance Addendum Template v1.0
**Validated Against:** M63 GBDC v1.0 (§2–§7)
**Upstream Reference:** Tier 1 Cross-Module Validation Report
**Status:** DRAFT — Emission Layer Only; No Core Logic Changes

---

## A. Module Identity & Addendum Scope

| Field | Value |
|---|---|
| Module ID | M14 |
| Module Name | Action & Escalation Engine |
| V5.2 Spec Version | V5.2 |
| Addendum Version | V6-A.1.0 |
| Addendum Type | Emission Layer |
| Core Logic Modified | No |
| M63 Contract Coverage | Trace Integrity, Support Disclosure, Uncertainty Preservation, Constraint Disclosure |

**Scope:** M14 harmonizes all upstream severity notions into a unified T0–T4 risk taxonomy. This harmonization step is a **governance gate** — a structural constraint that shapes every downstream output. Additionally, M14 performs suppression-aware routing (another constraint-producing step). M14 does not produce new probabilistic values; it consumes M13's probabilities and translates them into tier assignments and action bundles. Uncertainty carriers from M13 are **carried through** (not recomputed); constraint carriers are **produced** at the tier harmonization and suppression routing steps.

---

## B. Input Artifact Pointer Table

| V5.2 Input | Source Module | Artifact Pointer Format | Status |
|---|---|---|---|
| `risk_indices` | M13 | `M13:obs:prognostic-indices:{pid}:{ts}` | Pointer-backed (M13 addendum) |
| `volatility_indices` | M13 | `M13:obs:mpa-vector:{pid}:{ts}` (volatility components) | Pointer-backed |
| `stabilityBand` | M6, M11 | `M6:obs:stability-band:{pid}:{ts}` | **MISSING** — M6 unspecified |
| `stack_shifts` | M6, M11 | `M6:obs:stack-shifts:{pid}:{ts}` | **MISSING** — M6 unspecified |
| `psi_score` | M5, M11 | `M5:obs:psi:{pid}:{ts}` | Pointer-backed |
| `symbolic_flags` | M5, M11 | `M5:obs:symbolic-flags:{pid}:{ts}` | Pointer-backed |
| `pauseFlag` | M8/M9 | `M8:obs:suppression-state:{pid}:{ts}` or `M9:obs:suppression-state:{pid}:{ts}` | Pointer-backed |
| `pauseReason` | M8/M9 | (within suppression state artifact) | Pointer-backed |
| `trajectory_features` | M10, M13, M26A | `M13:internal:trajectory-features:{pid}:{ts}` (from M13); `M10:obs:trajectory-features:{pid}:{ts}` (from M10); `M26A:obs:inference-context:{pid}:{ts}` | Pointer-backed (M13); **MISSING** (M10 unspecified) |
| `alert_fatigue_settings` | Configuration | `config:alert-fatigue:{site}:{version}` | Pointer-backed |
| `communication_preferences` | Configuration | `config:communication-prefs:{pid}:{version}` | Pointer-backed |
| `context_preferences` | Configuration | `config:context-prefs:{pid}:{version}` | Pointer-backed |

---

## C. Uncertainty Carrier Emissions

M14 does NOT produce new probabilistic values. It carries through M13's uncertainty and, where tier harmonization introduces discretization loss, discloses that loss.

| Output | Output Form Class | Uncertainty Carrier Type | Carrier Content | Artifact Pointer |
|---|---|---|---|---|
| `risk_tier` (T0–T4) | SCALAR | **CARRIED_THROUGH** from M13's CONFIDENCE_INTERVAL on risk_indices | M14 does not recompute uncertainty; the interval from M13 is attached to the tier assignment. If the point estimate is near a tier boundary AND the M13 confidence interval spans that boundary, a **DEGRADATION_STATE** carrier is emitted noting tier-boundary ambiguity. | `M14:unc:tier-boundary-ambiguity:{pid}:{ts}` (emitted only when CI spans boundary); otherwise M13 carriers carried through |
| `patient_action_bundle` | NARRATIVE | NOT_PROVIDED acceptable | | — |
| `clinician_action_bundle` | COMPOSITE | Per-component carry-through | | — |

---

## D. Constraint Carrier Emissions

| Constraint Scenario | Constraint Type (§5.2) | Carrier Content | Artifact Pointer |
|---|---|---|---|
| Tier harmonization applied (T0–T4 mapping) | **GOVERNANCE_GATE** | Harmonization rule version, input signals consumed, tier assigned, enforced constraint that no output bypasses tier alignment | `M14:constraint:tier-harmonization:{pid}:{ts}` with `source_artifact_pointer -> governance:tier-table:{version}` |
| Suppression-aware routing active (pauseFlag=true) | **SUPPRESSION** | Upstream suppression state reference; routing decision; confirmation event was not silently dropped | `M14:constraint:suppression-routing:{pid}:{ts}` with `source_artifact_pointer -> M8:obs:suppression-state:{pid}:{ts}` or `M9:obs:suppression-state:{pid}:{ts}` |
| Human-in-the-loop gate enforced (tier > T2) | **GOVERNANCE_GATE** | Tier at which HITL gate triggered; clinician-review-required flag set | `M14:constraint:hitl-gate:{pid}:{ts}` |
| Alert suppression event (AlertSuppressed outcome) | **SUPPRESSION** | Suppression reasons, canonical pauseFlag reason, routing to Reflex Suppression Audit Surface | `M14:constraint:alert-suppression:{pid}:{ts}` with `source_artifact_pointer -> M41:audit:suppression-surface:{pid}:{ts}` |

---

## E. Process Step -> Transformation Record Mapping

| V5.2 Step | step_index | owning_module_id | input_artifact_pointers[] | output_artifact_pointer | step_status |
|---|---|---|---|---|---|
| 1. Ingest inputs | 1 | M14 | `[M13:obs:prognostic-indices:{pid}:{ts}`, `M13:obs:mpa-vector:{pid}:{ts}`, `M6:obs:stability-band:{pid}:{ts}`, `M5:obs:psi:{pid}:{ts}`, `M5:obs:symbolic-flags:{pid}:{ts}`, `M8:obs:suppression-state:{pid}:{ts}`, `M13:internal:trajectory-features:{pid}:{ts}`, config artifacts]` | `M14:internal:orchestration-envelope:{pid}:{ts}` | POINTER_BACKED (M13, M5, M8, config); MISSING (M6, M10) |
| 2. Build orchestration envelope | 2 | M14 | `M14:internal:orchestration-envelope:{pid}:{ts}` | `M14:internal:action-context:{pid}:{ts}` | POINTER_BACKED |
| 3. Harmonize severity to T0–T4 | 3 | M14 | `M14:internal:action-context:{pid}:{ts}` | `M14:obs:risk-tier:{pid}:{ts}`, `M14:constraint:tier-harmonization:{pid}:{ts}` | POINTER_BACKED |
| 4. Apply suppression-aware routing | 4 | M14 | `M14:obs:risk-tier:{pid}:{ts}`, `M8:obs:suppression-state:{pid}:{ts}` | `M14:internal:routed-context:{pid}:{ts}`, `M14:constraint:suppression-routing:{pid}:{ts}` (if active) | POINTER_BACKED |
| 5. Generate dual-channel outputs | 5 | M14 | `M14:obs:risk-tier:{pid}:{ts}`, `M5:obs:psi:{pid}:{ts}`, `config:context-prefs:{pid}:{version}` | `M14:obs:patient-action-bundle:{pid}:{ts}`, `M14:obs:clinician-action-bundle:{pid}:{ts}` | POINTER_BACKED |
| 6. Enforce HITL controls | 6 | M14 | `M14:obs:risk-tier:{pid}:{ts}` | `M14:constraint:hitl-gate:{pid}:{ts}` (if tier > T2) | POINTER_BACKED |
| 7. Apply handoff rules | 7 | M14 | `M14:obs:risk-tier:{pid}:{ts}`, `M14:internal:routed-context:{pid}:{ts}` | `M14:obs:handoff-targets:{pid}:{ts}` | POINTER_BACKED |
| 8. Emit audit + provenance | 8 | M14 | (all prior step outputs) | `M14:fhir:audit-event:{pid}:{ts}`, `M14:fhir:provenance:{pid}:{ts}` | POINTER_BACKED |
| 9. Emit external delivery artifacts | 9 | M14 | `M14:obs:patient-action-bundle:{pid}:{ts}`, `M14:obs:clinician-action-bundle:{pid}:{ts}` | `M14:fhir:delivery-artifacts:{pid}:{ts}` | POINTER_BACKED |

---

## F. Output Artifact Pointer Table

| V5.2 Output | Artifact Pointer Format | Output Form Class | Uncertainty Carrier Required? | Constraint Carrier Required? |
|---|---|---|---|---|
| `risk_tier` | `M14:obs:risk-tier:{pid}:{ts}` | SCALAR | Carry-through from M13; DEGRADATION_STATE if boundary ambiguity | Yes — GOVERNANCE_GATE |
| `patient_action_bundle` | `M14:obs:patient-action-bundle:{pid}:{ts}` | NARRATIVE | NOT_PROVIDED acceptable | If suppression active: SUPPRESSION |
| `clinician_action_bundle` | `M14:obs:clinician-action-bundle:{pid}:{ts}` | COMPOSITE | Per-component carry-through | If HITL gate: GOVERNANCE_GATE |
| `handoff_targets[]` | `M14:obs:handoff-targets:{pid}:{ts}` | VECTOR | No | If tier-driven: GOVERNANCE_GATE |
| `suppression_event` | `M14:obs:suppression-event:{pid}:{ts}` | — | — | Yes — SUPPRESSION |
| `audit_events[]` | `M14:fhir:audit-event:{pid}:{ts}` | — | — | — |
| `provenance_records[]` | `M14:fhir:provenance:{pid}:{ts}` | — | — | — |
| `fhir_delivery_artifacts[]` | `M14:fhir:delivery-artifacts:{pid}:{ts}` | — | — | — |

---

## G. Cross-Module Pointer Validation

### G.1 — Do M14's tier outputs match what M15 consumes?

| M14 Output Pointer | M15 Declares as Input? | Match? |
|---|---|---|
| `M14:obs:risk-tier:{pid}:{ts}` -> M15 `tier` (T0–T4) | Yes | **Match** |
| `M14:constraint:suppression-routing:{pid}:{ts}` -> M15 `suppression_context` | Yes | **Match** |
| `M14:obs:clinician-action-bundle:{pid}:{ts}` -> M15 `sla.required_by_date` | Yes | **Match** |

### G.2 — Do M14's handoff pointers resolve?

| Handoff Target | Pointer | Resolves? |
|---|---|---|
| M10 (crisis engine, T4) | `M10:intake:crisis-handoff:{pid}:{ts}` | **MISSING** — M10 unspecified |
| M15/M19 (CarePlan changes) | `M15:intake:tier-escalation:{pid}:{ts}` | Pointer-backed (M15 addendum) |
| M43/M44 (documentation triggers) | `M43:intake:documentation-trigger:{pid}:{ts}` | **MISSING** — M43/M44 unspecified |
| M47 (FHIR gateway) | `M47:intake:fhir-delivery:{pid}:{ts}` | **MISSING** — M47 unspecified |

---

## H. Gap Register

| Gap ID | V6 Requirement | Current Status | Resolution Tier | Blocking? |
|---|---|---|---|---|
| G-T2-07 | M6 `stabilityBand` / `stack_shifts` input pointer | MISSING — M6 unspecified | Tier 3 (M6 addendum) | Yes |
| G-T2-08 | M10 `trajectory_features` input pointer | MISSING — M10 unspecified | Tier 3 (M10 addendum) | Yes |
| G-T2-09 | M10 crisis handoff target pointer | MISSING — M10 unspecified | Tier 3 | No |
| G-T2-10 | M43/M44 documentation trigger target pointer | MISSING — M43/M44 unspecified | Tier 3 | No |
| G-T2-11 | M47 FHIR gateway target pointer | MISSING — M47 unspecified | Tier 3 | No |

**No gap requires core logic change.**

---

## I. FHIR Anchor Mapping

| M14 Output | FHIR Resource | FHIR Profile Reference |
|---|---|---|
| `risk_tier` | Embedded in `AuditEvent.outcome` | Appendix C.11 |
| `patient_action_bundle` | `Communication` (patient-directed) | Appendix C.4 / M47 |
| `clinician_action_bundle` | `Task` (clinician-directed) | Appendix C.4 / M47 |
| `suppression_event` | `AuditEvent` (type: AlertSuppressed) | Appendix C.11.1 |
| `audit_events[]` | `AuditEvent` | Appendix C.7/C.11 |
| `provenance_records[]` | `Provenance` | Appendix C.7 |

---

## J. Addendum Acceptance Tests

| Test ID | Test | Expected Result |
|---|---|---|
| M14-AT-01 | Run M14 with M13 outputs; verify DerivationChain for risk_tier | Chain present with M13 prognostic indices as inputs |
| M14-AT-02 | Verify tier harmonization produces GOVERNANCE_GATE carrier | `constraint_disclosure.status = CARRIERS_PRESENT` |
| M14-AT-03 | Run with pauseFlag=true; verify SUPPRESSION carrier at routing step | Suppression carrier present |
| M14-AT-04 | Verify tier > T2 produces HITL GOVERNANCE_GATE carrier | Constraint carrier present |
| M14-AT-05 | Verify M13 uncertainty carriers carried through on risk_tier | M13's CONFIDENCE_INTERVAL in derivation chain |
| M14-AT-06 | AlertSuppressed event routes to Suppression Audit Surface | AuditEvent emitted with suppression_reasons |
| M14-AT-07 | Point estimate near boundary with CI spanning; verify DEGRADATION_STATE | Tier-boundary-ambiguity carrier present |
| M14-AT-08 | Verify "no action" path produces audit event | AuditEvent with "no action" emitted |
