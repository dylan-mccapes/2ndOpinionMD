# Evidence for Agentic workflow orchestration

- `fmp/agents/__init__.py:0-5` → # Agent modules
- `full_metal_packet.py:0-5` → #!/usr/bin/env python3
"""
full_metal_packet.py
--------------------
FullMetalPacket - Full autonomous engineering cycle orchestrator.

Orchestrates:
1. coder_goal_agent - Decompose user query into go
- `RUN_TRIAGE_DEBUG.sh:0-5` → #!/bin/bash
# Complete workflow: Triage -> DEBUG_LOOP for citation_agent.py error

cd "$(dirname "$0")"

OUTPUT_DIR="ai_coder_output/test_citation"
RUN_LOG="output/runs/test_citation/events.jsonl"

# 
- `fmp_cli.py:0-5` → #!/usr/bin/env python3
"""
FullMetalPacket CLI (UX Scaffold)
---------------------------------
Retro, text-based interface for intent capture only.

No actions are executed yet; this is purely UX scaf
- `run_triage_to_debug.sh:0-5` → #!/bin/bash
# Complete workflow: Triage -> DEBUG_LOOP for dogfooding
# This script runs triage and automatically executes DEBUG_LOOP if recommended

cd "$(dirname "$0")"

OUTPUT_DIR="ai_coder_output/t
- `run_eoh_v5_2_probe.sh:0-5` → #!/bin/bash
# Run 10 probes for EoH v5.2 mechanical constraints

python3 ai_code_pipelines/run_probe.py \
  --query "Strengthen EoH v5.2 by introducing explicit mechanical constraints, deterministic r
- `run_coder.py:0-5` → #!/usr/bin/env python3
"""
run_coder.py
------------
Orchestrator for the ai_coder pipeline:
  ticket → probe → gap → code → review → report

Optional debug loop:
  --debug-loop: Enable autopatch cycl
- `run_probe_api_docs.sh:0-5` → #!/bin/bash
# Run probe to comprehensively document RAG stream endpoints and briefly document rest of API
# For design lead context

cd "$(dirname "$0")"

python3 run_probe.py \
  --query "Document th
- `show_artifacts.sh:0-5` → #!/bin/bash
# show_artifacts.sh - Display all artifacts from an ai_probe/ai_coder run
# Usage: ./show_artifacts.sh [suffix]
# Example: ./show_artifacts.sh timeline_provenance_v1

set -e

SUFFIX="${1:-
- `run_mke_landing_page.sh:0-5` → #!/bin/bash
# Command to build the 2ndOpinionMD Medical Knowledge Engine landing page
# This creates a production-grade interface that streams the engine's thinking in real-time

cd "$(dirname "$0")"

- `run_debug_from_triage.py:0-5` → #!/usr/bin/env python3
"""
run_debug_from_triage.py
-------------------------
Simple integration point: Execute DEBUG_LOOP when triage recommends it.

This script:
1. Loads triage decision
2. Verifies
- `fmp/agents/issue.py:0-5` → #!/usr/bin/env python3
"""
fmp/agents/issue.py
------------------
Structured issue representation for triage agent.

Supports integration with external systems (Crashlytics, etc.) that provide
structu
- `run_probe.py:0-5` → #!/usr/bin/env python3
"""
ai_probe/run_probe.py
---------------------
End-to-end execution for the AI Probe pipeline.

Stages:
  1. Ensure virtual environment + dependencies
  2. Incremental embeddin
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
- `run_diagnose_file_resolution.sh:0-5` → #!/bin/bash
# Diagnostic probe to investigate why run_probe.py file resolution fails in coder_code_agent

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  --qu
- `run_fmp_dogfood_probe.sh:0-5` → #!/bin/bash
# Run probe on FullMetalPacket (dogfood) to populate repo_vision and fix file resolution issues

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  -
- `run_fmp_file_resolution_probe.sh:0-5` → #!/bin/bash
# Probe to investigate file resolution and repo_vision issues in FullMetalPacket

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  --query "Investi
- `fmp/utils/__init__.py:0-5` → # Utility modules
- `invariants/invariant_loader.py:0-5` → from __future__ import annotations

import threading
from pathlib import Path
from typing import Iterable, List, Tuple

import yaml

from fmp.config.software_invariants import SoftwareInvariant

_INVA
- `fmp/utils/context_detection.py:0-5` → #!/usr/bin/env python3
"""
context_detection.py
--------------------
Auto-detection utilities for embedding context selection.

Detects when to use fmp_dogfood context based on failure signals.
"""

i
- `fmp/__init__.py:0-5` → # FullMetalPacket triage and invariant system
- `fmp/config/__init__.py:0-5` → # Configuration modules
- `fmp/config/software_invariants.py:0-5` → from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

