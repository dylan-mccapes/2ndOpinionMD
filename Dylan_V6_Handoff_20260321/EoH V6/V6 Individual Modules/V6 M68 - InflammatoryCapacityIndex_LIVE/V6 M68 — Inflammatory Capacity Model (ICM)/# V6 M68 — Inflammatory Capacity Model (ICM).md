# **V6 M68 — Inflammatory Capacity Model (ICM)**  
  
**Real-Time Allostatic Headroom Estimation with Three-Valve Dynamics for Proactive Flare Prevention**  
  
**Version:** 1.0 — Initial specification. Establishes the three-valve capacity architecture (inflow, displacement, outflow), the Inflammatory Capacity Index (ICI), threshold-triggered wellness activation, stressor identification and tagging, and integration contracts with M3, M5, M13, M64, M66, and M21.  
  
-----  
  
## **Purpose (3–5 sentences)**  
  
Module 68 (ICM) computes a real-time estimate of how much **inflammatory and allostatic headroom** a patient has remaining before a clinical event — flare, reaction, symptom cascade, or decompensation — becomes probable. No existing EoH module models the patient’s **remaining capacity** as a unified dynamic system; M3 tracks instability (how unstable you are *now*), M13 projects trajectories (where instability is *heading*), and M66 offers wellness interventions, but no module answers the question: **“How close am I to overflowing, and which specific factors are filling me up fastest?”** ICM fills this gap by formalizing three independently modifiable dynamics — inflow rate (environmental and psychosocial stressor exposure), displacement volume (chronic stressors as space-occupying burden reducers), and outflow rate (recovery and excretion capacity) — into a single **Inflammatory Capacity Index (ICI)** that expresses remaining headroom as a percentage. When ICI drops below governed thresholds, ICM triggers proactive patient engagement via M11/M24 and activates wellness action recommendations from M66. (New logic; V6 only.)  
  
-----  
  
## **Foundational Concept: Inflammatory Capacity as Three-Valve Fluid Dynamics**  
  
### **Definition**  
  
**Inflammatory Capacity** is the patient’s remaining tolerance for additional allostatic burden before cumulative load exceeds the system’s ability to maintain functional homeostasis, resulting in a clinically observable event (flare, reaction, symptom escalation, or decompensation). ICM models this as a **bounded vessel** (the patient) with three independently measurable and modifiable dynamics:  
  
1. **Inflow** — the rate at which environmental, psychosocial, immunological, dietary, and behavioral stressors are adding inflammatory burden. Inflow is partially volitional: boundaries, mindfulness practices, environmental control, and behavioral choices modulate how much of the world’s stressor load the patient absorbs.  
1. **Displacement** — chronic stressors that occupy persistent volume within the vessel, reducing the available capacity for transient inflow. Disease states, unresolved psychosocial burdens (relationships, work, caregiving), chronic pain, untreated mental health conditions, and persistent environmental exposures act as “bricks in the bucket” — they do not flow through; they sit and take up space. Displacement factors can expand (depression worsening, new diagnosis) or contract (effective therapy, cognitive reframing, resolution of a stressor).  
1. **Outflow** — the rate at which the patient’s regulatory systems clear inflammatory burden: sleep quality and duration, anti-inflammatory dietary patterns, physical activity, stress-recovery practices (meditation, breathwork, social connection), pharmacological support (mast cell stabilizers, anti-inflammatories), and general physiological resilience. Outflow is the “spout on the bucket” — how fast the body can process and excrete what flows in.  
  
**Overflow** occurs when inflow rate + displacement volume exceeds outflow rate + total vessel capacity for a sufficient duration. Overflow is the computational proxy for clinical events: flares, allergic/histaminergic reactions, autoimmune symptom cascades, mood decompensation, or somatic symptom amplification.  
  
### **Clinical Precedent**  
  
This architecture formalizes and unifies concepts that exist independently across multiple clinical domains:  
  
- **Allostatic load theory** (McEwen & Stellar, 1993) — the cumulative “wear and tear” of chronic stress on physiological systems, with allostatic overload as the tipping point. ICM operationalizes allostatic load as a real-time, prospective computation rather than a retrospective biomarker index.  
- **Mast cell activation threshold models** — the clinical observation that mast cell degranulation occurs not from a single trigger but from cumulative trigger burden exceeding a patient-specific activation threshold. The MCAS literature describes patients who tolerate individual triggers (alcohol, metals, stress) in isolation but react when triggers co-occur — a classic overflow pattern.  
- **Psychoneuroimmunology** — the bidirectional relationship between psychological state and immune function, where emotional stressors produce measurable inflammatory cytokine changes (IL-6, TNF-α, CRP elevation) and where inflammatory states produce psychological symptoms (sickness behavior, depression, cognitive fog).  
- **Stress-vulnerability models in psychiatry** — the diathesis-stress framework in which pre-existing vulnerabilities (displacement) lower the threshold for symptom expression under environmental stressor load (inflow).  
- **Contemplative and somatic regulation traditions** — mindfulness, breathwork, and somatic practices that demonstrably modulate HPA axis activity, vagal tone, and inflammatory cytokine profiles. These map directly to outflow enhancement and inflow modulation within ICM.  
  
### **What Is Novel**  
  
