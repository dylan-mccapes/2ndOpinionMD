"""
uc.py — UncertaintyCarrier (UC) dataclass + serializer.

The UC is now a *posterior summary* (per ``reports/STRATEGY_BAYESIAN_PTV_UC_20260423.md``),
not a heuristic point-estimate. It carries:

* ``point_estimate`` — posterior mean.
* ``band_90`` — 90% credible interval (equal-tail percentiles 5%, 95%).
* ``confidence`` — stability score in [0, 1] (1 = sharp posterior, 0 = diffuse).
* ``basis`` — short list of human-readable reasons / spec hash / lineage tags.
* ``evidence_event_ids`` — the conditioning set (the events the update saw).
* ``method`` — kernel tag, e.g. ``beta_conjugate_v1``.
* ``prior`` — full prior spec (family, params, source: 'weak' | 'mkg').
* ``posterior_params`` — full posterior parameters (alpha/beta, mu/sigma, etc.).
* ``spec_hash`` — sha256 of the canonical (prior + likelihood) spec; trace.
* ``hypothesis_id`` — e.g. ``flare_30d``, ``progression_3mo``, ``taper_safety``.

Serialization is round-trip-safe through:

1. The PTV ``derived_metric`` event annotation block (legacy/visual format used by
   ``server/scripts/gen_forward_exemplar.py``).
2. The PTV toolkit handoff schema (``ptv_toolkit.handoff.v1`` ``posteriors[]``
   block, per the strategy doc).

The legacy fields (``point_estimate``, ``band_90``, ``confidence``, ``basis``,
``evidence_event_ids``) keep their previous wire shape so existing renderers and
graphs continue to work; new Bayesian fields ride alongside.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

UC_SCHEMA_VERSION = "uc.v1.bayes"


# --------------------------------------------------------------------------- #
# Confidence-from-band heuristic
# --------------------------------------------------------------------------- #
#
# Confidence is **not** another distribution — it is a 0-to-1 score that summarizes
# how *sharp* the 90% band is on the unit scale. A band that spans 90% of [0,1]
# (i.e. a uniform Beta(1,1)) gives confidence ≈ 0; a band of width 0.05 gives
# confidence ≈ 0.95. This keeps the legacy "low / moderate / high" categorical
# usable while exposing the underlying numeric for the gap agent.
def confidence_from_band(band_90: Sequence[float], *, scale: float = 1.0) -> float:
    """Return a 0..1 confidence summary from band width on the unit scale.

    ``scale`` is the natural support width (1.0 for probabilities, finite for rates).
    """
    if not band_90 or len(band_90) != 2:
        return 0.0
    lo, hi = float(band_90[0]), float(band_90[1])
    if hi < lo:
        lo, hi = hi, lo
    width = max(0.0, hi - lo)
    if scale <= 0:
        return 0.0
    # Inverse-of-width on a 0..1 scale, clipped.
    rel = min(1.0, width / float(scale))
    return round(max(0.0, min(1.0, 1.0 - rel)), 3)


def confidence_label(score: float) -> str:
    """Map numeric confidence to legacy 'low / moderate / high / very_high' bucket."""
    s = float(score)
    if s >= 0.85:
        return "very_high"
    if s >= 0.70:
        return "high"
    if s >= 0.45:
        return "moderate"
    return "low"


# --------------------------------------------------------------------------- #
# Spec hashing (canonical, deterministic)
# --------------------------------------------------------------------------- #

def canonical_spec_hash(spec: Any, *, prefix: str = "uc") -> str:
    """SHA-256 of a canonical-JSON serialization (sorted keys), short hex prefix."""
    blob = json.dumps(spec or {}, sort_keys=True, ensure_ascii=True, default=str)
    digest = hashlib.sha256(blob.encode("utf-8")).hexdigest()
    return f"{prefix}_{digest[:16]}"


# --------------------------------------------------------------------------- #
# UC dataclass
# --------------------------------------------------------------------------- #

@dataclass
class UncertaintyCarrier:
    """Posterior-summary UC for a single hypothesis.

    Numeric fields use Python builtins (no numpy) so this is JSON-safe at rest.
    """
    hypothesis_id: str
    point_estimate: float
    band_90: Tuple[float, float]
    confidence: float                              # numeric in [0, 1]
    basis: List[str] = field(default_factory=list)
    evidence_event_ids: List[str] = field(default_factory=list)
    method: str = "beta_conjugate_v1"
    prior: Dict[str, Any] = field(default_factory=dict)
    posterior_params: Dict[str, Any] = field(default_factory=dict)
    likelihood_summary: Dict[str, Any] = field(default_factory=dict)
    spec_hash: Optional[str] = None
    schema: str = UC_SCHEMA_VERSION
    confidence_label: Optional[str] = None
    notes: Optional[str] = None

    def __post_init__(self) -> None:
        # Normalize band ordering and bounds.
        b = list(self.band_90)
        if len(b) == 2 and b[1] < b[0]:
            b = [b[1], b[0]]
        self.band_90 = (round(float(b[0]), 4), round(float(b[1]), 4))
        self.point_estimate = round(float(self.point_estimate), 4)
        self.confidence = round(float(self.confidence), 3)
        if not self.confidence_label:
            self.confidence_label = confidence_label(self.confidence)

    # ------- serializers ----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        # Tuple → list for JSON.
        d["band_90"] = list(self.band_90)
        return d

    def to_handoff_block(self) -> Dict[str, Any]:
        """Render under the ``ptv_toolkit.handoff.v1 → posteriors[]`` schema.

        Matches the JSON in §5.3 of ``STRATEGY_BAYESIAN_PTV_UC_20260423.md``.
        """
        return {
            "hypothesis_id": self.hypothesis_id,
            "uc": {
                "point_estimate": self.point_estimate,
                "band_90": list(self.band_90),
                "confidence": self.confidence,
                "confidence_label": self.confidence_label,
                "basis": list(self.basis),
                "evidence_event_ids": list(self.evidence_event_ids),
                "prior": dict(self.prior),
                "posterior_params": dict(self.posterior_params),
                "likelihood_summary": dict(self.likelihood_summary),
                "method": self.method,
                "spec_hash": self.spec_hash,
                "schema": self.schema,
                "notes": self.notes,
            },
        }

    def to_legacy_annotation(self) -> Dict[str, Any]:
        """Render the legacy ``derived_metric.annotations`` shape used by exemplars.

        Keeps the public fields of the existing UC events that already exist in
        synthetic graphs (``annotations.kind == "uncertainty_carrier"``) so any
        downstream renderer keeps working; Bayesian extras live next to them.
        """
        return {
            "kind": "uncertainty_carrier",
            "metric": self.hypothesis_id,
            "point_estimate": self.point_estimate,
            "band_90": list(self.band_90),
            "basis": list(self.basis),
            "confidence": self.confidence_label,
            "confidence_score": self.confidence,
            "evidence_event_ids": list(self.evidence_event_ids),
            "method": self.method,
            "prior": dict(self.prior),
            "posterior_params": dict(self.posterior_params),
            "spec_hash": self.spec_hash,
            "uc_schema": self.schema,
        }

    # ------- factories ------------------------------------------------------

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "UncertaintyCarrier":
        band = d.get("band_90") or [0.0, 1.0]
        return cls(
            hypothesis_id=str(d.get("hypothesis_id") or d.get("metric") or "unknown"),
            point_estimate=float(d.get("point_estimate") or 0.0),
            band_90=tuple(band),  # type: ignore[arg-type]
            confidence=float(
                d.get("confidence")
                if isinstance(d.get("confidence"), (int, float))
                else d.get("confidence_score") or 0.0
            ),
            basis=list(d.get("basis") or []),
            evidence_event_ids=list(d.get("evidence_event_ids") or []),
            method=str(d.get("method") or "beta_conjugate_v1"),
            prior=dict(d.get("prior") or {}),
            posterior_params=dict(d.get("posterior_params") or {}),
            likelihood_summary=dict(d.get("likelihood_summary") or {}),
            spec_hash=d.get("spec_hash"),
            schema=str(d.get("schema") or d.get("uc_schema") or UC_SCHEMA_VERSION),
            confidence_label=d.get("confidence_label")
            or (d.get("confidence") if isinstance(d.get("confidence"), str) else None),
            notes=d.get("notes"),
        )


# --------------------------------------------------------------------------- #
# Convenience: build the handoff posteriors[] block from a list of UCs.
# --------------------------------------------------------------------------- #

def render_handoff_posteriors(ucs: Sequence["UncertaintyCarrier"]) -> List[Dict[str, Any]]:
    return [uc.to_handoff_block() for uc in ucs if isinstance(uc, UncertaintyCarrier)]
