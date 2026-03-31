#!/usr/bin/env python3
"""
Resume timeline summarization using Claude Opus.

Loads an existing PatientTimelineVision graph (from a prior extraction run)
and re-extracts PDF text (fast, no LLM), then runs the narrative summarizer
through Claude Opus instead of GPT-4.1.

Usage (from 2ndOpinionMD-MVP/server, .BeatingHeart active):
    python -u scripts/run_opus_summarize.py \
        ../data/patient_timelines/NormanEricRoberts_decrypted.pdf \
        --vision-path ../artifacts/timeline_ollama_20260329_1805/patient_timeline_vision_norman_eric_roberts_20260329_195915.json \
        --artifact-dir ../artifacts/timeline_ollama_20260329_1805

Requires ANTHROPIC_API_KEY in .env or shell environment.
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
from typing import Optional

script_dir = Path(__file__).resolve().parent
server_dir = script_dir.parent
parent_of_server = server_dir.parent

if str(parent_of_server) not in sys.path:
    sys.path.insert(0, str(parent_of_server))

os.chdir(server_dir)

from dotenv import load_dotenv
load_dotenv(parent_of_server / ".env", override=False)
load_dotenv(server_dir / ".env", override=True)


class EmojiLogFormatter(logging.Formatter):
    _EMOJI = {
        logging.DEBUG: "\U0001f41b",
        logging.INFO: "\U0001f4cb",
        logging.WARNING: "\u26a0\ufe0f",
        logging.ERROR: "\u274c",
        logging.CRITICAL: "\U0001f525",
    }

    def format(self, record: logging.LogRecord) -> str:
        record.levelemoji = self._EMOJI.get(record.levelno, "\U0001f4cc")
        return super().format(record)


def _setup_logging(verbose: bool) -> None:
    root = logging.getLogger()
    root.handlers.clear()
    level = logging.DEBUG if verbose else logging.INFO
    root.setLevel(level)
    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(
        EmojiLogFormatter(
            fmt="%(levelemoji)s %(asctime)s \u2502 %(name)s \u2502 %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root.addHandler(handler)
    logging.getLogger("server").setLevel(level)
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def _log(msg: str, *, emoji: str = "\U0001f4ac") -> None:
    print(f"{emoji} {msg}", file=sys.stderr, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Resume timeline summarization using Claude Opus."
    )
    parser.add_argument("pdf", type=Path, help="Path to decrypted timeline PDF")
    parser.add_argument(
        "--vision-path",
        type=Path,
        required=True,
        help="Path to saved PatientTimelineVision JSON from prior run.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
        help="Directory for outputs (reuses prior run's artifact dir).",
    )
    parser.add_argument("--patient-id", default="norman_eric_roberts")
    parser.add_argument(
        "--question",
        default=(
            "Perform a comprehensive diagnostic investigation for this case. "
            "Focus on major clinical arcs, diagnostic mysteries, treatment divergences, "
            "and internal contradictions."
        ),
    )
    parser.add_argument("--password", default=None, help="PDF password if encrypted")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    _setup_logging(verbose=args.verbose)
    log = logging.getLogger("run_opus_summarize")

    if not os.getenv("ANTHROPIC_API_KEY"):
        _log(
            "ANTHROPIC_API_KEY not set. Add it to server/.env or export it.",
            emoji="\u274c",
        )
        sys.exit(1)

    pdf_file = args.pdf.expanduser()
    if not pdf_file.is_file():
        _log(f"PDF not found: {pdf_file}", emoji="\u274c")
        sys.exit(1)

    vision_path = args.vision_path.expanduser().resolve()
    if not vision_path.is_file():
        _log(f"Vision file not found: {vision_path}", emoji="\u274c")
        sys.exit(1)

    artifact_dir: Optional[Path] = None
    if args.artifact_dir:
        artifact_dir = args.artifact_dir.expanduser().resolve()
        artifact_dir.mkdir(parents=True, exist_ok=True)

    _log(f"PDF: {pdf_file.resolve()}", emoji="\U0001f4c4")
    _log(f"Vision graph: {vision_path}", emoji="\U0001f578\ufe0f")
    _log(f"Patient id: {args.patient_id}", emoji="\U0001f9fe")
    _log(f"Summarizer: Claude Opus", emoji="\U0001f916")
    if artifact_dir:
        _log(f"Artifact dir: {artifact_dir}", emoji="\U0001f4e6")

    from pypdf import PdfReader
    from server.eoh.patient_timeline_vision import PatientTimelineVision
    from server.eoh.timeline_summarizer import summarize_timeline_for_eoh
    from server.eoh.graph_enrichment import enrich_graph_opportunistic

    async def run() -> None:
        t0 = time.perf_counter()

        # Step 1: Re-extract PDF text (fast, no LLM)
        _log("Extracting text from PDF...", emoji="\U0001f4d6")
        reader = PdfReader(str(pdf_file))
        if reader.is_encrypted:
            pw = args.password
            if pw is None:
                import getpass
                pw = getpass.getpass("Enter PDF decryption password: ")
            if reader.decrypt(pw) == 0:
                raise ValueError("Incorrect password")
            del pw

        chunks = []
        for idx, page in enumerate(reader.pages):
            text = (page.extract_text() or "").strip()
            text = text.replace("\x00", "")
            if text:
                chunks.append(f"=== Page {idx + 1} ===\n{text}")

        timeline_text = "\n\n".join(chunks)
        _log(
            f"PDF text extracted: {len(chunks)} pages, {len(timeline_text):,} chars",
            emoji="\u2705",
        )

        # Step 2: Load the saved PatientTimelineVision graph
        _log("Loading saved PatientTimelineVision graph...", emoji="\U0001f578\ufe0f")
        vision = PatientTimelineVision.load(str(vision_path))
        _log(
            f"Graph loaded: {len(vision.events)} events",
            emoji="\u2705",
        )

        # Step 3: Run summarization with Claude Opus
        _log("Starting Claude Opus summarization...", emoji="\U0001f680")
        from openai import AsyncOpenAI
        dummy_client = AsyncOpenAI(api_key="unused")

        summaries = await summarize_timeline_for_eoh(
            client=dummy_client,
            question=args.question,
            timeline_text=timeline_text,
            pool=None,
            patient_id=args.patient_id,
            use_timeline_rag=False,
            timeline_vision=vision,
            use_claude=True,
            # Full Opus map+reduce: this script uses a dummy OpenAI client; reduce_only would
            # send map steps to OpenAI and fail without a real key.
            claude_scope="all",
        )

        elapsed = time.perf_counter() - t0
        _log(f"Summarization complete in {elapsed:.1f}s", emoji="\u2705")

        # Print results
        print("\n" + "=" * 80, flush=True)
        print("\U0001f4dc TIMELINE SUMMARY (Claude Opus)", flush=True)
        print("=" * 80, flush=True)
        excerpt = (summaries.timeline_summary or "")[:6000]
        print(
            excerpt + ("\u2026" if len(summaries.timeline_summary or "") > 6000 else ""),
            flush=True,
        )

        if summaries.meds_and_labs_snapshot:
            print("\n" + "=" * 80, flush=True)
            print("\U0001f48a MEDS & LABS", flush=True)
            print("=" * 80, flush=True)
            print(summaries.meds_and_labs_snapshot[:3000], flush=True)

        if summaries.valyu_summary:
            print("\n" + "=" * 80, flush=True)
            print("\U0001f50e VALYU / QUERY SIGNALS", flush=True)
            print("=" * 80, flush=True)
            print(summaries.valyu_summary[:2000], flush=True)

        # Save updated artifacts
        if artifact_dir:
            export_path = artifact_dir / "timeline_summaries_opus_export.json"
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(asdict(summaries), f, indent=2, ensure_ascii=False)
            _log(f"Opus summaries JSON: {export_path}", emoji="\U0001f4c7")

            vision_out = artifact_dir / "patient_timeline_vision_opus.json"
            vision.save(str(vision_out))
            _log(f"Updated vision graph: {vision_out}", emoji="\U0001f578\ufe0f")

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        _log("Interrupted.", emoji="\U0001f6d1")
        sys.exit(130)
    except Exception as e:
        log.exception("Pipeline failed: %s", e)
        sys.exit(1)

    _log("All done.", emoji="\U0001f389")


if __name__ == "__main__":
    main()
