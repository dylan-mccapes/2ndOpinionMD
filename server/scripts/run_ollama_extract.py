#!/usr/bin/env python3
"""
Script 1 of 2: Ollama-only PDF extraction + graph building.

Extracts events from a timeline PDF using a local Ollama model, builds the
PatientTimelineVision graph (events + connascence edges), and saves it.
NO narrative summarization — that is handled by run_gpt41_summarize.py.

Usage (from 2ndOpinionMD-MVP/server, .BeatingHeart active):
    python -u scripts/run_ollama_extract.py \
        ../data/patient_timelines/NormanEricRoberts_decrypted.pdf \
        --artifact-dir ../artifacts/timeline_extract_$(date +%Y%m%d_%H%M)

Requires a running Ollama instance with the ingestion model pulled.
Does NOT require OPENAI_API_KEY or ANTHROPIC_API_KEY.

Output:
    <artifact-dir>/patient_timeline_vision_<patient_id>_<ts>.json
    <artifact-dir>/patient_timeline_snapshot_<patient_id>_<ts>.json
    <artifact-dir>/patient_timeline_graph_final.json

Feed the vision path into run_gpt41_summarize.py for narrative summarization.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from pathlib import Path

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


def _setup_logging(*, verbose: bool, trace_http: bool) -> None:
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
        logging.getLogger(noisy).setLevel(logging.DEBUG if trace_http else logging.WARNING)


def _log(msg: str, *, emoji: str = "\U0001f4ac") -> None:
    print(f"{emoji} {msg}", file=sys.stderr, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Ollama-only PDF extraction + PTV graph building (no summarization)."
    )
    parser.add_argument("pdf", type=Path, help="Path to decrypted (or unencrypted) timeline PDF")
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        required=True,
        help="Directory for all outputs: vision JSON, snapshot JSON, graph JSON.",
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
    parser.add_argument("--password", default=None, help="PDF password if still encrypted")
    parser.add_argument(
        "--extraction-mode",
        choices=["lite", "full"],
        default="full",
        help="'lite': head+tail+MC sample (~800 pages). 'full' (default): all pages.",
    )
    parser.add_argument(
        "--ollama-url",
        default=None,
        help="Ollama base URL (default: OLLAMA_BASE_URL env var or http://localhost:11434/v1).",
    )
    parser.add_argument(
        "--ingestion-model",
        default=None,
        help="Ollama model name (default: eoh-llama3.1:8b).",
    )
    parser.add_argument(
        "--ingestion-context-tokens",
        type=int,
        default=32768,
        help="Context window size for the ingestion model (default: 32768).",
    )
    parser.add_argument(
        "--extraction-concurrency",
        type=int,
        default=1,
        help="Parallel extraction batches (default: 1). Use 2-3 with spare GPU VRAM.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--trace-http", action="store_true")
    args = parser.parse_args()

    _setup_logging(verbose=args.verbose, trace_http=args.trace_http)
    log = logging.getLogger("run_ollama_extract")

    from server.api.stream_config import OLLAMA_BASE_URL
    from server.llm.llm_client import get_ollama_client
    from server.eoh.timeline_summarizer import summarize_timeline_from_pdf

    ollama_url = args.ollama_url or OLLAMA_BASE_URL
    ingestion_model = args.ingestion_model or "eoh-llama3.1:8b"

    pdf_file = args.pdf.expanduser()
    if not pdf_file.is_file():
        _log(f"PDF not found: {pdf_file}", emoji="\u274c")
        sys.exit(1)

    artifact_dir = args.artifact_dir.expanduser().resolve()
    artifact_dir.mkdir(parents=True, exist_ok=True)
    graph_out = str(artifact_dir / "patient_timeline_graph_final.json")

    ingestion_client = get_ollama_client(base_url=ollama_url)

    _log(f"PDF: {pdf_file.resolve()}", emoji="\U0001f4c4")
    _log(f"Patient id: {args.patient_id}", emoji="\U0001f9fe")
    _log(f"Extraction mode: {args.extraction_mode}", emoji="\U0001f52c")
    _log(f"Ollama URL: {ollama_url}", emoji="\U0001f999")
    _log(f"Ingestion model: {ingestion_model}", emoji="\U0001f916")
    _log(f"Context tokens: {args.ingestion_context_tokens}", emoji="\U0001f4ca")
    _log(f"Concurrency: {args.extraction_concurrency}", emoji="\u2699\ufe0f")
    _log(f"Artifact dir: {artifact_dir}", emoji="\U0001f4e6")
    _log("Mode: EXTRACTION ONLY (no summarization)", emoji="\U0001f3af")

    async def run() -> None:
        t0 = time.perf_counter()

        result = await summarize_timeline_from_pdf(
            client=ingestion_client,
            question=args.question,
            pdf_path=str(pdf_file),
            password=args.password,
            patient_id=args.patient_id,
            graph_out_path=graph_out,
            artifact_dir=str(artifact_dir),
            extraction_mode=args.extraction_mode,
            ingestion_client=ingestion_client,
            ingestion_model=ingestion_model,
            ingestion_context_tokens=args.ingestion_context_tokens,
            extraction_concurrency=args.extraction_concurrency,
            use_claude=False,
            skip_summarization=True,
        )

        elapsed = time.perf_counter() - t0
        _log(f"Extraction complete in {elapsed:.1f}s", emoji="\u2705")

        if result.vision_path:
            _log(f"Vision JSON: {result.vision_path}", emoji="\U0001f5c2\ufe0f")
        if result.graph_out_path:
            _log(f"Graph JSON:  {result.graph_out_path}", emoji="\U0001f578\ufe0f")

        print(flush=True)
        print("=" * 80, flush=True)
        print("EXTRACTION COMPLETE — NO SUMMARIZATION", flush=True)
        print("=" * 80, flush=True)
        print(f"Vision: {result.vision_path}", flush=True)
        print(f"Graph:  {result.graph_out_path}", flush=True)
        print(flush=True)
        print("Next step:", flush=True)
        print(f"  python -u scripts/run_gpt41_summarize.py \\", flush=True)
        print(f"      {pdf_file} \\", flush=True)
        print(f"      --vision-path {result.vision_path} \\", flush=True)
        print(f"      --artifact-dir {artifact_dir}", flush=True)

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        _log("Interrupted.", emoji="\U0001f6d1")
        sys.exit(130)
    except Exception as e:
        log.exception("Extraction failed: %s", e)
        sys.exit(1)

    _log("All done.", emoji="\U0001f389")


if __name__ == "__main__":
    main()
