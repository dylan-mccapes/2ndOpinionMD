# V6 EoH Implementation Tickets: M63 - M68

**Created:** 2026-03-21
**Reporter:** Andras (Product/Architecture)
**Default Assignee:** Dylan (CTO/Engineering)

---

## 2OPMD-M63 -- Glass-Box Derivation Contract (GBDC)

| Field | Value |
|-------|-------|
| **Title** | M63 Glass-Box Derivation Contract -- Transparency Enforcement Infrastructure |
| **Type** | Architecture |
| **Priority** | High |
| **Assignee** | Dylan |
| **Reporter** | Andras |
| **Status** | READY FOR REVIEW |

### Summary

M63 defines and enforces the mechanical requirements under which any EoH output may be labeled GLASS_BOX -- meaning a complete, pointer-backed, reproducible account of how it was derived. It separates "what the system concluded and how it got there" (disclosed) from "how the system is built" (protected). M63 discloses; it does not compute, score, grade, or execute anything.

### Scope

- **DerivationChain object**: Immutable structured record capturing all reasoning steps from inputs to final output, including `chain_id`, `output_ref`, `inputs[]`, `transformations[]`, `assumptions[]`, `motifs_referenced[]`, `uncertainty_disclosure`, `constraint_disclosure`, `completeness_classification`, `replay_metadata`
- **Transformation Step Records**: Per-step owning module, input/output artifact pointers, provenance pointers, step status (POINTER_BACKED / MISSING / REDACTED)
- **Four orthogonal enforcement contracts**: Trace Integrity, Support Disclosure, Uncertainty Preservation, Constraint Disclosure
- **Glass-Box eligibility gate**: Hard enforcement -- no output may claim transparency without a complete DerivationChain
- **Replay determinism envelope**: Same role-context + version state must produce deterministic replay
- **Motif Registry and Math/Logic Update template reference**
- **Status labels**: TRACE_COMPLETE, TRACE_PARTIAL, TRACE_REDACTED, TRACE_UNAVAILABLE
- **Append-only chain semantics**: Corrections require new chain version with supersession pointer

### Dependencies

- **Upstream (consumes from):** All modules that produce surfaced outputs (M13, M14, M15, M49, M53, M64, M66, M67, M68) -- M63 wraps their outputs with derivation chains
- **Downstream (feeds into):** M24/M43 (UI rendering of transparency labels), M67 ARGL (evidence provenance enforcement)
- **Note:** M63 is read-only and analysis-only. It depends on owning modules emitting proper artifacts and provenance records. If upstream modules don't emit artifacts, chains get TRACE_UNAVAILABLE status.

### Acceptance Criteria

1. DerivationChain can be constructed for any surfaced output that has proper upstream artifact emission, with all required fields populated and validated
2. No output can receive GLASS_BOX label without passing all four enforcement contracts (Trace Integrity, Support Disclosure, Uncertainty Preservation, Constraint Disclosure)
3. Silent omission is impossible -- every gap appears as an explicit MISSING or REDACTED placeholder
4. Replay of the same chain in the same role-context and version state produces a deterministic result
5. DerivationChain is append-only; corrections produce a new chain version with explicit supersession pointer to the prior version

### Spec Reference

`EoH/EoH V6/V6 Individual Modules/V6 M63 GlassBoxDerivationContract/V6_M63_GlassBox_Derivation_Contract_GBDC_v2.md`

### Notes

- V6-only module. Non-executable. Read-only. Analysis-only.
- Does NOT compute, score, or evaluate clinical output. It only governs the representation and completeness of already-existing artifacts.
- This is governance infrastructure -- it underpins trust/transparency claims for the entire V6 stack.
- No V5.2 modification required.

---

## 2OPMD-M64 -- Functional Utilization Discordance Detector (FUDD)

| Field | Value |
|-------|-------|
| **Title** | M64 FUDD -- Two-Layer Serum-vs-Tissue Discordance Detection |
| **Type** | Implementation |
| **Priority** | Critical |
| **Assignee** | Dylan |
| **Reporter** | Andras |
| **Status** | READY FOR REVIEW |

### Summary

M64 detects cases where a patient's blood levels look normal but effective utilization at the tissue level is impaired (Functional Utilization Discordance), and the inverse -- where blood levels look abnormal but tissue status is actually adequate. It uses a two-layer architecture: Layer 1 matches against curated FUD signatures for known patterns, Layer 2 applies a general discordance heuristic capable of catching novel patterns that haven't been formally characterized yet.

