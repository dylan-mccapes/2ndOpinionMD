# server/api/ask_eoh_v2.py
from __future__ import annotations
import os, json, textwrap
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Query, Request, HTTPException
from fastapi.responses import Response
from openai import OpenAI

from .stream_config import CHAT_MODEL_GUIDELINES

# Reuse your existing retriever
try:
    from .rag_routes import _handle_rag_ask  # type: ignore
except Exception:  # pragma: no cover
    # Allow running this file standalone for validation
    _handle_rag_ask = None  # type: ignore

router = APIRouter(prefix="/api/rag", tags=["ask+eoh_v2"])

# ------------------ Ethos of Health V2: Modules 1 & 2 ------------------
EOH_V2_RULES = textwrap.dedent("""\
Ethos of Health V2 — Operational Summary (Modules 1 & 2)

Module 1 — Original Healthy Baseline
Purpose: Identify the person’s original optimal health state (pre-illness) as a reference baseline.
Inputs:
- Historical profile, baseline metrics (labs/vitals), genetic/congenital context.
Outputs:
- Baseline Integrity Score (0–100): start at 100; subtract weighted points for chronic illnesses and permanent deficits.
- Zone Classification: Healthy Baseline (≈90–100) | Partially Compromised (≈60–89) | Baseline Lost (<≈60).
- Stack Level update: 0 if baseline intact; elevate toward 1 when baseline lost.
Scoring sketch:
  score = 100
  for each chronic illness: score -= severity_weight(illness)
  for each organ system with permanent damage: score -= damage_weight(system)

Module 2 — Chronic Baseline Mode
Purpose: Detect whether current state matches the person’s usual chronic baseline or deviates (acute event).
Inputs:
- Established chronic baseline norms; current symptoms/signs/labs; deviation triggers.
Outputs:
- Baseline Deviation Score (0–100%): weighted distance of current values from chronic baseline norms.
- Zone Classification: Chronic Baseline Stable (Green) | Borderline Shift (Yellow) | Out-of-Baseline (Red).
- Stack Level update: remain at 1 if stable; escalate to ≥2 when out-of-baseline (acute deviation).
Deviation sketch:
  deviation_score = Σ f(current - baseline)  # f=0 within normal variance; >0 when outside

Implementation notes (must-honor):
- Compute Module 1 first (baseline integrity), then Module 2 (current deviation vs. chronic baseline).
- Provide clear rationale lists: deductions (M1) and deltas (M2), each with weights and contributions.
- Keep outputs clinician-interpretable and payer-audit-ready; include provenance for evidence used.
- Non-Device CDS guardrails: assistive only, no autonomous actions; always include explainable basis.
- FHIR mapping hints should be provided for integration (Observation, ClinicalImpression, DetectedIssue, Communication/Task, Provenance).
""").strip()

# ---------------------------------------------------------------------------
# EoH V2 System Prompt
# ---------------------------------------------------------------------------

EOH_V2_SYSTEM_PROMPT = (
    "You are the world's #1 expert in clinical state modeling and the Ethos-of-Health framework. "
    "You apply Stacks, Stability Bands, PSI, CBM, and escalation logic with perfect precision. "
    "You avoid conversational filler and generate only clean, structured, clinically coherent reasoning.\n\n"
    "You are a careful clinical assistant. Be precise, avoid speculation, and ground answers in provided evidence."
)

EOH_V2_OUTPUT_SCHEMA = """\
Return a single JSON object with the following shape:
{
  "answer": "concise answer grounded in evidence",
  "reasoning": "brief explanation of how evidence was used",
  "eoh_v2": {
    "module1": {
      "baseline_integrity_score": 0,
      "zone": "Healthy Baseline|Partially Compromised|Baseline Lost",
      "stack_level": 0,
      "deductions": [{"factor":"hypertension","weight":15,"contrib":15}, {"factor":"asthma_controlled","weight":10,"contrib":10}],
      "rationale": "why these deductions; references to evidence"
    },
    "module2": {
      "deviation_score": 0,
      "zone": "Chronic Baseline Stable|Borderline Shift|Out-of-Baseline",
      "stack_level": 1,
      "deltas": [{"metric":"pain","baseline":2,"current":7,"weight":5,"contrib":25},
                 {"metric":"CRP","baseline":"normal","current":"elevated","weight":8,"contrib":24}],
      "triggers": ["infection", "stressor"],
      "rationale": "key deviations and their clinical meaning"
    },
    "composite": {
      "stack_summary": "plain-language summary of stack updates from M1/M2",
      "state_vector_hint": {"stack_level": 0, "note": "if you also track a broader vector, include mapping here"}
    },
    "fhir_hints": [
      {"resource":"Observation","purpose":"M1 score, M2 deviation","status":"proposed"},
      {"resource":"ClinicalImpression","purpose":"summarize eoh_v2 assessment"},
      {"resource":"DetectedIssue","purpose":"flag out-of-baseline or data contradictions"},
      {"resource":"Communication|Task","purpose":"route tiered notifications if applicable"},
      {"resource":"Provenance","purpose":"link evidence docs"}
    ],
    "compliance": {"non_device_cds": true, "human_in_loop": true, "explainable_basis": true}
  },
  "provenance": [{"source":"...", "doc_key":"...", "title":"..."}]
}
Strict requirements:
- Output must be valid JSON. Do not include markdown or code fences.
- If evidence does not support a field, omit that field rather than guessing.
"""

