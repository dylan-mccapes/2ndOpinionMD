# server/scripts/test_eoh_valyu_stream.py
"""
Run a suite of Ethos-of-Health (EoH) queries through the streaming endpoint
with use_valyu=1, to exercise the full EoH pipeline + Valyu deepsearch.

Usage (from repo root):

  source server/venv312/bin/activate
  python -m server.scripts.test_eoh_valyu_stream

Adjust BASE_URL and EOH_PATH below if needed.
"""

import asyncio
import json
import sys
from typing import Any, Dict, List

import httpx

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------

# External base URL; change to http://localhost:8000 for local testing
BASE_URL = "https://2ndopinionmd.ai"
# Update this if your EoH stream endpoint path is different
EOH_PATH = "/api/rag/eoh_stream"

# Common query params: use_valyu should always be 1 for this test harness
COMMON_PARAMS = {
    "use_valyu": 1,
    "with_llm": 1,
    # Uncomment / tweak if your router expects additional flags:
    # "pipeline": "eoh",
    # "valyu_mode": "search",  # or "answer" depending on your design
}

# ---------------------------------------------------------------------
# Test cases – designed to hit the full EoH surface area
# ---------------------------------------------------------------------

TEST_CASES: List[Dict[str, Any]] = [
    {
        "id": "eoh_sle_pregnancy_flare",
        "label": "SLE – flare risk & management in pregnancy",
        "question": (
            "In a woman with systemic lupus erythematosus who is planning pregnancy "
            "within the next 6–12 months and has a history of lupus nephritis but is "
            "currently in low disease activity on hydroxychloroquine and azathioprine, "
            "how should we: (1) counsel her on flare risk during pregnancy and in the "
            "3-month postpartum period, (2) optimize medications before conception, and "
            "(3) monitor her for preeclampsia vs lupus nephritis flares according to "
            "current ACR/EULAR pregnancy guidance and recent literature?"
        ),
        "tags": ["sle", "pregnancy", "flare_risk", "valyu_pubmed"],
    },
    {
        "id": "eoh_ra_treat_to_target_multi_morbidity",
        "label": "RA – treat-to-target with multimorbidity",
        "question": (
            "In a 55-year-old woman with seropositive rheumatoid arthritis, class II heart "
            "failure with reduced ejection fraction, type 2 diabetes, and obesity who has "
            "moderate disease activity on methotrexate and leflunomide, how should we "
            "implement a treat-to-target strategy (remission or low disease activity) "
            "while balancing heart failure, infection risk, and metabolic comorbidities? "
            "Compare TNF inhibitors vs non-TNF biologics vs JAK inhibitors based on "
            "current ACR and EULAR RA guidelines and key outcome trials."
        ),
        "tags": ["ra", "treat_to_target", "multimorbidity"],
    },
    {
        "id": "eoh_ra_ild_pregnancy",
        "label": "RA-ILD – pregnancy planning & DMARD strategy",
        "question": (
            "In a 32-year-old woman with seropositive RA and mild RA-associated interstitial "
            "lung disease who wishes to conceive in the next 1–2 years, what is the optimal "
            "csDMARD and biologic strategy before conception, during pregnancy, and postpartum? "
            "Which agents should be avoided (e.g., mycophenolate, leflunomide, JAK inhibitors) "
            "and which can be continued (e.g., hydroxychloroquine, azathioprine, certain TNF "
            "inhibitors) according to ACR/EULAR RA and ILD guidance and recent cohort data?"
        ),
        "tags": ["ra", "ild", "pregnancy", "med_safety"],
    },
    {
        "id": "eoh_sle_aps_thrombosis",
        "label": "SLE + APS – thrombosis & pregnancy risk management",
        "question": (
            "In a 28-year-old woman with SLE, triple-positive antiphospholipid antibodies "
            "(lupus anticoagulant, anticardiolipin, anti-β2-glycoprotein I), prior DVT, and "
            "one first-trimester miscarriage, how should we manage anticoagulation and "
            "pregnancy planning? Outline preconception counseling, anticoagulant regimen "
            "during pregnancy and postpartum, and monitoring for thrombosis and preeclampsia "
            "based on current EULAR/ACR APS and SLE pregnancy guidelines."
        ),
        "tags": ["sle", "aps", "thrombosis", "pregnancy"],
    },
    {
        "id": "eoh_ckd_bp_glp1_sglt2",
        "label": "CKD + diabetes + GLP-1/SGLT2 – long-term EoH care",
        "question": (
            "In a 60-year-old man with type 2 diabetes, CKD stage 3b (eGFR 35), albuminuria, "
            "and heart failure with preserved EF who is already on an ACE inhibitor and an "
            "SGLT2 inhibitor, what is the Ethos-of-Health long-term plan for kidney and "
            "cardiovascular risk reduction? Compare the roles of GLP-1 receptor agonists vs "
            "further RAAS blockade vs non-steroidal MRAs (e.g., finerenone) according to "
            "KDIGO, ADA, and major outcome trials."
        ),
        "tags": ["ckd", "t2dm", "cv_risk", "glp1", "sglt2"],
    },
    {
        "id": "eoh_ibd_biologic_strategy",
        "label": "IBD – biologic sequencing & flare prevention",
        "question": (
            "In a 30-year-old woman with extensive ulcerative colitis who has had an "
            "inadequate response to optimized anti-TNF therapy and is considering switching "
            "to vedolizumab vs ustekinumab vs upadacitinib, how should we choose and plan "
            "her long-term Ethos-of-Health strategy to minimize flares, hospitalizations, "
            "and colorectal cancer risk? Summarize evidence from major trials and ECCO/ACG "
            "guidelines."
        ),
        "tags": ["ibd", "ulcerative_colitis", "biologics", "flare_prevention"],
    },
    {
        "id": "eoh_vasculitis_flare_prediction",
        "label": "ANCA-vasculitis – remission maintenance & flare prediction",
        "question": (
            "In a 65-year-old man with MPO-ANCA–associated vasculitis in remission after "
            "rituximab induction, what is the recommended strategy for remission maintenance "
            "and flare prediction over the next 5 years? Compare fixed-interval rituximab vs "
            "relapse-driven dosing vs azathioprine or methotrexate, and discuss biomarker-"
            "guided monitoring (ANCA titers, B-cell repopulation) based on current EULAR "
            "vasculitis guidance and key RCTs."
        ),
        "tags": ["anca_vasculitis", "remission_maintenance", "flare_prediction"],
    },
    {
        "id": "eoh_longitudinal_multimorbidity",
        "label": "Multimorbidity – holistic Ethos-of-Health longitudinal plan",
        "question": (
            "Design a 12-month Ethos-of-Health longitudinal care plan for a 50-year-old "
            "woman with SLE, RA, hypertension, obesity, and generalized anxiety disorder. "
            "She has low-moderate inflammatory disease activity, is on hydroxychloroquine "
            "and low-dose methotrexate, and works full-time. Integrate guideline-based "
            "targets for SLE and RA disease activity, blood pressure, weight, and mental "
            "health; include flare prevention, vaccination, pregnancy counseling, and "
            "lifestyle interventions. Provide milestones at 3, 6, 9, and 12 months."
        ),
        "tags": ["multimorbidity", "longitudinal_plan", "eoh_core"],
    },
]