No existing clinical framework or CDS system computes these three dynamics as a **unified, real-time capacity model** with:  
  
- A single continuous index (ICI) expressing remaining headroom  
- Per-factor attribution (which specific stressors contribute most to capacity loss)  
- Prospective overflow forecasting (“at current rates, overflow in ~N days”)  
- Direct linkage to actionable interventions targeting the specific valve (inflow, displacement, or outflow) most amenable to modification  
  
### **Canonical Statement**  
  
> **“You are a vessel with a finite capacity for burden. How much flows in, how much sits inside, and how much flows out are three levers you can learn to adjust — and the system’s job is to show you which lever matters most right now.”**  
  
-----  
  
## **Scope**  
  
### **In scope**  
  
- Computation of the Inflammatory Capacity Index (ICI) as a continuous value (0–100%) representing remaining headroom before probable overflow.  
- Three-valve decomposition: independent tracking of inflow rate, displacement volume, and outflow rate with per-factor attribution.  
- Stressor identification and tagging: classification of individual stressors by valve type (inflow vs. displacement), magnitude, modifiability, and trajectory.  
- Threshold-triggered patient engagement: when ICI crosses governed thresholds (e.g., 65%, 50%, 35%), emit engagement signals to M11 (patient guidance) and M24 (UI) with valve-specific recommendations.  
- M66 activation bridge: when ICI enters the proactive engagement zone, generate a structured prompt to M66 (Exploratory Wellness Actions) specifying which valve domain needs intervention and the patient’s current stressor attribution profile.  
- Overflow forecasting: given current inflow, displacement, and outflow trajectories, estimate time-to-overflow under “no change” and “best achievable intervention” scenarios.  
- Stressor discovery via patient narrative: consume M4/M5 outputs (tags, PSI, persona flags) to identify stressors the patient may not have explicitly labeled — the “two-year-old you didn’t realize was your biggest stressor” pattern.  
- Vault integration: persist ICI time-series, stressor attributions, overflow events, and intervention-response correlations to M21 for longitudinal pattern detection.  
- Wellness action lifecycle tracking: distinguish between exploratory wellness actions (M66 domain; unvalidated, patient-specific experiments) and **Validated Wellness Actions (VWA)** — actions that have demonstrated measurable positive effect on ICI for this specific patient and are promoted from exploratory to established protocol.  
  
### **Out of scope**  
  
- Clinical diagnosis — ICM does not diagnose allostatic overload, MCAS, autoimmune flares, or any specific condition. It computes capacity and attributes stressors.  
- Treatment recommendation — ICM does not prescribe medications, supplements, or therapies. Pharmacological interventions that affect capacity (e.g., mast cell stabilizers) are tracked as outflow modifiers but not recommended by this module.  
- Suppression policy — ICM does not define or execute suppression rules (owned by M8/M9). ICM may emit data that suppression modules consume (e.g., “this band elevation may be capacity-driven, not disease-driven”) but does not suppress signals directly.  
- Wellness action content — the specific wellness action catalog, domain taxonomy, and pharmacist-lens evaluation belong to M66 (EWA). ICM triggers M66 and provides context; M66 owns the intervention library.  
- MKE knowledge curation — ICM does not curate or store medical knowledge about inflammatory pathways, cytokine cascades, or allostatic biomarkers. ICM consumes structured signals from upstream modules.  
- Band/Stack computation — ICM does not recompute Stability Band or Stack Level (owned by M3). ICM consumes these as inputs and contributes a complementary “remaining headroom” dimension.  
- Consent, privacy, or data minimization enforcement (owned by M26, M27, M34–M37).  
  
### **Relationship to V5.2**  
  
ICM is a **V6-only module** that does not modify any V5.2 logic. It consumes V5.2 module outputs as read-only inputs (M3 Band/Stack, M5 PSI/persona flags, M13 trajectory vectors, M21 vault history) and produces capacity artifacts (ICI values, stressor attributions, overflow forecasts, M66 activation prompts) that downstream modules may consume. ICM provides an integration contract for V5.2 modules that opt in to capacity-aware behavior (e.g., M6 escalation routing may optionally factor ICI into tier determination; M14 action engine may optionally include capacity context in intervention timing).  
  
-----  
  
## **Placement in the EoH Stack**  
  
```  
┌─────────────────────────────────────────────────────────┐  
│                    Patient-Facing Layer                  │  
│              M24 (UI) / M11 (Patient Guidance)          │  
│         ↑ ICI visualization, valve guidance,            │  
│           threshold alerts, VWA recommendations          │  
├─────────────────────────────────────────────────────────┤  
│                  ┌──────────────┐                        │  
│                  │   M68 (ICM)  │  ← THIS MODULE        │  
│                  │  ICI Engine  │                        │  
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
├─────────────────────────────────────────────────────────┤  
│                    Input Layer                           │  
│  M3 (Band/Stack) │ M5 (PSI) │ M13 (Trajectory)        │  
│  M4 (Tags)       │ M64 (FUDD) │ M12 (Narrative)       │  
│  Wearables/PROs  │ Journal entries │ Lab events         │  
└─────────────────────────────────────────────────────────┘  
```  
  
ICM sits **above** the state-computation and trajectory layers and **below** the patient-facing layer. It is a **synthesis module** that transforms multi-modal upstream signals into a single capacity representation with attribution, then routes that representation to patient engagement and wellness action systems.  
  
