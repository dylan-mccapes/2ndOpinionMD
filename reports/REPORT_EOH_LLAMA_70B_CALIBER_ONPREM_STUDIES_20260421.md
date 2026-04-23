# REPORT — Why `eoh-llama-70b` Should Produce Higher-Caliber Answers Than Expected on On-Premise Studies

**Date:** 2026-04-21
**Author:** 2ndOpinionMD Platform Team
**Companion to:** `STUDY_PROPOSAL_LONGITUDINAL_GRAPH_COMPARISON_20260421.md`
**Scope:** PortalNode-01, `eoh-llama-70b` (2× RTX 4090, up to ~100 k usable context), with `eoh-llama-8b` as the traversal/retrieval worker, PTV as the patient substrate, MKG as the knowledge substrate, and EoH modules + Python scripts as the reasoning substrate.

---

## TL;DR

**Yes — within a well-defined envelope, `eoh-llama-70b` in this stack should meaningfully out-perform a general cloud LLM answering the same clinical question.** Not because the 70B is smarter than a frontier model — it isn't — but because **we have removed almost every task the model is bad at** (fact recall, pharmacology, guideline citation, arithmetic, causal inference) and **handed it the tasks it is genuinely good at** (structured synthesis over already-retrieved facts, pattern recognition over long, well-formatted context, JSON-schema-compliant output, and "is anything missing?" judgments).

The architectural bet is: **the 70B never has to know anything. It only has to read carefully and tell us what fits, what doesn't, and what's missing.** That is a reading-comprehension job, and 70B-class models are good at it.

---

## 1. Restating the User's Claim Precisely

> "With PTV, MKG, and EoH, `eoh-llama-70b` should produce a much higher-caliber answer for these on-premise studies than would be expected. It needs nothing in its training data. It doesn't need to do the reasoning itself. It gets PTV, MKG, EoH and the result is either deterministic or the agent says what is missing."

Decomposed:

1. **"Needs nothing in its training data."**
   — True in the limit: every factual claim is anchored to retrieved context. Training data still contributes *language competence*, *formatting*, *summarization*, and *pattern completion*; these are acceptable because they don't create new clinical facts.

2. **"Doesn't need to do the reasoning itself."**
   — Largely true: causal reasoning lives in **EoH modules** (M68 Inflammatory Capacity, flare detector, adherence estimator, etc.); numerical reasoning lives in **Python scripts**; retrieval ranking lives in **hybrid TS/ANN fusion**. The 70B performs *structured synthesis* over those outputs.

3. **"Deterministic, or agent says what's missing."**
   — This is the critical closure. "I don't know" is a first-class answer, rewarded by the Modelfile system prompt and enforced by JSON schema validation. This collapses the distribution of failure modes to one we can triage, rather than a long tail of plausible-sounding hallucinations.

The rest of this report justifies each piece.

---

## 2. The Architectural Bet, Stated as a Theorem

> **Theorem (informal).** For a clinical question `Q` over patient graph `G`, let `R = retrieve(Q, G, MKG)` be the set of facts and citations produced by the 8B worker, `E = eoh_modules(G, R)` be the deterministic reasoning outputs, and `M = math_scripts(G, R, E)` be the numerical outputs. Then the 70B's job is to compute
>
>   `answer(Q) = render(Q, R, E, M)  ∪  missing(Q, R, E, M)`
>
> where `render` is a structured-synthesis function (reading comprehension + JSON output) and `missing` is a completeness check. Neither requires the model to originate new facts.

**Why this is easier than "clinical reasoning":**
- `render` is a task modern 70B models crush on benchmarks (MMLU-style, JSON-mode, citation-style).
- `missing` is implemented as a schema: the Modelfile requires every slot to be filled from `R ∪ E ∪ M` or explicitly marked unfilled; structural validation catches violations.

**Why the 8B can do `retrieve` well:**
- The 8B walks a typed graph with connascence edges — a *navigational* task, not a reasoning task.
- Hybrid TS/ANN fusion is deterministic machinery; the 8B picks *what to ask*, not *what the answer is*.

**Why EoH and math own the reasoning:**
- Flare detection is a rule/window algorithm, not an opinion.
- M68 Inflammatory Capacity is a parameterized model.
- Propensity scoring, survival, change-points — all Python.
- None of these depend on model weights.

---

## 3. What the 70B Is Asked to Do — And Why It Is Suited to It

