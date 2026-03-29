# Addendum: M15 — Consolidation Report (Care Plan Composer)

**Template Version:** V5.2 -> V6 Governance Addendum Template v1.0
**Validated Against:** M63 GBDC v1.0 (§2–§7)
**Upstream Reference:** Tier 1 Cross-Module Validation Report
**Status:** DRAFT — Emission Layer Only; No Core Logic Changes

---

## A. Module Identity & Addendum Scope

| Field | Value |
|---|---|
| Module ID | M15 |
| Module Name | Consolidation Report (Care Plan Composer) |
| V5.2 Spec Version | V5.2 |
| Addendum Version | V6-A.1.0 |
| Addendum Type | Emission Layer |
| Core Logic Modified | No |
| M63 Contract Coverage | Trace Integrity, Support Disclosure, Uncertainty Preservation, Constraint Disclosure |

**Scope:** M15 composes calendarized CarePlans for multi-morbidity patients (Stack >= 3). This module is constraint-dense: the Stack >= 3 guard is a GOVERNANCE_GATE; capacity enforcement is a GOVERNANCE_GATE; human-in-loop gating is a GOVERNANCE_GATE; suppression transparency (pauseFlag/pauseReason on deferred/throttled actions) produces SUPPRESSION constraint carriers. M15 does not produce new probabilities — it consumes M13/M14 outputs and translates them into time-placed care plan actions.

---

## B. Input Artifact Pointer Table

| V5.2 Input | Source Module | Artifact Pointer Format | Status |
|---|---|---|---|
| `flare_risk_slopes` | M13 | `M13:obs:flare-probability:{pid}:{ts}:{horizon}` | Pointer-backed (M13 addendum) |
| `relapse_probability` | M13 | `M13:obs:relapse-risk:{pid}:{ts}:{horizon}` | Pointer-backed |
| `recovery_vectors` | M13 | `M13:internal:trajectory-features:{pid}:{ts}` | Pointer-backed |
| `tier` (T0–T4) | M14 | `M14:obs:risk-tier:{pid}:{ts}` | Pointer-backed (M14 addendum) |
| `suppression_context.pauseFlag` | M14 | `M14:constraint:suppression-routing:{pid}:{ts}` | Pointer-backed |
| `suppression_context.pauseReason` | M14 | (within suppression routing artifact) | Pointer-backed |
| `sla.required_by_date` | M14 | (within clinician_action_bundle if provided) | Pointer-backed |
| `stackLevel` | M11 | `M11:obs:patient-state:{pid}:{ts}` | **MISSING** — M11 unspecified |
| `stabilityBand` | M11 | `M11:obs:patient-state:{pid}:{ts}` (component) | **MISSING** |
| `cbm_status` | M11 | `M11:obs:patient-state:{pid}:{ts}` (component) | **MISSING** |
| `psi` | M5 | `M5:obs:psi:{pid}:{ts}` | Pointer-backed |
| `intervention_history` | M21 | `M21:obs:intervention-history:{pid}:{ts}` | Pointer-backed |
| `capacity_constraints` | Configuration | `config:capacity-constraints:{pid}:{version}` | Pointer-backed |

---

## C. Uncertainty Carrier Emissions

M15 does not produce new probabilistic values. Uncertainty is carried through from upstream.

| Output | Output Form Class | Uncertainty Carrier Type | Carrier Content | Artifact Pointer |
|---|---|---|---|---|
| CarePlan element (per action) | COMPOSITE | **CARRIED_THROUGH** from M13/M14 | Each plan element references upstream prognostic index and tier; upstream uncertainty carriers attached to `drivers[]` | (upstream pointers referenced) |
| Rescheduled element | COMPOSITE | **DEGRADATION_STATE** (if rescheduling triggered by conflicting signals or new diagnosis) | Rescheduling provenance: what changed, when, who/what triggered | `M15:unc:reschedule-degradation:{pid}:{ts}:{element_id}` |

---

## D. Constraint Carrier Emissions

M15 is the most constraint-dense module in Tier 2.

