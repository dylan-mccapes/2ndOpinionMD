#!/bin/bash
# TM+WMM: run Wave Modulation Machine from repo root.
# Uses .StandardVenv; runs without demucs if demucs not installed (--no-demucs implied when demucs missing).
# Usage: ./run_tm_wmm_analysis.sh [audio_file] [--verbose] [--save-json] ...
# Default audio: dylans_artifacts/audio/BETTERTHANPERFECT.m4a

set -e
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

AUDIO_DEFAULT="dylans_artifacts/audio/BETTERTHANPERFECT.m4a"

# If first arg is not a flag, treat as audio file; else use default
if [[ -n "$1" && "$1" != --* ]]; then
  AUDIO_FILE="$1"
  shift
else
  AUDIO_FILE="$AUDIO_DEFAULT"
fi

if [[ ! -f "$AUDIO_FILE" ]]; then
  echo "Error: Audio file not found: $AUDIO_FILE"
  exit 1
fi

# Activate venv; create and install minimal deps if missing
if [[ -d ".StandardVenv" ]]; then
  source .StandardVenv/bin/activate
else
  echo "Creating .StandardVenv (minimal: numpy, librosa, soundfile, torch)..."
  python3 -m venv .StandardVenv
  source .StandardVenv/bin/activate
  pip install --quiet --upgrade pip
  pip install --quiet numpy librosa soundfile torch
  echo "(.StandardVenv ready; demucs not installed — WMM will use full mix)"
fi

# Run WMM (script auto-uses --no-demucs when demucs not installed)
exec python3 wave_modulation_machine.py "$AUDIO_FILE" "$@"