| task                                             | traditional LLM difficulty | why easy for 70B here                                  |
|--------------------------------------------------|----------------------------|--------------------------------------------------------|
| Recall drug dose ranges                          | hallucinates              | **not asked** — pulled from MKG with citation           |
| Recall ACR/EULAR guidelines                      | partially right           | **not asked** — retrieved guideline snippets in context |
| Check guideline adherence                        | plausible-sounding        | **diff** over expected vs. observed, both in context    |
| Compute latencies / slopes                       | poor                      | **not asked** — Python produces, 70B reads              |
| Detect a flare                                   | hand-wavy                 | **not asked** — EoH flare detector emits a signal       |
| Summarize a 769-node patient timeline            | good                      | **asked** — fits well within 100 k context              |
| Produce valid JSON per schema                    | improving                 | **asked** — enforced by system prompt + validator       |
| Say "I don't know enough to answer X"            | historically weak         | **asked** — rewarded, not punished, by our scoring      |
| Chain plausible-but-wrong clinical stories       | high                      | **removed** — causal graph comes from EoH, not the LLM  |

The key shift: **every row where a traditional LLM is weak is either taken off the 70B's plate or converted into a structured-match task.**

---

## 4. Why 100 k Context × On-Prem × Temperature 0 Is a Force Multiplier

### 4.1 Full patient visible at once
A typical 769-node graph (prototype), compressed through the 8B down-selector, fits comfortably under 100 k tokens with room for MKG snippets, EoH emissions, and guideline text. Compare to a cloud workflow where retrieval-per-turn causes the model to forget earlier slices — **the 70B never has "retrieval-induced amnesia"** for a single patient.

### 4.2 Deterministic outputs
- `temperature = 0`, fixed seed, locked weights → same input yields same output.
- This is *necessary* for a study. Stochastic LLM outputs do not pass peer review.
- The cloud alternative (streaming, sampled) does not offer this guarantee even at T=0 due to batched-inference non-determinism on managed endpoints.

### 4.3 Reproducibility as evidence
- Every answer is replayable from `(graph_hash, prompt_hash, retrieval_ids, model_hash)`.
- Reviewers can re-run the pipeline and obtain the same result — the scientific baseline.

### 4.4 HIPAA closure
- No PHI ever leaves the box. This is not a quality claim, but it is a necessary condition for the entire enterprise; without it, the best model in the world can't be used.

### 4.5 Modelfile as guardrail
- System prompt fixes output schema, forbids un-cited claims, and converts uncertainty into a declared field.
- Because it's our Modelfile, its contents are version-controlled alongside code — another provenance hook.

---

## 5. Quantified Expectation vs. a Naive LLM Baseline

For **bounded-scope clinical-reasoning questions** (the class our studies ask):

| metric                                          | naive cloud LLM baseline (no tools) | our stack (8B+70B+MKG+EoH) | expected delta |
|-------------------------------------------------|------------------------------------:|---------------------------:|---------------:|
| Hallucinated pharmacological fact rate          | 10–25 %                             | ~0 % (retrieval-anchored)  | **−10–25 pp**  |
| Correct guideline citation                      | 40–60 %                             | 90–98 %                    | **+30–50 pp**  |
| Numerical arithmetic error                      | 5–20 %                              | 0 % (Python)               | **−5–20 pp**   |
| Reproducibility (same input → same output)      | probabilistic                       | deterministic              | **qualitative**|
| "I don't know" answered when appropriate        | rare                                | expected/required          | **qualitative**|
| Clinically-interesting novel reasoning          | frontier-dependent                  | slightly weaker (70B local)| **small −**    |
| Narrative readability                           | good                                | good                       | **≈ 0**        |

These are engineering expectations, not benchmark results — benchmarking is a study deliverable. They reflect the pattern seen in every LLM+tools deployment since 2023: **bind the model to retrieved facts and the error rate collapses by an order of magnitude on fact-bearing tasks, at the cost of a small ceiling on creative reasoning (which we do not want in a study anyway).**

---

## 6. The Cost Side: What the 70B *Won't* Do Better

Honesty about limits is part of the caliber claim.

1. **Frontier-level creative reasoning.** On an open-ended "what's the differential?" with no retrieval, GPT-5-class closed models will outperform a local 70B. We do not operate in that mode.
2. **Long-chain multi-hop reasoning without decomposition.** If we ask the 70B to "figure it out end-to-end," context-middle attention decay and chain-of-thought drift will hurt. **Mitigation:** EoH modules and Python do the chaining; 70B reviews each step.
3. **Rare-concept coverage below MKG.** If a guideline or drug isn't in MKG, the 70B shouldn't invent it. The system correctly fails to `missing_data`. This is a coverage-engineering problem, not a model problem.
4. **Temporal reasoning at the day-level.** Latency / ordering questions belong in Python. We must not let the 70B answer "was drug A stopped before lab B spiked?" without a Python check.
5. **Dose conversions / unit math.** Never. Always Python.
6. **Causal inference.** The 70B can *render* a causal story only when EoH modules + study design support it. Otherwise, the answer is descriptive.

