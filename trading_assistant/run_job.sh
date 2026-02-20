#!/bin/bash
# Trading Assistant — Cron job wrapper
# Run from PortalVision root. Uses .BeatingHeart venv.
set -e
cd "$(dirname "$0")/../.."
ROOT=$(pwd)
source "$ROOT/2ndOpinionMD-MVP/.BeatingHeart/bin/activate" 2>/dev/null || true
python "$ROOT/2ndOpinionMD-MVP/trading_assistant/run.py"
