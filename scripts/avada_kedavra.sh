#!/usr/bin/env bash
# Avada Kedavra — Kill all 2OPMD/Uvicorn server processes.
# Named after the Killing Curse in Harry Potter. Use to restart server cleanly.
# Run from 2ndOpinionMD-MVP or repo root.

set -e
pkill -f "run_postgres_app.py" 2>/dev/null || true
pkill -f "uvicorn.*8000" 2>/dev/null || true
echo "Avada Kedavra. Server processes killed (or none were running)."
