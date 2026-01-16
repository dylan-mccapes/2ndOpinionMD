#!/usr/bin/env bash
set -euo pipefail

# Full-stack smoke: 5 guideline Q&A, 5 coding, 10 EoH (full pipeline)
# Requires:
#   - BASE_URL (optional; defaults to https://2ndopinionmd.ai)
#   - Synthetic timelines seeded (e.g. DEMO_RA_001, DEMO_SLE_001)
#
# Usage:
#   chmod +x full_stack_pipeline.sh
#   ./full_stack_pipeline.sh

BASE_URL="${BASE_URL:-https://2ndopinionmd.ai}"

COMMON_FLAGS=(
  --get
  -N
  -H "Accept: text/event-stream"
)

banner() {
  echo
  echo "===================================================================="
  echo "$1"
  echo "===================================================================="
  echo
}

# ---------------------------------------------------------------------
# 1) GUIDELINE Q&A: /ask_stream (5 tests)
# ---------------------------------------------------------------------

run_guideline_tests() {
  banner "GUIDELINE Q&A TEST 1 – RA csDMARD escalation (ACR/EULAR, NICE, etc.)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/ask_stream" \
    --data-urlencode "q=In a 38-year-old woman with seropositive rheumatoid arthritis and high disease activity despite 6 months of methotrexate at 25 mg weekly, what do recent ACR and EULAR RA guidelines recommend for csDMARD escalation and first-line biologic choices, including when to consider TNF inhibitors versus non-TNF biologics?" \
    --data-urlencode "limit=10" \
    --data-urlencode "ctx_k=32" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=search" \
    --data-urlencode "valyu_raw=1"

  banner "GUIDELINE Q&A TEST 2 – SLE renal flare management"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/ask_stream" \
    --data-urlencode "q=For a patient with class III–IV lupus nephritis in partial remission who develops a mild rise in proteinuria and anti-dsDNA with stable creatinine, how do KDIGO and EULAR/ERA-EDTA lupus nephritis guidelines distinguish a true flare requiring treatment escalation from noise, and what monitoring strategy is recommended?" \
    --data-urlencode "limit=10" \
    --data-urlencode "ctx_k=32" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=search" \
    --data-urlencode "valyu_raw=1"

  banner "GUIDELINE Q&A TEST 3 – HF + CKD (SGLT2i, ARNI, MRA)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/ask_stream" \
    --data-urlencode "q=In a 70-year-old man with HFrEF (LVEF 30 percent), type 2 diabetes, and eGFR 35 mL/min, what do contemporary ACC/AHA/HFSA heart failure and KDIGO CKD guidelines say about the use of SGLT2 inhibitors, ARNI, and MRAs, including dose adjustments and safety monitoring?" \
    --data-urlencode "limit=10" \
    --data-urlencode "ctx_k=32" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=search" \
    --data-urlencode "valyu_raw=1"

  banner "GUIDELINE Q&A TEST 4 – UC biologic sequencing"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/ask_stream" \
    --data-urlencode "q=For a 29-year-old with moderate-to-severe ulcerative colitis who has lost response to an anti-TNF, how do recent AGA and ECCO guidelines frame sequencing options such as vedolizumab, ustekinumab, and JAK inhibitors, including safety considerations in a patient who wishes to conceive in the next 1–2 years?" \
    --data-urlencode "limit=10" \
    --data-urlencode "ctx_k=32" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=search" \
    --data-urlencode "valyu_raw=1"

  banner "GUIDELINE Q&A TEST 5 – Infective endocarditis prophylaxis"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/ask_stream" \
    --data-urlencode "q=According to recent AHA/ACC and ESC infective endocarditis guidelines, which adult patients still warrant antibiotic prophylaxis before dental procedures, and how should regimens be adapted in a patient with a prosthetic valve and penicillin allergy?" \
    --data-urlencode "limit=10" \
    --data-urlencode "ctx_k=32" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=0"
}

# ---------------------------------------------------------------------
# 2) CODING / ABSTRACTION: /coding_stream (5 tests)
# ---------------------------------------------------------------------

