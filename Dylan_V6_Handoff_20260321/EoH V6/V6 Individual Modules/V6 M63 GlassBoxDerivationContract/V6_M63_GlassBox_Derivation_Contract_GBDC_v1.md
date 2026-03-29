# V6 M63 — Glass-Box Derivation Contract (GBDC)

**Version:** 1.0 — Final Canonical Draft
**Status:** V6-only · Analysis-only · Non-executable · Read-only
**Classification:** Governance infrastructure — disclosure enforcement

---

## 1. Identity & Scope Lock

### Purpose

Define and enforce the mechanical requirements under which an EoH output MAY be labeled GLASS_BOX. M63 governs derivation transparency — the ability to produce a complete, pointer-backed, reproducible account of how a surfaced output was reached — without exposing architectural internals, proprietary reasoning infrastructure, or module-level implementation.

M63 is the contract that separates **what the system concluded and how it got there** (disclosed) from **how the system is built** (protected).

### Scope

**In scope:**

- Definition of the DerivationChain object and its required fields
- Enforcement contracts: Trace Integrity, Support Disclosure, Uncertainty Preservation, Constraint Disclosure
- Carrier requirements for uncertainty and constraint metadata
- Glass-Box eligibility gate (hard enforcement)
- Replay determinism envelope
- Motif Registry and Math & Logic Update template reference
- Governance MUST / MUST NOT guarantees

**Out of scope:**

- Computing, scoring, or evaluating any clinical output
- Modifying any V5.2 module behavior or V6 module output
- Inventing mathematical structures, equations, or formulas
- Injecting world knowledge, guidelines, disease facts, or drug tables
- Grading evidence quality, support sufficiency, or clinical correctness
- Any execution authority whatsoever

### Foundational Invariant

**M63 discloses. It does not compute, score, grade, or execute.**

Every contract defined herein concerns the representation and completeness of already-existing artifacts produced by owning modules. M63 never creates the content it discloses; it enforces the conditions under which that content may be labeled transparent.

---

## 2. DerivationChain Object Definition

A DerivationChain is a structured, immutable record that captures all reasoning steps required to reproduce a surfaced output from its inputs through to its final form.

### 2.1 Required Fields

| Field | Type | Description |
|---|---|---|
| `chain_id` | string | Unique identifier for this derivation chain instance |
| `output_ref` | pointer | Reference to the surfaced output this chain explains |
| `output_form_class` | enum | Classification of output type (SCALAR, VECTOR, LANDSCAPE, NARRATIVE, COMPOSITE) |
| `inputs[]` | pointer[] | Ordered references to all input artifacts consumed |
| `transformations[]` | step[] | Ordered sequence of processing steps, each with owning module identifier |
| `assumptions[]` | record[] | Declared assumptions active at time of production |
| `motifs_referenced[]` | identifier[] | Mathematical or structural motifs invoked (by registry ID) |
| `uncertainty_disclosure` | object | Status + carriers[] — see §5.1 |
| `constraint_disclosure` | object | Status + applied[] — see §5.2 |
| `completeness_classification` | enum | TRACE_COMPLETE · TRACE_PARTIAL · TRACE_REDACTED · TRACE_UNAVAILABLE |
| `replay_metadata` | object | Version IDs, idempotency key, timestamp, role-context — see §7 |

### 2.2 Transformation Step Record

Each entry in `transformations[]` MUST include:

- `step_index` — ordinal position in the chain
- `owning_module_id` — the module that produced this step's output
- `input_artifact_pointers[]` — references to artifacts consumed (or explicit MISSING / REDACTED placeholders)
- `output_artifact_pointer` — reference to the artifact produced
- `provenance_pointers[]` — stored provenance records connecting inputs to output
- `step_status` — POINTER_BACKED · MISSING · REDACTED

### 2.3 Status Labels

| Label | Meaning |
|---|---|
| TRACE_COMPLETE | No missing placeholders, no redaction placeholders in viewer's role-context, every step pointer-backed |
| TRACE_PARTIAL | One or more steps have MISSING placeholders |
| TRACE_REDACTED | One or more steps have REDACTED placeholders due to role/permissions |
| TRACE_UNAVAILABLE | Chain cannot be constructed (e.g., output predates M63 adoption, upstream module did not emit artifacts) |

