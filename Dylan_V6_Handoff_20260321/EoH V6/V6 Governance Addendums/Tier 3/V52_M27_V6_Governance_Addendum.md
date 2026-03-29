# Addendum: M27 — Data Minimization & De-Identification Engine

**Template Version:** V5.2 → V6 Governance Addendum Template v1.0
**Validated Against:** M63 GBDC v1.0 (§5.1 uncertainty enum, §5.2 constraint enum)
**Status:** DRAFT

---

## A. Module Identity & Addendum Scope

```
Module:           V5.2 M27 — Data Minimization & De-Identification Engine
V5.2 Spec Ref:    V5.2 M27 canonical spec (V5.2-A1)
Addendum Version: 1.0
Addendum Status:  DRAFT
```

**Addendum scope statement:** Core processing logic is unchanged. This addendum adds V6 governance emission only. M27's purpose-bound minimization, de-identification/pseudonymization transforms, denial semantics, and replayability binding all remain unmodified. The addendum formalizes M27's existing transform operations as M63-compatible constraint carriers and maps its denial semantics to GOVERNANCE_GATE carriers.

---

## B. M63 Compliance — Derivation Chain Emission

### B.1 Output Artifact Registration

| Output | Artifact Type | Pointer Format | Provenance Record Emitted? |
|---|---|---|---|
| Minimized response bundle | FHIR Bundle with meta.security tags | `M27:bundle:minimized:{pid}:{profile_id}:{ts}` | Yes |
| De-identified packet | Schema-conformant packet | `M27:packet:de-identified:{pid}:{profile_id}:{packet_version}` | Yes |
| Pseudonymized packet | Schema-conformant packet | `M27:packet:pseudonymized:{pid}:{profile_id}:{packet_version}` | Yes |
| Denied bundle | Denied output with denialReason | `M27:denied:bundle:{pid}:{ts}:{denial_reason_code}` | Yes |
| Denied transform record | Denied output with denialReason | `M27:denied:transform:{pid}:{ts}:{denial_reason_code}` | Yes |
| Transform lineage record | Provenance with transformList + parameters | `M27:lineage:transforms:{pid}:{profile_id}:{ts}` | Yes |
| Disclosure log pointer | DocumentReference-style artifact | `M27:docref:disclosure-log:{pid}:{ts}` | Yes |

### B.2 Input Artifact Traceability

| Input | Source Module | Pointer Available? | If No, Gap Classification |
|---|---|---|---|
| ConsentVersion / consent state | M26 | Yes — `M26:binding:consent-state:{pid}:{consent_version}` | — |
| PurposeOfUse | Upstream request context | Yes | — |
| RequesterRole / audience tier | Upstream request context | Yes | — |
| JurisdictionOverlayID(s) + versions | Governance infrastructure | Yes | — |
| ProfileID | Governance infrastructure | Yes | — |
| Source payload (raw bundle) | Upstream clinical modules | Yes | — |
| Emergency override signal | M26 passthrough | Yes — `M26:constraint:emergency-override:{pid}:{ts}` | — |

### B.3 Transformation Step Registration

| Step Index | Processing Stage | Owning Module | Input Pointers | Output Pointer |
|---|---|---|---|---|
| 1 | Validate declared purpose (Step 1) | M27 | Request context | `M27:internal:purpose-validated:{pid}:{ts}` (or denied) |
| 2 | Reconcile purpose with consent + overlays (Step 2) | M27 | `M26:binding:consent-state:{pid}:{consent_version}`, overlays, purpose | `M27:internal:reconciliation-result:{pid}:{ts}` (or denied) |
| 3 | Apply minimization transform suite (Step 3) | M27 | Source payload, ProfileID, overlays | `M27:bundle:minimized:{pid}:{profile_id}:{ts}` |
| 4 | Secondary-use transform: de-ID/pseudonymization (Step 4) | M27 | `M27:bundle:minimized:{pid}:{profile_id}:{ts}` | `M27:packet:de-identified` or `M27:packet:pseudonymized` |
| 5 | Replayability binding (Step 5) | M27 | All prior outputs, PacketVersion, LedgerSchemaVersion | Replay metadata attached |
| 6 | Emit lineage + downstream handoff (Step 6) | M27 | All prior outputs | `M27:lineage:transforms`, `M27:docref:disclosure-log`, AuditEvent + Provenance |

---

## C. M63 Compliance — Uncertainty Carrier Emission

All M27 outputs are deterministic transforms. No uncertainty carriers required. NOT_PROVIDED is correct.

---

## D. M63 Compliance — Constraint Carrier Emission

### D.1 Constraint Inventory

