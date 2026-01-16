#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://2ndopinionmd.ai}"

echo "Using BASE_URL=$BASE_URL"

cat <<'NOTE'
EoH FULL PIPELINE TESTS (SCGP synthetic patients)

This suite is meant to exercise the *entire* Ethos-of-Health pipeline:

- All ten synthetic SCGP patients:
  - SCGP_ASTHMA_001
  - SCGP_RA_001
  - SCGP_SLE_001
  - SCGP_UC_001
  - SCGP_CROHNS_001
  - SCGP_HF_001
  - SCGP_T1DM_001
  - SCGP_MS_001
  - SCGP_AS_001
  - SCGP_RA_FIBRO_001

- Question types: A, B, C, D, E, OTHER (at least once each, router-permitting)
- Timelines: use_timeline=1 for ALL tests (hits ehr.patient_timeline + eoh.patient_state)
- Valyu: used in MOST tests (research=1, valyu_raw=1) to drive full research path
- MIMIC / case analogs: triggered via B/C/OTHER-style questions
- NO explicit `sources=` parameter — the source router + EoH router pick sources

You can run this whole file as:

  chmod +x full-pipeline-tests.sh
  ./full-pipeline-tests.sh

Or copy/paste individual curls.
NOTE

# --------------------------------------------------------------------
# Common flags shared by all tests (router + source router choose sources)
# --------------------------------------------------------------------
COMMON_FLAGS=(
  --data-urlencode "limit=8"
  --data-urlencode "ctx_k=24"
  --data-urlencode "with_llm=1"
  --data-urlencode "llm_mode=chunk"
)

# Helper separator
sep() {
  echo
  echo "============================================================"
  echo "$1"
  echo "============================================================"
}

# ====================================================================
# TEST 1 – SCGP_ASTHMA_001
# Target: TYPE B (flare vs noise) + Valyu + MIMIC + timeline
# ====================================================================
sep "TEST 1: TYPE B – Asthma flare vs noise (SCGP_ASTHMA_001)"

curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  "${COMMON_FLAGS[@]}" \
  --data-urlencode "q=For synthetic patient SCGP_ASTHMA_001 in the Ethos-of-Health sandbox, whose timeline includes recurrent wheeze, variable symptoms, and several suspected exacerbations, how should EoH distinguish true asthma flares from noisy cough or viral upper respiratory episodes, and what does the timeline suggest about near-term flare risk and controller-intensification strategy over the next 6–12 months?" \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_ASTHMA_001" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=3" \
  --data-urlencode "valyu_raw=1" \
  --data-urlencode "research=1"

# ====================================================================
# TEST 2 – SCGP_RA_001
# Target: TYPE A (flare risk / trajectory) + timeline (Valyu usually off)
# ====================================================================
sep "TEST 2: TYPE A – RA flare risk and trajectory (SCGP_RA_001)"

curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  "${COMMON_FLAGS[@]}" \
  --data-urlencode "q=For synthetic RA patient SCGP_RA_001, whose timeline in the EoH sandbox shows seropositive inflammatory arthritis with periods of good control, one or more flares after medication lapses, and partial restabilization, how would Ethos-of-Health describe their flare risk and baseline trajectory over the next 3 and 12 months using stacks, stability bands, and baseline drift concepts derived from the timeline?" \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_RA_001" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=2" \
  --data-urlencode "valyu_raw=1" \
  --data-urlencode "research=0"

# ====================================================================
# TEST 3 – SCGP_SLE_001
# Target: TYPE B (flare vs noise in lupus) + Valyu + MIMIC + timeline
# ====================================================================
sep "TEST 3: TYPE B – SLE flare vs noise (SCGP_SLE_001)"

curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  "${COMMON_FLAGS[@]}" \
  --data-urlencode "q=For lupus demo patient SCGP_SLE_001, with a synthetic timeline that includes high-titer ANA and anti-dsDNA, prior lupus nephritis, and more recent mild hand pain, fatigue, and modest complement and urine-protein changes, how should Ethos-of-Health distinguish a true SLE flare from background noise (infection, medication effects, chronic pain), and what qualitative flare-risk interpretation follows from the recent labs and events in the timeline?" \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_SLE_001" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=3" \
  --data-urlencode "valyu_raw=1" \
  --data-urlencode "research=1"

# ====================================================================
# TEST 4 – SCGP_UC_001
# Target: TYPE D (12-month plan / control trajectory) + Valyu + timeline
# ====================================================================
sep "TEST 4: TYPE D – UC control and 12-month plan (SCGP_UC_001)"

curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  "${COMMON_FLAGS[@]}" \
  --data-urlencode "q=For ulcerative colitis demo patient SCGP_UC_001, whose synthetic timeline shows periods of remission, moderate flares with rectal bleeding and increased stool frequency, and changes in maintenance therapy, how would Ethos-of-Health summarize the current control status and outline a qualitative 12-month plan trajectory, including how flare history and recovery patterns in the timeline shape monitoring intensity and treatment-adjustment thresholds?" \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_UC_001" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=3" \
  --data-urlencode "valyu_raw=1" \
  --data-urlencode "research=1"

# ====================================================================
# TEST 5 – SCGP_CROHNS_001
# Target: TYPE C (diagnostic landscape – Crohn’s vs IBS vs infection)
#         + Valyu + MIMIC + timeline
# ====================================================================
sep "TEST 5: TYPE C – Diagnostic landscape (SCGP_CROHNS_001)"

curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  "${COMMON_FLAGS[@]}" \
  --data-urlencode "q=For synthetic patient SCGP_CROHNS_001, whose timeline shows chronic diarrhea, weight changes, abdominal pain, imaging and endoscopy compatible with Crohn’s disease, and some episodes where infection or IBS-like symptoms are possible explanations, how would Ethos-of-Health describe the diagnostic landscape (Crohn’s-like versus IBS-like versus infection-driven), and what misclassification or hidden-comorbidity patterns are suggested by the trajectory captured in the timeline?" \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_CROHNS_001" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=3" \
  --data-urlencode "valyu_raw=1" \
  --data-urlencode "research=1"

# ====================================================================
# TEST 6 – SCGP_HF_001
# Target: OTHER (guideline-heavy HF question) + Valyu + MIMIC + timeline
# ====================================================================
sep "TEST 6: OTHER – HF guideline-backed EoH view (SCGP_HF_001)"

curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  "${COMMON_FLAGS[@]}" \
  --data-urlencode "q=For heart failure demo patient SCGP_HF_001, using the synthetic timeline of hospitalizations, guideline-directed medical therapy starts and uptitrations, and changes in symptoms and biomarkers, how would Ethos-of-Health synthesize the current stability band and near-term decompensation risk, and how does this conceptual trajectory align with contemporary HF guideline principles (quadruple therapy, diuretics, and follow-up intensity) visible in the retrieved context?" \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_HF_001" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=3" \
  --data-urlencode "valyu_raw=1" \
  --data-urlencode "research=1"

# ====================================================================
# TEST 7 – SCGP_T1DM_001
# Target: TYPE D (plan / risk over 12 months) + timelines, some Valyu
# ====================================================================
sep "TEST 7: TYPE D – T1DM control and risk (SCGP_T1DM_001)"

curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  "${COMMON_FLAGS[@]}" \
  --data-urlencode "q=For synthetic type 1 diabetes patient SCGP_T1DM_001, whose timeline shows episodes of hypoglycemia, variable glucose control, and one or more DKA or near-DKA events, how would Ethos-of-Health qualitatively describe their current stability band, near-term risk for severe glycemic events, and the conceptual 12-month trajectory if current patterns persist versus if adherence and time-in-range improve, based solely on the timeline and EoH stack logic?" \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_T1DM_001" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=2" \
  --data-urlencode "valyu_raw=1" \
  --data-urlencode "research=1"

# ====================================================================
# TEST 8 – SCGP_MS_001
# Target: TYPE A (trajectory / progression risk) + timeline + Valyu
# ====================================================================
sep "TEST 8: TYPE A – MS trajectory and progression risk (SCGP_MS_001)"

curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  "${COMMON_FLAGS[@]}" \
  --data-urlencode "q=For multiple sclerosis demo patient SCGP_MS_001, whose synthetic timeline includes relapses, imaging changes, and periods of stability on disease-modifying therapy, how would Ethos-of-Health describe the current stability band, relapse risk over the next 1–3 years, and conceptual progression trajectory, using the EoH terrain and baseline-drift framework informed by the events in the timeline?" \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_MS_001" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=3" \
  --data-urlencode "valyu_raw=1" \
  --data-urlencode "research=1"

# ====================================================================
# TEST 9 – SCGP_AS_001
# Target: TYPE C/B hybrid – axial SpA vs mechanical back pain
#         + Valyu + MIMIC + timeline
# ====================================================================
sep "TEST 9: TYPE C/B – Axial SpA vs mechanical back pain (SCGP_AS_001)"

curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  "${COMMON_FLAGS[@]}" \
  --data-urlencode "q=For axial spondyloarthritis demo patient SCGP_AS_001, whose synthetic timeline shows inflammatory back pain features, HLA-B27 status, imaging findings, and variable response to therapy, how would Ethos-of-Health describe the diagnostic landscape (axial SpA-like versus mechanical back pain or other causes) and distinguish true inflammatory flares from noninflammatory noise when interpreting recent symptom patterns in the timeline?" \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_AS_001" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=3" \
  --data-urlencode "valyu_raw=1" \
  --data-urlencode "research=1"

# ====================================================================
# TEST 10 – SCGP_RA_FIBRO_001
# Target: TYPE E / OTHER – miscalibration & overlay (RA + fibromyalgia)
#         + Valyu + MIMIC + timeline
# ====================================================================
sep "TEST 10: TYPE E/OTHER – RA + fibromyalgia overlay (SCGP_RA_FIBRO_001)"

curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  "${COMMON_FLAGS[@]}" \
  --data-urlencode "q=For synthetic patient SCGP_RA_FIBRO_001, in whom the timeline reflects seropositive RA features plus a strong chronic pain and fatigue overlay consistent with fibromyalgia, how would Ethos-of-Health conceptually separate inflammatory RA flares from noninflammatory fibromyalgia noise, and what does the EoH framework suggest about miscalibration risk (over-treating pain as flare or under-recognizing true flare) when reading this mixed timeline over the next 12 months?" \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_RA_FIBRO_001" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=3" \
  --data-urlencode "valyu_raw=1" \
  --data-urlencode "research=1"

echo
echo "All full-pipeline EoH synthetic tests dispatched."
