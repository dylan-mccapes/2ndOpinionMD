#!/usr/bin/env bash

BASE_URL="https://2ndopinionmd.ai/api/rag/eoh_stream"

run_test() {
  local label=$1
  local q=$2

  echo "========================================"
  echo "TEST: $label"
  echo "========================================"
  echo ""

  curl -N -G "$BASE_URL" \
    --data-urlencode "q=$q" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=answer" \
    --data-urlencode "sources=mimic4_note,valyu,all_eoh" \
    --data-urlencode "limit=8" \
    --data-urlencode "ctx_k=24"

  echo ""
  echo ""
}

###########################################
# TYPE A — Flare risk / baseline / trajectory
###########################################
run_test "TYPE A (Flare Risk)" \
"In a patient with seropositive rheumatoid arthritis whose CRP and symptoms have been fluctuating, what is their flare risk and EoH baseline trajectory over the next 3 months?"

###########################################
# TYPE B — Flare vs noise (symbolic / artefact)
###########################################
run_test "TYPE B (Flare vs Noise)" \
"A lupus patient reports new joint pain after poor sleep. Is this a true flare or symbolic/physiologic noise in EoH terms?"

###########################################
# TYPE C — Explainability / diagnostic landscape
###########################################
run_test "TYPE C (Explainability)" \
"EoH recently escalated this ulcerative colitis patient from Tier 2 to Tier 4. Explain why the system made that change and which underlying signals drove the decision."

###########################################
# TYPE D — Plan adjustment (non-emergency)
###########################################
run_test "TYPE D (Plan Adjustment)" \
"In ANCA vasculitis remission, how should we adjust the maintenance plan and monitoring intensity over the next 12 months to prevent relapse?"

###########################################
# TYPE E — Meta / calibration / system QA
###########################################
run_test "TYPE E (Calibration)" \
"Across high-risk RA patients, is the EoH flare detector over-suppressing events? Evaluate calibration and potential drift."

###########################################
# TYPE OTHER — Pure guideline Q&A
###########################################
run_test "TYPE OTHER (Guideline Only)" \
"According to the 2021 ACR guideline, what is the recommended initial methotrexate dosing strategy for rheumatoid arthritis?"

###########################################
# ANALOG: Valyu-heavy (research-style)
###########################################
run_test "Valyu-heavy analog" \
"Summarize emerging evidence from 2021–2025 on GLP-1 receptor agonists for heart failure with preserved EF, focusing on outcomes relevant to long-term care planning."

###########################################
# ANALOG: MIMIC-heavy (clinical-text-like)
###########################################
run_test "MIMIC-heavy analog" \
"Based on ICU-style clinical documentation patterns (MIMIC-like), how would EoH interpret a pattern of recurrent inflammatory spikes and determine whether they represent a meaningful flare stack?"
