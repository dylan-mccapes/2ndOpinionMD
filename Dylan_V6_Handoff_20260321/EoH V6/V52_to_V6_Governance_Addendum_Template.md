# V5.2 → V6 Governance Addendum Template

**Version:** 1.0
**Status:** Canonical template — used for all V5.2 module addendums
**Classification:** Governance infrastructure — compliance retrofitting

---

## Purpose of This Template

This template defines the standard format for retrofitting V5.2 modules with V6 governance compliance. An addendum does NOT modify the core logic of a V5.2 module. It adds an **emission layer** that makes the module's existing behavior visible to V6 governance infrastructure (M63, M67, M57, and downstream consumers).

The goal: V5.2 modules keep doing what they do. They now **tell the governance stack what they did** in a format that V6 modules can evaluate, trace, and disclose.

---

## Hard Constraints on Addendum Authoring

**An addendum MUST NOT:**

- Change, replace, or reinterpret the module's core processing logic
- Add new clinical reasoning, scoring formulas, or diagnostic behavior
- Introduce new variables, thresholds, or state machines not already present in the V5.2 spec
- Embed world knowledge, guidelines, disease facts, drug tables, or ontology content
- Alter the module's input/output contract (existing consumers must not break)
- Expand the module's scope or ownership boundaries

**An addendum MUST:**

- Be a companion document to the existing V5.2 spec (not a replacement)
- Reference the V5.2 spec by version and section for every emission it defines
- Produce only artifacts that describe what the module already does — never artifacts that introduce new behavior
- Follow the section structure defined below exactly
- Be traceable: every addendum field must map to a specific V6 governance requirement with a cited source (M63 section, M67 contract, etc.)

---

## Addendum Document Structure

Each addendum follows this structure. All sections are required. If a section is not applicable, it MUST contain "Not applicable — [reason]" rather than being omitted.

---

### A. Module Identity & Addendum Scope

```
Module:          [V5.2 Module ID and Name]
V5.2 Spec Ref:   [Version, date, or document pointer]
Addendum Version: [1.0]
Addendum Status:  DRAFT | REVIEW | CANONICAL
```

**Addendum scope statement:** One paragraph describing what this addendum adds and, critically, what it does NOT change. Must explicitly state: "Core processing logic is unchanged. This addendum adds V6 governance emission only."

---

### B. M63 Compliance — Derivation Chain Emission

Define what this module must emit so that M63 can construct a DerivationChain through it.

**B.1 Output Artifact Registration**

For each output the module produces, declare:

| Output | Artifact Type | Pointer Format | Provenance Record Emitted? |
|---|---|---|---|
| [output name] | [FHIR type or internal type] | [pointer format] | Yes / No — if No, state why |

**B.2 Input Artifact Traceability**

For each input the module consumes, declare:

| Input | Source Module | Pointer Available? | If No, Gap Classification |
|---|---|---|---|
| [input name] | [M-ID] | Yes / MISSING / REDACTED | [reason if not available] |

**B.3 Transformation Step Registration**

Map the module's processing stages to DerivationChain transformation steps:

| Step Index | Processing Stage (from V5.2 spec) | Owning Module | Input Pointers | Output Pointer |
|---|---|---|---|---|
| 1 | [stage name, with V5.2 section ref] | [M-ID] | [pointer list] | [pointer] |

---

### C. M63 Compliance — Uncertainty Carrier Emission

Define what uncertainty metadata this module emits (or does not emit) for its outputs.

**C.1 Uncertainty Inventory**

For each output that is probabilistic, prognostic, or trajectory-based:

| Output | Uncertainty Metadata Currently Emitted? | Carrier Type (per M63 §5.1 enum) | Action Required |
|---|---|---|---|
| [output name] | Yes — [describe] / No | [CONFIDENCE_INTERVAL / BOUNDS_OBJECT / etc.] | None / Emit new carrier / Mark NOT_PROVIDED |

**C.2 Degradation State**

Does this module emit widened-uncertainty or reduced-confidence states when inputs are sparse/unstable?

- If yes: describe the existing mechanism and how it maps to M63's DEGRADATION_STATE carrier type.
- If no: state explicitly. M63 will mark uncertainty as NOT_PROVIDED for degraded outputs.

---

### D. M63 Compliance — Constraint Carrier Emission

Define what constraint records this module emits when its invariants, suppression logic, or governance gates fire.

**D.1 Constraint Inventory**

| Constraint | Trigger Condition (V5.2 spec ref) | Constraint Type (per M63 §5.2 enum) | Currently Emitted as Artifact? | Action Required |
|---|---|---|---|---|
| [constraint name] | [section ref] | [SUPPRESSION / GOVERNANCE_GATE / INVARIANT_ENFORCEMENT / etc.] | Yes / No | None / Emit new record |

**D.2 Materiality Declaration**

