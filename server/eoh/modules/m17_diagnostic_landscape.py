# server/eoh/modules/m17_diagnostic_landscape.py

from __future__ import annotations

from typing import Dict, Any


MODULE_NAME = "M17_diagnostic_landscape"
MODULE_VERSION = "0.1.0-M0"


def compute_diagnostic_landscape(features: Dict[str, Any]) -> Dict[str, float]:
    """
    Crude, transparent diagnostic landscape.

    Uses 'evidence' scores derived from the timeline to create a conceptual
    probability distribution across diseases of interest. This is deliberately
    simple so you can later swap in a trained model.
    """
    ra_e = float(features.get("ra_evidence") or 0.0)
    sle_e = float(features.get("sle_evidence") or 0.0)

    scores = {
        "p_ra": ra_e,
        "p_sle": sle_e,
        "p_psa": 0.1,
        "p_sjogren": 0.1,
        "p_mctd": 0.1,
        "p_vasculitis": 0.1,
        "p_other": 0.5,
    }

    total = sum(scores.values()) or 1.0
    for k in scores:
        scores[k] = scores[k] / total

    return scores