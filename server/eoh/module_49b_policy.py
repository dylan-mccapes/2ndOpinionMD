# server/eoh/module_49b_policy.py
#
# Module 49B — Diagnostic Consistency Sentinel
#
# This encodes the weight and threshold policies described in Appendix F.49B.
# It is deliberately "thin": a governed parameter surface plus pure functions
# that apply those parameters to a single differential snapshot.
#
# Integration points:
#   - Called post-Module 49, once p_base(d), rank_base(d) and evidence_bundle(d)
#     are available.
#   - Downstream modules (9, 11–15, 19, 40–48) can inspect the structured
#     results for escalation, QA and learning.
#
# NOTE: This file does *not* reach into the DB or EHR. It is purely functional
# and should be easy to test offline.

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, List, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Enums for coherence factors and statuses
# ---------------------------------------------------------------------------


class TerrainCoherence(Enum):
    STRONGLY_ALIGNED = auto()
    MILD_MISMATCH = auto()
    MAJOR_MISMATCH = auto()
    IMPOSSIBLE = auto()


class RequiredFeatureState(Enum):
    ALL_PRESENT = auto()
    PARTIAL_MISSING = auto()
    CONTRAINDICATED = auto()


class SuppressionState(Enum):
    NONE = auto()
    SYMBOLIC_SUBJECTIVE = auto()
    SYMBOLIC_OBJECTIVE = auto()
    LABERROR_DEPENDS = auto()
    LABERROR_OVERRULED = auto()


class PsychosomaticState(Enum):
    LOW_PSI = auto()
    HIGH_PSI_SUBJECTIVE = auto()
    HIGH_PSI_OBJECTIVE = auto()


class TemporalPattern(Enum):
    FITS = auto()
    BORDERLINE = auto()
    INCONSISTENT = auto()


class CoherenceStatus(Enum):
    COHERENT = "coherent"
    TERRAIN_CONFLICT = "terrain_conflict"
    SUPPRESSION_CONFLICT = "suppression_conflict"
    EVIDENCE_INSUFFICIENT = "evidence_insufficient"
    CONTRAINDICATED = "contraindicated"


# ---------------------------------------------------------------------------
# Input / Output data structures
# ---------------------------------------------------------------------------


@dataclass
class EvidenceBundleSummary:
    """
    Minimal abstraction of the Module 49 evidence bundle for a diagnosis.

    This is deliberately sparse: upstream code can enrich it later.
    """
    required_present: bool
    has_contraindication: bool
    non_redundant_evidence_nodes: int
    objective_evidence_fraction: float  # 0.0–1.0 fraction of "objective" vs subjective
    safety_critical: bool               # flag if dx is on the safety-critical list


@dataclass
class TerrainSuppressionContext:
    """
    Context view for Module 49B.

    Upstream code is responsible for mapping raw terrain/suppression state
    (Module 11–15, 41–42) into these enums.
    """
    terrain: TerrainCoherence
    required_state: RequiredFeatureState
    suppression_state: SuppressionState
    psychosomatic_state: PsychosomaticState
    temporal_pattern: TemporalPattern
    pause_flag: bool  # whether suppression is currently active


@dataclass
class DiagnosisCandidate49B:
    """
    Single candidate diagnosis entering Module 49B.

    p_base and rank_base come from Module 49 (already calibrated via Module 19).
    """
    code: str
    label: str
    p_base: float
    rank_base: int
    evidence: EvidenceBundleSummary
    context: TerrainSuppressionContext


@dataclass
class CoherenceFactorWeights:
    """
    C_terrain, C_required, C_suppression, C_psycho, C_temporal and overall C(d).
    """
    terrain: float
    required: float
    suppression: float
    psychosomatic: float
    temporal: float
    overall: float


@dataclass
class EscalationTriggers49B:
    """
    Triggers for CriticalOverride / ReviewRequired, surfaced for Modules 9, 14, 19, 40–48.
    """
    critical_override: bool
    review_required: bool
    review_reason: Optional[str] = None


@dataclass
class Diagnosis49BResult:
    """
    Output for each diagnosis after applying Module 49B.
    """
    code: str
    label: str
    p_base: float
    rank_base: int
    p_adj: float
    coherence_status: CoherenceStatus
    factors: CoherenceFactorWeights
    triggers: EscalationTriggers49B


