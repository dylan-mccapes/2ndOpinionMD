#!/usr/bin/env python3
"""
Script 2 of 2: GPT-4.1 narrative summarization + Opus final synthesis.

Loads an existing PatientTimelineVision graph (from run_ollama_extract.py),
re-extracts PDF text (fast, no LLM), then:

  1. Runs hierarchical map+reduce summarization with GPT-4.1  (~$5-7)
  2. Runs a SINGLE Opus synthesis call over the GPT-4.1 output + compact graph
     with generous output tokens for enrichment.                (~$1-2)

Total estimated cost: $6-9.

Usage (from 2ndOpinionMD-MVP/server, .BeatingHeart active):
    python -u scripts/run_gpt41_summarize.py \
        ../data/patient_timelines/NormanEricRoberts_decrypted.pdf \
        --vision-path ../artifacts/timeline_extract_YYYYMMDD_HHMM/patient_timeline_vision_*.json \
        --artifact-dir ../artifacts/timeline_extract_YYYYMMDD_HHMM

Requires OPENAI_API_KEY.  Opus synthesis requires ANTHROPIC_API_KEY.
If ANTHROPIC_API_KEY is not set, Opus synthesis is skipped (GPT-4.1 only).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import textwrap
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


OPUS_SYNTHESIS_MAX_TOKENS = 16_384


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
    logging.getLogger("openai").setLevel(logging.DEBUG if verbose else logging.INFO)


def _log(msg: str, *, emoji: str = "\U0001f4ac") -> None:
    print(f"{emoji} {msg}", file=sys.stderr, flush=True)


OPUS_SYNTHESIS_SYSTEM = textwrap.dedent("""\
    You are a senior clinical investigator synthesizing a patient's longitudinal
    medical record for a diagnostic investigation system called Ethos-of-Health (EoH).

    You will receive:
    1. GPT-4.1 narrative summaries (from hierarchical map+reduce) — field-level JSON.
    2. A compact enriched graph (typed events + connascence edges) from the
       PatientTimelineVision system.
    3. The clinical investigation question.

    Your task: produce a SINGLE JSON object with these fields:
    - "timeline_summary": A rich, longitudinal clinical narrative that weaves
      together the GPT-4.1 summaries with graph-level provenance. Include time
      anchors, organ-system trajectories, diagnostic arcs, treatment inflection
      points, and unresolved mysteries. This is the PRIMARY output — be thorough.
      Aim for 2000-4000 words.
    - "meds_and_labs_snapshot": Concise summary of critical medications, lab
      trends, monitoring issues, and pharmacological history. Include dosing
      changes, adverse reactions, and notable lab trajectories.
    - "valyu_summary": Key clinical signals that should condition external
      research queries — rare diagnoses, unusual drug combinations, atypical
      lab patterns, relevant comorbidities. Compact list form.
    - "query_terms": Search terms/phrases useful for querying guidelines,
      literature, and the patient's own timeline.
    - "enrichment_findings": Any NEW clinical insights, contradictions, or
      diagnostic hypotheses you identified by cross-referencing the graph
      structure with the narrative summaries. This field is specifically for
      enrichment — insights the GPT-4.1 pass may have missed.
    - "confidence_flags": Array of objects {"finding": str, "confidence": float,
      "reasoning": str} for any claims where your confidence is < 0.8.

    Respond with valid JSON ONLY. No markdown, no code fences, no prose outside
    the JSON object.
