#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://2ndopinionmd.ai}"
EohPath="${EOH_PATH:-/api/rag/ask_stream}"

RA_ID="${RA_ID:-DEMO_RA_001}"
SLE_ID="${SLE_ID:-DEMO_SLE_001}"
PSA_ID="${PSA_ID:-DEMO_PSA_001}"

COMMON_QS=(
  "limit=8"
  "ctx_k=24"
  "sources=mimic4_note,valyu,all_eoh"
  "with_llm=1"
  "use_valyu=1"
  "valyu_k=2"
  "mode=eoh"
)

run_test() {
  local name="$1"; shift
  echo
  echo "========================================"
  echo "TEST: $name"
  echo "========================================"
  echo

  curl -N "${BASE_URL}${EohPath}" \
    --get \
    "$@"
}

# Helper to add common query-string params
qs_common() {
  for kv in "${COMMON_QS[@]}"; do
    printf -- "--data-urlencode\n%s\n" "$kv"
  done
}

###############################################################################
# TYPE A – Short-horizon flare risk, RA timeline
###############################################################################
run_test "TYPE A (Flare Risk, DEMO_RA_001)" \
  --data-urlencode "q=For synthetic RA patient ${RA_ID}, whose CRP and symptoms improved on methotrexate but then had a flare after a 2-week medication gap with rising CRP and ESR around day 165–180, what is their flare risk and EoH baseline trajectory over the next 3 months?" \
  --data-urlencode "patient_id=${RA_ID}" \
  $(qs_common)

###############################################################################
# TYPE B – Flare vs noise, SLE timeline
###############################################################################
run_test "TYPE B (Flare vs Noise, DEMO_SLE_001)" \
  --data-urlencode "q=For lupus patient ${SLE_ID} with a history of high-titer ANA and dsDNA and prior renal flare but now with mild hand pain and fatigue, how should Ethos-of-Health distinguish a true flare from noise based on their recent labs, complements, proteinuria, and symptom pattern?" \
  --data-urlencode "patient_id=${SLE_ID}" \
  $(qs_common)

###############################################################################
# TYPE C – Explainability, UC-style tier jump (uses generic EoH views but still ties to RA timeline)
###############################################################################
run_test "TYPE C (Explain Tier Escalation, DEMO_RA_001 as fixture)" \
  --data-urlencode "q=EoH recently escalated this rheumatoid arthritis patient ${RA_ID} from Tier 2 to Tier 4 after a flare following missed methotrexate doses and rising inflammatory markers. Explain why the system made that change and which underlying signals and decision packets drove the decision." \
  --data-urlencode "patient_id=${RA_ID}" \
  $(qs_common)

###############################################################################
# TYPE D – Plan adjustment over 12 months, ANCA-style but bound to SLE fixture
###############################################################################
run_test "TYPE D (Plan Adjustment, ANCA-style scenario bound to DEMO_SLE_001)" \
  --data-urlencode "q=In a vasculitis-like remission scenario anchored on patient ${SLE_ID}, with prior renal involvement that has now stabilized, how should Ethos-of-Health adjust the maintenance plan and monitoring intensity over the next 12 months to minimize relapse risk?" \
  --data-urlencode "patient_id=${SLE_ID}" \
  $(qs_common)

###############################################################################
# TYPE E – Calibration / over-suppression across high-risk RA patients
###############################################################################
run_test "TYPE E (Calibration / Over-suppression, high-risk RA pool)" \
  --data-urlencode "q=Across high-risk rheumatoid arthritis patients like ${RA_ID} who have had at least one documented flare after missed methotrexate, is the EoH flare detector over-suppressing events? Evaluate calibration, suppression audit, and potential drift across the pool." \
  --data-urlencode "patient_id=${RA_ID}" \
  $(qs_common)

###############################################################################
# Psoriatic arthritis long-horizon planning (D-flavored, DEMO_PSA_001)
###############################################################################
run_test "TYPE D-ish (Psoriatic Arthritis Long-Horizon Plan, DEMO_PSA_001)" \
  --data-urlencode "q=For psoriatic arthritis patient ${PSA_ID} with longstanding plaque psoriasis, HLA-B27 positivity, dactylitis, enthesitis, and good response to adalimumab with normalized CRP, how should Ethos-of-Health structure the next 3–5 years of maintenance therapy, monitoring, and flare prevention?" \
  --data-urlencode "patient_id=${PSA_ID}" \
  $(qs_common)

###############################################################################
# OTHER – Pure guideline methotrexate dosing, but with RA fixture present
###############################################################################
run_test "OTHER (Guideline-only MTX dosing, with DEMO_RA_001 present)" \
  --data-urlencode "q=According to the 2021 ACR guideline, what is the recommended initial methotrexate dosing strategy for rheumatoid arthritis, including starting dose, titration, and route adjustments?" \
  --data-urlencode "patient_id=${RA_ID}" \
  $(qs_common)

###############################################################################
# Valyu-heavy analog – GLP-1 RAs in HFpEF, still carrying a patient_id
###############################################################################
run_test "Valyu-heavy analog (GLP-1 RAs in HFpEF, generic + DEMO_SLE_001 fixture)" \
  --data-urlencode "q=Summarize emerging evidence from 2021–2025 on GLP-1 receptor agonists for heart failure with preserved ejection fraction, focusing on outcomes relevant to long-term care planning and how such findings might influence Ethos-of-Health style recommendations for multimorbid patients." \
  --data-urlencode "patient_id=${SLE_ID}" \
  $(qs_common)

###############################################################################
# MIMIC-heavy analog – ICU patterns, no strong EoH trigger but tests source gating
###############################################################################
run_test "MIMIC-heavy analog (ICU trajectory patterns, generic patient)" \
  --data-urlencode "q=Using ICU discharge and progress note patterns similar to MIMIC-IV, what clinical trajectories tend to precede catastrophic decompensation in severe ulcerative colitis, and how could Ethos-of-Health encode these as high-tier triggers for escalation?" \
  --data-urlencode "patient_id=${RA_ID}" \
  $(qs_common)
