#!/bin/bash
# Generate mock patient timeline PDF for demo graph seeding.
# Uses .StandardVenv (reportlab). Output: data/patient-timelines/mock_timeline_demo.pdf
# Spell: {Creo...en vivo}.StandardVenv.generate_mock_timeline_pdf.cast()

set -e
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$REPO_ROOT"

if [[ -d ".StandardVenv" ]]; then
  source .StandardVenv/bin/activate
  pip install -q reportlab 2>/dev/null || true
else
  echo "Creating .StandardVenv (numpy, librosa, soundfile, torch, reportlab)..."
  python3 -m venv .StandardVenv
  source .StandardVenv/bin/activate
  pip install -q reportlab
fi

exec python server/scripts/generate_mock_timeline_pdf.py
