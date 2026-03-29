# M63 — Derivation Transparency Contract

## 1. Module Header (Identity + Scope Lock)

Purpose: Define mandatory disclosure and enforcement requirements for derivation transparency.

Scope:
- Analysis-only
- Read-only
- No execution authority
- No mathematical invention
- No certainty inflation

---

## 2. DerivationChain Object Definition

A DerivationChain is a structured record that captures all reasoning steps required to reproduce an output.

Required fields:
- Inputs
- Transformations
- Assumptions
- Motifs referenced
- Uncertainty markers

Status labels:
- COMPLETE
- PARTIAL
- REDACTED
- UNAVAILABLE

Rules:
- No silent omission permitted
- No output may claim transparency without a DerivationChain
- Replay must be deterministic within role-context

---
## 3. Contracts

### One-line Enforcement Summary (Non-Normative)

- Trace Integrity: “Do we have the full chain, pointer-backed, with no silent gaps?”
- Support Disclosure: “What support metadata exists for each step, without grading it?”
- Uncertainty Preservation: “What uncertainty did owners emit, and are we showing it without inflation or collapse?”

The following contracts are authoritative. This summary is descriptive only and has no enforcement power.

### 3.1 Trace Integrity Contract
Trace Integrity Contract

Definition (non-negotiable separation):
Trace Integrity concerns only whether the system can produce a complete, pointer-backed derivation chain for a surfaced output. It is independent of how strong/weak the underlying sources are.

Trace Integrity MUST

MUST represent each surfaced output as a DerivationChain that is constructed solely from already-existing stored artifacts and lineage pointers.

MUST preserve the full chain topology: upstream inputs → intermediate artifacts → producing module outputs → surfaced output.

MUST include, for every derivation step that is represented:

the owning module identifier (the module that produced that artifact/step),

the referenced input artifact pointers (where available),

the output artifact pointer,

and any stored provenance pointer(s) that connect those artifacts.

MUST be explicit about any missing or inaccessible chain elements:

If a dependency exists but is not accessible due to role/permissions, it MUST appear as an explicit REDACTED placeholder (never silently removed).

If an expected provenance pointer or upstream artifact pointer does not exist in storage, it MUST appear as an explicit MISSING / NOT-PROVIDED placeholder.

MUST mark a chain as TRACE_COMPLETE only when:

there are no missing placeholders, and

there are no redaction placeholders in the viewer’s role-context, and

each represented step is pointer-backed by stored artifacts/provenance.

MUST otherwise mark the chain as TRACE_PARTIAL, TRACE_REDACTED, or TRACE_UNAVAILABLE (consistent with the reason for incompleteness).

Trace Integrity MUST NOT

MUST NOT invent a provenance pointer, input reference, intermediate artifact, or module step that is not present in stored artifacts.

MUST NOT “compress away” steps to make the chain look continuous if doing so would remove missing/redacted segments.

MUST NOT treat descriptive prose (“the system used X”) as a substitute for an artifact pointer.

MUST NOT use Trace Integrity status as a claim of correctness, truth, validity, or clinical sufficiency.

### 3.2 Support Disclosure Contract
Support Disclosure Contract

Definition (hard separation):
Support Disclosure concerns only what support metadata exists and is surfaced (e.g., driver attributions, evidence snapshots, timestamps, provenance, declared confidence objects). It does not evaluate whether support is “good” or “bad.”

Support Disclosure MUST

MUST attach to the DerivationChain any support artifacts already emitted by owning modules, when present and accessible (e.g., feature snapshots, driver lists, explainer bundles, provenance summaries).

MUST disclose, step-by-step, whether each derivation node has:

support metadata present, or

support metadata not provided by owner, or

support metadata redacted for role.

MUST preserve modality provenance structurally:

If multiple modalities contributed, each modality’s contribution MUST be pointer-represented as an input artifact (or explicitly marked missing/redacted).

MUST preserve source characteristics as already stored:

timestamps, source identifiers, confidence/bounds objects, “driver” explanations, etc., only if they exist in the artifacts.

Support Disclosure MUST NOT

MUST NOT create a “support strength score,” “evidence grade,” or “literature-backed” label unless such a construct already exists as a governed artifact elsewhere in EoH.

MUST NOT upgrade weak/ambiguous inputs into stronger claims by narrative phrasing.

MUST NOT import external validation (“proven in literature”) as a substitute for internal, pointer-backed support disclosure.

MUST NOT treat “support metadata present” as equivalent to “support is sufficient.”

### 3.3 Uncertainty Preservation Contract
Uncertainty Preservation Contract

Definition (hard separation):
Uncertainty Preservation concerns how uncertainty is represented and carried through as emitted by owning modules (intervals, bounds, multi-hypothesis sets, suppression-context flags). M63 discloses uncertainty; it does not compute it.

Uncertainty Preservation MUST

MUST surface uncertainty representations as provided by producing modules:

confidence intervals / bounds objects,

multi-pathway posterior sets,

probability landscapes with uncertainty bounds,

suppression context markers that indicate constrained/held outputs.

MUST preserve non-collapse when upstream modules output multiple hypotheses/pathways:

M63 may not collapse multi-output uncertainty into a single statement for convenience.

MUST disclose uncertainty absence explicitly:

If the owning module did not emit uncertainty metadata for an output, M63 MUST mark uncertainty as NOT-PROVIDED (not inferred).

MUST preserve “degradation honesty” structurally:

If an owning module outputs a widened-uncertainty state (or reduced-confidence state) due to sparse/unstable inputs, M63 MUST carry and display that state exactly as emitted.

Uncertainty Preservation MUST NOT

MUST NOT tighten uncertainty (narrow intervals, increase confidence, reduce dispersion) through any formatting, aggregation, or summarization behavior.

MUST NOT widen uncertainty by adding new bounds or uncertainty objects not present in the owning module’s artifacts.

MUST NOT infer uncertainty from missing metadata.

MUST NOT present uncertainty handling as an epistemic guarantee (“therefore safe/true”)—it is disclosure only.
---
## 4. Motif Registry + Math & Logic Update Template

M63 defines a single Math & Logic Update template to be referenced by other modules.

No equations may be invented inside M63.
All math descriptions are structural, not computational.
---
## 5. Glass-Box Eligibility Rules
An output MAY be labeled “glass-box” only if:
- DerivationChain is present
- Trace Integrity Contract is satisfied
- No silent omissions exist
- Uncertainty markers are preserved

Failure to meet these conditions does not invalidate the output,
but prohibits glass-box labeling.
