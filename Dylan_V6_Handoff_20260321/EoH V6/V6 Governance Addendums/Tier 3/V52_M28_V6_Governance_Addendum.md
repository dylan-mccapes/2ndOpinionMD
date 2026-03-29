# Addendum: M28 — Disclosure & Access Accounting Ledger

**Template Version:** V5.2 → V6 Governance Addendum Template v1.0
**Validated Against:** M63 GBDC v1.0 (§5.1 uncertainty enum, §5.2 constraint enum)
**Status:** DRAFT

---

## A. Module Identity & Addendum Scope

```
Module:           V5.2 M28 — Disclosure & Access Accounting Ledger
V5.2 Spec Ref:    V5.2 M28 canonical spec (V5.2-A3)
Addendum Version: 1.0
Addendum Status:  DRAFT
```

**Addendum scope statement:** Core processing logic is unchanged. This addendum adds V6 governance emission only. M28's universal logging, canonical ledger entry construction, normalization pipeline, denied disclosure semantics, dual-audience views, retention/expiry handling, and oversight cross-checks all remain unmodified. The addendum formalizes M28's role as the terminal recording surface for upstream constraint carriers and maps its retention/expiry and replayability enforcement to M63-compatible structures.

---

## B. M63 Compliance — Derivation Chain Emission

### B.1 Output Artifact Registration

| Output | Artifact Type | Pointer Format | Provenance Record Emitted? |
|---|---|---|---|
| Disclosure Ledger Entry (approved) | AuditEvent + Provenance + DocumentReference triplet | `M28:ledger:entry:{pid}:{packet_version}:{ts}` | Yes |
| Disclosure Ledger Entry (denied) | AuditEvent + Provenance + DocumentReference triplet (denied) | `M28:ledger:denied:{pid}:{denial_reason_code}:{ts}` | Yes |
| Patient-facing summary | Narrative bound to ledger entry | `M28:summary:patient:{pid}:{ledger_entry_id}` | Yes |
| Regulator-facing log | Full detail bound to ledger entry | `M28:log:regulator:{pid}:{ledger_entry_id}` | Yes |
| Expired entry stub | Metadata-only stub with DataAbsentReason=expired | `M28:stub:expired:{pid}:{original_ledger_entry_id}` | Yes |
| QA/oversight signal | Aggregated metrics + cross-check output | `M28:signal:qa:{pid}:{ts}` | Yes |

### B.2 Input Artifact Traceability

| Input | Source Module | Pointer Available? |
|---|---|---|
| Disclosure Packet events (approved) | M33 | Yes — `M33:handoff:ledger:{pid}:{packet_version}:{ts}` |
| Denied Packet events | M33 | Yes — `M33:packet:denied:{pid}:{denial_reason_code}:{ts}` |
| Minimization lineage + ProfileID | M27 | Yes — `M27:lineage:transforms:{pid}:{profile_id}:{ts}` |
| ConsentVersion snapshot | M26 (via M33) | Yes — `M26:binding:consent-state:{pid}:{consent_version}` |
| Jurisdiction overlay context | Governance infrastructure | Yes |
| Upstream constraint carriers (M26) | M26 | Yes — all M26 constraint pointers |
| Upstream constraint carriers (M27) | M27 | Yes — all M27 constraint pointers |
| Upstream constraint carriers (M33) | M33 | Yes — all M33 constraint pointers |

### B.3 Transformation Step Registration

| Step Index | Processing Stage | Owning Module | Input Pointers | Output Pointer |
|---|---|---|---|---|
| 1 | Universal logging (Step 1) | M28 | M33 handoff + upstream constraint carriers | `M28:internal:event-received:{pid}:{ts}` |
| 2 | Canonical entry construction (Step 2) | M28 | `M28:internal:event-received:{pid}:{ts}` | `M28:ledger:entry` or `M28:ledger:denied` |
| 3 | Ledger normalization pipeline (Step 3) | M28 | Ledger entry + version tags | Normalized entry |
| 4 | Denied disclosure semantics (Step 4) | M28 | M33 denied packet + upstream carriers | `M28:ledger:denied:{pid}:{denial_reason_code}:{ts}` |
| 5 | Dual-audience views (Step 5) | M28 | Ledger entry | `M28:summary:patient` + `M28:log:regulator` |
| 6 | Retention & expiry handling (Step 6) | M28 | Ledger entry + jurisdiction retention rules | `M28:stub:expired` (when expired) |
| 7 | Replayability and version governance (Step 7) | M28 | LedgerSchemaVersion + all version IDs | Replay metadata attached |
| 8 | Oversight & integrity cross-check (Step 8) | M28 | All entries + suppression trail | `M28:signal:qa:{pid}:{ts}` |

---

## C. M63 Compliance — Uncertainty Carrier Emission

All M28 outputs are deterministic records. No uncertainty carriers required. NOT_PROVIDED is correct.

---

## D. M63 Compliance — Constraint Carrier Emission

### D.1 Constraint Inventory

| Constraint | Trigger Condition | Constraint Type (§5.2) | Currently Emitted? | Action Required |
|---|---|---|---|---|
| Universal logging enforcement | Every export request (Step 1) | **INVARIANT_ENFORCEMENT** | Yes — structurally enforced | Emit `M28:constraint:universal-logging:{pid}:{ts}` |
| Retention/expiry policy enforcement | Jurisdictional rules convert entries to stubs (Step 6) | **JURISDICTION_OVERLAY** | Yes — DataAbsentReason=expired | Emit `M28:constraint:retention-expiry:{pid}:{original_ledger_entry_id}:{ts}` |
| Denied disclosure recording | Upstream denial propagated (Step 4) | **GOVERNANCE_GATE** | Yes — Denied Disclosure Record | Emit `M28:constraint:denied-disclosure:{pid}:{denial_reason_code}:{ts}` |
| Schema authority externalization | Ledger schema owned by appendices | **INVARIANT_ENFORCEMENT** | Partial | Emit `M28:constraint:schema-authority:{ledger_schema_version}:{ts}` |
| Disclosure-suppression integrity cross-check | Cross-check against suppression trail (Step 8) | **INVARIANT_ENFORCEMENT** | Partial — QA output but not discrete carrier | Emit `M28:constraint:integrity-crosscheck:{pid}:{ts}` |