run_coding_tests() {
  # NOTE: Use broad coding vocabularies; router will still gate internally.
  CODING_SOURCES="icd10cm,icd11,snomed,rxnorm,loinc,hpo,orphanet"

  banner "CODING TEST 1 – RA visit (problem list codes)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/coding_stream" \
    --data-urlencode "q=Follow-up rheumatology visit for seropositive rheumatoid arthritis with moderate disease activity, symmetric small-joint synovitis of hands and feet, morning stiffness 90 minutes, on methotrexate and folic acid, no extra-articular organ involvement today." \
    --data-urlencode "sources=$CODING_SOURCES" \
    --data-urlencode "limit=15" \
    --data-urlencode "ctx_k=32" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=0"

  banner "CODING TEST 2 – SLE nephritis admission"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/coding_stream" \
    --data-urlencode "q=Hospital admission for systemic lupus erythematosus with active proliferative lupus nephritis, nephrotic-range proteinuria, hypertension, and anemia of chronic disease. Pulse steroids and mycophenolate started." \
    --data-urlencode "sources=$CODING_SOURCES" \
    --data-urlencode "limit=15" \
    --data-urlencode "ctx_k=32" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=0"

  banner "CODING TEST 3 – UC flare vs infection (ED visit)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/coding_stream" \
    --data-urlencode "q=ED visit for a patient with known ulcerative colitis presenting with bloody diarrhea, abdominal cramping, and low-grade fever. Stool studies pending to rule out C. difficile. Mild dehydration, IV fluids given." \
    --data-urlencode "sources=$CODING_SOURCES" \
    --data-urlencode "limit=15" \
    --data-urlencode "ctx_k=32" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=0"

  banner "CODING TEST 4 – Psoriatic arthritis outpatient note"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/coding_stream" \
    --data-urlencode "q=40-year-old with psoriatic arthritis and nail pitting, enthesitis at Achilles insertion, and plaque psoriasis on elbows and knees, maintained on TNF inhibitor with good control. Screening for latent TB and hepatitis negative." \
    --data-urlencode "sources=$CODING_SOURCES" \
    --data-urlencode "limit=15" \
    --data-urlencode "ctx_k=32" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=0"

  banner "CODING TEST 5 – ANCA vasculitis with pulmonary-renal syndrome"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/coding_stream" \
    --data-urlencode "q=ICU admission for ANCA-associated vasculitis with pulmonary-renal syndrome: diffuse alveolar hemorrhage, rapidly progressive glomerulonephritis, hemoptysis, hypoxic respiratory failure, and rising creatinine requiring hemodialysis. High-dose steroids and rituximab initiated." \
    --data-urlencode "sources=$CODING_SOURCES" \
    --data-urlencode "limit=15" \
    --data-urlencode "ctx_k=32" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=0"
}

# ---------------------------------------------------------------------
# 3) EoH: /eoh_stream (10 tests, full pipeline)
#   - Mix of question types (A–E / OTHER)
#   - Most use Valyu + research
#   - Many use patient timelines (DEMO_RA_001, DEMO_SLE_001)
#   - Some hit case analogs (B/C -> mimic4_note via router)
# ---------------------------------------------------------------------

