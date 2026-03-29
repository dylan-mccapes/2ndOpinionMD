# V6 M53 — Probabilistic Terrain Model (PTM) Full Specification

**Version:** 1.0 — Full-Rigor Specification
**Status:** V6-only - Analysis-only - Non-executable - Read-only
**Classification:** Clinical reasoning infrastructure — probabilistic terrain computation
**Validated Against:** M63 GBDC v1.0 (carrier enums S5.1, S5.2); M67 ARGL Integration Contract; M54 TCS interface

---

## 1. Purpose

The Probabilistic Terrain Model (PTM) maintains a **time-evolving probability landscape** over multiple plausible conditions for a given patient, rather than forcing a single categorical diagnosis. It represents **partial expression, overlap, and uncertainty** across conditions and tracks how those probabilities **shift over time** in response to new data and interventions. PTM exists to support **early, non-pharmaceutical action** (e.g., lifestyle and monitoring strategies) before irreversible disease commitment or acute escalation is warranted.

**PTM computes and maintains the probability landscape when invoked; scheduling, cadence selection, and publish gating are owned by Module 54 (Terrain Conductor & Scheduler).**

PTM does **not** diagnose, prescribe, or mandate treatment; it contextualizes patient-specific terrain.

---

## 2. Scope

### 2.1 In Scope

* Maintain a **multi-condition probability vector** (top-N hypotheses + residual/unknown).
* Track **probability deltas across time windows** (e.g., 7 / 14 / 30 / 90 days).
* Incorporate uncertainty explicitly (confidence bands / volatility signals).
* Reflect **mixed phenotypes / codominance** without collapsing to a single label.
* Evaluate **recommendation tier gates** (proactive -> monitoring -> escalation prompts) when invoked.
* Emit M63-compliant derivation artifacts for every computation cycle.
* Emit uncertainty and constraint carriers per M63 S5.1 / S5.2.
* Declare M67 ARGL opt-in status and comply with integration contract.

### 2.2 Out of Scope

* Assigning definitive diagnoses.
* Executing diagnostic or prognostic tools directly.
* Triggering or prescribing treatments.
* Overriding upstream module outputs or governance constraints.
* **Cadence selection, publish gating, and deep-pass orchestration (owned by Module 54).**
* Evidence retrieval or knowledge curation (owned by MKE).
* Suppression policy execution (owned by M8/M9).

---

## 3. Inputs

PTM consumes **signals**, not raw data. All inputs must be tagged with source module, timestamp, and confidence.

### 3.1 Input Definitions

| Input | Source Module | Description | Pointer Format |
|---|---|---|---|
| `differentialHypotheses[]` | M18 (MPA) / M49 (Dx) / M17 (CIR) | Ranked condition hypotheses with likelihood contributions | `{source_module}:obs:hypothesis-set:{patient_id}:{timestamp}` |
| `riskTrajectorySignals[]` | M20 (Flare Risk) / M6 (PSI) / progression modules | Flare risk tiers, progression indicators, temporal trends | `{source_module}:obs:risk-signal:{patient_id}:{timestamp}` |
| `toolOutputs[]` | M51/M52 (Tool Library) | Diagnostic scores, phenotypers, flare predictors with trust/use-class metadata | `M51:obs:tool-result:{tool_id}:{patient_id}:{timestamp}` |
| `temporalContext` | M3 (Terrain Index) / temporal state modules | Change rates, persistence, reversals, volatility | `{source_module}:obs:temporal-context:{patient_id}:{timestamp}` |
| `interventionMetadata[]` | MKE patient layer (read-only) | What interventions were applied, when (lifestyle, monitoring changes) | `MKE:obs:intervention-record:{patient_id}:{timestamp}` |
| `updatePlan` | M54 (TCS) | Invocation context: which horizons to compute, publish permissions | `M54:plan:update-plan:{patient_id}:{timestamp}` |
| `narrativeState` | MKE-EoHD (optional) | Long-horizon narrative context for weighting/interpretation context only | `EoHD:doc:narrative-state:{patient_id}:{window_id}` |
| `priorLandscape` | M53 (self, prior cycle) | Previous PTM output for delta computation | `M53:obs:terrain-landscape:{patient_id}:{prev_timestamp}` |

### 3.2 Input Validation Rules

1. Every input artifact MUST carry: `source_module_id`, `timestamp` (ISO-8601), and `confidence` (float 0.0-1.0 or structured bounds object).
2. Inputs missing `confidence` metadata are accepted but marked `confidence = NOT_PROVIDED` and receive minimum trust weight in Step 2.
3. Inputs with timestamps older than the `updatePlan.staleness_threshold` (default: 180 days) are flagged `STALE` and down-weighted but not discarded.
4. If `updatePlan` is absent, PTM MUST NOT execute. Invocation without an M54 UpdatePlan is a hard gate violation.

---

## 4. Outputs

PTM emits **terrain representations**, not decisions.

### 4.1 Output Definitions

| Output | Artifact Type | Pointer Format | Description |
|---|---|---|---|
| `terrainLandscape` | Observation (FHIR) | `M53:obs:terrain-landscape:{patient_id}:{timestamp}` | `{ condition -> probability }` with uncertainty bounds for each condition |
| `trajectoryViews[]` | Observation (FHIR) | `M53:obs:trajectory:{patient_id}:{horizon}:{timestamp}` | Probability shifts over each defined time horizon (7/14/30/90 days) |
| `codominanceIndicators[]` | Flag (FHIR) | `M53:flag:codominance:{patient_id}:{timestamp}` | Flags when multiple conditions meaningfully co-exist (overlap > codominance_threshold) |
| `earlyWarningSignals[]` | DetectedIssue (FHIR) | `M53:alert:early-warning:{patient_id}:{timestamp}` | Rising probability trends or accelerating change exceeding alert thresholds |
| `recommendationTier` | Observation (FHIR) | `M53:obs:recommendation-tier:{patient_id}:{timestamp}` | Proactive (lifestyle/monitoring), Watchful, Escalation-discussion |
| `narrativeSummary` | DocumentReference (internal) | `M53:doc:terrain-narrative:{patient_id}:{timestamp}` | Human-readable explanation of terrain and uncertainty (no directives) |
| `computationRationale` | DocumentReference (internal) | `M53:doc:rationale:{patient_id}:{timestamp}` | Top contributing signals, weight assignments, and delta drivers |
| `degradationState` | Observation (FHIR) | `M53:obs:degradation-state:{patient_id}:{timestamp}` | Emitted when inputs are sparse/unstable; captures widened uncertainty reason |

### 4.2 Terrain Landscape Structure

