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