@dataclass
class Differential49BResult:
    """
    Aggregate output for a full differential snapshot.
    """
    diagnoses: List[Diagnosis49BResult]
    # Normalization metadata
    total_p_before: float
    total_p_after: float


# ---------------------------------------------------------------------------
# Governed parameters for 49B (weights & thresholds)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CoherenceParameters49B:
    # Factor weights
    C_terrain_strong: float = 1.2
    C_terrain_mild_mismatch: float = 0.8
    C_terrain_major_mismatch: float = 0.5
    C_terrain_impossible: float = 0.0

    C_required_all_present: float = 1.2
    C_required_partial_missing: float = 0.7
    C_required_contraindicated: float = 0.0

    C_supp_none: float = 1.0
    C_supp_symbolic_subjective: float = 0.6
    C_supp_symbolic_objective: float = 1.0
    C_supp_laberror_depends: float = 0.5
    C_supp_laberror_overruled: float = 1.0

    C_psycho_low_PSI: float = 1.0
    C_psycho_high_PSI_subjective: float = 0.5
    C_psycho_high_PSI_objective: float = 0.9

    C_temp_fit: float = 1.1
    C_temp_borderline: float = 0.9
    C_temp_inconsistent: float = 0.5

    C_min: float = 0.0
    C_max: float = 1.5

    # Status thresholds
    coherent_min_C: float = 0.8
    terrain_conflict_max_C_terrain: float = 0.6
    evidence_insufficient_max_p_base: float = 0.10
    evidence_insufficient_min_nodes: int = 2
    p_base_floor_for_contra_flag: float = 0.15
    suppression_conflict_obj_fraction: float = 0.60  # ≥60% objective evidence

    # Escalation thresholds
    critical_p_base_min: float = 0.30
    critical_p_adj_alt: float = 0.20
    review_p_adj_terrain: float = 0.20
    review_p_adj_supp_low_min: float = 0.10
    review_p_adj_supp_low_max: float = 0.20  # [min, max)
    review_p_base_contra: float = 0.15


DEFAULT_PARAMS_49B = CoherenceParameters49B()


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def _factor_for_terrain(params: CoherenceParameters49B, t: TerrainCoherence) -> float:
    if t == TerrainCoherence.STRONGLY_ALIGNED:
        return params.C_terrain_strong
    if t == TerrainCoherence.MILD_MISMATCH:
        return params.C_terrain_mild_mismatch
    if t == TerrainCoherence.MAJOR_MISMATCH:
        return params.C_terrain_major_mismatch
    if t == TerrainCoherence.IMPOSSIBLE:
        return params.C_terrain_impossible
    return 1.0


def _factor_for_required(params: CoherenceParameters49B, r: RequiredFeatureState) -> float:
    if r == RequiredFeatureState.ALL_PRESENT:
        return params.C_required_all_present
    if r == RequiredFeatureState.PARTIAL_MISSING:
        return params.C_required_partial_missing
    if r == RequiredFeatureState.CONTRAINDICATED:
        return params.C_required_contraindicated
    return 1.0


def _factor_for_suppression(params: CoherenceParameters49B, s: SuppressionState) -> float:
    if s == SuppressionState.NONE:
        return params.C_supp_none
    if s == SuppressionState.SYMBOLIC_SUBJECTIVE:
        return params.C_supp_symbolic_subjective
    if s == SuppressionState.SYMBOLIC_OBJECTIVE:
        return params.C_supp_symbolic_objective
    if s == SuppressionState.LABERROR_DEPENDS:
        return params.C_supp_laberror_depends
    if s == SuppressionState.LABERROR_OVERRULED:
        return params.C_supp_laberror_overruled
    return 1.0


def _factor_for_psycho(params: CoherenceParameters49B, p: PsychosomaticState) -> float:
    if p == PsychosomaticState.LOW_PSI:
        return params.C_psycho_low_PSI
    if p == PsychosomaticState.HIGH_PSI_SUBJECTIVE:
        return params.C_psycho_high_PSI_subjective
    if p == PsychosomaticState.HIGH_PSI_OBJECTIVE:
        return params.C_psycho_high_PSI_objective
    return 1.0