```
terrainLandscape: {
  patient_id: string
  timestamp: ISO-8601
  invocation_ref: pointer -> M54:plan:update-plan:{pid}:{ts}
  hypotheses: [
    {
      condition_id: string
      condition_label: string
      probability: float (0.0 - 1.0)
      confidence_interval: { lower: float, upper: float }
      trend: enum { RISING, STABLE, FALLING, VOLATILE, INSUFFICIENT_DATA }
      trend_velocity: float (probability units per day, signed)
      contributing_signals: pointer[]  // references to input artifacts
      codominant_with: condition_id[] | null
    }
  ]
  residual_unknown: {
    probability: float  // 1.0 - sum(hypothesis probabilities)
    interpretation: string  // "unexplained terrain fraction"
  }
  volatility_index: float  // aggregate measure of landscape instability
  data_density_score: float  // 0.0 - 1.0, reflects input completeness
  horizon_set: int[]  // which horizons were computed (from UpdatePlan)
}
```

### 4.3 Output Invariants

1. `sum(hypotheses[].probability) + residual_unknown.probability` MUST equal 1.0 (within floating-point tolerance of 1e-6).
2. Every `hypotheses[].confidence_interval` MUST satisfy `lower <= probability <= upper`.
3. `residual_unknown.probability` MUST be >= 0.0. If the model accounts for all probability mass, residual is 0.0.
4. `volatility_index` MUST increase when successive landscapes show large deltas; it MUST NOT be fabricated when insufficient prior data exists (set to `NOT_COMPUTABLE` instead).

---

## 5. Process / Logic (Deterministic Steps)

PTM executes the following steps **in order** when invoked by M54 via UpdatePlan. Each step is a discrete transformation with defined inputs and outputs.

### Step 1: Validate Invocation

**Input:** `updatePlan` from M54
**Output:** Validated invocation context or HARD_REJECT

1.1. Verify `updatePlan` is present and structurally valid (contains `run_ptm_update: yes`, `ptm_horizon_set`, `publish_to_patient`, `publish_to_clinician`, `confidence_gate_status`).
1.2. If `updatePlan` is absent or `run_ptm_update != yes`, emit no output. Log `M53:audit:invocation-rejected:{pid}:{ts}` with reason `NO_VALID_UPDATE_PLAN`. Terminate.
1.3. Extract `horizon_set` from `updatePlan.ptm_horizon_set`. If empty, default to `[7, 14, 30, 90]`.
1.4. Load `priorLandscape` for this patient (most recent `M53:obs:terrain-landscape:{pid}:{prev_ts}`). If none exists, flag `is_initial_computation = true`.

**Constraint carrier emitted:** `M53:constraint:invocation-gate:{pid}:{ts}` (type: GOVERNANCE_GATE, references `M54:plan:update-plan:{pid}:{ts}`).

### Step 2: Collect and Normalize Inputs

**Input:** All input artifacts per S3.1
**Output:** Normalized signal vector `normalizedSignals[]`

2.1. **Collect** all available input artifacts for this patient from upstream modules, filtering by the `updatePlan.data_window` (default: all data since last PTM computation, or all available if `is_initial_computation`).

2.2. **Validate each input** against S3.2 rules:
   - Tag missing confidence as `confidence = NOT_PROVIDED`.
   - Flag stale inputs (timestamp older than `staleness_threshold`).
   - Count valid inputs. If `valid_input_count < minimum_input_threshold` (default: 3 distinct source modules), enter **degraded mode** (see Step 2.5).

2.3. **Normalize likelihood contributions** to a common scale:
   - For each `differentialHypotheses[]` entry: extract `condition_id`, `likelihood_contribution` (float 0.0-1.0), and `source_confidence`.
   - For each `riskTrajectorySignals[]` entry: map risk tier to a probability modifier using the governed mapping table (`gov:table:risk-to-probability-modifier:{version}`).
   - For each `toolOutputs[]` entry: extract the tool's score, apply the tool's `use_class` scaling factor from the Tool Library metadata.

2.4. **Construct `normalizedSignals[]`**: Each entry contains:
   - `signal_id`: unique identifier
   - `source_pointer`: pointer to the originating artifact
   - `condition_id`: which condition this signal pertains to (or `GLOBAL` if it affects all conditions)
   - `normalized_contribution`: float (-1.0 to 1.0, where negative = evidence against)
   - `confidence`: float or bounds object
   - `timestamp`: from source artifact
   - `staleness_flag`: boolean

2.5. **Degraded mode** (if `valid_input_count < minimum_input_threshold`):
   - Set `degradation_active = true`.
   - Emit `M53:obs:degradation-state:{pid}:{ts}` with reason `INSUFFICIENT_INPUT_DENSITY`.
   - Widen all confidence intervals by the governed `degradation_widening_factor` (default: 2.0x).
   - Continue computation but flag all outputs with `data_density_score < 0.3`.

**Provenance emitted:** `M53:prov:signals-from-inputs:{pid}:{ts}` linking each `normalizedSignal` to its source artifact pointer.

### Step 3: Weight Contributions

**Input:** `normalizedSignals[]`, `priorLandscape` (if exists), `narrativeState` (if provided)
**Output:** `weightedSignals[]`

3.1. **Assign trust weight** to each signal based on four factors:

| Factor | Weight Component | Computation |
|---|---|---|
| Source trust | `w_trust` | Governed per-module trust table (`gov:table:module-trust-weights:{version}`). Range 0.0-1.0. |
| Recency | `w_recency` | Exponential decay: `exp(-lambda * age_days)` where `lambda` is governed (default: 0.01). |
| Relevance | `w_relevance` | 1.0 if signal's `condition_id` matches a current hypothesis; 0.5 if `GLOBAL`; 0.2 if no match but related via governed condition-relationship table. |
| Stability | `w_stability` | If signal has appeared consistently in prior N cycles (default N=3), `w_stability = 1.0`. If new or volatile, `w_stability = 0.6`. If contradicts prior signal from same source, `w_stability = 0.3`. |

3.2. **Compute composite weight** for each signal:
   `composite_weight = w_trust * w_recency * w_relevance * w_stability`

3.3. **Apply narrative context** (optional, soft influence only):
   - If `narrativeState` is provided and contains long-horizon pattern indicators relevant to a condition, apply a narrative relevance modifier (range 0.8-1.2) to signals for that condition.
   - Narrative modifier MUST NOT exceed the governed bounds (default: +/-20% of composite weight).
   - If `narrativeState` is absent, all narrative modifiers default to 1.0.

3.4. **Store `weightedSignals[]`**: Each entry = `normalizedSignal` + `composite_weight` + `weight_components {w_trust, w_recency, w_relevance, w_stability, w_narrative}`.

**Constraint carrier emitted (if narrative modifier applied):** `M53:constraint:narrative-influence:{pid}:{ts}` (type: GOVERNANCE_GATE, references `EoHD:doc:narrative-state:{pid}:{window_id}` and the governed narrative influence bounds).

