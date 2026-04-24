# STRATEGY — Bayesian Reasoning over PatientTimelineVision (PTV)

**Date:** 2026-04-23  
**Scope:** Honest, rigorous uncertainty math under our existing PTV / MKG / EoH stack. Pilot-grade in 4–6 weeks; cohort-grade by the end of the FORWARD/RISE longitudinal phase.  
**Companion docs:**
- `reports/STRATEGY_GRAPH_TRAVERSAL.md`
- `reports/STRATEGY_MKG_LOCAL_EMBEDDINGS_20260421.md`
- `reports/STRATEGY_PATIENT_GRAPH_LIVING_SYSTEM_20260317.md`
- `receipts/RECEIPT_PTV_TOOLKIT_HARNESS_EOH_LLAMA_LUCIFER_20260423.md`

> **One-liner.** Make the math under our Uncertainty Carriers (UCs) **explicitly Bayesian**: per-patient posteriors update sequentially as new PTV events arrive; population priors come from MKG and the cohort itself; 8B probes compute the cheap closed-form updates, 70B reviewers learn the hyperpriors and finalize answers.

---

## 1. Why Bayesian, why now

We already produce **Uncertainty Carriers** with `point_estimate`, `band_90`, `confidence`, `basis`, `evidence_event_ids`. Today the bands are **heuristic-coherent** (calibrated by tuning, plus provenance) but **not provably coherent** in the Bayesian sense. Three pressures push us to formalize:

1. **Longitudinal questions** dominate the FORWARD/RISE pilot (flare risk, progression, taper safety). These are **belief updates over time** — exactly Bayes.
2. **Heterogeneous evidence**: PROs, labs, meds, notes, imaging — each with different reliability. Likelihoods + provenance weights are the principled way to combine them.
3. **Glass-box requirement**: regulators, clinicians, and partner societies will ask "how confident, why, and what would change your mind?" Bayesian posteriors answer all three by construction.

### Bayes' theorem (recap)

\[
P(H \mid E) = \frac{P(E \mid H)\,P(H)}{P(E)}
\]

For an ordered PTV stream of events \(E_1,\dots,E_n\):

\[
P(H \mid E_1,\dots,E_n) = \frac{P(E_n \mid H, E_1\dots E_{n-1})\,P(H \mid E_1\dots E_{n-1})}{P(E_n \mid E_1\dots E_{n-1})}
\]

Yesterday's posterior is today's prior. PTVs are this equation's natural substrate.

---

## 2. PTV ↔ Bayes mapping (canonical)

| PTV element | Bayesian role | Why it fits |
|---|---|---|
| Clinical hypothesis (flare, progression, dx) | Hypothesis \(H\) | What we want a belief over |
| Events (lab / med / PRO / note) + connascence | Evidence \(E_i\) | Time-stamped, typed, traceable |
| MKG (ICD / RxNorm / LOINC + guidelines) | Source of priors \(P(H)\) | Population base rates and conditional risks |
| Code index (`metadata.code_index`) | Likelihood feature store | Per-code chronology = features over time |
| Salience + provenance (`discovered_by`, `edge_provenance`) | Likelihood weights | Down-weight noisy or weakly-attributed evidence |
| **Uncertainty Carrier** (UC) | **Posterior summary** | `point_estimate` = posterior mean; `band_90` = 90% credible interval; `confidence` = stability of the posterior; `evidence_event_ids` = the conditioning set |
| Connascence edges | Conditional independence structure | Bayesian-network skeleton already exists |
| OGrE enrichment cycles | Posterior refresh trigger | When new evidence is added, recompute UCs |

**The architectural claim:** a UC, properly redefined, **is** a posterior. We do not need new objects — we tighten the math under existing ones.

---

## 3. Single-patient flare update — worked example

### 3.1 Conjugate prior choice
For a probability in \([0,1]\) (e.g., "flare in next 30 days"), the **Beta–Bernoulli** family is the natural conjugate pair:

\[
H \sim \mathrm{Beta}(\alpha,\beta), \quad E_i \mid H \sim \mathrm{Bernoulli}(H)
\]

Update is closed form: each "positive" evidence increments \(\alpha\), each "negative" increments \(\beta\). No MCMC, no tensors — a single 8B forward pass can do this.

### 3.2 Numbers (illustrative)
Initial weak prior \(\mathrm{Beta}(2,8)\) → mean **0.200**.

| Step | Event semantics | Posterior mean | Notes |
|---|---|---|---|
| Prior | none | 0.200 | weakly informative |
| +1 | positive flare signal (CRP↑, PRO↑) | **0.273** | one positive |
| +2 | positive (PRO sustained) | **0.333** | two positives |
| +3 | positive (med change for control) | **0.385** | three positives |
| +4 | negative (PRO returns to baseline) | **0.357** | one negative |

Final 90% credible interval ≈ **[0.166, 0.573]** — what a UC's `band_90` should literally be.

### 3.3 Implementation surface
A new toolkit primitive:

```text
bayesian_update_uc(
    hypothesis_id: str,           # e.g. "flare_30d"
    evidence_event_ids: list[str],
    prior: {"family": "beta", "alpha": 2.0, "beta": 8.0},
    likelihood_spec: {            # how each event maps to (positive|negative|skip)
        "rules": [...],           # MKG / regex / code_index features
        "weight_by": "salience"   # weight per provenance
    }
) -> UncertaintyCarrier         # mean, band_90, confidence, basis, evidence_event_ids
```

Lives next to the existing PTV toolkit (`server/ptv_toolkit/`) — same JSON contract, same handoff format. The 8B probe stays on routing; this primitive is **deterministic**.

---

## 4. Cohort-scale: hierarchical Bayes over 100k PTVs

### 4.1 Model sketch
Per-patient parameters drawn from population hyperpriors:

\[
\theta_i \sim \mathrm{Normal}(\mu, \sigma^2)
\]
\[
\mu \sim \mathrm{Normal}(0, 1),\quad \sigma \sim \mathrm{HalfNormal}(1)
\]

\(\theta_i\) is the patient-specific log-odds of (e.g.) 30-day flare conditional on a feature vector built from `code_index`, PRO trajectories, and MKG-derived covariates. Per-patient updates remain conjugate-fast; **population learning** of \((\mu,\sigma)\) is where we spend GPU.

### 4.2 Why hierarchical wins for FORWARD/RISE
- **Borrows strength**: a sparse-data patient inherits population behavior gracefully.
- **Subgroup-aware**: cohorts (RA + SLE + JIA + age strata) can each get their own \(\mu\) without losing global regularization.
- **Equity-friendly**: differential calibration becomes auditable, not hidden.

### 4.3 Inference ladder (cheapest first)
1. **Closed-form conjugate** (Beta/Gamma/Normal–Normal) — runs on 8B path; default for the pilot.
2. **Laplace approximation** at the MAP — fast for moderate models; good when conjugacy breaks.
3. **Variational Inference (VI / ADVI)** in PyMC or NumPyro — scales to 100k easily; principled posteriors.
4. **MCMC (NUTS)** on a stratified subsample — gold-standard sanity check; never on the full cohort in real time.

The 70B reviewer's job is **(2)–(4) when (1) flags a regime change** (e.g. posterior bands widening, evidence outside MKG support).

### 4.4 PTV as a Bayesian network
Connascence edges (`same_encounter`, `caused_by`, `in_workup_for`, `temporal`) are already a typed dependency graph. Treat each event as a node-variable; existing `bfs_expand` becomes the **message-passing scaffold**. We do not need a separate inference engine — the toolkit already walks the right neighborhoods.

---

## 5. Integration into the current stack

### 5.1 Where each piece lives
| Layer | Today | Bayesian addition |
|---|---|---|
| `server/eoh/code_index_ops.py` | flat per-code chronology | unchanged — feature substrate |
| `server/ptv_toolkit/tools.py` | code/temporal/semantic/bfs/get | **+ `bayesian_update_uc`** |
| `server/ptv_toolkit/agent.py` | PLAN-first JSON loop | new `route: "bayesian_update"` |
| `server/eoh/eoh_plans.py` | reasoning routes | flare/progression/taper plans gain a posterior step |
| MKG | retrieval-only today | **+ priors lookup** (population base rates, conditional risks) |
| OGrE | enrichment writer | **+ refresh hook** to recompute UCs when new evidence lands |

### 5.2 Three-agent pipeline (fits perfectly)
- **8B probe (Lucifer)** — routes the question, gathers evidence ids, runs the closed-form `bayesian_update_uc` call when the route is `bayesian_update`. Cheap, parallelizable per patient.
- **70B gap (2×4090)** — reviews the working set, decides whether to escalate to Laplace/VI, calls MKG for stronger priors, requests OGrE re-runs.
- **70B report** — writes the answer + DerivationChain; cites posterior mean/band and the evidence ids that produced them.

### 5.3 Handoff contract additions
Extend `ptv_toolkit.handoff.v1` with an optional `posteriors` block:

```json
"posteriors": [
  {
    "hypothesis_id": "flare_30d",
    "uc": {
      "point_estimate": 0.357,
      "band_90": [0.166, 0.573],
      "confidence": 0.71,
      "evidence_event_ids": [...],
      "prior": {"family": "beta", "alpha": 2.0, "beta": 8.0},
      "method": "beta_conjugate_v1"
    }
  }
]
```

The 70B gap agent treats this as a **starting belief**, not a final answer.

---

## 6. Pilot plan (FORWARD/RISE, 5 patients → 50)

### Phase 0 — week 0 (already done)
- Indexed PTV + toolkit + harness (this branch).
- UC fields shipped on synthetic exemplars.

### Phase 1 — weeks 1–2: closed-form Bayes for one hypothesis
- Implement `bayesian_update_uc` with Beta–Bernoulli only.
- One hypothesis: **30-day flare risk**.
- Evidence rules drawn from `code_index` (CRP, ESR, PRO deltas, med changes).
- Prior: weak `Beta(2,8)` per patient, **no MKG yet**.
- Acceptance: harness gains a Bayesian question class; transcripts attach `posteriors[]`.

