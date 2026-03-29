# Addendum: M49 -- Evidence-Weighted Second Opinion Differential Diagnosis Engine

**Modules:** M49 (Evidence-Weighted Second Opinion Differential Diagnosis Engine)
**Template Version:** V5.2 -> V6 Governance Addendum Template v1.0
**Validated Against:** M63 GBDC v1.0 (carrier enums SS5.1, SS5.2); M67 ARGL Integration Contract
**Status:** DRAFT -- pending Dylan review

---

## A. Module Identity & Addendum Scope

```
Module:           V5.2 M49 -- Evidence-Weighted Second Opinion Differential Diagnosis Engine
V5.2 Spec Ref:    V5.2 Cannon, M49 (Evidence-Weighted Second Opinion Differential Diagnosis Engine)
Addendum Version: 1.0
Addendum Status:  DRAFT
```

**Addendum scope statement:** This addendum defines the V6 governance emission layer for M49. It specifies which artifacts M49 must emit so that M63 can construct a DerivationChain through it, what uncertainty and constraint carriers accompany those artifacts, and how M67 ARGL opt-in status is declared. Core processing logic is unchanged. This addendum adds V6 governance emission only. M49's evidence ingestion from MKG, weight-by-source scoring, optional prevalence adjustment, rank-and-select logic (single vs. top-3), evidence citation attachment, and evidence contribution ranking remain exactly as specified in the V5.2 Cannon. No new variables, thresholds, scoring formulas, or state machines are introduced.

---

## B. M63 Compliance -- Derivation Chain Emission

### B.1 Output Artifact Registration

| Output | Artifact Type | Pointer Format | Provenance Record Emitted? |
|---|---|---|---|
| `ranked_diagnoses[]` | RiskAssessment (FHIR) | `M49:ra:ranked-diagnoses:{patient_id}:{timestamp}` | Yes -- links to input `MKG_results` snapshot and per-diagnosis score computations |
| `final_output` (single_diagnosis OR top_3_differentials) | RiskAssessment (FHIR) | `M49:ra:final-output:{patient_id}:{timestamp}` | Yes -- links to `ranked_diagnoses[]` and selection decision trace |
| `diagnosis_score` (per output diagnosis) | Observation (FHIR) | `M49:obs:diagnosis-score:{patient_id}:{diagnosis_id}:{timestamp}` | Yes -- links to evidence_list scoring breakdown |
| `evidence_citations[]` (per output diagnosis) | DocumentReference (FHIR) | `M49:doc:evidence-citations:{patient_id}:{diagnosis_id}:{timestamp}` | Yes -- links to MKG source_citation_pointers consumed |
| `evidence_contribution_ranking[]` (per output diagnosis) | DocumentReference (internal) | `M49:doc:evidence-contribution:{patient_id}:{diagnosis_id}:{timestamp}` | Yes -- links to per-node weight computations |
| `output_size_decision` (single vs. top-3 trace) | DocumentReference (internal) | `M49:doc:output-size-decision:{patient_id}:{timestamp}` | Yes -- links to score distribution analysis |

### B.2 Input Artifact Traceability

| Input | Source Module | Pointer Available? | If No, Gap Classification |
|---|---|---|---|
| `MKG_results` (full payload) | MKG reasoning engine | MISSING | G-01: MKG does not currently emit pointer-backed result snapshots; results arrive as transient payloads without artifact IDs |
| `candidate_diagnoses[]` | MKG reasoning engine (within MKG_results) | MISSING | Same as G-01 -- subfield of unregistered MKG payload |
| `evidence_list[]` (per candidate) | MKG reasoning engine (within MKG_results) | MISSING | Same as G-01 -- evidence nodes are MKG-internal objects without discrete artifact pointers |
| `source_citation_pointer` (per evidence node) | MKG / external literature | PARTIAL | G-02: Some MKG evidence nodes carry linkable citation pointers (DOIs, guideline IDs); others carry only descriptive metadata without resolvable artifact references |
| `prevalence_or_rarity_metadata` (optional) | MKG / epidemiological data | MISSING | G-03: When present, this metadata lacks artifact registration; it is an optional transient field |

### B.3 Transformation Step Registration

