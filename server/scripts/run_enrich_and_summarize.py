#!/usr/bin/env python3
"""
Run connascence enrichment + narrative summarization on an existing
PatientTimelineVision JSON (the graph Ollama already built).

Skips PDF extraction entirely.  Requires OPENAI_API_KEY.

Usage (from 2ndOpinionMD-MVP/server):
    python3 -u scripts/run_enrich_and_summarize.py \
      ../artifacts/timeline_ollama_20260327_2117/patient_timeline_vision_norman_eric_roberts_20260328_000933.json \
      --artifact-dir ../artifacts/timeline_ollama_20260327_2117
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

script_dir = Path(__file__).resolve().parent
server_dir = script_dir.parent
parent_of_server = server_dir.parent

if str(parent_of_server) not in sys.path:
    sys.path.insert(0, str(parent_of_server))

os.chdir(server_dir)

from dotenv import load_dotenv
load_dotenv(server_dir / ".env", override=True)


class EmojiLogFormatter(logging.Formatter):
    _EMOJI = {
        logging.DEBUG: "🐛", logging.INFO: "📋",
        logging.WARNING: "⚠️", logging.ERROR: "❌", logging.CRITICAL: "🔥",
    }
    def format(self, record):
        record.levelemoji = self._EMOJI.get(record.levelno, "📌")
        return super().format(record)


def _setup_logging(verbose: bool):
    root = logging.getLogger()
    root.handlers.clear()
    level = logging.DEBUG if verbose else logging.INFO
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(EmojiLogFormatter(
        fmt="%(levelemoji)s %(asctime)s │ %(name)s │ %(message)s", datefmt="%H:%M:%S",
    ))
    root.addHandler(handler)
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser(
        description="Enrich + summarize an existing PatientTimelineVision graph."
    )
    parser.add_argument("vision_json", type=Path, help="Path to saved vision JSON")
    parser.add_argument("--artifact-dir", type=Path, default=None)
    parser.add_argument("--patient-id", default="norman_eric_roberts")
    parser.add_argument(
        "--question", default=(
            "Perform a comprehensive diagnostic investigation for this case. "
            "Focus on major clinical arcs, diagnostic mysteries, treatment divergences, "
            "and internal contradictions."
        ),
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()
    _setup_logging(args.verbose)
    log = logging.getLogger("run_enrich_and_summarize")

    if not args.vision_json.exists():
        print(f"❌ Vision JSON not found: {args.vision_json}", file=sys.stderr)
        sys.exit(1)

    if not os.getenv("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY required for GPT-4.1 enrichment + summarization.", file=sys.stderr)
        sys.exit(1)

    from openai import AsyncOpenAI
    from server.eoh.patient_timeline_vision import PatientTimelineVision
    from server.eoh.timeline_summarizer import (
        _run_timeline_enrichment_gap_synthesis_connascence,
        _existing_context_rows_from_vision,
        summarize_timeline_for_eoh,
        _compact_graph_for_reduce,
    )
    from server.api.stream_config import EOH_TIMELINE_SUMMARIZER_MODEL

    client = AsyncOpenAI()

    vision_path = str(args.vision_json.expanduser().resolve())
    with open(vision_path) as f:
        data = json.load(f)
    vision = PatientTimelineVision.from_dict(data)

    print(f"📋 Loaded vision: {len(vision.events)} events, {vision.count_edges()} edges", flush=True)
    print(f"🤖 Enrichment + summarization model: {EOH_TIMELINE_SUMMARIZER_MODEL}", flush=True)

    artifact_dir = str(args.artifact_dir.expanduser().resolve()) if args.artifact_dir else None
    if artifact_dir:
        Path(artifact_dir).mkdir(parents=True, exist_ok=True)

    async def run():
        t0 = time.perf_counter()

        # Step 1: Connascence enrichment (RULE 1 temporal, RULE 4 treatment, LLM diagnostic + lab_trend)
        print("\n═══ Step 1: Connascence enrichment (GPT-4.1) ═══", flush=True)
        try:
            enrichment = await _run_timeline_enrichment_gap_synthesis_connascence(
                client=client,
                vision=vision,
                patient_id=args.patient_id,
                pool=None,
                question=args.question,
                existing_context=_existing_context_rows_from_vision(vision),
                artifact_base_path=vision_path,
                phase_label="gpt41_enrichment",
                ingestion_client=None,
                ingestion_model=EOH_TIMELINE_SUMMARIZER_MODEL,
                force_json_format=True,
            )
            print(f"✅ Enrichment complete: {vision.count_edges()} edges", flush=True)
        except Exception:
            log.exception("Connascence enrichment failed")

        # Save enriched vision
        vision.save(vision_path, force=True)
        print(f"📋 Enriched vision saved: {vision_path}", flush=True)

        # Save updated snapshot
        snapshot_path = vision_path.replace("_vision_", "_snapshot_")
        try:
            snap = vision.snapshot()
            with open(snapshot_path, "w", encoding="utf-8") as f:
                json.dump(snap, f, indent=2, ensure_ascii=False)
            print(f"📋 Updated snapshot saved: {snapshot_path}", flush=True)
        except Exception:
            log.exception("Snapshot save failed")

        # Step 2: Narrative summarization (hierarchical map-reduce via GPT-4.1)
        # We need the raw timeline text — load from PDF pages stored in vision metadata
        # or from the original PDF.  Since we don't have raw text, we'll use the graph
        # compact representation as the summarization input.
        print("\n═══ Step 2: Narrative summarization (GPT-4.1) ═══", flush=True)

        # Build a text representation from the graph for the summarizer
        compact = _compact_graph_for_reduce(vision, max_chars=200_000)
        graph_text = json.dumps(compact, indent=1, ensure_ascii=False)

        try:
            summaries = await summarize_timeline_for_eoh(
                client=client,
                question=args.question,
                timeline_text=graph_text,
                patient_id=args.patient_id,
                timeline_vision=vision,
            )
            print(f"\n{'='*80}", flush=True)
            print("📜 TIMELINE SUMMARY", flush=True)
            print(f"{'='*80}", flush=True)
            print(summaries.timeline_summary[:3000], flush=True)

            if artifact_dir:
                export_path = str(Path(artifact_dir) / "timeline_summaries_enriched.json")
                with open(export_path, "w", encoding="utf-8") as f:
                    json.dump(asdict(summaries), f, indent=2, ensure_ascii=False)
                print(f"\n📇 Summaries: {export_path}", flush=True)

            # Save final graph
            graph_path = str(Path(artifact_dir or "/tmp") / "patient_timeline_graph_enriched.json")
            vision.save(graph_path, force=True)
            print(f"🕸️ Enriched graph: {graph_path}", flush=True)

        except Exception:
            log.exception("Narrative summarization failed")

        elapsed = time.perf_counter() - t0
        print(f"\n✅ Done in {elapsed:.1f}s", flush=True)

    asyncio.run(run())


if __name__ == "__main__":
    main()