If a reviewer asks *"won't the 70B hallucinate?"* — the answer is: **it can, if you ask it to originate facts. We have structurally removed almost every opportunity to do so.**

---

## 7. Failure Modes and Their Mitigations

| failure mode                                              | mitigation                                                                   |
|-----------------------------------------------------------|------------------------------------------------------------------------------|
| Context-middle attention decay at 100 k                   | Place the summary + question at both start and end; 8B pre-digests to <40 k |
| Un-cited claim sneaks through                             | JSON schema requires `evidence_ids: []`; validator rejects empty arrays      |
| Out-of-schema output                                      | Regenerate (retry), then degrade to `structured_error` with partial fields   |
| Drift across runs                                         | `temperature=0`, fixed seed, pinned model hash; CI-check answer equality    |
| Model claims certainty where MKG coverage is thin          | Confidence must be derived from retrieval-coverage metrics, not model-free  |
| 8B over-selects irrelevant nodes                          | Bounded context budget per node-type; scoring rubric; manual audits          |
| EoH module disagrees with 70B's rendering                 | Module emits the authoritative value; 70B cannot override, only explain it   |
| MKG citation stale (guideline updated)                    | Retrieval filters by `valid_from`/`valid_to`; provenance notes guideline rev |
| Spurious graph edges bias pattern detection               | `edge_provenance.strength` thresholded; low-strength edges flagged for review|

---

## 8. Caliber Evaluation Plan

We will measure, not assert, caliber:

### 8.1 Benchmarks
- Internal rheumatology QA set (curated with clinician review; N = 200) — accuracy + citation correctness.
- Guideline-adherence diff task — agreement with clinician-reviewed gold (κ).
- Schema-compliance rate (fraction of runs passing validator on first try).
- Determinism — bit-identical outputs across N replicas.
- Missing-data calibration — is confidence ~proportional to retrieval coverage?

### 8.2 Ablations
- Remove MKG → expect collapse on factual questions.
- Remove EoH modules → expect collapse on flare/trajectory tasks.
- Remove Python math → expect arithmetic error rate to spike.
- Remove 8B pre-digest → expect context-middle decay to show up.

Each ablation tells us **which component is load-bearing**, which is an architectural validation, not just a model evaluation.

### 8.3 Dual-review for the study
- For a stratified random sample (≥ 5 %), a board-certified reviewer grades the 70B output on accuracy, completeness, and safety.
- Disagreements are auto-logged with provenance and fed back into prompt / retrieval improvements.

---

## 9. Why This Out-Performs "Just Use a Frontier Cloud Model"

Even if we had an API to a frontier cloud model, for **on-premise longitudinal studies** the local stack wins:

- **HIPAA:** frontier cloud is not an option for full-graph PHI.
- **Determinism:** required for peer review; cloud doesn't reliably provide it.
- **Reproducibility:** model weights can change under you; locked local weights cannot.
- **Cost:** 100 K graphs × multi-pass review at cloud token rates is prohibitive; local electricity is bounded.
- **Latency & parallelism:** we control the queue; we can run continuous OGrE.
- **Tool integration:** EoH modules and `ehr.patient_graph_vision` queries are in-process; no network hop.
- **Provenance:** ProvenanceEngine can hash the exact model binary.

The claim is not "local 70B beats cloud frontier at everything." It is "**for the class of questions these studies actually ask, local 70B with PTV + MKG + EoH beats cloud frontier without them, and beats cloud frontier-with-them on the non-performance axes that decide whether a study is publishable.**"

---

## 10. Practical Upgrade Path (short list)

These make the caliber claim demonstrably true, not merely plausible:

1. **Lock the Modelfile v1** — system prompt enforcing: retrieval citation, JSON schema, `missing_data` as first-class, temperature 0 default, no freeform chain-of-thought in the user-visible channel.
2. **Introduce `missing_data` as a schema field** at the top of the 70B's output, populated by an explicit check against retrieval coverage.
3. **Add a retrieval-coverage score** to every output (`coverage = retrieved_codes / asked_codes`), surfaced in the UI.
4. **Ship the 8B "budget" rubric** — per-node-type token allowance, ensures the context pack fits and avoids one node-type dominating.
5. **Per-answer unit tests** — for our 200-question internal set, CI asserts the answer is *equivalent* (not byte-identical, but structurally matching) across runs.
6. **Ablation dashboards** — toggle MKG / EoH / Python and re-run 20 graphs to visualize caliber drop.
7. **Adversarial prompts** — periodic "trick" questions designed to induce hallucination; our pass criterion is to produce `missing_data`, not a plausible-sounding wrong answer.

