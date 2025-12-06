#!/usr/bin/env bash
set -euo pipefail

# Change if you want to hit localhost instead
BASE_URL="${BASE_URL:-https://2ndopinionmd.ai}"
EOH_PATH="${EOH_PATH:-/api/rag/eoh_stream}"

# Common query params (router decides what to do with use_valyu=1)
COMMON_PARAMS=(
  --data-urlencode "use_valyu=1"
  --data-urlencode "with_llm=1"
)

run_case() {
  local id="$1"
  local label="$2"
  local question="$3"

  echo "================================================================================"
  echo "[$id] $label"
  echo "--------------------------------------------------------------------------------"
  echo "GET ${BASE_URL}${EOH_PATH}"
  echo "q: $question"
  echo "--------------------------------------------------------------------------------"

  # Raw SSE stream – no client parsing, just let curl print everything.
  curl -N \
    --silent \
    --show-error \
    --get "${BASE_URL}${EOH_PATH}" \
    --data-urlencode "q=${question}" \
    "${COMMON_PARAMS[@]}"

  echo
  echo "--------------------------------------------------------------------------------"
  echo "[END $id]"
  echo
}

# ------------------------------------------------------------------------------
# Test cases – exercise as much of the EoH pipeline as possible
# ------------------------------------------------------------------------------

run_case \
  "eoh_sle_pregnancy_flare" \
  "SLE – flare risk & management in pregnancy" \
  "In a woman with systemic lupus erythematosus who is planning pregnancy within the next 6–12 months and has a history of lupus nephritis but is currently in low disease activity on hydroxychloroquine and azathioprine, how should we: (1) counsel her on flare risk during pregnancy and in the 3-month postpartum period, (2) optimize medications before conception, and (3) monitor her for preeclampsia versus lupus nephritis flares according to current ACR/EULAR pregnancy guidance and recent literature?"

run_case \
  "eoh_ra_treat_to_target_multi_morbidity" \
  "RA – treat-to-target with multimorbidity" \
  "In a 55-year-old woman with seropositive rheumatoid arthritis, class II heart failure with reduced ejection fraction, type 2 diabetes, and obesity who has moderate disease activity on methotrexate and leflunomide, how should we implement a treat-to-target strategy (remission or low disease activity) while balancing heart failure, infection risk, and metabolic comorbidities? Compare TNF inhibitors versus non-TNF biologics versus JAK inhibitors based on current ACR and EULAR RA guidelines and key outcome trials."

run_case \
  "eoh_ra_ild_pregnancy" \
  "RA-ILD – pregnancy planning & DMARD strategy" \
  "In a 32-year-old woman with seropositive rheumatoid arthritis and mild RA-associated interstitial lung disease who wishes to conceive in the next 1–2 years, what is the optimal csDMARD and biologic strategy before conception, during pregnancy, and postpartum? Which agents should be avoided (for example mycophenolate, leflunomide, JAK inhibitors) and which can be continued (for example hydroxychloroquine, azathioprine, certain TNF inhibitors) according to ACR/EULAR RA and ILD guidance and recent cohort data?"

run_case \
  "eoh_sle_aps_thrombosis" \
  "SLE + APS – thrombosis & pregnancy risk management" \
  "In a 28-year-old woman with systemic lupus erythematosus, triple-positive antiphospholipid antibodies (lupus anticoagulant, anticardiolipin, anti-β2-glycoprotein I), prior deep vein thrombosis, and one first-trimester miscarriage, how should we manage anticoagulation and pregnancy planning? Outline preconception counseling, anticoagulant regimen during pregnancy and postpartum, and monitoring for thrombosis and preeclampsia based on current EULAR and ACR APS and SLE pregnancy guidelines."

run_case \
  "eoh_ckd_bp_glp1_sglt2" \
  "CKD + diabetes + GLP-1/SGLT2 – long-term EoH care" \
  "In a 60-year-old man with type 2 diabetes, chronic kidney disease stage 3b (eGFR 35), albuminuria, and heart failure with preserved ejection fraction who is already on an ACE inhibitor and an SGLT2 inhibitor, what is the Ethos-of-Health long-term plan for kidney and cardiovascular risk reduction? Compare the roles of GLP-1 receptor agonists versus further RAAS blockade versus non-steroidal mineralocorticoid receptor antagonists such as finerenone according to KDIGO, ADA, and major outcome trials."

run_case \
  "eoh_ibd_biologic_strategy" \
  "IBD – biologic sequencing & flare prevention" \
  "In a 30-year-old woman with extensive ulcerative colitis who has had an inadequate response to optimized anti-TNF therapy and is considering switching to vedolizumab versus ustekinumab versus upadacitinib, how should we choose and plan her long-term Ethos-of-Health strategy to minimize flares, hospitalizations, and colorectal cancer risk? Summarize evidence from major trials and ECCO and ACG guidelines."

run_case \
  "eoh_vasculitis_flare_prediction" \
  "ANCA-vasculitis – remission maintenance & flare prediction" \
  "In a 65-year-old man with MPO-ANCA–associated vasculitis in remission after rituximab induction, what is the recommended strategy for remission maintenance and flare prediction over the next 5 years? Compare fixed-interval rituximab versus relapse-driven dosing versus azathioprine or methotrexate, and discuss biomarker-guided monitoring (ANCA titers, B-cell repopulation) based on current EULAR vasculitis guidance and key randomized trials."

run_case \
  "eoh_longitudinal_multimorbidity" \
  "Multimorbidity – holistic Ethos-of-Health longitudinal plan" \
  "Design a 12-month Ethos-of-Health longitudinal care plan for a 50-year-old woman with systemic lupus erythematosus, rheumatoid arthritis, hypertension, obesity, and generalized anxiety disorder. She has low-to-moderate inflammatory disease activity, is on hydroxychloroquine and low-dose methotrexate, and works full-time. Integrate guideline-based targets for SLE and RA disease activity, blood pressure, weight, and mental health; include flare prevention, vaccination, pregnancy counseling, and lifestyle interventions, with milestones at 3, 6, 9, and 12 months."