### Step 4: Maintain Concurrent Hypotheses (No Forced Collapse)

**Input:** `weightedSignals[]`, `priorLandscape` (if exists)
**Output:** `rawProbabilityVector[]`

4.1. **Initialize hypothesis set:**
   - If `is_initial_computation`: Build initial hypothesis set from all unique `condition_id` values present in `weightedSignals[]`. Set initial probability for each to `1.0 / (N + 1)` where N = number of conditions. Allocate `1.0 / (N + 1)` to `residual_unknown`.
   - If prior landscape exists: Carry forward `priorLandscape.hypotheses[]` as the starting probability vector.

4.2. **Aggregate weighted contributions per condition:**
   For each condition `c` in the hypothesis set:
   `delta_c = sum(weightedSignals[i].normalized_contribution * weightedSignals[i].composite_weight)` for all signals where `signal.condition_id == c` or `signal.condition_id == GLOBAL`.

4.3. **Apply probability update:**
   For each condition `c`:
   `raw_probability_c = prior_probability_c + (delta_c * learning_rate)`
   Where `learning_rate` is governed (default: 0.1). This prevents single-cycle probability jumps from dominating the landscape.

4.4. **Enforce non-collapse invariant:**
   - No condition may be removed from the hypothesis set unless its probability has been below `removal_threshold` (default: 0.01) for `removal_persistence` consecutive cycles (default: 3).
   - New conditions may be added if a signal references a `condition_id` not in the current hypothesis set AND its `normalized_contribution > addition_threshold` (default: 0.05).

4.5. **Renormalize:**
   - Clamp all probabilities to [0.0, 1.0].
   - Compute `residual_unknown = max(0.0, 1.0 - sum(raw_probability_c for all c))`.
   - If `sum > 1.0`, proportionally scale all `raw_probability_c` so `sum + residual_unknown = 1.0`, preserving `residual_unknown >= minimum_residual` (default: 0.02).
   - The `minimum_residual` enforces epistemic humility: the system always acknowledges the possibility of conditions not yet hypothesized.

4.6. **Store `rawProbabilityVector[]`**: Each entry = `{ condition_id, probability, delta_from_prior, contributing_signal_pointers[] }`.

**Invariant enforced:** No single signal may cause a probability shift greater than `max_single_signal_shift` (default: 0.15) in a single cycle. If a signal's contribution would exceed this, it is clamped and logged.
**Constraint carrier emitted:** `M53:constraint:no-forced-collapse:{pid}:{ts}` (type: INVARIANT_ENFORCEMENT).
**Constraint carrier emitted (if single-signal clamp fires):** `M53:constraint:single-signal-cap:{pid}:{ts}` (type: INVARIANT_ENFORCEMENT).

### Step 5: Propagate Probabilities Forward (Trajectory Computation)

**Input:** `rawProbabilityVector[]`, `priorLandscape` (if exists), `horizon_set` from UpdatePlan
**Output:** `trajectoryViews[]`, `volatilityIndex`, `codominanceIndicators[]`, `earlyWarningSignals[]`

5.1. **Compute trajectory per horizon:**
   For each horizon `h` in `horizon_set` (e.g., 7, 14, 30, 90 days):
   - If sufficient prior data exists (at least 2 prior landscapes spanning a period >= `h`):
     - Compute `trend_velocity_c = (current_probability_c - probability_c_at_t_minus_h) / h` for each condition `c`.
     - Classify `trend`: RISING if velocity > `trend_threshold` (default: 0.001/day), FALLING if < `-trend_threshold`, STABLE if within threshold, VOLATILE if sign has changed in the last 3 cycles.
   - If insufficient prior data: set `trend = INSUFFICIENT_DATA`, `trend_velocity = null`.

5.2. **Compute volatility index:**
   - `volatility_index = mean(abs(delta_from_prior) for all conditions in rawProbabilityVector)`.
   - If `is_initial_computation` or fewer than 2 prior landscapes, set `volatility_index = NOT_COMPUTABLE`.

5.3. **Detect codominance:**
   For every pair of conditions `(c1, c2)`:
   - If `probability_c1 > codominance_threshold` (default: 0.15) AND `probability_c2 > codominance_threshold` AND `abs(probability_c1 - probability_c2) < codominance_proximity` (default: 0.10):
     - Emit codominance indicator linking `c1` and `c2`.

5.4. **Detect early warnings:**
   For each condition `c`:
   - If `trend == RISING` AND `trend_velocity_c > alert_velocity_threshold` (default: 0.005/day) AND `probability_c > alert_probability_floor` (default: 0.10):
     - Emit early warning signal for condition `c`.
   - If `volatility_index > volatility_alert_threshold` (default: 0.08):
     - Emit general landscape instability warning.

5.5. **Compute confidence intervals per condition:**
   - Base interval width: `base_width = 0.10` (governed).
   - Adjust for data density: `adjusted_width = base_width / sqrt(data_density_score)` (wider when data is sparse).
   - If `degradation_active`: multiply width by `degradation_widening_factor`.
   - Clamp interval to [0.0, 1.0].
   - `confidence_interval = { lower: max(0.0, probability_c - adjusted_width/2), upper: min(1.0, probability_c + adjusted_width/2) }`.

**Provenance emitted:** `M53:prov:trajectory-from-landscape:{pid}:{ts}` linking trajectory outputs to `rawProbabilityVector` and prior landscapes.

### Step 6: Evaluate Recommendation Tiers

**Input:** `rawProbabilityVector[]`, `trajectoryViews[]`, `earlyWarningSignals[]`, `codominanceIndicators[]`
**Output:** `recommendationTier`

6.1. **Evaluate tier criteria** (mutually exclusive, evaluated in order of severity):

| Tier | Label | Criteria | Action Implication |
|---|---|---|---|
| 3 | ESCALATION_DISCUSSION | Any condition with `probability > 0.40` AND `trend == RISING` AND `trend_velocity > 0.005/day`; OR any early warning signal on a condition with `probability > 0.30` | Clinician should consider further workup discussion |
| 2 | WATCHFUL | Any condition with `probability > 0.25` AND (`trend == RISING` OR `trend == VOLATILE`); OR `volatility_index > 0.06`; OR codominance detected between conditions in different clinical categories | Increased monitoring frequency warranted |
| 1 | PROACTIVE | Default tier when no Tier 2 or Tier 3 criteria are met | Lifestyle/monitoring strategies, no escalation |

6.2. **Apply confidence gate:**
   - If `data_density_score < 0.3` OR `degradation_active`: cap maximum tier at WATCHFUL (cannot recommend ESCALATION_DISCUSSION on sparse data).
   - If `data_density_score < 0.15`: cap maximum tier at PROACTIVE.

6.3. **Record tier decision** with the specific criteria that triggered it (or the absence of trigger criteria for PROACTIVE).

