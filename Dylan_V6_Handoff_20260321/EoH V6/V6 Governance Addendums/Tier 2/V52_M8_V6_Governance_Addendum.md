# Addendum: M8 — Clinician Suppression Controls & Systemwide Suppression Governance

**Template Version:** V5.2 -> V6 Governance Addendum Template v1.0
**Validated Against:** M63 GBDC v1.0 (§2–§7)
**Upstream Reference:** Tier 1 Cross-Module Validation Report
**Status:** DRAFT — Emission Layer Only; No Core Logic Changes
**Tier 1 Gap Resolved:** G-08 (M8A MD_Toggle suppression candidate pointer)

---

## A. Module Identity & Addendum Scope

| Field | Value |
|---|---|
| Module ID | M8 |
| Module Name | Clinician Suppression Controls & Systemwide Suppression Governance |
| V5.2 Spec Version | V5.2 |
| Addendum Version | V6-A.1.0 |
| Addendum Type | Emission Layer |
| Core Logic Modified | No |
| M63 Contract Coverage | Trace Integrity, Support Disclosure, Uncertainty Preservation, Constraint Disclosure |

**Scope:** M8 is fundamentally a **constraint source** — it defines and governs the canonical suppression fields that shape outputs across the entire pipeline. Every module that reads `pauseFlag`/`pauseReason` downstream is consuming M8's constraint output. This addendum formalizes M8 as the emitter of SUPPRESSION and INVARIANT_ENFORCEMENT constraint carriers, and critically, **resolves Tier 1 Gap G-08** (M9 B.2 declared M8A MD_Toggle suppression candidate as MISSING).

**Tier 1 Gap Resolution:** M9's Tier 1 addendum identified Gap G-08: the M8A (MD_Toggle) suppression candidate pointer was MISSING. This addendum provides the pointer: `M8:obs:suppression-candidate:md-toggle:{pid}:{ts}`. With this addendum in place, M9 Step 1 can resolve the MD_Toggle candidate to a pointer-backed input. **G-08 is resolved.**

---

## B. Input Artifact Pointer Table

| V5.2 Input | Source Module | Artifact Pointer Format | Status |
|---|---|---|---|
| Suppression candidates: `SymbolicFlare` | M5 | `M5:obs:symbolic-flare:{pid}:{ts}` | Pointer-backed |
| Suppression candidates: persona flags, PSI context | M5 | `M5:obs:psi:{pid}:{ts}`, `M5:obs:symbolic-flags:{pid}:{ts}` | Pointer-backed |
| QA/sanity triggers: `LabError` | M7A | `M7A:obs:qa-trigger:lab-error:{pid}:{ts}` | Pointer-backed (M7 Tier 1 addendum) |
| QA/sanity triggers: `Overshoot` | M7A | `M7A:obs:qa-trigger:overshoot:{pid}:{ts}` | Pointer-backed |
| QA/sanity triggers: `HealingPain` | M7A | `M7A:obs:qa-trigger:healing-pain:{pid}:{ts}` | Pointer-backed |
| Clinician toggle actions (MD Toggle) | M8A | `M8A:event:md-toggle-action:{pid}:{ts}:{session_id}` | Pointer-backed — **this addendum is the authority for this pointer** |
| Locked suppression fields (Appendix H.2) | Governance | `governance:appendix:H.2:{version}` | Pointer-backed |
| Critical instability context (Zone 5) | M6/M3 | `M3:obs:stability-band:{pid}:{ts}` (Band 5) | Pointer-backed (M3 Tier 1 addendum); **MISSING** for M6's direct emission |

---

## C. Uncertainty Carrier Emissions

M8 does not produce probabilistic outputs. However, M8 produces a **SUPPRESSION_CONTEXT** uncertainty carrier that downstream modules use to understand their data environment has been altered by suppression.

| Output | Output Form Class | Uncertainty Carrier Type | Carrier Content | Artifact Pointer |
|---|---|---|---|---|
| Unified suppression state when active | SCALAR (Boolean + enum) | **SUPPRESSION_CONTEXT** | Which reason is active; priority selection trace; TTL reference; that downstream environments are operating under suppression | `M8:unc:suppression-context:{pid}:{ts}` |
| Unified suppression state when NOT active | SCALAR | No uncertainty carrier required | — | — |

---

## D. Constraint Carrier Emissions

M8 is the **primary constraint source** for the suppression subsystem.