---

## 11. Direct Answer to the Two Posed Questions

### 11.1 Is the 70B higher-caliber than expected here?
**Yes, because we measure "caliber" on axes that matter for an on-premise, reproducible, HIPAA-bound clinical study:** retrieval-anchored factuality, guideline citation, deterministic output, structured schema compliance, and explicit missing-data signaling. On those axes the stack's ceiling is set by retrieval quality and EoH module quality — both are things we can grind on — rather than by the model's raw capability.

### 11.2 Will the result be deterministic or "what's missing"?
**Yes — by construction, if we enforce the Modelfile and validator.** The non-determinism risk is eliminated via `temperature=0 + seed + pinned weights`; the hallucination risk is eliminated by requiring every claim to carry an `evidence_id`. Where evidence is absent, the schema forces a `missing_data` emission, which is exactly the well-defined failure mode the user described.

---

## 12. One-Sentence Summary for External Reviewers

> *"We are not asking `eoh-llama-70b` to practice medicine; we are asking it to read 100 k tokens of already-retrieved, already-verified, already-computed material and tell us — in structured, cited, reproducible form — what fits, what diverges, and what is missing. That is a task the model is demonstrably good at, and every other step in the pipeline is deterministic."*

---

## Addendum (rev 2026-04-22) — Graph primitives that make the caliber claim stronger

Review of the full-schema reference graph (`ptv_46860f06-...full_20260422T143255Z_pretty.json`, 632 events / 142 arcs) confirms that several primitives *already in the graph* tighten the argument above. They are worth calling out explicitly because each of them removes work the 70B would otherwise have to do — and removing LLM work is the mechanism by which caliber goes up.

1. **`card` is a built-in 70B-optimized digest.** Every event ships with a ~100–200 token `{ts, icd, drug, type, title, arc_ids, one_line, salience}` object. The 70B's context is dominated by these digests rather than raw events, roughly halving context burn and placing *only signal* in front of the model. Reading comprehension over digests is the easiest case of reading comprehension.

2. **`salience` is a native priority signal (1.69–8.04 range).** The 8B does not have to re-derive "which events matter"; the graph already assigns a score. This collapses the selection-error surface — a historically common source of LLM mistakes ("the model focused on the wrong thing") — into a deterministic rank.

3. **`entity_keys` are normalized join handles.** Motif queries and cross-graph cohorting become set-membership tests. The 70B is never asked "is M05.9 the same as M06.0?" — the keys make identity explicit.

4. **`canonical_id` encodes cross-source agreement.** When the same clinical fact appears from multiple sources, `canonical_id` collisions signal *independent confirmation* — a trust lever the 70B can cite directly ("fact F confirmed by N sources") rather than guessing.

5. **`status_flags` are pre-labeled longitudinal states.** `flare`, `worsening`, `improving`, `stopped`, `continued`, `chronic`, `acute` — the 70B is not asked to infer temporal state from prose; it is asked to reconcile labeled state with MKG expectations.

6. **`in_workup_for` and `caused_by` are already clinical-semantic edges.** Diagnoses carry links to the procedures/labs that worked them up, and to coded causes. The 70B reviews an existing causal graph rather than constructing one — its most reliable mode.

7. **Arcs are the unit of work, not events.** 142 populated arcs give us a native cohort-comparable substrate. The 70B reviews *arcs*, with ~3.3 events per arc on average, which fits trivially. `arc.open_questions` becomes the exact bi-directional TODO list that makes "missing_data" a first-class output rather than an afterthought.

8. **`metadata.index.by_arc` is a pre-computed reverse index.** No scans, no LLM traversal cost — the pipeline's data access is O(1) per arc.

9. **`metadata.pro.forward.patient_reported_outcomes_channel: true` is already wired.** The FORWARD PRO channel is a first-class metadata concept; journal/PRO event nodes slot into the existing structure rather than requiring a parallel system.

**Net effect.** Every item above is work the 70B does *not* have to perform. The section-3 table of "tasks the 70B is not asked to do" was already long; these primitives lengthen it further. The caliber claim stated in §2 (theorem) becomes more defensible, not less: `render(Q, R, E, M)` gets a richer, cleaner `R` than we had at the time of the original report, and the `missing(Q, R, E, M)` check has a native home in `arc.open_questions`.

The practical implication is that **caliber on this stack is bounded above by MKG coverage and EoH module quality, not by model capability.** Invest accordingly.

---

**End of report.**
