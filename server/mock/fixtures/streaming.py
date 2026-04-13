"""SSE event generators for mock streaming endpoints."""
from __future__ import annotations

import asyncio
import json
from typing import AsyncIterator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _chunks(text: str, size: int = 10):
    for i in range(0, len(text), size):
        yield text[i : i + size]


# ---------------------------------------------------------------------------
# Canned answers
# ---------------------------------------------------------------------------

ASK_ANSWER = """\
Based on the available clinical evidence, Norman presents with a complex \
multi-system picture consistent with longstanding autoimmune activity.

**Key findings:**
- Elevated Hgb A1c (6.2%) indicating borderline metabolic control
- Pattern of joint involvement with morning stiffness
- Prior ANA positivity in the record

**Assessment:** The evidence supports a moderate-to-high inflammatory burden. \
There is no single pathognomonic finding, but the constellation of lab trends \
and symptom chronology warrants rheumatologic re-evaluation within 4–6 weeks.

*This is a read-only clinical summary. No diagnosis is being made.*\
"""

EOH_ANSWER = """\
**EoH Reasoning — Type A (Flare Risk)**

Using the Core Terrain Model (M1–M3):

- **Stack Level:** 2 — two confirmed chronic conditions active
- **Stability Band:** 3 — moderate instability, rising flare risk
- **Baseline Deviation:** Yellow Zone — shifting from CBM

**M13 Flare Trajectory:**
Probability of acute flare within 30 days: **61%** (moderate-high).
Trajectory is upward over the preceding 90-day window based on \
lab trend and symptom escalation pattern.

**M68 ICM — Inflammatory Capacity:**
Inflow valve load elevated; outflow clearance marginally reduced. \
Estimated allostatic headroom: 22% of ICmax.

**Drivers (M14):**
1. Metabolic load (A1c drift)
2. Sleep disruption pattern (journal entries)
3. Prior NSAID course — possible rebound effect

**Recommended next steps:**
- Re-check inflammatory panel (CRP, ESR) within 2 weeks
- Review current suppression channel via M9 audit
- EWA: gentle nervous-system regulation, anti-inflammatory diet trial (M66)

*EoH output — not a diagnosis. Clinician review required.*\
"""

ANSWERS = {
    "ask": ASK_ANSWER,
    "eoh": EOH_ANSWER,
}


# ---------------------------------------------------------------------------
# Generator
# ---------------------------------------------------------------------------

async def mock_sse_stream(mode: str = "ask") -> AsyncIterator[str]:
    answer = ANSWERS.get(mode, ASK_ANSWER)

    yield sse("phase_start", {"phase": "retrieval"})
    await asyncio.sleep(0.25)

    yield sse("retrieval_summary", {
        "sources_considered": 14,
        "sources_used": 9,
        "confidence": "high",
    })
    await asyncio.sleep(0.2)

    yield sse("reasoning_progress", {
        "step": "Applying EoH M13 flare trajectory analysis..."
    })
    await asyncio.sleep(0.35)

    yield sse("reasoning_progress", {
        "step": "Cross-referencing M68 inflammatory capacity model..."
    })
    await asyncio.sleep(0.3)

    for chunk in _chunks(answer, size=14):
        yield sse("llm_chunk", {"content": chunk})
        await asyncio.sleep(0.025)

    yield sse("llm_done", {
        "text": answer,
        "confidence": 0.82,
        "limitations": [
            "Mock response — not connected to live inference",
            "No real retrieval performed",
        ],
    })
    await asyncio.sleep(0.1)

    yield sse("completion", {
        "tokens_used": len(answer) // 4,
        "duration_ms": 1340,
    })