**Constraint carrier emitted:** `M53:constraint:tier-confidence-gate:{pid}:{ts}` (type: GOVERNANCE_GATE, references `data_density_score` and tier cap logic).

### Step 7: Emit Landscape and Rationale

**Input:** All computed outputs from Steps 1-6
**Output:** All output artifacts per S4.1

7.1. **Assemble `terrainLandscape`** per the structure in S4.2, populating all fields from computed values.

7.2. **Generate `computationRationale`:**
   - List the top 5 contributing signals (by composite weight) for each condition in the top 3 by probability.
   - List any signals that were clamped (single-signal cap), flagged stale, or marked `confidence = NOT_PROVIDED`.
   - List any degradation conditions active.

7.3. **Generate `narrativeSummary`:**
   - Plain-language description of the terrain: which conditions are most probable, which are trending, what the uncertainty looks like.
   - MUST NOT contain diagnostic claims, treatment recommendations, or directive language.
   - MUST include uncertainty acknowledgment: "Based on available data, which has [high/moderate/limited] density..."

7.4. **Emit all output artifacts** with their defined pointer formats (S4.1).

7.5. **Emit audit artifacts** (see S9 for full specification).

7.6. **Emit DerivationChain** (see S8 for full specification).

**Provenance emitted:** `M53:prov:landscape-assembly:{pid}:{ts}` linking all output artifacts to their computation step sources.

---

## 6. Constraints / Governance

### 6.1 Hard Invariants

| ID | Invariant | Enforcement |
|---|---|---|
| INV-01 | **No diagnosis claims.** PTM outputs probabilities, not labels. No output may contain language asserting a definitive diagnosis. | Narrative summary validation gate; audit log check. |
| INV-02 | **No treatment mandates.** Recommendations are tiered guidance only. No output may prescribe, suggest, or mandate any intervention. | Tier output validation; no treatment-class content permitted. |
| INV-03 | **No single-signal dominance.** No single input signal may cause a probability shift > `max_single_signal_shift` in one cycle. Multiple inputs must corroborate shifts. | Step 4 clamp logic with constraint carrier emission. |
| INV-04 | **Auditability required.** Every probability change must be traceable to specific input signals with pointer-backed provenance. | DerivationChain completeness check per M63. |
| INV-05 | **Degradation-safe.** If inputs are sparse or unstable, PTM widens uncertainty rather than guessing. | Step 2.5 degraded mode; Step 5.5 interval widening; Step 6.2 tier cap. |
| INV-06 | **Invocation-bound.** PTM runs only when triggered via UpdatePlan from Module 54. | Step 1 hard gate. |
| INV-07 | **Probability conservation.** Total probability mass (hypotheses + residual) must equal 1.0. | Step 4.5 renormalization with floating-point tolerance. |
| INV-08 | **Minimum residual.** `residual_unknown >= minimum_residual` at all times. The system never claims complete knowledge. | Step 4.5 minimum residual enforcement. |
| INV-09 | **No forced collapse.** Conditions may not be removed from the hypothesis set unless below removal threshold for N consecutive cycles. | Step 4.4 removal criteria. |
| INV-10 | **Narrative read-only.** NarrativeState from MKE-EoHD influences weighting within governed bounds only; it cannot override signal-driven probabilities. | Step 3.3 narrative modifier bounds. |

### 6.2 Governed Parameters

All numeric thresholds referenced in the process steps are governed parameters, not hard-coded values. They are loaded from a versioned governance artifact:

```
gov:params:M53-terrain-params:{version}
```

| Parameter | Default | Description |
|---|---|---|
| `staleness_threshold` | 180 days | Inputs older than this are flagged STALE |
| `minimum_input_threshold` | 3 modules | Minimum distinct source modules before degraded mode |
| `degradation_widening_factor` | 2.0 | Confidence interval multiplier in degraded mode |
| `learning_rate` | 0.1 | Dampens per-cycle probability updates |
| `removal_threshold` | 0.01 | Probability floor before condition can be removed |
| `removal_persistence` | 3 cycles | Consecutive cycles below threshold before removal |
| `addition_threshold` | 0.05 | Minimum contribution for a new condition to be added |
| `minimum_residual` | 0.02 | Floor for residual_unknown |
| `max_single_signal_shift` | 0.15 | Cap on per-signal probability change |
| `trend_threshold` | 0.001/day | Velocity threshold for RISING/FALLING classification |
| `codominance_threshold` | 0.15 | Minimum probability for codominance consideration |
| `codominance_proximity` | 0.10 | Maximum probability gap between codominant conditions |
| `alert_velocity_threshold` | 0.005/day | Velocity for early warning emission |
| `alert_probability_floor` | 0.10 | Minimum probability for early warning eligibility |
| `volatility_alert_threshold` | 0.08 | Volatility index triggering instability warning |
| `base_interval_width` | 0.10 | Base confidence interval width |
| `narrative_modifier_bounds` | [0.8, 1.2] | Min/max narrative context influence multiplier |
| `lambda_recency_decay` | 0.01 | Exponential decay rate for recency weighting |

---

## 7. Dependencies

### 7.1 Upstream Modules (Feed PTM)

| Module | What PTM Reads | Pointer Available? |
|---|---|---|
| M18 (MPA) | Multi-pathway hypotheses with likelihood contributions | Yes (per M18 output contract) |
| M49 (Dx Engine) | Ranked differential diagnoses with evidence scores | Yes (per M49 output contract) |
| M17 (CIR) | Clinical interpretation reasoning outputs | Yes (per M17 output contract) |
| M20 (Flare Risk) | Flare risk tiers and progression indicators | Yes (per M20 output contract) |
| M6 (PSI) | Patient Stability Index scores and trajectories | Yes (per M6 output contract) |
| M3 (Terrain Index) | Stability band, stack level, temporal trends | Yes (per M3 addendum: `M3:obs:stability-band:{pid}:{ts}`) |
| M51/M52 (Tool Library) | Tool output scores with trust/use-class metadata | Yes (per Tool Library output contract) |
| MKE patient layer | Intervention metadata (read-only) | Partial (event stream; discrete pointers may be MISSING) |
| MKE-EoHD | NarrativeState (optional long-horizon context) | Yes (when available; absence is normal) |
| M54 (TCS) | UpdatePlan (invocation trigger) | Yes (`M54:plan:update-plan:{pid}:{ts}`) |

### 7.2 Downstream Consumers (Consume PTM)