### Phase 2 — weeks 3–4: MKG-informed priors
- MKG returns base rates by ICD family + age stratum + sex.
- Prior becomes \(\mathrm{Beta}(\alpha_{pop},\beta_{pop})\) sized to a configurable equivalent-sample count.
- Acceptance: posteriors shift sensibly when prior changes; calibration plot on synthetic + 5 real graphs.

### Phase 3 — weeks 5–6: hierarchical pilot
- 50 PTVs (mix synthetic + real). VI in NumPyro on 1×4090.
- Population \(\mu,\sigma\) for flare; per-patient posteriors borrow strength.
- Acceptance: leave-one-out calibration ≥ baseline; band coverage close to nominal 90%.

### Phase 4 — weeks 7–8: Kaleb / Andras handoff
- One hypothesis class is enough to demo on the 5 + 50 packages.
- Add second hypothesis (**progression-3-month**) as a parallel module.
- Acceptance: report PDF includes posterior mean/band per patient with the evidence ids cited.

---

## 7. Cohort plan (study scale, 1k → 100k)

### 7.1 What scales as-is
- **Per-patient conjugate updates**: linear in events; trivial.
- **VI on 100k**: feasible on 1–2 GPUs nightly; daily incremental updates from new events.
- **`code_index` features**: already O(1) per code.

### 7.2 What needs care
- **Prior drift**: hyperpriors must be versioned and rebuilt on a cadence (monthly?) with provenance.
- **Subgroup fairness audits**: stratify calibration by age, sex, race, payer, geography.
- **Privacy of population stats**: every prior we ship is a population statistic — log lineage, never per-patient leakage.
- **Concept drift**: register a monitor (PSI / KL on posterior summaries) and trigger refits.

### 7.3 OGrE as the closer
When new evidence lands for a patient:
1. `code_index_ops.upsert_event_in_code_index(...)` (already wired).
2. `ptv_toolkit.bayesian_update_uc(...)` recomputes affected hypotheses.
3. UC delta written into the graph with `discovered_by: ["ogre:bayes_v1"]`.
4. If posterior band crossed an action threshold, escalate to 70B gap.

This is the same OGrE loop we already run, with a new writer.

---

## 8. Risks and how we mitigate

| Risk | Mitigation |
|---|---|
| Wrong likelihood specs → confidently wrong posteriors | Likelihood definitions live in versioned YAML/JSON; every UC carries the spec hash in `basis` |
| Prior gaming ("dial to confidence") | Priors are MKG-derived or fixed weak; manual overrides require a `discovered_by: clinician` and a reason |
| Calibration drift over time | Nightly calibration job; band coverage logged per cohort |
| 8B confabulation around UCs | Posteriors are **deterministic Python**, not LLM output; agents can only call the tool, not invent the math |
| Conditional independence violations on PTV | Start with strong factorization; test with held-out events; escalate to BN/VI when violated |
| Patient privacy in population stats | Aggregate-only priors; differential-privacy noise budget for any cohort statistic shipped externally |

---

## 9. Acceptance criteria (pilot exit)

- Every UC the report agent emits has: prior spec, evidence id list, posterior mean, 90% CI, method tag, basis hash.
- Calibration on synthetic + 5 real PTVs within ±10% of nominal coverage.
- Latency: per-patient single-hypothesis update < 50 ms (closed form), < 5 s (Laplace), < 30 s (VI single-patient).
- Glass-box: a clinician can ask "what would change your mind?" and the system can list the **k** evidence types whose absence/flip moves the posterior the most (sensitivity analysis on the existing UC).

---

## 10. What this gives FORWARD / RISE

1. **A defensible flare risk number** with an honest band, not a vibe.
2. **An obvious place for PROs** to influence care — they enter as evidence with explicit likelihood weights.
3. **A path from 5 patients to 100k** without changing the public contract: same UCs, better priors, tighter bands.
4. **A disagreement protocol**: when the 70B gap agent's posterior diverges from the 8B's, that disagreement is logged and reviewed — exactly the audit trail partner societies will want.

---

## 11. Next concrete deliverables (this PR or the next)

1. `server/ptv_toolkit/bayes.py` — Beta/Gamma/Normal–Normal conjugate kernels, fully typed, no stochastic deps.
2. `server/ptv_toolkit/tools.py` — register `bayesian_update_uc`.
3. `server/ptv_toolkit/agent.py` — accept `route: "bayesian_update"`; emit `posteriors[]` in `final_answer`.
4. `server/eoh/uc.py` — UC dataclass + serializer that round-trips through the handoff schema.
5. `server/scripts/ptv_toolkit_questions.json` — add 3 Bayesian probes (flare, progression, taper safety).
6. `reports/REPORT_PTV_TOOLKIT.md` — first toolkit report (already pending) gains a Bayesian section.
7. **One-page handout** for Kaleb/Andras explaining why our UCs are now posteriors, not point estimates.

---

*This strategy formalizes what we are already doing in spirit. Nothing about the user-facing contract changes; the math underneath becomes provable instead of plausible.*
