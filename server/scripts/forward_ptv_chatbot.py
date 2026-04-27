#!/usr/bin/env python3
"""Interactive FORWARD chatbot powered by the 3-agent harness stages.

Default behavior:
- Uses a synthetic FORWARD PTV graph (P1) unless --graph is provided.
- Runs Stage A (probe) -> Stage B (gap) -> Stage C (curation) -> Stage D (synthesis)
  for each user question.
- Optionally runs Stage E (MKG overall synthesis) unless --no-mkg is set.
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Dict

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.ptv_toolkit.graph import load_graph
from server.scripts.forward_ptv_3agent_harness import (  # type: ignore
    MODEL,
    _curate_bundle,
    _stage_gap,
    _stage_mkg_synth,
    _stage_probe,
    _stage_synth,
)

DEFAULT_GRAPH = (
    ROOT
    / "artifacts"
    / "forward_kaleb_package_20260423"
    / "synthetic_pro_cohort"
    / "ptv_synth_P1_early_responder.json"
)


def _extract_mkg_markdown(stage_e: Dict[str, Any]) -> str:
    llm = stage_e.get("llm") or {}
    if isinstance(llm, dict) and llm.get("mode") == "two_pass":
        return str(((llm.get("synth_pass") or {}).get("markdown") or ""))
    return str((llm.get("markdown") or ""))


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graph", type=Path, default=DEFAULT_GRAPH, help="Path to synthetic FORWARD PTV graph JSON.")
    ap.add_argument("--patient-code", default="P1", help="Patient code label used in output metadata.")
    ap.add_argument("--patient-phenotype", default="early_responder", help="Patient phenotype label.")
    ap.add_argument("--patient-label", default="Synthetic FORWARD Patient", help="Patient label shown in metadata.")
    ap.add_argument("--patient-headline", default="FORWARD synthetic trajectory", help="Patient headline shown in metadata.")
    ap.add_argument("--probe-model", default=os.environ.get("FORWARD_PROBE_MODEL", MODEL))
    ap.add_argument("--gap-model", default=os.environ.get("FORWARD_GAP_MODEL", MODEL))
    ap.add_argument("--synth-model", default=os.environ.get("FORWARD_SYNTH_MODEL", MODEL))
    ap.add_argument("--mkg-synth-model", default=os.environ.get("FORWARD_MKG_SYNTH_MODEL", MODEL))
    ap.add_argument("--mkg-compress-model", default=os.environ.get("FORWARD_MKG_COMPRESS_MODEL", MODEL))
    ap.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    ap.add_argument("--temperature", type=float, default=0.15)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--probe-max-turns", type=int, default=6)
    ap.add_argument("--gap-max-turns", type=int, default=6)
    ap.add_argument("--agent-num-ctx", type=int, default=int(os.environ.get("OLLAMA_AGENT_NUM_CTX", "32768")))
    ap.add_argument("--synth-num-ctx", type=int, default=int(os.environ.get("OLLAMA_SYNTH_NUM_CTX", "32768")))
    ap.add_argument("--no-mkg", action="store_true")
    ap.add_argument("--mkg-use-router", dest="mkg_use_router", action="store_true", default=True)
    ap.add_argument("--mkg-no-router", dest="mkg_use_router", action="store_false")
    ap.add_argument("--mkg-router-model", default=os.environ.get("EOH_SOURCE_ROUTER_MODEL", "eoh-llama3.2-source-router"))
    ap.add_argument("--mkg-router-num-ctx", type=int, default=int(os.environ.get("OLLAMA_ROUTER_NUM_CTX", "8192")))
    ap.add_argument("--mkg-router-restrict-sources", action="store_true")
    ap.add_argument("--mkg-embed-model", default=os.environ.get("LOCAL_EMBED_MODEL", "BAAI/bge-base-en-v1.5"))
    ap.add_argument("--mkg-top-k", type=int, default=10)
    ap.add_argument("--mkg-two-pass-synth", dest="mkg_two_pass_synth", action="store_true", default=True)
    ap.add_argument("--mkg-single-pass-synth", dest="mkg_two_pass_synth", action="store_false")
    ap.add_argument("--mkg-compress-num-ctx", type=int, default=int(os.environ.get("OLLAMA_COMPRESS_NUM_CTX", "32768")))
    ap.add_argument("--mkg-compress-evidence-k", type=int, default=8)
    ap.add_argument("--mkg-synth-num-ctx", type=int, default=int(os.environ.get("OLLAMA_SYNTH_NUM_CTX", "32768")))
    ap.add_argument("--mkg-sources", default="", help="Optional comma-separated rag_corpus.source filter.")
    return ap.parse_args()


def main() -> int:
    args = _parse_args()
    graph_path = args.graph.expanduser().resolve()
    if not graph_path.exists():
        print(f"error: graph not found: {graph_path}", file=sys.stderr)
        return 2

    patient = {
        "code": args.patient_code,
        "phenotype": args.patient_phenotype,
        "label": args.patient_label,
        "headline": args.patient_headline,
        "patient_id": "",
        "path": graph_path,
    }
    gh = load_graph(graph_path)
    print(f"Loaded graph {graph_path.name} events={len(gh.events)} hash={gh.graph_hash}")
    print("Interactive FORWARD chat ready. Type 'quit' to exit.\n")

    while True:
        try:
            question = input("forward> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0
        if not question:
            continue
        if question.lower() in {"quit", "exit", "q"}:
            print("bye")
            return 0

        t0 = time.monotonic()
        probe = _stage_probe(
            gh=gh,
            question=question,
            model=args.probe_model,
            ollama_url=args.ollama_url,
            max_turns=args.probe_max_turns,
            temperature=args.temperature,
            timeout=args.timeout,
            num_ctx=args.agent_num_ctx,
        )
        gap = _stage_gap(
            gh=gh,
            original_question=question,
            probe_stage=probe,
            model=args.gap_model,
            ollama_url=args.ollama_url,
            max_turns=args.gap_max_turns,
            temperature=args.temperature,
            timeout=args.timeout,
            num_ctx=args.agent_num_ctx,
        )
        bundle = _curate_bundle(original_question=question, probe_stage=probe, gap_stage=gap)
        synth = _stage_synth(
            bundle=bundle,
            model=args.synth_model,
            ollama_url=args.ollama_url,
            temperature=args.temperature,
            timeout=args.timeout,
            num_ctx=args.synth_num_ctx,
        )

        final_text = str((synth or {}).get("markdown") or "")
        if not args.no_mkg:
            stage_e = _stage_mkg_synth(
                original_question=question,
                patient=patient,
                ptv_synth_markdown=final_text,
                args=SimpleNamespace(**vars(args)),
            )
            mkg_text = _extract_mkg_markdown(stage_e)
            if mkg_text.strip():
                final_text = mkg_text

        elapsed = round(time.monotonic() - t0, 2)
        print(f"\n--- answer ({elapsed}s) ---\n")
        print(final_text or "(no final synthesis text returned)")
        print()


if __name__ == "__main__":
    raise SystemExit(main())
