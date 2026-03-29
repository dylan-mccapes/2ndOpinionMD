# Addendum: M26 — Consent & Ethical Safeguards

**Template Version:** V5.2 → V6 Governance Addendum Template v1.0
**Validated Against:** M63 GBDC v1.0 (§5.1 uncertainty enum, §5.2 constraint enum)
**Status:** DRAFT

---

## A. Module Identity & Addendum Scope

```
Module:           V5.2 M26 — Consent & Ethical Safeguards
V5.2 Spec Ref:    V5.2 M26 canonical spec (Cannon_V5_2)
Addendum Version: 1.0
Addendum Status:  DRAFT
```

**Addendum scope statement:** Core processing logic is unchanged. This addendum adds V6 governance emission only. M26's consent state machine, dynamic consent refresh, ethical override handling, dual-audience documentation, and ledger/audit artifact production all remain unmodified. The addendum formalizes M26's existing consent gate decisions, jurisdiction overlay enforcement, role-based consent filtering, and emergency override governance into M63-compatible carrier format so that downstream DerivationChains can reference M26's constraint artifacts by pointer.

---

## B. M63 Compliance — Derivation Chain Emission

### B.1 Output Artifact Registration

| Output | Artifact Type | Pointer Format | Provenance Record Emitted? |
|---|---|---|---|
| Consent gate decision (allow/deny) | Internal decision record | `M26:decision:consent-gate:{pid}:{ts}` | Yes — AuditEvent + Provenance per Step 7 |
| Consent state snapshot | FHIR Consent | `M26:consent:state:{pid}:{consent_version}` | Yes — Consent Ledger entry per Step 7 |
| Emergency override record | Internal override record | `M26:override:emergency:{pid}:{ts}` | Yes — Ethical Override Ledger per Step 4 |
| Patient-facing Communication | FHIR Communication | `M26:comm:patient:{pid}:{consent_version}:{ts}` | Yes — bound to consent provenance IDs per Step 6 |
| Clinician-facing DocumentReference | FHIR DocumentReference | `M26:docref:clinician:{pid}:{consent_version}:{ts}` | Yes — bound to consent provenance IDs per Step 6 |
| Consent Ledger entry | Appendix L.3.11 record | `M26:ledger:consent:{pid}:{consent_version}:{change_type}` | Yes — per Step 7 |
| Downstream consent binding | Internal binding object | `M26:binding:consent-state:{pid}:{consent_version}` | Yes — emitted at Step 8 for M27-M33 consumption |

### B.2 Input Artifact Traceability

| Input | Source Module | Pointer Available? | If No, Gap Classification |
|---|---|---|---|
| `patient_id` | Upstream request context | Yes — request-scoped | — |
| `requesting_module_id` | Upstream request context | Yes — request-scoped | — |
| `requested_operation` | Upstream request context | Yes — request-scoped | — |
| `purpose_of_use` | Upstream request context | Yes — request-scoped | — |
| `requester_role` / `requester_actor_id` | Upstream request context | Yes — request-scoped | — |
| `jurisdiction_overlay_ids[]` | Governance infrastructure | Yes — overlay registry pointer | — |
| `override_requested` / `override_reason` | M8B (Emergency Override) | Yes — `M8B:override:request:{pid}:{ts}` | — |
| Prior `ConsentState` | M26 own state store | Yes — `M26:consent:state:{pid}:{prior_consent_version}` | — |

### B.3 Transformation Step Registration

| Step Index | Processing Stage (from V5.2 spec) | Owning Module | Input Pointers | Output Pointer |
|---|---|---|---|---|
| 1 | Load current consent context (Step 1) | M26 | `M26:consent:state:{pid}:{prior_consent_version}` | `M26:internal:consent-context:{pid}:{ts}` |
| 2 | Evaluate consent state gate (Step 2) | M26 | `M26:internal:consent-context:{pid}:{ts}` | `M26:decision:consent-gate:{pid}:{ts}` |
| 3 | Apply dynamic consent refresh/decay (Step 3) | M26 | `M26:decision:consent-gate:{pid}:{ts}`, request context | `M26:decision:consent-gate:{pid}:{ts}` (updated if refresh triggers deny) |
| 4 | Ethical override handling (Step 4) | M26 | `M8B:override:request:{pid}:{ts}` | `M26:override:emergency:{pid}:{ts}` |
| 5 | Enforce no-bypass rule (Step 5) | M26 | request context | `M26:decision:consent-gate:{pid}:{ts}` (deny if bypass attempted) |
| 6 | Generate dual-audience documentation (Step 6) | M26 | `M26:decision:consent-gate:{pid}:{ts}`, `M26:consent:state:{pid}:{consent_version}` | `M26:comm:patient:{pid}:{consent_version}:{ts}`, `M26:docref:clinician:{pid}:{consent_version}:{ts}` |
| 7 | Write ledger + audit/provenance (Step 7) | M26 | All prior step outputs | `M26:ledger:consent:{pid}:{consent_version}:{change_type}`, AuditEvent + Provenance |
| 8 | Emit downstream bindings (Step 8) | M26 | `M26:consent:state:{pid}:{consent_version}` | `M26:binding:consent-state:{pid}:{consent_version}` |

