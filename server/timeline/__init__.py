"""
EoH Timeline Engine

This module provides the backbone for 2ndOpinionMD's Patient Timeline Engine:
1. Autoimmune flare prediction
2. Probabilistic diagnostic landscape mapping
3. Trajectory analysis & symptom/lab clustering
4. Clinician-auditable EoH reasoning

All outputs are probabilistic, transparent, and non-diagnostic per regulatory strategy.
"""

from .engine import TimelineEngine
from .models import TimelineEvent, FlareSignature, DiagnosticLandscape

__all__ = [
    "TimelineEngine",
    "TimelineEvent",
    "FlareSignature",
    "DiagnosticLandscape",
]