AppliesTo = Literal["all", "goal", "triage", "debug", "coder", "probe", "ga
- `fmp/logging/run_log.py:0-5` → from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now_iso(
- `fmp/agents/triage_agent.py:0-5` → from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from fmp.agents.issue imp
- `utils.py:0-5` → #!/usr/bin/env python3
"""
Global (repo-root) utilities shared by the runner scripts.

Important:
- This file lives at the repo root (next to run_probe.py / run_coder.py).
- It is intentionally separa
- `test_path_resolution.py:0-5` → #!/usr/bin/env python3
"""
Test script for path resolution.
Run: python3 test_path_resolution.py
"""
import sys
import os

# Add ai_code_pipelines to path
sys.path.insert(0, os.path.dirname(os.path.ab
- `fmp/logging/__init__.py:0-5` → # Logging modules
- `./run_probe.py:0-5` → stage2 = query_agent_result.get("stage2", {})
- `./run_probe.py:0-5` → chosen_path = stage2.get("chosen_path", "FULL_PROBE")
- `./run_probe.py:0-5` → print(f"✅ Query agent decision: {chosen_path}")
- `./run_probe.py:0-5` → if chosen_path == "UPDATE_ONLY":
- `./run_probe.py:0-5` → elif chosen_path == "PARTIAL_EXPANSION":
- `./run_probe.py:0-5` → elif chosen_path == "TARGETED_PROBE":
- `./run_probe.py:0-5` → topics = stage2.get("topics", [])
- `./run_probe.py:0-5` → elif chosen_path == "FULL_PROBE":
- `./run_probe.py:0-5` → print(f"⚠️ Unknown path '{chosen_path}', falling back to default probe")
- `./run_probe.py:0-5` → chosen_path = None
- `./run_probe.py:0-5` → chosen_path = query_agent_result.get("stage2", {}).get("chosen_path", "")
- `./run_probe.py:0-5` → if chosen_path in ["UPDATE_ONLY", "PARTIAL_EXPANSION"]:
- `./run_probe.py:0-5` → print(f"⏭️  Skipping probe/gap phases (path: {chosen_path})")
- `./run_probe.py:0-5` → run(f"{py} -u {os.path.join(PROBE_DIR_STR, 'probe_agent.py')} 2>&1 | tee {os.path.join(run_output_dir_str, f'probe_log{suffix_tag}.txt')}", "Running probe phase")
- `./run_probe.py:0-5` → run(f"{py} -u {os.path.join(PROBE_DIR_STR, 'gap_agent.py')} 2>&1 | tee {os.path.join(run_output_dir_str, f'gap_log{suffix_tag}.txt')}", "Running gap analysis")
- `./run_probe.py:0-5` → # For UPDATE_ONLY/PARTIAL_EXPANSION, report_agent will handle the update
- `./run_probe.py:0-5` → report_cmd = f"{py} -u {os.path.join(PROBE_DIR_STR, 'report_agent.py')} --suffix {suffix_arg or 'default'}"
- `./run_probe.py:0-5` → if query_agent_result and skip_probe_gap and chosen_path:
- `./run_probe.py:0-5` → # Pass query agent decision to report_agent via environment variable
- `./run_probe.py:0-5` → os.environ["QUERY_AGENT_DECISION"] = json.dumps(query_agent_result.get("stage2", {}))
- `./run_probe.py:0-5` → os.environ["QUERY_AGENT_PATH"] = chosen_path
- `./run_triage.py:0-5` → from fmp.agents.triage_agent import TriageConfig, run_triage_agent
- `./run_triage.py:0-5` → peek["file_paths"] = file_paths  # Add to peek for triage_agent
- `./run_triage.py:0-5` → # Will be created/updated by triage_agent if files are seeded
- `./run_probe_api_docs.sh:0-5` → '{"topic": "Comprehensively document /rag/eoh_detective_stream endpoint: request/response format, multi-step investigation workflow, orchestration pattern, internal delegation to eoh_stream, step-by-s
- `./run_triage_to_debug.sh:0-5` → # Complete workflow: Triage -> DEBUG_LOOP for dogfooding
- `./run_triage_to_debug.sh:0-5` → echo "✅ Triage -> Debug workflow complete"
- `./RUN_TRIAGE_DEBUG.sh:0-5` → # Complete workflow: Triage -> DEBUG_LOOP for citation_agent.py error
- `./fmp/config/software_invariants.py:0-5` → "escalation_requires_explanation": "Any change in model tier or workflow path must be justified and present alternatives.",
- `./fmp/agents/triage_agent.py:0-5` → return f"""You are triage_agent for FullMetalPacket.
- `./fmp/agents/triage_agent.py:0-5` → discovered_by="triage_agent",
- `./fmp/agents/triage_agent.py:0-5` → repo_vision_obj.update_file_importance(file_path, importance, confidence, "triage_agent")
- `./fmp/agents/issue.py:0-5` → Convert to peek dict format expected by triage_agent.