---

## C. M63 Compliance — Uncertainty Carrier Emission

### C.1 Uncertainty Inventory

| Output | Uncertainty Metadata Currently Emitted? | Carrier Type (per M63 §5.1 enum) | Action Required |
|---|---|---|---|
| Consent gate decision (allow/deny) | No — deterministic binary decision | N/A — not probabilistic/prognostic | None |
| Consent state snapshot | No — deterministic state machine | N/A | None |
| Emergency override record | No — deterministic binary | N/A | None |

### C.2 Degradation State

M26 does not emit degradation states. Consent gate decisions are deterministic. M63 will mark uncertainty as NOT_PROVIDED for all M26 outputs, which is correct — consent decisions should never carry uncertainty.

---

## D. M63 Compliance — Constraint Carrier Emission

### D.1 Constraint Inventory

| Constraint | Trigger Condition (V5.2 spec ref) | Constraint Type (per M63 §5.2 enum) | Currently Emitted as Artifact? | Action Required |
|---|---|---|---|---|
| Consent gate denial | `consent_state` in {Revoked, Expired} or delegation mismatch (Step 2) | **CONSENT_OVERLAY** | Partial — decision logged in Consent Ledger but not as discrete constraint carrier | Emit `M26:constraint:consent-overlay:{pid}:{ts}` |
| Jurisdiction overlay enforcement | `jurisdiction_overlay_ids[]` constrain consent scope (Step 2-3) | **JURISDICTION_OVERLAY** | Partial — overlay IDs recorded in ledger but not as discrete carrier | Emit `M26:constraint:jurisdiction-overlay:{pid}:{overlay_id}:{ts}` |
| Role-specific consent filtering | `requester_role` gates consent flow (Step 2 delegation check) | **ROLE_FILTER** | Partial — role recorded in AuditEvent but not as discrete carrier | Emit `M26:constraint:role-filter:{pid}:{requester_role}:{ts}` |
| Emergency override bypass | M8B override invoked (Step 4) | **GOVERNANCE_GATE** | Yes — Ethical Override Ledger entry with `overrideReason` | Emit `M26:constraint:emergency-override:{pid}:{ts}` referencing override record |
| No-bypass enforcement | Downstream module attempts consent bypass without 8B (Step 5) | **GOVERNANCE_GATE** | Yes — denial decision logged | Emit `M26:constraint:no-bypass-enforcement:{pid}:{ts}` |
| Consent decay / refresh trigger | Time or event triggers consent renewal (Step 3) | **CONSENT_OVERLAY** | Partial — consent version transition logged but not as discrete carrier | Emit `M26:constraint:consent-decay:{pid}:{ts}` when refresh blocks operation |

### D.2 Materiality Declaration

Every constraint in D.1 materially shapes downstream output. CONSENT_OVERLAY carriers are consumed by M27, M33, and M28. JURISDICTION_OVERLAY carriers determine which minimization transforms M27 applies. ROLE_FILTER carriers determine audience tier access. GOVERNANCE_GATE carriers (override and no-bypass) override normal consent flow or block unauthorized bypass.

---

## E. M67 (ARGL) Integration — Opt-In Declaration

**Opt-in status:** NOT_APPLICABLE

M26 is a deterministic consent gate, not a clinical reasoning module.

---

## F. FHIR Audit Artifact Emission

### F.1 AuditEvent Emission