For each constraint in D.1: when this constraint fires, the module MUST include a constraint record in its output bundle. This constitutes the module's materiality declaration per M63 §3.4.

---

### E. M67 (ARGL) Integration — Opt-In Declaration

**Opt-in status:** OPT_IN | DEFERRED | NOT_APPLICABLE

If OPT_IN:

- **Integration point:** Where in the module's processing does ARGL invocation occur? (Must be before downstream propagation.)
- **Invocation payload:** What does the module send to ARGL? (`reasoning_chain_output`, `invocation_context`, `patient_state_snapshot` per M67 integration contract)
- **Result handling:** Module proceeds only with `accepted_claims[]` from ARGL decision record. Rejected claims are logged but not propagated.

If DEFERRED:

- **Reason for deferral:** [explain]
- **Conditions for future opt-in:** [describe what would need to change]

---

### F. FHIR Audit Artifact Emission

Define the audit artifacts this module emits per V6 standards.

**F.1 AuditEvent Emission**

| Event | Trigger | Required Fields |
|---|---|---|
| [event name] | [trigger condition] | [field list per Appendix C.7/C.11] |

**F.2 Provenance Emission**

| Provenance Record | Connects | FHIR Resource Type |
|---|---|---|
| [record name] | [input artifact → output artifact] | Provenance |

---

### G. V6 Consumer Contract

Declare which V6 modules consume this module's outputs and what they expect.

| V6 Consumer | What It Reads | Contract Reference | Addendum Satisfies? |
|---|---|---|---|
| M63 (GBDC) | DerivationChain steps, carriers | M63 §2, §5 | Yes / Partial — [gap] |
| M64 (FUDD) | [if applicable] | M64 § | Yes / Partial — [gap] |
| M67 (ARGL) | [if applicable] | M67 integration contract | Yes / Deferred |
| M68 (ICM) | [if applicable] | M68 § | Yes / Partial — [gap] |

---

### H. Gap Register

Any V6 governance requirement that this addendum cannot satisfy without modifying core module logic.

| Gap ID | V6 Requirement | Why Addendum Cannot Satisfy | Resolution Path |
|---|---|---|---|
| [G-01] | [requirement with section ref] | [explanation] | [future rewrite / V6 module owns this / deferred] |

---

### I. Implementation Checklist

| Item | Status | Notes |
|---|---|---|
| Output artifact pointers defined | ☐ | |
| Input traceability mapped | ☐ | |
| Transformation steps registered | ☐ | |
| Uncertainty carriers defined or NOT_PROVIDED declared | ☐ | |
| Constraint carriers defined or NOT_PROVIDED declared | ☐ | |
| ARGL opt-in status declared | ☐ | |
| FHIR audit artifacts specified | ☐ | |
| V6 consumer contracts validated | ☐ | |
| Gap register complete | ☐ | |
| Addendum reviewed against V5.2 spec (no core logic changes) | ☐ | |

---

### J. Acceptance Tests

| ID | Test | Expected Result |
|---|---|---|
| AT-01 | Module produces identical outputs with and without addendum emission layer active | Core logic unchanged; emission is additive only |
| AT-02 | M63 can construct a DerivationChain through this module using emitted artifacts | Chain steps are POINTER_BACKED (or explicitly MISSING with gap registered) |
| AT-03 | Uncertainty carriers match M63 §5.1 enum types | No invented carrier types; NOT_PROVIDED where metadata absent |
| AT-04 | Constraint carriers match M63 §5.2 enum types | No invented carriers; NOT_PROVIDED where records absent |
| AT-05 | ARGL integration (if opted in) follows M67 contract | Decision record consumed; rejected claims not propagated |
| AT-06 | Existing downstream V5.2 consumers unaffected | No breaking changes to module's output contract |

---

## Tiered Rollout Plan

Addendums are authored in dependency-priority order:

| Tier | Modules | Rationale |
|---|---|---|
| **Tier 1** | M3, M9, M7 | Highest V6 dependency pressure — M63/M64/M67/M68 trace through these |
| **Tier 2** | M13, M14, M15, M8 | Feed M53/M54 (PTM/TCS); uncertainty metadata critical for prognostic transparency |
| **Tier 3** | M26, M27, M28, M33 | Governance/disclosure stack — already closest to M63 compliance |
| **Tier 4** | M49, M53 | Require substantive rewrites, not addendums — separate workstream |

---

## Workflow for Addendum Generation

1. Add this template + patched M63 spec + V5.2 Cannon to project reference files.
2. Open a new chat per tier (not per module — modules within a tier need cross-validation).
3. Prompt: "Generate V6 governance addendums for Tier [N] modules: [list]. Use the V5.2 Addendum Template. Read the V5.2 specs from the Cannon and validate against M63 carrier requirements."
4. Review, refine, iterate within the chat.
5. Export finalized addendums back into project reference files as canonical documents.
6. Repeat for next tier.

---

*End of V5.2 → V6 Governance Addendum Template v1.0*
