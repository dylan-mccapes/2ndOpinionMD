# Evidence for Provenance graph and artifact lineage

- `show_artifacts.sh:0-5` → #!/bin/bash
# show_artifacts.sh - Display all artifacts from an ai_probe/ai_coder run
# Usage: ./show_artifacts.sh [suffix]
# Example: ./show_artifacts.sh timeline_provenance_v1

set -e

SUFFIX="${1:-
- `run_eoh_v5_2_probe.sh:0-5` → #!/bin/bash
# Run 10 probes for EoH v5.2 mechanical constraints

python3 ai_code_pipelines/run_probe.py \
  --query "Strengthen EoH v5.2 by introducing explicit mechanical constraints, deterministic r
- `run_fmp_file_resolution_probe.sh:0-5` → #!/bin/bash
# Probe to investigate file resolution and repo_vision issues in FullMetalPacket

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  --query "Investi
- `run_probe_api_docs.sh:0-5` → #!/bin/bash
# Run probe to comprehensively document RAG stream endpoints and briefly document rest of API
# For design lead context

cd "$(dirname "$0")"

python3 run_probe.py \
  --query "Document th
- `fmp_cli.py:0-5` → #!/usr/bin/env python3
"""
FullMetalPacket CLI (UX Scaffold)
---------------------------------
Retro, text-based interface for intent capture only.

No actions are executed yet; this is purely UX scaf
- `run_fmp_dogfood_probe.sh:0-5` → #!/bin/bash
# Run probe on FullMetalPacket (dogfood) to populate repo_vision and fix file resolution issues

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  -
- `run_diagnose_file_resolution.sh:0-5` → #!/bin/bash
# Diagnostic probe to investigate why run_probe.py file resolution fails in coder_code_agent

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  --qu
- `fmp/agents/triage_agent.py:0-5` → from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from fmp.agents.issue imp
- `run_probe.py:0-5` → #!/usr/bin/env python3
"""
ai_probe/run_probe.py
---------------------
End-to-end execution for the AI Probe pipeline.

Stages:
  1. Ensure virtual environment + dependencies
  2. Incremental embeddin
- `full_metal_packet.py:0-5` → #!/usr/bin/env python3
"""
full_metal_packet.py
--------------------
FullMetalPacket - Full autonomous engineering cycle orchestrator.

Orchestrates:
1. coder_goal_agent - Decompose user query into go
- `run_triage_to_debug.sh:0-5` → #!/bin/bash
# Complete workflow: Triage -> DEBUG_LOOP for dogfooding
# This script runs triage and automatically executes DEBUG_LOOP if recommended

cd "$(dirname "$0")"

OUTPUT_DIR="ai_coder_output/t
- `RUN_TRIAGE_DEBUG.sh:0-5` → #!/bin/bash
# Complete workflow: Triage -> DEBUG_LOOP for citation_agent.py error

cd "$(dirname "$0")"

OUTPUT_DIR="ai_coder_output/test_citation"
RUN_LOG="output/runs/test_citation/events.jsonl"

# 
- `run_coder.py:0-5` → #!/usr/bin/env python3
"""
run_coder.py
------------
Orchestrator for the ai_coder pipeline:
  ticket → probe → gap → code → review → report

Optional debug loop:
  --debug-loop: Enable autopatch cycl
- `fmp/agents/__init__.py:0-5` → # Agent modules
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
- `run_triage.py:0-5` → #!/usr/bin/env python3
"""
run_triage.py
-------------
CLI entrypoint for the triage agent.

Usage (traditional flags):
    python3 run_triage.py \
        --config ai_coder/coder_config.yaml \
      
- `fmp/__init__.py:0-5` → # FullMetalPacket triage and invariant system
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
- `fmp/utils/context_detection.py:0-5` → #!/usr/bin/env python3
"""
context_detection.py
--------------------
Auto-detection utilities for embedding context selection.

Detects when to use fmp_dogfood context based on failure signals.
"""

i
- `utils.py:0-5` → #!/usr/bin/env python3
"""
Global (repo-root) utilities shared by the runner scripts.