| Constraint Scenario | Constraint Type (§5.2) | Carrier Content | Artifact Pointer |
|---|---|---|---|
| Suppression activated (any canonical reason) | **SUPPRESSION** | pauseFlag=true, pauseReason, pauseStartTimestamp, pauseSourceModule, TTL reference | `M8:constraint:suppression-active:{pid}:{ts}` with source_artifact_pointer to triggering module |
| Single-reason invariant enforced | **INVARIANT_ENFORCEMENT** | Candidate list with sources; selected reason; priority ladder reference (F.9); rejected candidates | `M8:constraint:single-reason-invariant:{pid}:{ts}` with `source_artifact_pointer -> governance:appendix:F.9:{version}` |
| MD Toggle session-default scope enforced | **INVARIANT_ENFORCEMENT** | Toggle scope (session-only vs. extended); session_id; expiry conditions | `M8:constraint:md-toggle-scope:{pid}:{ts}:{session_id}` |
| Zone 5 safety override of MD Toggle | **GOVERNANCE_GATE** | Critical band detection reference; MD Toggle overridden; Zone 5 cannot be masked | `M8:constraint:zone5-override:{pid}:{ts}` with `source_artifact_pointer -> M3:obs:stability-band:{pid}:{ts}` |
| Non-destructive semantics enforced | **INVARIANT_ENFORCEMENT** | Confirmation raw data NOT deleted/overwritten; suppression only affected Band computation participation | `M8:constraint:non-destructive:{pid}:{ts}` |
| State alignment check (M6 <> M11 <> M41) | **INVARIANT_ENFORCEMENT** | Cross-module consistency verification result; modules checked; discrepancies | `M8:constraint:state-alignment:{pid}:{ts}` |

---

## E. Process Step -> Transformation Record Mapping

| V5.2 Step | step_index | owning_module_id | input_artifact_pointers[] | output_artifact_pointer | step_status |
|---|---|---|---|---|---|
| 1. Initialize/require canonical fields | 1 | M8 | `governance:appendix:H.2:{version}` | `M8:internal:canonical-fields-initialized:{pid}:{ts}` | POINTER_BACKED |
| 2. Ingest suppression candidates | 2 | M8 | `[M5:obs:symbolic-flare, M5:obs:psi, M5:obs:symbolic-flags, M7A:obs:qa-trigger:*, M8A:event:md-toggle-action]` | `M8:internal:candidate-list:{pid}:{ts}` | POINTER_BACKED |
| 3. Enforce canonical reason set | 3 | M8 | `M8:internal:candidate-list:{pid}:{ts}` | `M8:internal:validated-candidates:{pid}:{ts}` | POINTER_BACKED |
| 4. Enforce single-reason invariant | 4 | M8 | `M8:internal:validated-candidates:{pid}:{ts}`, `governance:appendix:F.9:{version}` | `M8:obs:selected-reason:{pid}:{ts}`, `M8:constraint:single-reason-invariant:{pid}:{ts}` | POINTER_BACKED |
| 5. Apply MD Toggle activation | 5 | M8 | `M8A:event:md-toggle-action:{pid}:{ts}:{session_id}` (if present) | `M8:obs:suppression-candidate:md-toggle:{pid}:{ts}` -- **resolves Tier 1 G-08** | POINTER_BACKED |
| 6. Apply MD Toggle persistence/reactivation | 6 | M8 | `M8:obs:suppression-candidate:md-toggle:{pid}:{ts}`, new evidence events | `M8:internal:toggle-lifecycle:{pid}:{ts}:{session_id}` | POINTER_BACKED |
| 7. Apply safety override for MD Toggle | 7 | M8 | `M3:obs:stability-band:{pid}:{ts}` (if Band 5), `M8:obs:suppression-candidate:md-toggle:{pid}:{ts}` | `M8:constraint:zone5-override:{pid}:{ts}` (if Zone 5), `M8:internal:override-result:{pid}:{ts}` | POINTER_BACKED |
| 8. Apply non-destructive semantics | 8 | M8 | (all prior step outputs) | `M8:constraint:non-destructive:{pid}:{ts}` | POINTER_BACKED |
| 9. Emit outputs | 9 | M8 | `M8:obs:selected-reason:{pid}:{ts}`, all constraint carriers | `M8:obs:suppression-state:{pid}:{ts}` (unified), `M8:fhir:audit-event:{pid}:{ts}` | POINTER_BACKED |
| 10. Enforce state alignment | 10 | M8 | `M8:obs:suppression-state:{pid}:{ts}`, `M6:obs:stability-band:{pid}:{ts}`, `M11:obs:patient-state:{pid}:{ts}`, `M41:audit:suppression-trail:{pid}:{ts}` | `M8:constraint:state-alignment:{pid}:{ts}` | POINTER_BACKED (M8, M41); MISSING (M6, M11 unspecified) |

---

## F. Output Artifact Pointer Table