| Constraint | Trigger Condition | Constraint Type (§5.2) | Currently Emitted? | Action Required |
|---|---|---|---|---|
| Purpose-consent-overlay reconciliation denial | Conflict (Step 2) | **GOVERNANCE_GATE** | Yes — Denied bundle | Emit `M27:constraint:reconciliation-denial:{pid}:{ts}` |
| Suppress transform | Field suppressed (Step 3) | **CONSENT_OVERLAY** | Partial — in transformList | Emit `M27:constraint:suppress:{pid}:{field_path}:{ts}` |
| Mask transform | Field masked (Step 3) | **CONSENT_OVERLAY** | Partial | Emit `M27:constraint:mask:{pid}:{field_path}:{ts}` |
| Generalize transform | Field generalized (Step 3) | **JURISDICTION_OVERLAY** | Partial | Emit `M27:constraint:generalize:{pid}:{field_path}:{ts}` |
| Date-shift transform | Dates shifted (Step 3) | **JURISDICTION_OVERLAY** | Partial | Emit `M27:constraint:date-shift:{pid}:{ts}` |
| Geo-coarsen transform | Geo data coarsened (Step 3) | **JURISDICTION_OVERLAY** | Partial | Emit `M27:constraint:geo-coarsen:{pid}:{ts}` |
| Undefined purpose denial | PurposeOfUse not declared (Step 1) | **GOVERNANCE_GATE** | Yes — Denied bundle | Emit `M27:constraint:undefined-purpose:{pid}:{ts}` |
| Emergency override passthrough | Override signal from M26 | **GOVERNANCE_GATE** | Partial | Emit `M27:constraint:override-passthrough:{pid}:{ts}` |

### D.2 Materiality Declaration

Every transform materially shapes downstream data. Suppressed fields are invisible to M33 and M28. The "no silent drops" invariant reinforces this — suppressed fields must appear in lineage. Constraint carrier emission formalizes what M27 already tracks.

---

## E. M67 (ARGL) Integration — Opt-In Declaration

**Opt-in status:** NOT_APPLICABLE — deterministic transform engine.

---

## F. FHIR Audit Artifact Emission

### F.1 AuditEvent Emission

| Event | Trigger | Required Fields |
|---|---|---|
| Minimization transform execution | Every transform suite application (Step 3) | patient_id, profile_id, jurisdiction_overlay_ids[], transform_list, meta.security tags, requester_role, audience_tier, consent_version, timestamp |
| De-ID/pseudonymization execution | Secondary-use transform (Step 4) | patient_id, profile_id, consent_version, packet_version, transform_type, timestamp |
| Purpose validation denial | Undefined purpose (Step 1) | patient_id, denial_reason=UndefinedPurpose, timestamp |
| Reconciliation denial | Consent/overlay conflict (Step 2) | patient_id, denial_reason, consent_version, overlay_ids[], purpose_of_use, timestamp |
| Emergency override passthrough | Override signal consumed | patient_id, override_reason, override_scope, M26_override_ref, timestamp |

### F.2 Provenance Emission

| Provenance Record | Connects | FHIR Resource Type |
|---|---|---|
| Minimization provenance | Source payload -> minimized bundle (with transformList) | Provenance |
| De-ID provenance | Minimized bundle -> de-identified packet | Provenance |
| Pseudonymization provenance | Minimized bundle -> pseudonymized packet | Provenance |
| Denial provenance | Request context -> denied bundle/transform | Provenance |
| Replayability provenance | PacketVersion + LedgerSchemaVersion binding | Provenance |

---

## G. V6 Consumer Contract

| V6 Consumer | What It Reads | Contract Reference | Addendum Satisfies? |
|---|---|---|---|
| M63 (GBDC) | DerivationChain steps; CONSENT_OVERLAY, JURISDICTION_OVERLAY, GOVERNANCE_GATE carriers | M63 §2, §3.4, §5.2 | Yes |
| M33 (Packetization) | Minimized payload + transform lineage | M33 Inputs | Yes |
| M28 (Ledger) | Minimization lineage + ProfileID references | M28 Inputs | Yes |

---

## H. Gap Register

| Gap ID | V6 Requirement | Why Addendum Cannot Satisfy | Resolution Path |
|---|---|---|---|
| G-T3-M27-01 | Individual transform operations must each emit discrete constraint carrier | M27 currently logs transforms as bundled list in Provenance | Unbundle per-field carriers — no core logic change |

---

## I. Implementation Checklist

| Item | Status | Notes |
|---|---|---|
| Output artifact pointers defined | ☐ | B.1 — seven types |
| Input traceability mapped | ☐ | B.2 — all pointer-backed |
| Transformation steps registered | ☐ | B.3 — six steps |
| Uncertainty carriers | ☐ | All NOT_PROVIDED |
| Constraint carriers | ☐ | D.1 — eight carriers, three §5.2 types |
| ARGL opt-in | ☐ | NOT_APPLICABLE |
| FHIR audit artifacts | ☐ | F — five AuditEvent, five Provenance |
| V6 consumer contracts | ☐ | G — M63 + M33/M28 |
| Gap register | ☐ | One gap, zero core logic changes |
| V5.2 spec review | ☐ | Confirmed: emissions describe existing transforms |

---

## J. Acceptance Tests

| ID | Test | Expected Result |
|---|---|---|
| AT-M27-01 | Identical minimized bundles with/without addendum | Core logic unchanged |
| AT-M27-02 | M63 DerivationChain through M27 | All steps POINTER_BACKED |
| AT-M27-03 | CONSENT_OVERLAY carrier per suppress/mask | Per-field carriers |
| AT-M27-04 | JURISDICTION_OVERLAY carrier per generalize/date-shift/geo-coarsen | Valid §5.2 types |
| AT-M27-05 | GOVERNANCE_GATE on reconciliation denial | Carrier present |
| AT-M27-06 | GOVERNANCE_GATE on undefined purpose | Carrier present |
| AT-M27-07 | Denial outputs include full lineage | No silent drops |
| AT-M27-08 | Replayability: identical inputs -> identical carriers | Deterministic |
| AT-M27-09 | M33 can resolve minimized bundle pointer | Downstream confirmed |
| AT-M27-10 | Existing consumers unaffected | No breaking changes |