-----  
  
## **Foundational Invariants**  
  
### **I-A: Capacity Is Not Instability**  
  
ICI and Stability Band are **complementary, non-redundant** measures. A patient can have a low Stability Band (currently stable) with low ICI (nearly full — one stressor away from overflow). Conversely, a patient can have an elevated Band (currently unstable) with high ICI (plenty of headroom, the instability is from a single acute cause that is resolving). ICM MUST NOT be used as a proxy for Band, and Band MUST NOT be used as a proxy for ICI.  
  
**Test:** Construct a patient scenario where Band = 1 (stable) and ICI = 30% (near overflow). Verify that M3 and M68 produce independent, non-contradictory outputs and that downstream modules treat them as separate dimensions.  
  
### **I-B: Three-Valve Independence**  
  
The three valves (inflow, displacement, outflow) are **independently modifiable** and **independently attributable**. An intervention that reduces inflow does not automatically increase outflow. A displacement reduction does not automatically reduce inflow. Each valve has its own set of contributing factors, its own trajectory, and its own intervention surface.  
  
**Test:** Apply a simulated intervention that reduces inflow by 20% (e.g., patient sets a boundary with a stressor). Verify that displacement and outflow values remain unchanged and that ICI improvement is attributed solely to inflow reduction.  
  
### **I-C: Overflow Is Probabilistic, Not Deterministic**  
  
ICM produces **probability of overflow within a time horizon**, not a binary “will overflow / won’t overflow” prediction. Overflow probability increases as ICI decreases, but the mapping is non-linear and patient-specific (calibrated from M21 vault history of prior overflow events for this patient).  
  
**Test:** Given identical ICI values for two patients with different overflow histories, verify that their overflow probabilities differ and that the difference is traceable to vault-derived calibration parameters.  
  
### **I-D: Stressor Attribution Is Auditable**  
  
Every ICI computation MUST produce a **stressor attribution vector** identifying the top contributors to capacity loss, classified by valve type (inflow/displacement), magnitude, modifiability (high/medium/low/none), and data source (journal, PRO, lab, wearable, M5 inference). No “black box” ICI values.  
  
**Test:** Given an ICI of 45%, extract the attribution vector and verify that the sum of attributed contributions accounts for ≥90% of capacity loss, that each attribution carries a data source provenance chain, and that modifiability classifications are present.  
  
### **I-E: No Diagnosis by Capacity**  
  
ICM MUST NOT assert that a low ICI *causes* a specific clinical event, *constitutes* a diagnosis, or *confirms* a disease state. ICM provides a **risk context** (“this patient’s remaining capacity is low; clinical events are more probable”) — not a causal or diagnostic claim.  
  
**Test:** Verify that no ICM output contains diagnostic language (ICD codes, disease names as conclusions, or causal assertions). Verify that clinician-facing outputs use language like “capacity context suggests elevated risk” rather than “patient has allostatic overload.”  
  
### **I-F: Validated Wellness Action Promotion Gate**  
  
An Exploratory Wellness Action (M66 domain) is promoted to a **Validated Wellness Action (VWA)** for a specific patient ONLY when:  
  
1. The action has been attempted ≥3 times by the patient with logged adherence.  
1. ICI improvement is measurably correlated with the action across ≥2 of those attempts (controlled for confounders via M21 longitudinal data).  
1. The patient has not reported adverse effects from the action.  
1. A clinician has not flagged the action as contraindicated for this patient.  
  
Promotion is **patient-specific** — an action validated for Patient A is not automatically validated for Patient B.  
  
**Test:** Simulate a patient who tries a breathing practice 4 times. In 3 of 4 attempts, ICI improves by ≥5% within 24 hours with no confounding stressor changes. Verify that the action is promoted to VWA status. Then simulate a second patient with the same practice showing no ICI correlation — verify that VWA promotion does not occur.  
  
-----  
  
## **The Three-Valve Model: Detailed Architecture**  
  
### **Valve 1 — Inflow (Environmental & Psychosocial Stressor Rate)**  
  
Inflow represents the rate at which new inflammatory burden enters the patient’s system. Inflow sources include:  
  
**Environmental:** allergen exposure, weather/barometric changes, pollution, mold, chemical exposure, circadian disruption (blue light, irregular schedule), noise, temperature extremes.  
  
**Psychosocial:** interpersonal conflict, work stress, caregiving burden, financial stress, social media consumption, news/media exposure, social isolation, grief, existential/identity stress.  
  
**Immunological/Physiological:** acute infections, menstrual cycle phase (estrogen-mediated mast cell sensitization), post-exertional malaise, drug/supplement interactions (M64/M66 domain), alcohol or substance use, dietary inflammatory load (processed foods, high-histamine foods, known trigger foods).  
  
**Behavioral/Volitional:** inflow is **partially controllable** through boundary-setting, environmental modification, dietary choices, media consumption habits, and social engagement patterns. The “faucet” metaphor: you cannot turn it off entirely (life is inherently inflammatory), but you can modulate the flow rate.  
  
**Inflow Modulation Practices (mapped to intervention surface):**  
  
