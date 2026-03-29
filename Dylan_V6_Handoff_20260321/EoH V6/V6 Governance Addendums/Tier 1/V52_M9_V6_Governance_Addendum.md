# Addendum: M9 — Reflex Suppression Core

**Modules:** M9 (Reflex Suppression Core)
**Template Version:** V5.2 → V6 Governance Addendum Template v1.0
**Validated Against:** M63 GBDC v1.0 (carrier enums §5.1, §5.2); M67 ARGL Integration Contract
**Status:** DRAFT — pending Dylan review

---

## A. Module Identity & Addendum Scope

```
Module:           V5.2 M9 — Reflex Suppression Core (Unified pauseFlag Governance)
V5.2 Spec Ref:    V5.2 Cannon, M9
Addendum Version: 1.0
Addendum Status:  DRAFT
```

**Addendum scope statement:** This addendum defines the V6 governance emission layer for M9. It specifies which artifacts M9 must emit so that M63 can construct a DerivationChain through it, what uncertainty and constraint carriers accompany those artifacts, and how M67 opt-in status is declared. Core processing logic is unchanged. This addendum adds V6 governance emission only. M9's priority ladder, TTL/time-box behavior, IDLE→ACTIVE→RESOLVE state machine, band-freezing integration, and Band-5 safety guardrail remain exactly as specified in the V5.2 Cannon.

---

## B. M63 Compliance — Derivation Chain Emission

### B.1 Output Artifact Registration

| Output | Artifact Type | Pointer Format | Provenance Record Emitted? |
|---|---|---|---|
| `pauseFlag` + `pauseReason` + `pauseStartTimestamp` + `pauseSourceModule` | Observation extension (FHIR, per C.4/H.2) | `M9:obs:suppression-state:{patient_id}:{timestamp}` | Yes — links to winning `suppression_candidates[]` entry and priority ladder evaluation |
| `suppression_state` (IDLE/ACTIVE/RESOLVE) | Observation (internal) | `M9:obs:suppression-lifecycle:{patient_id}:{timestamp}` | Yes — links to state machine transition |
| `ttl_remaining_hours` | Observation (internal) | `M9:obs:ttl-state:{patient_id}:{timestamp}` | Yes — links to activation/renewal timestamp |
| `stabilityBand.current_band` (post-suppression) | Observation (FHIR) | `M9:obs:band-gated:{patient_id}:{timestamp}` | Yes — links to pre-suppression band input + suppression state |
| `suppression_audit_events[]` | AuditEvent (FHIR) | `M9:audit:suppression-lifecycle:{patient_id}:{timestamp}:{event_type}` | Yes — routed to M41 |
| `pauseEndTimestamp` + resolution outcome | Observation extension (FHIR) | `M9:obs:suppression-resolution:{patient_id}:{timestamp}` | Yes — links to resolution trigger |

### B.2 Input Artifact Traceability

| Input | Source Module | Pointer Available? | If No, Gap Classification |
|---|---|---|---|
| `stabilityBand.prev_band` | M3 (Terrain Index Engine) | Yes | `M3:obs:stability-band:{pid}:{ts-1}` — M3 addendum defines this pointer |
| `stabilityBand.new_band` | M3 (Terrain Index Engine) | Yes | `M3:obs:stability-band:{pid}:{ts}` (pre-suppression) — M3 addendum defines this |
| `safety_flags.critical` | M6 / M20 | MISSING | G-05: Safety flag sources do not currently emit pointer-backed artifacts |
| `band5_persistence_days` | M6 / M20 | MISSING | G-06: Band-5 persistence tracking is computed but not pointer-registered |
| `suppression_candidates[]` from M5 (`SymbolicFlare`) | M5 (PSI) | MISSING | G-07: M5 does not emit pointer-backed suppression candidate artifacts |
| `suppression_candidates[]` from M7A (`LabError`, `Overshoot`, `HealingPain`) | M7A (Data Quality) | Yes | `M7A:event:qa-suppression-candidate:{pid}:{ts}` — M7 addendum (this document) defines this pointer |
| `suppression_candidates[]` from M8A (`MD_Toggle`) | M8A (Clinician Toggle) | MISSING | G-08: M8A does not emit pointer-backed suppression candidate artifacts |
| Current suppression state (if any) | M9 internal state | Yes | Self-referential: `M9:obs:suppression-state:{pid}:{ts-1}` |

### B.3 Transformation Step Registration

