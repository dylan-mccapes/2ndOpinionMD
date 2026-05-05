"""
registry.py — tool-name → callable mapping + JSON schema for the agent.
"""
from __future__ import annotations

import json
from typing import Any, Callable, Dict, List

from .graph import GraphHandle
from . import tools as T


# ---------------------------------------------------------------------------
# JSON schema the agent is shown (used by Modelfile + harness prompt)
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "graph_stats",
        "purpose": (
            "Cold-start snapshot of the graph: event count, type distribution, "
            "date range, code-index sizes. Call once if you need orientation; "
            "never in a loop."
        ),
        "args": {},
    },
    {
        "name": "list_event_types",
        "purpose": "Enumerate distinct event_type values and their counts.",
        "args": {},
    },
    {
        "name": "code_index_lookup",
        "purpose": (
            "Flat lookup into metadata.code_index. Best tool for questions of "
            "the form 'every X, in order' where X is a drug, RxNorm code, "
            "ICD-10 code, lab name, or LOINC code. Pass exactly one of "
            "`key` (exact match) or `key_contains` (substring). Omit both "
            "to list the top-n keys in that bucket."
        ),
        "args": {
            "bucket": "one of: drugs, rxnorm, icd, labs, loinc (required)",
            "key": "exact key to look up (e.g. 'hydrocodone', 'I10', '1049630')",
            "key_contains": "case-insensitive substring match on keys",
            "limit": "max rows/keys returned (default 50, max 500)",
        },
    },
    {
        "name": "semantic_search",
        "purpose": (
            "sentence-transformers cosine search over event text. Best for "
            "free-text questions ('pain radiating', 'first signs of kidney "
            "trouble') where exact codes are not known. Before calling, "
            "rewrite the query to include medical synonyms, ICD family hints, "
            "and drug class names. With `event_ids`, this becomes a rerank "
            "of that subset (combine with temporal_scan / code_index_lookup "
            "to rerank a scope-filtered working set)."
        ),
        "args": {
            "query": "expanded natural-language query (required; include synonyms)",
            "k": "number of results (default 12, max 50)",
            "event_types": "optional list restricting to these event_type values",
            "event_ids": "optional list; when present, rerank only these events",
        },
    },
    {
        "name": "bfs_expand",
        "purpose": (
            "Multi-seed BFS over typed connascence edges. Use AFTER "
            "semantic_search or code_index_lookup has produced seed "
            "event_ids; BFS then pulls the story around those seeds. "
            "edge_kinds: same_chapter, same_day, same_encounter, same_icd, "
            "same_drug, temporal, in_workup_for, caused_by."
        ),
        "args": {
            "seed_event_ids": "list of event_ids to start from (required)",
            "edge_kinds": "optional subset of connascence kinds (default: all)",
            "depth": "BFS depth, 1–4 (default 1)",
            "max_events": "cap on total events returned (default 40, max 200)",
        },
    },
    {
        "name": "temporal_scan",
        "purpose": (
            "Scan events chronologically by type and/or date window. Best "
            "for 'all labs in 2023', 'every medication in the last year', "
            "'visits between 2016-01-01 and 2016-12-31'. Combine `query` to "
            "keyword-filter within the window."
        ),
        "args": {
            "event_types": "optional list of event_type values to include",
            "start": "ISO date YYYY-MM-DD (inclusive)",
            "end": "ISO date YYYY-MM-DD (inclusive)",
            "query": "optional keyword filter (tokens AND-matched on preview/card)",
            "order": "asc | desc (default asc)",
            "limit": "max rows returned (default 40, max 200)",
            "include_unknown_timestamps": "true to include events with unknown ts",
        },
    },
    {
        "name": "get_event",
        "purpose": (
            "Fetch the full row for a single event_id (annotations, "
            "connascence, preview). Use to confirm evidence before a "
            "final answer."
        ),
        "args": {
            "event_id": "event_id string (required)",
        },
    },
    {
        "name": "bayesian_update_uc",
        "purpose": (
            "Closed-form Bayesian posterior summary (UC) for one hypothesis. "
            "Per STRATEGY_BAYESIAN_PTV_UC_20260423.md §3.3: combines a "
            "Beta/Gamma/Normal-Normal prior with evidence drawn from PTV "
            "events under a declarative likelihood spec. Output is a "
            "deterministic UncertaintyCarrier with point_estimate, band_90, "
            "confidence, basis, evidence_event_ids, prior, posterior_params, "
            "method, spec_hash. Default hypotheses (with built-in priors and "
            "rules): flare_30d, progression_3mo, taper_safety. "
            "Choose this when a question asks for a probability or rate "
            "('how likely is a flare in the next 30 days', 'will this "
            "patient progress in 3 months', 'is it safe to taper now')."
        ),
        "args": {
            "hypothesis_id": (
                "string — one of flare_30d | progression_3mo | taper_safety "
                "(or a custom id when prior+likelihood_spec are supplied)."
            ),
            "evidence_event_ids": (
                "optional list of event_ids to restrict the conditioning set; "
                "omit to use every event in the graph."
            ),
            "prior": (
                "optional dict {family, alpha, beta, mu, sigma, sigma_obs, source, notes}; "
                "omit to use the strategy-doc default for this hypothesis."
            ),
            "likelihood_spec": (
                "optional dict {family, weight_by, rules:[{name, match, outcome, weight}]} "
                "matching the LikelihoodSpec DSL in server/ptv_toolkit/bayes.py; omit to use the "
                "default rules for the hypothesis."
            ),
            "notes": "optional free-text annotation to attach to the UC.",
        },
    },
]


_TOOL_FNS: Dict[str, Callable[[GraphHandle, Dict[str, Any]], Dict[str, Any]]] = {
    "graph_stats":         T.graph_stats,
    "list_event_types":    T.list_event_types,
    "code_index_lookup":   T.code_index_lookup,
    "semantic_search":     T.semantic_search,
    "bfs_expand":          T.bfs_expand,
    "temporal_scan":       T.temporal_scan,
    "get_event":           T.get_event,
    "bayesian_update_uc":  T.bayesian_update_uc,
}


def tool_names() -> List[str]:
    return list(_TOOL_FNS.keys())


def call_tool(name: str, gh: GraphHandle, args: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if name not in _TOOL_FNS:
        return {
            "tool": name,
            "ok": False,
            "error": f"unknown tool '{name}'. allowed: {tool_names()}",
        }
    try:
        result = _TOOL_FNS[name](gh, dict(args or {}))
        return {"tool": name, "ok": True, "args": args or {}, "result": result}
    except Exception as exc:  # noqa: BLE001
        return {
            "tool": name,
            "ok": False,
            "args": args or {},
            "error": f"{type(exc).__name__}: {exc}",
        }


def render_tool_catalog() -> str:
    """Pretty catalog for the agent's system prompt."""
    lines = []
    for spec in TOOL_SCHEMAS:
        lines.append(f"- {spec['name']} — {spec['purpose']}")
        if spec.get("args"):
            for k, v in spec["args"].items():
                lines.append(f"    • {k}: {v}")
    return "\n".join(lines)


def schemas_json() -> str:
    return json.dumps(TOOL_SCHEMAS, indent=2)
