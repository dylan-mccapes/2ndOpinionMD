#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-https://2ndopinionmd.ai}"

echo "Using BASE_URL=${BASE_URL}"
echo
echo "NOTE: Make sure you've seeded timelines, e.g.:"
echo "  python -m server.timeline.seed_data --patient-id DEMO_RA_001 --type all"
echo

###############################################################################
# TYPE A – Flare Risk (DEMO_RA_001 – RA)
###############################################################################
echo "========================================"
echo "TEST: TYPE A (Flare Risk, DEMO_RA_001)"
echo "========================================"
echo

curl -sS -N "${BASE_URL}/api/rag/eoh_stream" \
  --get \
  --data-urlencode "q=For synthetic RA patient DEMO_RA_001, whose CRP and symptoms improved on methotrexate but then had a flare after a 2-week medication gap with rising CRP and ESR around day 165–180, what is their flare risk and Ethos-of-Health baseline trajectory over the next 3 and 12 months?" \
  --data-urlencode "patient_id=DEMO_RA_001" \
  --data-urlencode "limit=8" \
  --data-urlencode "ctx_k=24" \
  --data-urlencode "sources=mimic4_note,valyu,all_eoh" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=2" \
  --data-urlencode "mode=eoh"

echo -e "\n\n"

###############################################################################
# TYPE B – Flare vs Noise (DEMO_SLE_001 – SLE)
###############################################################################
echo "========================================"
echo "TEST: TYPE B (Flare vs Noise, DEMO_SLE_001)"
echo "========================================"
echo

curl -sS -N "${BASE_URL}/api/rag/eoh_stream" \
  --get \
  --data-urlencode "q=For lupus patient DEMO_SLE_001 with a history of high-titer ANA and dsDNA and a prior renal flare, but now with mild hand pain and fatigue and modest changes in complements and proteinuria, how should Ethos-of-Health distinguish a true flare from noise using the recent labs, urine protein, and symptom pattern?" \
  --data-urlencode "patient_id=DEMO_SLE_001" \
  --data-urlencode "limit=8" \
  --data-urlencode "ctx_k=24" \
  --data-urlencode "sources=mimic4_note,valyu,all_eoh" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=2" \
  --data-urlencode "mode=eoh"

echo -e "\n\n"

###############################################################################
# TYPE C – Explain Tier Escalation (DEMO_RA_001)
###############################################################################
echo "========================================"
echo "TEST: TYPE C (Explain Tier Escalation, DEMO_RA_001)"
echo "========================================"
echo

curl -sS -N "${BASE_URL}/api/rag/eoh_stream" \
  --get \
  --data-urlencode "q=Ethos-of-Health recently escalated synthetic rheumatoid arthritis patient DEMO_RA_001 from Tier 2 to Tier 4 after a flare following missed methotrexate doses and rising inflammatory markers. Explain why the system made that change and which underlying signals, bands, and decision packets drove the tier escalation." \
  --data-urlencode "patient_id=DEMO_RA_001" \
  --data-urlencode "limit=8" \
  --data-urlencode "ctx_k=24" \
  --data-urlencode "sources=mimic4_note,valyu,all_eoh" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=2" \
  --data-urlencode "mode=eoh"

echo -e "\n\n"

###############################################################################
# TYPE D – Plan Adjustment / Remission Maintenance (DEMO_PSA_001)
###############################################################################
echo "========================================"
echo "TEST: TYPE D (Plan Adjustment, DEMO_PSA_001)"
echo "========================================"
echo

curl -sS -N "${BASE_URL}/api/rag/eoh_stream" \
  --get \
  --data-urlencode "q=For psoriatic arthritis patient DEMO_PSA_001 with long-standing psoriasis, prior dactylitis and enthesitis, and now good response to adalimumab with near-normal CRP, how should Ethos-of-Health adjust the care plan and monitoring over the next 12–24 months to balance flare prevention, functional outcomes, and biologic safety?" \
  --data-urlencode "patient_id=DEMO_PSA_001" \
  --data-urlencode "limit=8" \
  --data-urlencode "ctx_k=24" \
  --data-urlencode "sources=mimic4_note,valyu,all_eoh" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=2" \
  --data-urlencode "mode=eoh"

echo -e "\n\n"

###############################################################################
# TYPE E – Calibration / Over-Suppression (RA flare detector)
###############################################################################
echo "========================================"
echo "TEST: TYPE E (Calibration & Over-Suppression, DEMO_RA_001)"
echo "========================================"
echo

curl -sS -N "${BASE_URL}/api/rag/eoh_stream" \
  --get \
  --data-urlencode "q=Using DEMO_RA_001 as a fixture, assess whether the RA flare detector in Ethos-of-Health might be over-suppressing events. How would calibration metrics, suppression audits, and drift detection modules use this patient’s flare history, missed doses, and lab trajectories to detect over-suppression or calibration drift?" \
  --data-urlencode "patient_id=DEMO_RA_001" \
  --data-urlencode "limit=8" \
  --data-urlencode "ctx_k=24" \
  --data-urlencode "sources=mimic4_note,valyu,all_eoh" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=2" \
  --data-urlencode "mode=eoh"

echo -e "\n\n"

echo "Done."
