# Addendum: M3 — Terrain Index Engine

**Modules:** M3 (Terrain Index Engine)
**Template Version:** V5.2 → V6 Governance Addendum Template v1.0
**Validated Against:** M63 GBDC v1.0 (carrier enums §5.1, §5.2); M67 ARGL Integration Contract
**Status:** DRAFT — pending Dylan review

---

## A. Module Identity & Addendum Scope

```
Module:           V5.2 M3 — Terrain Index Engine (Stability Band + Stack Level)
V5.2 Spec Ref:    V5.2 Cannon, M3 (M3A: Stability Score→Band; M3B: Stack Score→Stack Level)
Addendum Version: 1.0
Addendum Status:  DRAFT
```

**Addendum scope statement:** This addendum defines the V6 governance emission layer for M3. It specifies which artifacts M3 must emit so that M63 can construct a DerivationChain through it, what uncertainty and constraint carriers accompany those artifacts, and how M67 opt-in status is declared. Core processing logic is unchanged. This addendum adds V6 governance emission only. M3's weighted additive aggregation, Band mapping, Stack counting, complication depth marking, CBM event emission, and suppression propagation semantics remain exactly as specified in the V5.2 Cannon. No new variables, thresholds, scoring formulas, or state machines are introduced.

---

## B. M63 Compliance — Derivation Chain Emission

### B.1 Output Artifact Registration

| Output | Artifact Type | Pointer Format | Provenance Record Emitted? |
|---|---|---|---|
| `stabilityScore` | Observation (FHIR) | `M3:obs:stability-score:{patient_id}:{timestamp}` | Yes — links to input `normalizedTags[]` snapshot |
| `stabilityBand` | Observation (FHIR) | `M3:obs:stability-band:{patient_id}:{timestamp}` | Yes — links to `stabilityScore` artifact |
| `stackLevel` | Observation (FHIR) | `M3:obs:stack-level:{patient_id}:{timestamp}` | Yes — links to `confirmedDiagnoses[]` snapshot |
| `complicationDepth` | Observation (FHIR) | `M3:obs:complication-depth:{patient_id}:{timestamp}` | Yes — links to `complicationDepthMarkers[]` |
| `pauseFlag` + `pauseReason` (propagated) | Observation extension (FHIR, per C.4) | `M3:obs:suppression-state:{patient_id}:{timestamp}` | Yes — links to upstream M9 suppression record |
| `rationale` (top contributors) | DocumentReference (internal) | `M3:doc:rationale:{patient_id}:{timestamp}` | Yes — links to `stabilityScore` computation |
| `trendFlag` | Flag (FHIR) | `M3:flag:trend:{patient_id}:{timestamp}` | Yes — links to `stabilityScore` trajectory |
| `CBM_entered` / `CBM_exited` | DetectedIssue (FHIR) | `M3:event:cbm-transition:{patient_id}:{timestamp}` | Yes — links to Stack/Band state at transition |

### B.2 Input Artifact Traceability

| Input | Source Module | Pointer Available? | If No, Gap Classification |
|---|---|---|---|
| `normalizedTags[]` | M4 (Tag Normalization) / upstream coding layers | MISSING | G-01: M4 does not currently emit pointer-backed normalized tag snapshots; tags arrive as transient payloads without artifact IDs |
| `confirmedDiagnoses[]` | M10 / upstream diagnosis lifecycle | MISSING | G-02: Diagnosis lifecycle events lack discrete artifact pointers traceable to M63; lifecycle is event-driven but not pointer-registered |
| `diagnosisLifecycleEvents[]` | M10 / upstream | MISSING | Same as G-02 |
| `complicationDepthMarkers[]` | M10 / upstream | MISSING | G-03: Complication depth markers are display metadata without dedicated artifact pointers |
| `pauseFlag` + `pauseReason` | M9 (Reflex Suppression Core) | Yes | — M9 addendum (this document) defines `M9:obs:suppression-state:{patient_id}:{timestamp}` |
| Appendix H.5 (ladder semantics) | Governance infrastructure | Yes | Version-pinned reference pointer: `gov:appendix:H.5:{version}` |
| Appendix H.2 (field definitions) | Governance infrastructure | Yes | Version-pinned reference pointer: `gov:appendix:H.2:{version}` |
| Appendix F.5–F.9 (suppression policy) | Governance infrastructure | Yes | Version-pinned reference pointer: `gov:appendix:F.5-F.9:{version}` |

