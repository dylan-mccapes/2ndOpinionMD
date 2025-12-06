"""
server/tests/run_eoh_synthetic_timeline_queries.py

Utility script to fire the 10 synthetic EoH + timeline test queries
against /api/rag/eoh_stream and save the raw SSE output for grading.

Usage (from repo root):

    python -m server.tests.run_eoh_synthetic_timeline_queries

Optional:

    EOH_BASE_URL="https://2ndopinionmd.ai" python -m server.tests.run_eoh_synthetic_timeline_queries
"""

import os
import pathlib
import subprocess
from typing import Dict, List

# ---------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------

BASE_URL = os.getenv("EOH_BASE_URL", "http://localhost:8000").rstrip("/")

# Directory to store raw outputs for manual review
OUTPUT_DIR = pathlib.Path(__file__).parent / "eoh_synthetic_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Ten synthetic patients from SCGP timelines
# (Queries are intentionally descriptive so you, Nate, and Andras can
#  quickly eyeball flare / diagnostic reasoning when you read outputs.)
TEST_CASES: List[Dict[str, str]] = [
    {
        "name": "scgp_ra_001",
        "patient_id": "SCGP_RA_001",
        "q": (
            "For synthetic patient SCGP_RA_001, summarize the rheumatoid arthritis "
            "course using the EoH stacks / stability band framework, describe recent "
            "flare dynamics, and discuss what monitoring or treatment adjustments "
            "might be appropriate conceptually."
        ),
        "sources": "eoh_2025,acr_ra_2021,eular_ra_2022,acr_ild_2023",
    },
    {
        "name": "scgp_ra_fibro_001",
        "patient_id": "SCGP_RA_FIBRO_001",
        "q": (
            "For synthetic patient SCGP_RA_FIBRO_001, use the EoH framework to explain "
            "how RA inflammation appears vs. fibromyalgia amplification, how the "
            "timeline separates inflammatory control from persistent pain, and what "
            "this implies for flare prediction and diagnostic framing."
        ),
        "sources": "eoh_2025,acr_ra_2021,eular_ra_2022,va_guidelines",
    },
    {
        "name": "scgp_sle_001",
        "patient_id": "SCGP_SLE_001",
        "q": (
            "For synthetic patient SCGP_SLE_001, interpret the lupus course including "
            "renal involvement using the EoH stacks / banding concept. Describe how "
            "flares and treatment responses show up in the timeline and what this "
            "means for future flare vigilance and organ protection."
        ),
        "sources": "eoh_2025,eular_sle_nephritis_2025,kdigo_gn_ln_2021,nice_ta397_belimumab",
    },
    {
        "name": "scgp_crohns_001",
        "patient_id": "SCGP_CROHNS_001",
        "q": (
            "For synthetic patient SCGP_CROHNS_001, use the timeline and EoH "
            "misdiagnosis logic to explain the IBS_to_Crohns pattern: what early "
            "signals should have triggered re-evaluation, how banding changes after "
            "true Crohn's treatment, and what this means for future flare risk."
        ),
        "sources": "eoh_2025,acg_crohns_2018,acg_uc_2019",
    },
    {
        "name": "scgp_uc_001",
        "patient_id": "SCGP_UC_001",
        "q": (
            "For synthetic patient SCGP_UC_001, describe the ulcerative colitis "
            "stability pattern using EoH bands: how induction, partial response, and "
            "maintenance appear across time and how this shapes expected flare risk "
            "and surveillance needs."
        ),
        "sources": "eoh_2025,acg_uc_2019,acg_crohns_2018",
    },
    {
        "name": "scgp_asthma_001",
        "patient_id": "SCGP_ASTHMA_001",
        "q": (
            "For synthetic patient SCGP_ASTHMA_001, interpret asthma control vs. "
            "exacerbations using EoH bands and the GOLD/EoH stack framing: how "
            "exacerbation precursors show up in the timeline and how the pipeline "
            "would conceptually forecast flare risk."
        ),
        "sources": "eoh_2025,gina_asthma_2023,ats_ers_severe_asthma_2020",
    },
    {
        "name": "scgp_hf_001",
        "patient_id": "SCGP_HF_001",
        "q": (
            "For synthetic patient SCGP_HF_001, use the timeline to describe heart "
            "failure stability vs. decompensation episodes within the EoH banding "
            "framework and how guideline-directed therapy changes would shift "
            "prognostic trajectory."
        ),
        "sources": "eoh_2025,acc_aha_hfsa_hf_2022,nice",
    },
    {
        "name": "scgp_ms_001",
        "patient_id": "SCGP_MS_001",
        "q": (
            "For synthetic patient SCGP_MS_001, interpret relapses, remission periods, "
            "and treatment changes within the EoH stacks / stability bands concept and "
            "explain how the pipeline would reason about flare risk and disability "
            "trajectory at a high level."
        ),
        "sources": "eoh_2025,va_guidelines",
    },
    {
        "name": "scgp_t1dm_001",
        "patient_id": "SCGP_T1DM_001",
        "q": (
            "For synthetic patient SCGP_T1DM_001, use the timeline to reason about "
            "glycemic stability, hypoglycemia risk, and cardio-renal complications "
            "within the EoH framework, referencing diabetes and CKD guideline themes "
            "from context when present."
        ),
        "sources": "eoh_2025,ada_dm_2024,kdigo_diabetes_ckd_2020",
    },
    {
        "name": "scgp_as_001",
        "patient_id": "SCGP_AS_001",
        "q": (
            "For synthetic patient SCGP_AS_001 (axial spondyloarthritis), describe how "
            "EoH would interpret inflammatory back pain, treatment escalation, and "
            "residual symptoms over time, and what that implies for flare vigilance "
            "and diagnostic certainty."
        ),
        "sources": "eoh_2025,eular_axspa_2022,va_guidelines",
    },
]


