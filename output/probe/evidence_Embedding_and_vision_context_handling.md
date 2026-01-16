# Evidence for Embedding and vision context handling

- `fmp/utils/context_detection.py:0-5` → #!/usr/bin/env python3
"""
context_detection.py
--------------------
Auto-detection utilities for embedding context selection.

Detects when to use fmp_dogfood context based on failure signals.
"""

i
- `run_fmp_dogfood_probe.sh:0-5` → #!/bin/bash
# Run probe on FullMetalPacket (dogfood) to populate repo_vision and fix file resolution issues

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  -
- `fmp/agents/__init__.py:0-5` → # Agent modules
- `run_eoh_v5_2_probe.sh:0-5` → #!/bin/bash
# Run 10 probes for EoH v5.2 mechanical constraints

python3 ai_code_pipelines/run_probe.py \
  --query "Strengthen EoH v5.2 by introducing explicit mechanical constraints, deterministic r
- `show_artifacts.sh:0-5` → #!/bin/bash
# show_artifacts.sh - Display all artifacts from an ai_probe/ai_coder run
# Usage: ./show_artifacts.sh [suffix]
# Example: ./show_artifacts.sh timeline_provenance_v1

set -e

SUFFIX="${1:-
- `run_fmp_file_resolution_probe.sh:0-5` → #!/bin/bash
# Probe to investigate file resolution and repo_vision issues in FullMetalPacket

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  --query "Investi
- `run_probe.py:0-5` → #!/usr/bin/env python3
"""
ai_probe/run_probe.py
---------------------
End-to-end execution for the AI Probe pipeline.

Stages:
  1. Ensure virtual environment + dependencies
  2. Incremental embeddin
- `fmp/utils/__init__.py:0-5` → # Utility modules
- `run_coder.py:0-5` → #!/usr/bin/env python3
"""
run_coder.py
------------
Orchestrator for the ai_coder pipeline:
  ticket → probe → gap → code → review → report

Optional debug loop:
  --debug-loop: Enable autopatch cycl
- `fmp/config/__init__.py:0-5` → # Configuration modules
- `run_mke_landing_page.sh:0-5` → #!/bin/bash
# Command to build the 2ndOpinionMD Medical Knowledge Engine landing page
# This creates a production-grade interface that streams the engine's thinking in real-time

cd "$(dirname "$0")"

- `run_probe_api_docs.sh:0-5` → #!/bin/bash
# Run probe to comprehensively document RAG stream endpoints and briefly document rest of API
# For design lead context

cd "$(dirname "$0")"

python3 run_probe.py \
  --query "Document th
- `run_diagnose_file_resolution.sh:0-5` → #!/bin/bash
# Diagnostic probe to investigate why run_probe.py file resolution fails in coder_code_agent

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  --qu
- `fmp/__init__.py:0-5` → # FullMetalPacket triage and invariant system
- `fmp/agents/issue.py:0-5` → #!/usr/bin/env python3
"""
fmp/agents/issue.py
------------------
Structured issue representation for triage agent.

Supports integration with external systems (Crashlytics, etc.) that provide
structu
- `fmp/agents/triage_agent.py:0-5` → from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from fmp.agents.issue imp
- `run_triage_to_debug.sh:0-5` → #!/bin/bash
# Complete workflow: Triage -> DEBUG_LOOP for dogfooding
# This script runs triage and automatically executes DEBUG_LOOP if recommended

cd "$(dirname "$0")"

OUTPUT_DIR="ai_coder_output/t
- `utils.py:0-5` → #!/usr/bin/env python3
"""
Global (repo-root) utilities shared by the runner scripts.

Important:
- This file lives at the repo root (next to run_probe.py / run_coder.py).
- It is intentionally separa
- `fmp/logging/__init__.py:0-5` → # Logging modules
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
- `run_triage.py:0-5` → #!/usr/bin/env python3
"""
run_triage.py
-------------
CLI entrypoint for the triage agent.

Usage (traditional flags):
    python3 run_triage.py \
        --config ai_coder/coder_config.yaml \
      
- `run_debug_from_triage.py:0-5` → #!/usr/bin/env python3
"""
run_debug_from_triage.py
-------------------------
Simple integration point: Execute DEBUG_LOOP when triage recommends it.

This script:
1. Loads triage decision
2. Verifies
- `fmp/config/software_invariants.py:0-5` → from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

