#!/usr/bin/env python3
"""
Norman PTV graph retrieval sandbox — deterministic tools + optional Ollama (eoh-llama-lucifer).

Primary pipeline (STRATEGY v1.1): graph_reduce → graph_hybrid_search (semantic on reduced corpus)
→ graph_bfs_expand (multi-seed, restricted to reduced) → PE / Lorenz → token budget.

Usage (from repo root, with .BeatingHeart or venv active):
  PYTHONPATH=. python sandbox/norman_graph_retrieval/run.py --no-ollama
  PYTHONPATH=. python sandbox/norman_graph_retrieval/run.py -q "ANA and renal involvement"
  PYTHONPATH=. python sandbox/norman_graph_retrieval/run.py --no-semantic   # keyword-only, faster

Env:
  NORMAN_PTV_JSON   — override path to patient_timeline_vision JSON
  OLLAMA_URL        — default http://127.0.0.1:11434
  OLLAMA_MODEL      — default eoh-llama-lucifer
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Repo root = parent of sandbox/
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / "server" / ".env", override=False)
    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass

from server.eoh.patient_timeline_vision import PatientTimelineVision
from server.graph_traversal.agent_tools import execute_graph_tool, GRAPH_TOOL_DEFINITIONS
from server.graph_traversal.pe_adapter import run_provenance_engine_classify, vision_to_pe_nodes


DEFAULT_PTV = (
    ROOT
    / "artifacts"
    / "timeline_ollama_20260329_1805"
    / "patient_timeline_vision_norman_eric_roberts_20260329_195915.json"
)


def _ollama_chat(base_url: str, model: str, user_message: str, system: str | None = None) -> dict:
    import urllib.request

    payload: dict = {
        "model": model,
        "messages": [],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    if system:
        payload["messages"].append({"role": "system", "content": system})
    payload["messages"].append({"role": "user", "content": user_message})
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=600) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser(description="Norman graph retrieval sandbox")
    parser.add_argument("--ptv", type=Path, default=None, help="Path to PTV JSON")
    parser.add_argument("--query", "-q", type=str, default="What is the overall inflammatory and autoimmune trajectory?")
    parser.add_argument("--no-ollama", action="store_true", help="Skip LLM synthesis")
    parser.add_argument(
        "--no-semantic",
        action="store_true",
        help="Disable sentence-transformers in hybrid search (keyword-only, faster)",
    )
    parser.add_argument(
        "--with-centrality",
        action="store_true",
        help="Also run graph_centrality on reduced set (exploratory; not the default Q&A path)",
    )
    parser.add_argument("--pe-nodes", type=int, default=400, metavar="N", help="Max nodes for provenance-engine classify")
    args = parser.parse_args()

    ptv_path = args.ptv or Path(os.environ.get("NORMAN_PTV_JSON", str(DEFAULT_PTV)))
    if not ptv_path.is_file():
        print(f"PTV file not found: {ptv_path}", file=sys.stderr)
        print("Set NORMAN_PTV_JSON or place Norman artifact under artifacts/", file=sys.stderr)
        sys.exit(1)

    with open(ptv_path, encoding="utf-8") as f:
        data = json.load(f)
    vision = PatientTimelineVision.from_dict(data)

    print(f"Loaded patient_id={vision.patient_id} events={len(vision.events)} edges={vision.count_edges()}")
    print(f"PTV path: {ptv_path}")

    bundle: dict = {
        "ptv_path": str(ptv_path),
        "patient_id": vision.patient_id,
        "tools": {},
    }

    bundle["tools"]["graph_snapshot"] = execute_graph_tool("graph_snapshot", vision, {})
    bundle["tools"]["graph_reduce"] = execute_graph_tool(
        "graph_reduce",
        vision,
        {"drop_page": True, "drop_unknown_timestamp": False, "drop_isolates": True},
    )
    reduced_ids = bundle["tools"]["graph_reduce"].get("event_ids") or []
    print(f"After reduce (drop page + isolates, keep unknown ts): {len(reduced_ids)} event_ids")

    if args.with_centrality:
        bundle["tools"]["graph_centrality"] = execute_graph_tool(
            "graph_centrality",
            vision,
            {"event_ids": reduced_ids[:6000] if len(reduced_ids) > 6000 else reduced_ids, "top_k": 25},
        )

    use_semantic = not args.no_semantic
    bundle["tools"]["graph_hybrid_search"] = execute_graph_tool(
        "graph_hybrid_search",
        vision,
        {
            "query": args.query,
            "top_k": 30,
            "semantic": use_semantic,
            "event_ids": reduced_ids,
        },
    )
    hybrid_ids = bundle["tools"]["graph_hybrid_search"].get("event_ids") or []
    print(
        f"Hybrid search (semantic={use_semantic}, corpus=reduced): {len(hybrid_ids)} hits; "
        f"corpus_size={bundle['tools']['graph_hybrid_search'].get('corpus_size')}"
    )

    seed_n = min(10, max(3, len(hybrid_ids)))
    seed_ids = hybrid_ids[:seed_n] if hybrid_ids else reduced_ids[:5]
    bundle["tools"]["graph_bfs_expand"] = execute_graph_tool(
        "graph_bfs_expand",
        vision,
        {
            "seed_event_ids": seed_ids,
            "restrict_to_event_ids": reduced_ids,
            "max_depth": 2,
            "max_nodes": 600,
        },
    )
    bfs_ids = bundle["tools"]["graph_bfs_expand"].get("event_ids") or []

    def _dedupe(ids: list) -> list:
        seen: set = set()
        out: list = []
        for x in ids:
            if x not in seen:
                seen.add(x)
                out.append(x)
        return out

    working_ids = _dedupe((hybrid_ids[:50] if hybrid_ids else []) + bfs_ids)[: args.pe_nodes]
    if not working_ids:
        working_ids = reduced_ids[: args.pe_nodes]

    bundle["tools"]["graph_pe_lorenz_classify"] = execute_graph_tool(
        "graph_pe_lorenz_classify",
        vision,
        {"event_ids": working_ids, "rho": 28.0, "tau": 2.0, "steps": 1500},
    )
    lorenz_items = bundle["tools"]["graph_pe_lorenz_classify"].get("items") or []
    bundle["tools"]["graph_pe_govern_adjust"] = execute_graph_tool(
        "graph_pe_govern_adjust",
        vision,
        {"items": lorenz_items},
    )

    # Native provenance-engine (optional package)
    pe_nodes = vision_to_pe_nodes(vision, event_ids=working_ids, max_nodes=args.pe_nodes)
    bundle["provenance_engine"] = run_provenance_engine_classify(pe_nodes, rho=28.0, tau=2.0)

    budget_ids = hybrid_ids[:80] if hybrid_ids else reduced_ids[:400]
    bundle["tools"]["graph_token_budget"] = execute_graph_tool(
        "graph_token_budget",
        vision,
        {
            "event_ids": budget_ids,
            "max_tokens": 8000,
            "query": args.query,
            "prefer_recent": True,
        },
    )

    if not args.no_ollama:
        ollama_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
        model = os.environ.get("OLLAMA_MODEL", "eoh-llama-lucifer")
        tool_digest = {
            "snapshot_summary": {
                "total_events": bundle["tools"]["graph_snapshot"]["snapshot"].get("total_events"),
                "total_edges": bundle["tools"]["graph_snapshot"]["snapshot"].get("total_edges"),
            },
            "reduced_count": len(reduced_ids),
            "hybrid_top_10": bundle["tools"]["graph_hybrid_search"].get("event_ids", [])[:10],
            "bfs_seed_count": len(seed_ids),
            "bfs_reachable_count": len(bfs_ids),
            "lorenz_counts": _count_lorenz(lorenz_items),
            "token_budget_ids": bundle["tools"]["graph_token_budget"].get("event_ids", [])[:40],
        }
        if args.with_centrality and bundle["tools"].get("graph_centrality"):
            tool_digest["centrality_top_5"] = bundle["tools"]["graph_centrality"].get("top", [])[:5]
        user_prompt = f"""Clinical question: {args.query}

