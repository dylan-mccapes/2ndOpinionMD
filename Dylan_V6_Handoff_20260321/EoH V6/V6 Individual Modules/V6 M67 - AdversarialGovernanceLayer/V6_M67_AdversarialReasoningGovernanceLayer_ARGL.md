# **V6 M67 — Adversarial Reasoning Governance Layer (ARGL)**

**Multi-Agent Decomposition, Evidence Provenance Enforcement, and Mandatory Falsification for Clinical AI Output Quality Assurance**

**Version:** 1.0 — Initial specification. Establishes the adversarial governance architecture, evidence tagging system, rebinding contract, mandatory falsification protocol, vertical-only synthesis invariant, and agent roster with deterministic arbitration workflow.

---

## **Purpose (3–5 sentences)**

Module 67 (ARGL) provides a **single, adversarial command layer** that orchestrates specialized reasoning agents and prevents weak, unsupported, or hallucinated conclusions from propagating through the EoH pipeline. No existing EoH module systematically governs the **quality of reasoning itself** — modules govern patient state (M1–M6), suppression (M8/M9), evidence (MKE), and clinical outputs (M13–M15), but no module asks whether the reasoning chain connecting inputs to outputs is internally consistent, evidence-grounded, and adversarially tested. ARGL fills this gap by enforcing **computable evidence provenance** (every claim must carry typed, traceable evidence tags), **contextual validity rebinding** (every conclusion must re-verify its relevance to the current patient state before emission), and **mandatory falsification** (at least one independent adversarial evaluation must attempt to break the leading conclusion before it is published). ARGL operates as a **meta-governance layer** positioned above individual reasoning modules and below the user-facing response layer; it does not generate clinical content, propose diagnoses, or interact with patients. (New logic; V6 only.)

---

## **Foundational Concept: Adversarial Reasoning Governance**

### **Definition**

**Adversarial Reasoning Governance** is a quality assurance discipline in which the system's own reasoning outputs are subjected to structured, independent, hostile evaluation before being permitted to propagate downstream. The term "adversarial" here is used in its engineering sense (as in adversarial testing, adversarial validation, or red-teaming) — not in the sense of hostility toward the patient or clinician.

### **Clinical Precedent**

This architecture formalizes patterns already present in high-stakes clinical practice:

* **Tumor boards** — independent specialists each evaluate the same patient data and present their conclusions before a synthesizing discussion. No single specialist's view is accepted without challenge.
* **Morbidity and mortality conferences** — structured retrospective adversarial review of clinical decisions to identify reasoning failures, premature closure, and evidence gaps.
* **Independent data safety monitoring boards (DSMBs)** — entities structurally separated from trial investigators whose function is to challenge the leading interpretation of accumulating evidence.
* **GRADE evidence appraisal** — the Grading of Recommendations Assessment, Development and Evaluation framework, which requires explicit classification of evidence certainty (high/moderate/low/very low) and forces transparent acknowledgment of limitations. ARGL's typed tag system is a machine-readable analogue.
* **Differential diagnosis discipline** — the clinical practice of always asking "what else could this be?" before committing to a working diagnosis, formalized here as a system invariant rather than an optional cognitive habit.

### **Why This Module Is Necessary**

AI reasoning systems exhibit characteristic failure modes that human clinical reasoning also exhibits, but at greater speed and scale:

* **Premature closure** — locking onto an initial hypothesis and interpreting subsequent evidence as confirmatory (confirmation bias). In LLM-based systems, this manifests as fluency bias: outputs that sound coherent are treated as correct.
* **Hallucination** — generating claims that are linguistically plausible but factually unsupported. In clinical AI, hallucinated mechanism claims or fabricated citations are a patient safety risk.
* **Evidence laundering** — citing a source that does not actually support the claim being made, creating a false appearance of evidentiary support.
* **Narrative drift** — progressive departure from the original clinical question as the reasoning chain accumulates inferences upon inferences without re-verifying relevance to the patient's actual state.
* **Groupthink in multi-agent systems** — when agents coordinate horizontally (sharing intermediate conclusions), they converge prematurely and suppress dissenting signals, mimicking the clinical failure mode where team consensus overrides individual clinical judgment.

ARGL prevents these failure modes through architectural constraints rather than post-hoc review.

### **Canonical Statement**

> **"The system learns by being attacked internally before it ever speaks externally. Conclusions must survive adversarial evaluation — not merely be generated fluently."**

---

## **Scope**

### **In scope**

* Governance of multi-agent reasoning workflows across EoH modules that produce clinical interpretations, pattern detections, trajectory forecasts, or recommendation candidates.
* Enforcement of computable evidence provenance (typed evidence tags on all claims).
* Enforcement of contextual validity rebinding (outputs must bind to question, current patient state, and evidence set).
* Mandatory falsification protocol (at least one independent adversarial evaluation per reasoning chain before downstream propagation).
* Conflict surfacing (contradictory evidence must be preserved and reported, not averaged or suppressed).
* Vertical-only synthesis (specialized agents report upward; synthesis occurs only at the command layer).
* After-action learning (structured logging of reasoning failures, hallucination triggers, and evidence gaps for continuous improvement via M48).
* Agent lifecycle governance (scope, failure modes, stop conditions, and shutdown for every spawned reasoning agent).

### **Out of scope**

* Clinical content generation — ARGL does not generate diagnoses, treatment recommendations, biomarker interpretations, or patient-facing narratives (owned by M13–M15, M49, M53, M64, and MKE).
* Patient state computation — ARGL does not compute stability bands, stack levels, PSI scores, or other state variables (owned by M1–M6).
* Suppression policy — ARGL does not define or execute suppression rules (owned by M8/M9). ARGL may flag conclusions that should be evaluated by the suppression system but does not suppress them directly.
* MKE knowledge curation — ARGL does not curate, validate, or store medical knowledge (owned by MKE). ARGL consumes evidence from MKE and enforces provenance discipline on how that evidence is used in reasoning.
* Consent, privacy, or data minimization enforcement (owned by M26, M27, M34–M37).
* UI/UX rendering of ARGL outputs (owned by M24/M43).
* Tool discovery or construction (owned by M51/M52).

