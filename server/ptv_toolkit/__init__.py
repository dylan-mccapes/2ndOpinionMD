"""
ptv_toolkit — agent-facing tools for the indexed PTV graph (noarcs build).

Exposes a deterministic, JSON-serializable tool surface an LLM agent can
call to answer longitudinal clinical questions over a PatientTimelineVision
JSON artifact:

    - code_index_lookup   (drugs | rxnorm | icd | labs | loinc)
    - semantic_search     (sentence-transformers over event text)
    - bfs_expand          (typed connascence-edge traversal)
    - temporal_scan       (event_type + time-window + optional query)
    - get_event           (full row by event_id)
    - list_event_types    (cheap enumeration)
    - graph_stats         (snapshot for cold-start orientation)

No Lorenz / provenance-engine dependencies. The toolkit loads a single
JSON file, builds in-memory indexes, and caches sentence-transformer
embeddings to disk keyed by graph hash.
"""
from __future__ import annotations

from .bayes import (
    DEFAULT_HYPOTHESIS_PRIORS,
    BetaPrior,
    GammaPrior,
    NormalNormalPrior,
    LikelihoodSpec,
    bayesian_update_uc,
    update_beta_bernoulli,
    update_gamma_poisson,
    update_normal_normal,
)
from .graph import GraphHandle, load_graph
from .handoff import build_handoff, save_handoff
from .registry import TOOL_SCHEMAS, call_tool, tool_names

__all__ = [
    "GraphHandle",
    "load_graph",
    "TOOL_SCHEMAS",
    "call_tool",
    "tool_names",
    "build_handoff",
    "save_handoff",
    "bayesian_update_uc",
    "BetaPrior",
    "GammaPrior",
    "NormalNormalPrior",
    "LikelihoodSpec",
    "update_beta_bernoulli",
    "update_gamma_poisson",
    "update_normal_normal",
    "DEFAULT_HYPOTHESIS_PRIORS",
]

__version__ = "0.2.0"
