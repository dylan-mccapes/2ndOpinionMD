# server/api/stream_gating.py

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from .stream_config import (
    SOURCE_GATING_ENABLED,
    MIN_DOCS_PER_SOURCE,
    REL_SCORE_CUTOFF,
    ABS_SCORE_CUTOFF,
    ALWAYS_KEEP_SOURCES,
)

logger = logging.getLogger(__name__)


def _max_score(rows: List[Dict[str, Any]]) -> float:
    if not rows:
        return 0.0
    return max(float(r.get("score", 0.0) or 0.0) for r in rows)


def apply_source_gating(
    results_by_source: Dict[str, List[Dict[str, Any]]],
    query: str,
    *,
    extra_always_keep: Optional[set[str]] = None,
    coding_mode: bool = False,
    ctx_k: Optional[int] = None,
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """
    Simple, domain-agnostic source gating.

    - If SOURCE_GATING_ENABLED=0 → pass-through, but still emit stats.
    - Always keeps sources in ALWAYS_KEEP_SOURCES ∪ extra_always_keep.
    - Otherwise:
        * Drops obviously empty / zero-score sources when there are others.
        * Optionally drops sources whose max_score is far below the global max,
          using REL_SCORE_CUTOFF and ABS_SCORE_CUTOFF.

    No RA/lupus/whatever-specific logic here; the LLM router + graders
    are responsible for disease-specific routing.
    """
    gating_info: Dict[str, Any] = {
        "enabled": bool(SOURCE_GATING_ENABLED),
        "coding_mode": bool(coding_mode),
        "ctx_k": ctx_k,
        "sources": {},
    }

    if not results_by_source:
        gating_info["n_sources_before"] = 0
        gating_info["n_sources_after"] = 0
        return results_by_source, gating_info

    # Per-source stats
    stats: Dict[str, Dict[str, Any]] = {}
    for src, rows in results_by_source.items():
        stats[src] = {
            "n_rows": len(rows),
            "max_score": _max_score(rows),
        }

    gating_info["n_sources_before"] = len(results_by_source)

    # If global gating disabled → keep everything but record stats
    if not SOURCE_GATING_ENABLED:
        for src, st in stats.items():
            gating_info["sources"][src] = {
                "decision": "keep",
                "reason": "gating_disabled",
                "n_rows": st["n_rows"],
                "max_score": st["max_score"],
            }
        gating_info["n_sources_after"] = len(results_by_source)
        return results_by_source, gating_info

    always_keep: set[str] = set(ALWAYS_KEEP_SOURCES or set())
    if extra_always_keep:
        always_keep |= set(extra_always_keep)

    global_max = max(st["max_score"] for st in stats.values()) or 0.0

    keep_sources: set[str] = set()

    for src, st in stats.items():
        n_rows = st["n_rows"]
        max_sc = st["max_score"]

        # 1) Always-keep overrides everything.
        if src in always_keep:
            keep_sources.add(src)
            gating_info["sources"][src] = {
                "decision": "keep",
                "reason": "always_keep",
                "n_rows": n_rows,
                "max_score": max_sc,
            }
            continue

        # If we only have one source, don't over-gate.
        if len(results_by_source) == 1:
            keep_sources.add(src)
            gating_info["sources"][src] = {
                "decision": "keep",
                "reason": "single_source",
                "n_rows": n_rows,
                "max_score": max_sc,
            }
            continue

        # 2) Drop trivially empty / zero-score sources.
        if n_rows < MIN_DOCS_PER_SOURCE:
            gating_info["sources"][src] = {
                "decision": "drop",
                "reason": "too_few_rows",
                "n_rows": n_rows,
                "max_score": max_sc,
            }
            continue

        if max_sc <= 0.0:
            gating_info["sources"][src] = {
                "decision": "drop",
                "reason": "no_signal",
                "n_rows": n_rows,
                "max_score": max_sc,
            }
            continue

        # 3) Relative / absolute score cutoff.
        rel_ok = True
        if global_max > 0.0:
            rel_ok = max_sc >= global_max * REL_SCORE_CUTOFF

        abs_ok = max_sc >= ABS_SCORE_CUTOFF

        if rel_ok and abs_ok:
            keep_sources.add(src)
            gating_info["sources"][src] = {
                "decision": "keep",
                "reason": "score_ok",
                "n_rows": n_rows,
                "max_score": max_sc,
            }
        else:
            gating_info["sources"][src] = {
                "decision": "drop",
                "reason": "low_score",
                "n_rows": n_rows,
                "max_score": max_sc,
            }

    # Build gated dict
    gated: Dict[str, List[Dict[str, Any]]] = {}
    for src, rows in results_by_source.items():
        if src in keep_sources:
            gated[src] = rows

    gating_info["n_sources_after"] = len(gated)

    logger.info(
        "apply_source_gating: before=%d after=%d coding_mode=%s",
        len(results_by_source),
        len(gated),
        coding_mode,
    )

    return gated, gating_info

def apply_code_row_filter(
    rows: List[Dict[str, Any]],
    q: str,
    source: str,
) -> List[Dict[str, Any]]:
    """
    Lightweight per-row filter for *code* sources in coding_mode.

    Goals:
      - Prefer TS rows (lexical / term-based matches) over pure ANN noise.
      - Drop very low-score ANN rows that are far from the top for that source.
      - Never completely wipe out a source that already has some rows; if
        everything gets filtered, fall back to the original rows.

    This runs *before* source-level gating and fusion.
    """
    if not rows:
        return rows

    # Partition rows by method
    ts_rows: List[Dict[str, Any]] = []
    ann_rows: List[Dict[str, Any]] = []
    other_rows: List[Dict[str, Any]] = []

    for r in rows:
        m = (r.get("method") or "").lower()
        if m.startswith("ts"):
            ts_rows.append(r)
        elif m == "ann":
            ann_rows.append(r)
        else:
            other_rows.append(r)

    def _sort(rs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            rs,
            key=lambda x: float(x.get("score", 0.0) or 0.0),
            reverse=True,
        )

    ts_rows = _sort(ts_rows)
    ann_rows = _sort(ann_rows)
    other_rows = _sort(other_rows)

    # Always keep all TS rows we already retrieved — TS is already bounded
    # by per-source limit in rag_stream_routes, and is our strongest signal.
    keep_ts: List[Dict[str, Any]] = list(ts_rows)

    # For ANN, drop rows that are too weak relative to top ANN and absolute cutoff
    keep_ann: List[Dict[str, Any]] = []
    if ann_rows:
        top_ann_score = float(ann_rows[0].get("score", 0.0) or 0.0)

        # Use global gating thresholds as soft guidance
        rel_cutoff = max(0.0, min(1.0, REL_SCORE_CUTOFF))  # e.g. 0.35
        abs_cutoff = float(ABS_SCORE_CUTOFF or 0.0)         # e.g. 0.0–0.1

        for r in ann_rows:
            s = float(r.get("score", 0.0) or 0.0)

            # absolute floor
            if s < abs_cutoff:
                continue

            # relative to best ANN row for this source
            if top_ann_score > 0.0 and s < top_ann_score * rel_cutoff:
                continue

            keep_ann.append(r)

    # For "other" methods (valyu, custom), just keep them as-is for now.
    keep_other = list(other_rows)

    filtered = keep_ts + keep_ann + keep_other

    # Safety: never accidentally wipe a source that had rows.
    if not filtered:
        return rows

    return filtered