| V5.2 Output | Artifact Pointer Format | Output Form Class | Uncertainty Carrier Required? | Constraint Carrier Required? |
|---|---|---|---|---|
| Unified suppression state (pauseFlag + pauseReason) to M6 | `M8:obs:suppression-state:{pid}:{ts}` | SCALAR (composite) | SUPPRESSION_CONTEXT when active | Yes — SUPPRESSION; INVARIANT_ENFORCEMENT |
| MD Toggle suppression candidate (resolves Tier 1 G-08) | `M8:obs:suppression-candidate:md-toggle:{pid}:{ts}` | SCALAR | No | Yes — INVARIANT_ENFORCEMENT (toggle scope) |
| Audit events to M41 / Appendix C.7/C.11 | `M8:fhir:audit-event:{pid}:{ts}` | — | — | — |

---

## G. Cross-Module Pointer Validation

### G.1 — Does M8's suppression output align with M9's Tier 1 addendum?

| M8 Output Pointer | M9 Tier 1 Declaration | Alignment? |
|---|---|---|
| `M8:obs:suppression-state:{pid}:{ts}` | M9 B.2 consumes suppression state from M8 | **Aligned** |
| `M8:obs:suppression-candidate:md-toggle:{pid}:{ts}` | M9 B.2 declared M8A as MISSING (Gap G-08) | **RESOLVED** — M8 addendum Step 5 produces this pointer. **Tier 1 Gap G-08 is closed.** |

### G.2 — Does M8's Zone 5 override reference M3's stability band?

| M8 Constraint | M3 Pointer | Alignment? |
|---|---|---|
| `M8:constraint:zone5-override:{pid}:{ts}` references `M3:obs:stability-band:{pid}:{ts}` (Band 5) | M3 Tier 1 addendum emits post-suppression stability band at this pointer | **Aligned** |

### G.3 — Does M8's audit emission align with M41?

| M8 Output | M41 Expected Input | Alignment? |
|---|---|---|
| `M8:fhir:audit-event:{pid}:{ts}` | M41 ingests audit events from all modules | **Aligned** |

---

## H. Gap Register

| Gap ID | V6 Requirement | Current Status | Resolution Tier | Blocking? |
|---|---|---|---|---|
| G-T2-13 | M6 stability band pointer for state alignment (Step 10) | MISSING — M6 unspecified | Tier 3 (M6 addendum) | No — state alignment degrades gracefully |
| G-T2-14 | M11 patient state pointer for state alignment (Step 10) | MISSING — M11 unspecified | Tier 3 (M11 addendum) | No — same as G-T2-13 |

**Tier 1 Gap G-08 is RESOLVED by this addendum.**
**No gap requires core logic change.**

---

## I. FHIR Anchor Mapping

| M8 Output | FHIR Resource | FHIR Profile Reference |
|---|---|---|
| Suppression activation/deactivation events | `AuditEvent` | Appendix C.7/C.11 |
| MD Toggle actions (activate, re-enable, extend) | `AuditEvent` (type: ClinicianToggle) | Appendix C.7/C.11 |
| Zone 5 safety override events | `AuditEvent` (type: SafetyOverride) | Appendix C.11 |
| Unified suppression state | `Observation` | Appendix C.7 |
| Provenance linking toggle to clinician identity | `Provenance` | Appendix C.7 |

---

## J. Addendum Acceptance Tests

| Test ID | Test | Expected Result |
|---|---|---|
| M8-AT-01 | Activate suppression via SymbolicFlare; verify SUPPRESSION carrier | `constraint_disclosure.status = CARRIERS_PRESENT`; source points to M5 |
| M8-AT-02 | Activate via MD_Toggle; verify pointer resolves Tier 1 G-08 | `M8:obs:suppression-candidate:md-toggle:{pid}:{ts}` produced |
| M8-AT-03 | Multiple simultaneous candidates; verify single-reason invariant | INVARIANT_ENFORCEMENT carrier; selected reason matches F.9 priority |
| M8-AT-04 | MD_Toggle then Zone 5; verify safety override | GOVERNANCE_GATE carrier; MD_Toggle overridden |
| M8-AT-05 | Verify non-destructive semantics | INVARIANT_ENFORCEMENT carrier confirms data preservation |
| M8-AT-06 | Verify state alignment across M6, M11, M41 | INVARIANT_ENFORCEMENT carrier; discrepancies flagged if found |
| M8-AT-07 | MD_Toggle session scope: verify toggle expires at session close | Toggle lifecycle artifact shows expiry |
| M8-AT-08 | Verify SUPPRESSION_CONTEXT uncertainty carrier when active | `uncertainty_disclosure.status = CARRIERS_PRESENT` |
| M8-AT-09 | Suppression inactive; verify no carriers emitted | No carriers (correct) |
| M8-AT-10 | Replay identical inputs + versions; verify identical chain | Replay determinism confirmed per M63 §7 |