### Scope

- **Layer 1 -- Signature-Matched Detection**: Pattern matching against curated `[analyte x mechanism x indicator constellation]` triples from MKE registry. Confidence assignment (high/moderate/low) based on converging signal count. Full mechanism classification and intervention candidates.
- **Layer 2 -- General Discordance Heuristic**: Signature-independent detection using 5 general discordance indicators (clinical symptoms consistent with deficiency, downstream metabolite abnormality, trajectory inconsistency, known interfering factor, response failure). Fires when >=2 indicators present despite adequate serum.
- **9 FUD mechanism classes**: Receptor Blockade (FUD-RB), Competitive Displacement (FUD-CD), Transport Impairment (FUD-TI), Enzymatic Conversion Failure (FUD-EC), Cofactor Depletion (FUD-CF), Molecular Mimicry Trigger (FUD-MM), Compartmental Trapping (FUD-CT), Gut-Barrier Dysfunction (FUD-GB), Inflammatory Redistribution (FUD-IR)
- **Inverse discordance (iFUD) detection**: Abnormal serum + adequate tissue status
- **Role-differentiated output payloads**: B2C (patient-facing with intervention guidance) vs B2MD (clinician-facing with expandable mechanism context, togglable panel, clinician-gated activation)
- **Coverage across 8 analyte classes**
- **Cascading discordance chain detection** (e.g., selenium deficiency -> impaired T4->T3 -> functional hypothyroidism)

### Dependencies

- **Upstream (consumes from):** M7A (lab quality checks), MKE (FUD signature registry, symptom-analyte association tables), M6/M13 (stability band, trajectory), M21 (patient history/vault)
- **Downstream (feeds into):** M68 ICM (bidirectional feed -- FUD-IR and FUD-GB flags become backpressure signals), M24/M43 (visualization), M66 EWA (intervention candidates)
- **Bidirectional:** M68 (M64 sends FUD flags to M68 for backpressure; M68 sends advisory back when backpressure >0.6)

### Acceptance Criteria

1. Layer 1 correctly matches curated FUD signatures from MKE registry and assigns confidence levels (high/moderate/low) based on converging signal count
2. Layer 2 fires on novel discordance patterns (no pre-loaded signature required) when >=2 of 5 general indicators are present, with distinct governance constraints and lower nudge posture than Layer 1
3. Inverse discordance (iFUD) correctly flags cases where serum looks abnormal but tissue status is adequate (e.g., inflammation-driven redistribution)
4. Role-differentiated payloads are correct: B2C surfaces intervention guidance directly; B2MD surfaces detection flag + expandable mechanism context with clinician-gated activation
5. FUD flags include mechanism-type codes (FUD-RB, FUD-CD, etc.) compatible with M68 backpressure consumption

### Spec Reference

`EoH/EoH V6/V6 Individual Modules/V6_M64_FunctionalUtilizationDiscordanceDetector_Two_Layer_Detection.md`

### Notes

- V6-only module. New logic.
- This is one of the heaviest clinical modules in V6. The two-layer architecture is the key innovation -- Layer 2's ability to detect unknown patterns is what separates this from a simple lookup table.
- M64<->M68 bidirectional feed is a critical integration point. Verify M64 emits mechanism-typed flags before M68 can consume them.
- Layer 2 exploratory detections require distinct governance (lower confidence framing, exploratory labeling) -- do not surface them at the same confidence as Layer 1.

---

## 2OPMD-M65 -- Dark Passenger (Addiction Topology / Linguistic Drift Detection)

| Field | Value |
|-------|-------|
| **Title** | M65 Dark Passenger -- Voice Identity Drift Detection & Coaching Posture System |
| **Type** | Implementation |
| **Priority** | High |
| **Assignee** | Dylan |
| **Reporter** | Andras |
| **Status** | READY FOR REVIEW |

### Summary

M65 detects, classifies, and scores longitudinal drift in a patient's narrative voice — the "Dark Passenger" phenomenon where the person speaking through the chatbot journal ceases to be the person the system learned to recognize. Voice identity fracture correlates with disease flares, medication non-adherence, and behavioral destabilization. M65 builds a voice baseline, computes Voice Identity Drift (VDI) scores, classifies drift into named persona types, and emits coaching posture advisories to downstream patient-facing modules.

### Scope