AppliesTo = Literal["all", "goal", "triage", "debug", "coder", "probe", "ga
- `invariants/invariant_loader.py:0-5` → from __future__ import annotations

import threading
from pathlib import Path
from typing import Iterable, List, Tuple

import yaml

from fmp.config.software_invariants import SoftwareInvariant

_INVA
- `test_path_resolution.py:0-5` → #!/usr/bin/env python3
"""
Test script for path resolution.
Run: python3 test_path_resolution.py
"""
import sys
import os

# Add ai_code_pipelines to path
sys.path.insert(0, os.path.dirname(os.path.ab
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
- `fmp_cli.py:0-5` → #!/usr/bin/env python3
"""
FullMetalPacket CLI (UX Scaffold)
---------------------------------
Retro, text-based interface for intent capture only.

No actions are executed yet; this is purely UX scaf
- `fmp/logging/run_log.py:0-5` → from __future__ import annotations

import json
import os
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional


def utc_now_iso(
- `./show_artifacts.sh:0-5` → if [ -f "$PROBE_DIR/vision_context.json" ]; then
- `./show_artifacts.sh:0-5` → file_header "$PROBE_DIR/vision_context.json"
- `./show_artifacts.sh:0-5` → head -n 100 "$PROBE_DIR/vision_context.json"
- `./show_artifacts.sh:0-5` → if [ -f "$dir/ts_hits.json" ]; then
- `./show_artifacts.sh:0-5` → file_header "$dir/ts_hits.json"
- `./show_artifacts.sh:0-5` → echo "Lines: $(wc -l < "$dir/ts_hits.json")"
- `./show_artifacts.sh:0-5` → echo "Size: $(du -h "$dir/ts_hits.json" | cut -f1)"
- `./show_artifacts.sh:0-5` → head -n 20 "$dir/ts_hits.json"
- `./run_probe.py:0-5` → help="Use fmp_dogfood embedding context (for FullMetalPacket self-analysis)",
- `./run_probe.py:0-5` → help="Explicit embedding context name (overrides --dogfood)",
- `./run_probe.py:0-5` → # Resolve embedding context up-front so we know where the index should land
- `./run_probe.py:0-5` → print(f"⚠️ Could not resolve embedding context: {e}")
- `./run_probe.py:0-5` → # Create temp filtered index file for embed_incremental.py
- `./run_probe.py:0-5` → print(f"🟡 Filtered index: {after}/{before} files retained (ai_probe_index/embeddings_diff.json)")
- `./run_probe.py:0-5` → os.environ["AI_PROBE_INDEX_PATH"] = os.path.join(PROBE_DIR_STR, "ai_probe_index", "embeddings_diff.json")
- `./run_probe.py:0-5` → repo_structure_path = os.path.join(run_output_dir_str, f"repo_structure{suffix_tag}.json")
- `./run_probe.py:0-5` → # If the index was previously pruned/small, embed_incremental will auto-rebuild.
- `./run_probe.py:0-5` → if "AI_PROBE_INDEX_PATH" in os.environ:
- `./run_probe.py:0-5` → index_path = os.environ["AI_PROBE_INDEX_PATH"]
- `./run_probe.py:0-5` → print(f"📦 Resolved index via embedding context: {index_path}")
- `./run_probe.py:0-5` → print(f"📦 Resolved index via resolver: {index_path}")
- `./run_probe.py:0-5` → print(f"📦 Resolved index via default path: {index_path}")
- `./run_probe.py:0-5` → raise SystemExit("❌ Index not found after embedding. Provide --index or ensure ai_probe_index/embeddings.json exists.")
- `./run_probe.py:0-5` → os.environ["AI_PROBE_INDEX_PATH"] = index_path
- `./run_probe.py:0-5` → run_vision_query(args.query, index_path=index_path, out_path=os.path.join(run_output_dir_str, "vision_context.json"))
- `./run_fmp_dogfood_probe.sh:0-5` → --query "FullMetalPacket triage and coder pipeline: analyze file resolution, repo_vision population, embedding context handling, and ensure all entry-point scripts (run_probe.py, run_triage.py, run_co
- `./run_fmp_dogfood_probe.sh:0-5` → echo "   - ai_probe_index/fmp_dogfood/embeddings.json (should have all files)"
- `./run_triage.py:0-5` → effective_msg = "✅ fmp_dogfood" if dogfood_final else "❌ default"
- `./run_triage.py:0-5` → # Include embedding context if dogfood detected/flagged
- `./run_triage.py:0-5` → result["embedding_context"] = "fmp_dogfood"
- `./run_triage.py:0-5` → # Include embedding context in result if detected
- `./run_triage.py:0-5` → print(f"   📦 Embedding context: {result['embedding_context']}")
- `./run_coder.py:0-5` → print(f"⏭️  Skipping embedding - index was updated {age_minutes:.1f} minutes ago (recent run_probe?)")
- `./run_coder.py:0-5` → ts_hits_path = os.path.join(base_dir, "ts_hits.json")
- `./run_coder.py:0-5` → print("❌ Phase-gating invariant failed: probe_hits.json or ts_hits.json required but missing")
- `./invariants/invariant_loader.py:0-5` → raise RuntimeError(f"❌ Invalid invariant at index {i}: missing keys {sorted(missing)}")
- `./fmp/agents/triage_agent.py:0-5` → - repo_vision (semantic index of files, entities, responsibilities)
- `./fmp/utils/context_detection.py:0-5` → Auto-detection utilities for embedding context selection.
- `./fmp/utils/context_detection.py:0-5` → Detects when to use fmp_dogfood context based on failure signals.
- `./fmp/utils/context_detection.py:0-5` → Auto-detect which embedding context to use based on failure signals.
- `./fmp/utils/context_detection.py:0-5` → "fmp_dogfood" if failure originates in ai_code_pipelines
- `./fmp/utils/context_detection.py:0-5` → return "fmp_dogfood"
- `./fmp/utils/context_detection.py:0-5` → Determine if fmp_dogfood context should be used based on peek signals.
- `./fmp/utils/context_detection.py:0-5` → return detected == "fmp_dogfood"
