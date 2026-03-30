#!/usr/bin/env python3
"""
EoH Detective (EoHD) harness — runs the full detective stream outside the
web server, printing SSE events to stdout and saving results.

Connects directly to Postgres for graph + pool, no FastAPI needed.

Usage (from 2ndOpinionMD-MVP):
    python server/scripts/run_eohd.py \
        --patient-id NORMAN_ROBERTS \
        --query "What are the key unresolved clinical issues and how has treatment failed?"

    # Short form with focus and step cap:
    python server/scripts/run_eohd.py \
        -p NORMAN_ROBERTS \
        -q "How much does alcoholism contribute to his condition?" \
        --focus diagnostic_landscape \
        --max-steps 4

    # Dry-run (planner only, no step execution):
    python server/scripts/run_eohd.py -p NORMAN_ROBERTS -q "..." --dry-run

Requires: asyncpg, openai, anthropic (optional), sentence-transformers
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Path + env setup
# ---------------------------------------------------------------------------
script_dir = Path(__file__).resolve().parent
server_dir = script_dir.parent
project_root = server_dir.parent

if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv

for name in (".pulse", ".env"):
    p = project_root / name
    if p.is_file():
        load_dotenv(p, override=True)
        break

os.chdir(project_root)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_FMT = "%(asctime)s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FMT, datefmt="%H:%M:%S")
log = logging.getLogger("run_eohd")

# Quiet noisy libs
for lib in ("httpx", "httpcore", "openai", "urllib3", "matplotlib", "datasets"):
    logging.getLogger(lib).setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Stub Request object (the generator calls request.is_disconnected())
# ---------------------------------------------------------------------------

class _FakeQueryParams(dict):
    """Mimics starlette QueryParams (dict-like, .get() returns None)."""
    pass


class _FakeRequest:
    """Minimal stand-in for starlette.requests.Request."""

    def __init__(self):
        self.query_params = _FakeQueryParams()
        self.headers = {}
        self.state = type("State", (), {})()

    async def is_disconnected(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Pretty-print SSE
# ---------------------------------------------------------------------------

_QUIET_EVENTS = {
    "timeline_flare_features",
    "timeline_signals_summary",
    "timeline_diagnostic_landscape_history",
}

_TRUNC_EVENTS = {
    "detective_timeline_snapshot",
    "llm_start",
}


def _print_sse(event_type: str, data: Any, *, verbose: bool = False) -> None:
    """Colour-coded SSE printer."""
    if event_type in _QUIET_EVENTS and not verbose:
        return

    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[32m"
    CYAN = "\033[36m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    RESET = "\033[0m"

    colour = {
        "start": GREEN,
        "status": CYAN,
        "detective_plan": YELLOW,
        "evidence_map": YELLOW,
        "llm_done": GREEN,
        "detective_report": f"{BOLD}{GREEN}",
        "detective_run_saved": f"{BOLD}{GREEN}",
        "end": f"{BOLD}{GREEN}",
        "error": RED,
    }.get(event_type, DIM)

    prefix = f"{colour}[{event_type}]{RESET}"

    if isinstance(data, dict):
        if event_type == "detective_report":
            text = data.get("report") or data.get("text") or ""
            print(f"\n{prefix}")
            print("=" * 72)
            print(text)
            print("=" * 72)
            return

        if event_type == "llm_done":
            text = data.get("text", "")
            step = data.get("step_id", "?")
            print(f"\n{prefix} step={step}")
            print("-" * 60)
            snip = text[:2000] + ("..." if len(text) > 2000 else "")
            print(snip)
            print("-" * 60)
            return

        if event_type in _TRUNC_EVENTS and not verbose:
            summary = {k: (str(v)[:120] + "...") if isinstance(v, (str, list)) and len(str(v)) > 120 else v
                       for k, v in data.items()}
            print(f"{prefix} {json.dumps(summary, default=str)[:400]}")
            return

        print(f"{prefix} {json.dumps(data, default=str)[:600]}")
    else:
        print(f"{prefix} {str(data)[:600]}")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

async def run_detective(
    patient_id: str,
    query: str,
    *,
    focus: str = "diagnostic_landscape",
    max_steps: int = 6,
    with_llm: bool = True,
    use_valyu: bool = False,
    dry_run: bool = False,
    verbose: bool = False,
    output_dir: Optional[str] = None,
) -> Dict[str, Any]:
    """Execute a full EoHD run, return collected metadata."""

    import asyncpg

    dsn = os.getenv("SYNC_DATABASE_URL") or os.getenv("DATABASE_URL")
    if dsn and "+asyncpg" in dsn:
        dsn = dsn.replace("+asyncpg", "")
    if dsn and "+psycopg" in dsn:
        dsn = dsn.replace("+psycopg", "")
    if not dsn:
        dsn = "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"

    log.info("Connecting to Postgres: %s", dsn.split("@")[-1])
    pool = await asyncpg.create_pool(dsn, min_size=1, max_size=4)

    # Verify graph exists
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT event_count, edge_count, is_ready FROM ehr.patient_graph_status WHERE patient_id = $1",
            patient_id,
        )
    if row:
        log.info(
            "Graph found: %d events, %d edges, ready=%s",
            row["event_count"], row["edge_count"], row["is_ready"],
        )
    else:
        log.warning("No graph in ehr.patient_graph_status for %s — will fall back to legacy timeline", patient_id)

    # Check Claude availability
    try:
        from server.llm.llm_client import get_anthropic_client, CLAUDE_SYNTHESIS_MODEL
        if get_anthropic_client():
            log.info("Claude available: %s (will use for synthesis)", CLAUDE_SYNTHESIS_MODEL)
        else:
            log.info("Claude not available — synthesis will use GPT")
    except Exception:
        log.info("Claude not available — synthesis will use GPT")

    print()
    print("=" * 72)
    print(f"  EoH DETECTIVE RUN")
    print(f"  Patient:    {patient_id}")
    print(f"  Query:      {query}")
    print(f"  Focus:      {focus}")
    print(f"  Max steps:  {max_steps}")
    print(f"  Valyu:      {use_valyu}")
    print(f"  Dry run:    {dry_run}")
    print("=" * 72)
    print()

    from server.api.rag_stream_detective import eoh_detective_stream_event_generator
    from server.api.stream_config import EOH_STREAM_DEFAULT_SOURCES

    fake_request = _FakeRequest()

    t0 = time.perf_counter()
    collected: Dict[str, Any] = {
        "patient_id": patient_id,
        "query": query,
        "focus": focus,
        "events": [],
        "plan": None,
        "step_reports": [],
        "evidence_maps": [],
        "final_report": None,
        "run_id": None,
        "pdf_path": None,
    }

    event_count = 0
    async for sse_dict in eoh_detective_stream_event_generator(
        request=fake_request,
        q=query,
        timeline_patient_id=patient_id,
        pool=pool,
        focus=focus,
        max_steps=max_steps,
        db_sources=list(EOH_STREAM_DEFAULT_SOURCES),
        limit=10,
        ctx_k=32,
        valyu_k=3,
        with_llm=with_llm,
        llm_mode="chunk",
        use_valyu=use_valyu,
        valyu_mode="search",
        valyu_raw=True,
        valyu_sources=None,
        valyu_boost=1.0,
        research=1,
        enable_gap=1,
    ):
        event_count += 1
        event_type = sse_dict.get("event", "message")
        data_raw = sse_dict.get("data", "{}")
        try:
            data = json.loads(data_raw) if isinstance(data_raw, str) else data_raw
        except json.JSONDecodeError:
            data = data_raw

        _print_sse(event_type, data, verbose=verbose)

        # Collect key events
        if event_type == "detective_plan":
            collected["plan"] = data
        elif event_type == "llm_done":
            collected["step_reports"].append(data)
        elif event_type == "evidence_map":
            collected["evidence_maps"].append(data)
        elif event_type == "detective_report":
            collected["final_report"] = (data.get("report") or data.get("text") or "") if isinstance(data, dict) else data
        elif event_type == "detective_run_saved":
            if isinstance(data, dict):
                collected["run_id"] = data.get("run_id")
                collected["pdf_path"] = data.get("pdf_path")

        if dry_run and event_type == "detective_plan":
            log.info("Dry run — stopping after plan.")
            break

    elapsed = time.perf_counter() - t0
    collected["elapsed_s"] = round(elapsed, 1)
    collected["event_count"] = event_count

    print()
    print("=" * 72)
    print(f"  DONE  ({elapsed:.1f}s, {event_count} SSE events)")
    if collected["run_id"]:
        print(f"  Run ID:   {collected['run_id']}")
    if collected["pdf_path"]:
        print(f"  PDF:      {collected['pdf_path']}")
    print(f"  Steps:    {len(collected['step_reports'])} completed")
    print(f"  Evidence: {len(collected['evidence_maps'])} maps")
    print("=" * 72)

    # Save run log
    if output_dir is None:
        output_dir = str(project_root / "artifacts")
    os.makedirs(output_dir, exist_ok=True)

    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = os.path.join(output_dir, f"eohd_run_{patient_id}_{ts}.json")
    serializable = {k: v for k, v in collected.items()}
    with open(log_path, "w") as f:
        json.dump(serializable, f, indent=2, default=str)
    log.info("Run log saved: %s", log_path)

    await pool.close()
    return collected


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Run EoH Detective stream directly (no web server required)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-p", "--patient-id", required=True, help="Patient ID in Postgres (e.g. NORMAN_ROBERTS)")
    parser.add_argument("-q", "--query", required=True, help="Clinical question")
    parser.add_argument("--focus", default="diagnostic_landscape", help="Investigation focus (default: diagnostic_landscape)")
    parser.add_argument("--max-steps", type=int, default=6, help="Max investigation steps (default: 6)")
    parser.add_argument("--no-llm", action="store_true", help="Disable LLM calls (retrieval only)")
    parser.add_argument("--use-valyu", action="store_true", help="Enable Valyu literature search")
    parser.add_argument("--dry-run", action="store_true", help="Stop after plan generation")
    parser.add_argument("--verbose", "-v", action="store_true", help="Print all SSE events (including noisy ones)")
    parser.add_argument("--output-dir", default=None, help="Directory for run log (default: artifacts/)")
    args = parser.parse_args()

    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")

    asyncio.run(run_detective(
        patient_id=args.patient_id,
        query=args.query,
        focus=args.focus,
        max_steps=args.max_steps,
        with_llm=not args.no_llm,
        use_valyu=args.use_valyu,
        dry_run=args.dry_run,
        verbose=args.verbose,
        output_dir=args.output_dir,
    ))


if __name__ == "__main__":
    main()
