#!/usr/bin/env python3
"""
ptv_test_harness.py — Multi-timeline, multi-model PTV acceptance test harness.

Runs extraction pipelines across a matrix of (timeline_source, model_config),
grades each output against the acceptance rubric, and produces a comparison
report for evaluating extraction quality across configurations.

═══════════════════════════════════════════════════════════════════════════════
TEST STRATEGY
═══════════════════════════════════════════════════════════════════════════════

Timeline Sources (rows):
  1. Norman Eric Roberts  — Real 4,223-page Kaiser PDF. MG + multimorbid.
                            Stress test: huge document, messy EHR formatting.
  2. Mock RA Patient      — Synthetic 15-page PDF with explicit ISO dates.
                            Gold standard: every gate should pass if extraction
                            is not hallucinating.
  3. MIMIC-IV Discharge   — Clinical notes from MIMIC-IV (no labs/drugs in
                            source). Tests how extraction handles note-only
                            input. Medication normalization expected to fail.
                            Extend via MKG for structured data overlay.
  4. [Future] Andras      — Additional patient timelines as they arrive.

Model Configs (columns):
  A. eoh-llama3.1:8b      — Local Ollama, free, fast. Baseline.
  B. eoh-llama3.1:70b     — Local Ollama, bigger model. Quality delta?
  C. gpt-4.1              — Cloud API, extraction + enrichment.
  D. gpt-4.1-mini         — Cloud API, cheaper. Quality/cost tradeoff.
  E. [Future] claude-*     — When Anthropic credit is restored.

═══════════════════════════════════════════════════════════════════════════════
HARNESS MODES
═══════════════════════════════════════════════════════════════════════════════

  grade-only     Grade existing PTV artifacts (no extraction). Fast.
  extract+grade  Run extraction then grade. Requires model access.
  compare        Load multiple scorecards and produce comparison table.
  mimic-prep     Prepare MIMIC discharge notes as synthetic timeline PDFs.

═══════════════════════════════════════════════════════════════════════════════

Usage:
  cd 2ndOpinionMD-MVP/server

  # Grade all existing artifacts
  python scripts/ptv_test_harness.py grade-only --artifacts-dir ../artifacts

  # Grade a specific build
  python scripts/ptv_test_harness.py grade-only \
      --artifacts-dir ../artifacts/timeline_ollama_20260330_1312

  # Extract + grade with a specific model
  python scripts/ptv_test_harness.py extract+grade \
      --pdf ../data/patient_timelines/NormanEricRoberts_decrypted.pdf \
      --patient-id norman_eric_roberts \
      --model eoh-llama3.1:8b \
      --output-dir ../artifacts/harness_run_$(date +%Y%m%d_%H%M)

  # Compare scorecards
  python scripts/ptv_test_harness.py compare \
      --scorecards ../artifacts/harness_run_*/scorecard.json

  # Prepare MIMIC notes as PDFs for extraction testing
  python scripts/ptv_test_harness.py mimic-prep \
      --limit 5 \
      --output-dir ../data/patient_timelines/mimic_test_set
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

_SCRIPT_DIR = Path(__file__).resolve().parent
_SERVER_DIR = _SCRIPT_DIR.parent
_MVP_DIR = _SERVER_DIR.parent

if str(_MVP_DIR) not in sys.path:
    sys.path.insert(0, str(_MVP_DIR))


# ── grade-only mode ──────────────────────────────────────────────────────────

def cmd_grade_only(args: argparse.Namespace) -> None:
    """Grade existing PTV artifact directories."""
    sys.path.insert(0, str(_SCRIPT_DIR))
    from grade_ptv_build import grade_ptv_build, print_scorecard

    artifacts_dir = Path(args.artifacts_dir).resolve()
    if not artifacts_dir.is_dir():
        print(f"Not a directory: {artifacts_dir}", file=sys.stderr)
        sys.exit(1)

    vision_files = sorted(artifacts_dir.rglob("patient_timeline_vision_*.json"))
    # Exclude enriched/rxnorm variants — grade the base extraction
    vision_files = [
        f for f in vision_files
        if "_enriched" not in f.name
        and "_rxnorm" not in f.name
        and "_manifest" not in f.name
    ]

    if not vision_files:
        print(f"No PTV vision files found under {artifacts_dir}", file=sys.stderr)
        sys.exit(1)

    scorecards: List[Dict[str, Any]] = []
    for vf in vision_files:
        print(f"\n{'━' * 72}")
        print(f"  Grading: {vf.relative_to(artifacts_dir.parent)}")
        print(f"{'━' * 72}")
        sc = grade_ptv_build(vf)
        print_scorecard(sc)
        scorecards.append(sc.to_dict())

        sc_path = vf.parent / "scorecard.json"
        with open(sc_path, "w") as f:
            json.dump(sc.to_dict(), f, indent=2)
        print(f"  📋 Scorecard saved: {sc_path}")

    if len(scorecards) > 1:
        _print_comparison_table(scorecards)

    summary_path = artifacts_dir / "harness_summary.json"
    with open(summary_path, "w") as f:
        json.dump({
            "run_at": datetime.now(timezone.utc).isoformat(),
            "mode": "grade-only",
            "scorecards": scorecards,
        }, f, indent=2)
    print(f"\n📊 Summary written to {summary_path}")


# ── extract+grade mode ───────────────────────────────────────────────────────

def cmd_extract_grade(args: argparse.Namespace) -> None:
    """Run extraction pipeline then grade the output."""
    import asyncio

    sys.path.insert(0, str(_SCRIPT_DIR))
    from grade_ptv_build import grade_ptv_build, print_scorecard

    pdf_path = Path(args.pdf).resolve()
    if not pdf_path.is_file():
        print(f"PDF not found: {pdf_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    model = args.model or "eoh-qwen"
    patient_id = args.patient_id or pdf_path.stem.lower().replace(" ", "_")

    is_ollama = not model.startswith("gpt-") and not model.startswith("claude-")

    print(f"📄 PDF: {pdf_path}")
    print(f"🧬 Patient: {patient_id}")
    print(f"🤖 Model: {model}")
    print(f"📦 Output: {output_dir}")
    print()

    meta = {
        "pdf": str(pdf_path),
        "patient_id": patient_id,
        "model": model,
        "is_ollama": is_ollama,
        "started_at": datetime.now(timezone.utc).isoformat(),
    }

    os.chdir(_SERVER_DIR)
    from dotenv import load_dotenv
    load_dotenv(_MVP_DIR / ".env", override=False)
    load_dotenv(_SERVER_DIR / ".env", override=True)

    from server.eoh.timeline_summarizer import summarize_timeline_from_pdf

    graph_out = str(output_dir / "patient_timeline_graph_final.json")

    if is_ollama:
        from server.api.stream_config import OLLAMA_BASE_URL
        from server.llm.llm_client import get_ollama_client

        ollama_url = args.ollama_url or OLLAMA_BASE_URL
        client = get_ollama_client(base_url=ollama_url)

        async def _run():
            return await summarize_timeline_from_pdf(
                client=client,
                question="Perform a comprehensive diagnostic investigation.",
                pdf_path=str(pdf_path),
                patient_id=patient_id,
                graph_out_path=graph_out,
                artifact_dir=str(output_dir),
                extraction_mode=args.extraction_mode or "full",
                ingestion_client=client,
                ingestion_model=model,
                ingestion_context_tokens=args.context_tokens or 32768,
                extraction_concurrency=args.concurrency or 1,
                use_claude=False,
                skip_summarization=True,
            )
    else:
        from openai import AsyncOpenAI
        client = AsyncOpenAI()

        async def _run():
            return await summarize_timeline_from_pdf(
                client=client,
                question="Perform a comprehensive diagnostic investigation.",
                pdf_path=str(pdf_path),
                patient_id=patient_id,
                graph_out_path=graph_out,
                artifact_dir=str(output_dir),
                extraction_mode=args.extraction_mode or "full",
                ingestion_model=model,
                use_claude=False,
                skip_summarization=True,
            )

    t0 = time.perf_counter()
    try:
        result = asyncio.run(_run())
    except KeyboardInterrupt:
        print("\n🛑 Interrupted.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Extraction failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

    elapsed = time.perf_counter() - t0
    meta["elapsed_seconds"] = round(elapsed, 1)
    meta["finished_at"] = datetime.now(timezone.utc).isoformat()
    meta["vision_path"] = result.vision_path

    with open(output_dir / "harness_meta.json", "w") as f:
        json.dump(meta, f, indent=2)

    print(f"\n✅ Extraction complete in {elapsed:.1f}s")

    if result.vision_path:
        print(f"\n{'━' * 72}")
        print(f"  GRADING")
        print(f"{'━' * 72}")
        sc = grade_ptv_build(result.vision_path)
        print_scorecard(sc)

        sc_dict = sc.to_dict()
        sc_dict["harness_meta"] = meta
        with open(output_dir / "scorecard.json", "w") as f:
            json.dump(sc_dict, f, indent=2)
        print(f"📋 Scorecard saved: {output_dir / 'scorecard.json'}")
    else:
        print("⚠️  No vision path returned — cannot grade.", file=sys.stderr)


# ── compare mode ─────────────────────────────────────────────────────────────

def cmd_compare(args: argparse.Namespace) -> None:
    """Load scorecards and produce a comparison table."""
    paths = []
    for p in args.scorecards:
        p = Path(p)
        if p.is_dir():
            paths.extend(sorted(p.rglob("scorecard.json")))
        elif p.is_file():
            paths.append(p)

    if not paths:
        print("No scorecards found.", file=sys.stderr)
        sys.exit(1)

    scorecards = []
    for p in paths:
        with open(p) as f:
            sc = json.load(f)
        sc["_path"] = str(p)
        scorecards.append(sc)

    _print_comparison_table(scorecards)

    if args.output:
        with open(args.output, "w") as f:
            json.dump({
                "run_at": datetime.now(timezone.utc).isoformat(),
                "mode": "compare",
                "scorecards": scorecards,
            }, f, indent=2)
        print(f"\n📊 Comparison written to {args.output}")


def _print_comparison_table(scorecards: List[Dict[str, Any]]) -> None:
    """Print a compact comparison of multiple scorecards."""
    print(f"\n{'═' * 90}")
    print(f"  COMPARISON TABLE — {len(scorecards)} builds")
    print(f"{'═' * 90}")

    gate_names = []
    if scorecards and scorecards[0].get("hard_gates"):
        gate_names = [g["name"] for g in scorecards[0]["hard_gates"]]

    header = f"{'Build':<40} {'Overall':^10}"
    for gn in gate_names:
        short = gn.split(" ", 1)[1][:12] if " " in gn else gn[:12]
        header += f" {short:^12}"
    print(header)
    print("─" * len(header))

    for sc in scorecards:
        source = sc.get("source_file", "?")
        label = Path(source).parent.name if "/" in source else source[:38]
        meta = sc.get("harness_meta", {})
        if meta.get("model"):
            label = f"{meta['model'][:15]} / {label[:22]}"

        overall = sc.get("overall_level", "?")
        emoji = {"accept": "🟢", "candidate": "🟡", "reject": "❌"}.get(overall, "⚪")
        row = f"{label:<40} {emoji + ' ' + overall:^10}"

        for gate in sc.get("hard_gates", []):
            ge = gate.get("emoji", "⚪")
            val = gate.get("metric", "?")
            row += f"  {ge} {val:>7}"
        print(row)

    print(f"{'═' * 90}")


# ── mimic-prep mode ──────────────────────────────────────────────────────────

def cmd_mimic_prep(args: argparse.Namespace) -> None:
    """
    Prepare MIMIC discharge notes as individual pseudo-PDF text files
    for extraction testing. Requires PostgreSQL with MIMIC data loaded.

    MIMIC limitations: no structured labs or drugs in discharge summaries.
    Use MKG overlay for structured medication/lab enrichment post-extraction.
    """
    import psycopg2
    from psycopg2.extras import DictCursor

    from server.timeline.seed_data import get_db_url

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    limit = args.limit or 5
    min_length = args.min_length or 2000

    conn = psycopg2.connect(get_db_url())
    try:
        with conn.cursor(cursor_factory=DictCursor) as cur:
            cur.execute("""
                SELECT id, source, external_id, text, meta
                FROM rag_corpus
                WHERE source IN ('mimic3_note', 'mimic4_note')
                  AND length(text) >= %s
                ORDER BY random()
                LIMIT %s
            """, (min_length, limit))
            rows = cur.fetchall()
    finally:
        conn.close()

    if not rows:
        print("No MIMIC notes found in rag_corpus. "
              "Run ingest_mimic_notes_to_timeline.py first.", file=sys.stderr)
        sys.exit(1)

    manifest = []
    for row in rows:
        meta = row["meta"] or {}
        subject_id = meta.get("subject_id", meta.get("patient_id", "UNK"))
        patient_id = f"mimic_{subject_id}"
        ext_id = row["external_id"] or str(row["id"])

        # Write as plain text "pseudo-PDF" — the extraction pipeline can
        # handle .txt via the page-text fallback path, or use reportlab
        # to create real PDFs if needed.
        fname = f"{patient_id}_{ext_id}.txt"
        fpath = output_dir / fname

        header = (
            f"DISCHARGE SUMMARY\n"
            f"Patient ID: {patient_id}\n"
            f"Source: {row['source']}\n"
            f"Note Type: {meta.get('note_type', 'discharge')}\n"
            f"Chart Time: {meta.get('charttime', 'unknown')}\n"
            f"{'=' * 72}\n\n"
        )

        with open(fpath, "w") as f:
            f.write(header + row["text"])

        manifest.append({
            "patient_id": patient_id,
            "file": fname,
            "source": row["source"],
            "external_id": ext_id,
            "text_length": len(row["text"]),
            "note_type": meta.get("note_type"),
            "charttime": meta.get("charttime"),
        })
        print(f"  📄 {fname} ({len(row['text']):,} chars)")

    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(manifest, f, indent=2)
    print(f"\n📋 Manifest: {manifest_path}")
    print(f"📊 Prepared {len(manifest)} MIMIC notes for extraction testing.")
    print(f"\nNote: MIMIC discharge summaries lack structured labs/drugs.")
    print(f"Medication normalization (gate 1.4) expected to underperform.")
    print(f"Use MKG overlay post-extraction for structured data enrichment.")


# ── CLI ───────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="PTV acceptance test harness — multi-timeline, multi-model evaluation.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # grade-only
    p_grade = sub.add_parser("grade-only", help="Grade existing PTV artifacts")
    p_grade.add_argument("--artifacts-dir", required=True,
                         help="Directory containing PTV artifact subdirs")

    # extract+grade
    p_extract = sub.add_parser("extract+grade",
                               help="Run extraction then grade")
    p_extract.add_argument("--pdf", required=True, help="Path to timeline PDF")
    p_extract.add_argument("--patient-id", help="Patient identifier")
    p_extract.add_argument("--model", help="Model name (default: eoh-qwen)")
    p_extract.add_argument("--output-dir", required=True,
                           help="Artifact output directory")
    p_extract.add_argument("--ollama-url", help="Ollama base URL")
    p_extract.add_argument("--extraction-mode", choices=["lite", "full"],
                           default="full")
    p_extract.add_argument("--context-tokens", type=int, default=65536)
    p_extract.add_argument("--concurrency", type=int, default=1)

    # compare
    p_compare = sub.add_parser("compare",
                               help="Compare multiple scorecard files")
    p_compare.add_argument("--scorecards", nargs="+", required=True,
                           help="Paths to scorecard.json files or directories")
    p_compare.add_argument("-o", "--output", help="Write comparison JSON to file")

    # mimic-prep
    p_mimic = sub.add_parser("mimic-prep",
                             help="Prepare MIMIC notes for extraction testing")
    p_mimic.add_argument("--output-dir", required=True,
                         help="Output directory for prepared notes")
    p_mimic.add_argument("--limit", type=int, default=5,
                         help="Number of notes to prepare (default: 5)")
    p_mimic.add_argument("--min-length", type=int, default=2000,
                         help="Minimum note length in chars (default: 2000)")

    args = parser.parse_args()

    dispatch = {
        "grade-only": cmd_grade_only,
        "extract+grade": cmd_extract_grade,
        "compare": cmd_compare,
        "mimic-prep": cmd_mimic_prep,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
