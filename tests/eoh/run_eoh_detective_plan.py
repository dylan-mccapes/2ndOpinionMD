# server/scripts/run_eoh_detective_plan.py

import argparse
import textwrap
import httpx
import sys
from typing import List, Dict, Any


DETECTIVE_PLAN: Dict[str, Any] = {
    "focus": "mimic_mystery_probe",
    "steps": [
        {
            "step_id": "A1",
            "kind": "terrain_risk",
            "q": textwrap.dedent("""
                Using this patient's entire MIMIC-4 timeline, summarize their major clinical arcs
                and current Ethos-of-Health terrain. What were the main inflection points
                (new diagnoses, major complications, ICU transfers, surgeries, code events),
                and what are the 3–5 dominant problems now? Please ground the answer in the timeline,
                including approximate dates and key labs/vitals/events.
            """).strip(),
        },
        {
            "step_id": "B1",
            "kind": "renal_fluid",
            "q": textwrap.dedent("""
                Focusing on kidney function and fluid balance, describe the pattern of creatinine,
                urine output, diuretics, fluid resuscitation, and dialysis. Are there any episodes
                of acute kidney injury where the timing or recovery seems atypical for the presumed
                cause (e.g., HRS vs sepsis vs intrinsic renal)? Highlight candidate “mystery” episodes.
            """).strip(),
        },
        {
            "step_id": "B2",
            "kind": "infection_vs_noninfectious",
            "q": textwrap.dedent("""
                Using cultures, antibiotics, fever curves, WBC, and organ dysfunction patterns,
                outline this patient's infectious vs non-infectious episodes. Are there periods
                where the chart suggests “sepsis” but the timeline evidence (cultures, response
                to antibiotics, hemodynamics) is weak or contradictory? Flag at least one candidate
                episode where the diagnosis might be questionable.
            """).strip(),
        },
        {
            "step_id": "C1",
            "kind": "internal_contradictions",
            "q": textwrap.dedent("""
                Looking across this patient's timeline, identify 3–5 internal contradictions
                or unexplained patterns. Examples: diagnosis labels that don’t match labs or
                vitals, therapies that seem out of proportion to the documented diagnosis,
                sudden recoveries or deteriorations that don’t have an obvious trigger,
                or guideline discordance. For each, briefly explain why it looks like a
                potential “mystery” worth deeper investigation.
            """).strip(),
        },
        {
            "step_id": "C2",
            "kind": "guideline_discordance",
            "q": textwrap.dedent("""
                Compare this patient's management against the major ICU and specialty guidelines
                that appear relevant (e.g., KDIGO AKI, Sepsis guidelines, cardiology or hepatology
                guidelines depending on the case). Identify 2–3 places where the actual treatment
                path diverges from guideline-based expectations in a non-trivial way.
                These divergences are candidate “mysteries”; explain them.
            """).strip(),
        },
    ],
}


async def run_step(
    client: httpx.AsyncClient,
    base_url: str,
    patient_id: str,
    step: Dict[str, Any],
):
    q = step["q"]
    step_id = step["step_id"]
    print(f"\n\n=== DETECTIVE STEP {step_id} ({step['kind']}) ===\n", file=sys.stderr)
    print(f"Q: {q}\n", file=sys.stderr)

    params = {
        "q": q,
        "timeline_patient_id": patient_id,
        "valyu_raw": "1",
        "debug": "1",
        # you can pass additional flags if you want:
        # "with_llm": "1", "use_valyu": "1", "research": "1", ...
    }

    url = f"{base_url.rstrip('/')}/api/rag/eoh_stream"
    try:
        async with client.stream("GET", url, params=params, timeout=None) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                # For now just stream the raw SSE out; you can parse if desired.
                if line:
                    print(line)
    except httpx.ConnectError as e:
        print(
            f"\nERROR: Could not connect to {base_url}\n"
            f"Make sure the server is running. You can start it with:\n"
            f"  cd server && uvicorn api.app_postgres:app --reload --port 8000\n",
            file=sys.stderr,
        )
        raise


async def main_async(args):
    async with httpx.AsyncClient() as client:
        for step in DETECTIVE_PLAN["steps"]:
            await run_step(client, args.base_url, args.patient_id, step)


def main():
    parser = argparse.ArgumentParser(description="Run a fixed EoH detective plan against a MIMIC patient.")
    parser.add_argument(
        "--patient-id",
        required=True,
        help="Patient id, e.g. MIMIC4_10000032",
    )
    parser.add_argument(
        "--base-url",
        default="http://localhost:8000",
        help="Base URL of the 2ndOpinionMD API (default: http://localhost:8000)",
    )
    args = parser.parse_args()

    import asyncio
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