""")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "GPT-4.1 narrative summarization + Opus final synthesis. "
            "Loads existing PTV graph from run_ollama_extract.py."
        )
    )
    parser.add_argument("pdf", type=Path, help="Path to decrypted timeline PDF")
    parser.add_argument(
        "--vision-path",
        type=Path,
        required=True,
        help="Path to PatientTimelineVision JSON from run_ollama_extract.py.",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
        help="Directory for outputs (reuses extraction artifact dir).",
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
    parser.add_argument(
        "--skip-opus",
        action="store_true",
        help="Skip Opus synthesis (GPT-4.1 only). Useful for testing.",
    )
    parser.add_argument(
        "--opus-max-tokens",
        type=int,
        default=OPUS_SYNTHESIS_MAX_TOKENS,
        help=f"Max output tokens for Opus synthesis (default: {OPUS_SYNTHESIS_MAX_TOKENS}).",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    parser.add_argument("--trace-http", action="store_true")
    args = parser.parse_args()

    _setup_logging(verbose=args.verbose, trace_http=args.trace_http)
    log = logging.getLogger("run_gpt41_summarize")

    if not os.getenv("OPENAI_API_KEY"):
        _log(
            "OPENAI_API_KEY not set — required for GPT-4.1 summarization. "
            "Add it to server/.env or export it.",
            emoji="\u274c",
        )
        sys.exit(1)

    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))
    will_opus = has_anthropic and not args.skip_opus

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
    _log(f"Step 1: GPT-4.1 hierarchical map+reduce", emoji="\U0001f916")
    if will_opus:
        _log(
            f"Step 2: Opus final synthesis (max_tokens={args.opus_max_tokens})",
            emoji="\U0001f52d",
        )
    else:
        reason = "ANTHROPIC_API_KEY not set" if not has_anthropic else "--skip-opus"
        _log(f"Step 2: Opus synthesis SKIPPED ({reason})", emoji="\u23e9")
    if artifact_dir:
        _log(f"Artifact dir: {artifact_dir}", emoji="\U0001f4e6")

    from openai import AsyncOpenAI
    from pypdf import PdfReader
    from server.eoh.patient_timeline_vision import PatientTimelineVision
    from server.eoh.timeline_summarizer import (
        summarize_timeline_for_eoh,
        _compact_graph_for_reduce,
    )

    async def run() -> None:
        t0 = time.perf_counter()

        # --- PDF text extraction (fast, no LLM) ---
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
            f"PDF text: {len(chunks)} pages, {len(timeline_text):,} chars",
            emoji="\u2705",
        )

        # --- Load existing PTV graph ---
        _log("Loading PatientTimelineVision graph...", emoji="\U0001f578\ufe0f")
        vision = PatientTimelineVision.load(str(vision_path))
        _log(
            f"Graph loaded: {len(vision.events)} events, {vision.count_edges()} edges",
            emoji="\u2705",
        )

        # --- Step 1: GPT-4.1 hierarchical summarization ---
        _log("Starting GPT-4.1 summarization...", emoji="\U0001f680")
        client = AsyncOpenAI()

        summaries = await summarize_timeline_for_eoh(
            client=client,
            question=args.question,
            timeline_text=timeline_text,
            max_tokens=8192,
            pool=None,
            patient_id=args.patient_id,
            use_timeline_rag=False,
            timeline_vision=vision,
            use_claude=False,
        )

        t_gpt = time.perf_counter() - t0
        _log(f"GPT-4.1 summarization complete in {t_gpt:.1f}s", emoji="\u2705")

        # Print GPT-4.1 results
        print("\n" + "=" * 80, flush=True)
        print("\U0001f4dc TIMELINE SUMMARY (GPT-4.1)", flush=True)
        print("=" * 80, flush=True)
        excerpt = (summaries.timeline_summary or "")[:4000]
        print(
            excerpt + ("\u2026" if len(summaries.timeline_summary or "") > 4000 else ""),
            flush=True,
        )

        if summaries.meds_and_labs_snapshot:
            print("\n" + "=" * 80, flush=True)
            print("\U0001f48a MEDS & LABS (GPT-4.1)", flush=True)
            print("=" * 80, flush=True)
            print(summaries.meds_and_labs_snapshot[:2000], flush=True)

        # Save GPT-4.1 results
        if artifact_dir:
            gpt_export = artifact_dir / "timeline_summaries_gpt41.json"
            with open(gpt_export, "w", encoding="utf-8") as f:
                json.dump(asdict(summaries), f, indent=2, ensure_ascii=False)
            _log(f"GPT-4.1 summaries saved: {gpt_export}", emoji="\U0001f4c7")

        # --- Step 2: Opus final synthesis ---
        if not will_opus:
            _log("Opus synthesis skipped — saving GPT-4.1 results as final.", emoji="\u23e9")
            _save_final(summaries, vision, artifact_dir, args.patient_id)
            return

        _log("Starting Opus final synthesis...", emoji="\U0001f52d")
        from server.llm.llm_client import claude_chat_async, CLAUDE_SYNTHESIS_MODEL

        compact_graph = _compact_graph_for_reduce(vision, max_chars=80_000)

        synthesis_input = json.dumps({
            "question": args.question,
            "gpt41_summaries": {
                "timeline_summary": summaries.timeline_summary or "",
                "meds_and_labs_snapshot": summaries.meds_and_labs_snapshot or "",
                "valyu_summary": summaries.valyu_summary or "",
            },
            "enriched_graph": compact_graph,
        })

        _log(
            f"Opus input: {len(synthesis_input):,} chars "
            f"(~{len(synthesis_input) // 4:,} tokens); "
            f"max_tokens={args.opus_max_tokens}",
            emoji="\U0001f4ca",
        )

        raw_opus = await claude_chat_async(
            messages=[{"role": "user", "content": synthesis_input}],
            system=OPUS_SYNTHESIS_SYSTEM,
            model=CLAUDE_SYNTHESIS_MODEL,
            max_tokens=args.opus_max_tokens,
            temperature=0.0,
        )

        t_opus = time.perf_counter() - t0 - t_gpt
        _log(f"Opus synthesis complete in {t_opus:.1f}s", emoji="\u2705")

        raw_opus = (raw_opus or "").strip()
        if raw_opus.startswith("```"):
            lines = raw_opus.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw_opus = "\n".join(lines).strip()

        opus_data = {}
        try:
            opus_data = json.loads(raw_opus)
        except json.JSONDecodeError:
            _log(
                "Opus returned non-JSON; saving raw text as timeline_summary.",
                emoji="\u26a0\ufe0f",
            )
            opus_data = {"timeline_summary": raw_opus}

        if opus_data.get("timeline_summary"):
            summaries.timeline_summary = opus_data["timeline_summary"]
        if opus_data.get("meds_and_labs_snapshot"):
            summaries.meds_and_labs_snapshot = opus_data["meds_and_labs_snapshot"]
        if opus_data.get("valyu_summary"):
            summaries.valyu_summary = opus_data["valyu_summary"]

        opus_enrichment = {}
        for key in ("enrichment_findings", "confidence_flags", "query_terms"):
            if opus_data.get(key):
                opus_enrichment[key] = opus_data[key]

        if opus_enrichment:
            existing = summaries.timeline_enrichment or {}
            existing["opus_synthesis"] = opus_enrichment
            summaries.timeline_enrichment = existing

        # Print Opus results
        print("\n" + "=" * 80, flush=True)
        print("\U0001f52d TIMELINE SUMMARY (Opus synthesis)", flush=True)
        print("=" * 80, flush=True)
        excerpt = (summaries.timeline_summary or "")[:6000]
        print(
            excerpt + ("\u2026" if len(summaries.timeline_summary or "") > 6000 else ""),
            flush=True,
        )

        if opus_enrichment.get("enrichment_findings"):
            print("\n" + "=" * 80, flush=True)
            print("\U0001f4a1 OPUS ENRICHMENT FINDINGS", flush=True)
            print("=" * 80, flush=True)
            for finding in opus_enrichment["enrichment_findings"][:10]:
                if isinstance(finding, str):
                    print(f"  \u2022 {finding}", flush=True)
                elif isinstance(finding, dict):
                    print(f"  \u2022 {json.dumps(finding, indent=4)}", flush=True)

        # Save Opus results
        if artifact_dir:
            opus_raw_path = artifact_dir / "opus_synthesis_raw.json"
            with open(opus_raw_path, "w", encoding="utf-8") as f:
                json.dump(opus_data, f, indent=2, ensure_ascii=False)
            _log(f"Opus raw output: {opus_raw_path}", emoji="\U0001f4c7")

        _save_final(summaries, vision, artifact_dir, args.patient_id)

        total = time.perf_counter() - t0
        _log(
            f"Total: {total:.1f}s (GPT-4.1: {t_gpt:.1f}s, Opus: {t_opus:.1f}s)",
            emoji="\u23f1\ufe0f",
        )

    def _save_final(
        summaries,
        vision,
        artifact_dir: Optional[Path],
        patient_id: str,
    ) -> None:
        if artifact_dir:
            export_path = artifact_dir / "timeline_summaries_final.json"
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump(asdict(summaries), f, indent=2, ensure_ascii=False)
            _log(f"Final summaries: {export_path}", emoji="\U0001f4c7")

            vision_out = artifact_dir / f"patient_timeline_vision_final_{patient_id}.json"
            vision.save(str(vision_out), force=True)
            _log(f"Final vision graph: {vision_out}", emoji="\U0001f578\ufe0f")

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