Important:
- This file lives at the repo root (next to run_probe.py / run_coder.py).
- It is intentionally separa
- `fmp/logging/run_log.py:0-5` → from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now_iso(
- `fmp/logging/__init__.py:0-5` → # Logging modules
- `test_path_resolution.py:0-5` → #!/usr/bin/env python3
"""
Test script for path resolution.
Run: python3 test_path_resolution.py
"""
import sys
import os

# Add ai_code_pipelines to path
sys.path.insert(0, os.path.dirname(os.path.ab
- `invariants/invariant_loader.py:0-5` → from __future__ import annotations

import threading
from pathlib import Path
from typing import Iterable, List, Tuple

import yaml

from fmp.config.software_invariants import SoftwareInvariant

_INVA
- `fmp/config/software_invariants.py:0-5` → from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

AppliesTo = Literal["all", "goal", "triage", "debug", "coder", "probe", "ga
- `run_mke_landing_page.sh:0-5` → #!/bin/bash
# Command to build the 2ndOpinionMD Medical Knowledge Engine landing page
# This creates a production-grade interface that streams the engine's thinking in real-time

cd "$(dirname "$0")"

- `fmp/utils/__init__.py:0-5` → # Utility modules
- `fmp/config/__init__.py:0-5` → # Configuration modules
- `./run_fmp_file_resolution_probe.sh:0-5` → # Probe to investigate file resolution and repo_vision issues in FullMetalPacket
- `./run_fmp_file_resolution_probe.sh:0-5` → --query "Investigate FullMetalPacket triage and coder pipeline file resolution failures: why run_probe.py cannot be found despite being in issue JSON file_errors, and why repo_vision loads as empty de
- `./run_fmp_file_resolution_probe.sh:0-5` → '{"topic":"Analyze how file paths like run_probe.py are resolved from bare filenames to canonical repo-relative paths. Investigate resolve_canonical_file_path function, how it searches repo_vision, em
- `./run_fmp_file_resolution_probe.sh:0-5` → '{"topic":"Investigate repo_vision loading and saving: why repo_vision saves with files but loads as empty. Analyze GLOBAL_REPO_VISION_PATH vs PROBE_REPO_VISION_PATH usage, when repo_vision is saved v
- `./show_artifacts.sh:0-5` → if [ -f "$dir/repo_vision.json" ]; then
- `./show_artifacts.sh:0-5` → file_header "$dir/repo_vision.json"
- `./show_artifacts.sh:0-5` → head -n 100 "$dir/repo_vision.json"
- `./run_eoh_v5_2_probe.sh:0-5` → '{"topic":"Define the canonical Diagnostic Landscape data model with required fields and update rules, including temporal span, confidence vector, provenance references, suppression status, and explic
- `./run_eoh_v5_2_probe.sh:0-5` → '{"topic":"Specify provenance and audit invariants for EoH reasoning, including mandatory linkage between inferred states, source artifacts, timestamps, confidence vectors, and governance decisions su
- `./run_probe.py:0-5` → # 0b. Initialize repo_vision artifact (will be updated by agents)
- `./run_probe.py:0-5` → repo_vision_path = os.path.join(run_output_dir_str, f"repo_vision{suffix_tag}.json")
- `./run_probe.py:0-5` → repo_vision = {
- `./run_probe.py:0-5` → json.dump(repo_vision, f, indent=2)
- `./run_probe.py:0-5` → # Create run ledger for traceability
- `./run_probe.py:0-5` → ledger = {
- `./run_diagnose_file_resolution.sh:0-5` → '{"topic":"Trace the file resolution path for run_probe.py in coder_code_agent.py: how does resolve_canonical_file_path get called, what paths does it check (repo_vision, embeddings, git ls-files), an
- `./run_fmp_dogfood_probe.sh:0-5` → # Run probe on FullMetalPacket (dogfood) to populate repo_vision and fix file resolution issues
- `./run_fmp_dogfood_probe.sh:0-5` → --query "FullMetalPacket triage and coder pipeline: analyze file resolution, repo_vision population, embedding context handling, and ensure all entry-point scripts (run_probe.py, run_triage.py, run_co
- `./run_fmp_dogfood_probe.sh:0-5` → echo "   - ai_coder_output/repo_vision.json (should be populated)"
- `./run_triage.py:0-5` → help="Path to repo_vision.json file (optional, will try to find if not provided)",
- `./run_triage.py:0-5` → # Find GLOBAL repo_vision path (single source of truth in ai_code_pipelines/)
- `./run_triage.py:0-5` → canonical_repo_vision = os.path.join(BASE_DIR, "repo_vision.json")
- `./run_triage.py:0-5` → elif os.path.exists(os.path.join(BASE_DIR, "ai_coder_output", "repo_vision.json")):
- `./run_triage.py:0-5` → repo_vision_path_to_use = os.path.join(BASE_DIR, "ai_coder_output", "repo_vision.json")
- `./run_triage.py:0-5` → print(f"   Has repo_vision flag: {'✅' if peek.get('has_repo_vision', False) else '❌'}")
- `./run_coder.py:0-5` → If non-canonical paths are found, resolve them using repo_vision/git/fs and overwrite the file.
- `./run_coder.py:0-5` → repo_vision = load_repo_vision()
- `./run_coder.py:0-5` → repo_vision = None
- `./run_coder.py:0-5` → repo_vision=repo_vision,
- `./full_metal_packet.py:0-5` → --user-query "make timeline provenance first-class" \
- `./full_metal_packet.py:0-5` → help="High-level user request (e.g., 'make timeline provenance first-class')"
- `./fmp/agents/triage_agent.py:0-5` → - repo_vision (semantic index of files, entities, responsibilities)
- `./fmp/agents/triage_agent.py:0-5` → - repo_vision summaries
- `./fmp/agents/triage_agent.py:0-5` → - broader repo_vision context
- `./fmp/agents/triage_agent.py:0-5` → - repo_vision + trace hooks provide sufficient context
- `./fmp/agents/triage_agent.py:0-5` → repo_vision: Optional[Dict[str, Any]] = None,
- `./fmp/agents/triage_agent.py:0-5` → Uses repo_vision to resolve filenames to full paths when available.
- `./fmp/agents/triage_agent.py:0-5` → found_filenames = set()  # Track bare filenames for repo_vision lookup
- `./fmp/agents/triage_agent.py:0-5` → # Might be just a filename - try to resolve via repo_vision
- `./fmp/agents/triage_agent.py:0-5` → # Use repo_vision to resolve bare filenames
- `./fmp/agents/triage_agent.py:0-5` → if repo_vision and found_filenames:
- `./fmp/agents/triage_agent.py:0-5` → from ai_coder.repo_vision import RepoVision
- `./fmp/agents/triage_agent.py:0-5` → if isinstance(repo_vision, dict):
- `./fmp/agents/triage_agent.py:0-5` → vision = RepoVision.from_dict(repo_vision)
- `./fmp/agents/triage_agent.py:0-5` → vision = repo_vision
- `./fmp/agents/triage_agent.py:0-5` → Build user prompt with peek, repo_vision, and file snippets.
- `./fmp/agents/triage_agent.py:0-5` → parts.append("REPO_VISION CONTEXT")
- `./fmp/agents/triage_agent.py:0-5` → repo_vision_path: Path to repo_vision.json file (optional, will try to find if not provided)
- `./fmp/agents/triage_agent.py:0-5` → # Load or create repo_vision context
- `./fmp/agents/triage_agent.py:0-5` → # Import from ai_coder.utils and ai_coder.repo_vision
- `./fmp/agents/triage_agent.py:0-5` → # Try to load GLOBAL repo_vision (single source of truth at ai_code_pipelines/repo_vision.json)
- `./fmp/agents/triage_agent.py:0-5` → canonical_repo_vision = os.path.join(base_dir, "repo_vision.json")
- `./fmp/agents/triage_agent.py:0-5` → elif os.path.exists(os.path.join(base_dir, "ai_coder_output", "repo_vision.json")):
- `./fmp/agents/triage_agent.py:0-5` → repo_vision_path = os.path.join(base_dir, "ai_coder_output", "repo_vision.json")
- `./fmp/agents/triage_agent.py:0-5` → # Create new repo_vision if it doesn't exist
- `./fmp/agents/triage_agent.py:0-5` → # CRITICAL: Seed repo_vision with files from issue if available
- `./fmp/agents/triage_agent.py:0-5` → # Extract file paths early to seed repo_vision
- `./fmp/agents/global_triage_agent.py:0-5` → - PROBE: keywords {"probe", "report", "repo vision", "repo_vision", "repo report"}
- `./fmp/agents/global_triage_agent.py:0-5` → probe_keys = {"probe", "report", "repo vision", "repo_vision", "repo report", "vision"}
