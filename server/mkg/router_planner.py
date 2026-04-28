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
from server.mkg.portalnode_pilot_sources import pilot_source_descriptions


def _log(emoji: str, msg: str) -> None:
    print(f"{emoji} {msg}", file=sys.stderr, flush=True)


def _extract_json_object(raw: str) -> Dict[str, Any]:
    s = (raw or "").strip()
    try:
        return json.loads(s)
    except Exception:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL | re.IGNORECASE)
    if fenced:
        try:
            return json.loads(fenced.group(1))
        except Exception:
            pass
    m = re.search(r"\{.*\}", s, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise ValueError("No parseable JSON object in router response.")


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
    selected = [str(r.get("source") or "").strip().lower() for r in selected_rows]
    selected = [s for s in selected if s]
    selected_set = set(selected)

    # Mirror ask/eoh_stream behavior: avoid over-pruning by keeping a broader source set.
    min_needed = 5 if question_type in {"C", "D"} else 4 if question_type in {"A", "B", "E"} else 3
    target = min(max_sources, max(1, min_needed))
    if len(selected_set) >= target:
        return selected_rows

    q_toks = set(_tokenize(query_text))
    prefer_eoh = question_type in {"C", "D", "OTHER"}
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
    out = list(selected_rows)
    for _, s in scored:
        if len(out) >= target:
            break
        out.append(
            {
                "source": s,
                "priority": next_prio,
                "why": "router_post_validate_backfill_for_recall",
            }
        )
        next_prio += 1
    return out


def _build_system_prompt() -> str:
    return (
        "You are an EoH source-routing planner. You must return STRICT JSON only.\n"
        "Task: from one user query, choose rag sources, choose EoH modules, and create retrieval queries.\n"
        "Do not answer clinically. Do not fabricate source keys or module IDs.\n\n"
        "question_type codes:\n"
        "  A = anatomy/physiology/basic science\n"
        "  B = biomarker / lab / diagnostic test\n"
        "  C = clinical guideline / protocol / standard of care\n"
        "  D = drug / therapy / treatment / management plan\n"
        "  E = epidemiology / prevalence / evidence base\n"
        "  OTHER = administrative / unclear\n\n"
        "ROUTING RULES (follow strictly):\n"
        "- Therapy/management/dosing/first-line/protocol queries -> question_type D or C (NEVER E).\n"
        "- Guidelines, staging, standard-of-care -> C.\n"
        "- E is only for prevalence/epidemiology questions.\n"
        "- For D or C questions, select at least 3 sources unless fewer exist.\n"
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
        '  "notes": "short routing notes"\n'
        "}\n"
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
    return intro + "\n\n" + json.dumps(payload, ensure_ascii=True, indent=2)


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
    if any(r.get("why") == "router_post_validate_backfill_for_recall" for r in out["selected_sources"]):
        note = "source fanout widened in post-validate for recall"
        out["notes"] = f"{out['notes']} | {note}".strip(" |")

    return out


def plan_route(
    query: str,
    *,
    ollama_url: Optional[str] = None,
    model: Optional[str] = None,
    temperature: float = 0.1,
    timeout: float = 120.0,
    num_ctx: Optional[int] = None,
    max_sources: int = 8,
    max_modules: int = 6,
    source_candidates: Optional[Dict[str, str]] = None,
    module_candidates: Optional[Dict[str, Dict[str, str]]] = None,
    clinical_context: Optional[str] = None,
    patient_code_inventory: Optional[Any] = None,
    prior_session_summary: Optional[str] = None,
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

    _log("🧭", f"Source-router model={model_name} num_ctx={ctx}")
    t0 = time.monotonic()
    try:
        raw = _ollama_chat(
            url=url,
            model=model_name,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            timeout=timeout,
            temperature=temperature,
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
            "ts_terms": [t for t in re.split(r"[\s,]+", query) if len(t) >= 4][:8],
            "selected_sources": [],
            "selected_modules": [],
            "notes": "router_unavailable",
        }

    elapsed = round(time.monotonic() - t0, 3)
    try:
        parsed = _extract_json_object(raw)
    except Exception as exc:  # noqa: BLE001
        _log("⚠️", f"Router JSON parse failed: {exc}")
        return {
            "error": "parse_failed",
            "raw_response": raw,
            "elapsed_sec": elapsed,
            "model": model_name,
            "question_type": "OTHER",
            "semantic_query": query,
            "ts_query": query,
            "ts_terms": [t for t in re.split(r"[\s,]+", query) if len(t) >= 4][:8],
            "selected_sources": [],
            "selected_modules": [],
            "notes": "router_unparseable",
        }

    plan = _post_validate(
        parsed,
        source_candidates=sources,
        module_candidates=modules,
        max_sources=max_sources,
        max_modules=max_modules,
        fallback_query=query,
    )
    plan["elapsed_sec"] = elapsed
    plan["model"] = model_name
    return plan
