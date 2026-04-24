"""Run every tool once against the packaged real EHR graph.

Usage:
    python server/scripts/_ptv_toolkit_smoketest.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from server.ptv_toolkit import call_tool, load_graph  # noqa: E402


DEFAULT = ROOT / "artifacts" / "forward_kaleb_package_20260423" / "PTV_REAL_EHR_20260423.json"


def _print(title: str, out):
    print(f"\n==== {title} ====")
    txt = json.dumps(out, indent=2, default=str)
    if len(txt) > 1600:
        txt = txt[:1600] + "..."
    print(txt)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    gh = load_graph(path)

    _print("graph_stats", call_tool("graph_stats", gh))
    _print("list_event_types", call_tool("list_event_types", gh))

    _print("code_index_lookup drugs list",
           call_tool("code_index_lookup", gh, {"bucket": "drugs", "limit": 8}))
    _print("code_index_lookup icd exact I10",
           call_tool("code_index_lookup", gh, {"bucket": "icd", "key": "I10"}))
    _print("code_index_lookup drugs contains 'hydro'",
           call_tool("code_index_lookup", gh, {"bucket": "drugs", "key_contains": "hydro", "limit": 5}))

    _print("semantic_search pain",
           call_tool("semantic_search", gh, {"query": "low back pain radiating", "k": 5}))

    # Pick any seed event that has edges to exercise bfs_expand.
    seed = None
    for eid, deg in gh.degree.items():
        if deg >= 3:
            seed = eid
            break
    _print(f"bfs_expand seed={seed}",
           call_tool("bfs_expand", gh, {
               "seed_event_ids": [seed],
               "edge_kinds": ["same_encounter", "caused_by", "in_workup_for"],
               "depth": 1,
               "max_events": 10,
           }))

    _print("temporal_scan labs 2016",
           call_tool("temporal_scan", gh, {
               "event_types": ["lab"],
               "start": "2016-01-01",
               "end": "2016-12-31",
               "limit": 10,
           }))

    if seed:
        _print(f"get_event {seed}", call_tool("get_event", gh, {"event_id": seed}))


if __name__ == "__main__":
    main()