### B.3 Transformation Step Registration

| Step Index | Processing Stage (from V5.2 spec) | Owning Module | Input Pointers | Output Pointer |
|---|---|---|---|---|
| 1 | Enforce umbrella invariants (M3 Process §1) | M3 | `gov:appendix:H.5:{v}`, `gov:appendix:H.2:{v}` | No discrete output — gate only; constraint carrier emitted (see D.1) |
| 2 | Compute Stability Score via weighted additive aggregation (M3A, Process §2.1–2.2) | M3 | `normalizedTags[]` snapshot (MISSING — G-01) | `M3:obs:stability-score:{pid}:{ts}` |
| 3 | Map Stability Score → Stability Band using governed thresholds (M3A, Process §2.3) | M3 | `M3:obs:stability-score:{pid}:{ts}`, `gov:appendix:H.5:{v}` | `M3:obs:stability-band:{pid}:{ts}` (pre-suppression) |
| 4 | Apply suppression safeguard (M3A, Process §2.4) — consumes M9 output | M3 + M9 | `M3:obs:stability-band:{pid}:{ts}` (pre-suppression), `M9:obs:suppression-state:{pid}:{ts}` | `M3:obs:stability-band:{pid}:{ts}` (post-suppression); constraint carrier emitted |
| 5 | Compute Stack Level from confirmed diagnoses (M3B, Process §3.1–3.4) | M3 | `confirmedDiagnoses[]` snapshot (MISSING — G-02) | `M3:obs:stack-level:{pid}:{ts}` |
| 6 | Compute complication depth (M3B, Process §3.2) | M3 | `complicationDepthMarkers[]` (MISSING — G-03) | `M3:obs:complication-depth:{pid}:{ts}` |
| 7 | Emit CBM enter/exit events (Process §4) | M3 | `M3:obs:stability-band:{pid}:{ts}`, `M3:obs:stack-level:{pid}:{ts}`, `gov:appendix:H.5:{v}` | `M3:event:cbm-transition:{pid}:{ts}` |
| 8 | Audit-grade emission (Process §5) | M3 | All outputs from steps 2–7 | AuditEvent + Provenance records per C.4/C.11 |

---

## C. M63 Compliance — Uncertainty Carrier Emission

### C.1 Uncertainty Inventory

| Output | Uncertainty Metadata Currently Emitted? | Carrier Type (per M63 §5.1 enum) | Action Required |
|---|---|---|---|
| `stabilityScore` | No — continuous scalar with no bounds or interval metadata | NOT_PROVIDED | Mark NOT_PROVIDED. Future: emit CONFIDENCE_INTERVAL reflecting tag completeness/quality (requires M7A confidence integration — see G-04) |
| `stabilityBand` | No — discrete categorical derived from score; no probabilistic metadata | NOT_PROVIDED | Mark NOT_PROVIDED |
| `stackLevel` | No — deterministic count; uncertainty is in the diagnosis confirmation upstream, not in the count itself | NOT_PROVIDED | Mark NOT_PROVIDED. Correct: uncertainty belongs to the diagnosis lifecycle modules, not M3 |
| `complicationDepth` | No | NOT_PROVIDED | Mark NOT_PROVIDED |
| `pauseFlag` / `pauseReason` (propagated) | Yes — M9 emits suppression context | SUPPRESSION_CONTEXT | Carry through from M9 artifact pointer (no new carrier created by M3) |
| `trendFlag` | No — binary instrumentation flag | NOT_PROVIDED | Mark NOT_PROVIDED |
| `CBM_entered` / `CBM_exited` | No — deterministic event from Stack/Band rules | NOT_PROVIDED | Mark NOT_PROVIDED |

