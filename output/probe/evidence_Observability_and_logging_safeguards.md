# Evidence for Observability and logging safeguards

- `fmp/logging/__init__.py:0-5` → # Logging modules
- `run_eoh_v5_2_probe.sh:0-5` → #!/bin/bash
# Run 10 probes for EoH v5.2 mechanical constraints

python3 ai_code_pipelines/run_probe.py \
  --query "Strengthen EoH v5.2 by introducing explicit mechanical constraints, deterministic r
- `run_probe_api_docs.sh:0-5` → #!/bin/bash
# Run probe to comprehensively document RAG stream endpoints and briefly document rest of API
# For design lead context

cd "$(dirname "$0")"

python3 run_probe.py \
  --query "Document th
- `fmp/logging/run_log.py:0-5` → from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now_iso(
- `fmp/__init__.py:0-5` → # FullMetalPacket triage and invariant system
- `show_artifacts.sh:0-5` → #!/bin/bash
# show_artifacts.sh - Display all artifacts from an ai_probe/ai_coder run
# Usage: ./show_artifacts.sh [suffix]
# Example: ./show_artifacts.sh timeline_provenance_v1

set -e

SUFFIX="${1:-
- `run_triage_to_debug.sh:0-5` → #!/bin/bash
# Complete workflow: Triage -> DEBUG_LOOP for dogfooding
# This script runs triage and automatically executes DEBUG_LOOP if recommended

cd "$(dirname "$0")"

OUTPUT_DIR="ai_coder_output/t
- `fmp/utils/__init__.py:0-5` → # Utility modules
- `fmp/agents/__init__.py:0-5` → # Agent modules
- `run_fmp_file_resolution_probe.sh:0-5` → #!/bin/bash
# Probe to investigate file resolution and repo_vision issues in FullMetalPacket

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  --query "Investi
- `run_fmp_dogfood_probe.sh:0-5` → #!/bin/bash
# Run probe on FullMetalPacket (dogfood) to populate repo_vision and fix file resolution issues

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  -
- `fmp_cli.py:0-5` → #!/usr/bin/env python3
"""
FullMetalPacket CLI (UX Scaffold)
---------------------------------
Retro, text-based interface for intent capture only.

No actions are executed yet; this is purely UX scaf
- `fmp/utils/context_detection.py:0-5` → #!/usr/bin/env python3
"""
context_detection.py
--------------------
Auto-detection utilities for embedding context selection.

Detects when to use fmp_dogfood context based on failure signals.
"""

i
- `invariants/invariant_loader.py:0-5` → from __future__ import annotations

import threading
from pathlib import Path
from typing import Iterable, List, Tuple

import yaml

from fmp.config.software_invariants import SoftwareInvariant

_INVA
- `fmp/config/__init__.py:0-5` → # Configuration modules
- `full_metal_packet.py:0-5` → #!/usr/bin/env python3
"""
full_metal_packet.py
--------------------
FullMetalPacket - Full autonomous engineering cycle orchestrator.

Orchestrates:
1. coder_goal_agent - Decompose user query into go
- `fmp/config/software_invariants.py:0-5` → from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

AppliesTo = Literal["all", "goal", "triage", "debug", "coder", "probe", "ga
- `run_debug_from_triage.py:0-5` → #!/usr/bin/env python3
"""
run_debug_from_triage.py
-------------------------
Simple integration point: Execute DEBUG_LOOP when triage recommends it.

This script:
1. Loads triage decision
2. Verifies
- `RUN_TRIAGE_DEBUG.sh:0-5` → #!/bin/bash
# Complete workflow: Triage -> DEBUG_LOOP for citation_agent.py error

cd "$(dirname "$0")"

OUTPUT_DIR="ai_coder_output/test_citation"
RUN_LOG="output/runs/test_citation/events.jsonl"

# 
- `utils.py:0-5` → #!/usr/bin/env python3
"""
Global (repo-root) utilities shared by the runner scripts.

Important:
- This file lives at the repo root (next to run_probe.py / run_coder.py).
- It is intentionally separa
- `run_diagnose_file_resolution.sh:0-5` → #!/bin/bash
# Diagnostic probe to investigate why run_probe.py file resolution fails in coder_code_agent

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  --qu
- `run_mke_landing_page.sh:0-5` → #!/bin/bash
# Command to build the 2ndOpinionMD Medical Knowledge Engine landing page
# This creates a production-grade interface that streams the engine's thinking in real-time

cd "$(dirname "$0")"

- `run_probe.py:0-5` → #!/usr/bin/env python3
"""
ai_probe/run_probe.py
---------------------
End-to-end execution for the AI Probe pipeline.

Stages:
  1. Ensure virtual environment + dependencies
  2. Incremental embeddin
- `run_coder.py:0-5` → #!/usr/bin/env python3
"""
run_coder.py
------------
Orchestrator for the ai_coder pipeline:
  ticket → probe → gap → code → review → report

Optional debug loop:
  --debug-loop: Enable autopatch cycl
- `fmp/agents/triage_agent.py:0-5` → from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from fmp.agents.issue imp
- `run_triage.py:0-5` → #!/usr/bin/env python3
"""
run_triage.py
-------------
CLI entrypoint for the triage agent.

Usage (traditional flags):
    python3 run_triage.py \
        --config ai_coder/coder_config.yaml \
      
- `fmp/agents/global_triage_agent.py:0-5` → #!/usr/bin/env python3
"""
global_triage_agent.py
----------------------
Deterministic, keyword-based global triage (stub).

Inputs:
    user_request: free-text string

Outputs:
    {
      "recommend
- `fmp/agents/issue.py:0-5` → #!/usr/bin/env python3
"""
fmp/agents/issue.py
------------------
Structured issue representation for triage agent.

Supports integration with external systems (Crashlytics, etc.) that provide
structu
- `test_path_resolution.py:0-5` → #!/usr/bin/env python3
"""
Test script for path resolution.
Run: python3 test_path_resolution.py
"""
import sys
import os

# Add ai_code_pipelines to path
sys.path.insert(0, os.path.dirname(os.path.ab
- `./run_probe.py:0-5` → "phase_log": [],
- `./run_diagnose_file_resolution.sh:0-5` → '{"topic":"Trace the file resolution path for run_probe.py in coder_code_agent.py: how does resolve_canonical_file_path get called, what paths does it check (repo_vision, embeddings, git ls-files), an
- `./run_triage.py:0-5` → "run_log": "output/runs/test/events.jsonl",
- `./run_triage.py:0-5` → from fmp.logging.run_log import RunLogger
- `./run_triage.py:0-5` → if "run_log" in query_data:
- `./run_triage.py:0-5` → args.run_log = query_data["run_log"]
- `./run_triage.py:0-5` → # 🩹 TRIAGE STARTUP LOGGING
- `./run_triage.py:0-5` → if not args.run_log:
- `./run_triage.py:0-5` → run_log_path = args.run_log
- `./run_triage.py:0-5` → def emit(self, event, payload):
- `./run_triage.py:0-5` → print(f"[LOG] {event}: {json.dumps(payload)}", file=sys.stderr)
- `./run_triage.py:0-5` → # Extract file paths early for logging (before expensive operations)
- `./run_triage.py:0-5` → # 🩹 COMPREHENSIVE PRE-TRIAGE LOGGING (before expensive operations)
- `./run_triage.py:0-5` → # If logging fails, at least write to stderr
- `./run_probe_api_docs.sh:0-5` → '{"topic": "Document the Frontend Contract Summary for all RAG stream endpoints: shared SSE contract (text/event-stream transport), event.type semantic meaning, event.data JSON structure, and how a si
- `./run_probe_api_docs.sh:0-5` → '{"topic": "Document Event Schema Stability requirements: how SSE event payloads are semi-structured and may evolve, frontend client requirements (tolerate unknown event types, tolerate additional fie
- `./run_probe_api_docs.sh:0-5` → "EventSourceResponse" "SSE" "streaming" "text/event-stream" \
- `./run_probe_api_docs.sh:0-5` → "event.type" "event.data" "EventSource" "sse_starlette" \
- `./run_probe_api_docs.sh:0-5` → "event" "schema" "payload" "optional" "fields" "versioning" \
- `./run_triage_to_debug.sh:0-5` → RUN_LOG="output/runs/test_citation/events.jsonl"
- `./run_triage_to_debug.sh:0-5` → mkdir -p "$(dirname "$RUN_LOG")"
- `./run_triage_to_debug.sh:0-5` → --run-log "$RUN_LOG" \
- `./fmp/agents/triage_agent.py:0-5` → from fmp.logging.run_log import RunLogger, to_jsonable
- `./fmp/agents/triage_agent.py:0-5` → - error output or stack trace excerpts
- `./fmp/agents/triage_agent.py:0-5` → 3. Trace-derived hooks (if available)
- `./fmp/agents/triage_agent.py:0-5` → - trace-linked file/function hints
- `./fmp/agents/triage_agent.py:0-5` → - Stack trace or error points clearly to a small fix
- `./fmp/agents/triage_agent.py:0-5` → - repo_vision + trace hooks provide sufficient context
- `./fmp/agents/triage_agent.py:0-5` → parts.append("FILE SNIPPETS (from error trace)")
- `./fmp/agents/triage_agent.py:0-5` → # Files from error trace also get high importance if they're crash-related
- `./fmp/agents/triage_agent.py:0-5` → summary=f"File referenced in error trace",
- `./fmp/logging/run_log.py:0-5` → def emit(self, event: str, payload: Dict[str, Any]) -> None:
- `./fmp/logging/run_log.py:0-5` → "event": event,
