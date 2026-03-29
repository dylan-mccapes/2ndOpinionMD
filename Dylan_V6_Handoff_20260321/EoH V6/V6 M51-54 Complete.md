## **V6 M51 — EoH Sentinel**

**Tool Watchdog between MKE Ingestion and EoH Tool Builder**

### **Purpose (3–5 sentences)**

EoH Sentinel is an **offline watchdog** that monitors MKE’s ingestion stream and detects **new diagnostic/prognostic “tool-like” artifacts** (scores, models, calculators, guideline algorithms). It extracts their structure (inputs/outputs/model definition/performance/context) and normalizes each into a standardized **ToolCandidate** object. Sentinel also maintains a registry of discovered tools and their lifecycle status so the tool universe can be reviewed, approved, versioned, and audited. Sentinel **does not** execute tools or choose tools at query time; it only keeps the candidate pool current and structured. (New logic; V6 only.)

### **Scope**

#### **In scope**

* Detect that a new diagnostic/prognostic tool exists in newly ingested content (papers, guidelines, model cards, APIs).  
* Extract tool structure: inputs, outputs, model definition blocks, thresholds, performance metrics, applicability, limitations.  
* Classify tool\_type / primary\_task / domain / horizon / modality dependence.  
* Emit a standardized **ToolCandidate** object and corresponding **ToolRegistry** entry.  
* Drive candidate lifecycle states: `new → pending_review → approved → rejected → deprecated`.  
* Emit audit-grade events: `ToolCandidateCreated`, `ToolCandidateUpdated`, `ToolDeprecated` (+ audit metadata).

#### **Out of scope**

* Deep integration into EoH reasoning modules (owned by **Tool Builder \+ downstream wiring**).  
* Query-time tool selection or fusion (owned by **EoH runtime \+ Tool Library**).  
* Tool execution/prediction/scoring (owned by **runtime engines** / MKE services / tool runtimes).  
* Clinical truth claims or guideline interpretation beyond extraction/typing.

### **Inputs**

#### **Triggers**

* **Batch trigger:** invoked on scheduled MKE ingest cycles (weekly/monthly) via a `NewDocsBatch` event containing doc\_ids.  
* **On-demand trigger:** manual run against specified `doc_id`, URL, DOI, guideline update, or model card.  
* **Incremental trigger (optional):** subscription to high-value ingestion topics for near–real-time detection.

#### **Primary inputs (from MKE)**

A normalized document payload with at least:

* `doc_id`, `title`, `abstract`, `fulltext` (or sectioned text)  
* `sections[]` with headings (Methods/Results/Model Development, etc.)  
* `tags[]` (domain hints)  
* `source` (journal|guideline|api|preprint|registry)  
* `pub_date`

### **Outputs**

#### **1\) ToolCandidate (core output)**

A normalized candidate object suitable for Tool Builder intake. **Minimum required fields**:

* `tool_id` (sentinel-generated UUID)  
* `source_doc_id`  
* `name` (+ optional aliases)  
* `tool_type` \+ `primary_task`  
* `clinical_domain[]`  
* `inputs[]` (typed \+ required flag \+ optional coding pointers)  
* `outputs[]` (typed \+ range/buckets when available)  
* `model_spec` (family \+ extractable equation/pseudocode/rules \+ thresholds when available)  
* `performance` (at least one metric when available; never invented)  
* `applicability` \+ `limitations`  
* `sentinel_metadata` (detected\_at, sentinel\_version, confidence, status, notes)

#### **2\) ToolRegistry entry**

A persisted record keyed by `tool_id` (and later tool family grouping if needed) containing:

* status, timestamps, source pointers, version lineage pointers, review outcomes, and de-dup references.

#### **3\) Events \+ audit artifacts**

* `ToolCandidateCreated`  
* `ToolCandidateUpdated`  
* `ToolCandidateDeprecated`  
* Each event produces an AuditEvent-style record with:  
  * who/what triggered it, input doc\_ids, extraction confidence, and outcome status.

### **Process / Logic (deterministic stages)**

