# M66 Handoff Fragment — Siddhi Practice Taxonomy for Exploratory Wellness Actions

**Source:** M68 ICM v1.1, Siddhi-to-Valve Capacity Modulation Taxonomy
**Purpose:** This document proposes practice catalog additions to M66 (Exploratory Wellness Actions) organized around the eight-siddhi framework defined in M68. M68 owns the mapping (which valve/infrastructure target each practice class affects and why). M66 owns the practice catalog (specific protocols, durations, patient-doable actions, and contraindication screening).

**This fragment does not modify M66 unilaterally; it proposes an integration contract for M66's next revision.**

---

## Proposed M66 Addition: Siddhi-Derived Practice Domains

Each siddhi maps to a **practice domain** within M66's existing six-domain action taxonomy. Where a siddhi-derived domain overlaps with an existing M66 domain, the siddhi framing provides *valve-specific targeting* — M68's `EWAActivationPrompt` can request a specific siddhi domain rather than a generic wellness category, enabling M66 to recommend actions that target the exact valve or infrastructure deficit identified by ICM.

---

### Domain 1: Aṇimā Practices — Displacement Reduction via Perspective Contraction

**ICM target:** Displacement valve — shrinking the subjective magnitude of chronic stressors.

**Mechanism:** Cognitive reframing, focused attention meditation, and therapeutic journaling that isolate a specific stressor and systematically reduce its perceived magnitude without denying its existence.

**Practice catalog (Exploratory):**

| Practice | Duration | Frequency | Data capture | Contraindication screen |
|----------|----------|-----------|--------------|------------------------|
| **Stressor isolation journaling** — Write about one specific displacement stressor. Describe it in three sentences. Then rewrite those sentences making the stressor 50% smaller. Then 90% smaller. Notice what changes in your body. | 10 min | As needed; recommended when M68 flags an expanding displacement stressor | PRO: pre/post magnitude self-rating (1–10); journal text → M4/M5 | Active psychotic episode; acute grief <30 days (reframing may feel dismissive) |
| **Zoom-out meditation** — Visualize the stressor as an object. See it at normal size. Now zoom out — see it from across the room, from a rooftop, from orbit. Hold the orbital perspective for 2 minutes. | 5 min | Daily during ORANGE/RED band | PRO: post-practice calm rating; wearable HRV delta if available | Dissociative disorders (depersonalization risk); active PTSD flashback state |
| **Proportionality check** — List 5 things in your life that are going well. Place the stressor alongside them. Rate its size relative to the list. | 5 min | 2–3x/week | PRO: pre/post magnitude rating | None known |

**When to activate:** M68 `EWAActivationPrompt` with `priority_valve = DISPLACEMENT` and at least one stressor with `trajectory = EXPANDING` and `modifiability ≥ MEDIUM`.

---

### Domain 2: Mahimā Practices — Displacement Reduction via Perspective Expansion

**ICM target:** Displacement valve — expanding self/awareness so stressors become proportionally smaller.

**Mechanism:** Self-transcendence practices, awe induction, and meaning-making that shift the frame of reference from problem-focused to context-expanded. Distinct from aṇimā (which shrinks the stressor) — mahimā grows the container.

**Practice catalog (Exploratory):**

| Practice | Duration | Frequency | Data capture | Contraindication screen |
|----------|----------|-----------|--------------|------------------------|
| **Awe walk** — Walk slowly in nature (or an unfamiliar environment) focusing entirely on things that are larger, older, or more complex than your problem. Deliberately seek wonder. | 15–30 min | 2x/week | PRO: post-walk mood + capacity rating; wearable: activity + HRV | Mobility limitations (adapt to seated outdoor observation); agoraphobia |
| **Legacy perspective** — Write or speak about your current stressor from the perspective of yourself 10 years from now. What does future-you think about this? | 10 min | As needed | Journal text → M4/M5; PRO: perspective shift rating | Active suicidal ideation (future-self exercise may trigger hopelessness); adjust framing with clinician guidance |
| **Vastness meditation** — Close eyes. Imagine the sky. Expand it. Imagine the ocean. Expand it. Imagine the universe. Hold awareness at the largest scale you can for 3 minutes. Notice where the stressor sits in that space. | 5 min | Daily during high-displacement periods | PRO: post-practice spaciousness rating | Dissociative disorders |

**When to activate:** M68 `EWAActivationPrompt` with `priority_valve = DISPLACEMENT` when multiple displacement stressors are present (the patient needs to feel larger than the aggregate, not shrink any single one).

