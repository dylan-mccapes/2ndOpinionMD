# **V6 M64 — Functional Utilization Discordance Detector (FUDD)**

**Serum Adequacy ≠ Effective Utilization: Detection, Classification, and Role-Differentiated Surfacing**

---

## **Purpose (3–5 sentences)**

Module 64 (FUDD) detects, classifies, and surfaces cases where a patient's serum/plasma levels of an analyte fall within reference ranges but effective utilization at the tissue, organ, or intracellular level is impaired. The system currently treats lab values at face value once they pass M7A quality checks; no existing module systematically asks whether "normal bloodstream levels" reflect actual functional adequacy. FUDD fills this gap by identifying **discordance patterns** — combinations of adequate serum markers plus clinical signals, downstream metabolite anomalies, or known blockade indicators that together suggest the body is not effectively absorbing, transporting, converting, or utilizing the analyte in question. FUDD generates **role-differentiated output payloads**: B2C (patient-facing) outputs surface intervention guidance directly; B2MD (clinician-facing) outputs surface the detection flag plus expandable mechanism context and candidate interventions as a togglable panel, with all intervention activation remaining under clinician authority. (New logic; V6 only.)

---

## **Foundational Concept: Functional Utilization Discordance (FUD)**

### **Definition**

**Functional Utilization Discordance (FUD)** is the state in which measured serum/plasma concentration of a bioactive substance (nutrient, hormone, neurotransmitter precursor, protein, or cofactor) falls within the laboratory reference range, while downstream functional indicators — clinical presentation, tissue-level metabolite assays, receptor-status markers, or organ-specific utilization tests — indicate that effective biological utilization is impaired.

### **Canonical Statement**

> **"You are not what you eat; you are what you absorb — and you are not what circulates in your bloodstream; you are what your organs effectively utilize."**

### **Why This Matters**

Standard blood panels measure **compartmental concentration** (what is present in the vascular compartment). They do not measure:

* **Transport efficiency** — whether the analyte is successfully crossing barriers (blood-brain barrier, intestinal epithelium, cell membranes, placental barrier) to reach target tissues.
* **Receptor availability** — whether the receptors required for cellular uptake are functional, unblocked, and unsaturated by competing ligands or autoantibodies.
* **Enzymatic conversion capacity** — whether the analyte can be converted to its biologically active form (e.g., folic acid → dihydrofolate → tetrahydrofolate → 5-MTHF; 25-OH-D → 1,25-dihydroxy-D).
* **Cofactor sufficiency** — whether the cofactors required for the analyte's biological activity are present (e.g., glutathione for folate transport backup pathways; vitamin D for folate receptor expression).
* **Competitive displacement** — whether synthetic analogs, structural mimics, or cross-reactive antibodies are occupying binding sites and preventing the biologically active form from functioning.

### **Discordance Mechanism Taxonomy**

FUDD classifies the root cause of each detected discordance into one or more of the following mechanism categories:

| Mechanism Class | Code | Description | Canonical Example |
|---|---|---|---|
| **Receptor Blockade** | `FUD-RB` | Autoantibodies or cross-reactive antibodies block the receptor required for analyte uptake by the target tissue. | Folate receptor autoantibodies (FRAs) blocking folate transport across the blood-brain barrier; ~75% prevalence in autism spectrum disorder. |
| **Competitive Displacement** | `FUD-CD` | A synthetic analog, structural mimic, or pharmacological agent binds the receptor/transporter with higher affinity than the biologically active form, preventing functional uptake. | Folic acid binding folate receptors ~3× more strongly than 5-MTHF; unmetabolized folic acid (UMFA) accumulation blocking receptors. |
| **Transport Impairment** | `FUD-TI` | The transport infrastructure (carrier proteins, channel proteins, active transport mechanisms, barrier-crossing pathways) is degraded, saturated, or cofactor-depleted. | Low vitamin D reducing backup folate transport pathway capacity; low glutathione degrading the tertiary folate transport route by 20–40%. |
| **Enzymatic Conversion Failure** | `FUD-EC` | The enzyme(s) required to convert the circulating form to the biologically active form are overwhelmed, polymorphically slow, or inhibited. | DHFR enzyme saturation at >200 µg folic acid, preventing conversion to tetrahydrofolate and impairing biopterin recycling (downstream: reduced dopamine, serotonin, nitric oxide synthesis). |
| **Cofactor Depletion** | `FUD-CF` | A required cofactor for the analyte's biological activity is itself deficient, rendering the primary analyte functionally inert despite adequate serum levels. | Adequate serum B12 but low intracellular glutathione preventing B12-dependent methylation; adequate iron but low copper impairing ceruloplasmin-mediated iron mobilization. |
| **Molecular Mimicry Trigger** | `FUD-MM` | A dietary or environmental antigen structurally mimics the receptor or the analyte, triggering immune cross-reactivity that degrades transport or utilization. | Dairy protein (casein) structural mimicry of the folate receptor alpha (FRα), triggering FRA production; 71–76% of children with ASD produce FRAs in response to dairy consumption. |
| **Compartmental Trapping** | `FUD-CT` | The analyte accumulates in the vascular compartment or an intermediate compartment because the efflux/uptake mechanism into the target compartment is impaired, producing artificially "normal" or elevated serum readings. | Normal or elevated serum folate with critically low cerebrospinal fluid folate (cerebral folate deficiency); normal serum iron with low bone marrow iron (functional iron deficiency). |
| **Gut-Barrier Dysfunction** | `FUD-GB` | The analyte is present in the bloodstream (via supplementation or fortification) but the gut epithelium is not effectively absorbing the dietary form, and/or gut inflammation is consuming the analyte before systemic distribution. | Celiac disease impairing folate and iron absorption despite supplementation; SIBO consuming B12 before host absorption. |

A single patient may exhibit **multiple simultaneous FUD mechanisms** for the same analyte (e.g., FUD-RB + FUD-CD + FUD-TI for folate, as described in the cerebral folate deficiency literature) or different mechanisms across different analytes.

---

## **Scope**

### **In scope**

* Detect discordance between serum/plasma adequacy and functional utilization indicators across all supported analyte classes.
* Classify detected discordances by mechanism (FUD-RB, FUD-CD, FUD-TI, FUD-EC, FUD-CF, FUD-MM, FUD-CT, FUD-GB) using pattern-matching against known discordance signatures referenced via MKE.
* Generate a **FUD Flag** (structured detection output) for each detected discordance, carrying the analyte, mechanism class(es), confidence level, evidence pointers, and known contributing factors.
* Produce **role-differentiated output payloads**:
  * **B2C payload**: patient-facing intervention guidance surfaced directly through M14/M24, framed as actionable recommendations.
  * **B2MD payload**: clinician-facing detection flag + expandable mechanism context panel + candidate intervention list as a togglable/selectable UI element, routed through M16/M19/M24. Interventions remain `status=proposal` and require clinician confirmation per existing M16/M19 governance.
* Attach known mechanism context via **MKE reference hooks** (pointers to evidence, not embedded knowledge).
* Consume validated lab data from M7A, clinical presentation signals from M4/M5/M12, stability/trajectory data from M6/M13, and tool outputs from the V6 Tool Library (M51–M53).
* Emit audit-grade records for every detection, non-detection, and surfacing decision.
* Support an **extensibility framework** for adding new analyte-discordance signatures over time without altering the module contract.

### **Out of scope**

* Diagnosing specific conditions (e.g., "this patient has cerebral folate deficiency"). FUDD detects and flags the discordance pattern; diagnostic confirmation remains with M49/clinician workflows.
* Executing interventions or activating treatment plans. FUDD surfaces candidates; M16/M19 govern activation.
* Embedding medical knowledge (disease facts, guideline text, drug interactions, reference ranges). All clinical knowledge is referenced via MKE hooks.
* Overriding M7A lab validation. If M7A marks a lab as valid and within range, FUDD does not dispute the lab value — it interrogates whether "within range" equals "functionally adequate."
* Replacing existing specialty testing logic. FUDD flags the need for functional assays (e.g., FRAT, CSF folate, methylmalonic acid, homocysteine); it does not interpret those specialty tests.

---

## **Inputs**

### **From M7A (validated lab data)**

* `validated_labs[]` — analyte, value, unit, reference_range, timestamp, source, QA_flags.
* `lab_adequacy_status` per analyte — `within_range | below_range | above_range`.

### **From M4/M5/M12 (clinical presentation and narrative)**

* `normalized_tags[]` — symptom tags with severity, duration, trajectory.
* `PSI` — Psychosomatic Index (to distinguish functional deficiency symptoms from psychosomatic overlay).
* `narrative_digest` — patient-reported symptoms, progression context.

