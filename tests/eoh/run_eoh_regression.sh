#!/usr/bin/env bash
set -euo pipefail

# Base URL for your FastAPI app
BASE_URL="${BASE_URL:-http://localhost:8000}"
ENDPOINT="$BASE_URL/api/rag/eoh_stream"

# Common wrapper: one patient per query, full EoH pipeline turned on
run_eoh_query() {
  local label="$1"
  local patient_id="$2"
  local question="$3"

  echo
  echo "================================================================================"
  echo "=== $label (timeline_patient_id=$patient_id) ==================================="
  echo "================================================================================"
  echo "Q: $question"
  echo

  curl -sS -N "$ENDPOINT" \
    --get \
    --data-urlencode "q=$question" \
    --data-urlencode "timeline_patient_id=$patient_id" \
    --data-urlencode "use_timeline=1" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "llm_mode=chunk" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_k=3" \
    --data-urlencode "research=1" \
    --data-urlencode "enable_gap=1" \
    --data-urlencode "limit=10" \
    --data-urlencode "ctx_k=32"
}

###############################################################################
# Q1 – DEMO_RA_001 – Type A (RA flare risk / terrain & trajectory)
###############################################################################
run_eoh_query \
  "Q1_DEMO_RA_001_TypeA_FlareRisk" \
  "DEMO_RA_001" \
  "For this seropositive rheumatoid arthritis patient whose timeline you have as a synthetic Episode of Health, how would Ethos-of-Health classify their current stability band and short-horizon flare risk over the next 3–6 months, and which 2–3 concrete phases of the timeline (flares, lab clusters, or med changes) are most responsible for that trajectory?"

###############################################################################
# Q2 – DEMO_RA_002 – Type B (RA flare vs noise, with case analogs)
#   - research=1 -> MIMIC-IV case analogs should be used
###############################################################################
run_eoh_query \
  "Q2_DEMO_RA_002_TypeB_FlareVsNoise" \
  "DEMO_RA_002" \
  "In this rheumatoid arthritis patient, there is a segment of the timeline where joint pain and fatigue increase but inflammatory markers and function are only modestly changed. Using Ethos-of-Health flare-vs-noise logic, is that episode more likely a true inflammatory flare or fibro/noise/artefact, and why, including how ICU case analogs and suppression modules would inform the decision tag (flare_likely vs noise_likely vs indeterminate)?"

###############################################################################
# Q3 – DEMO_RA_003 – Type D (RA plan adjustment over 12 months)
###############################################################################
run_eoh_query \
  "Q3_DEMO_RA_003_TypeD_RA_PlanAdjustment" \
  "DEMO_RA_003" \
  "For this rheumatoid arthritis patient who has had repeated moderate flares despite methotrexate-based therapy, how would Ethos-of-Health recommend adjusting maintenance therapy intensity and monitoring frequency over the next 12 months to reduce flare risk while avoiding overtreatment, grounded in the visible timeline and guideline evidence?"

###############################################################################
# Q4 – DEMO_SLE_001 – Type A (SLE flare risk & renal trajectory)
###############################################################################
run_eoh_query \
  "Q4_DEMO_SLE_001_TypeA_SLE_FlareRisk" \
  "DEMO_SLE_001" \
  "For this systemic lupus erythematosus patient with a history of lupus nephritis and fluctuating serologies, where does Ethos-of-Health place them in the current stability bands, and what is their near-term flare risk—especially for renal relapse—based on the pattern of events, labs, and treatment changes in the timeline?"

###############################################################################
# Q5 – DEMO_SLE_002 – Type C (Diagnostic landscape: RA-like vs SLE-like vs MCTD-like)
###############################################################################
run_eoh_query \
  "Q5_DEMO_SLE_002_TypeC_DiagnosticLandscape" \
  "DEMO_SLE_002" \
  "For this patient with SLE-like and overlapping autoimmune features, how does Ethos-of-Health's diagnostic landscape weight RA-like, SLE-like, and mixed connective tissue disease–like labels at the current time, and which concrete timeline events or features push those landscape weights in each direction? Please respond as a Type C explainability answer, including a clear diagnostic landscape snapshot."

###############################################################################
# Q6 – DEMO_PSA_001 – Type D (PsA care-plan adjustment)
###############################################################################
run_eoh_query \
  "Q6_DEMO_PSA_001_TypeD_PsA_Plan" \
  "DEMO_PSA_001" \
  "For this psoriatic arthritis patient with both axial and peripheral involvement, how should Ethos-of-Health structure the care plan over the next year—medication intensity, visit cadence, and lab/monitoring bands—to minimize flare risk and structural progression, based on the observed terrain, flares, and response history in the timeline plus guideline and research evidence?"

###############################################################################
# Q7 – DEMO_SJOGREN_001 – Type E (Calibration & suppression for Sjögren)
###############################################################################
run_eoh_query \
  "Q7_DEMO_SJOGREN_001_TypeE_Calibration" \
  "DEMO_SJOGREN_001" \
  "For this Sjögren syndrome patient whose timeline mixes chronic background symptoms (fatigue, dryness) with possible systemic flares, does the Ethos-of-Health calibration and suppression stack (including M48 governance modules) appear appropriately sensitive to true systemic flares versus background noise, or is there evidence of over-suppression or under-detection in this Episode of Health?"

###############################################################################
# Q8 – DEMO_MCTD_001 – Type C/E (Landscape stability and drift in MCTD)
###############################################################################
run_eoh_query \
  "Q8_DEMO_MCTD_001_TypeC_LandscapeDrift" \
  "DEMO_MCTD_001" \
  "For this mixed connective tissue disease patient with overlapping RA-, SLE-, and scleroderma-like features, how does Ethos-of-Health's diagnostic landscape evolve across the visible history, and does the governance layer (M50 together with M48C) suggest that the landscape has remained stable or has drifted toward one dominant phenotype over time?"

###############################################################################
# Q9 – DEMO_VASC_001 – Type B/E (Vasculitis flare vs infection in high-acuity segment)
###############################################################################
run_eoh_query \
  "Q9_DEMO_VASC_001_TypeB_Vasculitis_FlareVsInfection" \
  "DEMO_VASC_001" \
  "In this vasculitis patient who has at least one high-acuity deterioration in the timeline, how does Ethos-of-Health distinguish a true vasculitic flare from infection or hemodynamic noise during that critical segment, and what single TypeB_event_tag (flare_likely, noise_likely, or indeterminate) would the system assign, given the labs, treatments, and any case analogs retrieved?"

###############################################################################
# Q10 – DEMO_FIBRO_001 – OTHER (Guideline-focused chronic pain / fibromyalgia)
#   - Intentionally NOT an EoH flare/plan question: pure guideline / research.
###############################################################################
run_eoh_query \
  "Q10_DEMO_FIBRO_001_OTHER_GuidelineChronicPain" \
  "DEMO_FIBRO_001" \
  "For this patient whose dominant problem is chronic widespread pain consistent with fibromyalgia, based on the guideline and research evidence you retrieve here, what non-pharmacologic strategies and behavioral interventions (exercise, sleep, CBT-style approaches, pacing) are recommended for long-term management? Focus on guideline-backed themes; you do not need to apply Ethos-of-Health flare or tiering concepts."