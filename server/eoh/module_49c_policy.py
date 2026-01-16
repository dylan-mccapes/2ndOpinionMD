# server/eoh/module_49c_policy.py
#
# Module 49C — Diagnostic Update Reactor
#
# Encodes the labeling, learning and governance thresholds from Appendix F.49C.
# This module does NOT directly change production weights; it produces
# structured "LearningProposal" and performance labels for Modules 19, 40, 48.
#

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Sequence


# ---------------------------------------------------------------------------
# Enums and core types
# ---------------------------------------------------------------------------


class EventConfidence(Enum):
    LOW = auto()
    MEDIUM = auto()
    HIGH = auto()


class DiagnosticOutcome(Enum):
    CONFIRMED = auto()
    RULED_OUT = auto()
    REVISED = auto()
    STAGE_CHANGE = auto()


class PerformanceLabel(Enum):
    CORRECT_PRIMARY = "correct_primary"
    CORRECT_TOP3 = "correct_top3"
    UNDER_RANKED = "under_ranked"
    MISSED = "missed"
    INCORRECT_HIGH_CONFIDENCE = "incorrect_high_confidence"
    INCORRECT_LOW_CONFIDENCE = "incorrect_low_confidence"


@dataclass
class CandidateSnapshot:
    """
    Snapshot of a single diagnosis from the latest 49/49B output
    before the real-world outcome was known.
    """
    code: str
    label: str
    p_adj: float
    rank_adj: int


@dataclass
class DifferentialSnapshot:
    """
    Snapshot of a full differential (post-49B) at a decision time.
    """
    candidates: List[CandidateSnapshot]


@dataclass
class DiagnosticEvent:
    """
    Real-world diagnostic outcome event that 49C consumes.
    """
    patient_id: str
    diagnosis_code: str      # d*
    outcome: DiagnosticOutcome
    confidence: EventConfidence
    safety_critical: bool
    # Optional metadata for terrain/suppression updates (not used in core label logic)
    ts_iso: Optional[str] = None


@dataclass
class PerformanceLabelResult:
    """
    Per-case performance label of the diagnostic engine for d*.
    """
    patient_id: str
    diagnosis_code: str
    label: PerformanceLabel
    confidence: EventConfidence
    safety_critical: bool
    p_adj_star: float
    rank_adj_star: Optional[int]
    competitor_max_p_adj: float


# ---------------------------------------------------------------------------
# Governed thresholds
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Thresholds49C:
    # Performance labels
    p_adj_primary_min: float = 0.50
    p_adj_top3_min: float = 0.30
    p_adj_under_ranked_floor: float = 0.10
    p_adj_competitor_min: float = 0.40
    p_adj_missed_max: float = 0.10
    p_adj_incorrect_high_min: float = 0.50
    p_adj_all_max_low: float = 0.50

    # Terrain/suppression update thresholds
    cbm_recalibration_min_days: int = 30
    oversupp_window_days: int = 30
    oversupp_conflict_fraction: float = 0.20

    # Learning / update thresholds
    missed_plus_high_conf_err_pct: float = 0.15
    incorrect_high_conf_pct: float = 0.05
    under_ranked_bias_delta_pct: float = 0.10
    rolling_window_days_learning: int = 90

    # CAPA / governance
    capa_incorrect_high_conf_pct: float = 0.10
    missed_rr_threshold: float = 1.25
    critical_dx_event_count: int = 3
    critical_dx_window_days: int = 30


DEFAULT_THRESHOLDS_49C = Thresholds49C()


# ---------------------------------------------------------------------------
# Core labeler
# ---------------------------------------------------------------------------


def _find_candidate(snapshot: DifferentialSnapshot, code: str) -> Optional[CandidateSnapshot]:
    for c in snapshot.candidates:
        if c.code == code:
            return c
    return None


