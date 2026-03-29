#!/usr/bin/env python3
"""
Quick-iteration test harness for the timeline PDF pipeline.

Uses the 1-page mock_timeline_demo.pdf (11 events, ~1 batch) so you get
a full extraction → connascence → summary cycle in under 30 seconds
instead of waiting 4+ minutes on the 4223-page Norman Roberts record.

Usage (from 2ndOpinionMD-MVP/server, .BeatingHeart active):

    # Ollama (free)
    python3 -u scripts/test_timeline_pdf_quick.py --llm-backend ollama-full

    # OpenAI
    python3 -u scripts/test_timeline_pdf_quick.py

Reads the same CLI flags as run_eohd_timeline_pdf.py.  Defaults to the
mock PDF and patient_id "demo_patient".
"""

from __future__ import annotations

import sys
from pathlib import Path

script_dir = Path(__file__).resolve().parent
server_dir = script_dir.parent
repo_root = server_dir.parent

MOCK_PDF = repo_root / "data" / "patient-timelines" / "mock_timeline_demo.pdf"

if not MOCK_PDF.exists():
    print(f"Mock PDF not found at {MOCK_PDF}", file=sys.stderr)
    print("Generate it:  python3 server/scripts/generate_mock_timeline_pdf.py", file=sys.stderr)
    sys.exit(1)

# Inject defaults into sys.argv before the real script runs.
# Any explicit args the user passes will override these via argparse.
defaults_injected = False
if len(sys.argv) == 1 or not any(a for a in sys.argv[1:] if not a.startswith("-")):
    sys.argv.insert(1, str(MOCK_PDF))
    defaults_injected = True

# Default to demo_patient unless user specified --patient-id.
if "--patient-id" not in sys.argv:
    sys.argv.extend(["--patient-id", "demo_patient"])

# Default artifact dir.
if "--artifact-dir" not in sys.argv:
    ad = repo_root / "artifacts" / "test_quick"
    ad.mkdir(parents=True, exist_ok=True)
    sys.argv.extend(["--artifact-dir", str(ad)])

# Import and hand off to the real entry point.
# This avoids duplicating any CLI logic.
import importlib.util
spec = importlib.util.spec_from_file_location(
    "run_eohd_timeline_pdf", script_dir / "run_eohd_timeline_pdf.py"
)
mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
spec.loader.exec_module(mod)  # type: ignore[union-attr]