### C.2 Degradation State

M3 does not currently emit a widened-uncertainty or reduced-confidence state when inputs are sparse or unstable. The `trendFlag` is instrumentation-only and does not constitute a degradation state carrier.

**However**, M3 *receives* M7A's failsafe withholding signal (the "uncertain day" marker). When M7A withholds downstream scoring due to >30% critical input invalidity, M3 does not execute its computation cycle. This means M3 produces *no output* rather than a degraded output — the absence of an M3 artifact for a given timestamp is itself the degradation signal.

**Action Required:** Emit a `DEGRADATION_STATE` carrier when M3 is not invoked due to M7A failsafe withholding. The carrier artifact pointer references the M7A failsafe record (`M7A:event:failsafe-withhold:{pid}:{ts}`). See G-04 for implementation dependency.

---

## D. M63 Compliance — Constraint Carrier Emission

### D.1 Constraint Inventory

| Constraint | Trigger Condition (V5.2 spec ref) | Constraint Type (per M63 §5.2 enum) | Currently Emitted as Artifact? | Action Required |
|---|---|---|---|---|
| No Band→Stack coupling | Process §1.ii: "Do not allow Band shifts to increment Stack" | INVARIANT_ENFORCEMENT | No — enforced structurally but not emitted as a discrete artifact | Emit constraint record when this invariant is tested and holds (i.e., when a Band shift occurs and Stack is confirmed unchanged). Artifact: `M3:constraint:no-band-stack-coupling:{pid}:{ts}` |
| Single suppression channel | Process §1.iii: "Enforce a single suppression channel" | INVARIANT_ENFORCEMENT | No — enforced structurally | Emit constraint record on every suppression propagation event. Artifact: `M3:constraint:single-suppression-channel:{pid}:{ts}` |
| Suppression band-freeze | Process §2.4: pauseFlag/pauseReason holds/dampens upward Band movement | SUPPRESSION | Partial — suppression is logged per audit hooks, but not as a typed M63 constraint carrier | Emit SUPPRESSION constraint carrier referencing the M9 suppression record. Artifact: `M3:constraint:suppression-band-freeze:{pid}:{ts}` with `source_artifact_pointer → M9:obs:suppression-state:{pid}:{ts}` |
| Thresholds governed elsewhere | Process §1.iv + Governance: "numeric cut-points, TTL windows, and escalation tiers are not hard-coded in M3" | GOVERNANCE_GATE | No — implicit | Emit GOVERNANCE_GATE carrier referencing the appendix version that supplies the active thresholds. Artifact: `M3:constraint:threshold-governance:{pid}:{ts}` with pointer to `gov:appendix:H.5:{v}` |
| No auto-diagnosis | Governance: "Stack changes only via confirmed diagnosis lifecycle" | INVARIANT_ENFORCEMENT | No | Emit constraint record when a Stack change occurs, linking to the triggering diagnosis lifecycle event. Artifact: `M3:constraint:no-auto-diagnosis:{pid}:{ts}` |

### D.2 Materiality Declaration

For each constraint in D.1: when the constraint fires (i.e., when the invariant is enforced, suppression is applied, or a governance gate is consulted), M3 MUST include the corresponding constraint record in its output bundle for that computation cycle. This constitutes M3's materiality declaration per M63 §3.4.

The SUPPRESSION constraint at Step 4 is the highest-frequency materiality trigger — it fires every time M9 has an active suppression and M3's pre-suppression Band exceeds the previous Band.

---

## E. M67 (ARGL) Integration — Opt-In Declaration

**Opt-in status:** DEFERRED

