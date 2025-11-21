# server/api/stream_gating.py

import json
import re
from typing import Any, Dict, List, Optional, Tuple, Set

from .stream_config import (
    ABS_SCORE_CUTOFF,
    ALWAYS_KEEP_SOURCES,
    CODE_SOURCES,
    GUIDELINE_SOURCES,
    MIN_DOCS_PER_SOURCE,
    REL_SCORE_CUTOFF,
    SOURCE_CONFIG,
    SOURCE_GATING_ENABLED,
    RA_GUIDELINE_SOURCES,
    is_ra_query,
    TS_PIN_K_PER_SOURCE_CODING,
    TS_PIN_K_PER_SOURCE_DEFAULT,
    TS_PIN_MAX_FRAC_CTX,
)


def summarize_source_scores(
    rows: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """
    Compute simple statistics over scores for a source, for gating.
    """
    if not rows:
        return None

    scores = sorted(
        [float(r.get("score", 0.0) or 0.0) for r in rows],
        reverse=True,
    )
    n = len(scores)
    top1 = scores[0]
    top3_mean = sum(scores[:3]) / min(3, n)
    median = scores[n // 2]
    return {
        "n": n,
        "top1": top1,
        "top3_mean": top3_mean,
        "median": median,
    }


def _simple_token_set(text: str) -> set[str]:
    """
    Lowercase, strip non-alphanumerics, and return a set of tokens (len>=3).
    Used for rough lexical gating.
    """
    if not text or not isinstance(text, str):
        return set()
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return {t for t in text.split() if len(t) >= 3}

def _apply_light_pinning(
    results_by_source: Dict[str, List[Dict[str, Any]]],
    *,
    coding_mode: bool,
    ctx_k: Optional[int],
) -> None:
    """
    Light fusion step that "pins" top TS / TS_TERM rows per source.

    - For coding_mode + code sources: use TS_PIN_K_PER_SOURCE_CODING.
    - For others:          use TS_PIN_K_PER_SOURCE_DEFAULT.
    - Adds a boolean 'pinned' flag to rows, to be respected by heavy fusion.
    - Enforces a global cap so pinned rows don't eat all of ctx_k.
    """
    if not results_by_source:
        return

    # Reset any previous pinning
    for rows in results_by_source.values():
        for r in rows:
            if "pinned" in r:
                r["pinned"] = False

    # 1) Per-source pinning
    all_pinned: List[Dict[str, Any]] = []

    for src, rows in results_by_source.items():
        src_norm = (src or "").lower()

        if coding_mode and src_norm in CODE_SOURCES:
            cap = TS_PIN_K_PER_SOURCE_CODING
        else:
            cap = TS_PIN_K_PER_SOURCE_DEFAULT

        if cap <= 0:
            continue

        ts_rows = [
            r
            for r in rows
            if (r.get("method") in ("ts_terms", "ts"))
        ]
        if not ts_rows:
            continue

        ts_rows_sorted = sorted(
            ts_rows,
            key=lambda r: float(r.get("score", 0.0) or 0.0),
            reverse=True,
        )

        for r in ts_rows_sorted[:cap]:
            r["pinned"] = True
            all_pinned.append(r)

    if not all_pinned or ctx_k is None or ctx_k <= 0:
        return

    # 2) Global cap on pinned rows (as fraction of ctx_k)
    max_frac = TS_PIN_MAX_FRAC_CTX
    if max_frac <= 0.0:
        max_pinned = 0
    elif max_frac >= 1.0:
        max_pinned = ctx_k
    else:
        max_pinned = max(1, int(max_frac * ctx_k))

    if len(all_pinned) <= max_pinned:
        return

    # Too many pinned rows; keep only the globally best by score
    all_pinned_sorted = sorted(
        all_pinned,
        key=lambda r: float(r.get("score", 0.0) or 0.0),
        reverse=True,
    )
    keep_keys = {
        ((r.get("source") or ""), r.get("id"))
        for r in all_pinned_sorted[:max_pinned]
    }

    for rows in results_by_source.values():
        for r in rows:
            if r.get("pinned"):
                key = ((r.get("source") or ""), r.get("id"))
                if key not in keep_keys:
                    r["pinned"] = False


def apply_source_gating(
    results_by_source: Dict[str, List[Dict[str, Any]]],
    query: str | None = None,
    extra_always_keep: Optional[Set[str]] = None,
    coding_mode: bool = False,
    ctx_k: Optional[int] = None,
) -> Tuple[Dict[str, List[Dict[str, Any]]], Dict[str, Any]]:
    """
    Apply heuristics to drop obviously off-topic / weak sources.

    - Uses RA-aware tweaks for RA guideline PDFs.
    - Supports an extra_always_keep set (e.g., ethos_model when use_ethos=1).
    - Adds a light lexical-overlap check to trim “background” guidelines.
    - Fails open if everything would be dropped.
    - Also performs *light pinning* of TS matches per source, adding
      a boolean 'pinned' field to rows. Heavy fusion will respect this.
    """
    is_ra = is_ra_query(query or "")

    GUIDELINE_REL_CUTOFF = 0.65
    RA_GUIDELINE_REL_CUTOFF = 0.35

    # Merge ALWAYS_KEEP with any per-call extra_always_keep (e.g., ethos)
    always_keep: Set[str] = set(ALWAYS_KEEP_SOURCES)
    if extra_always_keep:
        always_keep |= set(extra_always_keep)

    q_tokens = _simple_token_set(query or "") if query else set()

    gating_info: Dict[str, Any] = {
        "enabled": SOURCE_GATING_ENABLED,
        "min_docs": MIN_DOCS_PER_SOURCE,
        "rel_cutoff": REL_SCORE_CUTOFF,
        "abs_cutoff": ABS_SCORE_CUTOFF,
        "always_keep": sorted(list(always_keep)),
        "guideline_sources": sorted(list(GUIDELINE_SOURCES)),
        "ra_guideline_sources": sorted(list(RA_GUIDELINE_SOURCES)),
        "is_ra_query": is_ra,
        "sources": {},
    }

    stats_by_src: Dict[str, Optional[Dict[str, Any]]] = {
        src: summarize_source_scores(rows)
        for src, rows in results_by_source.items()
    }
    nonempty_stats = {
        src: st for src, st in stats_by_src.items() if st is not None and st["n"] > 0
    }

    if not nonempty_stats:
        gating_info["n_sources_before"] = len(results_by_source)
        gating_info["n_sources_after"] = len(results_by_source)
        gating_info["global_top1"] = None
        gating_info["fail_open"] = True

        # Still apply light pinning (no-op if empty)
        _apply_light_pinning(results_by_source, coding_mode=coding_mode, ctx_k=ctx_k)
        return results_by_source, gating_info

    global_top1 = max(st["top1"] for st in nonempty_stats.values())
    gating_info["global_top1"] = global_top1

    kept: Dict[str, List[Dict[str, Any]]] = {}

    # If gating disabled or we're not in coding_mode, keep everything but still
    # compute stats + apply light pinning.
    if not SOURCE_GATING_ENABLED or not coding_mode:
        kept = dict(results_by_source)
        for src, rows in results_by_source.items():
            gating_info["sources"][src] = {
                "decision": "keep",
                "reason": "gating_disabled",
                "stats": stats_by_src[src],
            }
        gating_info["n_sources_before"] = len(results_by_source)
        gating_info["n_sources_after"] = len(kept)
        gating_info["fail_open"] = False

        _apply_light_pinning(kept, coding_mode=coding_mode, ctx_k=ctx_k)
        return kept, gating_info

    # ---- Normal gating path (coding_mode=True) ----------------------------

    for src, rows in results_by_source.items():
        stats = stats_by_src[src]

        # Compute a quick lexical overlap between the query and the
        # highest-scoring row for this source (if we have both).
        lexical_overlap = 0
        if q_tokens and rows:
            top_row = max(rows, key=lambda r: float(r.get("score", 0.0) or 0.0))
            blob = f"{top_row.get('title') or ''} {top_row.get('text') or ''}"
            doc_tokens = _simple_token_set(blob)
            lexical_overlap = len(q_tokens & doc_tokens)

        if stats is None or stats["n"] == 0:
            decision = "drop"
            reason = "no_rows"
        elif src in always_keep:
            decision = "keep"
            reason = "always_keep"
        elif is_ra and src in RA_GUIDELINE_SOURCES:
            decision = "keep"
            reason = "ra_query && ra_guideline_source"
        elif stats["n"] < MIN_DOCS_PER_SOURCE:
            decision = "drop"
            reason = f"too_few_docs({stats['n']})"
        else:
            rel = stats["top1"] / global_top1 if global_top1 > 0 else 0.0

            if src in GUIDELINE_SOURCES:
                # RA-aware tweak: for RA queries, keep RA guideline sources at
                # a lower rel_cutoff, but *raise* the bar for other guidelines.
                base_cutoff = (
                    RA_GUIDELINE_REL_CUTOFF
                    if (is_ra and src in RA_GUIDELINE_SOURCES)
                    else GUIDELINE_REL_CUTOFF
                )
                if is_ra and src not in RA_GUIDELINE_SOURCES:
                    # Non-RA guidelines in an RA query must be very competitive
                    # to stay in the mix.
                    rel_cutoff = max(base_cutoff, 0.80)
                else:
                    rel_cutoff = base_cutoff
            else:
                rel_cutoff = REL_SCORE_CUTOFF

            meets_rel = rel >= rel_cutoff
            meets_abs = ABS_SCORE_CUTOFF > 0.0 and stats["top1"] >= ABS_SCORE_CUTOFF

            if meets_rel or meets_abs:
                # Light lexical sanity check for non-ALWAYS_KEEP, non-RA guidelines:
                if (
                    q_tokens
                    and lexical_overlap == 0
                    and src not in RA_GUIDELINE_SOURCES
                    and src not in always_keep
                ):
                    decision = "drop"
                    reason = (
                        f"weak_lexical_overlap(0) despite score_ok"
                        f"(rel={rel:.3f}, cutoff={rel_cutoff:.3f})"
                    )
                else:
                    decision = "keep"
                    reason = f"score_ok(rel={rel:.3f}, cutoff={rel_cutoff:.3f})"
            else:
                decision = "drop"
                reason = f"weak_score(rel={rel:.3f}, cutoff={rel_cutoff:.3f})"

        gating_info["sources"][src] = {
            "decision": decision,
            "reason": reason,
            "stats": stats,
            "lexical_overlap": lexical_overlap,
        }

        if decision == "keep":
            kept[src] = rows

    if not kept:
        gating_info["fail_open"] = True
        kept = dict(results_by_source)
    else:
        gating_info["fail_open"] = False

    gating_info["n_sources_before"] = len(results_by_source)
    gating_info["n_sources_after"] = len(kept)

    # IMPORTANT: light pinning happens *after* we decide which sources to keep.
    _apply_light_pinning(kept, coding_mode=coding_mode, ctx_k=ctx_k)

    return kept, gating_info


# ---------------------------------------------------------------------------
# Coding-specific row filter for high-noise map corpora
# ---------------------------------------------------------------------------


def _simple_token_set(text: str) -> set[str]:
    """
    Lowercase, strip non-alphanumerics, and return a set of tokens (len>=3).
    Used for rough lexical gating.
    """
    if not text or not isinstance(text, str):
        return set()
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return {t for t in text.split() if len(t) >= 3}


def apply_code_row_filter(
    rows: List[Dict[str, Any]],
    q: str,
    source: str,
) -> List[Dict[str, Any]]:
    """
    Extra lexical gating for mapping-heavy code sources in coding mode.

    - Only applies to sources marked codes_authoritative in SOURCE_CONFIG.
    - Drops junk ICD-10-CM rows from SNOMED crosswalks.
    - Keeps *all* rows that meet the heuristic overlap threshold; no
      top-k truncation happens here.
    """
    src_norm = (source or "").lower()
    if src_norm not in CODE_SOURCES:
        return rows

    cfg = SOURCE_CONFIG.get(src_norm, {})
    exclude_from_tags = cfg.get("exclude_meta_from") or []

    # 1) Drop rows whose meta->>'from' is in exclude_meta_from
    if exclude_from_tags:
        filtered_rows: List[Dict[str, Any]] = []
        for r in rows:
            meta = r.get("meta")
            tag = None

            if isinstance(meta, dict):
                tag = meta.get("from")
            elif isinstance(meta, str):
                try:
                    parsed = json.loads(meta)
                except Exception:
                    parsed = None
                if isinstance(parsed, dict):
                    tag = parsed.get("from")

            if tag in exclude_from_tags:
                continue

            filtered_rows.append(r)

        rows = filtered_rows
        if not rows:
            return []

    # 2) Lexical overlap gating
    q_tokens = _simple_token_set(q or " ")
    if not q_tokens:
        return rows

    scored: List[tuple[int, float, Dict[str, Any]]] = []

    for r in rows:
        title = (r.get("title") or "") or ""
        text = (r.get("text") or "") or ""

        meta = r.get("meta")
        meta_parts: List[str] = []

        if isinstance(meta, dict):
            for val in meta.values():
                if isinstance(val, str):
                    meta_parts.append(val)
        elif isinstance(meta, str):
            meta_parts.append(meta)
            try:
                parsed = json.loads(meta)
            except Exception:
                parsed = None
            if isinstance(parsed, dict):
                for val in parsed.values():
                    if isinstance(val, str):
                        meta_parts.append(val)

        blob = " ".join([title, text] + meta_parts)
        doc_tokens = _simple_token_set(blob)
        overlap = len(q_tokens & doc_tokens)
        base_score = float(r.get("score", 0.0) or 0.0)

        scored.append((overlap, base_score, r))

    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)

    # For ICD-10-CM, be more permissive: descriptions are short and
    # RA codes can have low lexical overlap with the full question.
    if src_norm == "icd10cm":
        MIN_OVERLAP = 0
        FAIL_OPEN_TOP_N = 10
    else:
        MIN_OVERLAP = 1
        FAIL_OPEN_TOP_N = 3

    kept: List[Dict[str, Any]] = []
    for idx, (overlap, base_score, row) in enumerate(scored):
        if overlap >= MIN_OVERLAP or idx < FAIL_OPEN_TOP_N:
            kept.append(row)

    # Fail-open: if everything would be dropped, fall back to original rows.
    if not kept:
        return rows

    return kept