### **Relationship to V5.2**

ARGL is a **V6-only module** that does not modify any V5.2 logic. It consumes V5.2 module outputs as read-only inputs and produces governance artifacts (decision records, evidence maps, conflict ledgers, after-action logs) that downstream V5.2 and V6 modules may optionally consume. ARGL enforces reasoning quality constraints on V6 reasoning workflows (M53 PTM, M64 FUDD, Tool Library queries) and provides an integration contract for any V5.2 module that opts in to adversarial governance (e.g., M17 CIR, M18 MPA, M49 diagnostic scoring).

---

## **Placement in the EoH Stack**

```
┌─────────────────────────────────────────────┐
│           User-Facing Response Layer         │
│              (M24 / M43 / UI)                │
├─────────────────────────────────────────────┤
│      M67 — Adversarial Reasoning             │
│      Governance Layer (ARGL)                 │
│  ┌──────────────────────────────────────┐   │
│  │  Command Arbiter                      │   │
│  │  (arbitration + decision record)      │   │
│  ├──────────────────────────────────────┤   │
│  │  Specialized Agents (vertical only)   │   │
│  │  Retrieval │ Reasoning │ QC │ Safety  │   │
│  └──────────────────────────────────────┘   │
├─────────────────────────────────────────────┤
│     Clinical Reasoning Modules               │
│  M17 CIR │ M18 MPA │ M49 Dx │ M53 PTM │    │
│  M64 FUDD │ Tool Library                     │
├─────────────────────────────────────────────┤
│     Patient State & Safety Modules           │
│  M1-M6 │ M8/M9 │ M20 │ M21 Vault           │
├─────────────────────────────────────────────┤
│     MKE (Medical Knowledge Engine)           │
└─────────────────────────────────────────────┘
```

**Upstream inputs:** Reasoning chain outputs from clinical modules (claims, evidence citations, confidence scores, intermediate inferences); current patient state snapshot (from M56 Patient Vision); MKE evidence payloads.

**Downstream outputs:** Sterile decision record (accepted/rejected claims with reasons); evidence map (claim-to-tag bindings); conflict ledger; uncertainty bounds; after-action log.

**Side effects:** After-action learning telemetry to M48; counterexample bank entries; retrieval pattern logs.

---

## **Invariants (Binding Rules)**

Each invariant is testable and must be enforced by runtime gates. Invariants are grouped by category and assigned identifiers for traceability.

### **Category A — Containment & Control**

**I-A1. No Agent Publishes Conclusions**
Specialized agents may not emit final answers, patient-facing outputs, or clinician-facing recommendations. They output structured reports only, in the standardized schema defined in Section D. All synthesis occurs at the Command Arbiter level.

*Test:* Inject an agent output directly into the downstream pipeline without passing through arbitration. The pipeline must reject it.

**I-A2. Containment Before Invocation**
No new agent, tool, model, or external service may be invoked without:
- Defined scope (what it is tasked to do and not do)
- Expected output schema
- Enumerated failure modes
- Stop conditions (when to halt)
- Rollback/abort plan (what happens if it fails or times out)

*Test:* Attempt to invoke an agent without a complete containment record. The command layer must refuse invocation.

**I-A3. Deterministic Arbitration**
The Command Arbiter must produce a reproducible decision record: why each claim was accepted, rejected, or held, under what rules, and with what evidence. Identical inputs, agent reports, and arbiter version must produce identical decisions.

*Test:* Replay a complete agent report set through the arbiter twice with the same version. Decision records must be identical.

### **Category B — Evidence & Provenance**

**I-B1. Every Claim Must Carry a Tag**
A claim without at least one evidence tag is classified as noise and cannot appear in the final output. Claims explicitly marked as `ASSUMPTION` or `UNKNOWN` are permitted but must carry those type markers and cannot be treated as evidenced assertions.

*Test:* Inject an untagged claim into the arbitration pipeline. The final output must omit it (or mark it explicitly as ASSUMPTION/UNKNOWN with a flag).

**I-B2. Tags Are Typed**
Every evidence tag must declare its type from the controlled vocabulary: `OBSERVATION | CITATION | MEASUREMENT | INFERENCE | ASSUMPTION | TEST | RISK | UNKNOWN`. Untyped tags are invalid.

*Test:* Submit a claim with a tag lacking a `tag_type` field. The validation gate must reject it.

**I-B3. Evidence Must Support the Specific Claim**
A tag whose source material does not support the specific claim it is attached to triggers rejection and logging. Evidence laundering (citing a source that discusses the topic but does not support the precise assertion) is treated as a validation failure, not merely a quality issue.

*Test:* Attach a citation to a claim where the cited source contradicts or is irrelevant to the claim. The Noise Agent or Command Arbiter must flag and reject the claim.

### **Category C — Rebinding & Contextual Validity**

**I-C1. Rebind or Discard**
Every agent output must bind to three anchors before it can be accepted:
1. **The question** — which specific sub-question or clinical query does this output address?
2. **The current patient state** — is this output valid given the patient's current stability band, medication regimen, suppression status, and temporal context?
3. **The evidence set** — which specific evidence tags support this output, and are they still valid (not retracted, superseded, or contradicted by newer data)?

If any anchor fails, the output is discarded or returned for repair.

*Test:* Submit an agent report where `rebind_check.binds_to_state = false`. The arbiter must discard it.

**I-C2. State Changes Are Logged**
If any agent report implies a change to a belief, probability, or state variable, it must explicitly declare: what changed, from what value to what value, which evidence tags support the change, and the confidence delta. Implicit state changes are prohibited.