### 2.4 Structural Rules

- No silent omission permitted. Every gap MUST appear as an explicit placeholder.
- No output may claim derivation transparency without a DerivationChain.
- Replay MUST be deterministic within the same role-context and version state (see §7).
- DerivationChain is append-only once emitted. Corrections require a new chain version with explicit supersession pointer.

---

## 3. Enforcement Contracts

M63 defines four orthogonal enforcement contracts. Each concerns a distinct dimension of transparency. They MUST NOT bleed into one another.

| Contract | Concern | Does NOT concern |
|---|---|---|
| Trace Integrity | Structural completeness of the chain | Quality, strength, or sufficiency of sources |
| Support Disclosure | Presence/absence of support metadata | Whether support is "good" or "bad" |
| Uncertainty Preservation | Faithful carriage of uncertainty as emitted | Computing, narrowing, or widening uncertainty |
| Constraint Disclosure | Traceability of constraints that shaped output | Whether constraints were correct or optimal |

### 3.1 Trace Integrity Contract

**Definition:** Trace Integrity concerns only whether the system can produce a complete, pointer-backed derivation chain for a surfaced output. It is independent of how strong or weak the underlying sources are.

**Trace Integrity MUST:**

- Represent each surfaced output as a DerivationChain constructed solely from already-existing stored artifacts and lineage pointers.
- Preserve the full chain topology: upstream inputs → intermediate artifacts → producing module outputs → surfaced output.
- Include, for every represented derivation step: the owning module identifier, referenced input artifact pointers (where available), the output artifact pointer, and any stored provenance pointers connecting those artifacts.
- Be explicit about any missing or inaccessible chain elements:
  - If a dependency exists but is inaccessible due to role/permissions, it MUST appear as an explicit REDACTED placeholder (never silently removed).
  - If an expected provenance pointer or upstream artifact pointer does not exist in storage, it MUST appear as an explicit MISSING / NOT_PROVIDED placeholder.
- Mark a chain as TRACE_COMPLETE only when: there are no missing placeholders, there are no redaction placeholders in the viewer's role-context, and each represented step is pointer-backed by stored artifacts/provenance.
- Otherwise mark the chain as TRACE_PARTIAL, TRACE_REDACTED, or TRACE_UNAVAILABLE, consistent with the reason for incompleteness.

**Trace Integrity MUST NOT:**

- Invent a provenance pointer, input reference, intermediate artifact, or module step that is not present in stored artifacts.
- Compress away steps to make the chain appear continuous if doing so would remove missing/redacted segments.
- Treat descriptive prose ("the system used X") as a substitute for an artifact pointer.
- Use Trace Integrity status as a claim of correctness, truth, validity, or clinical sufficiency.

### 3.2 Support Disclosure Contract

**Definition:** Support Disclosure concerns only what support metadata exists and is surfaced (e.g., driver attributions, evidence snapshots, timestamps, provenance, declared confidence objects). It does not evaluate whether support is "good" or "bad."

**Support Disclosure MUST:**

- Attach to the DerivationChain any support artifacts already emitted by owning modules, when present and accessible (e.g., feature snapshots, driver lists, explainer bundles, provenance summaries).
- Disclose, step-by-step, whether each derivation node has: support metadata present, support metadata not provided by owner, or support metadata redacted for role.
- Preserve modality provenance structurally: if multiple modalities contributed, each modality's contribution MUST be pointer-represented as an input artifact (or explicitly marked MISSING / REDACTED).
- Preserve source characteristics as already stored: timestamps, source identifiers, confidence/bounds objects, driver explanations — only if they exist in the artifacts.

**Support Disclosure MUST NOT:**

- Create a "support strength score," "evidence grade," or "literature-backed" label unless such a construct already exists as a governed artifact elsewhere in EoH.
- Upgrade weak or ambiguous inputs into stronger claims by narrative phrasing.
- Import external validation ("proven in literature") as a substitute for internal, pointer-backed support disclosure.
- Treat "support metadata present" as equivalent to "support is sufficient."

