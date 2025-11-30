#!/usr/bin/env bash
set -euo pipefail

# ---------------------------------------------------------------------------
# 2ndOpinionMD RAG / Streaming Test Harness
#
# Covers:
#   - /api/rag/eoh_stream   (Ethos-of-Health)
#   - /api/rag/ask_stream   (Guideline Q&A)
#   - /api/rag/coding_stream (Coding / Abstraction)
#
# Notes:
#   - Uses SSE (-N) so you can tail output and see events.
#   - Reads BASE_URL from env or defaults to https://2ndopinionmd.ai
#   - All tests are GET with URL-encoded query params.
# ---------------------------------------------------------------------------

BASE_URL="${BASE_URL:-https://2ndopinionmd.ai}"

# Optional: tweak these defaults if you want "lighter" runs
DEFAULT_CTX_K="${CTX_K:-48}"
DEFAULT_LIMIT="${LIMIT:-8}"

divider() {
  echo
  echo "================================================================================"
  echo ">>> $1"
  echo "================================================================================"
  echo
}

run_curl() {
  local label="$1"
  shift
  divider "$label"
  echo "+ curl $*"
  echo
  curl -N "$@"
  echo
  echo "--------------------------------------------------------------------------------"
  echo
}

# ---------------------------------------------------------------------------
# EoH: Ethos-of-Health Streaming Tests (/api/rag/eoh_stream)
# ---------------------------------------------------------------------------

test_eoh_flare_risk_ra() {
  # EoH Type A: flare risk + safety context for RA
  local Q="For this RA patient with recent Zone-5 flares and high Stack Level, what is their flare risk over the next 4 weeks and what safety context should we surface?"

  run_curl \
    "EoH RA – Zone-5 flares, high Stack Level (with router plan, guidelines, full ctx)" \
    "${BASE_URL}/api/rag/eoh_stream" \
    --get \
    --data-urlencode "q=${Q}" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "ctx_k=${DEFAULT_CTX_K}" \
    --data-urlencode "limit=${DEFAULT_LIMIT}"
}

test_eoh_flare_risk_ra_with_patient_state() {
  # Same as above, but with patient_state JSON to exercise router + patient context
  local Q="For this RA patient with high Stack Level and recent Zone-5 instability, how would EoH typically characterize flare risk over 4 weeks and which safety themes should we surface?"

  # Patient state JSON (keep small and simple)
  local PATIENT_STATE='{"stack_level":5,"stability_band":"zone5_flare","recent_flare":true,"cbm_status":"unstable"}'

  run_curl \
    "EoH RA – Zone-5 flares with patient_state JSON" \
    "${BASE_URL}/api/rag/eoh_stream" \
    --get \
    --data-urlencode "q=${Q}" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "ctx_k=${DEFAULT_CTX_K}" \
    --data-urlencode "limit=${DEFAULT_LIMIT}" \
    --data-urlencode "patient_state=${PATIENT_STATE}"
}

test_eoh_ckd_stability() {
  # EoH in CKD: stability / drift framing (should still route to KDIGO CKD via ask_stream internals)
  local Q="In a patient with CKD Stage 3b and drifting blood pressure control, how would Ethos-of-Health typically describe their Stack, Stability Band, and short-term risk trajectory?"

  run_curl \
    "EoH CKD – Stack/Band/trajectory framing" \
    "${BASE_URL}/api/rag/eoh_stream" \
    --get \
    --data-urlencode "q=${Q}" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "ctx_k=${DEFAULT_CTX_K}" \
    --data-urlencode "limit=${DEFAULT_LIMIT}"
}

test_eoh_no_llm_metadata() {
  # Metadata-only EoH: good for verifying router + retrieval + gating *without* LLM noise
  local Q="For an RA patient with frequent Zone-4 and Zone-5 flares, which EoH modules would typically be involved in estimating flare risk and alert tiers?"

  run_curl \
    "EoH metadata-only – router + retrieval, no LLM" \
    "${BASE_URL}/api/rag/eoh_stream" \
    --get \
    --data-urlencode "q=${Q}" \
    --data-urlencode "with_llm=0" \
    --data-urlencode "ctx_k=${DEFAULT_CTX_K}" \
    --data-urlencode "limit=${DEFAULT_LIMIT}"
}