*Test:* Submit an agent report that changes a probability estimate without a state-change declaration. The arbiter must flag it as a validation failure.

### **Category D — Anti-Hallucination & Anti-Groupthink**

**I-D1. Mandatory Falsification**
At least one dedicated falsification evaluation must attempt to break the leading conclusion before any output is published downstream. The arbiter must refuse to publish if no falsification report is present.

*Test:* Disable the falsification agent and attempt to publish. The pipeline must hard-block publication with a logged reason.

**I-D2. No Horizontal Collusion**
Agents may not reference other agents' outputs as evidence. Agents may reference only:
- Primary sources (literature, data, measurements)
- MKE knowledge objects
- Explicitly tagged assumptions
- The original patient data and state

All synthesis of agent outputs occurs exclusively at the Command Arbiter level.

*Test:* Submit an agent report containing a tag with `source_id` pointing to another agent's report. The validation gate must reject it.

**I-D3. Two-Stage Retrieval**
Evidence retrieval must proceed in at least two stages: broad recall first (maximize coverage), then focused precision (extract specific supporting evidence), followed by canonicalization/deduplication. Single-pass retrieval is prohibited for any clinical reasoning chain unless explicitly justified and logged.

*Test:* Audit a reasoning chain's retrieval log. It must show at least two retrieval stages with distinct query strategies.

### **Category E — Uncertainty Discipline**

**I-E1. Conflicts Must Surface**
If evidence sources disagree, the output must:
- State the disagreement explicitly
- Preserve competing interpretations when unresolved
- Bound confidence to reflect the conflict (no premature certainty collapse)

*Test:* Provide two sources with contradictory findings on the same question. The final output must report the disagreement and provide bounded conclusions.

**I-E2. Unknowns Must Remain Unknown**
The system must not fill evidence gaps with narrative completion, plausible-sounding inference, or implied certainty. When evidence is absent, the output must state what is unknown and identify what data would be needed to resolve the gap.

*Test:* Ask a question where the evidence base is empty. The output must contain explicit `UNKNOWN` markers and identify the missing data, not a fabricated answer.

### **Category F — Safety & Boundary Enforcement**

**I-F1. Sterile Output Is Canonical**
All formal outputs consumed by downstream EoH modules must be in sterile, mechanistic language. No metaphorical, teleological, or intent-attributing language may appear in formal outputs. Internal documentation and design artifacts may use metaphorical overlays if explicitly marked as non-canonical.

*Test:* Run the final output through a terminology validator. No terms from the mythic overlay vocabulary may appear.

**I-F2. No Clinical Recommendations from ARGL**
ARGL governs reasoning quality. It does not generate clinical recommendations, treatment suggestions, or diagnostic conclusions. If ARGL's adversarial evaluation reveals that the reasoning chain it is evaluating produces an unsafe conclusion, ARGL flags and blocks the conclusion — it does not substitute its own.

*Test:* Verify that no ARGL output contains recommendation-class content (diagnosis, treatment, medication suggestion).

**I-F3. Honest Operational Limitations**
The Command Arbiter must track and surface operational limitations affecting the current reasoning chain: missing data sources, unavailable tools, time constraints, retrieval failures, or agent timeouts. These limitations must appear in the decision record.

*Test:* Induce a retrieval timeout mid-chain. The decision record must log the limitation and adjust confidence bounds accordingly.

---

## **Agent Roster**

ARGL agents are narrow, specialized, and disposable. They are spawned for a specific reasoning task and terminated upon completion. They report upward only. They do not negotiate with each other, share intermediate conclusions, or self-authorize outputs.

### **Shared Constraints (All Agents)**

* Must comply with I-B1 through I-B3 (evidence tagging)
* Must comply with I-C1 and I-C2 (rebinding and state-change logging)
* Must produce output in the standardized Agent Report Schema (Section D)
* Must declare stop conditions and failure modes at invocation time
* Must not message users, patients, or clinicians directly
* Must not mutate patient state or EoH module state unless explicitly authorized by the Command Arbiter

### **Retrieval & Indexing Agents**

**A1 — Scout Agent (Broad Retrieval)**

| Field | Value |
|---|---|
| **Mission** | Maximize recall; find candidate evidence sources and surface coverage gaps for the clinical question. |
| **Allowed tools** | Broad search against MKE indices, internal knowledge graph queries, metadata scans, external literature APIs (if authorized). |
| **Output** | Coverage map: which topics/sub-questions are well-sourced vs. under-sourced. Candidate source list with provenance metadata. |
| **Failure modes** | Topical drift (retrieves irrelevant material); source flooding (returns too many low-quality sources); stale source inclusion (retrieves superseded evidence). |
| **Stop conditions** | Coverage saturates (marginal new sources fall below threshold); time budget exhausted; sub-question coverage map is complete. |

**A2 — Harvester Agent (Focused Retrieval)**

| Field | Value |
|---|---|
| **Mission** | Precision extraction from the most promising sources identified by A1. Extract the minimal supporting evidence for each candidate claim. |
| **Allowed tools** | Targeted search, document-level access, passage extraction with exact locators. |
| **Output** | Evidence extractions with locators (page/section/paragraph), typed tags, and relevance scores. Must include best counterevidence found. |
| **Failure modes** | Cherry-picking (selects only confirmatory evidence); missing counterevidence; over-extraction (returns too much, diluting signal). |
| **Stop conditions** | Top candidate claims each have ≥2 independent supporting extractions, or remaining sources are exhausted, or are explicitly marked UNKNOWN. |

**A3 — Librarian Agent (Canonicalization & Deduplication)**

