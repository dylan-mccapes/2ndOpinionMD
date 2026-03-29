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