def label_single_event(
    snapshot: DifferentialSnapshot,
    event: DiagnosticEvent,
    thresholds: Thresholds49C = DEFAULT_THRESHOLDS_49C,
) -> Optional[PerformanceLabelResult]:
    """
    Label a single diagnostic outcome event using 49C rules.

    Only CONFIRMED diagnoses with MEDIUM/HIGH confidence generate labels
    that are eligible for weight/threshold learning.
    """
    if event.outcome != DiagnosticOutcome.CONFIRMED:
        return None

    if event.confidence not in (EventConfidence.MEDIUM, EventConfidence.HIGH):
        # low-confidence events are logged but not used for learning
        return None

    d_star = _find_candidate(snapshot, event.diagnosis_code)
    competitors = [c for c in snapshot.candidates if c.code != event.diagnosis_code]
    competitor_max_p = max((c.p_adj for c in competitors), default=0.0)

    if d_star is None:
        # Diagnosis missing from candidate list
        label = PerformanceLabel.MISSED
        p_adj_star = 0.0
        rank_star = None
    else:
        p_adj_star = d_star.p_adj
        rank_star = d_star.rank_adj

        # correct_primary
        if (
            d_star.rank_adj == 1
            and p_adj_star >= thresholds.p_adj_primary_min
        ):
            label = PerformanceLabel.CORRECT_PRIMARY

        # correct_top3
        elif (
            d_star.rank_adj in (2, 3)
            and p_adj_star >= thresholds.p_adj_top3_min
        ):
            label = PerformanceLabel.CORRECT_TOP3

        # under_ranked
        elif (
            p_adj_star >= thresholds.p_adj_under_ranked_floor
            and competitor_max_p >= thresholds.p_adj_competitor_min
        ):
            label = PerformanceLabel.UNDER_RANKED

        # missed (weak presence or too low)
        elif p_adj_star < thresholds.p_adj_missed_max:
            label = PerformanceLabel.MISSED

        # incorrect_high_confidence
        elif competitor_max_p >= thresholds.p_adj_incorrect_high_min:
            label = PerformanceLabel.INCORRECT_HIGH_CONFIDENCE

        else:
            # incorrect_low_confidence
            label = PerformanceLabel.INCORRECT_LOW_CONFIDENCE

    return PerformanceLabelResult(
        patient_id=event.patient_id,
        diagnosis_code=event.diagnosis_code,
        label=label,
        confidence=event.confidence,
        safety_critical=event.safety_critical,
        p_adj_star=p_adj_star,
        rank_adj_star=rank_star,
        competitor_max_p_adj=competitor_max_p,
    )


# ---------------------------------------------------------------------------
# Batch aggregation skeletons (for Module 19 / 48)
# ---------------------------------------------------------------------------


@dataclass
class LabelAggregateStats:
    """
    Aggregate counts used by Module 19 / 48 for QA and learning decisions.
    """
    n_total: int = 0
    n_correct_primary: int = 0
    n_correct_top3: int = 0
    n_under_ranked: int = 0
    n_missed: int = 0
    n_incorrect_high_conf: int = 0
    n_incorrect_low_conf: int = 0

    def update(self, label: PerformanceLabel) -> None:
        self.n_total += 1
        if label == PerformanceLabel.CORRECT_PRIMARY:
            self.n_correct_primary += 1
        elif label == PerformanceLabel.CORRECT_TOP3:
            self.n_correct_top3 += 1
        elif label == PerformanceLabel.UNDER_RANKED:
            self.n_under_ranked += 1
        elif label == PerformanceLabel.MISSED:
            self.n_missed += 1
        elif label == PerformanceLabel.INCORRECT_HIGH_CONFIDENCE:
            self.n_incorrect_high_conf += 1
        elif label == PerformanceLabel.INCORRECT_LOW_CONFIDENCE:
            self.n_incorrect_low_conf += 1


@dataclass
class LearningProposal:
    """
    Placeholder for downstream learning proposals to Module 19 / 48 / 40.

    This is intentionally generic; you can extend `details` with structured
    per-diagnosis deltas once you wire this into your analytics pipeline.
    """
    scope: str          # e.g. "diagnosis:M32.1", "cohort:female_RA"
    reason: str         # e.g. "missed_plus_high_conf_err_pct_exceeded"
    details: Dict[str, float]


