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