# ---------------------------------------------------------------------------
# Guideline Q&A Tests (/api/rag/ask_stream)
# ---------------------------------------------------------------------------

test_ask_ra_guidelines() {
  local Q="In adults with rheumatoid arthritis and high disease activity despite methotrexate, how do ACR 2021 and EULAR 2022 recommend escalating therapy, and what safety considerations should be highlighted?"

  run_curl \
    "Guideline Q&A – RA escalation (ACR 2021 + EULAR 2022)" \
    "${BASE_URL}/api/rag/ask_stream" \
    --get \
    --data-urlencode "q=${Q}" \
    --data-urlencode "sources=acr_ra_2021,eular_ra_2022" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "ctx_k=${DEFAULT_CTX_K}" \
    --data-urlencode "limit=${DEFAULT_LIMIT}" \
    --data-urlencode "use_valyu=0"
}

test_ask_hf_glp1_sglt2_no_valyu() {
  local Q="In adults with heart failure, what is the role of GLP-1 receptor agonists compared with SGLT2 inhibitors according to contemporary guidelines?"

  run_curl \
    "Guideline Q&A – HF GLP-1 vs SGLT2 (no Valyu)" \
    "${BASE_URL}/api/rag/ask_stream" \
    --get \
    --data-urlencode "q=${Q}" \
    --data-urlencode "sources=acc_aha_hfsa_hf_2022" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "ctx_k=${DEFAULT_CTX_K}" \
    --data-urlencode "limit=${DEFAULT_LIMIT}" \
    --data-urlencode "use_valyu=0"
}

test_ask_ckd_bp_with_valyu() {
  local Q="How do KDIGO 2021 blood pressure guidelines in CKD define blood pressure targets and preferred agents for non-diabetic CKD with albuminuria?"

  run_curl \
    "Guideline Q&A – KDIGO BP in CKD (Valyu answer mode)" \
    "${BASE_URL}/api/rag/ask_stream" \
    --get \
    --data-urlencode "q=${Q}" \
    --data-urlencode "sources=kdigo_bp_ckd_2021,kdigo_ckd_2021" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "ctx_k=${DEFAULT_CTX_K}" \
    --data-urlencode "limit=${DEFAULT_LIMIT}" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=answer" \
    --data-urlencode "valyu_k=3" \
    --data-urlencode "valyu_raw=0"
}

test_ask_general_search_nice() {
  local Q="What do NICE guidelines say about initial antihypertensive therapy in adults under 55 with uncomplicated hypertension?"

  run_curl \
    "Guideline Q&A – NICE hypertension search (broad source, no Valyu)" \
    "${BASE_URL}/api/rag/ask_stream" \
    --get \
    --data-urlencode "q=${Q}" \
    --data-urlencode "sources=nice" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "ctx_k=${DEFAULT_CTX_K}" \
    --data-urlencode "limit=${DEFAULT_LIMIT}" \
    --data-urlencode "use_valyu=0"
}

# ---------------------------------------------------------------------------
# Coding / Abstraction Tests (/api/rag/coding_stream)
# ---------------------------------------------------------------------------

# NOTE: Make sure CODING_DEFAULT_SOURCES / CODE_SOURCES in stream_config
# include these vocabularies, or explicitly pass sources here.

CODING_SOURCES_ALL="icd10cm,icd11,snomed,rxnorm,loinc"

test_coding_ra_diagnosis_multi_vocab() {
  local Q="Seropositive rheumatoid arthritis with high disease activity and erosions on imaging."

  run_curl \
    "Coding – RA diagnosis across ICD-10-CM, ICD-11, SNOMED" \
    "${BASE_URL}/api/rag/coding_stream" \
    --get \
    --data-urlencode "q=${Q}" \
    --data-urlencode "sources=${CODING_SOURCES_ALL}" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=0" \
    --data-urlencode "ctx_k=${DEFAULT_CTX_K}" \
    --data-urlencode "limit=${DEFAULT_LIMIT}"
}