def derive_learning_proposals(
    stats_by_scope: Dict[str, LabelAggregateStats],
    thresholds: Thresholds49C = DEFAULT_THRESHOLDS_49C,
) -> List[LearningProposal]:
    """
    Given aggregate stats per diagnosis / cohort, emit LearningProposals when
    thresholds are crossed. This does not change weights; it just surfaces signals.
    """
    proposals: List[LearningProposal] = []

    for scope, stats in stats_by_scope.items():
        if stats.n_total == 0:
            continue

        missed_plus_high = (
            stats.n_missed + stats.n_incorrect_high_conf
        ) / float(stats.n_total)

        incorrect_high_pct = stats.n_incorrect_high_conf / float(stats.n_total)

        # Diagnosis-level failures
        if missed_plus_high >= thresholds.missed_plus_high_conf_err_pct:
            proposals.append(
                LearningProposal(
                    scope=scope,
                    reason="missed_plus_high_conf_err_pct_exceeded",
                    details={
                        "missed_plus_high": missed_plus_high,
                        "threshold": thresholds.missed_plus_high_conf_err_pct,
                    },
                )
            )
        elif incorrect_high_pct >= thresholds.incorrect_high_conf_pct:
            proposals.append(
                LearningProposal(
                    scope=scope,
                    reason="incorrect_high_conf_pct_exceeded",
                    details={
                        "incorrect_high_pct": incorrect_high_pct,
                        "threshold": thresholds.incorrect_high_conf_pct,
                    },
                )
            )

    return proposals