- Boundary-setting (interpersonal, professional, digital)  
- Environmental control (allergen avoidance, air quality, light hygiene)  
- Dietary choices (anti-inflammatory diet, trigger avoidance, histamine management)  
- Mindful engagement practices — including contemplative traditions that specifically address non-attachment to emotional stressors. The principle of *vairāgya* (dispassion/non-attachment) in yogic philosophy, *aparigraha* (non-grasping), and the chakra-based emotional processing frameworks describe a systematic practice of observing stressors without absorbing their full inflammatory weight. In practical terms: recognizing that the two-year-old’s tantrum does not require a full cortisol cascade — the stressor is real, but the magnitude of your physiological response to it is negotiable.  
  
### **Valve 2 — Displacement (Chronic Burden as Space-Occupying Stressors)**  
  
Displacement represents persistent stressors that occupy baseline capacity, reducing the volume available for transient inflow before overflow occurs. Displacement factors are characteristically:  
  
- **Slow-moving:** they change over weeks to months, not hours.  
- **High-inertia:** they resist quick intervention (you cannot resolve a chronic disease, a difficult family relationship, or a housing situation in a day).  
- **Variable-magnitude:** they can expand (depression worsening, new comorbidity, job loss) or contract (successful therapy, relationship resolution, medication stabilization) over time.  
  
**Displacement Sources:**  
  
- Active disease states (autoimmune conditions, chronic pain, metabolic disorders, mental health conditions)  
- Persistent psychosocial burdens (difficult relationships, caregiving for a chronically ill family member, financial insecurity, housing instability)  
- Unresolved trauma (PTSD, ACEs — these occupy persistent capacity even when not actively symptomatic)  
- Environmental persistence (living in a moldy home, chronic occupational exposure, unavoidable allergen environment)  
  
**Displacement Modulation Practices:**  
  
- Cognitive behavioral practices that reframe the subjective magnitude of a stressor (“shrinking the brick”) — the stressor remains present, but its capacity-occupying footprint contracts.  
- Contemplative traditions that address the *size* of emotional objects in awareness: the yogic concept of *aṇimā* (making oneself — or one’s attachment — infinitely small) and *mahimā* (expanding one’s perspective to make stressors proportionally smaller). These are historically described as *siddhis* (attainments) in the Yoga Sutras of Patanjali and are practically applied as perspective-scaling exercises in modern mindfulness-based interventions.  
- Therapeutic intervention (psychotherapy, medication optimization, disease management)  
- Life circumstance changes (where achievable)  
  
### **Valve 3 — Outflow (Recovery & Excretion Capacity)**  
  
Outflow represents the rate at which the patient’s regulatory systems clear inflammatory and allostatic burden. Outflow is the body’s natural capacity for self-regulation — and it is highly modifiable.  
  
**Outflow Determinants:**  
  
- **Sleep:** quality, duration, consistency, architecture (deep sleep proportion). Sleep is the single highest-leverage outflow factor — a full histamine reset, cortisol recalibration, and inflammatory cytokine clearance cycle.  
- **Physical activity:** anti-inflammatory myokine release, lymphatic drainage, vagal tone enhancement. Must be calibrated to avoid post-exertional malaise (which converts exercise from outflow to inflow).  
- **Nutrition:** anti-inflammatory dietary patterns, adequate hydration, gut microbiome support, avoidance of individual trigger foods.  
- **Stress-recovery practices:** meditation, breathwork (specifically practices that enhance vagal tone — slow exhalation, box breathing, *prāṇāyāma*), progressive muscle relaxation, nature exposure, social connection, creative expression.  
- **Pharmacological support:** mast cell stabilizers, antihistamines, anti-inflammatory medications, targeted supplementation (where M66/clinician-directed).  
- **Physiological resilience factors:** baseline HPA axis function, vagal tone, gut barrier integrity, hepatic detoxification capacity, renal clearance.  
  
**Outflow Enhancement Practices:**  
  
- Sleep hygiene optimization (circadian alignment, temperature, light, consistency)  
- Calibrated physical activity (below post-exertional malaise threshold)  
- Breathwork and vagal tone practices (*prāṇāyāma*, physiological sigh, cold exposure where tolerated)  
- Anti-inflammatory nutrition  
- Contemplative practices that directly modulate the parasympathetic nervous system — the yogic concept of *laghimā* (lightness) describes the experiential quality of successful outflow: the subjective felt sense of burden leaving the body. Modern breathwork and meditation research confirms measurable reductions in salivary cortisol, CRP, and IL-6 following sustained practice.  
  
