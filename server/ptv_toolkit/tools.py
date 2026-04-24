"""
tools.py — deterministic graph tools called by the agent.

Every tool:
* Takes ``(gh: GraphHandle, args: dict)`` and returns a JSON-serializable
  ``dict``.
* Returns ``{"tool": <name>, "args": ..., "result": {...}}`` when used
  directly, but the :mod:`registry` wrapper adds the envelope; the
  tool functions themselves return just the ``result`` payload so they
  can be composed internally.
* Caps every list in the response (``max_events`` / ``limit``) so the
  agent context never blows up.
"""
from __future__ import annotations

import logging
import re
from collections import deque
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from .graph import CONNASCENCE_KINDS, GraphHandle, _parse_iso

logger = logging.getLogger(__name__)

DEFAULT_SEARCH_K = 12
DEFAULT_BFS_MAX = 40
DEFAULT_TEMPORAL_LIMIT = 40
DEFAULT_LOOKUP_LIMIT = 50


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def _event_card(gh: GraphHandle, event_id: str) -> Dict[str, Any]:
    """Compact event summary returned in tool results (bounded size)."""
    ev = gh.events.get(event_id)
    if not ev:
        return {"event_id": event_id, "missing": True}
    ann = ev.get("annotations") or {}
    card = ann.get("card") or {}
    return {
        "event_id": event_id,
        "event_type": ev.get("event_type"),
        "timestamp": ev.get("timestamp"),
        "title": (card.get("title") or "")[:120],
        "one_line": (card.get("one_line") or "")[:160],
        "icd": card.get("icd"),
        "drug": card.get("drug"),
        "salience": ann.get("salience"),
        "preview": (ev.get("preview") or "")[:200].replace("\n", " "),
    }