### 3.3 Uncertainty Preservation Contract

**Definition:** Uncertainty Preservation concerns how uncertainty is represented and carried through as emitted by owning modules (intervals, bounds, multi-hypothesis sets, suppression-context flags). M63 discloses uncertainty; it does not compute it.

**Uncertainty Preservation MUST:**

- Surface uncertainty representations as provided by producing modules: confidence intervals / bounds objects, multi-pathway posterior sets, probability landscapes with uncertainty bounds, suppression context markers that indicate constrained/held outputs.
- Preserve non-collapse when upstream modules output multiple hypotheses/pathways: M63 MUST NOT collapse multi-output uncertainty into a single statement for convenience.
- Disclose uncertainty absence explicitly: if the owning module did not emit uncertainty metadata for an output, M63 MUST mark uncertainty as NOT_PROVIDED (not inferred).
- Preserve degradation honesty structurally: if an owning module outputs a widened-uncertainty state or reduced-confidence state due to sparse/unstable inputs, M63 MUST carry and display that state exactly as emitted.

**Uncertainty Preservation MUST NOT:**

- Tighten uncertainty (narrow intervals, increase confidence, reduce dispersion) through any formatting, aggregation, or summarization behavior.
- Widen uncertainty by adding new bounds or uncertainty objects not present in the owning module's artifacts.
- Infer uncertainty from missing metadata.
- Present uncertainty handling as an epistemic guarantee ("therefore safe/true") — it is disclosure only.

### 3.4 Constraint Disclosure Contract

**Definition:** Constraint Disclosure concerns whether the constraints that materially shaped an output are traceable and surfaced. Constraints include: suppression state, governance policy gates, invariant enforcement, role-based filtering, consent/jurisdiction overlays, and any other structural shaping that altered what the output would have been in the absence of that constraint.

**Constraint Disclosure MUST:**

- Identify, for each derivation step, whether stored constraint artifacts exist that shaped the output at that step.
- Surface constraint carriers as pointer-backed references to the governing artifact (e.g., suppression record, invariant version, consent gate decision, overlay ID).
- Disclose constraint absence explicitly: if no constraint artifacts are stored for a step that is expected to have been constrained, M63 MUST mark constraint status as NOT_PROVIDED.
- Treat the producing module as the sole authority on materiality. Whether a constraint "materially shaped" an output is determined by the producing module at emission time — not inferred by M63. If the producing module includes a constraint record in its output bundle, that constraint is material. If it does not, M63 has no basis to assert constraint presence.

**Constraint Disclosure MUST NOT:**

- Invent constraint carriers for steps where no constraint artifact exists in storage.
- Infer constraint presence from output characteristics (e.g., "the output looks suppressed, therefore a constraint was applied").
- Override or second-guess a producing module's materiality determination.
- Evaluate whether constraints were correct, optimal, or clinically appropriate — that judgment belongs to other modules.

### 3.5 Constraint Emission Expectation (Non-Normative)

M63 does not require producing modules to emit constraint artifacts. However, any output that was materially shaped by a constraint and lacks a corresponding constraint carrier will have `constraint_disclosure.status` set to NOT_PROVIDED, which blocks GLASS_BOX eligibility per §6.1.5.

Producing modules that enforce invariants, apply suppression, or gate on consent/governance policies are RECOMMENDED to emit a discrete constraint record as part of their standard output bundle. Each constraint record SHOULD contain: constraint identifier, version, enforcement timestamp, and the derivation step at which it was applied.

This is escalation pressure, not a mandate. M63 does not own producing module behavior. The V5.2 Addendum process (see companion document) provides the standard mechanism for retrofitting constraint emission into existing modules without altering their core logic.

---

## 4. One-Line Enforcement Summary (Non-Normative)

The following is descriptive only and has no enforcement power. The contracts in §3 are authoritative.

| Contract | Enforcement question |
|---|---|
| Trace Integrity | "Do we have the full chain, pointer-backed, with no silent gaps?" |
| Support Disclosure | "What support metadata exists for each step, without grading it?" |
| Uncertainty Preservation | "What uncertainty did owners emit, and are we showing it without inflation or collapse?" |
| Constraint Disclosure | "What constraints shaped this output, and can we point to their governing artifacts?" |