-----  
  
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
  magnitude:            float (0.0–1.0; normalized contribution to capacity loss)  
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
  trajectory:           enum { IMPROVING | STABLE | DECLINING | UNKNOWN }  
  data_sources:         enum[] { WEARABLE | JOURNAL | PRO | LAB | M66_LOG }  
  last_updated:         timestamp  
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
  inflow_rate:          float (normalized; 0.0–1.0)  
  displacement_volume:  float (normalized; 0.0–1.0)  
  outflow_rate:         float (normalized; 0.0–1.0)  
  overflow_probability: float (0.0–1.0; within governed time horizon)  
  time_to_overflow:     duration | null (estimated under "no change" scenario)  
  top_stressors:        Stressor[] (top 5 by magnitude, descending)  
  top_outflow_deficits: OutflowFactor[] (bottom 3 by current_level, ascending)  
  attribution_vector:   Map<stressor_id, float> (% contribution to capacity loss)  
  vault_ref:            Reference (M21 ledger entry)  
  module_version:       string  
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
  priority_valve:       enum { INFLOW | DISPLACEMENT | OUTFLOW }  
  valve_context: {  
    inflow: {  
      top_modifiable_stressors: Stressor[] (filtered to modifiability ≥ MEDIUM)  
      suggested_domains:        string[] (e.g., ["boundary-setting", "dietary"])  
    }  
    displacement: {  
      expanding_stressors:      Stressor[] (trajectory = EXPANDING)  
      suggested_domains:        string[] (e.g., ["cognitive reframing",  
                                                  "therapeutic support"])  
    }  
    outflow: {  
      deficit_factors:          OutflowFactor[] (current_level < 0.4)  
      suggested_domains:        string[] (e.g., ["sleep hygiene", "breathwork"])  
    }  
  }  
  patient_vwa_list:     VWA[] (this patient's Validated Wellness Actions,  
                               ordered by historical ICI impact)  
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
  
-----  
  
## **Process / Logic (Deterministic, Stepwise)**  
  
### **Stage 1 — Input Ingestion & Stressor Census**  
  
1. **Consume upstream signals:**  
- M3: current `stabilityBand`, `stackLevel`, `pauseFlag`, `pauseReason`  
- M5: current `PSI`, `persona_flags[]`, symbolic/psychosocial tags  
- M13: `flare_risk_slopes`, `inflammatory_burden_composite`, trajectory vectors  
- M64: active `fud_flags[]` (functional utilization discordances as displacement stressors)  
- M4: `normalizedTags[]` (symptom tags, lifestyle tags, psychosocial tags)  
- M12: narrative digest (for stressor extraction via NLP)  
- M21: patient’s historical ICI time-series, prior overflow events, VWA records  
- Wearable data: sleep metrics, HRV (vagal tone proxy), activity levels  
- PRO inputs: patient-reported stress, mood, energy, symptom severity  
- Lab events: inflammatory markers (CRP, IL-6, ESR), cortisol, tryptase (where available)  
1. **Build stressor census:** From ingested signals, enumerate all active stressors. Classify each as INFLOW or DISPLACEMENT based on temporal persistence (stressors present for >14 days default to DISPLACEMENT; <14 days default to INFLOW; clinician or patient may override).  
1. **Assign magnitude scores:** For each stressor, compute magnitude using a weighted combination of: (a) direct measurement where available (lab values, wearable metrics), (b) patient self-report intensity, (c) M5 inferred intensity (for stressors the patient may not have explicitly reported), (d) historical impact calibration from M21 vault (if this stressor has been seen before in this patient, use prior ICI impact data).  
1. **Assign modifiability classifications:** For each stressor, classify modifiability as HIGH (patient can meaningfully reduce within 1–7 days via behavioral/environmental change), MEDIUM (reducible over weeks with sustained effort or therapeutic support), LOW (reducible only with significant life changes or long-term treatment), or NONE (disease state, immutable circumstance). Modifiability is a governance-level classification informed by M66 action catalog, not a clinical judgment by ICM.  
  
### **Stage 2 — Three-Valve Computation**  
  
1. **Compute inflow rate:** Aggregate all INFLOW stressor magnitudes using weighted additive aggregation. Apply recency weighting (stressors reported in last 24h weighted higher than those from 3 days ago). Normalize to 0.0–1.0.  
1. **Compute displacement volume:** Aggregate all DISPLACEMENT stressor magnitudes. Apply trajectory adjustment: EXPANDING stressors receive a +10% magnitude boost (anticipatory); CONTRACTING stressors receive a -10% magnitude reduction. Normalize to 0.0–1.0.  
1. **Compute outflow rate:** Aggregate all OutflowFactor current levels. Weight by factor class importance (governed; default weights: sleep 0.30, activity 0.15, nutrition 0.15, practice 0.15, pharmacological 0.10, physiological 0.10, social 0.05). Normalize to 0.0–1.0.  
1. **Compute ICI:**  
  
```  
effective_burden = (inflow_rate × inflow_weight) + (displacement_volume × displacement_weight)  
effective_recovery = outflow_rate × outflow_weight  
ici_raw = 1.0 - (effective_burden - effective_recovery)  
ici_value = clamp(ici_raw × 100, 0.0, 100.0)  
```  
  
Where `inflow_weight`, `displacement_weight`, and `outflow_weight` are patient-specific calibration parameters initialized from population defaults and refined via M21 longitudinal data. The calibration loop adjusts weights when predicted overflow events are confirmed or disconfirmed by actual clinical events.  
  
1. **Assign ICI band:** Map `ici_value` to band per governed thresholds:  
- **GREEN** (>65%): adequate headroom; maintenance mode  
- **YELLOW** (50–65%): reduced headroom; proactive engagement zone  
- **ORANGE** (35–50%): low headroom; active intervention recommended  
- **RED** (<35%): critical; overflow probable without immediate intervention  
1. **Compute overflow probability:** Using the patient’s M21-calibrated overflow function, estimate `P(overflow | current ICI, current trajectories, time_horizon)`. Time horizon is governed (default: 72 hours).  
1. **Compute time-to-overflow:** Under “no change” scenario (all current rates persist), estimate when ICI would cross 0%. If trajectories suggest ICI is rising (recovering), time-to-overflow = null. If trajectories suggest ICI is falling but slowly, time-to-overflow may exceed the governed horizon.  
  