**Reason for deferral:** M3 is a state-computation module that performs deterministic aggregation and mapping. It does not produce clinical interpretations, pattern detections, trajectory forecasts, or recommendation candidates — the categories of output for which ARGL governance is designed. M3's outputs (Band, Stack, CBM events) are structural state variables, not reasoning conclusions.

**Conditions for future opt-in:** If M3's weighted additive aggregation is replaced or augmented with model-based scoring that produces probabilistic outputs (e.g., a learned aggregation function), ARGL opt-in should be reconsidered. This would be a core logic change and belongs in Tier 4 rewrite territory, not this addendum.

---

## F. FHIR Audit Artifact Emission

### F.1 AuditEvent Emission

| Event | Trigger | Required Fields |
|---|---|---|
| `M3:audit:score-computed` | Every Stability Score computation | `patient_id`, `timestamp`, `stabilityScore`, `tag_snapshot_ref`, `module_version`, `H.5_version` |
| `M3:audit:band-transition` | Band value changes from previous cycle | `patient_id`, `timestamp`, `prev_band`, `new_band`, `suppression_state`, `driver_summary`, `module_version` |
| `M3:audit:stack-transition` | Stack Level changes | `patient_id`, `timestamp`, `prev_stack`, `new_stack`, `diagnosis_event_ref`, `module_version` |
| `M3:audit:cbm-transition` | CBM entered or exited | `patient_id`, `timestamp`, `event_type` (entered/exited), `band_at_event`, `stack_at_event`, `H.5_version` |
| `M3:audit:suppression-applied` | Suppression dampens/holds Band movement | `patient_id`, `timestamp`, `pre_suppression_band`, `post_suppression_band`, `suppression_record_ref` (→ M9), `module_version` |
| `M3:audit:complication-depth-change` | Complication depth marker added/removed | `patient_id`, `timestamp`, `layer`, `prev_depth`, `new_depth`, `module_version` |

### F.2 Provenance Emission

| Provenance Record | Connects | FHIR Resource Type |
|---|---|---|
| `M3:prov:score-from-tags` | `normalizedTags[]` snapshot → `stabilityScore` | Provenance |
| `M3:prov:band-from-score` | `stabilityScore` → `stabilityBand` (pre-suppression) | Provenance |
| `M3:prov:band-suppression` | `stabilityBand` (pre) + M9 suppression record → `stabilityBand` (post) | Provenance |
| `M3:prov:stack-from-diagnoses` | `confirmedDiagnoses[]` → `stackLevel` | Provenance |
| `M3:prov:cbm-from-state` | `stabilityBand` + `stackLevel` + H.5 rules → CBM event | Provenance |

---

## G. V6 Consumer Contract

| V6 Consumer | What It Reads | Contract Reference | Addendum Satisfies? |
|---|---|---|---|
| M63 (GBDC) | DerivationChain steps, uncertainty carriers, constraint carriers | M63 §2, §5 | Partial — steps defined and pointer-formatted; uncertainty is NOT_PROVIDED for most outputs (correct per spec: M3 outputs are deterministic scalars/categoricals, not probabilistic); 3 input pointers MISSING (G-01, G-02, G-03) |
| M64 (FUDD) | `stabilityBand` as context input | M64 input contract (M6/M13 reference) | Yes — `M3:obs:stability-band` pointer is available |
| M67 (ARGL) | N/A — M3 is DEFERRED for ARGL | M67 integration contract | N/A — deferred |
| M68 (ICM) | `stabilityBand`, `stackLevel` as input layer | M68 stack placement diagram | Yes — both pointers available |
| M9 (Reflex Suppression Core) | `stabilityBand.prev_band`, `stabilityBand.new_band` | M9 input contract | Yes — M3 emits both pre- and post-suppression Band artifacts with distinct pointers |

---

## H. Gap Register