def _factor_for_temporal(params: CoherenceParameters49B, t: TemporalPattern) -> float:
    if t == TemporalPattern.FITS:
        return params.C_temp_fit
    if t == TemporalPattern.BORDERLINE:
        return params.C_temp_borderline
    if t == TemporalPattern.INCONSISTENT:
        return params.C_temp_inconsistent
    return 1.0


def _clamp(params: CoherenceParameters49B, value: float) -> float:
    return max(params.C_min, min(params.C_max, value))


def _determine_status(
    params: CoherenceParameters49B,
    candidate: DiagnosisCandidate49B,
    factors: CoherenceFactorWeights,
) -> CoherenceStatus:
    e = candidate.evidence
    ctx = candidate.context

    # Hard contraindications collapse to contraindicated
    if e.has_contraindication or factors.overall <= params.C_min:
        return CoherenceStatus.CONTRAINDICATED

    # Evidence insufficient
    if (
        candidate.p_base < params.evidence_insufficient_max_p_base
        and e.non_redundant_evidence_nodes < params.evidence_insufficient_min_nodes
    ):
        return CoherenceStatus.EVIDENCE_INSUFFICIENT

    # Suppression conflict — active suppression + strong objective evidence
    if (
        ctx.pause_flag
        and e.objective_evidence_fraction >= params.suppression_conflict_obj_fraction
    ):
        return CoherenceStatus.SUPPRESSION_CONFLICT

    # Terrain conflict — terrain factor low but required strong / no contraindication
    if (
        factors.terrain <= params.terrain_conflict_max_C_terrain
        and candidate.context.required_state == RequiredFeatureState.ALL_PRESENT
    ):
        return CoherenceStatus.TERRAIN_CONFLICT

    # Coherent if overall multiplier is high and no required-missing/contraindication
    if (
        factors.overall >= params.coherent_min_C
        and candidate.context.required_state == RequiredFeatureState.ALL_PRESENT
    ):
        return CoherenceStatus.COHERENT

    # Default fallback (soft “evidence_insufficient” is safest)
    return CoherenceStatus.EVIDENCE_INSUFFICIENT


def _compute_factors(
    params: CoherenceParameters49B,
    candidate: DiagnosisCandidate49B,
) -> CoherenceFactorWeights:
    t = _factor_for_terrain(params, candidate.context.terrain)
    r = _factor_for_required(params, candidate.context.required_state)
    s = _factor_for_suppression(params, candidate.context.suppression_state)
    p = _factor_for_psycho(params, candidate.context.psychosomatic_state)
    tp = _factor_for_temporal(params, candidate.context.temporal_pattern)

    overall = t * r * s * p * tp

    # If any factor is zero, enforce overall = 0
    if 0.0 in (t, r, s, p, tp):
        overall = 0.0

    overall = _clamp(params, overall)

    return CoherenceFactorWeights(
        terrain=t,
        required=r,
        suppression=s,
        psychosomatic=p,
        temporal=tp,
        overall=overall,
    )


def _compute_triggers(
    params: CoherenceParameters49B,
    candidate: DiagnosisCandidate49B,
    p_adj: float,
    status: CoherenceStatus,
) -> EscalationTriggers49B:
    e = candidate.evidence
    critical_override = False
    review_required = False
    review_reason: Optional[str] = None

    # A. CriticalOverride suggestion for safety-critical diagnoses
    if e.safety_critical:
        if (
            candidate.p_base >= params.critical_p_base_min
            and candidate.context.terrain in (TerrainCoherence.STRONGLY_ALIGNED, TerrainCoherence.MILD_MISMATCH)
        ):
            # We *approximate* C(d) ≥ 0.9 via terrain alignment; actual C(d) is visible upstream.
            critical_override = True
        elif candidate.rank_base == 1 and p_adj >= params.critical_p_adj_alt:
            critical_override = True

    # B. ReviewRequired triggers
    if status == CoherenceStatus.TERRAIN_CONFLICT and p_adj >= params.review_p_adj_terrain:
        review_required = True
        review_reason = "terrain_conflict"
    elif status == CoherenceStatus.SUPPRESSION_CONFLICT and (
        params.review_p_adj_supp_low_min <= p_adj < params.review_p_adj_supp_low_max
    ):
        review_required = True
        review_reason = "suppression_conflict"
    elif status == CoherenceStatus.CONTRAINDICATED and candidate.p_base >= params.review_p_base_contra:
        review_required = True
        review_reason = "contraindicated_high_p_base"

    return EscalationTriggers49B(
        critical_override=critical_override,
        review_required=review_required,
        review_reason=review_reason,
    )