- **Voice baseline construction**: Longitudinal voice profile from patient-authored chatbot journal text (lexical diversity, sentence structure, emotional range, self-reference patterns, temporal coherence)
- **Voice Identity Drift (VDI) scoring**: Continuous metric quantifying deviation from baseline voice profile
- **Persona taxonomy**: Classification of drift into named persona types (The Minimizer, The Catastrophizer, The Denier, The Dissociator, The Performer, The Ghost) with distinct detection signatures and etiology tags
- **Six-stage engagement ladder**: Progressive severity classification from Vexation through Possession
- **Coaching posture advisory**: Structured output signal recommending interaction stance for downstream patient-facing modules (M11)
- **Disclosure encouragement level**: Structured output for downstream modules on whether/how to create space for patient self-report
- **Dark Passenger naming readiness**: Flag indicating sufficient longitudinal evidence to offer the naming protocol
- **FUDD↔M65 bidirectional feed**: Cross-module contract for metabolic-versus-psychiatric differential signaling
- **ICM↔M65 feed**: Inflammatory capacity context as interpretive modifier for drift classification
- **Evidence base integration**: Mood-flare bidirectionality, linguistic feature candidates, confounder rules, PSI gating constraints

### Dependencies

- **Upstream (consumes from):** M4 (tag normalization), M5 PSI/persona, M6 (escalation context), M11 (engagement state), M12 (narrative digests), M13 (trajectory), M64 FUDD (metabolic-psychiatric differential), M68 ICM (inflammatory capacity)
- **Downstream (feeds into):** M11 (coaching posture), M14 (escalation candidates), M16 (intervention guardrails), M19 (QA learning), M66 EWA (action recommendations), M10 (safety escalation)

### Acceptance Criteria

1. Voice baseline is constructed from minimum N journal entries and produces a stable voice profile with defined feature dimensions
2. VDI score correctly increases when patient text deviates from baseline across multiple linguistic features, with drift classified into the correct persona type
3. Six-stage engagement ladder correctly classifies severity from Vexation (stage 1) through Possession (stage 6) with appropriate coaching posture output at each stage
4. Diagnostic Independence Invariant enforced — M65 never asserts a psychiatric, metabolic, or autoimmune diagnosis; it emits advisory signals only
5. FUDD↔M65 bidirectional feed correctly differentiates metabolic causes of voice drift (e.g., thyroid-driven fatigue altering language) from psychological causes

### Spec Reference

`EoH/EoH V6/V6 Individual Modules/V6 M65 Dark Passenger/V6_M65_Dark_Passenger_Voice_Identity_Drift_v1_0.md`

### Notes

- V6-only module. Detection and advisory only — does not execute chatbot changes, modify patient state, or assert diagnoses.
- The canonical spec (v1.0, 2026-03-18) is now available. Previous raw research files (CHAPTER_0.md, RAW_Chat, Attribution Signal Threshold) are included as background context.
- The Addiction Topology / field-theoretic framework (CHAPTER_0.md) is Andras's philosophical grounding — not an engineering artifact, but worth reading for design intent.
- ML/transformer pipeline specification is deferred to implementation — spec defines detection semantics, not algorithms.
- Depends on M64 and M68 — verify those feeds before M65 integration work.

---

## 2OPMD-M66 -- Exploratory Wellness Actions (EWA)

| Field | Value |
|-------|-------|
| **Title** | M66 EWA -- Terrain-Stabilizing Wellness Action Engine |
| **Type** | Implementation |
| **Priority** | High |
| **Assignee** | Dylan |
| **Reporter** | Andras |
| **Status** | READY FOR REVIEW |

### Summary

M66 surfaces low-risk, reversible, terrain-supportive actions (diet, lifestyle, herbs/teas, targeted supplements, signal-clarifying tests) that reduce physiologic burden and stabilize baseline without treating named diseases. It operates in LOCKED threads and feeds forward into higher-order reasoning. Everything is framed as "supportive, not curative" and remains optional and reversible.

### Scope