#### **Stage 0 — Candidate Document Detection**

Goal: from newly ingested docs, identify documents likely containing a usable tool.

* Heuristic signals (rules \+ model-assisted classification):  
  * “risk score”, “prediction model”, “scoring system”, “nomogram”, “clinical decision rule”  
  * performance metrics language (“AUROC”, “C-statistic”, “calibration”, etc.)  
  * guideline flowchart / if-then pathway structure  
  * presence of equations, coefficient tables, decision trees, feature lists  
    Output:  
* `tool_candidate_doc=true|false` per doc with a detection confidence.

#### **Stage 1 — Tool Snippet Extraction**

For each candidate doc:

* Extract model definition blocks:  
  * equations, point tables, if/then trees, rule lists, pseudocode fragments, API specs  
* Extract input variables:  
  * names, datatypes, units (when present), required vs optional  
* Extract outputs:  
  * probability/score/class label/stage/time-to-event; time horizon if present  
* Extract performance:  
  * AUROC/AUPRC/sensitivity/specificity/etc. (only if reported)  
  * validation\_type, sample\_size when extractable  
* Extract applicability/limitations:  
  * population, setting, geography, exclusions, known constraints  
    Output:  
* A structured extraction bundle per doc/tool with evidence pointers to source text spans.

#### **Stage 2 — Tool Typing & Tagging**

Classify:

* `tool_type` (diagnostic\_score, flare\_predictor, progression\_model, severity\_score, phenotyper, guideline\_algorithm, etc.)  
* `primary_task`  
* `clinical_domain[]`  
* `time_horizon` (if prognostic)  
* modality dependence (EHR/labs/PROs/imaging)  
  Output:  
* Tool typing fields \+ classifier confidence.

#### **Stage 3 — Quality & Safety Filter**

Goal: prevent flooding Tool Builder with unusable garbage.

* Minimum completeness gates (configurable, but deterministic):  
  * inputs and outputs are at least partially extractable  
  * at least one performance metric OR explicitly “none reported” tagged  
  * some context: population or setting or sample\_size (if available)  
* Output status assignment:  
  * `new` if passes minimal completeness  
  * `pending_review` if incomplete/ambiguous but potentially salvageable  
  * `rejected` if clearly not a tool or too underspecified  
    Important:  
* Sentinel **must not invent metrics**; missing values remain null and are recorded as limitations.

#### **Stage 4 — ToolCandidate Assembly**

Assemble the ToolCandidate JSON from Stage 1–3 outputs.

* Generate `tool_id`  
* Attach evidence pointers and extraction confidence  
* Attach status and notes

#### **Stage 5 — Registry, De-dup hints, and Handoff**

* Persist ToolCandidate to ToolRegistry  
* Emit `ToolCandidateCreated/Updated`  
* Provide “de-dup hint” fields (same name/aliases, same domain/task, similar inputs) **without** enforcing merge logic (Tool Builder owns dedup/versioning decisions).

### **Governance / Constraints**

* **Offline only:** Sentinel is not in the per-patient query hot path.  
* **No execution:** Sentinel never runs a diagnostic score or model.  
* **No selection:** Sentinel never chooses tools for a patient question.  
* **No invented facts:** No fabricated performance metrics, thresholds, or validation claims.  
* **Human review lane:** certain tool types/domains may be forced to `pending_review` until approved (policy-controlled).  
* **Lifecycle state machine is mandatory:** every candidate must have a status; deprecated tools remain auditable.  
* **De-dup is advisory only:** Sentinel may suggest duplicates; Tool Builder decides canonicalization/versioning.

### **Dependencies**

* **Upstream:** MKE ingestion pipeline (document stream \+ metadata).  
* **Downstream:** EoH Tool Builder (compiler) consumes ToolCandidates.  
* **Side systems:** ToolRegistry storage; event bus; audit logging sink.

### **Audit Hooks**

Sentinel must log at minimum:

* detection event: doc\_id(s), timestamp, sentinel\_version, detection confidence, tool count found  
* for each ToolCandidate:  
  * tool\_id, source\_doc\_id, extracted name/aliases  
  * extracted inputs/outputs presence flags  
  * performance fields presence flags (not values if absent)  
  * validation\_type/sample\_size presence flags  
  * status transitions with reasons (`new`, `pending_review`, `rejected`, `deprecated`)  
* de-dup hints and any “superseded by” relationships recorded later  
* linkable evidence pointers (source text span IDs) for every extracted critical field

---

## 

## 

## **V6 M52 — EoH Tool Builder**

**Tool Compiler: ToolCandidate → ToolDefinition \+ ToolImplementation \+ Tool Library Entry**

### **Purpose (3–5 sentences)**

EoH Tool Builder is an **offline compiler** that converts Sentinel’s raw **ToolCandidate** objects into **EoH-native, versioned tools** that can be safely selected and executed at runtime. It produces three artifacts: **ToolDefinition** (canonical metadata \+ routing semantics), **ToolImplementation** (how the tool is executed), and a **Tool Library Index** entry for fast query-time selection. Tool Builder owns deduplication/versioning, input harmonization (names/units/ontology bindings), and safe-use tagging; it does not itself run tools for a patient. Tool Builder enforces auditability and reversibility so every tool version can be traced back to its source documents and compilation decisions. (New logic; V6 only.)

---

### **Scope**

#### **In scope**

* Intake ToolCandidate objects from Sentinel and normalize them into EoH-native tool artifacts.  
* Deduplicate candidates against existing tools; decide “new tool” vs “new version.”  
* Structural validation of candidates (completeness, parseability, mappability).  
* Harmonize inputs: canonical names, units, coding bindings, missingness handling.  
* Assign routing metadata: which EoH modules can consume the tool and in what role.  
* Choose an execution strategy and generate ToolImplementation artifacts.  
* Compute/assign trust and safe-use tags (primary vs adjunct; review requirements).  
* Publish tool versions into the Tool Library and maintain status lifecycle.  
* Emit audit-grade records for every compile/publish/deny/deprecate action.

#### **Out of scope**

* Detecting tools in documents (owned by Sentinel).  
* Query-time tool selection/fusion (owned by EoH runtime \+ tool selection layer).  
* Actual execution of tools on patient data (owned by runtime engine/tool runtime).  
* Clinical guideline interpretation beyond converting explicit tool definitions into executable representations.

---

### **Inputs**

#### **Primary input**

* **ToolCandidate** objects from V6 M51 (Sentinel), including:  
  * tool identity, type/task/domain  
  * inputs/outputs  
  * model\_spec (equation/rules/pseudocode/API spec pointers)  
  * performance/applicability/limitations  
  * Sentinel metadata and evidence pointers

#### **Reference inputs / dependencies**

* Existing **Tool Library** manifest (current active \+ deprecated tool versions)  
* MKE feature/ontology interface (to map inputs to canonical data paths)  
* Policy configuration:  
  * versioning rules  
  * approval requirements by tool\_type/domain  
  * trust/safety tagging thresholds (configurable; not hard-coded)

---

### **Outputs**

#### **1\) ToolDefinition (compiled, canonical tool)**

A stable, versioned representation containing:

* `tool_id` (stable), `version` (semver), `name`, `aliases`  
* `tool_type`, `primary_task`, `clinical_domain`  
* canonical `inputs[]` with units, coding bindings, missing handling  
* canonical `outputs[]` with ranges/buckets when known  
* `model_spec` representation (DSL / model\_ref / API binding)  
* `performance` summary (reported \+ local validation slots)  
* `applicability`, `limitations`, `regulatory` posture  
* `routing` metadata: modules, roles, scenarios, priority  
* `source` lineage: doc\_ids, sentinel ids, timestamps  
* `status`: `draft | active | deprecated | rejected`

#### **2\) ToolImplementation (executable plan)**

An execution artifact describing:

* runtime type: `expression_eval | python_model | external_api | llm_surrogate | unsupported`  
* runtime config (DSL expression, module path, endpoint, prompt template id)  
* feature\_map: canonical inputs → MKE feature paths  
* safety gates: max frequency, human review requirements, hard stops

#### **3\) Tool Library Index entry**

A minimal indexed entry for selection:

* tool\_id, version, name  
* tool\_type, primary\_task, domain, horizon  
* priority \+ trust score  
* status

#### **4\) Events \+ audit artifacts**

* `ToolCompiled`  
* `ToolPublished`  
* `ToolRejected`  
* `ToolDeprecated`  
  Each emits AuditEvent-style records with:  
* tool\_id/version, source lineage, policy versions, compile decisions, and reviewer approvals (if required)

---

### **Process / Logic (deterministic pipeline)**

#### **Stage 0 — Intake & Deduplication**

Goal: decide whether a ToolCandidate is:

* a new tool, or  
* a new version of an existing tool.

Steps:

* Canonicalize name \+ aliases (normalize casing, punctuation, known synonyms).  
* Compare against existing tools using a deterministic match policy:  
  * name/alias similarity \+ same domain/task  
  * overlap of canonicalized inputs  
  * similarity of model\_spec representation (when parseable)  
    Decision:  
* If match → treat as version update (semver bump rule from policy)  
* If no match → create new tool\_id, version \= 1.0.0  
  Output:  
* `dedup_decision` record with justification pointers.

#### **Stage 1 — Structural Validation**

Goal: reject unusable or dangerously incomplete candidates early.

Checks (policy-driven):

* Inputs and outputs present (at least minimally)  
* At least one performance metric extracted OR explicitly marked “none reported”  
* Model spec is parseable into one of:  
  * equation/score DSL  
  * rules tree/if-then DSL  
  * external API contract  
  * model wrapper reference (if weights/code provided)  
* Time horizon present or inferable for prognostic tools (if required by tool\_type)  
* Inputs mappable to MKE features (directly or via allowed transforms)

If fail:

* mark ToolCandidate → rejected with reasons  
* emit `ToolRejected` \+ audit artifacts

#### **Stage 2 — Harmonization (Variables, Units, Ontologies)**

Goal: map ToolCandidate inputs into canonical features.

Steps:

* Normalize input names (“CRP”, “C-reactive protein” → `serum_crp`)  
* Normalize units (mg/dL vs mg/L, etc.) and embed conversion rules in implementation metadata  
* Bind to ontology codes where available (LOINC/SNOMED/RxNorm pointers)  
* Define `feature_map` for each canonical input → MKE feature path (e.g., `mke.labs.crp.latest`)  
* Define missing handling per input based on policy and tool requirements:  
  * exclude / default / median / hard-stop

If an input cannot be reliably mapped:

* set tool status to `draft` or `pending_manual_mapping` (policy term)  
* require human configuration before publication

#### **Stage 3 — Routing & Role Assignment (EoH integration metadata)**

Goal: specify where this tool’s outputs flow in EoH reasoning.

Inputs:

* tool\_type, primary\_task, domain, horizon  
* optional routing hints from Sentinel  
* EoH module map (which modules consume which kinds of signals)

Output fields:

* `routing.eoh_modules[]` (module IDs)  
* `routing.roles[]` (e.g., `flare_feature`, `diagnostic_vote`, `trajectory_feature`)  
* `routing.scenarios[]` (trigger contexts)  
* `routing.priority` (normalized ranking input for selection; policy-driven)

Constraint:

* Routing is metadata only; it does not execute selection.

#### **Stage 4 — Implementation Strategy (runtime plan)**

Goal: choose the safest executable representation.

Decision tree (deterministic policy):

* If explicit equation / points table / rules → `expression_eval` with internal DSL.  
* If model weights/code are available and supported → `python_model` wrapper.  
* If external API exists and allowed → `external_api` with validation \+ throttling.  
* If model is described but not reproducible:  
  * mark `unsupported` (default)  
  * optional `llm_surrogate` only if policy allows AND tool is non-decisive adjunct (future-facing, off by default)

Output:

* ToolImplementation runtime\_type \+ runtime\_config \+ safety gates.

#### **Stage 5 — Trust Scoring & Safe-Use Tagging**

Goal: determine how heavily the tool can influence decisions (metadata only).

Compute (policy-configurable, deterministic):

* validation strength (external \> internal \> none)  
* sample size  
* reported metrics presence/quality  
* population/setting fit  
* recency  
  Outputs:  
* `trust_score` (0–1)  
* `use_class` tags:  
  * `primary_eligible | adjunct_only | research_only`  
* `requires_human_review` flags based on tool\_type \+ risk class.

#### **Stage 6 — Versioning & Publishing**

Steps:

* Persist ToolDefinition \+ ToolImplementation under tool\_id/version.  
* Update Tool Library Index.  
* If replacing prior versions:  
  * mark previous versions as `deprecated` or `superseded`  
  * retain for audit replayability.  
* Emit `ToolPublished` event \+ audit artifacts.

---

### **Governance / Constraints**

* **Offline compiler only:** Tool Builder is not in the query hot path.  
* **No silent activation:** tools requiring review must not be published as active without approvals.  
* **Deterministic execution preference:** default policy prioritizes reproducible execution (DSL/code/API) over LLM surrogates.  
* **Traceability required:** every ToolDefinition/Implementation must be auditable back to Sentinel ToolCandidate \+ source doc IDs.  
* **Reversibility:** ability to deactivate/deprecate any tool version quickly (“kill switch”) via status controls.  
* **No invented metrics:** Builder must not fabricate AUROC/sensitivity/etc.; may compute internal trust score only from available fields \+ policy.

---

### **Dependencies**

* Upstream: **V6 M51 Sentinel** (ToolCandidate feed)  
* Data layer: ToolRegistry \+ Tool Library storage (versioned records \+ index)  
* MKE: canonical feature/ontology interface (for feature\_map and coding pointers)  
* Policy/Governance: approval workflows and thresholds (config, not hard-coded)

---

### **Audit Hooks**

Tool Builder must log at minimum, per tool version:

* `tool_id`, `version`, status transitions  
* source lineage: source\_doc\_id(s), DOI/URL pointers if available, sentinel\_tool\_id(s)  
* dedup/version decision \+ rationale pointer  
* structural validation results (pass/fail \+ reasons)  
* harmonization decisions:  
  * canonical input names  
  * unit conversions  
  * ontology bindings  
  * feature\_map paths  
  * missing handling  
* routing decisions:  
  * modules/roles/scenarios/priority  
* implementation choice:  
  * runtime\_type \+ config identifiers  
  * safety gates (rate limits, human review requirements)  
* trust score and safe-use tags \+ policy version used  
* publish/deprecate events, including “superseded by” links  
* reviewer approvals and timestamps (if required)

---

# **V6 M53 — Probabilistic Terrain Model (PTM)**

## **Purpose**

The Probabilistic Terrain Model (PTM) maintains a **time-evolving probability landscape** over multiple plausible conditions for a given patient, rather than forcing a single categorical diagnosis. It represents **partial expression, overlap, and uncertainty** across conditions and tracks how those probabilities **shift over time** in response to new data and interventions. PTM exists to support **early, non-pharmaceutical action** (e.g., lifestyle and monitoring strategies) before irreversible disease commitment or acute escalation is warranted.

**PTM computes and maintains the probability landscape when invoked; scheduling, cadence selection, and publish gating are owned by Module 54 (Terrain Conductor & Scheduler).**

PTM does **not** diagnose, prescribe, or mandate treatment; it contextualizes patient-specific terrain.

---

## **Scope**

### **In scope**

* Maintain a **multi-condition probability vector** (top-N hypotheses \+ residual/unknown).

* Track **probability deltas across time windows** (e.g., 7 / 14 / 30 / 90 days).

* Incorporate uncertainty explicitly (confidence bands / volatility signals).

* Reflect **mixed phenotypes / codominance** without collapsing to a single label.