---

### Domain 3: Laghimā Practices — Outflow Enhancement via Active Release

**ICM target:** Outflow valve + `lymphatic_tone` + `vagal_tone`.

**Mechanism:** Practices that directly enhance parasympathetic activation, lymphatic drainage, and the felt sense of burden leaving the body. These combine physical (lymphatic pump) and neurological (vagal tone) pathways.

**Practice catalog (Exploratory):**

| Practice | Duration | Frequency | Data capture | Contraindication screen |
|----------|----------|-----------|--------------|------------------------|
| **Extended-exhalation breathwork** — Inhale for 4 counts, exhale for 8 counts. Repeat 10 cycles. The extended exhalation activates the vagal brake and stimulates the respiratory lymphatic pump. | 5 min | 2–3x daily; prioritize evening (cytokine peak) | Wearable: HRV delta; PRO: lightness/heaviness rating | Severe respiratory conditions (adjust ratio); panic disorder (may trigger hyperawareness of breathing — start with 4:6 ratio) |
| **Physiological sigh** — Double inhale through nose (fill lungs, then top off with a second short inhale), followed by long exhale through mouth. Repeat 3x. This is the fastest known vagal activation technique (Huberman Lab, Stanford). | 1 min | As needed; excellent for acute turbulence moments | PRO: pre/post stress rating | None known at recommended dosage |
| **Gentle movement flow** — 10 minutes of slow, continuous movement: walking, stretching, gentle yoga, tai chi. Focus on smooth, uninterrupted motion. The goal is lymphatic pumping, not exertion. | 10 min | Daily; critical when `lymphatic_tone < 0.4` | Wearable: activity; PRO: energy/heaviness rating | Post-exertional malaise (PEM) — if patient has ME/CFS or PEM history, cap at 5 min and monitor for 24h crash. If crash occurs, this practice is CONTRAINDICATED and should not be promoted to VWA. |
| **Body-scan release** — Progressive attention scan from feet to head. At each body region, notice tension, then deliberately "let it drain downward." Combine with slow exhalation at each release point. | 10 min | Daily; pre-sleep optimal (enhances glymphatic clearance window) | PRO: pre/post tension rating; wearable: sleep onset latency | None known |
| **Cold exposure (calibrated)** — 30-second cold water at end of shower, or face immersion in cold water for 15 seconds. Activates vagal response via trigeminal nerve (dive reflex). | 30 sec–2 min | 1x daily | PRO: post-practice alertness + calm rating; wearable: HRV | Cardiovascular conditions (consult clinician); Raynaud's; cold urticaria; pregnancy |

**When to activate:** M68 `EWAActivationPrompt` with `priority_valve = OUTFLOW` or infrastructure deficit `lymphatic_tone < 0.4` or `vagal_tone < 0.4`.

---

### Domain 4: Garimā Practices — Inflow Reduction via Grounding

**ICM target:** Inflow valve + turbulence dampening.

**Mechanism:** Somatic grounding practices that activate the ventral vagal complex, reducing HPA axis reactivity to acute stressors. Under the turbulence regime, garimā practices are first-line because they directly counteract the amplification coefficient.

**Practice catalog (Exploratory):**

| Practice | Duration | Frequency | Data capture | Contraindication screen |
|----------|----------|-----------|--------------|------------------------|
| **5-4-3-2-1 sensory grounding** — Name 5 things you see, 4 you hear, 3 you touch, 2 you smell, 1 you taste. Forces attention into present-moment sensory experience, interrupting rumination and cortisol cascade. | 3 min | As needed; especially during turbulence | PRO: pre/post reactivity rating | None known |
| **Weighted breathing** — Place a heavy book or weighted object on your chest/abdomen while lying down. Breathe against the weight. The proprioceptive input from the weight activates grounding circuitry. | 5–10 min | Daily during turbulence periods | PRO: groundedness rating; wearable: HRV | Chest/abdominal pain; recent surgery |
| **Barefoot earth contact** — Stand or walk barefoot on natural ground (grass, soil, sand) for 5 minutes. Grounding/earthing research shows measurable cortisol reduction and anti-inflammatory effects (Oschman et al., 2015). | 5 min | Daily if accessible | PRO: calm rating | Neuropathy with loss of protective sensation; unsafe terrain |
| **Anchor phrase repetition** — Choose a short phrase ("I am here. I am safe. This will pass.") and repeat it slowly, synchronized with breath, for 2 minutes. The rhythmic vocalization activates vagal tone via laryngeal nerve. | 2 min | As needed | PRO: pre/post reactivity rating | None known |