| Step Index | Processing Stage (from V5.2 spec) | Owning Module | Input Pointers | Output Pointer |
|---|---|---|---|---|
| 1 | Ingest MKG output -- read candidate diagnoses and linked evidence nodes (Process SS1) | M49 | `MKG_results` snapshot (MISSING -- G-01) | No discrete output -- ingestion gate only |
| 2 | Initialize scoring -- set score = 0 for each candidate (Process SS2) | M49 | Candidate set from Step 1 | Internal state only -- no emitted artifact |
| 3 | Weight-by-source and relevance accumulation -- compute weight * relevance per evidence node, accumulate per diagnosis (Process SS3) | M49 | Evidence nodes from Step 1 (MISSING -- G-01) | `M49:obs:diagnosis-score:{pid}:{dx_id}:{ts}` (intermediate, pre-adjustment) |
| 4 | Optional prevalence adjustment -- AdjustForPrevalence if applicable (Process SS4) | M49 | `M49:obs:diagnosis-score:{pid}:{dx_id}:{ts}` (pre-adjustment), `prevalence_or_rarity_metadata` (MISSING -- G-03) | `M49:obs:diagnosis-score:{pid}:{dx_id}:{ts}` (post-adjustment); constraint carrier emitted if adjustment applied (see D.1) |
| 5 | Rank diagnoses -- sort by score descending (Process SS6) | M49 | All `M49:obs:diagnosis-score:{pid}:{dx_id}:{ts}` | `M49:ra:ranked-diagnoses:{pid}:{ts}` |
| 6 | Select output size (1 vs. 3) -- evaluate confidence distribution gap (Process SS7) | M49 | `M49:ra:ranked-diagnoses:{pid}:{ts}` | `M49:doc:output-size-decision:{pid}:{ts}`; constraint carrier emitted (see D.1) |
| 7 | Attach provenance -- link evidence citations to each output diagnosis (Process SS8) | M49 | `M49:ra:ranked-diagnoses:{pid}:{ts}`, source_citation_pointers (PARTIAL -- G-02) | `M49:doc:evidence-citations:{pid}:{dx_id}:{ts}` |
| 8 | Rank evidence contributions per diagnosis -- highlight most influential sources (Process SS9) | M49 | Per-diagnosis weight breakdowns from Step 3 | `M49:doc:evidence-contribution:{pid}:{dx_id}:{ts}` |
| 9 | Emit final output -- assemble patient-facing second opinion bundle (Process SS7 output) | M49 | Steps 5-8 outputs | `M49:ra:final-output:{pid}:{ts}` |
| 10 | Audit-grade emission (Audit Hooks) | M49 | All outputs from Steps 3-9 | AuditEvent + Provenance records per F.1/F.2 |

---

## C. M63 Compliance -- Uncertainty Carrier Emission

### C.1 Uncertainty Inventory

| Output | Uncertainty Metadata Currently Emitted? | Carrier Type (per M63 SS5.1 enum) | Action Required |
|---|---|---|---|
| `diagnosis_score` (per diagnosis) | No -- continuous scalar produced by weighted additive accumulation; no bounds, intervals, or confidence metadata emitted | NOT_PROVIDED | Mark NOT_PROVIDED. Future: emit CONFIDENCE_INTERVAL reflecting evidence completeness and source quality variance across the evidence_list (requires MKG to emit quality metadata consistently -- see G-04) |
| `ranked_diagnoses[]` | No -- ordered list with scores but no uncertainty envelope around rank stability | NOT_PROVIDED | Mark NOT_PROVIDED. Future: emit BOUNDS_OBJECT reflecting score-gap sensitivity (how much would scores need to shift to change the ranking) |
| `final_output` (single vs. top-3) | No -- the selection decision is deterministic given scores, but no metadata about how close the decision was to flipping | NOT_PROVIDED | Mark NOT_PROVIDED. Future: emit CONFIDENCE_INTERVAL reflecting proximity of the score gap to the selection threshold |
| `evidence_citations[]` | No -- citations are provenance pointers, not probabilistic outputs | N/A | Not applicable -- citations are structural references, not probabilistic or prognostic artifacts; no uncertainty carrier required |
| `evidence_contribution_ranking[]` | No -- deterministic ranking of weight contributions | NOT_PROVIDED | Mark NOT_PROVIDED |

### C.2 Degradation State