- **5 core subdomains**: Dietary Load Reduction, Lifestyle & Respiratory Support, Herbs/Teas/Tinctures (terrain stabilizers), Supplements (optional, targeted), Signal-Clarifying Tests/Evaluations
- **EWA Action Set output**: Non-ranked, non-prescriptive action recommendations with explicit "supportive, not curative" annotation
- **Observation window recommendations**: How long to observe before evaluating effect
- **Safety flags**: What to stop if condition worsens
- **Medication terrain review integration**: Med-by-med burden review, identify sedating/respiratory-depressing/neuromuscular-worsening agents, simplify rather than add
- **M68 integration**: M68 triggers M66 activation prompts with valve context and infrastructure deficit information. VWA (Validated Wellness Action) promotion lifecycle managed by M68.
- **MUST/MUST-NOT guarantees enforcement**: Diet/lifestyle/habit-forward, low-risk, reversible, non-pharmacologic first. Never claims treatment, never escalates therapy, never overrides clinician.

### Dependencies

- **Upstream (consumes from):** Confirmed diagnoses (read-only), current medications (read-only), symptom patterning, comorbid terrain, patient capacity constraints, M68 activation prompts (with valve context)
- **Downstream (feeds into):** M68 ICM (EWA actions become outflow-enhancing interventions tracked in VWA lifecycle), M24/M43 (patient-facing wellness recommendations)
- **Note:** M66 bridges V5.2 terrain logic with patient-facing wellness guidance. Does not belong to MKE, diagnosis, escalation, or execution pathways.

### Acceptance Criteria

1. EWA Action Sets are generated with explicit "supportive, not curative" annotation on every output
2. All recommended actions are low-risk, reversible, and non-pharmacologic first -- no immune-stimulating herbs by default when immunosuppression history is present
3. Safety flags are attached to every action set specifying what to stop if condition worsens
4. M68 activation prompts correctly trigger M66 with valve context and infrastructure deficit data, and M66 returns actions targeting the specific deficit
5. MUST-NOT guarantees are enforced: system cannot claim disease treatment, escalate therapy, override clinician, or make diagnostic claims through M66

### Spec Reference

`EoH/EoH V6/V6 Individual Modules/V6 M66 -- Exploratory Wellness Actions (EWA).md`

### Notes

- V6-only module. New logic.
- M66 is the patient-facing wellness layer. It is deliberately conservative -- "stabilize terrain so truth can surface."
- The herb/tea/tincture catalog and supplement recommendations are clinically grounded but need pharmacist-level review (Andras owns this -- do not invent interactions).
- The VWA (Validated Wellness Action) promotion lifecycle is owned by M68, not M66. M66 generates candidates; M68 validates them through outcome tracking.
- M66 Siddhi Practice Taxonomy Fragment exists as an extension proposal -- separate from core M66 scope.

---

## 2OPMD-M67 -- Adversarial Reasoning Governance Layer (ARGL)

| Field | Value |
|-------|-------|
| **Title** | M67 ARGL -- Multi-Agent Adversarial Reasoning Quality Assurance |
| **Type** | Architecture |
| **Priority** | Critical |
| **Assignee** | Dylan |
| **Reporter** | Andras |
| **Status** | READY FOR REVIEW |

### Summary

M67 provides a single adversarial command layer that orchestrates specialized reasoning agents and prevents weak, unsupported, or hallucinated conclusions from propagating through the EoH pipeline. It enforces computable evidence provenance (every claim carries typed, traceable evidence tags), contextual validity rebinding (every conclusion re-verifies relevance to the current patient state before emission), and mandatory falsification (at least one independent adversarial evaluation attempts to break the leading conclusion before publication).

### Scope

- **Multi-agent architecture**: Command Arbiter at top, specialized agents (Retrieval, Reasoning, QC, Safety) reporting vertically only -- no horizontal agent-to-agent communication (prevents groupthink)
- **Computable evidence provenance**: Typed evidence tags on all claims (tag types TBD in spec -- analogous to GRADE certainty levels but machine-readable)
- **Contextual validity rebinding**: Every conclusion must re-verify it binds to the current clinical question, current patient state, and current evidence set before downstream emission
- **Mandatory falsification protocol**: At least one independent adversarial evaluation per reasoning chain before propagation. Formalizes tumor board / M&M conference patterns.
- **Conflict surfacing**: Contradictory evidence must be preserved and reported, not averaged or suppressed
- **Vertical-only synthesis invariant**: Specialized agents report upward; synthesis occurs only at the Command Arbiter layer
- **After-action learning**: Structured logging of reasoning failures, hallucination triggers, evidence gaps for continuous improvement via M48
- **Agent lifecycle governance**: Scope, failure modes, stop conditions, and shutdown for every spawned reasoning agent
- **Stack placement**: Sits between Clinical Reasoning Modules (M17, M18, M49, M53, M64) and User-Facing Response Layer (M24/M43)

