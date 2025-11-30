#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://2ndopinionmd.ai}"
ENDPOINT="$BASE_URL/api/rag/eoh_stream"

echo "Using endpoint: $ENDPOINT"
echo

run_curl() {
  local label="$1"
  shift
  echo "===== $label ====="
  echo "curl $ENDPOINT ..."
  echo
  curl -N "$ENDPOINT" "$@"
  echo
  echo "============================="
  echo
}

# 1) Question A – RA patient, 4-week flare risk + safety context
run_curl "Q1 (Type A) – RA Zone-5, high Stack Level: flare risk + safety" \
  --get \
  --data-urlencode "q=For this RA patient with recent Zone-5 flares and high Stack Level, what is their flare risk over the next 4 weeks and what safety context should we surface?" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "ctx_k=96" \
  --data-urlencode "limit=10"

# 2) Question B – Real flare vs overshoot vs symbolic flare (with patient_state)
run_curl "Q2 (Type B) – 9/10 pain spike: real vs overshoot vs symbolic" \
  --get \
  --data-urlencode "q=The patient reports a sudden 9 out of 10 pain spike after a medication increase. Is this a real flare, overshoot, or symbolic flare, and how should we classify it?" \
  --data-urlencode 'patient_state={"stack_level":3,"stability_band":"unstable","recent_flare":true}' \
  --data-urlencode "with_llm=1" \
  --data-urlencode "ctx_k=96" \
  --data-urlencode "limit=10"

# 3) Question C – Why Tier-3 escalation last week?
run_curl "Q3 (Type C) – Why Tier-3 escalation last week?" \
  --get \
  --data-urlencode "q=Why did the system escalate this patient to Tier-3 last week, and which signals and suppression events were most responsible for that escalation?" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "ctx_k=96" \
  --data-urlencode "limit=10"

# 4) Question D – Plan adjustment after Zone-5 -> Zone-3 stabilization
run_curl "Q4 (Type D) – Zone-5 to Zone-3: adjust care plan & cadence" \
  --get \
  --data-urlencode "q=Given this patient has stabilized from Zone-5 to Zone-3 over the past month, how should we adjust their care plan intensity and monitoring cadence over the next 8 weeks?" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "ctx_k=96" \
  --data-urlencode "limit=10"

# 5) Question E – Calibration / over-suppression over last 6 months
run_curl "Q5 (Type E) – Model calibration & over-suppression over 6 months" \
  --get \
  --data-urlencode "q=Over the last 6 months, is the flare model still well-calibrated, or are we over-suppressing real flares in this cohort?" \
  --data-urlencode "with_llm=0" \
  --data-urlencode "ctx_k=64" \
  --data-urlencode "limit=8"

echo "All EoH v1 QA calls completed."
