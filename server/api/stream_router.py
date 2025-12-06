# server/api/stream_router.py

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI
import json

from .stream_config import CHAT_MODEL, CHAT_MODEL_UTIL, STRICT_CODE_SOURCES, is_strict_code_source, GUIDELINE_SOURCE_META

client = OpenAI()


# ---------------------------------------------------------------------------
# Router system prompts
# ---------------------------------------------------------------------------

RAG_ROUTER_SYSTEM_PROMPT = """
You are the 2ndOpinionMD routing brain for guideline Q&A and internal Ethos-of-Health reasoning.

You receive a JSON object with fields including:
- "question": the clinician's question.
- "guideline_catalog": a list of guideline metadata. Each entry has:
  - "source": the internal source id (matches rag_corpus.source).
  - "title": the guideline title.
  - "condition": the main condition or topic.
  - "domain": clinical domain (cardiology, rheumatology, nephrology, etc.).
  - "year": publication or last major update year (if available).
- "available_guideline_sources": list of guideline source ids that are eligible.

Your job:
1. Decide which guideline source ids are most relevant to the question.
   - Use "condition", "domain", "title", and "year" from guideline_catalog.
   - Prefer the most recent guideline when multiple cover the same condition.
   - Include multiple guidelines if the question explicitly asks for comparison
     (e.g., "ACR vs EULAR", "KDIGO vs ADA").
2. Optionally include internal EoH sources if the question is clearly about
   disease trajectories, flares, or shared decision-making beyond a single
   guideline.
3. Return STRICT JSON with this schema:

{
  "task_type": "guideline_only" | "guideline_plus_eoh" | "eoh_only" | "none",
  "selected_sources": ["acc_aha_hfsa_hf_2022", "kdigo_diabetes_ckd_2020"],
  "reasoning": "short explanation of routing choices for logging/debugging"
}

Constraints:
- Only choose guideline or EoH sources that appear in available_guideline_sources.
- If the question is not guideline-focused at all, you may set task_type="none"
  and return an empty selected_sources list, but explain why in "reasoning".
"""


@dataclass
class CodingRouterPlan:
    task_type: str
    selected_sources: List[str]
    reasoning: str


def _build_source_description_block(candidate_sources: List[str]) -> str:
    lines: List[str] = []
    for s in sorted(candidate_sources):
        meta = GUIDELINE_SOURCE_META.get(s)
        if not meta:
            lines.append(f"- {s}: (no structured metadata; generic internal corpus)")
            continue

        kind = meta.get("kind", "unknown")
        title = meta.get("title", "").strip()
        domain = meta.get("domain", "multi")
        condition = meta.get("condition", "multi")
        summary = meta.get("summary", "").strip()

        line = f"- {s}: [{kind}] {title}"
        if domain or condition:
            line += f" — domain={domain}, condition={condition}"
        if summary:
            line += f". {summary}"
        lines.append(line)

    return "\n".join(lines)


