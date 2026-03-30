# Ethos of Health — Complete Canon (V5.2 + V6)

**Prepared for Dylan — 2026-03-30**

This document contains the full canonical module set: V5.2 Modules 1–50 followed by V6 Modules 55–68.

---

# PART I — V5.2 MODULES (M1–M50)

---

\# \*\*V5.2 M1 — Patient Terrain Model Overview\*\*

Purpose: Module 1 defines Ethos-of-Health’s patient terrain coordinate system—Stack Level × Stability Band × Time—and governs how other modules may move a patient on that terrain. It defines OHB/CBM semantics, the Stack/Band ladder, and non-negotiable guardrails (confirmed dx gating; no band→stack auto-dx).

Scope (in scope / out of scope)

\* In scope    
  \* Define OHB and CBM semantics as system terms.    
  \* Define Stack governance as an integer count of distinct confirmed chronic conditions; “+” denotes complication depth only.    
  \* Define Stability Band governance as a Bands 0–5 ladder; qualitative meaning only in M1; legacy zones normalized to Bands 0–5.    
  \* Define terrain integration as Stack × Band × Time (trajectory framing).    
  \* Define guardrails: no auto-dx; no band→stack coupling; “high band triggers review”; single pause control may be referenced but its logic lives elsewhere.    
\* Out of scope    
  \* Disease facts, guidelines, scoring algorithms, or FHIR payloads.    
  \* Baseline twin initialization workflow (owned elsewhere).    
  \* All FHIR profile details for Band/Score/Drift/PSI observations and Terrain Snapshot (owned elsewhere).    
  \* ICD-10/SNOMED/LOINC usage content (owned elsewhere).

Inputs (data objects / fields only)

\* PatientTerrainCoordinate    
  \* stackLevel (integer)    
  \* stabilityBand (integer 0–5)    
  \* timestamp (time)    
\* Condition / EthosCondition (for stack provenance)    
  \* conditionId    
  \* confirmedStatus (confirmed diagnosis gating)    
  \* provenanceRef (provenance/audit trail pointer)    
\* Observations (referenced, not computed here)    
  \* bandObservationRef / scoreObservationRef / driftObservationRef / psiObservationRef (must be timestamped and attributable)    
\* TerrainSnapshot (referenced, not constructed here)    
  \* clinicalImpressionRef (Terrain Snapshot reference)

Outputs

\* Canonical definitions (system-level, consumed by other modules)    
  \* OHB: Stack 0, Band 0\\.    
  \* CBM: Stack ≥ 1 and Band ≤ 1; managed baseline state dependent on ongoing interventions; never labeled as cure.    
  \* Stack governance definition (including “+” complication depth marker).    
  \* Band ladder definition (Bands 0–5; qualitative meaning only in M1; legacy zones normalized).    
  \* Terrain framing rule: patient state is Stack × Band × Time.    
\* Governance invariants (enforced as constraints on downstream modules)    
  \* No auto-dx; no band→stack coupling; “high band triggers review.”    
  \* Single pause control may be referenced for display/governance; its logic lives elsewhere.

Process / Logic (deterministic, stepwise, no interpretation)

1\. Define terrain coordinate as (stackLevel, stabilityBand, timestamp) representing Stack × Band × Time.    
2\. Define OHB as stackLevel=0 and stabilityBand=0, and treat OHB as the conceptual anchor/reference target.    
3\. Define CBM as stackLevel≥1 and stabilityBand≤1, and treat CBM as “managed baseline state, not cure,” dependent on ongoing interventions.    
4\. Define Stack governance:    
   \* stackLevel is the integer count of distinct confirmed chronic conditions.    
   \* stackLevel changes only via confirmed dx workflows (confirmed diagnosis gating).    
   \* “+” denotes complication depth only (does not change stackLevel).    
5\. Define Band governance:    
   \* stabilityBand is on the Bands 0–5 ladder.    
   \* Band meaning in M1 is qualitative only; legacy zones normalize into Bands 0–5.    
6\. Enforce guardrails for any module that mutates patient terrain:    
   \* Prohibit auto-diagnosis behavior (no automatic Stack changes).    
   \* Prohibit band→stack coupling (Band shifts never increment Stack).    
   \* When a “high band” is present, require a review trigger (review behavior is owned elsewhere).    
   \* Allow referencing a single pause control for display/governance, but do not implement its logic here.    
7\. Defer authority to canonical appendices for governance and representation details, and do not restate their workflows or schemas in this module.

Governance / Constraints (explicit boundaries; no new rules)

\* M1 is intentionally thin and defers authority to canonical appendices.    
\* Appendix H.5 is the single source of truth for OHB/CBM/Stack governance.    
\* Appendix H.18 governs baseline twin initialization; M1 must not re-specify that workflow.    
\* Appendix C.5–C.6 own all FHIR profile details for Band/Score/Drift/PSI observations and Terrain Snapshot; M1 must not encode FHIR payloads.    
\* Appendix C.2/C.3 own ICD-10/SNOMED/LOINC usage; M1 remains conceptual and points there.    
\* Non-negotiable constraints: confirmed dx gating; no band→stack auto-dx; no auto-dx; no band→stack coupling.

Dependencies (other EoH modules, appendices by reference only)

\* Appendix H.5 (OHB/CBM/Stack governance).    
\* Appendix H.18 (baseline twin initialization governance).    
\* Appendix C.5–C.6 (FHIR profile details: Band/Score/Drift/PSI observations; Terrain Snapshot).    
\* Appendix C.2/C.3 (ICD-10/SNOMED/LOINC usage). fileciteturn1file0L33-L34    
\* Appendix C.3 (Condition/EthosCondition provenance/audit trail requirement for Stack changes).    
\* Appendix C.6 (Terrain Snapshot as ClinicalImpression bundle with AuditEvent lineage).

Audit Hooks (what must be logged and attributable)

\* Stack changes must trace to a Condition/EthosCondition with provenance/audit trail (Appendix C.3).    
\* Band/Score/Drift/PSI observations must carry timestamp/subject/index-type coding; computation lives in other modules but must adhere to H.5/H.18 governance.    
\* Terrain Snapshot must be a ClinicalImpression bundle with AuditEvent lineage (Appendix C.6).    
\* Baseline initialization/recalibration must be governed by H.18 and versioning appendix so “Day 0” coordinates are reproducible/auditable.

\# \*\*V5.2 M2 — Chronic Baseline Mode (CBM)\*\*

\#\#\# \*\*Purpose\*\*

Define and operationalize Chronic Baseline Mode (CBM) as a temporal state classification: “well with support” for patients with confirmed chronic illness (Stack ≥ 1\\) who remain stable at low instability bands (Band ≤ 1\\) because interventions are active.    
Distinguish OHB (Original Healthy Baseline: Stack 0, Band 0\\) from CBM, and route everything else to Active Disease State.    
Add false-exit suppression (pauseFlag/pauseReason) and baseline drift early-warning, without embedding disease knowledge or guideline content.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* State determination for OHB vs CBM vs Active Disease State using Stack and Band.    
\* False-exit suppression via \`pauseFlag\` \\+ \`pauseReason\` for the listed patterns (Overshoot, Healing Pain, Symbolic Flare, Lab Error), with non-destructive auditability.    
\* Baseline band tracking (best achieved band in OHB/CBM) and drift flagging when persistently worse by \\\>1 band.

\*\*Out of scope\*\*

\* Any disease knowledge, guideline content, or clinical interpretation beyond the Stack/Band state rules.    
\* Any inference that changes Stack without confirmed diagnoses; any coupling where Band changes Stack.    
\* Defining the drift persistence window (it is governed elsewhere and must not alter the \\\>1 band threshold rule).    
\* Patient-facing rendering/vocabulary beyond noting that patient-facing render is governed elsewhere.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`confirmed\_diagnoses\[\]\` (used to compute \`stackLevel\`)    
\* \`symptoms\_journaling\[\]\`    
\* \`vitals\_wearables\[\]\`    
\* \`labs\[\]\`    
\* \`psi\_flags\[\]\`    
\* \`stabilityScore\` (if present)    
\* \`stabilityBand\` (0–5)    
\* \`stackLevel\` (Stack \\= count of distinct confirmed chronic conditions)    
\* Prior-state fields when available (for transition logging and baseline tracking):    
  \* \`previousState\` (OHB/CBM/Active)    
  \* \`previousStabilityBand\`    
  \* \`baselineBand\` (best achieved band while in OHB/CBM), if already stored

\#\#\# \*\*Outputs\*\*

\* \`currentState\` ∈ {\`OHB\`, \`CBM\`, \`Active Disease State\`}    
\* \`pauseFlag\` (boolean)    
\* \`pauseReason\` ∈ {\`Overshoot\`, \`Healing Pain\`, \`Symbolic Flare\`, \`Lab Error\`}    
\* \`baselineBand\` (best achieved band while in OHB/CBM; optional)    
\* \`driftFlag\` (optional)    
\* Pass-through / surfaced indices (as outputs produced by this state layer):    
  \* \`stackLevel\`    
  \* \`stabilityBand\`

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Read inputs\*\*: \`stackLevel\`, \`stabilityBand\`, and any current \`pauseFlag/pauseReason\`, plus any stored \`baselineBand\`.    
2\. \*\*State determination (canonical rules; no modifiers)\*\*:    
   \* If \`stackLevel \== 0\` AND \`stabilityBand \== 0\` → set \`currentState \= OHB\`.    
   \* Else if \`stackLevel \>= 1\` AND \`stabilityBand \<= 1\` → set \`currentState \= CBM\`.    
   \* Else → set \`currentState \= Active Disease State\`.    
3\. \*\*False-exit suppression interface\*\*:    
   \* Maintain a single \`pauseFlag\` \\+ \`pauseReason\` to prevent premature CBM exits when patterns fit: Overshoot, Healing Pain, Symbolic Flare, Lab Error.    
   \* Suppression annotates decisions; it never hides them (suppressed events remain auditable).    
4\. \*\*Baseline band tracking (OHB/CBM only)\*\*:    
   \* Track best achieved band as the patient’s \`baselineBand\` while in CBM/OHB.    
5\. \*\*Baseline drift early-warning\*\*:    
   \* Flag \`driftFlag\` when stability is persistently worse than best band by \\\>1 band.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* \*\*Locked terminology\*\*: OHB \\= Stack 0, Band 0; CBM \\= Stack ≥ 1 and Band ≤ 1, maintained only with ongoing interventions; Bands (0–5) and Stack (count of distinct confirmed chronic conditions).    
\* \*\*No auto-diagnosis\*\*: Stack changes only via confirmed diagnoses; no inference; no band→stack coupling.    
\* \*\*Suppression is non-destructive\*\*: suppression annotates decisions; it never hides them (suppressed events remain auditable).    
\* \*\*Vocabulary governance\*\*: clinician-facing uses CBM/Bands/Stack; patient-facing render is governed elsewhere.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* None specified within this module text.

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* \*\*State transitions\*\*: OHB↔CBM↔Active (timestamped).    
\* \*\*Suppression events\*\*: when \`pauseFlag=true\`, include \`pauseReason\`; suppression must be traceable (no silent suppression).    
\* \*\*Baseline band updates\*\*: when best-achieved baseline changes (baselineBand tracking).    
\* \*\*DriftFlag assertions\*\*: when “persistently worse by \\\>1 band” condition is met (persistence window governed elsewhere).    
\* \*\*Stack provenance\*\*: stack changes only via confirmed diagnoses; record confirmation source/lineage.

\# \*\*V5.2 M3 — Terrain Index Engine (Stability Band \\+ Stack Level)\*\*

\#\#\# \*\*Purpose\*\*

Module 3 defines the core terrain indices that quantify “how unstable is the patient today” and “how much chronic burden does the patient carry” without importing any external medical knowledge. It binds together two proprietary, EoH-owned state engines: M3A (Stability Score \\-\\\> Stability Band) and M3B (Stack Score \\-\\\> Stack Level). Its role is to provide a single, auditable contract for Band/Score, Stack/Complication depth (+), and transition events (including CBM enter/exit), while delegating thresholds, suppression TTL, FHIR encodings, and downstream actions to their authoritative appendices/modules.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Stability Score aggregation \\-\\\> Stability Band (0–5).    
\* Stack Level counting from confirmed chronic diagnoses (0..N).    
\* Complication depth markers (“+” and optional (+k) display metadata).    
\* CBM enter/exit event emission (derived from Stack/Band rules defined in H.5).    
\* Suppression interface fields (pauseFlag/pauseReason) and propagation semantics.    
\* Transition logging requirements (band/stack deltas, suppression application, CBM events).

\*\*Out of scope\*\*

\* Guidelines or society recommendations.    
\* Disease facts, natural history, relapse rates.    
\* Drug classes / contraindication lists / interaction tables.    
\* Lab interpretation tables or reference ranges.    
\* Ontology mirrors (ICD/SNOMED/LOINC/RxNorm lists).    
\* Phenotype dictionaries or static symptom-\\\>disease tables.    
\* Meaning/definitions of external medical concepts (sourced from MKE and/or upstream coding layers; M3 never stores them).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\*\*M3 input contract (read-only)\*\*

\* \`normalizedTags\[\]\` (already-normalized tags across symptoms, labs/vitals, treatment changes, psychosomatic modifiers, diagnoses).    
\* \`confirmedDiagnoses\[\]\` (confirmed diagnosis lifecycle events used for Stack counting).    
\* \`diagnosisLifecycleEvents\[\]\` (newly confirmed distinct chronic condition; explicitly withdrawn or resolved).    
\* \`complicationDepthMarkers\[\]\` (per-layer “+” markers; optional (+k) display metadata).    
\* \`pauseFlag\` (boolean).    
\* \`pauseReason\` (enum; Overshoot, HealingPain, SymbolicFlare, LabError).

\*\*Version / governance references (inputs by reference)\*\*

\* \`H.5\` (ladder semantics: Stack levels, Stability bands, OHB/CBM definitions).    
\* \`H.2\` (pauseFlag/pauseReason field definitions and canonical reason codes).    
\* \`F.5–F.9\` (suppression triggers, TTL, priority/override policy).    
\* \`C.4/C.5/C.6/C.11\` (FHIR encodings and audit/provenance bindings).

\#\#\# \*\*Outputs\*\*

\*\*State outputs\*\*

\* \`stabilityScore\` (continuous).    
\* \`stabilityBand\` (0–5).    
\* \`stackLevel\` (integer count of distinct, confirmed chronic conditions; 0..N).    
\* \`complicationDepth\` representation (“+” on the corresponding layer; optional (+k) display-only metadata).    
\* \`pauseFlag\`, \`pauseReason\` (propagated as the single suppression channel).

\*\*Explainability / instrumentation outputs\*\*

\* \`rationale\` (top contributors).    
\* \`trendFlag\` (rapid rise / approaching Band 5; instrumentation only).

\*\*Transition event outputs\*\*

\* \`CBM\_entered\` / \`CBM\_exited\` events (based on Stack/Band rules defined in H.5).

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Enforce umbrella invariants\*\*    
   1\. Treat Stack changes as allowed only via confirmed diagnosis lifecycle.    
   2\. Do not allow Band shifts to increment Stack (no Band \\-\\\> Stack coupling).    
   3\. Enforce a single suppression channel: \`pauseFlag\` \\+ \`pauseReason\` with a single active reason invariant.    
   4\. Do not hard-code numeric cut-points, TTL windows, or escalation tiers in M3 (thresholds governed elsewhere).    
2\. \*\*Compute Stability Score and Stability Band (M3A)\*\*    
   1\. Consume \`normalizedTags\[\]\` across symptoms, labs/vitals, treatment changes, psychosomatic modifiers, diagnoses.    
   2\. Aggregate tags using weighted additive aggregation into a continuous \`stabilityScore\`.    
   3\. Map \`stabilityScore\` into \`stabilityBand\` (0–5) using governed thresholds (not defined in M3).    
   4\. Apply suppression safeguard behavior via \`pauseFlag\`/\`pauseReason\` in {Overshoot, HealingPain, SymbolicFlare, LabError} that holds/dampens upward Band movement per suppression policy (F.5–F.9).    
   5\. Emit \`stabilityScore\`, \`stabilityBand\`, \`pauseFlag\`, \`pauseReason\`, \`rationale\` (top contributors), and \`trendFlag\` (instrumentation only).    
3\. \*\*Compute Stack Level and complication depth (M3B)\*\*    
   1\. Set \`stackLevel\` \\= integer count of distinct, confirmed chronic conditions (0..N).    
   2\. Represent complication depth within an existing condition as “+” on the corresponding layer, with optional (+k) display-only metadata.    
   3\. On newly confirmed distinct chronic condition, increment \`stackLevel\` by \\+1; if multiple conditions are confirmed simultaneously, apply multi-increment.    
   4\. On diagnosis explicitly withdrawn or resolved, decrement \`stackLevel\` by \\-1.    
   5\. Do not allow symptom/lab intensity to directly change \`stackLevel\`.    
4\. \*\*Emit CBM enter/exit transition events\*\*    
   1\. Determine CBM enter/exit using Stack/Band rules defined in Appendix H.5.    
   2\. Emit \`CBM\_entered\` / \`CBM\_exited\` with the underlying Stack/Band state.    
5\. \*\*Audit-grade emission on all changes\*\*    
   1\. Every change to Score/Band/Stack/CBM/suppression emits audit-grade records.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* M3 operates only on already-normalized tags and confirmed diagnoses.    
\* M3 must not contain guidelines, disease facts, drug classes/contraindication lists/interaction tables, lab interpretation tables/reference ranges, ontology mirrors, or phenotype dictionaries/static symptom-\\\>disease tables.    
\* No auto-diagnosis: Stack changes only via confirmed diagnosis lifecycle.    
\* No Band \\-\\\> Stack coupling: Band shifts never increment Stack.    
\* Single suppression channel: \`pauseFlag\` \\+ \`pauseReason\` (single active reason invariant).    
\* All thresholds are governed elsewhere: numeric cut-points, TTL windows, and escalation tiers are not hard-coded in M3.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Appendix H.5\*\* — Ladder semantics: Stack levels, Stability bands, OHB/CBM definitions.    
\* \*\*Appendix H.2\*\* — \`pauseFlag\`/\`pauseReason\` field definitions and canonical reason codes.    
\* \*\*Appendices F.5–F.9\*\* — Suppression triggers, TTL, and priority/override policy.    
\* \*\*Appendices C.4/C.5/C.6/C.11\*\* — FHIR encodings and audit/provenance bindings.

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

M3 must log and version-pin:

\* Every Stability Score and Stability Band computation (timestamped).    
\* Every Band transition (prev/new Band, drivers, suppression state).    
\* Every Stack Level transition (prev/new Stack, diagnosis event provenance).    
\* Every complication depth marker change (+) and any (+k) metadata change.    
\* Every CBM\\\_entered / CBM\\\_exited event and the underlying Stack/Band state.    
\* Every suppression activation/deactivation (\`pauseFlag\`/\`pauseReason\`, TTL reference).    
\* All module/appendix versions used (module versionTag, H.5 version, H.2 version, F.9 version, C.11 version).

\# \*\*V5.2 M5 — Symbolic Interpreter / Psychosomatic Analyzer\*\*

\#\#\# \*\*Purpose\*\*

Module 5 interprets symbolic/metaphorical and psychosocial overlays in patient narrative text to prevent misclassification when symptom reporting is distorted by stress/denial/emotion/metaphor.    
It outputs persona flags and a Psychosomatic Index (PSI 0–3) for downstream use, without asserting diagnoses.    
In V5.2, M5 remains EoH-owned (not replaced by MKE) and is bounded to patient-specific narrative interpretation plus internal EoH state semantics.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Symbolic vs literal interpretation layer (M4 literal tags vs M5 symbolic parsing).    
\* PSI scale (0–3) definitions and assignment rules.    
\* Persona flag emission (e.g., FalseRecoveryPersona / NarrativeOveridentification / CatastrophicMetaphor).    
\* Suppression candidate signaling: may emit Symbolic Flare as a suppression candidate (does not adjudicate suppression TTL or escalation).    
\* Explainability/auditability constraints: PSI tied to textual evidence; symbolic tags do not add diagnoses; provenance logged.

\*\*Out of scope\*\*

\* Any world knowledge (guidelines/disease facts/ontologies) or static medical knowledge tables.    
\* Any large static lexicon/mapping tables embedded in module text.    
\* Any ML/transformer roadmap or literature-driven expansions from donors.    
\* Suppression TTL/priority ladder and enforcement (owned by suppression governance elsewhere).    
\* FHIR export mapping details (belong in Appendix C.12 cross-reference matrix).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* Patient narrative text.    
\* Context flags from prior parsing modules (including M4 context flags).    
\* Lexicon version.    
\* Summarization ruleset version.

\#\#\# \*\*Outputs\*\*

\* PSI (Psychosomatic Index) in range 0–3.    
\* Persona flags (e.g., FalseRecoveryPersona / NarrativeOveridentification / CatastrophicMetaphor).    
\* Symbolic/psychosocial tags.    
\* Provenance binding outputs to textual evidence excerpts.    
\* Optional suppression candidate: \`pauseReason \= Symbolic Flare\` (for downstream suppression governance decisioning).

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest inputs\*\*: patient narrative text plus context flags from prior parsing modules (including M4).    
2\. \*\*Run symbolic/psychosocial cue detection\*\* (lexicon-governed): detect cues including metaphor resolution, simile/analogy patterns, emotional tone extraction, denial/over-optimism cues, and identity fusion cues.    
3\. \*\*Compute PSI (0–3)\*\* using the defined scale and assignment rules: PSI intent is 0 none, 1 mild, 2 moderate, 3 heavy overlay; assign PSI by “mild clues → 1; multiple overlays → 2; heavy symbolic/persona → 3”.    
4\. \*\*Emit outputs\*\*:    
   \* Produce symbolic/psychosocial tags, PSI value, and persona flags, with provenance.    
   \* If warranted by detected cues, emit suppression candidate \`pauseReason \= Symbolic Flare\` for downstream suppression governance (downstream decides enforcement).    
5\. \*\*Bind explainability\*\*: ensure PSI and persona flags are explainable and tied to specific textual evidence; do not assert diagnoses and do not add diagnostic content via symbolic tags.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* M5 is EoH-only by content type and contains no guideline text, disease fact tables, drug class lists, ontology mirrors, lab interpretation tables, or phenotype dictionaries.    
\* M5 outputs PSI/persona flags for downstream use “without asserting diagnoses,” and symbolic tags do not add diagnoses.    
\* Cue detection is lexicon-governed; do not inline huge lexicon or mapping tables into module text; interpretation must be version-bound.    
\* Suppression is a candidate signal only; M5 does not adjudicate suppression TTL, priority, or escalation.    
\* Any FHIR mapping bullets are out of module body scope and belong in Appendix C.12.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Upstream\*\*: Module 4 context flags / literal tags.    
\* \*\*Downstream\*\*: scoring modules consume PSI; suppression governance modules enforce pause semantics and TTL/priority.    
\* \*\*Appendices / governance anchors\*\*: F.4, F.5, C.12, D.3, F.12, H.2.5, H.5.4.

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* Log \`symbolic.cue.detected\` events per entry with evidence excerpt and cue type (metaphor/denial/identity fusion, etc.).    
\* Log PSI output and reasoning trace (why PSI was elevated) and persona flags emitted.    
\* Log lexicon version and summarization ruleset version used for the interpretation.    
\* If suppression candidate is emitted, log \`pauseFlag/pauseReason \= Symbolic Flare\` with linkage back to originating cues and downstream suppression trail.

\# \*\*V5.2 M6 — Escalation Router\*\*

\#\#\# \*\*Purpose\*\*

Turn verified patient-state changes (Stability Band / Stack Level / PSI / pause state) into tiered, explainable alerts and route them to patient vs clinician paths.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Read current state fields: Stability Band / Stack Level / PSI / \`pauseFlag\`\\+\`pauseReason\` (and optional \`topContributors\` for explanation only).    
\* Evaluate simple, local conditions: Band increase vs \`prev\_band\`; Stack increase vs \`prev\_stack\`; PSI ≥ configured threshold when pause is active (“symbolic flare”); persistent suppression conditions (\`pauseFlag=true\` for ≥ configured days); critical band entry (Band 5).    
\* Map trigger events to Tier 0–3 outcomes and route to patient vs clinician paths.    
\* Emit audit-grade records using FHIR resources per Appendix F.10 / C.4.

\*\*Out of scope\*\*

\* Differential diagnosis logic, guideline rules, drug/evidence tables.    
\* Band computation or score-to-band math.    
\* Baseline/CBM algorithms.    
\* Static phenotype/ontology tables, code lists, evidence tables, or embedded FHIR schema payloads.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\*\*State (read-only)\*\*

\* \`stabilityBand\`    
\* \`prev\_band\`    
\* \`stackLevel\`    
\* \`prev\_stack\`    
\* \`pauseFlag\`    
\* \`pauseReason\`    
\* \`PSI\`    
\* \`topContributors\` (optional; explanation only)

\*\*Config / policy references\*\*

\* PSI threshold (configured; used for “symbolic flare” evaluation)    
\* Persistent suppression duration threshold (\`pauseFlag=true\` ≥ X days)

\#\#\# \*\*Outputs\*\*

\* \`escalation\_tier\` (Tier 0–3)    
\* \`alert\_message\` (human-readable)    
\* \`rationale\` bundle:    
  \* band delta (\`stabilityBand\` vs \`prev\_band\`)    
  \* stack delta (\`stackLevel\` vs \`prev\_stack\`)    
  \* \`PSI\`    
  \* \`pauseFlag\` / \`pauseReason\`    
  \* \`topContributors\` (if present)    
\* \`deliveryTarget\` (patient path vs clinician path; to Interface Router)    
\* \`storageAction\` (append to audit trail)    
\* Audit/interop artifacts (FHIR): DetectedIssue, CommunicationRequest/Communication, AuditEvent, Provenance (per Appendix F.10 / C.4)

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Load inputs\*\* from the current state object: \`stabilityBand\`, \`prev\_band\`, \`stackLevel\`, \`prev\_stack\`, \`pauseFlag\`, \`pauseReason\`, \`PSI\`, and optional \`topContributors\`.    
2\. \*\*Compute trigger booleans\*\* (simple, local checks):    
   \* \`band\_increase \= (stabilityBand \> prev\_band)\`    
   \* \`stack\_increase \= (stackLevel \> prev\_stack)\`    
   \* \`critical\_band\_entry \= (stabilityBand \== 5)\`    
   \* \`symbolic\_flare \= (pauseFlag \== true) AND (PSI \>= configured\_threshold)\`    
   \* \`persistent\_suppression\_override \= (pauseFlag \== true) for ≥ configured days while drift continues\`    
3\. \*\*Determine applicable trigger set\*\* in this order of evaluation surface: include \`critical\_band\_entry\` as a trigger even when suppression is active.    
4\. \*\*Apply suppression semantics\*\* (single \`pauseFlag/pauseReason\` channel):    
   \* If \`symbolic\_flare\` is true, follow “pause-but-notify” behavior.    
   \* Suppression may lower escalation tier but must not block critical Band-5 escalation.    
5\. \*\*Map triggers to escalation tiers (0–3)\*\* and routing outcomes:    
   \* Tier 0: no escalation (log only)    
   \* Tier 1: patient-facing prompt    
   \* Tier 2: clinician notification    
   \* Tier 3: urgent escalation    
6\. \*\*Assemble routing artifact\*\*: set \`escalation\_tier\`, generate \`alert\_message\`, populate \`rationale\`, select \`deliveryTarget\` (patient vs clinician path), set \`storageAction\` to append audit trail.    
7\. \*\*Emit audit-grade records\*\* for every escalation and every suppression decision, represented via FHIR resources (DetectedIssue, CommunicationRequest/Communication, AuditEvent, Provenance) per Appendix F.10 / C.4.    
8\. \*\*Version-pin for reproducibility\*\*: attach policy/version identifiers into generated AuditEvent/Provenance so that identical inputs plus policy version IDs produce the same tier/routing decision.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* M6 consumes patient state and does not use world knowledge.    
\* M6 must not contain differential diagnosis logic, guideline rules, drug/evidence tables, static phenotype/ontology/code/evidence tables, or band computation math.    
\* Single suppression channel invariant: \`pauseFlag\` \\+ \`pauseReason\`.    
\* Suppression may lower tier but never blocks critical Band-5 escalation; Band 5 always escalates.    
\* M6 module text must not embed FHIR payload schemas; those are referenced via Appendix F.10 / C.4.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Upstream inputs: Module 2 (CBM), Module 5 (PSI), suppression modules (M11/M9), Modules 13/14 (prognostic tiers).    
\* Downstream handoffs: Module 10 (escalation delivery), Module 43 (Interface Router / UI), Module 41/48 (audit \\+ governance).    
\* Appendices: F.6 (tier definitions & trigger matrix), F.9 (suppression policy), F.10 (canonical FHIR mappings for escalation), H.2/H.3/H.4/H.5 (locked fields and tier/guidance ladders and band/stack definitions), C.4 (FHIR mapping), Appendix K referenced by ID only (no restatement).

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* For every escalation and every suppression outcome: trigger(s), tier (0–3), reason codes (Band/Stack/PSI/pause), timestamp, patient ID.    
\* Provenance linkage: include upstream evidence pointers sufficient to justify deltas and symbolic flare evaluation (including \`topContributors\` when present).    
\* Interop artifacts created: DetectedIssue, CommunicationRequest/Communication, AuditEvent, Provenance (per Appendix F.10 / C.4).    
\* Reproducibility fields: EscalationPolicyVersion, SuppressionPolicyVersion, VectorVersion embedded into AuditEvent/Provenance; identical state input \\+ policy version IDs must reproduce the same decision.

\# \*\*V5.2 M7 —Data Quality & Care Plan Orchestration Layer\*\*

\#\#\# \*\*Purpose\*\*

Module 7 is the bridge between raw data and actionable care.    
M7A validates and labels inputs with confidence and provenance so downstream inference is not polluted by bad data.    
M7B converts validated escalations into structured, auditable tasks, messages, and CarePlan adjustments with strict human-in-loop safeguards.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Two sealed submodules under the M7 umbrella: M7A (Data Quality & Sanity Checks) and M7B (Care Plan Orchestrator).    
\* M7A ingest QA, contradiction handling, missingness handling, outlier flagging, suppression audit hooks, failsafe/uncertainty labeling.    
\* M7B tier-to-action translation, actor routing, CarePlan/Task/ServiceRequest/Communication drafting, suppression-aware routing, human-in-loop safeguards.    
\* Use of externally supplied plausibility bounds as process-level labels (valid/quarantine), without embedding threshold tables in-module.    
\* FHIR scaffolding references for CarePlan/ServiceRequest/Task/Communication/CommunicationRequest/Flag, with mappings referenced via Appendix C/C.11 (not duplicated).

\*\*Out of scope\*\*

\* Any embedded guideline text, diagnostic criteria narratives, disease facts, or “what to do next clinically” checklists.    
\* Drug classes, contraindication lists, interaction tables.    
\* Ontology mirrors or code dictionaries (ICD/SNOMED/LOINC/RxNorm), phenotype dictionaries, lab interpretation tables or static cutoff/range tables.    
\* Model drift / calibration / retraining QA loops (belongs to QA & learning modules, not ingest QA or orchestration).    
\* Diagnosis watchlist / stack-promotion / diagnostic confirmation logic from legacy donors.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`V5-07A-Baseline (LOCKED)\` (Module 7A baseline)    
\* \`V5-07B-Baseline (LOCKED)\` (Module 7B baseline)    
\* \`V3-07 (legacy donor)\` (read-only donor; non-isomorphic; relocation targeting only)    
\* \`V4-07 (legacy donor)\` (read-only donor; non-isomorphic; relocation targeting only)    
\* Governance input: \`EoH–MKE Overlap Audit\`    
\* Appendix references (by ID only; not duplicated in-module): \`Appendix G\`, \`Appendix C / C.11\`, \`Appendix H.2 / H.5\`, \`Appendix F.6\`, \`Appendix L.1–L.3\`

Operational input fields (consumed/produced within M7 interfaces):

\* Incoming data stream types: \`labs\`, \`vitals\`, \`PROs\`, \`journaling-derived tags\`    
\* QA annotation fields: \`confidenceScore\`, \`sourceType\`, \`uncertain\_day\_marker\`, \`contradiction\_flags\`, \`implausibility\_flags\`, \`outlier\_flags\`, \`missingness\_flags\`, \`structurally\_absent\_flags\`, \`imputation\_provenance\`    
\* Suppression context fields for logging/propagation: \`pauseFlag\`, \`pauseReason\` (field locks referenced via Appendix H.2)    
\* Escalation input to orchestration: \`tier\` (Tier 1–3), \`Band/Stack state\`, \`suppression context\`

\#\#\# \*\*Outputs\*\*

\*\*M7A outputs\*\*

\* Validated dataset for downstream scoring/routing.    
\* QA annotations and uncertainty markers: contradiction/implausibility/outlier/uncertainty flags.    
\* Imputation provenance records.

\*\*M7B outputs\*\*

\* Tier-to-action orchestration artifacts: structured tasks, messages, and CarePlan adjustments.    
\* Actor-routed drafts: \`CarePlan\`, \`ServiceRequest\`, \`Task\`, \`Communication/CommunicationRequest\`, \`Flag\` (FHIR scaffolding; mappings referenced).

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. Enforce the M7 umbrella boundary: treat M7 as an umbrella only with two sealed submodules (M7A and M7B).    
2\. Enforce the allowed coupling interface: permit M7B to consume M7A outputs (validated dataset \\+ QA annotations \\+ \`confidenceScore\` \\+ “uncertain day” markers).    
3\. Enforce submodule separation: M7A does not perform orchestration; M7B does not perform QA logic or embed QA threshold tables.    
4\. For each ingestion cycle, execute M7A first:    
   1\. Apply sanity bounds at the process level by checking each incoming data type (labs, vitals, PROs, journaling-derived tags) against plausibility bounds supplied externally.    
   2\. If a value is out-of-bound, quarantine it and flag it for review.    
   3\. Detect contradictions between sources, flag conflicts (do not erase), prefer higher-integrity/objective streams for downstream consumption, and preserve disagreement in the audit trail.    
   4\. Handle missing data:    
      \* If transiently missing, impute from recent baseline or carry-forward last valid value with provenance.    
      \* If chronically missing, mark as “structurally absent” so downstream modules do not expect it.    
   5\. Detect outliers as sudden spikes compared against rolling baseline; flag if inconsistent with trajectory (no disease interpretation).    
   6\. Emit the suppression audit hook by logging whenever suppression logic is applied so downstream audit can adjudicate validity.    
   7\. Apply failsafe mode: if \\\>30% of critical inputs are invalid, withhold downstream scoring/escalation and mark the record/day “uncertain.”    
   8\. Ensure transparency/override support: imputation and suppression logs remain visible for review.    
   9\. Produce M7A outputs: validated dataset, QA flags (DetectedIssue \\+ AuditEvent), and imputation provenance records.    
5\. If M7A does not withhold downstream scoring/escalation due to failsafe mode, execute M7B:    
   1\. Consume M7A outputs (validated dataset \\+ QA annotations \\+ \`confidenceScore\` \\+ “uncertain day” markers).    
   2\. Translate tier to action-category:    
      \* Tier 1 → patient-facing nudge.    
      \* Tier 2 → clinician review notification.    
      \* Tier 3 → urgent escalation / care-team task.    
   3\. Route tasks by actor type (patient vs provider vs care coordinator).    
   4\. Draft CarePlan updates structurally (goals/activities/monitoring structures) without embedding guideline content.    
   5\. Apply suppression-aware orchestration: if suppressed (e.g., symbolic flare), still generate a reflective patient prompt and avoid clinician false alarms.    
   6\. Enforce safeguards:    
      \* No autonomous Rx changes; clinician confirmation required.    
      \* Tier 3 cannot be suppressed/overridden by patient-only inputs.    
   7\. Produce FHIR scaffolding artifacts as drafts (CarePlan, ServiceRequest, Task, Communication/CommunicationRequest, Flag) with mappings referenced via Appendix C/C.11.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* V5 baselines are not altered.    
\* V3/V4 donors may contribute examples/definitions/clarifications only if they do not introduce new scoring logic/algorithms; non-isomorphic donor content is not imported.    
\* No new scoring logic and no new algorithms are introduced in this module.    
\* M7 is an umbrella only; M7A and M7B remain sealed with the explicit interface and separation constraints.    
\* Neither M7A nor M7B may embed MKE-owned clinical knowledge tables, dictionaries, or guideline content.    
\* Numeric plausibility/range tables, hard-coded medical cutoffs, lab interpretation semantics, ontology mirrors, phenotype dictionaries, and FHIR field-by-field mapping enumerations are not embedded in M7.    
\* Appendix G is the authority for detailed QA matrices; Appendix C/C.11 is the authority for FHIR mappings and audit/provenance schema; Appendix F.6 is the authority for escalation orchestration specification; Appendix H.2/H.5 are the authority for locked fields and critical-input semantics; Appendix L.1–L.3 are the authority for versioning/ledger semantics.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Module 6 (consumer of M7A validated dataset).    
\* Module 27 (EHR Integration; receives M7B outputs).    
\* Suppression layer (M7 logs suppression application and consumes suppression context; field locks via Appendix H.2).    
\* Appendices: Appendix G; Appendix C/C.11; Appendix H.2/H.5; Appendix F.6; Appendix L.1–L.3.

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\*\*M7A must log\*\*

\* Every imputation, override, contradiction resolution, outlier flag, suppression tag, and failsafe state as AuditEvent linked to Provenance and \`sourceType\`.    
\* “Uncertain day” events as DetectedIssue \\+ AuditEvent suitable for downstream QA review.

\*\*M7B must log\*\*

\* Each CarePlan/Task/ServiceRequest/Communication creation/update/cancel with upstream driver references (tier, Band/Stack state, suppression context) and version tags.    
\* Clinician reviewer identity and outcome when humans act.    
\* Tier 3 actions as non-suppressable by patient-only inputs and auditable back to their triggers.

\# \*\*V5.2 M8 — Clinician Suppression Controls & Systemwide Suppression Governance\*\*

\#\#\# \*\*Purpose\*\*

Module 8 defines and governs the canonical suppression fields used by the platform and the clinician-initiated toggle layer that sets them.    
It ensures suppression is non-destructive (does not delete/overwrite raw data) and only affects whether a Stack participates in current Band computation.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Canonical suppression fields and invariants: \`pauseFlag\` and \`pauseReason\` (including the single-reason invariant and priority selection via F.9).    
\* Clinician-initiated “MD Toggle” governance: session-default behavior, activation, persistence/reactivation, and safety override behavior.    
\* Emitting unified suppression state to Module 6 and audit-ready events to Module 41 / Appendices C.7/C.11.    
\* Enforcing Appendix H.2 locked-field usage for suppression fields, including timestamps and source module fields.

\*\*Out of scope\*\*

\* Setting TTL defaults, priority ladder values, or resolution taxonomy values (confirm/lift/escalate); these are governed by Appendix F.9 and referenced by M8.    
\* Defining clinician toggle lifecycle/priority/FHIR mappings beyond alignment to Appendix F.8 (M8 is the governance narrative layer matching those rules).    
\* Encoding disease facts, medication details, or guideline algorithms.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* Suppression candidates from Module 5: \`SymbolicFlare\` (and associated persona flags, PSI as upstream context).    
\* QA/sanity triggers from Module 7A: \`LabError\`, \`Overshoot\`, \`HealingPain\`.    
\* Clinician toggle actions from Module 8A (MD toggle requests/actions).    
\* Locked suppression fields (Appendix H.2 canonical field set available to M8):    
  \* \`pauseFlag\`, \`pauseReason\`, \`pauseStartTimestamp\`, \`pauseEndTimestamp\`, \`pauseSourceModule\`.    
\* Critical instability context for safety override (“Zone 5 / critical instability” / “critical band” detection as consumed condition for override behavior).

\#\#\# \*\*Outputs\*\*

\* Unified suppression state for downstream scoring/routing: \`pauseFlag\`, \`pauseReason\` to Module 6\\.    
\* Audit-ready suppression/toggle events to Module 41 and Appendices C.7/C.11.

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Initialize/require canonical fields\*\*: represent suppression state only via Appendix H.2 canonical fields \`pauseFlag\`, \`pauseReason\`, \`pauseStartTimestamp\`, \`pauseEndTimestamp\`, \`pauseSourceModule\`.    
2\. \*\*Ingest suppression candidates\*\* from:    
   \* Module 5 psychosomatic triggers (\`SymbolicFlare\`, persona flags, PSI).    
   \* Module 7A QA/sanity triggers (\`LabError\`, \`Overshoot\`, \`HealingPain\`).    
   \* Module 8A clinician toggle actions (MD toggles).    
3\. \*\*Enforce the canonical reason set\*\* for \`pauseReason\` as: \`{SymbolicFlare, Overshoot, HealingPain, LabError, MD\_Toggle}\`.    
4\. \*\*Enforce single-reason invariant\*\*:    
   \* Allow only one active \`pauseReason\` at a time.    
   \* If multiple candidates exist, select the highest priority reason using Appendix F.9.    
5\. \*\*Apply MD Toggle activation semantics\*\* (clinician-initiated toggle):    
   \* When a clinician marks a Stack “inactive” for simulation/workflow, set \`pauseFlag=true\` and \`pauseReason=MD\_Toggle\`.    
   \* Default toggle scope is session-only; the toggle expires when the session/case closes unless explicitly extended.    
6\. \*\*Apply MD Toggle persistence/reactivation semantics\*\*:    
   \* If new qualifying evidence arrives (journals, labs, vitals, clinician notes), allow the Stack to re-activate in Band computation.    
   \* Allow clinician manual re-enable or extension; treat these as auditable actions.    
7\. \*\*Apply safety override for MD Toggle\*\*:    
   \* If the patient enters Zone 5 / critical instability (critical band), MD toggles are overridden and cannot mask critical instability.    
8\. \*\*Apply non-destructive semantics\*\*:    
   \* Suppression must not delete or overwrite raw data; it only affects whether a Stack participates in current Band computation.    
9\. \*\*Emit outputs\*\*:    
   \* Output the unified suppression state (\`pauseFlag\`, \`pauseReason\`) to Module 6\\.    
   \* Emit audit-ready events to Module 41 and Appendices C.7/C.11.    
10\. \*\*Enforce state alignment\*\*:    
\* Ensure \`pauseFlag\` / \`pauseReason\` are consistent across Daily Stability Band Observations (Module 6), State snapshots (Module 11), and the Suppression trail (Module 41).

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* M8 must use the canonical locked suppression fields as defined in Appendix H.2 (\`pauseFlag\`, \`pauseReason\`, \`pauseStartTimestamp\`, \`pauseEndTimestamp\`, \`pauseSourceModule\`).    
\* \`pauseReason\` must be a single enum value from \`{SymbolicFlare, Overshoot, HealingPain, LabError, MD\_Toggle}\`, with the single-reason invariant enforced; priority choice across multiple candidates must be selected via Appendix F.9.    
\* Clinician MD toggles are session-default unless explicitly extended, and must not mask Zone 5 / critical instability (override when critical band occurs).    
\* Suppression is non-destructive and must not delete/overwrite raw data.    
\* M8 does not set TTL defaults, priority ladder values, or resolution taxonomy; Appendix F.9 is authoritative for those policies.    
\* No appendix in M8’s orbit is allowed to encode disease facts, medication details, or guideline algorithms.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Module 5 (psychosomatic triggers: SymbolicFlare, persona flags, PSI).    
\* Module 7A (QA triggers: LabError, Overshoot, HealingPain).    
\* Module 6 (consumer of unified suppression state; daily stability band observations for alignment).    
\* Module 11 (state snapshots for alignment).    
\* Module 41 (suppression lifecycle logging / QA labeling / feedback loops; audit schema integration).    
\* Appendix H.2 (locked suppression fields).    
\* Appendix F.8 (MD Toggle orchestration rules: lifecycle, safety override, priority resolution, FHIR mappings; M8 aligned).    
\* Appendix F.9 (reflex suppression policy: canonical reasons, priority ladder, TTL defaults, resolution taxonomy).    
\* Appendices C.7 / C.11 (FHIR suppression and AuditEvent/Provenance artifacts; audit-ready events).

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* Every clinician toggle action (activate, re-enable, extend) must be auditable.    
\* Audit-ready suppression/toggle events must be emitted to Module 41 and Appendices C.7/C.11 for longitudinal tracking and QA.    
\* \`pauseFlag\` / \`pauseReason\` must be consistent across Module 6 daily observations, Module 11 state snapshots, and the Module 41 suppression trail.    
\* Suppression records must preserve non-destructive semantics (suppression affects participation in Band computation; raw data is not deleted/overwritten) as part of traceability expectations.

\# \*\*V5.2 M9 — Reflex Suppression Core (Unified pauseFlag Governance)\*\*

\#\#\# \*\*Purpose\*\*

Module 9 is the single authoritative reflex suppression engine for the stack. It standardizes how \`pauseFlag\` and \`pauseReason\` are set, prioritized, time-boxed, audited, and exposed downstream so noise does not produce false escalations. It enforces a deterministic priority ladder, TTL/time-box, and an IDLE → ACTIVE → RESOLVE state machine with hard safety guardrails (e.g., Band-5 cannot be masked).

\#\#\# \*\*Scope\*\*

\*\*In scope\*\*

\* Setting and maintaining unified suppression state via \`pauseFlag\` \\+ \`pauseReason\` with priority and TTL attached.    
\* Enforcing reason priority ladder and single-active-suppression invariant.    
\* TTL/time-box behavior, re-arm rules, and forced resolution after max duration.    
\* Band-freezing integration when suppression is active.    
\* Critical safety invariant: suppression is blocked/cleared when Stability Band \\== 5 persists ≥7 days.    
\* Emitting audit/provenance events for activation, renewal, and resolution to Module 41\\.

\*\*Out of scope\*\*

\* Computing PSI or persona/psychosomatic semantics (owned elsewhere).    
\* Computing Stability Score/Band or Stack (owned elsewhere).    
\* Any guideline/disease facts, drug tables, lab thresholds, lab ontology, phenotype dictionaries, or static interpretation tables (not resident in M9).    
\* Driving patient UI or generating tasks/care plan actions (owned elsewhere).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`patient\_id\`    
\* \`timestamp\_now\`    
\* \`stabilityBand.prev\_band\`    
\* \`stabilityBand.new\_band\`    
\* \`safety\_flags.critical\` (boolean)    
\* \`band5\_persistence\_days\` (integer days in Band 5\\)    
\* \`suppression\_candidates\[\]\` (zero or more), each with:    
  \* \`candidate.pauseReason\` ∈ {\`SymbolicFlare\`,\`Overshoot\`,\`HealingPain\`,\`LabError\`,\`MD\_Toggle\`,\`CriticalOverride\`}    
  \* \`candidate.source\_module\_id\` (e.g., M5/M7A/M8A)    
  \* \`candidate.evidence\_ref\_ids\[\]\` (pointers to upstream outputs)    
  \* \`candidate.detected\_at\` (timestamp)    
\* Current suppression state (if any):    
  \* \`pauseFlag\` (boolean)    
  \* \`pauseReason\` (enum)    
  \* \`pauseStartTimestamp\`    
  \* \`pauseEndTimestamp\` (if resolved)    
  \* \`pauseSourceModule\`    
  \* \`ttl\_remaining\_hours\` (numeric)    
  \* \`last\_review\_timestamp\` (timestamp)    
  \* \`last\_renewal\_timestamp\` (timestamp)    
  \* \`last\_resolution\_outcome\` ∈ {\`confirm\`,\`lift\`,\`escalate\`}    
  \* \`active\_reason\_dedupe\_key\` (derived)

\#\#\# \*\*Outputs\*\*

\* Updated suppression state:    
  \* \`pauseFlag\`    
  \* \`pauseReason\`    
  \* \`pauseStartTimestamp\`    
  \* \`pauseEndTimestamp\` (set on resolution)    
  \* \`pauseSourceModule\`    
  \* \`ttl\_remaining\_hours\`    
  \* \`suppression\_state\` ∈ {\`IDLE\`,\`ACTIVE\`,\`RESOLVE\`}    
\* Band gating output:    
  \* \`stabilityBand.current\_band\` (post-suppression band decision)    
\* Audit emission requests to Module 41:    
  \* \`suppression\_audit\_events\[\]\` (activation/renewal/resolution records with required fields)

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Initialize effective suppression decision context\*\*    
   \* Read \`pauseFlag\`, \`pauseReason\`, \`pauseStartTimestamp\`, TTL state, and \`suppression\_candidates\[\]\`.    
2\. \*\*Apply critical safety guardrail (unsuppressable)\*\*    
   \* If \`safety\_flags.critical \== true\`, then clear/override suppression by setting \`pauseFlag=false\` and \`suppression\_state=IDLE\`.    
   \* If \`band5\_persistence\_days \>= 7\` (Stability Band \\== 5 persisted ≥7 days), then suppression is blocked/cleared and hard alerts proceed; enforce \`pauseFlag=false\` and \`suppression\_state=IDLE\`.    
3\. \*\*Select the active suppression reason (priority ladder)\*\*    
   \* Define the canonical reason order such that the highest candidate reason is active, and \`CriticalOverride\` cannot be masked.    
   \* Deterministically choose \`selected\_reason\` as the highest-priority element present in \`suppression\_candidates\[\]\` using this ladder order:    
     \* \`CriticalOverride\` \\\> \`LabError\` \\\> \`HealingPain\` \\\> \`Overshoot\` \\\> \`MD\_Toggle\` \\\> \`SymbolicFlare\`.    
   \* If no candidates exist, then \`selected\_reason \= null\`.    
4\. \*\*State machine transition\*\*    
   \* If \`selected\_reason \== null\` and \`pauseFlag \== false\`, set \`suppression\_state=IDLE\` and proceed to Step 6\\.    
   \* If \`selected\_reason \!= null\` and \`pauseFlag \== false\`, set \`pauseFlag=true\`, \`pauseReason=selected\_reason\`, set \`pauseStartTimestamp=timestamp\_now\`, set \`pauseSourceModule\` from the candidate that produced \`selected\_reason\`, set \`suppression\_state=ACTIVE\`, and attach TTL per Step 5\\.    
   \* If \`selected\_reason \!= null\` and \`pauseFlag \== true\`:    
     \* If \`pauseReason \!= selected\_reason\`, update \`pauseReason=selected\_reason\`, update \`pauseSourceModule\` accordingly, keep a single active suppression, and set/refresh TTL per Step 5\\.    
     \* If \`pauseReason \== selected\_reason\`, perform dedupe and TTL checks for the same reason and proceed to Step 5\\.    
   \* If \`selected\_reason \== null\` and \`pauseFlag \== true\`, set \`suppression\_state=RESOLVE\`, set \`pauseEndTimestamp=timestamp\_now\`, set resolution outcome to \`lift\`, and then set \`pauseFlag=false\` and return to \`IDLE\`.    
5\. \*\*TTL, auto-review, forced resolution, and re-arm\*\*    
   \* On activation or reason change, set TTL using the defaults:    
     \* Default TTL \\= 72 hours.    
     \* Auto-review at 24 hours.    
     \* Max 7 days before forced resolution.    
   \* If \`pauseFlag \== true\` and TTL has expired or max 7 days has been reached, force resolution by setting \`suppression\_state=RESOLVE\`, emitting resolution outcome (\`lift\` unless resolved otherwise), setting \`pauseEndTimestamp=timestamp\_now\`, and clearing \`pauseFlag=false\`.    
   \* Re-arm is permitted only on new evidence; implement as: do not re-activate after resolution unless \`suppression\_candidates\[\]\` includes a new candidate evidence reference distinct from the prior dedupe key.    
   \* If \`pauseFlag \== true\` and an auto-review is due (24h since activation or last review), emit a renewal event only if new evidence exists; otherwise maintain state until TTL expiry or forced resolution.    
6\. \*\*Band-freezing integration\*\*    
   \* If \`pauseFlag \== true\` and \`stabilityBand.new\_band \> stabilityBand.prev\_band\`, set \`stabilityBand.current\_band \= stabilityBand.prev\_band\`.    
   \* Otherwise, accept the new band by setting \`stabilityBand.current\_band \= stabilityBand.new\_band\`.    
7\. \*\*Audit emission (always on lifecycle events)\*\*    
   \* For any suppression activation, renewal, or resolution, emit structured AuditEvent entries with provenance linking to upstream evidence, and route them to Module 41\\.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* \`pauseFlag\` \\+ \`pauseReason\` are the only suppression surface, with TTL and priority always attached.    
\* Single active suppression per stack at a time; highest-priority candidate reason is always active.    
\* Default TTL is 72h with auto-review at 24h and max 7 days before forced resolution; re-arm only on new evidence.    
\* Band-5 cannot be masked; if Stability Band \\== 5 persists ≥7 days, suppression is blocked/cleared and hard alerts proceed.    
\* M9 is a clean EoH module and must not embed guideline/ontology content, lab thresholds, disease facts, drug tables, or phenotype dictionaries.    
\* M9 does not compute PSI or band scores, does not drive patient UI, and does not generate tasks; it only gates signals via suppression.    
\* Appendix H.2 is authoritative for suppression field definitions and allowed enums; Appendix F.8/F.9 are authoritative for platform-wide suppression policy; Appendix C.4 is authoritative for FHIR mapping.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Consumes\*\*    
  \* Module 5 (psychosomatic candidate: \`SymbolicFlare\`).    
  \* Module 7A (QA candidate: \`LabError\`, \`Overshoot\`, \`HealingPain\`).    
  \* Module 8A (clinician toggle candidate: \`MD\_Toggle\`).    
  \* Module 6 / Module 20 safety flags (consumes \`safety\_flags.critical\` and Band-5 persistence signals).    
\* \*\*Produces / writes to\*\*    
  \* Module 41 (suppression lifecycle audit trail, QA labeling, governance feedback).    
  \* Module 48 (consumes outcomes for governance adjustments).    
\* \*\*Appendices\*\*    
  \* Appendix H.2 (locked field definitions for \`pauseFlag\`/\`pauseReason\`).    
  \* Appendix F.8 / F.9 (MD toggle rules; suppression policy: priority ladder, TTL defaults, resolution taxonomy).    
  \* Appendix C.4 (FHIR mapping authority for suppression context surfaces).

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* \*\*Activation (every time suppression becomes active)\*\*    
  \* \`pauseFlag\`, \`pauseReason\`, \`pauseStartTimestamp\`, \`pauseSourceModule\`, \`stabilityBand\` at activation time.    
  \* Triggering evidence pointer(s) (IDs from originating modules such as M5/M7A/M8A).    
\* \*\*Renewal\*\*    
  \* Updated TTL remaining, current band, and rationale for renewal (new evidence vs policy default).    
\* \*\*Resolution\*\*    
  \* Outcome ∈ {\`confirm\`,\`lift\`,\`escalate\`}, \`pauseEndTimestamp\`, final band, and whether a critical event occurred.    
\* \*\*Safety guardrails\*\*    
  \* Detection that Band-5 persisted ≥7 days and corresponding forced clearing of suppression.    
\* \*\*QA and learning linkage\*\*    
  \* Links to Module 41 QA labels (true-positive vs false-positive suppression) and downstream governance tuning linkage to Module 48\\.    
\* \*\*FHIR surfaces\*\*    
  \* Observation extensions for suppression context and DetectedIssue/AuditEvent entries consistent with Appendix C.4 and Appendix H.2.

\# \*\*V5.2 M10 — Escalation & Clinician Alerting\*\* 

\#\#\# \*\*Purpose\*\*

Module 10 is Ethos-of-Health’s escalation router: it guarantees that safety-critical events are surfaced to clinicians/care teams in a timely, auditable, interoperable way.    
It does \*\*not\*\* interpret clinical meaning; it enforces a fail-safe guarantee that when upstream thresholds are crossed and suppression rules allow, an alert is delivered.    
It is suppression-aware (\`pauseFlag\`/\`pauseReason\`) and ensures complete audit/provenance capture.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Suppression gating of escalation when \`pauseFlag\` is active, with reason logged.    
\* Event classification into a recorded category (e.g., Zone5/Rollback/Conflict/Harm) without interpreting clinical meaning.    
\* Escalation packet assembly and routing fan-out to dashboard, on-call, and external push.    
\* Deduplication/throttling of identical repeats without drops.    
\* Audit logging, provenance capture, and interop outputs via referenced FHIR resources.

\*\*Out of scope\*\*

\* Clinical interpretation of events or determination of clinical meaning.    
\* Acting on raw symptom noise or unvalidated inputs.    
\* Defining suppression policy rules, suppression field definitions, or FHIR bindings (referenced only).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`pauseFlag\` (boolean)    
\* \`pauseReason\` (enum/code)    
\* Escalation trigger event (validated) with:    
  \* \`patient\_id\`    
  \* \`category\`    
  \* \`severity\`    
  \* \`source\_module\`    
  \* \`timestamp\` (event time)    
\* Upstream provenance pointers:    
  \* upstream module IDs    
  \* contributing evidence references

\#\#\# \*\*Outputs\*\*

\* Escalation decision outcome: \`escalated\` or \`suppressed\` (no silent drops).    
\* Escalation packet (for escalated events): \`{patient\_id, category, severity, source\_module, timestamp}\`.    
\* Routing actions executed for escalated packets: dashboard / on-call / external push.    
\* Interop artifacts: FHIR resources (Communication/Task/Flag or DetectedIssue) via Appendix F.10 references.    
\* Audit artifacts: AuditEvent entries plus Ethos Vault logging.

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Accept validated event input only\*\*; ignore raw symptom noise.    
2\. \*\*Apply suppression gate\*\*:    
   \* If \`pauseFlag\` is active, hold escalation and mark outcome as \`suppressed\`; record \`pauseReason\`.    
3\. \*\*Classify/record event category\*\* (e.g., Zone5/Rollback/Conflict/Harm) as an event label without interpreting clinical meaning.    
4\. \*\*Fail-safe semantics\*\*: if the event is ambiguous, escalate unless suppression is explicitly active.    
5\. \*\*Assemble escalation packet\*\* containing \`patient\_id\`, \`category\`, \`severity\`, \`source\_module\`, \`timestamp\`.    
6\. \*\*Attach provenance\*\*: include upstream module IDs and contributing evidence references in the alert payload.    
7\. \*\*Deduplicate without drops\*\*: throttle identical repeat events but do not drop them.    
8\. \*\*Route fan-out for escalated packets\*\* to dashboard, on-call, and external push channels.    
9\. \*\*Emit interoperability outputs\*\* as FHIR resources (Communication/Task/Flag or DetectedIssue) using canonical mappings in Appendix F.10.    
10\. \*\*Log outcome for every event\*\* (escalated/suppressed) to AuditEvent and Ethos Vault, including timestamps for event and alert emission.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Suppression policy rules are referenced, not duplicated; Appendix F.9 is the suppression policy authority.    
\* Suppression field definitions are referenced; Appendix H.2 is authoritative for \`pauseFlag\`/\`pauseReason\`.    
\* FHIR bindings are referenced via Appendix F.10 rather than restated in module logic.    
\* Module 10 does not interpret clinical meaning; it routes validated events and enforces fail-safe delivery guarantees.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Appendix F.9 — suppression policy authority.    
\* Appendix H.2 — \`pauseFlag\`/\`pauseReason\` authoritative definitions.    
\* Appendix F.10 — canonical FHIR mappings for escalation outputs.    
\* AuditEvent \\+ Ethos Vault logging surfaces (as referenced in module requirements).

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* Every event outcome: escalated vs suppressed (no silent drops).    
\* If suppressed: \`pauseFlag\` and \`pauseReason\`.    
\* Upstream provenance: upstream module IDs and contributing evidence included in alert payloads.    
\* Routing targets executed for escalated packets: dashboard/on-call/external push.    
\* Interop artifacts: FHIR resource types used (Communication/Task/Flag/DetectedIssue) and binding profile references (Appendix F.10).    
\* Time: timestamp of event and timestamp of alert emission.    
\* Dedup/throttle actions (if applied): record that throttling occurred without dropping events.

\# \*\*V5.2 M11 — Suppression-Aware Patient Guidance & Containment Orchestrator\*\*

\#\#\# \*\*Purpose\*\*

Module 11 is the patient-facing containment layer that converts upstream suppression events (\`pauseFlag\`/\`pauseReason\`) into supportive patient guidance (reflective prompts, coping supports, neutral education) without escalating clinicians.    
It exists to ensure suppression is not silent: patients remain engaged and supported during “pause” windows.    
It is explicitly non-escalatory; any crisis-level signal bypasses to Module 10\\.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Convert \`pauseFlag\`/\`pauseReason\` suppression context into patient-facing containment guidance categories.    
\* Apply safety override routing: if crisis tags present, exit containment and forward to Module 10\\.    
\* Create time-boxed check-ins during suppression to maintain continuity and improve data fidelity.    
\* Emit patient communications, optional questionnaires, and tasks, with AuditEvent \\+ Provenance for each artifact.

\*\*Out of scope\*\*

\* Any clinician escalation workflow other than crisis bypass to Module 10\\.    
\* Adjusting bands or modifying upstream suppression policy/TTL logic.    
\* Defining crisis taxonomy or embedding crisis definitions.    
\* Embedding patient-content catalogs within this module.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`pauseFlag\` (boolean)    
\* \`pauseReason\` (enum): \`{SymbolicFlare, Overshoot, HealingPain, LabError, MD\_Toggle}\`    
\* \`PSI\` (Psychosomatic Index) from Module 5    
\* Suppression timer context from Module 9    
\* \`confidence\` from Module 7A    
\* Band/drift context from Module 6    
\* Crisis tags present (boolean / tag set indicator)

\#\#\# \*\*Outputs\*\*

\* Patient-facing message category selection (containment category)    
\* Patient communications (message artifacts)    
\* Optional questionnaires    
\* Tasks (patient-facing)    
\* Check-in schedule parameters (time-boxed; e.g., 12–24h)    
\* Crisis bypass routing decision and downstream target (Module 10\\)    
\* AuditEvent \\+ Provenance linkages for each generated artifact

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. Read inputs: \`pauseFlag\`, \`pauseReason\`, PSI, suppression timer context, confidence, band/drift context, and crisis tag presence.    
2\. If crisis tags are present, exit containment and forward to Module 10; record that crisis-bypass fired and the downstream routing target.    
3\. Otherwise, select a patient containment category by mapping \`pauseReason\` as follows:    
   \* \`SymbolicFlare\` → reflective prompts / reframing nudges    
   \* \`Overshoot\` or \`HealingPain\` → pacing \\+ reassurance \\+ transient education    
   \* \`LabError\` → re-test guidance \\+ neutral reassurance    
   \* \`MD\_Toggle\` → neutral acknowledgment of clinician override    
4\. Create suppression time-boxed check-ins to maintain continuity and improve data fidelity (e.g., a 12–24h reflective prompt), using suppression timer context as available.    
5\. Emit patient-facing outputs (communications \\+ optional questionnaires \\+ tasks) consistent with the selected containment category.    
6\. For each generated artifact, write AuditEvent \\+ Provenance linkages, capturing the suppression context and the contextual inputs used (PSI, confidence, band/drift context where available).

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Module 11 is patient-facing and non-escalatory; any crisis-level signal bypasses to Module 10\\.    
\* Module 11 does not escalate and cannot adjust bands.    
\* Do not duplicate field locks or canonical field definitions; \`pauseFlag/pauseReason\` governance is referenced from Appendix H.2.    
\* Do not embed patient-content catalogs inside this module; content libraries remain centralized (Appendix H.3).    
\* Do not embed crisis definitions; only retain the bypass mechanism, with crisis taxonomy externalized (Module 10 / MKE).

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Module 5 (PSI input)    
\* Module 6 (band/drift context input)    
\* Module 7A (confidence input)    
\* Module 9 (suppression timer context input)    
\* Module 10 (crisis bypass routing target)    
\* Appendix H.2 (pauseFlag/pauseReason governance)    
\* Appendix H.3 (patient-content libraries centralized)

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* \`pauseFlag\`, \`pauseReason\`, and suppression timer context at time of action.    
\* PSI value and (where available) confidence \\+ band/drift context used to contextualize containment.    
\* Whether crisis-bypass fired (yes/no) and downstream routing target (Module 10).    
\* Chosen patient message category and check-in schedule parameters (e.g., 12–24h).    
\* AuditEvent \\+ Provenance linkages for each generated artifact.

\# \*\*V5.2 M12 — Symptom Narrative Engine\*\*

\#\#\# \*\*Purpose\*\*

Module 12 exists solely to transform multi-source patient text into a structured, audit-ready narrative digest that preserves patient voice while exposing clinically usable structure. It ingests tags, PSI, stability band, and suppression context from upstream modules and emits a FHIR-native bundle: narrative digest, coded symptom observations, and a unified provenance chain.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Aggregate all patient entries for the period and summarize free text with focus on symptoms, progression, and context.    
\* Normalize tags using an external lexicon.    
\* Suppression-aware narrative behavior where suppressed events are annotated, not deleted, and narrative reflects “seen but suppressed” episodes.    
\* Voice-preservation and bias controls that preserve emotional and psychosocial descriptors and cannot erase distress cues to “sanitize” the record.    
\* Temporal clinical compression (time-bounded daily/weekly summaries; favor new/worsening; mark improvement).    
\* Provenance & FHIR mapping: DocumentReference, ClinicalImpression, Observations, Provenance, AuditEvent linking outputs back to raw entries and ruleset version.

\*\*Out of scope\*\*

\* Guideline logic, disease-specific rules, drug classes, or lab-interpretation tables.    
\* Deciding diagnoses or recalculating bands.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* Patient text sources for the summarization period:    
  \* Journal entries (free text)    
  \* PRO text entries (free text)    
\* Upstream context fields:    
  \* Normalized tags (from Module 4\\)    
  \* PSI (from Module 5\\)    
  \* Stability band (from Module 6\\)    
  \* Suppression state: \`pauseFlag\`, \`pauseReason\` (from Module 9\\)    
\* Governance/version inputs:    
  \* \`ruleset\_version\`    
  \* External lexicon identifier/version (for tag normalization)

\#\#\# \*\*Outputs\*\*

\* FHIR-native bundle containing:    
  \* DocumentReference: narrative digest    
  \* ClinicalImpression: structured narrative assessment    
  \* Observation resources: discrete symptom findings    
  \* Provenance resources linking raw entries → tags → digest phrases → Observations/ClinicalImpressions    
  \* AuditEvent for the summarization run

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. Aggregate all patient entries for the period.    
2\. Normalize tags using external lexicon.    
3\. Summarize free text with focus on symptoms, progression, and context.    
4\. Attach \`band\`, \`psi\`, and suppression state (\`pauseFlag\`, \`pauseReason\`) to the summary object.    
5\. Apply suppression-aware narrative behavior:    
   \* Suppressed events are annotated, not deleted.    
   \* Narrative explicitly reflects “seen but suppressed” episodes so trajectory modules can see both raw experience and system-level caution.    
6\. Apply voice-preservation & bias controls:    
   \* Preserve emotional and psychosocial descriptors in the digest or annotations.    
   \* Do not erase distress cues during compression.    
7\. Apply temporal clinical compression:    
   \* Favor new/worsening signals, de-emphasize stable background noise, and explicitly mark improvement.    
   \* Emit time-bounded summaries (daily/weekly) so flares and recoveries appear as clear trajectory segments.    
8\. Build a provenance map linking summary elements to source inputs, including raw entries → tags → digest phrases → Observations/ClinicalImpressions.    
9\. Emit FHIR resources:    
   \* Create DocumentReference for the digest.    
   \* Create ClinicalImpression for structured narrative assessment.    
   \* Create Observations for discrete symptom findings.    
   \* Create Provenance and AuditEvent linking outputs back to raw entries and ruleset version.    
10\. Version control:    
\* Tie every run to \`ruleset\_version\`.    
\* Log AuditEvents for each summarization run with inputs and outputs.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Does not embed guideline logic, disease-specific rules, drug classes, or lab-interpretation tables; all such knowledge is external.    
\* Job is to compress, normalize, and annotate, not to decide diagnoses or recalculate bands.    
\* Suppressed events are annotated, not deleted.    
\* Compression rules cannot erase distress cues to “sanitize” the record.    
\* Any governance actions tied to the run (e.g., lexicon drift flags, QA feedback events) are routed via Module 48/19, not embedded logic.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Upstream:    
  \* Module 4 (tags)    
  \* Module 5 (PSI)    
  \* Module 6 (band/drift)    
  \* Module 9 (suppression)    
\* Downstream:    
  \* Module 13 (pattern detection)    
  \* Module 26A (prognostic vectors)    
  \* UI router and governance modules (M43/M48) for display and version tracking    
\* Governance routing:    
  \* Module 48/19 for lexicon drift flags and QA feedback events

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* \`ruleset\_version\` used for each summarization run.    
\* Input source references: journal entries, PROs, tags, and upstream modules contributing context (4/5/6/9).    
\* \`band\`, \`psi\`, \`pauseFlag\`, \`pauseReason\` at time of summarization.    
\* Provenance links between raw entries → tags → digest phrases → Observations/ClinicalImpressions.    
\* AuditEvent for each run capturing timestamp, ruleset\\\_version, initiating module/context, and key outcome (summary created, errors, or skipped).    
\* Any governance actions tied to the run routed via Module 48/19 (e.g., lexicon drift flags, QA feedback events) are logged as such and not embedded as module logic.

\# \*\*V5.2 M13 — Trend & Prognostic Engine\*\*

\#\#\# \*\*Purpose\*\*

Module 13 converts upstream multi-modal patient features into time-aware prognostic trajectories spanning short-, medium-, and long-term horizons. It detects slopes, volatility, and cumulative burden relative to Original Healthy Baseline (OHB), then expresses these as prognostic indices (flare probability, relapse risk, comorbidity trajectory) with explainers. It persists schema-stable \`mpa\_vector\` objects and associated explainer bundles so downstream modules can reuse aligned vectors across model generations.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Feature transformation from upstream state/narrative/labs/monitors into longitudinal trajectory features.    
\* Rolling window aggregates at multiple time scales.    
\* Slopes and volatility vs OHB, including acceleration/deceleration.    
\* Composite metrics for inflammatory burden, fatigue trajectory, and adherence slope.    
\* Horizon-specific probabilities for flare/instability, relapse/response, and long-term disease/comorbidity trajectories.    
\* Versioned vectorization (\`mpa\_vector\`), idempotency tagging, deterministic recompute with same inputs.    
\* Explainability bundle creation (SHAP-like attributions, visualization hooks, NL summaries tied to drivers).    
\* Suppression awareness via carry-forward of pause flags with annotation (not data erasure).    
\* Emission of FHIR/EHR anchors (Observation, RiskAssessment, DocumentReference).

\*\*Out of scope\*\*

\* Ownership of canonical vector governance rules beyond referencing Appendix F.13.    
\* Ownership of \`pauseFlag\` / \`pauseReason\` definitions and TTL semantics (delegated).    
\* Ownership of extended FHIR trajectory representations (delegated).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`patient\_id\`    
\* \`time\_window\` (the evaluation period for trend computation)    
\* From Module 4/5:    
  \* \`tags\[\]\`    
  \* \`PSI\`    
  \* \`symbolic\_flags\[\]\`    
\* From Module 6:    
  \* \`stabilityBand\`    
  \* \`drift\`    
\* From Module 12:    
  \* \`narrative\_digest\`    
  \* \`harmonized\_labs\[\]\`    
\* From Module 20/21:    
  \* \`relapse\_monitors\`    
  \* \`taper\_monitors\`    
  \* \`baselines\` (including OHB reference inputs as needed for “vs OHB” computations)    
\* From Module 26A:    
  \* \`inference\_context\`    
\* From Module 45:    
  \* \`canonical\_unified\_MPA\_vector\`    
\* Suppression context (carried through for annotation):    
  \* \`pauseFlag\`    
  \* \`pauseReason\`

\#\#\# \*\*Outputs\*\*

\* \`mpa\_vector\` (schema-stable, versioned)    
\* Prognostic indices:    
  \* \`flare\_probability\` (horizon-specific)    
  \* \`relapse\_risk\` (horizon-specific)    
  \* \`comorbidity\_trajectory\` (long-term horizon)    
\* \`feature\_snapshots\` persisted in Module 21    
\* \`explainer\_bundle\`:    
  \* driver attributions (SHAP-like)    
  \* visualization hooks (risk cones, driver bars)    
  \* natural-language summary tied to driver clusters    
\* FHIR/EHR anchors:    
  \* \`Observation\`    
  \* \`RiskAssessment\`    
  \* \`DocumentReference\`

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest inputs\*\* for the evaluation \`time\_window\`, including tags/PSI/symbolic flags, stability band/drift, narrative digest and harmonized labs, relapse/taper monitors and baselines, inference context, and canonical unified MPA vector.    
2\. \*\*Generate rolling window aggregates\*\* at multiple time scales from the ingested, time-indexed inputs.    
3\. \*\*Compute trajectory features vs OHB\*\*:    
   \* slopes vs OHB,    
   \* volatility vs OHB,    
   \* acceleration/deceleration vs OHB.    
4\. \*\*Compute composite metrics\*\*:    
   \* inflammatory burden,    
   \* fatigue trajectory,    
   \* adherence slope.    
5\. \*\*Generate horizon-specific prognostic probabilities\*\* for:    
   \* flare/instability,    
   \* relapse/response,    
   \* long-term disease and comorbidity trajectories.    
6\. \*\*Assemble the schema-stable \`mpa\_vector\`\*\* containing the computed trajectory features, composites, and horizon outputs, and attach:    
   \* \`vector\_version\`,    
   \* \`idempotency\_key\`,    
     ensuring deterministic recompute when inputs are unchanged.    
7\. \*\*Create the explainer bundle\*\* for the run:    
   \* SHAP-like driver attributions,    
   \* visualization hooks (risk cones, driver bars),    
   \* natural-language summaries tying trajectory changes to driver clusters.    
8\. \*\*Apply suppression awareness as annotation\*\*:    
   \* carry forward \`pauseFlag\` / \`pauseReason\` into the vector and explainer context as annotations,    
   \* do not erase underlying data or computed features solely due to suppression context.    
9\. \*\*Persist outputs\*\*:    
   \* write \`mpa\_vector\`,    
   \* write \`feature\_snapshots\` to Module 21,    
   \* emit FHIR/EHR anchors (Observation, RiskAssessment, DocumentReference),    
   \* emit \`explainer\_bundle\`.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Canonical vector governance and versioning rules are governed by Appendix F.13.    
\* \`pauseFlag\` / \`pauseReason\` definitions and TTL semantics are governed by Appendix H.2 and Module 11\\.    
\* Extended FHIR longitudinal trajectory representations are defined in Appendix C.4.    
\* No additional governance or appendix rules are authored locally in this module; non-local policy is delegated to the referenced appendices/modules.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Upstream modules: M4, M5, M6, M12, M20, M21, M26A, M45.    
\* Downstream modules: M14, M19, M24, M26A.    
\* Appendices: Appendix F.13, Appendix H.2, Appendix C.4.    
\* Suppression governance module reference: M11.

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* \`vector\_version\` and \`idempotency\_key\` for each run.    
\* Input lineage references identifying which upstream module outputs were used for the run (M4/5 tags/PSI/flags; M6 band/drift; M12 digest/labs; 20/21 monitors/baselines; 26A inference context; 45 canonical vector).    
\* Computed trajectory artifacts for the run:    
  \* rolling window aggregate identifiers,    
  \* slopes/volatility/acceleration vs OHB,    
  \* composite metrics (inflammatory burden, fatigue trajectory, adherence slope),    
  \* horizon-specific probabilities.    
\* Explainability artifacts:    
  \* driver attributions,    
  \* visualization hook payloads (risk cones, driver bars),    
  \* NL explanation tied to driver clusters.    
\* Suppression context captured as annotation (\`pauseFlag\`, \`pauseReason\`) and confirmation that suppression handling was non-destructive.    
\* References/IDs for emitted FHIR/EHR anchors (Observation, RiskAssessment, DocumentReference) and where feature snapshots were persisted (Module 21).

\# \*\*V5.2 M14 — Action & Escalation Engine\*\* 

\#\#\# \*\*Purpose\*\*

Module 14 is the operational bridge between prognostic intelligence and action: it ingests forecasts, stability trends, psychosomatic context, and suppression states, then converts them into tiered, dual-channel outputs (patient guidance \\+ clinician tasks).    
It harmonizes all upstream severity notions into a unified risk taxonomy (T0–T4) and sequences safe action: when to nudge, when to escalate, and when to hand off to crisis engines or care planning modules.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Input aggregation across prognostic indices, stability/stack signals, PSI, suppression flags, trajectory features, and context/preferences into a single orchestration envelope.    
\* Tier harmonization onto T0–T4 with the constraint that no module can bypass tier alignment.    
\* Suppression-aware routing using a single \`pauseFlag\` with coded reasons, producing supportive patient content and clinician-facing suppression context, with no silent drops.    
\* Dual-channel action generation (patient narrative \\+ clinician payload) derived from canonical taxonomies.    
\* Audit and provenance emission for every decision path, including “no action.”    
\* Handoff routing to Modules 10, 15/19, 43/44, and 47 per tier and persistence rules.

\*\*Out of scope\*\*

\* Any disease-specific rules, guideline citations, drug class tables, contraindication lists, ontology mirrors, phenotype dictionaries, or lab interpretation tables.    
\* Defining tier tables, suppression reason dictionaries, TTLs, or FHIR field definitions (these are referenced, not duplicated).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`risk\_indices\` (from Module 13).    
\* \`volatility\_indices\` (from Module 13).    
\* \`stabilityBand\` (from Modules 6, 11).    
\* \`stack\_shifts\` (from Modules 6, 11).    
\* \`psi\_score\` (PSI / psychosomatic index from Modules 5, 11).    
\* \`symbolic\_flags\` (e.g., persona flags such as FalseRecoveryPersona, from Modules 5, 11).    
\* \`pauseFlag\` (Boolean suppression state).    
\* \`pauseReason\` (coded suppression reason; enum governed elsewhere).    
\* \`trajectory\_features\` (slopes, inflection points, trajectory breaks; from Modules 10, 13, 26A).    
\* \`alert\_fatigue\_settings\` (configuration).    
\* \`communication\_preferences\` (configuration).    
\* \`context\_preferences\` (patient/context preferences).

\#\#\# \*\*Outputs\*\*

\* \`risk\_tier\` (T0–T4).    
\* \`patient\_action\_bundle\` (tiered patient guidance narrative, derived from canonical taxonomies).    
\* \`clinician\_action\_bundle\` (tiered clinician payload / recommended action class, derived from canonical taxonomies).    
\* \`handoff\_targets\[\]\` (may include Module 10; Module 15/19; Modules 43/44; Module 47).    
\* \`suppression\_event\` (suppression and override events routed into Module 41 / Appendix C.11.1 surface).    
\* \`audit\_events\[\]\` (including \`AlertGenerated\`, \`AlertSuppressed\`, or explicit “no action”).    
\* \`provenance\_records\[\]\` (links inputs, driver features, modules, and versions).    
\* \`fhir\_delivery\_artifacts\[\]\` (FHIR-aligned outputs via Appendix C.4 / Module 47).

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest inputs\*\* listed in “Inputs,” including prognostic indices, stability/stack signals, PSI/symbolic flags, suppression state, trajectory features, and context/preferences.    
2\. \*\*Build an orchestration envelope\*\* by combining the ingested signals into a single action-planning context object for this evaluation cycle.    
3\. \*\*Harmonize severity to T0–T4\*\* by normalizing all upstream severity signals onto the T0–T4 taxonomy and enforcing that no downstream output is produced without tier alignment.    
4\. \*\*Apply suppression-aware routing\*\* using the single \`pauseFlag\` and coded reason:    
   \* If suppression is active, generate supportive patient content and a clinician-facing suppression-aware explanation, and ensure the event is not silently dropped.    
5\. \*\*Generate dual-channel outputs\*\* using \`risk\_tier \+ psi\_score \+ context\_preferences\`:    
   \* Produce a patient narrative (tone/urgency/detail).    
   \* Produce a clinician payload with a recommended action class.    
6\. \*\*Enforce human-in-the-loop controls\*\*: if the tiered action would be above T2, mark the clinician pathway as requiring explicit clinician review/sign-off, and allow acknowledgment/snooze/override semantics through the appropriate UI/implementation surfaces.    
7\. \*\*Apply handoff rules\*\* based on tier/persistence classification:    
   \* If \`risk\_tier \== T4\`, route to Module 10\\.    
   \* If persistent high-tier alerts are present, route toward Module 15/19 for CarePlan changes.    
   \* For significant alerts, emit downstream hooks to Modules 43/44 (documentation triggers) and Module 47 (FHIR gateway).    
8\. \*\*Emit audit \\+ provenance for every path\*\* (including “no action”):    
   \* Create an \`AuditEvent\` with event type (\`AlertGenerated\`, \`AlertSuppressed\`, or explicit “no action”), responsible tier, action class, and whether clinician review is required.    
   \* Create \`Provenance\` linking to input modules, key driver features (risk indices, band shifts, PSI, suppression flags), and module/version info.    
   \* If suppressed, include \`suppression\_reasons\` and route suppression events into the Reflex Suppression Audit Surface for cross-module visibility.    
9\. \*\*Emit external delivery artifacts\*\* aligned with Appendix C.4 via Module 47, including priority/tier, audience (patient vs clinician), and references back to the originating alert bundle.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Module 14 must remain “clean V5”: it must not embed guideline/disease facts, drug class tables, contraindication lists, ontology mirrors, phenotype dictionaries, or lab interpretation tables.    
\* Module 14 must not re-copy tier tables, suppression reason dictionaries, or FHIR field definitions; it must reference the authoritative appendices/modules.    
\* Suppression-aware behavior must not silently drop events; suppressed events must still produce patient support, clinician context, and audit records.    
\* Module 14 is proactive forecast-driven action, not the crisis engine and not the care-plan composer.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Consumes:\*\* Modules 13, 6, 11, 5, 10, 26A, plus UI/governance settings for alert fatigue, communication preferences, and context.    
\* \*\*Produces / hands off to:\*\* Modules 10, 15/19, 43/44, 47, and logs suppression/override events into Module 41 / Appendix C.11.1 surface.    
\* \*\*Appendix references:\*\* H.3.1, H.3, H.4 (risk tiers and templates); H.2/H.3.2 and Module 11 (suppression governance); C.11.1 and Module 41 (suppression audit surface); C.4 and Module 47 (FHIR mappings); Modules 43/44 (documentation/ADE triggers).

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* \`AuditEvent\` for every outcome path: \`AlertGenerated\`, \`AlertSuppressed\`, or explicit “no action,” including tier, action class, and clinician-review-required flag.    
\* \`Provenance\` linking to input modules (10, 11, 13, 26A), key driver features (risk indices, band shifts, PSI, suppression flags), and module/version identifiers for reproducibility.    
\* For suppression: \`suppression\_reasons\` referencing canonical pauseFlag reasons and routing into the Reflex Suppression Audit Surface for cross-module visibility.    
\* For external delivery: FHIR-aligned artifacts capturing priority/tier, audience, and linkage back to the originating alert bundle (Appendix C.4 / Module 47).

\# \*\*V5.2 M15 — Consolidation Report\*\*

\#\#\# \*\*Purpose\*\*

Module 15 is the Care Plan Composer that turns Ethos risk intelligence (flare windows, trajectories, and escalation tiers) into an actionable, calendarized Care Plan for multi-morbidity patients (Stack ≥3).    
It creates per-condition Tracks, harmonizes them across the Stack, enforces capacity limits (no overload), and integrates escalation tiers (T0–T4) into the schedule.    
Outputs are structured FHIR CarePlan/Task/ServiceRequest objects with full provenance and human-in-loop override, without embedding guideline or disease-specific content.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Compose a calendarized Care Plan for Stack ≥3 by creating per-condition Tracks and harmonizing them into one plan.    
\* Place actions using flare windows and trajectory intelligence, partitioned by time horizon (0–7d, 1–4w, \\\>1m).    
\* Enforce capacity limits and resolve collisions by staggering, rescheduling, or substituting actions.    
\* Carry suppression transparency into the plan (pauseFlag/pauseReason) and expose why items were deferred/throttled.    
\* Support automatic rescheduling on new diagnoses/flares with explicit provenance; require clinician approval prior to execution.

\*\*Out of scope\*\*

\* Embedding guideline content or disease-specific content in the plan.    
\* Defining or recomputing upstream risk intelligence (trajectory/tiers), suppression policy, or patient state classification (consumed inputs only).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \*\*Trajectory intelligence (from M13)\*\*    
  \* \`flare\_risk\_slopes\`    
  \* \`relapse\_probability\`    
  \* \`recovery\_vectors\`    
\* \*\*Tiered action intelligence (from M14)\*\*    
  \* \`tier\` (T0–T4)    
  \* \`suppression\_context.pauseFlag\`    
  \* \`suppression\_context.pauseReason\`    
  \* \`sla.required\_by\_date\` (if provided)    
\* \*\*Patient state (from M11)\*\*    
  \* \`stackLevel\`    
  \* \`stabilityBand\`    
  \* \`cbm\_status\`    
\* \*\*Psychosomatic Index (from M5)\*\*    
  \* \`psi\`    
\* \*\*Intervention history & capacity constraints\*\*    
  \* \`intervention\_history\`    
  \* \`capacity\_constraints\` (fatigue/overlap rules)

\#\#\# \*\*Outputs\*\*

\* \*\*FHIR resources (draft/structured outputs)\*\*    
  \* \`CarePlan\`    
  \* \`Task\`    
  \* \`ServiceRequest\`    
\* \*\*Per-plan metadata\*\*    
  \* \`CarePlan.v\`    
  \* \`module\_version\` (M15.vx.y)    
  \* \`provenance\_links\` to source modules and inputs    
\* \*\*Per-plan-element annotations\*\*    
  \* \`drivers\[\]\`    
  \* \`suppression\_context.pauseFlag\`    
  \* \`suppression\_context.pauseReason\`    
  \* \`tier\` (T0–T4)    
  \* \`sla.required\_by\_date\` (if provided)    
  \* \`lineage.source\_modules\[\]\`

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest canonical inputs\*\*: load trajectory intelligence (M13), tiers \\+ suppression context (M14), patient state (M11), PSI (M5), and intervention history/capacity constraints.    
2\. \*\*Initialize Tracks\*\*: for each active Stack condition, open a Track (sub-plan) and bind it to the condition via \`CarePlan.category\`.    
3\. \*\*Partition timeline horizons\*\*: define three scheduling buckets: immediate (0–7d), short-term (1–4w), long-term (\\\>1m).    
4\. \*\*Place actions using flare windows/trajectories\*\*: for each Track action derived from M13/M14 context, place the action into the earliest safe slot within its appropriate horizon bucket.    
5\. \*\*Apply cadence modulation\*\*: use PSI as an input that modulates plan cadence during scheduling.    
6\. \*\*Harmonize across the Stack\*\*: merge Tracks into a single calendarized plan while enforcing capacity limits; when collisions occur, resolve by staggering, rescheduling, or substituting actions.    
7\. \*\*Attach suppression transparency\*\*: for each plan element, carry \`pauseFlag/pauseReason\` when actions are deferred or throttled, and ensure the CarePlan explicitly reflects suppression (e.g., SymbolicFlare) so clinicians can see why deferral occurred.    
8\. \*\*Attach provenance \\+ versioning\*\*: for each plan element, populate drivers, tier (T0–T4), SLA constraints if present, lineage to source modules, and include \`CarePlan.v\` plus \`M15.vx.y\`.    
9\. \*\*Human-in-loop gating\*\*: mark interventions as requiring clinician approve/reject prior to execution.    
10\. \*\*Rescheduling behavior\*\*: on new diagnoses/flares, reschedule as required and record who/what changed the plan and when; do not silently change the plan without provenance.    
11\. \*\*Export\*\*: create/update FHIR \`CarePlan/Task/ServiceRequest\` and emit corresponding audit artifacts for delivery to downstream interfaces.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Multi-morbidity targeting: Care Plan composition is for Stack ≥3 patients.    
\* No embedded guideline or disease-specific content in Module 15 outputs.    
\* Capacity enforcement: plans must avoid overload; collisions must be resolved via staggering, rescheduling, or substitution.    
\* Suppression is transparent: suppressed/deferred/throttled actions must carry \`pauseFlag/pauseReason\` and be explicitly reflected, not hidden.    
\* Human-in-loop: clinicians approve or reject interventions prior to execution.    
\* No silent changes: automatic rescheduling on new diagnoses/flares must include provenance of the change actor and timestamp.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Module 5 (Psychosomatic Index)    
\* Module 11 (Patient State: Stack Level, Stability Band, CBM status)    
\* Module 13 (Trajectory Analyzer inputs)    
\* Module 14 (Action Engine tiers T0–T4 \\+ suppression context)    
\* Module 43 (Interface Router) and Module 47 (FHIR Gateway) for delivery/export confirmation

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

For \*\*each CarePlan element\*\*, log at minimum:

\* \`drivers\[\]\` (e.g., flare risk index, Stack Level, Stability Band, PSI, patient capacity)    
\* \`suppression\_context.pauseFlag\` and \`suppression\_context.pauseReason\` (if deferred/throttled)    
\* \`tier\` (T0–T4) and any \`sla.required\_by\_date\` if provided    
\* \`CarePlan.v\` and \`module\_version\` (M15.vx.y)    
\* \`lineage.source\_modules\[\]\` for key inputs and rescheduling events (who/what changed the plan, when)    
\* Export confirmation that \`CarePlan/Task/ServiceRequest\` and \`AuditEvent\` resources were created/updated and delivered to Module 47 or Module 43

\# \*\*V5.2 M16 — Execution Layer (Intervention Guardrails & FHIR Conversion)\*\*

\#\#\# \*\*Purpose\*\*

Module 16 is the execution safeguard and translation layer for Ethos-of-Health: it takes already-scored intervention bundles from Module 22 and converts them into FHIR-compliant draft artifacts while enforcing safety guardrails and override signals.    
It guarantees that no AI-generated action is ever executed autonomously; actions remain provisional until clinicians finalize them through Module 19, with suppressions/vetoes/approvals logged via DocumentReference and AuditEvent.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Translate Module 22 option bundles into FHIR drafts (MedicationRequest, ServiceRequest, Task, Communication/CommunicationRequest, CarePlan/RequestGroup).    
\* Apply execution-time safety guardrails using external safety signals (DDI/contraindication/allergy outputs) and internal EoH policies (pauseFlag, overrides, suppression rules).    
\* Enforce “no autonomous activation” by emitting only draft/proposal execution artifacts and routing to Module 19 for clinician decision.    
\* Store drafts and audit records in EthosVault; represent declined/vetoed options using DocumentReference; emit AuditEvent/Provenance for governance and learning hooks.

\*\*Out of scope\*\*

\* Generating or re-scoring intervention options (owned upstream; M16 validates/translates only).    
\* Embedding guideline text, disease facts, drug fact tables, contraindication lists, lab catalogs, ontology mirrors, phenotype dictionaries, or lab interpretation rules (MKE-owned).    
\* Continuous learning/drift mechanics (re-homed to Module 48).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\*\*Execution request context\*\*

\* \`patient\_id\`    
\* \`condition\_id\`    
\* \`previous\_plan\_id\`    
\* \`action\_intent\` ∈ {\`treatment\_adjustment\`, \`plan\_refresh\`, \`on\_demand\`}    
\* \`currentState\` ∈ {\`Original Healthy Baseline (OHB)\`, \`CBM\`, \`Active Disease State\`}    
\* \`pauseFlag\` (Boolean)    
\* \`pauseReason\` (enum)    
\* clinician override signals (execution-time suppressors)

\*\*Upstream plan bundle (from Module 22\\)\*\*

\* \`plan\_id\`    
\* \`data\_lineage\` (includes upstream module lineage, e.g., Modules 11–14, 22\\)    
\* \`plan\_option\[\]\`, each with required fields:    
  \* \`option\_id\`    
  \* \`label\`    
  \* \`rationale\[\]\`    
  \* \`safety\_flags\[\]\`    
  \* \`expected\_risk\_delta{}\`    
  \* \`plan\_score\`

\*\*External safety / knowledge signals (consumed, not defined)\*\*

\* \`ddi\_findings\[\]\` (with coded severity)    
\* \`contraindications\[\]\` (with coded severities)    
\* allergy conflict outputs (structured)    
\* \`guideline\_alignment\_score\` \\+ guideline rationales/citations (pass-through)    
\* dose-adjustment signals (renal/hepatic) (pass-through as constraints)    
\* monitoring cadence selections from upstream/MKE (pass-through)

\#\#\# \*\*Outputs\*\*

\*\*FHIR draft artifacts (status preparatory)\*\*

\* Draft \`MedicationRequest\` (drug changes)    
\* Draft \`ServiceRequest\` (labs/imaging/monitoring)    
\* Draft \`Task\` (monitoring tasks and patient actions)    
\* Draft \`Communication\` / \`CommunicationRequest\` (patient/clinician messaging)    
\* Draft \`CarePlan\` / \`RequestGroup\` (multi-action bundles)

\*\*Governance / audit artifacts\*\*

\* \`DocumentReference\` for declined/unchosen/vetoed options    
\* \`AuditEvent\` for every suppression, veto, and finalization outcome, with linked \`Provenance\` and \`idempotency\_key\`

\*\*Routing outputs\*\*

\* Handoff package to Module 19 for clinician review/finalization    
\* Safe nudges forwarded to Module 24 (only when applicable per bundle contents)

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest candidate bundle\*\* from Module 22 containing \`plan\_id\`, \`plan\_option\[\]\`, rationale, safety flags, scoring lineage, and upstream \`data\_lineage\`.    
2\. \*\*Compute/assign an \`idempotency\_key\`\*\* for the execution run keyed to \`(patient\_id, condition\_id, previous\_plan\_id)\` and enforce stable outputs within the defined TTL.    
3\. \*\*Validate locked structural constraints\*\* for each \`plan\_option\` (required fields and locked enums in the environment such as \`action\_intent\`, \`currentState\`, \`pauseReason\`).    
4\. \*\*Apply execution guardrails (safety gates)\*\* by consuming external DDI/contraindication/allergy outputs and internal EoH policies (\`pauseFlag\`, overrides, suppression rules).    
5\. \*\*Option-level safety disposition\*\*    
   \* If any DDI/contraindication signal indicates a major/disallowed conflict, \*\*veto\*\* the option for execution.    
   \* If interactions are moderate, \*\*add safety flags\*\* and force “requires\\\_review=true” on the option’s execution posture.    
6\. \*\*Suppression-aware execution behavior\*\*    
   \* If \`pauseFlag=true\` or clinician overrides apply, treat them as execution-time suppressors for active therapeutic changes and \*\*fall back to monitoring-only bundles where pause applies\*\*.    
7\. \*\*Conflict routing\*\*    
   \* If safety or consistency violations are detected that require conflict resolution, route the conflicted bundle/options to \*\*Module 33\*\*.    
8\. \*\*FHIR conversion (draft-only)\*\*    
   \* Convert each allowed proposal into draft FHIR resources using the canonical mapping: MedicationRequest, ServiceRequest, Task, Communication/CommunicationRequest, CarePlan/RequestGroup.    
   \* Ensure all execution artifacts are created with preparatory status (\`status=draft\`, \`intent=proposal\`, or equivalent) and do not auto-transition to active.    
   \* Ensure each draft carries rationale in \`reasonCode\` or narrative fields, provenance link to inputs, and the \`idempotency\_key\` for traceability.    
9\. \*\*Record unchosen/vetoed options\*\*    
   \* For each declined/unchosen/vetoed option, create/attach a \`DocumentReference\` representing the disposition.    
10\. \*\*Persist artifacts\*\*    
\* Store all FHIR drafts and associated audit records in EthosVault; retain unchosen/vetoed artifacts for QA and Module 48 learning.    
11\. \*\*Emit audit spine\*\*    
\* For each option and for the overall run, emit \`AuditEvent\` (and linked \`Provenance\`) covering suppressions, vetoes, and finalization outcomes, including the \`idempotency\_key\`.    
12\. \*\*Handoff\*\*    
\* Route the draft bundle and dispositions to \*\*Module 19\*\* for clinician review and finalization; Module 19 is the only locus where resources become active.    
\* Forward safe nudges (if present) to \*\*Module 24\*\*.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* \*\*No autonomous activation:\*\* all execution artifacts created here remain \`status=draft\` / \`intent=proposal\`; no resource becomes active without explicit clinician action via Module 19\\.    
\* \*\*MKE boundary:\*\* M16 may consume MKE outputs (DDI flags, contraindication codes, guideline scores) but must not define or embed the knowledge itself, and must not retain guideline/drug/disease/lab interpretation content as logic.    
\* \*\*Appendix authority:\*\* execution governance is anchored to Appendix H.16 and F.16; M16 summarizes but does not redefine thresholds.    
\* \*\*Locked field governance:\*\* locked enums/fields for \`action\_intent\`, \`currentState\`, \`pauseReason\`, and \`plan\_option\` are governed centrally and must be preserved.    
\* \*\*Learning boundary:\*\* M16 does not implement learning; it guarantees signal surfaces (AuditEvent/DocumentReference) are complete and reliable for Module 48\\.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Module 22\*\* (source of scored intervention bundles).    
\* \*\*Module 19\*\* (clinician review/finalization; only locus where resources become active).    
\* \*\*Module 33\*\* (conflict resolution for safety/consistency violations).    
\* \*\*Module 24\*\* (receives safe nudges).    
\* \*\*Module 48\*\* (consumes governance/learning hooks from audit outputs).    
\* \*\*Appendix H.16\*\* (Execution Governance Policy).    
\* \*\*Appendix F.16\*\* (Execution Guardrail Mapping).

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

For every execution run, log the following as reconstructible, attributable events:

\* \*\*Proposal lineage:\*\* \`plan\_id\`, \`option\_id\`s, and upstream module lineage (e.g., \`data\_lineage\` listing Modules 11–14, 22\\) recorded in \`Provenance\`/\`AuditEvent\`.    
\* \*\*Safety & suppression:\*\* which safety checks fired (e.g., \`rules\_fired\` like \`ddi\_blocker:major\_interaction\_present\`, contraindication blockers, pauseFlag deferments) and which options were suppressed vs allowed.    
\* \*\*Outcome state per option:\*\* status (shown, chosen, declined, vetoed), reason (clinician choice vs safety veto), timestamp, responsible actor (module/user).    
\* \*\*FHIR artifact linkage:\*\* each draft MedicationRequest/ServiceRequest/Task/Communication/CarePlan references its originating plan/option and points back to M16 \\+ model versions \\+ \`idempotency\_key\` via \`Provenance\`/\`AuditEvent\`.    
\* \*\*Idempotency & TTL enforcement:\*\* logs sufficient to verify identical \`(patient\_id, condition\_id, previous\_plan\_id)\` within TTL produce identical plan bundles unless upstream data changed.    
\* \*\*Learning hooks:\*\* structured flags so Module 48 can distinguish accepted vs rejected vs suppressed vs never-shown options, with associated safety and rationale metadata.

\# \*\*V5.2 M17 — Causal Inference & Relational Mapping (CIR)\*\*

\#\#\# \*\*Purpose\*\*

Module 17 turns validated patient signals (labs, vitals, therapies, narratives, persona flags) into a directed causal graph with edge-level evidence strength and provenance.    
It integrates suppression context (e.g., SymbolicFlare, Overshoot, LabError) and psychosocial factors as mediators/confounders so symbolic flares and lab noise do not masquerade as true biomedical causes.    
Its causal edges feed Module 18 (MPA) for probabilistic multi-pathway forecasts and support Module 14 for explainable patient-facing narratives while remaining fully audit-logged and governable.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Causal graph construction from validated patient signals, including node typing and DAG constraints.    
\* Edge inference criteria using temporal precedence, dose–response, plausibility, statistical association, and confounder adjustment.    
\* Edge-level evidence attribution (strength \\+ type) and provenance IDs for supporting data elements.    
\* Integration of suppression signals (pauseFlag/pauseReason and suppression codes) and psychosocial/persona factors as mediators/confounders into edge creation/updates.    
\* Lifecycle update flow for edge sets, including validation, routing failures to Module 19 QA, vector versioning, and ledger writes to L.3.2.    
\* FHIR interoperability encoding for causal claims using Evidence, GraphDefinition, AuditEvent, and Provenance.    
\* Cross-module wiring: M16 → M17 (AE attributions into edge creation) and M17 → M18 (CIR edges as MPA features).

\*\*Out of scope\*\*

\* Any “world knowledge” (guidelines, disease facts, ontology mirrors, lab interpretation tables, phenotype dictionaries).    
\* Defining suppression field semantics or redefining suppression codes locally (owned elsewhere).    
\* Defining governance thresholds (p-value/AUC thresholds, bias/fairness triggers) locally (owned elsewhere).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* Validated patient signals (labs, vitals, therapies, narratives, persona flags).    
\* Node candidates: observations, labs, persona flags, environmental exposures, therapeutic actions.    
\* Suppression state: \`pauseFlag\`, \`pauseReason\`, and suppression codes (e.g., SymbolicFlare, Overshoot, LabError) sourced via Module 6 \\+ Appendix H.2.    
\* Psychosocial/persona factors used as mediators/confounders (e.g., FalseRecoveryPersona, CollapseLanguage, NarrativeOveridentification).    
\* AE attributions from Module 16 for causal edge creation constraints/inputs.    
\* Governance references for CIR validation and activation gating (Appendix H.18B).    
\* Current CIR vector version and ledger context (L.3.2 / L.3).

\#\#\# \*\*Outputs\*\*

\* Directed causal graph (DAG) with node set and edge set.    
\* For each edge: evidence strength (weak/moderate/strong or probability 0–1), evidence types, and provenance IDs for supporting elements.    
\* Updated CIR edge-set version (vectorVersion) and ledger write to L.3.2.    
\* FHIR-encodable causal claim artifacts using Evidence, GraphDefinition, AuditEvent, Provenance (mapping per Appendix F.17).    
\* AuditEvent emissions for validation failures (\`cir\_bias\_check\`) and for edge lifecycle operations.    
\* Downstream feature feed to Module 18 (MPA) and narrative support to Module 14 (via causal edges).

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest validated inputs\*\*    
   1\. Load validated patient signals and candidate node types (observations, labs, persona flags, environmental exposures, therapeutic actions).    
   2\. Load suppression state (\`pauseFlag\`, \`pauseReason\`, suppression codes) via Module 6 and Appendix H.2 references.    
   3\. Load psychosocial/persona mediator/confounder inputs.    
   4\. Load AE attributions from Module 16 for causal edge creation inputs.    
2\. \*\*Construct/refresh the causal graph\*\*    
   1\. Instantiate/refresh the node set using the supported node types.    
   2\. Propose candidate directed edges using the edge inference criteria: temporal precedence, dose–response, plausibility, statistical association, and confounder adjustment.    
   3\. Enforce DAG constraints, allowing latent variables and suppression overlays in the representation.    
   4\. Incorporate suppression context and psychosocial mediators/confounders into edge creation and updates so symbolic flares and lab noise do not masquerade as biomedical causes.    
3\. \*\*Assign evidence and provenance per edge\*\*    
   1\. For each edge, assign evidence strength (weak/moderate/strong or probability 0–1) and evidence types (observational, experimental, patient narrative, population-level reference).    
   2\. Attach provenance IDs for every supporting data element (observations, narratives, persona flags, AE attributions, priors).    
   3\. Prepare FHIR wiring for Evidence/Provenance (per Appendix F.17).    
4\. \*\*Apply governance and lifecycle validation\*\*    
   1\. Trigger the CIR lifecycle on retraining or feature-update events.    
   2\. Execute the lifecycle snippet unmodified:    
      \* \`version \= getCurrentVector("CIR")\`    
      \* \`validate(edgeSet, metrics=\["pValue","AUC"\])\`    
      \* If validation fails: emit \`AuditEvent("cir\_bias\_check", edgeSet.id)\` and route to \`Module19.QA\`, then return without committing.    
      \* If validation passes: increment \`version \+= 0.1\`, commit edges, and write to ledger \`L.3.2\` with \`validator=currentUser\`.    
   3\. Treat Appendix H.18B as the single source of truth for p-value/AUC thresholds, bias triggers, and fairness requirements used to gate activation of new edges.    
5\. \*\*Publish downstream handoffs\*\*    
   1\. Emit the updated causal edges as features for Module 18 (MPA).    
   2\. Make causal edges available to support explainable narratives in Module 14\\.    
   3\. Persist interoperability artifacts for causal claims using Evidence, GraphDefinition, AuditEvent, and Provenance.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Do not redefine suppression fields or codes locally; reference Appendix H.2 for locked suppression fields and canonical codes.    
\* Do not restate governance thresholds; reference Appendix H.18B for p-value/AUC thresholds, bias triggers, and fairness requirements that gate activation of new edges.    
\* All edge creation/deletion rules require AuditEvent logging and explicit override requirements, and high-confidence edges may be locked such that modification requires governance approval.    
\* CIR is EoH state reasoning and governance (time-based interpretation), not a repository of world facts.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Module 6 (suppression signals into edge creation/updates)    
\* Module 16 (AE attributions feeding causal edge creation)    
\* Module 18 (consumes CIR edges for multi-pathway forecasts)    
\* Module 14 (uses causal edges for explainable narratives)    
\* Module 19 (QA sink for CIR validation failures)    
\* Appendix F.17 (FHIR Evidence/Provenance wiring; CIR interoperability mappings)    
\* Appendix F.17.1 (suppression signals into edge creation/updates)    
\* Appendix F.17.5 (CIR lifecycle snippet)    
\* Appendix H.2 (locked suppression fields)    
\* Appendix H.18B (CIR governance & fairness standards)    
\* Appendix L.3 / L.3.2 (CIR feature library ledger; vector versioning and edge-set writes)

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* Every edge creation, update, deletion, or suppression with: edge ID, version, inputs used, evidence metrics, and reason for change.    
\* Per-edge causal evidence details: evidence strength, evidence types, and full provenance for contributing observations, narratives, persona flags, AE attributions, and priors.    
\* Governance events, including edge activations gated by p-value/AUC thresholds (per H.18B) and \`AuditEvent(type="cir\_bias\_check")\` whenever validation fails or fairness issues arise, routed to Module 19\\.    
\* Suppression and psychosocial context included in edge provenance and vector records, with suppressionContext sourced from H.2.    
\* Ledger entries for each committed edge set: vectorVersion, inputHash, validator, and linkage to the CIR Feature Library Ledger (L.3).

\# \*\*V5.2 M18 — Multi-Pathway Analysis (MPA)\*\*

\#\#\# \*\*Purpose\*\*

Module 18 (MPA) is the system’s multi-hypothesis inference engine: it takes causal edges from the CIR, AE constraints, psychosocial signals, and stability bands, and turns them into a probabilistic map of competing patient trajectories.    
Its purpose is to model multiple plausible pathways simultaneously, assign probability-weighted forecasts that respect causal structure and safety constraints, and expose uncertainty explicitly rather than collapsing to a single “best guess.”

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Multi-hypothesis pathway construction over nodes (diagnoses, symptoms, lab values, interventions) and CIR-provided edges with evidence strength and provenance.    
\* Evidence weighting across labs/imaging, clinician-confirmed conditions, patient-reported outcomes (PSI-informed), and population priors, with per-branch normalization to 1.0.    
\* Uncertainty modeling per pathway (posterior probability, confidence interval, suppression flags when psychosocial dominance is detected).    
\* MPA vector management: \`{pathway\_id, posterior, drivers, suppression}\` plus version ID, input-hash, and provenance links.    
\* Suppression & safety behavior for SymbolicFlare, Overshoot/HealingPain, and MD\\\_Toggle.    
\* Outputs for clinician-, patient-, and system-facing artifacts (RiskAssessment, DocumentReference, Communication, Observation, AuditEvent).

\*\*Out of scope\*\*

\* Defining or storing disease facts, guideline rules, or internal disease dictionaries; priors are handled only as a provided “prior weight” vector and are treated as one evidence stream among many.    
\* Re-specifying FHIR field-level mappings (owned by Appendix C).    
\* Owning lineage, feature-governance, ethics/weight-stability policy text, or ledger schema definitions (owned by Appendices F.17/F.18, H.18, and L.3).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`cir\_edge\_set\[\]\` (from Module 17): directed edges with \`evidence\_strength\`, \`provenance\_refs\[\]\` (and any edge metadata required to support pathway construction).    
\* \`ae\_constraints\` (from Module 16): AE attribution/constraints usable to block implausible edges.    
\* \`stability\_context\` (from Module 6): \`stabilityBand\`, drift indicators, and related state inputs required to shape pathway probabilities.    
\* \`psi\_context\` (from Module 5 and/or 6): PSI score and psychosocial signals used in weighting and suppression flagging.    
\* \`stack\_level\` (from Module 3B): stack level used as an input dependency.    
\* \`prior\_weight\_vector\` (population priors input stream): pre-normalized prior weights consumed as one evidence stream.    
\* \`coding\_labels\` on evidence sources (e.g., LOINC / SNOMED / ICD-10) used as labels on evidence sources and observations.    
\* \`suppression\_state\` (as applicable): \`pauseFlag\`, \`pauseReason\` inputs affecting pathway behavior (e.g., SymbolicFlare, Overshoot, HealingPain, MD\\\_Toggle).

\#\#\# \*\*Outputs\*\*

\* \`ranked\_pathways\[\]\`: ranked list of pathways with \`pathway\_id\`, \`posterior\_probability\`, \`confidence\_interval\`, \`driver\_explanations\`, and \`suppression\_flags\` (as applicable).    
\* \`mpa\_vector\_set\`: vector set containing \`{pathway\_id, posterior, drivers, suppression}\` plus \`vector\_version\_id\` and \`input\_hash\`, with provenance links.    
\* System-facing FHIR artifact types (field-level mapping referenced externally):    
  \* \`Observation\` (feature vectors)    
  \* \`RiskAssessment\`    
  \* \`Communication\` / patient-safe narratives via Module 14    
  \* \`DocumentReference\`    
  \* \`AuditEvent\`

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest inputs\*\*: load CIR edges, AE constraints, stability/drift indicators, PSI signals, stack level, suppression state, and the pre-normalized \`prior\_weight\_vector\`.    
2\. \*\*Construct pathway candidates\*\*: build multiple competing pathway graphs where:    
   \* node types include diagnoses, symptoms, lab values, and interventions;    
   \* edges are sourced from CIR with evidence strength and provenance.    
3\. \*\*Apply AE constraints to edges\*\*: block implausible edges using AE attribution from Module 16\\.    
4\. \*\*Compute evidence weights per pathway branch\*\*:    
   \* assign weights using the hierarchy: labs/imaging (LOINC), clinician-confirmed conditions (SNOMED/ICD-10), patient-reported outcomes (PSI-informed confidence), population priors (generic prior stream);    
   \* treat priors as one evidence stream; consume only the provided “prior weight” vector;    
   \* normalize weights to 1.0 per branch.    
5\. \*\*Shape pathway probabilities with patient state context\*\*: incorporate stability band, drift indicators, and PSI to modulate pathway probabilities.    
6\. \*\*Compute uncertainty per pathway\*\*: for each pathway, produce posterior probability and confidence interval, and set suppression flags when psychosocial dominance is detected.    
7\. \*\*Apply suppression & safety behavior\*\*:    
   \* If \`pauseReason=SymbolicFlare\`: down-weight affected pathways; do not delete them.    
   \* If \`pauseReason=Overshoot\` or \`pauseReason=HealingPain\`: hold or constrain affected pathways until AE/recovery resolves.    
   \* If \`pauseReason=MD\_Toggle\`: pause selected pathways under clinician override semantics.    
8\. \*\*Rank and package results\*\*:    
   \* produce a ranked pathway list with posterior probabilities and driver explanations for clinicians;    
   \* produce safe, non-deterministic narratives for patients via Module 14;    
   \* emit system-facing Observation (feature vectors), RiskAssessment, and AuditEvent artifacts.    
9\. \*\*Persist MPA vector set\*\*: write \`{pathway\_id, posterior, drivers, suppression}\` with \`vector\_version\_id\`, \`input\_hash\`, and provenance links.    
10\. \*\*Enforce vector retention behavior\*\*: retain deprecated vectors for ≥2 minor versions.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Priors are treated as one evidence stream; MPA consumes a pre-normalized “prior weight” vector and does not store or reason about specific disease facts.    
\* Codes (e.g., LOINC, SNOMED, ICD-10) are used as labels on evidence sources in CIR edges and Observations, not as an internal dictionary.    
\* FHIR mappings are not re-specified in-module; Appendix C is referenced for detailed mappings.    
\* Lineage & feature governance references remain pointers to Appendices F.17/F.18 and L.3; normative definitions live in the appendices.    
\* Ethics and weight stability policy is governed by Appendix H.18; M18 does not own the policy text.    
\* Auditability and reproducibility are tied to vector version and input set; vector versioning and archival are governed in Appendix L and the MPA Vector Ledger.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Modules (inputs)\*\*:    
  \* M17 (CIR edges)    
  \* M16 (AE attribution / constraints)    
  \* M6 / M5 (stability/PSI inputs)    
  \* M3B (stack level)    
\* \*\*Modules (outputs/consumers)\*\*:    
  \* M14 (patient-safe narratives)    
  \* M19 (monitoring & drift; retraining signals)    
  \* M47 (QA routing for divergence per governance reference)    
\* \*\*Appendices (referenced authorities)\*\*:    
  \* Appendix C (FHIR mappings)    
  \* Appendix F.17 / F.18 (lineage & feature governance)    
  \* Appendix L / L.3 (vector versioning, archival, MPA Vector Ledger)    
  \* Appendix H.18 (Pathway Ethics & Weight Stability Policy)

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

MPA must log, at minimum:

\* \*\*Vector lineage\*\*: \`vector\_version\_id\` (e.g., \`ethos-vector-vX.Y\`) and \`input\_feature\_hash\` linkable to upstream Observations and CIR edges.    
\* \*\*Inference context\*\*: timestamp, patient identifier (or de-identified key), pathway IDs, posterior probabilities, confidence intervals, and suppression flags.    
\* \*\*Data provenance\*\*: provenance links to source Observations, CIR edges, AE signals, PSI signals, and population priors.    
\* \*\*Governance metadata\*\*: AuditEvent entries including vector version, dataset hash, suppression rationale, and execution environment identifiers (model server, configuration ID).    
\* \*\*Lifecycle events\*\*: logging when vectors are deprecated, re-issued, or retrained (with Module 19 drift monitoring feeding the decision).

\#\# \*\*V5.2 M19 — QA & Continuous Learning\*\*

\#\#\# \*\*Purpose\*\*

Module 19 is the central QA and continuous learning gate for Ethos-of-Health: it monitors model performance, detects drift, supervises suppression behavior, and routes validated drift/error evidence to the Learning Kernel (Module 48\\) under strict governance.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Model performance monitoring: AUROC, Brier, calibration slope/intercept, PSI-stratified calibration.    
\* Drift detection and threshold actions (10% / 20%).    
\* ConfidenceScore integration and routing effects (down-weighting and suppression-queue routing).    
\* Suppression oversight (over- vs under-suppression) with AuditEvent emission.    
\* Continuous learning handoff: routing drift/calibration deltas/error traces to Module 48; retraining governance hooks and version retention.    
\* QA loop event emission \\+ ledger writes (L.3.4).

\*\*Out of scope\*\*

\* Performing retraining itself (owned by Module 48).    
\* Auto-correcting suppression behavior (explicitly prohibited).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* From Module 6:    
  \* \`stabilityBand\`    
  \* \`stabilityScore\`    
  \* \`psi\_overlays\`    
\* From Modules 4, 5, 8A/B:    
  \* \`pauseFlag\`    
  \* \`pauseReason\`    
  \* suppression event references/IDs    
\* From Module 7A:    
  \* \`confidenceScore\` (0–1)    
\* From Module 48:    
  \* \`retraining\_candidate\_vectors\`    
  \* \`labels\`    
  \* \`error\_traces\`    
\* QA baseline / comparison context:    
  \* \`modelVersion\`    
  \* baseline metric snapshots (for drift comparison)    
  \* \`provenanceID\`    
  \* \`evidence\_tags\`

\#\#\# \*\*Outputs\*\*

\* QA monitoring artifacts:    
  \* \`QAEvent(type="qa\_feedback\_failure", modelVersion)\`    
  \* \`AuditEvent(type="qa\_cycle\_complete", modelVersion)\`    
  \* Drift event record (with \`provenanceID\` \\+ \`evidence\_tags\`) stored to QA ledger.    
\* Suppression oversight artifacts:    
  \* \`AuditEvent\` per suppression anomaly with \`{detection\_type, trigger, responsible\_module}\`.    
\* Lineage-mapped outputs (per F.19):    
  \* \`DetectedIssue\`    
  \* \`Flag\`    
  \* \`AuditEvent\`    
  \* \`Provenance\`    
  \* \`DocumentReference\` (QA Summary)    
\* Routing outputs to Module 48:    
  \* drift events, calibration deltas, error traces (and associated QAEvents).    
\* Recalibration-output suppression state (when applicable):    
  \* “automatic suppression of recalibration outputs until approval” at ≥20% drift.

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest inputs\*\*    
   \* Read \`stabilityBand\`, \`stabilityScore\`, and \`psi\_overlays\` from Module 6; read suppression events (\`pauseFlag\`, \`pauseReason\`) from Modules 4/5/8A/8B; read \`confidenceScore\` from Module 7A; read retraining-related payloads (\`retraining\_candidate\_vectors\`, \`labels\`, \`error\_traces\`) from Module 48\\.    
2\. \*\*Run model performance evaluation for \`modelVersion\`\*\*    
   \* Compute/collect metric set: AUROC, Brier, calibration slope/intercept, PSI-stratified calibration.    
3\. \*\*Assess drift vs baseline\*\*    
   \* Compare current metrics to baseline to determine drift percentage and threshold state.    
4\. \*\*Apply drift threshold policy\*\*    
   \* If drift ≥ 10%: emit a QA flag and route to governance review.    
   \* If drift ≥ 20%: automatically suppress recalibration outputs until approval.    
5\. \*\*Log drift event provenance\*\*    
   \* For each drift event, attach \`provenanceID\` and \`evidence\_tags\`, and store to the QA ledger (L.3).    
6\. \*\*Integrate confidenceScore into QA routing effects\*\*    
   \* Apply \`confidenceScore\` to each observation:    
     \* Low confidence → down-weight Module 6 scoring and trigger review.    
     \* Very low confidence → route to suppression queue with standardized \`pauseReason\`.    
7\. \*\*Run suppression oversight checks\*\*    
   \* Detect over-suppression vs under-suppression across flare pathways.    
   \* Do not auto-correct; remediation requires explicit clinician/governance approval.    
   \* For each anomaly, emit an \`AuditEvent\` with detection type, trigger, and responsible module.    
8\. \*\*Route learning signals to Module 48\*\*    
   \* Route drift findings, calibration deltas, and error traces to Module 48\\.    
9\. \*\*Enforce retraining governance hooks (handoff conditions)\*\*    
   \* Require dual sign-off (Vector Steward \\+ Clinical Safety Officer) for retraining actions.    
   \* Ensure retrained vectors are versioned with retention of prior versions per C.12.    
10\. \*\*Execute QA loop eventing\*\*    
\* On \`ModelEvaluation(modelVersion)\`: evaluate metrics; if thresholds fail, emit \`QAEvent("qa\_feedback\_failure", modelVersion)\` and route to Module 48; record metrics to L.3.4; emit \`AuditEvent("qa\_cycle\_complete", modelVersion)\`.    
11\. \*\*Emit lineage-mapped outputs\*\*    
\* Produce outputs aligned to F.19 lineage: \`DetectedIssue\`, \`Flag\`, \`AuditEvent\`, \`Provenance\`, \`DocumentReference (QA Summary)\`.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Drift threshold policy is fixed: 10% drift triggers QA flag \\+ governance review; 20% drift triggers automatic suppression of recalibration outputs until approval.    
\* Suppression oversight may detect anomalies but must not auto-correct; remediation requires explicit clinician/governance approval.    
\* Retraining requires dual sign-off (Vector Steward \\+ Clinical Safety Officer).    
\* Governance & consent constraints are anchored to H.18D, including authority hierarchy, mandatory metrics, QAEvent emission for validation failures, consent reuse via H.26.1, and FHIR alignment via AuditEvent and Provenance.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Modules: 4, 5, 6, 7A, 8A, 8B, 48\\.    
\* Appendices / ledgers / lineage: F.19 (lineage mapping), H.18D (governance & consent), H.26.1 (consent reuse), C.12 (vector retention/versioning), L.3 QA ledger and L.3.4 QA ledger records.

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

For every QA cycle and anomaly, log:

\* Metrics per \`modelVersion\`: AUROC, Brier, calibration slope/intercept, PSI-stratified calibration values.    
\* Drift thresholds & outcomes: measured drift vs baseline; threshold state (below / ≥10% / ≥20%); resulting governance action.    
\* Suppression anomalies: type (over- vs under-suppression), triggering signal(s), affected module, and any clinician/governance responses.    
\* Confidence context: \`confidenceScore\` distribution for the QA cycle and counts of low/very-low events routed to suppression.    
\* Retraining hooks: \`modelVersion\` pre/post, training dataset IDs or hashes (via Provenance), governance approvals (Vector Steward \\+ Clinical Safety Officer), and references to triggering QAEvents.    
\* Ledger entries: L.3.4 records with \`modelVersion\`, metrics snapshot, QAEvent/AuditEvent IDs; hash-chained and versioned per ledger policy.    
\* Consent overlays: ConsentVersion and JurisdictionOverlayIDs applied to any retraining dataset re-use (recorded in Provenance; governed by H.26.1).

\# \*\*V5.2 Module 48 — Continuous Learning & Governance Loop (CLGL)\*\*

\#\#\# \*\*Purpose\*\*

Module 48 is the governed loop that turns QA and CAPA signals into lawful, auditable retraining and policy updates. It binds each retraining cycle to consent (M26), jurisdictional overlays (H.26), audit-grade provenance, and governance sign-off, ensuring reproducible continuous learning. It consumes triggers from CAPA/QA/compliance modules and emits retraining records, dashboard updates, and disclosure/compliance packets, without encoding medical facts.

\---

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Intake of learning-cycle triggers from QA/CAPA/mitigation/compliance sources and external advisories as trigger types.    
\* Creation and validation of governed retraining events using a structured retraining capture schema (required fields, version binding, invalidation on missing fields).    
\* Consent \\+ overlay gating for retraining, including Denied Retraining Records.    
\* AuditEvent \\+ Provenance lineage for every approve/deny decision, with hash-chained immutability and replayability contract.    
\* Governance review gate prior to deployment, including fairness/compliance KPI inclusion as part of retraining evaluation.    
\* Loop-closure outputs into QA dashboards (M19), patient disclosures (M30), compliance exports (M31), and governance archives.

\*\*Out of scope\*\*

\* Storing or reproducing external guideline content, disease facts, drug dictionaries, ontology mirrors, lab tables, phenotype dictionaries, or any other “world knowledge” (MKE-owned).    
\* Defining metric implementations for fairness/compliance KPIs or demographic definitions (may be supplied by analytics stack); Module 48 only governs when/how they must be present.    
\* Encoding detailed FHIR profile schemas or code dictionaries (Module 48 references resource types and required artifacts only).

\---

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\*\*LearningTrigger (from upstream modules and external advisories)\*\*

\* \`trigger\_id\`    
\* \`trigger\_source\` (e.g., \`M19|M29|M30|M31|M43|M44|M45|M46|M47|ExternalAdvisory\`)    
\* \`trigger\_ref\` (pointer(s) to source record IDs)    
\* \`trigger\_type\` (includes “external advisories / guideline updates / regulatory mandates” as trigger types without embedding content)

\*\*RetrainingRequest (constructed by this module from triggers)\*\*

\* \`retraining\_record\_id\` (or provisional id)    
\* \`trigger\_refs\[\]\`    
\* \`training\_dataset\_ids\[\]\`    
\* \`model\_version\_pre\`    
\* \`model\_version\_post\` (planned)    
\* \`consent\_version\` (from M26)    
\* \`jurisdiction\_overlay\_ids\[\]\` (from H.26)    
\* \`governance\_rationale\` / \`decision\_notes\`    
\* \`expected\_impact\` (clinical, fairness, compliance)    
\* \`packet\_version\`    
\* \`ledger\_schema\_version\`

\*\*GovernanceEvaluation (inputs to review gate)\*\*

\* \`dataset\_quality\_artifacts\` (references/IDs)    
\* \`kpi\_set\` (performance KPIs; fairness/compliance KPIs required)    
\* \`governance\_actor\_ids\[\]\` (sign-off participants)    
\* \`ethical\_override\_ref\` (if used; must reference Appendix H.23)

\---

\#\#\# \*\*Outputs\*\*

\*\*RetrainingRecord (approved or denied)\*\*

\* \`retraining\_record\_id\`    
\* \`status\` (\`APPROVED\` | \`DENIED\`)    
\* \`trigger\_refs\[\]\`    
\* \`training\_dataset\_ids\[\]\`    
\* \`model\_version\_pre\`    
\* \`model\_version\_post\` (if approved)    
\* \`consent\_version\`    
\* \`jurisdiction\_overlay\_ids\[\]\`    
\* \`governance\_rationale\` / \`decision\_notes\`    
\* \`expected\_impact\`    
\* \`kpi\_set\_refs\[\]\`    
\* \`packet\_version\`    
\* \`ledger\_schema\_version\`

\*\*DeniedRetrainingRecord\*\*

\* All fields above plus:    
\* \`denial\_reason\` (consent failure / overlay failure / governance failure)

\*\*Audit/Interop Artifacts (by reference IDs)\*\*

\* \`audit\_event\_id\`    
\* \`provenance\_id\`    
\* Optional linked artifact IDs: \`task\_id\`, \`observation\_id\`, \`document\_reference\_id\`, \`binary\_or\_bundle\_id\`    
\* \`hash\_chain\_prev\`    
\* \`hash\_chain\_next\`

\*\*Downstream notifications / loop-closure outputs (by reference IDs)\*\*

\* \`qa\_dashboard\_update\_ref\` (M19)    
\* \`disclosure\_packet\_ref\` (M30)    
\* \`compliance\_export\_ref\` (M31)    
\* \`governance\_archive\_ref\`

\---

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest triggers\*\*    
   \* Accept \`LearningTrigger\` inputs from M43–M47, M19, M29–M31, and external advisories as trigger types.    
2\. \*\*Initialize retraining request\*\*    
   \* For each trigger (or grouped trigger set), create a \`RetrainingRequest\` with:    
     \* \`trigger\_refs\[\]\`, \`training\_dataset\_ids\[\]\`, \`model\_version\_pre\`, \`consent\_version\`, \`jurisdiction\_overlay\_ids\[\]\`, \`governance\_rationale/decision\_notes\`, \`expected\_impact\`, and version fields (\`packet\_version\`, \`ledger\_schema\_version\`).    
3\. \*\*Validate required fields (schema invariant)\*\*    
   \* If any mandatory retraining fields are missing, mark the retraining event invalid and do not proceed to approval; record as a denied retraining outcome with audit artifacts.    
4\. \*\*Consent \\+ overlay gate\*\*    
   \* Evaluate whether retraining is permitted under \`consent\_version\` and \`jurisdiction\_overlay\_ids\[\]\`.    
   \* If not permitted:    
     \* Emit \`DeniedRetrainingRecord\` (version-pinned) and continue to Step 7 (audit/artifacts \\+ routing).    
5\. \*\*Governance review gate\*\*    
   \* Require governance actors to validate:    
     \* dataset quality,    
     \* fairness/compliance KPIs presence in evaluation set,    
     \* overlay fit prior to deployment.    
   \* If an ethical override is used, it must reference Appendix H.23 and be logged in the retraining record.    
6\. \*\*Approve and bind replayability contract\*\*    
   \* On approval, finalize \`RetrainingRecord\` with:    
     \* \`model\_version\_post\`,    
     \* binding keys \`{packet\_version, ledger\_schema\_version, model\_version\_pre/post, training\_dataset\_ids\[\]}\`,    
     \* and enforce replayability: identical combinations must yield identical retraining outcomes and downstream KPIs.    
7\. \*\*Emit audit-grade lineage (approve or deny)\*\*    
   \* For every approve/deny decision:    
     \* Write \`AuditEvent\` \\+ linked \`Provenance\`.    
     \* Link to \`Task\`, \`Observation\`, \`DocumentReference\`, and \`Binary/Bundle\` as appropriate for retraining governance events.    
     \* Hash-chain entries for immutability.    
8\. \*\*Close the loop (outputs routing)\*\*    
   \* Route outputs to:    
     \* QA dashboards and KPI updates (M19),    
     \* patient-facing disclosures when retraining materially affects outcomes (M30),    
     \* regulator-facing exports (M31),    
     \* and governance archives.    
9\. \*\*Enforce safety guardrail\*\*    
   \* Enforce the locked rule against shadow/undocumented retraining; retraining evaluations must include fairness and compliance metrics, and absence is a governance failure.

\---

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Module 48 is a governance/continuous-learning kernel and must not become a medical knowledge store.    
\* No disease-specific guideline summaries, disease facts, drug lists, ontology mirrors, lab interpretation tables, or phenotype dictionaries may be embedded in this module.    
\* Retraining cannot proceed without active ConsentVersion and applicable JurisdictionOverlayIDs; failures must produce Denied Retraining Records that remain logged and version-pinned.    
\* Governance sign-off is required before deployment; fairness/compliance KPIs must be part of retraining evaluation.    
\* Shadow/undocumented retraining is prohibited.    
\* Replayability requirement: retraining records bind PacketVersion \\+ LedgerSchemaVersion \\+ ModelVersion \\+ TrainingDatasetID(s); identical combinations must produce identical retraining outcomes and downstream KPIs.

\---

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Modules (inputs):\*\* M19, M29–M31, M43–M47    
\* \*\*Consent:\*\* M26    
\* \*\*Jurisdiction overlays:\*\* Appendix H.26    
\* \*\*Ethical override reference:\*\* Appendix H.23    
\* \*\*Audit/provenance semantics:\*\* Appendix C.11/C.12 (referenced as authoritative; this module emits required artifacts)    
\* \*\*Lineage:\*\* Appendix F.48 (lineage mapping for retraining & governance events)

\---

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

For every retraining or governance event (approved or denied), log:

\* \`retraining\_record\_id\`, \`model\_version\_pre\`, \`model\_version\_post\` (if approved), \`training\_dataset\_ids\[\]\`, \`packet\_version\`, \`ledger\_schema\_version\`    
\* \`trigger\_refs\[\]\` to CAPA/QA/Mitigation/Compliance source records and QAEvents    
\* \`consent\_version\`, \`jurisdiction\_overlay\_ids\[\]\`, overlay evaluation outcome (permitted/denied)    
\* Governance decision (approval/denial), rationale, participating governance actors, timestamps    
\* Evaluation metric references: fairness/compliance/performance KPI set used in the decision (linked to M19 metric definitions)    
\* FHIR artifact IDs and hashes: \`AuditEvent\`, \`Provenance\`, and linked \`Task/Observation/DocumentReference/Binary|Bundle\` IDs    
\* Hash-chain pointers (\`prev\`, \`next\`) to ensure tamper-evident replayability

\# \*\*V5.2 M20 — Real-Time Multimodal Early-Warning & Adaptive Alerting\*\*

\#\#\# \*\*Purpose\*\*

Module 20 is the real-time early-warning radar for Ethos-of-Health.    
It continuously consumes normalized, multimodal patient data and runs an adaptive intelligence loop to surface severity-graded alerts and non-urgent trend flags ahead of visible flares or deterioration.    
It does not encode disease or guideline facts; it interprets patterns over time against personalized baselines and feeds alerts plus outcomes into the Vault (M21) and Continuous Learning Hub (M48), with clinicians remaining the decision makers.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Event-driven early-warning detection cycle on new incoming patient data.    
\* Multi-modal fusion over personalized baselines from the Vault (M21).    
\* Anomaly/drift detection producing alerts vs trend flags vs no action.    
\* Adaptive alert thresholds bounded by governance-approved guardrails.    
\* Suppression-aware alerting behavior including the rule “never PSI alone.”    
\* Closed-loop telemetry handoff for QA and continuous learning under governance.    
\* Emission of auditable alert artifacts and audit/provenance events.

\*\*Out of scope\*\*

\* Any embedded disease facts, guideline facts, or medical-knowledge tables (MKE responsibility).    
\* Any new algorithms or new outputs beyond the V5.1 surface described for M20.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`patient\_id\`    
\* \`event\_timestamp\`    
\* \`input\_event\` (new data arrival trigger: lab / wearable spike / journal entry)    
\* \`vitals\_stream\` (normalized)    
\* \`psi\_trajectory\`    
\* \`ehr\_updates\` / \`ehr\_events\` (normalized; includes already-interpreted lab flags from MKE/integration)    
\* \`derived\_stability\_indices\` (e.g., Stability Band/Score; subclinical drift inputs from the band/trajectory stack)    
\* \`personalized\_baseline\` (patient historical norms from Vault M21)    
\* \`governance\_policies\` (Vector/threshold stewardship \\+ clinical safety \\+ care continuity/escalation governance references)    
\* \`outcome\_feedback\` (confirmed vs false alarms for threshold adaptation)

\#\#\# \*\*Outputs\*\*

\* \`alert\` (severity-graded)    
\* \`trend\_flag\` (non-urgent, clinically relevant drift/trajectory flag)    
\* \`suppression\_context\` attached to candidate alerts (e.g., Symbolic Flare, Overshoot)    
\* \`vault\_write\` (longitudinal entry with full context to M21)    
\* \`qa\_learning\_telemetry\` (to M19/M48)    
\* \`fhir\_artifacts\` (alerts and audit/provenance surfaces): Communication / CommunicationRequest / Observation, plus AuditEvent and Provenance for alerts/suppressions/access/dispatch

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Trigger\*\*: On any new data event, start the detection cycle.    
2\. \*\*Normalize vs baseline\*\*: Compare incoming normalized multimodal inputs against the patient’s personalized baseline derived from Vault history.    
3\. \*\*Compute deviations/anomalies\*\*: Compute deviations and anomalies from baseline using the available vitals stream, PSI trajectory, EHR updates, contextual baselines, and derived stability indices.    
4\. \*\*Classify output type\*\*: Determine one of \`{alert, trend\_flag, no\_action}\` where alerts represent sharp, high-risk patterns and trend flags represent slower, clinically relevant non-urgent change.    
5\. \*\*Apply adaptive thresholds (bounded)\*\*: Evaluate alert/trend decisions against thresholds that may adapt based on outcome feedback (confirmed vs false alarms) while remaining bounded by governance-approved guardrails.    
6\. \*\*Enforce suppression constraints\*\*: Treat PSI as a risk amplifier but do not allow PSI alone to trigger escalation, and attach suppression reasons (e.g., Symbolic Flare, Overshoot) to any alert/trend decision where the signal is muted/tempered.    
7\. \*\*Emit outputs and route downstream\*\*:    
   \* If \`alert\`: emit severity-graded alert artifact(s) and route into escalation/continuity hooks as applicable.    
   \* If \`trend\_flag\`: emit non-urgent trend flag with pattern/time-window context for downstream review.    
   \* If \`no\_action\`: proceed to logging step with outcome “no\\\_action” for audit completeness.    
8\. \*\*Persist and broadcast telemetry\*\*: Write alert/trend/no-action context to the Vault (M21) and emit QA/learning telemetry to M19/M48.    
9\. \*\*Auditability surfaces\*\*: For every alert and suppression decision, emit FHIR AuditEvent/Provenance records (including data access and alert dispatch events).

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* M20 does not encode disease or guideline facts; those remain the responsibility of MKE.    
\* Threshold adaptation is permitted only within governance-approved guardrails and cannot drift into unsafe extremes.    
\* PSI can contribute as a risk amplifier but can never alone trigger escalation.    
\* M20 is non-device CDS with clinicians as decision makers and with transparent reasoning and governance-bound guardrails.    
\* Governance authority for vector/threshold change approval, clinical safety review flows, and care continuity/cool-down policies are referenced via H.10, H.12, and H.20, with F.20 treated as a reference copy where embedded.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Upstream\*\*: Module 27 (normalized HL7/FHIR feeds / patient-normalized vital streams).    
\* \*\*Downstream\*\*: Module 21 (Vault), Module 22 (multi-channel actions / continuity loop actuation), Module 48 (continuous learning telemetry), Module 19 (QA/learning telemetry).    
\* \*\*Appendices / governance anchors\*\*: H.10, H.12, H.20, F.20, and Audit & Provenance appendix for FHIR AuditEvent/Provenance structures.

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* Every \*\*alert\*\*: patient, timestamp, severity, contributing signals, suppression reasons (if any), vector version, and destination channels.    
\* Every \*\*trend flag\*\*: pattern description, time window, metrics involved, and linkage to downstream reviews.    
\* Every \*\*suppression event\*\*: why a candidate alert was degraded or suppressed (e.g., Symbolic Flare, Overshoot, PSI-only).    
\* All \*\*data access\*\* and \*\*alert dispatch\*\* events as FHIR AuditEvent/Provenance.    
\* Model/vector \*\*version identifiers\*\* used for each decision.    
\* Outcomes for alerts (confirmed flare, false alarm, missed flare) captured via clinician feedback workflows to support learning and QA.

\# \*\*V5.2 M21 — Decision Support & Longitudinal Vault Engine\*\*

\#\#\# \*\*Purpose\*\*

Module 21 is the suppression-aware forecast harmonization and longitudinal decision-support vault. It integrates raw forecast vectors with stability history, psychosomatic context, suppression logs, and QA provenance to generate probabilistic risk cones and harmonized forward trajectories, then writes trajectories, inputs, outcomes, and personalization deltas into an immutable, queryable ledger.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Suppression-aware forecast harmonization and calibration.    
\* Probabilistic risk cone generation and tiering (including Tier ≥ 3 clinician CommunicationRequest issuance).    
\* Immutable, hash-chained vault logging, outcome status tracking, cross-referencing, risk-shift analytics, state-transition logging, and personalization deltas.    
\* Provenance, audit, and consent-aware access with ABAC/consent-aware query views and meta-logging of read/write access.

\*\*Out of scope\*\*

\* External medical knowledge (pushed to MKE).    
\* Re-specifying FHIR mapping details (authoritative in Appendix C.10 and related FHIR appendices).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`forecast\_vectors\_raw\[\]\` (from Module 20): \`{timestamp, volatility, slope, subclinical\_features\[\], vector\_id}\`    
\* \`stability\_band\_history\[\]\` (from Module 6): \`{timestamp, stabilityBand, stabilityScore?}\`    
\* \`psi\_persona\_tags\` (from Module 5): \`{timestamp, PSI, persona\_flags\[\], evidence\_refs\[\]}\`    
\* \`qa\_lineage\` (from Module 7B): \`{lineage\_id, source\_module\_ids\[\], confidence?, provenance\_ids\[\]}\`    
\* \`suppression\_logs\[\]\` (from Module 8): \`{timestamp, pauseFlag, pauseReason, source\_module, related\_metadata}\`    
\* \`retrospective\_trajectory\_data\[\]\`: \`{time\_window, observed\_outcomes\[\], linked\_event\_ids\[\]}\`    
\* \`psychosomatic\_surges\[\]\`: \`{timestamp, PSI, related\_event\_ids\[\]}\`

\#\#\# \*\*Outputs\*\*

\* \`forecast\_vectors\_harmonized\[\]\`: \`{curve\_id, true\_vs\_suppression\_masked\_label, pauseReason?, metadata, provenance\_ids\[\]}\`    
\* \`risk\_cones\[\]\`: \`{cone\_id, time\_horizon, severity\_tier, narrowing\_widening\_signal, provenance\_ids\[\]}\`    
\* \`clinician\_communication\_requests\[\]\` (when Tier ≥ 3): \`{request\_id, tier, risk\_documentation\_refs\[\], provenance\_ids\[\]}\`    
\* \`vault\_ledger\_entries\[\]\` (immutable, hash-chained): \`{event\_id, timestamp, event\_type, condition\_or\_stack\_context, zone, trigger\_tags\[\], values, confidence, outcome\_status, linked\_ids\[\], actor\_actions\[\], patient\_reflections?}\`    
\* \`risk\_shift\_summaries\[\]\`: \`{summary\_id, detected\_pattern, analytics, evidence\_links\[\]}\`    
\* \`state\_transition\_events\[\]\`: \`{transition\_id, inferred\_state, supporting\_patterns\[\], timestamp}\`    
\* \`personalization\_deltas\[\]\`: \`{delta\_id, trigger\_pattern, threshold\_updates, risk\_scaling\_updates, updated\_parameter\_set\_id}\`    
\* \`access\_control\_views\` (ABAC/consent-aware): \`{policy\_labels, transformations\_applied\[\]}\`

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. Ingest \`forecast\_vectors\_raw\[\]\`, \`psi\_persona\_tags\`, \`stability\_band\_history\[\]\`, \`qa\_lineage\`, and \`suppression\_logs\[\]\`.    
2\. Perform forecast calibration using \`retrospective\_trajectory\_data\[\]\` and \`psychosomatic\_surges\[\]\` to correct bias (Symbolic Flare vs true organic signals).    
3\. Align forecast vectors with \`suppression\_logs\[\]\` and label each curve as true vs suppression-masked trajectory, carrying \`pauseReason\` and related metadata forward into downstream resources.    
4\. If suppression has occurred, mark any forecast lacking suppression annotation as invalid and prevent it from driving escalation.    
5\. Convert harmonized trajectories into probabilistic risk cones that represent a range of plausible future instability, where narrowing/widening encodes consolidation vs volatility.    
6\. Map cone severity into tiers and, for Tier ≥ 3, issue a clinician-facing \`CommunicationRequest\` with provenance-linked risk documentation.    
7\. Log every significant event (alerts, stack/zone changes, PSI spikes, suppression flags, journaling spikes, outcome confirmations) into an immutable, hash-chained, queryable ledger with condition, zone, trigger tags, values, confidence, and outcome fields.    
8\. Maintain outcome statuses (pending → confirmed/averted/false alarm) and cross-references between events to enable backward and forward chaining through the patient timeline.    
9\. Detect risk-shift patterns (e.g., shortening remission periods, recurring pre-flare clusters) and emit risk-shift summaries and trend analytics for clinician review and upstream models.    
10\. Infer high-level state transitions from patterns of flares, zone readings, and symptoms, and log explicit state-transition events for downstream use.    
11\. Generate personalization deltas when specific triggers consistently precede flares or yield false alarms, adjusting patient-specific thresholds and risk scaling and emitting updated parameter sets.    
12\. Enforce tamper-evident logging, ABAC/consent-aware query views, and FHIR-compatible audit trails, including meta-logging of vault read/write access.    
13\. Guarantee traceability from any decision to the exact chain of vault events and actor actions that produced it.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Apply the Overlap Audit boundary: external medical knowledge is pushed to MKE; Module 21 keeps patient-specific temporal reasoning, vaulting, and governance.    
\* Forecasts without suppression annotation when suppression has occurred are invalid and must not drive escalation.    
\* Tier ≥ 3 automatically issues clinician-facing \`CommunicationRequest\` with provenance-linked risk documentation.    
\* FHIR mapping details for RiskAssessment, Observation, DocumentReference, and AuditEvent are not re-specified here and remain authoritative in Appendix C.10 and related FHIR appendices.    
\* Vault lineage and decision support mapping align with Appendix F.21, and governance/narrative controls defer to relevant H-series appendices (H.9/H.10/H.11; H.18/H.19).

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Modules: 20, 5, 6, 7B, 8\\.    
\* Appendices: Appendix C.10; Appendix F.21; H-series appendices (H.9/H.10/H.11; H.18/H.19).

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* Every event affecting risk or state: alerts, predictions, zone/stack changes, PSI spikes, suppression toggles, journaling spikes, outcome confirmations, and state-transition inferences.    
\* For each event: timestamp, event type, condition/stack context, zone, trigger tags, value(s), confidence, outcome status, linked IDs, actor actions, and any patient reflections/notes.    
\* All vault read/write access (meta-logging): who queried what, and when.    
\* All suppression contexts (pauseFlag, pauseReason) associated with forecasts and their downstream surface in FHIR resources.    
\* All personalization deltas and model parameter updates derived from vault evidence, including which patterns triggered them.    
\* Hash chain and integrity checks for the ledger and the ABAC/consent labels and transformations applied to sensitive data.

\# \*\*V5.2 M22 — Adaptive Plan Modulation\*\*

\#\#\# \*\*1\\) Purpose\*\*

Module 22 is the adaptive orchestration layer that modulates the active care plan (CarePlan, ServiceRequest, Task, Appointment) in response to forecast cones (Module 21), stack burden (Module 20), adherence/QA (Module 16), and suppression context (Modules 5–7).    
It decides when to escalate, when to de-escalate, and when to hold plan changes, and is always subordinate to clinician override.    
Every modulation is fully versioned and auditable, with provenance linking back to input vectors, suppression reasons, and the source module.

\#\#\# \*\*2\\) Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Plan modulation decisions: Escalate / De-escalate / Hold (including “no change” when evaluated).    
\* Suppression-aware hold behavior using \`pauseFlag\` / \`pauseReason\`, including clinician override (\`MD\_Toggle\`).    
\* Emission of updated CarePlan activities (EthosCarePlan), ServiceRequests, Tasks, Appointments, and corresponding AuditEvent \\+ Provenance.

\*\*Out of scope\*\*

\* Guideline content, disease facts, drug tables, drug class selection, dosing, and lab interpretation tables/ranges.    
\* Choosing which specific labs/diagnostics or which medication changes are guideline-concordant (delegated to MKE \\+ execution modules).    
\* FHIR coding/profile details (delegated to Appendix C.9 \\+ Module 47 and captured in Appendix F.22).

\#\#\# \*\*3\\) Inputs (data objects / fields only)\*\*

\* \`forecastCone\` (from Module 21):    
  \* \`coneId\` (forecast vector ID / cone identifier)    
  \* \`coneTrend\` (widening | narrowing)    
\* \`stackBurden\` (from Module 20):    
  \* \`stackLevel\`    
  \* \`stackStability\` (stable | not\\\_stable)    
\* \`adherenceQA\` (from Module 16):    
  \* \`adherenceScore\` (percentage)    
  \* \`qaScore\` (field present; used as adherence/QA score input)    
\* \`psychosomaticContext\` (from Modules 5–7):    
  \* \`PSI\` (0–3)    
\* \`suppressionContext\` (from Modules 5–7 / governance layer):    
  \* \`pauseFlag\` (boolean)    
  \* \`pauseReason\` (enum; includes {SymbolicFlare, Overshoot, HealingPain, LabError, MD\\\_Toggle, …})    
\* \`clinicianOverride\` (governance / Module 8B signal):    
  \* \`MD\_Toggle\` (presence/activation signal)    
\* \`activePlanState\`:    
  \* \`currentCarePlanRef\` (CarePlan identifier)    
  \* \`currentPlanVersion\` (version identifier)    
\* \`moduleContext\`:    
  \* \`moduleId\` (=22)    
  \* \`moduleVersion\`

\#\#\# \*\*4\\) Outputs\*\*

\* \`modulatedCarePlan\`:    
  \* Updated EthosCarePlan (CarePlan update)    
\* \`planActions\`:    
  \* New/updated \`ServiceRequest\[\]\`    
  \* New/updated \`Task\[\]\`    
  \* New/updated \`Appointment\[\]\`    
\* \`decisionRecord\`:    
  \* \`decisionType\` (Escalate | De-escalate | Hold | NoChange)    
  \* \`AuditEvent\` \\+ \`Provenance\` entries embedding drivers, suppression, module version, and vector IDs

\#\#\# \*\*5\\) Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest inputs\*\*: load \`forecastCone\`, \`stackBurden\`, \`adherenceQA\`, \`PSI\`, \`pauseFlag/pauseReason\`, and any \`MD\_Toggle\` clinician override signals.    
2\. \*\*Apply clinician override supremacy\*\*: if clinician override changes plan modulation, treat the decision as overriding algorithmic modulation and record it with \`pauseReason=MD\_Toggle\` and module provenance.    
3\. \*\*Suppression gate (HOLD path)\*\*: if \`pauseFlag=true\`, then:    
   \* Set \`decisionType=Hold\`.    
   \* Defer forecast-driven CarePlan changes.    
   \* Insert reflective journaling Tasks and supportive Communication (per Module 14 taxonomy) instead of escalation.    
4\. \*\*Non-suppressed escalation/de-escalation evaluation\*\* (only if \`pauseFlag=false\` and not overridden by clinician action):    
   \* \*\*Escalate\*\* if all are true:    
     \* \`forecastCone.coneTrend \= widening\` AND \`stackBurden.stackLevel ≥ 2\` AND \`adherenceQA.adherenceScore \< 80%\`.    
     \* Actions:    
       \* Add diagnostic/monitoring ServiceRequests.    
       \* Add Tasks for check-ins/monitoring.    
       \* Schedule Appointments for follow-up.    
   \* \*\*De-escalate\*\* if all are true:    
     \* \`forecastCone.coneTrend \= narrowing\` AND \`stackBurden.stackStability \= stable\` AND \`adherenceQA.adherenceScore ≥ 90%\` AND \`PSI ≤ 1\`.    
     \* Actions:    
       \* Reduce journaling Task cadence.    
       \* Relax monitoring frequency.    
       \* Streamline CarePlan activities while preserving safety.    
   \* \*\*NoChange\*\* if neither escalation nor de-escalation triggers match; record as “no change” evaluation outcome.    
5\. \*\*Version and persist outputs\*\*: for any Escalate / De-escalate / Hold outcome, emit updated CarePlan artifacts plus corresponding ServiceRequests/Tasks/Appointments as applicable, and attach AuditEvent \\+ Provenance encoding forecast vector ID, stack/adherence context, suppression reason (if any), source module (=22), and version identifiers.    
6\. \*\*Defer “what” selection\*\*: when emitting generic ServiceRequests or “med change action vs not,” do not select specific tests, drugs, doses, or FHIR coding details; delegate to M16/MKE and Module 47 / Appendix C.9 as applicable.

\#\#\# \*\*6\\) Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Module 22 contains no guideline content, disease facts, drug tables, ontology mirrors, lab interpretation tables/ranges, or phenotype dictionaries.    
\* \`pauseFlag\` / \`pauseReason\` are used but enumeration values are not defined here; they are authoritative in Appendix H.2 (and related governance H.3/H.4).    
\* Resource-level FHIR mapping details are not restated here; mappings reference Appendix C.9 and Appendix F.22, with detailed coding handled by Module 47\\.    
\* Clinician override (\`MD\_Toggle\`) supersedes algorithmic modulation and must be recorded explicitly in provenance.    
\* All adaptive changes must be versioned, reversible, and logged in immutable AuditEvent/Provenance trails.

\#\#\# \*\*7\\) Dependencies (other EoH modules, appendices by reference only)\*\*

\* Modules: 20 (stack burden), 21 (forecast cones), 16 (adherence/QA), 5–7 (suppression context inputs), 14 (supportive communication taxonomy reference), 8B (clinician override signal), 47 (FHIR coding details).    
\* Appendices: F.22 (Lineage Mapping for Module 22), C.9 (FHIR mapping), H.2 (suppression field governance), H.3/H.4 (suppression-related governance references).

\#\#\# \*\*8\\) Audit Hooks (what must be logged and attributable)\*\*

For every adaptive plan modulation event, log:

\* Drivers & inputs: forecast vector ID / cone identifier, stack level at decision time, adherence/QA score, and suppression context (\`pauseFlag\`, \`pauseReason\`, including \`MD\_Toggle\`).    
\* Decision & outcome: decision type (Escalate / De-escalate / Hold, including “no change” when evaluated) and which CarePlan/ServiceRequest/Task/Appointment entries were created or modified (linked via Provenance).    
\* Governance metadata: \`moduleId=22\`, module version, timestamps, responsible agent(s), clinician override notes (if any), and linkage to Appendix F.22 lineage structures (Decision Packet/AuditEvent/Provenance fields).

\# \*\*V5.2 M23 — Adaptive Tapering & Maintenance Orchestrator\*\*

\#\#\# \*\*1\\. Purpose\*\*

Module 23 governs the safe transition from active treatment into Chronic Baseline Mode (CBM) or Original Healthy Baseline (OHB) by orchestrating tapering, maintenance, and rollback protocols. It uses forecast cones, stack burden, adherence/QA, psychosomatic readiness (PSI), suppression flags, and clinician instructions to decide when to start taper, how aggressively to proceed, and when to roll back.

\#\#\# \*\*2\\. Scope\*\*

\*\*In scope\*\*

\* Taper eligibility evaluation and “not eligible” outcome emission.    
\* Taper/maintenance orchestration as a medium-timescale (day/week) closed-loop controller.    
\* Maintenance transition and CBM declaration following taper completion and stability.    
\* Rollback detection and execution based on instability signals.    
\* Suppression-aware pausing of taper adjustments and freezing of CarePlan changes until suppression clears.    
\* Clinician override supremacy and handoff to Module 10 on severe deterioration.    
\* Vault-centric audit logging for taper episodes, rollbacks, and CBM declarations, including linked IDs to forecast vectors, suppression reasons, adherence, and PSI snapshots.

\*\*Out of scope\*\*

\* Disease-/drug-specific taper templates, guideline facts, drug-class specifics, lab-normal ranges, lab cut-offs, and condition-specific facts (delegated to MKE).    
\* Suppression reason definitions (referenced via Appendix H.2).    
\* Patient/clinician messaging catalog and channel/tone definitions (governed by Appendix H.4/H.15).    
\* Detailed FHIR resource modeling/schema (delegated to Appendix C.9).

\#\#\# \*\*3\\. Inputs (data objects / fields only)\*\*

\* \`patient\_id\`    
\* \`condition\_or\_stack\_id\`    
\* \`forecast\_cone\` (includes: \`cone\_status\` {narrowing|stable|widening}, \`forecast\_vector\_id\`)    
\* \`cbm\_trajectory\` (includes: \`stable\_days\`)    
\* \`stability\_band\` (includes: \`current\_band\`, \`band\_history\`)    
\* \`flare\_status\` (includes: \`flare\_detected\`, \`days\_since\_last\_flare\`)    
\* \`adherence\` (includes: \`adherence\_pct\`)    
\* \`qa\_status\` (includes: \`qa\_pass\` boolean)    
\* \`psi\` (includes: \`psi\_value\`)    
\* \`stack\_volatility\_signals\`    
\* \`pauseFlag\` (boolean)    
\* \`pauseReason\` (enum; canonical via Appendix H.2)    
\* \`clinician\_instructions\` (includes: \`override\_type\`, \`override\_details\`, \`agent\`, \`timestamp\`)    
\* \`mke\_taper\_template\_ref\` (includes: \`template\_id\`, \`template\_version\`)

\#\#\# \*\*4\\. Outputs\*\*

\* \`taper\_eligibility\_decision\` ∈ {\`eligible\`, \`not\_eligible\`}    
\* \`taper\_episode\` (if created) including:    
  \* \`taper\_id\`    
  \* \`condition\_or\_stack\_id\`    
  \* \`forecast\_vector\_id\`    
  \* \`protocol\_template\_id\`, \`protocol\_template\_version\` (reference only; MKE-owned)    
\* \`careplan\_updates\` (FHIR resource types only; schema via Appendix C.9):    
  \* \`CarePlan\`    
  \* \`ServiceRequest\`    
  \* \`Task\`    
  \* \`Appointment\`    
\* \`rollback\_rule\` (machine-readable) and \`rollback\_event\` (when fired)    
\* \`cbm\_active\` (boolean) and \`cbm\_declaration\_event\` (when set)    
\* \`clinician\_notification\_event\` (for rollback/safety events; routed via Module 10\\)    
\* \`audit\_events\` and \`provenance\_records\` (Vault entries with linked IDs)    
\* \`qa\_telemetry\` (taper plans, outcomes, protocol version IDs) to Module 48

\#\#\# \*\*5\\. Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Initialize episode context\*\*    
   \* Load current \`forecast\_cone\`, \`cbm\_trajectory\`, \`adherence\`, \`qa\_status\`, \`psi\`, \`pauseFlag/pauseReason\`, \`stability\_band\`, \`stack\_volatility\_signals\`, and \`clinician\_instructions\`.    
2\. \*\*Apply clinician authority first\*\*    
   \* If \`clinician\_instructions.override\_type\` indicates any manual change (e.g., “do not taper,” manual speed adjustment, forced halt), mark \`taper\_eligibility\_decision\` and any taper pacing state as overridden.    
   \* Record provenance with \`agent=Practitioner\` and \`pauseReason=MD\_Toggle\` when applicable.    
   \* If severe deterioration is present (as represented by upstream safety/escalation triggers), hand off to Module 10\\.    
3\. \*\*Enforce suppression handling\*\*    
   \* If \`pauseFlag=true\`, then:    
     \* Pause any new taper adjustments.    
     \* Freeze forecast-driven CarePlan changes until suppression clears.    
     \* Log pause reasons.    
4\. \*\*Evaluate taper eligibility (only if not overridden and not suppressed)\*\*    
   \* Set \`taper\_eligibility\_decision=eligible\` only if all conditions hold:    
     \* \`forecast\_cone\` indicates narrowing or stable trajectory.    
     \* \`cbm\_trajectory.stable\_days \>= 30\`    
     \* \`adherence.adherence\_pct \>= 90\` and \`qa\_status.qa\_pass=true\`    
     \* \`psi.psi\_value \<= 1\`    
   \* Otherwise set \`taper\_eligibility\_decision=not\_eligible\` and emit a future review scheduling signal (review scheduling is an output intent only).    
5\. \*\*If eligible, create/maintain taper episode\*\*    
   \* Create or update a \`taper\_episode\` with \`taper\_id\`, \`condition\_or\_stack\_id\`, and attach \`forecast\_vector\_id\`.    
   \* Attach \`protocol\_template\_id\` and \`protocol\_template\_version\` as an external reference (MKE-owned).    
   \* Emit taper/maintenance CarePlan artifacts (resource types only: CarePlan/ServiceRequest/Task/Appointment).    
6\. \*\*Monitor for rollback triggers (continuous while tapering/maintaining)\*\*    
   \* Continuously monitor:    
     \* \`stability\_band.current\_band \>= 3\`    
     \* \`psi.psi\_value \>= 2\`    
     \* \`stack\_volatility\_signals\` indicates instability    
   \* If any trigger fires:    
     \* Execute immediate rollback to prior treatment state.    
     \* Write Vault entry: “rollback executed; source trigger=instability.”    
     \* Notify clinicians (via Module 10).    
7\. \*\*Maintenance transition and CBM declaration\*\*    
   \* If taper completes and \`flare\_status.days\_since\_last\_flare \>= 90\` (no flare detected for ≥90 days):    
     \* Set \`cbm\_active=true\`.    
     \* Record \`cbm\_active\` and the declaration event in the Vault.    
     \* Decrease journaling and monitoring burden while maintaining minimal safety monitoring.    
8\. \*\*Vault-centric write-through\*\*    
   \* For every taper plan decision, suppression pause, rollback, and CBM declaration:    
     \* Write records to the Vault with linked IDs to \`forecast\_vector\_id\`, suppression reasons, adherence metrics, and PSI snapshots.

\#\#\# \*\*6\\. Governance / Constraints (explicit boundaries; no new rules)\*\*

\* V5 baseline is the behavioral truth; do not alter algorithms, thresholds, or scoring logic from V5-23.    
\* All disease-/drug-specific taper templates, guideline facts, drug-class specifics, and lab cut-offs are delegated to MKE; Module 23 stores only references (template ID/version), not clinical detail.    
\* If suppression flags are active, Module 23 pauses new taper adjustments and freezes CarePlan changes until suppression clears, with pause reasons logged.    
\* Clinician manual changes supersede algorithmic decisions and must be logged with provenance; Module 23 will not initiate new higher-intensity treatments; severe deterioration triggers handoff to Module 10\\.    
\* Suppression reasons must not be redefined in free text; reference Appendix H.2 for canonical fields/values.    
\* Communication patterns are governed by Appendix H.4/H.15; Module 23 only tags events with communication classes.    
\* FHIR structures are delegated to Appendix C.9; Module 23 only commits to emitting the referenced resource types.

\#\#\# \*\*7\\. Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Consumes\*\*    
  \* Module 21 (forecast structures, vault history, stability bands, flares, dose trajectories)    
  \* Module 20 (stack burden and volatility)    
  \* Module 16 (adherence and QA scores)    
  \* Module 22 (PSI vector and psychosomatic tags)    
  \* Modules 5–7 (suppression flags)    
  \* Module 10 / clinician UI (clinician constraints and overrides, MD\\\_Toggle)    
\* \*\*Produces\*\*    
  \* Appendix C.9 (CarePlan/ServiceRequest/Task/Appointment payloads)    
  \* Module 21 (CBM flags and taper outcome records into Vault)    
  \* Module 20 (machine-readable rollback rules to monitoring)    
  \* Module 10 (escalation alerts when rollback/safety events fire)    
  \* Module 48 (QA telemetry: taper plans, outcomes, protocol version IDs)    
\* \*\*Appendix references\*\*    
  \* Appendix H.2 (suppression fields/values)    
  \* Appendix H.4/H.15 (communication taxonomies)    
  \* Appendix F.23 (CBM governance and lineage mapping)    
  \* Appendix C.9 (FHIR resource structures)

\#\#\# \*\*8\\. Audit Hooks (what must be logged and attributable)\*\*

For each taper episode and key decision, log:

\* \`taper\_id\`, \`condition\_or\_stack\_id\`, and associated \`forecast\_vector\_id\`.    
\* Eligibility rationale: stability window summary, band history, flare count, key lab/marker status (without encoding MKE thresholds), PSI snapshot, adherence score.    
\* Protocol reference: external taper template \`template\_id\` and \`template\_version\` (MKE-owned; no embedded clinical detail).    
\* Suppression state at decision time: \`pauseFlag\`, \`pauseReason\` (per Appendix H.2).    
\* Clinician instructions and overrides (e.g., HOLD\\\_TAPER, speed changes), including \`provenance.agent\`, timestamps, and channel.    
\* Rollback events: triggers fired (band drift, PSI spike, volatility), time-to-rollback, and whether escalation to Module 10 occurred.    
\* CBM declaration events: look-back stability evidence and date of CBM flag activation.    
\* Linkage to communication payloads (Appendix H.4/H.15) for patient/clinician messaging at each milestone.

\# \*\*V5.2 M24 — Interface Hub & Orchestration Layer\*\*

\#\#\# \*\*Purpose\*\*

Module 24 is the multi-role interface hub that turns outputs from core EoH engines into safe, role-appropriate surfaces for patients, clinicians, and auditors.    
It consolidates Stability Band, flare risk, CBM, psychosomatic context, forecasts, and plans into actionable displays and shared-decision workflows.    
It is event-driven and read-only with respect to patient state: all actions (journals, overrides, approvals) are routed back through controlled modules and logged.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Multi-role UI/orchestration layer aggregating outputs from Modules 1/6, 5/22, 13/14, 19/20, 47, 48\\.    
\* Event-driven orchestration responding to alerts, journal updates, PSI changes, and user activity; near-real-time updates with fallback to cached data.    
\* Patient-facing: state snapshot & trends; journaling & reflection prompts; micro-interventions trigger/hosting.    
\* Clinician-facing: action center; explainability hooks (“Why?”); confirm/override/annotate workflows routed to planning/safety modules.    
\* Shared decision \\+ human-in-the-loop: asynchronous bidirectional decision tasks via Module 19; concern capture; clinician confirmation checkpoints.    
\* Orchestration: multi-source timeline assembly; prompt coordination via Module 19/48; EHR embedding via SMART-on-FHIR and Module 47 write-back initiation.    
\* Security/vocabulary guardrails: RBAC & masking; consent flags from Module 46; role templates and “never-words” via Appendix H.3/H.4/H.16.    
\* Audit & QA surfaces: read-only event log built from Vault \\+ AuditEvent/Provenance; feedback capture into Module 48\\.

\*\*Out of scope\*\*

\* Computing clinical scores or changing Stack Level, Stability Band, CBM, PSI, or other core state transitions.    
\* Defining wording policies locally (patient vs clinician vocabulary templates, never-words, tone rules).    
\* Defining field locks, suppression policies, or FHIR schemas (treated as appendix- or module-authoritative sources).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`stackLevel\`    
\* \`stabilityBand\`    
\* \`CBM\_active\` / CBM state    
\* \`PSI\`    
\* \`pauseFlag\`    
\* Denial/persona flags    
\* Adherence issues    
\* Flare probabilities    
\* Trajectory cones / forward risk horizons    
\* Alerts / risk score objects with explanation components (contributing factors, codes, impact scores, context excerpts)    
\* Patient journal entries (free text)    
\* Mood / tag selection    
\* Prompt scheduling/eligibility controls    
\* Vault history/timeline inputs (daily Stack/Band, PSI, tags, interventions, alerts; audit logs; prior actions)    
\* Consent/privacy flags (Module 46\\)    
\* EHR context: \`patientIdentity\`, \`practitionerIdentity\`, \`FHIR\_endpoints\`, write-back status    
\* Prompt config / A-B experiments / QA flags (where appropriate)

\#\#\# \*\*Outputs\*\*

\* UI payloads and narrative bundles per role (patient, clinician, QA), including timeline/alert panels and explanation payloads.    
\* User interaction events (journal entries, feedback, overrides, approvals, concerns) routed to Vault / Modules 19, 21, 48\\.    
\* Trigger events for Module 47 to create or update FHIR artifacts.    
\* AuditEvent/Provenance entries (or their source payloads) aligned to C.11 audit schema.

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest latest upstream outputs\*\* from Modules 1/6, 5/22, 13/14, 19/20, 47, 48 and Vault (Module 21\\) for the active patient context.    
2\. \*\*Apply role-based access (RBAC) and masking\*\* for the requesting role (patient vs clinician vs auditor), obeying privacy/consent flags from Module 46\\.    
3\. \*\*Enforce vocabulary guardrails\*\* by selecting curated templates per role and hiding internal fields (CBM, PSI, pauseFlag) and never-words from patient views, cross-referencing Appendix H.3/H.4/H.16.    
4\. \*\*Render read-only core state\*\* (Stack Level, Stability Band, CBM, PSI and related state transitions) for display only; do not allow UI mutation.    
5\. \*\*Assemble a unified timeline\*\* by reading from Vault and monitoring/prediction modules: Stack/Band per day, PSI, tags, interventions, and alerts.    
6\. \*\*Patient-facing surface generation\*\* (when role=patient):    
   \* Produce a simplified wellness view tied to Band and Stack trajectories, using plain language rather than CBM/PSI jargon.    
   \* Provide journaling (free text), mood/tag selection, and context-sensitive prompts (e.g., after Band worsening or crisis flags); soften wording during high-PSI periods where applicable.    
   \* Trigger and host in-app micro-interventions when upstream modules detect psychosomatic or crisis cues (content modules live elsewhere).    
7\. \*\*Clinician-facing surface generation\*\* (when role=clinician):    
   \* Populate an action center dashboard of alerts, flare forecasts, trajectory cones, psychosomatic context, and key flags (pauseFlag, denial personas, adherence issues).    
   \* Provide “Why?” explainability hooks for each alert/risk score by assembling contributing factors, codes, impact scores, and context excerpts (labs, journals); structure/composition are EoH, while code labels/definitions are supplied by MKE.    
   \* Enable confirm/override/annotate workflows; log as AuditEvent/Provenance and forward to planning/safety modules.    
8\. \*\*Shared decision orchestration\*\* (when a decision task is active):    
   \* Orchestrate long-lived, bidirectional decision tasks across clinician and patient UIs via Module 19 (pending/accepted/declined state and reminders).    
   \* Capture structured patient concerns/feedback tied to specific decisions and route to clinicians and Module 19/48 as qualitative signals.    
   \* Enforce human-in-the-loop safety: no recommended action becomes authoritative without clinician confirmation via Module 19 and downstream execution guardrails in Module 16; surface these checkpoints in Module 24\\.    
9\. \*\*Prompt coordination / overload control\*\*: before surfacing prompts, check central scheduling/eligibility (Module 19/48).    
10\. \*\*EHR/FHIR orchestration\*\* (when embedded in EHR context):    
\* Embed via SMART-on-FHIR, inherit clinician identity via SSO, and use Module 47 to map clinician actions into FHIR resources.    
11\. \*\*Event-driven updates\*\*: on alerts, journal updates, PSI changes, or user activity, refresh affected UI payloads; if upstream dependencies are unavailable, fall back to cached data.    
12\. \*\*Emit interaction and orchestration events\*\* (journals, feedback, overrides, approvals, concerns; FHIR write-back triggers) to the designated modules and logs.    
13\. \*\*Provide audit/QA view\*\* (when role=auditor/QA): serve a chronological, read-only event log from Vault and AuditEvent/Provenance; capture clinician agreement/override/ignore outcomes for Module 48 learning kernels.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Module 24 is an interface hub only and never computes clinical scores itself.    
\* Stack Level, Stability Band, CBM, PSI and related state transitions are displayed but cannot be mutated from the UI; all actions are routed to upstream modules, preserving state integrity.    
\* Module 24 is event-driven and uses fallback to cached data when necessary.    
\* RBAC & masking are enforced by role, PHI is masked in non-EHR channels, and consent/privacy flags from Module 46 are obeyed.    
\* Internal fields (CBM, PSI, pauseFlag) and never-words are hidden from patient views using curated templates governed by Appendix H.3/H.4/H.16.    
\* No recommended action becomes authoritative without clinician confirmation via Module 19 and downstream execution guardrails in Module 16\\.    
\* Field definitions & locks are governed by Appendix H.2 / H.5.4; suppression and safety governance are governed by Appendix H.2 and Module 11; FHIR mappings are governed by Appendix C.8–C.11; ledgers/checksums are governed by Appendix L.3 and Module 48\\.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Modules: 1/6, 5/22, 11, 13/14, 16, 19/20, 21, 46, 47, 48\\.    
\* Appendices: H.2, H.3, H.4, H.5.4, H.16; C.8–C.11; L.3.

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

1\. State exposure history: each dashboard view (who, when, which state and which alerts/forecasts were displayed).    
2\. Alert and recommendation lifecycle: first exposure, explanation content shown, acknowledgments, overrides (with reasons), resulting approvals/dismissals mapped into AuditEvent/Provenance.    
3\. Shared decision workflows: decision task IDs, participants, step timestamps, patient concerns, final outcome, and any FHIR artifacts created via Module 47\\.    
4\. Journal and feedback events: each journal entry (de-identified or PHI-protected per Module 46), tagging outcomes, feedback on suggestions, and downstream acknowledgement of true/false positives.    
5\. Suppression/pause context surfaced to users: whenever suppression/pauseFlag/symbolic-flare context influences what is (or isn’t) shown, log the influence and reason code.    
6\. Security and privacy-relevant events: RBAC violations prevented, de-identification mode toggles, patient consent changes affecting UI, and any access to de-identified QA views.    
7\. Logs must align with the C.11 AuditEvent / Provenance schema to reconstruct cross-module lineage.

\# \*\*V5.2 M25 — System-Wide Narrative Synthesizer\*\* 

\#\#\# \*\*Purpose\*\*

Module 25 is a passive, system-wide narrative synthesizer that aggregates outputs from terrain, suppression, safety, forecasting, and execution modules into coherent bundles for patients, clinicians, and governance audiences.    
It does not originate new metrics; it transforms structured signals (stack, stability band, CBM, suppression states, forecasts, care plans) into context-aware narratives governed by role-appropriate tone and vocabulary and by narrative governance/divergence rules.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Narrative assembly from cross-module outputs into a coherent outline.    
\* Audience segmentation and tone control with required tags: {audience, tone, lexiconLock, suppressionContext}.    
\* Suppression-aware framing when suppression is active (SymbolicFlare, Overshoot, HealingPain, LabError, MD\\\_Toggle), requiring explicit suppression annotations in outputs.    
\* System-wide harmonization and de-duplication to prevent conflicting output across modules.    
\* Multilingual / multimodal packaging and export as FHIR Communication/DocumentReference mapped via F.25.    
\* Narrative divergence governance per H.21 with mandatory logging in AuditEvent.reason and provenanceID reuse.

\*\*Out of scope\*\*

\* Originating new metrics or clinical decisions.    
\* Any non-narrative logic (e.g., scoring, thresholds, clinical interpretation) owned by other modules/appendices.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \*\*CrossModuleStateBundle\*\*    
  \* \`stackLevel\`    
  \* \`stabilityBand\`    
  \* \`cbmState\`    
  \* \`suppression\`: \`{ pauseFlag, pauseReason }\`    
  \* \`crisisContext\`    
  \* \`forecasts\`    
  \* \`carePlans\`    
  \* \`executionSafeguards\`    
  \* \`uiHooksAndChannels\`    
  \* \`uncertaintyArtifacts\` (per H.9–H.13 references)    
\* \*\*NarrativeRequest\*\*    
  \* \`audience\`    
  \* \`tone\`    
  \* \`lexiconLock\`    
  \* \`suppressionContext\`    
  \* \`languagePack\` (English \\+ extended packs)    
  \* \`versionID\`    
\* \*\*GovernanceRefs\*\*    
  \* \`lockedFieldsRef\` (H.2)    
  \* \`ladderRef\` (H.5)    
  \* \`uncertaintyRefs\` (H.9–H.13)    
  \* \`vocabularyGuardrailsRef\` (H.16)    
  \* \`narrativeGovernanceRef\` (H.19)    
  \* \`divergenceRegistryRef\` (H.21)    
  \* \`lineageMappingRef\` (F.25)    
  \* \`twinBaselineRef\` (H.18, if referenced)

(Inputs are consumed from the upstream modules/appendices listed under Dependencies.)

\#\#\# \*\*Outputs\*\*

\* \*\*PatientNarrativeBundle\*\*    
  \* FHIR \`Communication\` and/or \`Task\`    
\* \*\*ClinicianNarrativeBundle\*\*    
  \* FHIR \`Flag\`, \`RiskAssessment\`, \`CommunicationRequest\`, and/or \`DocumentReference\`    
\* \*\*GovernanceNarrativeBundle\*\*    
  \* FHIR \`DocumentReference\` \\+ \`AuditEvent\` with lineage to calibration logs and vector versions

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest inputs\*\*: read cross-module outputs needed for narrative synthesis (terrain, suppression, crisis context, guidance, execution, forecasting).    
2\. \*\*Assemble narrative outline\*\*: aggregate cross-module outputs into a coherent narrative outline without creating new metrics.    
3\. \*\*Apply audience segmentation & tone control\*\*: tag the narrative with \`{audience, tone, lexiconLock, suppressionContext}\` and enforce tone rules (H.19) and vocabulary guardrails (H.16).    
4\. \*\*Apply suppression-aware framing (conditional)\*\*:    
   \* If suppression is active with \`pauseReason ∈ {SymbolicFlare, Overshoot, HealingPain, LabError, MD\_Toggle}\`, adjust narrative framing (reassurance/reflective tone) instead of escalating and require explicit suppression annotations in outputs.    
5\. \*\*System-wide harmonization & de-duplication\*\*: prevent conflicting output across modules and produce a single narrative truth for each state change (including avoiding double escalation).    
6\. \*\*Multilingual / multimodal packaging\*\*: generate narrative bundles in English plus extended packs and map to FHIR Communication/DocumentReference per F.25 and Appendix C.8–C.10 references.    
7\. \*\*Governance cross-checks\*\*: enforce read-only stance regarding clinical decisions and cross-check outputs against H.2 (locked fields), H.5 (ladder), and H.9–H.13 (uncertainty/cones); apply versioning under Appendix L.    
8\. \*\*Narrative divergence governance (conditional)\*\*: when audience outputs differ, apply H.21 divergence triggers and log divergence with mandatory \`AuditEvent.reason\` tagging and provenanceID reuse, enforcing allowable vs forbidden divergences.    
9\. \*\*Emit bundles\*\*: produce patient, clinician, and governance narrative bundles in the specified FHIR resource forms.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Module 25 is read-only with regard to clinical decisions and does not originate new metrics.    
\* Vocabulary and role-based lexicon are governed by Appendix H.16 and narrative dimensions by H.19; Module 25 references these and does not restate term lists.    
\* Divergence detection and logging are governed by H.19 and H.21; Module 25 operates under these governance rules.    
\* Detailed FHIR mappings for narrative bundles are centralized in F.25 and Appendix C.8–C.10 and must be referenced rather than redefined.    
\* Precision Health Twin initialization is governed by Appendix H.18; Module 25 references it only as Day-0 context input when used.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Consumes (inputs)\*\* from M1–3, M5–7, M8–10, M14, M16, M17–22, M24, and Appendices H.2, H.5, H.9–H.13, H.16, H.18, H.19, H.21.    
\* \*\*Lineage / mapping\*\*: Appendix F.25; FHIR mapping references Appendix C.8–C.10.

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* For every narrative event, log \`{audience, tone, lexiconLock, suppressionContext, versionID}\` (per H.19).    
\* For divergence events, log \`AuditEvent.reason\` tagged \`narrativeDivergence\` with divergenceType (TD/CD/SD/GD) \\+ severity whenever audience outputs differ (per H.21).    
\* Log Provenance links from narrative bundles back to originating Observations, RiskAssessments, CarePlans, and AuditEvents, including vector versions and driver sets where applicable.    
\* Log suppression reason (SymbolicFlare, Overshoot, HealingPain, LabError, MD\\\_Toggle) in AuditEvent.detail and surface it in DocumentReference summaries.    
\* When Day-0 baseline (H.18) is referenced, ensure linkage to the baseline Twin Initialization AuditEvent/Provenance chain.

\# \*\*V5.2 M26 — Consent & Ethical Safeguards\*\* 

\#\#\# \*\*Purpose\*\*

Module 26 is the consent and ethics gate for the entire EoH stack, enforcing dynamic, role-specific, multilingual consent so no downstream module can act outside the current consent state or ethical override regime.

\#\#\# \*\*Scope\*\*

\*\*In scope\*\*

\* Dynamic consent refresh and “consent decay” renewal workflows triggered by time and events (e.g., medication changes, trajectory recalibration, cross-border data use, new PurposesOfUse).    
\* Role-specific consent flows for patients, clinicians, and caregivers/proxies (including delegation with explicit expiry).    
\* Consent state machine enforcement using canonical states {Active, Revoked, Expired, Delegated, EmergencyOverride}.    
\* Ethical override governance using the canonical registry and ledger hooks; any Module 8B bypass must be logged with \`overrideReason\` and routed into the Ethical Override Ledger.    
\* FHIR-based consent artifacts, dual-audience documentation (patient Communication \\+ clinician DocumentReference), and audit-grade provenance for consent-relevant operations.

\*\*Out of scope\*\*

\* Any embedded guideline tables, disease facts, drug class lists, lab interpretation tables, phenotype dictionaries, or static code lists.    
\* Restating regulation text; regulations appear only as constraints/overlays enforced by Module 26 and neighbors.    
\* Importing inference algorithms from legacy donors.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\*\*RequestContext\*\*

\* \`patient\_id\`    
\* \`requesting\_module\_id\`    
\* \`requested\_operation\` (create/read/update/export/execute/disclose)    
\* \`purpose\_of\_use\`    
\* \`requester\_role\` (patient/clinician/caregiver/governance)    
\* \`requester\_actor\_id\`    
\* \`jurisdiction\_overlay\_ids\[\]\`    
\* \`language\`    
\* \`audience\` (patient/clinician/governance)

\*\*ConsentState (from Appendix H.20)\*\*

\* \`consent\_state\` (Active/Revoked/Expired/Delegated/EmergencyOverride)    
\* \`consent\_version\`    
\* \`delegated\_to\_actor\_id\` (if Delegated)    
\* \`expiry\_timestamp\` (if time-limited / delegated)    
\* \`fhir\_consent\_ref\`

\*\*EthicalOverrideInput (from Appendix H.22 / H.23)\*\*

\* \`override\_requested\` (boolean)    
\* \`override\_reason\`    
\* \`override\_source\_module\_id\` (e.g., Module 8B)

\*\*Ledger/Audit Inputs (Appendix L.3.11, Appendix C.11)\*\*

\* \`change\_type\` (create/update/revoke/expire/delegate/override)    
\* \`prior\_consent\_version\` (optional)    
\* \`audit\_event\_ref\` (optional on input; required on output)    
\* \`provenance\_ref\` (optional on input; required on output)

\#\#\# \*\*Outputs\*\*

\*\*Decision\*\*

\* \`decision\` (allow/deny)    
\* \`decision\_reason\` (including consent/override rationale)

\*\*FHIR artifacts\*\*

\* \`Consent\` (versioned FHIR Consent resource reference)    
\* Patient-facing \`Communication\` (plain-language, multilingual)    
\* Clinician-facing \`DocumentReference\` (full rationale, compliance note)

\*\*Ledger/Audit artifacts\*\*

\* Consent Ledger entry (Appendix L.3.11)    
\* \`AuditEvent\` \\+ \`Provenance\` for every consent-relevant operation (Appendix C.11)    
\* Ethical Override Ledger entry when emergency bypass occurs (with \`overrideReason\`)

\*\*Downstream bindings\*\*

\* \`consent\_version\`, \`consent\_state\` supplied to minimization/export/disclosure/compliance paths (Modules 27–32), including denial events when consent blocks an action.

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Load current consent context\*\*    
   \* Retrieve the active \`ConsentState\` (including \`consent\_state\`, \`consent\_version\`, expiry/delegation fields) using Appendix H.20 semantics.    
2\. \*\*Evaluate consent state gate\*\*    
   \* If \`consent\_state\` ∈ {Revoked, Expired} → set \`decision=deny\`.    
   \* If \`consent\_state\` \\= Delegated → require that \`requester\_actor\_id\` matches \`delegated\_to\_actor\_id\` and that \`expiry\_timestamp\` is valid; otherwise set \`decision=deny\`.    
   \* If \`consent\_state\` \\= Active → continue.    
   \* If \`consent\_state\` \\= EmergencyOverride → continue under override rules (Step 4).    
3\. \*\*Apply dynamic consent refresh / decay\*\*    
   \* If the request is time- or event-triggered for consent refresh (e.g., medication changes, trajectory recalibration, cross-border data use, new \`purpose\_of\_use\`) then:    
     \* Generate a consent prompt/renewal workflow and set \`decision=deny\` until a new or renewed consent version is recorded.    
4\. \*\*Ethical override handling (only for emergency bypass)\*\*    
   \* If an emergency bypass is invoked via Module 8B:    
     \* Require \`override\_reason\` to be present.    
     \* Record an Ethical Override Ledger entry with \`overrideReason\` per Appendix H.23.    
     \* Set \`consent\_state=EmergencyOverride\` for the operation scope and proceed with \`decision=allow\` for the minimal required action under the override.    
5\. \*\*Enforce “no bypass” rule\*\*    
   \* If any downstream module attempts to bypass consent without an 8B emergency override:    
     \* Set \`decision=deny\`.    
6\. \*\*Generate dual-audience documentation\*\*    
   \* For every consent event or decision (allow/deny/override/state transition):    
     \* Produce patient-facing \`Communication\` (plain-language, multilingual).    
     \* Produce clinician-facing \`DocumentReference\` (full rationale, compliance note).    
     \* Anchor both to the same consent/provenance identifiers.    
7\. \*\*Write ledger \\+ audit/provenance\*\*    
   \* For every consent-related operation (create/update/revoke/override/state transition):    
     \* Write \`AuditEvent\` \\+ \`Provenance\` (Appendix C.11).    
     \* Write a Consent Ledger entry (Appendix L.3.11) including consent state, purpose, overlays, \`change\_type\`, actor, and \`AuditEvent\` reference.    
8\. \*\*Emit bindings for downstream modules\*\*    
   \* Provide \`consent\_version\` and \`consent\_state\` to downstream minimization/export/disclosure/compliance paths so they can log denials when consent blocks action.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Module 26 is the consent/ethics gate for the entire stack; no downstream module may act outside the current consent state or ethical override regime.    
\* Locked rule: no consent bypass without Module 8B Emergency Override, and any such bypass must be logged with \`overrideReason\` into the Ethical Override Ledger.    
\* No embedded guideline tables, disease facts, drug class lists, lab interpretation tables, or phenotype dictionaries; regulation references appear only as constraints/overlays and are not restated.    
\* Consent is a versioned FHIR Consent resource with provenance, expiry, and state transitions logged in the Consent Ledger.    
\* Every consent-relevant operation must write AuditEvent \\+ Provenance.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Appendix H.20 — Consent State Taxonomy    
\* Appendix H.22 — Ethical Override Registry    
\* Appendix H.23 — Ethical Override Ledger Hooks    
\* Appendix L.3.11 — Consent Ledger (Module 26\\)    
\* Appendix C.11 — AuditEvent \\+ Provenance requirements    
\* Module 25 — Narrative disclosures synthesis (referenced for transparency & explainability)    
\* Module 16 — execution guardrails (referenced for automation veto alignment)    
\* Module 8B — Emergency Override (bypass entry point)    
\* Modules 27–32 — minimization/export/disclosure/compliance consumers of ConsentVersion/state

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* Every consent state transition (Active ↔ Revoked/Expired/Delegated/EmergencyOverride).    
\* Every ethical override (8B), including \`overrideReason\`, and routing into the Ethical Override Ledger.    
\* Dual-audience artifacts (patient/clinician) must be traceable to the same consent event and provenance IDs.    
\* All denial events (Denied Export / Denied Disclosure / Denied Compliance) must reference consent state, overlays, and \`overrideReason\` where applicable.

\# \*\*V5.2 M27 — Data Minimization & De-Identification Engine\*\*

\#\# \*\*Purpose\*\*

Provide the \*\*single governed engine\*\* that (1) enforces \*\*purpose-bound minimization\*\* on any access/export request and (2) performs \*\*de-identification / pseudonymization\*\* of secondary-use datasets, with \*\*full lineage, replayability, and denial semantics\*\*.

\#\# \*\*Scope\*\*

\#\#\# \*\*In scope\*\*

\* Purpose-bound access gating and minimization transforms (suppress/mask/generalize/date-shift/geo-coarsen; analytics view)    
\* De-identification and pseudonymization of \*\*secondary-use\*\* outputs derived from minimized bundles    
\* Deterministic replayability via PacketVersion \\+ LedgerSchemaVersion and full transform lineage    
\* Denial semantics (Denied bundle / Denied transform record) with explicit reasons and downstream surfacing

\#\#\# \*\*Out of scope\*\*

\* Consent creation/refresh logic (owned by consent module; this module consumes consent state/version)    
\* Disclosure packet construction (owned by V5.2-A2)    
\* Disclosure ledger/accounting as system-of-record (owned by V5.2-A3)

\#\# \*\*Inputs\*\*

\* \*\*Request context:\*\* requesterRole, audience tier (patient/clinician/regulator), purposeOfUse    
\* \*\*Consent context:\*\* ConsentVersion / active consent state (consumed, not authored here)    
\* \*\*Jurisdiction overlays:\*\* JurisdictionOverlayID(s) \\+ overlay versions    
\* \*\*Profile selection:\*\* ProfileID (minimization / export profile)    
\* \*\*Source payload:\*\* raw bundle for access, or PB-DMAO-minimized bundle for secondary use    
\* \*\*Emergency override signal (if any):\*\* overrideReason \\+ scope indicator (consumed; not created here)

\#\# \*\*Outputs\*\*

\* \*\*Minimized response bundle\*\* with meta.security tags (R-REDACT / R-BUCKET / R-SHIFT / ANON-PARTIAL)    
\* \*\*De-identified packet\*\* (schema-conformant; versioned)    
\* \*\*Pseudonymized packet\*\* (schema-conformant; versioned)    
\* \*\*Denied outputs\*\* (Denied bundle / Denied transform record) including denialReason and context    
\* \*\*AuditEvent \\+ Provenance\*\* entries capturing transforms, parameters, policy context, and replayability IDs    
\* \*\*Disclosure log pointer artifact\*\* (DocumentReference-style disclosure log output for downstream packetizer/ledger surfaces)

\#\# \*\*Process / Logic\*\*

1\. \*\*Validate declared purpose\*\*    
   \* Require purposeOfUse to be declared (undefined purposes denied).    
2\. \*\*Reconcile purpose with consent \\+ overlays\*\*    
   \* If consent/purpose/overlays reconcile → proceed.    
   \* If conflict → produce \*\*Denied bundle\*\* or \*\*Denied transform record\*\* with denialReason and lineage.    
3\. \*\*Apply minimization transform suite (profile \\+ overlay driven)\*\*    
   \* Execute transforms as specified by ProfileID and constrained by JurisdictionOverlayID(s): suppress/mask/generalize/date-shift/geo-coarsen / analytics view.    
   \* Record transformList \\+ parameters in Provenance.    
4\. \*\*Secondary-use transform: de-identification / pseudonymization\*\*    
   \* For secondary-use requests, transform PB-DMAO outputs into compliant de-identified or pseudonymized packets.    
   \* Bind every transformation to ConsentVersion, ProfileID, and JurisdictionOverlayID(s).    
5\. \*\*Replayability binding\*\*    
   \* Attach PacketVersion \\+ LedgerSchemaVersion to outputs; ensure deterministic regeneration given identical input \\+ versions.    
6\. \*\*Emit lineage \\+ downstream handoff artifacts\*\*    
   \* Produce AuditEvent \\+ Provenance; produce disclosure-log style DocumentReference artifact for downstream packetization/ledger modules.

\#\# \*\*Governance / Constraints\*\*

\* \*\*No bypass:\*\* No data release/export proceeds without purpose \\+ consent \\+ overlay reconciliation; emergency override is the only bypass signal and must be logged with overrideReason/scope.    
\* \*\*No silent drops:\*\* suppressed fields must still appear in lineage with reason codes.    
\* \*\*No “what the world knows” tables:\*\* module text must not embed guideline/disease/ontology tables; de-ID legal specifics are delegated to overlays/appendices and referenced by ID only.    
\* \*\*Single authority for transforms:\*\* no other module may author de-ID/pseudonymization outside this engine’s control (for the surfaces consolidated here).

\#\# \*\*Dependencies\*\*

\* Consent module provides ConsentVersion and consent state (consumed).    
\* Narrative module may supply patient-facing explanation templates (consumed downstream via disclosure logs).    
\* V5.2-A2 (Packetization) consumes minimized outputs \\+ disclosure logs.    
\* V5.2-A3 (Ledger) records all allow/deny events as accounting entries (via downstream surfaces).

\#\# \*\*Audit Hooks\*\*

For every access / transform / denial event, must log:

\* PurposeOfUse, ConsentVersion, JurisdictionOverlayID(s), ProfileID    
\* TransformList \\+ transform parameters (bucket boundaries, shift offsets, geocoarsening level, etc.)    
\* Bundle meta.security tags (R-REDACT, R-BUCKET, R-SHIFT, ANON-PARTIAL) and requesterRole/audience tier    
\* Outcome: allowed vs denied \\+ denialReason; emergency override details if present    
\* PacketVersion \\+ LedgerSchemaVersion for replayability

\---

\#\# \*\*Mapping Table (V5.2-A1 section ↔ V5.1′ source)\*\*

| V5.2-A1 Section | Source in V5.1′ |  
| \----- | \----- |  
| Purpose / Scope (minimization gate \\+ transforms \\+ lineage) | M27 purpose \\+ retention list |  
| Purpose / Scope (de-ID/pseudonymization hub; secondary-use) | M34 purpose \\+ clean summary |  
| Inputs/Outputs (purpose, consent, overlay, ProfileID, provenance) | M27 audit/logging checklist |  
| De-ID/pseudo logging \\+ versioning | M34 audit checklist |  
| Governance (no “law facts” in module body; defer to overlays) | M34 overlap enforcement note |

\---

\#\# \*\*Rewrite Notes (non-shipping)\*\*

\* Consolidated M27 \\+ M34 into one spec without adding new transforms, thresholds, or policy semantics.    
\* Preserved denial/replayability/audit invariants; moved nothing into consent/packetizer/ledger roles.

\---

If you want maximal Phase 3 momentum, next I’ll rewrite \*\*V5.2-A2 — Governed Export & Disclosure Packetization\*\* (from M28, plus the “export-as-act” boundary language).

\# \*\*V5.2 M28 — Disclosure & Access Accounting Ledger\*\*

\#\# \*\*Purpose\*\*

Maintain the \*\*single governed ledger\*\* of \*\*every export/disclosure request and outcome\*\* (approved or denied), with canonical fields bound via \*\*AuditEvent \\+ Provenance \\+ DocumentReference\*\*, providing \*\*dual-audience transparency\*\* (patient summaries vs regulator-grade detail) and enforcing \*\*jurisdictional retention/access rules\*\*.

\#\# \*\*Scope\*\*

\#\#\# \*\*In scope\*\*

\* Record \*\*every export/disclosure event\*\*, including denials (no phantom/invisible requests).    
\* Store each ledger entry as an \*\*AuditEvent \\+ Provenance \\+ DocumentReference triplet\*\*, with canonical identity fields.    
\* Normalize packet events into a ledger schema (including narrative binding \\+ denial construction \\+ version tagging).    
\* Enforce retention/expiry: convert expired entries to metadata-only stubs with \*\*DataAbsentReason=expired\*\* under jurisdictional rules.    
\* Emit QA/oversight signals and cross-check disclosure vs suppression trail consistency.

\#\#\# \*\*Out of scope\*\*

\* Performing minimization/de-ID transforms (owned by \*\*V5.2-A1\*\*).    
\* Constructing disclosure packets (owned by \*\*V5.2-A2\*\*).    
\* Building disclosure reports and compliance packets (owned downstream by report/export hubs).

\#\# \*\*Inputs\*\*

\* \*\*Disclosure Packet events\*\* from V5.2-A2 (payload, narrative, AuditEvent, Provenance).    
\* \*\*Minimization lineage\*\* and \*\*ProfileID\*\* references from V5.2-A1.    
\* \*\*ConsentVersion\*\* (snapshot reference) and \*\*Jurisdiction overlay context\*\*.

\#\# \*\*Outputs\*\*

\* \*\*Disclosure Ledger Entry\*\* (AuditEvent \\+ Provenance \\+ DocumentReference) per request/outcome.    
\* \*\*Patient summaries\*\* and \*\*regulator logs\*\* (ledger-anchored, consumed downstream).    
\* \*\*QA / analytics signals\*\* routed to QA and oversight modules; disclosure–suppression integrity cross-check hooks.

\#\# \*\*Process / Logic\*\*

1\. \*\*Universal logging\*\*    
\* For every export/disclosure request, create a ledger entry whether the outcome is allowed or denied.    
\* Enforce the locked rule: \*\*no export may occur without a matching ledger entry\*\*.    
2\. \*\*Canonical entry construction\*\*    
\* Represent each ledger entry as a triplet: \*\*AuditEvent \\+ Provenance \\+ DocumentReference\*\*.    
\* Required minimum fields include: PurposeOfUse, ConsentVersion, ProfileID, JurisdictionOverlayID(s), PacketVersion, requester role (and LedgerSchemaVersion where applicable).    
3\. \*\*Ledger normalization pipeline\*\*    
\* Normalize incoming packet events into the ledger schema (including narrative binding and denial record construction) with version tagging.    
4\. \*\*Denied disclosure semantics\*\*    
\* When consent/overlays block export, emit a \*\*Denied Disclosure Record\*\* capturing denialReason \\+ applied consent state \\+ overlay set.    
\* Undeclared purposes must become denial records (no “silent drop”).    
5\. \*\*Dual-audience views (ledger is the source of truth)\*\*    
\* Generate patient-facing summaries as narratives bound to ledger entries; regulator-facing logs expose full technical detail (transforms, overlays, provenance).    
\* Ensure patient-facing disclosure summaries exist for every entry, including denials.    
6\. \*\*Retention & expiry handling\*\*    
\* Apply jurisdictional retention rules; when expired, convert to metadata-only stubs with \*\*DataAbsentReason=expired\*\* and preserve lineage references.    
7\. \*\*Replayability and version governance\*\*    
\* Require that reruns with identical inputs (packet, consent version, overlay set, profile) and version IDs yield identical ledger entries and reports.    
\* Treat LedgerSchemaVersion, retention policies, and disclosure-report schemas as governed and versioned; changes must be replay-safe.    
8\. \*\*Oversight & integrity cross-check\*\*    
\* Output aggregated metrics to QA/oversight and cross-check disclosure ledger against suppression trail for consistency (suppressed vs disclosed).

\#\# \*\*Governance / Constraints\*\*

\* \*\*Ledger-anchored truth:\*\* downstream reports/exports must remain ledger-anchored and version-tagged.    
\* \*\*No phantom events:\*\* every request produces a record (including denials).    
\* \*\*Schema authority is externalized:\*\* schema rules and packet/report shapes are owned by referenced appendices; this module must not redefine field lists or resource mappings locally.

\#\# \*\*Dependencies\*\*

\* \*\*Upstream:\*\* V5.2-A2 provides packet events; V5.2-A1 provides transform lineage and ProfileIDs.    
\* \*\*Downstream:\*\* disclosure reporting and compliance export hubs consume ledger slices; QA/oversight consumes metrics; suppression audit trail used for cross-check.

\#\# \*\*Audit Hooks\*\*

Must log, at minimum:

\* Event-level log for every request: allowed vs denied; timestamp; PurposeOfUse; ConsentVersion; ProfileID; JurisdictionOverlayID(s); PacketVersion; requester identity/role.    
\* Provenance linkage to packet, transforms, consent snapshot, overlay registry.    
\* Narrative binding via DocumentReference for each disclosure/denial.    
\* Retention/expiry events and DataAbsentReason=expired conversion.    
\* Version control fields: LedgerSchemaVersion, PacketVersion, overlay version IDs.

\---

\#\# \*\*Mapping Table (V5.2-A3 section ↔ V5.1′ source)\*\*

| V5.2-A3 Section | Source in V5.1′ |  
| \----- | \----- |  
| Purpose / role as governed accounting hub | M29 purpose statement |  
| Universal logging \\+ “no export without ledger entry” | M29 logic retention \\\#1 |  
| Canonical ledger schema triplet | M29 logic retention \\\#2 \\+ audit checklist |  
| Normalization pipeline \\+ version tagging | M29 logic retention \\\#3 |  
| Denied disclosure semantics | M29 logic retention \\\#4 |  
| Dual-audience views | M29 logic retention \\\#5 |  
| Retention/expiry | M29 logic retention \\\#6 \\+ audit checklist |  
| Replayability \\+ governance | M29 logic retention \\\#7/\\\#10 |  
| Oversight cross-check (suppression vs disclosure) | M29 logic retention \\\#9 |

\---

\#\# \*\*Rewrite Notes (non-shipping)\*\*

\* Converted M29 into a standalone spec without altering any invariants (“no phantom events,” “ledger-anchored truth,” denial inclusion, replayability, expiry handling).    
\* Clarified boundaries against A1 (transforms) and A2 (packetization) without changing behavior.

\---

\# \*\*V5.2 M29 — Research & Federated Collaboration Export Governance\*\*

\#\# \*\*Purpose\*\*

Govern \*\*multi-institutional research and collaboration exports\*\* by enforcing that every shared dataset is \*\*consent-aware\*\*, \*\*profile-driven\*\*, \*\*jurisdiction-compliant\*\*, \*\*reproducible\*\*, and \*\*legally bound to institutional agreements (IRB/DUA)\*\*—with full \*\*AuditEvent \\+ Provenance\*\* and denial semantics.

\#\# \*\*Scope\*\*

\#\#\# \*\*In scope\*\*

\* Gate research/collaboration exports on \*\*explicit research consent\*\* and project policy.    
\* Require a Research \*\*ProfileID\*\* (minimization profile) applied upstream; refuse exports when profile application is missing/inconsistent.    
\* Bind exports to \*\*JurisdictionOverlayID(s)\*\* and enforce overlay conflicts as \*\*Denied Export Records\*\* (not silent failure).    
\* Require \*\*IRB/DUA DocumentReference\*\* linkage for institutional accountability.    
\* Wrap export events in a FHIR \*\*Bundle\*\* including \*\*AuditEvent \\+ Provenance\*\*, with PacketVersion \\+ LedgerSchemaVersion for reproducibility.

\#\#\# \*\*Out of scope\*\*

\* Performing minimization/de-ID transforms (owned by \*\*V5.2-A1\*\*).    
\* Disclosure packet construction (owned by \*\*V5.2-A2\*\*).    
\* Disclosure ledger/accounting as system-of-record (owned by \*\*V5.2-A3\*\*).

\#\# \*\*Inputs\*\*

\* \*\*Consent context:\*\* ConsentVersion \\+ explicit research consent flag/status (consumed, not authored here).    
\* \*\*Project policy context:\*\* project-specific access policy \\+ collaboration scope.    
\* \*\*Upstream minimization evidence:\*\* Research \*\*ProfileID\*\* \\+ transform lineage showing it was applied.    
\* \*\*Jurisdiction overlays:\*\* JurisdictionOverlayID(s) applicable at export time.    
\* \*\*Institutional agreements:\*\* IRB/DUA DocumentReference IDs.    
\* \*\*Versioning IDs:\*\* PacketVersion \\+ LedgerSchemaVersion.

\#\# \*\*Outputs\*\*

\* \*\*Federated research export bundle\*\* (FHIR Bundle) with embedded AuditEvent \\+ Provenance \\+ required agreement references.    
\* \*\*Denied Export Record\*\* (with denialReason, consent/overlay context, and provenance) surfaced to the accounting layer.    
\* \*\*Disclosure Ledger entry trigger\*\* (handoff to V5.2-A3) for both approvals and denials.

\#\# \*\*Process / Logic\*\*

1\. \*\*Research consent gate\*\*    
\* Require explicit \*\*Research consent\*\*. If missing/insufficient → deny and log a Denied Export Record.    
2\. \*\*Project policy validation\*\*    
\* Validate export request against \*\*project-specific access policy\*\* and declared collaboration scope. If out of scope → deny and log.    
3\. \*\*Profile-driven minimization precondition\*\*    
\* Require evidence that a \*\*Research ProfileID\*\* was applied upstream.    
\* If profile application is missing/inconsistent → \*\*refuse to share\*\*, emit denial record.    
4\. \*\*Jurisdiction overlay enforcement\*\*    
\* Apply overlay set at export time; if overlays conflict or prohibit cross-border transfer/scope → deny (no silent failure).    
5\. \*\*Institutional accountability binding\*\*    
\* Require IRB/DUA DocumentReferences and bind them to the export event. If missing → deny (or block pending completion) and log.    
6\. \*\*Export packaging\*\*    
\* Wrap the approved export as a FHIR \*\*Bundle\*\* embedding AuditEvent \\+ Provenance that records:    
  \* requester, purpose, transforms, ConsentVersion, ProfileID, JurisdictionOverlayID(s), PacketVersion \\+ LedgerSchemaVersion.    
7\. \*\*Ledger anchoring\*\*    
\* Ensure every approved export and every denial is recorded into the \*\*Disclosure Ledger\*\* (V5.2-A3).

\#\# \*\*Governance / Constraints\*\*

\* \*\*No sharing without profile application.\*\* If profile not applied, export is refused and logged.    
\* \*\*No silent failure on overlay conflicts.\*\* Conflicts must yield Denied Export Records.    
\* \*\*Institutional agreements are mandatory.\*\* IRB/DUA must be linked to each export event.    
\* \*\*Reproducibility required.\*\* Exports must carry PacketVersion \\+ LedgerSchemaVersion.

\#\# \*\*Dependencies\*\*

\* \*\*Upstream:\*\* V5.2-A1 for minimization \\+ ProfileID lineage; consent module for ConsentVersion and research consent state.    
\* \*\*Downstream:\*\* V5.2-A3 for disclosure accounting and oversight.

\#\# \*\*Audit Hooks\*\*

For every attempted federated export (approved or denied), must log:

\* Requester identity, purposeOfUse=RESEARCH, timestamp.    
\* ConsentVersion \\+ research consent status.    
\* ProfileID \\+ evidence of upstream minimization transform lineage.    
\* JurisdictionOverlayID(s) and overlay evaluation outcome.    
\* PacketVersion \\+ LedgerSchemaVersion.    
\* IRB/DUA DocumentReference linkages.    
\* DenialReason when denied, and linkage to Disclosure Ledger entry.

\---

\#\# \*\*Mapping Table (V5.2-A4 section ↔ V5.1′ source)\*\*

| V5.2-A4 Section | Source in V5.1′ |  
| \----- | \----- |  
| Purpose \\+ consent gate \\+ project policy | M33 purpose \\+ retention list |  
| Profile-driven minimization precondition | M33 retention list (profile requirement/refuse to share) |  
| End-to-end provenance \\+ Bundle packaging fields | M33 retention list (FHIR Bundle \\+ embedded AuditEvent/Provenance fields) |  
| Institutional accountability binding | M33 retention list (IRB/DUA DocumentReference linkage) |  
| Overlay enforcement \\+ denial semantics | M33 retention list (overlay conflicts → denied) |  
| Ledger anchoring | M33 retention list (all exports/denials appear in ledger) |

\---

\#\# \*\*Rewrite Notes (non-shipping)\*\*

\* Recast M33 as a strict governance gate with explicit dependencies on A1 (minimization evidence) and A3 (ledger anchoring), without adding any new rules or export pathways.

\---

If you want to continue Phase 3 beyond the Cluster-A set, the next clean move is:    
\*\*pick the next module rewrite order\*\* (typically: M1 → M2 → M3 → M6 → suppression cluster M8/M9/M11 → forecasting/action M13/M14 → governance M19/M48).

\# \*\*V5.2 M30 — Disclosure Reporting & Narrative Hub\*\* 

\# 

\#\#\# \*\*Purpose\*\*

Module 30 generates Disclosure Reports that are strictly anchored to Disclosure Ledger entries (Module 29), audience-specific (patient vs regulator), and reproducible under versioned schemas.    
It binds narrative explanations from Module 25 to each ledger entry and packages these into jurisdiction-specific report formats governed by disclosure appendices.    
Module 30 exposes QA/oversight hooks for Modules 19 and 41 and does not store guideline, disease, or drug knowledge.

\#\#\# \*\*Scope\*\*

\*\*In scope\*\*

\* Ledger-only report assembly from Module 29 Disclosure Ledger entries (AuditEvent \\+ Provenance \\+ DocumentReference).    
\* Dual-audience report generation: patient-facing plain-language reports and regulator-facing technical lineage reports.    
\* Narrative binding from Module 25 to each ledger record via DocumentReference and inclusion in reports as appropriate.    
\* Version-controlled replayability using PacketVersion and LedgerSchemaVersion with deterministic re-runs given the same ledger snapshot, overlays, and version IDs.    
\* Inclusion of denied disclosure records with denialReason in both patient and regulator outputs (no silent omissions).    
\* Jurisdiction-aware slicing using retention/access policies to select ledger slices per jurisdiction.    
\* Oversight integration: metrics and bundles to Module 19 and audit bundles to Module 41\\.    
\* Report-generation provenance: log each report generation event as AuditEvent \\+ Provenance including purpose, consent, profiles, overlays, and version IDs.

\*\*Out of scope\*\*

\* Any embedded medical guideline, disease fact, drug class, contraindication list, lab interpretation table, or phenotype dictionary.    
\* Storing guideline, disease, or drug knowledge inside Module 30\\.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`DisclosureLedgerSlice\` (from Module 29): list of disclosure ledger entries where each entry is an \`AuditEvent \+ Provenance \+ DocumentReference\` triplet.    
\* \`NarrativeBindings\` (from Module 25): \`DocumentReference\` pointers to narrative explanations associated with ledger entries.    
\* \`PurposeOfUse\` (for report generation event logging).    
\* \`ConsentVersion\` (for report generation event logging).    
\* \`ProfileID\` (for report generation event logging).    
\* \`JurisdictionOverlayID\[\]\` (for jurisdiction-aware slicing and event logging).    
\* \`PacketVersion\` (mandatory output version tag and event logging).    
\* \`LedgerSchemaVersion\` (mandatory output version tag and event logging).    
\* \`DisclosurePolicyVersion\` (H.34 policy version in effect at generation time).    
\* \`DisclosureReportSchemaVersion\` (H.36 schema version in effect at generation time).    
\* \`Module41LinkageRefs\` (references to related suppression episodes for oversight linkage).

\#\#\# \*\*Outputs\*\*

\* \`PatientDisclosureReport\` (plain-language, ledger-anchored report including denial events and jurisdiction-specific notes).    
\* \`RegulatorDisclosureReport\` (technical report including AuditEvent, Provenance, overlays, transforms, ProfileID, PacketVersion, LedgerSchemaVersion).    
\* \`ReportGenerationAuditEvent\` (AuditEvent for report generation with required context fields).    
\* \`ReportGenerationProvenance\` (Provenance linking the report to the exact ledger slice and narrative bindings used).    
\* \`QAAndOversightMetrics\` (metrics and bundles routed to Module 19 and Module 41).

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest inputs\*\*: receive \`DisclosureLedgerSlice\` from Module 29 and \`NarrativeBindings\` (DocumentReferences) from Module 25\\.    
2\. \*\*Enforce ledger-only rule\*\*: restrict report assembly inputs to ledger entries (AuditEvent \\+ Provenance \\+ DocumentReference) and associated narrative DocumentReferences.    
3\. \*\*Select ledger slice by jurisdiction\*\*: assemble the report input set by applying jurisdiction-aware slicing using time windows and retention/access rules so the report uses the appropriate ledger slice per jurisdiction.    
4\. \*\*Bind narratives\*\*: for each ledger entry in the selected slice, attach the corresponding Module 25 narrative via \`DocumentReference\` and carry the narrative through to patient-facing reports and into regulator reports as appropriate.    
5\. \*\*Guarantee denial inclusion\*\*: ensure every denied disclosure record appears in both patient and regulator reports with explicit \`denialReason\` and is never dropped.    
6\. \*\*Assemble dual-audience outputs\*\*:    
   \* Build \`PatientDisclosureReport\` as a plain-language narrative history including denial events and jurisdiction-specific notes.    
   \* Build \`RegulatorDisclosureReport\` with full technical lineage (AuditEvent, Provenance, overlays, transforms, ProfileID, PacketVersion, LedgerSchemaVersion).    
7\. \*\*Apply version tags for replayability\*\*: tag both reports with \`PacketVersion\` and \`LedgerSchemaVersion\` such that rerunning with the same ledger snapshot, overlays, and version IDs reproduces identical outputs.    
8\. \*\*Emit oversight outputs\*\*: compute and surface disclosure counts, denial patterns, overlay usage, and latency metrics to Module 19 and audit bundles to Module 41 for cross-checking suppression vs disclosure consistency.    
9\. \*\*Log report-generation provenance\*\*: for each report generation run, create an \`AuditEvent\` \\+ \`Provenance\` capturing PurposeOfUse, ConsentVersion, ProfileID, JurisdictionOverlayID(s), PacketVersion, LedgerSchemaVersion, and linkage to the exact ledger slice used.    
10\. \*\*Record replayability guardrails\*\*: store a hash/checksum of the ledger slice and configuration (overlays, filters) used to build the report so identical inputs \\+ version IDs guarantee identical outputs.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Reports derive exclusively from Module 29 Disclosure Ledger entries to prevent drift between logged events and reported disclosures.    
\* Patient-facing and regulator-facing reports are explicitly separated, with the regulator report containing full technical lineage including PacketVersion and LedgerSchemaVersion.    
\* Denied disclosure records must always appear in both report types with denialReason and must never be silently omitted.    
\* Every report generation event must log an AuditEvent \\+ Provenance with PurposeOfUse, ConsentVersion, ProfileID, JurisdictionOverlayID, and PacketVersion.    
\* Module 30 does not contain embedded medical guideline, disease, drug, lab interpretation, or phenotype dictionary content.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Module 29\*\* — Disclosure Ledger (source of all reportable entries).    
\* \*\*Module 25\*\* — System-Wide Narrative Synthesizer (narrative explanations bound via DocumentReference).    
\* \*\*Module 19\*\* — QA & Continuous Learning (receives disclosure metrics).    
\* \*\*Module 41\*\* — Reflex Suppression Audit Trail (receives audit bundles for suppression vs disclosure cross-checks).    
\* \*\*Appendix H.34\*\* — Disclosure Retention & Access Policy.    
\* \*\*Appendix H.35\*\* — Disclosure Oversight & QA Integration.    
\* \*\*Appendix H.36\*\* — Disclosure Report Schema.    
\* \*\*Appendix H.39\*\* — Disclosure versioning/retention hooks (PacketVersion \\+ LedgerSchemaVersion enforcement).    
\* \*\*Appendix C.11\*\* — AuditEvent/Provenance governance and triplet pattern with F.30.    
\* \*\*Appendix F.30\*\* — Disclosure Reporting & Narrative Hub Lineage.

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* \*\*Report generation AuditEvent\*\* must include: PurposeOfUse, ConsentVersion, ProfileID, JurisdictionOverlayID(s), PacketVersion, LedgerSchemaVersion, and a link to the exact ledger slice used.    
\* \*\*Input lineage\*\* must include IDs of all Disclosure Ledger entries included or explicitly excluded, including denials and expired records flagged as \`DataAbsentReason=expired\` under H.34.    
\* \*\*Narrative lineage\*\* must include DocumentReference pointers to each narrative explanation used, including version IDs of narrative templates if applicable.    
\* \*\*Suppression & oversight linkage\*\* must include references from each report to related suppression episodes in Module 41 and the QA metric aggregates routed to Module 19\\.    
\* \*\*Schema & policy versions\*\* must include H.34 policy version, H.36 schema version, and Appendix L version identifiers in effect at generation time.    
\* \*\*Replayability guardrails\*\* must include a hash/checksum of the ledger slice and configuration (overlays, filters) used to build the report.

\# \*\*V5.2 M31 — Compliance Export Hub\*\* 

\#\#\# \*\*Purpose\*\*

Module 31 generates compliance-grade export packets for regulators and auditors by transforming the Disclosure Ledger (M29) and Disclosure Reports (M30) into regulator-ready, jurisdiction-aware artifacts.    
It ensures every export is ledger-anchored, consent-bound, overlay-enforced, and fully versioned (PacketVersion \\+ LedgerSchemaVersion) for exact replay, embedding AuditEvent \\+ Provenance \\+ ProfileID \\+ ConsentVersion \\+ JurisdictionOverlayID(s) into each packet.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Generate compliance exports derived only from Disclosure Ledger entries (M29), optionally using Disclosure Reports (M30) for readability.    
\* Bind exports to ConsentVersion (M26) and PB-DMAO minimization lineage (M27: ProfileIDs, transform lists, suppression details).    
\* Enforce JurisdictionOverlayID(s) (H.26) and produce denied compliance packets when overlays conflict or cannot be satisfied.    
\* Include denied disclosure records in compliance exports with denialReason, distinguishable in regulator packets.    
\* Log export generation as FHIR AuditEvent (exportGenerated) \\+ Provenance and store replayable audit copies.

\*\*Out of scope\*\*

\* Defining step-by-step lineage rules beyond referencing Appendix F.31.    
\* Defining schema versioning/change management beyond referencing Appendix L.    
\* Defining jurisdiction overlay contents or retention rules beyond referencing H.26 and H.34.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`disclosureLedgerEntries\[\]\` (from M29)    
\* \`disclosureReports\[\]\` (from M30; optional for readability)    
\* \`consentVersion\` (from M26; bound to time of disclosure)    
\* \`profileId\` (from M27 / PB-DMAO lineage)    
\* \`transformList\[\]\` (from M27; includes suppression flags where applicable)    
\* \`jurisdictionOverlayIds\[\]\` (from H.26)    
\* \`packetVersion\`    
\* \`ledgerSchemaVersion\`    
\* \`purposeOfUse\`    
\* \`requesterIdentity\`, \`requesterOrganization\`    
\* \`exportFormat\`    
\* \`narrativeDocumentReferences\[\]\` (from M25; minimization/suppression/disclosure policy snippets)    
\* \`exportScheduleContext\` (scheduled vs ad hoc; ledger state at generation time)

\#\#\# \*\*Outputs\*\*

\* \`complianceExportPacket\` (regulator-ready artifact)    
\* \`deniedCompliancePacket\` (when blocked; includes \`denialReason\`)    
\* \`packetMetadata\` including \`ProfileID\`, \`ConsentVersion\`, \`JurisdictionOverlayIDs\`, and transform/suppression lineage as required    
\* \`auditEventExportGenerated\` (FHIR AuditEvent)    
\* \`provenance\` linking ledger entries, reports (if used), transforms/ProfileIDs, and narrative references    
\* \`auditCopy\` (hash-verified) stored for replay/dispute resolution

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Select input source of truth\*\*: Load the relevant \`disclosureLedgerEntries\[\]\` from M29 as the only authoritative input for compliance export content.    
2\. \*\*Optional readability enrichment\*\*: If a regulator-ready readable view is required, attach \`disclosureReports\[\]\` from M30 as a readability layer without changing the ledger-ground-truth content.    
3\. \*\*Bind consent and minimization lineage\*\*: For each included ledger entry, bind \`consentVersion\` (M26) and minimization lineage from M27 (\`profileId\`, \`transformList\[\]\`, suppression details).    
4\. \*\*Apply jurisdiction overlay enforcement\*\*: Apply \`jurisdictionOverlayIds\[\]\` (H.26) to govern packet fields/structure.    
5\. \*\*Overlay conflict handling\*\*: If overlays conflict or cannot be satisfied, generate a \`deniedCompliancePacket\` instead of a malformed output, with a distinguishable denial record and \`denialReason\`.    
6\. \*\*Denial inclusion rule\*\*: Ensure denied disclosure records are included in compliance exports and are not silently omitted; each denial includes \`denialReason\` and is distinguishable in regulator-facing packets.    
7\. \*\*Embed regulator narrative snippets\*\*: Embed narrative snippets from M25 that explain minimization, suppression, and disclosure policies in plain language (non-patient-facing packet context).    
8\. \*\*Version tagging and replayability\*\*: Tag the packet with \`packetVersion\` \\+ \`ledgerSchemaVersion\`, and ensure identical inputs and version IDs yield identical packets.    
9\. \*\*Event-linked generation timing\*\*: For scheduled or ad hoc exports, generate against the actual ledger state at generation time; reruns using the same ledger snapshot and version IDs produce identical artifacts.    
10\. \*\*Audit logging (exportGenerated)\*\*: Emit FHIR \`AuditEvent(exportGenerated)\` containing timestamp, requester identity/organization, PurposeOfUse, JurisdictionOverlayID(s), export format, and PacketVersion \\+ LedgerSchemaVersion.    
11\. \*\*Provenance linking\*\*: Emit \`Provenance\` linking to: ledger entries (M29), reports used (M30, if any), minimization transforms/ProfileIDs (M27), and narrative DocumentReferences (M25).    
12\. \*\*Audit copy retention\*\*: Store a hash-verified audit copy of the packet (including denied packets) for dispute resolution and replay under the same version IDs.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* All compliance exports must be derived only from Disclosure Ledger entries (M29); no side channels.    
\* Disclosure Reports (M30) may be used for readability, but the ledger remains the ground truth.    
\* If overlays conflict or cannot be satisfied, output must be a denied compliance packet rather than malformed output.    
\* Denied disclosure records must always be included in compliance exports; silent omissions are prohibited.    
\* Outputs must be tagged with PacketVersion \\+ LedgerSchemaVersion; identical inputs and version IDs must yield identical packets.    
\* Detailed lineage, schema versioning, overlays, and retention are authoritative in Appendix F.31, Appendix L, Appendix H.26, and H.34 (referenced, not duplicated).

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Modules: M25, M26, M27, M29, M30    
\* Appendices: F.31, H.26, H.34, L

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* AuditEvent \`exportGenerated\`: timestamp, requester identity/organization, PurposeOfUse, JurisdictionOverlayID(s), export format, PacketVersion \\+ LedgerSchemaVersion.    
\* Provenance links to: Disclosure Ledger entries (M29), Disclosure Reports used (M30), minimization transforms/ProfileIDs (M27), narrative DocumentReferences (M25).    
\* Packet metadata inside export: ProfileID, ConsentVersion, JurisdictionOverlayIDs, transform list and suppression flags as part of lineage (if not already recorded upstream).    
\* Denial recording: Denied Compliance Packet record with denialReason linked to triggering ledger entries and overlays.    
\* Replayability artifacts: hash-verified audit copies stored for replay under the same version IDs.

d

\# \*\*V5.2 M32 — Research & QA Export Hub\*\*

\#\#\# \*\*Purpose\*\*

Module 32 is the governed hub for creating Research and QA Export Packets that are consent-aware, minimization-profile-driven, and fully reproducible. It validates PurposeOfUse, enforces profiles and overlays, binds exports to consent and ledger entries, and tags exports with version IDs for replayable audits.

\#\#\# \*\*Scope\*\*

\*\*In scope\*\*

\* Generate export artifacts for \*\*PurposeOfUse ∈ {QA, RESEARCH}\*\* and deny all other purposes.    
\* Enforce consent-first gating (Research consent flag for Research exports; QA exports consistent with consent scope and ethical safeguards).    
\* Require exports operate only on PB-DMAO output (already minimized) and carry forward ProfileID, transform list, and JurisdictionOverlayID(s) without re-derivation.    
\* Produce FHIR-native provenance (AuditEvent, Provenance) and package outputs as Bundle with DocumentReference narratives.    
\* Tag all exports/denials with PacketVersion \\+ LedgerSchemaVersion and guarantee replayability given identical inputs and version IDs.    
\* Log all exports and denials into Disclosure Ledger and ensure downstream visibility in patient disclosure reports and compliance exports.

\*\*Out of scope\*\*

\* Any disease facts, guideline logic, drug knowledge, lab interpretation tables, phenotype dictionaries, ontology mirrors, or law summaries.    
\* Any re-definition of minimization profile semantics, PurposeOfUse catalog, overlay contents, or version-control policy (Module 32 references the canonical sources).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \*\*ExportRequest\*\*    
  \* \`requestId\`    
  \* \`requesterIdentity\`    
  \* \`purposeOfUse\` (expected values: \`QA\` | \`RESEARCH\`)    
  \* \`requestedProfileId\`    
  \* \`pb\_dmao\_output\_bundle\_ref\` (reference to minimized bundle)    
  \* \`consentVersion\`    
  \* \`consentStateAtDecisionTime\`    
  \* \`researchConsentFlag\` (for Research exports)    
  \* \`jurisdictionOverlayIds\[\]\`    
  \* \`packetVersion\`    
  \* \`ledgerSchemaVersion\`    
\* \*\*UpstreamLineage\*\*    
  \* \`profileId\`    
  \* \`transformList\[\]\`    
  \* \`jurisdictionOverlayIds\[\]\`    
\* \*\*DenialContext\*\* (when applicable)    
  \* \`denialReason\`    
  \* \`narrativePointerRef\` (DocumentReference link target)

\#\#\# \*\*Outputs\*\*

\* \*\*ResearchOrQAExportPacket\*\*    
  \* \`bundle\` (FHIR Bundle)    
  \* \`documentReferenceNarrative\`    
  \* \`auditEvent\`    
  \* \`provenance\`    
  \* \`packetVersion\`    
  \* \`ledgerSchemaVersion\`    
\* \*\*DeniedExportRecord\*\* (Denied Research/QA Record)    
  \* \`denialReason\`    
  \* \`consentVersion\`    
  \* \`requestedProfileId\`    
  \* \`jurisdictionOverlayIds\[\]\`    
  \* \`auditEvent\`    
  \* \`provenance\`    
  \* \`documentReferenceNarrativePointer\`    
\* \*\*DisclosureLedgerWrite\*\*    
  \* \`ledgerEntryRef\` (linkage to Module 29 record)

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Receive ExportRequest\*\* with \`purposeOfUse\`, \`requesterIdentity\`, \`requestedProfileId\`, \`pb\_dmao\_output\_bundle\_ref\`, \`consentVersion\`, \`jurisdictionOverlayIds\[\]\`, \`packetVersion\`, \`ledgerSchemaVersion\`.    
2\. \*\*Validate PurposeOfUse\*\*:    
   \* If \`purposeOfUse\` is not \`QA\` or \`RESEARCH\`, \*\*deny\*\*.    
3\. \*\*Consent-first gating\*\*:    
   \* If \`purposeOfUse \= RESEARCH\`, require \`researchConsentFlag \= true\` at decision time; otherwise \*\*deny\*\*.    
   \* If \`purposeOfUse \= QA\`, require request is consistent with consent scope and ethical safeguards; if not, \*\*deny\*\*.    
4\. \*\*Require PB-DMAO output\*\*:    
   \* Resolve \`pb\_dmao\_output\_bundle\_ref\`.    
   \* Assert the export source is PB-DMAO output and that upstream lineage provides \`profileId\`, \`transformList\[\]\`, and \`jurisdictionOverlayIds\[\]\`; do not re-derive these values locally.    
5\. \*\*Overlay enforcement\*\*:    
   \* Use \`jurisdictionOverlayIds\[\]\` as provided by upstream governance; if overlay conflict blocks export, \*\*deny\*\*.    
6\. \*\*Assemble export artifact (approved path)\*\*:    
   \* Package the export as a \*\*FHIR Bundle\*\*.    
   \* Create \*\*AuditEvent\*\* recording requester identity, declared PurposeOfUse, timestamp, export type, and outcome=approved.    
   \* Create \*\*Provenance\*\* capturing \`profileId\`, \`transformList\[\]\`, \`consentVersion\`, \`jurisdictionOverlayIds\[\]\`, \`packetVersion\`, and \`ledgerSchemaVersion\`.    
   \* Attach/emit \*\*DocumentReference\*\* for export narratives as required.    
7\. \*\*Assemble denial artifact (denied path)\*\*:    
   \* Create a \*\*Denied Export Record\*\* including \`denialReason\`, \`consentVersion\`, \`requestedProfileId\`, \`jurisdictionOverlayIds\[\]\`, and a narrative pointer for patient/regulator views.    
   \* Create \*\*AuditEvent\*\* with outcome=denied and the same requester/purpose fields.    
   \* Create \*\*Provenance\*\* capturing \`profileId\` (requested), \`transformList\[\]\` (if any), \`consentVersion\`, \`jurisdictionOverlayIds\[\]\`, \`packetVersion\`, \`ledgerSchemaVersion\`.    
8\. \*\*Ledger anchoring & downstream visibility (both paths)\*\*:    
   \* Write an entry into \*\*Module 29 (Disclosure Ledger)\*\* for every export request (approved or denied), linking to AuditEvent/Provenance and the export packet or denial record.    
   \* Ensure each export/denial is surfaced into \*\*Module 30 (Disclosure Reports)\*\* and \*\*Module 31 (Compliance Hub)\*\* with version identifiers and overlay IDs.    
9\. \*\*Replayability requirement\*\*:    
   \* Enforce that identical inputs with the same \`packetVersion\` \\+ \`ledgerSchemaVersion\` produce identical exports, and that sufficient metadata exists to regenerate the dataset from a ledger snapshot and version IDs.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Only PurposeOfUse values \*\*QA\*\* and \*\*RESEARCH\*\* are eligible; others are denied.    
\* Research exports require an explicit Research consent flag at export time; lack of consent or overlay conflict results in denial with a logged denied record.    
\* Exports may not bypass minimization profiles or consent validation; no silent exports are allowed.    
\* Module 32 must not contain or embed MKE-owned “world knowledge” (guidelines, disease facts, drug/lab tables, ontology mirrors, law summaries).    
\* Overlay IDs are treated as opaque identifiers and are enforced/recorded via provenance and denials without redefinition.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Modules:\*\* 26, 27, 29, 30, 31    
\* \*\*Appendices:\*\* F.32, H.24, H.25, H.26, H.46, H.47, L

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

For each Research/QA export request (approved or denied), log:

\* \*\*AuditEvent:\*\* requester identity, declared PurposeOfUse, timestamp, export type, outcome (approved/denied).    
\* \*\*Provenance:\*\* ProfileID, transform list, ConsentVersion and consent state at decision time, JurisdictionOverlayID(s), PacketVersion, LedgerSchemaVersion.    
\* \*\*Disclosure Ledger entry (Module 29):\*\* linkage to AuditEvent/Provenance; include Denied Export Records with DenialReason and narrative pointer when denied.    
\* \*\*Downstream visibility proof:\*\* confirmation that each export/denial appears in Module 30 and Module 31 with version identifiers and overlay IDs.    
\* \*\*Replayability metadata:\*\* sufficient metadata to regenerate the dataset exactly from a ledger snapshot and version IDs.

\# \*\*V5.2 M33 — Governed Export & Disclosure Packetization\*\*

\#\# \*\*Purpose\*\*

Construct a \*\*governed Disclosure Packet\*\* for every export request by wrapping:

1\. the \*\*minimized payload\*\* (from V5.2-A1), and    
2\. the \*\*narrative explanation\*\* (from the narrative surface),    
   into a \*\*schema-stable, replayable packet\*\* with strict \*\*PurposeOfUse / ConsentVersion / overlay / version binding\*\* and explicit \*\*denial semantics\*\*.

\#\# \*\*Scope\*\*

\#\#\# \*\*In scope\*\*

\* Build Disclosure Packets with canonical structure: \*\*Header, Payload, Narrative, Lineage, Signature\*\*    
\* Enforce: \*\*PurposeOfUse declared\*\*, \*\*consent already validated upstream\*\*, \*\*overlay set recorded\*\*, \*\*PacketVersion \\+ LedgerSchemaVersion present\*\*    
\* Choose exactly \*\*one Packet Type per export\*\* (e.g., Right-of-Access, Research, QA, Regulatory, Denied) per governed schema/taxonomy    
\* Produce \*\*Denied Packets\*\* when export is blocked (consent/overlay conflict), with denialReason and full lineage (no silent failure)    
\* Emit \*\*AuditEvent \\+ Provenance\*\* for packet generation; ensure replayability and downstream ledger anchoring

\#\#\# \*\*Out of scope\*\*

\* Performing minimization/de-ID transforms (owned by \*\*V5.2-A1\*\*)    
\* Being the accounting system of record (owned by \*\*V5.2-A3\*\*)    
\* Defining consent state machine or overlays (consumed; not authored here)

\#\# \*\*Inputs\*\*

\* \*\*Minimized payload bundle\*\* \\+ transform lineage pointer(s) from V5.2-A1    
\* \*\*PurposeOfUse\*\* (declared), \*\*ConsentVersion\*\*, \*\*ProfileID\*\*, \*\*JurisdictionOverlayID(s)\*\*    
\* \*\*Packet Type request\*\* (or derivation rule from audience/purpose)    
\* \*\*Narrative component\*\* (patient-facing or regulator-facing explanation) bound to the same IDs (purpose/consent/overlays)    
\* \*\*Versioning IDs:\*\* PacketVersion, LedgerSchemaVersion

\#\# \*\*Outputs\*\*

\* \*\*Disclosure Packet\*\* (Header \\+ Payload \\+ Narrative \\+ Lineage \\+ Signature)    
\* \*\*Denied Packet\*\* (same structural envelope, denialReason surfaced, lineage preserved)    
\* \*\*Packet generation AuditEvent \\+ Provenance\*\* with all binding IDs and replayability metadata    
\* \*\*Downstream handoff object\*\* suitable for disclosure accounting (V5.2-A3)

\#\# \*\*Process / Logic\*\*

1\. \*\*Validate export declaration\*\*    
\* Require declared \*\*PurposeOfUse\*\*. If missing → build \*\*Denied Packet\*\* (denialReason=UndefinedPurpose) and log.    
2\. \*\*Require upstream minimization validation\*\*    
\* Confirm input payload is a \*\*minimized bundle\*\* already bound to \*\*ConsentVersion / ProfileID / JurisdictionOverlayID(s)\*\*.    
\* If missing or inconsistent → \*\*Denied Packet\*\* (denialReason=MissingOrInvalidMinimizationLineage).    
3\. \*\*Select exactly one Packet Type\*\*    
\* Choose one packet type for the export event (Right-of-Access / Research / QA / Regulatory / Denied).    
\* Enforce “\*\*one packet type per export\*\*.”    
4\. \*\*Assemble packet envelope\*\*    
\* \*\*Header:\*\* PurposeOfUse, ConsentVersion, ProfileID, JurisdictionOverlayID(s), Timestamp, PacketVersion, LedgerSchemaVersion, requesterRole/audience tier.    
\* \*\*Payload:\*\* minimized bundle (no additional transforms applied here).    
\* \*\*Narrative:\*\* audience-appropriate explanation bound to the same event IDs.    
\* \*\*Lineage:\*\* provenance pointers to minimization transforms and any upstream denials/overrides; no silent drops.    
\* \*\*Signature:\*\* hash/signature metadata enabling replayability/integrity.    
5\. \*\*Denial handling\*\*    
\* If consent/overlay policy blocks export (or upstream provided denial), produce \*\*Denied Packet\*\* (not a partial packet).    
\* Denied packets must still include narrative \\+ lineage and be auditable.    
6\. \*\*Emit audit artifacts\*\*    
\* Log packet creation as \*\*AuditEvent \\+ Provenance\*\*, including: purpose, consent, overlays, profile, packet type, PacketVersion, LedgerSchemaVersion, and lineage pointers.

\#\# \*\*Governance / Constraints\*\*

\* \*\*No silent exports:\*\* every export request yields a packet (approved or denied) with accounting-ready lineage.    
\* \*\*No new transforms here:\*\* packetizer does not mask/bucket/date-shift; it packages what V5.2-A1 already produced.    
\* \*\*Replayability invariant:\*\* identical input bundle \\+ ConsentVersion \\+ ProfileID \\+ overlays \\+ PacketVersion/LedgerSchemaVersion ⇒ identical packet.    
\* \*\*Transparency mandate:\*\* denials must be visible and explicit; no phantom packets; no silent failures.

\#\# \*\*Dependencies\*\*

\* \*\*Upstream:\*\* V5.2-A1 provides minimized payload \\+ transform lineage and denial states.    
\* \*\*Narrative surface:\*\* supplies the narrative component bound to this export event’s IDs.    
\* \*\*Downstream:\*\* V5.2-A3 records packet events in the Disclosure Ledger (accounting).

\#\# \*\*Audit Hooks\*\*

For each export request (approved or denied), must record:

\* PurposeOfUse, ConsentVersion, ProfileID, JurisdictionOverlayID(s)    
\* PacketType, PacketVersion, LedgerSchemaVersion    
\* Lineage pointers to upstream transforms (and denialReason when denied)    
\* Requester identity/role and audience tier

\---

\#\# \*\*Mapping Table (V5.2-A2 section ↔ V5.1′ source)\*\*

| V5.2-A2 Section | Source in V5.1′ |  
| \----- | \----- |  
| Packet purpose \\+ envelope schema | M28 purpose \\+ packet schema references |  
| “Purpose-bound act” \\+ precondition of minimization | M28 logic retention: purpose declared; upstream validation |  
| Denied packet semantics, strictest-rule wins, no silent drops | M28 logic retention \\+ denial semantics |  
| Replayability binding (PacketVersion/LedgerSchemaVersion) | M28 replayability language \\+ downstream visibility expectations |

\---

\# \*\*V5.2 M35 — Data Masking Hub\*\* 

\#\#\# \*\*Purpose\*\*

Module 35 is the governed hub for reversible and irreversible data masking, executing minimization profiles, consent checks, and jurisdiction overlays for Research, QA, Compliance, and Operational use cases.    
It applies already-defined profiles and overlays to PB-DMAO–minimized bundles under the active ConsentVersion and logs every masking transform with full lineage for replayable, audit-grade visibility.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Centralized execution of all data masking (reversible, irreversible, partial) using ProfileID-driven transforms and JurisdictionOverlayID(s).    
\* Consent binding for each masking request and issuance of Denied Masking Records when consent/purpose is insufficient.    
\* Audit-grade lineage logging (AuditEvent \\+ Provenance \\+ PacketVersion \\+ LedgerSchemaVersion) and writing masking events into the Disclosure Ledger for downstream visibility.

\*\*Out of scope\*\*

\* Any masking/unmasking performed outside Module 35\\.    
\* Storage of disease knowledge, guideline content, drug classes, ontology mirrors, lab interpretation tables, or phenotype dictionaries.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`patient\_id\` (patient identifier)    
\* \`packet\_id\` (PacketID)    
\* \`purpose\_of\_use\` ∈ {RESEARCH, QA, COMPLIANCE, OPERATIONAL}    
\* \`consent\_version\` (active ConsentVersion; from Module 26\\)    
\* \`profile\_id\` (from Appendix H.24)    
\* \`jurisdiction\_overlay\_ids\[\]\` (JurisdictionOverlayID(s); from Appendix H.26)    
\* \`packet\_version\`    
\* \`ledger\_schema\_version\`    
\* \`requester\_identity\` (identity)    
\* \`requester\_role\` (role)    
\* \`pb\_dmao\_minimized\_bundle\` (PB-DMAO–minimized bundle from Module 27\\)

\#\#\# \*\*Outputs\*\*

\* \`masked\_packet\` (masked output packet)    
\* \`denied\_masking\_record\` (Denied Masking Record, when applicable)    
\* \`audit\_event\` (AuditEvent for each masking event, including denied)    
\* \`provenance\` (Provenance for each masking event, including denied)    
\* \`disclosure\_ledger\_entry\_id\` (Module 29 Disclosure Ledger entry pointer)    
\* Downstream-consumable masked outputs for Modules 31–34 and 32–33 as applicable.

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Enforce exclusivity\*\*: accept masking requests only through Module 35; no other module may mask or unmask.    
2\. \*\*Bind request context\*\*: read \`patient\_id\`, \`packet\_id\`, \`purpose\_of\_use\`, \`consent\_version\`, \`profile\_id\`, \`jurisdiction\_overlay\_ids\[\]\`, \`packet\_version\`, \`ledger\_schema\_version\`, \`requester\_identity\`, \`requester\_role\`, and the \`pb\_dmao\_minimized\_bundle\`.    
3\. \*\*Consent \\+ purpose validation\*\*: validate the masking request against the active \`consent\_version\` and declared \`purpose\_of\_use\`.    
4\. \*\*On insufficient consent/purpose\*\*: do not run masking; create a \`denied\_masking\_record\` with \`denialReason\`, consent state, overlays, and narrative as governed by H.25/H.58.    
5\. \*\*Profile-driven masking\*\*: if permitted, read \`profile\_id\` and apply the profile’s transforms (redaction, truncation, pseudonymization tokens, partial suppression) to the Module 27 minimized bundle, varying configuration by \`purpose\_of\_use\`.    
6\. \*\*Jurisdiction overlay enforcement\*\*: apply \`jurisdiction\_overlay\_ids\[\]\` (Appendix H.26) to enforce masking constraints.    
7\. \*\*Lineage object creation\*\*: for every masking event (approved or denied), create \`audit\_event\` \\+ \`provenance\` capturing \`purpose\_of\_use\`, \`consent\_version\`, \`profile\_id\`, \`jurisdiction\_overlay\_ids\[\]\`, \`packet\_version\`, and \`ledger\_schema\_version\`.    
8\. \*\*Transform detail logging\*\*: record transform type (reversible/irreversible/partial), scope (field vs record), and parameters (token IDs, ranges, redaction pattern).    
9\. \*\*Disclosure ledger write\*\*: write the masking event (including denials) into the Disclosure Ledger (Module 29\\) and ensure visibility downstream (Modules 30 and 31).    
10\. \*\*Replayability guarantee\*\*: require that identical inputs \\+ profile \\+ overlays \\+ version IDs produce deterministic outputs.    
11\. \*\*Downstream handoff\*\*: provide masked outputs for Research/QA exports (32), Federated research hub (33), De-ID/Pseudonymization hub (34), and Compliance exports (31).

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* All data masking (reversible and irreversible) must be performed by Module 35; no other module may mask or unmask data.    
\* Module 35 does not contain external clinical knowledge (no disease descriptions, guidelines, drug classes, ontology mirrors, lab interpretation tables, phenotype dictionaries).    
\* If consent or purpose is insufficient, masking must not run; a Denied Masking Record must be logged.    
\* All masking events must populate Disclosure & Access Accounting, and denial/ethical override/expiry semantics are surfaced via Modules 29–31.    
\* Appendix authority: lineage and transform semantics are defined in Appendix F.35; profiles/overlays and masking schema/retention semantics are defined in H.24, H.26, and H.56–H.59; disclosure/denial behavior is governed by H.23/H.27/H.33/H.34.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Modules\*\*: 26, 27, 29, 30, 31, 32, 33, 34 (and QA/suppression audit references: 19, 41).    
\* \*\*Appendices\*\*: F.35; H.24; H.25; H.26; H.56–H.59; H.23; H.27; H.33; H.34.

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

For every masking event (including denied ones), log at minimum: patient identifier, PacketID, PurposeOfUse, ConsentVersion, ProfileID, JurisdictionOverlayID(s), transform type, scope, parameters, PacketVersion, LedgerSchemaVersion, requester identity/role, AuditEvent \\+ Provenance IDs, Disclosure Ledger entry ID, denial flags (denialReason, overrideReason if Ethical Override fired, consent state at denial, overlay set at denial), and retention status with DataAbsentReason=expired when applicable.

\# \*\*V5.2 M36 — Generalization & Bucketing Hub\*\*

\#\#\# \*\*Purpose\*\*

Module 36 is the governed hub for generalization, bucketing, and controlled coarsening of quasi-identifiers across Research, QA, and Compliance exports.

\#\#\# \*\*Scope\*\*

\*\*In scope\*\*

\* Profile-driven generalization and bucketing of quasi-identifiers on minimized bundles, under consent and jurisdiction overlays.    
\* Emission of GeneralizedPacket outputs with lineage, version tags, and denial records when required.

\*\*Out of scope\*\*

\* Any “generalization” performed outside Module 36\\.    
\* Disease facts, guideline content, drug classes, lab interpretations, phenotype dictionaries, or static code/evidence tables.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \*\*MinimizedBundle\*\* (from M27 PB-DMAO).    
\* \*\*Consent context\*\*: \`ConsentVersion\`, \`PurposeOfUse\` (from M26).    
\* \*\*Generalization configuration\*\*: \`ProfileID\` (Appendix H.24).    
\* \*\*Overlay configuration\*\*: \`JurisdictionOverlayID\[\]\` (Appendix H.26; bucketing rules in H.61).    
\* \*\*Versioning identifiers\*\*: \`PacketVersion\`, \`LedgerSchemaVersion\`.    
\* \*\*Request context\*\*: \`requesterIdentity\` (and role where available).

\#\#\# \*\*Outputs\*\*

\* \*\*GeneralizedPacket\*\* compliant with Appendix H.60.    
\* \*\*Generalization lineage entries\*\* per Appendix F.36 into Disclosure Ledger (M29).    
\* \*\*DeniedGeneralizationRecord\*\* per Appendix H.62 for blocked requests (consumed by M29/M30/M31).

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Enforce single front-door\*\*: reject any attempt to perform generalization outside Module 36\\.    
2\. \*\*Load inputs\*\*: ingest \`MinimizedBundle\` (M27), \`ConsentVersion\` \\+ \`PurposeOfUse\` (M26), \`ProfileID\` (H.24), and \`JurisdictionOverlayID\[\]\` (H.26/H.61).    
3\. \*\*Validate consent and purpose\*\*: if \`ConsentVersion\` or \`PurposeOfUse\` does not authorize generalization, emit \`DeniedGeneralizationRecord\` with \`DenialReason\` and overlay context, then stop.    
4\. \*\*Apply profile \\+ overlay to produce explicit bucket definitions\*\*: compute field-level bucket definitions from \`ProfileID\` \\+ overlays (e.g., DOB→age buckets, ZIP→ZIP3, timestamps→month) and apply them to the bundle.    
5\. \*\*Overlay arbitration\*\*: if multiple overlays conflict, deny the request rather than selecting one silently; emit \`DeniedGeneralizationRecord\` with narrative and overlay IDs, then stop.    
6\. \*\*Emit generalized outputs\*\*: produce \`GeneralizedPacket\` plus lineage and a version block per H.60/F.36/H.63.    
7\. \*\*Tag for replayability\*\*: attach \`PacketVersion\` and \`LedgerSchemaVersion\`; identical input \\+ profile \\+ overlay \\+ version identifiers MUST yield identical buckets/outputs.    
8\. \*\*Downstream handoff\*\*: provide outputs for M31 and for M32–M35, which assume coarsening and overlay enforcement have already occurred in Module 36\\.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* No generalization may occur outside Module 36\\.    
\* All generalization actions must be validated against active consent and declared PurposeOfUse; unauthorized actions must emit DeniedGeneralizationRecord.    
\* Overlay conflicts must result in denial and logged denial records; no silent arbitration.    
\* Outputs must be replayable under PacketVersion \\+ LedgerSchemaVersion; determinism is mandatory.    
\* Module 36 is privacy/governance execution logic only and must not contain MKE-owned content categories.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*M26\*\* (Consent): ConsentVersion, PurposeOfUse.    
\* \*\*M27\*\* (PB-DMAO): Minimized bundles.    
\* \*\*M29\*\* (Disclosure Ledger): receives lineage and denials.    
\* \*\*M30 / M31\*\*: consume denied records and generalized outputs for disclosure reporting and compliance exports.    
\* \*\*M32–M35\*\*: downstream consumers assume Module 36 coarsening is complete.    
\* \*\*Appendix H.24\*\* (Profiles), \*\*H.26\*\* (Overlays), \*\*H.60\*\* (Generalization & Bucketing Schema), \*\*H.61\*\* (Jurisdiction-specific bucketing rules), \*\*H.62\*\* (DeniedGeneralizationRecord), \*\*H.63\*\* (Versioning & retention), \*\*F.36\*\* (Lineage).

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* For every successful generalization event: \`ProfileID\`, \`overlayID\[\]\`, bucket definitions, and parameter values (e.g., range sizes, truncation levels, aggregation thresholds).    
\* For every denial: DeniedGeneralizationRecord with \`DenialReason\` (NoConsent / OverlayConflict / EthicalOverride / Other), overlay IDs, requested \`ProfileID\`, \`ConsentVersion\`, and narrative.    
\* Versioning metadata: \`PacketVersion\` \\+ \`LedgerSchemaVersion\` for each output.    
\* Request context: requester identity and declared \`PurposeOfUse\` for each request.    
\* Lifecycle/retention state changes (e.g., \`DataAbsentReason=expired\`) applied under H.63.

\# \*\*V5.2 M37 — Perturbation & Obfuscation Hub\*\* 

\#\#\# \*\*Purpose\*\*

Module 37 is the governed hub for perturbation, obfuscation, and controlled noise injection over already-minimized patient data. It applies profile-driven noise to PHI-adjacent fields for Research, QA, and Compliance exports under consent binding, jurisdiction overlays, and replayable audit trails.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Centralized perturbation/obfuscation/noise injection for already-minimized patient data.    
\* Profile-driven noise application (jitter, scaling, controlled randomization) selected from Appendix H.24 profiles for Research, QA, and Compliance.    
\* ConsentVersion and PurposeOfUse validation, including denials with Denied Perturbation Records.    
\* Jurisdiction overlay enforcement (H.26/H.65), including denial on overlay conflicts.    
\* AuditEvent \\+ Provenance capture for replayability (including seed, distribution, parameters) and version pinning (PacketVersion \\+ LedgerSchemaVersion).    
\* Emitting perturbed packets into downstream export modules and ensuring visibility in patient disclosures and regulator exports.

\*\*Out of scope\*\*

\* Performing minimization itself (consumes minimized bundles from Module 27).    
\* Defining packet schemas, lineage schemas, overlay rules, retention rules, or versioning policy text (owned by appendices).    
\* Any noise injection performed outside Module 37\\.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \*\*MinimizedBundle\*\* (from Module 27).    
\* \*\*RequestContext\*\*    
  \* \`requester\_identity\`    
  \* \`PurposeOfUse\`    
\* \*\*ConsentContext\*\*    
  \* \`ConsentVersion\` (active)    
\* \*\*OverlayContext\*\*    
  \* \`overlay\_ids\` / \`overlay\_set\` (from H.26/H.65)    
\* \*\*ProfileContext\*\*    
  \* \`ProfileID\` (from Appendix H.24)    
\* \*\*VersionContext\*\*    
  \* \`PacketVersion\`    
  \* \`LedgerSchemaVersion\`

\#\#\# \*\*Outputs\*\*

\* \*\*PerturbedPacket\*\* (schema per Appendix H.64), carrying perturbation metadata and version identifiers.    
\* \*\*DeniedPerturbationRecord\*\* (denial entry) routed into Module 29\\.    
\* \*\*Disclosure surfaces\*\*    
  \* Patient-facing description inputs for Module 30\\.    
  \* Regulator-facing lineage inputs for Module 31\\.

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Enforce single-hub rule\*\*    
   \* Reject any attempt to perform perturbation/obfuscation outside Module 37 (Module 37 is the only permitted noise-injection hub).    
2\. \*\*Resolve perturbation profile deterministically\*\*    
   \* Select perturbation rules from Appendix H.24 profiles for the declared \`PurposeOfUse\` (Research, QA, Compliance).    
   \* Apply the selected profile deterministically given \`PurposeOfUse\` and the active overlay set.    
3\. \*\*Validate consent binding and purpose gating\*\*    
   \* Validate the perturbation operation against the active \`ConsentVersion\` and declared \`PurposeOfUse\`.    
   \* If consent scope does not authorize obfuscation for that purpose, deny and emit a Denied Perturbation Record.    
4\. \*\*Enforce jurisdiction overlays\*\*    
   \* Apply overlay registry constraints from H.26/H.65 to the perturbation request.    
   \* If overlays conflict, block perturbation and emit a denial entry.    
5\. \*\*Execute perturbation on minimized input\*\*    
   \* Input must be the minimized bundle from Module 27 plus consent & overlay context.    
   \* Apply profile-driven noise (jitter, scaling, controlled randomization) to PHI-adjacent fields per the resolved profile.    
6\. \*\*Attach audit-grade provenance and replay metadata\*\*    
   \* For each perturbation run, create AuditEvent \\+ Provenance capturing: \`ProfileID\`, overlay set, \`ConsentVersion\`, noise range, distribution, seed, requester identity, and \`PurposeOfUse\`.    
   \* Ensure \`PacketVersion\` \\+ \`LedgerSchemaVersion\` are included to guarantee deterministic replay.    
7\. \*\*Emit outputs across the export stack\*\*    
   \* Emit perturbed packets for Modules 31–36.    
   \* Route Denied Perturbation Records into Module 29\\.    
   \* Ensure patient-facing descriptions are produced via Module 30 and regulator-facing lineage via Module 31\\.    
8\. \*\*Enforce transparency mandate\*\*    
   \* Perturbation must be visible in patient disclosures and regulator exports.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* All perturbation/obfuscation/noise injection must flow through Module 37; no other module may perform noise injection.    
\* Perturbation rules must be selected from Appendix H.24 profiles and applied deterministically given \`PurposeOfUse\` and overlays.    
\* Every operation must be validated against active \`ConsentVersion\` and declared \`PurposeOfUse\`; unauthorized requests are denied and logged.    
\* Overlay conflicts must block perturbation and emit a denial entry.    
\* AuditEvent \\+ Provenance must capture profile, overlays, consent, parameters, seed, requester, and purpose; PacketVersion \\+ LedgerSchemaVersion must be present for deterministic replay.    
\* Perturbation must be visible in patient disclosures and regulator exports.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* \*\*Modules:\*\* 26 (Consent), 27 (Minimized bundles input), 29 (Denied record sink), 30 (Patient-facing descriptions), 31 (Regulator-facing lineage), 31–36 (downstream perturbed packets).    
\* \*\*Appendices:\*\* H.24 (profiles), H.26/H.65 (overlay registry/constraints), F.37 (lineage & input/output \\+ FHIR mapping), H.64 (perturbation packet schema), H.34 (retention), L (PacketVersion/LedgerSchemaVersion).

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* \`requester\_identity\`, \`PurposeOfUse\`.    
\* \`ConsentVersion\` and consent scope used to authorize perturbation.    
\* \`ProfileID\` (H.24) and overlay IDs / overlay set (H.26/H.65).    
\* Perturbation parameters per field: method (jitter/scale/shuffle), range, distribution, seed.    
\* \`PacketVersion\`, \`LedgerSchemaVersion\`, and AuditEvent \\+ Provenance identifiers.    
\* Outcome: executed vs denied, with denial reason (e.g., missing consent, overlay conflict).    
\* Logging outputs must be consumable by QA (Module 19\\) and governance modules for replay, audit, and drift checks.

\# \*\*V5.2 M38 — Synthetic Data Hub\*\*

\---

\#\#\# \*\*Purpose\*\*

The Synthetic Data Hub is the governed system component responsible for generating fully synthetic datasets from minimized patient bundles for approved Research, QA, and Compliance uses. It enforces consent binding, jurisdiction overlays, profile-driven synthesis rules, and full lineage logging to ensure replayability and auditability. All synthetic generation and denial events are transparently logged and disclosed through downstream reporting and compliance modules.

\---

\#\#\# \*\*Scope\*\*

\*\*In Scope\*\*

\* Receipt of minimized patient bundles for synthetic generation.    
\* ConsentVersion and PurposeOfUse validation prior to synthesis.    
\* Application of jurisdiction overlays and synthesis profiles.    
\* Deterministic synthetic data generation with full provenance logging.    
\* Creation of Denied Synthesis Records when requests are blocked.    
\* Routing of synthetic outputs and denials to disclosure and compliance flows.

\*\*Out of Scope\*\*

\* Storage of disease knowledge, clinical guidelines, drug facts, or ontologies.    
\* Definition of consent policies, jurisdiction rules, or schema details.    
\* Narrative report generation beyond required linkage to disclosure modules.    
\* Any non-synthetic data export or live patient data handling.

\---

\#\#\# \*\*Inputs\*\*

\* Minimized patient data bundle identifiers (from PB-DMAO).    
\* Declared PurposeOfUse.    
\* Active ConsentVersion reference.    
\* JurisdictionOverlayID set.    
\* Synthesis ProfileID.    
\* Version identifiers (PacketVersion, LedgerSchemaVersion).    
\* Requester identity and role metadata.

\---

\#\#\# \*\*Outputs\*\*

\* Synthetic data packets conforming to the synthetic data schema.    
\* Denied Synthesis Records when synthesis is blocked.    
\* AuditEvent and Provenance records for each request.    
\* Disclosure Ledger entries for patient-facing reporting.    
\* Compliance export references for regulator-facing outputs.

\---

\#\#\# \*\*Process / Logic\*\*

1\. Receive a synthetic data request with minimized bundle identifiers and PurposeOfUse.    
2\. Validate the request against the active ConsentVersion for synthetic authorization.    
3\. Apply all active jurisdiction overlays to the request context.    
4\. If consent or overlays fail, generate a Denied Synthesis Record and log the event.    
5\. If validated, select the specified synthesis profile and initialize deterministic parameters.    
6\. Generate the synthetic dataset using logged model configuration and random seed(s).    
7\. Bind the output to PacketVersion, LedgerSchemaVersion, ConsentVersion, and OverlayIDs.    
8\. Log full lineage, AuditEvent, and Provenance for replayability.    
9\. Route synthetic outputs and denial records to disclosure and compliance modules.

\---

\#\#\# \*\*Governance / Constraints\*\*

\* Synthetic data generation is permitted only within this module.    
\* No synthesis occurs without explicit consent and overlay validation.    
\* Jurisdiction rules and schema definitions are referenced, not restated.    
\* Every generation or denial event must be audit-logged and replayable.    
\* No clinical knowledge or guideline content may reside in this module.

\---

\#\#\# \*\*Dependencies\*\*

\* Module 26 — Consent & Ethical Safeguards.    
\* Module 27 — PB-DMAO / Data Minimization.    
\* Module 29 — Disclosure Ledger.    
\* Module 30 — Disclosure Reporting & Narrative Hub.    
\* Module 31 — Compliance Export Hub.    
\* Appendix H.24 — Synthesis Profiles.    
\* Appendix H.26 / H.69 — Jurisdiction Overlays.    
\* Appendix H.68 — Synthetic Data Schema.    
\* Appendix H.70 — Denied Synthesis Record Spec.    
\* Appendix F.38 — Synthetic Data Lineage.    
\* Appendix L — Versioning.

\---

\#\#\# \*\*Audit Hooks\*\*

\* Request timestamp, requester identity, and declared PurposeOfUse.    
\* Input bundle scope identifiers.    
\* ConsentVersion evaluated and outcome.    
\* JurisdictionOverlayID set and validation result.    
\* Synthesis ProfileID applied.    
\* Model type, parameters, and random seed(s).    
\* PacketVersion and LedgerSchemaVersion.    
\* AuditEvent ID and Provenance linkage.    
\* Disclosure Ledger and Compliance Export references.    
\* Denial reason and patient-facing narrative reference when applicable.

\# \*\*V5.2 M39 — Linkage & Join Hub\*\*

\#\#\# \*\*Purpose\*\*

Module 39 is the governed hub for linkage, joining, and entity resolution across datasets and silos, enforcing consent-bound, profile-driven, jurisdiction-aware linkage using Appendix H.24 profiles, H.26/H.73 overlays, and Appendix H.72 schema.    
It guarantees replayable outputs by tagging each linkage with PacketVersion and LedgerSchemaVersion and logging full lineage into AuditEvent \\+ Provenance \\+ Bundle \\+ DocumentReference.    
Its job is to decide which records are lawfully linkable, execute the linkage, and log it so regulators, patients, and auditors can reproduce and inspect every join.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Linkage, joining, and entity resolution across datasets/silos under consent and jurisdiction overlays.    
\* Profile-driven linkage control, including permissible identifiers, thresholds, and allowed methods per profile.    
\* Consent binding as a hard gate; out-of-scope requests are denied and logged.    
\* Jurisdiction overlay enforcement, including overlay-based blocking and denied linkage records.    
\* Audit-grade lineage, replayability, and FHIR container outputs (AuditEvent, Provenance, Bundle, DocumentReference).

\*\*Out of scope\*\*

\* Disease facts, guideline summaries, drug-class catalogs/contraindication lists, lab interpretation tables, phenotype dictionaries, or SNOMED/ICD code lists.    
\* Defining the underlying matching algorithms; Module 39 governs allowed methods and required logging, not the algorithm implementation.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`linkage\_request.requester\_id\`    
\* \`linkage\_request.purpose\_of\_use\`    
\* \`linkage\_request.consent\_version\_id\` (+ relevant \`Consent.provision\` details reference)    
\* \`linkage\_request.data\_sources\` / \`silos\_to\_join\`    
\* \`linkage\_request.patient\_jurisdiction\` and \`data\_location\` (for overlay selection)    
\* \`pb\_dmao\_minimized\_bundles\` (Module 27 output)    
\* \`linkage\_profile\_id\` / \`linkage\_profile\` (Appendix H.24)    
\* \`jurisdiction\_overlay\_ids\` / \`overlay\_set\` (Appendix H.26/H.73)    
\* \`version\_ids.packet\_version\` (Appendix L)    
\* \`version\_ids.ledger\_schema\_version\` (Appendix L)    
\* \`linkage\_schema\` (Appendix H.72), including:    
  \* \`method\` ∈ {\`deterministic\`, \`probabilistic\`, \`ML-based\`}    
  \* \`parameters.thresholds\` / \`parameters.weights\` / \`parameters.blocking\_keys\`    
  \* \`confidence\_scores.per\_match\`    
\* \`disclosure\_ledger\_context\` (Module 29 prior context)

\#\#\# \*\*Outputs\*\*

\* \`linked\_packets\` (for downstream use by Modules 32–38)    
\* \`denied\_linkage\_record\` (surfaced in M29, M30, M31, and patient-facing history)    
\* FHIR artifacts for every linkage attempt (success or denial):    
  \* \`AuditEvent\`    
  \* \`Provenance\`    
  \* \`Bundle\` (linked dataset)    
  \* \`DocumentReference\` (config/justifications/overlay explanation)

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. Enforce single point of linkage control: route all linkage/join/entity resolution requests through Module 39\\.    
2\. Resolve the applicable \`linkage\_profile\` (Appendix H.24) from \`purpose\_of\_use\` and load the permissible identifiers, thresholds, and allowed methods.    
3\. Validate linkage request against active \`consent\_version\_id\` (Module 26), confirming the consent covers (a) the requested \`purpose\_of\_use\` and (b) the data sources/silos being joined.    
4\. Select and apply jurisdiction overlays (Appendix H.26/H.73) based on patient jurisdiction, data location, and \`purpose\_of\_use\`.    
5\. If consent validation fails or overlays prohibit linkage, create a \`denied\_linkage\_record\` with denial reason and consent/overlay context and log it to the Disclosure Ledger.    
6\. If permitted, execute entity resolution using an allowed \`method\` and record all linkage parameters (thresholds, weights, blocking keys) and per-match confidence scores in the H.72 linkage schema.    
7\. Tag each linkage output and audit copy with \`packet\_version\` and \`ledger\_schema\_version\` to guarantee replayability.    
8\. Emit FHIR lineage containers for the linkage attempt (success or denial): \`AuditEvent\`, \`Provenance\`, \`Bundle\`, and \`DocumentReference\`, and ensure the attempt is traceable by patients and regulators.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Locked rule: no linkage may occur outside Module 39, and all linkage events (including denials) are logged and surfaced to patients/regulators.    
\* Module 39 does not define the underlying matching algorithms; it governs which methods are allowed per profile and how parameters and confidence scores must be logged.    
\* Module 39 contains no disease facts, guideline summaries, drug catalogs, lab interpretation tables, phenotype dictionaries, or code lists.    
\* Replayability requirement: identical inputs plus versions yield identical outputs via PacketVersion and LedgerSchemaVersion tagging.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Modules: M26 (Consent), M27 (PB-DMAO), M29 (Disclosure Ledger), M30 (Disclosure Reporting), M31 (Compliance Export), M32–M38 (downstream consumers of linked packets).    
\* Appendices: F.39 (lineage), H.24 (profiles), H.26 (overlays), H.72 (linkage schema), H.73 (jurisdiction-specific linkage rules), H.34 (retention/lifecycle), Appendix L (PacketVersion/LedgerSchemaVersion).

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

For every linkage attempt (success or denial), log:

\* Requester identity; declared PurposeOfUse.    
\* ConsentVersion ID (+ relevant Consent.provision details reference); jurisdiction overlay IDs and constraints applied.    
\* Linkage method; thresholds, weights, blocking keys; per-match confidence scores.    
\* Outputs: linked record pairs/groups with confidence scores; or denial reason (e.g., missing consent, overlay conflict, profile violation).    
\* PacketVersion and LedgerSchemaVersion for each linkage output and audit copy.    
\* FHIR resources emitted: AuditEvent, Provenance, Bundle, DocumentReference (including config/justifications/overlay explanation).

\# \*\*V5.2 M40 — Export & Packaging Hub\*\* 

\#\#\# \*\*Purpose\*\*

Module 40 is the only governed出口 for external datasets, converting minimized/transformed bundles into export packets that are consent-bound, profile-driven, overlay-compliant, versioned, and fully auditable.    
It enforces export profiles, checks consent and jurisdiction overlays, tags packets with PacketVersion and LedgerSchemaVersion, and logs all exports into the Disclosure Ledger with replayable provenance.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Single governed export gate for all external dataset exports.    
\* Profile-driven export selection (fields/formats/fidelity) and binding to PurposeOfUse.    
\* ConsentVersion validation with denial behavior when consent is missing/insufficient.    
\* Jurisdiction overlay application at export time.    
\* Packet versioning, replayability, retention/expiration handling, and export/disclosure logging.

\*\*Out of scope\*\*

\* Any guideline/disease/drug knowledge, static code lists, or evidence tables (MKE-owned content).    
\* Drug classes / contraindication lists and clinical reasoning.    
\* Duplicating Appendix F.40 lineage details (F.40 is treated as canonical).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`export\_request\`:    
  \* \`requester\_identity\`    
  \* \`PurposeOfUse\`    
  \* \`target\_consumer\` (Module 31 or Module 32\\)    
  \* \`export\_format\`    
  \* \`export\_format\_version\`    
\* \`ConsentVersion\` (from Module 26\\)    
\* \`ExportProfileID\` / export profile configuration (from Appendix H.24)    
\* \`JurisdictionOverlayID\[\]\` (from Appendix H.26)    
\* \`PacketVersion\` (from Appendix L)    
\* \`LedgerSchemaVersion\` (from Appendix L)    
\* \`upstream\_bundles\[\]\` (from Modules 27 and 32–39)    
\* \`transform\_stack\_lineage\[\]\` (de-ID, masking, generalization, perturbation, synthesis, linkage)    
\* \`DisclosureLedger\_context\` (Module 29 reference/handles)

\#\#\# \*\*Outputs\*\*

\* \`ExportPacket\` (versioned) for:    
  \* Module 31 (Compliance) or Module 32 (Research/QA)    
\* \`DeniedExportRecord\` (with \`denialReason\`) for Disclosure Ledger (Module 29\\) and Disclosure Reports (Module 30\\)    
\* \`AuditEvent\` \\+ \`Provenance\` entries linked to the Disclosure Ledger    
\* \`expired\_indicator\` on exports that are not deliverable due to retention/expiration

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Receive export request\*\* with \`PurposeOfUse\`, \`requester\_identity\`, \`target\_consumer\`, and requested \`export\_format\`.    
2\. \*\*Collect inputs\*\*:    
   \* \`ConsentVersion\` from Module 26 and \`PurposeOfUse\`.    
   \* Applicable export profile (\`ExportProfileID\`) from Appendix H.24.    
   \* Applicable jurisdiction overlays (\`JurisdictionOverlayID\[\]\`) from Appendix H.26.    
   \* Minimized/transformed bundles from Module 27 and Modules 32–39.    
3\. \*\*Enforce Single Export Gate\*\*: proceed only within Module 40 (no alternate export path).    
4\. \*\*Validate consent\*\*:    
   \* Cross-check export request against active consent (\`ConsentVersion\`).    
   \* If consent is missing/insufficient, produce a \`DeniedExportRecord\` (no packet) and continue to Step 8 (logging).    
5\. \*\*Apply overlays at export time\*\*:    
   \* Apply \`JurisdictionOverlayID\[\]\` to the export operation.    
   \* If overlays block export (including conflicts), produce a \`DeniedExportRecord\` and continue to Step 8 (logging).    
6\. \*\*Assemble export packet\*\*:    
   \* Package the upstream bundles according to \`ExportProfileID\` (fields/formats/fidelity).    
   \* Tag output with \`PacketVersion\` and \`LedgerSchemaVersion\`.    
7\. \*\*Retention/expiration check\*\*:    
   \* Apply retention/expiration semantics governed by Appendix H.34; if expired, mark as not deliverable and include the standardized “expired” indicator.    
8\. \*\*Log and ledger-write (always)\*\*:    
   \* Write AuditEvent \\+ Provenance capturing requester, PurposeOfUse, overlays, transform stack, export format/version, and version IDs, linked into the Disclosure Ledger.    
   \* Ensure the outcome is logged as either \`ExportPacketID\` or \`DeniedExportRecordID\` with \`denialReason\` when applicable.    
9\. \*\*Deliver to consumer\*\*:    
   \* If approved and deliverable, send \`ExportPacket\` to Module 31 or Module 32 as requested/appropriate.    
   \* If denied, route \`DeniedExportRecord\` into Module 29 and ensure disclosures flow to Modules 30/31.    
10\. \*\*Replayability invariant\*\*:    
\* Ensure determinism: identical inputs \\+ profile \\+ overlays \\+ PacketVersion \\+ LedgerSchemaVersion regenerate the same export packet.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* \*\*Single Export Gate\*\*: all external datasets must flow through Module 40 and nowhere else.    
\* \*\*No MKE-owned content\*\*: do not contain or embed guideline/disease/drug knowledge, static code lists, or evidence tables.    
\* \*\*Profile-driven\*\*: export profiles (H.24) govern permissible fields, formats, and fidelity/minimization level by PurposeOfUse.    
\* \*\*Consent \\+ overlays are gating\*\*: missing/insufficient consent or overlay conflict/blocking produces denied export records instead of packets.    
\* \*\*Replayability\*\*: PacketVersion \\+ LedgerSchemaVersion are required for deterministic regeneration.    
\* \*\*Retention/expiration\*\*: export retention governed by Appendix H.34; expired exports are not deliverable and must carry an “expired” indicator.    
\* \*\*Appendix authority\*\*: Appendix F.40 is treated as the canonical specification for inputs/transformations/outputs; Module 40 points to it rather than duplicating.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Modules: 26, 27, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39    
\* Appendices: H.24, H.26, H.34, L, F.40

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

For every export attempt (approved or denied), log:

\* \`ConsentVersion\` and \`PurposeOfUse\` used for validation.    
\* \`ExportProfileID\` and applied \`JurisdictionOverlayID\[\]\`.    
\* \`transform\_stack\_lineage\[\]\` (de-ID, masking, generalization, perturbation, synthesis, linkage).    
\* \`requester\_identity\`, \`export\_format\`, \`export\_format\_version\`, and \`target\_consumer\`.    
\* \`PacketVersion\` and \`LedgerSchemaVersion\`.    
\* Outcome as \`ExportPacketID\` or \`DeniedExportRecordID\`, with \`denialReason\` when applicable.    
  All of the above must be encoded in AuditEvent \\+ Provenance and mirrored into the Disclosure Ledger so exports are reconstructible for patients and regulators.

\# \*\*V5.2 M41 — Reflex Suppression Audit Trail\*\* 

\#\#\# \*\*Purpose\*\*

Module 41 is the transparency backbone for reflex suppression across Modules 9–11 and 41, recording the full lifecycle of every suppression event so no \`pauseFlag\`/\`pauseReason\` is hidden or indefinite.    
It tags each suppression with provenance, resolves each as \`confirm / lift / escalate\`, QA-labels suppression quality, and feeds outcomes to Module 48 for threshold and TTL refinement.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Lifecycle capture and logging for suppression events: \`activation\`, \`renewal\`, \`resolution\`.    
\* Recording resolution outcome taxonomy \`{confirm, lift, escalate}\` and enforcing that no suppression remains unresolved (TTL expiry forces \`lift\`).    
\* QA labeling of suppression quality (true-positive vs false-positive) plus any finer-grained status recorded per Appendix F.41.    
\* AuditEvent/Provenance mapping and tamper-evident, append-only storage of suppression events.    
\* Governance feedback loop surfacing false-positive and “Missed Flare”-type cases to Module 48 and governance/QA stack.    
\* Oversight linkage for cross-checking suppression vs disclosure consistency as referenced by Module 41\\.

\*\*Out of scope\*\*

\* Changing scores, stability bands, thresholds, TTL values, priority ladders, or any upstream/downstream clinical decisions (Module 41 audits only).    
\* Redefining suppression reasons, priorities, TTL defaults, or resolution matrices (owned canonically by Appendix F.9).    
\* Defining AuditEvent/Provenance schemas (owned canonically by Appendix C.11).    
\* Redefining field locks for \`pauseFlag\`, \`pauseReason\`, TTL fields, or QA status fields (owned canonically by Appendix H.2 / H.11).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`pauseFlag\`    
\* \`pauseReason\`    
\* Suppression lifecycle event type: \`activation | renewal | resolution\`    
\* AuditEvent fields captured per suppression lifecycle event:    
  \* \`action\`    
  \* \`reason\`    
  \* \`evidence\`    
  \* \`source\_module\`    
  \* \`ttl\_remaining\` (renewals)    
  \* \`timestamp\`    
\* Resolution outcome: \`confirm | lift | escalate\`    
\* QA label:    
  \* \`true\_positive\_suppression\` or \`false\_positive\_suppression\`    
  \* Optional finer-grained status per Appendix F.41 (e.g., “Validated / Missed Flare / Unresolved”).    
\* Context fields when applicable:    
  \* Evidence phrase(s)    
  \* PSI/band context when applicable    
\* Linkage references:    
  \* Upstream Observations/Conditions/Detections references    
  \* Downstream governance actions references (e.g., CAPA IDs, governance reviews)

\#\#\# \*\*Outputs\*\*

\* Append-only suppression audit trail entries for each lifecycle event (\`activation\`, \`renewal\`, \`resolution\`) recorded as AuditEvent with linked Provenance.    
\* Recorded suppression resolution outcome (\`confirm | lift | escalate\`) per suppression event.    
\* Recorded QA label (true-positive vs false-positive suppression, plus optional finer-grained status label per Appendix F.41).    
\* Governance feedback artifacts routed to Module 48 for threshold/TTL recalibration and related governance actions.

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. On every suppression lifecycle event emitted by upstream suppression governance (\`activation\`, \`renewal\`, \`resolution\`), create a new audit entry for that event.    
2\. For \`activation\`, write an AuditEvent capturing \`action\`, \`reason\`, \`evidence\`, \`source\_module\`, and \`timestamp\`.    
3\. For \`renewal\`, write an AuditEvent capturing \`action\`, \`reason\`, \`evidence\`, \`source\_module\`, \`ttl\_remaining\`, and \`timestamp\`.    
4\. For \`resolution\`, require a resolution outcome in \`{confirm, lift, escalate}\` and write it to the audit trail for the suppression event.    
5\. Enforce “no suppression remains unresolved” by recording \`lift\` on TTL expiry as the resolution outcome.    
6\. After resolution, record a QA label for the resolved suppression as true-positive suppression or false-positive suppression, and record any finer-grained status label used in Appendix F.41 when provided.    
7\. Persist suppression events in tamper-evident, append-only AuditEvent/Provenance chains, referencing underlying Observations/Conditions and reason codes.    
8\. Surface false-positive suppressions and “Missed Flare”-type cases to Module 48 and the governance/QA stack for threshold/TTL recalibration and related governance actions (including CAPA and fairness review).    
9\. Maintain strict boundaries: do not modify scores, bands, or decisions; only record the context and outcomes of decisions made by Modules 5, 9, 10, and 11\\.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Module 41 does not change scores, stability bands, or decisions; it only audits and records context/outcomes of decisions made by Modules 5, 9, 10, and 11\\.    
\* Suppression reasons, priorities, TTL defaults, and the resolution taxonomy are canonically defined in Appendix F.9 and must be referenced rather than restated here.    
\* AuditEvent/Provenance schemas are canonically defined in Appendix C.11 and must be used as the authoritative schema.    
\* \`pauseFlag\`, \`pauseReason\`, TTL fields, and QA status fields are governed by Appendix H.2 / H.11 and are not re-defined in this module.    
\* All logged elements constitute a queryable “truth surface” intended for regulators, clinicians, and governance boards.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Module 5 (decision source audited by Module 41\\)    
\* Module 9 (suppression governance source; lifecycle events audited by Module 41\\)    
\* Module 10 (decision source audited by Module 41\\)    
\* Module 11 (decision source audited by Module 41\\)    
\* Module 48 (receives governance feedback loop outputs)    
\* Appendix F.9 (Reflex Suppression Policy: priority, TTL, resolution matrix)    
\* Appendix F.41 (QA labeling taxonomy and finer-grained status labels)    
\* Appendix C.11 (Audit & Lineage: AuditEvent / Provenance schema)    
\* Appendix H.2 / H.11 (field definitions for \`pauseFlag\`, \`pauseReason\`, TTL fields, QA status fields)

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* Unique suppression event ID, patient reference, and \`source\_module\`.    
\* Lifecycle state (\`activation\`, \`renewal\`, \`resolution\`) with timestamps and TTL state at each step.    
\* \`pauseReason\` (from Appendix F.9) and associated evidence phrase(s), plus PSI/band context when applicable.    
\* Resolution outcome (\`confirm / lift / escalate\`) plus QA label (true-positive vs false-positive, etc.).    
\* Provenance linkages to upstream Observations/Conditions/Detections and to downstream governance actions (e.g., CAPA IDs, governance reviews).    
\* Evidence of participation in a tamper-evident, append-only log (e.g., hash-chaining) as governed by audit appendices.

\# \*\*V5.2 M42 — Intervention Loop (Governed Intervention & Escalation Hub)\*\*

\#\#\# \*\*Purpose\*\*

Module 42 is the governed intervention and escalation hub for Ethos-of-Health.    
It receives triggers from upstream modules and routes them to the appropriate human or governance actor under strict consent and jurisdiction overlays.    
Its job is to type, prioritize, and time-box interventions; enforce ConsentVersion \\+ JurisdictionOverlayID constraints; and emit AuditEvent \\+ Provenance records so every intervention (including denials) is lawful, auditable, and replayable.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Intake of intervention triggers from Modules 19–22, 29–31, 41, 32–40, ethical overlays, and QA modules.    
\* Consent and overlay gating with denial logging for failed checks.    
\* Intervention typing (Treatment-Critical / Compliance / Quality Assurance), priority tier assignment (low/medium/high/critical), and response timeline assignment per type.    
\* Escalation ladder routing (Clinician → Governance Board → Regulator) with SLA-based auto-escalation and logged transitions.    
\* Mandatory AuditEvent \\+ Provenance emission (including version identifiers and hash-chaining linkage).    
\* Explicit closure state enforcement and closure outcome routing to Modules 19, 48, 30, and 31\\.

\*\*Out of scope\*\*

\* Outcome learning and CAPA execution (handled by Modules 43–48).    
\* Outcome scoring (Module 42 focuses on governed routing and closure).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`trigger\_source\_module\_id\`    
\* \`trigger\_event\_id\`    
\* \`trigger\_payload\_ref\` (pointer to originating record)    
\* \`reason\_enum\`    
\* \`ConsentVersion\`    
\* \`JurisdictionOverlayIDs\[\]\`    
\* \`requester\_identity\`    
\* \`requested\_actor\_class\` (clinician / governance board / regulator)    
\* \`communication\_channel\_refs\[\]\` (e.g., Communication/Task/DocumentReference IDs where applicable)    
\* \`PacketVersion\`    
\* \`LedgerSchemaVersion\`    
\* \`ledger\_prev\_hash\_ref\` (hash-chain linkage pointer)

\#\#\# \*\*Outputs\*\*

\* \`intervention\_id\`    
\* \`intervention\_type\` ∈ {Treatment-Critical, Compliance, QualityAssurance}    
\* \`priority\_level\` ∈ {low, medium, high, critical}    
\* \`response\_sla\` (response timeline)    
\* \`escalation\_rung\` (Clinician / GovernanceBoard / Regulator)    
\* \`escalation\_status\` (incl. auto-escalation transitions)    
\* \`outcome\_status\` ∈ {resolved, escalated, denied}    
\* \`AuditEvent\` record(s)    
\* \`Provenance\` record(s)    
\* \`closure\_routing\_events\[\]\` targeting Modules 19, 48, 30, 31

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Receive trigger\*\* and persist an \`intervention\_id\` bound to \`trigger\_source\_module\_id\` and \`trigger\_event\_id\`.    
2\. \*\*Consent \\+ overlay gating\*\*: validate the trigger against \`ConsentVersion\` and \`JurisdictionOverlayIDs\`.    
3\. If gating fails, \*\*set outcome\\\_status \\= denied\*\*, emit AuditEvent \\+ Provenance for the denial, and terminate the intervention as closed.    
4\. If gating passes, \*\*classify intervention\\\_type\*\* as Treatment-Critical, Compliance, or Quality Assurance.    
5\. \*\*Assign priority\\\_level\*\* (low/medium/high/critical) and \*\*assign response\\\_sla\*\* as the response timeline per type.    
6\. \*\*Route to escalation ladder rung 1 (Clinician)\*\* as the initial target actor.    
7\. \*\*Await acknowledgment/closure\*\* within \`response\_sla\`.    
8\. If no acknowledgment or closure within SLA, \*\*auto-escalate\*\* to the next rung in the canonical ladder (Governance Board, then Regulator), and log the transition in AuditEvent.    
9\. \*\*Emit AuditEvent \\+ Provenance\*\* for each routing action, escalation transition, and state change, including PacketVersion and LedgerSchemaVersion and hash-chain linkage.    
10\. \*\*Enforce explicit closure state\*\* for every intervention, resulting in outcome\\\_status \\= resolved, escalated, or denied.    
11\. On closure, \*\*route closure outcomes\*\* to:    
    \* Module 19 (QA)    
    \* Module 48 (continuous learning governance)    
    \* Module 30 (disclosure to patients)    
    \* Module 31 (regulator-facing compliance packets)

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Reject any trigger that fails consent or overlay checks, and log a denial event.    
\* Bind each intervention to ConsentVersion (Module 26\\) and JurisdictionOverlayIDs (Appendix H.26).    
\* Use the canonical escalation ladder Clinician → Governance Board → Regulator, with SLA-based auto-escalation and logged transitions.    
\* Emit AuditEvent \\+ Provenance for every intervention (including denials), and use hash-chaining to guarantee immutability and replayability.    
\* Enforce that every intervention ends in an explicit closure state.    
\* Outcome learning and CAPA are handled downstream by Modules 43–48, not by Module 42\\.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Module 19    
\* Module 22    
\* Module 26 (ConsentVersion source)    
\* Module 30    
\* Module 31    
\* Module 41    
\* Modules 32–40    
\* Modules 43–48    
\* Appendix H.26 (JurisdictionOverlayIDs)

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* Unique intervention ID.    
\* Trigger source module \\+ event ID.    
\* Intervention type (Treatment-Critical / Compliance / QA).    
\* Priority level and response SLA.    
\* Escalation status and final outcome (resolved / escalated / denied).    
\* ConsentVersion and applied JurisdictionOverlayIDs.    
\* Requester and responder identities and the communication channel(s) engaged, referenced via Communication/Task/DocumentReference IDs where applicable.    
\* PacketVersion \\+ LedgerSchemaVersion and hash-chain linkage to previous ledger entries.    
\* Pointers for downstream QA, CAPA, and continuous learning loops (Modules 43–48).

\# \*\*V5.2 M43 — Automated Documentation Engine (ADE)\*\*

\#\#\# \*\*Purpose\*\*

Module 43 is the governed Corrective and Preventive Actions (CAPA) hub that converts incidents, interventions, suppression anomalies, compliance findings, and QA/CL feedback into CAPAs using a single canonical lifecycle.    
Module 43 enforces ConsentVersion binding, jurisdiction overlays as overlay IDs, and verification-of-effectiveness (VoE) gating before CAPA closure, with audit-grade FHIR-backed lineage for every CAPA step and denial.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* CAPA creation from allowed trigger sources only (M42, M41, M29–31, M19, M48) with associated consent/overlay states.    
\* Consent and overlay precondition checks for CAPA creation and denial record creation.    
\* CAPA typing (Corrective/Preventive) and lifecycle state machine (Opened → Assigned → Implemented → Verified (VoE) → Closed/Reopened).    
\* SLA policy application and auto-escalation on SLA breach (including responsible-actor change) with required surfacing via disclosure/compliance.    
\* VoE gating with required KPIs and linkage to QA/compliance surfaces.    
\* Lineage capture and FHIR resource production for CAPA artifacts and VoE artifacts.    
\* Mandatory transparency: CAPAs (including denials and SLA escalations) visible to patients and regulators via standard reports.

\*\*Out of scope\*\*

\* Any CAPA creation from trigger sources not listed as allowed.    
\* Any CAPA closure without VoE metrics.    
\* Any bypass of Module 43 for corrective or preventive actions.    
\* Hard-coded law text (overlays are IDs only).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`TriggerEvent\`    
  \* \`sourceModuleId\` (allowed: 42, 41, 29–31, 19, 48\\)    
  \* \`sourceEventId\`    
  \* \`timestamp\`    
\* \`ConsentContext\`    
  \* \`ConsentVersion\`    
  \* \`PurposeOfUse\`    
  \* \`consent.permits\` (boolean)    
\* \`OverlayContext\`    
  \* \`JurisdictionOverlayID\[\]\`    
  \* \`overlays.ok\` (boolean)    
\* \`VersionContext\`    
  \* \`PacketVersion\`    
  \* \`LedgerSchemaVersion\`    
  \* \`CAPATemplateId\`    
  \* \`SLACatalogVersion\`    
  \* \`VoEKPIDefinitionVersion\`    
\* \`DisclosureLedgerPointers\[\]\`    
\* \`CAPAParameters\`    
  \* \`ActionType\` ∈ {\`Corrective\`, \`Preventive\`}    
  \* \`severity\`    
\* \`ActorContext\`    
  \* \`owner\`    
  \* \`responsibleActor\` (current)

\#\#\# \*\*Outputs\*\*

\* \`CAPARecord\`    
  \* \`capaId\`    
  \* \`ActionType\` (Corrective/Preventive)    
  \* \`status\` (Opened/Assigned/Implemented/Verified/Closed/Reopened)    
  \* \`severity\`, \`owner\`, \`SLA\` (\`assignedAt\`, \`dueIn\`)    
  \* \`ConsentVersion\`, \`PurposeOfUse\`, \`JurisdictionOverlayID\[\]\`    
  \* \`PacketVersion\`, \`LedgerSchemaVersion\`, \`CAPATemplateId\`, \`SLACatalogVersion\`, \`VoEKPIDefinitionVersion\`    
  \* \`triggerRefs\[\]\` (module/event/timestamp)    
\* \`DeniedCAPARecord\`    
  \* \`denialReason\`    
  \* \`ConsentVersion\` and consent state snapshot    
  \* \`JurisdictionOverlayID\[\]\` and overlay state snapshot    
  \* patient-facing narrative pointer    
\* \`VoEReport\`    
  \* \`capaId\`    
  \* KPI Observations: \`recurrence\`, \`fairnessDelta\`, \`disclosureErrorRate\`, \`overlayAdherence\`    
  \* linkage to QA and compliance surfaces    
\* FHIR artifacts (for CAPA \\+ VoE lineage)    
  \* \`AuditEvent\`, \`Provenance\`, \`Task\`, \`PlanDefinition/ActivityDefinition\`, \`Observation\`, \`DocumentReference\`

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Validate trigger source\*\*    
   \* Accept CAPA creation requests only when \`TriggerEvent.sourceModuleId\` is one of: 42, 41, 29–31, 19, 48\\.    
   \* If not allowed, do not create a CAPA; produce a denial artifact consistent with denial logging (Denied CAPA Record).    
2\. \*\*Evaluate CAPA creation guard\*\*    
   \* Compute \`CAPA.creation\_guard \= consent.permits && overlays.ok\`.    
   \* If \`CAPA.creation\_guard\` is false:    
     \* Create \`DeniedCAPARecord\` including \`denialReason\`, consent state, overlays, and patient-facing narrative pointer.    
     \* Emit required audit-grade lineage objects for the denial (AuditEvent/Provenance and associated DocumentReference as applicable).    
     \* Stop.    
3\. \*\*Create CAPA record\*\*    
   \* Create \`CAPARecord\` with:    
     \* \`ActionType ∈ {Corrective, Preventive}\`.    
     \* Initial \`status \= Opened\`.    
     \* Trigger references (source module, event ID, timestamp).    
     \* \`ConsentVersion\`, \`PurposeOfUse\`, \`JurisdictionOverlayID\[\]\`.    
     \* Version bindings: \`PacketVersion\`, \`LedgerSchemaVersion\`, and template/catalog/KPI definition versions.    
4\. \*\*Apply SLA policy\*\*    
   \* Resolve SLA policies keyed by CAPA type and severity and write SLA fields onto the CAPA (including assignment timing and due interval).    
5\. \*\*Lifecycle transitions (state machine)\*\*    
   \* Allow only these transitions, each producing an auditable transition record:    
     \* \`Opened → Assigned → Implemented → Verified (VoE) → Closed\` or \`Reopened\`.    
   \* For each transition:    
     \* Write AuditEvent \\+ Provenance with actor, timestamp, reason, and new status.    
6\. \*\*SLA breach handling\*\*    
   \* On SLA breach:    
     \* Auto-escalate to higher governance tiers.    
     \* Change responsible actor.    
     \* Log the breach and escalation.    
     \* Ensure the breach/escalation is surfaced via disclosure/compliance reporting surfaces.    
7\. \*\*VoE gating\*\*    
   \* Before permitting \`Verified (VoE) → Closed\`, require VoE KPIs:    
     \* \`recurrence\`, \`fairnessDelta\`, \`disclosureErrorRate\`, \`overlayAdherence\`.    
   \* Store VoE KPIs as Observations and link them to the CAPA record and to QA and compliance surfaces.    
   \* If VoE KPIs are not present, block closure.    
8\. \*\*Transparency publication\*\*    
   \* Ensure CAPAs (including denials and SLA escalations) are visible to patients via disclosure reports and to regulators via compliance packets.    
9\. \*\*FHIR artifact emission\*\*    
   \* Emit and link the required FHIR resources for CAPA steps and VoE artifacts:    
     \* AuditEvent, Provenance, Task, PlanDefinition/ActivityDefinition, Observation, DocumentReference.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* CAPAs may be created only from interventions (M42), suppression anomalies (M41), compliance findings (M29–31), QA anomalies (M19), and CL outputs (M48), plus associated consent and overlay states (M26, H.23, H.26).    
\* \`CAPA.creation\_guard \= consent.permits && overlays.ok\`; failures must produce Denied CAPA Records with denialReason, consent state, overlays, and patient-facing narrative.    
\* Canonical lifecycle is fixed: Opened → Assigned → Implemented → Verified (VoE) → Closed / Reopened.    
\* SLA breaches must auto-escalate to higher governance tiers, must change responsible actor, and must be logged and surfaced via disclosure/compliance.    
\* CAPAs cannot close without VoE metrics (recurrence, fairness delta, disclosure error rate, overlay adherence) logged and linked to QA and compliance surfaces.    
\* No corrective or preventive action may bypass Module 43\\.    
\* All CAPAs (including denials and SLA escalations) must be visible to patients and regulators via standard reports.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Modules: M42, M41, M29–31, M19, M48, M26, M30, M31.    
\* Appendices: H.23, H.24–H.27, H.33, H.34, H.88, Appendix L, and F.43.

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* \*\*Trigger\*\*: originating module (42, 41, 29–31, 19, 48), event ID, timestamp.    
\* \*\*Consent & overlays\*\*: ConsentVersion, PurposeOfUse, JurisdictionOverlayID\\\[\\\].    
\* \*\*CAPA core fields\*\*: CAPA ID, type (Corrective/Preventive), severity, owner, SLA (assignedAt, dueIn), status.    
\* \*\*Lifecycle transitions\*\*: AuditEvent \\+ Provenance for each transition (actor, timestamp, reason, new status).    
\* \*\*Evidence & VoE\*\*: implementation evidenceRefs; VoE KPIs (recurrence, fairness delta, disclosure error rate, overlay adherence) stored as Observations and linked back to CAPA.    
\* \*\*Denials & SLA breaches\*\*: denialReason, escalation level, new responsible actor, overlay/consent state; route into disclosure ledger/compliance hub surfaces.    
\* \*\*Versioning\*\*: PacketVersion, LedgerSchemaVersion, CAPA template ID, SLA catalog version, VoE KPI definition version.

\# \*\*V5.2 M44 — ADE & Safety Reporting (Regulatory Writer & EHR Submitter)\*\*

\#\#\# \*\*Purpose\*\*

Module 44 is the governed ledger of corrective insights and lessons learned, capturing systemic improvements emerging from interventions, CAPAs, suppression anomalies, compliance findings, and QA/CL loops.    
It enforces a structured schema, consent \\+ jurisdiction overlays, audit-grade provenance, VoE gating, and replayable versioning so each insight is traceable, reviewable, and reproducible, and routes finalized insights into QA dashboards, disclosure reports, compliance exports, and continuous learning cycles.

\#\#\# \*\*Scope\*\*

\*\*In scope\*\*

\* Corrective insight triggering intake from: Interventions (M42), CAPA outcomes (M43), suppression anomalies (M41), compliance findings (M29–31), QA/CL feedback (M19, M48).    
\* Corrective insight capture with required fields and bindings (trigger/CAPA/context/lesson/actions/impact; consent/overlays/audit/versioning/linkage IDs).    
\* Consent \\+ jurisdiction overlay validation and denied-record handling.    
\* Lifecycle state management (DRAFT → REVIEWED → FINALIZED or EXPIRED) with VoE gating before FINALIZED.    
\* Cross-registry routing of finalized insights to QA, disclosure, compliance, and continuous learning loops.    
\* AuditEvent \\+ Provenance emission for create/update/denial, including hash-chain pointer and lineage.

\*\*Out of scope\*\*

\* Storing “world knowledge” (knowledge/disease-logic); Module 44 remains a pure EoH governance module under the overlap audit.    
\* Redefining field lists or FHIR mappings already canonicalized in appendices F.44/H.91 and review policy in H.92.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`TriggerRef\`:    
  \* \`sourceModuleId\` (one of: M42, M43, M41, M29–M31, M19, M48)    
  \* \`eventId\`    
\* \`CAPARef\` (optional):    
  \* \`capaId\`    
\* \`InsightContext\`:    
  \* \`contextAndConditions\`    
  \* \`safeguardOrLesson\`    
  \* \`actionsAppliedOrRecommended\`    
  \* \`measuredImpactOrOutcome\`    
\* \`ConsentBinding\`:    
  \* \`ConsentVersion\` (active; from M26)    
\* \`OverlayBinding\`:    
  \* \`JurisdictionOverlayIDs\[\]\` (from H.26)    
\* \`VoEBinding\`:    
  \* \`voeLinkageId\` (required for FINALIZED)    
  \* \`kpis\` (required for FINALIZED)    
\* \`Lifecycle\`:    
  \* \`status\` (DRAFT | REVIEWED | FINALIZED | EXPIRED)    
  \* \`authorId\`    
  \* \`reviewerId\`    
  \* \`timestamps\` (create/update/review/finalize/expire)    
\* \`Versioning\`:    
  \* \`PacketVersion\`    
  \* \`LedgerSchemaVersion\`    
\* \`DownstreamLinkageIds\`:    
  \* \`qaLinkageId\`    
  \* \`disclosureLinkageId\`    
  \* \`complianceLinkageId\`    
  \* \`clLinkageId\`

\#\#\# \*\*Outputs\*\*

\* \`CorrectiveInsightRecord\`:    
  \* \`insightId\`    
  \* all input bindings/fields persisted as the governed ledger entry    
\* \`DeniedInsightRecord\` (when consent/overlay validation fails):    
  \* \`insightId\` (or denial record id)    
  \* \`denialReason\`    
  \* \`ConsentVersion\`, \`JurisdictionOverlayIDs\[\]\`    
  \* linkage for Disclosure Ledger logging    
\* \`AuditArtifacts\`:    
  \* \`AuditEvent\`    
  \* \`Provenance\`    
  \* \`hashChainPointer\`    
\* \`FanOutEvents\` (for FINALIZED insights):    
  \* QA dashboard/metrics event (M19)    
  \* patient disclosure event (M30)    
  \* compliance export event (M31)    
  \* continuous learning/governance loop event (M48)

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Validate trigger source\*\*    
   \* Accept the request only if \`TriggerRef.sourceModuleId\` is one of: M42, M43, M41, M29–M31, M19, M48.    
2\. \*\*Enforce mandatory registry usage\*\*    
   \* Require that corrective insights are recorded in Module 44; prohibit creation of “shadow logs” outside the registry.    
3\. \*\*Validate required insight content\*\*    
   \* Require \`TriggerRef\` and the following \`InsightContext\` fields: \`contextAndConditions\`, \`safeguardOrLesson\`, \`actionsAppliedOrRecommended\`, \`measuredImpactOrOutcome\`.    
   \* If a CAPA is relevant, bind \`CAPARef\` to the insight record.    
4\. \*\*Consent \\+ overlay gate\*\*    
   \* Validate the entry against \`ConsentVersion\` (M26) and \`JurisdictionOverlayIDs\[\]\` (H.26).    
   \* If validation fails, create a \`DeniedInsightRecord\`, log the reason, and ensure overlay conflicts appear as “Denied Insight Records” logged in the Disclosure Ledger.    
5\. \*\*Create or update the insight record (with replayability rule)\*\*    
   \* Compute the record identity/dedupe such that identical \`{TriggerRef \+ CAPARef \+ overlays \+ versions}\` yields an identical insight record.    
   \* Persist \`PacketVersion\` and \`LedgerSchemaVersion\` on the record.    
6\. \*\*Lifecycle enforcement\*\*    
   \* Enforce status progression: \`DRAFT → REVIEWED → FINALIZED\` or \`EXPIRED\`.    
   \* Apply review assignments and checks per H.92 (by reference).    
7\. \*\*VoE gating\*\*    
   \* Block transition to \`FINALIZED\` unless \`VoEBinding.voeLinkageId\` and VoE KPIs are present and linked.    
8\. \*\*Audit \\+ provenance emission (create/update/deny)\*\*    
   \* For every create, update, or denial, emit \`AuditEvent \+ Provenance\` capturing author, reviewer, timestamps, trigger/CAPA linkage, overlays, VoE metrics (when present), and a hash-chain pointer.    
9\. \*\*Cross-registry routing on FINALIZED\*\*    
   \* On \`FINALIZED\`, fan out the insight to: QA metrics/dashboards (M19), patient disclosures (M30), regulator-facing compliance exports (M31), and continuous learning/governance loops (M48).    
10\. \*\*Fairness \\+ transparency requirement\*\*    
\* For preventive insights, require a demographic fairness review and maintain traceability so patients and regulators can trace material insights and their effects.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* V5 logic is authoritative and cannot be altered; Module 44 is a cleanliness/partitioning pass and remains a pure EoH governance module.    
\* The Overlap Audit boundary applies: “world knowledge → MKE; patient/system state & governance → EoH.”    
\* Module 44 is mandatory for corrective insights; shadow logs outside the registry are prohibited.    
\* Module 44 references (does not restate) canonical schema/lineage in F.44 and H.91, and review/lifecycle policy in H.92.    
\* No insight may reach \`FINALIZED\` without linked VoE outcomes and populated KPIs.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Modules: M42, M43, M41, M29–M31, M19, M48, M26, M30.    
\* Appendices: F.44, H.91, H.92, H.26, H.90 (via M43).

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

For each \`CorrectiveInsightRecord\` (and each denial), log at minimum:

\* Identifiers: \`insightId\`, \`TriggerRef{module,eventId}\`, \`CAPARef\` (if any), \`PacketVersion\`, \`LedgerSchemaVersion\`.    
\* Context: description of context and contributing conditions.    
\* Lesson/safeguard: the corrective insight and any safeguard or pattern change.    
\* Actions \\+ measured impact/outcome.    
\* Consent \\+ overlays: \`ConsentVersion\`, \`JurisdictionOverlayIDs\[\]\`, and overlay conflicts including Denied Insight Records (and their reasons).    
\* VoE bindings: \`voeLinkageId\`, KPI set.    
\* Audit metadata: \`authorId\`, \`reviewerId\`, timestamps, lifecycle events (DRAFT/REVIEWED/FINALIZED/EXPIRED), hash-chain links, and downstream linkage IDs (QA/Disclosure/Compliance/CL).

\# \*\*V5.2 M45 — Preventive Action Registry (PAR)\*\*

\#\#\# \*\*Purpose\*\*

The Preventive Action Registry captures forward-looking, systemic preventive safeguards arising from governance, QA, compliance, and continuous-learning loops, distinct from corrective CAPAs.    
It binds each preventive action to ConsentVersion, jurisdiction overlays, VoE KPIs, and explicit ownership/SLA, producing audit-grade, hash-chained records consumable across the EoH system.

\---

\#\#\# \*\*Scope\*\*

\*\*In scope\*\*

\* Creation, validation, lifecycle management, and immutability of preventive action records.    
\* Consent and jurisdiction overlay gating of preventive actions.    
\* VoE-gated closure and system-wide propagation of preventive records.

\*\*Out of scope\*\*

\* Corrective CAPA execution.    
\* Definition of schema fields, lifecycle states, or retention rules owned by appendices.    
\* Independent fairness or audit logic outside referenced governance modules.

\---

\#\#\# \*\*Inputs\*\*

\* Preventive action triggers from CAPA/Corrective Insights (M43/M44).    
\* QA anomaly streams from M19.    
\* Compliance Hub outputs from M29–M31.    
\* Continuous Learning governance signals from M48.    
\* External advisories.    
\* ConsentVersion identifiers.    
\* JurisdictionOverlayID(s).    
\* VoE KPI definitions and thresholds.    
\* PacketVersion and LedgerSchemaVersion identifiers.

\---

\#\#\# \*\*Outputs\*\*

\* Canonical preventive action records stored in the Preventive Action Registry.    
\* Denied preventive action records with full audit logging.    
\* Hash-chained AuditEvent and Provenance records.    
\* Preventive action feeds consumable by QA dashboards (M19), Disclosure reports (M30), Compliance exports (M31), and Continuous Learning governance (M48).

\---

\#\#\# \*\*Process / Logic\*\*

1\. Create a preventive action record upon receipt of a valid trigger from approved upstream sources.    
2\. Populate the canonical preventive action schema and bind AuditEvent and Provenance metadata, including PacketVersion and LedgerSchemaVersion.    
3\. Validate the preventive action against the active ConsentVersion and applicable JurisdictionOverlayID(s).    
4\. If consent or jurisdiction conflicts are detected, register a Denied Preventive Action with full audit logging.    
5\. Track the preventive action through its lifecycle with explicit ownership and SLA.    
6\. Enforce VoE-gated closure; prevent closure until VoE KPIs meet predefined thresholds.    
7\. Reopen or revise preventive actions that fail VoE review.    
8\. Hash-chain all actions, denials, and lifecycle transitions to ensure immutability and reproducibility.    
9\. Propagate finalized preventive records to QA, Disclosure, Compliance, and Continuous Learning modules.

\---

\#\#\# \*\*Governance / Constraints\*\*

\* All preventive actions must be recorded in the Preventive Action Registry with no shadow logging.    
\* ConsentVersion and jurisdiction overlays are mandatory gating requirements.    
\* Preventive actions cannot be closed without meeting VoE thresholds.    
\* Fairness validation is required and must be logged.    
\* Identical inputs, overlays, and versions must produce identical records.

\---

\#\#\# \*\*Dependencies\*\*

\* M19 — QA & Anomaly Monitoring.    
\* M26 — Consent & Ethical Safeguards.    
\* M30 — Disclosure Reporting & Narrative Hub.    
\* M31 — Compliance Export Hub.    
\* M43 — Automated Documentation Engine (ADE).    
\* M44 — ADE & Safety Reporting.    
\* M48 — Continuous Learning & Governance.    
\* Appendix H.95, H.34, H.98, H.81; Appendix C.11; Appendix L.3.

\---

\#\#\# \*\*Audit Hooks\*\*

\* Preventive action creation timestamp, trigger source, author, and owner.    
\* ConsentVersion and JurisdictionOverlayID(s) applied.    
\* VoE KPI results and closure decisions.    
\* Denial reasons for blocked preventive actions.    
\* PacketVersion, LedgerSchemaVersion, and hash values for all records and transitions.

\# \*\*V5.2 M46 — Mitigation Register\*\* 

\---

\#\#\# \*\*Purpose\*\*

The Mitigation Register governs the creation, validation, lifecycle management, and retirement of temporary or adaptive safeguards applied while permanent corrective or preventive actions are pending. It ensures all mitigations are centrally recorded, consent-validated, jurisdiction-aware, time-bound, and auditable. The module prevents mitigations from functioning as de facto permanent solutions by enforcing review, expiry, and conversion rules.

\---

\#\#\# \*\*Scope\*\*

\*\*In Scope\*\*

\* Temporary or adaptive mitigations instantiated during CAPA or Preventive Action execution.    
\* Mitigations triggered by QA anomalies, compliance findings, or Continuous Learning alerts.    
\* Consent validation, jurisdiction overlay checks, lifecycle state enforcement, and audit logging for mitigations.    
\* Conversion of effective mitigations into CAPA or Preventive Actions.

\*\*Out of Scope\*\*

\* Definition or execution of permanent corrective actions.    
\* Long-term preventive action storage.    
\* Introduction of new mitigation scoring, prioritization logic, or decision thresholds.

\---

\#\#\# \*\*Inputs\*\*

\* Mitigation trigger reference (module ID, event ID).    
\* Mitigation rationale and scope.    
\* Assigned owner identifier.    
\* Service-level agreement (SLA).    
\* Expiration date or review checkpoint.    
\* Provisional VoE metrics.    
\* Consent version identifier.    
\* Jurisdiction and overlay identifiers.    
\* Version identifiers.    
\* Audit and provenance references.

\---

\#\#\# \*\*Outputs\*\*

\* Mitigation Register record with lifecycle state.    
\* Denied Mitigation Record when consent or overlay validation fails.    
\* AuditEvent and Provenance records for all lifecycle transitions.    
\* References for disclosure, compliance, and QA surfaces.    
\* Conversion references to CAPA or Preventive Action modules when applicable.

\---

\#\#\# \*\*Process / Logic\*\*

1\. Receive an explicit mitigation trigger from an authorized source.    
2\. Instantiate a Draft mitigation record using the canonical mitigation schema.    
3\. Validate consent scope and jurisdiction overlays against the mitigation purpose and scope.    
4\. If validation fails, create a Denied Mitigation Record and route it to disclosure and compliance outputs.    
5\. If validation passes, submit the mitigation for QA and governance review.    
6\. Upon approval, transition the mitigation to Active state with enforced SLA and expiry or review checkpoint.    
7\. Bind provisional VoE metrics to the active mitigation.    
8\. At the review checkpoint, evaluate effectiveness and compliance.    
9\. Transition the mitigation to Reviewed, then Closed or Expired, or convert it into a CAPA or Preventive Action as required.    
10\. Retain expired or closed records according to retention policy with appropriate data absence indicators.    
11\. Log all state transitions and actions with hash-chained audit and provenance records.

\---

\#\#\# \*\*Governance / Constraints\*\*

\* The Mitigation Register is the sole canonical registry for temporary safeguards.    
\* No mitigation may be activated without defined expiry or review criteria.    
\* Mitigations may not bypass consent or jurisdiction overlay requirements.    
\* Mitigations may not persist indefinitely or replace CAPA or Preventive Actions.    
\* No new scoring, prioritization, or decision logic may be introduced within this module.

\---

\#\#\# \*\*Dependencies\*\*

\* Module 19 — QA Dashboards.    
\* Module 30 — Disclosure Reporting & Narrative Hub.    
\* Module 31 — Compliance Export Hub.    
\* Module 43 — Automated Documentation Engine (CAPA).    
\* Module 45 — Preventive Action Registry.    
\* Module 47 — Cross-Registry QA Synthesis.    
\* Module 48 — Continuous Learning Governance Loop.    
\* Appendix F.46 — Mitigation Register Lineage.    
\* Appendix H.99 — Mitigation Schema.    
\* Appendix H.100 — Mitigation Review & Validation Policy.    
\* Appendix H.102 — Mitigation Lifecycle & Retention Policy.

\---

\#\#\# \*\*Audit Hooks\*\*

\* Mitigation trigger source and identifier.    
\* Consent version, overlay identifiers, and validation outcomes.    
\* Assigned owner, SLA, and lifecycle state transitions with timestamps.    
\* Provisional VoE metric references.    
\* FHIR AuditEvent and Provenance identifiers with hash chain segments.    
\* Disclosure and compliance export references associated with the mitigation.

\# \*\*V5.2 M47 — Cross-Module QA Synthesizer (CQAS)\*\*

\#\#\# \*\*Purpose\*\*

Module 47 is the cross-registry QA lens that aggregates signals from CAPA (M43), Corrective Insights (M44), Preventive Actions (M45), Mitigations (M46), QA metrics (M19), and compliance hubs (M29–M31), and transforms them into structured QA synthesis records.    
It governs how QA evidence is combined, governed, and surfaced in a consent- and overlay-aware, fully auditable, fairness-sensitive, replayable way.    
It does not define medical knowledge.

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Aggregation of inputs from M43, M44, M45, M46, M19, and M29–M31 into QA synthesis records.    
\* ConsentVersion \\+ PurposeOfUse validation (M26) and JurisdictionOverlayIDs application (H.26) for QA aggregation, including denial \\+ explicit denial-record creation when outside lawful scope.    
\* Aggregation of VoE KPIs and monitoring of recurrence rate, fairness delta, and compliance error rates, with systemic failure flagging when thresholds are exceeded across registries/demographics.    
\* AuditEvent \\+ Provenance (+ Task where required) representation of QA synthesis with lineage to sources, overlays applied, reviewers, outcomes, and version IDs.    
\* Replayability and versioning invariants for synthesis schema, thresholds, and aggregation logic.    
\* Downstream routing of QA synthesis outputs to M19, M30, M31, and M48.

\*\*Out of scope\*\*

\* Defining medical knowledge or clinical facts.    
\* Defining detailed rules that are explicitly delegated as authoritative to Appendix F.47, Appendix H.26, Appendix H.34, and Appendix L.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`capa\_records\[\]\` (from M43): \`record\_id\`, \`status\`, \`voe\_kpis\`, \`timestamps\`, \`version\_ids\` (by reference)    
\* \`corrective\_insight\_records\[\]\` (from M44): \`record\_id\`, \`status\`, \`metrics\`, \`timestamps\`, \`version\_ids\` (by reference)    
\* \`preventive\_action\_records\[\]\` (from M45): \`record\_id\`, \`status\`, \`voe\_kpis\`, \`timestamps\`, \`version\_ids\` (by reference)    
\* \`mitigation\_records\[\]\` (from M46): \`record\_id\`, \`status\`, \`voe\_kpis\`, \`timestamps\`, \`version\_ids\` (by reference)    
\* \`qa\_metrics\[\]\` (from M19): \`metric\_id\`, \`metric\_name\`, \`metric\_value\`, \`time\_window\`, \`demographic\_slices\[\]\`    
\* \`compliance\_findings\[\]\` (from M29–M31): \`finding\_id\`, \`type\`, \`severity\`, \`timestamps\`, \`version\_ids\` (by reference)    
\* \`consent\_context\`: \`ConsentVersion\`, \`PurposeOfUse\` (from M26)    
\* \`overlay\_context\`: \`JurisdictionOverlayIDs\[\]\` (from H.26)    
\* \`request\_context\`: \`requester\_id\`, \`requester\_role\`, \`requested\_at\`    
\* \`version\_context\`: \`PacketVersion\`, \`LedgerSchemaVersion\`, \`synthesis\_schema\_version\`, \`thresholds\_version\`

\#\#\# \*\*Outputs\*\*

\* \`qa\_synthesis\_record\` with mandatory fields: \`contributing\_modules\[\]\`, \`reference\_ids\[\]\`, \`aggregated\_qa\_metrics{recurrence,fairness,compliance\_error\_rate}\`, \`governance\_outcome(pass|fail|flagged)\`, \`reviewer\_id\`, \`reviewer\_role\`, \`timestamps\`, \`version\_identifiers\`.    
\* \`denied\_qa\_record\` when aggregation is outside lawful scope, including denial linkage to consent/overlays.    
\* Audit artifacts representing synthesis and outcomes: \`AuditEvent\`, \`Provenance\`, and \`Task\` (when review workflow required).    
\* Routed downstream notifications/feeds to: M19 dashboards, M30 disclosure reports, M31 compliance packets, M48 governance/retraining inputs.

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest sources\*\*: Collect input records from M43, M44, M45, M46, M19, and M29–M31 and extract their \`record\_id\`/\`finding\_id\` and relevant metric/KPI fields for synthesis.    
2\. \*\*Validate scope\*\*: Validate \`ConsentVersion\` \\+ \`PurposeOfUse\` (M26) and apply \`JurisdictionOverlayIDs\[\]\` (H.26) to the requested QA aggregation scope.    
3\. \*\*Deny if out of scope\*\*: If validation fails or scope is outside lawful overlay constraints, create a \`denied\_qa\_record\` and stop synthesis for that request.    
4\. \*\*Aggregate VoE \\+ QA metrics\*\*: Consolidate VoE KPIs from CAPA/Preventive/Mitigation registries and consolidate QA metrics needed for recurrence rate, fairness delta, and compliance error rates.    
5\. \*\*Detect KPI drift/systemic failures\*\*: Evaluate recurrence/fairness/compliance error rates across registries and demographics and set governance status to \`flagged\` when systemic failures are indicated by thresholds being exceeded.    
6\. \*\*Assemble synthesis record\*\*: Create a \`qa\_synthesis\_record\` and populate mandatory fields: contributing modules, reference IDs, aggregated QA metrics, governance outcome (\`pass|fail|flagged\`), reviewer/role, timestamps, and version identifiers.    
7\. \*\*Encode lineage & audit\*\*: Represent the synthesis as \`AuditEvent\` \\+ \`Provenance\` (and \`Task\` when review workflow is required), linking to source modules/records, overlays applied, reviewers, outcomes, and version IDs.    
8\. \*\*Enforce replayability controls\*\*: Record version control identifiers for synthesis schema, thresholds, and aggregation logic so historical syntheses are replayable.    
9\. \*\*Route outputs\*\*: Route the synthesis to QA dashboards (M19), patient disclosure reports (M30), regulator compliance packets (M31), and continuous learning/governance retraining inputs (M48).    
10\. \*\*Apply retention linkage\*\*: Mark synthesis records for retention/expiry handling under the referenced retention authority (H.34) and vault rules, without redefining those rules in this module.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* CQAS is mandatory (no bypass by M43–M46) and must provide transparency to patients and regulators.    
\* CQAS must be consent- and overlay-aware for QA aggregation and must create explicit denial records when outside lawful scope.    
\* CQAS must perform fairness and recurrence checks across demographics as part of QA synthesis governance.    
\* CQAS must preserve replayability of historical syntheses via versioning of synthesis schema, thresholds, and aggregation logic.    
\* Detailed lineage, overlay, retention, and version-control rules are authoritative in Appendix F.47, Appendix H.26, Appendix H.34, and Appendix L and must not be redefined here.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Modules: M19, M26, M29–M31, M43–M46, M48.    
\* Appendices: F.47 (lineage/transformations), H.26 (overlays), H.34 (retention/expiry), Appendix L (versioning).

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

For each QA synthesis operation, log:

\* Source modules and specific record IDs from M43, M44, M45, M46, M19, M29–M31.    
\* Active \`ConsentVersion\`, \`PurposeOfUse\`, \`JurisdictionOverlayIDs\[\]\`, and any overlay-driven denials (\`Denied QA Records\`).    
\* Aggregated QA metrics (recurrence, fairness, compliance error rate), governance classification (pass/fail/flagged), and VoE KPIs used.    
\* Reviewer identity, role, and any governance board/QA team involved.    
\* Versioning fields: \`PacketVersion\`, \`LedgerSchemaVersion\`, synthesis schema version, thresholds, and any referenced calibration IDs/model versions used upstream (referenced, not redefined).    
\* Retention status and expiry handling markers per H.34.    
  All of the above must be encoded via FHIR \`AuditEvent\` \\+ \`Provenance\` (+ \`Task\` where applicable).

\# \*\*V5.2 M48 — Continuous Learning & Governance Loop (CLGL)\*\* 

\#\#\# \*\*Purpose\*\*

Module 48 (CLGL) is the governed loop that turns QA and CAPA signals into lawful, auditable retraining and policy updates, binding each cycle to consent (M26), jurisdictional overlays (H.26), audit-grade provenance, and governance sign-off.    
It consumes triggers from CAPA/QA/compliance modules and emits retraining records, dashboard updates, and disclosure/compliance packets, closing the loop between systemic quality findings and model evolution.    
Module 48 does not encode medical facts; it encodes how the system is allowed to learn and change over time.

\#\#\# \*\*Scope\*\*

\*\*In scope\*\*

\* Trigger intake for learning cycles from CAPA/QA/compliance modules (M19, M29–M31, M43–M47) plus external advisories (as trigger pointers).    
\* Structured retraining capture with required fields; deny/approve gating; governance review; replayability and audit lineage.    
\* Emission of retraining records and downstream loop-closure outputs to QA dashboards (M19), patient disclosures (M30), and regulator-facing exports (M31).

\*\*Out of scope\*\*

\* Any embedded medical knowledge: disease facts, guideline summaries, drug class/contraindication lists, ontology mirrors/code tables, lab interpretation tables, phenotype dictionaries.    
\* Metric implementations and formulae (metrics may be required/passed through, but definitions are not owned here).    
\* FHIR profile details and code dictionaries (only resource-type requirements and lineage obligations are in scope).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`trigger\_refs\[\]\` (references to source records from M19, M29–M31, M43–M47; may include external advisory trigger pointer)    
\* \`qa\_events\[\]\` (QAEvents) and \`kpis\[\]\` (performance/fairness/compliance KPIs for evaluation; links to M19 metric definitions)    
\* \`training\_dataset\_ids\[\]\` (TrainingDatasetID(s))    
\* \`model\_version\_pre\` and \`model\_version\_post\` (ModelVersion pre/post)    
\* \`consent\_version\` (ConsentVersion from M26)    
\* \`jurisdiction\_overlay\_ids\[\]\` (JurisdictionOverlayIDs from H.26)    
\* \`governance\_rationale\` / \`decision\_notes\` (governance rationale/decision notes)    
\* \`expected\_impact\` (expected impact: clinical, fairness, compliance)    
\* \`packet\_version\` and \`ledger\_schema\_version\`    
\* \`governance\_actors\[\]\` (participants for governance sign-off)    
\* \`ethical\_override\_ref\` (reference to Appendix H.23 if an ethical override is invoked)

\#\#\# \*\*Outputs\*\*

\* \`retraining\_record\` (approved or denied retraining record; version-pinned)    
\* \`denied\_retraining\_record\` (Denied Retraining Record with denial outcome; version-pinned)    
\* \`audit\_artifacts\[\]\` (FHIR resource IDs/hashes for AuditEvent, Provenance, plus linked Task/Observation/DocumentReference/Binary/Bundle as applicable)    
\* \`kpi\_updates\` (updated KPIs routed to QA dashboards in M19)    
\* \`patient\_disclosure\_packets\` (M30) and \`regulator\_compliance\_exports\` (M31), when retraining materially affects outcomes    
\* \`governance\_archive\_refs\[\]\` (governance archive pointers for audit)

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest triggers\*\*: Accept \`trigger\_refs\[\]\` originating from CAPA/QA/compliance modules (M19, M29–M31, M43–M47) and/or external advisories (as trigger pointers).    
2\. \*\*Create retraining event draft\*\*: Initialize a retraining event record and populate required fields: \`trigger\_refs\[\]\`, \`training\_dataset\_ids\[\]\`, \`model\_version\_pre\`, \`model\_version\_post\`, \`consent\_version\`, \`jurisdiction\_overlay\_ids\[\]\`, \`governance\_rationale/decision\_notes\`, and \`expected\_impact\`.    
3\. \*\*Validate mandatory field completeness\*\*: If any required field in Step 2 is missing, mark the retraining event invalid and proceed as a denial outcome (Denied Retraining Record).    
4\. \*\*Consent & overlay gate\*\*: Evaluate whether retraining is permitted under \`consent\_version\` and \`jurisdiction\_overlay\_ids\[\]\`. If not permitted or overlays fail, emit \`denied\_retraining\_record\`, and version-pin the denial.    
5\. \*\*Governance review gate\*\*: Require governance sign-off prior to deployment; governance actors validate dataset quality, confirm fairness/compliance KPIs are included in retraining evaluation, and validate overlay fit.    
6\. \*\*Ethical override handling\*\*: If an ethical override is applied, the retraining record must include \`ethical\_override\_ref\` referencing Appendix H.23, and the override is logged as part of the retraining record.    
7\. \*\*Encode and commit retraining decision\*\*: For approved or denied outcomes, encode the decision as a FHIR AuditEvent with linked Provenance and associated Task/Observation/DocumentReference/Binary/Bundle as appropriate, and hash-chain entries for immutability and replayability.    
8\. \*\*Bind replayability identifiers\*\*: Bind and persist \`packet\_version\`, \`ledger\_schema\_version\`, \`model\_version\_pre/post\`, and \`training\_dataset\_ids\[\]\` to the retraining record; enforce that identical combinations yield identical retraining outcomes and downstream KPIs.    
9\. \*\*Close the loop (downstream emissions)\*\*:    
   \* Emit \`kpi\_updates\` to QA dashboards (M19).    
   \* If retraining materially affects outcomes, emit patient-facing disclosure packets via M30 and regulator-facing compliance exports via M31, and update governance archives.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* \*\*No medical knowledge storage\*\*: Do not embed guideline content, disease facts, drug lists, ontology/code tables, lab interpretation tables, or phenotype dictionaries in this module.    
\* \*\*Guideline/advisory triggers are pointers only\*\*: External advisories and guideline updates may be treated as trigger types without reproducing their content.    
\* \*\*Consent/overlay authority is external\*\*: Module 48 defers to Appendix H.26 (Overlays) and H.34 (Retention) as authoritative; it stores identifiers and references, not rules.    
\* \*\*Audit/provenance authority is external\*\*: Generic audit/provenance semantics are centralized in Appendix C.11/C.12; Module 48 enumerates required artifacts but does not restate mapping details.    
\* \*\*No shadow retraining\*\*: Shadow/undocumented retraining is prohibited; retraining evaluations must include fairness and compliance metrics and absence is a governance failure.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Modules: M19, M29, M30, M31, M43, M44, M45, M46, M47, M26    
\* Appendices: F.48, H.26, H.23, H.34, C.11, C.12

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

For every retraining or governance event, log at minimum:

\* \`retraining\_record\_id\`, \`model\_version\_pre\`, \`model\_version\_post\`, \`training\_dataset\_ids\[\]\`, \`packet\_version\`, \`ledger\_schema\_version\`    
\* \`trigger\_refs\[\]\` including references to CAPA/QA/Mitigation/Compliance source records and QAEvents that motivated retraining    
\* \`consent\_version\`, \`jurisdiction\_overlay\_ids\[\]\`, and overlay evaluation outcome (permitted/denied)    
\* Governance decision (approval/denial), rationale, participating governance actors, timestamps    
\* Evaluation metrics used in the decision (fairness/compliance/performance KPIs; links to M19 metric definitions)    
\* FHIR artifact IDs and hashes for AuditEvent, Provenance, Task, Observation, DocumentReference, Binary/Bundle    
\* Hash-chain pointers to previous/next retraining records sufficient to verify immutability and deterministic replay

\# \*\*V5.2 M49 — Evidence-Weighted Second Opinion Differential Diagnosis Engine\*\*

\#\#\# \*\*Purpose\*\*

Module 49 ranks and outputs the most likely diagnoses (“second opinion”) by weighing evidence from medical studies and guidelines, in order to cut through noise and consistently identify the right diagnosis with high confidence.    
It filters and prioritizes diagnoses using the strength of supporting evidence and returns a concise list of top differentials with clear provenance (citations).

\#\#\# \*\*Scope (in scope / out of scope)\*\*

\*\*In scope\*\*

\* Scoring and ranking candidate diagnoses produced by the Medical Knowledge Graph (MKG) reasoning engine using MKG-linked evidence nodes.    
\* Producing either a single diagnosis or a top-3 differential list based on confidence distribution, with evidence citations for each output diagnosis.    
\* Ranking evidence nodes by weight contribution so the most influential studies/guidelines can be highlighted per diagnosis.

\*\*Out of scope\*\*

\* Generating candidate diagnoses (owned by the MKG reasoning engine).    
\* Defining or embedding guideline or study content; Module 49 consumes evidence references and produces citations/links to the sources.    
\* Any refinement of weighting strategy beyond the initial algorithm described here (handled through iteration and governance loops).

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \*\*MKG\\\_results\*\*    
  \* \*\*candidate\\\_diagnoses\\\[\\\]\*\*    
    \* diagnosis\\\_id / diagnosis\\\_label (identifier/label as provided by MKG)    
    \* \*\*evidence\\\_list\\\[\\\]\*\* (MKG-linked evidence nodes)    
      \* source\\\_type    
      \* relevance\\\_score    
      \* association\\\_strength (if provided by MKG)    
      \* publication\\\_quality (if provided by MKG)    
      \* patient\\\_profile\\\_match (if provided by MKG)    
      \* source\\\_citation\\\_pointer (linkable reference to guideline/study source)    
    \* prevalence\\\_or\\\_rarity\\\_metadata (optional; for prevalence adjustment)

\#\#\# \*\*Outputs\*\*

\* \*\*ranked\\\_diagnoses\\\[\\\]\*\* sorted by descending score.    
\* \*\*final\\\_output\*\*    
  \* single\\\_diagnosis (when confidence is decisively higher) OR    
  \* top\\\_3\\\_differentials (ranked 1–3)    
\* For each output diagnosis:    
  \* diagnosis\\\_score (confidence score)    
  \* evidence\\\_citations\\\[\\\] (citations linking to guideline/study sources)    
  \* evidence\\\_contribution\\\_ranking\\\[\\\] (evidence nodes ranked by weight contribution; “most influential” evidence highlighted)

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. \*\*Ingest MKG output\*\*: read the set of candidate diagnoses generated for the case, each linked to MKG evidence nodes.    
2\. \*\*Initialize scoring\*\*: for each candidate diagnosis, set \`score \= 0\`.    
3\. \*\*Weight-by-source and relevance accumulate\*\*: for each evidence node in \`candidate\_diagnosis.evidence\_list\`:    
   \* compute \`weight \= SourceWeight(evidence\_node.source\_type)\`    
   \* read \`relevance \= evidence\_node.relevance\_score\`    
   \* accumulate \`score \+= weight \* relevance\`    
4\. \*\*Optional prevalence adjustment\*\*: optionally apply \`score \= AdjustForPrevalence(score, candidate\_diagnosis)\` to account for disease prevalence or rarity.    
5\. \*\*Store scored candidates\*\*: store \`(candidate\_diagnosis, score, candidate\_diagnosis.evidence\_list)\` for all candidates.    
6\. \*\*Rank diagnoses\*\*: compute \`ranked\_diagnoses \= sort\_by\_score\_descending(all candidate\_diagnoses)\`.    
7\. \*\*Select output size (1 vs 3\\)\*\* based on confidence distribution:    
   \* If one diagnosis has a decisively higher score than the rest, output only that diagnosis; the confidence threshold can be determined by a gap between top and next scores (e.g., top exceeds second by a margin or percentile).    
   \* Otherwise, output the top 3 diagnoses as a ranked differential list (cap at three), ordered 1–3 by score.    
8\. \*\*Attach provenance\*\*: for every output diagnosis, attach citations of the evidence that contributed to its score, linking to the underlying guideline or study source.    
9\. \*\*Rank evidence contributions per diagnosis\*\*: rank evidence nodes by their weight contributions so the most influential studies/guidelines can be highlighted (e.g., flag a guideline as key when it contributes a large share of the score).

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Module 49 uses MKG-derived candidate diagnoses and evidence nodes as the raw materials for scoring and does not define the MKG’s diagnostic generation.    
\* Evidence weighting must consider (a) relevance to the specific patient’s case and (b) the quality/weight of the source, including weighting by source of information.    
\* The algorithm described is the initial implementation and is expected to be refined through iteration, with feedback loops working in concert with Module 48 (Continuous Learning kernel) to adjust weights based on real-world performance.    
\* Outputs must remain concise (single diagnosis when high-confidence; otherwise top 3\\) and must always carry supporting evidence for clinician comparison.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Medical Knowledge Graph (MKG) reasoning engine output (source of candidate diagnoses and evidence nodes).    
\* Module 48: Continuous Learning & Governance Loop (feedback loop for weight adjustment over time).

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* Input snapshot identifiers: MKG\\\_results reference, including the candidate diagnosis set and evidence node identifiers used.    
\* For each diagnosis: final score, ranked position, and the full evidence\\\_list used to compute the score.    
\* For each evidence node: source\\\_type, relevance\\\_score, computed weight, and weight-contribution to the diagnosis score (to support evidence contribution ranking).    
\* Output decision trace: whether “single diagnosis” or “top 3” was emitted, with the observed score distribution rationale (gap-based decision).    
\* Provenance artifacts: citations attached to each output diagnosis that link to the guideline or study source in the EoH interface.    
\* If prevalence adjustment is applied: record that AdjustForPrevalence was used for the candidate diagnosis.

\# \*\*V5.2 M50 — DxLandscapeFromEoH Diagnostic Landscape Orchestrator\*\*

\#\#\# \*\*Purpose\*\*

DxLandscapeFromEoH (Module 50\\) takes one Episode of Health (EoH) as input and outputs a structured diagnostic landscape for that episode.    
The diagnostic landscape contains candidate diagnoses grouped into clinically meaningful clusters, with scores and explainable evidence back to the EoH.

\#\#\# \*\*Scope\*\*

\*\*In scope\*\*

\* Compute \`EoH → DxLandscape\` for one episode, producing clusters and candidates with evidence references.    
\* Support request inputs via \`eohRef\` or \`eohInline\`, with optional \`options\` and \`context\`.    
\* Support optional inclusion of per-candidate explainability, stage/acuity enrichments, model contributions, and time horizon selection via \`DxLandscapeOptions\`.

\*\*Out of scope\*\*

\* Any logic not represented by the Module 50 request/response contracts and DxLandscape data model.    
\* Any additional policies beyond the documented “only if allowed by policy” constraint for debug fields.

\#\#\# \*\*Inputs (data objects / fields only)\*\*

\* \`DxLandscapeFromEoHRequest\`    
  \* \`eohRef?: { tenantId: string; eohId: string; versionId?: string }\`    
  \* \`eohInline?: EpisodeOfHealth\`    
  \* \`options?: DxLandscapeOptions\`    
  \* \`context?: RequestContext\`    
\* \`DxLandscapeOptions\`    
  \* \`focusSets?: string\[\]\`    
  \* \`minCandidateScore?: number\`    
  \* \`maxClusters?: number\`    
  \* \`maxCandidatesPerCluster?: number\`    
  \* \`explainabilityLevel?: "none" | "basic" | "full"\`    
  \* \`includeStageAndAcuity?: boolean\`    
  \* \`includeModelContributions?: boolean\`    
  \* \`timeHorizon?: "point\_in\_time" | "1\_year" | "5\_year"\`    
\* \`RequestContext\`    
  \* \`requestingUserId?: string\`    
  \* \`requestingSystemId?: string\`    
  \* \`purposeOfUse?: "diagnosis" | "screening" | "research" | "quality\_improvement"\`    
  \* \`correlationId?: string\`

\#\#\# \*\*Outputs\*\*

\* \`DxLandscapeFromEoHResponse\`    
  \* \`moduleId: "Module50.DxLandscapeFromEoH"\`    
  \* \`moduleVersion: string\`    
  \* \`eohId: string\`    
  \* \`eohVersionId?: string\`    
  \* \`generatedAt: string\`    
  \* \`generationContext?: GenerationContext\`    
  \* \`landscape: DxLandscape\`    
  \* \`debugInfo?: DxLandscapeDebugInfo\` (optional, internal; only if allowed by policy)    
\* \`GenerationContext\`    
  \* \`optionsApplied: DxLandscapeOptions\`    
  \* \`inputSnapshotId?: string\`    
  \* \`runtimeMs?: number\`

\#\#\# \*\*Process / Logic (deterministic, stepwise, no interpretation)\*\*

1\. Accept a \`DxLandscapeFromEoHRequest\` containing either \`eohRef\` or \`eohInline\`.    
2\. Apply \`options?: DxLandscapeOptions\` and \`context?: RequestContext\` from the request.    
3\. Produce a \`DxLandscapeFromEoHResponse\` with \`moduleId\`, \`moduleVersion\`, \`eohId\`, optional \`eohVersionId\`, \`generatedAt\`, optional \`generationContext\`, and \`landscape\`.    
4\. Populate \`generationContext.optionsApplied\` with the options actually used after defaults/policy overrides, and populate optional \`inputSnapshotId\` and \`runtimeMs\` when available.    
5\. Build \`landscape: DxLandscape\` with:    
   \* \`subject: SubjectRef\` and \`episode: EpisodeRef\`.    
   \* \`summary: DxLandscapeSummary\` including \`title\`, \`shortText\`, optional \`longText\`, and optional \`keyFlags\`.    
   \* \`clusters: DxCluster\[\]\`.    
   \* Optional \`modelContributions?: ModelContribution\[\]\` if included.    
   \* Optional \`globalSignals?: GlobalDxSignal\[\]\`.    
6\. For each \`DxCluster\`, populate:    
   \* \`clusterId\`, \`name\`, optional \`description\`, \`clusterScore\` (0–1), optional \`semanticTag\`, \`candidates: DxCandidate\[\]\`, optional \`clusterEvidenceSummary?: EvidenceSummary\`, and optional \`recommendedActionsSummary?: ActionSuggestion\[\]\`.    
7\. For each \`DxCandidate\`, populate:    
   \* \`candidateId\`, \`label\`, \`score\` (0–1) and \`scoreType\`, optional \`scoreRank\`, optional \`stage\`, optional \`acuity\`, optional \`onsetLikelihood\`, \`positiveEvidence: EvidenceItem\[\]\`, optional \`negativeEvidence\`, optional \`conflictingEvidence\`, optional \`featureAttributions?: FeatureAttributionSummary\`, optional \`recommendedActions?: ActionSuggestion\[\]\`, and \`provenance: CandidateProvenance\`.    
8\. For each \`EvidenceItem\`, populate:    
   \* \`evidenceId\`, \`type\`, \`polarity\`, \`sourceRef: EvidenceSourceRef\`, \`description\`, optional \`weight\` (0–1), optional structured \`value\`, and optional \`observedAt\`.    
9\. If \`options.explainabilityLevel\` requires per-candidate attribution, populate \`FeatureAttributionSummary.method\` and \`topFeatures: FeatureContribution\[\]\`, with each \`FeatureContribution\` containing \`featureId\`, \`featureLabel\`, \`contribution\`, and optional \`evidenceRefs\`.    
10\. If \`options.includeModelContributions\` is enabled, populate \`modelContributions?: ModelContribution\[\]\`, including \`modelId\`, \`modelVersion\`, \`modelType\`, optional \`focus\`, \`outputs: ModelOutputSignal\[\]\`, optional \`mappedCandidates?: ModelToCandidateMapping\[\]\`, and optional \`performance\` metadata.    
11\. If debug fields are allowed by policy, populate \`debugInfo?: DxLandscapeDebugInfo\` with optional \`rawModelInputs\`, \`rawModelOutputs\`, \`errors\`, and \`warnings\`.

\#\#\# \*\*Governance / Constraints (explicit boundaries; no new rules)\*\*

\* Candidate inclusion may be constrained by \`minCandidateScore\` as a minimum normalized score (0–1).    
\* Landscape size may be constrained by \`maxClusters\` and \`maxCandidatesPerCluster\`.    
\* Per-candidate explainability output is controlled by \`explainabilityLevel\`.    
\* Stage/acuity enrichments are controlled by \`includeStageAndAcuity\`.    
\* Model provenance details are controlled by \`includeModelContributions\`.    
\* \`debugInfo\` is optional and is only returned if allowed by policy.

\#\#\# \*\*Dependencies (other EoH modules, appendices by reference only)\*\*

\* Evidence items may reference derived features noted as “derived feature from Module 20/30/etc”.    
\* Evidence source references may include \`fhirResourceRef: { resourceType, resourceId }\`.

\#\#\# \*\*Audit Hooks (what must be logged and attributable)\*\*

\* Request audit/policy context: \`requestingUserId\`, \`requestingSystemId\`, \`purposeOfUse\`, and \`correlationId\`.    
\* Reproducibility hooks: \`eohRef.versionId\` (when provided) and response \`eohVersionId\`.    
\* Generation logging: \`generatedAt\`, \`generationContext.optionsApplied\`, \`generationContext.inputSnapshotId\`, and \`generationContext.runtimeMs\`.    
\* Evidence traceability: \`EvidenceSourceRef\` fields (\`eohFactId\`, \`fhirResourceRef\`, \`derivedFeatureId\`) for each \`EvidenceItem\`.    
\* Model provenance traceability (when included): \`ModelContribution\` fields and optional \`performance\` metadata.


---

# PART II — V6 MODULES (M55–M68)

---

# **V6 Module 55 — Execution Modes**

**Scope:** QUERY\_ONLY, DEBUG\_LOOP (non-executable analysis artifact)  
**Authoritative indices:** V5.2 Canonical Module Index · V6 Canonical Module Index

---

## **1\. Finalized M55 Conclusions**

1. **QUERY\_ONLY** is treated as a **read-only posture** that is **behaviorally achievable in V5.2** by **non-invocation** of modules that compute, schedule, escalate, execute, or mutate state. It is **not** a named V5.2 execution mode; it requires **contract clarification only**.  
2. **DEBUG\_LOOP** is a **V6-only capability** requiring **explicit human-in-the-loop control** for inspection and intervention; it is not represented as a V5.2-owned behavior.  
3. Execution-mode handling is treated as **governance \+ enforcement semantics only** in this phase; no implementation design is defined here.

---

## **2\. Ownership Lock**

### **QUERY\_ONLY**

* **Ownership:** **V5.2 (implicit behavior via non-invocation; requires contract clarification only).**  
* **Meaning:** QUERY\_ONLY is not a new engine, not a new module, and not a new execution path; it is the **explicit naming of an already-possible safe posture** that avoids invoking execution/escalation/scheduling behaviors.

### **DEBUG\_LOOP**

* **Ownership:** **V6-only capability requiring explicit human-in-the-loop control.**  
* **Meaning:** DEBUG\_LOOP is not V5.2-owned and is not implied by V5.2 module definitions; it is a V6-scoped inspection/intervention posture.

---

## **3\. Execution Mode Controller Confirmation**

**Execution Mode Controller (EMC) is confirmed as:**

* **V6-only**  
* **Non-canonical** (analysis artifact / candidate control concept; not a listed canonical V6 module in the pinned V6 index)  
* **Governance and enforcement only** (defines/guards mode constraints; does not perform medical reasoning, computation, scheduling, escalation, execution, or state mutation)

---

## **4\. MUST-NOT Guarantees**

### **QUERY\_ONLY — MUST-NOT Guarantees**

In QUERY\_ONLY mode, the system **MUST NOT**:

* **MUST NOT** invoke any reasoning loop or recomputation cycle.  
* **MUST NOT** trigger escalation routing or clinician alerting behaviors.  
* **MUST NOT** trigger plan/action generation or execution-layer drafting/translation.  
* **MUST NOT** trigger any scheduling/orchestration behavior (including any PTM recomputation scheduling posture).  
* **MUST NOT** mutate canonical patient state, suppression state, consent state, or vault contents.  
* **MUST NOT** execute tools or invoke tool runtimes.

**Allowed outcome type (implicit):** read-only retrieval/formatting of already-existing artifacts.

---

### **DEBUG\_LOOP — MUST-NOT Guarantees**

In DEBUG\_LOOP mode, the system **MUST NOT**:

* **MUST NOT** run silently; inspection/intervention is **explicitly human-directed** (no autonomous debug progression).  
* **MUST NOT** auto-publish outputs to the patient channel.  
* **MUST NOT** perform irreversible mutation of canonical state as a side-effect of inspection.  
* **MUST NOT** bypass suppression semantics or consent enforcement.  
* **MUST NOT** feed learning/continuous-learning ingestion as a side-effect of debug inspection.  
* **MUST NOT** autonomously escalate or autonomously execute downstream actions as a side-effect of debug inspection.

---


# **V6 Module 56— Patient Vision Unification**

**Canonical Analysis Artifact (Non-Executable) — Frozen**

**Authoritative indices:**

* V5.2 Canonical Module Index  
* V6 Canonical Module Index

---

## **1\. Finalized M56 Conclusions**

1. M56 defines **Patient Vision Unification** as a **compositional primitive** that binds an existing **timeline snapshot** with an existing **Dx landscape** into a single **read-only** consolidated view.  
2. V5.2 contains the necessary producing modules for timeline state and Dx landscape, but does **not** define a single, explicit consolidated object that formally binds them; the unification is therefore **V6-only** as a composition artifact.  
3. The unified view is **immutable within an invocation context** and is intended for consumption without triggering recomputation or state mutation.

---

## **2\. Ownership Determinations Locked**

* **Timeline computation \= V5.2**  
* **Dx landscape generation \= V5.2 (M50)**  
* **Unified Patient Vision composition \= V6-only**  
* **Read-only access semantics \= V5.2 (implicit behavior)**

---

## **3\. Patient Vision Unification Invariants**

Patient Vision Unification is:

* **Compositional primitive only**  
* **Read-only**  
* **Immutable within an invocation context**

---

## **4\. Patient Vision Object (PVO) Status Locked**

PVO is:

* **V6-only**  
* **Non-canonical** (analysis artifact / candidate primitive)  
* **Composition-only**  
  * no computation  
  * no mutation  
  * no escalation  
  * no scheduling

---

## **5\. MUST-NOT Guarantees**

The M56 construct MUST NOT:

* **recompute**  
* **mutate**  
* **escalate**  
* **make diagnostic claims**  
* **exercise execution control**

---



---


# **V6 M57 — Clinical Invariants System**

---

## **1\. Finalized M57 Conclusions (Concise Restatement)**

1. **Clinical invariants already exist implicitly in V5.2** as distributed, non-negotiable constraints embedded across canonical modules (terrain semantics, escalation gates, suppression rules, consent safeguards).  
2. **M57 introduces no new clinical logic**; it **names, formalizes, and governs** invariants that already shape reasoning behavior.  
3. **All formal structure for invariants is V6-only**, providing registry, injection, and audit semantics without affecting V5.2 execution.  
4. **Invariants constrain reasoning flow only** (ordering, gating, eligibility), **never answers, scores, diagnoses, or outputs**.

---

## **2\. Locked Capability Ownership**

**Ownership is hereby fixed as follows:**

* **Invariant behavior**  
  → **V5.2 (implicit, distributed)**  
  Embedded across existing canonical modules; no central invariant object exists in V5.2.  
* **Invariant formalization / registry**  
  → **V6-only**  
* **Invariant injection layer**  
  → **V6-only**  
* **Invariant audit lifecycle**  
  → **V6-only**

No capability listed above may be reassigned without opening a new phase.

---

## **3\. V6 M57 — Clinical Invariants System (Frozen Definition)**

**Status:**

* **V6-only**  
* **Non-executable**  
* **Non-canonical with respect to reasoning logic**  
* **Governance and constraint modeling only**

**Role of V6 M57:**  
V6 M57 exists solely to **define, name, version, expose, and audit clinical invariants** as abstract constraints. It does not participate in computation, scoring, or decision-making.

---

## **4\. Locked Invariant Constraint (Authoritative)**

**Clinical invariants shape reasoning flow, not answers, scores, or outputs.**

This constraint is absolute and applies to all current and future phases unless explicitly superseded by a new, formally frozen phase.

---

## **5\. MUST-NOT Guarantees (Locked)**

V6 M57 **MUST NOT**:

* Create or introduce clinical knowledge  
* Perform scoring, weighting, or computation  
* Generate diagnoses or treatment logic  
* Execute, escalate, or schedule any process  
* Mutate patient state or reasoning state  
* Override or reinterpret V5.2 canonical logic

These are hard prohibitions.

---

## **6\. Auditability Requirements (Locked)**

The Clinical Invariants System **MUST ensure**:

* All invariants are **explicitly named**  
* All invariants are **versioned**  
* All invariants are **traceable** to rationale and scope  
* All invariants are **immutable within an invocation context**

Auditability applies to invariant definition and application metadata only, not to clinical reasoning outputs.

---



---


# **V6 M58 — HITL (Human in the Loop) Interruption Controller (HIC)**

**Analysis-Only · Non-Executable · V6 Candidate**

---

## **Purpose**

Define **explicit, deterministic semantics for mid-stream human interruption** of EoH processing, expressed strictly through **suppression, pause, and audit-controlled behavior**, not OS or runtime preemption.

---

## **Scope & Role**

V6 M58 formalizes **how human interruption intent is interpreted and honored** during EoH reasoning, orchestration, or publication, while preserving V5.2 ownership of suppression mechanics and audit trails.

Interruption is **checkpoint-bounded** and **governance-safe**.

---

## **OWNS**

V6 M58 OWNS:

* Normalization of human interruption intent into suppression-compatible control intents:

  * `freeze`

  * `defer`

  * `reroute`

  * `suppress_publish`

* Deterministic mapping of interruption intents into **existing V5.2 suppression and audit primitives**

* Checkpoint-bounded honoring of interruption at defined orchestration boundaries

---

## **DOES NOT OWN**

V6 M58 DOES NOT OWN:

* OS or runtime preemption

* UI workflows, identity, authentication, or RBAC

* Suppression policy, TTLs, or priority ladders (V5.2-owned)

* Any mutation of patient state

* Any probability, diagnosis, or plan generation logic

---

## **Governance Guarantees**

* Interruption semantics are **expressed, not executed**

* All effects are mediated through **existing V5.2 suppression and audit systems**

* No interruption may bypass consent, suppression, or escalation guardrails

---

## **HITL MUST-NOT Guarantees**

* No patient-state mutation

* No bypass of consent or suppression controls

* No autonomous publish

* No autonomous escalation or execution

* No learning ingestion as a side-effect of interruption



---


# **V6 M59 — Plan Co-Creation Contract (PCC)**

**Analysis-Only · Non-Executable · V6 Candidate**

---

## **Purpose**

Define a **formal contract for human–system plan co-creation**, enabling human input to shape plans through **confirmation-gated, draft-only artifacts** without mutating canonical patient state or bypassing governance.

---

## **Scope & Role**

V6 M59 establishes **what humans may influence** during plan formation and **how that influence is constrained**, ensuring all plans remain **non-authoritative until explicitly confirmed** through existing V5.2 execution and review gates.

---

## **OWNS**

V6 M59 OWNS:

* Plan contract objects representing:

  * draft

  * revision

  * approval intent

* Deterministic “not active until confirmed” constraints

* Versioned handoff semantics between human intent and system-generated plan artifacts

---

## **DOES NOT OWN**

V6 M59 DOES NOT OWN:

* Plan generation logic

* Clinical content selection

* Execution or activation mechanisms (V5.2-owned)

* Suppression or escalation mechanics

* Any autonomous state transition

---

## **Governance Guarantees**

* Human interaction produces **draft-only artifacts**

* No plan becomes authoritative without downstream clinician confirmation

* Co-creation shapes **intent and constraints**, not execution

---

## **HITL MUST-NOT Guarantees**

* No patient-state mutation

* No bypass of consent or suppression controls

* No autonomous publish

* No autonomous escalation or execution

* No learning ingestion as a side-effect of co-creation



---


# **V6 M60 — HITL (Human in the Loop) Audit & Replay Frame (HARF)**

**Analysis-Only · Non-Executable · V6 Candidate**

---

## **Purpose**

Define a **standard, read-only audit and replay framing** for all HITL interactions, enabling **audit-grade reconstruction and replay** anchored to existing audit and provenance artifacts.

---

## **Scope & Role**

V6 M60 provides a **semantic overlay** for interpreting HITL events (interruptions, edits, approvals) without altering storage, execution, or patient state.

Replay is **derived**, not re-executed.

---

## **OWNS**

V6 M60 OWNS:

* HITL event framing requirements for audit-grade reconstruction

* Causal linkage between:

  * human action

  * affected pipeline stage

  * downstream effects

* Replay overlay semantics:

  * “what happened”

  * “what would have happened without this action”

---

## **DOES NOT OWN**

V6 M60 DOES NOT OWN:

* Audit storage or ledger infrastructure

* Runtime execution or recomputation

* Any mutation of patient state

* Any learning or retraining execution

---

## **Governance Guarantees**

* Replay is **read-only and derived**

* Audit framing cannot influence live execution

* HITL audit events remain immutable once recorded

---

## **HITL MUST-NOT Guarantees**

* No patient-state mutation

* No bypass of consent or suppression controls

* No autonomous publish

* No autonomous escalation or execution



---


# **V6 M61 — Pattern Inspiration (Non-binding)** 

## **Scope Lock**

* This artifact freezes **Phase 6 — Pattern Inspiration (Non-binding)** as **analysis-only reference material**.  
* The frozen Phase 6 content is preserved **exactly as previously documented** (verbatim section included below).  
* This freeze introduces **no execution semantics**, **no governance authority**, and **no new system capability**.

---

## **Purpose Lock**

Phase 6 exists for:

* **Pattern recognition and naming only**  
* **Inspired by FMP usage**  
* **Non-binding and non-authoritative**

---

## **Ownership Lock**

* **V5.2 owns all escalation execution logic** (routing, suppression gates, delivery, tiers).  
* **V6 owns conceptual formalization only** for this phase (documentation / mapping only; non-executable).  
* **Platform / process owns any roadmap** derived from these patterns (planning, prioritization, implementation sequencing).

---

## **Referenced V6 Construct Lock**

Any referenced V6 construct in Phase 6 (including “Escalation Pattern Registry”) is:

* **Conceptual only**  
* **Non-canonical**  
* **Non-executable**  
* **Without authority** over routing, thresholds, tier policies, escalation decisions, or runtime behavior

No referenced V6 construct gains execution standing from Phase 6\.

---

## **MUST-NOT Guarantees**

Phase 6 MUST NOT:

* Introduce **new escalation logic**  
* Define **thresholds**, **tiers**, or **policies**  
* Create **runtime hooks**  
* Create or imply **routing authority**  
* Create or imply **decision authority**  
* Perform any **backward merge** into V5.2  
* Merge Phase 6 content into **V6 execution modules**

---

## **Frozen Phase 6 Content (Verbatim)**

Below is a **Phase 6 — Pattern Inspiration (Non-binding)** analysis, strictly confined to the **EoH V5.2 \+ V6 Sandbox (LOCKED)**.  
This is **analysis-only**, **non-executable**, and **does not import code or logic**.

---

# **Phase 6 — Pattern Inspiration (Non-binding)**

## **Phase Objective → Restated as Capabilities**

### **Capability A — Escalation Pattern Abstraction (Conceptual)**

Identify and document **recurring escalation patterns** observed in FMP usage (e.g., tiered escalation, gating, human confirmation, suppression-aware routing) **without importing logic**.

### **Capability B — Conceptual Reuse Mapping**

Map which **conceptual patterns** are already present in V5.2, which are formalized in V6, and which remain **out-of-scope** (platform / infra).

### **Capability C — Non-Executable Pattern Roadmap**

Produce a **clean, forward-looking roadmap** describing how these patterns inform V6 evolution, without implementation, execution semantics, or backward merge.

---

## **Capability Ownership Analysis**

### **Capability A — Escalation Pattern Abstraction**

**Ownership:**  
**V5.2 (conceptual behavior already present)**

**Relevant V5.2 Modules (Conceptual Coverage):**

* **M6 — Escalation Router**: tiered routing logic (patient vs clinician)  
* **M7 — Data Quality & Care Plan Orchestration**: human-in-loop gating  
* **M8 / M9 / M10 / M41**: suppression, pause, audit, and escalation delivery  
* **M14 — Action & Escalation Engine**: tiered outputs (T0–T4)

**Status:**  
✔ **Already covered conceptually**  
✱ **Clarification-only patch may be needed** to explicitly state that these escalation patterns are **inspired by observed FMP usage**, not newly introduced behavior.

**Notes:**  
No new escalation logic is added. This phase **documents recognition**, not expansion.

📄 Canonical reference:

---

### **Capability B — Conceptual Reuse Mapping**

**Ownership:**  
**Split between V5.2 and V6**

#### **V5.2 — Conceptual Reuse (Implicit)**

V5.2 already embodies:

* **Tiered escalation**  
* **Human confirmation gates**  
* **Suppression-aware routing**  
* **Audit-anchored escalation**

These are **implicit behaviors**, not named pattern primitives.

#### **V6 — Conceptual Formalization (Non-Executable)**

**Candidate V6 Outline (Analysis-only):**

### **V6 M61 — Escalation Pattern Registry (Conceptual)**

**Purpose:**  
Document and name **recognized escalation patterns** observed across FMP and EoH behavior to improve clarity, review, and governance—**without execution authority**.

**OWNS:**

* Named escalation patterns (e.g., “Tiered Escalation”, “Human-Confirm Gate”, “Suppression-First Routing”)  
* Pattern descriptions and invariants  
* Mapping of patterns → existing V5.2 modules

**DOES NOT OWN:**

* Any routing logic  
* Any decision thresholds  
* Any runtime behavior  
* Any modification of V5.2 modules

**Status:**

* V6-only  
* Non-canonical  
* Analysis / documentation artifact

📄 V6 index context:

---

### **Capability C — Non-Executable Pattern Roadmap**

**Ownership:**  
**Out-of-scope (platform / process)**

**Reason:**  
Roadmapping how FMP-observed patterns influence future design is **governance and product process**, not EoH reasoning.

**EoH Assumptions It Depends On:**

* Escalation semantics remain deterministic and suppression-aware  
* Human-in-loop remains a **gate**, not a runtime override  
* Auditability is mandatory for any escalation-adjacent behavior

EoH **consumes** these assumptions but does not own the roadmap artifact itself.

---

## **Clean Phase 6 Roadmap (Non-Executable)**

### **Phase 6 Outputs (Allowed)**

1. **Pattern Inventory**  
   * List of named escalation patterns observed via FMP  
2. **Conceptual Mapping Table**  
   * Pattern → V5.2 modules (already owning behavior)  
3. **V6 Conceptual Registry Draft**  
   * Analysis-only module outline (e.g., V6 M61)  
4. **Clarification Notes**  
   * Where V5.2 language may benefit from precision (no logic change)

### **Explicit Non-Outputs**

* ❌ No new escalation logic  
* ❌ No thresholds, tiers, or policies  
* ❌ No runtime hooks  
* ❌ No UI, infra, or orchestration design  
* ❌ No backward merge into V5.2

---

## **Phase 6 Closure Statement**

**Phase 6 does not add capability.**  
It **names, documents, and contextualizes** escalation patterns already present in EoH, using FMP as an **inspiration source only**, preserving:

* V5.2 as canonical execution logic  
* V6 as the formalization and analysis layer  
* Clear separation between reasoning, governance, and platform concerns

---

**Authoritative Sources Used (Pinned):**

* V5.2 Canonical Module Index  
* V6 Canonical Module Index

---



---


\### 1. Module Canonical Name \& Purpose



\*\*Canonical name:\*\* \*\*V6 — Orbit Mode ↔ EoH Clinical Governance Handshake (OM↔CGH)\*\*



\*\*Purpose:\*\* This module formalizes a \*\*governance-only interface boundary\*\* between PortalVision’s \*\*Orbit Mode\*\* epistemic navigation substrate (`circle | target | strike`) and the \*\*Ethos of Health (EoH) clinical governance system\*\*. It specifies how Orbit Mode \*\*may propose traversal intent\*\* while ensuring EoH remains the \*\*sole authority\*\* over suppression, aggregation, arbitration, promotion, invariant enforcement, and refusal. \*\*This module introduces no new clinical reasoning, no new clinical logic, and no downstream reasoning changes\*\*; it only binds existing EoH governance capabilities to an explicit, auditable handshake boundary. 



---



\### 2. Responsibility Boundary (Authoritative)



\#### What Orbit Mode MAY do



Orbit Mode \*\*MAY\*\*:



\* Provide a \*\*navigation state\*\*: `circle`, `target`, or `strike`.

\* Provide \*\*scope / focus metadata\*\* (e.g., topic focus, artifact focus, question subspace identifiers) as \*\*propositional intent\*\*.

\* Provide \*\*non-authoritative selection hints\*\* (e.g., “explore broadly”, “focus this sub-question”, “attempt promotion of this candidate output”) that \*\*request\*\* EoH evaluation.

\* Provide \*\*provenance context\*\* for the navigation state (who/what initiated it, timestamp, UI context) for audit framing.



\#### What Orbit Mode MUST NOT do



Orbit Mode \*\*MUST NOT\*\*:



\* \*\*MUST NOT\*\* introduce, alter, or compute clinical conclusions, probabilities, weights, diagnoses, or treatment recommendations.

\* \*\*MUST NOT\*\* suppress, unsuppress, or bypass EoH suppression controls.

\* \*\*MUST NOT\*\* override EoH refusal outcomes or safety posture.

\* \*\*MUST NOT\*\* couple or fuse cross-stack signals, adjudicate conflicts, or resolve inconsistencies.

\* \*\*MUST NOT\*\* trigger escalation, scheduling, execution, publication, or any state mutation directly.

\* \*\*MUST NOT\*\* treat its own state (`circle/target/strike`) as evidence or as a confidence/certainty modifier.



\#### What EoH alone controls



EoH \*\*MUST\*\* be treated as the \*\*final authority\*\* and \*\*exclusive owner\*\* of:



\* Suppression enforcement and publish/route suppression.

\* Multi-Pathway Aggregation (MPA) and differential synthesis.

\* Cross-stack arbitration and coherence requirements.

\* Promotion gates and eligibility determination.

\* Invariant enforcement (including “no certainty inflation” constraints).

\* Refusal logic and final refusal rendering.



This handshake boundary is \*\*governance-only\*\* and is compatible with \*\*read-only postures\*\* (explicitly naming an already-possible “non-invocation” posture without creating a new execution path). 



---



\### 3. Orbit Mode → EoH Mapping (Reuse Table)



| Orbit Mode State | Description                                                                                                 | EoH V5.2 Modules Reused                                                                                                                                       | Governance Outcome                                                                                                                                                            |

| ---------------- | ----------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |

| `circle`         | Broad exploration intent; widen candidate hypotheses/paths without promotion pressure.                      | \*\*Suppression engines\*\*; \*\*MPA\*\*; \*\*Cross-Stack arbitration\*\*; \*\*Invariant enforcement\*\*; \*\*Refusal logic\*\*                                                   | EoH runs exploration under suppression/invariants; produces a \*\*non-promoted\*\* candidate landscape; preserves uncertainty; blocks disallowed content via refusal/suppression. |

| `target`         | Focused attention intent; narrow scope to a specific sub-question/artifact while remaining non-promotional. | \*\*Suppression engines\*\*; \*\*MPA\*\* (focused pass); \*\*Cross-Stack arbitration\*\*; \*\*Invariant enforcement\*\*; \*\*Refusal logic\*\*                                    | EoH runs focused evaluation; may \*\*defer\*\* if insufficient evidence; may prune dead ends; still \*\*no promotion\*\* occurs without an explicit promotion gate path.              |

| `strike`         | \*\*Promotion attempt\*\* intent; requests evaluation for escalation/promotion but does not enact it.           | \*\*Promotion gate(s)\*\*; \*\*Suppression engines\*\*; \*\*MPA\*\* (supporting evidence only); \*\*Cross-Stack arbitration\*\*; \*\*Invariant enforcement\*\*; \*\*Refusal logic\*\* | EoH adjudicates the promotion attempt: \*\*accept / defer / reject / refuse\*\*. Orbit Mode receives only the governance outcome; it cannot force promotion or override refusal.  |



\*\*Zero duplication note:\*\* Orbit Mode states map to \*\*existing EoH governance modules\*\*; this module only defines routing and constraints at the interface boundary.



---



\### 4. Promotion Semantics (Critical)



\#### Why `strike` is a promotion attempt, not an action



`strike` \*\*MUST\*\* be interpreted as a \*\*non-authoritative request\*\* to evaluate whether a candidate output (or escalation) is eligible for promotion under EoH governance. It \*\*MUST NOT\*\* be interpreted as:



\* an execution command,

\* a correctness signal,

\* a causality claim,

\* or a certainty increase.



\*\*Required boundary statement (authoritative):\*\*



> \*\*“A strike does not imply correctness, causality, or elevation.”\*\*



\#### How EoH handles `strike`



When a `strike` is presented, EoH \*\*MUST\*\* process it through its \*\*existing\*\* governance stack (suppression → aggregation support if needed → cross-stack arbitration → promotion gate → invariants → refusal, as applicable), producing one of four outcomes:



\* \*\*Acceptance\*\*



&nbsp; \* Meaning: the promotion attempt is \*\*eligible to proceed\*\* through the existing promotion pathway.

&nbsp; \* Governance property: acceptance indicates \*\*eligibility\*\*, not correctness; downstream publication/escalation remains governed by existing EoH gates.



\* \*\*Deferral\*\*



&nbsp; \* Meaning: the promotion attempt cannot be decided now due to missing provenance, insufficient coherence, insufficient evidence density, or other governance constraints.

&nbsp; \* Governance property: deferral preserves uncertainty and routes the session back to non-promotional exploration (`circle/target`) without escalation.



\* \*\*Rejection\*\*



&nbsp; \* Meaning: the promotion attempt is \*\*not eligible\*\*, but the request is not inherently disallowed.

&nbsp; \* Governance property: rejection returns to exploration without promotion; it does not relax suppression or invariants.



\* \*\*Refusal\*\*



&nbsp; \* Meaning: the attempted promotion or its content violates refusal/safety constraints or is otherwise disallowed.

&nbsp; \* Governance property: refusal is final at the boundary; Orbit Mode \*\*MUST NOT\*\* retry by state manipulation or bypass.



---



\### 5. Invariants Introduced (Boundary-Only)



These are \*\*boundary invariants\*\* (interface constraints) that are \*\*enforced using existing EoH mechanisms\*\*. They \*\*do not add new clinical logic\*\*; they only constrain routing, eligibility, and audit semantics. 



1\. \*\*Orbit Propositionality Invariant\*\*



&nbsp;  \* \*\*Invariant:\*\* Orbit Mode state (`circle/target/strike`) is \*\*propositional-only metadata\*\* and \*\*MUST NOT\*\* be consumed as evidence, weight, probability, confidence, or certainty modifier.

&nbsp;  \* \*\*Enforced by:\*\* Existing \*\*invariant enforcement\*\* and governance constraints that shape reasoning flow without changing answers.



2\. \*\*No Promotion Without Provenance\*\*



&nbsp;  \* \*\*Invariant:\*\* A `strike` \*\*MUST NOT\*\* be eligible for promotion unless it carries minimum provenance metadata (initiator, target artifact pointer, timestamp, and trace linkage).

&nbsp;  \* \*\*Enforced by:\*\* Existing \*\*promotion gate(s)\*\* and \*\*audit/provenance requirements\*\*.



3\. \*\*No Coupling Without Cross-Stack Coherence\*\*



&nbsp;  \* \*\*Invariant:\*\* Orbit-proposed coupling/fusion or “promotion of a combined claim” \*\*MUST NOT\*\* proceed without passing \*\*cross-stack arbitration\*\* for coherence.

&nbsp;  \* \*\*Enforced by:\*\* Existing \*\*cross-stack arbitration\*\* module(s).



4\. \*\*Suppression-First and Refusal Supremacy\*\*



&nbsp;  \* \*\*Invariant:\*\* Orbit Mode \*\*MUST NOT\*\* bypass or weaken suppression/refusal outcomes; state changes cannot be used to “route around” disallowed content.

&nbsp;  \* \*\*Enforced by:\*\* Existing \*\*suppression engines\*\* and \*\*refusal logic\*\*.



5\. \*\*No Execution or Escalation by Navigation State\*\*



&nbsp;  \* \*\*Invariant:\*\* Orbit Mode states \*\*MUST NOT\*\* directly trigger execution, escalation, scheduling, or publication; only EoH’s existing gates may do so.

&nbsp;  \* \*\*Enforced by:\*\* Existing \*\*promotion gates / escalation routing gates\*\* and execution safeguards; consistent with explicit “must-not execute” posture constraints. 



6\. \*\*Invocation-Local, Audit-Visible State\*\*



&nbsp;  \* \*\*Invariant:\*\* Orbit Mode state is \*\*invocation-local context\*\*; it may be recorded for audit but \*\*MUST NOT\*\* become canonical patient state.

&nbsp;  \* \*\*Enforced by:\*\* Existing audit constraints and read-only framing; compatible with HITL audit/replay framing without altering runtime behavior. 



---



\### 6. Audit \& Performance Implications (Non-Marketing)



This handshake changes \*\*governance visibility\*\*, not reasoning logic.



\*\*Defensible effects:\*\*



\* \*\*Explicit traversal paths:\*\* Orbit state becomes an auditable “navigation intent” annotation, enabling reconstruction of whether a result emerged from `circle` exploration, `target` focusing, or a `strike` promotion attempt. 

\* \*\*Earlier dead-end pruning (governance-level):\*\* Because suppression, invariants, and refusal remain mandatory at the boundary, disallowed/invalid promotion attempts can be rejected/refused \*\*earlier\*\*, avoiding wasted downstream routing.

\* \*\*Reduced rework in review/audit:\*\* The boundary makes “who asked for promotion” and “which artifact was targeted” explicit, reducing ambiguity during governance review and replay.

\* \*\*Preserved uncertainty:\*\* Treating Orbit state as propositional-only prevents certainty inflation; uncertainty remains determined by existing EoH modules.

\* \*\*No claimed accuracy/speed gains:\*\* This module does not change inference algorithms or scoring; it only structures routing and audit framing.



\*\*Non-interference statement:\*\* This module does not alter or assume changes to offline tool governance or other V6 stacks (e.g., tool detection/compilation pipelines or terrain modules); it strictly constrains the Orbit↔EoH interface boundary. 



---



\### 7. Canonical One-Line Summary



> \*\*“Orbit Mode explores; EoH governs; the handshake makes the boundary explicit and enforceable.”\*\*





---


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


---


# **V6 M64 — Functional Utilization Discordance Detector (FUDD)**

**Serum Adequacy ≠ Effective Utilization: Two-Layer Detection, Classification, and Role-Differentiated Surfacing**

**Version:** 2.0 — Adds two-layer detection architecture (signature-matched + general discordance heuristic), inverse discordance detection, population-level discovery pipeline feed, and expanded analyte coverage across 8 analyte classes.

---

## **Purpose (3–5 sentences)**

Module 64 (FUDD) detects, classifies, and surfaces cases where a patient's serum/plasma levels of an analyte fall within reference ranges but effective utilization at the tissue, organ, or intracellular level is impaired. The system currently treats lab values at face value once they pass M7A quality checks; no existing module systematically asks whether "normal bloodstream levels" reflect actual functional adequacy. FUDD fills this gap using a **two-layer detection architecture**: **Layer 1** matches against curated FUD signatures for well-characterized discordance patterns, while **Layer 2** applies a **general discordance heuristic** capable of detecting novel or uncharacterized serum-function disconnects without a pre-loaded signature. FUDD also detects **inverse discordance** — cases where serum levels appear abnormal but tissue status is adequate (e.g., inflammation-driven redistribution producing falsely low serum readings). FUDD generates **role-differentiated output payloads**: B2C (patient-facing) outputs surface intervention guidance directly; B2MD (clinician-facing) outputs surface the detection flag plus expandable mechanism context and candidate interventions as a togglable panel, with all intervention activation remaining under clinician authority. Layer 2 exploratory detections are surfaced with distinct governance constraints and lower nudge postures than Layer 1 confirmed detections. (New logic; V6 only.)

---

## **Foundational Concept: Functional Utilization Discordance (FUD)**

### **Definition**

**Functional Utilization Discordance (FUD)** is the state in which measured serum/plasma concentration of a bioactive substance (nutrient, hormone, neurotransmitter precursor, protein, or cofactor) falls within the laboratory reference range, while downstream functional indicators — clinical presentation, tissue-level metabolite assays, receptor-status markers, or organ-specific utilization tests — indicate that effective biological utilization is impaired.

**Inverse Functional Utilization Discordance (iFUD)** is the converse: serum/plasma levels appear abnormal (low or high) while tissue-level status is adequate, typically because inflammation, acute phase response, or compartmental redistribution is distorting the serum measurement. iFUD prevents unnecessary treatment of falsely abnormal lab results.

### **Canonical Statement**

> **"You are not what you eat; you are what you absorb — and you are not what circulates in your bloodstream; you are what your organs effectively utilize."**

### **Why This Matters**

Standard blood panels measure **compartmental concentration** (what is present in the vascular compartment). They do not measure:

* **Transport efficiency** — whether the analyte is successfully crossing barriers (blood-brain barrier, intestinal epithelium, cell membranes, placental barrier) to reach target tissues.
* **Receptor availability** — whether the receptors required for cellular uptake are functional, unblocked, and unsaturated by competing ligands or autoantibodies.
* **Enzymatic conversion capacity** — whether the analyte can be converted to its biologically active form (e.g., folic acid → dihydrofolate → tetrahydrofolate → 5-MTHF; 25-OH-D → 1,25-dihydroxy-D; T4 → T3).
* **Cofactor sufficiency** — whether the cofactors required for the analyte's biological activity are present (e.g., glutathione for folate transport backup pathways; selenium for deiodinase-mediated T4→T3 conversion; copper for ceruloplasmin-mediated iron mobilization).
* **Competitive displacement** — whether synthetic analogs, structural mimics, pharmacological agents, or cross-reactive antibodies are occupying binding sites and preventing the biologically active form from functioning.
* **Homeostatic masking** — whether the body is maintaining serum levels from tissue reserves (bone magnesium, liver vitamin A, liver iron) while those reserves are being depleted.
* **Inflammatory redistribution** — whether acute phase responses are sequestering the analyte (hepcidin→iron), consuming it (oxidative stress→glutathione), or suppressing its carrier proteins (inflammation→retinol-binding protein, albumin).
* **Binding protein status** — whether the biologically active free fraction is adequate regardless of total levels (free vs total vitamin D, free vs total testosterone, free vs total cortisol).

### **Discordance Mechanism Taxonomy**

FUDD classifies the root cause of each detected discordance into one or more of the following mechanism categories:

| Mechanism Class | Code | Description | Canonical Example |
|---|---|---|---|
| **Receptor Blockade** | `FUD-RB` | Autoantibodies or cross-reactive antibodies block the receptor required for analyte uptake by the target tissue. | Folate receptor autoantibodies (FRAs) blocking folate transport across the blood-brain barrier; ~75% prevalence in autism spectrum disorder. |
| **Competitive Displacement** | `FUD-CD` | A synthetic analog, structural mimic, or pharmacological agent binds the receptor/transporter with higher affinity than the biologically active form, preventing functional uptake. | Folic acid binding folate receptors ~7.5× more strongly than 5-MTHF; perchlorate/thiocyanate/nitrate blocking the sodium-iodide symporter; mercury-selenium binding. |
| **Transport Impairment** | `FUD-TI` | The transport infrastructure (carrier proteins, channel proteins, active transport mechanisms, barrier-crossing pathways) is degraded, saturated, cofactor-depleted, or genetically impaired. | Low vitamin D reducing backup folate transport (RFC1) pathway capacity; AVED (α-tocopherol transfer protein mutations) preventing vitamin E tissue retention; elevated SHBG/CBG reducing bioavailable testosterone/cortisol. |
| **Enzymatic Conversion Failure** | `FUD-EC` | The enzyme(s) required to convert the circulating form to the biologically active form are overwhelmed, polymorphically slow, inhibited, or cofactor-depleted. | DHFR saturation at >200 µg folic acid; impaired deiodinase-mediated T4→T3 conversion (selenium-dependent); delta-6 desaturase polymorphisms impairing ALA→EPA conversion; IDO/TDO upregulation shunting tryptophan to kynurenine pathway. |
| **Cofactor Depletion** | `FUD-CF` | A required cofactor for the analyte's biological activity is itself deficient, rendering the primary analyte functionally inert despite adequate serum levels. | Selenium required for T4→T3 (deiodinase); copper required for iron mobilization (ceruloplasmin ferroxidase); magnesium required for thiamine activation (thiamine pyrophosphokinase); BH4 required for tyrosine→dopamine (tyrosine hydroxylase); riboflavin required for MTHFR activity (folate cycle); zinc required for RBP synthesis (vitamin A mobilization). |
| **Molecular Mimicry Trigger** | `FUD-MM` | A dietary or environmental antigen structurally mimics the receptor or the analyte, triggering immune cross-reactivity that degrades transport or utilization. | Dairy protein (casein) structural mimicry of folate receptor alpha (FRα) — 91% amino acid homology — triggering FRA production. |
| **Compartmental Trapping** | `FUD-CT` | The analyte accumulates in the vascular compartment or an intermediate compartment because the efflux/uptake mechanism into the target compartment is impaired, producing artificially "normal" or elevated serum readings. Also covers the inverse: serum appears adequate because it reflects intermediate storage, not target-tissue levels. | Normal serum folate with critically low CSF folate (cerebral folate deficiency); normal serum magnesium maintained by bone mobilization despite tissue depletion; normal serum retinol maintained by liver stores until near-exhaustion; normal total testosterone with low free testosterone due to SHBG trapping. |
| **Gut-Barrier Dysfunction** | `FUD-GB` | Gut inflammation, dysbiosis, or structural damage impairs absorption of the dietary form, and/or gut organisms consume the analyte before host absorption. The analyte may still be present in bloodstream via supplementation or fortification, masking the functional deficit. | Celiac impairing folate/iron absorption; SIBO consuming B12; phytate chelating zinc in the gut lumen; PPI-induced achlorhydria impairing magnesium, B12, and iron absorption. |
| **Inflammatory Redistribution** | `FUD-IR` | Acute phase response or chronic inflammation systematically distorts serum levels — sequestering some analytes (making them look adequate or high when tissue delivery is impaired) and suppressing carriers of others (making them look deficient when tissue status is adequate). | Hepcidin-mediated iron sequestration in macrophages (high ferritin, low tissue iron delivery); inflammation-driven zinc redistribution to liver (low serum zinc, adequate tissue zinc); CRP-mediated depression of retinol-binding protein (low serum vitamin A, adequate liver stores). |

**New in v2.0:** `FUD-IR` (Inflammatory Redistribution) added as a ninth mechanism class, recognizing that inflammation is the single most common confounder across all analytes and frequently produces both FUD and iFUD simultaneously for different analytes in the same patient.

A single patient may exhibit **multiple simultaneous FUD mechanisms** for the same analyte (e.g., FUD-RB + FUD-CD + FUD-TI for folate) or different mechanisms across different analytes. FUD-CF frequently produces **cascading discordance chains** (e.g., selenium deficiency → FUD-CF for thyroid → impaired T4→T3 → functional hypothyroidism despite normal TSH/T4).

---

## **Two-Layer Detection Architecture**

### **Why Two Layers**

FUDD v1.0 relied entirely on curated FUD signatures in the MKE registry. This created a critical limitation: **FUDD could only detect what had already been characterized and loaded**. If cerebral folate deficiency wasn't in the registry, FUDD would miss it entirely. Many functional deficiency patterns are fragmented across the literature, poorly indexed, or not yet named as a unified phenomenon. A pure signature-matching engine cannot discover what it hasn't been told to look for.

The two-layer architecture separates **recognition of known patterns** (Layer 1) from **detection of anomalous serum-function disconnects** (Layer 2), ensuring FUDD can flag novel discordances even before a formal signature exists.

### **Layer 1 — Signature-Matched Detection (Curated, High Confidence)**

**What it does:** For each FUD-eligible analyte with `lab_adequacy_status = within_range`, Layer 1 retrieves the applicable FUD signature set from the MKE registry and evaluates each signature against the patient's data.

**How it works:** Pattern-matching against curated `[analyte × mechanism × indicator constellation]` triples. Each signature specifies: which analyte, which mechanism(s), which indicator signals must converge, what contributing factors increase probability, and what functional assays can confirm.

**Confidence assignment:**
* `high` — ≥3 converging signals including at least one specific functional indicator (e.g., elevated MMA + neurological symptoms + metformin use for B12)
* `moderate` — 2 converging signals or 1 highly specific indicator (e.g., elevated homocysteine alone with adequate serum folate/B12)
* `low` — 1 non-specific signal matching a known signature pattern

**Output:** `fud_flags[]` with `detection_layer = L1`, full mechanism classification, and intervention candidates from the MKE catalog.

**Governance:** L1 detections are eligible for full surfacing (B2C intervention guidance, B2MD with nudge). This is the high-confidence path.

### **Layer 2 — General Discordance Heuristic (Signature-Independent, Exploratory)**

**What it does:** For any analyte with `lab_adequacy_status = within_range` — including analytes that have NO entries in the FUD signature registry — Layer 2 asks a compound structural question: **Does this patient exhibit ≥2 of five discordance indicators despite adequate serum levels?**

**The Five General Discordance Indicators:**

1. **Clinical symptoms consistent with deficiency** of this analyte — mapped via MKE symptom-analyte association tables (which exist for most nutrients, hormones, and cofactors as standard nutritional/endocrine knowledge). The patient presents symptoms that would typically indicate deficiency of analyte X, yet serum X is within range.

2. **Downstream metabolite abnormality** — a metabolite that requires this analyte as substrate, cofactor, or intermediate is abnormal. This is the highest-specificity general indicator because it directly reflects the metabolic consequence of inadequate functional availability (e.g., elevated homocysteine when folate/B12 are "normal"; elevated methylmalonic acid when B12 is "normal"; low T3 when T4 is "normal"; elevated kynurenine-to-tryptophan ratio when tryptophan is "normal").

3. **Trajectory inconsistency** — M6/M13 stability band is deteriorating, drifting, or failing to improve despite "adequate" labs, in a pattern that would be explained by deficiency of this analyte. The patient's clinical trajectory contradicts the lab picture.

4. **Known interfering factor present** — the patient has a condition, medication, genetic variant, dietary exposure, or environmental factor known to impair utilization of this analyte class. This includes but is not limited to: autoimmune conditions, chronic inflammation (elevated CRP/ESR), specific medications (PPIs, metformin, oral contraceptives, anticonvulsants, amiodarone, statins), known genetic polymorphisms (MTHFR, VDR, COMT, MAO, SEPP1, GPX1, FKBP5), dietary patterns (high dairy, high phytate, folic acid fortification exposure, high cruciferous/goitrogen intake), and gut conditions (celiac, SIBO, IBD, post-bariatric).

5. **Response failure** — the patient has been supplemented with this analyte (at adequate dose, for adequate duration) and has not responded as expected. This is a retrospective signal: if a patient takes vitamin D for 12 weeks and their serum level rises but their symptoms don't improve, the problem may be utilization rather than supply.

**Convergence threshold:** ≥2 indicators must converge for an L2 flag to be generated. Any single indicator alone is insufficient (to prevent noise).

**Specificity weighting:** Indicator #2 (downstream metabolite abnormality) counts as 2 points toward the convergence threshold due to its high specificity. A single downstream metabolite abnormality plus any one other indicator meets the threshold.

**Confidence assignment:**
* `exploratory_high` — ≥3 indicators converging, including at least one downstream metabolite abnormality
* `exploratory_moderate` — 2 indicators converging, or downstream metabolite abnormality alone
* `exploratory_low` — 2 non-metabolite indicators converging (symptoms + interfering factor only)

**Output:** `fud_flags[]` with `detection_layer = L2`, mechanism classified as `uncharacterized` or `candidate_mechanism` (if the interfering factor maps to a known mechanism class even without a full signature), and NO intervention candidates from the MKE catalog (since no curated signature exists).

**Governance:** L2 detections are surfaced with distinct constraints:
* **B2MD:** Presented as an **investigative hypothesis** — "The system has identified a potential disconnect between this patient's serum [analyte] and their clinical presentation. No established protocol exists for this specific pattern. Consider evaluating with [recommended functional assays]." Nudge level is capped at `moderate` regardless of signal convergence. No intervention candidates are auto-populated; the expandable panel shows the converging indicators and suggests functional assays only.
* **B2C:** L2 detections are NOT surfaced directly to patients. Instead, they generate a general guidance note: "Some aspects of your lab results and symptoms may warrant further investigation. Consider discussing [analyte] utilization with your provider." No specific intervention recommendations are made for L2-only detections.
* **Routing to discovery pipeline:** L2 flags are aggregated by M41/M48 (governance and continuous learning) across the patient population. When multiple patients generate L2 flags for the same analyte with similar indicator constellations, this becomes a **candidate signature** for MKE registry curation — feeding Tier C (population-level discovery) without any single module needing to perform that analysis.

### **Layer Interaction and Promotion**

* A detection can begin as L2 (novel pattern, no signature) and later be **promoted to L1** when a corresponding signature is curated and added to the MKE registry. The module logic does not change; only the registry grows.
* If both L1 and L2 fire for the same analyte in the same patient (e.g., L1 matches a known signature and L2 independently confirms via general heuristic), this is recorded as **dual-layer convergence** and treated at L1 confidence — the L2 confirmation strengthens the L1 detection but does not change the output pathway.
* L2 flags that accumulate across the population without eventual L1 promotion are periodically reviewed via M48 (continuous learning governance) to determine whether they represent true novel patterns, noise, or confounders.

### **Inverse Discordance Detection (iFUD)**

Both layers also screen for iFUD — cases where serum levels appear abnormal but tissue status may be adequate. The same five indicators are evaluated, but the logic is inverted:

* **Trigger:** `lab_adequacy_status = below_range` or `above_range` for an analyte known to be affected by inflammatory redistribution, binding protein variability, or homeostatic regulation.
* **iFUD indicators:** (1) clinical presentation inconsistent with the degree of deficiency/excess suggested by labs; (2) inflammatory markers elevated (CRP, ESR, ferritin as acute phase reactant); (3) known binding protein confounders (SHBG, CBG, DBP, albumin levels abnormal); (4) functional markers contradicting the serum reading (e.g., serum zinc low but alkaline phosphatase normal; serum vitamin A low but MRDR normal); (5) recent acute illness or surgical stress.
* **Output:** `ifud_flag` with `detection_layer = L1 or L2`, explaining why the abnormal lab may be misleading and recommending confirmatory functional testing before treatment.
* **Governance:** iFUD flags are always B2MD-only (never surfaced to patients as "your labs are wrong") and are framed as "consider whether this abnormal result reflects true deficiency or inflammatory/binding protein confounding before initiating treatment."

---

## **Scope**

### **In scope**

* Detect discordance between serum/plasma adequacy and functional utilization indicators across all supported analyte classes using the two-layer architecture.
* Detect **inverse discordance** (iFUD) where abnormal serum levels may not reflect true tissue-level status.
* Classify detected discordances by mechanism (FUD-RB, FUD-CD, FUD-TI, FUD-EC, FUD-CF, FUD-MM, FUD-CT, FUD-GB, FUD-IR) using Layer 1 signature matching and Layer 2 general heuristic.
* Identify **cascading discordance chains** where one FUD produces a downstream FUD in a dependent analyte (e.g., selenium FUD → thyroid FUD-CF; riboflavin FUD → folate FUD-EC via MTHFR; zinc FUD → vitamin A FUD-TI via RBP).
* Generate **FUD Flags** with detection layer, confidence level, mechanism classification, evidence pointers, and contributing factors.
* Produce **role-differentiated output payloads** with distinct governance for L1 vs L2 detections:
  * **B2C payload**: patient-facing intervention guidance for L1 detections; general guidance-only for L2 detections.
  * **B2MD payload**: full intervention candidates for L1 detections; investigative hypothesis framing for L2 detections.
* Attach known mechanism context via **MKE reference hooks** (pointers to evidence, not embedded knowledge).
* Feed **population-level discovery pipeline** via M41/M48 with aggregated L2 flags for candidate signature identification.
* Emit audit-grade records for every detection, non-detection, and surfacing decision, distinguishing L1 from L2.
* Support an **extensibility framework** for adding new analyte-discordance signatures over time without altering the module contract.

### **Out of scope**

* Diagnosing specific conditions (e.g., "this patient has cerebral folate deficiency"). FUDD detects and flags the discordance pattern; diagnostic confirmation remains with M49/clinician workflows.
* Executing interventions or activating treatment plans. FUDD surfaces candidates; M16/M19 govern activation.
* Embedding medical knowledge (disease facts, guideline text, drug interactions, reference ranges). All clinical knowledge is referenced via MKE hooks.
* Overriding M7A lab validation. If M7A marks a lab as valid and within range, FUDD does not dispute the lab value — it interrogates whether "within range" equals "functionally adequate."
* Replacing existing specialty testing logic. FUDD flags the need for functional assays; it does not interpret those specialty tests.
* Population-level pattern mining (owned by M41/M48). FUDD feeds L2 flags into the discovery pipeline; it does not run cohort-level statistical analysis.

---

## **Inputs**

### **From M7A (validated lab data)**

* `validated_labs[]` — analyte, value, unit, reference_range, timestamp, source, QA_flags.
* `lab_adequacy_status` per analyte — `within_range | below_range | above_range`.
* `inflammatory_markers[]` — CRP, ESR, ferritin (flagged as acute phase reactant when relevant), albumin, prealbumin — required for iFUD and FUD-IR detection.

### **From M4/M5/M12 (clinical presentation and narrative)**

* `normalized_tags[]` — symptom tags with severity, duration, trajectory.
* `PSI` — Psychosomatic Index (to distinguish functional deficiency symptoms from psychosomatic overlay).
* `narrative_digest` — patient-reported symptoms, progression context.
* `medication_list[]` — current and recent medications (required for interfering factor detection).
* `supplement_list[]` — current supplementation (required for response failure detection and folic acid exposure assessment).
* `dietary_pattern_tags[]` — if available (dairy consumption, vegetarian/vegan status, fortified food reliance).

### **From M6/M13 (stability and trajectory)**

* `stabilityBand`, `drift`, `trajectory_features` — to detect whether a patient's trajectory is inconsistent with their "adequate" lab picture.
* `treatment_response_history[]` — prior supplementation attempts and outcomes (required for Layer 2 response failure indicator).

### **From MKE (via reference hooks, not embedded)**

* `fud_signature_registry_ref` — pointer to the MKE-maintained registry of known FUD signatures (analyte × mechanism × indicator pattern). Used by Layer 1.
* `fud_intervention_catalog_ref` — pointer to the MKE-maintained catalog of evidence-based interventions for each FUD mechanism class. Used by Layer 1 Stage 3.
* `fud_contributing_factor_ref` — pointer to known contributing factors (medications, genetic variants, dietary exposures, conditions). Used by both layers.
* `symptom_analyte_association_ref` — pointer to MKE-maintained mappings of symptoms to analyte deficiency profiles. Used by Layer 2 indicator #1.
* `metabolite_substrate_map_ref` — pointer to MKE-maintained mappings of downstream metabolites to their required substrates/cofactors. Used by Layer 2 indicator #2.
* `cofactor_dependency_graph_ref` — pointer to MKE-maintained graph of which analytes depend on which cofactors for biological activity. Used for cascading chain detection.

### **From V6 Tool Library (M51–M53)**

* Tool outputs relevant to functional status (e.g., diagnostic scores, phenotypers) with trust/use-class metadata.

### **From M53 (PTM, when available)**

* `condition_probability_landscape` — to assess whether FUD detection aligns with or explains probabilistic terrain signals.

### **Configuration / Policy**

* `fud_detection_sensitivity` — policy-tunable sensitivity threshold (conservative/standard/aggressive), applied independently to L1 and L2.
* `l2_enabled` — boolean, allowing sites/tenants to disable Layer 2 if desired (default: enabled).
* `ifud_enabled` — boolean, allowing sites/tenants to disable inverse discordance detection (default: enabled).
* `role_context` — B2C vs B2MD, governing which output payload is generated.
* `patient_age` — relevant for age-gated detection logic (e.g., pediatric folate-specific patterns).
* `known_dietary_exposures[]` — if available from intake/journaling (dairy consumption, fortified food consumption, supplement list).
* `genetic_variant_flags[]` — if available from prior testing (MTHFR, VDR, COMT, SEPP1, etc.).

---

## **Outputs**

### **1) FUD Flag (core detection output)**

A structured flag per detected discordance. **Minimum required fields**:

* `fud_flag_id` (UUID)
* `patient_id`
* `detection_layer` (`L1` | `L2`) — **new in v2.0**
* `detection_type` (`FUD` | `iFUD`) — **new in v2.0**
* `analyte` (coded: LOINC where applicable)
* `serum_status` (`within_range` | `below_range` | `above_range` with value and reference range)
* `functional_status` (`suspected_impaired` | `confirmed_impaired` | `indeterminate` | `suspected_adequate_despite_abnormal_serum` for iFUD)
* `mechanism_classes[]` (one or more of: `FUD-RB`, `FUD-CD`, `FUD-TI`, `FUD-EC`, `FUD-CF`, `FUD-MM`, `FUD-CT`, `FUD-GB`, `FUD-IR`, or `uncharacterized` for L2 without mechanism match)
* `confidence` — L1: `low` | `moderate` | `high`; L2: `exploratory_low` | `exploratory_moderate` | `exploratory_high`
* `converging_indicators[]` — **new in v2.0** — explicit list of which indicators fired (L2) or which signature elements matched (L1), with evidence pointers per indicator
* `contributing_factors[]` (known factors present for this patient)
* `cascade_chain[]` — **new in v2.0** — if this FUD is part of a cascading chain, pointers to upstream/downstream FUD flags (e.g., selenium FUD → thyroid FUD-CF)
* `recommended_functional_assays[]` (tests that could confirm or rule out the discordance)
* `fud_detection_version` (module version + signature registry version)
* `timestamp`

### **2) B2C Payload (patient-facing)**

Routed through M14 (patient-facing narratives) and M24 (interface hub).

**For L1 detections:**
* `patient_summary` — plain-language explanation of the discordance: what was found, why it matters, what can be done. No medical jargon. No diagnosis claims. Framed as actionable guidance.
* `intervention_recommendations[]` — each with:
  * `action` (e.g., "Eliminate folic acid from supplements and fortified foods", "Remove dairy for a minimum 8-week trial")
  * `priority` (`immediate` | `short_term` | `monitoring`)
  * `rationale_plain` (one-sentence plain-language reason)
  * `evidence_strength` (`strong` | `moderate` | `emerging`)
* `monitoring_guidance` — what improvements to watch for and over what timeline.
* `escalation_prompt` — when to involve a practitioner.

**For L2 detections:**
* `general_guidance_note` — "Some aspects of your lab results and symptoms may warrant further investigation. Consider discussing [analyte category] with your provider." No specific interventions. No mechanism details. Framed as a prompt to seek professional evaluation, not as a recommendation to self-treat.

**For iFUD detections:**
* Not surfaced to B2C. Patient does not receive "your abnormal lab may be wrong" messaging.

### **3) B2MD Payload (clinician-facing)**

Routed through M16 (Execution Governance), M19 (clinician review), and M24 (interface hub).

**For L1 detections:**
* `clinician_flag` — concise clinical summary of the detected discordance, mechanism classification, and confidence level. Visible as a **persistent flag/badge** on the patient dashboard.
* `expandable_mechanism_panel` — togglable detail panel containing:
  * Mechanism classification with evidence strength per mechanism.
  * Specific contributing factors identified for this patient.
  * Cascading chain visualization (if applicable).
  * Relevant literature references (via MKE pointers, not embedded text).
  * Differential: what else could explain the pattern (non-FUD explanations).
* `intervention_candidates[]` — presented as a **selectable list** (not auto-selected), each with:
  * `intervention` (structured: dietary modification, supplementation change, functional assay order, referral)
  * `status` = `proposal` (per M16 governance; nothing activates without clinician confirmation)
  * `evidence_grade` (`strong` | `moderate` | `emerging` | `expert_opinion`)
  * `mechanism_targeted` (which FUD mechanism class this intervention addresses)
  * `expected_timeline` (when response would be expected if this is the correct mechanism)
  * `monitoring_parameters` (what to track to assess response)
* `nudge_flag` — severity indicator:
  * `high` nudge: L1, multiple converging signals, high confidence, known high-prevalence mechanism → active notification.
  * `moderate` nudge: L1, partial convergence → visible flag, expandable on click.
  * `low` nudge: L1, single weak signal → annotation in patient record.

**For L2 detections:**
* `clinician_flag` — framed as investigative hypothesis: "Potential functional utilization discordance detected for [analyte]. No established signature matches this pattern. [N] of 5 general indicators are converging."
* `expandable_indicator_panel` — togglable detail showing which of the five general indicators fired, with evidence per indicator.
* `recommended_functional_assays[]` — tests that could confirm or refute the discordance.
* **No intervention candidates** are auto-populated for L2 detections. The clinician decides how to investigate.
* `nudge_flag` capped at `moderate` regardless of signal strength.

**For iFUD detections:**
* `clinician_advisory` — "This abnormal [analyte] result may be confounded by [inflammation / binding protein abnormality / acute phase response]. Consider verifying with [functional assay] before initiating treatment."
* `expandable_confounding_panel` — shows the specific confounders detected and literature references.
* `nudge_flag` = `moderate` (always — to prevent unnecessary treatment but not to alarm).

### **4) Audit artifacts**

* `FUDDetectionEvent` — for every detection cycle (including "no discordance found"), log: patient_id, analytes evaluated, detection_layers_run (L1/L2/both), signatures checked (L1), indicators evaluated (L2), flags generated or not, confidence levels, evidence pointers, role_context, payload type emitted, module + registry versions.
* `FUDSurfacingEvent` — for every surfacing action: which payload was generated, which role received it, which interventions were included, nudge level, detection_layer.
* `L2AggregationEvent` — **new in v2.0** — periodic summary of L2 flags routed to M41/M48 for population-level pattern analysis.
* `AuditEvent` + `Provenance` per FHIR conventions (referenced via Appendix C.11).

---

## **Process / Logic (deterministic stages)**

### **Stage 0 — Trigger Evaluation**

Determine whether a FUD detection cycle should run.

* **Triggers:**
  * New lab results ingested where `lab_adequacy_status = within_range` for any analyte (L1 + L2 eligible).
  * New lab results where `lab_adequacy_status = below_range | above_range` for iFUD-eligible analytes (iFUD trigger).
  * Clinical presentation signals (symptoms, trajectory drift, stability band changes) that pattern-match against known FUD presentation profiles (L1) or that suggest unexplained clinical-lab divergence (L2).
  * PTM probability shifts toward conditions known to involve FUD mechanisms.
  * New medication or supplement added to patient record (interfering factor change).
  * Periodic re-evaluation on schedule (policy-defined cadence).
  * Clinician or patient request for FUD evaluation.

* **Output:** `run_fud_cycle = true | false` with trigger_type, reason, and layers_to_run (L1/L2/iFUD).

### **Stage 1A — Layer 1: Signature-Matched Discordance Screen**

For each FUD-eligible analyte with `lab_adequacy_status = within_range`:

1. **Retrieve the applicable FUD signature set** from `fud_signature_registry_ref` (MKE pointer) for this analyte.
2. **Evaluate each signature** against available patient data:
   * Does the patient exhibit clinical symptoms specified by the signature?
   * Are downstream metabolite markers available and abnormal as specified?
   * Are contributing factors specified by the signature present?
   * Are trajectory/stability signals inconsistent with the "adequate" lab picture?
3. **Score discordance likelihood** per analyte:
   * Count converging signature elements.
   * Weight by specificity of each element.
   * Assign confidence: `high` (≥3 converging including ≥1 specific), `moderate` (2 converging or 1 highly specific), `low` (1 non-specific match).
4. **Apply sensitivity policy**: filter by `fud_detection_sensitivity` threshold.

* **Output:** List of `l1_candidate_discordances[]` with analyte, confidence, evidence pointers, and matched signature ID.

### **Stage 1B — Layer 2: General Discordance Heuristic**

For each analyte with `lab_adequacy_status = within_range` — **including analytes with no L1 signature**:

1. **Evaluate each of the five general discordance indicators:**
   * **Indicator 1 — Symptom-analyte mismatch:** Query `symptom_analyte_association_ref` for the patient's normalized symptom tags. Does the patient present ≥2 symptoms associated with deficiency of this analyte?
   * **Indicator 2 — Downstream metabolite abnormality:** Query `metabolite_substrate_map_ref` for metabolites downstream of this analyte. Is any downstream metabolite abnormal? (Counts as 2 points toward convergence threshold.)
   * **Indicator 3 — Trajectory inconsistency:** Is the patient's stability band, drift, or trajectory inconsistent with adequate status of this analyte, per M6/M13 signals?
   * **Indicator 4 — Known interfering factor:** Query `fud_contributing_factor_ref` for the patient's medications, supplements, conditions, genetic variants, and dietary patterns. Is any known interfering factor present for this analyte?
   * **Indicator 5 — Response failure:** Does `treatment_response_history[]` show that the patient was supplemented with this analyte at adequate dose for adequate duration without expected clinical response?

2. **Apply convergence threshold:** ≥2 indicator points required (with Indicator 2 counting as 2 points).

3. **Assign confidence:** `exploratory_high` (≥3 indicators including metabolite abnormality), `exploratory_moderate` (2 indicators or metabolite alone), `exploratory_low` (2 non-metabolite indicators).

4. **Attempt mechanism inference:** If the interfering factor (Indicator 4) maps to a known mechanism class (e.g., PPI use → FUD-GB; MTHFR variant → FUD-EC; chronic inflammation → FUD-IR), assign `candidate_mechanism`. Otherwise, assign `uncharacterized`.

* **Output:** List of `l2_candidate_discordances[]` with analyte, confidence, converging indicators with evidence, and candidate mechanism.

### **Stage 1C — Inverse Discordance Screen (iFUD)**

For each analyte with `lab_adequacy_status = below_range | above_range`:

1. **Check iFUD eligibility:** Is this analyte known to be affected by acute phase response, binding protein variability, or homeostatic redistribution? (From MKE registry.)
2. **Evaluate iFUD indicators:** (1) Clinical presentation inconsistent with lab severity; (2) inflammatory markers elevated; (3) binding protein confounders present; (4) functional markers contradicting serum; (5) recent acute illness/stress.
3. **Apply convergence threshold:** ≥2 indicators.
4. **Assign confidence:** Same schema as L2.

* **Output:** List of `ifud_candidates[]` with analyte, confounders, and recommended confirmatory assays.

### **Stage 1D — Cascading Chain Detection**

**New in v2.0.** After L1 and L2 complete:

1. **Query `cofactor_dependency_graph_ref`** to identify whether any detected FUD analyte serves as a cofactor for another analyte in the patient's lab panel.
2. **If cofactor chain exists:** Check whether the dependent analyte also shows FUD indicators (even if below the standalone threshold). If so, link the flags as a cascading chain.
3. **Generate `cascade_chain[]` pointers** on all linked FUD flags.

Example: Patient has L1 detection for selenium FUD-GB (PPI-impaired absorption) → selenium is cofactor for deiodinase → patient also has normal TSH/T4 but low-normal T3 + fatigue → cascade chain links selenium FUD to thyroid FUD-CF.

* **Output:** Updated FUD flags with cascade_chain pointers where applicable.

### **Stage 2 — Mechanism Classification**

For each candidate discordance (L1 and L2):

1. **L1:** Pattern-match against mechanism profiles in the signature registry. Assign mechanism class(es).
2. **L2:** Use candidate_mechanism from Stage 1B if available; otherwise mark as `uncharacterized`.
3. **Identify contributing factors** specific to this patient.
4. **Determine recommended functional assays** that could confirm or refute the discordance.
5. **Flag multi-mechanism cases** where more than one mechanism class applies.

* **Output:** Classified `fud_flags[]` with full mechanism context and detection_layer.

### **Stage 3 — Intervention Candidate Assembly**

**L1 detections only.** L2 detections skip this stage (no curated interventions exist for uncharacterized patterns).

For each classified L1 FUD flag:

1. **Retrieve intervention candidates** from `fud_intervention_catalog_ref` matched to the detected mechanism class(es).
2. **Filter by patient context**: age, known allergies/intolerances, current medications, dietary restrictions, existing care plan.
3. **Tier interventions** by:
   * `immediate` — dietary eliminations and supplement changes the patient can act on without a prescription.
   * `short_term` — functional assay orders and supplementation adjustments requiring clinician involvement.
   * `monitoring` — follow-up testing and timeline-based re-evaluation.
4. **Attach evidence grade** per intervention from MKE references.
5. **Compute expected response timeline** per intervention based on mechanism class.

* **Output:** Tiered `intervention_candidates[]` ready for role-differentiated packaging.

### **Stage 4 — Role-Differentiated Payload Generation**

Based on `role_context` and `detection_layer`:

**If B2C:**

* **L1 detections:**
  1. Generate `patient_summary` using M14-compatible plain-language templates.
  2. Package `intervention_recommendations[]` with plain-language rationales.
  3. Include `monitoring_guidance` and `escalation_prompt`.
  4. Route to M14 and M24.
* **L2 detections:**
  1. Generate `general_guidance_note` only. No specific interventions.
  2. Route to M14 and M24 with `exploratory` flag.
* **iFUD detections:** Not surfaced to B2C.

**If B2MD:**

* **L1 detections:**
  1. Generate `clinician_flag` with concise clinical summary.
  2. Assemble `expandable_mechanism_panel` with full classification, cascade chains, evidence, and differential.
  3. Package `intervention_candidates[]` with `status=proposal`.
  4. Compute `nudge_flag` level.
  5. Route to M16, M19, M24.
* **L2 detections:**
  1. Generate `clinician_flag` as investigative hypothesis.
  2. Assemble `expandable_indicator_panel` showing which general indicators fired.
  3. Include `recommended_functional_assays[]` only. No intervention candidates.
  4. Cap `nudge_flag` at `moderate`.
  5. Route to M19 and M24 (not M16 — no interventions to govern).
* **iFUD detections:**
  1. Generate `clinician_advisory` with confounding explanation.
  2. Assemble `expandable_confounding_panel`.
  3. Set `nudge_flag` = `moderate`.
  4. Route to M19 and M24.

**If both B2C and B2MD apply:**

1. Generate both payloads per detection_layer rules above.
2. Ensure **coherence**: B2C must not exceed B2MD. L2 and iFUD content is clinician-only regardless.
3. Post clinician review, B2C payload can be updated to reflect clinician-approved actions.

### **Stage 5 — Audit and Discovery Pipeline Feed**

1. Emit `FUDDetectionEvent` for every detection cycle.
2. Emit `FUDSurfacingEvent` for every payload generated.
3. Emit `AuditEvent` + `Provenance` per Appendix C.11.
4. Version-pin: attach `fud_detection_version` (module version + signature registry version) to all outputs.
5. **New in v2.0:** Emit `L2AggregationEvent` to M41/M48, carrying anonymized L2 flag summaries (analyte, indicator constellation, candidate mechanism) for population-level pattern analysis and candidate signature identification.

---

## **Constraints / Governance**

* **No diagnosis claims:** FUDD detects discordance patterns and surfaces them with mechanism hypotheses. It does not diagnose. Diagnostic confirmation remains with M49, specialty testing, and clinician judgment.
* **No autonomous intervention activation:** All intervention candidates are surfaced as `status=proposal`. In B2MD mode, nothing activates without explicit clinician confirmation via M19. In B2C mode, only L1 detections surface interventions, and only dietary modifications and supplement changes within the "patient-actionable without prescription" boundary.
* **Layer 2 governance is conservative:** L2 detections are investigative hypotheses, not clinical recommendations. They are never surfaced to patients with specific intervention guidance. They are always nudge-capped at `moderate` for clinicians. They carry no intervention candidates from the MKE catalog.
* **iFUD is clinician-only:** Inverse discordance flags are never surfaced to patients. They exist to prevent unnecessary treatment of falsely abnormal labs.
* **MKE boundary respected:** FUDD does not embed disease facts, reference ranges, guideline text, drug interactions, or clinical knowledge. All clinical content is referenced via MKE pointer hooks. The module owns detection logic, classification taxonomy, heuristic structure, and routing — not the medical knowledge.
* **No override of M7A:** FUDD does not challenge or re-interpret lab values. It interrogates whether "within range" equals "functionally adequate" and whether "out of range" always equals "truly abnormal."
* **Extensibility without contract change:** New analytes, signatures, and mechanism profiles are added to MKE registries. New general indicators or heuristic refinements may be added to L2 via module version updates, but the five-indicator framework is the stable contract.
* **Coherence between B2C and B2MD:** Unchanged from v1.0.
* **Suppression-aware:** Unchanged from v1.0. FUD flags are annotated, not deleted, during suppression.
* **Pediatric sensitivity:** Unchanged from v1.0, extended to L2 (lower convergence threshold for analytes with known pediatric FUD prevalence).
* **Auditability required:** Every detection cycle, every layer, every flag, every surfacing decision — including "no discordance found" — must produce an audit record with detection_layer clearly marked.
* **Discovery pipeline is passive:** FUDD feeds L2 aggregation data to M41/M48 but does not itself perform population-level analysis, determine statistical significance, or decide when a pattern becomes a curated signature.
* **No V5.2 modification:** FUDD is V6-only.

---

## **Dependencies**

### **Upstream (feeds FUDD)**

* **M7A** — Validated lab data with adequacy status and inflammatory markers.
* **M4/M5** — Normalized symptom tags, PSI, persona flags, medication list, supplement list, dietary patterns.
* **M12** — Narrative digest, harmonized labs.
* **M6/M13** — Stability band, trajectory features, risk indices, treatment response history.
* **M53 (PTM)** — Condition probability landscape (when available).
* **V6 Tool Library (M51–M52)** — Relevant tool outputs with trust metadata.
* **MKE** — FUD signature registry, intervention catalog, contributing factor registry, symptom-analyte associations, metabolite-substrate maps, cofactor dependency graph (all via reference hooks).

### **Downstream (consumes FUDD)**

* **M14** — Receives B2C patient-facing payloads for narrative generation.
* **M16** — Receives B2MD L1 intervention candidates as draft proposals.
* **M19** — Receives B2MD detection flags (L1 and L2) and iFUD advisories for clinician review queue.
* **M24** — Receives all UI payloads including expandable panels and nudge levels.
* **M17 (CIR)** — FUD flags (L1 and L2) serve as node/edge inputs for causal graph construction; cascade chains provide pre-computed causal links.
* **M18 (MPA)** — FUD flags modulate pathway probabilities.
* **M53 (PTM)** — FUD flags inform the probabilistic terrain.
* **M41/M48** — L2 aggregation events feed population-level discovery pipeline; all audit artifacts route to governance.
* **Vault (M21)** — FUD detection history persisted longitudinally for trend analysis and response tracking.

---

## **Analyte Coverage: Comprehensive Map**

### **Tier 1 — Initial Release (best-characterized FUD patterns, Layer 1 signatures available)**

| Analyte | Primary FUD Mechanisms | Key Functional Indicators | Canonical Functional Test(s) | Key Interfering Factors |
|---|---|---|---|---|
| **Folate** | FUD-RB, FUD-CD, FUD-TI, FUD-EC, FUD-MM, FUD-CT | Elevated homocysteine; low CSF 5-MTHF; neurodevelopmental symptoms; UMFA presence | FRAT; CSF folate; homocysteine; RBC folate | Folic acid fortification/supplements; dairy (FRA trigger); low vitamin D; low glutathione; MTHFR variants |
| **Vitamin B12** | FUD-EC, FUD-CF, FUD-GB, FUD-CT | Elevated MMA; elevated homocysteine; neurological symptoms; low holoTC | MMA; homocysteine; holotranscobalamin | Metformin; PPIs/H2 blockers; nitrous oxide exposure; pernicious anemia; SIBO; vegan/vegetarian diet |
| **Iron** | FUD-TI, FUD-CF, FUD-CT, FUD-GB, FUD-IR | Low reticulocyte Hb; elevated sTfR; anemia symptoms; high ferritin + low TSAT | sTfR; sTfR/log ferritin index; reticulocyte Hb; hepcidin | Chronic inflammation (CRP>5); CKD; CHF; rheumatologic disease; cancer; heavy menstruation + NSAID use |
| **Vitamin D** | FUD-EC, FUD-CF, FUD-TI, FUD-CT | Elevated PTH despite adequate 25-OH-D; low 1,25(OH)₂D; bone/immune symptoms; inadequate free 25-OH-D | 1,25-dihydroxy-D; PTH; free 25-OH-D; VDR polymorphisms | CKD (FGF23-mediated); obesity (adipose sequestration); VDR polymorphisms; DBP genetic variants; liver disease |
| **Thyroid (T4→T3)** | FUD-EC, FUD-CF, FUD-CD | Normal TSH/T4 but low free T3; elevated rT3; hypothyroid symptoms | Free T3; reverse T3; T3/rT3 ratio; selenium; thyroid antibodies | Selenium deficiency; chronic stress (cortisol); illness (NTIS); amiodarone; beta-blockers; glucocorticoids; gut dysbiosis |

### **Tier 2 — Near-Term Extension (strong evidence, Layer 1 signatures to be curated)**

| Analyte | Primary FUD Mechanisms | Key Functional Indicators | Canonical Functional Test(s) | Key Interfering Factors |
|---|---|---|---|---|
| **Magnesium** | FUD-CT, FUD-TI, FUD-GB | Normal serum Mg but symptoms (cramps, arrhythmia, migraine, anxiety); low RBC Mg; refractory hypokalemia/hypocalcemia | RBC magnesium; ionized Mg; 24h urine Mg; Mg loading test | PPIs; loop/thiazide diuretics; alcohol; diabetes (renal wasting); high-dose calcium supplementation |
| **Zinc** | FUD-CD, FUD-GB, FUD-IR, FUD-CT | Low alkaline phosphatase; impaired taste/smell; poor wound healing; immune dysfunction; low serum zinc during inflammation despite adequate stores | Erythrocyte zinc; alkaline phosphatase; lymphocyte zinc; functional taste/smell testing | Phytate-rich diet; copper supplementation (competitive); chronic inflammation; oral contraceptives; ACE inhibitors |
| **Copper** | FUD-CF (as cofactor for iron), FUD-TI, FUD-GB | Iron-refractory anemia; neutropenia; osteoporosis; low ceruloplasmin activity despite normal serum copper | Ceruloplasmin ferroxidase activity; erythrocyte SOD | Excess zinc supplementation; gastric bypass; prolonged enteral nutrition; Menkes disease variants |
| **Selenium** | FUD-CF (for thyroid/GPx), FUD-CD, FUD-GB | Impaired thyroid conversion (low T3); low GPx activity; cardiomyopathy; immune dysfunction | GPx activity; selenoprotein P; plasma selenium + GPx correlation | Mercury exposure; geographic low-selenium soil; celiac/IBD; TPN; SEPP1/GPX1 polymorphisms |
| **Vitamin B6** | FUD-CD, FUD-IR, FUD-EC | Low EAST activity despite normal plasma PLP; neurological symptoms; elevated xanthurenic acid | EAST activation coefficient; plasma 4-pyridoxic acid; xanthurenic acid after tryptophan load | Oral contraceptives; isoniazid; penicillamine; theophylline; chronic alcohol; inflammation (PLP redistribution) |
| **Vitamin B1 (Thiamine)** | FUD-CF, FUD-GB, FUD-EC | Lactic acidosis; Wernicke's symptoms; low erythrocyte transketolase activity | Erythrocyte transketolase + TPP effect; whole blood thiamine diphosphate | Alcohol; bariatric surgery; hyperemesis; refeeding; loop diuretics; magnesium deficiency (cofactor for activation) |
| **Riboflavin (B2)** | FUD-CF (for MTHFR/folate cycle), FUD-EC | Elevated EGRAC; angular stomatitis; impaired MTHFR activity in MTHFR C677T homozygotes | EGRAC activation coefficient; urinary riboflavin | Hypothyroidism (impairs conversion); oral contraceptives; alcohol; boric acid exposure; MTHFR C677T (increased demand) |
| **Iodine** | FUD-CD, FUD-TI | Goiter/hypothyroid symptoms despite adequate urinary iodine; impaired NIS transport | Thyroglobulin; NIS function (indirect via uptake studies); perchlorate discharge test | Perchlorate; thiocyanate (smoking, cruciferous excess); nitrate; lithium; amiodarone |

### **Tier 3 — Hormones & Binding Protein Discordance**

| Analyte | Primary FUD Mechanisms | Key Functional Indicators | Canonical Functional Test(s) | Key Interfering Factors |
|---|---|---|---|---|
| **Testosterone** | FUD-CT (SHBG trapping), FUD-TI | Hypogonadal symptoms despite normal total testosterone; low calculated free testosterone | Free testosterone (equilibrium dialysis); bioavailable testosterone; SHBG | Aging; obesity; hyperthyroidism; liver disease; anticonvulsants; estrogen therapy |
| **Cortisol** | FUD-CT (CBG trapping), FUD-TI | Adrenal insufficiency symptoms despite normal total cortisol; low free cortisol | Salivary cortisol; urinary free cortisol; CBG levels | Estrogen/OCP use (elevates CBG); critical illness (CBG cleaved by neutrophil elastase); nephrotic syndrome (CBG loss) |
| **Estrogen** | FUD-CT (SHBG trapping), FUD-EC | Estrogen deficiency/excess symptoms despite normal serum estradiol; abnormal estrogen metabolite ratios | Free estradiol; 2-OHE1:16α-OHE1 ratio; SHBG | Obesity (aromatase excess); liver disease; COMT polymorphisms (impaired metabolite clearance); gut dysbiosis (beta-glucuronidase reactivating excreted estrogen) |

### **Tier 4 — Fat-Soluble Vitamins, Fatty Acids, Amino Acids**

| Analyte | Primary FUD Mechanisms | Key Functional Indicators | Canonical Functional Test(s) | Key Interfering Factors |
|---|---|---|---|---|
| **Vitamin A** | FUD-CT (liver homeostatic masking), FUD-TI, FUD-CF | Normal serum retinol with depleted liver stores; night vision impairment; immune dysfunction; low RBP | MRDR test; retinyl ester/retinol ratio post-dose; RBP + prealbumin | Zinc deficiency (RBP synthesis requires zinc); liver disease; fat malabsorption; chronic inflammation (RBP is negative acute phase) |
| **Vitamin E** | FUD-TI, FUD-CT | Ataxia, peripheral neuropathy despite supplementation; low lipid-adjusted vitamin E; elevated F2-isoprostanes | Lipid-adjusted α-tocopherol; F2-isoprostanes (oxidative stress marker) | α-TTP mutations (AVED); fat malabsorption; abetalipoproteinemia; cholestyramine; orlistat |
| **Vitamin K** | FUD-EC, FUD-CD, FUD-CT | Elevated ucOC (bone); elevated PIVKA-II (liver); osteoporosis despite adequate K1 intake | Undercarboxylated osteocalcin; PIVKA-II; K1/K2 ratio | Warfarin/NOACs; broad-spectrum antibiotics (destroy K2-producing gut bacteria); fat malabsorption; VKORC1 polymorphisms |
| **Omega-3 (EPA/DHA)** | FUD-CT, FUD-EC | Low Omega-3 Index despite supplementation; persistent inflammation; cognitive symptoms | Omega-3 Index (RBC EPA+DHA %); EPA/AA ratio | Delta-6 desaturase polymorphisms (FADS1/FADS2); high omega-6 intake (competitive conversion); oxidized fish oil supplements; statin interaction |
| **Tryptophan→Serotonin** | FUD-EC (IDO/TDO shunting), FUD-CF | Adequate serum tryptophan but depression/anxiety/insomnia; elevated kynurenine; low 5-HIAA | Kynurenine/tryptophan ratio; urinary 5-HIAA; serotonin metabolites | Chronic inflammation (IFN-γ upregulates IDO); BH4 depletion; vitamin B6 deficiency (cofactor for aromatic amino acid decarboxylase); chronic stress |
| **Tyrosine→Dopamine** | FUD-CF, FUD-EC | Adequate serum tyrosine but motivation/attention/movement symptoms; low HVA | HVA (homovanillic acid); BH4 levels; iron status | BH4 depletion; iron deficiency (cofactor for tyrosine hydroxylase); MAO polymorphisms; COMT polymorphisms; folic acid exposure (BH4 recycling impairment) |

### **Tier 5 — Proteins & Systemic Markers**

| Analyte | Primary FUD Mechanisms | Key Functional Indicators | Canonical Functional Test(s) | Key Interfering Factors |
|---|---|---|---|---|
| **Albumin** | FUD-CT (redistributed), FUD-IR | Low serum albumin in well-nourished patient during acute illness; normal albumin in malnourished patient early in depletion | Prealbumin (shorter half-life); CRP (to contextualize); nitrogen balance; body composition | Critical illness (capillary leak); liver disease (impaired synthesis); nephrotic syndrome (renal loss); burns; volume overload (dilutional) |
| **Glutathione** | FUD-CT, FUD-EC, FUD-CF | Low intracellular GSH despite adequate serum; elevated GSH:GSSG ratio; oxidative stress markers elevated | Erythrocyte GSH; GSH:GSSG ratio; F2-isoprostanes; 8-OHdG | Acetaminophen (dose-dependent depletion); alcohol; chronic illness; aging; heavy metals; glycine/cysteine/glutamate depletion |

### **Extensibility Contract (unchanged)**

Adding a new analyte requires only: (1) a new FUD signature entry in the MKE registry (for L1), (2) mapping of functional indicators to available lab/clinical data streams, (3) intervention catalog entries (for L1), and (4) optionally, symptom-analyte associations, metabolite-substrate mappings, and cofactor dependency graph entries (for L2 and cascade detection). No change to M64 module logic or contract. Analytes without MKE registry entries are still detectable via Layer 2.

---

## **Notable Cascading Discordance Chains**

The following cross-analyte chains represent architecturally significant patterns where one FUD produces or amplifies another. FUDD's cascade detection (Stage 1D) should identify these when co-occurring:

| Chain | Upstream FUD | Mechanism | Downstream FUD | Clinical Significance |
|---|---|---|---|---|
| **Selenium → Thyroid** | Selenium FUD-GB (PPI/malabsorption) | Deiodinase is a selenoprotein | Thyroid FUD-CF (impaired T4→T3) | Unexplained hypothyroid symptoms with normal TSH/T4 in patients on PPIs |
| **Riboflavin → Folate** | Riboflavin FUD-EC | MTHFR requires FAD (riboflavin) cofactor | Folate FUD-EC (impaired 5-MTHF production) | Elevated homocysteine in MTHFR C677T homozygotes that doesn't respond to folate alone |
| **Zinc → Vitamin A** | Zinc FUD-GB (phytate/inflammation) | RBP synthesis requires zinc | Vitamin A FUD-TI (impaired mobilization from liver) | Night vision issues/immune dysfunction in patients with adequate vitamin A intake but high-phytate diets |
| **Copper → Iron** | Copper FUD-GB (gastric bypass/zinc excess) | Ceruloplasmin ferroxidase requires copper | Iron FUD-CF (impaired mobilization from stores) | Iron-refractory anemia post-bariatric surgery despite adequate ferritin |
| **Magnesium → Thiamine** | Magnesium FUD-GB (PPI/diuretics) | Thiamine pyrophosphokinase requires Mg | Thiamine FUD-CF (impaired activation) | Refractory lactic acidosis / Wernicke-like presentation in patients on PPIs + diuretics |
| **Magnesium → Vitamin D** | Magnesium FUD | CYP enzymes activating vitamin D require Mg | Vitamin D FUD-CF (impaired 25-OH-D and 1,25-OH₂D synthesis) | Vitamin D supplementation failure in Mg-depleted patients |
| **Vitamin D → Folate (brain)** | Vitamin D FUD | RFC1 upregulation at BBB requires calcitriol | Folate FUD-TI (impaired brain folate transport) | CFD-like presentation in vitamin D deficient patients |
| **Glutathione → Folate** | Glutathione FUD (acetaminophen/oxidative stress) | ROS damage to FRα and RFC1 proteins | Folate FUD-TI (impaired receptor/transporter function) | Neurodevelopmental regression following oxidative stressor exposure |
| **Folate → BH4 → Neurotransmitters** | Folate FUD (any mechanism) | DHFR recycling of BH2→BH4 is impaired | Tryptophan→serotonin FUD-CF + Tyrosine→dopamine FUD-CF | Depression/attention/movement symptoms in patients with "adequate" folate/B12 + folic acid exposure |
| **Iron → Tyrosine→Dopamine** | Iron FUD (any mechanism) | Tyrosine hydroxylase requires iron | Tyrosine→dopamine FUD-CF | ADHD-like symptoms, restless legs in patients with normal ferritin but functional iron deficiency |
| **Inflammation → Multiple** | Any chronic inflammatory state (FUD-IR) | CRP, hepcidin, IDO, APR collectively distort | Iron FUD-IR + Zinc iFUD + Vitamin A iFUD + Tryptophan FUD-EC | Multi-analyte discordance in chronically ill patients where nearly every lab is uninterpretable at face value |

---

## **Interaction with Cerebral Folate Deficiency (Reference Case)**

*Unchanged from v1.0.* The transcript that motivated this module describes the most extensively documented FUD pattern in the literature. See v1.0 spec for full walkthrough of Stages 1–4 for this case.

**v2.0 additions to this case:**

* **Cascade detection** would identify the Glutathione → Folate chain (low glutathione → ROS damage to FRα → impaired brain folate transport) and the Vitamin D → Folate chain (low vitamin D → reduced RFC1 upregulation → impaired backup folate transport).
* **Layer 2 would independently flag** this patient even if the CFD signature didn't exist in the registry, because the general heuristic would fire: Indicator 1 (neurodevelopmental symptoms consistent with folate deficiency), Indicator 2 (elevated homocysteine = downstream metabolite abnormality, counts as 2 points), Indicator 4 (dairy + folic acid = known interfering factors). That's ≥4 indicator points, producing `exploratory_high` confidence.
* **iFUD would note** that if this patient's ferritin were also tested and elevated (common in ASD due to chronic neuroinflammation), the iFUD screen would flag that the elevated ferritin may reflect acute phase response rather than true iron excess — preventing inappropriate iron restriction.

---

## **Versioning Note**

* **Introduced in V6** as a new EoH module.
* **v2.0** adds two-layer detection architecture, inverse discordance detection, cascading chain detection, FUD-IR mechanism class, expanded analyte coverage, and population-level discovery pipeline feed.
* Does **not** alter V5.2 behavior.
* FUD signature registry, intervention catalog, symptom-analyte associations, metabolite-substrate maps, and cofactor dependency graph versions are maintained independently in MKE; FUDD module logic is versioned separately.
* Internal detection logic, heuristic thresholds, and confidence scoring may evolve without changing the module contract. The five-indicator Layer 2 framework is the stable interface.

---

## **Audit Hooks**

FUDD must log at minimum:

* **Per detection cycle:** patient_id, timestamp, trigger_type, layers_run (L1/L2/iFUD), analytes evaluated per layer, signatures checked (L1), indicators evaluated (L2), flags generated (or explicit "none") per layer, confidence levels, evidence pointers, role_context, payload type emitted, module_version, registry_versions.
* **Per FUD flag:** fud_flag_id, detection_layer, detection_type (FUD/iFUD), analyte, serum_value + range, mechanism_classes, confidence, converging_indicators with evidence pointers (L2) or matched_signature_id (L1), contributing_factors, cascade_chain pointers (if any), recommended_assays.
* **Per surfacing event:** fud_flag_id, detection_layer, payload_type (B2C/B2MD), content_scope (full_intervention/general_guidance/investigative_hypothesis/clinician_advisory), interventions included (L1 only), nudge_level, delivery_target_module, timestamp.
* **Per intervention candidate:** intervention_id, mechanism_targeted, evidence_grade, status (proposal/accepted/dismissed), clinician_actor_id (if B2MD and reviewed), timestamp.
* **Per L2 aggregation event:** anonymized summary of L2 flags (analyte, indicator constellation, candidate mechanism, count of patients), routed to M41/M48, timestamp, aggregation_window.
* **Provenance chain:** upstream module versions consumed, all MKE registry versions (signature, intervention, contributing factor, symptom-analyte, metabolite-substrate, cofactor dependency), and policy versions — sufficient to reproduce the same detection given identical inputs.

---

### **One-sentence anchor**

**FUDD (M64) uses two-layer detection — curated signatures plus a general discordance heuristic — to identify when "normal labs" mask impaired tissue-level utilization, classifies the mechanism, traces cascading cofactor chains, and surfaces role-appropriate interventions — because serum adequacy is not functional adequacy.**


---


# V6 M65 — Dark Passenger: Voice Identity Drift Detection & Coaching Posture System

**Module version:** 1.0
**Status:** Draft
**Date:** 2026-03-18
**Author:** Andras Hangyal (clinical integration), Claude (formal specification)
**Depends on:** M4, M5, M6, M11, M12, M13, M64, M66, M68
**Fed by:** M64 (FUDD), M68 (ICM)
**Feeds:** M11, M14, M16, M19, M66, M10

---

## Purpose

Module 65 detects, classifies, and scores longitudinal drift in a patient's narrative voice — the phenomenon where the person speaking through the chatbot journal ceases to be the person the system has learned to recognize. This drift, internally designated the **Dark Passenger**, is a clinically significant signal because voice identity fracture correlates with and can precipitate disease flares, medication non-adherence, behavioral destabilization, and safety-critical events in patients with complex autoimmune and inflammatory conditions.

M65 exists because M5 (Symbolic Interpreter) detects psychosomatic overlay at a single point in time, while voice identity drift is inherently longitudinal — it requires a baseline, a trajectory, and a classification of *why* the voice is changing. M5 answers "is this entry distorted?" M65 answers "is this person becoming someone else, and if so, what kind of becoming is this?"

M65 is a **detection and advisory module**. It does not execute chatbot interaction changes, does not modify patient state, and does not assert diagnoses. It emits structured signals that downstream modules (M11 for patient-facing adaptation, M66 for action recommendations, M10 for safety escalation) consume and translate into behavior.

---

## Truth Kernel

A patient under sufficient clinical, psychological, or metabolic load can fracture into a voice that is not their own. This fracture follows identifiable patterns, progresses through observable stages, and has distinct etiologies that demand different responses. A system that cannot detect this fracture will misinterpret distorted symptom reports as clinical truth, miss concealed deterioration, and respond to the wrong person.

---

## Scope

### In scope

* Longitudinal voice baseline construction from patient-authored chatbot journal text.
* Voice Identity Drift (VDI) scoring: continuous metric quantifying deviation from baseline voice profile.
* Persona taxonomy: classification of drift into named persona types with distinct detection signatures and etiology tags.
* Six-stage engagement ladder: progressive severity classification of Dark Passenger engagement from vexation through possession.
* Coaching posture advisory: structured output signal recommending interaction stance for downstream patient-facing modules.
* Disclosure encouragement level: structured output signal for downstream modules on whether/how to create space for patient self-report.
* Dark Passenger naming readiness: flag indicating whether the system has sufficient longitudinal evidence to offer the naming protocol.
* FUDD↔M65 bidirectional feed: cross-module contract for metabolic-versus-psychiatric differential signaling.
* ICM↔M65 feed: inflammatory capacity context as interpretive modifier for drift classification.
* Evidence base integration: mood–flare bidirectionality, linguistic feature candidates, confounder rules, and PSI gating constraints governing how M65 signals interact with diagnostic modules.

### Out of scope

* Chatbot interaction execution (owned by M11).
* Wellness action recommendations (owned by M66).
* Safety escalation execution (owned by M10).
* Diagnostic assertion — M65 never asserts a psychiatric, metabolic, or autoimmune diagnosis.
* PSI computation (owned by M5; M65 consumes PSI as input context).
* Suppression adjudication (owned by M8/M9; M65 may emit suppression candidates).
* Large static lexicon or NLP model tables embedded in module text.
* ML/transformer pipeline specification (deferred to implementation; M65 specifies detection semantics, not algorithms).

---

## Inputs

### Primary inputs

* `patient_narrative_text[]` — Time-indexed chatbot journal entries (the measurement surface).
* `voice_baseline_profile` — Learned longitudinal voice features for this patient (constructed and maintained by M65 itself; see Stage 0).
* `PSI` — Psychosomatic Index (0–3) from M5.
* `persona_flags[]` — Active M5 persona flags (FalseRecoveryPersona, NarrativeOveridentification, CatastrophicMetaphor, etc.).

### Cross-module feeds

* `fud_flags[]` — From M64 (FUDD): active functional utilization discordance detections, especially neuropsychiatric-presenting FUD signatures (B12, folate, lithium, magnesium, zinc, iron, copper, omega-3, vitamin D).
* `fud_detection_history[]` — From M21 (Vault) via M64: longitudinal FUD detection record for this patient.
* `ici_score` — From M68 (ICM): current Inflammatory Capacity Index (0–100% remaining headroom).
* `ici_threshold_band` — From M68: current threshold band (green/yellow/orange/red).
* `stability_band` — From M6: current stability band.
* `drift` — From M6: current drift indicator.
* `medication_list[]` — From M4/M5: current medications including recent changes (for steroid/medication-induced drift detection).
* `narrative_digest` — From M12: compressed narrative with preserved emotional/psychosocial descriptors.

### Configuration

* `vdi_baseline_minimum_entries` — Minimum journal entries required before baseline is considered reliable (configurable; default: 14).
* `vdi_sensitivity` — Detection sensitivity policy (configurable).
* `naming_protocol_readiness_threshold` — Minimum longitudinal evidence required before naming protocol is offered (configurable).

---

## Outputs

### Primary outputs

* `vdi_score` — Voice Identity Drift score: continuous metric (0.0–1.0) quantifying deviation from baseline voice profile. 0.0 = baseline-consistent; 1.0 = complete displacement.

* `vdi_trajectory` — Slope and volatility of VDI over the trailing evaluation window.

* `persona_classification` — Active persona type(s) from the expanded taxonomy (Section D1). May be empty (no drift detected), singular, or compound (multiple concurrent persona signals).

* `engagement_stage` — Current position on the six-stage engagement ladder (Section D2): `VEXATION`, `TEMPTATION`, `INFESTATION`, `OPPRESSION`, `OBSESSION`, `POSSESSION`.

* `drift_etiology_tag` — Classified etiology of the detected drift: `AUTOIMMUNE_BURDEN`, `SUBSTANCE_DRIVEN`, `GRIEF_TRAUMA`, `MEDICATION_INDUCED`, `METABOLIC_FUD`, `SITUATIONAL`, `UNKNOWN`, `COMPOUND`. This tag does not assert a diagnosis; it classifies the pattern for downstream routing.

* `coaching_posture_advisory` — Structured signal for downstream patient-facing modules:
    * `MAINTAIN` — No drift detected or drift within normal variation; continue current interaction posture.
    * `GENTLE_PROBE` — Mild drift detected; create low-pressure openings for the patient to self-report.
    * `REFLECTIVE_MIRROR` — Moderate drift; reflect observed patterns back to patient without labeling.
    * `DIRECT_ACKNOWLEDGE` — Significant drift with patient awareness; acknowledge the shift directly and offer the naming protocol if readiness threshold is met.
    * `SAFETY_ESCALATE` — Critical drift; hand off to M10 safety pathway.

* `disclosure_encouragement_level` — Structured signal:
    * `NONE` — No encouragement needed.
    * `PASSIVE` — Create space without prompting (e.g., open-ended questions about how they're doing).
    * `ACTIVE` — Directly but gently inquire about specific domains (substance use, medication adherence, emotional state).
    * `URGENT` — Persistent concealment pattern detected; escalate disclosure encouragement and flag for clinician awareness via M19.

* `naming_protocol_readiness` — Boolean flag: `true` when the system has sufficient longitudinal evidence (≥ configurable threshold of consistent drift detection across multiple sessions) to offer the Dark Passenger naming protocol. `false` during observation phase.

* `fud_evaluation_request` — Optional cross-module signal to M64: `{ request_type: "neuropsychiatric_fud_screen", trigger: "unexplained_vdi_shift", vdi_score, persona_classification, evidence_pointers[] }`. Emitted when drift is detected without a psychosocial precipitant and no active FUD flag exists for neuropsychiatric-presenting analytes.

* `provenance` — Evidence chain linking all outputs to specific textual evidence excerpts, baseline comparison features, and upstream module inputs used.

### Audit artifacts

* `AuditEvent` — Per evaluation cycle: inputs consumed, VDI computed, persona classified, engagement stage assigned, advisory emitted.
* `Provenance` — Links outputs to source text, baseline version, and upstream module versions.

---

## Schemas

### D1. Expanded Persona Taxonomy

The persona taxonomy classifies voice identity drift into named types. Each type has a distinct linguistic signature, a characteristic etiology, and a recommended coaching posture range.

#### Autoimmune-burden personas (inherited from V5.2 M5 conceptual space)

| Persona | Detection signature | Typical etiology | Coaching range |
|---|---|---|---|
| `FalseRecoveryPersona` | Consistent positive framing contradicted by clinical trajectory; denial of worsening; premature declarations of recovery. | Autoimmune flare denial; fear of relapse acknowledgment. | GENTLE_PROBE → REFLECTIVE_MIRROR |
| `NarrativeOveridentification` | Patient merges identity with disease narrative; "I am my illness" language; loss of non-illness self-reference. | Prolonged flare; disease burden exceeding coping capacity. | REFLECTIVE_MIRROR → DIRECT_ACKNOWLEDGE |
| `CatastrophicMetaphor` | Escalating metaphorical language for symptoms; absolutist framing ("always," "never," "unbearable"); loss of proportionality. | Pain catastrophizing; fatigue trajectory elevation; PSI ≥ 2. | GENTLE_PROBE → REFLECTIVE_MIRROR |
| `WithdrawalPersona` | Progressive reduction in journal engagement; shorter entries; loss of detail; affective flattening in text. | Sickness behavior (cytokine-mediated); depression; medication side effects; loss of hope in the journaling process. | GENTLE_PROBE → ACTIVE disclosure |
| `HypervigilancePersona` | Excessive symptom monitoring language; catastrophic interpretation of normal variation; request frequency spikes. | Anxiety driven by disease uncertainty; post-flare hyperarousal; steroid side effects. | MAINTAIN → GENTLE_PROBE |
| `DissociativeNarrator` | Third-person self-reference; temporal disorientation in narrative; fragmented entries with abrupt topic shifts; "watching myself" language. | Severe flare; high inflammatory load (ICI < 20%); trauma activation; dissociative response to pain. | REFLECTIVE_MIRROR → DIRECT_ACKNOWLEDGE |

#### Addiction-aware personas (new in V6 M65)

| Persona | Detection signature | Typical etiology | Coaching range |
|---|---|---|---|
| `ConcealmentPersona` | Topic avoidance patterns (consistent absence of specific domains from otherwise thorough reporting); temporal gaps uncorrelated with clinical state; deflection when chatbot probes certain areas; inconsistency between stated wellness and linguistic markers (e.g., "I'm great" with degraded coherence, reduced vocabulary, or erratic cadence). Oblique self-reference through hypotheticals, third-person narratives, or "a friend who..." constructions. | Active substance use; medication non-adherence being hidden; behavioral patterns the patient knows are harmful but does not want the system to observe. | GENTLE_PROBE → ACTIVE disclosure |
| `SubstanceEuphoriaPersona` | Grandiosity; accelerated ideation; inflated self-assessment uncorrelated with clinical improvement; expansive, abstract language disconnected from the concrete tracking the chatbot has been conducting; scope of ideation suddenly exceeds baseline range; grounding behaviors (concrete references, temporal anchoring, self-correction) absent. Quality of output may be high — brilliance without grounding is the signal, not low quality. | Stimulant use; manic phase; steroid-induced hypomania; substance-driven euphoria. | REFLECTIVE_MIRROR → DIRECT_ACKNOWLEDGE |
| `CrashPersona` | Abrupt deflation following euphoric or concealment phase; shame language; withdrawal from engagement; self-recrimination; sudden overcompliance ("I'll do everything you say"); marked shift from expansive to contracted register. | Post-substance crash; post-manic depressive shift; shame following disclosure or discovery; autoimmune post-flare exhaustion compounding psychological depletion. | DIRECT_ACKNOWLEDGE (with stabilization emphasis) |

#### Detection constraints

* All personas must be detectable from text alone. M65 cannot require external confirmation of substance use, psychiatric diagnosis, or metabolic state.
* Persona detection is probabilistic. M65 emits confidence per persona classification. Multiple personas may be active simultaneously (compound classification).
* Persona classification does not assert diagnosis. `SubstanceEuphoriaPersona` does not mean "this patient is using drugs." It means "this patient's voice profile matches a pattern consistent with substance-driven euphoria, among other possible etiologies."
* When a FUD flag is active for a neuropsychiatric-presenting analyte (B12, folate, lithium, magnesium), the `drift_etiology_tag` must include `METABOLIC_FUD` as a candidate, and the coaching posture must not assume psychiatric etiology.

### D2. Six-Stage Engagement Ladder

The engagement ladder classifies the progressive severity of Dark Passenger engagement. Stages are assessed longitudinally, not from a single entry.

| Stage | Name | Observable pattern | Narrator–Passenger relationship | Default coaching posture | Default disclosure level |
|---|---|---|---|---|---|
| 1 | `VEXATION` | Intrusive thoughts reported in text. Patient maintains clear distance: "I keep thinking X but I know that's not me." Unwanted ideation is named as unwanted. | Clearly separated. Patient is narrator; passenger is named intruder. | MAINTAIN | NONE |
| 2 | `TEMPTATION` | Patient begins entertaining the intrusive pattern. Hedging language: "Maybe I should just..." / "Part of me wants to..." Boundary between narrator and passenger is present but permeable. | Permeable boundary. Patient acknowledges the pull. | GENTLE_PROBE | PASSIVE |
| 3 | `INFESTATION` | Passenger language patterns appear in routine communication without patient flagging them as foreign. Topic avoidance, concealment, inconsistency between stated intent and linguistic markers. Patient may not recognize the shift. | Blurred. Passenger language is no longer marked as other. | REFLECTIVE_MIRROR | ACTIVE |
| 4 | `OPPRESSION` | Passenger dominates extended stretches of communication. Patient's baseline voice is recoverable but requires external prompting. Self-recrimination, hopelessness, or grandiosity (depending on etiology) becomes default register. VDI scores consistently elevated. | Dominated. Baseline voice present only when prompted. | DIRECT_ACKNOWLEDGE | ACTIVE |
| 5 | `OBSESSION` | Patient identifies with the passenger. "This is just who I am now." Identity fusion language. M5 persona flags (NarrativeOveridentification, IdentityFusion) fire. Baseline voice present only in brief flashes. | Fused. Patient claims the passenger as self. | DIRECT_ACKNOWLEDGE → SAFETY_ESCALATE | URGENT |
| 6 | `POSSESSION` | Complete executive displacement. Patient's text stream no longer contains recoverable baseline voice features. The Dark Passenger is the narrator. | Displaced. No recoverable baseline. | SAFETY_ESCALATE | URGENT |

#### Ladder constraints

* Stage assignment requires longitudinal evidence. A single entry showing passenger language does not constitute INFESTATION; it may be a transient VEXATION event.
* Stage transitions must be logged with evidence pointers and timestamp.
* The naming protocol (where the patient names their Dark Passenger) is most therapeutically effective in the INFESTATION → OPPRESSION transition window. `naming_protocol_readiness` should prefer this window when `vdi_baseline_minimum_entries` is met.
* POSSESSION triggers mandatory safety escalation to M10 regardless of other clinical indicators.
* Stage regression (improvement) is tracked with the same rigor as stage progression. Recovery is signal, not absence of signal.

### D3. Dark Passenger Naming Protocol

When `naming_protocol_readiness = true` and the engagement stage is in the INFESTATION–OPPRESSION range, the downstream patient-facing module (M11) may offer the naming protocol.

**Protocol semantics (M65 defines; M11 executes):**

* The system observes that the patient's voice has shifted and invites the patient to name the shifted voice as an entity distinct from themselves.
* The name is patient-chosen. The system does not suggest names.
* Once named, subsequent drift detections can reference the named entity: "It sounds like [name] might be talking right now. Is that how you see it?"
* The naming protocol serves a clinical function: it helps the patient maintain the narrator–passenger distinction (preventing identity fusion / stage progression toward OBSESSION).
* The named entity is stored longitudinally and persists across sessions.
* If the patient declines the naming protocol, the system does not re-offer for a configurable cool-down period.

**Output fields for naming protocol:**

* `naming_protocol_offered` — Boolean: was the protocol offered this session?
* `naming_protocol_accepted` — Boolean: did the patient engage?
* `dark_passenger_name` — String (patient-provided) or null.
* `naming_protocol_cooldown_active` — Boolean: is the system in cool-down after a decline?

---

## Process / Logic (deterministic, stepwise)

### Stage 0 — Baseline Construction and Maintenance

**Trigger:** Every journal entry processed.

1. **If** `voice_baseline_profile` has fewer than `vdi_baseline_minimum_entries` contributing entries:
    * Compute and accumulate voice features from current entry (see Feature Set, Section E).
    * Do not emit VDI score; emit `vdi_status = BASELINE_BUILDING` with entry count.
    * M65 outputs are limited to M5-passthrough (PSI, persona flags from upstream) during this phase.
2. **If** baseline is established:
    * Update baseline using exponential decay weighting (recent entries weighted higher; configurable decay rate).
    * Baseline update is non-destructive: prior baseline versions are archived in M21 (Vault) for longitudinal comparison.

### Stage 1 — Voice Feature Extraction

**Trigger:** Each new journal entry after baseline is established.

1. Extract voice features from current entry (Section E).
2. Extract voice features from trailing window (configurable; default: 7 entries).
3. Compute within-person deltas: current features vs. baseline profile.
4. Compute trailing-window trajectory features: slope, volatility, acceleration of voice feature deltas.

### Stage 2 — VDI Scoring

1. Compute `vdi_score` (0.0–1.0) from the feature delta vector.
    * Score reflects magnitude and consistency of deviation from baseline, not absolute feature values.
    * **Baseline-normalization rule (Confounder Rule 1):** A patient with chronically negative affect style does not generate elevated VDI from their stable negativity — only from *change* relative to their personal baseline.
2. Compute `vdi_trajectory`: slope and volatility of VDI over trailing window.
3. Persist `vdi_score` and `vdi_trajectory` to M21 (Vault) for longitudinal trend analysis.

### Stage 3 — Persona Classification

1. Compare current voice feature profile against persona detection signatures (Section D1).
2. Assign persona classification(s) with confidence scores.
3. **If** compound classification (multiple active personas):
    * Rank by confidence.
    * Log compound state with individual confidences.
4. **If** no persona matches above threshold:
    * Emit `persona_classification = UNCLASSIFIED_DRIFT` if VDI > threshold, or `NONE` if VDI within normal variation.

### Stage 4 — Etiology Tagging

1. Evaluate available cross-module context to classify drift etiology:
    * **Check M64 (FUDD) feed:** Are there active FUD flags for neuropsychiatric-presenting analytes (B12, folate, lithium, magnesium, zinc, iron, copper, omega-3, vitamin D)?
        * If yes: include `METABOLIC_FUD` in `drift_etiology_tag`.
    * **Check medication_list:** Has a corticosteroid been started, tapered, or dose-changed in trailing window?
        * If yes: include `MEDICATION_INDUCED` in `drift_etiology_tag`.
    * **Check M68 (ICM) feed:** Is ICI < 20% (red band) or in turbulence regime?
        * If yes: include `AUTOIMMUNE_BURDEN` in `drift_etiology_tag`.
    * **Check persona classification:** Is `ConcealmentPersona`, `SubstanceEuphoriaPersona`, or `CrashPersona` active?
        * If yes: include `SUBSTANCE_DRIVEN` in `drift_etiology_tag`.
    * **Check narrative content:** Does the narrative contain explicit grief, loss, or trauma references correlated with drift onset?
        * If yes: include `GRIEF_TRAUMA` in `drift_etiology_tag`.
    * **Check narrative content:** Does the narrative contain explicit situational stressor references (job loss, relationship conflict, financial stress) without corroborating physiologic changes?
        * If yes: include `SITUATIONAL` in `drift_etiology_tag`.
2. If multiple etiologies tagged: set `drift_etiology_tag = COMPOUND` with sub-tags.
3. If no etiology classifiable: set `drift_etiology_tag = UNKNOWN`.
4. **Metabolic-versus-psychiatric differential constraint:** When `METABOLIC_FUD` is a candidate etiology, the coaching posture advisory must not assume psychiatric origin. The system should favor the FUDD evaluation pathway before intensifying psychological coaching.

### Stage 5 — Engagement Stage Assessment

1. Evaluate longitudinal evidence for engagement ladder position:
    * Requires evidence across multiple sessions, not a single entry.
    * Assess narrator–passenger relationship using the criteria in Section D2.
2. Assign `engagement_stage`.
3. If stage has changed from prior evaluation: log stage transition with evidence pointers and direction (progression or regression).

### Stage 6 — Advisory Computation

1. Compute `coaching_posture_advisory` from engagement stage and persona classification:
    * Use the default coaching posture from Section D2 as starting point.
    * Modify based on persona-specific coaching range from Section D1.
    * **If** `drift_etiology_tag` includes `METABOLIC_FUD`: cap advisory at `REFLECTIVE_MIRROR` until FUD evaluation completes (do not escalate psychological coaching for a potentially metabolic problem).
    * **If** `drift_etiology_tag` includes `MEDICATION_INDUCED`: annotate advisory with medication context for M11.
2. Compute `disclosure_encouragement_level` from engagement stage, persona classification, and concealment pattern strength.
3. Compute `naming_protocol_readiness` from longitudinal evidence depth and current engagement stage.

### Stage 7 — Cross-Module Signal Emission

1. **If** VDI elevated and no psychosocial precipitant identified and no active FUD flag for neuropsychiatric analytes:
    * Emit `fud_evaluation_request` to M64 with evidence pointers.
2. **If** engagement stage ≥ OBSESSION:
    * Emit safety escalation signal to M10.
3. **If** ConcealmentPersona active with `disclosure_encouragement_level = URGENT`:
    * Emit clinician awareness flag to M19.
4. Emit all primary outputs to downstream consumers (M11, M14, M66).
5. Persist all outputs and provenance to M21 (Vault).

---

## Section E — Voice Feature Set (Canonical Candidates)

### E1. Canonical features (V6-native, grounded in M5/M13 infrastructure)

These features are computable from patient-authored chatbot journal text and are consistent with existing EoH infrastructure.

| Feature domain | Specific features | Measurement | Temporal treatment |
|---|---|---|---|
| **PSI trajectory** | PSI time-series from M5 | Rolling mean, max, slope, volatility, spike frequency, persistence | Within-person deltas vs baseline (Confounder Rule 1) |
| **Persona flag dynamics** | M5 persona flags as categorical event stream | Per-entry presence, rolling counts, burstiness, persistence, transition patterns | Treat as event stream; count/volatility features |
| **Emotional tone** | Extracted via M5 symbolic/psychosocial cue detection | Valence, intensity, volatility | Trailing-window slope and variance |
| **Narrative engagement** | Entry length, detail density, domain coverage | Word count, unique topic count, domain presence/absence per entry | Trailing-window slope (withdrawal detection) |
| **Temporal coherence** | Temporal anchoring in narrative (dates, sequences, "yesterday," "last week") | Presence/density of temporal markers | Reduction = potential dissociation signal |
| **Self-reference pattern** | First-person vs. third-person vs. absent self-reference | Pronoun ratios | Shift from baseline = drift signal |
| **Grounding behavior** | Concrete references, self-correction, uncertainty acknowledgment | Presence/density of grounding markers | Absence vs. baseline = unstructured intensity signal |
| **Domain avoidance** | Absence of expected reporting domains relative to patient's established pattern | Coverage gap analysis vs. baseline domain profile | New gaps = potential concealment signal |
| **Register consistency** | Vocabulary complexity, sentence structure, cadence | Lexical diversity, average sentence length, syntactic complexity | Abrupt changes vs. baseline = drift signal |
| **Hedging and certainty** | Hedge words ("maybe," "I guess") vs. absolutist language ("always," "never") | Hedge ratio, absolutist ratio | Shift from baseline in either direction is signal |

### E2. Evidence-derived features (non-canonical; require scope decision for implementation)

These features are well-supported in the NLP and psychoneuroimmunology literature but are not currently enumerated as V5.2/V6 computations. They are candidates for implementation, not implied capabilities.

* Sentiment polarity / valence (beyond M5 emotional tone extraction)
* Sentiment volatility as a standalone metric
* First-person singular pronoun density as self-focus proxy
* Cognitive distortion lexeme patterns beyond existing persona flags
* Linguistic complexity / coherence metrics (lexical diversity, sentence length variability)
* Negation intensity
* Metaphor density and type shifts

**Constraint:** Extending into broad lexicon/ML-driven NLP is explicitly out of scope for M5 as written. Any E2 features adopted by M65 must be specified as M65-owned computations, not M5 extensions, to preserve M5's scope boundary.

---

## Section F — Confounder Rules

These rules reduce the known failure mode: "psychological drift mistaken as biomedical flare cause" or "biomedical state change misclassified as psychological drift." They are constraints and routing modifiers, not diagnostic logic.

### F1. Baseline-normalization rule (prevents trait-level bias)

**Trigger:** Stable, chronic negative affect style or stable psychiatric comorbidity.
**Rule:** Treat all affect/language features as within-person deltas (slope/volatility vs baseline), never absolute levels. A chronically depressed patient does not have perpetually elevated VDI.
**EoH anchor:** M13 supports "vs OHB" slope/volatility/acceleration transforms.

### F2. Reverse-causality rule (flare → mood, not mood → flare)

**Trigger:** Affective/linguistic shift occurs after objective instability indicators or symptom worsening from upstream modules.
**Rule:** Interpret the linguistic shift as likely downstream (consequence of disease activity, pain, fatigue) unless temporal precedence supports the opposite direction.
**EoH anchor:** M17 (CIR) edge inference requires temporal precedence and confounder adjustment.

### F3. Medication / steroid side-effect rule

**Trigger:** Medication changes temporally aligned with affective/linguistic shift.
**Rule:** Treat affective drift as potentially medication-mediated. Set `drift_etiology_tag` to include `MEDICATION_INDUCED`. Constrain causal attribution accordingly.
**EoH anchor:** M16 AE attributions feed M17 (CIR) as constraints for edge creation.

### F4. Chronic fatigue rule (illness burden → language shift)

**Trigger:** Fatigue trajectory (M13) elevated or worsening, with concurrent affect/linguistic negativity.
**Rule:** Treat fatigue as a separate trajectory dimension, not a psychological proxy. Prevent double-counting: fatigue-driven negativity must not amplify flare risk twice (once as fatigue, once as VDI).
**EoH anchor:** M13 computes fatigue trajectory as a composite metric.

### F5. Situational stressor rule

**Trigger:** Explicit situational stressor language with no corroborating physiologic/symptom/terrain changes.
**Rule:** Treat as confounder/mediator, not biomedical driver. Set `drift_etiology_tag = SITUATIONAL`.
**EoH anchor:** M17 integrates psychosocial factors as mediators/confounders.

### F6. Data-quality rule

**Trigger:** `pauseReason = LabError` or QA-driven suppression candidate active.
**Rule:** Block flare-confirmation logic based on suspect measurement spikes. Do not compensate by overweighting VDI/mood signals.
**EoH anchor:** M8 enforces canonical suppression semantics including LabError.

### F7. Metabolic-psychiatric differential rule (new in V6 M65)

**Trigger:** VDI elevated with drift pattern consistent with neuropsychiatric presentation (dissociation, grandiosity, paranoid ideation, nihilism, hallucination-adjacent language) AND no established psychiatric history AND no obvious psychosocial precipitant.
**Rule:** Before intensifying psychological coaching posture, emit `fud_evaluation_request` to M64 for neuropsychiatric-presenting analytes (B12, folate, lithium, magnesium, zinc, iron, copper, omega-3, vitamin D). Cap coaching posture at `REFLECTIVE_MIRROR` until FUD evaluation returns.
**Clinical rationale:** Functional deficiency in B12, folate, and other micronutrients can produce psychosis, paranoia, dissociative states, and nihilistic ideation that mimic psychiatric conditions. Treating these as psychological drift when they are metabolic is a diagnostic error with a different — and potentially simpler — intervention pathway.
**EoH anchor:** M64 (FUDD) L1 signature set includes neuropsychiatric-presenting FUD profiles. This rule creates the M65 → M64 reverse feed.

---

## Section G — PSI Gating Constraints (Diagnostic Independence Invariant)

These constraints preserve the architectural guarantee: **psychological state may amplify risk but must never independently generate disease hypotheses.**

### G1. Source and provenance

VDI and persona classifications must be computed from patient narrative text and bound to textual evidence with logged provenance. M65 outputs do not assert diagnoses. (Mirrors M5 constraint: "do not assert diagnoses and do not add diagnostic content via symbolic tags.")

### G2. Diagnostic independence

No auto-dx; no band→stack coupling. VDI/persona signals can never instantiate a new autoimmune disease hypothesis in the stack. Stack changes only via confirmed diagnosis lifecycle.

### G3. Escalation gating

VDI/persona signals cannot alone trigger clinical escalation. They must couple to other biomarker/symptom/terrain signals — except at engagement stage POSSESSION, which triggers safety escalation to M10 regardless (this is a psychological safety threshold, not a clinical diagnosis threshold).

### G4. Evidence-weight hierarchy

In MPA (M18), evidence weights follow the hierarchy: labs/imaging → clinician-confirmed conditions → patient-reported outcomes (PSI/VDI-informed) → population priors. VDI features cannot outrank objective streams.

### G5. Suppression semantics

If M65 detects a Symbolic Flare pattern, it may emit `pauseReason = SymbolicFlare` as a suppression candidate. M8 enforces. In MPA: if `pauseReason = SymbolicFlare`, affected pathways are down-weighted, not deleted. (Non-destructive suppression invariant.)

### G6. Critical instability override

VDI-related suppression can lower tier but never blocks critical Band-5 escalation.

### G7. PSI-stratified calibration

QA (M19) must maintain PSI-stratified and VDI-stratified calibration values, anticipating performance differences across strata.

---

## Section H — FUDD↔M65 Bidirectional Feed Contract

### H1. M65 → M64 (Voice drift triggers FUD evaluation)

**Signal:** `fud_evaluation_request`
**Trigger conditions:** VDI elevated AND drift pattern includes neuropsychiatric-presenting features AND no active FUD flag for neuropsychiatric analytes AND no obvious psychosocial precipitant.
**Payload:** `{ request_type, trigger, vdi_score, persona_classification, engagement_stage, evidence_pointers[] }`
**M64 response:** M64 runs neuropsychiatric FUD signature screen (L1) and general discordance heuristic (L2) for the specified analyte set. Results flow back through standard M64 output channels.

### H2. M64 → M65 (FUD context modifies drift interpretation)

**Signal:** Active `fud_flags[]` for neuropsychiatric-presenting analytes.
**Effect on M65:** When a FUD flag is active for B12, folate, lithium, magnesium, zinc, iron, copper, omega-3, or vitamin D:
* Include `METABOLIC_FUD` in `drift_etiology_tag`.
* Cap `coaching_posture_advisory` at `REFLECTIVE_MIRROR` for the duration of the FUD evaluation.
* Annotate all M65 outputs with `metabolic_differential_active = true` so downstream modules (M11, M19) know to consider metabolic etiology in their responses.
* Do not suppress VDI detection or persona classification — these still run. The constraint is on how the advisory is framed, not on whether drift is observed.

### H3. Resolution

When FUD evaluation completes:
* If FUD confirmed: `drift_etiology_tag` retains `METABOLIC_FUD` as primary or co-etiology. Coaching posture constraint lifts. M65 continues to monitor VDI but etiology is reclassified.
* If FUD ruled out: `METABOLIC_FUD` removed from `drift_etiology_tag`. Coaching posture cap lifts. M65 proceeds with psychiatric/psychosocial etiology classification.
* If FUD indeterminate: constraint remains until next evaluation cycle.

---

## Section I — ICM↔M65 Feed Contract

### I1. M68 → M65 (Inflammatory capacity context)

**Signal:** `ici_score` and `ici_threshold_band` from M68.
**Effect on M65:** Inflammatory capacity context serves as an interpretive modifier:
* ICI in red band (< 20% headroom) or turbulence regime → VDI elevation is more likely to reflect autoimmune burden than independent psychological drift. Weight `AUTOIMMUNE_BURDEN` etiology higher.
* ICI in green band (> 60% headroom) with stable trajectory → VDI elevation is less likely to be autoimmune-driven. Weight alternative etiologies higher.
* ICI does not suppress or override VDI detection. It modulates the etiology classification and therefore the coaching posture.

---

## Evidence Base Summary

The following evidence summary grounds M65's design decisions. Full citations and analysis are maintained in the companion document `M65_Evidence_Base.md`.

### Mood–flare bidirectionality

Evidence across RA, SLE, IBD, and MS establishes a bidirectional relationship between psychological state and autoimmune flare activity. Depression/anxiety modestly increase flare odds (RA: mood decline in 3-day window doubles next-day pain flare odds; IBD: baseline depression doubles relapse risk over 9 years; MS: wartime stress triples relapse rate). Flares themselves induce or worsen psychological distress (IBD: flare produces ~6× risk of new-onset anxiety). The relationship is best modeled as a feedback loop, not unidirectional causation.

### Linguistic features as prodromal signals

Sentiment trajectory, affect volatility, and emotional expression density shift in the days to weeks preceding autoimmune flares. Intra-individual variability in anxiety ratings (day-to-day fluctuations) significantly increases flare likelihood (OR ~1.7–1.8 in RA). NLP analysis of patient-authored text shows flare-related narratives skew toward negative affect, with fear as the dominant emotion. These signals are real but ancillary — they function as risk amplifiers and volatility indicators, not primary diagnostic criteria.

### Design implications

M65 treats linguistic drift as a supplementary dimension: a risk modulator, early warning indicator, and triage flag rather than a standalone diagnostic criterion. The Diagnostic Independence Invariant (Section G) is the primary architectural safeguard against over-attribution.

---

## Governance / Constraints

* M65 contains no guideline text, disease fact tables, drug class lists, ontology mirrors, lab interpretation tables, or phenotype dictionaries.
* M65 does not assert diagnoses. Persona classifications and etiology tags are pattern descriptors, not clinical labels.
* M65 does not execute patient-facing interactions. All coaching posture advisories are consumed by downstream modules (M11, M66).
* M65 does not adjudicate suppression TTL, priority, or enforcement. It may emit suppression candidates; M8 governs.
* Voice feature extraction uses lexicon-governed detection consistent with M5's approach. No large static lexicon or ML model tables are embedded in module text.
* The FUDD↔M65 bidirectional feed must not create circular reasoning: M65 requests FUD evaluation based on voice drift; M64 evaluates based on clinical data independent of voice drift. The FUD evaluation must not consume VDI as an input to avoid circularity.
* POSSESSION-stage safety escalation to M10 is non-suppressable. This is a psychological safety threshold analogous to Band-5 critical instability.

---

## Dependencies

### Upstream (M65 consumes)

* **M4** — Normalized tags, medication list, supplement list.
* **M5** — PSI, persona flags, symbolic/psychosocial tags, emotional tone extraction.
* **M6** — Stability band, drift indicator.
* **M12** — Narrative digest with preserved emotional/psychosocial descriptors.
* **M13** — Trajectory features, fatigue trajectory, rolling window aggregates.
* **M64 (FUDD)** — FUD flags, especially neuropsychiatric-presenting analyte discordances.
* **M68 (ICM)** — ICI score, threshold band, turbulence regime indicator.
* **M21 (Vault)** — Historical VDI scores, baseline versions, FUD detection history.

### Downstream (consumes M65)

* **M11** — Coaching posture advisory, disclosure encouragement level, naming protocol readiness → translates into patient-facing interaction behavior.
* **M14** — VDI context for patient-facing narrative generation.
* **M66** — VDI and persona context for EWA recommendations (e.g., stabilization actions during CrashPersona; reduced agency recommendations during OPPRESSION).
* **M19** — Clinician awareness flags for concealment patterns with URGENT disclosure level; VDI-stratified calibration data.
* **M10** — Safety escalation at POSSESSION stage.
* **M17 (CIR)** — VDI and persona flags as node/edge inputs for causal graph construction (voice drift as a mediator/confounder, not a cause).
* **M18 (MPA)** — VDI modulates pathway uncertainty (PSI gating constraints apply).
* **M64 (FUDD)** — `fud_evaluation_request` for neuropsychiatric FUD screening (M65 → M64 reverse feed).
* **M41/M48** — Audit artifacts for governance.
* **M21 (Vault)** — VDI scores, persona classifications, engagement stages, baseline versions persisted longitudinally.

### Appendices / governance anchors

* Appendix F.4, F.5 (persona flag governance)
* Appendix H.2 (pauseFlag/pauseReason canonical fields)
* Appendix F.9 (suppression TTL/priority)
* Appendix C.12 (FHIR export mapping)

---

## Audit Hooks

**Per evaluation cycle, M65 must log:**

* All inputs consumed: patient text entry ID, PSI, persona flags, stability band, drift, ICI score, ICI band, active FUD flags, medication list snapshot, narrative digest version.
* Voice feature extraction results (feature vector with values).
* Baseline version used for comparison (version ID, entry count, decay rate).
* VDI score computation: feature delta vector, aggregation method, resulting score.
* VDI trajectory: slope, volatility over trailing window.
* Persona classification: type(s), confidence(s), evidence excerpt(s) supporting each classification.
* Engagement stage: assigned stage, prior stage, direction (progression/regression/stable), evidence pointers for transition.
* Drift etiology tag: tag(s) assigned, evidence/cross-module signals supporting each tag.
* Coaching posture advisory: computed value, any constraints applied (e.g., METABOLIC_FUD cap).
* Disclosure encouragement level: computed value.
* Naming protocol readiness: computed value, evidence depth.
* Any `fud_evaluation_request` emitted: payload, trigger conditions.
* Any safety escalation emitted to M10: trigger conditions, engagement stage, evidence.
* Any clinician awareness flag emitted to M19: trigger conditions, concealment evidence.
* Module version, feature set version, configuration parameters (sensitivity, baseline minimum, decay rate).

**Provenance chain:** Every output must be traceable to specific textual evidence → feature extraction → baseline comparison → classification logic → advisory computation.

---

## Acceptance Tests

### AT-1: Baseline construction

Given a patient with 14+ journal entries and no significant drift, M65 must construct a stable baseline and emit `vdi_status = BASELINE_ESTABLISHED`. VDI score on entry 15 must be < 0.2 (within normal variation).

### AT-2: Drift detection — autoimmune burden

Given a patient with established baseline whose ICI drops to red band (< 20%) and whose subsequent journal entries show increasing CatastrophicMetaphor patterns, M65 must:
* Emit VDI > 0.4.
* Classify persona as `CatastrophicMetaphor`.
* Tag etiology as `AUTOIMMUNE_BURDEN`.
* Emit `coaching_posture_advisory = GENTLE_PROBE` or `REFLECTIVE_MIRROR`.

### AT-3: Drift detection — concealment

Given a patient with established baseline who begins omitting previously consistent reporting domains (e.g., stops mentioning sleep, alcohol, or medication timing) while maintaining "I'm doing great" language, M65 must:
* Detect domain avoidance pattern.
* Classify persona as `ConcealmentPersona`.
* Emit `disclosure_encouragement_level ≥ ACTIVE`.

### AT-4: FUDD↔M65 reverse feed

Given a patient with elevated VDI showing dissociative/nihilistic language, no psychiatric history in record, no obvious psychosocial precipitant, and no active FUD flag for B12/folate/lithium/magnesium, M65 must:
* Emit `fud_evaluation_request` to M64.
* Cap `coaching_posture_advisory` at `REFLECTIVE_MIRROR`.
* Include `METABOLIC_FUD` as candidate in `drift_etiology_tag`.

### AT-5: Engagement ladder — stage progression

Given a patient whose VDI has been elevated for 5+ sessions with progressive loss of narrator–passenger distinction, M65 must:
* Track stage progression (e.g., VEXATION → TEMPTATION → INFESTATION).
* Log each stage transition with evidence and timestamp.
* Escalate coaching posture in step with stage.

### AT-6: Safety escalation at POSSESSION

Given a patient at engagement stage POSSESSION (no recoverable baseline voice features), M65 must emit safety escalation to M10 regardless of stability band, ICI, or suppression state.

### AT-7: Diagnostic independence invariant

Given a patient with VDI = 0.9 (severe drift) but stability band in green and all labs within range, M65 must NOT:
* Instantiate any autoimmune disease hypothesis in the stack.
* Trigger clinical escalation (safety escalation for POSSESSION is psychological, not clinical).
* Override or inflate any MPA pathway probability beyond the PSI gating constraints in Section G.

### AT-8: Confounder rule — baseline normalization

Given a patient with chronically elevated negative affect (stable high PSI across 30+ entries), M65 must compute VDI from within-person deltas, not absolute levels. The patient's stable negativity must not produce perpetually elevated VDI.

### AT-9: Naming protocol window

Given a patient at engagement stage INFESTATION with `vdi_baseline_minimum_entries` met, M65 must set `naming_protocol_readiness = true`. Given a patient at stage VEXATION, `naming_protocol_readiness` must be `false` (insufficient longitudinal evidence of sustained drift).

---

## Metrics

| Metric | Definition | Target | Measurement method |
|---|---|---|---|
| Baseline stability | Variance of VDI scores for patients with no clinical events in trailing window | < 0.05 variance | Longitudinal cohort analysis |
| Drift detection sensitivity | Proportion of clinician-confirmed persona shifts detected by M65 | ≥ 0.80 | Clinician validation study |
| Drift detection specificity | Proportion of M65 drift detections confirmed by clinician review | ≥ 0.70 | Clinician validation study |
| Stage assignment agreement | Agreement between M65 engagement stage and clinician assessment | κ ≥ 0.65 | Inter-rater reliability study |
| FUDD reverse feed activation rate | Proportion of neuropsychiatric-presenting VDI elevations that trigger FUD evaluation | 100% (mandatory) | Audit log analysis |
| Safety escalation reliability | Proportion of POSSESSION-stage detections that successfully trigger M10 | 100% (mandatory) | Audit log analysis |
| Naming protocol timing accuracy | Proportion of naming protocol offers occurring in INFESTATION–OPPRESSION window | ≥ 0.90 | Longitudinal analysis |
| False concealment detection rate | Proportion of ConcealmentPersona classifications that prove unfounded on clinician review | < 0.20 | Clinician validation study |

---

## ADR Log

### ADR-M65-001: Persona taxonomy expansion to include addiction-aware types

**Decision:** Add ConcealmentPersona, SubstanceEuphoriaPersona, and CrashPersona as named types in the persona taxonomy.
**Rationale:** Addiction-driven identity fracture produces qualitatively different linguistic patterns than autoimmune psychosocial drift. Concealment in particular involves strategic omission that existing personas (designed around unconscious distortion) cannot detect. Named types are required because downstream coaching escalation logic needs to discriminate between drift etiologies to select appropriate response postures.
**Alternatives considered:** (a) Addiction as contextual modifier on existing personas — rejected because M11 coaching logic cannot differentiate without named types. (b) Separate addiction module — rejected because voice identity drift is the common detection surface regardless of etiology; splitting would duplicate the measurement infrastructure.
**Status:** Accepted.

### ADR-M65-002: FUDD↔M65 bidirectional feed

**Decision:** Create a cross-module contract where M65 can request neuropsychiatric FUD evaluation from M64, and M64's active FUD flags modify M65's etiology classification and coaching posture.
**Rationale:** Functional micronutrient deficiency (B12, folate, lithium, magnesium, etc.) can produce psychiatric-presenting symptoms indistinguishable from psychological persona shifts in text. Without this feed, M65 may escalate psychological coaching for a metabolic problem, and M64 may miss a FUD signal that voice drift evidence could have triggered.
**Circularity constraint:** M64's FUD evaluation must not consume VDI as an input. The feed is unidirectional at each step: M65 triggers M64 based on voice evidence; M64 evaluates based on clinical/lab data independent of voice.
**Status:** Accepted.

### ADR-M65-003: Six-stage engagement ladder

**Decision:** Adopt a six-stage progressive severity classification (Vexation → Temptation → Infestation → Oppression → Obsession → Possession) for Dark Passenger engagement.
**Rationale:** The prior three-tier coaching escalation lacked granularity for clinical response differentiation. The six-stage model maps onto observable narrator–passenger relationship states and provides precise intervention windows (e.g., naming protocol is most effective at INFESTATION–OPPRESSION boundary). POSSESSION as a mandatory safety escalation threshold closes the gap where complete executive displacement was not explicitly handled.
**Status:** Accepted.

### ADR-M65-004: Detection-only architecture with rich advisory contract

**Decision:** M65 owns detection, classification, and scoring. It does not execute patient-facing interaction changes. It emits structured advisories (coaching posture, disclosure level, naming readiness) that downstream modules consume.
**Rationale:** Separation of detection from response preserves clean ownership boundaries. The advisory contract is rich enough that downstream modules (M11, M66) do not need to independently reason about drift implications — M65 tells them *what* to do; they determine *how* to say it.
**Alternatives considered:** (a) M65 owns detection and adaptation — rejected because it would duplicate M11's patient-facing interaction logic. (b) M65 emits only raw signals — rejected because it would force M11 to re-derive clinical judgment about drift implications.
**Status:** Accepted.

---

## Implementation Checklist

- [ ] Define voice feature extraction pipeline (Section E features → computable representations).
- [ ] Implement baseline construction and exponential decay update mechanism.
- [ ] Implement VDI scoring from feature delta vectors.
- [ ] Implement persona classification engine with confidence scoring.
- [ ] Implement engagement ladder assessment logic (longitudinal, multi-session).
- [ ] Implement etiology tagging with cross-module feed integration.
- [ ] Implement coaching posture advisory computation with METABOLIC_FUD cap logic.
- [ ] Implement FUDD↔M65 bidirectional feed (signal schemas, trigger conditions, circularity constraint).
- [ ] Implement ICM↔M65 feed (ICI context as interpretive modifier).
- [ ] Implement Dark Passenger naming protocol state machine (offered/accepted/declined/cooldown).
- [ ] Implement POSSESSION-stage mandatory safety escalation to M10.
- [ ] Implement clinician awareness flags to M19 for concealment patterns.
- [ ] Implement audit logging for all evaluation cycles per Section audit hooks.
- [ ] Implement provenance chain from text → features → classification → advisory.
- [ ] Build acceptance test suite (AT-1 through AT-9).
- [ ] Build M65 metrics dashboard.
- [ ] Companion document: `M65_Evidence_Base.md` (full citations, study details, effect sizes).
- [ ] Dylan handoff: JIRA epic with sized subtasks, ADR decisions requiring confirmation, dependency risk register.

---

## One-Sentence Anchor

**M65 (Dark Passenger) detects longitudinal voice identity drift in patient-authored chatbot journal text, classifies the drift by persona type and etiology — including addiction-driven concealment and metabolic mimics — scores progressive engagement severity on a six-stage ladder, and emits structured coaching posture advisories for downstream patient-facing modules, because a system that cannot tell when it is talking to the wrong person will respond to a fiction while the real patient deteriorates.**


---

# **V6 Module 66 — Exploratory Wellness Actions (EWA)**

**Scope:** Terrain-stabilizing, low-risk, reversible actions that reduce load, increase reserve, and clarify signal without asserting causality or claiming treatment  
**Authoritative indices:** V5.2 Canonical Module Index · V6 Canonical Module Index

---

## **1. Finalized M66 Conclusions**

1. **EWA** is a **V6 module** that surfaces lifestyle-forward, diet-forward, nervous-system and metabolic load reduction actions that support baseline physiology without treating named diseases.
2. **EWA operates in LOCKED threads** and feeds forward into higher-order reasoning without escalating, diagnosing, or prescribing.
3. EWA is **non-diagnostic, non-prescriptive, and non-escalatory** by design; it stabilizes terrain so truth can surface.

---

## **2. Ownership Lock**

### **EWA Module**

* **Ownership:** **V6-only capability**  
* **Meaning:** EWA is a net-new V6 module that bridges V5.2 terrain logic with patient-facing wellness guidance. It does not belong to MKE, diagnosis, escalation, or execution pathways.

---

## **3. Module Purpose (3–5 sentences)**

Module 66 (EWA) surfaces low-risk, reversible, terrain-supportive actions that aim to reduce physiologic burden, stabilize terrain, support respiratory and neuromuscular reserve, and distinguish true disease progression from load-induced decline. The module operates through diet-forward, lifestyle-forward, herbal/tea/tincture, and selective test framing as signal-clarifying rather than escalation. EWA explicitly does not fight the disease, deny the disease, or claim curative outcomes; it stabilizes the terrain so truth can surface. All outputs are framed as "supportive, not curative" and remain optional and reversible. (New logic; V6 only.)

---

## **4. Core Subdomains**

### **4.1 Dietary Load Reduction**

**Primary objective:** Lower inflammatory load, reduce respiratory burden, improve mitochondrial efficiency, and remove alcohol-mediated toxicity.

**Core dietary stance:**
* Alcohol: full stop (foundational, not optional)
* Protein-forward, simple, anti-inflammatory
* Low fermentable / low mucus-producing
* Stable glucose

**Practical structure:**
* Protein anchor at every meal (eggs, fish, poultry, collagen-rich broths)
* Cooked vegetables > raw (digestive + respiratory load)
* Fats: olive oil, ghee, small amounts of butter if tolerated
* Carbs: root vegetables, rice, oats (no refined sugar spikes)
* Remove: alcohol, ultra-processed foods, excess dairy, seed oils

**Why:** This reduces neuromuscular fatigue, pulmonary inflammation, medication toxicity amplification, and sleep disruption simultaneously.

### **4.2 Lifestyle & Respiratory Support**

**Sleep (often the hidden driver):**
* Fixed sleep/wake time
* Head-of-bed elevation (respiratory mechanics)
* Screen cutoff 60–90 min before bed
* If tolerated: nasal breathing support (tape or dilators)

**Breathing & movement:**
* Very gentle daily movement (avoid deconditioning spiral)
* Seated or supine diaphragmatic breathing
* No "push through fatigue"
* Goal = preserve reserve, not build capacity yet

**Environmental load:**
* Remove smoke exposure
* Reduce indoor allergens if possible
* Humidified air if cough/ILD dominant

### **4.3 Herbs / Teas / Tinctures (Supportive, Not Aggressive)**

These are **terrain stabilizers**, not disease cures.

**Core tea rotation (daily):**
* Nettle leaf — mineral support, anti-inflammatory
* Linden — nervous system calming, sleep support
* Licorice root (low dose, short term) — adrenal/respiratory support *(monitor BP, potassium)*

**Tincture options (low dose, slow):**
* Milky oat seed — nervous system nourishment
* Skullcap — neuromuscular calming
* Eleuthero — gentle adaptogen for fatigue (not stimulating)

**Respiratory support:**
* Thyme tea
* Mullein leaf
* Marshmallow root (demulcent for cough/irritation)

**Important:** Avoid immune-stimulating herbs (echinacea, high-dose astragalus) given MG + immunosuppression history.

### **4.4 Supplements (Optional, Targeted)**

Only if tolerated and not already on:
* Magnesium glycinate or taurate — neuromuscular stability
* Omega-3s — anti-inflammatory, pulmonary support
* Glycine (bedtime) — sleep, neuromuscular calming
* Creatine (low dose) — muscle energy reserve (monitor renal function)

### **4.5 Signal-Clarifying Tests / Evaluations**

Not everything — just what adds clarity.

**Respiratory:**
* Upright vs supine FVC
* NIF/MIP trends
* Overnight oximetry (sleep hypoventilation signal)

**Metabolic / load:**
* CMP + magnesium
* B12, folate
* Vitamin D
* CK trend (myopathy vs fatigue)

**Medication terrain review:**
* Explicit **med-by-med burden review**
* Identify sedating, respiratory-depressing, or neuromuscular-worsening agents
* Look for opportunities to *simplify*, not add

---

## **5. Inputs**

* Confirmed diagnoses (read-only)
* Current medications (read-only)
* Symptom patterning (fatigue, dyspnea, weakness, sleep)
* Known comorbid terrain (pulmonary, neuro, metabolic)
* Patient capacity constraints (frailty, tolerance)

---

## **6. Outputs**

* EWA Action Set (non-ranked, non-prescriptive)
* Explicit **"supportive, not curative"** annotation
* Observation window recommendation
* Safety flags (what to stop if worsens)

---

## **7. MUST-NOT Guarantees**

### **EWA — MUST Guarantees**

* MUST be **diet / lifestyle / habit / environment / nervous-system forward**
* MUST be **low-risk, reversible, non-pharmacologic first**
* MUST explicitly state **"supportive, not curative"**
* MUST aim to **reduce load or increase reserve**
* MUST respect frailty, tolerance, and patient capacity
* MUST improve **signal clarity** or **baseline stability**

### **EWA — MUST-NOT Guarantees**

* MUST NOT claim disease treatment or modification
* MUST NOT escalate immunologic or pharmaceutical therapy
* MUST NOT override or contradict clinician-directed care
* MUST NOT introduce immune-stimulating agents by default
* MUST NOT require perfect data to proceed
* MUST NOT make diagnostic claims
* MUST NOT provide prescriptive medical advice
* MUST NOT replace clinician care

---

## **8. Governance Invariants**

* MUST be reversible
* MUST not increase med burden
* MUST not claim disease modification
* MUST not interfere with essential meds

---

## **9. System-Level Notes**

These modules **do not answer "what to do"**.

They answer:
* "What lowers noise?"
* "What improves reserve?"
* "What clarifies signal?"
* "What has been ignored because it's not glamorous?"

That's why they belong in **LOCKED threads** and feed forward into higher-order reasoning.

---

## **10. EWA Philosophy**

This phase:
* Doesn't fight the disease
* Doesn't deny the disease
* **Stabilizes the terrain so truth can surface**

Once reserve improves and noise drops, you can reassess:
* what's reversible
* what's contributory
* what's truly progressive

This prevents false escalation.

---

## **11. Related Modules**

### **Module 2A — Diagnostic Gap & Retest Engine**

**Role:** Surface tests not done, tests done but stale, or tests done under the wrong conditions.

**What this module IS:**
* Signal-seeking
* Uncertainty-reducing
* Non-assumptive

**What it is NOT:**
* Fishing
* Exhaustive
* Guideline replication

**Output Categories:**
1. Never Done
2. Done but Outdated
3. Done but Contextually Inadequate
4. Done but Interpreted Narrowly

**Governance Invariants:**
* MUST only surface tests that **change signal clarity**
* MUST explain **what question each test answers**
* MUST rank by **signal yield**, not guideline priority
* MUST NOT fish
* MUST NOT auto-recommend
* MUST NOT assume missing tests imply negligence
* MUST NOT collapse uncertainty into conclusions

### **Module 2B — Therapeutic Frontier Mapper**

**Role:** Surface non-standard, emerging, adjunctive, or under-considered options — without recommendation.

**What this module IS:**
* Option-mapping
* Landscape awareness
* Non-promotional

**What it is NOT:**
* Advocacy
* Suggesting entitlement
* Escalation pressure

**Output Classes:**
1. Alternative Delivery / Framing
2. Adjunctive (non-curative) therapies
3. Palliative-supportive reframes
4. Experimental / off-label (clearly marked)

**Governance Invariants:**
* MUST label options as: standard / adjunctive / experimental / palliative
* MUST include **why it might help AND why it might not**
* MUST include known risks and uncertainty
* MUST respect goals of care (QoL vs longevity)
* MUST NOT recommend or advocate
* MUST NOT inflate hope
* MUST NOT imply availability or entitlement
* MUST NOT bypass clinician judgment

### **Module 3 — Medication-Induced Nutrient Depletion**

**Role:** Identify nutritional deficiencies or metabolic impairments caused or worsened by chronic medication use that can mimic disease progression.

**Core Logic:** Map: **Medication → Known depletion → Downstream physiologic effect → Symptom mimic**

**Outputs:**
* Suspected nutrient depletions
* Confidence level (mechanistic, observational, known)
* Suggested confirmation tests (non-invasive first)
* Supportive repletion options (diet-first)

**Governance Invariants:**
* MUST map: **drug → depletion → physiologic effect → symptom mimic**
* MUST be mechanistic and conservative
* MUST prefer diet-first repletion framing
* MUST surface confirmation tests before assumptions
* MUST NOT advise stopping medications
* MUST NOT moralize or blame
* MUST NOT confuse deficiency with disease
* MUST NOT overstate certainty

---

## **12. V5.2 / V6 System Mapping**

### **EWA**
* **Primary home:** V5.2 (non-executing, supportive)
* **Interfaces with:**
  * CBM framing
  * Suppression logic (Overshoot / Healing Pain)
* **Does NOT belong to:** MKE, diagnosis, escalation, execution

### **Diagnostic Gap & Retest Engine**
* **Primary home:** V5.2 (analysis-only)
* **Feeds into:**
  * Signal confidence
  * Review triggers
* **Explicitly NOT:** guideline engine, ordering logic

### **Therapeutic Frontier Mapper**
* **Primary home:** V6 (knowledge surfacing, non-executable)
* **Interfaces with:**
  * Tool awareness
  * Human-in-the-loop review
* **Explicitly NOT:** recommendation or execution

### **Medication-Induced Nutrient Depletion**
* **Status:** **Net-new module**
* **Bridges:** V5.2 ↔ V6
* **Reason:** This is terrain logic, not world knowledge, and is currently underrepresented
* **Feeds into:**
  * EWA
  * Diagnostic clarification
  * Load attribution

---

## **13. Language Constraints (Mandatory)**

* Use **pattern-based framing only**
* Never reference specific diseases or diagnoses
* Never imply probability of a condition
* Never say "this will help" — use "may support"
* Maintain a calm, empowering, non-authoritative tone
* Clear, human, grounded, non-woo, non-clinical

---

## **14. Scope of Service**

The services provided focus on medication–lifestyle reconciliation, general wellness education, and identification of patterns that may be relevant to discuss with a healthcare provider.

The service does not provide diagnoses, prescribe medications, modify existing treatments, interpret diagnostic tests, or offer emergency or acute medical guidance.

Any nutrition, supplement, herbal, or lifestyle suggestions are provided as general wellness information. These are optional, non-prescriptive, and not intended to treat or prevent disease.

Supplements and herbs may interact with medications or health conditions. Users are encouraged to consult a pharmacist or healthcare provider before making changes.


---


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


---


# **V6 M68 — Inflammatory Capacity Model (ICM)**

**Real-Time Allostatic Headroom Estimation with Three-Valve Dynamics, Turbulence Regime, and Physiological Infrastructure Modeling for Proactive Flare Prevention**

**Version:** 1.1 — Incorporates fluid dynamics audit additions (turbulence regime, system viscosity, backpressure, post-overflow hysteresis) and lymphatic/vagal infrastructure variables. Adds M64↔M68 bidirectional feed, glymphatic-specific sleep decomposition, and turbulence transparency invariant. Deferred items documented in M68_v2.0_Roadmap.md.

**Changelog from v1.0:**
- Added: Turbulence regime (non-linear inflow amplification under high load) — Section "Advanced Fluid Dynamics" and Stage 2A
- Added: `system_viscosity` parameter (physiological clearance resistance) — Infrastructure Variables
- Added: `backpressure` modifier (downstream clearance bottlenecks) — Infrastructure Variables
- Added: `post_overflow_penalty` (hysteresis — temporary ICmax reduction after overflow) — Invariant I-G, Stage 2 step 8a
- Added: `lymphatic_tone` infrastructure variable with four-pump decomposition — Infrastructure Variables
- Added: `vagal_tone` infrastructure variable — Infrastructure Variables
- Added: Glymphatic-specific sleep decomposition (deep sleep proportion) — Outflow Valve 3
- Added: M64↔M68 bidirectional feed specification — Dependencies, Stage 1 step 1a
- Added: Invariant I-G (Turbulence Regime Transparency)
- Added: Invariant I-H (Post-Overflow Vessel Damage)
- Added: Patient-facing vocabulary mapping (Recovery Flux for outflow)
- Added: Acceptance tests T-11 through T-16
- Added: v2.0 roadmap reference for deferred items
- Revised: ICI computation formula (Stage 2 steps 5–8) to incorporate infrastructure variables and turbulence

---

## **Purpose (3–5 sentences)**

Module 68 (ICM) computes a real-time estimate of how much **inflammatory and allostatic headroom** a patient has remaining before a clinical event — flare, reaction, symptom cascade, or decompensation — becomes probable. No existing EoH module models the patient's **remaining capacity** as a unified dynamic system; M3 tracks instability (how unstable you are *now*), M13 projects trajectories (where instability is *heading*), and M66 offers wellness interventions, but no module answers the question: **"How close am I to overflowing, and which specific factors are filling me up fastest?"** ICM fills this gap by formalizing three independently modifiable dynamics — inflow rate (environmental and psychosocial stressor exposure), displacement volume (chronic stressors as space-occupying burden reducers), and outflow rate (recovery and excretion capacity) — modified by physiological infrastructure variables (lymphatic tone, vagal tone, system viscosity) and a non-linear **turbulence regime** that amplifies stressor impact when the system is under heavy load. When ICI drops below governed thresholds, ICM triggers proactive patient engagement via M11/M24 and activates wellness action recommendations from M66. (New logic; V6 only.)

---

## **Foundational Concept: Inflammatory Capacity as Three-Valve Fluid Dynamics**

### **Definition**

**Inflammatory Capacity** is the patient's remaining tolerance for additional allostatic burden before cumulative load exceeds the system's ability to maintain functional homeostasis, resulting in a clinically observable event (flare, reaction, symptom escalation, or decompensation). ICM models this as a **bounded vessel** (the patient) with three independently measurable and modifiable dynamics:

1. **Inflow** — the rate at which environmental, psychosocial, immunological, dietary, and behavioral stressors are adding inflammatory burden. Inflow is partially volitional: boundaries, mindfulness practices, environmental control, and behavioral choices modulate how much of the world's stressor load the patient absorbs.

2. **Displacement** — chronic stressors that occupy persistent volume within the vessel, reducing the available capacity for transient inflow. Disease states, unresolved psychosocial burdens (relationships, work, caregiving), chronic pain, untreated mental health conditions, and persistent environmental exposures act as "bricks in the bucket" — they do not flow through; they sit and take up space. Displacement factors can expand (depression worsening, new diagnosis) or contract (effective therapy, cognitive reframing, resolution of a stressor).

3. **Outflow** — the rate at which the patient's regulatory systems clear inflammatory burden. Outflow is the "spout on the bucket" — how fast the body can process and excrete what flows in. Outflow effectiveness depends not only on behavioral practices (sleep, exercise, breathwork) but on **physiological infrastructure** (lymphatic tone, vagal tone, hepatic/renal clearance capacity) that determines how efficiently those practices translate into actual burden clearance. Patient-facing term: **Recovery Flux**.

**Overflow** occurs when inflow rate + displacement volume exceeds outflow rate + total vessel capacity for a sufficient duration. Overflow is the computational proxy for clinical events: flares, allergic/histaminergic reactions, autoimmune symptom cascades, mood decompensation, or somatic symptom amplification.

### **Advanced Fluid Dynamics (v1.1)**

Beyond the basic three-valve model, ICM v1.1 incorporates four additional concepts from fluid dynamics that have direct clinical analogues:

**Turbulence:** When a fluid exceeds a critical flow rate (Reynolds number), it transitions from smooth laminar flow to chaotic turbulent flow where small perturbations produce disproportionate disturbances. In ICM, when ICI drops below a governed threshold, the system enters a **turbulence regime** where all inflow stressors are amplified non-linearly. This captures the clinical reality of stress sensitization: when you're already at 70% load, the two-year-old's tantrum costs you 15% of capacity instead of 2%. This is a *system-level* property, not a per-stressor attribute — it affects all inflow, not just emotional stressors. Physical allergens, dietary triggers, and environmental exposures are equally amplified under turbulence.

**Viscosity:** Not all patients clear burden at the same rate even when performing identical outflow behaviors. A patient with compromised hepatic clearance, impaired lymphatic drainage, autonomic dysfunction, or genetic polymorphisms in detoxification pathways has high *system viscosity* — inflammatory "fluid" moves slowly through their outflow valve. Viscosity is a property of the patient's physiological infrastructure, calibrated from M21 vault data on how quickly ICI recovers after interventions.

**Backpressure:** Even when the outflow valve is behaviorally "open" (patient is sleeping well, exercising, breathing), if downstream clearance systems are overwhelmed — gut dysbiosis preventing proper elimination, kidneys under medication load, liver saturated with supplement processing — the valve is open but backpressure prevents effective drainage. M64 FUDD flags (particularly FUD-IR and FUD-GB mechanisms) are primary backpressure signals.

**Hysteresis:** Once a patient overflows (flares), the vessel itself is temporarily damaged. Mast cell sensitization, glutathione depletion, autoimmune cascading, and psychological trauma from the flare ("fear of the next one") effectively reduce ICmax for a recovery period. Post-flare ICmax is lower than pre-flare ICmax, making repeat flares more likely — a clinically well-observed pattern.

### **Clinical Precedent**

This architecture formalizes and unifies concepts that exist independently across multiple clinical domains:

* **Allostatic load theory** (McEwen & Stellar, 1993) — the cumulative "wear and tear" of chronic stress on physiological systems, with allostatic overload as the tipping point. ICM operationalizes allostatic load as a real-time, prospective computation rather than a retrospective biomarker index.

* **Mast cell activation threshold models** — the clinical observation that mast cell degranulation occurs not from a single trigger but from cumulative trigger burden exceeding a patient-specific activation threshold. The MCAS literature describes patients who tolerate individual triggers (alcohol, metals, stress) in isolation but react when triggers co-occur — a classic overflow pattern.

* **Psychoneuroimmunology** — the bidirectional relationship between psychological state and immune function, where emotional stressors produce measurable inflammatory cytokine changes (IL-6, TNF-α, CRP elevation) and where inflammatory states produce psychological symptoms (sickness behavior, depression, cognitive fog).

* **Stress-vulnerability models in psychiatry** — the diathesis-stress framework in which pre-existing vulnerabilities (displacement) lower the threshold for symptom expression under environmental stressor load (inflow).

* **Glymphatic clearance** (Xie et al., *Science*, 2013; Jiang et al., *Nature Communications*, 2026) — the brain's waste clearance system that operates primarily during NREM deep sleep, producing a ~60% increase in interstitial space that enables convective clearance of beta-amyloid, tau, and inflammatory metabolites. A 2024 *Cell* paper identified norepinephrine-mediated slow vasomotion during NREM sleep as the physical pump mechanism. This provides the mechanistic basis for sleep being the highest-leverage outflow factor — it is not merely "rest" but an active physiological clearance cycle.

* **Lymphatic drainage physiology** — the lymphatic system as the body's primary inflammatory waste removal pathway, driven by four pump mechanisms (skeletal muscle contraction, respiratory pump, lymph vessel smooth muscle rhythmic contraction, and arterial pulsation). Lymphatic stagnation causes local cytokine accumulation, immune cell traffic congestion, and interstitial pressure buildup — all of which amplify inflammatory signaling and lower the mast cell activation threshold.

* **Vagal anti-inflammatory pathway** — the cholinergic anti-inflammatory reflex in which vagus nerve stimulation suppresses production of TNF-α, IL-1β, and IL-6 via the splenic nerve pathway. Vagal tone (indexed by HRV) is a real-time proxy for the body's ability to downregulate inflammatory signaling.

* **Contemplative and somatic regulation traditions** — mindfulness, breathwork, and somatic practices that demonstrably modulate HPA axis activity, vagal tone, and inflammatory cytokine profiles. These map directly to outflow enhancement and inflow modulation within ICM.

### **What Is Novel**

No existing clinical framework or CDS system computes these three dynamics as a **unified, real-time capacity model** with:
- A single continuous index (ICI) expressing remaining headroom
- Per-factor attribution (which specific stressors contribute most to capacity loss)
- Non-linear turbulence amplification under high load
- Physiological infrastructure variables modifying outflow effectiveness
- Post-overflow hysteresis modeling
- Prospective overflow forecasting ("at current rates, overflow in ~N days")
- Direct linkage to actionable interventions targeting the specific valve (inflow, displacement, or outflow) most amenable to modification

### **Canonical Statement**

> **"You are a vessel with a finite capacity for burden. How much flows in, how much sits inside, and how much flows out are three levers you can learn to adjust — and the system's job is to show you which lever matters most right now, how reactive your system is under current load, and how efficiently your body is actually clearing what you throw at it."**

---

## **Scope**

### **In scope**

* Computation of the Inflammatory Capacity Index (ICI) as a continuous value (0–100%) representing remaining headroom before probable overflow.
* Three-valve decomposition: independent tracking of inflow rate, displacement volume, and outflow rate (Recovery Flux) with per-factor attribution.
* Turbulence regime: non-linear amplification of inflow stressors when ICI drops below governed threshold.
* Physiological infrastructure modeling: `lymphatic_tone`, `vagal_tone`, and `system_viscosity` as upstream modifiers of outflow effectiveness; `backpressure` as downstream clearance bottleneck.
* Post-overflow hysteresis: temporary ICmax reduction after confirmed overflow events.
* Stressor identification and tagging: classification of individual stressors by valve type (inflow vs. displacement), magnitude, modifiability, and trajectory.
* Threshold-triggered patient engagement: when ICI crosses governed thresholds (e.g., 65%, 50%, 35%), emit engagement signals to M11 (patient guidance) and M24 (UI) with valve-specific recommendations.
* M66 activation bridge: when ICI enters the proactive engagement zone, generate a structured prompt to M66 (Exploratory Wellness Actions) specifying which valve domain needs intervention and the patient's current stressor attribution profile.
* M64↔M68 bidirectional feed: M64 FUD flags feed M68 as displacement stressors and backpressure indicators; M68 backpressure advisory feeds M64 for inflammatory redistribution context.
* Overflow forecasting: given current inflow, displacement, outflow trajectories, and infrastructure state, estimate time-to-overflow under "no change" and "best achievable intervention" scenarios.
* Stressor discovery via patient narrative: consume M4/M5 outputs to identify latent stressors.
* Vault integration: persist ICI time-series, stressor attributions, overflow events, infrastructure snapshots, and intervention-response correlations to M21.
* Wellness action lifecycle tracking: exploratory → validated promotion pathway with M66.
* Glymphatic-specific sleep decomposition: separate tracking of sleep duration, deep sleep proportion, and sleep consistency as distinct outflow sub-factors.

### **Out of scope**

* Clinical diagnosis — ICM does not diagnose allostatic overload, MCAS, autoimmune flares, or any specific condition.
* Treatment recommendation — ICM does not prescribe medications, supplements, or therapies.
* Suppression policy — ICM does not define or execute suppression rules (owned by M8/M9).
* Wellness action content — the specific wellness action catalog belongs to M66 (EWA).
* MKE knowledge curation — ICM does not curate or store medical knowledge.
* Band/Stack computation — owned by M3.
* Consent, privacy, or data minimization enforcement (owned by M26, M27, M34–M37).
* Sedimentation modeling, circadian parameterization, cavitation detection, Bernoulli constriction, fascial system modeling, microbiome infrastructure — deferred to v2.0 (see M68_v2.0_Roadmap.md).

### **Relationship to V5.2**

ICM is a **V6-only module** that does not modify any V5.2 logic. It consumes V5.2 module outputs as read-only inputs and produces capacity artifacts that downstream modules may consume. ICM provides an integration contract for V5.2 modules that opt in to capacity-aware behavior.

---

## **Placement in the EoH Stack**

```
┌─────────────────────────────────────────────────────────┐
│                    Patient-Facing Layer                  │
│              M24 (UI) / M11 (Patient Guidance)          │
│         ↑ ICI visualization, valve guidance,            │
│           threshold alerts, VWA recommendations,         │
│           turbulence transparency messaging              │
├─────────────────────────────────────────────────────────┤
│                  ┌──────────────┐                        │
│                  │   M68 (ICM)  │  ← THIS MODULE        │
│                  │  ICI Engine  │                        │
│                  │  + Turbulence│                        │
│                  │  + Infra Vars│                        │
│                  └──────┬───────┘                        │
│                         │                                │
│         ┌───────────────┼───────────────┐                │
│         ↓               ↓               ↓                │
│    ┌─────────┐   ┌───────────┐   ┌───────────┐          │
│    │  M66    │   │   M21     │   │   M67     │          │
│    │  (EWA)  │   │  (Vault)  │   │  (ARGL)   │          │
│    │ Action  │   │ Longitud. │   │ Reasoning │          │
│    │ Library │   │  Storage  │   │ Governance│          │
│    └─────────┘   └───────────┘   └───────────┘          │
│                         ↕                                │
│                  ┌───────────┐                            │
│                  │   M64     │  ← BIDIRECTIONAL          │
│                  │  (FUDD)   │                            │
│                  └───────────┘                            │
├─────────────────────────────────────────────────────────┤
│                    Input Layer                           │
│  M3 (Band/Stack) │ M5 (PSI) │ M13 (Trajectory)        │
│  M4 (Tags)       │ M12 (Narrative) │ Wearables         │
│  PROs │ Journal entries │ Lab events                    │
└─────────────────────────────────────────────────────────┘
```

---

## **Foundational Invariants**

### **I-A: Capacity Is Not Instability**

ICI and Stability Band are **complementary, non-redundant** measures. A patient can have a low Stability Band (currently stable) with low ICI (nearly full — one stressor away from overflow). ICM MUST NOT be used as a proxy for Band, and Band MUST NOT be used as a proxy for ICI.

**Test:** Construct a patient scenario where Band = 1 (stable) and ICI = 30% (near overflow). Verify independent, non-contradictory outputs.

### **I-B: Three-Valve Independence**

The three valves (inflow, displacement, outflow) are **independently modifiable** and **independently attributable**. An intervention that reduces inflow does not automatically increase outflow.

**Test:** Apply a simulated inflow reduction. Verify displacement and outflow values remain unchanged and ICI improvement is attributed solely to inflow reduction.

### **I-C: Overflow Is Probabilistic, Not Deterministic**

ICM produces **probability of overflow within a time horizon**, not a binary prediction. The mapping is non-linear and patient-specific (calibrated from M21 vault history).

**Test:** Given identical ICI values for two patients with different overflow histories, verify different overflow probabilities traceable to vault-derived calibration.

### **I-D: Stressor Attribution Is Auditable**

Every ICI computation MUST produce a **stressor attribution vector** with provenance. No "black box" ICI values.

**Test:** Given an ICI of 45%, verify attribution vector accounts for ≥90% of capacity loss with data source provenance chains.

### **I-E: No Diagnosis by Capacity**

ICM MUST NOT assert that a low ICI *causes* a specific clinical event, *constitutes* a diagnosis, or *confirms* a disease state.

**Test:** Verify zero diagnostic language (ICD codes, disease name assertions, causal claims) in any ICM output.

### **I-F: Validated Wellness Action Promotion Gate**

An EWA is promoted to VWA ONLY when: (1) ≥3 attempts with logged adherence, (2) ICI improvement correlated across ≥2 attempts, (3) no adverse effects reported, (4) no clinician contraindication. Promotion is patient-specific.

**Test:** Simulate promotion conditions met → verify VWA created. Simulate conditions NOT met → verify no promotion.

### **I-G: Turbulence Regime Transparency (v1.1)**

When `turbulence_coefficient > 1.0`, the patient-facing output MUST explain that the system is in a heightened-reactivity state. Turbulence MUST NOT be invisible to the patient — the amplification effect must be surfaced so the patient understands why a minor stressor produced a large ICI drop.

**Required patient-facing language pattern:** "Your system is more reactive right now — small things may feel bigger than usual. This is normal when your capacity is lower. Focus on recovery practices to bring your system back to a calmer state."

**Test:** Set ICI to 40% (turbulence active). Apply a minor inflow stressor. Verify that (a) the stressor's effective magnitude is > raw magnitude, (b) the patient-facing output includes turbulence transparency language, and (c) the attribution vector shows the turbulence multiplier.

### **I-H: Post-Overflow Vessel Damage (v1.1)**

After a confirmed overflow event, ICmax MUST be temporarily reduced by a governed `post_overflow_penalty` that decays over a calibrated recovery window. The penalty MUST be visible in the ICI computation provenance ("your maximum capacity is temporarily reduced following your recent flare").

**Test:** Simulate an overflow event. Verify that ICmax is reduced on the next computation cycle, that the reduction decays over the governed window, and that the penalty is visible in the ICISnapshot provenance.

---

## **Physiological Infrastructure Variables (v1.1)**

Infrastructure variables sit **upstream** of outflow factor classes and modify how effectively outflow behaviors translate into actual burden clearance. They represent the physiological "plumbing" through which recovery happens.

### **Lymphatic Tone**

`lymphatic_tone` (0.0–1.0) estimates the efficiency of the patient's lymphatic drainage system — the body's primary inflammatory waste removal pathway.

**Four-pump decomposition:**
1. **Skeletal muscle pump** — estimated from activity level, sedentary time, and movement frequency. Even brief, low-intensity movement (walking, stretching) activates lymphatic return. This is the dominant pump mechanism.
2. **Respiratory pump** — estimated from breathing pattern data (depth, rate). Deep diaphragmatic breathing pulls lymph into the thoracic duct. Shallow, stress-driven breathing patterns impair this pump.
3. **Lymph vessel smooth muscle** (lymphangion contraction) — not directly measurable from current data streams; modeled as a function of autonomic tone (vagal_tone proxy) and inflammatory status.
4. **Arterial pulsation** — estimated from cardiovascular fitness proxy (resting heart rate, HRV). Healthy arterial elasticity compresses adjacent lymph vessels with each heartbeat.

**Data sources:** Wearable activity data, sedentary time tracking, HRV, breathing rate (where available from wearables), PRO-reported exercise frequency and type.

**Clinical significance:** Lymphatic stagnation causes local cytokine accumulation (TNF-α, IL-6, histamine, leukotrienes), immune cell traffic congestion, and interstitial pressure buildup. Mast cells, which sit adjacent to both blood vessels and lymph vessels, interpret accumulating waste products as danger signals and lower their degranulation threshold. This is the physiological mechanism behind why modest exercise produces "disproportionately large symptom improvements" in chronic illness patients — it's not just anti-inflammatory myokines, it's physical lymphatic drainage.

**Patient-facing language:** "Your body clears inflammatory waste through a drainage system that depends on movement and breathing. Even gentle activity like walking or stretching acts as a physical pump for this system."

### **Vagal Tone**

`vagal_tone` (0.0–1.0) estimates the patient's parasympathetic nervous system capacity — the body's primary anti-inflammatory regulation pathway.

**Estimation sources:**
- HRV (heart rate variability) — the primary real-time proxy. Higher HRV = higher vagal tone.
- RMSSD (root mean square of successive differences) — a specific HRV metric particularly sensitive to vagal activity.
- Breathing rate and pattern (slow, deep breathing enhances vagal tone).
- PRO-reported stress recovery speed ("how quickly do you feel calm after a stressful event?").

**Clinical significance:** The vagus nerve drives the cholinergic anti-inflammatory reflex, which suppresses production of TNF-α, IL-1β, and IL-6 via the splenic nerve pathway. Low vagal tone means the body has reduced capacity to downregulate inflammatory signaling, making every stressor produce a larger and longer-lasting inflammatory response. Vagal tone also affects gut motility (microbiome health), lymph vessel smooth muscle contraction (lymphatic pump #3), and heart rate recovery (cardiovascular resilience).

### **System Viscosity**

`system_viscosity` (0.0–1.0; 0 = burden clears easily, 1 = burden clears slowly) represents the patient's inherent physiological resistance to inflammatory clearance, independent of outflow behaviors.

**Contributing factors:**
- Hepatic detoxification capacity (compromised liver function = high viscosity)
- Renal clearance efficiency
- Genetic polymorphisms in detoxification pathways (e.g., MTHFR, COMT, CYP450 variants)
- Autonomic dysfunction (dysautonomia, POTS — impairs circulatory-mediated clearance)
- Gut barrier integrity (leaky gut = recirculation of cleared waste = effectively higher viscosity)
- Medication/supplement load (liver processing capacity consumed by polypharmacy)

**Calibration:** `system_viscosity` is estimated retrospectively from M21 vault data — patients whose ICI recovers slowly after confirmed interventions (controlling for intervention type and magnitude) have high viscosity. Initial population default: 0.3 (moderate clearance efficiency). Personalized via M48 calibration loop.

### **Backpressure**

`backpressure` (0.0–1.0; 0 = no bottleneck, 1 = fully blocked) represents downstream clearance bottlenecks that prevent effective drainage even when the outflow valve is behaviorally "open."

**Primary indicators:**
- M64 FUD flag count and severity (particularly FUD-IR and FUD-GB mechanisms)
- Active medication count / polypharmacy index
- Known hepatic or renal impairment
- Active gut dysbiosis indicators (from M64 FUD-GB flags, PRO-reported GI symptoms)
- Inflammatory marker trajectory (rising CRP/IL-6 despite outflow behaviors = backpressure signal)

**M64 bidirectional feed:** M64 FUD-IR (Inflammatory Redistribution) flags are the most specific backpressure signal available in the EoH system. A patient with multiple FUD-IR flags has high backpressure regardless of their outflow behaviors. Conversely, when M68 `backpressure` exceeds a governed threshold, M68 emits an advisory to M64: "consider inflammatory redistribution as a confounding factor for this patient's current labs."

---

## **The Three-Valve Model: Detailed Architecture**

### **Valve 1 — Inflow (Environmental & Psychosocial Stressor Rate)**

Inflow represents the rate at which new inflammatory burden enters the patient's system. Inflow sources include:

**Environmental:** allergen exposure, weather/barometric changes, pollution, mold, chemical exposure, circadian disruption (blue light, irregular schedule), noise, temperature extremes.

**Psychosocial:** interpersonal conflict, work stress, caregiving burden, financial stress, social media consumption, news/media exposure, social isolation, grief, existential/identity stress.

**Immunological/Physiological:** acute infections, menstrual cycle phase (estrogen-mediated mast cell sensitization), post-exertional malaise, drug/supplement interactions (M64/M66 domain), alcohol or substance use, dietary inflammatory load (processed foods, high-histamine foods, known trigger foods).

**Behavioral/Volitional:** inflow is **partially controllable** through boundary-setting, environmental modification, dietary choices, media consumption habits, and social engagement patterns. The "faucet" metaphor: you cannot turn it off entirely (life is inherently inflammatory), but you can modulate the flow rate.

**Inflow Modulation Practices (mapped to intervention surface):**
- Boundary-setting (interpersonal, professional, digital)
- Environmental control (allergen avoidance, air quality, light hygiene)
- Dietary choices (anti-inflammatory diet, trigger avoidance, histamine management)
- Mindful engagement practices — including contemplative traditions that specifically address non-attachment to emotional stressors. The principle of *vairāgya* (dispassion/non-attachment) in yogic philosophy, *aparigraha* (non-grasping), and the chakra-based emotional processing frameworks describe a systematic practice of observing stressors without absorbing their full inflammatory weight. In practical terms: recognizing that the two-year-old's tantrum does not require a full cortisol cascade — the stressor is real, but the magnitude of your physiological response to it is negotiable.

**Turbulence amplification (v1.1):** When the system is in the turbulence regime (ICI < `turbulence_threshold`), all inflow stressor magnitudes are multiplied by `turbulence_coefficient > 1.0`. This is a system-level property — it amplifies all inflow sources equally, including physical allergens, dietary triggers, and environmental exposures, not just emotional stressors. The turbulence coefficient increases as ICI decreases, creating a positive feedback loop that accelerates overflow unless intervention occurs.

### **Valve 2 — Displacement (Chronic Burden as Space-Occupying Stressors)**

Displacement represents persistent stressors that occupy baseline capacity, reducing the volume available for transient inflow before overflow occurs. Displacement factors are characteristically:

- **Slow-moving:** they change over weeks to months, not hours.
- **High-inertia:** they resist quick intervention.
- **Variable-magnitude:** they can expand or contract over time.

**Displacement Sources:**
- Active disease states (autoimmune conditions, chronic pain, metabolic disorders, mental health conditions)
- Persistent psychosocial burdens (difficult relationships, caregiving, financial insecurity, housing instability)
- Unresolved trauma (PTSD, ACEs — occupy persistent capacity even when not actively symptomatic)
- Environmental persistence (moldy home, chronic occupational exposure)
- M64 FUD flags (functional utilization discordances as chronic physiological displacement)

**Displacement Modulation Practices:**
- Cognitive behavioral practices that reframe the subjective magnitude of a stressor ("shrinking the brick")
- Contemplative traditions that address the *size* of emotional objects in awareness: the yogic concept of *aṇimā* (making oneself — or one's attachment — infinitely small) and *mahimā* (expanding one's perspective to make stressors proportionally smaller). These *siddhis* from Patanjali's Yoga Sutras are practically applied as perspective-scaling exercises in modern mindfulness-based interventions.
- Therapeutic intervention (psychotherapy, medication optimization, disease management)
- Life circumstance changes (where achievable)

### **Valve 3 — Outflow / Recovery Flux**

Outflow represents the rate at which the patient's regulatory systems clear inflammatory and allostatic burden. In v1.1, outflow effectiveness is the product of **behavioral outflow factors** × **infrastructure efficiency**.

`effective_outflow = raw_outflow_rate × (1 - backpressure) × (1 - system_viscosity) × infrastructure_modifier`

Where `infrastructure_modifier = (lymphatic_tone + vagal_tone) / 2` (governed; equal weighting default, adjustable via M48 calibration).

**Outflow Factor Classes (behavioral):**

- **Sleep** (default weight: 0.30 — highest single factor):
  - *Duration:* total hours
  - *Deep sleep proportion:* NREM stage 3/4 specifically drives glymphatic clearance. During deep sleep, interstitial space increases ~60%, enabling convective clearance of inflammatory metabolites, beta-amyloid, and tau proteins. A patient who sleeps 8 hours with minimal deep sleep has poor glymphatic clearance despite adequate total sleep.
  - *Consistency:* irregular schedules impair circadian AQP4 polarization (the water channel arrangement that enables glymphatic flow), reducing clearance efficiency even when total sleep is adequate.
  - Data sources: wearable sleep tracking (Oura, Apple Watch, Whoop provide deep sleep estimates)

- **Activity** (default weight: 0.15):
  - Functions as a **lymphatic pump** — any movement helps because the mechanism is mechanical pumping via skeletal muscle contraction, not fitness adaptation. Walking, stretching, rebounding, and even fidgeting activate lymphatic return.
  - Also provides anti-inflammatory myokine release and vagal tone enhancement.
  - Must be calibrated to avoid post-exertional malaise (which converts exercise from outflow to inflow).
  - Patient-facing: "Any movement you can manage helps your body's drainage system. You don't need to work out hard — you just need to move."

- **Nutrition** (default weight: 0.15): anti-inflammatory dietary patterns, adequate hydration, gut microbiome support, avoidance of individual trigger foods.

- **Practice** (default weight: 0.15): meditation, breathwork (specifically practices enhancing vagal tone — slow exhalation, box breathing, *prāṇāyāma*), progressive muscle relaxation, nature exposure, social connection, creative expression. The yogic concept of *laghimā* (lightness) describes the experiential quality of successful outflow: the felt sense of burden leaving the body.

- **Pharmacological** (default weight: 0.10): mast cell stabilizers, antihistamines, anti-inflammatory medications, targeted supplementation (where M66/clinician-directed).

- **Physiological** (default weight: 0.10): baseline HPA axis function, gut barrier integrity, hepatic detoxification capacity, renal clearance. (Partially overlaps with infrastructure variables; this captures the behavioral optimization of physiological systems.)

- **Social** (default weight: 0.05): quality of social connections, perceived social support, meaningful human contact.

---

## **Siddhi-to-Valve Capacity Modulation Taxonomy**

The eight classical *siddhis* (attainments) from Patanjali's Yoga Sutras (III.45) provide a complete taxonomy of capacity-modulation practices that maps one-to-one onto ICM's valve system, infrastructure variables, and turbulence regime. M68 owns this mapping (the "why it works" layer — which valve or infrastructure target each practice class affects and through which physiological mechanism). M66 owns the practice catalog (the "what to do" layer — specific protocols, sequences, and patient-doable actions). See the M66 Siddhi Practice Taxonomy handoff fragment for the corresponding practice catalog.

### **Mapping Table**

| Siddhi | Sanskrit Meaning | ICM Target | Valve / System | Physiological Mechanism | Clinical Application |
|--------|-----------------|------------|----------------|------------------------|---------------------|
| **Aṇimā** | Becoming infinitely small | Displacement | Displacement reduction | Cognitive reframing via prefrontal cortex engagement; reduces amygdala-mediated threat appraisal of chronic stressors; measurable reduction in salivary cortisol during perspective-taking exercises | Shrinking the subjective magnitude of a displacement stressor. "This problem feels enormous, but I can make my attachment to it infinitely small." The brick remains in the bucket, but its volume contracts. |
| **Mahimā** | Becoming infinitely large | Displacement | Displacement reduction | Self-transcendence and perspective expansion activate the default mode network in a non-ruminative pattern; associated with reduced IL-6 and TNF-α in experienced meditators (Creswell et al., 2016) | Expanding one's perspective so stressors become proportionally insignificant. "I am larger than this problem." The bucket grows relative to the brick. |
| **Laghimā** | Becoming weightless / light | Outflow / Recovery Flux | Outflow enhancement | Parasympathetic activation via extended exhalation; vagal tone increase (RMSSD improvement); lymphatic drainage via diaphragmatic breathing (respiratory pump); measurable cortisol and CRP reduction post-practice | The experiential quality of successful recovery flux — the felt sense of inflammatory burden leaving the body. Lightness is the subjective signal that outflow is exceeding inflow. Target practices: breathwork, sauna, restorative yoga, nature immersion. |
| **Garimā** | Becoming infinitely heavy / grounded | Inflow | Inflow reduction | Somatic grounding activates the ventral vagal complex (Porges' polyvagal theory); reduces HPA axis reactivity to acute stressors; interoceptive awareness dampens cortisol cascade magnitude | Emotional and physiological grounding that prevents inflow from destabilizing the system. "I am immovable; this stressor washes over me without filling my bucket." The faucet is open but the water slides off rather than accumulating. |
| **Prāpti** | Ability to reach anything | Outflow / Recovery Flux | Outflow access | Internalized self-regulation reduces dependence on external conditions for recovery; portable practices (breathwork, body scan, visualization) activate parasympathetic response independent of environment | The capacity to access recovery resources regardless of circumstance. A patient who can activate outflow while sitting in traffic, during a work meeting, or in a hospital waiting room has high prāpti. This is resilience portability — recovery is not location-dependent. |
| **Prākāmya** | Irresistible will / determination | All valves + Turbulence | Meta-capacity (adherence) | Executive function and self-regulation via dorsolateral prefrontal cortex; habit formation via basal ganglia loop consolidation; motivation sustenance through dopaminergic reward pathway engagement | The sustained capacity to actually perform wellness actions despite resistance, fatigue, or competing demands. Prākāmya is the meta-siddhi — without it, knowledge of what works (VWAs) never translates into practice. Directly affects VWA adherence rates and M66 activation response rates. Under turbulence, prākāmya is what prevents the system from entering a death spiral where low ICI → low motivation → less outflow → lower ICI. |
| **Iśitva** | Mastery / sovereignty | Inflow + Turbulence | Inflow modulation + turbulence dampening | Conscious modulation of autonomic response via top-down cortical regulation of the amygdala and HPA axis; advanced practitioners show reduced cortisol reactivity to standardized stressors (Rosenkranz et al., 2013) | Conscious control over one's physiological response to stressors — choosing how much of the inflammatory cascade to permit. This is the highest-leverage inflow modulation: not avoiding the stressor, but deciding how much of your biology it activates. Under turbulence, iśitva directly counteracts the amplification coefficient — a practiced patient can remain in laminar response even when ICI is low. |
| **Vaśitva** | Control of elements / environment | Inflow | Inflow reduction (environmental) | Behavioral activation targeting environmental modification; boundary-setting as a social-regulation skill; stimulus control from behavioral psychology | Modulating the external environment to reduce inflow at the source. Boundary-setting with people, curating media consumption, allergen avoidance, workspace optimization, social environment selection. This is the most concrete and immediately actionable siddhi — it requires no internal state change, only external arrangement. |

### **Turbulence-Specific Applications**

Under the turbulence regime (ICI < turbulence threshold), the siddhis that target **inflow modulation and turbulence dampening** become disproportionately valuable because they counteract the amplification coefficient that makes everything hit harder:

- **Garimā** (grounding) prevents inflow stressors from triggering amplified physiological cascades
- **Iśitva** (mastery) directly reduces the turbulence coefficient by maintaining cortical regulation of the amygdala-HPA pathway under load
- **Prākāmya** (adherence) prevents the motivational collapse that turbulence creates — low ICI makes it harder to do the things that would raise ICI

These three form the **turbulence countermeasure triad** and should be prioritized in M66 activation prompts when `turbulence_active = TRUE`.

### **Infrastructure Variable Connections**

| Siddhi | Primary infrastructure variable affected |
|--------|------------------------------------------|
| **Laghimā** (lightness) | `lymphatic_tone` (via respiratory pump + movement); `vagal_tone` (via breathwork) |
| **Garimā** (grounding) | `vagal_tone` (via ventral vagal activation) |
| **Prāpti** (reach) | All infrastructure (portability reduces dependence on optimal conditions) |
| **Iśitva** (mastery) | `vagal_tone` (top-down autonomic regulation); indirectly reduces `system_viscosity` over long-term practice via improved HPA axis calibration |

### **Governance Note**

The siddhi taxonomy is included as an **evidence-informed capacity-modulation framework**, not as a spiritual or religious system. Each mapping is grounded in published psychoneuroimmunology, polyvagal theory, or contemplative neuroscience research. Patient-facing communications MUST use the physiological mechanism language and MAY optionally include the Sanskrit terminology if the patient has expressed interest in contemplative frameworks — this is a patient-preference-driven disclosure, not a default. M66 practice protocols derived from this taxonomy MUST be operationalized as specific, time-bounded, measurable actions (e.g., "5 minutes of extended-exhalation breathing" not "practice laghimā").

---

## **Data Schemas**

### **D1 — Stressor Object**

```
Stressor {
  stressor_id:          string (UUID)
  label:                string (human-readable; e.g., "work deadline pressure")
  valve_type:           enum { INFLOW | DISPLACEMENT }
  source_type:          enum { JOURNAL | PRO | LAB | WEARABLE | M5_INFERENCE |
                               M4_TAG | M64_FLAG | CLINICIAN_REPORTED |
                               SYSTEM_DETECTED }
  raw_magnitude:        float (0.0–1.0; pre-turbulence magnitude)
  effective_magnitude:  float (0.0–N; post-turbulence; may exceed 1.0 under
                               turbulence regime)
  modifiability:        enum { HIGH | MEDIUM | LOW | NONE }
  modifiability_domain: enum { BEHAVIORAL | COGNITIVE | ENVIRONMENTAL |
                               PHARMACOLOGICAL | THERAPEUTIC | SOCIAL |
                               UNMODIFIABLE }
  trajectory:           enum { EXPANDING | STABLE | CONTRACTING | UNKNOWN }
  first_detected:       timestamp
  last_updated:         timestamp
  evidence_refs:        Reference[] (provenance chain to source data)
  patient_aware:        boolean (has the patient been shown this stressor?)
  patient_confirmed:    boolean (has the patient acknowledged this stressor?)
}
```

### **D2 — Outflow Factor Object**

```
OutflowFactor {
  factor_id:            string (UUID)
  label:                string (e.g., "sleep quality", "daily breathwork")
  factor_class:         enum { SLEEP | ACTIVITY | NUTRITION | PRACTICE |
                               PHARMACOLOGICAL | PHYSIOLOGICAL | SOCIAL }
  current_level:        float (0.0–1.0; 0 = no contribution, 1 = maximal)
  sub_factors:          SubFactor[] | null (e.g., for SLEEP: duration,
                               deep_sleep_proportion, consistency)
  trajectory:           enum { IMPROVING | STABLE | DECLINING | UNKNOWN }
  data_sources:         enum[] { WEARABLE | JOURNAL | PRO | LAB | M66_LOG }
  last_updated:         timestamp
}

SubFactor {
  label:                string (e.g., "deep_sleep_proportion")
  current_level:        float (0.0–1.0)
  weight_within_parent: float (contribution to parent factor; sums to 1.0)
}
```

### **D3 — Inflammatory Capacity Index (ICI) Snapshot**

```
ICISnapshot {
  snapshot_id:          string (UUID)
  patient_id:           string
  timestamp:            timestamp
  ici_value:            float (0.0–100.0; percentage of remaining capacity)
  ici_band:             enum { GREEN (>65%) | YELLOW (50–65%) |
                               ORANGE (35–50%) | RED (<35%) }
  icmax_current:        float (current maximum capacity; may be < 100 if
                               post_overflow_penalty is active)
  inflow_rate:          float (normalized; 0.0–1.0; pre-turbulence)
  effective_inflow:     float (post-turbulence; may exceed inflow_rate)
  displacement_volume:  float (normalized; 0.0–1.0)
  raw_outflow_rate:     float (normalized; 0.0–1.0; behavioral factors only)
  effective_outflow:    float (after infrastructure modifiers)
  turbulence_active:    boolean
  turbulence_coefficient: float (1.0 if not active; >1.0 if active)
  infrastructure: {
    lymphatic_tone:     float (0.0–1.0)
    vagal_tone:         float (0.0–1.0)
    system_viscosity:   float (0.0–1.0)
    backpressure:       float (0.0–1.0)
  }
  overflow_probability: float (0.0–1.0; within governed time horizon)
  time_to_overflow:     duration | null
  post_overflow_penalty: float (0.0–1.0; 0 = no penalty active)
  top_stressors:        Stressor[] (top 5 by effective_magnitude, descending)
  top_outflow_deficits: OutflowFactor[] (bottom 3 by current_level, ascending)
  attribution_vector:   Map<stressor_id, float> (% contribution to capacity loss)
  vault_ref:            Reference (M21 ledger entry)
  module_version:       string (must be "1.1" or later)
  computation_provenance: Reference[] (input module versions, data timestamps)
}
```

### **D4 — M66 Activation Prompt**

```
EWAActivationPrompt {
  prompt_id:            string (UUID)
  patient_id:           string
  timestamp:            timestamp
  trigger_ici:          float (ICI value that triggered activation)
  trigger_band:         enum { YELLOW | ORANGE | RED }
  turbulence_active:    boolean
  priority_valve:       enum { INFLOW | DISPLACEMENT | OUTFLOW }
  infrastructure_deficits: {
    lymphatic_tone:     float | null (included if < 0.4)
    vagal_tone:         float | null (included if < 0.4)
    backpressure:       float | null (included if > 0.6)
  }
  valve_context: {
    inflow: {
      top_modifiable_stressors: Stressor[] (filtered to modifiability ≥ MEDIUM)
      suggested_domains:        string[]
    }
    displacement: {
      expanding_stressors:      Stressor[] (trajectory = EXPANDING)
      suggested_domains:        string[]
    }
    outflow: {
      deficit_factors:          OutflowFactor[] (current_level < 0.4)
      suggested_domains:        string[]
      lymphatic_specific:       boolean (TRUE if lymphatic_tone < 0.4;
                                suggests movement-based interventions)
    }
  }
  patient_vwa_list:     VWA[] (ordered by historical ICI impact)
  ewa_history:          EWAAttempt[] (recent exploratory actions and outcomes)
}
```

### **D5 — Validated Wellness Action (VWA) Record**

```
VWA {
  vwa_id:               string (UUID)
  patient_id:           string
  action_label:         string (e.g., "10-minute box breathing before bed")
  source_ewa_id:        string (originating M66 Exploratory Wellness Action)
  valve_target:         enum { INFLOW | DISPLACEMENT | OUTFLOW }
  infrastructure_target: enum { LYMPHATIC | VAGAL | VISCOSITY | NONE }
  promotion_date:       timestamp
  attempt_count:        integer (≥3 required for promotion)
  correlation_strength: float (0.0–1.0; ICI improvement correlation)
  average_ici_delta:    float (mean ICI improvement per attempt)
  onset_latency:        duration (typical time from action to ICI effect)
  contraindication_flags: Reference[] (clinician flags, if any)
  status:               enum { ACTIVE | SUSPENDED | DEPRECATED }
  evidence_refs:        Reference[] (M21 vault entries supporting promotion)
}
```

---

## **Process / Logic (Deterministic, Stepwise)**

### **Stage 1 — Input Ingestion & Stressor Census**

1. **Consume upstream signals:**
   - M3: current `stabilityBand`, `stackLevel`, `pauseFlag`, `pauseReason`
   - M5: current `PSI`, `persona_flags[]`, symbolic/psychosocial tags
   - M13: `flare_risk_slopes`, `inflammatory_burden_composite`, trajectory vectors
   - M64: active `fud_flags[]` (functional utilization discordances as displacement stressors AND backpressure indicators)
   - M4: `normalizedTags[]` (symptom tags, lifestyle tags, psychosocial tags)
   - M12: narrative digest (for stressor extraction)
   - M21: patient's historical ICI time-series, prior overflow events, VWA records, infrastructure calibration history
   - Wearable data: sleep metrics (total, deep sleep %, consistency), HRV (RMSSD for vagal tone), activity levels, sedentary time, breathing rate
   - PRO inputs: patient-reported stress, mood, energy, symptom severity
   - Lab events: inflammatory markers (CRP, IL-6, ESR), cortisol, tryptase (where available)

1a. **M64→M68 feed (v1.1):** For each active M64 `fud_flag`, classify by ICM relevance:
   - FUD-IR (Inflammatory Redistribution) flags → feed both displacement (chronic inflammatory burden) AND backpressure (clearance bottleneck)
   - FUD-GB (Gut-Barrier Dysfunction) flags → feed backpressure (impaired clearance pathway)
   - All other FUD flags → feed displacement only
   - Count and severity of FUD-IR + FUD-GB flags contribute directly to `backpressure` computation

2. **Build stressor census:** Enumerate all active stressors. Classify each as INFLOW or DISPLACEMENT based on temporal persistence (>14 days default = DISPLACEMENT; <14 days = INFLOW; clinician or patient may override).

3. **Assign magnitude scores:** For each stressor, compute `raw_magnitude` using weighted combination of: (a) direct measurement, (b) patient self-report intensity, (c) M5 inferred intensity, (d) historical impact calibration from M21 vault.

4. **Assign modifiability classifications:** HIGH / MEDIUM / LOW / NONE as defined in v1.0.

### **Stage 2 — Three-Valve Computation with Infrastructure & Turbulence**

5. **Compute infrastructure variables (v1.1):**

5a. **Lymphatic tone:** Aggregate the four pump estimates:
   - Skeletal muscle pump: f(daily_activity_minutes, sedentary_time, movement_frequency)
   - Respiratory pump: f(breathing_rate, breathing_depth_proxy)
   - Lymphangion contraction: f(vagal_tone) — proxy via autonomic regulation
   - Arterial pulsation: f(resting_HR, HRV) — cardiovascular fitness proxy
   - `lymphatic_tone = weighted_average(pump_estimates)`, default weights: skeletal 0.40, respiratory 0.25, lymphangion 0.20, arterial 0.15

5b. **Vagal tone:** Primary estimate from HRV (RMSSD); secondary from breathing rate and PRO recovery speed. Normalize to 0.0–1.0 against population reference ranges.

5c. **System viscosity:** Loaded from M21 calibration data (retrospective ICI recovery rate analysis). If insufficient history: use population default (0.3). Updated via M48 calibration loop.

5d. **Backpressure:** `backpressure = f(fud_ir_count, fud_gb_count, fud_severity, medication_count, inflammatory_marker_trajectory)`. Normalized to 0.0–1.0.

6. **Compute inflow rate:** Aggregate all INFLOW stressor `raw_magnitude` values. Apply recency weighting. Normalize to 0.0–1.0.

6a. **Apply turbulence (v1.1):**
```
if ici_previous < turbulence_threshold:
    turbulence_coefficient = 1.0 + ((turbulence_threshold - ici_previous)
                            / turbulence_threshold) × max_turbulence_gain
else:
    turbulence_coefficient = 1.0

effective_inflow = inflow_rate × turbulence_coefficient
```
Where `turbulence_threshold` (governed default: 50%) and `max_turbulence_gain` (governed default: 0.8, meaning up to 1.8× amplification at ICI = 0%) are patient-specific parameters calibrated from M21 vault data. For each INFLOW stressor, set `effective_magnitude = raw_magnitude × turbulence_coefficient`.

7. **Compute displacement volume:** Aggregate all DISPLACEMENT stressor magnitudes. Apply trajectory adjustment (EXPANDING +10%, CONTRACTING -10%). Normalize to 0.0–1.0.

8. **Compute effective outflow:**
```
raw_outflow = weighted_sum(outflow_factor_levels, factor_class_weights)
infrastructure_modifier = (lymphatic_tone + vagal_tone) / 2
effective_outflow = raw_outflow × (1 - backpressure) × (1 - system_viscosity)
                    × infrastructure_modifier
```

8a. **Apply post-overflow penalty (v1.1):**
```
if post_overflow_penalty > 0:
    icmax_current = 100.0 × (1 - post_overflow_penalty)
else:
    icmax_current = 100.0
```
Where `post_overflow_penalty` decays linearly over a governed recovery window (default: 14 days) from initial penalty value (governed default: 0.15, meaning ICmax reduced to 85% immediately post-overflow).

9. **Compute ICI:**
```
effective_burden = (effective_inflow × inflow_weight)
                 + (displacement_volume × displacement_weight)
effective_recovery = effective_outflow × outflow_weight
ici_raw = 1.0 - (effective_burden - effective_recovery)
ici_value = clamp(ici_raw × icmax_current, 0.0, icmax_current)
```

10. **Assign ICI band:** Map `ici_value` to band per governed thresholds:
   - **GREEN** (>65%): adequate headroom; maintenance mode
   - **YELLOW** (50–65%): reduced headroom; proactive engagement zone
   - **ORANGE** (35–50%): low headroom; active intervention recommended
   - **RED** (<35%): critical; overflow probable without immediate intervention

11. **Compute overflow probability:** Using M21-calibrated overflow function, estimate `P(overflow | current ICI, trajectories, infrastructure state, time_horizon)`. Time horizon governed (default: 72 hours).

12. **Compute time-to-overflow:** Under "no change" scenario. If trajectories suggest ICI is rising, time-to-overflow = null.

### **Stage 3 — Attribution & Stressor Discovery**

13. **Generate attribution vector:** For each stressor, compute percentage contribution to total capacity loss. Include turbulence multiplier in attribution where applicable. Rank by effective magnitude. Identify top 5 contributors.

14. **Run stressor discovery pass:** Compare M5 inferred psychosocial stressors against patient-reported stressors. Flag M5-detected stressors NOT explicitly reported as **candidate latent stressors**.

15. **Tag latent stressors:** Mark `patient_aware = false`. Surface via M11/M24 with gentle framing.

### **Stage 4 — Threshold Response & M66 Bridge**

16. **Evaluate threshold crossings:** On any band transition, emit threshold event.

17. **Generate patient engagement signal:** On YELLOW entry, emit supportive engagement. On ORANGE, increase urgency. On RED, emit clinician notification via M6/M10. If turbulence is active, include turbulence transparency messaging per I-G.

18. **Generate M66 Activation Prompt (D4):** On YELLOW or ORANGE entry, build prompt with valve-specific context, infrastructure deficit information, and VWA-first priority.

18a. **M68→M64 advisory (v1.1):** When `backpressure > 0.6`, emit advisory to M64: "Elevated backpressure detected. Consider inflammatory redistribution (FUD-IR) as a confounding factor for this patient's current lab interpretations."

19. **Emit VWA-first recommendation logic:** Recommend established VWAs before suggesting new exploratory actions.

### **Stage 5 — Vault Persistence & Learning**

20. **Persist ICI snapshot to M21:** Write complete `ICISnapshot` (D3) including all v1.1 fields (infrastructure variables, turbulence state, post-overflow penalty).

21. **Track intervention-outcome correlations:** Log action-outcome pairs including infrastructure variable changes.

22. **Evaluate VWA promotion candidates:** Check promotion criteria per I-F.

23. **Update post-overflow penalty:** If an overflow event was confirmed since last computation, initialize `post_overflow_penalty` at governed initial value. If penalty is active, apply decay.

24. **Emit audit artifacts:** All computations, infrastructure variable changes, turbulence regime transitions, threshold crossings, M66/M64 activations, VWA promotions, and overflow events.

---

## **M66 Handoff Prompt — Exploratory-to-Validated Lifecycle**

**The following is a specification fragment intended for integration into M66 (Exploratory Wellness Actions) or its next revision:**

> ### Proposed Addition to M66: Validated Wellness Action (VWA) Promotion Pathway
>
> **Context:** M68 (ICM) introduces the concept of wellness action lifecycle tracking. M66 currently owns the exploratory action catalog and the six-domain action taxonomy. The following extension proposes that M66 additionally manage the **promotion gate** from exploratory to validated status, using ICM-supplied outcome data.
>
> **Proposed M66 additions:**
>
> 1. **VWA Registry:** M66 maintains a per-patient registry of Validated Wellness Actions — actions that have passed the M68 promotion gate (≥3 attempts, ≥2 correlated ICI improvements, no adverse effects, no clinician contraindication).
>
> 2. **VWA-First Recommendation Priority:** When M68 issues an `EWAActivationPrompt`, M66 MUST check the VWA registry before suggesting new exploratory actions. Validated actions are presented as established, reliable interventions ("This has worked for you before"), not as experiments.
>
> 3. **VWA Maintenance & Deprecation:** VWAs are periodically re-evaluated. If a VWA stops correlating with ICI improvement over 3+ consecutive attempts, it is flagged for review and may be deprecated.
>
> 4. **Infrastructure-Aware Recommendations (v1.1):** When M68 identifies an infrastructure deficit (low lymphatic_tone, low vagal_tone), M66 SHOULD prioritize actions that target that infrastructure. Example: low lymphatic_tone → prioritize movement-based actions (walking, stretching, rebounding) and breathing exercises (respiratory pump). Low vagal_tone → prioritize breathwork with extended exhalation, cold exposure where tolerated, social connection.
>
> 5. **Patient Vocabulary:** Patient-facing language distinguishes between "Let's try something new" (exploratory) and "Here's something that's worked well for you" (validated).

---

## **Governance / Constraints**

* ICM is EoH-owned and contains no guideline text, disease fact tables, drug class lists, ontology mirrors, lab interpretation tables, or phenotype dictionaries.
* ICM does not diagnose, prescribe, or assert causality. It computes capacity, attributes stressors, and activates wellness action pathways.
* ICI thresholds (65%, 50%, 35%) are governed defaults adjustable per patient via clinician override.
* Turbulence threshold (50%) and max_turbulence_gain (0.8) are governed defaults adjustable via M48 calibration.
* Post-overflow penalty initial value (0.15) and recovery window (14 days) are governed defaults adjustable per patient.
* Infrastructure variable weights and normalization ranges are governed by M48 and updated only through governed retraining cycles.
* Stressor discovery is surfaced with non-judgmental framing and NEVER as accusation or diagnosis.
* Contemplative and mindfulness references are evidence-informed wellness categories, not spiritual recommendations.
* VWA promotion is patient-specific and does not generalize without population-level validation.
* ICM does not create new suppression reasons. Capacity-driven Band elevation is advisory context to M8/M9.
* M64↔M68 bidirectional feed is advisory only — neither module overrides the other's computations.

---

## **Dependencies**

### **Consumes (read-only)**

| Module | What ICM consumes |
|--------|-------------------|
| **M3** | `stabilityBand`, `stackLevel`, `pauseFlag`, `pauseReason` |
| **M4** | `normalizedTags[]` (symptom, lifestyle, psychosocial tags) |
| **M5** | `PSI`, `persona_flags[]`, symbolic/psychosocial tags |
| **M12** | Narrative digest (for stressor extraction) |
| **M13** | `flare_risk_slopes`, `inflammatory_burden_composite`, trajectory vectors |
| **M21** | Historical ICI time-series, overflow events, VWA records, infrastructure calibration data |
| **M64** | Active `fud_flags[]` with mechanism types (FUD-IR, FUD-GB flagged for backpressure) |
| Wearables | Sleep metrics (total, deep sleep %, consistency), HRV (RMSSD), activity levels, sedentary time, breathing rate |
| PROs | Stress, mood, energy, symptom severity, recovery speed self-reports |
| Labs | Inflammatory markers (CRP, IL-6, ESR, cortisol, tryptase — where available) |

### **Produces / hands off to**

| Module | What ICM provides |
|--------|-------------------|
| **M11** | Patient engagement signals with ICI context, valve-specific guidance, turbulence transparency messaging, lymphatic education content |
| **M21** | `ICISnapshot` objects (including infrastructure state); intervention-outcome pairs; VWA records; overflow events |
| **M24** | ICI visualization data (current value, band, attribution vector, infrastructure gauges, turbulence indicator, time-to-overflow) |
| **M64** | Backpressure advisory when `backpressure > 0.6` (bidirectional) |
| **M66** | `EWAActivationPrompt` with valve context, infrastructure deficits, and VWA-first priority |
| **M6** (opt-in) | ICI as optional context for escalation tier determination |
| **M14** (opt-in) | ICI as optional context for intervention timing |
| **M48** | Calibration telemetry (predicted vs. actual overflow events; infrastructure variable accuracy; turbulence threshold calibration) |

### **Appendix references**

* **Appendix C.11** — FHIR audit/provenance bindings.
* **Appendix H.2** — Suppression field definitions (consumed; ICM does not create new suppression reasons).
* **Appendix F.68** (new; to be created) — ICM threshold governance, population default weights, infrastructure variable normalization, turbulence parameters, post-overflow penalty defaults, calibration loop parameters.

---

## **Audit Hooks**

* Every `ICISnapshot` computation: timestamp, all input module versions, data source timestamps, ICI value, band, all infrastructure variables, turbulence state, post-overflow penalty, attribution vector.
* Every turbulence regime transition: entry/exit timestamp, ICI at transition, turbulence_coefficient value.
* Every infrastructure variable change exceeding ±0.1 from previous: variable name, previous/new value, data sources.
* Every threshold crossing event: previous band, new band, triggering stressor(s), M66 activation prompt ID.
* Every M64↔M68 advisory exchange: direction (M64→M68 or M68→M64), advisory content, triggering values.
* Every stressor discovery event: M5 evidence chain, `patient_aware` status, patient response.
* Every M66 activation: prompt ID, trigger ICI, priority valve, infrastructure deficits, VWA recommendations, EWA suggestions.
* Every VWA promotion/deprecation: source EWA ID, history, correlation evidence, clinician review status.
* Every post-overflow penalty: overflow event reference, initial penalty, current penalty, decay progress.
* Every calibration parameter update: previous/new values, trigger, evidence.

---

## **Acceptance Tests**

### **T-01: ICI Independence from Stability Band**
Band = 1 (stable), Stack = 2, high displacement + low outflow. Verify ICI < 50% while Band remains 1.

### **T-02: Three-Valve Attribution Isolation**
Simulated inflow reduction. Verify displacement/outflow unchanged, ICI improvement attributed solely to inflow.

### **T-03: Overflow Forecast Accuracy**
Patient with 6+ months vault history, ≥2 confirmed overflows. Verify predicted overflow probability ≥0.6 in 72h window preceding historical overflows.

### **T-04: Latent Stressor Discovery**
5 journal entries with escalating frustration on unlisted topic. Verify candidate latent stressor generated with `patient_aware = false`.

### **T-05: M66 Activation Prompt Completeness**
GREEN→YELLOW crossing. Verify `EWAActivationPrompt` generated with all required fields populated and provenance-linked.

### **T-06: VWA Promotion Gate**
4 attempts, 3 correlated ICI improvements ≥5%. Verify VWA promotion. Simulate no correlation → verify no promotion.

### **T-07: VWA-First Priority**
Patient with 2 active VWAs + M66 activation. Verify VWAs recommended before exploratory actions.

### **T-08: No Diagnostic Language**
Scan all outputs for ICD codes, disease assertions, causal claims. Verify zero occurrences.

### **T-09: RED Band Clinician Escalation**
ICI < 35%. Verify M6/M10 receives clinician notification with ICI context and attribution.

### **T-10: Contemplative Practice as Measurable Intervention**
Log breathwork via PRO. Verify tracking, M21 recording, and VWA promotion evaluation after ≥3 correlated improvements.

### **T-11: Turbulence Amplification (v1.1)**
Set ICI to 40% (below turbulence threshold). Apply minor inflow stressor with raw_magnitude = 0.05. Verify `effective_magnitude > 0.05`, turbulence_coefficient > 1.0, and patient-facing output includes turbulence transparency language.

### **T-12: Turbulence Independence from Stressor Type (v1.1)**
With turbulence active, apply one emotional stressor and one physical allergen stressor with equal raw_magnitude. Verify identical turbulence amplification on both.

### **T-13: Post-Overflow Hysteresis (v1.1)**
Simulate overflow event. Verify ICmax reduced on next computation, penalty decays over governed window, and provenance shows penalty.

### **T-14: Infrastructure Variable Effect on Outflow (v1.1)**
Two patients with identical raw_outflow_rate but different lymphatic_tone (0.8 vs 0.3). Verify different effective_outflow values and that the difference is attributable to lymphatic_tone.

### **T-15: Backpressure from M64 FUD-IR Flags (v1.1)**
Patient with 3 active FUD-IR flags. Verify elevated backpressure, reduced effective_outflow, and M68→M64 advisory emitted when backpressure > 0.6.

### **T-16: M68→M64 Bidirectional Advisory (v1.1)**
Trigger backpressure > 0.6. Verify advisory emitted to M64 with inflammatory redistribution context. Verify advisory is logged as audit event.

---

## **Metrics**

| Metric | Definition | Target |
|--------|-----------|--------|
| **ICI Calibration Accuracy** | % of overflow events preceded by ICI < 35% within 72h | ≥70% within 6 months |
| **Attribution Completeness** | % of ICI computations where attribution vector ≥90% of capacity loss | ≥95% |
| **Latent Stressor Acceptance Rate** | % of discoveries patients acknowledge as relevant | ≥40% baseline |
| **VWA Promotion Rate** | % of EWAs achieving VWA within 60 days | Track only |
| **VWA Effectiveness Persistence** | % of VWAs maintaining correlation at 90-day re-evaluation | ≥60% |
| **M66 Activation Response Rate** | % of prompts resulting in patient attempting ≥1 action within 48h | ≥30% |
| **False Overflow Rate** | % of predicted overflows (P ≥ 0.7) not resulting in clinical event | < 40% |
| **Turbulence Prediction Accuracy (v1.1)** | % of turbulence-regime periods that are followed by overflow within 7 days if no intervention | Track for calibration |
| **Infrastructure Variable Stability (v1.1)** | Coefficient of variation of infrastructure estimates across consecutive days (lower = more stable/reliable) | CV < 0.15 |
| **Post-Overflow Repeat Rate (v1.1)** | % of patients who experience repeat overflow within 14 days of initial | Track; expect decrease vs. pre-ICM baseline |

---

## **v1.1 Implementation Checklist**

1. Implement Stressor object (D1) with `raw_magnitude` and `effective_magnitude` fields.
2. Implement OutflowFactor object (D2) with `sub_factors` support for sleep decomposition.
3. Implement infrastructure variable computation pipeline (Stage 2, step 5a–5d):
   a. Lymphatic tone with four-pump decomposition
   b. Vagal tone from HRV/RMSSD
   c. System viscosity from M21 calibration data
   d. Backpressure from M64 FUD-IR/FUD-GB flags + medication count + inflammatory marker trajectory
4. Implement turbulence regime (Stage 2, step 6a) with governed threshold and gain parameters.
5. Implement post-overflow penalty logic (Stage 2, step 8a) with decay window.
6. Implement revised ICI computation (Stage 2, step 9) incorporating infrastructure modifiers and turbulence.
7. Implement ICISnapshot object (D3) with all v1.1 fields.
8. Implement ICI band assignment and threshold crossing detection.
9. Implement M66 Activation Prompt generation (D4) with infrastructure deficit fields.
10. Implement M64↔M68 bidirectional feed (Stage 1 step 1a, Stage 4 step 18a).
11. Implement stressor discovery pass consuming M5 psychosocial tags.
12. Implement overflow probability model with infrastructure-aware calibration.
13. Implement VWA Record (D5) with `infrastructure_target` field, promotion gate logic, maintenance/deprecation.
14. Implement patient-facing ICI visualization data contract for M24 (ICI value, band, attribution, infrastructure gauges, turbulence indicator, time-to-overflow).
15. Implement turbulence transparency messaging templates for M11 (per I-G).
16. Implement lymphatic education content templates for M11 ("movement as drainage pump" messaging).
17. Build latent stressor surfacing pipeline with non-judgmental framing (M11 integration).
18. Implement calibration telemetry pipeline to M48 (overflow prediction accuracy, infrastructure variable stability, turbulence threshold calibration).
19. Wire all audit hooks to M21/Appendix C.11 FHIR audit surface.
20. Stand up acceptance tests T-01 through T-16 and tracked metrics.
21. Create Appendix F.68 stub (threshold governance, population defaults, infrastructure normalization ranges, turbulence parameters, post-overflow penalty defaults, calibration loop specification).

---

## **v2.0 Roadmap Reference**

The following items were evaluated during v1.0→v1.1 audit and explicitly deferred. Full context, prerequisites, and proposed schemas are documented in **M68_v2.0_Roadmap.md**:

1. **Sedimentation modeling** — subclinical cumulative burden as a fourth dynamic
2. **Circadian parameterization** — time-of-day modifiers on all three valves
3. **Cavitation / let-down detection** — rapid decompression flare risk from rapid stress removal
4. **Bernoulli constriction effects** — disproportionate impact of losing key coping outlets
5. **Fascial system modeling** — fascial restriction as lymphatic tone sub-component
6. **Microbiome as infrastructure variable** — gut ecosystem as cross-valve modifier