M49 does not currently emit a widened-uncertainty or reduced-confidence state when inputs are sparse or unstable. The V5.2 spec acknowledges that MKG evidence nodes may have optional fields (`association_strength`, `publication_quality`, `patient_profile_match`) that may or may not be provided by MKG. When these fields are absent, M49 proceeds with whatever is available -- it does not flag the computation as degraded.

**Action Required:** Emit a `DEGRADATION_STATE` carrier when the evidence base for a candidate diagnosis falls below a minimum density threshold (e.g., fewer than N evidence nodes, or all evidence nodes missing quality metadata). The carrier artifact pointer references the specific diagnosis and its sparse evidence set. This requires defining the density threshold, which would constitute a new variable -- therefore this is deferred to the Tier 4 rewrite workstream. See G-04.

For now: M63 will mark uncertainty as NOT_PROVIDED for all M49 outputs. The absence of a DEGRADATION_STATE carrier means M63 cannot distinguish between "M49 had rich evidence and produced a confident ranking" and "M49 had sparse evidence and produced a best-effort ranking." This is a known transparency gap.

---

## D. M63 Compliance -- Constraint Carrier Emission

### D.1 Constraint Inventory

| Constraint | Trigger Condition (V5.2 spec ref) | Constraint Type (per M63 SS5.2 enum) | Currently Emitted as Artifact? | Action Required |
|---|---|---|---|---|
| Output size selection (single vs. top-3) | Process SS7: confidence distribution gap determines whether one diagnosis or three are surfaced to the patient | GOVERNANCE_GATE | No -- the decision is logged in audit hooks but not as a typed M63 constraint carrier | Emit GOVERNANCE_GATE constraint carrier when this decision fires. Artifact: `M49:constraint:output-size-gate:{pid}:{ts}` with fields: `decision` (single/top-3), `score_gap` (top vs. second), `threshold_applied`. This is the most patient-material constraint in M49 -- it determines whether the patient sees "one strong answer" or "three possibilities to discuss with your doctor." |
| Prevalence adjustment application | Process SS4: optional prevalence/rarity adjustment alters diagnosis scores | GOVERNANCE_GATE | No -- if applied, recorded in audit hooks but not as a constraint carrier | Emit GOVERNANCE_GATE constraint carrier when AdjustForPrevalence is invoked. Artifact: `M49:constraint:prevalence-adjustment:{pid}:{dx_id}:{ts}` with fields: `pre_adjustment_score`, `post_adjustment_score`, `adjustment_source`. When NOT applied, no carrier emitted (absence is non-material). |
| Concise output invariant | Governance: "Outputs must remain concise (single diagnosis when high-confidence; otherwise top 3)" | INVARIANT_ENFORCEMENT | No -- enforced structurally (output is always 1 or 3, never unbounded) | Emit INVARIANT_ENFORCEMENT constraint carrier confirming the output count is within bounds. Artifact: `M49:constraint:concise-output:{pid}:{ts}` with field: `output_count` (1 or 3) |
| Evidence-backed output invariant | Governance: outputs "must always carry supporting evidence for clinician comparison" | INVARIANT_ENFORCEMENT | No -- enforced structurally (every output diagnosis has citations) | Emit INVARIANT_ENFORCEMENT constraint carrier confirming every output diagnosis has at least one evidence citation. Artifact: `M49:constraint:evidence-backed:{pid}:{ts}` with fields: `diagnoses_checked`, `all_have_citations` (boolean) |
| MKG-only input invariant | Scope/Governance: "Module 49 uses MKG-derived candidate diagnoses and evidence nodes as the raw materials" -- no self-generated candidates | INVARIANT_ENFORCEMENT | No -- enforced by design (M49 has no candidate generation logic) | Emit INVARIANT_ENFORCEMENT constraint carrier at ingestion confirming all candidates originated from MKG. Artifact: `M49:constraint:mkg-only-input:{pid}:{ts}` |

### D.2 Materiality Declaration

For each constraint in D.1: when the constraint fires (i.e., when the governance gate evaluates, the invariant is enforced, or a structural bound is tested), M49 MUST include the corresponding constraint record in its output bundle for that computation cycle. This constitutes M49's materiality declaration per M63 SS3.4.

The **output size selection** constraint at Step 6 is the highest-materiality trigger -- it directly determines the shape and content of the patient-facing output. The **prevalence adjustment** constraint at Step 4 is the highest-impact score-altering constraint, as it modifies the ranking that drives selection.

---

## E. M67 (ARGL) Integration -- Opt-In Declaration