async def route_sources(
    q: str,
    code_terms: List[str],
    candidate_sources: List[str],
    valyu_context: Optional[List[Dict[str, Any]]] = None,
) -> CodingRouterPlan:
    # Build a compact description of candidate sources
    src_lines = [f"- {s}" for s in sorted(candidate_sources)]
    source_desc_block = _build_source_description_block(candidate_sources)

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

    user_chunks: List[str] = [
        "Clinical question:",
        q.strip(),
        "",
        "Candidate internal sources (raw IDs):",
        *src_lines,
        "",
        "Source descriptions:",
        source_desc_block,
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
        {"role": "system", "content": RAG_ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(user_chunks)},
    ]

    try:
        completion = client.chat.completions.create(
            model=CHAT_MODEL_UTIL,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
    except Exception as e:
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


# ---------------------------------------------------------------------------
# Coding-only router for /coding_stream
# ---------------------------------------------------------------------------

CODING_ROUTER_SYSTEM_PROMPT = """
You are the world's #1 medical vocabulary router and source-selection engine. You choose exactly the correct coding vocabularies based on the user's query, with perfect enforcement of user-specified constraints (e.g., "SNOMED only", "ICD only", "phenotype only"). You never allow leakage from disallowed vocabularies. You interpret intent flawlessly and compute the most clinically appropriate source mix.

You are a routing controller for 2ndOpinionMD's medical coding system.

Your job is to select which CODING VOCABULARY sources to query for this coding/abstraction request.

IMPORTANT: You can ONLY select from coding vocabulary sources:
- icd10cm: ICD-10-CM diagnosis codes
- icd11: ICD-11 diagnosis codes  
- snomed: SNOMED CT clinical terms
- loinc: LOINC laboratory codes
- rxnorm: RxNorm medication codes
- hpo: Human Phenotype Ontology terms
- chv: Consumer Health Vocabulary

You MUST return STRICT JSON with keys:
  - task_type: string (always "coding" for this router)
  - selected_sources: list of source names from the candidate list
  - reasoning: short explanation of your choices

Rules:
- Always choose at least one source.
- Select sources based on what the clinical question needs:
  - Diagnosis codes → icd10cm, icd11, snomed
  - Lab tests → loinc
  - Medications → rxnorm
  - Phenotypes/symptoms → hpo
  - Lay terms → chv
- If the question is broad, include multiple relevant vocabularies.
- NEVER include guideline sources, EHR sources, or any non-coding sources.
"""


async def route_coding_sources_strict(
    q: str,
    code_terms: List[str],
    candidate_sources: List[str],
) -> CodingRouterPlan:
    """
    Coding-only router for /coding_stream.
    
    This router ONLY considers strict coding vocabulary sources and filters out
    any non-coding sources (guidelines, EHR, etc.) before routing.
    
    Args:
        q: The clinical coding query
        code_terms: Extracted code-related terms from the query
        candidate_sources: List of candidate sources (will be filtered to coding-only)
    
    Returns:
        CodingRouterPlan with only coding vocabulary sources selected
    """
    # Filter to only strict code sources
    coding_only_candidates = [
        s for s in candidate_sources 
        if is_strict_code_source(s)
    ]
    
    # If no coding sources in candidates, use all strict code sources
    if not coding_only_candidates:
        coding_only_candidates = list(STRICT_CODE_SOURCES)
    
    # Build source descriptions for the LLM
    src_lines = [f"- {s}" for s in sorted(coding_only_candidates)]
    
    source_descriptions: List[str] = []
    for s in sorted(coding_only_candidates):
        meta = GUIDELINE_SOURCE_META.get(s)
        if meta:
            title = meta.get("title", "").strip()
            summary = meta.get("summary", "").strip()
            source_descriptions.append(f"- {s}: {title}. {summary}")
        else:
            # Provide default descriptions for coding sources
            default_descs = {
                "icd10cm": "ICD-10-CM diagnosis and procedure codes (US clinical modification)",
                "icd11": "ICD-11 diagnosis codes (WHO international classification)",
                "snomed": "SNOMED CT clinical terminology for diagnoses, findings, procedures",
                "loinc": "LOINC codes for laboratory tests and clinical measurements",
                "rxnorm": "RxNorm medication codes and drug terminology",
                "hpo": "Human Phenotype Ontology terms for clinical phenotypes",
                "chv": "Consumer Health Vocabulary for lay medical terms",
            }
            desc = default_descs.get(s, "Coding vocabulary source")
            source_descriptions.append(f"- {s}: {desc}")
    
    code_term_lines: List[str] = []
    if code_terms:
        code_term_lines.append("Extracted coding-related terms:")
        for t in code_terms[:24]:
            code_term_lines.append(f"- {t}")
    
    user_chunks: List[str] = [
        "Clinical coding / abstraction request:",
        q.strip(),
        "",
        "Available coding vocabulary sources:",
        *src_lines,
        "",
        "Source descriptions:",
        *source_descriptions,
    ]
    if code_term_lines:
        user_chunks.append("")
        user_chunks.extend(code_term_lines)
    
    user_chunks.append("")
    user_chunks.append(
        "Return ONLY JSON of the form:\n"
        "{\n"
        '  \"task_type\": \"coding\",\n'
        '  \"selected_sources\": [\"source1\", \"source2\", ...],\n'
        '  \"reasoning\": \"...\"\n'
        "}\n"
    )
    
    messages = [
        {"role": "system", "content": CODING_ROUTER_SYSTEM_PROMPT},
        {"role": "user", "content": "\n".join(user_chunks)},
    ]
    
    try:
        completion = client.chat.completions.create(
            model=CHAT_MODEL_UTIL,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        # On failure, return all coding sources
        return CodingRouterPlan(
            task_type="coding",
            selected_sources=coding_only_candidates,
            reasoning=f"router_failed: {e}",
        )
    
    content = completion.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except Exception as e:
        return CodingRouterPlan(
            task_type="coding",
            selected_sources=coding_only_candidates,
            reasoning=f"router_json_parse_failed: {e}",
        )
    
    task_type = str(data.get("task_type") or "coding")
    selected = data.get("selected_sources") or []
    reasoning = str(data.get("reasoning") or "").strip()
    
    # Filter selected sources to only include valid coding sources
    cand_set = set(coding_only_candidates)
    cleaned: List[str] = []
    if isinstance(selected, list):
        for s in selected:
            if not isinstance(s, str):
                continue
            s_clean = s.strip().lower()
            if s_clean and s_clean in cand_set and s_clean not in cleaned:
                cleaned.append(s_clean)
    
    # Ensure at least one source is selected
    if not cleaned:
        cleaned = coding_only_candidates
    
    return CodingRouterPlan(
        task_type=task_type,
        selected_sources=cleaned,
        reasoning=reasoning,
    )