* Evaluate **recommendation tier gates** (proactive → monitoring → escalation prompts) when invoked.

### **Out of scope**

* Assigning definitive diagnoses.

* Executing diagnostic or prognostic tools directly.

* Triggering or prescribing treatments.

* Overriding upstream module outputs or governance constraints.

* **Cadence selection, publish gating, and deep-pass orchestration (owned by Module 54).**

---

## **Inputs**

PTM consumes **signals**, not raw data.

* **Differential & multi-pathway outputs**

  * Ranked condition hypotheses and likelihood contributions.

* **Risk & trajectory signals**

  * Flare risk tiers, progression indicators, temporal trends.

* **Tool outputs (via Tool Library)**

  * Diagnostic scores, phenotypers, flare predictors (with trust / use-class metadata).

* **Temporal context**

  * Change rates, persistence, reversals, volatility.

* **Intervention metadata (read-only)**

  * What interventions were applied, when (lifestyle, monitoring changes).

* **UpdatePlan (from Module 54\)**

  * Invocation context specifying which horizons to compute and whether outputs are publishable.

* **NarrativeState (from MKE-EoHD, optional)**

  * Long-horizon narrative context used only to inform weighting and interpretation, not to override signals.

*All inputs must be tagged with source module, timestamp, and confidence.*

---

## **Outputs**

PTM emits **terrain representations**, not decisions.

* **Condition Probability Landscape**

  * `{ condition → probability }` with uncertainty bounds.

* **Trajectory Views**

  * Probability shifts over defined time horizons.

* **Codominance Indicators**

  * Flags when multiple conditions meaningfully co-exist.

* **Early-Warning Signals**

  * Rising probability trends or accelerating change.

* **Recommendation Tier Evaluations**

  * Proactive (lifestyle/monitoring), Watchful, Escalation-discussion.

* **Narrative-ready summaries**

  * Human-readable explanation of terrain and uncertainty (no directives).

---

## **Process / Logic (high-level)**

1. **Normalize inputs** into comparable likelihood contributions.

2. **Weight contributions** by trust, recency, relevance, and stability.

3. **Maintain concurrent hypotheses** (no forced collapse).

4. **Propagate probabilities forward** using observed deltas and volatility.

5. **Evaluate recommendation tiers** based on trend strength and confidence.

6. **Emit landscape and rationale**, preserving uncertainty.

---

## **Constraints / Governance**

* **No diagnosis claims:** PTM outputs probabilities, not labels.

* **No treatment mandates:** recommendations are tiered guidance only.

* **No single-signal dominance:** multiple inputs must corroborate shifts.

* **Auditability required:** every probability change must be traceable.

* **Degradation-safe:** if inputs are sparse or unstable, PTM widens uncertainty rather than guessing.

* **Invocation-bound:** PTM runs only when triggered via UpdatePlan from Module 54\.

---

## **Upstream Modules (feed PTM)**

* Multi-pathway / differential reasoning modules (e.g., MPA, Dx landscape).

* Risk & trajectory modules (flare risk, progression signals).

* Tool outputs (diagnostic scores, phenotypers) via Tool Library.

* Temporal state modules (baseline, trends).

* MKE-EoHD (NarrativeState, optional context).

## **Downstream Consumers (consume PTM)**

* Guidance & narrative modules

  * To frame early, non-pharmaceutical actions and monitoring.

* Monitoring & escalation logic

  * To decide *when* discussion of further workup is warranted.

* Clinician / patient-facing explanations

  * To communicate uncertainty and trajectory responsibly.

* Learning / evaluation modules

  * To assess how terrain evolution correlates with outcomes.

---

## **Versioning Note**

* **Introduced in V6** as a new EoH module.

* Does **not** alter V5.2 behavior.

* Internal math and weighting may evolve without changing the module contract.

---

### **One-sentence anchor**

**PTM (M53) represents patient-specific terrain as a probability landscape over time, enabling early, low-risk action without premature diagnosis or treatment lock-in.**

# **V6 M54 — Terrain Conductor & Update Scheduler (TCS)**