| Field | Value |
|---|---|
| **Mission** | Deduplicate retrieved sources, resolve identity (same study reported in multiple venues), build a canonical citation set, and rank source trustworthiness. |
| **Allowed tools** | Similarity clustering, DOI/PMID matching, source-quality heuristics, recency checks. |
| **Output** | Canonical source set with one "blessed" reference per unique evidence item; deduplication log; source quality annotations. |
| **Failure modes** | Merges distinct studies with similar titles; over-prunes minority or dissenting sources; misidentifies preprint vs. peer-reviewed version. |
| **Stop conditions** | Canonical set is stable across two deduplication passes. |

### **Reasoning Agents**

**A4 — Signal Agent (Claim Extraction & Typing)**

| Field | Value |
|---|---|
| **Mission** | Separate observations from interpretations in the evidence base. Produce typed claim candidates with explicit classification. |
| **Allowed tools** | Structured parsing, controlled summarization, claim decomposition. |
| **Output** | Claim objects with `claim_type` (OBSERVATION / INFERENCE / ASSUMPTION), evidence tags, and confidence scores. |
| **Failure modes** | Implicit inference disguised as observation; missing qualifiers; splitting too aggressively (fragmenting coherent evidence). |
| **Stop conditions** | All candidate claims are typed, tagged, or explicitly marked UNKNOWN. |

**A5 — Mechanist Agent (Constraint Verification)**

| Field | Value |
|---|---|
| **Mission** | For each candidate conclusion, enumerate: what must be biologically/mechanistically true for this conclusion to hold? What are the necessary preconditions, and are they met? |
| **Allowed tools** | Structured reasoning, consistency checks against known biological constraints, MKE pathway queries. |
| **Output** | Constraint list per conclusion: preconditions, whether each is evidenced or assumed, and what would falsify the mechanistic chain. |
| **Failure modes** | Over-formalization (demands constraints that are not clinically relevant); false necessity (treats a common but non-essential pathway as required). |
| **Stop conditions** | Each candidate conclusion has a constraint set with evidenced/assumed status for each precondition. |

**A6 — Temporal Agent (Timeline & Causal Ordering)**

| Field | Value |
|---|---|
| **Mission** | Verify temporal consistency of the reasoning chain. Check that claimed causal relationships respect temporal ordering, that evidence time-windows align with the patient's current state, and that "what changed when" is documented. |
| **Allowed tools** | Timeline extraction, sequence validation, temporal overlap detection. |
| **Output** | Timeline consistency report: ordering violations, temporal gaps, confounders, and causal ordering assessments. |
| **Failure modes** | Assumes causality from temporal sequence (post hoc fallacy); ignores confounders; treats stale temporal data as current. |
| **Stop conditions** | Timeline is verified as consistent, or all inconsistencies are explicitly flagged with evidence. |

**A7 — Systems Agent (Interaction & Second-Order Effects)**

| Field | Value |
|---|---|
| **Mission** | Check for interactions and second-order effects across the reasoning chain — particularly where one conclusion affects the validity of another, or where interventions interact (drug-drug, drug-nutrient, condition-condition). |
| **Allowed tools** | Systems mapping, dependency graph analysis, interaction databases (via MKE). |
| **Output** | Interaction map: identified interactions with evidence tags, severity classification, and confidence. |
| **Failure modes** | Speculative cascading (inventing interactions without evidence); over-warning (flagging clinically irrelevant interactions). |
| **Stop conditions** | Interactions enumerated with confidence and evidence tags, or explicitly marked as not evaluated (with reason). |

### **Quality Control Agents**

**A8 — Noise Agent (Hallucination & Rhetoric Detection)**

| Field | Value |
|---|---|
| **Mission** | Detect untagged claims, evidence mismatches, rhetorical drift, soft-language certainty ("likely," "suggests" used without evidence), and schema violations in agent reports. |
| **Allowed tools** | Schema validation, tag completeness checks, claim-evidence alignment scoring. |
| **Output** | Violation report: type, location, severity, and recommended fix or rejection. |
| **Failure modes** | False positives (flags legitimate hedging as rhetoric); over-skepticism (rejects well-supported claims on technicality). |
| **Stop conditions** | All violations either fixed (in repair loop) or flagged for arbiter decision. |

**A9 — Falsifier Agent (Hostile Review)**

