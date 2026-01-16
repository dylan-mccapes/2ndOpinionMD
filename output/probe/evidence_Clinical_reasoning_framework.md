# Evidence for Clinical reasoning framework

- `run_eoh_v5_2_probe.sh:0-5` → #!/bin/bash
# Run 10 probes for EoH v5.2 mechanical constraints

python3 ai_code_pipelines/run_probe.py \
  --query "Strengthen EoH v5.2 by introducing explicit mechanical constraints, deterministic r
- `fmp_cli.py:0-5` → #!/usr/bin/env python3
"""
FullMetalPacket CLI (UX Scaffold)
---------------------------------
Retro, text-based interface for intent capture only.

No actions are executed yet; this is purely UX scaf
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
- `run_triage.py:0-5` → #!/usr/bin/env python3
"""
run_triage.py
-------------
CLI entrypoint for the triage agent.

Usage (traditional flags):
    python3 run_triage.py \
        --config ai_coder/coder_config.yaml \
      
- `fmp/utils/context_detection.py:0-5` → #!/usr/bin/env python3
"""
context_detection.py
--------------------
Auto-detection utilities for embedding context selection.

Detects when to use fmp_dogfood context based on failure signals.
"""

i
- `fmp/agents/issue.py:0-5` → #!/usr/bin/env python3
"""
fmp/agents/issue.py
------------------
Structured issue representation for triage agent.

Supports integration with external systems (Crashlytics, etc.) that provide
structu
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
- `run_triage_to_debug.sh:0-5` → #!/bin/bash
# Complete workflow: Triage -> DEBUG_LOOP for dogfooding
# This script runs triage and automatically executes DEBUG_LOOP if recommended

cd "$(dirname "$0")"

OUTPUT_DIR="ai_coder_output/t
- `run_diagnose_file_resolution.sh:0-5` → #!/bin/bash
# Diagnostic probe to investigate why run_probe.py file resolution fails in coder_code_agent

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  --qu
- `RUN_TRIAGE_DEBUG.sh:0-5` → #!/bin/bash
# Complete workflow: Triage -> DEBUG_LOOP for citation_agent.py error

cd "$(dirname "$0")"

OUTPUT_DIR="ai_coder_output/test_citation"
RUN_LOG="output/runs/test_citation/events.jsonl"

# 
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
- `fmp/config/software_invariants.py:0-5` → from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

AppliesTo = Literal["all", "goal", "triage", "debug", "coder", "probe", "ga
- `run_coder.py:0-5` → #!/usr/bin/env python3
"""
run_coder.py
------------
Orchestrator for the ai_coder pipeline:
  ticket → probe → gap → code → review → report

Optional debug loop:
  --debug-loop: Enable autopatch cycl
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
- `run_fmp_dogfood_probe.sh:0-5` → #!/bin/bash
# Run probe on FullMetalPacket (dogfood) to populate repo_vision and fix file resolution issues

cd /Users/2ndopinionmd/Sites/2ndOpinionMD-MVP/ai_code_pipelines

python3 run_probe.py \
  -