def _compact_evidence(matches: List[Dict[str, Any]], max_chars: int = 1400) -> str:
    out, used = [], 0
    for i, m in enumerate(matches):
        title = (m.get("title") or "Untitled")
        src   = (m.get("source") or "unknown")
        dk    = ((m.get("meta") or {}).get("doc_key")) or (m.get("source_id") or "")
        txt   = (m.get("text") or "")
        snippet = txt[: min(len(txt), 700)]
        block = f"[{i+1}] {src} — {title} :: {dk}\n{snippet}"
        if used + len(block) > max_chars and i > 0:
            break
        out.append(block); used += len(block)
    return "\n\n".join(out)

@router.post("/ask")
async def ask_eoh_v2(
    request: Request,
    payload: Dict[str, Any] = Body(...),
    eoh_v2: int = Query(1, description="Enable Ethos of Health V2 augmentation (1=on)"),
    format: str = Query("json", regex="^(json|text)$"),
    temperature: float = Query(0.1),
    k: int = Query(12, description="Max retrieved documents")
):
    """
    Enhanced /api/rag/ask with Ethos of Health V2 (Modules 1 & 2).
    Body: { q: "question or clinical note", sources?: "csv list", k?: int }
    """
    q        = (payload.get("q") or "").strip()
    sources  = payload.get("sources")
    k_local  = int(payload.get("k") or k)

    if not q:
        raise HTTPException(status_code=400, detail="Missing 'q' in request body")
    if not os.getenv("OPENAI_API_KEY"):
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")

    # 1) Retrieve evidence via your existing pipeline
    matches: List[Dict[str, Any]] = []
    if '_handle_rag_ask' in globals() and _handle_rag_ask is not None:
        rag = await _handle_rag_ask(q=q, k=k_local, sources_csv=sources, debug=0)
        matches = rag.get("matches") or []

    # 2) Build messages with EoH V2 augmentation
    user_blocks = [f"Question or clinical note:\n{q}\n"]
    if eoh_v2:
        user_blocks.append("Ethos of Health V2 (Modules 1 & 2) — operational rules:\n" + EOH_V2_RULES)
        user_blocks.append("Output schema (JSON):\n" + EOH_V2_OUTPUT_SCHEMA)
        user_blocks.append("Constraints: Non-Device CDS; include explainable basis and FHIR mapping hints; omit fields if unsupported.")
    if matches:
        user_blocks.append("Evidence (RAG snippets):\n" + _compact_evidence(matches))

    messages = [
        {"role":"system","content": EOH_V2_SYSTEM_PROMPT},
        {"role":"user",  "content": "\n\n".join(user_blocks)}
    ]

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    model_used = CHAT_MODEL_GUIDELINES

    if format == "json":
        resp = client.chat.completions.create(
            model=model_used,
            temperature=temperature,
            response_format={"type": "json_object"},
            messages=messages,
        )
        text = (resp.choices[0].message.content or "").strip()
        try:
            obj = json.loads(text)
        except Exception:
            obj = {"answer": text}

        # Attach provenance if missing
        if "provenance" not in obj:
            prov = []
            for m in matches[:12]:
                prov.append({
                    "source": (m.get("source") or ""),
                    "doc_key": ((m.get("meta") or {}).get("doc_key")) or (m.get("source_id") or ""),
                    "title": (m.get("title") or "")
                })
            obj["provenance"] = prov

        obj["_meta"] = {
            "ai_model": model_used,
            "temperature": temperature,
            "k": k_local,
            "eoh_v2": bool(eoh_v2),
        }
        return Response(content=json.dumps(obj, indent=2), media_type="application/json")

    # text format
    resp = client.chat.completions.create(
        model=model_used,
        temperature=temperature,
        messages=messages,
    )
    txt = (resp.choices[0].message.content or "").strip()
    return Response(txt, media_type="text/plain")