| Constraint Scenario | Constraint Type (§5.2) | Carrier Content | Artifact Pointer |
|---|---|---|---|
| Stack >= 3 guard (eligibility gate) | **GOVERNANCE_GATE** | Stack level at evaluation time; guard outcome (proceed / skip) | `M15:constraint:stack-guard:{pid}:{ts}` |
| Capacity enforcement (collision resolution) | **GOVERNANCE_GATE** | Which actions collided; resolution method (stagger/reschedule/substitute); capacity model version | `M15:constraint:capacity-enforcement:{pid}:{ts}:{element_id}` |
| Human-in-loop gating (clinician approve/reject) | **GOVERNANCE_GATE** | Which plan elements require clinician approval; approval status; clinician identity if approved | `M15:constraint:hitl-approval:{pid}:{ts}:{element_id}` |
| Suppression transparency on deferred/throttled actions | **SUPPRESSION** | pauseFlag, pauseReason for each affected element; upstream suppression artifact reference | `M15:constraint:suppression-deferral:{pid}:{ts}:{element_id}` with `source_artifact_pointer -> M14:constraint:suppression-routing:{pid}:{ts}` |
| PSI-modulated cadence adjustment | **INVARIANT_ENFORCEMENT** | PSI value at evaluation; cadence modulation parameters; modulation rule version | `M15:constraint:psi-cadence-modulation:{pid}:{ts}` |

---

## E. Process Step -> Transformation Record Mapping

| V5.2 Step | step_index | owning_module_id | input_artifact_pointers[] | output_artifact_pointer | step_status |
|---|---|---|---|---|---|
| 1. Ingest canonical inputs | 1 | M15 | `[M13 prognostic pointers, M14:obs:risk-tier, M14:constraint:suppression-routing, M11:obs:patient-state, M5:obs:psi, M21:obs:intervention-history, config:capacity-constraints]` | `M15:internal:plan-inputs:{pid}:{ts}` | POINTER_BACKED (M13, M14, M5, M21, config); MISSING (M11) |
| 2. Initialize Tracks | 2 | M15 | `M15:internal:plan-inputs:{pid}:{ts}` | `M15:internal:tracks:{pid}:{ts}` | POINTER_BACKED |
| 3. Partition timeline horizons | 3 | M15 | `M15:internal:tracks:{pid}:{ts}` | `M15:internal:horizon-buckets:{pid}:{ts}` | POINTER_BACKED |
| 4. Place actions using flare windows | 4 | M15 | `M15:internal:horizon-buckets:{pid}:{ts}`, `M13:obs:flare-probability:{pid}:{ts}:{horizon}` | `M15:internal:placed-actions:{pid}:{ts}` | POINTER_BACKED |
| 5. Apply cadence modulation (PSI) | 5 | M15 | `M15:internal:placed-actions:{pid}:{ts}`, `M5:obs:psi:{pid}:{ts}` | `M15:internal:modulated-plan:{pid}:{ts}`, `M15:constraint:psi-cadence-modulation:{pid}:{ts}` | POINTER_BACKED |
| 6. Harmonize across Stack | 6 | M15 | `M15:internal:modulated-plan:{pid}:{ts}`, `config:capacity-constraints:{pid}:{version}` | `M15:internal:harmonized-plan:{pid}:{ts}`, `M15:constraint:capacity-enforcement:{pid}:{ts}:{element_id}` (per collision) | POINTER_BACKED |
| 7. Attach suppression transparency | 7 | M15 | `M15:internal:harmonized-plan:{pid}:{ts}`, `M14:constraint:suppression-routing:{pid}:{ts}` | `M15:internal:annotated-plan:{pid}:{ts}`, `M15:constraint:suppression-deferral:{pid}:{ts}:{element_id}` (per affected element) | POINTER_BACKED |
| 8. Attach provenance + versioning | 8 | M15 | `M15:internal:annotated-plan:{pid}:{ts}` | `M15:obs:care-plan:{pid}:{ts}` with per-element provenance | POINTER_BACKED |
| 9. Human-in-loop gating | 9 | M15 | `M15:obs:care-plan:{pid}:{ts}` | `M15:constraint:hitl-approval:{pid}:{ts}:{element_id}` (per gated element) | POINTER_BACKED |
| 10. Rescheduling behavior | 10 | M15 | (triggered by new diagnosis/flare event) | `M15:obs:care-plan:{pid}:{ts_new}` (revised), `M15:unc:reschedule-degradation:{pid}:{ts}:{element_id}` | POINTER_BACKED |
| 11. Export | 11 | M15 | `M15:obs:care-plan:{pid}:{ts}` | `M15:fhir:care-plan:{pid}:{ts}`, `M15:fhir:task:{pid}:{ts}:{element_id}`, `M15:fhir:service-request:{pid}:{ts}:{element_id}`, `M15:fhir:audit-event:{pid}:{ts}` | POINTER_BACKED |