**Opt-in status:** OPT_IN

**Rationale for opt-in:** M49 is a patient-facing module. Its output -- ranked diagnoses with evidence summaries -- is presented directly to patients as a "second opinion." Unlike internal state-computation modules (e.g., M3), M49 produces clinical interpretive output that patients will read and potentially act upon before consulting their doctor. This places M49 squarely within ARGL's target category: "clinical interpretations, pattern detections, trajectory forecasts, or recommendation candidates" (M67 Scope). Adversarial governance is critical here because:

1. **Evidence laundering risk:** M49 consumes MKG evidence nodes and attaches citations. If the evidence does not actually support the specific diagnosis it is cited for, the patient receives a false impression of evidentiary support. ARGL's I-B3 (evidence must support the specific claim) directly mitigates this.
2. **Premature closure risk:** If one diagnosis scores decisively higher and the single-output path is taken, the patient sees only one possibility. ARGL's mandatory falsification (I-D1) ensures at least one adversarial evaluation challenges the top diagnosis before it reaches the patient alone.
3. **Narrative drift risk:** The evidence contribution ranking (which studies were "most influential") shapes patient perception. ARGL's rebinding contract (I-C1) ensures the ranking remains bound to the specific patient context.

**Integration point:** After Step 9 (final output assembly) and before downstream propagation to the patient-facing UI. M49 assembles the complete output bundle (ranked diagnoses, scores, citations, contribution rankings, output size decision), then invokes ARGL before emitting to downstream consumers.

**Invocation payload:**

- `reasoning_chain_output`: The complete M49 output bundle -- `final_output` (single or top-3), all `diagnosis_score` values, `evidence_citations[]`, `evidence_contribution_ranking[]`, and `output_size_decision` trace
- `invocation_context`: Module ID (M49), computation timestamp, V5.2 spec version, MKG_results reference ID
- `patient_state_snapshot`: Current patient state from M56 Patient Vision (stability band, medication regimen, suppression status, temporal context) -- required for ARGL rebinding check (I-C1)

**Result handling:** M49 proceeds only with `accepted_claims[]` from the ARGL decision record. Specifically:

- If ARGL accepts the full output bundle: M49 emits to downstream consumers unchanged.
- If ARGL rejects one or more diagnoses (e.g., evidence does not support the specific claim per I-B3): those diagnoses are removed from the patient-facing output. The rejection is logged with the ARGL decision record pointer. If the rejection reduces the top-3 to fewer than 3, the output reflects only accepted diagnoses.
- If ARGL rejects the single-diagnosis output (mandatory falsification finds the leading diagnosis unsupported): M49 falls back to the top-3 path with only ARGL-accepted diagnoses, or emits a "no confident second opinion available" result if no diagnoses survive. This fallback does not introduce new logic -- it uses the existing output paths with a reduced candidate set.
- All ARGL rejections are logged as audit artifacts with pointers to the ARGL decision record.

---

## F. FHIR Audit Artifact Emission

### F.1 AuditEvent Emission

| Event | Trigger | Required Fields |
|---|---|---|
| `M49:audit:scoring-complete` | All candidate diagnoses scored | `patient_id`, `timestamp`, `mkg_results_ref`, `candidate_count`, `scoring_version`, `prevalence_adjustment_applied` (boolean) |
| `M49:audit:ranking-complete` | Diagnoses sorted by score | `patient_id`, `timestamp`, `top_score`, `second_score`, `score_gap`, `ranked_count` |
| `M49:audit:output-size-selected` | Single vs. top-3 decision made | `patient_id`, `timestamp`, `decision` (single/top_3), `score_gap`, `threshold_applied`, `rationale_trace` |
| `M49:audit:final-output-emitted` | Complete output bundle assembled and (if ARGL opted in) adversarially validated | `patient_id`, `timestamp`, `output_type` (single/top_3), `diagnosis_ids[]`, `argl_decision_record_ref` (if applicable), `module_version` |
| `M49:audit:argl-rejection` | ARGL rejects one or more claims from M49 output | `patient_id`, `timestamp`, `rejected_diagnosis_ids[]`, `argl_decision_record_ref`, `fallback_action` (reduced output / no-confident-opinion) |
| `M49:audit:evidence-attached` | Citations linked to output diagnoses | `patient_id`, `timestamp`, `diagnosis_id`, `citation_count`, `citation_pointers[]`, `contribution_ranking_ref` |
| `M49:audit:prevalence-adjusted` | AdjustForPrevalence applied to a candidate | `patient_id`, `timestamp`, `diagnosis_id`, `pre_score`, `post_score`, `adjustment_source_ref` |

