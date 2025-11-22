# server/api/stream_router.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .stream_config import CHAT_MODEL

client = OpenAI()


@dataclass
class CodingRouterPlan:
    task_type: str                 # e.g. "guideline_qa", "coding", "mixed"
    selected_sources: List[str]    # subset of candidate_sources
    reasoning: str                 # short natural language explanation


async def route_coding_sources(
    q: str,
    code_terms: List[str],
    candidate_sources: List[str],
    valyu_context: Optional[List[Dict[str, Any]]] = None,
) -> CodingRouterPlan:
    """
    Single-pass router used for both coding and non-coding modes.

    - q: clinical question
    - code_terms: extracted coding terms (may be empty in non-coding mode)
    - candidate_sources: all DB sources we *could* hit
    - valyu_context: optional list of early Valyu hits (titles/snippets)
      used to bias guidelines toward the evidence signal (non-coding only).
    """
    # Build a compact description of candidate sources
    src_lines = [f"- {s}" for s in sorted(candidate_sources)]

    # Optional Valyu summary for the router prompt
    valyu_lines: List[str] = []
    if valyu_context:
        valyu_lines.append("External Valyu evidence snippets:")
        for i, r in enumerate(valyu_context[:8], start=1):
            title = (r.get("title") or "").strip()
            snippet = (r.get("text") or r.get("snippet") or "").strip()
            line = f"[VALYU-{i}] {title}" if title else f"[VALYU-{i}]"
            if snippet:
                line += f" — {snippet[:240]}"
            valyu_lines.append(line)

        valyu_lines.append(
            "Use these Valyu snippets only as a signal of which guideline "
            "or internal sources are likely relevant. Do NOT hallucinate "
            "new source names."
        )

    code_term_lines: List[str] = []
    if code_terms:
        code_term_lines.append("Extracted coding-related terms:")
        for t in code_terms[:24]:
            code_term_lines.append(f"- {t}")

    system_content = (
        "You are a routing controller for 2ndOpinionMD's medical RAG system.\n"
        "Your job is to choose which internal sources to query for this question.\n\n"
        "You MUST return STRICT JSON with keys:\n"
        "  - task_type: string (e.g., 'guideline_qa', 'coding', 'mixed')\n"
        "  - selected_sources: list of source names from the candidate list\n"
        "  - reasoning: short explanation of your choices\n\n"
        "Rules:\n"
        "- Always choose at least one source, unless there is a clear error.\n"
        "- Prefer focused subsets over 'everything'.\n"
        "- If the question is clearly about codes only, prioritize coding sources.\n"
        "- If the question is guideline-heavy (treatment algorithms, stepwise therapy, "
        "  risk stratification), prioritize guideline sources.\n"
        "- If Valyu evidence is present, use it to bias towards the most relevant "
        "  guideline or internal corpora, but do NOT invent sources.\n"
    )

    user_chunks: List[str] = [
        "Clinical question:",
        q.strip(),
        "",
        "Candidate internal sources:",
        *src_lines,
    ]
    if code_term_lines:
        user_chunks.append("")
        user_chunks.extend(code_term_lines)
    if valyu_lines:
        user_chunks.append("")
        user_chunks.extend(valyu_lines)

    user_chunks.append("")
    user_chunks.append(
        "Return ONLY JSON of the form:\n"
        "{\n"
        '  \"task_type\": \"...\",\n'
        '  \"selected_sources\": [\"source1\", \"source2\", ...],\n'
        '  \"reasoning\": \"...\"\n'
        "}\n"
    )

    messages = [
        {"role": "system", "content": system_content},
        {"role": "user", "content": "\n".join(user_chunks)},
    ]

    try:
        completion = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        # On router failure, fall back to all sources
        return CodingRouterPlan(
            task_type="fallback_all_sources",
            selected_sources=list(candidate_sources),
            reasoning=f"router_failed: {e}",
        )

    content = completion.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except Exception as e:
        return CodingRouterPlan(
            task_type="fallback_all_sources",
            selected_sources=list(candidate_sources),
            reasoning=f"router_json_parse_failed: {e}",
        )

    task_type = str(data.get("task_type") or "unknown")
    selected = data.get("selected_sources") or []
    reasoning = str(data.get("reasoning") or "").strip()

    # Sanitize selected_sources to be a subset of candidate_sources
    cand_set = set(candidate_sources)
    cleaned: List[str] = []
    if isinstance(selected, list):
        for s in selected:
            if not isinstance(s, str):
                continue
            s_clean = s.strip()
            if s_clean and s_clean in cand_set and s_clean not in cleaned:
                cleaned.append(s_clean)

    if not cleaned:
        cleaned = list(candidate_sources)

    return CodingRouterPlan(
        task_type=task_type,
        selected_sources=cleaned,
        reasoning=reasoning,
    )