### Dependencies

- **Upstream (consumes from):** M17 CIR, M18 MPA, M49 diagnostic scoring, M53 PTM, M64 FUDD, MKE (evidence), Tool Library (M51/M52)
- **Downstream (feeds into):** M24/M43 (user-facing response layer -- ARGL gates what passes through), M48 (after-action learning), M63 (evidence provenance feeds into derivation chains)
- **Integration contract:** Any V5.2 module can opt in to adversarial governance. M67 does not force V5.2 integration but provides the contract.

### Acceptance Criteria

1. No reasoning chain propagates to the user-facing layer without at least one independent adversarial evaluation (mandatory falsification)
2. Every claim in a reasoning chain carries a typed, traceable evidence tag. Claims without tags are rejected at the Command Arbiter.
3. Contextual validity rebinding passes before emission -- conclusions that have drifted from the original clinical question or are stale relative to current patient state are caught and rejected
4. Contradictory evidence is preserved and surfaced in the decision record, never silently averaged or suppressed
5. Agent communication is vertical-only -- no agent-to-agent horizontal sharing. Violation of this invariant is a hard failure.

### Spec Reference

`EoH/EoH V6/V6 Individual Modules/V6 M67 - AdversarialGovernanceLayer/V6_M67_AdversarialReasoningGovernanceLayer_ARGL.md`

### Notes

- V6-only module. Meta-governance layer. Does not generate clinical content.
- This is architecturally the most complex V6 module. It governs the quality of reasoning itself, not patient state or clinical outputs.
- The vertical-only synthesis invariant is the core architectural constraint -- it prevents the groupthink failure mode that plagues multi-agent systems.
- ARGL does not own suppression (M8/M9), consent/privacy (M26/M27/M34-M37), or UI rendering (M24/M43).
- Implementation will likely require a phased approach: evidence tagging system first, then falsification protocol, then full agent lifecycle governance.

---

## 2OPMD-M68 -- Inflammatory Capacity Model (ICM)

| Field | Value |
|-------|-------|
| **Title** | M68 ICM -- Real-Time Allostatic Headroom with Three-Valve Dynamics |
| **Type** | Implementation |
| **Priority** | Critical |
| **Assignee** | Dylan |
| **Reporter** | Andras |
| **Status** | READY FOR REVIEW |

### Summary

M68 computes a real-time estimate of how much inflammatory and allostatic headroom a patient has remaining before a clinical event (flare, reaction, decompensation) becomes probable. It models three independently modifiable dynamics -- inflow rate (stressor exposure), displacement volume (chronic burden), and outflow rate (recovery/clearance capacity) -- modified by physiological infrastructure variables and a non-linear turbulence regime that amplifies stressor impact under heavy load.

### Scope

- **ICI (Inflammatory Capacity Index)**: Continuous 0-100% value representing remaining headroom. Band thresholds: GREEN (>65%), YELLOW (50-65%), ORANGE (35-50%), RED (<35%)
- **Three-valve computation**: Inflow rate, displacement volume, outflow rate (Recovery Flux) with per-factor attribution
- **Turbulence regime**: Non-linear amplification when ICI drops below threshold (default 50%). Captures stress sensitization.
- **4 infrastructure variables**: Lymphatic tone (four-pump decomposition), vagal tone (HRV RMSSD), system viscosity (clearance resistance), backpressure (downstream bottlenecks)
- **Post-overflow hysteresis**: Temporary ICmax reduction after overflow event (mast cell sensitization, glutathione depletion, psychological trauma)
- **Stressor Census Engine**: Classification (inflow vs displacement), magnitude scoring, modifiability tagging, latent stressor discovery
- **Attribution vector**: Per-stressor contribution to capacity loss, top-5 ranking, top-3 outflow deficit identification
- **VWA (Validated Wellness Action) lifecycle**: Intervention-outcome correlation tracking, promotion gate (>=3 attempts, >=2 correlated improvements), 90-day re-evaluation, deprecation on correlation loss
- **M64 bidirectional feed**: FUD-IR/FUD-GB flags become backpressure signals; M68 sends advisory back when backpressure >0.6
- **Threshold logic and output routing**: Band transitions trigger M11/M24 engagement, M66 activation prompts, RED band clinician escalation
- **M24 visualization data contract**: ICI gauge, stressor attribution, infrastructure gauges, turbulence indicator, time-to-overflow, VWA quick-access
- **12 subtasks, 40-60 dev-days estimated** (see Dylan Handoff for full breakdown)

