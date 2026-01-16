#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
OUT_DIR="${OUT_DIR:-./qa_runs/eoh}"
DATE_TAG="$(date +%Y%m%d-%H%M%S)"

mkdir -p "${OUT_DIR}/${DATE_TAG}"

echo "Running EoH QA harness against ${BASE_URL}"
echo "Output folder: ${OUT_DIR}/${DATE_TAG}"

run_query() {
  local name="$1"
  local patient_id="$2"
  local question="$3"

  local outfile="${OUT_DIR}/${DATE_TAG}/${name}.sse.log"

  echo "=== ${name} ==="
  echo "Q: ${question}"
  echo "Patient: ${patient_id}"
  echo

  curl -N "${BASE_URL}/api/rag/eoh_stream" \
    --get \
    --data-urlencode "q=${question}" \
    --data-urlencode "use_timeline=1" \
    --data-urlencode "timeline_patient_id=${patient_id}" \
    >"${outfile}"

  echo "Saved to ${outfile}"
  echo
}

# 1. Prognostic A-type
run_query "A_prognostic_flare_risk" "DEMO_RA_001" \
  "Over the next 3 months, what is this patient’s flare risk and what drivers are most predictive?"

# 2. Symbolic B-type
run_query "B_symbolic_vs_inflammatory" "DEMO_RA_001" \
  "Given this episode, is this a true inflammatory flare or symbolic/central amplification?"

# 3. Explainability C-type
run_query "C_explain_escalation" "DEMO_RA_001" \
  "Why did EoH escalate flare risk today compared with last week?"

# 4. Plan D-type
run_query "D_plan_adjustment" "DEMO_RA_001" \
  "How should the care plan be adjusted for the next year given the stability band?"

# 5. Meta E-type
run_query "E_meta_QA" "DEMO_RA_001" \
  "How do we QA symbolic detection to ensure we are not overcalling?"

# 6. Guideline-general
run_query "F_guideline_general" "DEMO_RA_001" \
  "How do ACR/EULAR distinguish inflammatory flares from fibromyalgia overlap?"

# 7. Multi-disease (e.g., Crohn’s + RA demo)
run_query "G_multi_disease" "DEMO_CROHNS_RA_001" \
  "For Crohn’s + RA overlap, how should EoH separate independent stack levels?"

# 8. Timeline-heavy
run_query "H_timeline_turning_points" "DEMO_RA_001" \
  "Reviewing the last 6 months, what were the 3 pivotal turning points in disease stability?"

# 9. Valyu-forced (search)
run_query "I_valyu_search" "DEMO_RA_001" \
  "What does recent literature suggest about early predictors of RA flare recurrence?"

# 10. Valyu-forced (answer)
run_query "J_valyu_answer" "DEMO_RA_001" \
  "Summarize major 2020–2025 findings on optimizing MTX withdrawal timing."

echo "EoH QA harness complete."
