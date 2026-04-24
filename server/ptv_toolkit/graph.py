"""
graph.py — load an indexed PTV JSON artifact and build in-memory indexes.

Consumes the "noarcs" schema (no top-level ``arcs`` key, authoritative
``metadata.code_index``). Everything downstream reads these index
structures rather than re-scanning events.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

CONNASCENCE_KINDS = (
    "same_chapter",
    "same_day",
    "same_encounter",
    "same_icd",
    "same_drug",
    "temporal",
    "in_workup_for",
    "caused_by",
)


def _parse_iso(ts: str) -> Optional[str]:
    """Return ``YYYY-MM-DD`` or None for 'unknown' / un-parseable inputs."""
    if not ts:
        return None
    s = str(ts).strip()
    if not s or s.lower() in ("unknown", "n/a", "none"):
        return None
    # Primary format already ISO.
    if len(s) >= 10 and s[4] == "-" and s[7] == "-":
        return s[:10]
    return None


def _hash_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


# =============================================================================
# Handle
# =============================================================================

@dataclass
class GraphHandle:
    """Thin wrapper around a loaded PTV JSON graph + derived indexes."""

    path: Path
    graph: Dict[str, Any]
    graph_hash: str

    events: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    code_index: Dict[str, Dict[str, List[Dict[str, Any]]]] = field(default_factory=dict)

    by_type: Dict[str, List[str]] = field(default_factory=dict)
    by_date: List[Tuple[str, str]] = field(default_factory=list)   # sorted (date, event_id)
    unknown_date: List[str] = field(default_factory=list)
    adjacency: Dict[str, Dict[str, List[str]]] = field(default_factory=dict)
    degree: Dict[str, int] = field(default_factory=dict)

    def snapshot(self) -> Dict[str, Any]:
        ci = self.code_index or {}
        return {
            "graph_hash": self.graph_hash,
            "path": str(self.path),
            "patient_id": self.graph.get("patient_id"),
            "built_at": self.graph.get("built_at"),
            "n_events": len(self.events),
            "n_event_types": len(self.by_type),
            "event_type_counts": {
                t: len(ids) for t, ids in sorted(self.by_type.items(), key=lambda kv: -len(kv[1]))
            },
            "n_connascence_endpoints": sum(self.degree.values()),
            "date_range": self._date_range(),
            "n_unknown_timestamps": len(self.unknown_date),
            "code_index_summary": {
                "drugs": len(ci.get("drugs") or {}),
                "rxnorm": len(ci.get("rxnorm") or {}),
                "icd": len(ci.get("icd") or {}),
                "labs": len(ci.get("labs") or {}),
                "loinc": len(ci.get("loinc") or {}),
            },
        }

    def _date_range(self) -> Dict[str, Optional[str]]:
        if not self.by_date:
            return {"start": None, "end": None}
        return {"start": self.by_date[0][0], "end": self.by_date[-1][0]}


# =============================================================================
# Loader
# =============================================================================

def load_graph(path: str | Path) -> GraphHandle:
    p = Path(path).resolve()
    if not p.exists():
        raise FileNotFoundError(f"PTV graph not found: {p}")

    graph = json.loads(p.read_text(encoding="utf-8"))
    gh = GraphHandle(path=p, graph=graph, graph_hash=_hash_file(p))

    events = graph.get("events") or {}
    if not isinstance(events, dict):
        raise ValueError("graph.events must be a dict keyed by event_id")
    gh.events = events

    md = graph.get("metadata") or {}
    gh.code_index = md.get("code_index") or {
        "drugs": {}, "rxnorm": {}, "icd": {}, "labs": {}, "loinc": {},
    }

    # ---- by_type / by_date / adjacency --------------------------------------
    by_type: Dict[str, List[str]] = defaultdict(list)
    by_date: List[Tuple[str, str]] = []
    unknown_date: List[str] = []
    adjacency: Dict[str, Dict[str, List[str]]] = {}
    degree: Dict[str, int] = {}

    for eid, ev in events.items():
        et = (ev.get("event_type") or "unknown").strip() or "unknown"
        by_type[et].append(eid)

        iso = _parse_iso(ev.get("timestamp") or "")
        if iso:
            by_date.append((iso, eid))
        else:
            unknown_date.append(eid)

        conn = ev.get("connascence") or {}
        if not isinstance(conn, dict):
            conn = {}
        adj_row: Dict[str, List[str]] = {}
        total = 0
        for kind, neighbors in conn.items():
            if not isinstance(neighbors, list):
                continue
            lst = [n for n in neighbors if isinstance(n, str) and n in events]
            if lst:
                adj_row[kind] = lst
                total += len(lst)
        adjacency[eid] = adj_row
        degree[eid] = total

    by_date.sort(key=lambda t: t[0])

    gh.by_type = dict(by_type)
    gh.by_date = by_date
    gh.unknown_date = unknown_date
    gh.adjacency = adjacency
    gh.degree = degree
    return gh
