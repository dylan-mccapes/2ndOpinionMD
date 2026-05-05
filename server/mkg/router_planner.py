"""Reusable EoH source-router planner for MKG retrieval pipelines.

Extracted from ``server/scripts/eoh_source_router_harness.py`` so the same
planning logic can be invoked from any harness (e.g. the MKG dual-lane
retrieval harness) without code duplication.

Returns a normalized plan dict::

    {
      "question_type": "A|B|C|D|E|OTHER",
      "semantic_query": "expanded ANN query",
      "ts_query":       "compact lexical query",
      "ts_terms":       ["term1", "term2", ...],
      "selected_sources":[{"source": "...", "priority": 1, "why": "..."}, ...],
      "selected_modules":[{"module_id": "M13", "priority": 1, "why": "..."}, ...],
      "notes":          "short routing notes",
      "raw_response":   "(only when parse fails) raw model text",
      "elapsed_sec":    1.234,
      "model":          "eoh-llama3.2-source-router"
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


def _fallback_ts_terms_from_query(query: str, max_n: int = 8) -> List[str]:
    """Deterministic tokens when the router returns unparseable JSON."""
    q = query or ""
    stop = {
        "with", "from", "that", "this", "have", "what", "does", "when", "where",
        "tell", "about", "please", "patient", "clinical", "search", "suggest",
    }
    out: List[str] = []
    seen: set = set()
    for t in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", q):
        low = t.lower()
        if low in stop or low in seen:
            continue
        seen.add(low)
        out.append(t)
        if len(out) >= max_n:
            break
    if out:
        return out
    return [t for t in re.split(r"[\s,]+", q) if len(t) >= 4][:max_n]


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
    for t in re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text or ""):
        low = t.lower()
        if low in have_l:
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
            if len(out) >= max_sources:
                break
            if any(str(r.get("source") or "") == s for r in out):
                continue
            out.append(
                {
                    "source": s,
                    "priority": next_prio,
                    "why": "ensure_eoh_first_class_source",
                }
            )
            next_prio += 1
            break
    return out[:max_sources]


def _build_system_prompt() -> str:
    return (
        "You are an EoH Router planner. You **MUST** respond with **ONLY** valid JSON — one object, UTF-8.\n"
        "No markdown fences, no commentary, no text before or after the JSON.\n"
        "Task: from one user query, choose rag sources, choose EoH modules, and create retrieval queries.\n"
        "Do not answer clinically. Do not fabricate source keys or module IDs.\n"
        "If uncertain, still return valid JSON with your best guess (never prose).\n\n"
        "FEW-SHOT (shape only; keys must match the schema below):\n"
        'OTHER: query "prior auth form ICD-10" → question_type OTHER, ts_terms short tokens, '
        "selected_sources diverse terminology/guideline keys from candidates.\n"
        'D: query "first-line biologic for moderate UC flare when mesalamine fails" → question_type D, '
        "semantic_query names drug classes + guideline bodies, ts_terms include biologic names + UC.\n\n"
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
        "- ts_terms must be 6-12 concrete medical tokens or short phrases (drug names, ICD nouns,\n"
        "  procedures, lab names). Include synonyms and abbreviations a clinician would search.\n"
        "  Do NOT include stopwords or generic words like 'management' or 'treatment'.\n"
        "- ts_terms is the PRIMARY signal for downstream Postgres FTS — be generous and specific.\n"
        "- semantic_query: a 1-2 sentence expanded clinical statement enriched with synonyms,\n"
        "  drug classes, anatomic context, and guideline body names. Optimized for ANN retrieval.\n"
        "- ts_query: compact lexical OR-joined string for Postgres FTS.\n"
        "- Sources and modules must come from provided candidate lists.\n"
        "- priority=1 is highest; increase as relevance decreases.\n"
        "- When patient_code_inventory is present, it lists codes on this patient's timeline\n"
        "  (from metadata.code_index) with first/last dates — align ts_terms and semantic_query\n"
        "  with drugs/diagnoses/labs the patient actually has; still retrieve external evidence.\n\n"
        "Output JSON schema:\n"
        "{\n"
        '  "question_type": "A|B|C|D|E|OTHER",\n'
        '  "semantic_query": "expanded semantic query string",\n'
        '  "ts_query": "compact lexical ts query string",\n'
        '  "ts_terms": ["term1", "term2"],\n'
        '  "selected_sources": [\n'
        '    {"source": "<source_key>", "priority": 1, "why": "short reason"}\n'
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
    out: Dict[str, Any] = {
        "question_type": str(plan.get("question_type") or "OTHER"),
        "semantic_query": str(plan.get("semantic_query") or "").strip(),
        "ts_query": str(plan.get("ts_query") or "").strip(),
        "ts_terms": _clean_terms(plan.get("ts_terms")),
        "selected_sources": [],
        "selected_modules": [],
        "notes": str(plan.get("notes") or "").strip(),
    }
    if out["question_type"] not in {"A", "B", "C", "D", "E", "OTHER"}:
        out["question_type"] = "OTHER"

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
        out["selected_sources"].append({"source": src, "priority": prio, "why": why})
    out["selected_sources"].sort(key=lambda r: r["priority"])
    out["selected_sources"] = out["selected_sources"][:max_sources]
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
    if not out["ts_query"]:
        out["ts_query"] = out["semantic_query"] or fallback_query
    if not out["ts_terms"]:
        out["ts_terms"] = [
            t for t in re.split(r"[\s,]+", out["ts_query"]) if t and len(t) >= 3
        ][:8]
    min_tar = max(1, int(router_min_terms))
    if len(out["ts_terms"]) < min_tar:
        need = min_tar - len(out["ts_terms"])
        blob = " ".join(
            [
                fallback_query,
                out["semantic_query"],
                out["ts_query"],
            ]
        )
        extra = _supplement_ts_terms(blob, out["ts_terms"], want=need + 4)
        out["ts_terms"] = _clean_terms(out["ts_terms"] + extra)[:12]
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