| Step Index | Processing Stage (from V5.2 spec) | Owning Module | Input Pointers | Output Pointer |
|---|---|---|---|---|
| 1 | Initialize effective suppression decision context (Process §1) | M9 | `M9:obs:suppression-state:{pid}:{ts-1}`, `suppression_candidates[]` (mixed availability — see B.2) | Internal context — no discrete output artifact |
| 2 | Apply critical safety guardrail (Process §2) | M9 | `safety_flags.critical` (MISSING — G-05), `band5_persistence_days` (MISSING — G-06), `M9:obs:suppression-state:{pid}:{ts-1}` | Constraint carrier: `M9:constraint:safety-guardrail:{pid}:{ts}` (if fired); else no output |
| 3 | Select active suppression reason via priority ladder (Process §3) | M9 | `suppression_candidates[]`, `gov:appendix:F.8-F.9:{v}` | `M9:obs:selected-reason:{pid}:{ts}` (internal intermediate) |
| 4 | State machine transition IDLE→ACTIVE→RESOLVE (Process §4) | M9 | `M9:obs:selected-reason:{pid}:{ts}`, `M9:obs:suppression-state:{pid}:{ts-1}` | `M9:obs:suppression-state:{pid}:{ts}`, `M9:obs:suppression-lifecycle:{pid}:{ts}` |
| 5 | TTL, auto-review, forced resolution, re-arm (Process §5) | M9 | `M9:obs:suppression-state:{pid}:{ts}`, `M9:obs:ttl-state:{pid}:{ts-1}` | `M9:obs:ttl-state:{pid}:{ts}`, constraint carrier if forced resolution fires |
| 6 | Band-freezing integration (Process §6) | M9 | `M3:obs:stability-band:{pid}:{ts}` (pre-suppression), `M9:obs:suppression-state:{pid}:{ts}` | `M9:obs:band-gated:{pid}:{ts}` |
| 7 | Audit emission (Process §7) | M9 | All outputs from steps 2–6 | `M9:audit:suppression-lifecycle:{pid}:{ts}:{event_type}` routed to M41 |

---

## C. M63 Compliance — Uncertainty Carrier Emission

### C.1 Uncertainty Inventory

| Output | Uncertainty Metadata Currently Emitted? | Carrier Type (per M63 §5.1 enum) | Action Required |
|---|---|---|---|
| `pauseFlag` + `pauseReason` | No — suppression is a deterministic binary decision | SUPPRESSION_CONTEXT | M9's suppression state output IS the uncertainty carrier for downstream consumers. Emit as SUPPRESSION_CONTEXT carrier so that M3 and other consumers can carry it through their DerivationChains. Artifact pointer: `M9:obs:suppression-state:{pid}:{ts}` |
| `stabilityBand.current_band` (post-suppression) | No — deterministic gating of an upstream value | NOT_PROVIDED | Mark NOT_PROVIDED. The band value itself carries no probabilistic metadata; the constraint that shaped it (suppression) is disclosed via constraint carrier instead. |
| `suppression_state` (IDLE/ACTIVE/RESOLVE) | No — deterministic state machine | NOT_PROVIDED | Mark NOT_PROVIDED |
| `ttl_remaining_hours` | No — deterministic countdown | NOT_PROVIDED | Mark NOT_PROVIDED |

### C.2 Degradation State

M9 does not emit a degradation state. M9 operates deterministically on whatever suppression candidates it receives. If no candidates arrive, the state machine simply remains IDLE — this is normal operation, not degradation.

**One exception:** If `safety_flags.critical` or `band5_persistence_days` inputs are unavailable (i.e., the safety guardrail inputs cannot be evaluated), M9 should emit a DEGRADATION_STATE carrier indicating that the safety guardrail could not be enforced. This is a safety-critical gap. See G-09.

---

## D. M63 Compliance — Constraint Carrier Emission

### D.1 Constraint Inventory

| Constraint | Trigger Condition (V5.2 spec ref) | Constraint Type (per M63 §5.2 enum) | Currently Emitted as Artifact? | Action Required |
|---|---|---|---|---|
| Band-5 safety guardrail: suppression blocked/cleared when Band 5 persists ≥7 days | Process §2 | INVARIANT_ENFORCEMENT | No — enforced structurally; logged in audit hooks but not as M63 constraint carrier | Emit INVARIANT_ENFORCEMENT constraint carrier when guardrail fires. Artifact: `M9:constraint:band5-safety-guardrail:{pid}:{ts}` |
| Critical safety override: suppression cleared when `safety_flags.critical == true` | Process §2 | INVARIANT_ENFORCEMENT | No | Emit INVARIANT_ENFORCEMENT constraint carrier. Artifact: `M9:constraint:critical-safety-override:{pid}:{ts}` |
| Priority ladder enforcement: highest-priority candidate reason wins | Process §3 | GOVERNANCE_GATE | No — enforced deterministically but not emitted as carrier | Emit GOVERNANCE_GATE carrier on every suppression activation/reason-change. Artifact: `M9:constraint:priority-ladder:{pid}:{ts}` with pointer to `gov:appendix:F.8-F.9:{v}` |
| Single active suppression invariant | Process §4 | INVARIANT_ENFORCEMENT | No | Emit INVARIANT_ENFORCEMENT carrier when a reason-change preempts a lower-priority active suppression. Artifact: `M9:constraint:single-active-suppression:{pid}:{ts}` |
| Band-freezing: upward Band movement held when suppression active | Process §6 | SUPPRESSION | Partial — suppression is logged but not as a typed constraint carrier | Emit SUPPRESSION constraint carrier when band-freeze fires. Artifact: `M9:constraint:band-freeze:{pid}:{ts}` — this is the artifact M3 references at its Step 4 |
| TTL forced resolution: max 7 days | Process §5 | GOVERNANCE_GATE | No | Emit GOVERNANCE_GATE carrier when forced resolution fires. Artifact: `M9:constraint:ttl-forced-resolution:{pid}:{ts}` |
| Re-arm restriction: only on new evidence | Process §5 | GOVERNANCE_GATE | No | Emit GOVERNANCE_GATE carrier when re-arm is attempted (whether permitted or blocked). Artifact: `M9:constraint:rearm-evaluation:{pid}:{ts}` |

