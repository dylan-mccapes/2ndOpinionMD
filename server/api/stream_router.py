# server/api/stream_router.py

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set

from openai import OpenAI

from .stream_config import CHAT_MODEL, CODING_SOURCES, GUIDELINE_SOURCES

client = OpenAI()


@dataclass
class CodingRouterPlan:
    """
    Plan returned by the coding-source router LLM.

    - task_type: always "coding" for now, but kept for future extension.
    - selected_sources: the subset of candidate sources we should actually hit.
    - reasoning: short natural-language justification for observability/SSE.
    - raw_router: raw JSON from the LLM (for future debugging if needed).
    """

    task_type: str = "coding"
    selected_sources: Set[str] = field(default_factory=set)
    reasoning: str = ""
    raw_router: Dict[str, Any] | None = None


async def route_coding_sources(
    q: str,
    code_terms: List[str],
    candidate_sources: List[str],
) -> CodingRouterPlan:
    """
    Decide which datasets (rag_corpus.source keys) to query for a coding task.

    - q: natural-language coding question
    - code_terms: terms extracted by extract_code_terms(q)
    - candidate_sources: upper bound (usually the ?sources= list or
      CODING_DEFAULT_SOURCES). The router may only select a subset of these.

    Returns a CodingRouterPlan. If anything goes wrong, we fall back to:
      - selected_sources = set(candidate_sources)
    """
    # Partition candidate sources into rough semantic groups using config.
    candidate_sources = list(dict.fromkeys(s.strip() for s in candidate_sources if s.strip()))

    code_candidates = [s for s in candidate_sources if s in CODING_SOURCES]
    guideline_candidates = [s for s in candidate_sources if s in GUIDELINE_SOURCES]
    other_candidates = [
        s
        for s in candidate_sources
        if s not in code_candidates and s not in guideline_candidates
    ]

    system = (
        "You are a routing assistant for a medical coding retrieval system.\n"
        "Your job is to decide which internal datasets (sources) should be queried "
        "to answer the user's coding question.\n\n"
        "You are given:\n"
        "- The user's natural-language question.\n"
        "- A list of extracted code-related terms.\n"
        "- A list of candidate dataset keys (candidate_sources).\n"
        "- Which of those are code vocabularies vs guideline vs other.\n\n"
        "Goal:\n"
        "- Choose a *subset* of candidate_sources that should actually be queried.\n"
        "- Keep the context lean and focused, but do not omit clearly relevant "
        "  code vocabularies.\n\n"
        "Important rules:\n"
        "- You MUST ONLY select sources that appear in candidate_sources.\n"
        "- If the user explicitly mentions a vocabulary by name (e.g. 'ICD-10', "
        "  'ICD-10-CM', 'ICD-11', 'SNOMED', 'LOINC', 'RxNorm'), you MUST include "
        "  the corresponding dataset if it is present in candidate_sources.\n"
        "- For typical coding/abstraction questions that ask for diagnosis, "
        "  procedures, labs, and medications, you will usually want to keep the "
        "  main code vocabularies (ICD-10-CM, ICD-11, SNOMED, LOINC, RxNorm) "
        "  when they exist in candidate_sources.\n"
        "- Only include guideline sources when the question clearly requires "
        "  guideline interpretation for coding, or when the question explicitly "
        "  references specific guidelines.\n"
        "- When in doubt between including or excluding a code vocabulary, "
        "  prefer including it. When in doubt for guidelines or 'other' sources, "
        "  prefer excluding them to keep the context smaller.\n\n"
        "Output format (MUST be valid JSON):\n"
        "{\n"
        '  \"task_type\": \"coding\",\n'
        '  \"selected_sources\": [\"source_key1\", \"source_key2\", ...],\n'
        '  \"reasoning\": \"short explanation of why these sources were chosen\"\n'
        "}\n"
    )

    user_payload = {
        "question": q,
        "extracted_terms": code_terms,
        "candidate_sources": candidate_sources,
        "code_candidates": code_candidates,
        "guideline_candidates": guideline_candidates,
        "other_candidates": other_candidates,
    }

    try:
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": json.dumps(user_payload, ensure_ascii=False),
                },
            ],
        )
    except Exception:
        # Fail-safe: select everything if the router call itself fails.
        return CodingRouterPlan(
            task_type="coding",
            selected_sources=set(candidate_sources),
            reasoning="Router call failed; using all candidate_sources.",
            raw_router=None,
        )

    content = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except Exception:
        # Also fail-safe: select everything if parsing fails.
        return CodingRouterPlan(
            task_type="coding",
            selected_sources=set(candidate_sources),
            reasoning="Router JSON parse failed; using all candidate_sources.",
            raw_router={"raw": content},
        )

    task_type = data.get("task_type") or "coding"
    selected_sources_raw = data.get("selected_sources") or []
    if not isinstance(selected_sources_raw, list):
        selected_sources_raw = []

    # Only allow sources that are actually in candidate_sources.
    allowed_set = set(candidate_sources)
    selected_sources: Set[str] = set(
        s for s in selected_sources_raw if isinstance(s, str) and s in allowed_set
    )

    # Safety net: if the router returns nothing, fall back to all candidates.
    if not selected_sources:
        selected_sources = allowed_set
        reasoning = (
            data.get("reasoning")
            or "Router returned no sources; defaulted to all candidate_sources."
        )
    else:
        reasoning = data.get("reasoning") or ""

    return CodingRouterPlan(
        task_type=str(task_type),
        selected_sources=selected_sources,
        reasoning=reasoning,
        raw_router=data,
    )