### **From M6/M13 (stability and trajectory)**

* `stabilityBand`, `drift`, `trajectory_features` — to detect whether a patient's trajectory is inconsistent with their "adequate" lab picture.

### **From MKE (via reference hooks, not embedded)**

* `fud_signature_registry_ref` — pointer to the MKE-maintained registry of known FUD signatures (analyte × mechanism × indicator pattern).
* `fud_intervention_catalog_ref` — pointer to the MKE-maintained catalog of evidence-based interventions for each FUD mechanism class.
* `fud_contributing_factor_ref` — pointer to known contributing factors (e.g., folic acid exposure, dairy consumption, MTHFR polymorphisms, medication interactions).

### **From V6 Tool Library (M51–M53)**

* Tool outputs relevant to functional status (e.g., diagnostic scores, phenotypers) with trust/use-class metadata.

### **From M53 (PTM, when available)**

* `condition_probability_landscape` — to assess whether FUD detection aligns with or explains probabilistic terrain signals.

### **Configuration / Policy**

* `fud_detection_sensitivity` — policy-tunable sensitivity threshold (conservative/standard/aggressive).
* `role_context` — B2C vs B2MD, governing which output payload is generated.
* `patient_age` — relevant for age-gated detection logic (e.g., pediatric folate-specific patterns).
* `known_dietary_exposures[]` — if available from intake/journaling (dairy consumption, fortified food consumption, supplement list).

---

## **Outputs**

### **1) FUD Flag (core detection output)**

A structured flag per detected discordance. **Minimum required fields**:

* `fud_flag_id` (UUID)
* `patient_id`
* `analyte` (coded: LOINC where applicable)
* `serum_status` (`within_range` with value and reference range)
* `functional_status` (`suspected_impaired` | `confirmed_impaired` | `indeterminate`)
* `mechanism_classes[]` (one or more of: `FUD-RB`, `FUD-CD`, `FUD-TI`, `FUD-EC`, `FUD-CF`, `FUD-MM`, `FUD-CT`, `FUD-GB`)
* `confidence` (`low` | `moderate` | `high`) — based on how many indicator signals converge
* `evidence_pointers[]` (links to the specific labs, symptoms, narrative elements, and tool outputs that triggered the flag)
* `contributing_factors[]` (known factors present for this patient: e.g., `folic_acid_exposure`, `dairy_consumption`, `low_vitamin_D`, `low_glutathione`, `MTHFR_variant`, `medication_interaction`)
* `recommended_functional_assays[]` (tests that could confirm or rule out the discordance: e.g., `FRAT`, `CSF_folate`, `methylmalonic_acid`, `homocysteine`, `RBC_folate`, `intracellular_nutrient_panel`)
* `fud_detection_version` (module + signature registry version)
* `timestamp`

### **2) B2C Payload (patient-facing)**

Routed through M14 (patient-facing narratives) and M24 (interface hub).

* `patient_summary` — plain-language explanation of the discordance: what was found, why it matters, what can be done. No medical jargon. No diagnosis claims. Framed as actionable guidance.
* `intervention_recommendations[]` — each with:
  * `action` (e.g., "Eliminate folic acid from supplements and fortified foods", "Remove dairy for a minimum 8-week trial", "Request vitamin D testing — target 40–60 ng/mL", "Consider methylfolate or folinic acid supplementation")
  * `priority` (`immediate` | `short_term` | `monitoring`)
  * `rationale_plain` (one-sentence plain-language reason)
  * `evidence_strength` (`strong` | `moderate` | `emerging`)
* `monitoring_guidance` — what improvements to watch for and over what timeline.
* `escalation_prompt` — when to involve a practitioner (e.g., "If no improvement in 4–6 weeks, request the following tests from your provider: [list]").

### **3) B2MD Payload (clinician-facing)**

Routed through M16 (Execution Governance), M19 (clinician review), and M24 (interface hub).

* `clinician_flag` — concise clinical summary of the detected discordance, mechanism classification, and confidence level. Visible as a **persistent flag/badge** on the patient dashboard.
* `expandable_mechanism_panel` — togglable detail panel containing:
  * Mechanism classification with evidence strength per mechanism.
  * Specific contributing factors identified for this patient.
  * Relevant literature references (via MKE pointers, not embedded text).
  * Differential: what else could explain the pattern (non-FUD explanations).
