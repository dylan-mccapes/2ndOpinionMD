"""Rebuild ``metadata.code_index`` on an existing serialized PTV JSON and
strip legacy ``arc_drug_*`` entries.

One-shot tool for previously-exported graphs (e.g. the scrubbed Kaleb
exemplar).  Delegates all code-index logic to
:mod:`server.eoh.code_index_ops` so the on-disk rebuild and the live
finalize pass can never drift.

Usage (PowerShell)::

    python -m server.scripts.rebuild_ptv_code_index `
        --in  artifacts/ptv_XXXX_scrubbed_pretty.json `
        --out artifacts/ptv_XXXX_scrubbed_pretty.json `
        --pretty
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Dict

from server.eoh import code_index_ops


def _strip_drug_arcs(graph: Dict[str, Any]) -> Dict[str, int]:
    """Remove legacy ``arc_drug_*`` entries from arcs, annotations, and index."""
    report: Dict[str, int] = Counter()
    arcs: Dict[str, Any] = graph.get("arcs") or {}

    drug_arc_ids = [aid for aid in list(arcs.keys()) if aid.startswith("arc_drug_")]
    for aid in drug_arc_ids:
        arcs.pop(aid, None)
    report["arc_drug_dropped"] = len(drug_arc_ids)

    for ev in (graph.get("events") or {}).values():
        ann = ev.get("annotations") or {}
        aids = ann.get("arc_ids") or []
        if aids:
            new_aids = [a for a in aids if not a.startswith("arc_drug_")]
            if len(new_aids) != len(aids):
                ann["arc_ids"] = new_aids
                report["event_arc_ids_pruned"] += 1
        ev["annotations"] = ann

    idx = (graph.get("metadata") or {}).get("index")
    if isinstance(idx, dict) and isinstance(idx.get("by_arc"), dict):
        by_arc = idx["by_arc"]
        drop = [aid for aid in list(by_arc.keys()) if aid.startswith("arc_drug_")]
        for aid in drop:
            by_arc.pop(aid, None)
        report["index_by_arc_dropped"] = len(drop)

    return dict(report)


def rebuild(graph: Dict[str, Any]) -> Dict[str, Any]:
    report: Dict[str, Any] = {}
    report.update(_strip_drug_arcs(graph))
    report.update(code_index_ops.rebuild_code_index(graph))
    return report


def main() -> None:
    p = argparse.ArgumentParser(description="Rebuild metadata.code_index on a PTV JSON.")
    p.add_argument("--in",  dest="in_path",  required=True, help="input scrubbed PTV JSON")
    p.add_argument("--out", dest="out_path", required=True, help="output path")
    p.add_argument("--pretty", action="store_true", help="write with indent=2 (recommended)")
    args = p.parse_args()

    in_path  = Path(args.in_path)
    out_path = Path(args.out_path)

    with in_path.open("r", encoding="utf-8") as f:
        graph = json.load(f)

    report = rebuild(graph)

    with out_path.open("w", encoding="utf-8") as f:
        if args.pretty:
            json.dump(graph, f, ensure_ascii=False, indent=2)
        else:
            json.dump(graph, f, ensure_ascii=False)

    print(f"wrote: {out_path}")
    for k in sorted(report):
        print(f"  {k:<28} {report[k]}")


if __name__ == "__main__":
    main()