---

## F. Output Artifact Pointer Table

| V5.2 Output | Artifact Pointer Format | Output Form Class | Uncertainty Carrier Required? | Constraint Carrier Required? |
|---|---|---|---|---|
| FHIR CarePlan | `M15:fhir:care-plan:{pid}:{ts}` | COMPOSITE | Per-element carry-through from M13/M14 | Yes — GOVERNANCE_GATE (stack guard, capacity, HITL); SUPPRESSION (if deferred elements) |
| FHIR Task (per element) | `M15:fhir:task:{pid}:{ts}:{element_id}` | SCALAR | Carry-through | Per-element constraint carriers |
| FHIR ServiceRequest (per element) | `M15:fhir:service-request:{pid}:{ts}:{element_id}` | SCALAR | Same as Task | Same as Task |

---

## G. Cross-Module Pointer Validation

### G.1 — Do M15's input pointers match M13 and M14 outputs?

| M15 Input | Upstream Pointer | Match? |
|---|---|---|
| `flare_risk_slopes` | `M13:obs:flare-probability:{pid}:{ts}:{horizon}` | **Match** |
| `relapse_probability` | `M13:obs:relapse-risk:{pid}:{ts}:{horizon}` | **Match** |
| `recovery_vectors` | `M13:internal:trajectory-features:{pid}:{ts}` | **Match** |
| `tier` (T0–T4) | `M14:obs:risk-tier:{pid}:{ts}` | **Match** |
| `suppression_context` | `M14:constraint:suppression-routing:{pid}:{ts}` | **Match** |
| `sla.required_by_date` | Within `M14:obs:clinician-action-bundle:{pid}:{ts}` | **Match** |

**All M13->M15 and M14->M15 pointers are consistent.**

---

## H. Gap Register

| Gap ID | V6 Requirement | Current Status | Resolution Tier | Blocking? |
|---|---|---|---|---|
| G-T2-12 | M11 `stackLevel` / `stabilityBand` / `cbm_status` input pointer | MISSING — M11 unspecified | Tier 3 (M11 addendum) | Yes — blocks TRACE_COMPLETE for M15 Step 1; Stack >= 3 guard cannot verify stack level without M11 pointer |

**No gap requires core logic change.**

---

## I. FHIR Anchor Mapping

| M15 Output | FHIR Resource | FHIR Profile Reference |
|---|---|---|
| CarePlan | `CarePlan` | Appendix C.4 |
| Per-element tasks | `Task` | Appendix C.4 |
| Per-element service requests | `ServiceRequest` | Appendix C.4 |
| Audit trail | `AuditEvent` + `Provenance` | Appendix C.7/C.11 |
| Rescheduling events | `AuditEvent` (type: PlanRevision) | Appendix C.11 |

---

## J. Addendum Acceptance Tests

| Test ID | Test | Expected Result |
|---|---|---|
| M15-AT-01 | Run with Stack >= 3; verify Stack guard GOVERNANCE_GATE carrier | `constraint_disclosure.status = CARRIERS_PRESENT` |
| M15-AT-02 | Run with Stack < 3; verify CarePlan NOT composed, guard records skip | GOVERNANCE_GATE carrier with outcome = skip |
| M15-AT-03 | Create collision during harmonization; verify capacity GOVERNANCE_GATE | Carrier present with collision details and resolution method |
| M15-AT-04 | Run with suppression active on one Track; verify SUPPRESSION carrier | `M15:constraint:suppression-deferral` present with pauseReason |
| M15-AT-05 | Verify every plan element carries `drivers[]`, `tier`, `lineage` | Support metadata present per element |
| M15-AT-06 | Trigger rescheduling on new diagnosis; verify provenance | Rescheduling event logged with actor, timestamp, trigger |
| M15-AT-07 | Verify HITL gating produces GOVERNANCE_GATE carrier | Carrier present for each element requiring approval |
| M15-AT-08 | Verify M13 uncertainty carriers carried through to plan elements | M13 CONFIDENCE_INTERVAL referenced in element provenance |
| M15-AT-09 | PSI cadence modulation applied; verify INVARIANT_ENFORCEMENT carrier | Carrier present with PSI value and modulation parameters |
