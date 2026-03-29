"""
EoH Timeline Engine

This module provides the backbone for 2ndOpinionMD's Patient Timeline Engine:
1. Autoimmune flare prediction
2. Probabilistic diagnostic landscape mapping
3. Trajectory analysis & symptom/lab clustering
4. Clinician-auditable EoH reasoning

All outputs are probabilistic, transparent, and non-diagnostic per regulatory strategy.

TimelineEngine is lazy-imported so ``from server.timeline.embedding_cache import ...``
does not require psycopg2 (engine pulls Postgres drivers).
"""

from .models import TimelineEvent, FlareSignature, DiagnosticLandscape

__all__ = [
    "TimelineEngine",
    "TimelineEvent",
    "FlareSignature",
    "DiagnosticLandscape",
]


def __getattr__(name: str):
    if name == "TimelineEngine":
        from .engine import TimelineEngine

        return TimelineEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
