"""Patient code inventory from ``metadata.code_index`` (same source as ``code_index_lookup``).

Builds a full per-bucket list of keys with min/max ISO dates over index rows
(timeline grounding before source-router / MKG planning).
"""
from __future__ import annotations

import copy
import json
from typing import Any, Dict, List, Tuple

from server.ptv_toolkit.graph import GraphHandle, _parse_iso

CODE_INDEX_BUCKETS = ("drugs", "rxnorm", "icd", "labs", "loinc")


def _date_span_for_rows(rows: Any) -> Tuple[Optional[str], Optional[str]]:
    if not isinstance(rows, list):
        return None, None
    dates: List[str] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        d = _parse_iso(r.get("timestamp"))
        if d:
            dates.append(d)
    dates.sort()
    if not dates:
        return None, None
    return dates[0], dates[-1]


def build_patient_code_inventory(gh: GraphHandle) -> Dict[str, Any]:
    """Scan ``gh.code_index`` for all keys; first/last dates from row timestamps."""
    ci = gh.code_index or {}
    by_bucket: Dict[str, List[Dict[str, Any]]] = {}
    per_bucket_counts: Dict[str, int] = {}

    for bucket in CODE_INDEX_BUCKETS:
        table = ci.get(bucket) or {}
        if not isinstance(table, dict):
            table = {}
        items: List[Dict[str, Any]] = []
        for key, rows in table.items():
            if not isinstance(rows, list):
                continue
            first, last = _date_span_for_rows(rows)
            items.append(
                {
                    "key": key,
                    "first": first,
                    "last": last,
                    "n_events": len(rows),
                }
            )
        items.sort(key=lambda x: str(x.get("key") or "").lower())
        by_bucket[bucket] = items
        per_bucket_counts[bucket] = len(items)

    n_total = sum(per_bucket_counts.values())
    snap = gh.snapshot()
    return {
        "by_bucket": by_bucket,
        "n_keys_total": n_total,
        "n_keys_per_bucket": per_bucket_counts,
        "graph_timeline_range": snap.get("date_range") or {},
        "code_index_summary": snap.get("code_index_summary") or {},
    }


def strip_n_events(inv: Dict[str, Any]) -> Dict[str, Any]:
    """Deep copy and drop ``n_events`` from each row (smaller router payload)."""
    out = copy.deepcopy(inv)
    for _b, rows in (out.get("by_bucket") or {}).items():
        if not isinstance(rows, list):
            continue
        for r in rows:
            if isinstance(r, dict):
                r.pop("n_events", None)
    return out


def _flatten_inventory_rows(inv: Dict[str, Any]) -> List[Tuple[str, Dict[str, Any]]]:
    flat: List[Tuple[str, Dict[str, Any]]] = []
    by_bucket = inv.get("by_bucket") or {}
    if not isinstance(by_bucket, dict):
        return flat
    for bucket, rows in by_bucket.items():
        if not isinstance(rows, list):
            continue
        for r in rows:
            if isinstance(r, dict):
                flat.append((str(bucket), dict(r)))
    return flat


def _rebuild_inventory(
    *,
    flat_rows: List[Tuple[str, Dict[str, Any]]],
    graph_timeline_range: Any,
    code_index_summary: Any,
    truncated: bool,
    truncation_note: str,
) -> Dict[str, Any]:
    by_bucket: Dict[str, List[Dict[str, Any]]] = {b: [] for b in CODE_INDEX_BUCKETS}
    for bucket, row in flat_rows:
        if bucket in by_bucket:
            by_bucket[bucket].append(row)
    for b in by_bucket:
        by_bucket[b].sort(key=lambda x: str(x.get("key") or "").lower())
    per = {b: len(by_bucket[b]) for b in CODE_INDEX_BUCKETS}
    return {
        "by_bucket": by_bucket,
        "n_keys_total": len(flat_rows),
        "n_keys_per_bucket": per,
        "graph_timeline_range": graph_timeline_range,
        "code_index_summary": code_index_summary,
        "truncated": truncated,
        "truncation_note": truncation_note,
    }


def fit_code_inventory_to_budget(inv: Dict[str, Any], max_json_chars: int) -> Dict[str, Any]:
    """Shrink to top-N codes by ``n_events`` (desc) until JSON serializes under ``max_json_chars``."""
    raw = json.dumps(inv, ensure_ascii=True)
    if len(raw) <= max_json_chars:
        out = dict(inv)
        out["truncated"] = False
        out.pop("truncation_note", None)
        return out

    flat = _flatten_inventory_rows(inv)
    flat.sort(
        key=lambda x: (
            -int(x[1].get("n_events") or 0),
            str(x[0]),
            str(x[1].get("key") or ""),
        ),
    )
    graph_tr = inv.get("graph_timeline_range")
    cis = inv.get("code_index_summary")
    n_all = len(flat)
    for k in range(n_all, 0, -1):
        cand = _rebuild_inventory(
            flat_rows=flat[:k],
            graph_timeline_range=graph_tr,
            code_index_summary=cis,
            truncated=k < n_all,
            truncation_note=(
                f"router JSON budget: kept top {k} of {n_all} codes by n_events"
                if k < n_all
                else ""
            ),
        )
        if len(json.dumps(cand, ensure_ascii=True)) <= max_json_chars:
            return cand

    return _rebuild_inventory(
        flat_rows=[],
        graph_timeline_range=graph_tr,
        code_index_summary=cis,
        truncated=True,
        truncation_note="router JSON budget: empty inventory slice",
    )