- `fmp/agents/__init__.py:0-5` → # Agent modules
- `fmp/__init__.py:0-5` → # FullMetalPacket triage and invariant system
- `full_metal_packet.py:0-5` → #!/usr/bin/env python3
"""
full_metal_packet.py
--------------------
FullMetalPacket - Full autonomous engineering cycle orchestrator.

Orchestrates:
1. coder_goal_agent - Decompose user query into go
- `fmp/config/__init__.py:0-5` → # Configuration modules
- `fmp/agents/triage_agent.py:0-5` → from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional

from fmp.agents.issue imp
- `fmp/utils/__init__.py:0-5` → # Utility modules
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
- `fmp/logging/__init__.py:0-5` → # Logging modules
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
- `./show_artifacts.sh:0-5` → echo -e "\n${GREEN}=== REVIEWED (HIGH/MEDIUM confidence) ===${NC}\n"
- `./show_artifacts.sh:0-5` → echo -e "\n${YELLOW}=== SUPPRESSED (LOW confidence) ===${NC}\n"
- `./run_debug_from_triage.py:0-5` → print(f"   Confidence: {triage_decision.get('confidence', 0.0):.2f}")
- `./run_eoh_v5_2_probe.sh:0-5` → '{"topic":"Define the canonical Diagnostic Landscape data model with required fields and update rules, including temporal span, confidence vector, provenance references, suppression status, and explic
- `./run_eoh_v5_2_probe.sh:0-5` → '{"topic":"Constrain drift detection by defining at least one canonical operational embodiment, including drift magnitude, direction, persistence, and a minimum actionable rule based on confidence thr
- `./run_eoh_v5_2_probe.sh:0-5` → '{"topic":"Document governance decision ordering within EoH, including mandatory sequencing of abstention checks, suppression evaluation, state update comparison, and confidence mediation prior to any
- `./run_eoh_v5_2_probe.sh:0-5` → '{"topic":"Constrain concurrent inferred state handling by specifying rules for non-exclusive state coexistence, conflict tolerance, confidence weighting across states, and prohibition of forced colla
- `./run_eoh_v5_2_probe.sh:0-5` → '{"topic":"Define explicit authority boundaries between the Medical Knowledge Engine (MKE) and EoH, including rules that retrieved knowledge artifacts are non-authoritative until elevated by EoH throu
- `./run_eoh_v5_2_probe.sh:0-5` → '{"topic":"Specify provenance and audit invariants for EoH reasoning, including mandatory linkage between inferred states, source artifacts, timestamps, confidence vectors, and governance decisions su
- `./run_probe.py:0-5` → 5. Gap analysis (uncertainty pass)
- `./run_probe.py:0-5` → default="Investigate this codebase’s modular architecture, identifying coupling and connascence quantitatively and qualitatively.",
- `./run_probe.py:0-5` → # 4. Gap analysis
- `./run_probe.py:0-5` → run(f"{py} -u {os.path.join(PROBE_DIR_STR, 'gap_agent.py')} 2>&1 | tee {os.path.join(run_output_dir_str, f'gap_log{suffix_tag}.txt')}", "Running gap analysis")
- `./run_probe.py:0-5` → # Try to attach a summary of connascence signals if probe output exists
- `./run_triage.py:0-5` → description="Triage agent: decide next action based on failure signals"
- `./run_triage.py:0-5` → "confidence": "📊",
- `./fmp_cli.py:0-5` → "confidence": 0.51,
- `./fmp_cli.py:0-5` → print(f"  Confidence : {decision['confidence']:.2f}")
- `./run_coder.py:0-5` → run(f"{py} {os.path.join(BASE_DIR,'ai_coder','coder_gap_agent.py')}", "Running coder gap analysis")
- `./run_coder.py:0-5` → notes="Gap intentionally skipped; no gap analysis performed.",
- `./run_coder.py:0-5` → # Review agent: filters/tiers patches, adds metadata headers, clusters by hypothesis
- `./run_coder.py:0-5` → print(f"   🎯 Top hypothesis: {review.get('top_hypothesis')}")
- `./full_metal_packet.py:0-5` → "--human-confidence",
- `./full_metal_packet.py:0-5` → help="Human input confidence weighting (0.0-1.0, default: 0.5)"
- `./full_metal_packet.py:0-5` → print(f"❌ --human-confidence must be between 0.0 and 1.0 (got {args.human_confidence})")
- `./fmp/config/software_invariants.py:0-5` → - Failure to localize ≠ failure to reason; downgrade confidence, do not abort.
- `./fmp/config/software_invariants.py:0-5` → "user_preference_variant_path": "User selection always overrides internal confidence heuristics; confidence informs recommendation, never permission.",
- `./fmp/config/software_invariants.py:0-5` → "never_give_up": "Zero confidence still triggers a 4.1 debug attempt; confidence is a signal, not a kill switch.",
- `./fmp/agents/triage_agent.py:0-5` → "confidence": 0.0,
- `./fmp/agents/triage_agent.py:0-5` → 1. Failure signals
- `./fmp/agents/triage_agent.py:0-5` → - model override signals
- `./fmp/agents/triage_agent.py:0-5` → - Escalate ONLY if confidence is low or signals conflict.
- `./fmp/agents/triage_agent.py:0-5` → - Probe + vision + gap analysis is justified
- `./fmp/agents/triage_agent.py:0-5` → parts.append("TRIAGE_PEEK (FAILURE SIGNALS)")
- `./fmp/agents/triage_agent.py:0-5` → If it fails, treat as low-confidence and escalate or fail fast.
- `./fmp/agents/triage_agent.py:0-5` → confidence = 0.95  # Very high confidence since it's from structured error
- `./fmp/agents/triage_agent.py:0-5` → repo_vision_obj.update_file_importance(file_path, importance, confidence, "triage_agent")
- `./fmp/agents/triage_agent.py:0-5` → "confidence": confidence,
- `./fmp/agents/triage_agent.py:0-5` → confidence = 0.85
- `./fmp/agents/global_triage_agent.py:0-5` → "confidence": float,
- `./fmp/agents/global_triage_agent.py:0-5` → "confidence": 0.1,
- `./fmp/agents/global_triage_agent.py:0-5` → confidence = min(0.9, 0.4 + 0.1 * best_score)
- `./fmp/utils/context_detection.py:0-5` → Detects when to use fmp_dogfood context based on failure signals.
- `./fmp/utils/context_detection.py:0-5` → Auto-detect which embedding context to use based on failure signals.
- `./fmp/utils/context_detection.py:0-5` → Determine if fmp_dogfood context should be used based on peek signals.