---

## 5. Carrier Requirements

### 5.1 Uncertainty Carrier

When a surfaced output is probabilistic, prognostic, or trajectory-based, the DerivationChain MUST include an `uncertainty_disclosure` object:

```
uncertainty_disclosure: {
  status: CARRIERS_PRESENT | NOT_PROVIDED | PARTIAL | REDACTED
  carriers: [
    {
      carrier_type: enum { CONFIDENCE_INTERVAL, BOUNDS_OBJECT, MULTI_HYPOTHESIS_SET,
                           PROBABILITY_LANDSCAPE, SUPPRESSION_CONTEXT, DEGRADATION_STATE }
      source_module_id: identifier
      artifact_pointer: pointer
      emitted_at: timestamp
    }
  ]
}
```

**Rules:**

- Carrier types are a closed enum set. No new carrier types may be introduced inside M63.
- If the owning module emitted uncertainty metadata, M63 MUST attach it as a carrier. If the owning module did not, M63 MUST set status to NOT_PROVIDED.
- M63 MUST NOT infer a carrier type from a scalar probability. A scalar probability without an accompanying bounds/interval object does not constitute an uncertainty carrier.

### 5.2 Constraint Carrier

When a surfaced output was materially shaped by one or more constraints, the DerivationChain MUST include a `constraint_disclosure` object:

```
constraint_disclosure: {
  status: CARRIERS_PRESENT | NOT_PROVIDED | PARTIAL | REDACTED
  applied: [
    {
      constraint_type: enum { SUPPRESSION, GOVERNANCE_GATE, INVARIANT_ENFORCEMENT,
                              ROLE_FILTER, CONSENT_OVERLAY, JURISDICTION_OVERLAY }
      source_artifact_pointer: pointer
      owning_module_id: identifier
      applied_at_step: step_index
    }
  ]
}
```

**Rules:**

- Constraint types are a closed enum set. No new constraint types may be introduced inside M63.
- Constraint carriers MUST be pointer-backed references to stored governance artifacts. Narrative description ("a constraint was applied") does not constitute a carrier.
- If no constraint artifacts are stored for a constrained step, status MUST be NOT_PROVIDED.

### 5.3 Pairing Requirements

| Output form class | Uncertainty carrier required? | Constraint carrier required? |
|---|---|---|
| SCALAR | Only if owning module emitted uncertainty metadata | Only if materially shaped |
| VECTOR | Yes, if any component is probabilistic/prognostic | Only if materially shaped |
| LANDSCAPE | Yes | Only if materially shaped |
| NARRATIVE | Only if owning module emitted uncertainty metadata | Only if materially shaped |
| COMPOSITE | Per-component evaluation | Per-component evaluation |

---

## 6. Glass-Box Eligibility Gate

### 6.1 Eligibility Clause (Hard Enforcement)

An output MAY be labeled GLASS_BOX if and only if ALL of the following are satisfied:

1. A DerivationChain is present for the output.
2. The chain's `completeness_classification` is TRACE_COMPLETE in the current viewer's role-context.
3. No silent omissions exist anywhere in the chain (every gap is an explicit placeholder).
4. If the output is probabilistic/prognostic: an uncertainty carrier is present with status CARRIERS_PRESENT.
5. If the output was materially shaped by constraints: a constraint carrier is present with status CARRIERS_PRESENT.
6. All required pointer fields exist or are explicitly marked REDACTED / NOT_PROVIDED.

### 6.2 Failure Semantics

If any condition in §6.1 is not satisfied:

- The output MUST remain visible and usable. Eligibility failure does not invalidate the output.
- The output MUST NOT carry the GLASS_BOX label.
- The output MUST carry an explicit `transparency_status` field indicating which eligibility condition(s) failed.
- No weakening, softening, or conditional bypass of this gate is permitted.

### 6.3 Escalation Pressure

The eligibility gate is designed to create system pressure toward pointer completeness over time. Modules that fail to emit the artifacts required for GLASS_BOX eligibility will see their outputs permanently ineligible until they do. This is by design: glass-box status only means something if it costs something.