Below is JSON from deterministic graph tools (Patient Timeline Vision). Use only these event_ids when citing evidence. Apply EoH modules where relevant (M13 flare trajectory, M68 ICM language at high level — tool output is not calibrated ICM).

{json.dumps(tool_digest, indent=2)[:12000]}

Respond with: (1) short clinical synthesis, (2) bullet list of cited event_ids, (3) one sentence on uncertainty / missing data."""

        try:
            resp = _ollama_chat(ollama_url, model, user_prompt)
            msg = (resp.get("message") or {}).get("content") or json.dumps(resp)[:2000]
            bundle["ollama"] = {"model": model, "base_url": ollama_url, "reply": msg}
            print("\n--- Ollama synthesis ---\n")
            print(msg)
        except Exception as e:
            bundle["ollama"] = {"error": str(e), "hint": "Start Ollama and run: ollama create eoh-llama-lucifer -f server/ollama/eoh-llama3.1-8b-lucifer.Modelfile"}
            print(f"\nOllama call failed: {e}", file=sys.stderr)

    out_dir = Path(__file__).resolve().parent / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    out_path = out_dir / f"norman_sandbox_{stamp}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2, ensure_ascii=False)
    print(f"\nWrote receipt: {out_path}")


def _count_lorenz(items: list) -> dict:
    c = {}
    for it in items:
        k = it.get("classification") or "?"
        c[k] = c.get(k, 0) + 1
    return c


if __name__ == "__main__":
    main()
