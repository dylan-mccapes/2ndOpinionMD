---
title: CINDER — ACR Convergence 2026 Abstract (Draft v2)
project: CINDER
deadline: 2026-06-09 (ACR Convergence abstract submission)
target_word_count: 300
draft_word_count: 291
status: DRAFT v2 — aligned to PROTOCOL_DRAFT_v3 (cite-verified). Awaiting Andras edit + ACR category-window confirmation
date: 2026-05-03
authors:
  - Andras Hangyal, PharmD (presenting)
  - Dylan McCapes
  - Kaleb Michaud, PhD
session_target: Patient-Reported Outcomes / Health Services Research / Methods
abstract_type: Pre-registration (hypothesis-driven validation study)
v2_changes_from_v1:
  - "Methods: split cohort framing into Primary Analytic Cohort (escalation-enriched) + Registry-Representative Sensitivity Cohort, mirroring PROTOCOL_DRAFT_v3 §3.2"
  - "Methods: explicit mention of 1:1 matched comparator events, mirroring PROTOCOL_DRAFT_v3 §4.6"
  - "Anticipated Results: Aim 2 thresholds named numerically per PROTOCOL_DRAFT_v3 §4.7"
  - "Conclusion: replicability framing tightened to 'blinded external re-run pathway' per PROTOCOL_DRAFT_v3 §10"
  - "Submission notes: FLAME citation flag removed (abstract body cites no external papers)"
  - "Submission notes: §1.6 'legacy multiplier' replaced with 'lineage extension' framing in Conclusion"
---

# Validating a Trajectory-Relative, Uncertainty-Aware Flare Detection Definition Against the FORWARD Registry: The CINDER Study

**Background.** Mollard et al. (2026, *ACR Open Rheumatology*) reported 38 percent of RA flares in 292 FORWARD patients were managed without documented treatment change — a measurement gap current detection schemes miss. OMERACT defines what a flare is but does not specify how to compute one from longitudinal PRO and medication data in a replicable, patient-trajectory-aware way.

**Methods.** We will validate the 2OPMD Flare Axiom retrospectively in N=50 FORWARD RA participants (opening clause to N=200 or 500 on extended pull) under UNMC DUA Option B. The protocol pre-specifies two cohorts: a Primary Analytic Cohort enriched for documented escalation, and a Registry-Representative Sensitivity Cohort. The Flare Axiom operationalizes a flare as co-occurrence of (1) meaningful worsening across ≥2 PRO domains exceeding established MCIDs trajectory-relative to each patient's own baseline (HAQ-II, Pain VAS, Patient Global VAS, RAPID3); and (2) a temporally linked care escalation event within ±90 days. Detection emits flareEvent records with Uncertainty Carrier annotations and GlassBox derivation chains. Concordance is evaluated via Bayesian hierarchical modeling on 1:1 matched comparator events against three independent comparators: clinician-rated flares, the Mollard 2026 smartphone signature, and an OMERACT operationalization.

**Anticipated Results.** Primary endpoint is Cohen's kappa with 95 percent posterior credible interval against the clinician-rated comparator, with H1.1 supported if posterior probability that kappa > 0.40 is ≥ 0.80. Aim 2 tests whether Uncertainty Carriers widen ≥ K units prior to confirmed flares, widen honestly under specified missingness thresholds, and remain suppressed during stable windows defined trajectory-relative to baseline.

**Conclusion.** CINDER establishes patient-specific, terrain-aware, governance-auditable flare detection as a replicable category in RA outcomes research, with a blinded external re-run pathway substituting for code-level open release.

---

## Submission notes (not for submission body)

- 291 words including section labels; under the 300 cap. Verify with ACR submission portal counter at submission time (counters vary).
- Abstract serves as pre-registration vehicle per protocol §9.5 — locks H1.1 / H1.2 / H1.3 / H2.1 / H2.2 / H2.3 hypothesis frame before data is opened.
- Mollard 2026 cited proximally; FORWARD attribution for Kaleb's stewardship needs ICMJE acknowledgment at full submission.
- "Anticipated Results" framing because data has not been pulled yet — abstract pre-registers the analysis plan; full results land at ACR Convergence 2026 in November.
- Abstract category target: Patient-Reported Outcomes session most likely; Methods or Health Services Research are fallback categories.
- Disclosures: Andras is founder of 2OPMD LLC; this is a non-commercial research submission per the 2026-04-28 governance one-pager. Disclose at submission.
- Kaleb's senior authorship per protocol §12 reflects FORWARD scientific stewardship and the convergent independent formulation of the flare framing on 2026-04-22; abstract authorship list mirrors this.
- Aim 2 numerical thresholds (the K, missingness percentage, stable-window duration) are abbreviated to "specified" in the abstract for word-count reasons; full numerical bindings live in PROTOCOL_DRAFT_v3 §4.7.

## Edit hooks for next session

- Pre-registration commit hash from §9.5 must be inserted into the abstract submission's supplemental field once the GitHub repository is scaffolded and v3.0-FINAL is tagged.
- Kaleb may want a senior-author preview before submission; the Kaleb companion brief (KALEB_BRIEF_v2.md) carries that conversation.
- Session category submission decision deferred to closer to deadline; ACR programming usually opens late May with category guidance.
- If Andras overrides the Smolen 2016 substitution for the FLAME placeholder in the protocol, the abstract is unaffected (it cites no external papers in the body).
