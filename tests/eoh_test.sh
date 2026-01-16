#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"

echo "1) RA – stability band + flare risk (timeline + Valyu search)"
curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  --data-urlencode 'q=For this seropositive rheumatoid arthritis demo patient, based on the full timeline of visits, labs (CRP/ESR, RF, Anti-CCP), methotrexate and prednisone use, missed doses, and prior flares, how would Ethos-of-Health characterize their current stability band, short-term flare risk over the next 1–3 months, and the main flare precursors or warning patterns in this timeline?' \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=DEMO_RA_001" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=2" \
  --data-urlencode "valyu_mode=search" \
  --data-urlencode "valyu_raw=0"

echo
echo "2) RA – flare vs centralized pain (timeline, internal-only EoH, Valyu off)"
curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  --data-urlencode 'q=For this seropositive rheumatoid arthritis demo patient (DEMO_RA_001), looking specifically at the last 3–6 months of the timeline — visits, inflammatory markers, missed methotrexate doses, steroid bursts, sleep and stress notes, and any documented flares — would Ethos-of-Health treat the current spike in joint pain as a true inflammatory flare versus mainly centralized or amplified pain? Explain how EoH would classify this episode within the stability bands and flare stacks, and the short-term flare risk over the next 4–8 weeks.' \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=DEMO_RA_001" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=0" \
  --data-urlencode "valyu_k=0"

echo
echo "3) SLE-like – diagnostic landscape + kidney trajectory (timeline + Valyu search)"
curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  --data-urlencode 'q=For this lupus-like demo patient, using the full timeline of labs (ANA, anti-dsDNA, complements, proteinuria), flares, organ involvement, and treatment changes, how would Ethos-of-Health describe the diagnostic landscape across RA-like, SLE-like, psoriatic, Sjögren-like, mixed-CTD-like, vasculitis-like, and other patterns, and how would it qualitatively characterize current flare risk and kidney involvement trajectory?' \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=DEMO_SLE_001" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=2" \
  --data-urlencode "valyu_mode=search" \
  --data-urlencode "valyu_raw=0"

echo
echo "4) PsA – portal-style story (timeline + Valyu search, question_type OTHER-ish)"
curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  --data-urlencode 'q=For this psoriatic-arthritis-like demo patient (DEMO_PSA_001), using the full timeline of psoriasis history, joint flares, enthesitis, dactylitis, treatments, and stability periods, how would Ethos-of-Health explain the story of their disease to a patient and clinician in a portal setting? Focus less on numeric flare risk and more on what seems stable vs fragile and how this frames shared decision-making over the next year.' \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=DEMO_PSA_001" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=3" \
  --data-urlencode "valyu_mode=search" \
  --data-urlencode "valyu_raw=0"

echo
echo "5) UC – flare risk decision chain (timeline + Valyu search + explicit valyu_sources)"
curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  --data-urlencode 'q=For this ulcerative colitis patient, why would the Ethos-of-Health system escalate flare risk over the next 30 days based on the current timeline? Reconstruct the decision chain, including the key events and features that drive that prediction.' \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_UC_001" \
  --data-urlencode "limit=8" \
  --data-urlencode "ctx_k=24" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=3" \
  --data-urlencode "valyu_mode=search" \
  --data-urlencode "valyu_sources=valyu/valyu-pubmed"

echo
echo "6) UC – internal-only comparison (timeline, Valyu off)"
curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  --data-urlencode 'q=For this ulcerative colitis patient, using only internal MKG and Ethos-of-Health context, explain why flare risk is escalating over the next 30 days and which timeline events are most influential.' \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_UC_001" \
  --data-urlencode "limit=8" \
  --data-urlencode "ctx_k=24" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=0" \
  --data-urlencode "valyu_k=0"

echo
echo "7) HF – non-timeline, guideline + Valyu ANSWER mode (EoH high-level reasoning)"
curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  --data-urlencode 'q=In adults with chronic heart failure and type 2 diabetes, how does Ethos-of-Health integrate ACC/AHA/HFSA and NICE guidance with the internal EoH framework to prioritize SGLT2 inhibitors, GLP-1 receptor agonists, and other cardiometabolic therapies over the next 12 months?' \
  --data-urlencode "use_timeline=0" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=3" \
  --data-urlencode "valyu_mode=answer" \
  --data-urlencode "valyu_raw=0"

echo
echo "8) Asthma + metabolic disease – multi-morbidity (timeline + internal-only EoH)"
curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  --data-urlencode 'q=For this asthma and metabolic-syndrome demo patient, how would Ethos-of-Health describe the interaction between airway control, weight trajectory, and cardiometabolic risk over the next 2–3 years, and which stability bands are most fragile?' \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_ASTHMA_001" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=0" \
  --data-urlencode "valyu_k=0"

echo
echo "9) Crohn’s – horizon scan / scenario planning (timeline + Valyu ANSWER mode)"
curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  --data-urlencode 'q=For this Crohn’s disease demo patient, assume the current treatment is partially effective but instability is creeping back in. How would Ethos-of-Health frame best- and worst-case trajectories over the next 3–5 years, including key milestones that would trigger re-staging or treatment escalation?' \
  --data-urlencode "use_timeline=1" \
  --data-urlencode "timeline_patient_id=SCGP_CROHNS_001" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=1" \
  --data-urlencode "valyu_k=3" \
  --data-urlencode "valyu_mode=answer" \
  --data-urlencode "valyu_raw=0"

echo
echo "10) Framework sanity check – pure Ethos-of-Health explanation (no timeline, no Valyu)"
curl -N "$BASE_URL/api/rag/eoh_stream" \
  --get \
  --data-urlencode 'q=Without using any specific patient timeline, explain how Ethos-of-Health models original healthy baseline, chronic baseline modes, stability bands, flare stacks, and short-horizon flare prediction, as if preparing an internal whitepaper summary.' \
  --data-urlencode "use_timeline=0" \
  --data-urlencode "with_llm=1" \
  --data-urlencode "use_valyu=0" \
  --data-urlencode "valyu_k=0"

echo
echo "Done."
