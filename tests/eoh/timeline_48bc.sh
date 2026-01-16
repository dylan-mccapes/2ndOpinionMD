#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://2ndopinionmd.ai}"

run() {
  local label="$1"
  local q="$2"

  echo
  echo "============================================================"
  echo "== $label"
  echo "============================================================"
  curl -N "$BASE_URL/api/rag/eoh_stream" \
    --get \
    --data-urlencode "q=$q" \
    --data-urlencode "patient_id=DEMO_RA_001" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "debug=1"
    # NOTICE: no &sources=... on purpose
}

run "RA flare vs noise" \
  "In a 32-year-old woman with seropositive RA and RA-ILD on methotrexate and TNFi, how should we interpret a 2–3 week increase in fatigue and arthralgia without clear CRP/ESR rise? Focus on flare vs noise, when to escalate DMARDs, and when to watch and wait."

run "RA pregnancy planning" \
  "How should we plan pregnancy timing and DMARD adjustments for a woman with seropositive RA and mild RA-ILD who wants to conceive in the next 1–2 years? Focus on preconception disease control, medication changes, and ILD-specific safety issues."

run "HF / GLP-1 vs SGLT2" \
  "In an adult with HFrEF, obesity, and type 2 diabetes, how should we prioritize GLP-1 receptor agonists vs SGLT2 inhibitors for long-term cardiometabolic risk and heart failure outcomes?"