| Field | Value |
|---|---|
| **Mission** | Actively attempt to invalidate the leading conclusion. Search for counterexamples, alternative hypotheses, missing evidence, and unexamined assumptions. The goal is invalidation, not agreement. |
| **Allowed tools** | Adversarial search, counterfactual reasoning, alternative hypothesis generation, stress-testing against edge cases. |
| **Output** | Attack report: each attack with evidence tags, outcome (conclusion broken / conclusion survived with documented reason), and alternative hypotheses with their own evidence assessment. |
| **Failure modes** | Contrarianism without evidence (attacking for the sake of attacking); irrelevant attacks (testing conditions that don't apply to this patient); missing the actual weakness while testing peripheral ones. |
| **Stop conditions** | Either (a) the conclusion breaks and an alternative is documented, or (b) all evidence-based attacks fail with documented reasons and evidence tags. |

**A10 — Safety Agent (Boundary & Overreach Control)**

| Field | Value |
|---|---|
| **Mission** | Verify that the reasoning chain's conclusions respect EoH governance boundaries: no unauthorized clinical recommendations, no teleological/intent language in formal outputs, no scope violations, no overreach beyond the module's authority. Cross-references against M8/M9 suppression criteria and M57 clinical invariants. |
| **Allowed tools** | Policy/rule checks, boundary validation, scope verification against module definitions. |
| **Output** | Boundary check report: pass/fail per boundary criterion, with violation details and recommended action. |
| **Failure modes** | Blocks legitimate benign content; misses subtle scope violations; applies overly conservative interpretation of boundaries. |
| **Stop conditions** | All boundary checks evaluated; output is within bounds or blocked with specific reasons. |

### **Synthesis Support Agents**

**A11 — Translator Agent (Sterile Output Enforcement)**

| Field | Value |
|---|---|
| **Mission** | Ensure that all formal outputs are in sterile, mechanistic language per I-F1. If internal documentation uses metaphorical overlays, verify they are explicitly marked as non-canonical. Produce the canonical sterile version of any output that contains non-sterile language. |
| **Allowed tools** | Terminology mapping, rewrite, style validation. |
| **Output** | Sterile output text; translation log showing any terms replaced. |
| **Failure modes** | Leaks metaphorical language into formal output; over-sanitizes to the point of losing clinical meaning. |
| **Stop conditions** | Sterile output passes terminology validation and preserves all clinical content from the source. |

**A12 — Summarizer Agent (Compression Without Loss)**

| Field | Value |
|---|---|
| **Mission** | Compress the accepted claim set into a minimal, correct conclusion with uncertainty bounds. Must preserve all caveats, conflict flags, and UNKNOWN markers. |
| **Allowed tools** | Structured summarization, outline-to-prose conversion, caveat preservation checks. |
| **Output** | Compressed conclusion text with traceable links to accepted claims and evidence tags. |
| **Failure modes** | Drops caveats during compression; merges distinct claims into ambiguous summaries; introduces language not present in accepted claims. |
| **Stop conditions** | Summary is traceable to every accepted claim and evidence tag; no caveat or UNKNOWN marker is lost. |

---

## **Data Structures**

### **D1. Evidence Tag Object (Typed Provenance)**

An Evidence Tag is a typed, machine-readable reference that binds a claim to its evidentiary basis. Every tag must be resolvable to a specific source and location.

**Required fields:**

| Field | Type | Description |
|---|---|---|
| `tag_id` | string (UUID) | Unique identifier for this tag instance. |
| `tag_type` | enum | One of: `OBSERVATION`, `CITATION`, `MEASUREMENT`, `INFERENCE`, `ASSUMPTION`, `TEST`, `RISK`, `UNKNOWN`. |
| `source_id` | string | Resolvable identifier: DOI, PMID, MKE knowledge object ID, internal dataset ID, FHIR resource reference, or URL. |
| `locator` | string | Specific location within source: page number, section heading, paragraph index, table cell, data field path, or quote span. |
| `timestamp` | ISO 8601 datetime | When the evidence was retrieved or observed. |
| `notes` | string (optional) | Brief annotation on relevance or limitations. |

### **D2. Claim Object**

A Claim is a discrete assertion produced by an agent or accepted by the arbiter. Claims are the atomic units of reasoning governance.

**Required fields:**

| Field | Type | Description |
|---|---|---|
| `claim_id` | string (UUID) | Unique identifier. |
| `claim_text` | string | The assertion in sterile language. |
| `claim_type` | enum | One of: `OBSERVATION`, `INFERENCE`, `ASSUMPTION`, `UNKNOWN`. |
| `evidence_tags[]` | array of Tag references | Must be non-empty unless `claim_type` = `ASSUMPTION` or `UNKNOWN`. |
| `confidence` | float (0.0–1.0) | Calibrated confidence reflecting evidence strength and conflict status. |
| `failure_modes[]` | array of strings | How this claim could be wrong. |
| `conflicts_with[]` | array of claim_id references | Claims that contradict this one. |
| `answers[]` | array of strings | Which sub-question(s) this claim addresses (for rebinding verification). |

### **D3. Agent Report Schema**

All agents must produce reports in this standardized schema so the Command Arbiter can process them deterministically.

```json
{
  "agent_id": "string (agent type + instance UUID)",
  "mission": "string (tasked objective)",
  "stop_conditions_hit": ["string (which stop conditions were met)"],
  "findings": ["string (summary observations)"],
  "claims": [
    {
      "claim_id": "UUID",
      "claim_text": "string",
      "claim_type": "OBSERVATION | INFERENCE | ASSUMPTION | UNKNOWN",
      "evidence_tags": [
        {
          "tag_id": "UUID",
          "tag_type": "OBSERVATION | CITATION | MEASUREMENT | INFERENCE | ASSUMPTION | TEST | RISK | UNKNOWN",
          "source_id": "string",
          "locator": "string",
          "timestamp": "ISO 8601",
          "notes": "string (optional)"
        }
      ],
      "confidence": 0.0,
      "failure_modes": ["string"],
      "conflicts_with": ["claim_id"],
      "answers": ["sub-question reference"]
    }
  ],
  "conflicts": ["string (contradictions found across claims or sources)"],
  "recommended_next_queries": ["string (suggested follow-up if evidence is thin)"],
  "rebind_check": {
    "binds_to_question": true,
    "binds_to_state": true,
    "binds_to_evidence": true,
    "notes": "string (explanation if any anchor fails)"
  },
  "operational_limitations": ["string (retrieval failures, timeouts, missing tools)"]
}
```

**Extension for A8 (Noise Agent):** Add `violations[]` field:
```json
{
  "violations": [
    {
      "violation_type": "UNTAGGED_CLAIM | EVIDENCE_MISMATCH | RHETORICAL_DRIFT | SCHEMA_VIOLATION | SOFT_CERTAINTY",
      "location": "string (claim_id or report section)",
      "description": "string",
      "severity": "CRITICAL | WARNING | INFO",
      "recommended_action": "REJECT | REPAIR | FLAG"
    }
  ]
}
```

### **D4. Rebinding Contract**

An agent report passes the rebinding gate if and only if ALL of the following hold:

1. Every `claim_text` maps to at least one `evidence_tag` (unless `claim_type` = `ASSUMPTION` or `UNKNOWN`).
2. Every `evidence_tag` has a resolvable `source_id` + `locator`.
3. Every claim maps to at least one sub-question in `answers[]`.
4. Any state update includes a `from → to` declaration with supporting evidence tags.
5. The `rebind_check` object reports `true` for all three anchors.

**If any condition fails:** the report is either discarded (hard fail) or returned to the originating agent for a single repair attempt (soft fail), at the Command Arbiter's discretion. A report that fails rebinding twice is discarded with a logged reason.

### **D5. Decision Record (Command Arbiter Output)**

The arbiter produces a structured decision record after processing all agent reports.

**Required sections:**

| Section | Content |
|---|---|
| `accepted_claims[]` | Claims that passed all gates, with evidence tag references and acceptance rationale. |
| `rejected_claims[]` | Claims that failed one or more gates, with rejection reason per claim. |
| `conflict_ledger[]` | Explicit contradictions: which claims conflict, what evidence supports each side, and whether the conflict is resolved or preserved. |
| `final_conclusion` | Sterile, bounded conclusion text with uncertainty qualifiers. |
| `uncertainty_bounds` | What is known, what is unknown, what would change the conclusion if learned. |
| `operational_limitations` | Data gaps, retrieval failures, agent timeouts, or tool unavailability that affected this reasoning chain. |
| `falsification_summary` | Summary of the falsification report: what attacks were attempted, which succeeded/failed, and why. |
| `after_action_notes` | What failed, what hallucinated, what tags were missing, what should improve next time. |

---

## **Workflow / Protocol (Deterministic)**

### **Phase 0 — Invocation**

ARGL is invoked when any EoH reasoning module produces a clinical interpretation, pattern detection, trajectory forecast, or recommendation candidate that will propagate downstream. Invocation may be:
- **Automatic:** triggered by any module output that carries clinical weight (configurable per module).
- **On-demand:** requested by M24 (Interface Hub), M19 (QA), or a clinician via M58 (HITL Interruption Controller).

### **Phase 1 — Briefing (Command Arbiter)**

The Command Arbiter receives:
- **The question:** what clinical question or reasoning task is being evaluated?
- **The context/state:** current patient state snapshot (from M56 or upstream modules).
- **Constraints:** time budget, allowed sources, available tools, safety boundaries.
- **The candidate output:** the reasoning chain or conclusion to be evaluated.

The Command Arbiter produces:
- **Task decomposition:** sub-questions to be evaluated.
- **Agent tasking plan:** which agents to invoke, in what order, with what missions.
- **Acceptance criteria:** what counts as "sufficiently supported" for this specific question.
- **Stop conditions:** global time/resource limits for the evaluation.

### **Phase 2 — Agent Invocation (Vertical Only)**

Agents are invoked per the tasking plan. Default invocation order:

1. **Retrieval stage:** A1 Scout → A2 Harvester → A3 Librarian
2. **Reasoning stage:** A4 Signal → A5 Mechanist → A6 Temporal → A7 Systems (as applicable)
3. **Quality control stage:** A8 Noise → A9 Falsifier → A10 Safety
4. **Synthesis stage:** A11 Translator → A12 Summarizer

All agents receive their mission scope, the standardized report schema, and their specific stop conditions. Agents do not see other agents' outputs (I-D2 enforcement).

**Gate G-1 (Retrieval Gate):** After Phase 2 retrieval agents complete, the Command Arbiter verifies that the evidence base is sufficient to proceed. If coverage is critically thin, the arbiter may authorize a second retrieval cycle with modified queries before proceeding to reasoning agents.

### **Phase 3 — Reasoning (Typed Claims + Constraints)**

Reasoning agents produce typed claims with evidence tags. 

**Gate G-2 (Inference Gate):** Any inference (`claim_type = INFERENCE`) that lacks linked observations is reclassified as `ASSUMPTION` or rejected. The gate enforces I-B1 (every claim carries a tag) at the reasoning stage before hostile review.

### **Phase 4 — Hostile Review (Mandatory)**

The Falsifier Agent (A9) receives:
- The set of leading conclusions/claims from reasoning agents
- Access to the same evidence base (independently retrieved per I-D2)
- The mandate to invalidate

**Gate G-3 (Falsification Gate):** The Command Arbiter checks that a falsification report exists and is non-trivial (not a rubber-stamp approval). If no falsification report is present, or the report is trivially empty, publication is hard-blocked per I-D1.

### **Phase 5 — Arbitration (Command Arbiter)**

The Command Arbiter processes all agent reports:

1. **Reject** claims violating I-B1 (no tag), I-B3 (evidence mismatch), or I-C1 (failed rebinding).
2. **Build the conflict ledger** — identify all explicit contradictions across agent reports and evidence sources (I-E1).
3. **Evaluate the falsification report** — if the conclusion was broken, document the alternative. If attacks failed, document why.
4. **Verify the falsification gate** — refuse to publish without a falsification report (I-D1).
5. **Produce the decision record** (D5 schema) with accepted claims, rejected claims, conflict ledger, bounded conclusion, uncertainty qualifiers, and after-action notes.

**This is not consensus. This is not averaging.** The arbiter applies deterministic rules to accept or reject claims. Where rules do not resolve a conflict, the conflict is preserved in the output.

### **Phase 6 — Output (Sterile Canonical)**

1. A11 Translator ensures I-F1 compliance (no metaphorical language in formal outputs).
2. A12 Summarizer compresses without losing caveats.
3. A10 Safety Agent validates boundaries one final time.

**Gate G-4 (Output Gate):** The final output must satisfy:
- All claims traceable to accepted evidence tags
- No unresolved I-F1 violations
- No clinical recommendations from ARGL itself (I-F2)
- Operational limitations documented (I-F3)

### **Phase 7 — After-Action Learning**

The Command Arbiter emits after-action telemetry:
- **To M48 (Continuous Learning):** structured learning record including reasoning failures, hallucination triggers, evidence gaps, and successful falsification attacks.
- **To the counterexample bank:** falsifier-generated adversarial cases for regression testing.
- **To retrieval pattern logs:** which queries yielded high signal, for future retrieval optimization.

---

## **Inputs (Data Objects / Fields)**

* `reasoning_chain_output` (from upstream clinical module): the candidate conclusion, intermediate claims, cited evidence, and confidence scores to be evaluated.
* `patient_state_snapshot` (from M56 Patient Vision or upstream state modules): current `stabilityBand`, `stackLevel`, `PSI`, `pauseFlag`, `pauseReason`, active medications, active conditions, and temporal context.
* `mke_evidence_payloads` (from MKE): knowledge objects, evidence summaries, and source metadata relevant to the clinical question.
* `invocation_context`: `invoking_module_id`, `question_text`, `constraint_set` (time budget, allowed sources, safety boundaries), `acceptance_criteria`.
* `suppression_state` (from M8/M9): current suppression flags and reasons relevant to the patient, consumed as context (ARGL does not execute suppression).

## **Outputs**

* `decision_record` (D5 schema): the complete arbitration result including accepted/rejected claims, conflict ledger, bounded conclusion, uncertainty bounds, falsification summary, and after-action notes.
* `evidence_map`: claim-to-tag binding table for the accepted claim set, consumable by downstream modules for explainability (M14) and audit (M21 Vault).
* `conflict_ledger`: standalone conflict record consumable by M19 QA and M48 Continuous Learning.
* `after_action_log`: structured learning telemetry consumable by M48.
* `counterexample_entries[]`: adversarial cases generated by A9, stored for regression testing.
* `argl_audit_events[]`: FHIR-compatible AuditEvent + Provenance records for every invocation, agent tasking, gate evaluation, and arbitration decision.

---

## **Governance / Constraints (Explicit Boundaries; No New Rules)**

* ARGL is a pure EoH governance module; it does not contain MKE-owned content (disease facts, guideline rules, drug tables, ontology mirrors).
* ARGL does not compute or modify patient state variables (stability bands, stack levels, PSI, suppression flags). It consumes them as read-only context.
* ARGL does not replace or override suppression decisions (owned by M8/M9). If ARGL's adversarial evaluation identifies a conclusion that should be suppressed, it flags it for M8/M9 evaluation; it does not suppress directly.
* ARGL does not generate clinical recommendations. Its output is a quality assessment of someone else's reasoning, not its own clinical judgment.
* All ARGL invariants are enforceable at runtime through gates (not advisory). Violations result in hard rejection, not warnings.
* The EoH/MKE separation boundary is maintained: ARGL may consume MKE evidence payloads but does not curate, validate, or store medical knowledge.
* Metaphorical overlays (internal design language) may appear in internal documentation but must be translated to sterile language before inclusion in any formal output, module specification, or downstream data structure (I-F1).

---

## **Dependencies (Other EoH Modules, Appendices by Reference Only)**

### **Upstream (consumed inputs)**

* **M56** (Patient Vision Unification): patient state snapshot for rebinding verification.
* **M8/M9** (Suppression): suppression state consumed as context.
* **M57** (Clinical Invariants System): named invariants that constrain reasoning flow.
* **MKE**: evidence payloads, knowledge objects, source metadata.
* **Any clinical reasoning module** producing outputs subject to ARGL governance: M17 (CIR), M18 (MPA), M49 (Dx Scoring), M53 (PTM), M64 (FUDD), Tool Library.

### **Downstream (consumers of ARGL outputs)**

* **M48** (Continuous Learning): after-action logs and counterexample bank entries.
* **M19** (QA & Anomaly Monitoring): conflict ledger entries and validation failure logs.
* **M21** (Vault): decision records and evidence maps for immutable audit storage.
* **M24** (Interface Hub): decision records for clinician-facing explainability.
* **M14** (Narrative): evidence maps for patient-facing and clinician-facing explanation generation.
* **M43** (ADE): audit artifacts for documentation and compliance.

### **Appendices (by reference only)**

* **Appendix H.67** (ARGL Invariant Registry): versioned list of all ARGL invariants with test specifications.
* **Appendix F.67** (ARGL Lineage Mapping): input/output FHIR mapping and provenance wiring.
* **Appendix C.67** (ARGL FHIR Profiles): AuditEvent, Provenance, and custom ARGL resource profiles.

---

## **Audit Hooks (What Must Be Logged and Attributable)**

For every ARGL invocation, the following must be logged as immutable, auditable records:

* **Invocation context:** `invoking_module_id`, `patient_id` (pseudonymized per consent), `question_text`, `constraint_set`, `acceptance_criteria`, `argl_version`, `timestamp`.
* **Agent tasking:** for each agent invoked: `agent_type`, `agent_instance_id`, `mission`, `start_time`, `end_time`, `stop_condition_hit`, `failure_mode_triggered` (if any).
* **Gate evaluations:** for each gate (G-1 through G-4): `gate_id`, `pass/fail`, `reason`, `timestamp`, `claims_affected[]`.
* **Arbitration decisions:** the complete D5 Decision Record, including all accepted claims, rejected claims with reasons, conflict ledger entries, falsification summary, and after-action notes.
* **Evidence tag resolution:** for each tag in the accepted claim set: `tag_id`, `source_id`, `locator`, `resolution_status` (resolvable / broken / retracted), `timestamp`.
* **Operational limitations:** any retrieval failures, agent timeouts, tool unavailability, or data gaps that affected the evaluation.
* **Version metadata:** `argl_module_version`, `agent_roster_version`, `invariant_set_version`, and `arbiter_ruleset_version` — sufficient for deterministic replay.

All audit records must be consumable by M21 (Vault), M19 (QA), and M48 (Continuous Learning) via standard FHIR AuditEvent + Provenance wiring per Appendix F.67.

---

## **Evaluation & Acceptance Tests**

### **Acceptance Tests (Pass/Fail)**

| Test ID | Test Name | Procedure | Pass Criterion |
|---|---|---|---|
| T-01 | Untagged Claim Rejection | Inject a claim with no `evidence_tags[]` and `claim_type` = `INFERENCE`. | Claim must not appear in `accepted_claims[]`. |
| T-02 | Evidence Mismatch Detection | Attach a citation that contradicts the claim it tags. | Claim must be rejected with reason `EVIDENCE_MISMATCH`. |
| T-03 | Falsification Gate Enforcement | Disable A9 (Falsifier) and attempt to publish. | Pipeline must hard-block with reason `NO_FALSIFICATION_REPORT`. |
| T-04 | Conflict Surfacing | Provide two sources with contradictory findings. | Output must contain a conflict ledger entry and bounded conclusion. |
| T-05 | Rebinding Enforcement | Submit an agent report where `rebind_check.binds_to_state = false`. | Report must be discarded or returned for repair. |
| T-06 | Sterile Output Validation | Run final output through terminology validator. | No terms from mythic/metaphorical overlay vocabulary may appear. |
| T-07 | Honest Unknowns | Ask a question with no available evidence. | Output must contain `UNKNOWN` markers and identify missing data. |
| T-08 | No Horizontal Collusion | Submit an agent report citing another agent's report as evidence. | Validation gate must reject with reason `HORIZONTAL_COLLUSION`. |
| T-09 | No Clinical Recommendations | Verify final ARGL output. | Must contain no diagnosis, treatment, or medication recommendation. |
| T-10 | Deterministic Replay | Replay identical inputs through identical arbiter version. | Decision records must be byte-identical. |
| T-11 | Containment Before Invocation | Attempt to invoke an agent without a containment record. | Command layer must refuse invocation. |
| T-12 | State Change Logging | Submit a report that changes a probability estimate without declaring the change. | Arbiter must flag as validation failure. |

### **Metrics (Track Over Time)**

| Metric | Definition | Target Direction |
|---|---|---|
| Hallucination rate | % of output claims in final conclusions lacking valid evidence tags | ↓ Minimize |
| Claim-evidence alignment | Human-rated or automated entailment score between claims and their cited evidence | ↑ Maximize |
| Contradiction detection rate | Proportion of seeded contradictions that are surfaced in the conflict ledger | ↑ Maximize |
| Retrieval precision proxy | % of retrieved sources that are actually used in accepted claims | ↑ Maximize |
| Retrieval recall proxy | Coverage score against a gold source set (when available) | ↑ Maximize |
| Uncertainty calibration | Confidence scores vs. empirical correctness on evaluation sets | ↑ Maximize (calibration) |
| Repair loop rate | % of agent reports that fail rebinding on first attempt and require rerun | ↓ Minimize over time |
| Falsification survival rate | % of leading conclusions that survive hostile review without modification | Monitor (neither extreme is ideal) |
| Time-to-arbitration | Latency from invocation to decision record emission | ↓ Minimize within quality bounds |
| After-action learning yield | # of counterexample bank entries and retrieval pattern updates per invocation | ↑ Maximize |

---

## **Integration Contracts**

### **For V6 Modules (M53 PTM, M64 FUDD, Tool Library)**

V6 reasoning modules that produce clinical interpretations SHOULD route their output through ARGL before downstream propagation. The integration pattern:

1. Module produces candidate output (e.g., PTM terrain update, FUDD detection, tool-generated score).
2. Module invokes ARGL with: `reasoning_chain_output`, `invocation_context`, `patient_state_snapshot`.
3. ARGL returns `decision_record`.
4. Module proceeds only with `accepted_claims[]` from the decision record. Rejected claims are logged but not propagated. Conflict ledger entries are surfaced alongside accepted claims.

### **For V5.2 Modules (Opt-In)**

V5.2 modules are not required to integrate with ARGL (zero backward contamination). However, any V5.2 module MAY opt in by routing candidate outputs through the same integration pattern above. Recommended initial candidates for opt-in: M17 (CIR edge creation), M18 (MPA pathway construction), M49 (diagnostic scoring).

### **For M62 (Orbit Mode Handshake)**

ARGL respects the M62 governance boundary: Orbit Mode navigation states (`circle | target | strike`) are treated as non-authoritative selection hints, not as evidence or confidence modifiers. ARGL does not consume Orbit Mode state as input to evidence evaluation or arbitration.

---

## **v1.0 Implementation Checklist**

1. Implement the Tag object (D1) and typed tag validation (I-B1, I-B2).
2. Implement the Claim object (D2) with required fields, confidence scoring, and failure mode enumeration.
3. Build the Rebinding Gate (D4) and enforce it as a hard fail at the arbiter level (I-C1).
4. Implement the Agent Report Schema (D3) and schema validation for all agent outputs.
5. Enforce "every claim must carry a tag" at the Command Arbiter level (I-B1).
6. Implement evidence mismatch detection — basic: manual checks; advanced: automated entailment scoring (I-B3).
7. Implement two-stage retrieval protocol (A1 → A2 → A3) with canonicalization (I-D3).
8. Implement the Falsifier Agent (A9) as mandatory and hard-block publication without a falsification report (I-D1).
9. Implement no horizontal collusion enforcement: agents cannot cite other agents' reports as evidence (I-D2).
10. Implement Conflict Ledger generation as a first-class output of arbitration (I-E1).
11. Build the sterile output translator (A11) and terminology validator (I-F1).
12. Implement the Safety Agent (A10) boundary checks: no clinical recommendations, no teleology, no scope violations (I-F2).
13. Build the Decision Record (D5) output with all required sections.
14. Create the After-Action Log format and wire it to M48 (Continuous Learning) telemetry intake.
15. Stand up the evaluation harness with acceptance tests T-01 through T-12 and tracked metrics.
16. Create the counterexample bank (fed by A9 outputs) and wire it for regression testing.
17. Implement Gate G-1 through G-4 as deterministic, logged checkpoints in the workflow.
18. Wire ARGL audit events to M21 (Vault) via FHIR AuditEvent + Provenance per Appendix F.67.