### **Stage 3 — Attribution & Stressor Discovery**  
  
1. **Generate attribution vector:** For each stressor, compute its percentage contribution to total capacity loss. Rank by magnitude. Identify the top 5 contributors.  
1. **Run stressor discovery pass:** Compare M5 inferred psychosocial stressors against patient-reported stressors. Flag any M5-detected stressor that the patient has NOT explicitly reported as a **candidate latent stressor** — a stressor the patient may not be consciously aware of or may be underestimating. (Example: M5 detects escalating frustration language around childcare topics across 3 journal entries, but the patient has not listed childcare as a stressor.)  
1. **Tag latent stressors:** Mark `patient_aware = false` on candidate latent stressors. These are surfaced to the patient via M11/M24 with gentle, non-judgmental framing (“We’ve noticed some patterns in your journal entries that might be worth exploring…”).  
  
### **Stage 4 — Threshold Response & M66 Bridge**  
  
1. **Evaluate threshold crossings:** Compare current ICI band to previous ICI band. On any band transition (GREEN→YELLOW, YELLOW→ORANGE, ORANGE→RED), emit a threshold event.  
1. **Generate patient engagement signal:** On YELLOW entry, emit a supportive engagement signal to M11/M24: “Your inflammatory capacity is getting a bit crowded. Let’s look at what’s filling up and what we can do about it.” On ORANGE entry, increase engagement urgency and frequency. On RED entry, emit clinician notification via M6/M10 escalation pathway in addition to patient engagement.  
1. **Generate M66 Activation Prompt (D4):** On YELLOW or ORANGE entry, build the `EWAActivationPrompt` object specifying:  
- Which valve is the primary driver of capacity loss (the valve where intervention would produce the largest ICI improvement)  
- The top modifiable stressors for that valve  
- The patient’s existing VWA list (validated actions that have worked before — use these first)  
- Recent EWA history (what was tried, what hasn’t been tried yet)  
- Suggested intervention domains (mapped from stressor types to M66 action domains)  
1. **Emit VWA-first recommendation logic:** When the patient has active VWAs, the system MUST recommend established validated actions before suggesting new exploratory actions. Framing: “You’ve found that [VWA label] has consistently helped restore your capacity. This would be a good time to [action].” Only when VWAs are insufficient or unavailable for the current valve deficit should M66 exploratory actions be suggested.  
  
### **Stage 5 — Vault Persistence & Learning**  
  
1. **Persist ICI snapshot to M21:** Write the complete `ICISnapshot` (D3) to the vault with full provenance.  
1. **Track intervention-outcome correlations:** When a patient performs a wellness action (exploratory or validated) and ICI subsequently changes, log the action-outcome pair with timing, magnitude, and confounders. This feeds the VWA promotion gate (I-F).  
1. **Evaluate VWA promotion candidates:** On each ICI computation, check whether any exploratory wellness action has met the promotion criteria (≥3 attempts, ≥2 correlated ICI improvements, no adverse effects, no clinician contraindication). If so, promote to VWA and persist the `VWA` record (D5).  
1. **Emit audit artifacts:** Log all ICI computations, stressor census updates, threshold crossings, M66 activations, VWA promotions, and stressor discovery events as FHIR-compatible audit entries per Appendix C.11.  
  
-----  
  
## **M66 Handoff Prompt — Exploratory-to-Validated Lifecycle**  
  
**The following is a specification fragment intended for integration into M66 (Exploratory Wellness Actions) or its next revision:**  
  
> ### Proposed Addition to M66: Validated Wellness Action (VWA) Promotion Pathway  
>   
> **Context:** M68 (ICM) introduces the concept of wellness action lifecycle tracking. M66 currently owns the exploratory action catalog and the six-domain action taxonomy. The following extension proposes that M66 additionally manage the **promotion gate** from exploratory to validated status, using ICM-supplied outcome data.  
>   
> **Proposed M66 additions:**  
>   
> 1. **VWA Registry:** M66 maintains a per-patient registry of Validated Wellness Actions — actions that have passed the M68 promotion gate (≥3 attempts, ≥2 correlated ICI improvements, no adverse effects, no clinician contraindication).  
> 1. **VWA-First Recommendation Priority:** When M68 issues an `EWAActivationPrompt`, M66 MUST check the VWA registry before suggesting new exploratory actions. Validated actions are presented as established, reliable interventions (“This has worked for you before”), not as experiments.  
> 1. **VWA Maintenance & Deprecation:** VWAs are periodically re-evaluated. If a VWA stops correlating with ICI improvement over 3+ consecutive attempts, it is flagged for review and may be deprecated (status → SUSPENDED or DEPRECATED). Patient notification: “This practice doesn’t seem to be as effective as it used to be. Would you like to try something different?”  
> 1. **Patient Vocabulary:** Patient-facing language distinguishes between “Let’s try something new” (exploratory) and “Here’s something that’s worked well for you” (validated). This distinction reinforces patient agency and builds confidence in self-management.  
>   
> **This prompt is provided for review and integration into M66’s next revision. It does not modify M66 unilaterally; it proposes an integration contract.**  
  