# ---------------------------------------------------------------------------
# Public API: apply 49B to a differential snapshot
# ---------------------------------------------------------------------------


def apply_49b_to_differential(
    candidates: Sequence[DiagnosisCandidate49B],
    params: CoherenceParameters49B = DEFAULT_PARAMS_49B,
) -> Differential49BResult:
    """
    Apply Module 49B coherence logic to a single differential snapshot.

    Steps:
      1) Compute C(d) factors per diagnosis.
      2) Compute p_adj_raw(d) = p_base(d) * C(d).
      3) Normalize p_adj_raw across candidates (sum ≤ 1, preserving ordering).
      4) Assign coherence_status and escalation triggers.
    """
    if not candidates:
        return Differential49BResult(
            diagnoses=[],
            total_p_before=0.0,
            total_p_after=0.0,
        )

    total_p_before = float(sum(max(0.0, c.p_base) for c in candidates))

    # 1–2) Raw adjusted probabilities
    tmp: List[Tuple[DiagnosisCandidate49B, CoherenceFactorWeights, float]] = []
    for c in candidates:
        factors = _compute_factors(params, c)
        p_adj_raw = max(0.0, c.p_base) * factors.overall
        tmp.append((c, factors, p_adj_raw))

    raw_sum = float(sum(p for _, _, p in tmp)) or 1.0

    # 3) Normalize
    results: List[Diagnosis49BResult] = []
    for c, factors, p_raw in tmp:
        p_adj = p_raw / raw_sum
        status = _determine_status(params, c, factors)
        triggers = _compute_triggers(params, c, p_adj, status)

        results.append(
            Diagnosis49BResult(
                code=c.code,
                label=c.label,
                p_base=c.p_base,
                rank_base=c.rank_base,
                p_adj=p_adj,
                coherence_status=status,
                factors=factors,
                triggers=triggers,
            )
        )

    total_p_after = float(sum(r.p_adj for r in results))

    # Keep results ordered by p_adj descending
    results.sort(key=lambda r: r.p_adj, reverse=True)

    return Differential49BResult(
        diagnoses=results,
        total_p_before=total_p_before,
        total_p_after=total_p_after,
    )