* `intervention_candidates[]` — presented as a **selectable list** (not auto-selected), each with:
  * `intervention` (structured: dietary modification, supplementation change, functional assay order, referral)
  * `status` = `proposal` (per M16 governance; nothing activates without clinician confirmation)
  * `evidence_grade` (`strong` | `moderate` | `emerging` | `expert_opinion`)
  * `mechanism_targeted` (which FUD mechanism class this intervention addresses)
  * `expected_timeline` (when response would be expected if this is the correct mechanism)
  * `monitoring_parameters` (what to track to assess response)
* `nudge_flag` — a boolean + severity indicator that determines whether the flag appears as a passive annotation vs an active notification. Governed by:
  * `high` nudge: multiple converging signals, high confidence, known high-prevalence mechanism → active notification on clinician dashboard.
  * `moderate` nudge: partial signal convergence → visible flag, expandable on click.
  * `low` nudge: single weak signal → annotation in patient record, no active notification.

### **4) Audit artifacts**

* `FUDDetectionEvent` — for every detection cycle (including "no discordance found"), log: patient_id, analytes evaluated, signatures checked, flags generated or not, confidence levels, evidence pointers, role_context, payload type emitted, module + registry versions.
* `FUDSurfacingEvent` — for every surfacing action: which payload was generated, which role received it, which interventions were included, nudge level.
* `AuditEvent` + `Provenance` per FHIR conventions (referenced via Appendix C.11).

---

## **Process / Logic (deterministic stages)**

### **Stage 0 — Trigger Evaluation**

Determine whether a FUD detection cycle should run.

* **Triggers:**
  * New lab results ingested where `lab_adequacy_status = within_range` for a FUD-eligible analyte.
  * Clinical presentation signals (symptoms, trajectory drift, stability band changes) that pattern-match against known FUD presentation profiles.
  * PTM probability shifts toward conditions known to involve FUD mechanisms.
  * Periodic re-evaluation on schedule (policy-defined cadence).
  * Clinician or patient request for FUD evaluation.

* **Output:** `run_fud_cycle = true | false` with trigger_type and reason.

### **Stage 1 — Analyte-Level Discordance Screen**

For each FUD-eligible analyte with `lab_adequacy_status = within_range`:

1. **Retrieve the applicable FUD signature set** from `fud_signature_registry_ref` (MKE pointer) for this analyte.
2. **Evaluate each signature** against available patient data:
   * Does the patient exhibit clinical symptoms consistent with deficiency of this analyte despite adequate serum levels?
   * Are downstream metabolite markers available and abnormal? (e.g., elevated homocysteine with adequate serum B12/folate; elevated methylmalonic acid with adequate serum B12; low CSF folate with adequate serum folate.)
   * Are known contributing factors present? (e.g., folic acid exposure, dairy consumption, medication use, genetic variants, chronic infections, oxidative stress indicators.)
   * Are trajectory/stability signals inconsistent with the "adequate" lab picture? (e.g., deteriorating stability band despite "normal" labs.)
3. **Score discordance likelihood** per analyte:
   * Count converging indicator signals.
   * Weight by specificity of each signal (a downstream metabolite abnormality is more specific than a generic symptom).
   * Assign confidence: `high` (≥3 converging signals including at least one specific indicator), `moderate` (2 converging signals or 1 highly specific indicator), `low` (1 non-specific signal).
4. **Apply sensitivity policy**: filter by `fud_detection_sensitivity` threshold.

* **Output:** List of `candidate_discordances[]` with analyte, confidence, and evidence pointers.

### **Stage 2 — Mechanism Classification**

For each candidate discordance:

1. **Pattern-match against mechanism profiles** in the signature registry.
2. **Assign mechanism class(es)** (FUD-RB, FUD-CD, etc.) based on which contributing factors and indicator patterns are present.
3. **Identify contributing factors** specific to this patient.
4. **Determine recommended functional assays** that could confirm or refute the discordance.
5. **Flag multi-mechanism cases** where more than one mechanism class applies to the same analyte.

* **Output:** Classified `fud_flags[]` with full mechanism context.

### **Stage 3 — Intervention Candidate Assembly**

For each classified FUD flag:

1. **Retrieve intervention candidates** from `fud_intervention_catalog_ref` (MKE pointer) matched to the detected mechanism class(es).
2. **Filter by patient context**: age, known allergies/intolerances, current medications, dietary restrictions, existing care plan.
3. **Tier interventions** by:
   * `immediate` — dietary eliminations and supplement changes the patient can act on without a prescription (e.g., remove folic acid, eliminate dairy, switch to methylfolate).
   * `short_term` — functional assay orders and supplementation adjustments requiring clinician involvement (e.g., order FRAT, optimize vitamin D to 40–60, add folinic acid at low dose).
   * `monitoring` — follow-up testing and timeline-based re-evaluation (e.g., recheck homocysteine in 6–8 weeks, monitor language/mood/sleep improvements).
4. **Attach evidence grade** per intervention from MKE references.
5. **Compute expected response timeline** per intervention based on mechanism class.

* **Output:** Tiered `intervention_candidates[]` ready for role-differentiated packaging.

### **Stage 4 — Role-Differentiated Payload Generation**

Based on `role_context`:

**If B2C:**

1. Generate `patient_summary` using M14-compatible plain-language templates (vocabulary guardrails enforced via Appendix H.3/H.4).
2. Package `intervention_recommendations[]` with plain-language rationales.
3. Include `monitoring_guidance` and `escalation_prompt`.
4. Route payload to M14 and M24 for patient-facing delivery.

**If B2MD:**

1. Generate `clinician_flag` with concise clinical summary.
2. Assemble `expandable_mechanism_panel` with full mechanism classification, evidence, and differential context.
3. Package `intervention_candidates[]` with `status=proposal` per M16 governance.
4. Compute `nudge_flag` level based on confidence and signal convergence.
5. Route payload to M16, M19, and M24 for clinician-facing delivery.
   * M16 receives intervention candidates as draft proposals.
   * M19 receives the detection for clinician review queue.
   * M24 receives the UI payload including the expandable panel and nudge level.

**If both B2C and B2MD apply (same patient, both surfaces active):**

1. Generate both payloads.
2. Ensure **coherence**: the B2C payload must not recommend anything that contradicts or exceeds the B2MD payload. If the clinician has not yet reviewed the B2MD flag, the B2C payload limits itself to general guidance and dietary modifications that do not require clinician authorization.
3. Once the clinician reviews and selects interventions via the B2MD panel, the B2C payload can be updated to reflect clinician-approved actions.

### **Stage 5 — Audit Emission**

1. Emit `FUDDetectionEvent` for every detection cycle.
2. Emit `FUDSurfacingEvent` for every payload generated.
3. Emit `AuditEvent` + `Provenance` per Appendix C.11.
4. Version-pin: attach `fud_detection_version` (module version + signature registry version) to all outputs for reproducibility.

---

## **Constraints / Governance**

* **No diagnosis claims:** FUDD detects discordance patterns and surfaces them with mechanism hypotheses. It does not diagnose. Diagnostic confirmation remains with M49, specialty testing, and clinician judgment.
* **No autonomous intervention activation:** All intervention candidates are surfaced as `status=proposal`. In B2MD mode, nothing activates without explicit clinician confirmation via M19. In B2C mode, only dietary modifications and supplement changes that fall within the "patient-actionable without prescription" boundary are surfaced directly; prescription-level interventions are gated behind clinician involvement.
* **MKE boundary respected:** FUDD does not embed disease facts, reference ranges, guideline text, drug interactions, or clinical knowledge. All clinical content is referenced via MKE pointer hooks (`fud_signature_registry_ref`, `fud_intervention_catalog_ref`, `fud_contributing_factor_ref`). The module owns the detection logic, classification taxonomy, and routing — not the medical knowledge.
* **No override of M7A:** FUDD does not challenge or re-interpret lab values. If M7A says a lab is valid and within range, FUDD accepts that. FUDD's question is different: "Given that the lab IS within range, is the patient functionally utilizing this analyte?"
* **Extensibility without contract change:** New analytes, new FUD signatures, and new mechanism profiles are added to the MKE-maintained registries, not to the FUDD module itself. The module contract (inputs/outputs/process) remains stable as the knowledge base grows.
* **Coherence between B2C and B2MD:** When both surfaces are active for the same patient, the B2C payload must not recommend actions that exceed what the clinician has reviewed or that contradict the B2MD payload. Unreviewed B2MD flags result in the B2C payload limiting itself to general dietary guidance and monitoring suggestions.
* **Suppression-aware:** If `pauseFlag` is active for the patient, FUDD detection still runs (to maintain completeness) but surfacing is subject to existing suppression semantics. FUD flags are annotated, not deleted, during suppression.
* **Pediatric sensitivity:** For patients flagged as pediatric (age < 18), FUDD applies heightened sensitivity for analytes with known pediatric FUD prevalence (e.g., folate in neurodevelopmental conditions) and adjusts B2C language to be parent/caregiver-directed.
* **Auditability required:** Every detection cycle — including "no discordance found" — must produce an audit record. Every surfacing decision must be traceable to the detection that generated it.
* **No V5.2 modification:** FUDD is V6-only. It consumes V5.2 outputs but does not alter V5.2 module behavior.