run_eoh_tests() {
  # TYPE A: Flare risk / baseline trajectory – RA
  banner "EOH TEST A1 – RA flare risk & baseline trajectory (DEMO_RA_001)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/eoh_stream" \
    --data-urlencode "q=For synthetic RA patient DEMO_RA_001, whose CRP and symptoms improved on methotrexate but then had a flare after a 2-week medication gap with rising CRP and ESR around day 165–180, what is their Ethos-of-Health flare risk and baseline trajectory over the next 3 and 12 months?" \
    --data-urlencode "limit=12" \
    --data-urlencode "ctx_k=24" \
    --data-urlencode "valyu_k=2" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=search" \
    --data-urlencode "valyu_raw=1" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "llm_mode=chunk" \
    --data-urlencode "use_timeline=1" \
    --data-urlencode "timeline_patient_id=DEMO_RA_001" \
    --data-urlencode "research=1"

  # TYPE A: Flare risk / baseline trajectory – SLE
  banner "EOH TEST A2 – SLE flare risk & baseline trajectory (DEMO_SLE_001)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/eoh_stream" \
    --data-urlencode "q=For synthetic lupus patient DEMO_SLE_001 with prior renal flare but recent partial remission, what does Ethos-of-Health infer about near-term (3 month) versus intermediate-term (12 month) flare risk based on the pattern of proteinuria, complements, and symptom stability in the timeline?" \
    --data-urlencode "limit=12" \
    --data-urlencode "ctx_k=24" \
    --data-urlencode "valyu_k=2" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=search" \
    --data-urlencode "valyu_raw=1" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "llm_mode=chunk" \
    --data-urlencode "use_timeline=1" \
    --data-urlencode "timeline_patient_id=DEMO_SLE_001" \
    --data-urlencode "research=1"

  # TYPE B: Flare vs noise – RA mechanical vs inflammatory
  banner "EOH TEST B1 – RA flare vs mechanical noise (DEMO_RA_001)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/eoh_stream" \
    --data-urlencode "q=For DEMO_RA_001, focusing on the later portion of the timeline when knee pain and stiffness recur but CRP and ESR remain near baseline, how would Ethos-of-Health distinguish a true inflammatory flare from mechanical knee pain or overuse, and what monitoring or small course corrections would it emphasize?" \
    --data-urlencode "limit=12" \
    --data-urlencode "ctx_k=24" \
    --data-urlencode "valyu_k=2" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=search" \
    --data-urlencode "valyu_raw=0" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "llm_mode=chunk" \
    --data-urlencode "use_timeline=1" \
    --data-urlencode "timeline_patient_id=DEMO_RA_001" \
    --data-urlencode "research=1"

  # TYPE B: Flare vs noise – SLE low-grade activity vs noise
  banner "EOH TEST B2 – SLE mild symptoms vs noise (DEMO_SLE_001)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/eoh_stream" \
    --data-urlencode "q=For DEMO_SLE_001, recent entries show mild hand pain and fatigue with modest shifts in complements and proteinuria. How would Ethos-of-Health separate a meaningful SLE flare signal from day-to-day noise, and what qualitative thresholds in the timeline would push this toward 'true flare' versus 'background variability'?" \
    --data-urlencode "limit=12" \
    --data-urlencode "ctx_k=24" \
    --data-urlencode "valyu_k=2" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=search" \
    --data-urlencode "valyu_raw=0" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "llm_mode=chunk" \
    --data-urlencode "use_timeline=1" \
    --data-urlencode "timeline_patient_id=DEMO_SLE_001" \
    --data-urlencode "research=1"

  # TYPE C: Diagnostic landscape – RA vs SLE-like tendencies
  banner "EOH TEST C1 – Diagnostic landscape RA-like vs SLE-like (DEMO_RA_001)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/eoh_stream" \
    --data-urlencode "q=Using the synthetic timeline for DEMO_RA_001, how does Ethos-of-Health's diagnostic landscape lean in terms of RA-like versus SLE-like or mixed CTD-like patterns, and which specific events (flares, labs, journals) in the timeline drive that qualitative landscape?" \
    --data-urlencode "limit=12" \
    --data-urlencode "ctx_k=24" \
    --data-urlencode "valyu_k=1" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=search" \
    --data-urlencode "valyu_raw=0" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "llm_mode=chunk" \
    --data-urlencode "use_timeline=1" \
    --data-urlencode "timeline_patient_id=DEMO_RA_001" \
    --data-urlencode "research=0"

  banner "EOH TEST C2 – Diagnostic landscape SLE vs mixed CTD (DEMO_SLE_001)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/eoh_stream" \
    --data-urlencode "q=For DEMO_SLE_001, how does Ethos-of-Health qualitatively position the diagnostic landscape between SLE-like, mixed connective tissue disease-like, and other autoimmune clusters, based on the sequence of renal flare, serologies, and subsequent stabilization in the timeline?" \
    --data-urlencode "limit=12" \
    --data-urlencode "ctx_k=24" \
    --data-urlencode "valyu_k=1" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=search" \
    --data-urlencode "valyu_raw=0" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "llm_mode=chunk" \
    --data-urlencode "use_timeline=1" \
    --data-urlencode "timeline_patient_id=DEMO_SLE_001" \
    --data-urlencode "research=0"

  # TYPE D: Bookkeeping / EoH state summary – RA
  banner "EOH TEST D1 – EoH state snapshot and bookkeeping (DEMO_RA_001)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/eoh_stream" \
    --data-urlencode "q=For DEMO_RA_001, summarize the current Ethos-of-Health state snapshot: stability band, recent baseline drift, flare tendency, and the most salient recent events that EoH would treat as bookkeeping anchors for the next visit." \
    --data-urlencode "limit=12" \
    --data-urlencode "ctx_k=24" \
    --data-urlencode "valyu_k=0" \
    --data-urlencode "use_valyu=0" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "llm_mode=chunk" \
    --data-urlencode "use_timeline=1" \
    --data-urlencode "timeline_patient_id=DEMO_RA_001" \
    --data-urlencode "research=0"

  # TYPE D: Bookkeeping / EoH state summary – SLE
  banner "EOH TEST D2 – EoH state snapshot and bookkeeping (DEMO_SLE_001)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/eoh_stream" \
    --data-urlencode "q=For DEMO_SLE_001, provide an Ethos-of-Health bookkeeping summary highlighting where they sit in the stability band, which prior flares and renal events are most important as anchors, and which labs or symptoms would be 'must-check' markers at the next visit." \
    --data-urlencode "limit=12" \
    --data-urlencode "ctx_k=24" \
    --data-urlencode "valyu_k=0" \
    --data-urlencode "use_valyu=0" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "llm_mode=chunk" \
    --data-urlencode "use_timeline=1" \
    --data-urlencode "timeline_patient_id=DEMO_SLE_001" \
    --data-urlencode "research=0"

  # TYPE E: Strategy / what-if – RA adherence and flare risk
  banner "EOH TEST E1 – Strategy: RA adherence and flare risk (DEMO_RA_001)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/eoh_stream" \
    --data-urlencode "q=If DEMO_RA_001 were to maintain excellent methotrexate adherence with no further gaps over the next year, how would Ethos-of-Health expect their flare risk and baseline stability band to evolve, and what small everyday interventions would be most impactful according to EoH’s flare-prevention logic?" \
    --data-urlencode "limit=12" \
    --data-urlencode "ctx_k=24" \
    --data-urlencode "valyu_k=2" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=search" \
    --data-urlencode "valyu_raw=1" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "llm_mode=chunk" \
    --data-urlencode "use_timeline=1" \
    --data-urlencode "timeline_patient_id=DEMO_RA_001" \
    --data-urlencode "research=1"

  # TYPE E: Strategy / what-if – SLE pregnancy planning
  banner "EOH TEST E2 – Strategy: SLE pregnancy planning (DEMO_SLE_001)"

  curl "${COMMON_FLAGS[@]}" \
    "$BASE_URL/api/rag/eoh_stream" \
    --data-urlencode "q=For DEMO_SLE_001, who wishes to conceive in the next 1–2 years, how would Ethos-of-Health integrate the timeline to prioritize pregnancy-safe stabilization strategies, and what patterns in the timeline would need to stay quiet for EoH to conceptually downgrade flare risk during pregnancy?" \
    --data-urlencode "limit=12" \
    --data-urlencode "ctx_k=24" \
    --data-urlencode "valyu_k=2" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=search" \
    --data-urlencode "valyu_raw=1" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "llm_mode=chunk" \
    --data-urlencode "use_timeline=1" \
    --data-urlencode "timeline_patient_id=DEMO_SLE_001" \
    --data-urlencode "research=1"
}

# ---------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------

run_guideline_tests
run_coding_tests
run_eoh_tests

echo
echo "===================================================================="
echo "FULL STACK PIPELINE TESTS COMPLETED (ask_stream + coding_stream + eoh_stream)"
echo "===================================================================="
echo