| Consumer | What It Reads | Pointer Format |
|---|---|---|
| M54 (TCS) | PTM state metadata (last update, uncertainty width, volatility) | `M53:obs:terrain-landscape:{pid}:{ts}` |
| M64 (FUDD) | Terrain landscape as context for uncertainty decomposition | `M53:obs:terrain-landscape:{pid}:{ts}` |
| M24/M43 (UI) | Narrative summary, terrain landscape, recommendation tier | `M53:doc:terrain-narrative:{pid}:{ts}`, `M53:obs:recommendation-tier:{pid}:{ts}` |
| M48 (Continuous Learning) | Terrain evolution data for outcome correlation | `M53:obs:terrain-landscape:{pid}:{ts}`, `M53:obs:trajectory:{pid}:{h}:{ts}` |
| M63 (GBDC) | DerivationChain, uncertainty carriers, constraint carriers | All M53 artifact pointers |
| M67 (ARGL) | Terrain landscape and rationale for adversarial review | `M53:obs:terrain-landscape:{pid}:{ts}`, `M53:doc:rationale:{pid}:{ts}` |

---

## 8. M63 Compliance -- Derivation Chain Emission

### 8.1 Output Artifact Registration

| Output | Artifact Type | Pointer Format | Provenance Record Emitted? |
|---|---|---|---|
| `terrainLandscape` | Observation (FHIR) | `M53:obs:terrain-landscape:{patient_id}:{timestamp}` | Yes -- links to `normalizedSignals[]` snapshot and `rawProbabilityVector` |
| `trajectoryViews[]` | Observation (FHIR) | `M53:obs:trajectory:{patient_id}:{horizon}:{timestamp}` | Yes -- links to `terrainLandscape` and prior landscapes |
| `codominanceIndicators[]` | Flag (FHIR) | `M53:flag:codominance:{patient_id}:{timestamp}` | Yes -- links to `rawProbabilityVector` pair analysis |
| `earlyWarningSignals[]` | DetectedIssue (FHIR) | `M53:alert:early-warning:{patient_id}:{timestamp}` | Yes -- links to trajectory and probability data |
| `recommendationTier` | Observation (FHIR) | `M53:obs:recommendation-tier:{patient_id}:{timestamp}` | Yes -- links to tier evaluation criteria |
| `narrativeSummary` | DocumentReference (internal) | `M53:doc:terrain-narrative:{patient_id}:{timestamp}` | Yes -- links to `terrainLandscape` |
| `computationRationale` | DocumentReference (internal) | `M53:doc:rationale:{patient_id}:{timestamp}` | Yes -- links to `weightedSignals[]` and contributing inputs |
| `degradationState` | Observation (FHIR) | `M53:obs:degradation-state:{patient_id}:{timestamp}` | Yes -- links to input validation results |

### 8.2 Input Artifact Traceability

| Input | Source Module | Pointer Available? | If No, Gap Classification |
|---|---|---|---|
| `differentialHypotheses[]` | M18/M49/M17 | Partial | G-01: M18 and M17 may not yet emit pointer-backed hypothesis snapshots (depends on Tier 2/3 addendums). M49 has pointer-backed output per V5.2 spec. |
| `riskTrajectorySignals[]` | M20/M6 | Partial | G-02: M20 flare risk output may lack discrete artifact pointers pending addendum. M6 PSI has pointer-backed output. |
| `toolOutputs[]` | M51/M52 | Yes | Tool Library emits pointer-backed result artifacts. |
| `temporalContext` | M3 / temporal modules | Yes | M3 addendum defines pointer-backed outputs. |
| `interventionMetadata[]` | MKE patient layer | MISSING | G-03: MKE intervention records are event-stream entries without discrete artifact IDs. |
| `updatePlan` | M54 | Yes | M54 emits pointer-backed UpdatePlan objects. |
| `narrativeState` | MKE-EoHD | Yes (when available) | Absence is normal and handled (optional input). |
| `priorLandscape` | M53 (self) | Yes | Prior M53 output artifacts are pointer-backed by definition. |

### 8.3 Transformation Step Registration

| Step Index | Processing Stage | Owning Module | Input Pointers | Output Pointer |
|---|---|---|---|---|
| 1 | Validate Invocation (S5 Step 1) | M53 | `M54:plan:update-plan:{pid}:{ts}` | No discrete output -- gate only; constraint carrier emitted |
| 2 | Collect and Normalize Inputs (S5 Step 2) | M53 | All input artifact pointers per S3.1; some MISSING (G-01, G-02, G-03) | `M53:internal:normalized-signals:{pid}:{ts}` (internal working artifact) |
| 3 | Weight Contributions (S5 Step 3) | M53 | `M53:internal:normalized-signals:{pid}:{ts}`, `gov:table:module-trust-weights:{v}`, `EoHD:doc:narrative-state:{pid}:{wid}` (optional) | `M53:internal:weighted-signals:{pid}:{ts}` (internal working artifact) |
| 4 | Maintain Concurrent Hypotheses (S5 Step 4) | M53 | `M53:internal:weighted-signals:{pid}:{ts}`, `M53:obs:terrain-landscape:{pid}:{prev_ts}` | `M53:internal:raw-probability-vector:{pid}:{ts}` |
| 5 | Propagate Probabilities Forward (S5 Step 5) | M53 | `M53:internal:raw-probability-vector:{pid}:{ts}`, `M53:obs:terrain-landscape:{pid}:{prev_ts}`, horizon_set | `M53:obs:trajectory:{pid}:{h}:{ts}`, `M53:flag:codominance:{pid}:{ts}`, `M53:alert:early-warning:{pid}:{ts}` |
| 6 | Evaluate Recommendation Tiers (S5 Step 6) | M53 | `M53:internal:raw-probability-vector:{pid}:{ts}`, trajectory + warning outputs | `M53:obs:recommendation-tier:{pid}:{ts}` |
| 7 | Emit Landscape and Rationale (S5 Step 7) | M53 | All computed outputs from Steps 1-6 | `M53:obs:terrain-landscape:{pid}:{ts}`, `M53:doc:terrain-narrative:{pid}:{ts}`, `M53:doc:rationale:{pid}:{ts}` |
| 8 | Audit-grade emission | M53 | All outputs from Steps 2-7 | AuditEvent + Provenance records per S9 |

### 8.4 DerivationChain Assembly

M53 emits a DerivationChain per M63 S2 for every computation cycle:

```
derivation_chain: {
  chain_id: "M53:chain:{patient_id}:{timestamp}"
  output_ref: "M53:obs:terrain-landscape:{patient_id}:{timestamp}"
  output_form_class: LANDSCAPE
  inputs[]: [pointers to all consumed input artifacts]
  transformations[]: [Steps 1-8 per S8.3]
  assumptions[]: [
    { "minimum_residual_enforced": true, "value": minimum_residual },
    { "learning_rate_applied": true, "value": learning_rate },
    { "governed_params_version": "gov:params:M53-terrain-params:{version}" }
  ]
  motifs_referenced[]: [
    "motif:weighted-additive-aggregation",
    "motif:exponential-recency-decay",
    "motif:bayesian-probability-update",
    "motif:confidence-interval-construction"
  ]
  uncertainty_disclosure: { ... per S8.5 }
  constraint_disclosure: { ... per S8.6 }
  completeness_classification: TRACE_PARTIAL  // until G-01, G-02, G-03 are resolved
  replay_metadata: {
    chain_version: "1.0"
    idempotency_key: "{patient_id}:{timestamp}:{param_version}"
    production_timestamp: ISO-8601
    module_version_snapshot: { "M53": "1.0" }
    governance_state_snapshot_ref: "gov:params:M53-terrain-params:{version}"
    role_context: identifier
    input_sequence_ref: "M53:obs:terrain-landscape:{patient_id}:{prev_timestamp}"
      // PTM is path-dependent: current output depends on ordered history of prior landscapes
  }
}
```

**Completeness note:** The chain is TRACE_PARTIAL until upstream modules (M18, M17, M20, MKE intervention layer) provide pointer-backed artifacts for all inputs. Steps 2-3 have MISSING input pointers for gaps G-01, G-02, G-03.

---

## 8.5 M63 Compliance -- Uncertainty Carrier Emission

### Uncertainty Inventory

| Output | Uncertainty Metadata Emitted? | Carrier Type (per M63 S5.1 enum) | Notes |
|---|---|---|---|
| `terrainLandscape` | Yes -- confidence intervals per condition, volatility index, data density score | PROBABILITY_LANDSCAPE | Primary uncertainty carrier; includes per-condition intervals and aggregate volatility |
| `trajectoryViews[]` | Yes -- trend classification includes INSUFFICIENT_DATA and VOLATILE states | PROBABILITY_LANDSCAPE | Trajectory uncertainty inherits from landscape intervals |
| `codominanceIndicators[]` | Partial -- flags are binary but derive from probabilistic thresholds | NOT_PROVIDED | Codominance flags are deterministic given the landscape; uncertainty is in the landscape itself |
| `earlyWarningSignals[]` | Partial -- alerts carry the probability and velocity that triggered them | NOT_PROVIDED | Alert triggers are deterministic given trajectory; uncertainty is upstream |
| `recommendationTier` | Yes -- tier is gated by data density and degradation state | CONFIDENCE_INTERVAL | Tier confidence is bounded by the input data density |
| `narrativeSummary` | Yes -- must include uncertainty language per Step 7.3 | PROBABILITY_LANDSCAPE | Carries through from terrainLandscape carrier |
| `degradationState` | Yes -- this IS the degradation carrier | DEGRADATION_STATE | Emitted when degraded mode activates; references input validation results |

### Degradation State

M53 emits a `DEGRADATION_STATE` carrier whenever degraded mode is active (Step 2.5). The carrier structure:

```
{
  carrier_type: DEGRADATION_STATE
  source_module_id: "M53"
  artifact_pointer: "M53:obs:degradation-state:{patient_id}:{timestamp}"
  emitted_at: timestamp
  degradation_reason: enum { INSUFFICIENT_INPUT_DENSITY, HIGH_VOLATILITY, STALE_INPUTS }
  widening_factor_applied: float
  data_density_score: float
}
```

When M53 is NOT in degraded mode, the `DEGRADATION_STATE` carrier is absent (not NOT_PROVIDED -- genuinely not applicable). The `PROBABILITY_LANDSCAPE` carriers on `terrainLandscape` and `trajectoryViews` constitute the primary uncertainty disclosure.

---

## 8.6 M63 Compliance -- Constraint Carrier Emission

### Constraint Inventory

| Constraint | Trigger Condition | Constraint Type (per M63 S5.2 enum) | Artifact Format |
|---|---|---|---|
| Invocation gate | Step 1: UpdatePlan validation | GOVERNANCE_GATE | `M53:constraint:invocation-gate:{pid}:{ts}` with pointer to `M54:plan:update-plan:{pid}:{ts}` |
| No-forced-collapse | Step 4.4: Hypothesis removal prevention | INVARIANT_ENFORCEMENT | `M53:constraint:no-forced-collapse:{pid}:{ts}` |
| Single-signal cap | Step 4 (INV-03): Signal contribution exceeds `max_single_signal_shift` | INVARIANT_ENFORCEMENT | `M53:constraint:single-signal-cap:{pid}:{ts}` with clamped signal reference |
| Narrative influence bounds | Step 3.3: Narrative modifier applied within governed bounds | GOVERNANCE_GATE | `M53:constraint:narrative-influence:{pid}:{ts}` with EoHD reference and bounds |
| Tier confidence gate | Step 6.2: Data density caps maximum recommendation tier | GOVERNANCE_GATE | `M53:constraint:tier-confidence-gate:{pid}:{ts}` with density score and cap applied |
| Minimum residual | Step 4.5: Residual unknown enforced >= floor | INVARIANT_ENFORCEMENT | `M53:constraint:minimum-residual:{pid}:{ts}` |
| Governed parameter version | All steps: Parameters loaded from versioned governance artifact | GOVERNANCE_GATE | `M53:constraint:param-version:{pid}:{ts}` with pointer to `gov:params:M53-terrain-params:{version}` |

### Materiality Declaration

For each constraint in the inventory: when the constraint fires (i.e., the invariant is tested and holds, or the gate is consulted), M53 MUST include the corresponding constraint record in its output bundle for that computation cycle. This constitutes M53's materiality declaration per M63 S3.4.

The **single-signal cap** constraint is a conditional emitter: it only fires when a signal's contribution would exceed the governed threshold. The **invocation gate** and **governed parameter version** constraints fire every cycle. All others fire conditionally based on computation state.

---

## 9. FHIR Audit Artifact Emission

### 9.1 AuditEvent Emission

| Event | Trigger | Required Fields |
|---|---|---|
| `M53:audit:invocation-accepted` | Step 1 passes | `patient_id`, `timestamp`, `update_plan_ref`, `horizon_set`, `module_version`, `param_version` |
| `M53:audit:invocation-rejected` | Step 1 fails | `patient_id`, `timestamp`, `rejection_reason`, `module_version` |
| `M53:audit:degradation-entered` | Step 2.5 activates degraded mode | `patient_id`, `timestamp`, `degradation_reason`, `data_density_score`, `valid_input_count`, `widening_factor` |
| `M53:audit:landscape-computed` | Step 7 completes | `patient_id`, `timestamp`, `hypothesis_count`, `top_condition`, `top_probability`, `volatility_index`, `data_density_score`, `module_version`, `param_version` |
| `M53:audit:tier-evaluated` | Step 6 completes | `patient_id`, `timestamp`, `recommendation_tier`, `triggering_criteria`, `tier_cap_applied`, `data_density_score` |
| `M53:audit:signal-clamped` | Step 4 INV-03 fires | `patient_id`, `timestamp`, `signal_ref`, `original_contribution`, `clamped_contribution`, `affected_condition` |
| `M53:audit:condition-added` | Step 4.4 adds new condition | `patient_id`, `timestamp`, `condition_id`, `initial_probability`, `triggering_signal_ref` |
| `M53:audit:condition-removed` | Step 4.4 removes condition below threshold | `patient_id`, `timestamp`, `condition_id`, `final_probability`, `cycles_below_threshold` |
| `M53:audit:codominance-detected` | Step 5.3 emits codominance flag | `patient_id`, `timestamp`, `condition_pair`, `probabilities`, `proximity` |
| `M53:audit:early-warning-emitted` | Step 5.4 emits early warning | `patient_id`, `timestamp`, `condition_id`, `probability`, `trend_velocity`, `alert_type` |