---

## **Dependencies**

### **Upstream (feeds FUDD)**

* **M7A** — Validated lab data with adequacy status.
* **M4/M5** — Normalized symptom tags, PSI, persona flags.
* **M12** — Narrative digest, harmonized labs.
* **M6/M13** — Stability band, trajectory features, risk indices.
* **M53 (PTM)** — Condition probability landscape (when available).
* **V6 Tool Library (M51–M52)** — Relevant tool outputs with trust metadata.
* **MKE** — FUD signature registry, intervention catalog, contributing factor registry (via reference hooks).

### **Downstream (consumes FUDD)**

* **M14** — Receives B2C patient-facing payloads for narrative generation.
* **M16** — Receives B2MD intervention candidates as draft proposals.
* **M19** — Receives B2MD detection flags for clinician review queue.
* **M24** — Receives both B2C and B2MD UI payloads, including expandable mechanism panels and nudge levels.
* **M17 (CIR)** — FUD flags can serve as node/edge inputs for causal graph construction (e.g., "functional folate deficiency" as a causal node upstream of neurological symptoms).
* **M18 (MPA)** — FUD flags modulate pathway probabilities (a detected FUD pattern increases probability of FUD-associated pathways and decreases probability of "adequate nutrition" pathways).
* **M53 (PTM)** — FUD flags inform the probabilistic terrain (a confirmed FUD pattern shifts condition probabilities).
* **M41/M48** — Audit artifacts route to governance and continuous learning.
* **Vault (M21)** — FUD detection history persisted longitudinally for trend analysis and response tracking.

---

## **Analyte Coverage: Initial Release + Extensibility**

### **Tier 1 — Initial release (best-characterized FUD patterns)**

| Analyte | Primary FUD Mechanisms | Key Functional Indicators | Canonical Test(s) |
|---|---|---|---|
| **Folate** | FUD-RB, FUD-CD, FUD-TI, FUD-EC, FUD-MM, FUD-CT | Elevated homocysteine; low CSF folate; neurodevelopmental symptoms despite normal serum folate; folic acid exposure history; dairy consumption | FRAT (folate receptor autoantibody test); CSF folate; homocysteine; RBC folate |
| **Vitamin B12** | FUD-EC, FUD-CF, FUD-GB, FUD-CT | Elevated methylmalonic acid (MMA); elevated homocysteine; neurological symptoms despite normal serum B12 | MMA; homocysteine; holotranscobalamin (active B12) |
| **Iron** | FUD-TI, FUD-CF, FUD-CT, FUD-GB | Low reticulocyte hemoglobin; elevated soluble transferrin receptor; anemia symptoms despite normal ferritin | sTfR; reticulocyte hemoglobin; hepcidin; iron saturation |
| **Vitamin D** | FUD-EC, FUD-CF, FUD-TI | Adequate 25-OH-D but low 1,25-dihydroxy-D; elevated PTH despite adequate 25-OH-D; bone/immune symptoms | 1,25-dihydroxy-D; PTH; VDR polymorphism status |
| **Thyroid hormones** | FUD-EC, FUD-RB, FUD-CF | Normal TSH/T4 but low free T3; conversion impairment symptoms; selenium/iodine status | Free T3; reverse T3; thyroid antibodies; selenium |

### **Tier 2 — Near-term extension**

* Magnesium (serum vs RBC magnesium)
* Zinc (serum vs functional zinc status)
* Vitamin B6 (serum vs PLP; interaction with hormonal contraceptives)
* Omega-3 fatty acids (serum vs RBC membrane composition)
* Glutathione (serum vs intracellular)