MODULE_TEXT = """
F.49C — Diagnostic Update Reactor Threshold & Learning Policy (Module 49C)

Purpose
Define when and how diagnostic outcome events (confirmed, ruled out, revised) are converted into labels, thresholds, and learning signals for Modules 49, 49B, 11–15, 19, 41–48.

Governance Hooks H.10 (vector & overlay governance), H.12 (calibration & drift standards), F.19 (QA & continuous learning), Appendix L (version lineage).
Version Control DiagUpdateReactor_v1.0 → checksum in L.3
One-Liner → Turns real-world diagnostic outcomes into governed updates for terrain, suppression, and differential priors.

⸻

F.49C.1 Event Confidence Thresholds

Each DiagnosticEvent (confirmed/ruled-out/revised/stage-change) is assigned an event_confidence in {low, medium, high} based on evidence type:

Evidence type	Examples	event_confidence
Gold-standard	Pathology, definitive imaging (e.g. angiography for ACS), surgical findings	high
Strong clinical	Clear multi-modal convergence (labs + imaging + exam + guideline-consistent course)	medium–high
Probabilistic / weak	Symptom-only judgments, ambiguous imaging, provisional diagnoses	low–medium

Policy
	•	Only medium or high confidence events may update weights, priors, or suppression thresholds.
	•	Low-confidence events are logged only and may be used for monitoring but not for parameter updates.

⸻

F.49C.2 Diagnostic Performance Labeling Thresholds

For each high- or medium-confidence confirmed diagnosis d*, 49C looks back at the latest 49/49B output before confirmation and labels performance:

Let:
	•	p_adj(d), rank_adj(d) – post-49B probability/rank at time of decision.
	•	TopK – set of diagnoses with highest p_adj at that time.

Labels:

Label	Criteria
correct_primary	d* in position 1 and p_adj(d*) ≥ 0.50.
correct_top3	d* in positions 2–3 and p_adj(d*) ≥ 0.30.
under_ranked	d* present but rank ≥4 or p_adj(d*) ∈ [0.10, 0.30) while a different diagnosis d' with p_adj(d') ≥ 0.40 is selected.
missed	d* absent from candidate list or p_adj(d*) < 0.10.
incorrect_high_confidence	A different diagnosis d' ≠ d* has p_adj(d') ≥ 0.50.
incorrect_low_confidence	All candidates have p_adj < 0.50 and none match d*.

Thresholds are governed and stored in Module 40; any change is logged to L.3 and QA-reviewed in Module 19.

⸻

F.49C.3 Terrain & Suppression Update Thresholds

When a diagnosis is confirmed with medium/high event_confidence:
	1.	Stack update
	•	If d* is chronic or structural → increment stackLevel and recompute multi-stack burden.
	•	If a prior chronic diagnosis is ruled out → decrement or reclassify stackLevel as appropriate.
	2.	Stability Band / CBM adjustment
	•	If ≥3 consecutive visits or ≥30 days show features consistent with d* and no contradictory evidence, CBM is updated and baseline band recalibrated.
	3.	Suppression policy correction
For the window leading up to confirmation:
	•	If pauseFlag=true and suppression_conflict flags were present from 49B for d* in ≥20% of entries in the last 30 days → mark over-suppression episode for Module 41; candidate for lowering suppression TTL or thresholds.
	•	If suppression correctly masked noise (no flare, d* ruled out) → mark true-positive suppression episode.

⸻

F.49C.4 Learning & Weight Update Thresholds (Modules 49 / 49B)

49C aggregates labels in rolling windows (default 90 days, minimum 100 eligible cases per diagnosis or category):
	1.	Diagnosis-level thresholds

For a given diagnosis d:
	•	If missed + incorrect_high_confidence ≥ 15% of high-confidence events, or
	•	If incorrect_high_confidence alone ≥ 5%,

→ emit qa_feedback_failure for d to Module 19 and route to Module 48 for:
	•	adjusting evidence source weights in Module 49 (SourceWeight matrix),
	•	updating required/typical/contraindicated feature sets and coherence weights in 49B.

	2.	Pattern-level thresholds

Across diseases or cohorts (e.g., by sex, ethnicity, disease family):
	•	If under_ranked rate for a group exceeds 10% above baseline for 3 months → trigger bias/fairness review via Modules 43–45 and Module 48.

⸻

F.49C.5 Safeguards on Model & Policy Updates

49C is not allowed to directly change production weights or thresholds.

Update pipeline:
	1.	49C → emits LearningProposals (candidate weight/threshold changes) with:
	•	affected modules (49, 49B, 11–15, 41–48),
	•	justification (aggregated label stats),
	•	expected direction of change.
	2.	Module 19 evaluates impact on:
	•	AUROC, Brier score, calibration slope/intercept,
	•	suppression over-/under-use metrics.
	3.	Module 48 (Learning Kernel) runs controlled retraining / A/B validation.
	4.	Only after Vector Steward + Clinical Safety Officer approval (H.10, H.18D) do changes propagate into Module 40 and become active.

All approved changes are:
	•	versioned (new ruleset_version / vector_version),
	•	logged to L.3,
	•	referenced in QA and compliance reports.

⸻

F.49C.6 CAPA / Governance Thresholds

49C also decides when diagnostic performance issues escalate into governance lanes:
	•	If any single diagnosis or pathway has incorrect_high_confidence ≥ 10% over 6 months → open CAPA (Module 43).
	•	If any demographic group shows relative risk ≥ 1.25 for missed diagnoses versus reference → generate PreventiveAction (Module 45) and Mitigation (Module 46) proposals.
	•	If safety-critical diagnoses (e.g., sepsis, ACS) accumulate ≥3 missed or incorrect_high_confidence cases in 30 days → trigger Treatment-Critical intervention via Module 42 and log to Module 31 (regulator-facing packet).

⸻

F.49C.7 Cross-References
	•	Module 11–15 (terrain, prognostics, escalation).
	•	Modules 41–47 (suppression audit, CAPA, insights, preventive, mitigation, QA).
	•	Module 48 (learning), Module 19 (QA).
	•	Appendix L (QA Feedback Ledger, version lineage).

⸻

If you want, next step I can compress this into:
	•	a single parameter table you can hand to Dylan/Hedy (all weight/threshold values in one matrix), or
	•	pseudocode snippets for 49B/49C that directly call these policies.
"""