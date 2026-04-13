"""
Agent-callable graph tools for Patient Timeline Vision (PTV).

Maps the core 12 strategies in game_plans/STRATEGY_GRAPH_TRAVERSAL.md to
deterministic Python functions. Each tool returns JSON-serializable dicts with
provenance fields for DerivationChain (M63).

Orchestrators should call execute_graph_tool(name, vision, args) and pass
results back to the LLM in bounded context.
"""

from __future__ import annotations

import math
import os
import re
import sys
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from server.eoh.patient_timeline_vision import PatientTimelineVision, TimelineEventVision
from server.utils.parse_date import parse_clinical_date

try:
    import numpy as np
except ImportError:  # pragma: no cover
    np = None  # type: ignore

try:
    import networkx as nx
except ImportError:  # pragma: no cover
    nx = None  # type: ignore

# ---------------------------------------------------------------------------
# Lorenz (Portal GC geometry) — RK4 fallback when provenance-engine not used
# ---------------------------------------------------------------------------

_SIGMA = 10.0
_BETA = 8.0 / 3.0


def _lorenz_deriv(state: "np.ndarray", rho: float) -> "np.ndarray":
    x, y, z = float(state[0]), float(state[1]), float(state[2])
    dx = _SIGMA * (y - x)
    dy = x * (rho - z) - y
    dz = x * y - _BETA * z
    return np.array([dx, dy, dz], dtype=np.float64)


def _rk4_lorenz_traj(x0: float, y0: float, z0: float, rho: float, steps: int = 2000, dt: float = 0.01) -> "np.ndarray":
    if np is None:
        raise RuntimeError("numpy required for Lorenz integration")
    s = np.array([x0, y0, z0], dtype=np.float64)
    xs = np.zeros(steps, dtype=np.float64)
    for i in range(steps):
        k1 = _lorenz_deriv(s, rho)
        k2 = _lorenz_deriv(s + 0.5 * dt * k1, rho)
        k3 = _lorenz_deriv(s + 0.5 * dt * k2, rho)
        k4 = _lorenz_deriv(s + dt * k3, rho)
        s = s + (dt / 6.0) * (k1 + 2 * k2 + 2 * k3 + k4)
        xs[i] = s[0]
    return xs


def _classify_from_traj(xs: "np.ndarray", tau: float) -> Tuple[str, float]:
    tail = xs[-200:] if len(xs) >= 200 else xs
    mean_x = float(np.mean(tail))
    if mean_x < -tau:
        return "KEEP", mean_x
    if mean_x > tau:
        return "EVICT", mean_x
    return "REVIEW", mean_x


def _event_text(ev: TimelineEventVision) -> str:
    parts = [ev.event_type]
    if ev.timestamp and ev.timestamp.lower() not in ("unknown", "n/a", ""):
        parts.append(ev.timestamp[:16])
    parts.append(ev.preview[:240])
    return " | ".join(parts)


def _unknown_ts(ts: Optional[str]) -> bool:
    if not ts:
        return True
    t = ts.strip().lower()
    return t in ("unknown", "n/a", "none", "") or parse_clinical_date(ts) is None