---

## 7. Replay Determinism Envelope

### 7.1 Definition

A DerivationChain is replay-deterministic if, given identical inputs, identical module versions, identical governance state, and identical role-context, the chain can be reconstructed with identical structure and pointer topology.

### 7.2 Required Replay Metadata

```
replay_metadata: {
  chain_version: string
  idempotency_key: string
  production_timestamp: ISO-8601
  module_version_snapshot: { module_id: version }[]
  governance_state_snapshot_ref: pointer
  role_context: identifier
}
```

### 7.3 Rules

- Replay determinism is a structural property of the chain, not a guarantee of clinical outcome equivalence.
- If any module version, governance state, or role-context has changed since chain production, replay MUST be flagged as STALE — not silently rerun under new conditions.
- Replay MUST NOT be used to back-justify outputs under conditions that did not exist at production time.

---

## 8. Motif Registry & Template Reference

### 8.1 Motif Registry

M63 defines a Motif Registry as a governed catalog of mathematical and structural motifs referenced by EoH modules. The registry is a reference mechanism, not a computational one.

**Rules:**

- No equations may be invented inside M63.
- All mathematical descriptions in the registry are structural (naming the abstract form), not computational (performing calculations).
- Modules that reference mathematical motifs in their Math & Logic Update sections MUST register those motifs by identifier in the registry.
- The Motif Registry is append-only. Removal requires explicit deprecation with supersession pointer.

### 8.2 Math & Logic Update Template

M63 defines the canonical template for Math & Logic Update sections used by other modules:

1. **Purpose (unchanged)** — one sentence restating existing module purpose
2. **Mathematical Motifs (Explicit)** — named abstract math structures used (no disease/guideline references)
3. **Deterministic Logic Flow** — input normalization → aggregation/construction → constraint application → output formation
4. **Governance Constraints** — what this math MUST NOT do; what it cannot infer alone; how uncertainty is preserved
5. **Notes** — structural clarifications only; no causal assertions

**Hard constraints on template use:**

- No new variables
- No thresholds unless already canonized
- No patient-facing interpretation
- No recommendations
- No code

---

## 9. Governance Guarantees

### 9.1 M63 MUST

- Enforce all four contracts (Trace Integrity, Support Disclosure, Uncertainty Preservation, Constraint Disclosure) as orthogonal, non-bleeding requirements.
- Require explicit placeholders for every gap, omission, or inaccessible element.
- Maintain the GLASS_BOX eligibility gate as a hard, non-negotiable enforcement mechanism.
- Preserve all upstream uncertainty exactly as emitted — no tightening, no widening, no inference.
- Treat every carrier type enum as closed — no expansion without formal governance amendment.
- Emit FHIR-compatible audit artifacts (AuditEvent, Provenance) for every DerivationChain production event.

### 9.2 M63 MUST NOT

- Compute, score, grade, or evaluate any clinical output.
- Invent provenance pointers, constraint carriers, uncertainty carriers, or any artifact not already stored.
- Collapse multi-hypothesis uncertainty into single-point summaries.
- Infer uncertainty from missing metadata.
- Infer constraints from output characteristics.
- Treat GLASS_BOX status as a claim of correctness, truth, validity, or clinical sufficiency.
- Substitute narrative prose for pointer-backed artifacts.
- Weaken, soften, or conditionally bypass the eligibility gate.
- Introduce new mathematical structures, equations, or computational logic.
- Embed world knowledge, guidelines, disease facts, drug tables, or ontology content.

---

## 10. Stack Placement & Dependencies

### Stack Position

M63 operates as a cross-cutting governance layer. It does not sit in the clinical processing pipeline. It reads artifacts produced by other modules and evaluates them against its contracts. It writes only DerivationChain records and transparency status labels.

### Dependencies (Consumed)

| Source | What M63 reads |
|---|---|
| Any producing module | Output artifacts, provenance records, uncertainty metadata, constraint records |
| Governance infrastructure (M57, invariants) | Named invariant versions, governance state snapshots |
| Suppression engine (M9) | Suppression records (pauseFlag, pauseReason) as constraint artifacts |
| Consent/overlay system (M26) | Consent gate decisions, jurisdiction overlay IDs |
| Audit infrastructure (M41, Appendix C) | Existing AuditEvent/Provenance records for pointer validation |

