# Addendum: M33 — Governed Export & Disclosure Packetization

**Template Version:** V5.2 → V6 Governance Addendum Template v1.0
**Validated Against:** M63 GBDC v1.0 (§5.1 uncertainty enum, §5.2 constraint enum)
**Status:** DRAFT

---

## A. Module Identity & Addendum Scope

```
Module:           V5.2 M33 — Governed Export & Disclosure Packetization
V5.2 Spec Ref:    V5.2 M33 canonical spec (V5.2-A2)
Addendum Version: 1.0
Addendum Status:  DRAFT
```

**Addendum scope statement:** Core processing logic is unchanged. This addendum adds V6 governance emission only. M33's packet envelope construction, packet type selection, denial handling, and replayability binding all remain unmodified. The addendum formalizes M33's denied packet semantics as GOVERNANCE_GATE constraint carriers, maps its packet assembly steps to M63 DerivationChain transformation records, and binds its replayability metadata to M63 §7 replay determinism requirements.

---

## B. M63 Compliance — Derivation Chain Emission

### B.1 Output Artifact Registration

| Output | Artifact Type | Pointer Format | Provenance Record Emitted? |
|---|---|---|---|
| Disclosure Packet (approved) | Governed packet | `M33:packet:disclosure:{pid}:{packet_type}:{packet_version}:{ts}` | Yes |
| Denied Packet | Governed denial envelope | `M33:packet:denied:{pid}:{denial_reason_code}:{ts}` | Yes |
| Packet generation AuditEvent | FHIR AuditEvent | `M33:audit:packet-generation:{pid}:{ts}` | Yes |
| Packet generation Provenance | FHIR Provenance | `M33:provenance:packet-generation:{pid}:{ts}` | Yes |
| Downstream handoff object | Internal object for M28 | `M33:handoff:ledger:{pid}:{packet_version}:{ts}` | Yes |

### B.2 Input Artifact Traceability

| Input | Source Module | Pointer Available? |
|---|---|---|
| Minimized payload bundle + transform lineage | M27 | Yes — `M27:bundle:minimized:{pid}:{profile_id}:{ts}` + `M27:lineage:transforms:{pid}:{profile_id}:{ts}` |
| PurposeOfUse | Upstream request context | Yes |
| ConsentVersion | M26 (via M27 or direct) | Yes — `M26:binding:consent-state:{pid}:{consent_version}` |
| ProfileID | Governance infrastructure | Yes |
| JurisdictionOverlayID(s) | Governance infrastructure | Yes |
| Packet Type request | Upstream request context | Yes |
| Narrative component | Narrative surface (M25/M14) | Yes — `narrative:export:{pid}:{ts}` |
| PacketVersion, LedgerSchemaVersion | Governance infrastructure | Yes |

### B.3 Transformation Step Registration

| Step Index | Processing Stage | Owning Module | Input Pointers | Output Pointer |
|---|---|---|---|---|
| 1 | Validate export declaration (Step 1) | M33 | Request context | `M33:internal:purpose-validated:{pid}:{ts}` (or denied) |
| 2 | Require upstream minimization validation (Step 2) | M33 | M27 bundle + lineage pointers | `M33:internal:minimization-validated:{pid}:{ts}` (or denied) |
| 3 | Select exactly one Packet Type (Step 3) | M33 | Audience/purpose derivation rule | `M33:internal:packet-type-selected:{pid}:{packet_type}:{ts}` |
| 4 | Assemble packet envelope (Step 4) | M33 | All validated inputs + narrative | `M33:packet:disclosure:{pid}:{packet_type}:{packet_version}:{ts}` |
| 5 | Denial handling (Step 5) | M33 | Consent/overlay conflict signal | `M33:packet:denied:{pid}:{denial_reason_code}:{ts}` |
| 6 | Emit audit artifacts (Step 6) | M33 | All prior outputs | AuditEvent + Provenance + handoff |

---

## C. M63 Compliance — Uncertainty Carrier Emission

All M33 outputs are deterministic. No uncertainty carriers required. NOT_PROVIDED is correct.

---

## D. M63 Compliance — Constraint Carrier Emission

### D.1 Constraint Inventory

| Constraint | Trigger Condition | Constraint Type (§5.2) | Currently Emitted? | Action Required |
|---|---|---|---|---|
| Undefined purpose denial | PurposeOfUse missing (Step 1) | **GOVERNANCE_GATE** | Yes — Denied Packet | Emit `M33:constraint:undefined-purpose:{pid}:{ts}` |
| Missing/invalid minimization lineage denial | Upstream not properly bound (Step 2) | **GOVERNANCE_GATE** | Yes — Denied Packet | Emit `M33:constraint:invalid-lineage:{pid}:{ts}` |
| Consent/overlay conflict denial | Policy blocks export (Step 5) | **GOVERNANCE_GATE** | Yes — Denied Packet | Emit `M33:constraint:consent-overlay-conflict:{pid}:{ts}` |
| One packet type per export | Packet type selection rule (Step 3) | **INVARIANT_ENFORCEMENT** | Partial | Emit `M33:constraint:single-packet-type:{pid}:{packet_type}:{ts}` |
| Replayability invariant | Identical inputs -> identical packet | **INVARIANT_ENFORCEMENT** | Partial | Emit `M33:constraint:replay-invariant:{pid}:{packet_version}:{ledger_schema_version}:{ts}` |