### D.2 Materiality Declaration

For each constraint in D.1: when the constraint fires, M9 MUST include the corresponding constraint record in its output bundle. The Band-5 safety guardrail and critical safety override are the highest-materiality constraints — they override all other suppression behavior and must always produce carriers when they fire, per M63 §3.4.

The band-freeze constraint (SUPPRESSION type) at Step 6 is the most architecturally significant for cross-module tracing: it is the artifact that M3 references at its suppression application step, and that M63 follows when constructing a chain through M3→M9→M3 band-gating.

---

## E. M67 (ARGL) Integration — Opt-In Declaration

**Opt-in status:** DEFERRED

**Reason for deferral:** M9 is a deterministic governance module that applies a priority ladder and state machine to suppression candidates. It does not produce clinical interpretations, pattern detections, or recommendations. Its outputs are structural governance artifacts (suppression state, band-gating decisions), not reasoning conclusions subject to adversarial review.

**Conditions for future opt-in:** If M9's priority ladder is replaced with a learned or adaptive suppression policy (e.g., context-sensitive suppression weighting), ARGL opt-in should be reconsidered. This would be a core logic change.

---

## F. FHIR Audit Artifact Emission

### F.1 AuditEvent Emission

| Event | Trigger | Required Fields |
|---|---|---|
| `M9:audit:suppression-activated` | `suppression_state` transitions IDLE→ACTIVE | `patient_id`, `timestamp`, `pauseReason`, `pauseSourceModule`, `selected_reason_ladder_position`, `candidate_count`, `evidence_ref_ids[]`, `ttl_set`, `module_version`, `F.8-F.9_version` |
| `M9:audit:suppression-renewed` | Auto-review at 24h or new evidence renewal | `patient_id`, `timestamp`, `pauseReason`, `ttl_remaining`, `renewal_basis` (new_evidence / policy_default), `module_version` |
| `M9:audit:suppression-resolved` | `suppression_state` transitions ACTIVE→RESOLVE→IDLE | `patient_id`, `timestamp`, `resolution_outcome` (confirm/lift/escalate), `pauseEndTimestamp`, `final_band`, `critical_event_occurred`, `module_version` |
| `M9:audit:safety-guardrail-fired` | Band-5 ≥7 days or `safety_flags.critical` | `patient_id`, `timestamp`, `guardrail_type` (band5_persistence / critical_flag), `band5_persistence_days` or `safety_flags.critical`, `suppression_cleared`, `module_version` |
| `M9:audit:band-freeze-applied` | Band-freezing prevents upward movement | `patient_id`, `timestamp`, `prev_band`, `new_band_proposed`, `band_held_at`, `suppression_record_ref`, `module_version` |

### F.2 Provenance Emission

| Provenance Record | Connects | FHIR Resource Type |
|---|---|---|
| `M9:prov:candidate-to-selection` | `suppression_candidates[]` → `selected_reason` via priority ladder | Provenance |
| `M9:prov:selection-to-state` | `selected_reason` + prior state → new `suppression_state` | Provenance |
| `M9:prov:state-to-band-gate` | `suppression_state` + pre-suppression Band → post-suppression Band | Provenance |
| `M9:prov:guardrail-to-clear` | Safety inputs → suppression cleared/blocked | Provenance |

---

## G. V6 Consumer Contract