**When to activate:** M68 `EWAActivationPrompt` with `priority_valve = INFLOW` OR `turbulence_active = TRUE`. Garimā practices are part of the **turbulence countermeasure triad** (garimā + iśitva + prākāmya).

---

### Domain 5: Prāpti Practices — Portable Recovery (Outflow Access Anywhere)

**ICM target:** Outflow valve — resilience portability.

**Mechanism:** Internalized self-regulation techniques that require no equipment, no specific location, and no time commitment beyond 1–2 minutes. These ensure the patient can activate outflow in any circumstance.

**Practice catalog (Exploratory):**

| Practice | Duration | Frequency | Data capture | Contraindication screen |
|----------|----------|-----------|--------------|------------------------|
| **Micro-breathwork** — 3 physiological sighs (double-inhale + long exhale) anytime, anywhere. Takes 30 seconds. No one around you notices. | 30 sec | Ad lib; encouraged before known stressor events | PRO: if logged, note context | None |
| **Palming** — Place warm palms over closed eyes. Press gently. Hold for 60 seconds. The vagal activation from orbital pressure + warmth + darkness is immediate. | 1 min | Ad lib | PRO: if logged, note context | Eye conditions (adjust pressure) |
| **Subvocal humming** — Hum at the lowest comfortable pitch with mouth closed. Vibration stimulates the vagus nerve via its auricular and laryngeal branches. Can be done silently enough for a meeting or commute. | 1–2 min | Ad lib | PRO: if logged | None |

**When to activate:** Always available in the patient's wellness toolkit. Prāpti practices should be introduced early (GREEN band) so they are familiar and habituated before they're needed under turbulence.

---

### Domain 6: Prākāmya Practices — Adherence and Motivational Sustenance

**ICM target:** Meta-capacity — the ability to perform wellness actions despite resistance.

**Mechanism:** Habit-formation, motivational interviewing principles, and micro-commitment strategies that maintain wellness practice adherence when the patient's executive function is depleted by high allostatic load.

**Practice catalog (Exploratory):**

| Practice | Duration | Frequency | Data capture | Contraindication screen |
|----------|----------|-----------|--------------|------------------------|
| **Two-minute rule** — Commit to doing the wellness action for only 2 minutes. If you want to stop after 2 minutes, stop. Most of the time, starting is the hard part and you'll continue. | 2 min (minimum) | Every time a VWA or EWA is recommended | PRO: did-you-start (yes/no); duration if continued | None |
| **Identity anchoring** — Write or say: "I am a person who [does the action]." Not "I should" or "I need to" — "I am." Identity-based framing produces stronger habit persistence than goal-based framing (Clear, 2018). | 1 min | At wellness action initiation | Journal text | None |
| **Accountability trigger** — Pair a wellness action with an existing daily habit (habit stacking). "After I pour my morning coffee, I do 3 physiological sighs." | N/A (embedded in routine) | Daily | M66 log: action completion | None |

**When to activate:** M68 `EWAActivationPrompt` when `M66_activation_response_rate < 0.3` (patient is receiving recommendations but not acting on them) OR during turbulence (when motivational collapse risk is highest). Prākāmya is part of the **turbulence countermeasure triad**.

---

### Domain 7: Iśitva Practices — Mastery of Physiological Response

**ICM target:** Inflow valve + turbulence dampening (advanced).

**Mechanism:** Advanced autonomic self-regulation that enables conscious modulation of the stress response itself — not avoiding the stressor or reframing it, but choosing how much of the inflammatory cascade to permit. This is the highest-leverage inflow modulation skill and the most advanced siddhi to develop.

**Practice catalog (Exploratory):**