def _edge_total(ev: TimelineEventVision) -> int:
    return sum(len(v) for v in ev.connascence.values())


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tool_meta(tool: str, strategy_id: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    out = {
        "tool": tool,
        "strategy_id": strategy_id,
        "generated_at": _iso_now(),
    }
    if extra:
        out.update(extra)
    return out


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def graph_snapshot(vision: PatientTimelineVision, args: Dict[str, Any]) -> Dict[str, Any]:
    snap = vision.snapshot()
    return {**_tool_meta("graph_snapshot", "S1"), "snapshot": snap}


def _latest_parseable_date_in_vision(vision: PatientTimelineVision) -> Optional[datetime]:
    latest: Optional[datetime] = None
    for ev in vision.events.values():
        dt = parse_clinical_date(ev.timestamp) if ev.timestamp else None
        if dt is not None and (latest is None or dt > latest):
            latest = dt
    return latest


def _temporal_bounds_from_reduce_args(
    vision: PatientTimelineVision, args: Dict[str, Any]
) -> Tuple[Optional[datetime], Optional[datetime], Optional[str]]:
    """
    Optional [start, end] inclusive window for graph_reduce.

    - recent_years (float): keep events in [anchor - window, anchor]. anchor is
      latest_in_corpus (max parseable event time) or utc_now.
    - temporal_start / temporal_end: explicit bounds (ISO strings), either may be omitted for open end.
    Returns (start, end, skip_reason). skip_reason set => do not apply temporal filter.
    """
    from datetime import timedelta

    rs = args.get("temporal_start")
    re = args.get("temporal_end")
    ry = args.get("recent_years")

    if ry is not None:
        try:
            ry_f = float(ry)
        except (TypeError, ValueError):
            return None, None, "invalid_recent_years"
        if ry_f <= 0:
            return None, None, "recent_years_non_positive"
        anchor_mode = str(args.get("temporal_anchor", "latest_in_corpus")).lower()
        if anchor_mode == "utc_now":
            end = datetime.now(timezone.utc)
        else:
            end = _latest_parseable_date_in_vision(vision)
            if end is None:
                return None, None, "no_parseable_dates_for_anchor"
        days = max(1, int(ry_f * 365.25))
        start = end - timedelta(days=days)
        return start, end, None

    if rs or re:
        t_start = parse_clinical_date(str(rs)) if rs else None
        t_end = parse_clinical_date(str(re)) if re else None
        return t_start, t_end, None

    return None, None, None


def graph_reduce(vision: PatientTimelineVision, args: Dict[str, Any]) -> Dict[str, Any]:
    drop_page = bool(args.get("drop_page", True))
    drop_unknown_timestamp = bool(args.get("drop_unknown_timestamp", True))
    drop_isolates = bool(args.get("drop_isolates", True))
    status_in: Optional[Set[str]] = None
    if args.get("status_in"):
        status_in = {str(x) for x in args["status_in"]}

    t_lo, t_hi, t_skip = _temporal_bounds_from_reduce_args(vision, args)
    apply_temporal = (t_lo is not None or t_hi is not None) and t_skip is None
    temporal_meta: Optional[Dict[str, Any]] = None
    if apply_temporal:
        temporal_meta = {
            "start": t_lo.isoformat() if t_lo is not None else None,
            "end": t_hi.isoformat() if t_hi is not None else None,
            "recent_years": args.get("recent_years"),
            "temporal_anchor": args.get("temporal_anchor"),
            "temporal_start_arg": args.get("temporal_start"),
            "temporal_end_arg": args.get("temporal_end"),
        }
    elif t_skip:
        temporal_meta = {"inactive_reason": t_skip}

    kept: List[str] = []
    dropped: List[Dict[str, str]] = []
    for eid, ev in vision.events.items():
        reasons: List[str] = []
        if status_in is not None and ev.status not in status_in:
            reasons.append("status_filter")
        if drop_page and ev.event_type == "page":
            reasons.append("page")
        if drop_unknown_timestamp and _unknown_ts(ev.timestamp):
            reasons.append("unknown_timestamp")
        if drop_isolates and _edge_total(ev) == 0:
            reasons.append("isolate")
        if apply_temporal:
            dt = parse_clinical_date(ev.timestamp) if ev.timestamp else None
            if dt is None:
                reasons.append("temporal_unparsed_date")
            else:
                if t_lo is not None and dt < t_lo:
                    reasons.append("temporal_before_window")
                if t_hi is not None and dt > t_hi:
                    reasons.append("temporal_after_window")
        if reasons:
            dropped.append({"event_id": eid, "reasons": ",".join(reasons)})
        else:
            kept.append(eid)
    out: Dict[str, Any] = {
        **_tool_meta("graph_reduce", "S2"),
        "event_ids": kept,
        "kept_count": len(kept),
        "dropped_count": len(dropped),
        "dropped_sample": dropped[:50],
    }
    if temporal_meta is not None:
        out["temporal_filter"] = temporal_meta
    return out


def graph_token_budget(vision: PatientTimelineVision, args: Dict[str, Any]) -> Dict[str, Any]:
    max_tokens = int(args.get("max_tokens", 12000))
    query = str(args.get("query", "") or "").lower()
    q_terms = [t for t in re.split(r"\W+", query) if len(t) > 2][:24]
    prefer_recent = bool(args.get("prefer_recent", True))
    raw_ids: List[str] = args.get("event_ids") or list(vision.events.keys())

    max_deg = 1
    for eid in raw_ids:
        ev = vision.events.get(eid)
        if ev:
            max_deg = max(max_deg, _edge_total(ev))

    def recency_score(ev: TimelineEventVision) -> float:
        dt = parse_clinical_date(ev.timestamp) if ev.timestamp else None
        if dt is None:
            return 0.0
        # newer → higher (rough ordinal)
        return min(1.0, (dt.year - 1970) / 60.0)

    scored: List[Tuple[float, str]] = []
    for eid in raw_ids:
        ev = vision.events.get(eid)
        if ev is None:
            continue
        deg = _edge_total(ev)
        text = (ev.preview + " " + ev.event_type).lower()
        q_hit = sum(1 for t in q_terms if t in text) / max(1, len(q_terms)) if q_terms else 0.0
        deg_n = deg / max_deg
        r = recency_score(ev) if prefer_recent else 0.5
        score = 0.45 * deg_n + 0.35 * r + 0.20 * q_hit
        scored.append((score, eid))
    scored.sort(key=lambda x: x[0], reverse=True)

    picked: List[str] = []
    token_sum = 0
    for _, eid in scored:
        ev = vision.events.get(eid)
        if ev is None:
            continue
        cost = max(1, len(ev.preview) // 4)
        if token_sum + cost > max_tokens:
            break
        token_sum += cost
        picked.append(eid)

    return {
        **_tool_meta("graph_token_budget", "S3"),
        "event_ids": picked,
        "estimated_tokens": token_sum,
        "max_tokens": max_tokens,
        "considered": len(scored),
    }


def graph_bfs_expand(vision: PatientTimelineVision, args: Dict[str, Any]) -> Dict[str, Any]:
    max_depth = int(args.get("max_depth", 2))
    max_nodes = int(args.get("max_nodes", 400))
    edge_types = args.get("edge_types")
    et_filter: Optional[Set[str]] = set(edge_types) if edge_types else None
    restrict: Optional[Set[str]] = None
    if args.get("restrict_to_event_ids"):
        restrict = {str(x) for x in args["restrict_to_event_ids"] if str(x) in vision.events}

    multi = args.get("seed_event_ids")
    if multi:
        seeds = [str(s) for s in multi if str(s) in vision.events]
    else:
        one = str(args.get("seed_event_id", ""))
        seeds = [one] if one in vision.events else []

    if not seeds:
        return {**_tool_meta("graph_bfs_expand", "S4", {"error": "unknown_seed"}), "event_ids": []}

    if restrict is not None:
        seeds = [s for s in seeds if s in restrict]
    if not seeds:
        return {**_tool_meta("graph_bfs_expand", "S4", {"error": "no_seed_in_restrict_set"}), "event_ids": []}

    visited: Set[str] = set()
    queue: deque[Tuple[str, int]] = deque((s, 0) for s in seeds)
    result: List[str] = []
    while queue and len(result) < max_nodes:
        eid, d = queue.popleft()
        if eid in visited:
            continue
        visited.add(eid)
        result.append(eid)
        if d >= max_depth:
            continue
        ev = vision.events.get(eid)
        if not ev:
            continue
        for kind, targets in ev.connascence.items():
            if et_filter is not None and kind not in et_filter:
                continue
            for tid in targets:
                if tid not in visited and tid in vision.events:
                    if restrict is not None and tid not in restrict:
                        continue
                    queue.append((tid, d + 1))
    primary_seed = seeds[0] if len(seeds) == 1 else None
    meta = {**_tool_meta("graph_bfs_expand", "S4"), "event_ids": result, "max_depth": max_depth, "seeds": seeds}
    if primary_seed is not None:
        meta["seed"] = primary_seed
    if restrict is not None:
        meta["restricted"] = True
    return meta


def _build_undirected_simple(vision: PatientTimelineVision, event_subset: Optional[Set[str]] = None) -> Any:
    if nx is None:
        return None
    G = nx.Graph()
    for eid, ev in vision.events.items():
        if event_subset is not None and eid not in event_subset:
            continue
        G.add_node(eid)
        for _kind, targets in ev.connascence.items():
            for tid in targets:
                if tid not in vision.events:
                    continue
                if event_subset is not None and tid not in event_subset:
                    continue
                G.add_edge(eid, tid)
    return G


def graph_centrality(vision: PatientTimelineVision, args: Dict[str, Any]) -> Dict[str, Any]:
    if nx is None:
        return {**_tool_meta("graph_centrality", "S5", {"error": "networkx_not_installed"}), "top": []}
    subset = set(args["event_ids"]) if args.get("event_ids") else None
    G = _build_undirected_simple(vision, subset)
    if G is None or G.number_of_nodes() == 0:
        return {**_tool_meta("graph_centrality", "S5"), "top": [], "note": "empty_graph"}

    top_k = int(args.get("top_k", 40))
    deg = nx.degree_centrality(G)
    # sampled betweenness for large graphs
    n = G.number_of_nodes()
    k = min(400, max(50, n))
    between = nx.betweenness_centrality(G, k=k, seed=42) if n > 2 else {n: 0.0 for n in G.nodes()}

    eig = {}
    try:
        if n > 1 and nx.is_connected(G):
            eig = nx.eigenvector_centrality_numpy(G, max_iter=500)
    except Exception:
        eig = {}

    combined: Dict[str, float] = {}
    for nid in G.nodes():
        combined[nid] = (
            0.5 * deg.get(nid, 0.0)
            + 0.35 * between.get(nid, 0.0)
            + 0.15 * eig.get(nid, 0.0)
        )
    ranked = sorted(combined.items(), key=lambda x: x[1], reverse=True)[:top_k]
    return {
        **_tool_meta("graph_centrality", "S5"),
        "top": [{"event_id": eid, "score": round(s, 6)} for eid, s in ranked],
        "node_count": n,
        "edge_count": G.number_of_edges(),
    }


def graph_kcore(vision: PatientTimelineVision, args: Dict[str, Any]) -> Dict[str, Any]:
    if nx is None:
        return {**_tool_meta("graph_kcore", "S6", {"error": "networkx_not_installed"}), "core": []}
    subset = set(args["event_ids"]) if args.get("event_ids") else None
    G = _build_undirected_simple(vision, subset)
    if G is None or G.number_of_nodes() == 0:
        return {**_tool_meta("graph_kcore", "S6"), "core": []}
    kmin = int(args.get("k", 2))
    core_num = nx.core_number(G)
    core_nodes = [n for n, k in core_num.items() if k >= kmin]
    core_nodes.sort(key=lambda nid: core_num[nid], reverse=True)
    max_out = int(args.get("max_nodes", 200))
    return {
        **_tool_meta("graph_kcore", "S6"),
        "k": kmin,
        "core_numbers_sample": {n: core_num[n] for n in core_nodes[:30]},
        "event_ids": core_nodes[:max_out],
        "count": len(core_nodes),
    }


def graph_bridges(vision: PatientTimelineVision, args: Dict[str, Any]) -> Dict[str, Any]:
    if nx is None:
        return {**_tool_meta("graph_bridges", "S7", {"error": "networkx_not_installed"}), "bridges": []}
    subset = set(args["event_ids"]) if args.get("event_ids") else None
    G = _build_undirected_simple(vision, subset)
    if G is None or G.number_of_nodes() == 0:
        return {**_tool_meta("graph_bridges", "S7"), "bridges": [], "articulation_points": []}
    max_b = int(args.get("max_bridges", 80))
    bridges = []
    for u, v in nx.bridges(G):
        bridges.append({"u": u, "v": v})
        if len(bridges) >= max_b:
            break
    arts = list(nx.articulation_points(G))[: max_b]
    return {
        **_tool_meta("graph_bridges", "S7"),
        "bridges": bridges,
        "articulation_points": arts,
    }


def _portal_ic(x0: float, y0: float, z0: float, ev: TimelineEventVision, max_deg: int) -> Tuple[float, float, float]:
    """Map event → Lorenz initial conditions (PE-style: degree, edge mass, vitality)."""
    deg = _edge_total(ev)
    x = (deg / max_deg) * 2.0 - 1.0 if max_deg else 0.0
    y = min(1.0, y0 + 0.1 * (1 if ev.event_type in ("diagnosis", "lab") else 0))
    dt = parse_clinical_date(ev.timestamp) if ev.timestamp else None
    if dt is None:
        z = 0.15
    else:
        z = min(1.0, math.log(1 + (dt.year - 1970)) / math.log(1 + (2026 - 1970)))
    return float(x), float(y), float(z)


def graph_pe_lorenz_classify(vision: PatientTimelineVision, args: Dict[str, Any]) -> Dict[str, Any]:
    if np is None:
        return {**_tool_meta("graph_pe_lorenz_classify", "S8", {"error": "numpy_not_installed"}), "items": []}
    eids: List[str] = args.get("event_ids") or list(vision.events.keys())[:400]
    rho = float(args.get("rho", 28.0))
    tau = float(args.get("tau", 2.0))
    steps = int(args.get("steps", 2000))
    max_deg = max((_edge_total(vision.events[e]) for e in eids if e in vision.events), default=1)

    items: List[Dict[str, Any]] = []
    for eid in eids:
        ev = vision.events.get(eid)
        if ev is None:
            continue
        y0 = 0.25 + 0.02 * min(10, len(ev.preview) / 200.0)
        x0, y0, z0 = _portal_ic(0.0, y0, 0.0, ev, max_deg=max_deg)
        xs = _rk4_lorenz_traj(x0, y0, z0, rho=rho, steps=steps, dt=0.01)
        label, mean_x = _classify_from_traj(xs, tau=tau)
        load_bearing = ev.event_type == "diagnosis" or _edge_total(ev) > 12
        items.append(
            {
                "event_id": eid,
                "classification": label,
                "mean_x": round(mean_x, 5),
                "load_bearing": load_bearing,
                "x0": round(x0, 5),
                "y0": round(y0, 5),
                "z0": round(z0, 5),
            }
        )
    return {
        **_tool_meta("graph_pe_lorenz_classify", "S8"),
        "rho": rho,
        "tau": tau,
        "steps": steps,
        "items": items,
    }


def graph_pe_sweep(vision: PatientTimelineVision, args: Dict[str, Any]) -> Dict[str, Any]:
    """Coarse grid over ρ and τ on a random-ish subset for speed."""
    if np is None:
        return {**_tool_meta("graph_pe_sweep", "S9", {"error": "numpy_not_installed"}), "grid": []}
    sample_n = int(args.get("sample_nodes", 300))
    all_ids = list(vision.events.keys())
    step_pick = max(1, len(all_ids) // sample_n)
    sample = all_ids[::step_pick][:sample_n]
    rho_vals = args.get("rho_values") or [22.0, 26.0, 28.0, 30.0, 34.0]
    tau_vals = args.get("tau_values") or [1.0, 1.5, 2.0, 2.5, 3.0]
    grid: List[Dict[str, Any]] = []
    for rho in rho_vals:
        for tau in tau_vals:
            sub = graph_pe_lorenz_classify(vision, {"event_ids": sample, "rho": float(rho), "tau": float(tau), "steps": 1200})
            labels = Counter(it["classification"] for it in sub["items"])
            n = max(1, len(sub["items"]))
            grid.append(
                {
                    "rho": float(rho),
                    "tau": float(tau),
                    "keep_pct": round(labels.get("KEEP", 0) / n, 4),
                    "evict_pct": round(labels.get("EVICT", 0) / n, 4),
                    "review_pct": round(labels.get("REVIEW", 0) / n, 4),
                }
            )
    stable = [g for g in grid if g["evict_pct"] < 0.30]
    return {**_tool_meta("graph_pe_sweep", "S9"), "grid": grid, "stable_band_candidates": stable[:12]}


def graph_pe_govern_adjust(vision: PatientTimelineVision, args: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic governance: protect load-bearing / diagnosis from silent EVICT."""
    items = args.get("items") or []
    adjusted: List[Dict[str, Any]] = []
    for row in items:
        eid = row.get("event_id")
        cls = row.get("classification")
        ev = vision.events.get(str(eid)) if eid else None
        load_bearing = bool(row.get("load_bearing"))
        if ev:
            load_bearing = load_bearing or ev.event_type == "diagnosis" or _edge_total(ev) > 12
        new_cls = cls
        reason = None
        if cls == "EVICT" and load_bearing:
            new_cls = "REVIEW"
            reason = "load_bearing_evict_blocked"
        adjusted.append(
            {
                "event_id": eid,
                "classification_before": cls,
                "classification_after": new_cls,
                "reason": reason,
            }
        )
    return {**_tool_meta("graph_pe_govern_adjust", "S10"), "items": adjusted}


def _rrf_merge(*ranked_lists: List[str], k: int = 60) -> List[str]:
    scores: Dict[str, float] = defaultdict(float)
    for rl in ranked_lists:
        for rank, eid in enumerate(rl):
            scores[eid] += 1.0 / (k + rank + 1)
    return sorted(scores.keys(), key=lambda x: scores[x], reverse=True)


def _keyword_rank(
    vision: PatientTimelineVision,
    query: str,
    limit: int,
    subset: Optional[Set[str]] = None,
) -> List[str]:
    terms = [t for t in re.split(r"\W+", query.lower()) if len(t) > 2][:20]
    if not terms:
        return []
    scored: List[Tuple[int, str]] = []
    for e in vision.events.values():
        if subset is not None and e.event_id not in subset:
            continue
        text = (e.preview + " " + e.event_type).lower()
        hits = sum(1 for t in terms if t in text)
        if hits:
            scored.append((hits, e.event_id))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [eid for _, eid in scored[:limit]]


_ST_MODEL = None


def _semantic_rank(
    vision: PatientTimelineVision,
    query: str,
    limit: int,
    subset: Optional[Set[str]] = None,
) -> Tuple[List[str], Optional[str]]:
    """
    Cosine similarity rank of events vs query embedding.
    Returns (event_ids, skip_reason). skip_reason is set when semantic is unavailable
    (missing deps) so callers can surface it instead of silently using keyword-only.
    """
    global _ST_MODEL
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        return [], (
            "semantic skipped: sentence-transformers not installed "
            "(install with: pip install 'sentence-transformers>=3' — see server/requirements.txt)"
        )
    if np is None:
        return [], "semantic skipped: numpy not installed"

    texts = []
    ids = []
    for e in vision.events.values():
        if subset is not None and e.event_id not in subset:
            continue
        texts.append(_event_text(e))
        ids.append(e.event_id)
    if not ids:
        return [], "semantic skipped: no events in corpus (empty subset)"

    if _ST_MODEL is None:
        if os.environ.get("GRAPH_SEMANTIC_VERBOSE", "").strip().lower() in ("1", "true", "yes"):
            print(
                "[graph_hybrid_search] loading SentenceTransformer "
                "sentence-transformers/all-MiniLM-L6-v2 (first call only) ...",
                file=sys.stderr,
                flush=True,
            )
        _ST_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
    model = _ST_MODEL
    qv = model.encode([query], show_progress_bar=False)[0].astype(np.float32)
    embs = model.encode(texts, show_progress_bar=len(texts) > 300, batch_size=64)
    embs = np.asarray(embs, dtype=np.float32)
    qn = np.linalg.norm(qv)
    scores = []
    for i, eid in enumerate(ids):
        ev = embs[i]
        s = float(np.dot(qv, ev) / (qn * np.linalg.norm(ev) + 1e-9))
        scores.append((s, eid))
    scores.sort(key=lambda x: x[0], reverse=True)
    return [eid for _, eid in scores[:limit]], None


def graph_hybrid_search(vision: PatientTimelineVision, args: Dict[str, Any]) -> Dict[str, Any]:
    query = str(args.get("query", "")).strip()
    top_k = int(args.get("top_k", 30))
    use_semantic = bool(args.get("semantic", True))
    subset: Optional[Set[str]] = None
    raw_ids = args.get("event_ids")
    if raw_ids:
        subset = {str(x) for x in raw_ids if str(x) in vision.events}
    if not query:
        return {**_tool_meta("graph_hybrid_search", "S11", {"error": "empty_query"}), "event_ids": []}
    kw = _keyword_rank(vision, query, top_k, subset)
    sem: List[str] = []
    sem_note: Optional[str] = None
    if use_semantic:
        try:
            sem, sem_note = _semantic_rank(vision, query, top_k, subset)
        except Exception as exc:  # pragma: no cover
            sem_note = f"semantic error: {exc.__class__.__name__}: {exc}"
    merged = _rrf_merge(kw, sem) if sem else kw
    merged = merged[:top_k]
    out = {
        **_tool_meta("graph_hybrid_search", "S11"),
        "event_ids": merged,
        "keyword_hits": len(kw),
        "semantic_hits": len(sem),
        "corpus_scope": "subset" if subset is not None else "full_graph",
        "corpus_size": len(subset) if subset is not None else len(vision.events),
    }
    if sem_note:
        out["note"] = sem_note
    return out


_LAB_PATTERNS = {
    "a1c": re.compile(r"(?:hgb\s*)?a1c\s*[%:]?\s*(\d+\.?\d*)", re.I),
    "crp": re.compile(r"crp\s*[:\s]*(\d+\.?\d*)", re.I),
    "esr": re.compile(r"esr\s*[:\s]*(\d+\.?\d*)", re.I),
}


def graph_biomarker_icm(vision: PatientTimelineVision, args: Dict[str, Any]) -> Dict[str, Any]:
    biomarkers = [str(b).lower() for b in (args.get("biomarkers") or ["a1c", "crp", "esr"])]
    ic_max = float(args.get("ic_max", 100.0))
    series: Dict[str, List[Dict[str, Any]]] = {b: [] for b in biomarkers if b in _LAB_PATTERNS}
    dated_events: List[Tuple[datetime, str, TimelineEventVision]] = []
    for eid, ev in vision.events.items():
        dt = parse_clinical_date(ev.timestamp) if ev.timestamp else None
        if dt:
            dated_events.append((dt, eid, ev))
    dated_events.sort(key=lambda x: x[0])
    for dt, eid, ev in dated_events:
        if ev.event_type != "lab":
            continue
        text = ev.preview
        for b in biomarkers:
            pat = _LAB_PATTERNS.get(b)
            if not pat:
                continue
            m = pat.search(text)
            if m:
                try:
                    val = float(m.group(1))
                except ValueError:
                    continue
                series[b].append({"event_id": eid, "date": dt.strftime("%Y-%m-%d"), "value": val})

    # lightweight ICM trace: inflow from CRP-like signal if present
    ic = 0.0
    trace: List[Dict[str, Any]] = []
    for dt, eid, ev in dated_events:
        infl = 0.0
        if "crp" in series:
            # if this event is latest crp-containing lab snippet
            pass
        text = ev.preview.lower()
        if "crp" in text or "esr" in text or "inflamm" in text:
            infl += 2.0
        if ev.event_type == "symptom":
            infl += 1.5
        if ev.event_type == "diagnosis":
            infl += 1.0
        outflow = 0.08 * ic
        ic = max(0.0, min(ic_max, ic + infl - outflow))
        if infl > 0 or ic > 1:
            trace.append(
                {
                    "event_id": eid,
                    "date": dt.strftime("%Y-%m-%d"),
                    "ic_level": round(ic, 2),
                    "ic_pct": round(100.0 * ic / ic_max, 2),
                    "inflow": round(infl, 2),
                }
            )
        if len(trace) >= 400:
            break

    return {
        **_tool_meta("graph_biomarker_icm", "S12"),
        "series": series,
        "icm_trace_sample": trace[:120],
        "note": "ICM is a lightweight heuristic for agent context — not a calibrated M68 engine.",
    }


_TOOL_REGISTRY: Dict[str, Callable[[PatientTimelineVision, Dict[str, Any]], Dict[str, Any]]] = {
    "graph_snapshot": graph_snapshot,
    "graph_reduce": graph_reduce,
    "graph_token_budget": graph_token_budget,
    "graph_bfs_expand": graph_bfs_expand,
    "graph_centrality": graph_centrality,
    "graph_kcore": graph_kcore,
    "graph_bridges": graph_bridges,
    "graph_pe_lorenz_classify": graph_pe_lorenz_classify,
    "graph_pe_sweep": graph_pe_sweep,
    "graph_pe_govern_adjust": graph_pe_govern_adjust,
    "graph_hybrid_search": graph_hybrid_search,
    "graph_biomarker_icm": graph_biomarker_icm,
}


GRAPH_TOOL_DEFINITIONS: List[Dict[str, Any]] = [
    {"name": "graph_snapshot", "strategy_id": "S1", "summary": "PTV shape: types, date ranges, per-node edge counts.", "args": {}},
    {"name": "graph_reduce", "strategy_id": "S2", "summary": "Drop page / unknown-date / isolate nodes (configurable).", "args": {"drop_page": True, "drop_unknown_timestamp": True, "drop_isolates": True}},
    {"name": "graph_token_budget", "strategy_id": "S3", "summary": "Rank events and pack into max_tokens budget.", "args": {"event_ids": [], "max_tokens": 12000, "query": "", "prefer_recent": True}},
    {
        "name": "graph_bfs_expand",
        "strategy_id": "S4",
        "summary": "BFS from one seed or many (seed_event_ids); optional restrict_to_event_ids keeps expansion on a subgraph (e.g. post-reduce).",
        "args": {
            "seed_event_id": "",
            "seed_event_ids": None,
            "max_depth": 2,
            "edge_types": None,
            "max_nodes": 400,
            "restrict_to_event_ids": None,
        },
    },
    {"name": "graph_centrality", "strategy_id": "S5", "summary": "Degree + sampled betweenness + eigenvector (undirected projection).", "args": {"event_ids": None, "top_k": 40}},
    {"name": "graph_kcore", "strategy_id": "S6", "summary": "k-core decomposition for dense clinical core.", "args": {"event_ids": None, "k": 2, "max_nodes": 200}},
    {"name": "graph_bridges", "strategy_id": "S7", "summary": "Bridges and articulation points (narrative pivots).", "args": {"event_ids": None, "max_bridges": 80}},
    {"name": "graph_pe_lorenz_classify", "strategy_id": "S8", "summary": "Lorenz RK4 wing classification: KEEP / EVICT / REVIEW.", "args": {"event_ids": [], "rho": 28.0, "tau": 2.0, "steps": 2000}},
    {"name": "graph_pe_sweep", "strategy_id": "S9", "summary": "ρ×τ grid on a sample; returns eviction/keep rates.", "args": {"sample_nodes": 300, "rho_values": None, "tau_values": None}},
    {"name": "graph_pe_govern_adjust", "strategy_id": "S10", "summary": "Promote EVICT→REVIEW for load-bearing / dense diagnosis nodes.", "args": {"items": []}},
    {
        "name": "graph_hybrid_search",
        "strategy_id": "S11",
        "summary": "BM25-style keywords + optional sentence-transformers cosine, RRF-fused. Pass event_ids to search only a subset (e.g. after graph_reduce).",
        "args": {"query": "", "top_k": 30, "semantic": True, "event_ids": None},
    },
    {"name": "graph_biomarker_icm", "strategy_id": "S12", "summary": "Regex lab series (A1c/CRP/ESR) + lightweight ICM headroom trace.", "args": {"biomarkers": ["a1c", "crp", "esr"], "ic_max": 100.0}},
]


def list_graph_tool_names() -> List[str]:
    return sorted(_TOOL_REGISTRY.keys())


def execute_graph_tool(name: str, vision: PatientTimelineVision, args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    fn = _TOOL_REGISTRY.get(name)
    if fn is None:
        return {"tool": name, "error": "unknown_tool", "known": list_graph_tool_names()}
    return fn(vision, dict(args or {}))