### D.2 Materiality Declaration

M28's constraints enforce ledger integrity, not clinical data visibility. INVARIANT_ENFORCEMENT carriers ensure the accounting system is trustworthy. JURISDICTION_OVERLAY carriers for retention/expiry materially shape long-term data availability. GOVERNANCE_GATE carriers ensure upstream denials are faithfully recorded.

M28's primary M63 role is Trace Integrity: the ledger entry is the terminal node of the disclosure DerivationChain.

---

## E. M67 (ARGL) Integration — Opt-In Declaration

**Opt-in status:** NOT_APPLICABLE — accounting ledger, not a reasoning module.

---

## F. FHIR Audit Artifact Emission

### F.1 AuditEvent Emission

| Event | Trigger | Required Fields |
|---|---|---|
| Ledger entry creation (approved) | Approved packet received (Step 2) | patient_id, purpose_of_use, consent_version, profile_id, overlay_ids[], packet_type, packet_version, ledger_schema_version, requester_role, timestamp |
| Ledger entry creation (denied) | Denied packet received (Step 4) | patient_id, denial_reason_code, consent_version, overlay_ids[], upstream_constraint_carrier_refs[], timestamp |
| Retention/expiry event | Entry -> metadata stub (Step 6) | patient_id, original_ledger_entry_id, expiry_reason, jurisdiction_overlay_id, DataAbsentReason=expired, timestamp |
| Dual-audience view generation | Summary/log created (Step 5) | patient_id, ledger_entry_id, view_type, timestamp |
| Integrity cross-check | Disclosure-suppression check (Step 8) | patient_id, cross_check_result, discrepancy_details, timestamp |

### F.2 Provenance Emission

| Provenance Record | Connects | FHIR Resource Type |
|---|---|---|
| Ledger entry provenance | M33 packet -> M28 ledger entry (full upstream chain) | Provenance |
| Denial chain provenance | Upstream carriers (M26/M27/M33) -> M28 denied entry | Provenance |
| Retention provenance | Original entry -> expired stub (with policy reference) | Provenance |
| View provenance | Ledger entry -> patient summary / regulator log | Provenance |

---

## G. V6 Consumer Contract

| V6 Consumer | What It Reads | Contract Reference | Addendum Satisfies? |
|---|---|---|---|
| M63 (GBDC) | DerivationChain terminal node; INVARIANT_ENFORCEMENT, JURISDICTION_OVERLAY, GOVERNANCE_GATE carriers; ledger entry as terminal provenance anchor | M63 §2, §3.1, §3.4, §5.2, §7 | Yes |
| QA/Oversight (M19) | QA signals + cross-check output | M28 Step 8 | Yes |
| Compliance hubs | Ledger slices | M28 downstream | Yes |

---

## H. Gap Register

| Gap ID | V6 Requirement | Why Addendum Cannot Satisfy | Resolution Path |
|---|---|---|---|
| G-T3-M28-01 | M63 §7: module_version_snapshot + governance_state_snapshot_ref | M28 binds LedgerSchemaVersion but not full version snapshot | Add version snapshot capture — no core logic change |
| G-T3-M28-02 | M63 §3.1: Suppression trail pointer for integrity cross-check | M28 cross-checks against suppression trail; M8/M9 Tier 2 addendum already produces required pointer | Validate pointer resolution during integration testing |

---

## I. Implementation Checklist

| Item | Status | Notes |
|---|---|---|
| Output artifact pointers defined | ☐ | B.1 — six types |
| Input traceability mapped | ☐ | B.2 — all pointer-backed |
| Transformation steps registered | ☐ | B.3 — eight steps |
| Uncertainty carriers | ☐ | All NOT_PROVIDED |
| Constraint carriers | ☐ | D.1 — five carriers, three §5.2 types |
| ARGL opt-in | ☐ | NOT_APPLICABLE |
| FHIR audit artifacts | ☐ | F — five AuditEvent, four Provenance |
| V6 consumer contracts | ☐ | G — M63 + QA + compliance |
| Gap register | ☐ | Two gaps, zero core logic changes |
| V5.2 spec review | ☐ | Confirmed: emissions describe existing behavior |

---

## J. Acceptance Tests

| ID | Test | Expected Result |
|---|---|---|
| AT-M28-01 | Identical ledger entries with/without addendum | Core logic unchanged |
| AT-M28-02 | M63 DerivationChain terminating at M28 | Full chain M26->M27->M33->M28 POINTER_BACKED |
| AT-M28-03 | INVARIANT_ENFORCEMENT for universal logging | Carrier present |
| AT-M28-04 | JURISDICTION_OVERLAY on retention/expiry | Carrier present |
| AT-M28-05 | GOVERNANCE_GATE for denied disclosure | Carrier references upstream chain |
| AT-M28-06 | Denied entries include full upstream constraint provenance | No phantom events |
| AT-M28-07 | Patient summary exists for every entry including denials | Dual-audience transparency |
| AT-M28-08 | Expired entries converted to stubs with lineage | DataAbsentReason=expired + provenance |
| AT-M28-09 | Replayability: identical inputs -> identical entries | Deterministic |
| AT-M28-10 | Existing consumers unaffected | No breaking changes |
