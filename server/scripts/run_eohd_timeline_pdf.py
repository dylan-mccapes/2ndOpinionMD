#!/usr/bin/env python3
"""
Run the EoHD-oriented timeline PDF pipeline (extract → PatientTimelineVision →
summarize_timeline_for_eoh → optional graph export).

Usage (from 2ndOpinionMD-MVP/server, .BeatingHeart active):
    python -u scripts/run_eohd_timeline_pdf.py ../data/patient_timelines/NormanEricRoberts_decrypted.pdf \\
        --artifact-dir ../artifacts/timeline_share_$(date +%Y%m%d)

Requires OPENAI_API_KEY in .env or shell environment.
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

# --- Path bootstrap ---
script_dir = Path(__file__).resolve().parent
server_dir = script_dir.parent
parent_of_server = server_dir.parent

if str(parent_of_server) not in sys.path:
    sys.path.insert(0, str(parent_of_server))

os.chdir(server_dir)

from dotenv import load_dotenv
load_dotenv(server_dir.parent / ".env", override=False)
load_dotenv(server_dir / ".env", override=True)


class EmojiLogFormatter(logging.Formatter):
    _EMOJI = {
        logging.DEBUG: "🐛",
        logging.INFO: "📋",
        logging.WARNING: "⚠️",
        logging.ERROR: "❌",
        logging.CRITICAL: "🔥",
    }

    def format(self, record: logging.LogRecord) -> str:
        record.levelemoji = self._EMOJI.get(record.levelno, "📌")  # type: ignore[attr-defined]
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
            fmt="%(levelemoji)s %(asctime)s │ %(name)s │ %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    root.addHandler(handler)
    logging.getLogger("server").setLevel(level)
    for noisy in ("httpx", "httpcore", "urllib3"):
        logging.getLogger(noisy).setLevel(logging.DEBUG if trace_http else logging.WARNING)
    logging.getLogger("openai").setLevel(logging.DEBUG if verbose else logging.INFO)


def _log(msg: str, *, emoji: str = "💬") -> None:
    print(f"{emoji} {msg}", file=sys.stderr, flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="EoHD-style timeline import from PDF.")
    parser.add_argument("pdf", type=Path, help="Path to decrypted (or unencrypted) timeline PDF")
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
        help="Directory for all outputs: vision snapshot, gap/synthesis sidecars, summaries JSON, graph JSON.",
    )
    parser.add_argument("--graph-out", type=Path, default=None, help="Write final graph JSON to this path.")
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
        help=(
            "Graph event extraction tier. "
            "'lite' (default): head+tail+Monte Carlo sample (~800 pages, ~4-5 LLM calls). "
            "'full': all pages (~23 calls for a 4K-page record)."
        ),
    )
    parser.add_argument(
        "--llm-backend",
        choices=["openai", "ollama", "ollama-full"],
        default="openai",
        help=(
            "LLM backend for ingestion. "
            "'openai' (default): all calls go to OpenAI. "
            "'ollama': event extraction + connascence use local Ollama; "
            "narrative summarization stays on OpenAI. "
            "'ollama-full': ALL calls use Ollama (no OpenAI key needed)."
        ),
    )
    parser.add_argument(
        "--ollama-url",
        default=None,
        help="Ollama base URL (default: OLLAMA_BASE_URL env var or http://localhost:11434/v1).",
    )
    parser.add_argument(
        "--ingestion-model",
        default=None,
        help=(
            "Model name for PDF event extraction and connascence passes. "
            "With --llm-backend ollama, defaults to INGESTION_MODEL or eoh-llama-8b. "
            "With --llm-backend openai, defaults to EOH_TIMELINE_SUMMARIZER_MODEL unless INGESTION_MODEL is set."
        ),
    )
    parser.add_argument(
        "--ingestion-context-tokens",
        type=int,
        default=None,
        help=(
            "Context window size (tokens) of the ingestion model, used to compute "
            "batch sizes for PDF event extraction. "
            "Defaults to 1,048,576 (GPT-4.1) for OpenAI backend. "
            "For Ollama backends defaults to 16,384 (tighter KV; override with "
            "--ingestion-context-tokens or INGESTION_CONTEXT_TOKENS). "
            "Override with the actual context size of any custom model."
        ),
    )
    parser.add_argument(
        "--extraction-concurrency",
        type=int,
        default=1,
        help=(
            "Number of PDF extraction batches to run in parallel. "
            "Default 1 (sequential). "
            "For a GPU with spare VRAM (e.g. RTX 4090 + llama3.1:8b-instruct-q8_0 ~9GB) "
            "use 2 or 3 to saturate the GPU and cut wall-clock time roughly in half. "
            "Each concurrent slot uses one full model context worth of VRAM."
        ),
    )
    parser.add_argument(
        "--use-claude",
        action="store_true",
        help=(
            "Use Claude (Opus via CLAUDE_SYNTHESIS_MODEL) where the summarizer allows it. "
            "Requires ANTHROPIC_API_KEY. With default --claude-scope reduce_only, the timeline "
            "summarizer uses OpenAI only (including hierarchical map+reduce). "
            "Use --claude-scope all to run Opus inside this summarizer (expensive)."
        ),
    )
    parser.add_argument(
        "--claude-scope",
        choices=["reduce_only", "all"],
        default=None,
        help=(
            "Anthropic usage when --use-claude is set. "
            "reduce_only (default via EOH_TIMELINE_CLAUDE_SCOPE): timeline summarizer uses OpenAI "
            "only (hierarchical + single-pass). "
            "all: Opus for hierarchical map+reduce and single-pass (legacy, very expensive). "
            "When omitted, env EOH_TIMELINE_CLAUDE_SCOPE applies (default reduce_only)."
        ),
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--trace-http", action="store_true")
    args = parser.parse_args()

    _setup_logging(verbose=args.verbose, trace_http=args.trace_http)
    log = logging.getLogger("run_eohd_timeline_pdf")

    from openai import AsyncOpenAI
    from server.api.stream_config import OLLAMA_BASE_URL, EOH_TIMELINE_SUMMARIZER_MODEL
    from server.llm.llm_client import get_ollama_client
    from server.eoh.timeline_summarizer import summarize_timeline_from_pdf

    backend = args.llm_backend
    ollama_url = args.ollama_url or OLLAMA_BASE_URL

    # API key only required when OpenAI is used for at least one call.
    if backend != "ollama-full" and not os.getenv("OPENAI_API_KEY"):
        _log(
            "OPENAI_API_KEY not set — required for summarization. "
            "Add it to server/.env or export it in your shell. "
            "Use --llm-backend ollama-full to run entirely without OpenAI.",
            emoji="❌",
        )
        sys.exit(1)

    # Resolve the ingestion model name.
    if args.ingestion_model:
        ingestion_model = args.ingestion_model
    elif backend in ("ollama", "ollama-full"):
        ingestion_model = os.getenv("INGESTION_MODEL", "eoh-llama-8b")
    else:
        # OpenAI backend: default to premium GPT unless INGESTION_MODEL is explicitly set
        ingestion_model = os.getenv("INGESTION_MODEL") or EOH_TIMELINE_SUMMARIZER_MODEL

    # Resolve ingestion context window.
    # Ollama 8B models have 128K training context but sustaining a full-context
    # KV cache during extraction batches causes timeouts.  32K is a safe default
    # that keeps each batch under ~8K input tokens, well within VRAM budget.
    if args.ingestion_context_tokens is not None:
        ingestion_context_tokens = args.ingestion_context_tokens
    elif backend in ("ollama", "ollama-full"):
        # Match timeline_summarizer Ollama defaults (smaller ctx → often better 8B JSON).
        ingestion_context_tokens = 16_384
    else:
        ingestion_context_tokens = None  # uses GPT-4.1 1M default

    # Build clients.
    if backend == "openai":
        summary_client = AsyncOpenAI()
        ingestion_client = None  # falls back to summary_client inside the pipeline
    elif backend == "ollama":
        summary_client = AsyncOpenAI()  # OpenAI for narrative summarization
        ingestion_client = get_ollama_client(base_url=ollama_url)
    else:  # ollama-full
        summary_client = get_ollama_client(base_url=ollama_url)
        ingestion_client = get_ollama_client(base_url=ollama_url)

    pdf_file = args.pdf.expanduser()
    if not pdf_file.is_file():
        _log(f"PDF not found: {pdf_file}", emoji="❌")
        sys.exit(1)

    artifact_dir_resolved: Optional[Path] = None
    if args.artifact_dir:
        artifact_dir_resolved = args.artifact_dir.expanduser().resolve()
        artifact_dir_resolved.mkdir(parents=True, exist_ok=True)

    if args.graph_out:
        graph_out = str(args.graph_out.expanduser().resolve())
    elif artifact_dir_resolved is not None:
        graph_out = str(artifact_dir_resolved / "patient_timeline_graph_final.json")
    else:
        graph_out = None

    artifact_dir_str = str(artifact_dir_resolved) if artifact_dir_resolved else None

    _log(f"PDF: {pdf_file.resolve()}", emoji="📄")
    _log(f"Patient id: {args.patient_id}", emoji="🧾")
    _log(f"Extraction mode: {args.extraction_mode}", emoji="🔬")
    _cs = args.claude_scope or os.getenv("EOH_TIMELINE_CLAUDE_SCOPE", "reduce_only")
    if args.use_claude and _cs == "all":
        _summ_desc = f"Claude Opus allowed in timeline summarizer (scope=all) / base {EOH_TIMELINE_SUMMARIZER_MODEL}"
    elif args.use_claude:
        _summ_desc = (
            f"{EOH_TIMELINE_SUMMARIZER_MODEL} for timeline summarizer "
            f"(scope={_cs}; --use-claude does not send Opus there)"
        )
    else:
        _summ_desc = str(EOH_TIMELINE_SUMMARIZER_MODEL)
    _log(
        f"LLM backend: {backend}  |  ingestion model: {ingestion_model}  |  summarizer: {_summ_desc}",
        emoji="🤖",
    )
    if backend in ("ollama", "ollama-full"):
        _log(f"Ollama URL: {ollama_url}", emoji="🦙")
    if artifact_dir_str:
        _log(f"Artifact dir: {artifact_dir_str}", emoji="📦")

    async def run() -> None:
        t0 = time.perf_counter()

        _opus_in_summarizer = args.use_claude and _cs == "all"
        _summarizer_model = (
            ingestion_model if backend == "ollama-full" and not _opus_in_summarizer else None
        )
        summaries = await summarize_timeline_from_pdf(
            client=summary_client,
            question=args.question,
            pdf_path=str(pdf_file),
            password=args.password,
            patient_id=args.patient_id,
            graph_out_path=graph_out,
            artifact_dir=artifact_dir_str,
            extraction_mode=args.extraction_mode,
            ingestion_client=ingestion_client,
            ingestion_model=ingestion_model,
            ingestion_context_tokens=ingestion_context_tokens,
            extraction_concurrency=args.extraction_concurrency,
            use_claude=args.use_claude,
            summarizer_model=_summarizer_model,
            claude_scope=args.claude_scope,
        )

        elapsed = time.perf_counter() - t0
        _log(f"Done in {elapsed:.1f}s", emoji="✅")

        print("\n" + "=" * 80, flush=True)
        print("📜 TIMELINE SUMMARY", flush=True)
        print("=" * 80, flush=True)
        excerpt = (summaries.timeline_summary or "")[:4000]
        print(excerpt + ("…" if len(summaries.timeline_summary or "") > 4000 else ""), flush=True)

        if summaries.meds_and_labs_snapshot:
            print("\n" + "=" * 80, flush=True)
            print("💊 MEDS & LABS", flush=True)
            print("=" * 80, flush=True)
            print(summaries.meds_and_labs_snapshot[:2000], flush=True)

        if summaries.valyu_summary:
            print("\n" + "=" * 80, flush=True)
            print("🔎 VALYU / QUERY SIGNALS", flush=True)
            print("=" * 80, flush=True)
            print(summaries.valyu_summary[:1500], flush=True)

        if summaries.vision_path:
            _log(f"Vision snapshot: {summaries.vision_path}", emoji="🗂️")
        if summaries.graph_out_path:
            _log(f"Graph export:    {summaries.graph_out_path}", emoji="🕸️")
        if artifact_dir_resolved is not None:
            export_path = artifact_dir_resolved / "timeline_summaries_export.json"
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(asdict(summaries), f, indent=2, ensure_ascii=False)
            _log(f"Summaries JSON:  {export_path}", emoji="📇")

    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        _log("Interrupted.", emoji="🛑")
        sys.exit(130)
    except Exception as e:
        log.exception("Pipeline failed: %s", e)
        sys.exit(1)

    _log("All done.", emoji="🎉")


if __name__ == "__main__":
    main()