### **Tier 3 — Framework-ready (future)**

* Neurotransmitter precursors (tryptophan→serotonin, tyrosine→dopamine pathways)
* Hormones (cortisol: serum vs salivary free cortisol; testosterone: total vs free)
* Proteins (albumin: serum vs nutritional status indicators)
* Any new analyte added to the MKE FUD signature registry

**Extensibility contract:** Adding a new analyte requires only: (1) a new FUD signature entry in the MKE registry, (2) mapping of functional indicators to available lab/clinical data streams, and (3) intervention catalog entries. No change to M64 module logic or contract.

---

## **Interaction with Cerebral Folate Deficiency (Reference Case)**

The transcript that motivated this module describes the most extensively documented FUD pattern in the literature. FUDD would process this case as follows:

1. **Stage 1 detection:** Child with ASD. Serum folate = within range. Clinical signals = neurodevelopmental delay, language regression, behavioral symptoms, sleep disturbance. Downstream indicator = elevated homocysteine. Contributing factors = dairy consumption, folic acid exposure (fortified formula, supplements). → `candidate_discordance` for folate at `high` confidence.

2. **Stage 2 classification:** FUD-RB (folate receptor autoantibodies from dairy cross-reactivity) + FUD-CD (folic acid competitive displacement at receptors) + FUD-TI (low vitamin D reducing backup transport; low glutathione degrading tertiary pathway) + FUD-EC (DHFR saturation from folic acid, impairing biopterin recycling) + FUD-MM (dairy protein molecular mimicry triggering FRA production). Multi-mechanism classification.

3. **Stage 3 interventions:**
   * `immediate`: Eliminate all dairy. Eliminate all folic acid (supplements + fortified foods). Switch to methylfolate or folinic acid.
   * `short_term`: Test vitamin D (target 40–60 ng/mL). Test homocysteine (target 6–7 µmol/L). Order FRAT. Support glutathione gently (s-acetyl glutathione lozenge or dietary sources). Consider low-dose folinic acid (200–800 µg, not high-dose leucovorin).
   * `monitoring`: Track language, mood, sleep, behavior improvements over 4–8 weeks. Recheck homocysteine at 6–8 weeks. Recheck vitamin D at 8–12 weeks.

4. **Stage 4 routing:**
   * **B2C** (parent/caregiver): "Your child's folate blood levels appear normal, but there are signs their brain may not be able to use it effectively. This is a recognized pattern. Here are steps you can take now: [dietary changes]. Here are tests to discuss with your provider: [FRAT, vitamin D, homocysteine]."
   * **B2MD**: Flag on dashboard with `nudge=high`. Expandable panel showing multi-mechanism classification, evidence, and differential. Intervention list as selectable proposals. Clinician selects, confirms, or dismisses.

---

## **Versioning Note**

* **Introduced in V6** as a new EoH module.
* Does **not** alter V5.2 behavior.
* FUD signature registry and intervention catalog versions are maintained independently in MKE; FUDD module logic is versioned separately.
* Internal detection logic and confidence scoring may evolve without changing the module contract.

---

## **Audit Hooks**

FUDD must log at minimum:

* **Per detection cycle:** patient_id, timestamp, trigger_type, analytes evaluated, signature_registry_version, detection_sensitivity_policy, role_context, FUD flags generated (or explicit "none"), module_version.
* **Per FUD flag:** fud_flag_id, analyte, serum_value + range, mechanism_classes, confidence, evidence_pointers (specific lab IDs, symptom tag IDs, narrative excerpts, tool output IDs), contributing_factors, recommended_assays.
* **Per surfacing event:** fud_flag_id, payload_type (B2C/B2MD), interventions included, nudge_level (B2MD only), delivery_target_module, timestamp.
* **Per intervention candidate:** intervention_id, mechanism_targeted, evidence_grade, status (proposal/accepted/dismissed), clinician_actor_id (if B2MD and reviewed), timestamp.
* **Provenance chain:** upstream module versions consumed (M7A, M4/M5, M6/M13, M53, Tool Library versions), MKE registry versions, and policy versions — sufficient to reproduce the same detection given identical inputs.

---

### **One-sentence anchor**

**FUDD (M64) detects when "normal labs" mask impaired tissue-level utilization, classifies the mechanism, and surfaces role-appropriate interventions — because serum adequacy is not functional adequacy.**
