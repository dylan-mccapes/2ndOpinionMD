# server/api/eoh_gap_retrieval.py

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

EOH_GAP_RETRIEVAL_SYSTEM_PROMPT = """
You are an EoH gap-retrieval planner for 2ndOpinionMD.

Your inputs (JSON):
{
  "question": "...",
  "router_plan": { ... },        // EoH router output (modules, handles, question_type)
  "context": [
    {
      "id": "string",
      "source": "string",
      "title": "string",
      "snippet": "short text snippet"
    },
    ...
  ],
  "known_sources": ["acr_ra_2021", "eular_ra_2022", "ethos_model", "mimic4_note", ...],
  "max_slots": 6
}

Your job:
- Look at the question, router_plan, and current context.
- Decide if the fused context is missing any *high-yield* pieces:
  - guideline subsections or pages (e.g. RA pregnancy, RA-ILD, sepsis bundles),
  - EoH / Ethos modules or documents,
  - timeline slices (e.g. earlier flare cluster, more recent labs),
  - ICU case analogs (MIMIC-4 notes) if clearly helpful,
  - or other specific internal sources.

If you think the existing context is already sufficient, set "needs_gap_retrieval": false
and return an empty "slots" list.

If more context is needed, propose a SMALL set (<= max_slots) of GAP SLOTS describing
targeted retrievals the system should run.

Each slot MUST be specific and practical, using ONLY the provided known_sources list
for "suggested_sources".

Output JSON schema (MANDATORY):

{
  "needs_gap_retrieval": true | false,
  "reason": "short explanation",
  "slots": [
    {
      "slot_id": "short-stable-identifier",
      "kind": "guideline" | "eoh_module" | "timeline" | "case_analog" | "other",
      "priority": "high" | "medium" | "low",
      "suggested_sources": ["acr_ra_2021", "eular_ra_2022"],
      "terms": ["pregnancy", "csDMARD"],
      "limit": 1
    }
  ]
}

Interpretation of kinds:

- "guideline": ask for specific pages/snippets from guideline sources (ACR, EULAR, KDIGO, NICE, etc.).
- "eoh_module": ask for EoH/Ethos docs (ethos_model, eoh_docs, etc.).
- "timeline": ask for narrower timeline slices (e.g. earlier flares vs recent).
- "case_analog": ask for MIMIC-4 / ICU analog notes (typically "mimic4_note").
- "other": anything else that is clearly helpful and mappable onto known_sources.

Rules:
- Prefer 0–3 HIGH priority slots; avoid noise.
- suggested_sources MUST be a subset of known_sources. If unsure, leave it empty.
- terms should be short keyword phrases that a text/ANN search could use.
- limit should be small (1–4) – we only want the sharpest few hits.
- NEVER invent new source names; use only those in known_sources.
"""


def build_compact_context_for_gap(
    final_ctx: List[Dict[str, Any]],
    max_docs: int = 40,
    max_chars_per_doc: int = 800,
) -> List[Dict[str, str]]:
    """
    Compress final_ctx into a small list of documents for gap planning.
    """
    compact: List[Dict[str, str]] = []
    for d in final_ctx[:max_docs]:
        doc_id = str(d.get("id") or "").strip()
        if not doc_id:
            continue
        compact.append(
            {
                "id": doc_id,
                "source": str(d.get("source") or ""),
                "title": (d.get("title") or "")[:200],
                "snippet": (d.get("text") or "")[:max_chars_per_doc],
            }
        )
    return compact


def build_eoh_gap_retrieval_payload(
    *,
    question: str,
    router_plan: Dict[str, Any],
    final_ctx: List[Dict[str, Any]],
    max_slots: int = 6,
) -> Dict[str, Any]:
    """
    Build the JSON payload that will be sent to the LLM gap-retrieval planner.

    This function does NOT call the LLM; it just prepares the payload.
    """
    compact_context = build_compact_context_for_gap(final_ctx)
    known_sources = sorted(
        {str(d.get("source") or "") for d in final_ctx if d.get("source")}
    )

    payload = {
        "question": question,
        "router_plan": router_plan,
        "context": compact_context,
        "known_sources": known_sources,
        "max_slots": max_slots,
    }

    return payload