def _event_cards(gh: GraphHandle, event_ids: Iterable[str], limit: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for eid in event_ids:
        if len(out) >= limit:
            break
        out.append(_event_card(gh, eid))
    return out


def _require_str(args: Dict[str, Any], name: str) -> str:
    v = args.get(name)
    if not isinstance(v, str) or not v.strip():
        raise ValueError(f"tool arg '{name}' must be a non-empty string")
    return v.strip()


def _opt_int(args: Dict[str, Any], name: str, default: int, *, minimum: int = 1, maximum: int = 500) -> int:
    v = args.get(name, default)
    try:
        v = int(v)
    except Exception:
        v = default
    return max(minimum, min(maximum, v))


def _opt_str_list(args: Dict[str, Any], name: str) -> List[str]:
    v = args.get(name) or []
    if isinstance(v, str):
        v = [v]
    return [str(x) for x in v if isinstance(x, (str, int))]


# ---------------------------------------------------------------------------
# 1) graph_stats — cold-start snapshot
# ---------------------------------------------------------------------------

def graph_stats(gh: GraphHandle, args: Dict[str, Any]) -> Dict[str, Any]:
    snap = gh.snapshot()
    snap["connascence_kinds"] = list(CONNASCENCE_KINDS)
    return snap


# ---------------------------------------------------------------------------
# 2) list_event_types — enumeration
# ---------------------------------------------------------------------------

def list_event_types(gh: GraphHandle, args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "event_types": sorted(gh.by_type.keys()),
        "counts": {t: len(ids) for t, ids in gh.by_type.items()},
    }


# ---------------------------------------------------------------------------
# 3) code_index_lookup — flat per-code chronology
# ---------------------------------------------------------------------------

_BUCKETS = ("drugs", "rxnorm", "icd", "labs", "loinc")


def code_index_lookup(gh: GraphHandle, args: Dict[str, Any]) -> Dict[str, Any]:
    bucket = _require_str(args, "bucket").lower()
    if bucket not in _BUCKETS:
        raise ValueError(f"bucket must be one of {_BUCKETS}, got '{bucket}'")

    table = (gh.code_index or {}).get(bucket) or {}
    if not isinstance(table, dict):
        table = {}

    limit = _opt_int(args, "limit", DEFAULT_LOOKUP_LIMIT, minimum=1, maximum=500)

    exact_key = args.get("key")
    key_contains = args.get("key_contains")

    # Listing mode: no key provided -> return the top-n keys by event count.
    if not exact_key and not key_contains:
        sorted_keys = sorted(table.items(), key=lambda kv: -len(kv[1]))
        return {
            "bucket": bucket,
            "mode": "list_keys",
            "n_keys_total": len(table),
            "keys": [
                {"key": k, "n_events": len(v), "first": (v[0].get("timestamp") if v else None),
                 "last": (v[-1].get("timestamp") if v else None)}
                for k, v in sorted_keys[:limit]
            ],
        }

    # Lookup mode.
    if exact_key:
        key = str(exact_key).strip()
        if bucket == "icd":
            key = key.upper()
        else:
            key = key.lower()
        rows = table.get(key) or []
        return {
            "bucket": bucket,
            "mode": "exact",
            "key": key,
            "n_events": len(rows),
            "entries": rows[:limit],
        }

    # Substring mode.
    needle = str(key_contains).strip().lower()
    matches: List[Tuple[str, List[Dict[str, Any]]]] = []
    for k, rows in table.items():
        if needle in str(k).lower():
            matches.append((k, rows))
    matches.sort(key=lambda kv: -len(kv[1]))
    return {
        "bucket": bucket,
        "mode": "contains",
        "key_contains": needle,
        "n_keys_matched": len(matches),
        "keys": [
            {"key": k, "n_events": len(v), "entries": v[:10]}
            for k, v in matches[:limit]
        ],
    }


# ---------------------------------------------------------------------------
# 4) get_event — full detail fetch
# ---------------------------------------------------------------------------

_FIELD_ALLOWLIST = (
    "event_id", "event_type", "timestamp", "preview",
    "annotations", "connascence", "discovered_by", "status",
)


def get_event(gh: GraphHandle, args: Dict[str, Any]) -> Dict[str, Any]:
    eid = _require_str(args, "event_id")
    ev = gh.events.get(eid)
    if not ev:
        return {"event_id": eid, "missing": True}
    out: Dict[str, Any] = {"event_id": eid}
    for k in _FIELD_ALLOWLIST:
        if k in ev:
            v = ev[k]
            if k == "preview" and isinstance(v, str):
                v = v[:800]
            out[k] = v
    return out


# ---------------------------------------------------------------------------
# 5) semantic_search — sentence-transformers over event text
# ---------------------------------------------------------------------------

def semantic_search(gh: GraphHandle, args: Dict[str, Any]) -> Dict[str, Any]:
    """Cosine search over event embeddings with optional subset / type filters.

    Rerank mode: when ``event_ids`` is provided, search is restricted to
    those ids and the result is effectively a ranked reordering. This is
    the primary way to combine semantic_search with another primitive
    (temporal_scan -> rerank the window, code_index_lookup -> rerank a
    drug's chronology, etc.).
    """
    query = _require_str(args, "query")
    k = _opt_int(args, "k", DEFAULT_SEARCH_K, minimum=1, maximum=50)
    event_types = _opt_str_list(args, "event_types")
    event_ids = _opt_str_list(args, "event_ids")

    allowed: Optional[Set[str]] = None
    filters_applied: Dict[str, Any] = {}

    if event_ids:
        subset = {eid for eid in event_ids if eid in gh.events}
        if not subset:
            return {
                "query": query,
                "filter": {"event_ids": event_ids},
                "results": [],
                "note": "none of the supplied event_ids exist in the graph",
            }
        allowed = subset
        filters_applied["event_ids_in"] = len(subset)

    if event_types:
        type_ids: Set[str] = set()
        for t in event_types:
            type_ids.update(gh.by_type.get(t, []))
        if not type_ids:
            return {
                "query": query,
                "filter": {"event_types": event_types},
                "results": [],
                "note": "no events match the requested event_types",
            }
        allowed = type_ids if allowed is None else (allowed & type_ids)
        filters_applied["event_types"] = event_types
        if not allowed:
            return {
                "query": query,
                "filter": filters_applied,
                "results": [],
                "note": "event_ids filter and event_types filter do not overlap",
            }

    try:
        from .embeddings import get_or_build_store
    except Exception as exc:  # noqa: BLE001
        return {
            "query": query,
            "results": [],
            "error": f"semantic_search unavailable: {exc}",
        }

    store = get_or_build_store(gh)
    hits = store.search(query, k=k, allowed_event_ids=allowed)
    results = []
    for eid, score in hits:
        card = _event_card(gh, eid)
        card["score"] = round(score, 4)
        results.append(card)
    return {
        "query": query,
        "filter": filters_applied or None,
        "k": k,
        "model": store.model_name,
        "mode": "rerank" if event_ids else "full",
        "results": results,
    }


# ---------------------------------------------------------------------------
# 6) bfs_expand — typed multi-seed BFS
# ---------------------------------------------------------------------------

def bfs_expand(gh: GraphHandle, args: Dict[str, Any]) -> Dict[str, Any]:
    seeds = _opt_str_list(args, "seed_event_ids")
    if not seeds:
        raise ValueError("bfs_expand requires non-empty 'seed_event_ids'")

    edge_kinds = _opt_str_list(args, "edge_kinds") or list(CONNASCENCE_KINDS)
    bad = [k for k in edge_kinds if k not in CONNASCENCE_KINDS]
    if bad:
        raise ValueError(f"unknown edge_kinds: {bad}; allowed={list(CONNASCENCE_KINDS)}")

    depth = _opt_int(args, "depth", 1, minimum=1, maximum=4)
    max_events = _opt_int(args, "max_events", DEFAULT_BFS_MAX, minimum=1, maximum=200)

    seen: Set[str] = set()
    order: List[Tuple[str, int, Optional[str], Optional[str]]] = []  # (eid, hop, parent, edge_kind)
    q: deque = deque()
    for s in seeds:
        if s in gh.events and s not in seen:
            seen.add(s)
            q.append((s, 0, None, None))
            order.append((s, 0, None, None))

    while q and len(order) < max_events:
        eid, hop, _parent, _kind = q.popleft()
        if hop >= depth:
            continue
        adj = gh.adjacency.get(eid) or {}
        for kind in edge_kinds:
            for nb in adj.get(kind, []):
                if nb in seen:
                    continue
                seen.add(nb)
                order.append((nb, hop + 1, eid, kind))
                q.append((nb, hop + 1, eid, kind))
                if len(order) >= max_events:
                    break
            if len(order) >= max_events:
                break

    events = []
    for eid, hop, parent, kind in order:
        card = _event_card(gh, eid)
        card["bfs_hop"] = hop
        if parent:
            card["bfs_parent"] = parent
            card["bfs_edge_kind"] = kind
        events.append(card)

    return {
        "seeds": [s for s in seeds if s in gh.events],
        "edge_kinds": edge_kinds,
        "depth": depth,
        "n_events": len(events),
        "truncated": len(order) >= max_events,
        "events": events,
    }


# ---------------------------------------------------------------------------
# 7) temporal_scan — event_type + window
# ---------------------------------------------------------------------------

_WORD_RX = re.compile(r"[A-Za-z][A-Za-z0-9\-]{2,}")


def _text_matches(ev: Dict[str, Any], needles: List[str]) -> bool:
    if not needles:
        return True
    hay = " ".join(
        str(p or "")
        for p in (
            ev.get("preview"),
            ((ev.get("annotations") or {}).get("card") or {}).get("one_line"),
            ((ev.get("annotations") or {}).get("card") or {}).get("title"),
        )
    ).lower()
    return all(n.lower() in hay for n in needles)


def temporal_scan(gh: GraphHandle, args: Dict[str, Any]) -> Dict[str, Any]:
    event_types = _opt_str_list(args, "event_types")
    start = args.get("start")
    end = args.get("end")
    query = (args.get("query") or "").strip() or None
    needles = _WORD_RX.findall(query) if query else []

    limit = _opt_int(args, "limit", DEFAULT_TEMPORAL_LIMIT, minimum=1, maximum=200)
    order = (args.get("order") or "asc").lower()

    start_iso = _parse_iso(start) if start else None
    end_iso = _parse_iso(end) if end else None

    # Build candidate list from by_date (+ optionally unknown-date if asked).
    include_unknown = bool(args.get("include_unknown_timestamps"))
    candidates: List[Tuple[str, str]] = []  # (iso, eid)
    for iso, eid in gh.by_date:
        if start_iso and iso < start_iso:
            continue
        if end_iso and iso > end_iso:
            continue
        candidates.append((iso, eid))
    if include_unknown:
        candidates.extend([("unknown", eid) for eid in gh.unknown_date])

    if order == "desc":
        candidates.sort(key=lambda t: t[0], reverse=True)

    # Filter by type and optional word needles.
    type_set = set(event_types) if event_types else None
    rows: List[Dict[str, Any]] = []
    for iso, eid in candidates:
        if len(rows) >= limit:
            break
        ev = gh.events.get(eid)
        if not ev:
            continue
        if type_set and ev.get("event_type") not in type_set:
            continue
        if needles and not _text_matches(ev, needles):
            continue
        card = _event_card(gh, eid)
        card["scan_date"] = iso
        rows.append(card)

    return {
        "event_types": event_types or None,
        "start": start_iso,
        "end": end_iso,
        "query": query,
        "order": order,
        "include_unknown_timestamps": include_unknown,
        "n_events": len(rows),
        "events": rows,
    }