| Event | Trigger | Required Fields |
|---|---|---|
| Consent gate evaluation | Every consent check (Step 2) | patient_id, requester_role, requester_actor_id, purpose_of_use, consent_state, consent_version, decision, decision_reason, jurisdiction_overlay_ids[], timestamp |
| Consent state transition | Any state change (Steps 2-4) | patient_id, prior_consent_state, new_consent_state, consent_version, change_type, actor, timestamp |
| Emergency override activation | M8B bypass invoked (Step 4) | patient_id, override_reason, override_source_module_id, scope, timestamp, ethical_override_ledger_ref |
| Consent decay/refresh trigger | Renewal workflow initiated (Step 3) | patient_id, trigger_type, prior_consent_version, renewal_status, timestamp |
| Dual-audience document generation | Communication + DocumentReference created (Step 6) | patient_id, consent_version, document_type, provenance_ref, timestamp |

### F.2 Provenance Emission

| Provenance Record | Connects | FHIR Resource Type |
|---|---|---|
| Consent gate provenance | Request context -> consent decision -> downstream binding | Provenance |
| Override provenance | M8B override request -> M26 override record -> ethical override ledger | Provenance |
| Dual-audience provenance | Consent event -> patient Communication + clinician DocumentReference | Provenance |
| State transition provenance | Prior consent state -> new consent state -> Consent Ledger entry | Provenance |

---

## G. V6 Consumer Contract

| V6 Consumer | What It Reads | Contract Reference | Addendum Satisfies? |
|---|---|---|---|
| M63 (GBDC) | DerivationChain steps; CONSENT_OVERLAY, JURISDICTION_OVERLAY, ROLE_FILTER, GOVERNANCE_GATE constraint carriers | M63 §2, §3.4, §5.2 | Yes |
| M27 (Minimization) | `consent_version`, `consent_state` via `M26:binding:consent-state:{pid}:{consent_version}` | M27 Inputs | Yes |
| M33 (Packetization) | `ConsentVersion` via `M26:binding:consent-state:{pid}:{consent_version}` | M33 Inputs | Yes |
| M28 (Ledger) | `ConsentVersion` snapshot via `M26:binding:consent-state:{pid}:{consent_version}` | M28 Inputs | Yes |

---

## H. Gap Register

| Gap ID | V6 Requirement | Why Addendum Cannot Satisfy | Resolution Path |
|---|---|---|---|
| G-T3-M26-01 | M63 §5.2: Constraint carriers must be discrete, pointer-backed artifacts | M26 currently logs constraint information inside Consent Ledger entries and AuditEvents but does not emit standalone constraint carrier objects | Addendum specifies the new emission pointers (Section D.1); implementation extracts constraint carriers from existing ledger writes — no core logic change |

---

## I. Implementation Checklist

| Item | Status | Notes |
|---|---|---|
| Output artifact pointers defined | ☐ | B.1 — seven output pointers |
| Input traceability mapped | ☐ | B.2 — all inputs pointer-backed |
| Transformation steps registered | ☐ | B.3 — eight steps |
| Uncertainty carriers defined or NOT_PROVIDED declared | ☐ | C.1 — all NOT_PROVIDED |
| Constraint carriers defined or NOT_PROVIDED declared | ☐ | D.1 — six constraint carriers across four §5.2 enum types |
| ARGL opt-in status declared | ☐ | E — NOT_APPLICABLE |
| FHIR audit artifacts specified | ☐ | F — five AuditEvent types, four Provenance records |
| V6 consumer contracts validated | ☐ | G — M63 + M27/M33/M28 |
| Gap register complete | ☐ | H — one gap, zero core logic changes |
| Addendum reviewed against V5.2 spec | ☐ | Confirmed: all emissions describe existing behavior |

---

## J. Acceptance Tests

| ID | Test | Expected Result |
|---|---|---|
| AT-M26-01 | Module produces identical consent decisions with and without addendum emission layer active | Core logic unchanged; emission is additive only |
| AT-M26-02 | M63 can construct a DerivationChain through M26 | All chain steps are POINTER_BACKED |
| AT-M26-03 | CONSENT_OVERLAY constraint carrier emitted on denial | Carrier with valid §5.2 enum type |
| AT-M26-04 | JURISDICTION_OVERLAY constraint carrier emitted on overlay constraint | Valid §5.2 enum type |
| AT-M26-05 | ROLE_FILTER constraint carrier emitted on role gate | Valid §5.2 enum type |
| AT-M26-06 | GOVERNANCE_GATE constraint carrier emitted on emergency override | Valid §5.2 enum type |
| AT-M26-07 | No uncertainty carriers emitted | NOT_PROVIDED for all outputs |
| AT-M26-08 | Downstream binding consumable by M27 | M27 can resolve pointer |
| AT-M26-09 | Existing downstream consumers unaffected | No breaking changes |