### F.2 Provenance Emission

| Provenance Record | Connects | FHIR Resource Type |
|---|---|---|
| `M49:prov:scores-from-mkg` | `MKG_results` snapshot -> `diagnosis_score` (per diagnosis) | Provenance |
| `M49:prov:ranking-from-scores` | All `diagnosis_score` values -> `ranked_diagnoses[]` | Provenance |
| `M49:prov:output-from-ranking` | `ranked_diagnoses[]` + output-size-decision -> `final_output` | Provenance |
| `M49:prov:citations-from-evidence` | MKG `source_citation_pointer` values -> `evidence_citations[]` (per diagnosis) | Provenance |
| `M49:prov:contribution-from-weights` | Per-evidence-node weight computations -> `evidence_contribution_ranking[]` | Provenance |
| `M49:prov:prevalence-adjustment` | `diagnosis_score` (pre) + `prevalence_or_rarity_metadata` -> `diagnosis_score` (post) | Provenance |
| `M49:prov:argl-validation` | M49 output bundle + ARGL decision record -> `final_output` (post-ARGL) | Provenance |

---

## G. V6 Consumer Contract

| V6 Consumer | What It Reads | Contract Reference | Addendum Satisfies? |
|---|---|---|---|
| M63 (GBDC) | DerivationChain steps, uncertainty carriers, constraint carriers | M63 SS2, SS5 | Partial -- steps defined and pointer-formatted; uncertainty is NOT_PROVIDED for all scoring outputs (correct per current state: M49 emits no bounds or intervals); 3 input pointer groups MISSING (G-01, G-02, G-03) |
| M64 (FUDD) | `final_output` as context for uncertainty-aware disclosure | M64 input contract | Yes -- `M49:ra:final-output` pointer is available; uncertainty carriers are NOT_PROVIDED (M64 will carry that status through) |
| M67 (ARGL) | M49 output bundle for adversarial validation | M67 integration contract | Yes -- ARGL opt-in declared; integration point, payload, and result handling defined |
| M68 (ICM) | `ranked_diagnoses[]`, `final_output` as input layer | M68 stack placement | Yes -- both pointers available |
| Patient-facing UI (M24/M43) | `final_output`, `evidence_citations[]`, `evidence_contribution_ranking[]` | UI rendering contract | Yes -- all output pointers available; ARGL validation ensures quality gate before patient exposure |
| Clinician review surface | `ranked_diagnoses[]`, `diagnosis_score`, full evidence breakdown, ARGL decision record | Clinician audit contract | Yes -- all pointers available; audit trail complete |
| M48 (Continuous Learning) | Scoring performance data, ARGL rejection logs | M48 feedback loop contract | Yes -- audit events capture scoring details and ARGL rejections for feedback analysis |

---

## H. Gap Register

| Gap ID | V6 Requirement | Why Addendum Cannot Satisfy | Resolution Path |
|---|---|---|---|
| G-01 | M63 SS3.1 Trace Integrity: every input must be pointer-backed or explicitly MISSING | `MKG_results`, `candidate_diagnoses[]`, and `evidence_list[]` arrive as transient payloads from the MKG reasoning engine without artifact IDs. M49 cannot create pointer-backed input references for data it does not own. | MKG must register its output as a pointer-backed artifact with a snapshot ID. Until then, Steps 1-3 are MISSING and the chain is TRACE_PARTIAL. |
| G-02 | M63 SS3.2 Support Disclosure: citation pointers should be resolvable artifact references | Some MKG evidence nodes carry resolvable citation pointers (DOIs, guideline IDs); others carry only descriptive metadata (source_type, relevance_score) without a resolvable external reference. M49 passes through whatever MKG provides. | MKG evidence node standardization: all source_citation_pointers must resolve to a registered artifact (MKE knowledge object, DOI, or explicit NOT_RESOLVABLE marker). This is an MKG/MKE workstream, not M49. |
| G-03 | M63 SS3.1 Trace Integrity: input pointer for prevalence metadata | `prevalence_or_rarity_metadata` is an optional transient field without artifact registration. When present, it lacks provenance. | Epidemiological data source must register prevalence metadata as a pointer-backed artifact. Low priority -- field is optional and prevalence adjustment is optional. |
| G-04 | M63 SS5.1 Uncertainty: DEGRADATION_STATE carrier when evidence is sparse | M49 currently does not distinguish between rich-evidence and sparse-evidence computations. Defining a density threshold for degradation detection would introduce a new variable, which the addendum MUST NOT do. | Tier 4 rewrite workstream: define evidence density thresholds, emit DEGRADATION_STATE carrier when density is below threshold. Requires new variable definition (out of addendum scope). |
| G-05 | M63 SS5.1 Uncertainty: CONFIDENCE_INTERVAL for diagnosis_score | `diagnosis_score` is a bare scalar with no bounds or interval metadata. Emitting a confidence interval would require computing variance across the evidence set, which is new logic. | Tier 4 rewrite: add score variance computation to the weighting algorithm. Not an addendum change -- requires core logic extension. |