| Practice | Duration | Frequency | Data capture | Contraindication screen |
|----------|----------|-----------|--------------|------------------------|
| **Biofeedback-assisted HRV training** — Using wearable HRV display, practice maintaining high coherence (balanced sympathetic/parasympathetic) while deliberately imagining a stressful scenario. Train the system to stay calm under imagined load. | 10–15 min | 3x/week; progressive difficulty | Wearable: HRV coherence score; PRO: difficulty rating | Severe anxiety disorders (start with neutral scenarios; progress slowly under clinician guidance) |
| **Stress inoculation micro-exposure** — Deliberately expose yourself to a minor stressor (cold water, brief social discomfort, physical challenge) and practice maintaining autonomic calm. Build upward gradually. | 2–5 min | 2–3x/week | PRO: reactivity rating + recovery time; wearable: HRV recovery curve | PTSD (trauma-informed approach required; do NOT use trauma-related stressors; use purely physical micro-stressors only) |
| **Equanimity meditation** — Sit with awareness of a moderately uncomfortable sensation (mild cold, mild hunger, itchy fabric) without reacting. Practice noticing the sensation, the urge to react, and the space between them. Gradually extend tolerance duration. | 5–10 min | Daily | PRO: duration maintained; equanimity self-rating | Chronic pain patients (may exacerbate pain-vigilance; adapt with clinician) |

**When to activate:** After patient has established baseline practices from domains 3–5 (laghimā, garimā, prāpti). Iśitva practices should NOT be the first recommendation — they require a foundation of somatic awareness and basic vagal regulation. Recommended after ≥2 VWAs are established in other domains. Iśitva is part of the **turbulence countermeasure triad** for advanced patients.

---

### Domain 8: Vaśitva Practices — Environmental Mastery

**ICM target:** Inflow valve — external source reduction.

**Mechanism:** Behavioral activation targeting the patient's environment, relationships, and information inputs. The most concrete and immediately actionable domain — requires no internal state change, only external arrangement.

**Practice catalog (Exploratory):**

| Practice | Duration | Frequency | Data capture | Contraindication screen |
|----------|----------|-----------|--------------|------------------------|
| **Digital boundary audit** — Review phone screen time, social media usage, and news consumption. Set one specific limit (e.g., no news after 8pm; 30-min social media cap). | 15 min (setup) | Review weekly | PRO: adherence to limit; screen time data if shared | None |
| **Environment scan** — Walk through your primary living/working space. Identify one source of sensory stress (clutter, noise, poor lighting, allergens) and address it today. | 15–30 min | 1x/week | PRO: what was changed; pre/post environment comfort rating | Physical limitations (adapt to what's achievable) |
| **Relationship energy audit** — List the 5 people you interact with most. Rate each as energy-giving (+) or energy-draining (−). For each (−), identify one specific boundary you could set. Set one this week. | 20 min | Monthly | Journal text → M4/M5; PRO: boundary-setting confidence rating | Active domestic violence or coercive control situations (boundary-setting may escalate danger — flag for clinician review) |

**When to activate:** M68 `EWAActivationPrompt` with `priority_valve = INFLOW` and top modifiable stressors having `modifiability_domain = ENVIRONMENTAL` or `SOCIAL`.

---

## Turbulence Countermeasure Triad — Priority Recommendation Logic

When M68 issues an `EWAActivationPrompt` with `turbulence_active = TRUE`, M66 SHOULD prioritize the following three domains as first-line recommendations:

1. **Garimā** (grounding) — immediate inflow dampening
2. **Iśitva** (mastery) — turbulence coefficient reduction (if patient has existing practice; skip if novice)
3. **Prākāmya** (adherence) — prevent motivational collapse under turbulence

If the patient is new to contemplative practices (no VWAs in domains 4, 7, or 6), substitute iśitva with:
- **Prāpti** (portable recovery) — gives the patient immediate tools that work anywhere

The triad addresses the three failure modes of turbulence: amplified reactivity (garimā), lost autonomic control (iśitva), and inability to act (prākāmya).

---

## Governance Notes for M66 Integration

* All practices are **Exploratory Wellness Actions** until promoted to VWA status via M68's promotion gate (I-F).
* Sanskrit terminology is OPTIONAL in patient-facing communication and is used ONLY if the patient has expressed interest. Default patient-facing labels use plain language (e.g., "grounding practice" not "garimā practice").
* Contraindication screening is mandatory before any practice is recommended. Contraindications flagged by a clinician override M66 recommendations.
* Practice durations and frequencies are starting recommendations. Patient tolerance and preference override defaults. The two-minute rule (prākāmya) applies to all practices — starting is more important than completing.
* Practices targeting the turbulence countermeasure triad should be introduced during GREEN band (low-stakes, habituating) so they are available as established tools when turbulence occurs. Do not wait for turbulence to introduce these practices.

---

*This fragment is provided for review and integration into M66's next revision. It does not modify M66 unilaterally; it proposes practice domains, catalog entries, and activation logic aligned with M68 ICM v1.1's siddhi-to-valve mapping.*