MODULE_TEXT = """
F.49B — Diagnostic Consistency Sentinel Weight & Threshold Policy (Module 49B)

Purpose
Define how Module 49B converts terrain, suppression, and evidence checks into quantitative score adjustments and deterministic escalation triggers for the differential engine (Module 49).

Governance Hooks H.2 (Suppression Logic), H.5.4 (Stability Band), H.9 (Probability classes), F.9 (Reflex Suppression), F.19 (Calibration/QA), Module 40 (weight governance).
Version Control DiagSentinel_v1.0 → checksum in L.3
One-Liner → Turns terrain + suppression context into governed score adjustments and safety overrides for differential diagnosis.

⸻

F.49B.1 Normalized Inputs

Module 49B assumes Module 49 outputs for each diagnosis d:
	•	p_base(d) – calibrated probability ∈ [0,1], via Module 19.
	•	rank_base(d) – ordinal rank (1 = highest).
	•	evidence_bundle(d) – list of required/typical/compatible/contradictory findings as defined in the MKG.

And consumes:
	•	Terrain: stackLevel, stabilityBand, cbm_active, drift_flags.
	•	Suppression: pauseFlag, pauseReason, TTL state (F.9).
	•	Psychosomatic: psi, persona_flags[] (F.4).

⸻

F.49B.2 Coherence Weight Matrix

For each candidate diagnosis d, 49B computes a coherence multiplier:

C(d) = C_{\text{terrain}} \times C_{\text{required}} \times C_{\text{suppression}} \times C_{\text{psycho}} \times C_{\text{temporal}}

Each factor takes discrete values:

Factor	State	Multiplier
Terrain (Band/Stack vs severity)	Strongly aligned (expected band ±1, stack compatible)	1.2
	Mild mismatch (±2 bands or comorbidity explains gap)	0.8
	Major mismatch (severity clearly inconsistent)	0.5
	Impossible (disease severity incompatible with observed band)	0.0
Required features	All required present; no absolute contraindications	1.2
	≥1 required missing but partial analogs present	0.7
	Any hard contraindication present	0.0
Suppression context	No suppression active	1.0
	pauseReason = SymbolicFlare and evidence is mostly subjective	0.6
	pauseReason = SymbolicFlare but strong objective evidence supports d	1.0 (no down-weight)
	pauseReason = LabError and d relies heavily on that lab	0.5
	pauseReason = LabError but repeat objective data support d	1.0
Psychosomatic (PSI/persona)	PSI < 2, no high-risk personas	1.0
	PSI ≥ 2 with #Catastrophizing / #Overidentification and only subjective features support d	0.5
	PSI ≥ 2 but objective findings dominate	0.9
Temporal pattern	Onset/trajectory fits expected course	1.1
	Borderline timing	0.9
	Temporal course inconsistent (e.g., acute dx with years-long stability)	0.5

Default weight bounds
	•	C(d) is clamped to [0.0, 1.5].
	•	For any factor = 0.0 → C(d) = 0.0 (diagnosis effectively contraindicated).

Governance: weight cells are maintained under Module 40; modifications require QA + Clinical Safety approval and are logged to L.3.

⸻

F.49B.3 Adjusted Probability & Status Thresholds

49B computes:

p_{\text{adj}}(d) = \operatorname{normalize}(p_{\text{base}}(d) \times C(d))

Normalization preserves relative ordering and rescales to sum ≤ 1 across candidates.

49B then sets coherence status using thresholds on C(d) and evidence bundle structure:

Status	Criteria (all must be satisfied)
coherent	C(d) ≥ 0.8 and no required-missing or contraindication flags.
terrain_conflict	C_terrain ≤ 0.6, but C_required ≥ 0.8 and no contraindication.
suppression_conflict	Active pauseFlag and objective evidence for d (labs/imaging/guidelines) contributes ≥60% of its evidence score while suppression is driven by psychosomatic or lab QA reasons.
evidence_insufficient	p_base(d) < 0.1 and <2 non-redundant evidence nodes; or no required/typical features present.
contraindicated	Any hard contraindication present OR C(d) = 0.

If multiple statuses apply, priority order:
	1.	contraindicated
	2.	suppression_conflict
	3.	terrain_conflict
	4.	evidence_insufficient
	5.	coherent

⸻

F.49B.4 Escalation & Override Thresholds

49B may generate governed intervention triggers:

A. CriticalOverride suggestion (to Module 9 / 41 / 42)
Trigger when both:
	1.	Diagnosis d* is safety-critical (ACS, PE, sepsis, stroke, etc.; governed list under Module 40).
	2.	Either:
	•	p_base(d*) ≥ 0.30 and C(d*) ≥ 0.9, or
	•	rank_base(d*) = 1 and p_adj(d*) ≥ 0.20.

And suppression_conflict is active.

Action:
	•	Emit CriticalOverride candidate to Module 9 (Reflex Suppression Core).
	•	Log SuppressionUnsafe event to Module 41.
	•	Trigger Module 42 with type Treatment-Critical.

B. ReviewRequired signal (non-critical conflicts)
Trigger when any of:
	•	terrain_conflict and p_adj(d) ≥ 0.20.
	•	suppression_conflict and p_adj(d) ∈ [0.10, 0.20).
	•	contraindicated on a diagnosis with p_base(d) ≥ 0.15.

Action:
	•	Emit Flag / DetectedIssue for clinician review (Tier 2 escalation via Module 14).

⸻

F.49B.5 QA & Drift Thresholds

Module 19 monitors 49B-specific performance:
	•	Missed-coherence rate: fraction of confirmed diagnoses where 49B set terrain_conflict or contraindicated but 49C later confirms the diagnosis.
	•	Over-penalization rate: average relative drop (p_adj - p_base) / p_base for eventually-confirmed diagnoses.

Drift triggers:
	•	If missed-coherence or over-penalization rate exceeds 10% over 3 months vs baseline, emit qa_feedback and route to Module 48 for 49B weight recalibration.

⸻

F.49B.6 Cross-References
	•	Module 49 (base scoring and evidence bundles).
	•	Module 11 / F.5 / F.9 (Band, Stack, suppression TTL).
	•	Module 41 (suppression audit trail).
	•	Module 42 (intervention loop).
	•	Module 48 (learning kernel).
"""