-----  
  
## **Governance / Constraints**  
  
- ICM is EoH-owned and contains no guideline text, disease fact tables, drug class lists, ontology mirrors, lab interpretation tables, or phenotype dictionaries.  
- ICM does not diagnose, prescribe, or assert causality. It computes capacity, attributes stressors, and activates wellness action pathways.  
- ICI thresholds (65%, 50%, 35%) are governed defaults that may be adjusted per patient via clinician override. Threshold adjustment is logged and auditable.  
- Stressor discovery (latent stressor identification via M5) is surfaced to patients with non-judgmental framing and NEVER as accusation, diagnosis, or unsolicited therapy. The patient retains full agency to accept, reject, or ignore any stressor identification.  
- Contemplative and mindfulness practice references (yogic traditions, breathwork, somatic practices) are included as **evidence-informed wellness categories**, not as spiritual or religious recommendations. ICM maps these to their physiological mechanisms (HPA axis modulation, vagal tone, cytokine profiles) and treats them as outflow/inflow interventions with measurable outcomes, not as belief systems.  
- VWA promotion is patient-specific and does not generalize across patients without explicit population-level validation (which is out of scope for ICM and would require M48/research governance).  
- ICM does not create new suppression reasons. If ICM determines that a Band elevation is capacity-driven rather than disease-driven, it emits this as **advisory context** to M8/M9 but does not directly suppress.  
- The three-valve weights (inflow_weight, displacement_weight, outflow_weight) are initialized from population defaults and refined per-patient. Population defaults are governed by M48 (Continuous Learning) and updated only through governed retraining cycles.  
  
-----  
  
## **Dependencies**  
  
### **Consumes (read-only)**  
  
|Module   |What ICM consumes                                                                   |  
|---------|------------------------------------------------------------------------------------|  
|**M3**   |`stabilityBand`, `stackLevel`, `pauseFlag`, `pauseReason`                           |  
|**M4**   |`normalizedTags[]` (symptom, lifestyle, psychosocial tags)                          |  
|**M5**   |`PSI`, `persona_flags[]`, symbolic/psychosocial tags                                |  
|**M12**  |Narrative digest (for stressor extraction)                                          |  
|**M13**  |`flare_risk_slopes`, `inflammatory_burden_composite`, trajectory vectors            |  
|**M21**  |Historical ICI time-series, overflow events, VWA records, intervention-outcome pairs|  
|**M64**  |Active `fud_flags[]` (functional discordances as displacement stressors)            |  
|Wearables|Sleep metrics, HRV, activity levels                                                 |  
|PROs     |Stress, mood, energy, symptom severity self-reports                                 |  
|Labs     |Inflammatory markers (CRP, IL-6, ESR, cortisol, tryptase — where available)         |  
  
### **Produces / hands off to**  
  
|Module          |What ICM provides                                                                      |  
|----------------|---------------------------------------------------------------------------------------|  
|**M11**         |Patient engagement signals with ICI context and valve-specific guidance                |  
|**M21**         |`ICISnapshot` objects for longitudinal storage; intervention-outcome pairs; VWA records|  
|**M24**         |ICI visualization data (current value, band, attribution vector, time-to-overflow)     |  
|**M66**         |`EWAActivationPrompt` with valve context, stressor attribution, and VWA-first priority |  
|**M6** (opt-in) |ICI as optional context for escalation tier determination                              |  
|**M14** (opt-in)|ICI as optional context for intervention timing                                        |  
|**M48**         |Calibration telemetry (predicted vs. actual overflow events) for weight refinement     |  
  
### **Appendix references**  
  
- **Appendix C.11** — FHIR audit/provenance bindings for ICI snapshots, threshold events, VWA promotions.  
- **Appendix H.2** — Suppression field definitions (consumed; ICM does not create new suppression reasons).  
- **Appendix F.68** (new; to be created) — ICM threshold governance, population default weights, calibration loop parameters.  
  
-----  
  
## **Audit Hooks**  
  
- Every `ICISnapshot` computation: timestamp, all input module versions, data source timestamps, ICI value, band, attribution vector.  
- Every threshold crossing event: previous band, new band, triggering stressor(s), M66 activation prompt ID (if generated).  
- Every stressor discovery event (latent stressor identification): M5 evidence chain, `patient_aware` status, patient response (accepted/rejected/ignored).  
- Every M66 activation: prompt ID, trigger ICI, priority valve, VWA recommendations made, EWA suggestions made.  
- Every VWA promotion: source EWA ID, attempt history, correlation evidence, clinician review status.  
- Every VWA deprecation: VWA ID, failed correlation evidence, patient notification status.  
- Every calibration parameter update: previous weights, new weights, trigger (M48 retraining cycle), evidence (predicted vs. actual overflow events).  
  
-----  
  
## **Acceptance Tests**  
  
### **T-01: ICI Independence from Stability Band**  
  
Construct a patient with Band = 1 (stable), Stack = 2, but high displacement (two chronic conditions + major life stressor) and low outflow (poor sleep, no exercise). Verify ICI < 50% while Band remains 1. Verify that downstream modules receive both signals independently.  
  