# ---------------------------------------------------------------------
# SSE client
# ---------------------------------------------------------------------


async def run_single_test(client: httpx.AsyncClient, case: Dict[str, Any]) -> None:
    url = f"{BASE_URL}{EOH_PATH}"
    params = {"q": case["question"], **COMMON_PARAMS}

    print("=" * 80)
    print(f"[{case['id']}] {case['label']}")
    print(f"Tags: {', '.join(case.get('tags', []))}")
    print("-" * 80)
    display_params = {"q": "...", **COMMON_PARAMS}
    print(f"GET {url}  params={display_params}")
    print("-" * 80)

    try:
        async with client.stream("GET", url, params=params, timeout=None) as resp:
            resp.raise_for_status()
            # Simple SSE parser: print events, capture last data payload
            current_event = None
            last_data: Dict[str, Any] | None = None

            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith("event:"):
                    current_event = line[len("event:") :].strip()
                elif line.startswith("data:"):
                    raw = line[len("data:") :].strip()
                    try:
                        payload = json.loads(raw)
                    except Exception:
                        payload = {"raw": raw}

                    # Print condensed view
                    print(f"event={current_event or 'message'}  keys={list(payload.keys())}")

                    # Heuristic: remember answer-ish payloads
                    if current_event in {"answer", "final", "eoh_answer"}:
                        last_data = payload

            print("-" * 80)
            if last_data:
                text = last_data.get("answer") or last_data.get("text") or str(last_data)
                print("Final answer excerpt:")
                print(text[:1200])
            else:
                print("No explicit final answer event captured; see event log above.")
    except Exception as e:
        print(f"ERROR running {case['id']}: {e}", file=sys.stderr)


async def main() -> None:
    async with httpx.AsyncClient() as client:
        for case in TEST_CASES:
            await run_single_test(client, case)


if __name__ == "__main__":
    asyncio.run(main())