test_coding_medication_rxnorm_only() {
  local Q="Start oral methotrexate 15 mg weekly with folic acid supplementation."

  run_curl \
    "Coding – Medication (RxNorm focus)" \
    "${BASE_URL}/api/rag/coding_stream" \
    --get \
    --data-urlencode "q=${Q}" \
    --data-urlencode "sources=rxnorm" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=0" \
    --data-urlencode "ctx_k=${DEFAULT_CTX_K}" \
    --data-urlencode "limit=${DEFAULT_LIMIT}"
}

test_coding_lab_loinc_only() {
  local Q="Order a basic metabolic panel and serum creatinine level."

  run_curl \
    "Coding – Labs (LOINC focus)" \
    "${BASE_URL}/api/rag/coding_stream" \
    --get \
    --data-urlencode "q=${Q}" \
    --data-urlencode "sources=loinc" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=0" \
    --data-urlencode "ctx_k=${DEFAULT_CTX_K}" \
    --data-urlencode "limit=${DEFAULT_LIMIT}"
}

test_coding_no_llm_metadata_only() {
  local Q="Type 2 diabetes mellitus with diabetic kidney disease and albuminuria."

  run_curl \
    "Coding metadata-only – no LLM (ICD + SNOMED rows only)" \
    "${BASE_URL}/api/rag/coding_stream" \
    --get \
    --data-urlencode "q=${Q}" \
    --data-urlencode "sources=icd10cm,icd11,snomed" \
    --data-urlencode "with_llm=0" \
    --data-urlencode "use_valyu=0" \
    --data-urlencode "ctx_k=${DEFAULT_CTX_K}" \
    --data-urlencode "limit=${DEFAULT_LIMIT}"
}

test_coding_with_valyu_assist() {
  local Q="Community-acquired pneumonia due to Streptococcus pneumoniae, initial encounter."

  run_curl \
    "Coding – CAP with Valyu assist (icd10cm + icd11 + snomed)" \
    "${BASE_URL}/api/rag/coding_stream" \
    --get \
    --data-urlencode "q=${Q}" \
    --data-urlencode "sources=icd10cm,icd11,snomed" \
    --data-urlencode "with_llm=1" \
    --data-urlencode "use_valyu=1" \
    --data-urlencode "valyu_mode=answer" \
    --data-urlencode "valyu_k=3" \
    --data-urlencode "valyu_raw=0" \
    --data-urlencode "ctx_k=${DEFAULT_CTX_K}" \
    --data-urlencode "limit=${DEFAULT_LIMIT}"
}

# ---------------------------------------------------------------------------
# Master runners
# ---------------------------------------------------------------------------

run_eoh_suite() {
  test_eoh_flare_risk_ra
  test_eoh_flare_risk_ra_with_patient_state
  test_eoh_ckd_stability
  test_eoh_no_llm_metadata
}

run_ask_suite() {
  test_ask_ra_guidelines
  test_ask_hf_glp1_sglt2_no_valyu
  test_ask_ckd_bp_with_valyu
  test_ask_general_search_nice
}

run_coding_suite() {
  test_coding_ra_diagnosis_multi_vocab
  test_coding_medication_rxnorm_only
  test_coding_lab_loinc_only
  test_coding_no_llm_metadata_only
  test_coding_with_valyu_assist
}

run_all() {
  run_eoh_suite
  run_ask_suite
  run_coding_suite
}

# ---------------------------------------------------------------------------
# CLI interface
#   ./test_rag_endpoints.sh         -> run_all
#   ./test_rag_endpoints.sh eoh     -> only EoH tests
#   ./test_rag_endpoints.sh ask     -> only ask_stream tests
#   ./test_rag_endpoints.sh coding  -> only coding_stream tests
# ---------------------------------------------------------------------------

main() {
  local suite="${1:-all}"

  case "${suite}" in
    eoh)
      run_eoh_suite
      ;;
    ask)
      run_ask_suite
      ;;
    coding)
      run_coding_suite
      ;;
    all)
      run_all
      ;;
    *)
      echo "Usage: $0 [all|eoh|ask|coding]" >&2
      exit 1
      ;;
  esac
}

main "$@"