### **T-02: Three-Valve Attribution Isolation**  
  
Apply a simulated inflow reduction (patient reports setting a boundary with a work stressor). Verify ICI improves, attribution vector shows reduced inflow contribution, and displacement/outflow values are unchanged.  
  
### **T-03: Overflow Forecast Accuracy**  
  
Using a patient with 6+ months of vault history including ≥2 confirmed overflow events, run the overflow probability model. Verify that predicted overflow probability for the 72-hour window preceding each historical overflow event was ≥0.6 (retrospective validation).  
  
### **T-04: Latent Stressor Discovery**  
  
Inject 5 journal entries with escalating frustration language about a specific topic (e.g., childcare) that the patient has not explicitly reported as a stressor. Verify that M5 tags are consumed by ICM and a candidate latent stressor is generated with `patient_aware = false` and appropriate evidence chain.  
  
### **T-05: M66 Activation Prompt Completeness**  
  
Trigger a GREEN→YELLOW threshold crossing. Verify that an `EWAActivationPrompt` is generated containing: priority valve identification, top modifiable stressors, VWA list (if any), EWA history, and suggested domains. Verify that all fields are populated and provenance-linked.  
  
### **T-06: VWA Promotion Gate**  
  
Simulate a patient who attempts a breathing practice 4 times over 3 weeks. In 3 of 4 attempts, ICI improves by ≥5% within 24h. Verify VWA promotion occurs. Then simulate the same practice with no ICI correlation — verify promotion does NOT occur.  
  
### **T-07: VWA-First Priority**  
  
Given a patient with 2 active VWAs and an M66 activation prompt, verify that the patient-facing output recommends VWAs before suggesting new exploratory actions.  
  
### **T-08: No Diagnostic Language**  
  
Scan all ICM outputs (patient-facing and clinician-facing) for diagnostic terminology (ICD codes, disease name assertions, causal claims). Verify zero occurrences.  
  
### **T-09: RED Band Clinician Escalation**  
  
Trigger ICI < 35% (RED). Verify that M6/M10 escalation pathway receives a clinician notification in addition to patient engagement, and that the notification includes ICI context and attribution vector.  
  
### **T-10: Contemplative Practice as Measurable Intervention**  
  
Log a patient’s breathwork practice via PRO. Verify that ICM tracks it as an outflow factor, M21 records the intervention-outcome pair, and that after ≥3 correlated ICI improvements, VWA promotion is evaluated.  
  
-----  
  
## **Metrics**  
  
|Metric                             |Definition                                                                                  |Target                                               |  
|-----------------------------------|--------------------------------------------------------------------------------------------|-----------------------------------------------------|  
|**ICI Calibration Accuracy**       |% of overflow events that were preceded by ICI < 35% within 72h                             |≥70% within 6 months of deployment                   |  
|**Attribution Completeness**       |% of ICI computations where attribution vector accounts for ≥90% of capacity loss           |≥95%                                                 |  
|**Latent Stressor Acceptance Rate**|% of latent stressor discoveries that patients acknowledge as relevant                      |≥40% (baseline; expected to improve with calibration)|  
|**VWA Promotion Rate**             |% of exploratory wellness actions that achieve VWA status within 60 days                    |Track only; no target (depends on patient population)|  
|**VWA Effectiveness Persistence**  |% of VWAs that maintain correlation at 90-day re-evaluation                                 |≥60%                                                 |  
|**M66 Activation Response Rate**   |% of M66 activation prompts that result in patient attempting ≥1 suggested action within 48h|≥30%                                                 |  
|**False Overflow Rate**            |% of predicted overflows (P ≥ 0.7) that do not result in a clinical event                   |< 40%                                                |  
  
-----  
  
## **v1.0 Implementation Checklist**  
  
1. Implement Stressor object (D1) and stressor census pipeline from M4/M5/M12/M64/wearable/PRO inputs.  
1. Implement OutflowFactor object (D2) and outflow aggregation from wearable/PRO/journal/M66 logs.  
1. Implement three-valve computation engine (Stage 2, steps 5–11) with governed default weights.  
1. Implement ICISnapshot object (D3) and vault persistence to M21.  
1. Implement ICI band assignment and threshold crossing detection (Stage 4, step 15).  
1. Implement M66 Activation Prompt generation (D4) with valve-specific context and VWA-first priority.  
1. Implement stressor discovery pass (Stage 3, steps 13–14) consuming M5 psychosocial tags.  
1. Implement overflow probability model with M21-calibrated parameters.  
1. Implement VWA Record (D5), promotion gate logic (I-F), and VWA maintenance/deprecation cycle.  
1. Implement patient-facing ICI visualization data contract for M24 (current value, band, top stressors, top outflow deficits, VWA recommendations).  
1. Build the latent stressor surfacing pipeline with non-judgmental patient framing templates (M11 integration).  
1. Implement calibration telemetry pipeline to M48 (predicted vs. actual overflow events, weight drift detection).  
1. Wire all audit hooks to M21/Appendix C.11 FHIR audit surface.  
1. Stand up acceptance tests T-01 through T-10 and tracked metrics.  
1. Create Appendix F.68 stub (ICM threshold governance, population defaults, calibration parameters).  