## **Purpose (3–5 sentences)**

Module 55 (TCS) is the EoH **orchestration and confidence-gating module** that decides **when** to (1) request long-horizon narrative passes from MKE-EoHD and (2) recompute and publish PTM (M53) terrain outputs. It converts incoming data/events into **scheduled update cycles** while preventing noisy over-updating. TCS ensures updates are triggered only when there is sufficient evidence density and stability to present a meaningful probabilistic snapshot. TCS does **not** compute probabilities itself and does **not** generate narratives; it only schedules, gates, and routes.

## **Scope**

### **In scope**

* Define and execute **update cadence policies**:

  * PTM refresh: **3–6 months** or **yearly**, based on data density and volatility.

  * EoHD deep-pass: **5–10 year windows** (optionally overlapping), triggered when warranted.

* Confidence gating: determine when there is “enough information” to publish an updated PTM snapshot.

* Trigger selection: time-based vs event-based triggers (new labs, new diagnoses, major episode changes, stability shifts).

* Prevent spam: rate-limit, debounce, and suppress updates when uncertainty is too high.

* Emit **UpdatePlan** objects: “what to run, when, and why.”

### **Out of scope**

* PTM probability math or hypothesis weighting (owned by M53).

* Longitudinal narrative extraction and story construction (owned by MKE-EoHD).

* Tool detection/compilation (Toolsmith stack).

* Any treatment decision logic.

## **Inputs**

* Patient data update events (from MKE patient layer): new labs, new encounters, new diagnoses, new symptoms, new medications.

* Stability/trajectory signals from EoH core modules (band/stack changes, drift flags, risk tier shifts).

* PTM state metadata (last update timestamp, uncertainty width, volatility).

* EoHD availability metadata (which historical windows exist, last deep-pass timestamp).

* Governance parameters (site/tenant policy): preferred cadence, min data threshold, “do not update more often than X.”

## **Outputs**

* **UpdatePlan** (per patient):

  * `run_ptm_update: yes/no`

  * `run_eohd_deeppass: yes/no`

  * `ptm_horizon_set: [7,14,30,90] (optional)`

  * `eohd_window: [start_year, end_year]`

  * `publish_to_patient: yes/no`

  * `publish_to_clinician: yes/no`

  * `reason_codes[]` (why triggered)

  * `confidence_gate_status`

* Audit events for: schedule decision, publish decision, defer decision.

## **Process / Logic (high-level)**

1. **Ingest triggers** (time \+ events).

2. **Assess evidence sufficiency** (data density, missingness, consistency, volatility).

3. **Apply gating policy**:

   * If insufficient evidence → defer (record why).

   * If high volatility/uncertainty widening → defer or clinician-only.

4. **Choose update type**:

   * PTM update cadence based on last update \+ evidence delta.

   * EoHD deep-pass triggered when long-horizon context is outdated or a major diagnostic inflection occurred.

5. **Emit UpdatePlan** and route:

   * PTM recompute request → M53

   * Narrative deep-pass request → MKE-EoHD

6. **Determine presentation** (patient vs clinician) based on confidence threshold and risk posture.

## **Constraints / Governance**

* Must never claim diagnostic certainty; gates are about publishability, not truth.

* Must not produce probabilities or narratives.

* Must be auditable: every “update/no update” is recorded with reasons.

* Must enforce hard rate limits per patient (policy-defined).

* Must allow tenant/site overrides for cadence and publish rules.

## **Dependencies**

* **Consumes:** M53 PTM state metadata; EoH stability/trajectory primitives; MKE patient event stream; MKE-EoHD job interface.

* **Produces:** UpdatePlan objects to M53 and MKE-EoHD; publish signals to UI/narrative layer.

## **Audit Hooks**

Log for each decision:

* timestamp, patient id, trigger type (time/event), last PTM update date, last EoHD deep-pass date

* evidence sufficiency summary (missingness %, volatility indicator, data delta)

* decision: run/defer \+ reason\_codes

* publish target: patient/clinician/both/none

* policy version used