| V6 Consumer | What It Reads | Contract Reference | Addendum Satisfies? |
|---|---|---|---|
| M63 (GBDC) | DerivationChain steps through suppression logic; SUPPRESSION and INVARIANT_ENFORCEMENT constraint carriers | M63 §2, §5.2 | Partial — steps defined; 4 input pointers MISSING (G-05 through G-08); constraint carriers fully specified |
| M3 (Terrain Index Engine) | `M9:obs:suppression-state:{pid}:{ts}` for band-freeze application; `M9:constraint:band-freeze:{pid}:{ts}` as constraint carrier | M3 addendum Step 4 | Yes — pointers match M3 addendum B.2 and B.3 Step 4 |
| M67 (ARGL) | `suppression_state` as context input (read-only) | M67 upstream dependency list | Yes — M67 reads suppression state as context, not as ARGL-governed output |
| M68 (ICM) | Suppression state as context | M68 input layer | Yes — pointer available |
| M7B (Care Plan Orchestrator) | Suppression context for suppression-aware routing | M7B Process §5.5 | Yes — `M9:obs:suppression-state:{pid}:{ts}` available for M7B consumption |

---

## H. Gap Register

| Gap ID | V6 Requirement | Why Addendum Cannot Satisfy | Resolution Path |
|---|---|---|---|
| G-05 | M63 §3.1 Trace Integrity: `safety_flags.critical` input pointer | M6/M20 safety flag sources do not emit pointer-backed artifacts. M9 cannot create pointers for data it does not own. | M6/M20 addendum (Tier 2/3) must register safety flag artifacts. |
| G-06 | M63 §3.1 Trace Integrity: `band5_persistence_days` input pointer | Band-5 persistence tracking is computed but not registered as a discrete artifact by M6/M20. | Same resolution as G-05. |
| G-07 | M63 §3.1 Trace Integrity: M5 suppression candidate pointer | M5 (`SymbolicFlare` candidate) does not emit pointer-backed suppression candidate artifacts. | M5 addendum (Tier 2) must register suppression candidates as artifacts. |
| G-08 | M63 §3.1 Trace Integrity: M8A suppression candidate pointer | M8A (`MD_Toggle` candidate) does not emit pointer-backed artifacts. | M8A addendum (Tier 2) must register clinician toggle events as artifacts. |
| G-09 | M63 §5.1 Uncertainty: DEGRADATION_STATE when safety guardrail inputs unavailable | If `safety_flags.critical` or `band5_persistence_days` are unavailable, M9 cannot evaluate its safety guardrail. Emitting a degradation carrier for this scenario requires M9 to detect input absence — which is currently not part of its invocation contract (M9 assumes these inputs arrive). | Requires invocation contract change: M9 must validate safety inputs on entry and emit DEGRADATION_STATE if they are missing. This is a minor safety-enhancing core logic extension — recommend micro-patch, not Tier 4. |

---

## I. Implementation Checklist

| Item | Status | Notes |
|---|---|---|
| Output artifact pointers defined | ☑ | B.1 complete — 6 outputs registered |
| Input traceability mapped | ☑ | B.2 complete — 4 MISSING gaps registered |
| Transformation steps registered | ☑ | B.3 complete — 7 steps |
| Uncertainty carriers defined or NOT_PROVIDED declared | ☑ | C.1 complete — 1 SUPPRESSION_CONTEXT, 3 NOT_PROVIDED |
| Constraint carriers defined or NOT_PROVIDED declared | ☑ | D.1 complete — 7 constraints, all require new emission |
| ARGL opt-in status declared | ☑ | DEFERRED with rationale |
| FHIR audit artifacts specified | ☑ | F.1/F.2 complete |
| V6 consumer contracts validated | ☑ | G table complete |
| Gap register complete | ☑ | 5 gaps registered |
| Addendum reviewed against V5.2 spec (no core logic changes) | ☐ | Pending — G-09 flagged as micro-patch |

---

## J. Acceptance Tests

| ID | Test | Expected Result |
|---|---|---|
| AT-01 | M9 produces identical suppression decisions, band-gating, TTL behavior, and safety guardrail enforcement with and without addendum emission layer active | Core logic unchanged; emission is additive only |
| AT-02 | M63 can construct a DerivationChain through M9 using emitted artifacts | Steps 2, 3, 4, 5, 6 are POINTER_BACKED for internal logic; Steps 1–2 TRACE_PARTIAL for external inputs (G-05 through G-08) |
| AT-03 | Uncertainty carriers match M63 §5.1 enum types | SUPPRESSION_CONTEXT is valid §5.1 enum; all others NOT_PROVIDED |
| AT-04 | Constraint carriers match M63 §5.2 enum types | SUPPRESSION, INVARIANT_ENFORCEMENT, GOVERNANCE_GATE — all from closed §5.2 enum |
| AT-05 | ARGL integration status is DEFERRED | No ARGL invocation code in M9 |
| AT-06 | Existing downstream V5.2 consumers (M3 band-freeze, M41 audit, M48 governance) receive unchanged outputs | No breaking changes to M9's output contract |
| AT-07 | M3 addendum Step 4 can resolve `M9:obs:suppression-state:{pid}:{ts}` and `M9:constraint:band-freeze:{pid}:{ts}` | Cross-module pointer consistency verified |