### D.2 Materiality Declaration

GOVERNANCE_GATE denial carriers determine whether M28 receives approved or denied packet events. INVARIANT_ENFORCEMENT carriers ensure structural integrity of the disclosure pipeline.

---

## E. M67 (ARGL) Integration — Opt-In Declaration

**Opt-in status:** NOT_APPLICABLE — packetizer, not a reasoning module.

---

## F. FHIR Audit Artifact Emission

### F.1 AuditEvent Emission

| Event | Trigger | Required Fields |
|---|---|---|
| Packet assembly (approved) | Disclosure Packet created (Step 4) | patient_id, purpose_of_use, consent_version, profile_id, overlay_ids[], packet_type, packet_version, ledger_schema_version, requester_role, timestamp |
| Packet denial | Denied Packet created (Steps 1, 2, 5) | patient_id, denial_reason_code, purpose_of_use, consent_version, overlay_ids[], timestamp |
| Upstream validation check | Minimization lineage validated (Step 2) | patient_id, M27_bundle_ref, M27_lineage_ref, validation_result, timestamp |

### F.2 Provenance Emission

| Provenance Record | Connects | FHIR Resource Type |
|---|---|---|
| Packet assembly provenance | M27 minimized bundle + narrative -> Disclosure Packet | Provenance |
| Denial provenance | Denial trigger -> Denied Packet | Provenance |
| Replayability provenance | PacketVersion + LedgerSchemaVersion -> packet output | Provenance |

---

## G. V6 Consumer Contract

| V6 Consumer | What It Reads | Contract Reference | Addendum Satisfies? |
|---|---|---|---|
| M63 (GBDC) | DerivationChain steps; GOVERNANCE_GATE, INVARIANT_ENFORCEMENT carriers; §7 replay metadata | M63 §2, §3.4, §5.2, §7 | Yes |
| M28 (Ledger) | Packet events via `M33:handoff:ledger:{pid}:{packet_version}:{ts}` | M28 Inputs | Yes |

---

## H. Gap Register

| Gap ID | V6 Requirement | Why Addendum Cannot Satisfy | Resolution Path |
|---|---|---|---|
| G-T3-M33-01 | M63 §7: module_version_snapshot + governance_state_snapshot_ref | M33 binds PacketVersion + LedgerSchemaVersion but not full version snapshot | Add version snapshot capture — no core logic change |
| G-T3-M33-02 | M63 §3.2: Narrative source module ID | V5.2 references "narrative surface" generically | Clarify during implementation (likely M25 or M14) |

---

## I. Implementation Checklist

| Item | Status | Notes |
|---|---|---|
| Output artifact pointers defined | ☐ | B.1 — five types |
| Input traceability mapped | ☐ | B.2 — all pointer-backed |
| Transformation steps registered | ☐ | B.3 — six steps |
| Uncertainty carriers | ☐ | All NOT_PROVIDED |
| Constraint carriers | ☐ | D.1 — five carriers, two §5.2 types |
| ARGL opt-in | ☐ | NOT_APPLICABLE |
| FHIR audit artifacts | ☐ | F — three AuditEvent, three Provenance |
| V6 consumer contracts | ☐ | G — M63 + M28 |
| Gap register | ☐ | Two gaps, zero core logic changes |
| V5.2 spec review | ☐ | Confirmed: emissions describe existing behavior |

---

## J. Acceptance Tests

| ID | Test | Expected Result |
|---|---|---|
| AT-M33-01 | Identical Disclosure Packets with/without addendum | Core logic unchanged |
| AT-M33-02 | M63 DerivationChain through M33 | All steps POINTER_BACKED |
| AT-M33-03 | GOVERNANCE_GATE on undefined purpose denial | Carrier present |
| AT-M33-04 | GOVERNANCE_GATE on invalid lineage denial | Carrier present |
| AT-M33-05 | GOVERNANCE_GATE on consent/overlay conflict | Carrier present |
| AT-M33-06 | INVARIANT_ENFORCEMENT for single-packet-type | Carrier present |
| AT-M33-07 | Denied Packets include full lineage + narrative | No silent failures |
| AT-M33-08 | M28 can resolve handoff pointer | Downstream confirmed |
| AT-M33-09 | Replayability: identical inputs -> identical packet + carriers | Deterministic |
| AT-M33-10 | Existing consumers unaffected | No breaking changes |