| Gap ID | V6 Requirement | Why Addendum Cannot Satisfy | Resolution Path |
|---|---|---|---|
| G-01 | M63 §3.1 Trace Integrity: every input must be pointer-backed or explicitly MISSING | `normalizedTags[]` arrive as transient payloads from M4/upstream without artifact IDs. M3 cannot create pointer-backed input references for data it does not own. | M4 addendum (Tier 2) must emit pointer-backed tag snapshots. Until then, Step 2 is MISSING and chain is TRACE_PARTIAL. |
| G-02 | M63 §3.1 Trace Integrity: input pointer for confirmed diagnoses | `confirmedDiagnoses[]` and `diagnosisLifecycleEvents[]` lack discrete artifact pointers from M10/upstream lifecycle. | M10 addendum (Tier 3) or diagnosis lifecycle rewrite must register lifecycle events as pointer-backed artifacts. |
| G-03 | M63 §3.1 Trace Integrity: input pointer for complication depth markers | `complicationDepthMarkers[]` are display metadata without artifact IDs. | Same resolution as G-02 — upstream must register. |
| G-04 | M63 §5.1 Uncertainty: DEGRADATION_STATE carrier when M7A withholds | M3 currently produces no artifact when M7A withholds. Emitting a DEGRADATION_STATE carrier requires M3 to be *invoked* to produce an artifact even when withholding — this would change the invocation contract. | Requires coordinated M7A/M3 invocation contract change: M3 must run in "degraded emission mode" when M7A withholds, producing a degradation record instead of a full computation. This is a minor core logic extension — evaluate for Tier 4 or a micro-patch. |

---

## I. Implementation Checklist

| Item | Status | Notes |
|---|---|---|
| Output artifact pointers defined | ☑ | B.1 complete — 8 outputs registered |
| Input traceability mapped | ☑ | B.2 complete — 3 MISSING gaps registered |
| Transformation steps registered | ☑ | B.3 complete — 8 steps, Steps 2/5/6 have MISSING inputs |
| Uncertainty carriers defined or NOT_PROVIDED declared | ☑ | C.1 complete — 6 NOT_PROVIDED, 1 SUPPRESSION_CONTEXT passthrough |
| Constraint carriers defined or NOT_PROVIDED declared | ☑ | D.1 complete — 5 constraints, all require new emission |
| ARGL opt-in status declared | ☑ | DEFERRED with rationale |
| FHIR audit artifacts specified | ☑ | F.1/F.2 complete |
| V6 consumer contracts validated | ☑ | G table complete |
| Gap register complete | ☑ | 4 gaps registered |
| Addendum reviewed against V5.2 spec (no core logic changes) | ☐ | Pending — G-04 flagged as potential micro-patch |

---

## J. Acceptance Tests

| ID | Test | Expected Result |
|---|---|---|
| AT-01 | M3 produces identical `stabilityScore`, `stabilityBand`, `stackLevel`, `complicationDepth`, CBM events, `pauseFlag`/`pauseReason` with and without addendum emission layer active | Core logic unchanged; emission is additive only |
| AT-02 | M63 can construct a DerivationChain through M3 using emitted artifacts | Steps 1, 3, 4, 7, 8 are POINTER_BACKED; Steps 2, 5, 6 are TRACE_PARTIAL (MISSING input pointers — G-01, G-02, G-03) |
| AT-03 | Uncertainty carriers match M63 §5.1 enum types | SUPPRESSION_CONTEXT passthrough from M9 uses valid enum; all others NOT_PROVIDED — no invented carrier types |
| AT-04 | Constraint carriers match M63 §5.2 enum types | SUPPRESSION, INVARIANT_ENFORCEMENT, GOVERNANCE_GATE — all from closed §5.2 enum |
| AT-05 | ARGL integration status is DEFERRED | No ARGL invocation code in M3 |
| AT-06 | Existing downstream V5.2 consumers (M6, M9, M20, M68, M64) receive unchanged outputs | No breaking changes to M3's output contract |