### Dependencies (Produced)

| Output | Consumers |
|---|---|
| DerivationChain records | Any module or surface that needs to display or verify transparency status |
| GLASS_BOX / ineligibility labels | Patient-facing surfaces, clinician UI, regulatory export, QA |
| Audit artifacts (AuditEvent, Provenance) | M41, Appendix C.7/C.11, disclosure accounting |

### Ownership Boundaries

- M63 owns the transparency contract and eligibility gate. It does not own the artifacts it evaluates.
- Producing modules own their outputs, uncertainty metadata, and constraint records. M63 cannot modify them.
- M67 (ARGL) owns adversarial reasoning governance. M63 does not duplicate adversarial review — it discloses the derivation of outputs that may or may not have passed through ARGL.

---

## 11. Acceptance Tests

| ID | Test | Input | Expected Result |
|---|---|---|---|
| T-01 | Complete chain eligibility | Output with all steps pointer-backed, uncertainty carrier present, constraint carrier present | GLASS_BOX label applied |
| T-02 | Missing step rejection | Output with one MISSING placeholder in chain | GLASS_BOX label denied; transparency_status indicates failed condition |
| T-03 | No silent omission | Output with a gap not represented by any placeholder | System-level validation failure; chain marked INVALID |
| T-04 | Uncertainty non-inference | Scalar probability output where owning module did not emit bounds | uncertainty_disclosure.status = NOT_PROVIDED; GLASS_BOX denied if output is probabilistic |
| T-05 | Uncertainty non-collapse | Upstream module emits 3-hypothesis set | DerivationChain carries all 3 hypotheses; no single-point summary |
| T-06 | Uncertainty non-tightening | Upstream emits wide confidence interval | Interval reproduced exactly; no narrowing |
| T-07 | Constraint non-invention | Step where no constraint artifact exists in storage | constraint_disclosure.status = NOT_PROVIDED; no invented carrier |
| T-08 | Redaction transparency | Step accessible in one role-context but not another | REDACTED placeholder in restricted context; TRACE_REDACTED classification |
| T-09 | Replay determinism | Identical inputs + versions + governance + role-context | Structurally identical DerivationChain |
| T-10 | Replay staleness detection | Replay attempted with changed module version | Chain flagged STALE; not silently regenerated |
| T-11 | Narrative substitution rejection | Attempt to use prose description ("system used X") as artifact pointer | Validation failure; pointer field rejected |
| T-12 | Contract orthogonality | Trace Integrity failure | Support Disclosure, Uncertainty Preservation, and Constraint Disclosure evaluated independently |

---

## 12. Metrics (Track Over Time)

| Metric | Definition | Target Direction |
|---|---|---|
| Glass-Box eligibility rate | % of surfaced outputs that qualify for GLASS_BOX label | ↑ Increase over time |
| Pointer completeness | % of derivation steps that are fully pointer-backed (no MISSING/REDACTED) | ↑ Increase over time |
| Uncertainty carrier coverage | % of probabilistic/prognostic outputs with CARRIERS_PRESENT | ↑ Increase over time |
| Constraint carrier coverage | % of constrained outputs with CARRIERS_PRESENT | ↑ Increase over time |
| Silent omission rate | % of chains flagged INVALID due to unplaceholdered gaps | ↓ Zero target |
| Replay consistency | % of replay attempts that produce structurally identical chains | ↑ Maximize |
| Staleness detection rate | % of version-changed replays correctly flagged STALE | ↑ 100% target |

---

## 13. Canonical Anchor Statement

M63 makes transparency a mechanical property of the system, not a marketing claim about the system.

The architecture is proprietary. The derivation is disclosed. An output either meets the eligibility gate or it does not. There is no partial credit, no narrative substitute, and no conditional bypass.

Glass-box status only means something if it costs something.

---

*End of V6 M63 — Glass-Box Derivation Contract (GBDC) v1.0*