def build_curl_args(test: Dict[str, str]) -> List[str]:
    """
    Build a curl command (as argv list) for a single test case.
    We use --get + --data-urlencode to mirror your usual workflow.
    """
    params = {
        "q": test["q"],
        "limit": "12",
        "ctx_k": "24",
        "with_llm": "1",
        "use_valyu": "0",
        "use_timeline": "1",
        "timeline_patient_id": test["patient_id"],
        "sources": test["sources"],
    }

    args: List[str] = [
        "curl",
        "-sS",          # quiet errors, but show stderr on failure
        "-N",           # no buffering for SSE, though we capture at once
        f"{BASE_URL}/api/rag/eoh_stream",
        "--get",
    ]

    for key, value in params.items():
        args.extend(["--data-urlencode", f"{key}={value}"])

    return args


def run_single_test(idx: int, test: Dict[str, str]) -> None:
    name = test["name"]
    patient_id = test["patient_id"]

    print(f"\n[{idx+1:02d}/10] Running EoH timeline test for {patient_id} ({name})...")
    args = build_curl_args(test)

    result = subprocess.run(args, capture_output=True, text=True)

    out_path = OUTPUT_DIR / f"{idx+1:02d}_{name}.txt"
    out_path.write_text(result.stdout, encoding="utf-8")

    if result.returncode != 0:
        err_path = OUTPUT_DIR / f"{idx+1:02d}_{name}.err.txt"
        err_path.write_text(result.stderr, encoding="utf-8")
        print(f"  -> FAILED (rc={result.returncode}), see {err_path}")
    else:
        print(f"  -> OK, wrote SSE stream to {out_path}")


def main() -> None:
    print(f"EOH_BASE_URL = {BASE_URL}")
    print(f"Output directory: {OUTPUT_DIR}")
    for i, test in enumerate(TEST_CASES):
        run_single_test(i, test)


if __name__ == "__main__":
    main()
