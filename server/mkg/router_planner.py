"""Reusable EoH source-router planner for MKG retrieval pipelines.

Extracted from ``server/scripts/eoh_source_router_harness.py`` so the same
planning logic can be invoked from any harness (e.g. the MKG dual-lane
retrieval harness) without code duplication.

Returns a normalized plan dict::

    {
      "question_type":       "A|B|C|D|E|OTHER",
      "semantic_query":      "legacy alias for mkg_semantic_query",
      "mkg_semantic_query":  "expanded ANN query for the EXTERNAL rag_corpus",
      "ptv_semantic_query":  "compact ANN query for the PATIENT timeline",
      "ts_query":            "compact lexical query (cross-source FTS fallback)",
      "ts_terms":            ["term1", "term2", ...],   # union of per-source ts_terms
      "selected_sources":[{"source": "...", "priority": 1, "why": "...",
                           "ts_terms": ["...", ...]}, ...],
      "selected_modules":[{"module_id": "M13", "priority": 1, "why": "..."}, ...],
      "notes":               "short routing notes",
      "raw_response":        "(only when parse fails) raw model text",
      "elapsed_sec":         1.234,
      "model":               "eoh-llama3.2-source-router"
    }
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional

from server.eoh.module_index import MODULE_INDEX
from server.mkg.llm_json_parse import force_json_dict
from server.mkg.portalnode_pilot_sources import pilot_source_descriptions


def _log(emoji: str, msg: str) -> None:
    print(f"{emoji} {msg}", file=sys.stderr, flush=True)


ROUTER_RETRY_COUNT = max(0, int(os.environ.get("ROUTER_RETRY_COUNT", "2")))

# Tokens useless for Postgres FTS / MKG ts lane — question glue, pronouns, and
# generic request words the model often echoes as "ts_terms" instead of drugs,
# ICD families, labs, or flare/PRO vocabulary.
_ROUTER_TS_STOPWORDS: frozenset = frozenset(
    {
        "with", "from", "that", "this", "these", "those", "have", "has", "had",
        "what", "which", "when", "where", "while", "whom", "whose", "why", "how",
        "does", "did", "doing", "done", "tell", "about", "please", "patient",
        "patients", "clinical", "search", "suggest", "for", "not", "but", "and",
        "the", "are", "was", "were", "been", "being", "our", "your", "their",
        "its", "they", "them", "you", "she", "her", "him", "his", "can", "could",
        "would", "should", "may", "might", "will", "shall", "must", "into", "onto",
        "over", "under", "than", "then", "there", "here", "such", "same", "other",
        "another", "each", "every", "all", "both", "few", "some", "any", "many",
        "much", "more", "most", "less", "least", "very", "just", "also", "only",
        "even", "like", "well", "best", "good", "better", "need", "want", "make",
        "made", "take", "took", "give", "gave", "get", "got", "use", "used",
        "work", "works", "help", "helps", "try", "tried", "call", "ask", "asked",
        "said", "say", "says", "find", "found", "look", "looks", "seem", "seems",
        "think", "thought", "know", "knew", "see", "saw", "come", "came", "go",
        "went", "put", "let", "way", "ways", "case", "cases", "thing", "things",
        "stuff", "kind", "sort", "type", "types", "time", "times", "day", "days",
        "week", "weeks", "month", "months", "year", "years", "last", "next",
        "first", "second", "third", "once", "twice", "again", "still", "already",
        "ever", "never", "always", "often", "sometimes", "usually", "maybe",
        "perhaps", "either", "neither", "both", "between", "among", "during",
        "before", "after", "since", "until", "unless", "though", "although",
        "because", "therefore", "thus", "hence", "estimate", "estimated",
        "estimates", "probability", "probabilities", "credible", "interval",
        "intervals", "evidence", "timeline", "timelines", "compared", "compare",
        "comparing", "answer", "answers", "question", "questions", "query",
        "support", "supports", "supporting", "main", "primary", "secondary",
        "general", "specific", "overall", "total", "based", "using", "given",
        "regarding", "related", "concerning", "including", "exclude", "excluding",
        "per", "via", "versus", "against", "within", "without", "amongst", "onto",
        "across", "around", "about", "above", "below", "near", "far", "long",
        "short", "high", "low", "new", "old", "big", "small", "large", "little",
        "able", "unable", "likely", "unlikely", "possible", "possibly", "sure",
        "really", "quite", "rather", "pretty", "basically", "essentially", "simply",
        "actually", "probably", "definitely", "certainly", "clearly", "obviously",
        "especially", "important", "importantly", "significant", "significantly",
        "various", "several", "numerous", "certain", "uncertain", "surely", "maybe",
        "show", "shows", "showing", "shown", "provide", "provides", "provided",
        "giving", "getting", "using", "used", "list", "lists", "listed",
        "describe", "describes", "described", "explain", "explains", "explained",
        "discuss", "discusses", "discussed", "consider", "considers", "considered",
        "recommend", "recommends", "recommended", "suggest", "suggests", "suggested",
    }
)

# Short clinical tokens we never strip (even if 2–3 letters).
_ROUTER_TS_ACRONYM_KEEP: frozenset = frozenset(
    {"ra", "esr", "crp", "haq", "vas", "pro", "dxa", "bmi", "icu", "pt", "ot"}
)


def _filter_ts_terms(terms: List[str]) -> List[str]:
    """Drop glue words; keep short uppercase-ish acronyms."""
    out: List[str] = []
    seen: set = set()
    for t in terms or []:
        s = str(t).strip()
        if not s:
            continue
        low = s.lower()
        if low in _ROUTER_TS_ACRONYM_KEEP:
            if low not in seen:
                seen.add(low)
                out.append(s)
            continue
        if len(s) < 3 or low in _ROUTER_TS_STOPWORDS:
            continue
        if low not in seen:
            seen.add(low)
            out.append(s)
    return out


def _ts_terms_dominated_by_noise(raw: List[str], filtered: List[str]) -> bool:
    """True when the model mostly echoed question glue instead of medical tokens."""
    if not raw:
        return False
    if not filtered:
        return True
    if len(raw) >= 4 and len(filtered) <= 1:
        return True
    ratio = len(filtered) / max(1, len(raw))
    return len(raw) >= 5 and ratio < 0.35


def _fallback_ts_terms_from_query(query: str, max_n: int = 8) -> List[str]:
    """Deterministic tokens when the router returns unparseable JSON."""
    q = query or ""
    out: List[str] = []
    seen: set = set()
    for t in re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", q):
        low = t.lower()
        if low in _ROUTER_TS_STOPWORDS and low not in _ROUTER_TS_ACRONYM_KEEP:
            continue
        if low in seen:
            continue
        seen.add(low)
        out.append(t)
        if len(out) >= max_n:
            break
    if out:
        return out[:max_n]
    return [
        t
        for t in re.split(r"[\s,]+", q)
        if len(t) >= 4 and t.lower() not in _ROUTER_TS_STOPWORDS
    ][:max_n]


def _coerce_router_parsed(raw: Dict[str, Any]) -> Dict[str, Any]:
    """Accept flat string lists the small model sometimes emits instead of row objects."""
    d = dict(raw)
    sm = d.get("selected_modules")
    if isinstance(sm, list) and sm:
        if all(isinstance(x, str) for x in sm):
            d["selected_modules"] = [
                {
                    "module_id": str(x).strip(),
                    "priority": i + 1,
                    "why": "coerced_from_string_list",
                }
                for i, x in enumerate(sm)
                if str(x).strip()
            ]
    ss = d.get("selected_sources")
    if isinstance(ss, list) and ss:
        fixed: List[Dict[str, Any]] = []
        for i, r in enumerate(ss):
            if isinstance(r, str) and r.strip():
                fixed.append(
                    {
                        "source": r.strip().lower(),
                        "priority": i + 1,
                        "why": "coerced_from_string_list",
                    }
                )
            elif isinstance(r, dict):
                row = dict(r)
                if "priority" not in row:
                    row["priority"] = i + 1
                row.setdefault("why", "")
                fixed.append(row)
        d["selected_sources"] = fixed
    return d


def _supplement_ts_terms(text: str, have: List[str], *, want: int) -> List[str]:
    if want <= 0:
        return []
    have_l = {t.lower() for t in have if t}
    out: List[str] = []
    for t in re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,}", text or ""):
        low = t.lower()
        if low in have_l:
            continue
        if low in _ROUTER_TS_STOPWORDS and low not in _ROUTER_TS_ACRONYM_KEEP:
            continue
        if len(t) < 3 and low not in _ROUTER_TS_ACRONYM_KEEP:
            continue
        out.append(t)
        have_l.add(low)
        if len(out) >= want:
            break
    return out


def _clean_terms(items: Any) -> List[str]:
    out: List[str] = []
    for x in (items or []):
        s = str(x).strip()
        if s:
            out.append(s)
    return out


_TOKEN_RX = re.compile(r"[A-Za-z][A-Za-z0-9_\-]{2,}")


def _tokenize(text: str) -> List[str]:
    return [t.lower() for t in _TOKEN_RX.findall(text or "")]


def _distinct_sources_from_rows(rows: List[Dict[str, Any]]) -> set:
    return {
        str(r.get("source") or "").strip().lower()
        for r in rows
        if r.get("source") and str(r.get("source")).strip()
    }


def _backfill_sources(
    *,
    selected_rows: List[Dict[str, Any]],
    question_type: str,
    source_candidates: Dict[str, str],
    query_text: str,
    max_sources: int,
) -> List[Dict[str, Any]]:
    """Reduce over-conservative router output by deterministically widening source fanout."""
    if not source_candidates:
        return selected_rows

    qt = str(question_type or "").strip().upper()
    if qt in {"C", "D"}:
        min_needed = min(max_sources, 12)
    elif qt in {"A", "B", "E"}:
        min_needed = min(max_sources, 7)
    else:
        min_needed = min(max_sources, 6)
    target = min(max_sources, max(1, min_needed))

    out = list(selected_rows)
    selected_set = _distinct_sources_from_rows(out)
    if len(selected_set) >= target:
        return selected_rows

    q_toks = set(_tokenize(query_text))
    prefer_eoh = qt in {"C", "D", "OTHER"}
    scored: List[tuple[float, str]] = []
    for src, desc in source_candidates.items():
        s = str(src).strip().lower()
        if not s or s in selected_set:
            continue
        blob = f"{s} {desc or ''}".lower()
        s_toks = set(_tokenize(blob))
        overlap = (len(q_toks & s_toks) / max(1, len(q_toks | s_toks))) if q_toks else 0.0
        eoh_boost = 0.2 if (prefer_eoh and s.startswith("eoh")) else 0.0
        guideline_boost = 0.1 if any(k in s for k in ("acr_", "eular_", "kdigo_", "ada_", "gold_", "gina_")) else 0.0
        scored.append((overlap + eoh_boost + guideline_boost, s))

    scored.sort(key=lambda x: (-x[0], x[1]))
    next_prio = max([int(r.get("priority") or 0) for r in selected_rows] + [0]) + 1
    for _, s in scored:
        if len(_distinct_sources_from_rows(out)) >= target:
            break
        out.append(
            {
                "source": s,
                "priority": next_prio,
                "why": "router_post_validate_backfill_for_recall",
                "ts_terms": [],
            }
        )
        selected_set.add(s)
        next_prio += 1

    if len(_distinct_sources_from_rows(out)) < target:
        taken = _distinct_sources_from_rows(out)
        for s in sorted(source_candidates.keys(), key=lambda x: str(x).lower()):
            sk = str(s).strip().lower()
            if not sk or sk in taken:
                continue
            if len(_distinct_sources_from_rows(out)) >= target:
                break
            out.append(
                {
                    "source": sk,
                    "priority": next_prio,
                    "why": "router_post_validate_alphabet_tail_fill",
                    "ts_terms": [],
                }
            )
            taken.add(sk)
            next_prio += 1

    needs_eoh = qt in {"C", "D", "OTHER"}
    has_eoh = any(str(r.get("source") or "").startswith("eoh_") for r in out)
    if needs_eoh and not has_eoh:
        eoh_candidates = sorted(
            str(s).strip().lower() for s in source_candidates if str(s).startswith("eoh_")
        )
        for s in eoh_candidates:
            if max_sources and len(out) >= max_sources:
                break
            if any(str(r.get("source") or "") == s for r in out):
                continue
            out.append(
                {
                    "source": s,
                    "priority": next_prio,
                    "why": "ensure_eoh_first_class_source",
                    "ts_terms": [],
                }
            )
            next_prio += 1
            break
    return out  # no hard slice — context budget is enforced downstream


def _build_system_prompt() -> str:
    return (
        "You are an EoH Router planner. You **MUST** respond with **ONLY** valid JSON — one object, UTF-8.\n"
        "No markdown fences, no commentary, no text before or after the JSON.\n"
        "Task: from one user query, choose rag sources, choose EoH modules, and create retrieval queries.\n"
        "Do not answer clinically. Do not fabricate source keys or module IDs.\n"
        "If uncertain, still return valid JSON with your best guess (never prose).\n\n"
        "FEW-SHOT (shape only; keys must match the schema below):\n"
        'OTHER: query "prior auth form ICD-10 for upadacitinib" → question_type OTHER. '
        '  selected_sources rows: rxnorm.ts_terms ["upadacitinib", "JAK inhibitor", "Rinvoq"], '
        '  icd10cm.ts_terms ["M05.9", "M06", "rheumatoid arthritis"].\n'
        'D: query "first-line biologic for moderate UC flare when mesalamine fails" → question_type D. '
        '  selected_sources rows: rxnorm.ts_terms ["infliximab", "vedolizumab", "ustekinumab"], '
        '  acg_uc_2024.ts_terms ["moderate ulcerative colitis", "biologic naive", "loss of response"], '
        '  eoh_m13_decision_support.ts_terms ["UC flare", "step-up", "regime change"].\n\n'
        "question_type codes:\n"
        "  A = anatomy/physiology/basic science\n"
        "  B = biomarker / lab / diagnostic test\n"
        "  C = clinical guideline / protocol / standard of care\n"
        "  D = drug / therapy / treatment / management plan\n"
        "  E = epidemiology / prevalence / evidence base\n"
        "  OTHER = administrative / unclear\n\n"
        "ROUTING RULES (follow strictly):\n"
        "- EoH sources (eoh_*) are FIRST-CLASS. For trajectory/flare/remission/baseline/"
        "longitudinal-planning/uncertainty questions, include at least one eoh_* source when available.\n"
        "- Therapy/management/dosing/first-line/protocol queries -> question_type D or C (NEVER E).\n"
        "- Guidelines, staging, standard-of-care -> C.\n"
        "- E is only for prevalence/epidemiology questions.\n"
        "- **SOURCE BREADTH (mandatory):** For types **C or D**, output **at least min(8, max_sources)** distinct "
        "source keys whenever the candidate list is large enough — never stop at two or three sources. "
        "For A/B/E/OTHER, aim for **at least min(6, max_sources)**. Prefer diversity: multiple guideline corpora "
        "(KDIGO + ADA + ACR/EULAR + VA), terminology layers (icd10cm, snomed, loinc, rxnorm when relevant), "
        "plus at least one **eoh_*** ethos source when available.\n"
        "- Fill toward **max_sources**; under-selection hurts recall badly.\n"
        "- ts_terms is the PRIMARY signal for downstream Postgres FTS. **Each selected_sources row\n"
        "  carries its OWN per-source ts_terms list** — what should be matched in rag_corpus rows\n"
        "  whose source = that key. Tailor terms to the source's vocabulary:\n"
        "    * rxnorm: drug names, brand names, drug classes (e.g. 'adalimumab', 'TNF inhibitor', 'Humira').\n"
        "    * icd10cm: ICD-10 codes and disease nouns (e.g. 'M05.9', 'rheumatoid arthritis, seropositive').\n"
        "    * snomed: SNOMED concept names ('Rheumatoid arthritis', 'Disease activity score').\n"
        "    * loinc: LOINC names / shortnames ('C reactive protein', 'CRP', 'Erythrocyte sedimentation rate').\n"
        "    * acr_*, eular_*, kdigo_*, ada_*, gold_*, gina_*: guideline-style phrases\n"
        "      ('treat to target', 'flare', 'low disease activity').\n"
        "    * eoh_*: PRO / Ethos terms ('HAQ-II', 'PAS-II', 'flare risk', 'taper safety').\n"
        "  Each per-source list must be 4-12 concrete tokens/phrases. Avoid stopwords and never\n"
        "  echo the question's glue words (for/this/patient/what/our/best/when/how) as ts_terms;\n"
        "  every entry must be something an FTS lane should match in rag_corpus rows of that source.\n"
        "- The number of selected_sources is NOT capped — pick as many sources as are clinically\n"
        "  relevant (terminology layers + guidelines + EoH ethos modules). Total context is the only\n"
        "  budget; downstream code dedups and pins one qualifying row per source.\n"
        "- mkg_semantic_query: 1-2 sentence expanded clinical statement, written for the EXTERNAL\n"
        "  rag_corpus dense lane (guidelines, terminology entries, EoH ethos modules). Use full\n"
        "  clinical concept names, drug *class* nouns, guideline body names, and synonyms a\n"
        "  professional knowledge corpus would use. Do NOT echo the user's pronouns or the phrase\n"
        "  'this patient'.\n"
        "- ptv_semantic_query: short query (1 sentence or comma-list, ~120 chars max) written for\n"
        "  the PATIENT TIMELINE dense lane. Sentence-transformer cosine searches event TITLES /\n"
        "  one-liners like 'VAS Pain = 96.1', 'Adalimumab 40 mg q2w', 'HAQ-II = 2.33',\n"
        "  'PRO-composite flare round 6'. Use the actual instrument names, drug brand+generic,\n"
        "  PRO labels, and event-type words ('flare', 'medication', 'derived_metric'). Do NOT use\n"
        "  guideline/corpus prose; do NOT include 'patient', 'evidence', or rhetorical glue.\n"
        "- semantic_query: legacy alias; if you only set one, set both — they may differ.\n"
        "- ts_query: compact lexical OR-joined string for Postgres FTS (cross-source fallback).\n"
        "- Top-level ts_terms[] is OPTIONAL and used only as a fallback union when a per-source row\n"
        "  has no ts_terms; prefer placing terms on each source row.\n"
        "- Sources and modules must come from provided candidate lists.\n"
        "- priority=1 is highest; increase as relevance decreases.\n"
        "- When patient_code_inventory is present, it lists codes on this patient's timeline\n"
        "  (from metadata.code_index) with first/last dates — align rxnorm/icd10cm/loinc per-source\n"
        "  ts_terms with what the patient actually has; still retrieve external evidence.\n\n"
        "Output JSON schema:\n"
        "{\n"
        '  "question_type": "A|B|C|D|E|OTHER",\n'
        '  "mkg_semantic_query": "MKG dense lane query (corpus-shaped prose)",\n'
        '  "ptv_semantic_query": "PTV dense lane query (patient-event-shaped phrases)",\n'
        '  "semantic_query":     "legacy alias; if set, use the same wording as mkg_semantic_query",\n'
        '  "ts_query": "compact lexical ts query string",\n'
        '  "ts_terms": ["term1", "term2"],            // OPTIONAL fallback union\n'
        '  "selected_sources": [\n'
        '    {\n'
        '      "source": "<source_key>",\n'
        '      "priority": 1,\n'
        '      "why": "short reason",\n'
        '      "ts_terms": ["term1", "term2"]         // REQUIRED, source-specific tokens\n'
        '    }\n'
        "  ],\n"
        '  "selected_modules": [\n'
        '    {"module_id": "M13", "priority": 1, "why": "short reason"}\n'
        "  ],\n"
        '  "notes": "short routing notes",\n'
        '  "question_type_explanation": "optional 1 sentence"\n'
        "}\n"
        "Optional key question_type_explanation is allowed; all other keys must match this schema.\n"
    )


def _build_user_prompt(
    *,
    query: str,
    source_candidates: Dict[str, str],
    module_candidates: Dict[str, Dict[str, str]],
    max_sources: int,
    max_modules: int,
    clinical_context: Optional[str] = None,
    patient_code_inventory: Optional[Any] = None,
    prior_session_summary: Optional[str] = None,
) -> str:
    payload: Dict[str, Any] = {
        "query": query,
        "max_sources": max_sources,
        "max_modules": max_modules,
        "source_candidates": source_candidates,
        "module_candidates": module_candidates,
    }
    if patient_code_inventory is not None:
        payload["patient_code_inventory"] = patient_code_inventory
    if prior_session_summary and prior_session_summary.strip():
        ps = prior_session_summary.strip()
        if len(ps) > 4000:
            ps = ps[:4000] + "\n…[prior_session_summary truncated]"
        payload["prior_session_summary"] = ps
    if clinical_context and clinical_context.strip():
        # Hard cap so an over-long PTV summary cannot blow the router context.
        ctx = clinical_context.strip()
        if len(ctx) > 8000:
            ctx = ctx[:8000] + "\n…[clinical_context truncated]"
        payload["clinical_context"] = ctx
    if patient_code_inventory is not None and clinical_context and clinical_context.strip():
        intro = (
            "Plan source/module routing for this query. The clinical_context "
            "block orients the PTV graph; patient_code_inventory lists indexed "
            "codes on this patient's timeline with first/last dates — use both "
            "to bias ts_terms and semantic_query toward documented entities; "
            "the query is still primary for external retrieval."
        )
    elif patient_code_inventory is not None:
        intro = (
            "Plan source/module routing for this query. The patient_code_inventory "
            "object lists indexed codes on this patient's timeline with first/last "
            "dates — use it to bias ts_terms and semantic_query; the query is still primary."
        )
    elif clinical_context and clinical_context.strip():
        intro = (
            "Plan source/module routing for this query. The clinical_context "
            "block is a per-patient timeline summary you may use to bias source "
            "and ts_term selection, but the query is still primary."
        )
    else:
        intro = "Plan source/module routing for this query."

    fanout_hint = ""
    if max_sources >= 4:
        fanout_hint = (
            f"\n\nSOURCE FANOUT TARGET: max_sources={max_sources}. "
            "Types **C/D**: **≥8 distinct selected_sources** keys when that many candidates apply (never 3). "
            "Types **A/B/E/OTHER**: **≥6** when possible. Stretch toward **"
            f"{max_sources}** for broad clinical questions.\n"
        )
    return intro + fanout_hint + "\n\n" + json.dumps(payload, ensure_ascii=True, indent=2)


def _module_candidates() -> Dict[str, Dict[str, str]]:
    out: Dict[str, Dict[str, str]] = {}
    for mid, mod in MODULE_INDEX.items():
        out[mid] = {
            "name": str(mod.get("name") or ""),
            "layer": str(mod.get("layer") or ""),
            "llm_use_when": str(mod.get("llm_use_when") or ""),
        }
    return out


def _ollama_chat(
    *,
    url: str,
    model: str,
    messages: List[Dict[str, str]],
    timeout: float,
    temperature: float,
    num_ctx: int,
) -> str:
    import requests

    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": num_ctx},
    }
    r = requests.post(f"{url.rstrip('/')}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return (data.get("message") or {}).get("content") or ""


def _post_validate(
    plan: Dict[str, Any],
    *,
    source_candidates: Dict[str, str],
    module_candidates: Dict[str, Dict[str, str]],
    max_sources: int,
    max_modules: int,
    fallback_query: str,
    router_min_terms: int = 4,
) -> Dict[str, Any]:
    # Two distinct semantic queries:
    #   * mkg_semantic_query  -> EXTERNAL rag_corpus dense lane (guideline prose).
    #   * ptv_semantic_query  -> PATIENT timeline dense lane (event-title phrasing).
    # ``semantic_query`` is the legacy alias; we keep it equal to mkg_semantic_query
    # for back-compat with downstream consumers.
    raw_mkg_q = str(plan.get("mkg_semantic_query") or plan.get("semantic_query") or "").strip()
    raw_ptv_q = str(plan.get("ptv_semantic_query") or "").strip()
    out: Dict[str, Any] = {
        "question_type": str(plan.get("question_type") or "OTHER"),
        "semantic_query": raw_mkg_q,
        "mkg_semantic_query": raw_mkg_q,
        "ptv_semantic_query": raw_ptv_q,
        "ts_query": str(plan.get("ts_query") or "").strip(),
        "ts_terms": [],
        "selected_sources": [],
        "selected_modules": [],
        "notes": str(plan.get("notes") or "").strip(),
    }
    if out["question_type"] not in {"A", "B", "C", "D", "E", "OTHER"}:
        out["question_type"] = "OTHER"

    # Per-source ts_terms: each row in selected_sources carries its own ts_terms
    # tailored to that source's vocabulary (e.g. rxnorm gets drug names, icd10cm
    # gets ICD codes, eoh_* gets PRO phrases). The top-level ts_terms is now a
    # back-compat fallback union; per-row terms are the primary signal.
    for row in plan.get("selected_sources") or []:
        if isinstance(row, str):
            row = {"source": row.strip().lower(), "priority": 999, "why": ""}
        if not isinstance(row, dict):
            continue
        src = str(row.get("source") or "").strip().lower()
        if src not in source_candidates:
            continue
        try:
            prio = int(row.get("priority", 999))
        except Exception:
            prio = 999
        why = str(row.get("why") or "").strip()
        row_terms_raw = _clean_terms(row.get("ts_terms"))
        row_terms = _filter_ts_terms(row_terms_raw)
        if (not row_terms) or _ts_terms_dominated_by_noise(row_terms_raw, row_terms):
            row_terms = []  # filled in second pass after global ts_terms resolved
        out["selected_sources"].append(
            {
                "source": src,
                "priority": prio,
                "why": why,
                "ts_terms": row_terms,
                "ts_query": str(row.get("ts_query") or "").strip(),
                "semantic_query": str(row.get("semantic_query") or "").strip(),
            }
        )
    out["selected_sources"].sort(key=lambda r: r["priority"])
    # ``max_sources`` is treated as a soft fanout target the model aims for; we
    # don't hard-cap here because the user explicitly asked for "no limit on
    # number of sources" — total context budget is what matters and is enforced
    # downstream by per-lane top_k + source_coverage pinning.
    out["selected_sources"] = _backfill_sources(
        selected_rows=out["selected_sources"],
        question_type=out["question_type"],
        source_candidates=source_candidates,
        query_text=(out["semantic_query"] or out["ts_query"] or fallback_query),
        max_sources=max_sources,
    )

    for row in plan.get("selected_modules") or []:
        if isinstance(row, str):
            row = {"module_id": row.strip(), "priority": 999, "why": ""}
        if not isinstance(row, dict):
            continue
        mid = str(row.get("module_id") or "").strip()
        if mid not in module_candidates:
            continue
        try:
            prio = int(row.get("priority", 999))
        except Exception:
            prio = 999
        why = str(row.get("why") or "").strip()
        out["selected_modules"].append({"module_id": mid, "priority": prio, "why": why})
    out["selected_modules"].sort(key=lambda r: r["priority"])
    out["selected_modules"] = out["selected_modules"][:max_modules]

    if not out["semantic_query"]:
        out["semantic_query"] = out["ts_query"] or fallback_query
    if not out["mkg_semantic_query"]:
        out["mkg_semantic_query"] = out["semantic_query"] or out["ts_query"] or fallback_query
    if not out["ts_query"]:
        out["ts_query"] = out["semantic_query"] or fallback_query

    # Derive a PTV semantic query from the per-source ts_terms when the model
    # didn't provide one. We bias toward tokens a patient timeline event title
    # actually contains (drug names, PRO instrument labels, ICD short forms,
    # flare wording) rather than the user's raw question.
    if not out["ptv_semantic_query"]:
        ptv_seed: List[str] = []
        seen_low: set = set()
        for r in out["selected_sources"]:
            src = str(r.get("source") or "").lower()
            if not any(
                tag in src
                for tag in ("rxnorm", "icd10cm", "snomed", "loinc", "eoh_")
            ):
                continue
            for t in r.get("ts_terms") or []:
                low = t.lower()
                if low and low not in seen_low and low not in _ROUTER_TS_STOPWORDS:
                    seen_low.add(low)
                    ptv_seed.append(t)
                if len(ptv_seed) >= 12:
                    break
            if len(ptv_seed) >= 12:
                break
        out["ptv_semantic_query"] = (
            ", ".join(ptv_seed)
            if ptv_seed
            else (out["mkg_semantic_query"] or fallback_query)
        )

    combined_blob = " ".join(
        str(x)
        for x in (
            fallback_query,
            out["semantic_query"],
            out["mkg_semantic_query"],
            out["ptv_semantic_query"],
            out["ts_query"],
        )
        if str(x).strip()
    )

    # 1) Build the **global** ts_terms (back-compat fallback used by retrieval
    #    when a per-source row has no ts_terms). Prefer the union of per-source
    #    terms; if none of the rows had usable terms, fall back to the model's
    #    top-level ts_terms (filtered) or, last resort, query-derived tokens.
    union: List[str] = []
    seen_low: set = set()
    for r in out["selected_sources"]:
        for t in r.get("ts_terms") or []:
            low = t.lower()
            if low and low not in seen_low:
                seen_low.add(low)
                union.append(t)

    if union:
        out["ts_terms"] = union[:24]  # generous cap; per-source lists are primary
    else:
        raw_terms = _clean_terms(plan.get("ts_terms"))
        filtered = _filter_ts_terms(raw_terms)
        if filtered and not _ts_terms_dominated_by_noise(raw_terms, filtered):
            out["ts_terms"] = filtered
        else:
            out["ts_terms"] = _fallback_ts_terms_from_query(combined_blob, max_n=12)

    min_tar = max(1, int(router_min_terms))
    if len(out["ts_terms"]) < min_tar:
        need = min_tar - len(out["ts_terms"])
        extra = _supplement_ts_terms(combined_blob, out["ts_terms"], want=need + 4)
        out["ts_terms"] = _filter_ts_terms(_clean_terms(out["ts_terms"] + extra))[:24]

    # 2) Second pass: fill in any source row that had no usable per-source
    #    ts_terms with the global union so downstream retrieval always has
    #    something to query that source with. Uses the source key as a lexical
    #    boost when synthesising terms (e.g. rxnorm-shaped tokens already in
    #    the union are preferred for that row).
    for r in out["selected_sources"]:
        if r.get("ts_terms"):
            continue
        r["ts_terms"] = list(out["ts_terms"])[:8] if out["ts_terms"] else []
        r.setdefault("ts_query", "")
        r.setdefault("semantic_query", "")

    if any(
        (r.get("why") or "").startswith("router_post_validate_") for r in out["selected_sources"]
    ):
        note = "source fanout widened in post-validate for recall"
        out["notes"] = f"{out['notes']} | {note}".strip(" |")

    return out


def plan_route(
    query: str,
    *,
    ollama_url: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.27,
    timeout: float = 120.0,
    num_ctx: Optional[int] = None,
    max_sources: int = 16,
    max_modules: int = 8,
    source_candidates: Optional[Dict[str, str]] = None,
    module_candidates: Optional[Dict[str, Dict[str, str]]] = None,
    clinical_context: Optional[str] = None,
    patient_code_inventory: Optional[Any] = None,
    prior_session_summary: Optional[str] = None,
    router_min_terms: int = 4,
    debug_router: bool = False,
) -> Dict[str, Any]:
    """Run the source-router model and return a normalized route plan.

    ``patient_code_inventory`` is optional structured JSON (e.g. from
    ``ptv_toolkit.code_inventory.build_patient_code_inventory``) so the router
    can align ``ts_terms`` / ``semantic_query`` with codes on the patient timeline.

    ``prior_session_summary`` is optional retro context (e.g. summary written by
    the chatbot's retro-retrieval loop after the user references prior turns).
    The router may reuse named entities / dates from it but the new ``query``
    remains primary.

    On any failure, returns a degraded plan with ``error`` set and useful
    fallbacks (``ts_terms`` derived from the raw query) so the caller can
    still execute retrieval.
    """
    sources = source_candidates or pilot_source_descriptions(sources=None)
    modules = module_candidates or _module_candidates()

    url = ollama_url or os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")
    model_name = model or os.environ.get("EOH_SOURCE_ROUTER_MODEL", "eoh-llama3.2-source-router")
    ctx = num_ctx if num_ctx is not None else int(os.environ.get("OLLAMA_ROUTER_NUM_CTX", "8192"))

    system = _build_system_prompt()
    user = _build_user_prompt(
        query=query,
        source_candidates=sources,
        module_candidates=modules,
        max_sources=max_sources,
        max_modules=max_modules,
        clinical_context=clinical_context,
        patient_code_inventory=patient_code_inventory,
        prior_session_summary=prior_session_summary,
    )

    _log("🧭", f"Source-router model={model_name} num_ctx={ctx} temp={temperature}")
    if debug_router:
        _log("🐛", f"ROUTER system ({len(system)} chars) head=\n{system[:1200]}…")
        _log("🐛", f"ROUTER user ({len(user)} chars) head=\n{user[:1200]}…")

    t0 = time.monotonic()
    raw = ""
    parsed: Optional[Dict[str, Any]] = None
    max_attempts = 1 + ROUTER_RETRY_COUNT
    last_err: Optional[str] = None
    for attempt in range(max_attempts):
        try:
            temp = min(0.32, float(temperature) + 0.02 * attempt)
            raw = _ollama_chat(
                url=url,
                model=model_name,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                timeout=timeout,
                temperature=temp,
                num_ctx=ctx,
            )
        except Exception as exc:  # noqa: BLE001
            elapsed = round(time.monotonic() - t0, 3)
            _log("⚠️", f"Router call failed in {elapsed}s: {exc}")
            return {
                "error": str(exc),
                "elapsed_sec": elapsed,
                "model": model_name,
                "question_type": "OTHER",
                "semantic_query": query,
                "mkg_semantic_query": query,
                "ptv_semantic_query": query,
                "ts_query": query,
                "ts_terms": _fallback_ts_terms_from_query(query),
                "selected_sources": [],
                "selected_modules": [],
                "notes": "router_unavailable",
            }

        if debug_router:
            _log("🐛", f"ROUTER raw ({len(raw)} chars) head=\n{raw[:1600]}…")

        parsed = force_json_dict(raw)
        if parsed:
            break
        last_err = "force_json_dict returned None"
        head = (raw or "")[:400].replace("\n", "\\n")
        _log(
            "⚠️",
            f"Router JSON parse failed attempt {attempt + 1}/{max_attempts} — raw_head400={head!r}",
        )
        if attempt + 1 < max_attempts:
            delay = 0.35 * (2**attempt)
            _log("⏳", f"Router retry backoff sleep_sec={delay:.2f}")
            time.sleep(delay)

    elapsed = round(time.monotonic() - t0, 3)
    if not parsed:
        fts = _fallback_ts_terms_from_query(query)
        _log(
            "⚠️",
            "Router JSON parse failed after retries — SAFE BROAD FALLBACK "
            f"({last_err}); raw_head400={(raw or '')[:400]!r}",
        )
        return {
            "error": "parse_failed",
            "raw_response": raw,
            "elapsed_sec": elapsed,
            "model": model_name,
            "question_type": "OTHER",
            "question_type_explanation": "parse_fallback",
            "semantic_query": query,
            "mkg_semantic_query": query,
            "ptv_semantic_query": query,
            "ts_query": query,
            "ts_terms": fts,
            "selected_sources": [],
            "selected_modules": [],
            "notes": "router_unparseable_fallback",
        }

    parsed = _coerce_router_parsed(parsed)
    plan = _post_validate(
        parsed,
        source_candidates=sources,
        module_candidates=modules,
        max_sources=max_sources,
        max_modules=max_modules,
        fallback_query=query,
        router_min_terms=router_min_terms,
    )
    plan["elapsed_sec"] = elapsed
    plan["model"] = model_name
    return plan