### Dependencies

- **Upstream (consumes from):** M3 (state), M4 (normalized tags), M5 (PSI/persona), M12 (narrative digests), M13 (trajectory), M21 (vault/history), M64 (FUD flags), wearables (sleep, HRV, activity), PROs (stress, mood, energy), labs (CRP, IL-6, ESR, cortisol, tryptase)
- **Downstream (feeds into):** M21 (ICI snapshots for vault), M24 (visualization data), M11 (engagement signals), M66 (activation prompts with valve context), M48 (calibration telemetry)
- **Bidirectional:** M64 (FUD flags in, advisory out)

### Acceptance Criteria

1. ICI computation produces correct values across all 4 bands with proper turbulence amplification when below threshold
2. Three-valve decomposition correctly isolates inflow, displacement, and outflow contributions with per-factor attribution accounting for >=90% of capacity loss
3. Infrastructure variables (lymphatic tone, vagal tone, system viscosity, backpressure) correctly modify outflow effectiveness and degrade gracefully when wearable data is absent
4. Post-overflow hysteresis reduces ICmax temporarily after a flare event and decays over the governed recovery window
5. VWA lifecycle correctly tracks intervention-outcome correlation and promotes actions that meet the promotion gate criteria (>=3 attempts, >=2 correlated improvements, no adverse effects)

### Spec Reference

`EoH/EoH V6/V6 Individual Modules/V6 M68 - InflammatoryCapacityIndex_LIVE/V6_M68_InflammatoryCapacityModel_ICM/V6_M68_InflammatoryCapacityModel_ICM_v1.1.md`

### Notes

- V6-only module. New logic. Zero backward contamination on V5.2.
- **Dylan Handoff package already exists** with full subtask breakdown, sizing, sprint allocation, dependency risk register, and 4 ADRs requiring decisions. See: `V6 M68 - InflammatoryCapacityIndex_LIVE/V6_M68_InflammatoryCapacityModel_ICM/M68_Dylan_Handoff.md`
- **4 open ADRs**: (1) ICI snapshot storage format, (2) HRV population reference ranges, (3) computation frequency, (4) primary wearable platform target. These need decisions before implementation begins.
- Critical path: Schemas + Ingestion (parallel) -> Stressor Census + Infrastructure Vars (parallel) -> Three-Valve Engine -> Outputs (partially parallel) -> Tests
- Wearable platform selection (ADR-68.4) is a blocking decision for the input ingestion pipeline.
- M64 integration (bidirectional feed) requires M64 to emit mechanism-typed FUD flags. Verify this capability exists in M64 before starting M68 Subtask 2.

---

## Cross-Module Dependency Map

```
M63 GBDC -----> wraps outputs from all modules with derivation chains
                 (read-only, non-blocking for other modules)

M64 FUDD <====> M68 ICM  (bidirectional: FUD flags -> backpressure; advisory <- M68)
     |
     +--------> M66 EWA  (intervention candidates)

M65 Dark Passenger ----> M68 ICM  (psychosocial stressor signals)
     [BLOCKED: needs canonical spec]

M66 EWA <------ M68 ICM  (activation prompts with valve context)
     |
     +--------> M24/M43  (patient-facing wellness recommendations)

M67 ARGL ------> gates all reasoning output to M24/M43
     |
     +--------> M63 GBDC (evidence provenance -> derivation chains)

M68 ICM -------> M11/M24 (engagement), M21 (vault), M66 (activation), M48 (calibration)
```

## Recommended Build Order

1. **M68 ICM** (Critical, most dependencies feed from it, Dylan Handoff already prepared, 40-60 dev-days)
2. **M64 FUDD** (Critical, bidirectional feed with M68, heaviest clinical module)
3. **M67 ARGL** (Critical, gates all output quality, but can run in parallel with M64/M68 since it's a governance layer)
4. **M66 EWA** (High, downstream of M68 activation prompts, simpler build)
5. **M63 GBDC** (High, read-only wrapper, can be built last since it consumes existing artifacts)
6. **M65 Dark Passenger** (High -- canonical spec v1.0 now available, depends on M64+M68 feeds)

---

*Prepared by Andras with Logos -- March 2026*