### 9.2 Provenance Emission

| Provenance Record | Connects | FHIR Resource Type |
|---|---|---|
| `M53:prov:signals-from-inputs` | Input artifacts -> `normalizedSignals[]` | Provenance |
| `M53:prov:weights-from-signals` | `normalizedSignals[]` + trust tables -> `weightedSignals[]` | Provenance |
| `M53:prov:probability-from-weights` | `weightedSignals[]` + prior landscape -> `rawProbabilityVector[]` | Provenance |
| `M53:prov:trajectory-from-landscape` | `rawProbabilityVector[]` + prior landscapes -> `trajectoryViews[]` | Provenance |
| `M53:prov:tier-from-analysis` | Probability vector + trajectories + warnings -> `recommendationTier` | Provenance |
| `M53:prov:landscape-assembly` | All computed outputs -> `terrainLandscape` + `narrativeSummary` + `rationale` | Provenance |
| `M53:prov:chain-production` | All artifacts -> DerivationChain | Provenance |

---

## 10. M67 (ARGL) Integration

### 10.1 Opt-In Status: ACTIVE

**Rationale:** M53 produces probabilistic outputs, trajectory forecasts, and recommendation tier evaluations -- categories explicitly within ARGL's governance scope (M67 Scope, "clinical interpretations, pattern detections, trajectory forecasts, or recommendation candidates"). PTM's terrain landscape is a core reasoning output that influences downstream clinical decisions and patient-facing communication. ARGL adversarial review is warranted.

### 10.2 ARGL Submission Contract

M53 submits its outputs for ARGL review under the following contract:

**What is submitted:**
- `terrainLandscape` (the probability landscape itself)
- `computationRationale` (signal weights and contributors)
- `recommendationTier` (the tier evaluation and triggering criteria)

**What is NOT submitted** (not reasoning outputs; structural/deterministic):
- `degradationState` (operational signal, not a reasoning claim)
- `codominanceIndicators` (deterministic from landscape; reviewed indirectly via landscape review)
- `earlyWarningSignals` (deterministic from trajectory; reviewed indirectly)

**Submission trigger:** Every computation cycle that produces a `terrainLandscape` with `recommendation_tier >= WATCHFUL` (Tier 2 or 3). Tier 1 (PROACTIVE) outputs are submitted only if `volatility_index > volatility_alert_threshold`.

### 10.3 ARGL Invariant Compliance

| ARGL Invariant | M53 Compliance |
|---|---|
| I-B1 (Every claim carries a tag) | Every condition probability in the landscape is pointer-backed to contributing signals. The `computationRationale` documents the tag chain. |
| I-B2 (Tags are typed) | Input signals carry typed evidence from upstream modules. M53 preserves source types in the rationale. |
| I-C1 (Rebind or discard) | M53 binds to: (1) the clinical question (UpdatePlan reason codes), (2) current patient state (input signals are current-cycle), (3) evidence set (all contributing signals with pointers). |
| I-C2 (State changes logged) | Every probability delta is logged with `delta_from_prior` and `contributing_signal_pointers[]`. |
| I-D1 (Mandatory falsification) | ARGL's Falsifier Agent (A9) reviews the terrain landscape. M53 does not self-falsify; it provides the structured output for external adversarial review. |
| I-E1 (Conflicts must surface) | Codominance indicators and volatility index surface conflicting signals. The rationale documents when signals from different modules disagree. |
| I-E2 (Unknowns remain unknown) | `residual_unknown` is always >= `minimum_residual`. `INSUFFICIENT_DATA` trend classifications are preserved. |
| I-F2 (No clinical recommendations from ARGL) | M53's recommendation tiers are guidance classifications, not clinical recommendations. ARGL reviews the terrain but does not substitute its own tier evaluation. |

### 10.4 ARGL Review Outcome Handling