---

## I. Implementation Checklist

| Item | Status | Notes |
|---|---|---|
| Output artifact pointers defined | Done | B.1 complete -- 6 outputs registered |
| Input traceability mapped | Done | B.2 complete -- all inputs MISSING or PARTIAL; 3 gaps registered |
| Transformation steps registered | Done | B.3 complete -- 10 steps; Steps 1-3 have MISSING inputs, Step 7 has PARTIAL inputs |
| Uncertainty carriers defined or NOT_PROVIDED declared | Done | C.1 complete -- all scoring outputs NOT_PROVIDED; citations N/A |
| Constraint carriers defined or NOT_PROVIDED declared | Done | D.1 complete -- 5 constraints, all require new emission |
| ARGL opt-in status declared | Done | OPT_IN with full integration contract |
| FHIR audit artifacts specified | Done | F.1 (7 events) / F.2 (7 provenance records) complete |
| V6 consumer contracts validated | Done | G table complete -- 7 consumers mapped |
| Gap register complete | Done | 5 gaps registered |
| Addendum reviewed against V5.2 spec (no core logic changes) | Pending | G-04 and G-05 flagged as Tier 4 rewrite items; no core logic introduced by this addendum |

---

## J. Acceptance Tests

| ID | Test | Expected Result |
|---|---|---|
| AT-01 | M49 produces identical `ranked_diagnoses[]`, `final_output`, `diagnosis_score`, `evidence_citations[]`, `evidence_contribution_ranking[]` with and without addendum emission layer active | Core logic unchanged; emission is additive only |
| AT-02 | M63 can construct a DerivationChain through M49 using emitted artifacts | Steps 5-6, 8-10 are POINTER_BACKED; Steps 1-3 are MISSING (G-01); Step 4 is MISSING when prevalence metadata absent (G-03); Step 7 is PARTIAL (G-02) |
| AT-03 | Uncertainty carriers match M63 SS5.1 enum types | All NOT_PROVIDED -- no invented carrier types; citations marked N/A (non-probabilistic) |
| AT-04 | Constraint carriers match M63 SS5.2 enum types | GOVERNANCE_GATE (output size selection, prevalence adjustment), INVARIANT_ENFORCEMENT (concise output, evidence-backed, MKG-only input) -- all from closed SS5.2 enum |
| AT-05 | ARGL integration follows M67 contract | Decision record consumed; rejected claims not propagated to patient-facing output; fallback behavior uses existing output paths only |
| AT-06 | Existing downstream V5.2 consumers (MKG feedback loop, M48) receive unchanged outputs | No breaking changes to M49's output contract; emission layer is additive |
| AT-07 | ARGL rejection of single-diagnosis output triggers correct fallback | If the sole diagnosis is rejected, M49 emits either a reduced set from remaining candidates or a "no confident opinion" result -- never an unvalidated diagnosis to the patient |
| AT-08 | Output size decision constraint carrier accurately records the gap-based selection rationale | Constraint carrier includes score_gap, threshold_applied, and decision; values match the audit event `M49:audit:output-size-selected` |
| AT-09 | Evidence citations in final output all have provenance pointers to MKG source_citation_pointers | `M49:prov:citations-from-evidence` records connect each citation to its MKG source; PARTIAL citations (G-02) are marked explicitly |

---

*End of V5.2 M49 V6 Governance Addendum v1.0*
