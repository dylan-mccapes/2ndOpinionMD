# server/eoh/modules/m13_flare_risk.py

from __future__ import annotations

from typing import Dict, Any


MODULE_NAME = "M13_flare_risk"
MODULE_VERSION = "0.1.0-M0"


def compute_flare_risk(features: Dict[str, Any]) -> Dict[str, float]:
    """
    Heuristic M0 version of flare risk.

    Returns conceptual probabilities in [0, 1] that are:
    - monotonic with respect to features we care about
    - easy to later replace with a trained model using the same interface.
    """
    n_flares_90d = int(features.get("n_flares_90d") or 0)
    max_crp_recent = features.get("max_crp_recent")
    has_biologic = bool(features.get("has_biologic"))

    # Base risk
    risk_30d = 0.05
    risk_90d = 0.15

    # More recent flares → higher risk
    if n_flares_90d >= 2:
        risk_30d += 0.15
        risk_90d += 0.25
    elif n_flares_90d == 1:
        risk_30d += 0.08
        risk_90d += 0.15

    # Inflammatory markers
    if isinstance(max_crp_recent, (int, float)):
        if max_crp_recent > 5:
            risk_30d += 0.10
            risk_90d += 0.15
        elif max_crp_recent > 1:
            risk_30d += 0.05
            risk_90d += 0.08

    # Biologic on board can modestly reduce near-term risk
    if has_biologic:
        risk_30d *= 0.8
        risk_90d *= 0.9

    # Clamp
    risk_30d = max(0.0, min(0.8, risk_30d))
    risk_90d = max(0.0, min(0.95, risk_90d))

    return {
        "ra_flare_30d_prob": risk_30d,
        "ra_flare_90d_prob": risk_90d,
    }