If ARGL returns a rejection or hold on M53 output:
- The `terrainLandscape` is NOT published to patient-facing or clinician-facing surfaces.
- The landscape IS stored internally (it remains valid as a computation; ARGL's concern is reasoning quality, not computation correctness).
- M53 emits `M53:audit:argl-hold:{pid}:{ts}` with the ARGL decision record reference.
- The `recommendationTier` is downgraded to PROACTIVE until the ARGL hold is resolved.
- M54 is notified via the standard event channel so it can adjust scheduling.

---

## 11. Versioning Note

* **Introduced in V6** as a new EoH module.
* Does **not** alter V5.2 behavior.
* Internal math and weighting may evolve without changing the module contract.
* Governed parameters (S6.2) allow tuning without spec amendment.
* Parameter changes require governance version increment and audit trail.

---

## 12. Gap Register

| Gap ID | V6 Requirement | Why Spec Cannot Fully Satisfy | Resolution Path |
|---|---|---|---|
| G-01 | M63 S3.1 Trace Integrity: input pointers for differential hypotheses | M18 (MPA) and M17 (CIR) may not yet emit pointer-backed hypothesis snapshots. M49 does. | M18 addendum (Tier 2) and M17 addendum (Tier 2) must emit pointer-backed output artifacts. Until then, Steps 2-3 have MISSING input pointers for M18/M17 sources. |
| G-02 | M63 S3.1 Trace Integrity: input pointers for risk trajectory signals | M20 flare risk output may lack discrete artifact pointers pending addendum. M6 PSI has pointers. | M20 addendum (Tier 3) must register output artifacts. |
| G-03 | M63 S3.1 Trace Integrity: input pointers for intervention metadata | MKE intervention records are event-stream entries without discrete artifact IDs. | MKE patient layer must register intervention events as pointer-backed artifacts. This is an MKE infrastructure task. |
| G-04 | M67 ARGL integration: full evidence tag chain | M53 preserves upstream evidence types in rationale but does not independently verify tag validity. ARGL's tag verification depends on upstream modules providing M67-compliant tags. | Upstream module ARGL opt-in (M18, M49, M17) will close the tag chain. M53 carries through whatever tagging its inputs provide. |

---

## 13. Acceptance Tests

| ID | Test | Input | Expected Result |
|---|---|---|---|
| AT-01 | **Invocation gate enforced** | M53 invoked without UpdatePlan from M54 | No computation. `M53:audit:invocation-rejected` emitted. No output artifacts. |
| AT-02 | **Probability conservation** | Any valid computation cycle | `sum(hypotheses[].probability) + residual_unknown.probability == 1.0` (within 1e-6 tolerance) |
| AT-03 | **Minimum residual enforced** | Computation where all hypotheses have high probability | `residual_unknown.probability >= minimum_residual` (0.02 default) |
| AT-04 | **No forced collapse** | Condition drops below 0.01 for 1 cycle | Condition remains in hypothesis set. Only removed after `removal_persistence` consecutive cycles below threshold. |
| AT-05 | **Single-signal cap** | One signal contributes a delta > 0.15 | Delta clamped to 0.15. `M53:audit:signal-clamped` emitted. `M53:constraint:single-signal-cap` carrier emitted. |
| AT-06 | **Degraded mode activation** | Fewer than 3 distinct source modules provide valid inputs | `degradation_active = true`. Confidence intervals widened by `degradation_widening_factor`. `M53:obs:degradation-state` emitted. Recommendation tier capped. |
| AT-07 | **Tier confidence gate** | `data_density_score < 0.3` with conditions meeting ESCALATION criteria | Tier capped at WATCHFUL. `M53:constraint:tier-confidence-gate` carrier emitted. |
| AT-08 | **No diagnosis claims in narrative** | Any computation cycle | `narrativeSummary` contains no definitive diagnosis language. Validation pass against prohibited terms list. |
| AT-09 | **DerivationChain completeness** | Computation with all pointer-backed inputs available | DerivationChain `completeness_classification = TRACE_COMPLETE`. All steps pointer-backed. |
| AT-10 | **DerivationChain partial trace** | Computation with M18 input (MISSING pointer, G-01) | DerivationChain `completeness_classification = TRACE_PARTIAL`. MISSING placeholder at Step 2 for M18 input. |
| AT-11 | **Uncertainty carriers present** | Any computation producing `terrainLandscape` | `uncertainty_disclosure.status = CARRIERS_PRESENT`. PROBABILITY_LANDSCAPE carrier references `M53:obs:terrain-landscape`. |
| AT-12 | **Degradation state carrier** | Degraded mode active | `DEGRADATION_STATE` carrier emitted referencing `M53:obs:degradation-state`. |
| AT-13 | **Constraint carriers match M63 S5.2 enum** | Any computation cycle | All emitted constraint types are from the closed enum: GOVERNANCE_GATE, INVARIANT_ENFORCEMENT. No invented types. |
| AT-14 | **Codominance detection** | Two conditions both > 0.15 probability, gap < 0.10 | `M53:flag:codominance` emitted for the pair. |
| AT-15 | **Early warning detection** | Condition with probability > 0.10, RISING trend, velocity > 0.005/day | `M53:alert:early-warning` emitted for that condition. |
| AT-16 | **Narrative modifier bounds** | NarrativeState provided with strong long-horizon indicators | Narrative modifier applied within [0.8, 1.2] bounds. No modifier exceeds governed limits. Constraint carrier emitted. |
| AT-17 | **ARGL submission on Tier 2+** | Computation produces `recommendationTier = WATCHFUL` | Outputs submitted to ARGL per S10.2. |
| AT-18 | **ARGL hold handling** | ARGL returns hold decision | Landscape stored but not published. Tier downgraded to PROACTIVE. `M53:audit:argl-hold` emitted. M54 notified. |
| AT-19 | **Replay determinism** | Same inputs, same parameter version, same prior landscape | Identical `terrainLandscape` output. DerivationChain structurally identical. |
| AT-20 | **Stale input handling** | Input with timestamp older than `staleness_threshold` | Input flagged STALE, down-weighted via recency decay, but not discarded. Rationale documents staleness. |
| AT-21 | **Initial computation (no prior landscape)** | First PTM run for a patient | `is_initial_computation = true`. Uniform probability distribution. `volatility_index = NOT_COMPUTABLE`. Trends = INSUFFICIENT_DATA. |

---

## 14. Metrics (Track Over Time)

| Metric | Definition | Target Direction |
|---|---|---|
| Landscape stability | Mean volatility index across patients per period | Context-dependent (low is good for stable patients; high may be appropriate during diagnostic workup) |
| Degradation rate | % of computation cycles entering degraded mode | Decrease over time (indicates improving input coverage) |
| Codominance frequency | % of landscapes with active codominance flags | Monitor (not inherently good or bad; reflects phenotype complexity) |
| Early warning lead time | Days between first early warning and downstream clinical action | Increase (earlier detection = more value) |
| Tier accuracy | Correlation between recommendation tier and eventual clinical trajectory | Increase |
| ARGL pass rate | % of ARGL-submitted outputs that pass adversarial review | Increase over time |
| GLASS_BOX eligibility | % of PTM outputs qualifying for GLASS_BOX label per M63 | Increase as upstream gaps (G-01 through G-03) close |
| Pointer completeness | % of DerivationChain steps that are fully pointer-backed | Increase as upstream addendums land |

---

## 15. Mathematical Motifs (M63 Motif Registry References)

Per M63 S8.1, M53 references the following structural motifs. These are named abstract forms, not computational implementations.

| Motif ID | Name | Usage in M53 |
|---|---|---|
| `motif:weighted-additive-aggregation` | Weighted Additive Aggregation | Step 3: Composite weight = product of factor weights. Step 4: Delta per condition = weighted sum of signal contributions. |
| `motif:exponential-recency-decay` | Exponential Recency Decay | Step 3.1: `w_recency = exp(-lambda * age_days)` for temporal discounting of older signals. |
| `motif:bayesian-probability-update` | Bayesian Probability Update (structural form) | Step 4.3: Prior probability + learning-rate-dampened delta. The structural form of updating beliefs given new evidence. |
| `motif:confidence-interval-construction` | Confidence Interval Construction | Step 5.5: Base width adjusted by data density and degradation factor, clamped to [0.0, 1.0]. |
| `motif:proportional-renormalization` | Proportional Renormalization | Step 4.5: Scale probabilities to sum to 1.0 while preserving minimum residual. |

---

## 16. Canonical Anchor Statement

**PTM (M53) represents patient-specific terrain as a probability landscape over time, enabling early, low-risk action without premature diagnosis or treatment lock-in.**

The landscape is always uncertain. The uncertainty is always disclosed. The system never claims to know what it does not know. When data is sparse, the landscape widens honestly rather than guessing confidently. Every probability shift is traceable to the signals that caused it, and every signal is traceable to the module that produced it.

---

*End of V6 M53 -- Probabilistic Terrain Model (PTM) Full Specification v1.0*
