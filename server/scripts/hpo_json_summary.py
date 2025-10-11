#!/usr/bin/env python3
import json, argparse, sys

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", required=True)
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--require-graphs", action="store_true")
    ap.add_argument("--min-edges", dest="min_edges", type=int, default=0)
    args = ap.parse_args()

    try:
        d = json.load(open(args.json))
    except Exception as e:
        print(f"ERROR: cannot read JSON: {args.json}: {e}")
        sys.exit(3)

    if "graphs" not in d or not d["graphs"]:
        print(f"NO_GRAPHS: {args.json}")
        if args.require_graphs:
            sys.exit(1)
        else:
            sys.exit(0)

    g = d["graphs"][0]
    nodes = g.get("nodes") or []
    edges = g.get("edges") or []

    print(f"SUMMARY: file={args.json} graphs={len(d['graphs'])} nodes={len(nodes)} edges={len(edges)}")
    if args.verbose:
        print("Sample node:", nodes[0] if nodes else None)
        print("Sample edge:", edges[0] if edges else None)

    if args.min_edges and len(edges) < args.min_edges:
        print(f"INSUFFICIENT_EDGES: have={len(edges)} < required={args.min_edges}")
        sys.exit(2)

    # success
    sys.exit(0)

if __name__ == "__main__":
    main()
