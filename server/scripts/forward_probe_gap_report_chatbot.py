#!/usr/bin/env python3
"""Terminal chatbot: probe (3.2) → gap (8B) → report (8B).

**Retro** (disabled by default; pass ``--retro`` when a session log has prior turns):

- Tiny ``eoh-llama3.2-source-router`` gate decides whether the new question
  references prior chatbot turns (``references_prior``, ``retro_query``).
- If yes, ripgrep-or-token-score over ``artifacts/chatbot_sessions/<id>.jsonl``
  retrieves the top-K candidate turns (default K=5).
- ``eoh-llama`` reviews and emits ``retro_summary`` + ``evidence_turn_ids``.
- ``retro_summary`` is forwarded to ``plan_route`` (as ``prior_session_summary``)
  and into the GAP / REPORT bundles via ``probe.retro``.

**Probe** (default ``eoh-llama3.2-source-router``):

- Scans ``metadata.code_index`` **before** the source-router (same rows as
  ``code_index_lookup``): every bucket/key with first/last observation dates
  and event counts. The router and graph-picker receive a JSON slice that fits
  their context budget; GAP/REPORT get the full inventory on the probe bundle.
- Calls the source-router planner (same stack as MKG harness) to produce
  ``semantic_query`` (MKG dense lane) and ``ts_terms`` (Postgres FTS lane).
- Second 3.2 call chooses exactly one PTV graph tool + JSON args.
- Executes: MKG semantic + per-term TS, PTV ``semantic_search`` with the
  router's semantic string, and the chosen graph tool.
- **TS** uses Postgres FTS (``ts_rank`` over the stored ``ts`` column with
  ``websearch_to_tsquery('public.simple_unaccent', term)``). When the per-term
  lane returns fewer than ``top_k/2`` rows, the chatbot merges in the tiered
  ``bm25_ts`` fallback (Tier 1 full query, Tier 2 OR-joined key tokens, Tier 3
  longest token anchor) on the router's ``semantic_query``. Note: this is NOT
  BM25 — Postgres FTS uses ``ts_rank`` (length-normalized tf-style score).

**Bayesian phase** (default ``--bayes-gate-model`` = probe model, deterministic update):

- Tiny 8B gate decides ``wants_bayes`` + ``hypothesis_id`` (one of
  ``flare_30d`` | ``progression_3mo`` | ``taper_safety``) per the strategy doc
  ``reports/STRATEGY_BAYESIAN_PTV_UC_20260423.md``.
- When yes, runs the deterministic ``bayesian_update_uc`` toolkit primitive
  against the probe's working set (PTV semantic_search + chosen graph tool)
  and emits an ``UncertaintyCarrier`` (point_estimate, 90% band, evidence_ids,
  prior, posterior_params, method, spec_hash). Closed-form Beta–Bernoulli
  by default; no LLM in the math.
- The posterior block is added to ``probe.bayes.posteriors[]`` and forwarded
  to GAP / REPORT. Disable with ``--no-bayes``.

**Gap** (default ``eoh-qwen3-14b`` 102K context):

- Consumes probe bundle (incl. ``bayes.posteriors``); may request at most one
  extra PTV semantic query, up to two additional TS terms, one follow-up graph
  tool, and **one additional Bayesian hypothesis** (``follow_bayes_hypothesis_id``).
- Emits a structured ``gap_report`` plus optional follow-up tool results.
- If the model leaves all follow fields empty but ``mkg_jaccard`` is 0.0 with
  both MKG lanes populated, a small heuristic adds TS terms from the user
  question or an enriched PTV semantic query (disable with ``--no-gap-heuristic``).
- When ``probe.bayes.posteriors`` is non-empty, the gap_report MUST cite each
  UC's point_estimate / band_90 and comment on whether evidence_event_ids
  look sufficient (regime-change check per strategy doc §5.2).

**Report** (default ``eoh-qwen3-14b`` 102K context):

- Synthesizes a single markdown answer from probe + gap context (no tools).
- When posteriors are present, MUST report the point_estimate and 90% band per
  hypothesis_id and cite ``evidence_event_ids`` (the UC IS the answer for that
  question class — see strategy doc §3.3 / §10).

**Session log**:

- Each turn appends one JSON line to ``artifacts/chatbot_sessions/<id>.jsonl``
  with ``turn_id``, question, router plan, MKG counts, gap/final reports, and
  any retro bundle. A sidecar ``__meta.json`` carries graph_hash + models.
  Resume by passing the same ``--session-id``. ``--no-session`` disables.

**Session harness** (non-interactive multi-question run):

- ``--harness-file`` JSON array of objects: required ``question``; optional
  ``id`` and ``seed_session_turns_before`` (list of dicts appended as prior
  turns — useful mainly when testing ``--retro``).
- Requires session logging (incompatible with ``--no-session``). Default
  session id is ``harness_<UTC>`` when ``--session-id`` is omitted.
- ``--harness-fresh`` deletes existing JSONL/meta for that session id before run.
- Receipt JSON written to ``--harness-receipt`` or under ``receipts/`` by default.
  The full session (every turn: questions, gap_report, final_report, retro,
  router fields, graph tool) is always **copied** next to that JSON as
  ``<receipt_stem>_session.jsonl`` and ``<receipt_stem>_session__meta.json`` so
  the harness bundle is self-contained. Use ``--harness-no-session-copy`` to
  skip copying (paths to the live session files are still recorded).

Env: same DB/embed/Ollama as ``mkg_retrieval_harness`` (``SYNC_DATABASE_URL``,
``LOCAL_EMBED_MODEL``, ``OLLAMA_URL``). If no DSN, MKG lanes are skipped with a
notice; PTV-only still works.

Qwen: ``FORWARD_QWEN_MODEL_NUM_CTX`` (default 102400) matches Modelfile ``PARAMETER num_ctx``.
``FORWARD_QWEN_CALL_NUM_CTX`` / ``OLLAMA_AGENT_NUM_CTX`` / ``OLLAMA_SYNTH_NUM_CTX`` default to ~60%
of that for GAP/REPORT API calls. ``FORWARD_GAP_REPORT_JSON_MAX_CHARS`` caps serialized JSON (~2.5
chars per token vs ``FORWARD_QWEN_CALL_NUM_CTX`` unless overridden).

Examples::

    python server/scripts/forward_probe_gap_report_chatbot.py
    python server/scripts/forward_probe_gap_report_chatbot.py --graph path/to/ptv.json
    python server/scripts/forward_probe_gap_report_chatbot.py --no-mkg
    python server/scripts/forward_probe_gap_report_chatbot.py \\
        --harness-file server/scripts/forward_probe_gap_session_harness_questions.json \\
        --harness-fresh
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg
import requests
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.mkg.llm_json_parse import force_json_dict
from server.mkg.router_planner import plan_route
from server.eoh.module_index import MODULE_INDEX
from server.ptv_toolkit.bayes import DEFAULT_HYPOTHESIS_PRIORS
from server.ptv_toolkit.code_inventory import (
    build_patient_code_inventory,
    fit_code_inventory_to_budget,
    strip_n_events,
)
from server.ptv_toolkit.graph import load_graph
from server.ptv_toolkit.registry import call_tool
from server.ptv_toolkit.session_log import SessionLog

from server.scripts.mkg_retrieval_harness import (  # type: ignore
    ann_local,
    bm25_ts,
    bm25_ts_terms,
    embed_query,
    ensure_source_coverage_retrieval,
    fetch_mkg_bayes_prior,
    _compact_hit,
    _overlap,
    _vec_literal,
)


# Align with eoh-qwen / eoh-qwen3-14b Modelfile PARAMETER num_ctx (102K). API requests default to
# ~60% of that window so KV + generation fit; JSON payloads scale with FORWARD_QWEN_CALL_NUM_CTX.
_FORWARD_QWEN_MODEL_NUM_CTX = int(os.environ.get("FORWARD_QWEN_MODEL_NUM_CTX", "102400"))
_FORWARD_QWEN_CALL_NUM_CTX = max(
    4096,
    int(os.environ.get("FORWARD_QWEN_CALL_NUM_CTX", str(_FORWARD_QWEN_MODEL_NUM_CTX * 60 // 100))),
)
_GAP_REPORT_JSON_MAX_CHARS = int(
    os.environ.get(
        "FORWARD_GAP_REPORT_JSON_MAX_CHARS",
        str(min(250_000, (_FORWARD_QWEN_CALL_NUM_CTX * 5) // 2)),
    )
)


def _log(emoji: str, msg: str) -> None:
    print(f"{emoji} {msg}", file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# Demo-mode verbose logging (tuned for YC demo video)
# --------------------------------------------------------------------------- #
#
# All demo helpers are no-ops when ``_Demo.enabled is False`` so the regular
# CLI run is unchanged. Demo mode is toggled by ``--demo`` (or the env var
# ``FORWARD_DEMO_MODE=1``) at the top of ``main`` / ``_run_full_turn``.
#
# Conventions:
#   * Banner / kv / preview lines go to stderr (interleaved with _log).
#   * The end-of-turn "FINAL REPORT" + evidence dump goes to stdout so it can
#     be piped / recorded.
#   * Previews truncate long blobs at ``head`` chars and report the cut size.
#
# Why this matters for the demo: the audience needs to see (a) what context is
# being curated at each stage, (b) the model's own words (raw response head),
# and (c) the deterministic Bayesian numbers behind the final answer. The
# helpers below make that visible without hand-rolling print statements at
# every stage.

_DEMO_BAR_WIDTH = 78


class _Demo:
    """Module-level demo state. Reset at the top of every ``_run_full_turn``."""

    enabled: bool = False
    stage_starts: Dict[str, float] = {}
    stage_durations: List[Tuple[str, float]] = []
    llm_calls: List[Dict[str, Any]] = []   # {stage, model, num_ctx, raw_chars, elapsed}


def _demo_enable(on: bool) -> None:
    _Demo.enabled = bool(on)


def _demo_reset_turn() -> None:
    _Demo.stage_starts = {}
    _Demo.stage_durations = []
    _Demo.llm_calls = []


def _demo_banner(title: str, subtitle: str = "", *, char: str = "─") -> None:
    if not _Demo.enabled:
        return
    bar = char * _DEMO_BAR_WIDTH
    print(f"\n{bar}", file=sys.stderr, flush=True)
    print(f"  {title}", file=sys.stderr, flush=True)
    if subtitle:
        print(f"  ↳ {subtitle}", file=sys.stderr, flush=True)
    print(bar, file=sys.stderr, flush=True)


def _demo_kv(key: str, value: Any) -> None:
    if not _Demo.enabled:
        return
    print(f"    · {key}: {value}", file=sys.stderr, flush=True)


def _demo_kvs(kvs: Dict[str, Any]) -> None:
    if not _Demo.enabled:
        return
    keylen = max((len(k) for k in kvs), default=0)
    for k, v in kvs.items():
        print(f"    · {k.ljust(keylen)} : {v}", file=sys.stderr, flush=True)


def _demo_preview(label: str, text: str, *, head: int = 800) -> None:
    """Indented multi-line preview of any text blob (LLM response, prompt, etc.)."""
    if not _Demo.enabled:
        return
    s = str(text or "").strip()
    if not s:
        print(f"    ↳ {label}: <empty>", file=sys.stderr, flush=True)
        return
    cut = s[:head]
    suffix = "" if len(s) <= head else f"... [truncated, +{len(s) - head} more chars]"
    print(f"    ↳ {label} ({len(s):,} chars total):", file=sys.stderr, flush=True)
    for line in cut.splitlines():
        print(f"        {line}", file=sys.stderr, flush=True)
    if suffix:
        print(f"        {suffix}", file=sys.stderr, flush=True)


def _demo_record_llm(
    stage: str,
    *,
    model: str,
    num_ctx: int,
    raw: str,
    elapsed_sec: float,
    user_chars: int,
    system_chars: int,
) -> None:
    """Capture every LLM call so the end-of-turn summary can show timing/cost."""
    rec = {
        "stage": stage,
        "model": model,
        "num_ctx": num_ctx,
        "raw_chars": len(raw or ""),
        "user_chars": user_chars,
        "system_chars": system_chars,
        "elapsed_sec": round(float(elapsed_sec), 3),
    }
    _Demo.llm_calls.append(rec)
    if _Demo.enabled:
        _demo_preview(
            f"LLM[{stage}] response — model={model} num_ctx={num_ctx} "
            f"input={user_chars + system_chars:,}c → output={len(raw or ''):,}c "
            f"in {elapsed_sec:.2f}s",
            raw or "",
            head=900,
        )


def _demo_stage_start(name: str) -> None:
    _Demo.stage_starts[name] = time.monotonic()


def _demo_stage_end(name: str) -> float:
    if name in _Demo.stage_starts:
        elapsed = time.monotonic() - _Demo.stage_starts.pop(name)
        _Demo.stage_durations.append((name, elapsed))
        if _Demo.enabled:
            print(
                f"    ⏱ stage `{name}` finished in {elapsed * 1000:.1f} ms",
                file=sys.stderr,
                flush=True,
            )
        return elapsed
    return 0.0


def _abridge(s: Any, n: int = 90) -> str:
    """Single-line cutoff helper used by the evidence dump table."""
    txt = str(s or "").replace("\n", " ").replace("\r", " ")
    return txt if len(txt) <= n else txt[: n - 1] + "…"


DEFAULT_GRAPH = (
    ROOT
    / "artifacts"
    / "forward_kaleb_package_20260423"
    / "synthetic_pro_cohort"
    / "ptv_synth_P1_early_responder.json"
)

DEFAULT_HARNESS_QUESTIONS = (
    ROOT / "server" / "scripts" / "forward_probe_gap_session_harness_questions.json"
)

_GRAPH_TOOLS = [
    "graph_stats",
    "list_event_types",
    "code_index_lookup",
    "semantic_search",
    "bfs_expand",
    "temporal_scan",
    "get_event",
]

def _mkg_dsn() -> Optional[str]:
    for k in ("SYNC_DATABASE_URL", "DATABASE_URL", "POSTGRES_URL"):
        v = os.environ.get(k)
        if v and v.strip():
            return v.strip()
    return None


_GAP_STOP = {
    "with",
    "from",
    "that",
    "this",
    "have",
    "what",
    "does",
    "when",
    "where",
    "tell",
    "about",
    "please",
    "any",
    "especially",
    "patient",
    "clinical",
    "medications",
    "medication",
    "confounders",
    "confounder",
}


def _probe_metrics(probe_bundle: Dict[str, Any]) -> Dict[str, Any]:
    """Compact stats for GAP prompting and heuristic follow-ups."""
    mkg = probe_bundle.get("mkg") or {}
    if mkg.get("skipped"):
        return {
            "mkg_skipped": True,
            "mkg_jaccard": None,
            "mkg_semantic_hits": 0,
            "mkg_ts_hits": 0,
            "mkg_ok": False,
            "ptv_semantic_result_count": 0,
        }
    ov = mkg.get("overlap") or {}
    j_raw = ov.get("jaccard")
    try:
        j = float(j_raw) if j_raw is not None else 0.0
    except (TypeError, ValueError):
        j = 0.0
    n_sem = len(mkg.get("semantic_hits") or [])
    n_ts = len(mkg.get("ts_hits") or [])
    mkg_ok = bool(mkg.get("ok", True))
    ptv_wr = probe_bundle.get("ptv_semantic_search") or {}
    res = (ptv_wr.get("result") or {}) if ptv_wr.get("ok") else {}
    n_ptv = len(res.get("results") or []) if isinstance(res, dict) else 0
    return {
        "mkg_skipped": False,
        "mkg_jaccard": j,
        "mkg_semantic_hits": n_sem,
        "mkg_ts_hits": n_ts,
        "mkg_ok": mkg_ok,
        "ptv_semantic_result_count": n_ptv,
    }


def _norm_gap_follow_field(val: Any) -> Any:
    """Treat JSON-ish string 'null' / empty as absent."""
    if val is None:
        return None
    if isinstance(val, str) and val.strip().lower() in ("", "null", "none", "undefined"):
        return None
    return val


def _heuristic_ts_terms_from_question(
    question: str,
    router_terms: List[str],
    *,
    max_terms: int = 2,
) -> List[str]:
    """Extra TS tokens from the user question (avoid duplicating router terms)."""
    rt = {t.strip().lower() for t in router_terms if t and str(t).strip()}
    tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", question)
    out: List[str] = []
    for t in tokens:
        low = t.lower()
        if low in _GAP_STOP or low in rt:
            continue
        out.append(t)
        if len(out) >= max_terms:
            break
    return out


def _ollama_chat(
    *,
    url: str,
    model: str,
    system: str,
    user: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
    demo_stage: Optional[str] = None,
) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": max(2048, int(num_ctx))},
    }
    t0 = time.monotonic()
    r = requests.post(f"{url.rstrip('/')}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    raw = (r.json().get("message") or {}).get("content") or ""
    elapsed = time.monotonic() - t0
    if demo_stage:
        _demo_record_llm(
            demo_stage,
            model=model,
            num_ctx=int(num_ctx),
            raw=raw,
            elapsed_sec=elapsed,
            user_chars=len(user or ""),
            system_chars=len(system or ""),
        )
    return raw


def _router_sources(plan: Dict[str, Any]) -> Optional[List[str]]:
    rows = plan.get("selected_sources") or []
    out = []
    for r in rows:
        if isinstance(r, dict) and r.get("source"):
            out.append(str(r["source"]).strip().lower())
    return out or None


def _router_source_rows(plan: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Return normalized selected_sources rows (with per-source ts_terms preserved)."""
    rows = plan.get("selected_sources") or []
    out: List[Dict[str, Any]] = []
    for r in rows:
        if not isinstance(r, dict):
            continue
        src = str(r.get("source") or "").strip().lower()
        if not src:
            continue
        terms = [str(t).strip() for t in (r.get("ts_terms") or []) if str(t).strip()]
        out.append(
            {
                "source": src,
                "priority": int(r.get("priority") or 999),
                "why": str(r.get("why") or "").strip(),
                "ts_terms": terms,
                "ts_query": str(r.get("ts_query") or "").strip(),
                "semantic_query": str(r.get("semantic_query") or "").strip(),
            }
        )
    return out


def _router_modules(plan: Dict[str, Any]) -> List[str]:
    rows = plan.get("selected_modules") or []
    out: List[str] = []
    for r in rows:
        if isinstance(r, dict) and r.get("module_id"):
            out.append(str(r["module_id"]).strip())
    return out


def _eoh_module_route_prelude(
    *,
    question: str,
    patient_state_summary: Optional[Dict[str, Any]],
    ollama_url: str,
    model: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
    debug_router: bool = False,
) -> Dict[str, Any]:
    """3.2 pre-router call using router_llm-style planning: question_type + exact module/doc plan."""
    module_index_for_prompt = {}
    for mid, mod in MODULE_INDEX.items():
        module_index_for_prompt[mid] = {
            "layer": mod.get("layer"),
            "llm_use_when": mod.get("llm_use_when"),
            "doc_handles": mod.get("doc_handles") or [],
        }
    system = (
        "You are an EoH Router planner. You **MUST** respond with **ONLY** valid JSON — one object.\n"
        "No markdown, no explanations, no text before or after the JSON.\n"
        "Planner-only: do not answer clinically.\n"
        "Choose ONE question_type from A|B|C|D|E|OTHER, plus module_plan and doc_retrieval_plan.\n"
        "Use ONLY module ids and doc handles present in module_index.\n"
        "EoH is first-class: for trajectory/flare/remission/longitudinal-plan/uncertainty questions,\n"
        "prefer A-E (not OTHER) and include specific EoH modules with exact doc handles.\n\n"
        "Output exactly this shape (optional keys may be null/empty arrays):\n"
        "{\n"
        '  "question_type": "A|B|C|D|E|OTHER",\n'
        '  "question_type_explanation": "...",\n'
        '  "module_plan": [{"step": "...", "modules": ["M1", "M13"]}],\n'
        '  "doc_retrieval_plan": [{"source": "eoh_router", "handles": ["eoh_m1_patient_terrain"]}],\n'
        '  "selected_modules": ["M1", "M13"]\n'
        "}\n"
    )
    user = json.dumps(
        {
            "question": question,
            "patient_state_summary": patient_state_summary or {},
            "module_index": module_index_for_prompt,
        },
        ensure_ascii=False,
        indent=2,
    )[:_GAP_REPORT_JSON_MAX_CHARS]
    _log("🧭", f"Stage EOH-PRELUDE model={model} num_ctx={num_ctx}")
    _demo_banner(
        "PROBE · EOH PRELUDE",
        "8B picks question_type and the EoH module plan (M1/M2/M13/...) before retrieval",
    )
    _demo_kvs({
        "model": model,
        "num_ctx": num_ctx,
        "module_index_size": len(module_index_for_prompt),
        "user_payload_chars": len(user),
        "patient_state_summary_keys": list((patient_state_summary or {}).keys()),
    })
    if debug_router:
        _log("🐛", f"EOH-PRELUDE system head=\n{system[:1200]}…")
        _log("🐛", f"EOH-PRELUDE user head=\n{user[:1200]}…")
    raw = ""
    parsed: Dict[str, Any] = {}
    for attempt in range(3):
        raw = _ollama_chat(
            url=ollama_url,
            model=model,
            system=system,
            user=user,
            temperature=min(0.32, float(temperature) + 0.02 * attempt),
            timeout=timeout,
            num_ctx=num_ctx,
            demo_stage=f"eoh_module_prelude(attempt={attempt + 1}/3)",
        )
        got = force_json_dict(raw)
        if got:
            parsed = got
            break
        if debug_router:
            _log("🐛", f"EOH-PRELUDE raw head=\n{(raw or '')[:1600]}…")
        _log(
            "⚠️",
            f"EOH-PRELUDE JSON parse miss attempt {attempt + 1}/3 raw_head400={(raw or '')[:400]!r}",
        )
        if attempt < 2:
            time.sleep(0.35 * (2**attempt))
    if not parsed:
        _log("⚠️", "EOH-PRELUDE JSON parse failed after retries — continuing with empty prelude dict")
    # normalize selected_modules from either explicit list or module_plan
    mods = []
    for m in parsed.get("selected_modules") or []:
        s = str(m).strip()
        if s in MODULE_INDEX and s not in mods:
            mods.append(s)
    if not mods:
        for step in parsed.get("module_plan") or []:
            if not isinstance(step, dict):
                continue
            for m in step.get("modules") or []:
                s = str(m).strip()
                if s in MODULE_INDEX and s not in mods:
                    mods.append(s)
    parsed["selected_modules"] = mods
    return parsed


def _mkg_retrieve_bundle(
    *,
    semantic_query: str,
    ts_terms: List[str],
    top_k: int,
    embed_model: str,
    sources: Optional[List[str]],
    text_chars: int,
    ts_fallback: bool = True,
    ts_fallback_threshold_frac: float = 0.5,
    source_coverage: bool = True,
    min_ann_score: float = 0.12,
    min_ts_score: float = 0.02,
    selected_source_rows: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Run dense + per-term TS retrieval against ``public.rag_corpus``.

    TS notes (Postgres FTS, not BM25):
    - ``bm25_ts_terms`` runs **one** ``websearch_to_tsquery('public.simple_unaccent', term)``
      per cleaned term and merges by max ``ts_rank``. Single-token terms therefore behave
      like single-token matches; this is what /ask_stream's
      ``search_source_ts_for_terms`` does, plus an OR-friendly query parser.
    - When the per-term lane yields fewer than
      ``ts_fallback_threshold_frac * top_k`` rows (default 0.5), we run the
      tiered ``bm25_ts`` (Tier 1: full query; Tier 2: OR-joined key tokens;
      Tier 3: longest token anchor) on the ``semantic_query`` and merge by
      max score, keeping the per-term hits that already passed.
    """
    dsn = _mkg_dsn()
    if not dsn:
        _log("🗄️", "MKG retrieve skipped: no SYNC_DATABASE_URL / DATABASE_URL")
        return {
            "ok": False,
            "error": "no_database_url",
            "semantic_hits": [],
            "ts_hits": [],
        }

    # Build per-source ts_terms map from the router's selected_source_rows when
    # supplied. Each source key maps to its tailored ts_terms (e.g. rxnorm gets
    # drug names, icd10cm gets ICD codes, eoh_* gets PRO phrases). The global
    # ``ts_terms`` is the union and used only as a per-source fallback.
    per_source_ts_terms: Dict[str, List[str]] = {}
    if selected_source_rows:
        for row in selected_source_rows:
            if not isinstance(row, dict):
                continue
            src = str(row.get("source") or "").strip().lower()
            terms = [str(t).strip() for t in (row.get("ts_terms") or []) if str(t).strip()]
            if src and terms:
                per_source_ts_terms[src] = terms

    _log(
        "🧠",
        f"MKG embed+retrieve top_k={top_k} ts_terms={len(ts_terms or [])} "
        f"sources={sources or 'all'} per_source_term_keys={len(per_source_ts_terms)}",
    )
    vec, device = embed_query(embed_model, semantic_query or "")
    lit = _vec_literal(vec)
    ts_per_term_n = 0
    ts_or_added_n = 0
    used_or_fallback = False
    source_expansion_mode = "none"
    cov_stats: Dict[str, Any] = {}
    ts_per_source_count: Dict[str, int] = {}
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("SET statement_timeout = '120s';")
            sem_rows = ann_local(cur, lit, top_k, sources=sources)
            ts_rows: List[Dict[str, Any]] = []
            if per_source_ts_terms:
                # Per-source TS retrieval: each source uses its OWN ts_terms.
                # We keep up to top_k per source then merge by max score.
                per_src_cap = max(3, top_k)
                merged: Dict[Any, Dict[str, Any]] = {}
                for src, terms in per_source_ts_terms.items():
                    rows_src = bm25_ts_terms(cur, terms, per_src_cap, sources=[src])
                    ts_per_source_count[src] = len(rows_src)
                    for r in rows_src:
                        rid = r["id"]
                        cur_row = merged.get(rid)
                        if cur_row is None or float(r.get("score") or 0.0) > float(
                            cur_row.get("score") or 0.0
                        ):
                            merged[rid] = dict(r)
                # Sources without their own per-source terms but still in the
                # ``sources`` list fall back to the global ts_terms / ts_query.
                fallback_sources = [
                    s for s in (sources or []) if s not in per_source_ts_terms
                ]
                if fallback_sources and ts_terms:
                    rows_fb = bm25_ts_terms(cur, ts_terms, top_k, sources=fallback_sources)
                    for r in rows_fb:
                        rid = r["id"]
                        cur_row = merged.get(rid)
                        if cur_row is None or float(r.get("score") or 0.0) > float(
                            cur_row.get("score") or 0.0
                        ):
                            merged[rid] = dict(r)
                ts_rows = sorted(
                    merged.values(),
                    key=lambda r: float(r.get("score") or 0.0),
                    reverse=True,
                )[:top_k]
            elif ts_terms:
                ts_rows = bm25_ts_terms(cur, ts_terms, top_k, sources=sources)
            else:
                ts_rows = []
            ts_per_term_n = len(ts_rows)
            need_fallback = ts_fallback and (
                len(ts_rows) < max(1, int(top_k * float(ts_fallback_threshold_frac)))
            )
            if need_fallback and (semantic_query or "").strip():
                _log(
                    "🔁",
                    f"TS per-term thin ({ts_per_term_n}/{top_k}) — merging OR-joined "
                    "websearch_to_tsquery fallback (bm25_ts tiered)",
                )
                fb_rows = bm25_ts(cur, semantic_query or "", top_k, sources=sources)
                used_or_fallback = bool(fb_rows)
                by_id: Dict[Any, Dict[str, Any]] = {}
                for r in ts_rows:
                    by_id[r["id"]] = dict(r)
                for r in fb_rows:
                    cur_row = by_id.get(r["id"])
                    if cur_row is None or float(r.get("score") or 0.0) > float(cur_row.get("score") or 0.0):
                        by_id[r["id"]] = dict(r)
                merged = sorted(
                    by_id.values(),
                    key=lambda r: float(r.get("score") or 0.0),
                    reverse=True,
                )[:top_k]
                ts_or_added_n = max(0, len(merged) - ts_per_term_n)
                ts_rows = merged

            # Router source selection is treated as a soft preference (ask/eoh_stream style):
            # if the selected source set is narrow, supplement from the full pilot slice and
            # keep only top-scored rows after merge so we preserve precision while widening recall.
            if sources and len(sources) < 6:
                source_expansion_mode = "router_soft_plus_global_topscore"
                sem_global = ann_local(cur, lit, top_k, sources=None)
                sem_by_id: Dict[Any, Dict[str, Any]] = {}
                for r in sem_rows + sem_global:
                    rid = r["id"]
                    cur_row = sem_by_id.get(rid)
                    if cur_row is None or float(r.get("score") or 0.0) > float(cur_row.get("score") or 0.0):
                        sem_by_id[rid] = dict(r)
                sem_rows = sorted(
                    sem_by_id.values(),
                    key=lambda r: float(r.get("score") or 0.0),
                    reverse=True,
                )[:top_k]

                if ts_terms:
                    ts_global = bm25_ts_terms(cur, ts_terms, top_k, sources=None)
                else:
                    ts_global = []
                if not ts_global and (semantic_query or "").strip():
                    ts_global = bm25_ts(cur, semantic_query or "", top_k, sources=None)
                ts_by_id: Dict[Any, Dict[str, Any]] = {}
                for r in ts_rows + ts_global:
                    rid = r["id"]
                    cur_row = ts_by_id.get(rid)
                    if cur_row is None or float(r.get("score") or 0.0) > float(cur_row.get("score") or 0.0):
                        ts_by_id[rid] = dict(r)
                ts_rows = sorted(
                    ts_by_id.values(),
                    key=lambda r: float(r.get("score") or 0.0),
                    reverse=True,
                )[:top_k]
                _log(
                    "🌐",
                    f"Router sources were narrow ({len(sources)}); supplemented with global retrieval "
                    f"then re-ranked to top_k={top_k}",
                )

            cov_stats = {}
            if sources and source_coverage:
                sem_rows, ts_rows, cov_stats = ensure_source_coverage_retrieval(
                    cur,
                    lit,
                    sem_rows,
                    ts_rows,
                    required_sources=sources,
                    ts_terms=list(ts_terms or []),
                    ts_query_fallback=(semantic_query or "").strip(),
                    top_k=top_k,
                    min_ann_score=min_ann_score,
                    min_ts_score=min_ts_score,
                    per_source_fetch_limit=max(16, top_k),
                    per_source_ts_terms=per_source_ts_terms or None,
                )

    if not cov_stats:
        if not source_coverage:
            cov_stats = {"enabled": False, "skipped_reason": "disabled"}
        elif not sources:
            cov_stats = {"enabled": False, "skipped_reason": "no_sources"}

    sem_c = [_compact_hit(r, text_chars=text_chars) for r in sem_rows]
    ts_c = [_compact_hit(r, text_chars=text_chars) for r in ts_rows]
    overlap = _overlap([h["id"] for h in sem_c], [h["id"] for h in ts_c])
    _log(
        "📚",
        f"MKG done semantic_hits={len(sem_c)} ts_hits={len(ts_c)} "
        f"(per_term={ts_per_term_n}, or_fallback={used_or_fallback}) "
        f"jaccard={overlap.get('jaccard', 0):.3f} source_expansion={source_expansion_mode}",
    )
    return {
        "ok": True,
        "embed_device": device,
        "semantic_hits": sem_c,
        "ts_hits": ts_c,
        "overlap": overlap,
        "ts_terms_used": list(ts_terms or []),
        "per_source_ts_terms_used": dict(per_source_ts_terms),
        "ts_per_source_hit_count": dict(ts_per_source_count),
        "ts_per_term_count": ts_per_term_n,
        "ts_or_fallback_used": used_or_fallback,
        "ts_or_fallback_added": ts_or_added_n,
        "source_expansion_mode": source_expansion_mode,
        "source_coverage": cov_stats,
    }


def _retro_gate(
    *,
    question: str,
    session: Optional[SessionLog],
    ollama_url: str,
    model: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
) -> Dict[str, Any]:
    """Tiny 3.2 call: does the question reference earlier turns?

    Returns ``{"references_prior": bool, "retro_query": str|None, "why": str}``.
    Always safe; on any error returns ``references_prior=False``.
    """
    if session is None or session.n_turns() == 0:
        return {"references_prior": False, "retro_query": None, "why": "no_prior_turns"}

    recent = session.read_all()[-6:]
    sketch = [
        {
            "turn_id": t.get("turn_id"),
            "turn_index": t.get("turn_index"),
            "ts": t.get("ts"),
            "question": (t.get("question") or "")[:240],
        }
        for t in recent
    ]
    system = (
        "You are a tiny gating classifier. Given a NEW user question and a sketch of recent\n"
        "chatbot turns (questions only), decide whether the new question references prior\n"
        "context (e.g. 'as we discussed', 'compare to last question', 'go back to the flare\n"
        "topic', anaphoric 'that', 'those events', etc.).\n\n"
        "OUTPUT: STRICT JSON ONLY, no markdown:\n"
        '{"references_prior": true|false, "retro_query": "<terms to retrieve over prior turns>"|null,\n'
        ' "why": "short reason"}\n'
        "If references_prior is false, retro_query must be null.\n"
        "If true, retro_query should be the concrete topic/keywords useful for ripgrep over\n"
        "prior chatbot turns (not a yes/no, not a sentence)."
    )
    user = json.dumps(
        {"new_question": question, "recent_turns_sketch": sketch},
        ensure_ascii=False,
        indent=2,
    )
    _log("🪞", f"Stage RETRO-GATE model={model} num_ctx={num_ctx} prior_turns={session.n_turns()}")
    _demo_banner("RETRO GATE", "does this question reference an earlier chatbot turn?")
    _demo_kvs({"model": model, "num_ctx": num_ctx, "prior_turns": session.n_turns(),
               "user_payload_chars": len(user)})
    try:
        raw = _ollama_chat(
            url=ollama_url,
            model=model,
            system=system,
            user=user,
            temperature=temperature,
            timeout=timeout,
            num_ctx=num_ctx,
            demo_stage="retro_gate",
        )
    except Exception as exc:  # noqa: BLE001
        _log("⚠️", f"retro-gate call failed: {exc}")
        return {"references_prior": False, "retro_query": None, "why": f"gate_error:{exc}"}
    parsed = force_json_dict(raw) or {}
    refs = bool(parsed.get("references_prior"))
    rq = _norm_gap_follow_field(parsed.get("retro_query"))
    if not isinstance(rq, str) or not rq.strip():
        rq = None
    why = str(parsed.get("why") or "").strip()[:240]
    _log("🪞", f"retro-gate references_prior={refs} retro_query={(rq or '')[:80]!r}")
    return {"references_prior": refs, "retro_query": rq, "why": why}


def _retro_summarize(
    *,
    question: str,
    matched_turns: List[Dict[str, Any]],
    session: SessionLog,
    ollama_url: str,
    model: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
    text_chars: int,
) -> Dict[str, Any]:
    """eoh-llama review of matched session turns. Returns retro_summary + evidence_turn_ids."""
    if not matched_turns:
        return {"retro_summary": "", "evidence_turn_ids": [], "n_turns_reviewed": 0}
    compact = [session.compact_turn(t, text_chars=text_chars) for t in matched_turns]
    system = (
        "You are the RETRO-REVIEW agent. The user asked a follow-up question that references\n"
        "earlier chatbot turns. You receive a JSON list of candidate prior turns retrieved from\n"
        "the session log (already token-overlap ranked).\n\n"
        "Task: produce a SINGLE JSON object:\n"
        "{\n"
        '  "retro_summary": "<<= 250-word grounded summary of relevant prior context, in markdown>",\n'
        '  "evidence_turn_ids": ["<turn_id>", ...]\n'
        "}\n"
        "Rules:\n"
        "- Cite turn_ids in the summary text using the form (turn=<turn_id>).\n"
        "- Prefer concrete facts (drug names, dates, scores, UC bands) over generic restatement.\n"
        "- Do NOT fabricate; if a candidate turn is not relevant, omit it from evidence_turn_ids."
    )
    user = json.dumps(
        {"new_question": question, "candidate_turns": compact},
        ensure_ascii=False,
        indent=2,
    )[:_GAP_REPORT_JSON_MAX_CHARS]
    _log("🪞", f"Stage RETRO-REVIEW model={model} num_ctx={num_ctx} candidates={len(compact)}")
    _demo_banner("RETRO REVIEW", f"summarising {len(compact)} candidate prior turn(s) for context")
    _demo_kvs({"model": model, "num_ctx": num_ctx, "user_payload_chars": len(user),
               "n_candidate_turns": len(compact)})
    try:
        raw = _ollama_chat(
            url=ollama_url,
            model=model,
            system=system,
            user=user,
            temperature=temperature,
            timeout=timeout,
            num_ctx=num_ctx,
            demo_stage="retro_summarize",
        )
    except Exception as exc:  # noqa: BLE001
        _log("⚠️", f"retro-review call failed: {exc}")
        return {"retro_summary": "", "evidence_turn_ids": [], "n_turns_reviewed": len(compact)}
    parsed = force_json_dict(raw) or {}
    summary = str(parsed.get("retro_summary") or "").strip()
    ev = parsed.get("evidence_turn_ids") or []
    if not isinstance(ev, list):
        ev = []
    ev = [str(x).strip() for x in ev if str(x).strip()]
    if not summary:
        summary = "[retro JSON unparsed]\n\n" + (raw or "").strip()[:4000]
    _log("🪞", f"retro-review summary_chars={len(summary)} evidence_turn_ids={ev[:6]}")
    return {
        "retro_summary": summary[:6000],
        "evidence_turn_ids": ev,
        "n_turns_reviewed": len(compact),
        "raw_chars": len(raw),
    }


def _pick_graph_tool(
    *,
    question: str,
    router_plan: Dict[str, Any],
    graph_brief: str,
    patient_code_inventory: Optional[Dict[str, Any]],
    ollama_url: str,
    model: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
) -> Tuple[str, Dict[str, Any]]:
    system = (
        "You are a PTV graph routing assistant. Return STRICT JSON only, one object, no markdown.\n"
        "Pick exactly ONE tool from this list and provide args:\n"
        + ", ".join(_GRAPH_TOOLS)
        + "\n\nSchema:\n"
        '{"graph_tool":"<name>","graph_args":{...}}\n'
        "Rules:\n"
        "- patient_code_inventory (when present) already lists codes on this timeline with date spans;\n"
        "  prefer semantic_search, temporal_scan, bfs_expand, or code_index_lookup **detail** (exact key / contains)\n"
        "  over repeating a full-bucket list_keys unless the user needs a fresh slice.\n"
        "- graph_args must match the tool (see toolkit hints below).\n"
        "- Prefer semantic_search with an expanded clinical query, temporal_scan for date windows,\n"
        "  code_index_lookup for drug/ICD/RxNorm/LOINC strings, bfs_expand only if you have seed event_ids,\n"
        "  graph_stats or list_event_types for orientation.\n"
        "- Do not invent event_ids.\n\n"
        "Arg hints:\n"
        "- semantic_search: query (required), k optional default 12.\n"
        "- temporal_scan: start, end (ISO), event_types optional, query optional, limit optional.\n"
        "- code_index_lookup: bucket (drugs|rxnorm|icd|labs|loinc), key or key_contains, limit.\n"
        "- bfs_expand: seed_event_ids (list), depth, max_events, edge_kinds optional.\n"
        "- get_event: event_id.\n"
        "- graph_stats / list_event_types: {}.\n"
    )
    payload: Dict[str, Any] = {
        "user_question": question,
        "router_plan_summary": {
            "question_type": router_plan.get("question_type"),
            "semantic_query": router_plan.get("semantic_query"),
            "ts_terms": router_plan.get("ts_terms"),
        },
        "graph_orientation": graph_brief[:6000],
    }
    if patient_code_inventory is not None:
        payload["patient_code_inventory"] = patient_code_inventory
    user = json.dumps(payload, ensure_ascii=False, indent=2)
    _log("🧭", f"Probe graph-pick model={model} num_ctx={num_ctx}")
    _demo_banner("PROBE · GRAPH-PICK", "8B picks ONE PTV graph tool + JSON args from the user question")
    _demo_kvs({
        "model": model,
        "num_ctx": num_ctx,
        "candidates": ", ".join(_GRAPH_TOOLS),
        "router_question_type": router_plan.get("question_type"),
        "router_semantic_query": _abridge(router_plan.get("semantic_query"), 120),
        "router_ts_terms": list(router_plan.get("ts_terms") or [])[:6],
        "patient_code_inventory_chars": (
            len(json.dumps(patient_code_inventory, ensure_ascii=True))
            if patient_code_inventory is not None
            else 0
        ),
        "user_payload_chars": len(user),
    })
    raw = _ollama_chat(
        url=ollama_url,
        model=model,
        system=system,
        user=user,
        temperature=temperature,
        timeout=timeout,
        num_ctx=num_ctx,
        demo_stage="probe_graph_pick",
    )
    parsed = force_json_dict(raw) or {}
    name = str(parsed.get("graph_tool") or "").strip()
    args = parsed.get("graph_args") if isinstance(parsed.get("graph_args"), dict) else {}
    if name not in _GRAPH_TOOLS:
        _log("⚠️", f"Graph pick parse miss len={len(raw)} — defaulting to semantic_search")
        return "semantic_search", {"query": question, "k": 12}
    _log("🎯", f"Graph pick → {name} args_keys={list((args or {}).keys())}")
    return name, dict(args or {})


# ---------------------------------------------------------------------------
# Bayesian gate + phase (per reports/STRATEGY_BAYESIAN_PTV_UC_20260423.md)
# ---------------------------------------------------------------------------

_BAYES_HYPOTHESES = ("flare_30d", "progression_3mo", "taper_safety")

# Cheap regex pre-screen: skip the LLM gate entirely when the question is
# clearly NOT Bayesian-shaped. Saves a 3.2 call on the most common questions.
_BAYES_KEYWORD_RX = re.compile(
    r"\b(flare|flares?|progress(?:ion)?|taper(?:ing)?|risk|likelihood|probabilit(?:y|ies)|"
    r"safe(?:ty)?|de-?escalat\w*|escalat\w*|remission|relapse|stable|stability|"
    r"chance|odds|projected|forecast|next\s+\d+\s+(?:day|week|month))\b",
    re.IGNORECASE,
)


def _bayes_keyword_hint(question: str) -> Optional[str]:
    """Quick keyword guess at hypothesis_id (None = not obviously Bayesian)."""
    q = (question or "").lower()
    if "taper" in q or "de-escalat" in q or "deescalat" in q:
        return "taper_safety"
    if "progress" in q:
        return "progression_3mo"
    if any(t in q for t in ("flare", "flare risk", "next 30", "next month")):
        return "flare_30d"
    if _BAYES_KEYWORD_RX.search(q):
        return "flare_30d"
    return None


def _bayes_gate(
    *,
    question: str,
    eoh_prelude_qtype: Optional[str],
    ollama_url: str,
    model: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
    debug_router: bool = False,
) -> Dict[str, Any]:
    """Tiny 3.2 gate: should we run a Bayesian update? Which hypothesis_id?

    Always safe — on parse failure we fall back to the keyword hint (or skip).
    """
    hint = _bayes_keyword_hint(question)
    if hint is None:
        return {
            "wants_bayes": False,
            "hypothesis_id": None,
            "rationale": "no Bayesian keywords matched (regex pre-screen)",
            "method": "keyword_prescreen",
        }

    system = (
        "You are a tiny gating classifier. Decide whether a clinical user question is "
        "best answered with a closed-form Bayesian posterior update over the patient's "
        "PatientTimelineVision (PTV) graph.\n\n"
        "Reply with STRICT JSON ONLY (no markdown, one object):\n"
        '{"wants_bayes": true|false,\n'
        ' "hypothesis_id": "flare_30d" | "progression_3mo" | "taper_safety" | null,\n'
        ' "rationale": "<short reason>"}\n\n'
        "wants_bayes=true ONLY when the question asks for a probability, risk, rate, or\n"
        "safety judgement projected over time (e.g. \"flare risk in next 30 days\",\n"
        "\"will this patient progress in 3 months\", \"is it safe to taper now\").\n"
        "wants_bayes=false for descriptive / lookup / orientation questions.\n"
        "Pick the hypothesis_id from the allowed set; null if wants_bayes=false."
    )
    user = json.dumps(
        {
            "question": question,
            "eoh_prelude_question_type": eoh_prelude_qtype,
            "allowed_hypothesis_ids": list(_BAYES_HYPOTHESES),
            "keyword_hint": hint,
        },
        ensure_ascii=False,
        indent=2,
    )
    _log("🧪", f"Stage BAYES-GATE model={model} num_ctx={num_ctx} hint={hint}")
    _demo_banner(
        "BAYES GATE",
        "8B classifier decides if the question wants a closed-form posterior, and which one",
    )
    _demo_kvs({
        "model": model,
        "num_ctx": num_ctx,
        "keyword_pre_screen_hint": hint,
        "allowed_hypothesis_ids": ", ".join(_BAYES_HYPOTHESES),
        "user_payload_chars": len(user),
    })
    try:
        raw = _ollama_chat(
            url=ollama_url,
            model=model,
            system=system,
            user=user,
            temperature=temperature,
            timeout=timeout,
            num_ctx=num_ctx,
            demo_stage="bayes_gate",
        )
    except Exception as exc:  # noqa: BLE001
        _log("⚠️", f"bayes-gate call failed: {exc}; falling back to keyword hint")
        return {
            "wants_bayes": True,
            "hypothesis_id": hint,
            "rationale": f"keyword fallback after gate error: {exc}",
            "method": "keyword_fallback",
        }
    parsed = force_json_dict(raw) or {}
    if debug_router:
        _log("🐛", f"bayes-gate raw head=\n{(raw or '')[:600]}…")
    wants = bool(parsed.get("wants_bayes"))
    hid = parsed.get("hypothesis_id")
    if hid not in _BAYES_HYPOTHESES:
        hid = hint if wants else None
    rationale = str(parsed.get("rationale") or "").strip()[:240]
    _log(
        "🧪",
        f"bayes-gate wants_bayes={wants} hypothesis_id={hid!r}",
    )
    return {
        "wants_bayes": wants,
        "hypothesis_id": hid,
        "rationale": rationale or f"keyword hint = {hint}",
        "method": "llm_gate",
    }


def _patient_cohort_strata(gh: Any) -> Dict[str, Any]:
    """Best-effort cohort strata for MKG prior lookup.

    Pulls top-level fields from the loaded PTV graph; when none of the standard
    slots are present, returns an empty dict — the lookup will then fall through
    to the all-keys-empty match (or to weak default priors).
    """
    g = getattr(gh, "graph", None) or {}
    if not isinstance(g, dict):
        return {}
    md = (g.get("metadata") or {}) if isinstance(g.get("metadata"), dict) else {}
    cohort = (md.get("cohort") or {}) if isinstance(md.get("cohort"), dict) else {}
    out: Dict[str, Any] = {}
    for key in ("icd_family", "age_band", "sex", "phenotype", "disease_cluster"):
        for src in (cohort, md, g):
            v = src.get(key) if isinstance(src, dict) else None
            if v is None:
                continue
            sv = str(v).strip()
            if sv:
                out[key] = sv
                break
    return out


def _bayes_phase(
    *,
    question: str,
    gh: Any,
    probe_bundle: Dict[str, Any],
    ollama_url: str,
    model: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
    enable_bayes: bool,
    use_mkg_priors: bool = True,
    debug_router: bool = False,
) -> Dict[str, Any]:
    """Decide → run deterministic kernel → emit posteriors[].

    Returns a dict shaped like::

        {
            "gate":        {wants_bayes, hypothesis_id, rationale, method},
            "ran":         bool,
            "posteriors":  [<handoff posterior block>, ...],
            "tool_results":[<call_tool envelope>, ...],
        }
    """
    if not enable_bayes:
        return {
            "gate": {"wants_bayes": False, "hypothesis_id": None,
                     "rationale": "disabled via --no-bayes", "method": "disabled"},
            "ran": False,
            "posteriors": [],
            "tool_results": [],
        }

    eoh_prelude = probe_bundle.get("eoh_module_prelude") or {}
    gate = _bayes_gate(
        question=question,
        eoh_prelude_qtype=eoh_prelude.get("question_type"),
        ollama_url=ollama_url,
        model=model,
        temperature=temperature,
        timeout=timeout,
        num_ctx=num_ctx,
        debug_router=debug_router,
    )
    if not gate.get("wants_bayes") or not gate.get("hypothesis_id"):
        return {
            "gate": gate,
            "ran": False,
            "posteriors": [],
            "tool_results": [],
            "mkg_prior": None,
            "cohort_strata": _patient_cohort_strata(gh) if use_mkg_priors else {},
        }

    # Use the probe's working set (top-N by code-lookup / final-answer hits when
    # available; otherwise fall back to the whole graph by passing None).
    working_set: List[str] = []
    ptv_sem = (probe_bundle.get("ptv_semantic_search") or {}).get("result") or {}
    for r in (ptv_sem.get("results") or [])[:40]:
        if isinstance(r, dict) and r.get("event_id"):
            working_set.append(r["event_id"])
    graph_out = (probe_bundle.get("graph_tool_result") or {}).get("result") or {}
    for r in (graph_out.get("events") or graph_out.get("entries") or [])[:40]:
        if isinstance(r, dict) and r.get("event_id"):
            eid = r["event_id"]
            if eid not in working_set:
                working_set.append(eid)

    args: Dict[str, Any] = {"hypothesis_id": gate["hypothesis_id"]}
    if working_set:
        args["evidence_event_ids"] = working_set

    cohort_strata = _patient_cohort_strata(gh) if use_mkg_priors else {}
    mkg_prior: Optional[Dict[str, Any]] = None
    if use_mkg_priors:
        try:
            mkg_prior = fetch_mkg_bayes_prior(
                gate["hypothesis_id"],
                cohort_strata=cohort_strata,
            )
        except Exception as exc:  # noqa: BLE001
            _log("⚠️", f"MKG prior lookup raised: {exc}")
            mkg_prior = None
    if mkg_prior:
        args["prior"] = mkg_prior
        _log(
            "🧬",
            f"Bayes prior source=MKG strata={cohort_strata or '<none>'} "
            f"family={mkg_prior.get('family')}",
        )
    else:
        _log(
            "🧬",
            f"Bayes prior source=weak (default per strategy doc) "
            f"strata_seen={cohort_strata or '<none>'}",
        )

    _log(
        "🧮",
        f"Stage BAYES-UPDATE hypothesis={gate['hypothesis_id']} "
        f"working_set={len(working_set)} (none⇒whole graph)",
    )
    res = call_tool("bayesian_update_uc", gh, args)
    if not res.get("ok"):
        _log("⚠️", f"bayesian_update_uc error: {res.get('error', res)}")
        return {
            "gate": gate,
            "ran": False,
            "posteriors": [],
            "tool_results": [res],
        }
    payload = res.get("result") or {}
    block = payload.get("posterior") or {}
    uc_inner = (block.get("uc") or {}) if isinstance(block, dict) else {}
    pe = uc_inner.get("point_estimate")
    band = uc_inner.get("band_90") or [None, None]
    _log(
        "✅",
        f"Bayesian UC {gate['hypothesis_id']}: mean={pe} band_90={band} "
        f"confidence={uc_inner.get('confidence_label')!r}",
    )
    return {
        "gate": gate,
        "ran": True,
        "posteriors": [block] if block else [],
        "tool_results": [res],
        "mkg_prior": mkg_prior,
        "cohort_strata": cohort_strata,
    }


def _gap_phase(
    *,
    question: str,
    probe_bundle: Dict[str, Any],
    gh: Any,
    ollama_url: str,
    model: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
    top_k: int,
    embed_model: str,
    gap_sources: Optional[List[str]],
    text_chars: int,
    gap_heuristic: bool = True,
    gap_heuristic_strength: float = 1.0,
    mkg_source_coverage: bool = True,
    mkg_min_ann_score: float = 0.12,
    mkg_min_ts_score: float = 0.02,
) -> Dict[str, Any]:
    metrics = _probe_metrics(probe_bundle)
    bayes_block = probe_bundle.get("bayes") or {}
    posteriors = bayes_block.get("posteriors") or []
    metrics["bayes_ran"] = bool(bayes_block.get("ran"))
    metrics["bayes_hypothesis_id"] = ((bayes_block.get("gate") or {}).get("hypothesis_id"))
    metrics["bayes_n_posteriors"] = len(posteriors)

    system = (
        "You are the GAP agent for a hybrid PTV + MKG retrieval pipeline.\n"
        "You receive JSON: user question, probe_metrics (summary), full probe bundle (MKG + PTV + graph + bayes).\n"
        "The probe bundle includes pre_router_code_inventory when enabled: indexed patient codes\n"
        "with first/last dates (from metadata.code_index) — use for gap analysis and follow-ups.\n"
        "When probe.bayes.posteriors is non-empty, treat each Uncertainty Carrier (UC) as a STARTING\n"
        "Bayesian belief, not a final answer. Per STRATEGY_BAYESIAN_PTV_UC_20260423.md §5.2 your job\n"
        "includes flagging regime changes (band widening, evidence outside prior support, contradictory\n"
        "evidence) before synthesis. Cite the posterior `point_estimate`, `band_90`, and `evidence_event_ids`.\n\n"
        "OUTPUT: Reply with a SINGLE JSON object only. No markdown fences, no prose before or after.\n"
        "Schema:\n"
        "{\n"
        '  "follow_ptv_semantic_query": null,\n'
        '  "follow_ts_terms": [],\n'
        '  "follow_graph_tool": null,\n'
        '  "follow_graph_args": {},\n'
        '  "follow_bayes_hypothesis_id": null,\n'
        '  "gap_report": "required markdown string"\n'
        "}\n"
        f"follow_graph_tool must be null or one of: {', '.join(_GRAPH_TOOLS)}.\n"
        "follow_bayes_hypothesis_id, when set, must be one of: "
        f"{', '.join(_BAYES_HYPOTHESES)} (or null). Use it ONLY when the probe missed a relevant\n"
        "Bayesian update or you want a second hypothesis (e.g. probe ran flare_30d, you want taper_safety).\n\n"
        "Rules:\n"
        "- probe_metrics.mkg_jaccard is overlap between dense (semantic) and BM25 (ts_terms) hit *ids*.\n"
        "  If mkg_jaccard is 0.0 but both mkg_semantic_hits and mkg_ts_hits are > 0, the two lanes disagree;\n"
        "  you SHOULD set at least one of: follow_ts_terms (1–2 NEW tokens from the user question),\n"
        "  follow_ptv_semantic_query (narrower retrieval), or follow_graph_tool (e.g. code_index_lookup on drugs).\n"
        "- follow_ts_terms: at most TWO strings; prefer tokens the user said explicitly that probe ts_terms may have missed.\n"
        "- follow_ptv_semantic_query: optional ONE extra PTV semantic query if probe PTV context is thin or user asks new angles.\n"
        "- follow_graph_tool: optional ONE extra graph tool; use null if not needed.\n"
        "- gap_report is REQUIRED: what probe covered, gaps, contradictions, what evidence is still missing.\n"
        "- If posteriors[] is present, gap_report MUST cite each UC's point_estimate and band_90 and\n"
        "  comment on whether the evidence_event_ids look sufficient (regime check).\n"
        "- Keep gap_report under 700 words.\n"
    )
    user = json.dumps(
        {
            "user_question": question,
            "probe_metrics": metrics,
            "probe": probe_bundle,
        },
        default=str,
        indent=2,
    )[:_GAP_REPORT_JSON_MAX_CHARS]
    _log("🔎", f"Stage GAP model={model} num_ctx={num_ctx} user_json_chars={len(user)}")
    _demo_banner(
        "GAP REVIEW",
        "qwen-14b reviews the curated probe bundle, flags gaps, may request follow-ups",
    )
    _demo_kvs({
        "model": model,
        "num_ctx": num_ctx,
        "user_payload_chars": len(user),
        "system_prompt_chars": len(system),
        "probe.mkg_jaccard": metrics.get("mkg_jaccard"),
        "probe.mkg_semantic_hits": metrics.get("mkg_semantic_hits"),
        "probe.mkg_ts_hits": metrics.get("mkg_ts_hits"),
        "probe.ptv_semantic_result_count": metrics.get("ptv_semantic_result_count"),
        "probe.bayes_n_posteriors": metrics.get("bayes_n_posteriors"),
        "probe.bayes_hypothesis_id": metrics.get("bayes_hypothesis_id"),
    })
    raw = _ollama_chat(
        url=ollama_url,
        model=model,
        system=system,
        user=user,
        temperature=temperature,
        timeout=timeout,
        num_ctx=num_ctx,
        demo_stage="gap_review",
    )
    _log("🔎", f"GAP raw response chars={len(raw)} preview={raw[:120]!r}…")

    parsed = force_json_dict(raw) or {}
    if not parsed:
        head = (raw or "")[:400].replace("\n", "\\n")
        _log("⚠️", f"GAP JSON parse failed — raw_head400={head!r}; using raw text as gap_report fallback")
    follow_sem = _norm_gap_follow_field(parsed.get("follow_ptv_semantic_query"))
    if not isinstance(follow_sem, str):
        follow_sem = None
    follow_terms = parsed.get("follow_ts_terms") or []
    if not isinstance(follow_terms, list):
        follow_terms = []
    follow_terms = [
        str(t).strip()
        for t in follow_terms
        if str(t).strip() and str(t).strip().lower() not in ("null", "none")
    ][:2]
    fg_tool = _norm_gap_follow_field(parsed.get("follow_graph_tool"))
    fg_args = parsed.get("follow_graph_args") if isinstance(parsed.get("follow_graph_args"), dict) else {}
    gap_report = str(parsed.get("gap_report") or "").strip()
    if not gap_report:
        gap_report = (raw or "").strip() or "(no gap_report)"
        if gap_report != "(no gap_report)":
            gap_report = "[gap JSON unparsed — model prose below]\n\n" + gap_report[:12000]

    model_wants_graph = bool(fg_tool and str(fg_tool).strip() in _GRAPH_TOOLS)
    model_wants_any = bool(follow_terms) or bool(follow_sem and follow_sem.strip()) or model_wants_graph

    max_ht = max(1, int(round(2 * min(1.0, float(gap_heuristic_strength))))) if gap_heuristic_strength > 0 else 0
    if (
        gap_heuristic
        and gap_heuristic_strength > 0.0
        and not model_wants_any
        and metrics.get("mkg_ok")
        and not metrics.get("mkg_skipped")
    ):
        j = float(metrics.get("mkg_jaccard") or 0.0)
        n_sem = int(metrics.get("mkg_semantic_hits") or 0)
        n_ts = int(metrics.get("mkg_ts_hits") or 0)
        if j == 0.0 and (n_sem > 0 or n_ts > 0):
            router_ts = list((probe_bundle.get("router_plan") or {}).get("ts_terms") or [])
            extra = _heuristic_ts_terms_from_question(question, router_ts, max_terms=max_ht)
            if extra:
                follow_terms = extra
                _log(
                    "🔧",
                    "Heuristic GAP: mkg_jaccard=0 with MKG lanes thin/disjoint → "
                    f"follow_ts_terms={follow_terms!r}",
                )
            else:
                follow_sem = (
                    question.strip()
                    + " medications drugs concomitant confounding adverse reactions alternatives"
                ).strip()[:480]
                _log(
                    "🔧",
                    "Heuristic GAP: mkg_jaccard=0, no extra question tokens → "
                    "follow_ptv_semantic_query (enriched)",
                )
        elif j == 0.0:
            follow_sem = (question.strip() + " clinical evidence differential diagnosis").strip()[:420]
            _log("🔧", "Heuristic GAP: mkg_jaccard=0 (sparse MKG) → follow_ptv_semantic_query")

    if (
        gap_heuristic
        and gap_heuristic_strength > 0.0
        and metrics.get("mkg_ok")
        and not metrics.get("mkg_skipped")
        and float(metrics.get("mkg_jaccard") or 0.0) == 0.0
    ):
        model_wants_any = (
            bool(follow_terms)
            or bool(isinstance(follow_sem, str) and follow_sem.strip())
            or model_wants_graph
        )
        if not model_wants_any:
            router_ts = list((probe_bundle.get("router_plan") or {}).get("ts_terms") or [])
            follow_terms = _heuristic_ts_terms_from_question(question, router_ts, max_terms=max(2, max_ht))
            if not follow_terms:
                follow_sem = (question.strip() + " evidence gaps confounders").strip()[:400]
            _log("🔧", "Heuristic GAP: forced minimal follow-up (jaccard=0 guard)")
            model_wants_any = True

    follow_mkg: Dict[str, Any] = {}
    if follow_terms:
        _log("🔁", f"GAP follow-up MKG ts_terms={follow_terms!r}")
        sq = str(follow_sem or probe_bundle.get("router_plan", {}).get("semantic_query") or question)
        follow_mkg = _mkg_retrieve_bundle(
            semantic_query=sq,
            ts_terms=follow_terms,
            top_k=top_k,
            embed_model=embed_model,
            sources=gap_sources,
            text_chars=text_chars,
            source_coverage=mkg_source_coverage,
            min_ann_score=mkg_min_ann_score,
            min_ts_score=mkg_min_ts_score,
        )

    follow_ptv = None
    if isinstance(follow_sem, str) and follow_sem.strip():
        _log("🔁", "GAP follow-up PTV semantic_search")
        follow_ptv = call_tool("semantic_search", gh, {"query": follow_sem.strip(), "k": 12})

    follow_graph = None
    if fg_tool and str(fg_tool).strip() in _GRAPH_TOOLS:
        _log("🔁", f"GAP follow-up graph tool={fg_tool!r}")
        follow_graph = call_tool(str(fg_tool).strip(), gh, dict(fg_args or {}))

    follow_bayes = None
    fb_hid = _norm_gap_follow_field(parsed.get("follow_bayes_hypothesis_id"))
    if fb_hid and str(fb_hid).strip() in _BAYES_HYPOTHESES:
        already = {p.get("hypothesis_id") for p in posteriors if isinstance(p, dict)}
        if str(fb_hid).strip() in already:
            _log("⏭️", f"GAP follow_bayes_hypothesis_id={fb_hid!r} already present in probe.bayes.posteriors")
        else:
            _log("🔁", f"GAP follow-up bayesian_update_uc hypothesis={fb_hid!r}")
            follow_bayes = call_tool(
                "bayesian_update_uc",
                gh,
                {"hypothesis_id": str(fb_hid).strip()},
            )

    if not follow_mkg and not follow_ptv and not follow_graph and not follow_bayes:
        if model_wants_graph and fg_tool:
            _log("⚠️", f"GAP follow_graph_tool not executed (invalid tool?): {fg_tool!r}")
        else:
            _log("⏭️", "GAP: no follow-up MKG/PTV/graph/bayes executions")

    _log("✅", f"GAP phase done gap_report_chars={len(gap_report)}")
    return {
        "raw_gap_json": parsed,
        "raw_gap_text": raw[:20000],
        "gap_report": gap_report,
        "follow_ptv_semantic": follow_ptv,
        "follow_mkg": follow_mkg,
        "follow_graph": follow_graph,
        "follow_bayes": follow_bayes,
        "probe_metrics": metrics,
    }


def _report_phase(
    *,
    question: str,
    probe_bundle: Dict[str, Any],
    gap_bundle: Dict[str, Any],
    ollama_url: str,
    model: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
) -> str:
    system = (
        "You are a clinical synthesis assistant. You receive structured JSON from a "
        "probe→gap hybrid run (PTV graph tools + MKG rag_corpus hits + optional Bayesian UCs). "
        "probe_context may include pre_router_code_inventory (patient codes + date spans) "
        "and probe_context.bayes.posteriors[] when the question is risk/probability shaped. "
        "Produce one markdown answer to the user question.\n\n"
        "Rules:\n"
        "- Ground claims in supplied hit ids (MKG: id/source; PTV: event_ids from tool results).\n"
        "- Cite uncertainty where evidence is thin.\n"
        "- When probe_context.bayes.posteriors is non-empty, ALWAYS report the posterior\n"
        "  point_estimate and 90% band per hypothesis_id (e.g. 'flare risk in next 30 days = 0.36,\n"
        "  90% band [0.17, 0.57]') and cite the underlying evidence_event_ids. Per the Bayesian\n"
        "  strategy doc, the UC IS the answer for that question class — do not hand-wave it.\n"
        "- Distinguish posterior_mean (point) from band (uncertainty); state the prior source.\n"
        "- Do not describe internal pipeline stage names unless useful; focus on patient-relevant synthesis.\n"
        "- Keep under 1600 words unless the question requires detail.\n"
    )
    payload = {
        "user_question": question,
        "probe_context": probe_bundle,
        "gap_context": gap_bundle,
    }
    user = json.dumps(payload, default=str, indent=2)[:50000]
    bayes_block = (probe_bundle or {}).get("bayes") or {}
    n_post = len(bayes_block.get("posteriors") or [])
    mkg_block = (probe_bundle or {}).get("mkg") or {}
    n_mkg_sem = len(mkg_block.get("semantic_hits") or [])
    n_mkg_ts = len(mkg_block.get("ts_hits") or [])
    _log("📝", f"Stage REPORT model={model} num_ctx={num_ctx} context_chars={len(user)}")
    _demo_banner(
        "REPORT SYNTHESIS",
        "qwen-14b synthesises the final markdown answer from probe + gap + posteriors",
    )
    _demo_kvs({
        "model": model,
        "num_ctx": num_ctx,
        "user_payload_chars": len(user),
        "system_prompt_chars": len(system),
        "probe.mkg_semantic_hits": n_mkg_sem,
        "probe.mkg_ts_hits": n_mkg_ts,
        "probe.bayes_n_posteriors": n_post,
        "gap.gap_report_chars": len((gap_bundle or {}).get("gap_report") or ""),
    })
    out = _ollama_chat(
        url=ollama_url,
        model=model,
        system=system,
        user=user,
        temperature=temperature,
        timeout=timeout,
        num_ctx=num_ctx,
        demo_stage="report_synth",
    )
    _log("✅", f"REPORT done out_chars={len(out or '')}")
    return out


def _run_probe(
    *,
    question: str,
    gh: Any,
    ollama_url: str,
    probe_model: str,
    probe_num_ctx: int,
    graph_pick_model: str,
    graph_pick_num_ctx: int,
    router_max_sources: int,
    router_max_modules: int,
    router_temperature: float,
    router_min_terms: int,
    debug_router: bool,
    temperature: float,
    timeout: float,
    top_k: int,
    embed_model: str,
    enable_mkg: bool,
    text_chars: int,
    enable_code_inventory: bool,
    code_inventory_compact: bool,
    code_inventory_router_json_max: int,
    code_inventory_graph_json_max: int,
    retro_bundle: Optional[Dict[str, Any]] = None,
    mkg_source_coverage: bool = True,
    mkg_min_ann_score: float = 0.12,
    mkg_min_ts_score: float = 0.02,
    enable_bayes: bool = True,
    bayes_gate_model: Optional[str] = None,
    bayes_gate_num_ctx: int = 8192,
    bayes_use_mkg_prior: bool = True,
) -> Dict[str, Any]:
    _demo_banner("PROBE", "curate context: code inventory → graph_stats → EoH prelude → router → MKG → graph tool → PTV semantic")
    _demo_stage_start("probe_total")
    inv_full: Optional[Dict[str, Any]] = None
    inv_for_router: Optional[Dict[str, Any]] = None
    inv_for_graph: Optional[Dict[str, Any]] = None
    if enable_code_inventory:
        _log("📇", "Stage PROBE — patient code_index inventory (pre-router; same index as code_index_lookup)")
        _demo_banner(
            "PROBE · CODE INVENTORY",
            "scan metadata.code_index for every code on this patient's timeline",
        )
        inv_full = build_patient_code_inventory(gh)
        slim_base = strip_n_events(inv_full) if code_inventory_compact else inv_full
        inv_for_router = fit_code_inventory_to_budget(slim_base, code_inventory_router_json_max)
        inv_for_graph = fit_code_inventory_to_budget(slim_base, code_inventory_graph_json_max)
        router_chars = len(json.dumps(inv_for_router, ensure_ascii=True))
        graph_chars = len(json.dumps(inv_for_graph, ensure_ascii=True))
        _log(
            "📇",
            "code_index inventory "
            f"n_keys={inv_full.get('n_keys_total')} "
            f"router_slice_json={router_chars} "
            f"graph_pick_slice_json={graph_chars}",
        )
        _demo_kvs({
            "n_keys_total": inv_full.get("n_keys_total"),
            "n_keys_per_bucket": inv_full.get("n_keys_per_bucket"),
            "graph_timeline_range": inv_full.get("graph_timeline_range"),
            "router_slice_json_chars": router_chars,
            "graph_pick_slice_json_chars": graph_chars,
        })

    _log("🛰️", "Stage PROBE — graph_stats for router clinical_context")
    _demo_banner("PROBE · GRAPH_STATS", "snapshot of the in-memory PTV graph: counts, types, date range")
    graph_stats = call_tool("graph_stats", gh, {})
    brief = json.dumps(graph_stats.get("result") or graph_stats, default=str)[:8000]
    gs = graph_stats.get("result") or {}
    _demo_kvs({
        "n_events": gs.get("n_events"),
        "n_event_types": gs.get("n_event_types"),
        "event_type_counts": gs.get("event_type_counts"),
        "date_range": gs.get("date_range"),
        "code_index_summary": gs.get("code_index_summary"),
        "graph_hash": gs.get("graph_hash"),
    })

    retro_summary_text = ""
    if retro_bundle and retro_bundle.get("retro_summary"):
        retro_summary_text = str(retro_bundle.get("retro_summary") or "")

    eoh_prelude = _eoh_module_route_prelude(
        question=question,
        patient_state_summary={
            "graph_stats": graph_stats.get("result") or graph_stats,
            "code_index_summary": (inv_full or {}).get("summary") if isinstance(inv_full, dict) else {},
        },
        ollama_url=ollama_url,
        model=probe_model,
        temperature=router_temperature,
        timeout=timeout,
        num_ctx=probe_num_ctx,
        debug_router=debug_router,
    )
    _log(
        "🧭",
        f"EOH prelude qtype={eoh_prelude.get('question_type')} "
        f"modules={len(eoh_prelude.get('selected_modules') or [])}",
    )
    _demo_kvs({
        "eoh.question_type": eoh_prelude.get("question_type"),
        "eoh.question_type_explanation": _abridge(eoh_prelude.get("question_type_explanation"), 110),
        "eoh.selected_modules": eoh_prelude.get("selected_modules"),
        "eoh.module_plan_steps": [
            (s or {}).get("step") for s in (eoh_prelude.get("module_plan") or [])
        ][:6],
    })

    _log("🧭", "Stage PROBE — plan_route (semantic_query + ts_terms + sources)")
    _demo_banner(
        "PROBE · ROUTER (plan_route)",
        "8B source-router rewrites the question into ANN semantic_query + per-term ts_terms + source list",
    )
    route = plan_route(
        question,
        ollama_url=ollama_url,
        model=probe_model,
        num_ctx=probe_num_ctx,
        timeout=timeout,
        temperature=router_temperature,
        clinical_context=brief,
        patient_code_inventory=inv_for_router,
        prior_session_summary=retro_summary_text or None,
        max_sources=router_max_sources,
        max_modules=router_max_modules,
        router_min_terms=router_min_terms,
        debug_router=debug_router,
    )
    if not str(route.get("semantic_query") or "").strip():
        route["semantic_query"] = question
        _log("⚠️", "router_plan.semantic_query empty — fell back to raw user question")
    sources = _router_sources(route)
    route_mods = _router_modules(route)
    prelude_mods = [str(m).strip() for m in (eoh_prelude.get("selected_modules") or []) if str(m).strip()]
    if prelude_mods:
        merged_mods = []
        for m in prelude_mods + route_mods:
            if m in MODULE_INDEX and m not in merged_mods:
                merged_mods.append(m)
        route["selected_modules"] = [
            {"module_id": m, "priority": i + 1, "why": "eoh_prelude+source_router_merge"}
            for i, m in enumerate(merged_mods)
        ]
    _log(
        "🧭",
        f"Router qtype={route.get('question_type')} ts_terms={len(route.get('ts_terms') or [])} "
        f"sources={len(sources or [])} modules={len(_router_modules(route))}",
    )
    _demo_kvs({
        "router.question_type": route.get("question_type"),
        "router.semantic_query": _abridge(route.get("semantic_query"), 140),
        "router.ts_terms": list(route.get("ts_terms") or [])[:10],
        "router.selected_sources": sources,
        "router.selected_modules": _router_modules(route),
    })

    mkg: Dict[str, Any] = {"skipped": True}
    if enable_mkg:
        _demo_banner(
            "PROBE · MKG RETRIEVAL",
            "dense (embedding_local + BGE) + per-term Postgres FTS over public.rag_corpus",
        )
        mkg = _mkg_retrieve_bundle(
            semantic_query=str(route.get("semantic_query") or question),
            ts_terms=list(route.get("ts_terms") or []),
            top_k=top_k,
            embed_model=embed_model,
            sources=sources,
            text_chars=text_chars,
            source_coverage=mkg_source_coverage,
            min_ann_score=mkg_min_ann_score,
            min_ts_score=mkg_min_ts_score,
            selected_source_rows=_router_source_rows(route),
        )
    else:
        _log("⏭️", "Stage PROBE — MKG skipped (--no-mkg)")
    if enable_mkg and not mkg.get("skipped"):
        _demo_kvs({
            "mkg.semantic_hits": len(mkg.get("semantic_hits") or []),
            "mkg.ts_hits": len(mkg.get("ts_hits") or []),
            "mkg.id_overlap_jaccard": (mkg.get("overlap") or {}).get("jaccard"),
            "mkg.ts_per_term_count": mkg.get("ts_per_term_count"),
            "mkg.ts_or_fallback_used": mkg.get("ts_or_fallback_used"),
            "mkg.source_expansion_mode": mkg.get("source_expansion_mode"),
            "mkg.per_source_ts_term_keys": list((mkg.get("per_source_ts_terms_used") or {}).keys()),
            "mkg.ts_per_source_hit_count": mkg.get("ts_per_source_hit_count"),
            "mkg.source_coverage_pinned_sem": (mkg.get("source_coverage") or {}).get("pinned_semantic_ids"),
            "mkg.source_coverage_pinned_ts": (mkg.get("source_coverage") or {}).get("pinned_ts_ids"),
        })
        for src, terms in (mkg.get("per_source_ts_terms_used") or {}).items():
            _demo_kv(
                f"mkg.ts_terms[{src}]",
                ", ".join(str(t) for t in (terms or [])[:8]) +
                ("" if len(terms or []) <= 8 else f" (+{len(terms) - 8})"),
            )
        for h in (mkg.get("semantic_hits") or [])[:3]:
            _demo_kv(
                "mkg.sem.top",
                f"#{h.get('id')} src={h.get('source')!r} "
                f"score={(h.get('score') or 0):.3f} title={_abridge(h.get('title'), 80)!r}",
            )
        for h in (mkg.get("ts_hits") or [])[:3]:
            _demo_kv(
                "mkg.ts.top",
                f"#{h.get('id')} src={h.get('source')!r} "
                f"score={(h.get('score') or 0):.3f} title={_abridge(h.get('title'), 80)!r}",
            )

    g_tool, g_args = _pick_graph_tool(
        question=question,
        router_plan=route,
        graph_brief=brief,
        patient_code_inventory=inv_for_graph,
        ollama_url=ollama_url,
        model=graph_pick_model,
        temperature=temperature,
        timeout=timeout,
        num_ctx=graph_pick_num_ctx,
    )
    _log("🔧", f"Stage PROBE — graph tool call {g_tool}")
    _demo_banner("PROBE · GRAPH TOOL CALL", f"executing deterministic PTV tool: {g_tool}({g_args})")
    graph_out = call_tool(g_tool, gh, g_args)
    if not graph_out.get("ok"):
        _log("⚠️", f"Graph tool error: {graph_out.get('error', graph_out)}")
    if graph_out.get("ok"):
        gtres = graph_out.get("result") or {}
        events_list = gtres.get("events") or gtres.get("entries") or gtres.get("keys") or []
        _demo_kvs({
            "graph_tool": g_tool,
            "graph_args": g_args,
            "result.n_events_or_keys": len(events_list) if isinstance(events_list, list) else "?",
        })
        for r in (events_list if isinstance(events_list, list) else [])[:5]:
            if isinstance(r, dict):
                if r.get("event_id"):
                    _demo_kv(
                        "graph.top",
                        f"{r.get('event_id'):<22} {r.get('event_type', '?'):<10} "
                        f"{r.get('timestamp', '?')} {_abridge(r.get('title') or r.get('one_line'), 60)!r}",
                    )
                else:
                    _demo_kv("graph.top", _abridge(r, 110))

    _log("🔍", "Stage PROBE — PTV semantic_search (router semantic_query)")
    _demo_banner(
        "PROBE · PTV SEMANTIC SEARCH",
        "sentence-transformer cosine search over event text using the router's expanded semantic_query",
    )
    ptv_sem = call_tool(
        "semantic_search",
        gh,
        {"query": str(route.get("semantic_query") or question), "k": min(28, max(16, top_k * 2))},
    )
    if not ptv_sem.get("ok"):
        _log("⚠️", f"PTV semantic_search error: {ptv_sem.get('error', ptv_sem)}")
    if ptv_sem.get("ok"):
        psem = ptv_sem.get("result") or {}
        ptv_results = psem.get("results") or []
        _demo_kvs({
            "ptv_semantic.k": psem.get("k"),
            "ptv_semantic.n_results": len(ptv_results),
            "ptv_semantic.expanded_query": _abridge(psem.get("query"), 140),
        })
        for r in ptv_results[:5]:
            _demo_kv(
                "ptv.top",
                f"{r.get('event_id'):<22} {(r.get('event_type') or '?'):<10} "
                f"{(r.get('timestamp') or '?')} score={r.get('score')} "
                f"{_abridge(r.get('title') or r.get('one_line'), 60)!r}",
            )

    pre_bayes_bundle = {
        "router_plan": route,
        "mkg": mkg,
        "ptv_semantic_search": ptv_sem,
        "graph_tool": g_tool,
        "graph_args": g_args,
        "graph_tool_result": graph_out,
        "pre_router_code_inventory": inv_full,
        "eoh_module_prelude": eoh_prelude,
        "retro": retro_bundle,
    }

    _demo_banner(
        "PROBE · BAYESIAN PHASE",
        "deterministic closed-form posterior — gate (8B) → bayesian_update_uc tool → UC",
    )
    bayes = _bayes_phase(
        question=question,
        gh=gh,
        probe_bundle=pre_bayes_bundle,
        ollama_url=ollama_url,
        model=bayes_gate_model or probe_model,
        temperature=router_temperature,
        timeout=timeout,
        num_ctx=bayes_gate_num_ctx,
        enable_bayes=enable_bayes,
        use_mkg_priors=bayes_use_mkg_prior,
        debug_router=debug_router,
    )
    if bayes.get("ran"):
        for p in bayes.get("posteriors") or []:
            uc = (p or {}).get("uc") or {}
            band = uc.get("band_90") or [None, None]
            ls = uc.get("likelihood_summary") or {}
            _demo_kvs({
                "bayes.hypothesis_id": p.get("hypothesis_id"),
                "bayes.point_estimate": uc.get("point_estimate"),
                "bayes.band_90": f"[{band[0]}, {band[1]}]",
                "bayes.confidence": f"{uc.get('confidence_label')} ({uc.get('confidence')})",
                "bayes.method": uc.get("method"),
                "bayes.spec_hash": uc.get("spec_hash"),
                "bayes.prior": uc.get("prior"),
                "bayes.posterior_params": uc.get("posterior_params"),
                "bayes.likelihood.rule_hits": ls.get("rule_hits"),
                "bayes.likelihood.n_pos / n_neg / n_skip": (
                    f"{ls.get('n_pos')} / {ls.get('n_neg')} / {ls.get('n_skip')}"
                ),
                "bayes.evidence_event_ids (n)": len(uc.get("evidence_event_ids") or []),
            })

    _demo_stage_end("probe_total")
    _log("✅", "Stage PROBE complete")
    return {
        **pre_bayes_bundle,
        "bayes": bayes,
    }


def _append_probe_turn_to_session(
    session: SessionLog,
    q: str,
    probe: Dict[str, Any],
    gap: Dict[str, Any],
    report: str,
) -> Dict[str, Any]:
    router_plan = probe.get("router_plan") or {}
    mkg_block = probe.get("mkg") or {}
    bayes_block = probe.get("bayes") or {}
    bayes_gate = bayes_block.get("gate") or {}
    return session.append_turn(
        {
            "question": q,
            "router_plan_semantic_query": str(router_plan.get("semantic_query") or ""),
            "router_ts_terms": list(router_plan.get("ts_terms") or []),
            "router_sources": list(_router_sources(router_plan) or []),
            "router_modules": list(_router_modules(router_plan) or []),
            "router_question_type": router_plan.get("question_type"),
            "mkg_jaccard": (mkg_block.get("overlap") or {}).get("jaccard"),
            "mkg_semantic_hit_count": len(mkg_block.get("semantic_hits") or []),
            "mkg_ts_hit_count": len(mkg_block.get("ts_hits") or []),
            "ts_or_fallback_used": mkg_block.get("ts_or_fallback_used"),
            "graph_tool": probe.get("graph_tool"),
            "graph_args": probe.get("graph_args"),
            "gap_report": gap.get("gap_report") or "",
            "final_report": report or "",
            "retro": probe.get("retro"),
            "bayes_wants": bool(bayes_gate.get("wants_bayes")),
            "bayes_hypothesis_id": bayes_gate.get("hypothesis_id"),
            "bayes_ran": bool(bayes_block.get("ran")),
            "posteriors": bayes_block.get("posteriors") or [],
        }
    )


# --------------------------------------------------------------------------- #
# Demo-mode end-of-turn printer (final report + structured evidence dump)
# --------------------------------------------------------------------------- #

def _section(title: str, *, char: str = "=") -> None:
    """Loud section header used by the demo summary."""
    bar = char * _DEMO_BAR_WIDTH
    print(f"\n{bar}")
    print(f"  {title}")
    print(bar)


def _gather_cited_event_ids(
    probe: Dict[str, Any], gap: Dict[str, Any]
) -> List[str]:
    """Collect every PTV event_id that appears in posteriors / tool results."""
    ids: List[str] = []
    seen: set[str] = set()

    def _add(eid: Any) -> None:
        if isinstance(eid, str) and eid and eid not in seen:
            seen.add(eid)
            ids.append(eid)

    bayes = probe.get("bayes") or {}
    for p in bayes.get("posteriors") or []:
        for eid in (p.get("uc") or {}).get("evidence_event_ids") or []:
            _add(eid)

    psem = (probe.get("ptv_semantic_search") or {}).get("result") or {}
    for r in (psem.get("results") or [])[:20]:
        if isinstance(r, dict):
            _add(r.get("event_id"))

    gtres = (probe.get("graph_tool_result") or {}).get("result") or {}
    for r in (gtres.get("events") or gtres.get("entries") or [])[:20]:
        if isinstance(r, dict):
            _add(r.get("event_id"))

    fp = (gap.get("follow_ptv_semantic") or {}).get("result") or {}
    for r in (fp.get("results") or [])[:20]:
        if isinstance(r, dict):
            _add(r.get("event_id"))

    fg = (gap.get("follow_graph") or {}).get("result") or {}
    for r in (fg.get("events") or fg.get("entries") or [])[:20]:
        if isinstance(r, dict):
            _add(r.get("event_id"))

    return ids


def _print_demo_summary(
    *,
    question: str,
    probe: Dict[str, Any],
    gap: Dict[str, Any],
    report: str,
    turn_elapsed: float,
    gh: Any,
) -> None:
    """End-of-turn printer for ``--demo`` mode: final report first, then evidence.

    Per the demo brief: the entire final report is printed in full, **followed by
    every piece of supporting evidence** (Bayesian posteriors, MKG hits, PTV hits,
    graph tool results, cited event cards, gap report, tool/LLM call ledger).
    Everything goes to stdout so it can be screen-recorded or piped.
    """
    _section("FINAL REPORT", char="█")
    print(report or "(empty)")

    _section("EVIDENCE", char="█")

    # 1) Question + run header --------------------------------------------------
    print("\n[run]")
    print(f"  question: {question}")
    print(f"  turn_elapsed: {turn_elapsed:.2f}s")
    print(f"  graph_hash: {getattr(gh, 'graph_hash', '?')}")
    print(f"  graph_path: {getattr(gh, 'path', '?')}")

    # 2) Stage timings ---------------------------------------------------------
    if _Demo.stage_durations:
        print("\n[stage timings]")
        for name, dur in _Demo.stage_durations:
            print(f"  {name:<24} {dur * 1000:>10.1f} ms")

    # 3) LLM call ledger --------------------------------------------------------
    if _Demo.llm_calls:
        print("\n[llm calls]")
        print(
            f"  {'stage':<32} {'model':<28} {'in_chars':>9} "
            f"{'out_chars':>9} {'elapsed_s':>9}"
        )
        for c in _Demo.llm_calls:
            in_c = int(c.get("user_chars", 0)) + int(c.get("system_chars", 0))
            print(
                f"  {c['stage'][:32]:<32} {str(c.get('model'))[:28]:<28} "
                f"{in_c:>9,} {c.get('raw_chars', 0):>9,} "
                f"{c.get('elapsed_sec', 0):>9.2f}"
            )

    # 4) Bayesian posteriors ----------------------------------------------------
    bayes = probe.get("bayes") or {}
    posteriors = bayes.get("posteriors") or []
    bayes_gate = bayes.get("gate") or {}
    print("\n[bayesian posteriors]")
    print(f"  gate.method:         {bayes_gate.get('method')}")
    print(f"  gate.wants_bayes:    {bayes_gate.get('wants_bayes')}")
    print(f"  gate.hypothesis_id:  {bayes_gate.get('hypothesis_id')!r}")
    print(f"  gate.rationale:      {bayes_gate.get('rationale')}")
    print(f"  cohort_strata:       {bayes.get('cohort_strata')}")
    print(f"  mkg_prior_used:      {bool(bayes.get('mkg_prior'))}")
    print(f"  ran:                 {bayes.get('ran')}")
    if posteriors:
        for p in posteriors:
            uc = p.get("uc") or {}
            band = uc.get("band_90") or [None, None]
            ls = uc.get("likelihood_summary") or {}
            print()
            print(f"  hypothesis_id      : {p.get('hypothesis_id')}")
            print(f"  point_estimate     : {uc.get('point_estimate')}")
            print(f"  band_90            : [{band[0]}, {band[1]}]")
            print(
                f"  confidence         : "
                f"{uc.get('confidence_label')} ({uc.get('confidence')})"
            )
            print(f"  method             : {uc.get('method')}")
            print(f"  spec_hash          : {uc.get('spec_hash')}")
            print(f"  prior              : {uc.get('prior')}")
            print(f"  posterior_params   : {uc.get('posterior_params')}")
            print(
                f"  likelihood (n_pos / n_neg / n_skip) : "
                f"{ls.get('n_pos')} / {ls.get('n_neg')} / {ls.get('n_skip')}"
            )
            print(f"  likelihood.rule_hits: {ls.get('rule_hits')}")
            print(f"  likelihood.weight_by: {ls.get('weight_by')}")
            ev_ids = uc.get("evidence_event_ids") or []
            print(f"  evidence_event_ids ({len(ev_ids)}):")
            for eid in ev_ids[:30]:
                print(f"    - {eid}")
            if len(ev_ids) > 30:
                print(f"    ... +{len(ev_ids) - 30} more")
            for line in (uc.get("basis") or []):
                print(f"  basis              : {line}")
    else:
        print("  (no posteriors emitted this turn)")

    # 5) PTV semantic search ----------------------------------------------------
    psem = (probe.get("ptv_semantic_search") or {}).get("result") or {}
    ptv_results = psem.get("results") or []
    print(f"\n[PTV semantic_search]  k={psem.get('k')}  n_results={len(ptv_results)}")
    print(f"  expanded_query: {_abridge(psem.get('query'), 200)!r}")
    for i, r in enumerate(ptv_results[:12]):
        print(
            f"  {i + 1:2d}. {r.get('event_id'):<22} "
            f"{(r.get('event_type') or '?'):<10} "
            f"{(r.get('timestamp') or '?')} "
            f"score={r.get('score')} "
            f"{_abridge(r.get('title') or r.get('one_line'), 70)!r}"
        )

    # 6) Graph tool result ------------------------------------------------------
    gt = probe.get("graph_tool")
    gtres = (probe.get("graph_tool_result") or {}).get("result") or {}
    events_list = gtres.get("events") or gtres.get("entries") or gtres.get("keys") or []
    print(f"\n[graph_tool {gt!r}]  args={probe.get('graph_args')}")
    if isinstance(events_list, list):
        print(f"  n_results={len(events_list)}")
        for i, r in enumerate(events_list[:12]):
            if isinstance(r, dict) and r.get("event_id"):
                print(
                    f"  {i + 1:2d}. {r.get('event_id'):<22} "
                    f"{(r.get('event_type') or '?'):<10} "
                    f"{(r.get('timestamp') or '?')} "
                    f"{_abridge(r.get('title') or r.get('one_line') or r.get('preview'), 70)!r}"
                )
            elif isinstance(r, dict):
                print(f"  {i + 1:2d}. {_abridge(r, 110)}")

    # 7) MKG hits ---------------------------------------------------------------
    mkg_block = probe.get("mkg") or {}
    if not mkg_block.get("skipped"):
        print(
            f"\n[MKG retrieval]  "
            f"semantic={len(mkg_block.get('semantic_hits') or [])}  "
            f"ts={len(mkg_block.get('ts_hits') or [])}  "
            f"jaccard={(mkg_block.get('overlap') or {}).get('jaccard')}"
        )
        per_src = mkg_block.get("per_source_ts_terms_used") or {}
        if per_src:
            ts_per_src_count = mkg_block.get("ts_per_source_hit_count") or {}
            print(f"  per-source ts_terms ({len(per_src)} source(s)):")
            for src, terms in per_src.items():
                hit_n = ts_per_src_count.get(src, "?")
                shown = ", ".join(terms[:10])
                tail = "" if len(terms) <= 10 else f" (+{len(terms) - 10} more)"
                print(f"    - {src:<28} hits={hit_n:>3}  terms=[{shown}]{tail}")
        sem_hits = mkg_block.get("semantic_hits") or []
        print(f"  semantic ({len(sem_hits)}):")
        for i, h in enumerate(sem_hits[:10]):
            print(
                f"  SEM {i + 1:2d}. #{h.get('id')} src={h.get('source')!r} "
                f"score={(h.get('score') or 0):.3f} "
                f"title={_abridge(h.get('title'), 80)!r}"
            )
        ts_hits = mkg_block.get("ts_hits") or []
        print(f"  ts ({len(ts_hits)}):")
        for i, h in enumerate(ts_hits[:10]):
            print(
                f"  TS  {i + 1:2d}. #{h.get('id')} src={h.get('source')!r} "
                f"score={(h.get('score') or 0):.3f} "
                f"title={_abridge(h.get('title'), 80)!r}"
            )
    else:
        print("\n[MKG retrieval]  SKIPPED (--no-mkg or DSN unset)")

    # 8) Gap follow-ups ---------------------------------------------------------
    print("\n[gap follow-ups]")
    fmkg = gap.get("follow_mkg") or {}
    if fmkg:
        print(
            f"  follow_mkg: semantic={len(fmkg.get('semantic_hits') or [])} "
            f"ts={len(fmkg.get('ts_hits') or [])} "
            f"ts_terms_used={fmkg.get('ts_terms_used')}"
        )
    fps = gap.get("follow_ptv_semantic") or {}
    if fps.get("ok"):
        n = len(((fps.get("result") or {}).get("results") or []))
        print(f"  follow_ptv_semantic: n_results={n}")
    fgr = gap.get("follow_graph") or {}
    if fgr:
        print(
            f"  follow_graph: tool={fgr.get('tool')!r} "
            f"ok={fgr.get('ok')} args={fgr.get('args')}"
        )
    fbz = gap.get("follow_bayes") or {}
    if fbz:
        fr = fbz.get("result") or {}
        print(
            f"  follow_bayes: hypothesis_id={fr.get('hypothesis_id')!r} "
            f"ok={fbz.get('ok')}"
        )
    if not (fmkg or fps.get("ok") or fgr or fbz):
        print("  (none)")

    # 9) Cited event cards ------------------------------------------------------
    cited = _gather_cited_event_ids(probe, gap)
    if cited:
        print(f"\n[cited event cards]  unique_event_ids={len(cited)}")
        events_dict = getattr(gh, "events", None) or {}
        for eid in cited[:30]:
            ev = events_dict.get(eid) if isinstance(events_dict, dict) else None
            if not ev:
                print(f"  - {eid}: <not found in graph>")
                continue
            ann = ev.get("annotations") or {}
            card = ann.get("card") or {}
            title = card.get("title") or card.get("one_line") or ev.get("preview") or ""
            print(
                f"  - {eid:<22} {(ev.get('event_type') or '?'):<12} "
                f"{(ev.get('timestamp') or '?')} :: {_abridge(title, 90)}"
            )
        if len(cited) > 30:
            print(f"  ... +{len(cited) - 30} more")

    # 10) Retro -----------------------------------------------------------------
    retro = probe.get("retro") or {}
    if retro and (retro.get("retro_summary") or "").strip():
        print("\n[retro session summary]")
        print(retro.get("retro_summary"))

    # 11) Gap report (full) -----------------------------------------------------
    _section("GAP REPORT", char="─")
    print(gap.get("gap_report") or "(empty)")

    # 12) Final report (full again, so the demo ends on the answer) -------------
    _section("FINAL REPORT (repeat)", char="─")
    print(report or "(empty)")
    print()


def _print_turn_outputs(
    q: str,
    probe: Dict[str, Any],
    gap: Dict[str, Any],
    report: str,
) -> None:
    if probe.get("retro") and (probe["retro"].get("retro_summary") or "").strip():
        print("\n--- retro summary ---\n")
        print(probe["retro"]["retro_summary"])
    bayes = probe.get("bayes") or {}
    if bayes.get("ran") and bayes.get("posteriors"):
        print("\n--- bayesian posteriors ---\n")
        for p in bayes["posteriors"]:
            uc = (p or {}).get("uc") or {}
            band = uc.get("band_90") or [None, None]
            print(
                f"  {p.get('hypothesis_id')}: "
                f"point_estimate={uc.get('point_estimate')} "
                f"band_90=[{band[0]}, {band[1]}] "
                f"confidence={uc.get('confidence_label')!r} "
                f"method={uc.get('method')!r} "
                f"n_evidence={len(uc.get('evidence_event_ids') or [])}"
            )
    print("\n--- gap report ---\n")
    print(gap.get("gap_report") or "")
    print("\n--- final report ---\n")
    print(report or "(empty)")
    print()


def _run_full_turn(
    *,
    question: str,
    gh: Any,
    session: Optional[SessionLog],
    args: argparse.Namespace,
    print_reports: bool = True,
) -> Dict[str, Any]:
    t0 = time.monotonic()
    q = (question or "").strip()
    _demo_enable(getattr(args, "demo", False) or os.environ.get("FORWARD_DEMO_MODE") == "1")
    _demo_reset_turn()
    _demo_banner(
        "USER QUESTION",
        f"q={q[:160]}{'…' if len(q) > 160 else ''}",
        char="═",
    )
    _demo_kvs({
        "models.probe (8B router)": args.probe_model,
        "models.graph_pick": args.graph_pick_model,
        "models.bayes_gate": args.bayes_gate_model or args.probe_model,
        "models.retro": args.retro_model,
        "models.gap (qwen-14b 102K)": args.gap_model,
        "models.report (qwen-14b 102K)": args.report_model,
        "models.embed": args.embed_model,
        "qwen_call_num_ctx": _FORWARD_QWEN_CALL_NUM_CTX,
        "gap_report_json_max_chars": _GAP_REPORT_JSON_MAX_CHARS,
        "mkg_enabled": not args.no_mkg,
        "bayes_enabled": not args.no_bayes,
    })
    _log("💬", f"User question ({len(q)} chars): {q[:100]}{'…' if len(q) > 100 else ''}")

    retro_bundle: Optional[Dict[str, Any]] = None
    if session is not None and args.retro:
        gate = _retro_gate(
            question=q,
            session=session,
            ollama_url=args.ollama_url,
            model=args.probe_model,
            temperature=args.temperature,
            timeout=args.timeout,
            num_ctx=args.probe_num_ctx,
        )
        if gate.get("references_prior") and gate.get("retro_query"):
            matches = session.search(str(gate["retro_query"]), k=args.retro_k)
            _log(
                "🪞",
                f"retro session.search hits={len(matches)} method="
                f"{(matches[0].get('__retrieval_method') if matches else 'none')}",
            )
            review = _retro_summarize(
                question=q,
                matched_turns=matches,
                session=session,
                ollama_url=args.ollama_url,
                model=args.retro_model,
                temperature=args.temperature,
                timeout=args.timeout,
                num_ctx=args.retro_num_ctx,
                text_chars=args.text_chars,
            )
            retro_bundle = {
                "gate": gate,
                "matched_turn_ids": [t.get("turn_id") for t in matches if t.get("turn_id")],
                "n_matches": len(matches),
                **review,
            }
        else:
            retro_bundle = {
                "gate": gate,
                "matched_turn_ids": [],
                "n_matches": 0,
                "retro_summary": "",
                "evidence_turn_ids": [],
                "n_turns_reviewed": 0,
            }

    probe = _run_probe(
        question=q,
        gh=gh,
        ollama_url=args.ollama_url,
        probe_model=args.probe_model,
        probe_num_ctx=args.probe_num_ctx,
        graph_pick_model=args.graph_pick_model,
        graph_pick_num_ctx=args.graph_pick_num_ctx,
        router_max_sources=args.router_max_sources,
        router_max_modules=args.router_max_modules,
        router_temperature=args.router_temperature,
        router_min_terms=args.router_min_terms,
        debug_router=args.debug_router,
        temperature=args.temperature,
        timeout=args.timeout,
        top_k=args.top_k,
        embed_model=args.embed_model,
        enable_mkg=not args.no_mkg,
        text_chars=args.text_chars,
        enable_code_inventory=not args.no_code_inventory,
        code_inventory_compact=args.code_inventory_compact,
        code_inventory_router_json_max=args.code_inventory_router_json_max,
        code_inventory_graph_json_max=args.code_inventory_graph_json_max,
        retro_bundle=retro_bundle,
        mkg_source_coverage=not args.no_mkg_source_coverage,
        mkg_min_ann_score=args.mkg_min_ann_score,
        mkg_min_ts_score=args.mkg_min_ts_score,
        enable_bayes=not args.no_bayes,
        bayes_gate_model=args.bayes_gate_model or args.probe_model,
        bayes_gate_num_ctx=args.bayes_gate_num_ctx,
        bayes_use_mkg_prior=not args.no_bayes_mkg_prior,
    )
    gap_sources = _router_sources(probe.get("router_plan") or {})
    _demo_stage_start("gap_total")
    gap = _gap_phase(
        question=q,
        probe_bundle=probe,
        gh=gh,
        ollama_url=args.ollama_url,
        model=args.gap_model,
        temperature=args.temperature,
        timeout=args.timeout,
        num_ctx=args.gap_num_ctx,
        top_k=args.top_k,
        embed_model=args.embed_model,
        gap_sources=gap_sources,
        text_chars=args.text_chars,
        gap_heuristic=not args.no_gap_heuristic,
        gap_heuristic_strength=float(args.gap_heuristic_strength),
        mkg_source_coverage=not args.no_mkg_source_coverage,
        mkg_min_ann_score=args.mkg_min_ann_score,
        mkg_min_ts_score=args.mkg_min_ts_score,
    )
    _demo_stage_end("gap_total")
    _demo_stage_start("report_total")
    report = _report_phase(
        question=q,
        probe_bundle=probe,
        gap_bundle=gap,
        ollama_url=args.ollama_url,
        model=args.report_model,
        temperature=args.temperature,
        timeout=args.timeout,
        num_ctx=args.report_num_ctx,
    )
    _demo_stage_end("report_total")

    stored: Optional[Dict[str, Any]] = None
    if session is not None:
        try:
            stored = _append_probe_turn_to_session(session, q, probe, gap, report)
            _log("📝", f"session turn {stored.get('turn_id')} appended -> {session.jsonl_path.name}")
        except Exception as exc:  # noqa: BLE001
            _log("⚠️", f"session append failed: {exc}")

    turn_elapsed = time.monotonic() - t0
    if print_reports:
        if _Demo.enabled:
            _print_demo_summary(
                question=q, probe=probe, gap=gap, report=report,
                turn_elapsed=turn_elapsed, gh=gh,
            )
        else:
            _print_turn_outputs(q, probe, gap, report)
    _log("⏱️", f"Turn done elapsed_sec={turn_elapsed:.2f}")

    return {"question": q, "probe": probe, "gap": gap, "report": report, "stored": stored}


def _load_harness_questions(path: Path) -> List[Dict[str, Any]]:
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)
    if isinstance(data, dict) and "questions" in data:
        data = data["questions"]
    if not isinstance(data, list) or not data:
        raise ValueError("harness file must be a non-empty JSON array (or {questions: [...]})")
    out: List[Dict[str, Any]] = []
    for i, row in enumerate(data):
        if isinstance(row, str):
            row = {"question": row}
        if not isinstance(row, dict):
            raise ValueError(f"harness entry {i} must be an object or string")
        q = str(row.get("question") or "").strip()
        if not q:
            raise ValueError(f"harness entry {i} missing question")
        row = dict(row)
        row["question"] = q
        out.append(row)
    return out


def _append_harness_seed_turns(session: SessionLog, seeds: List[Any]) -> int:
    n = 0
    for raw in seeds or []:
        if not isinstance(raw, dict):
            continue
        row = dict(raw)
        row.setdefault("synthetic_seed", True)
        session.append_turn(row)
        n += 1
    return n


def _harness_receipt_row(
    item: Dict[str, Any],
    rec: Dict[str, Any],
    n_seeds: int,
) -> Dict[str, Any]:
    probe = rec.get("probe") or {}
    retro = probe.get("retro") or {}
    gate = retro.get("gate") or {}
    gap = rec.get("gap") or {}
    stored = rec.get("stored") or {}
    bayes = probe.get("bayes") or {}
    bayes_gate = bayes.get("gate") or {}
    return {
        "harness_id": item.get("id"),
        "question": rec.get("question"),
        "n_seed_turns": n_seeds,
        "retro_references_prior": gate.get("references_prior"),
        "retro_query": gate.get("retro_query"),
        "retro_summary": (retro.get("retro_summary") or "")[:8000],
        "graph_tool": probe.get("graph_tool"),
        "mkg_jaccard": (probe.get("mkg") or {}).get("overlap", {}).get("jaccard"),
        "bayes_wants": bool(bayes_gate.get("wants_bayes")),
        "bayes_hypothesis_id": bayes_gate.get("hypothesis_id"),
        "bayes_ran": bool(bayes.get("ran")),
        "posteriors": bayes.get("posteriors") or [],
        "turn_id": stored.get("turn_id"),
        "turn_index": stored.get("turn_index"),
        "gap_report": gap.get("gap_report") or "",
        "final_report": rec.get("report") or "",
    }


def _harness_session_receipt_paths(receipt_path: Path) -> Tuple[Path, Path]:
    stem = receipt_path.stem
    parent = receipt_path.parent
    return (
        parent / f"{stem}_session.jsonl",
        parent / f"{stem}_session__meta.json",
    )


def _merge_session_into_harness_receipt(
    session: SessionLog,
    receipt_path: Path,
    *,
    copy_files: bool,
) -> Dict[str, Any]:
    """Record live session paths; optionally copy JSONL + meta beside receipt_path."""
    jsonl_live = session.jsonl_path.resolve()
    meta_live = session.meta_path.resolve() if session.meta_path.is_file() else None
    out: Dict[str, Any] = {
        "session_log_schema": "chatbot_session.v1 (one JSON object per line: question, gap_report, final_report, retro, router_*, graph_tool, graph_args, …)",
        "session_jsonl_live": str(jsonl_live),
        "session_meta_live": str(meta_live) if meta_live else None,
        "n_turns_in_session": session.n_turns(),
        "session_jsonl_receipt": None,
        "session_meta_receipt": None,
    }
    dest_jsonl, dest_meta = _harness_session_receipt_paths(receipt_path)
    if copy_files:
        if session.jsonl_path.is_file():
            shutil.copy2(session.jsonl_path, dest_jsonl)
            out["session_jsonl_receipt"] = str(dest_jsonl.resolve())
        if session.meta_path.is_file():
            shutil.copy2(session.meta_path, dest_meta)
            out["session_meta_receipt"] = str(dest_meta.resolve())
    _log(
        "session",
        f"harness receipt: turns={out['n_turns_in_session']} "
        f"jsonl={'copy' if copy_files and out['session_jsonl_receipt'] else 'live'} "
        f"{out.get('session_jsonl_receipt') or out['session_jsonl_live']}",
    )
    return out


def _run_harness_mode(
    args: argparse.Namespace,
    gh: Any,
    session: SessionLog,
    graph_path: Path,
) -> int:
    t0 = time.monotonic()
    path = Path(args.harness_file).expanduser().resolve()
    if not path.is_file():
        print(f"error: harness file not found: {path}", file=sys.stderr)
        return 2
    items = _load_harness_questions(path)
    receipt_path = args.harness_receipt
    if receipt_path is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        receipt_dir = ROOT / "receipts"
        receipt_dir.mkdir(parents=True, exist_ok=True)
        receipt_path = receipt_dir / f"FORWARD_PROBE_GAP_SESSION_HARNESS_{ts}.json"
    else:
        receipt_path = Path(receipt_path).expanduser().resolve()
        receipt_path.parent.mkdir(parents=True, exist_ok=True)

    rows: List[Dict[str, Any]] = []
    verbose = bool(getattr(args, "harness_verbose", False))
    # --demo implies full per-turn stdout (final report + evidence dump); same as
    # interactive mode, so harness runs are screen-recordable without remembering
    # --harness-verbose separately.
    print_turns = verbose or bool(getattr(args, "demo", False)) or (
        os.environ.get("FORWARD_DEMO_MODE") == "1"
    )
    continue_on_error = bool(getattr(args, "harness_continue_on_error", False))
    copy_session = not bool(getattr(args, "harness_no_session_copy", False))

    for i, item in enumerate(items):
        turn_t0 = time.monotonic()
        n_seeds = _append_harness_seed_turns(session, item.get("seed_session_turns_before") or [])
        print(
            f"[harness {i + 1}/{len(items)}] seeds={n_seeds} id={item.get('id', i)!r}",
            flush=True,
        )
        try:
            rec = _run_full_turn(
                question=item["question"],
                gh=gh,
                session=session,
                args=args,
                print_reports=print_turns,
            )
        except Exception as exc:  # noqa: BLE001
            err_row = {"error": str(exc), "harness_id": item.get("id"), "index": i}
            rows.append(err_row)
            print(f"  error: {exc}", file=sys.stderr, flush=True)
            if not continue_on_error:
                payload = {
                    "schema": "probe_gap_session_harness.v2",
                    "ok": False,
                    "graph_path": str(graph_path),
                    "harness_file": str(path),
                    "session_id": session.session_id,
                    "n_items": len(items),
                    "rows": rows,
                }
                payload.update(
                    _merge_session_into_harness_receipt(
                        session, receipt_path, copy_files=copy_session
                    )
                )
                receipt_path.write_text(
                    json.dumps(payload, indent=2, ensure_ascii=False),
                    encoding="utf-8",
                )
                _log("📝", f"harness receipt (partial) -> {receipt_path}")
                return 1
            continue

        rows.append(_harness_receipt_row(item, rec, n_seeds))
        if not print_turns:
            rk = (rec.get("probe") or {}).get("retro") or {}
            ref = (rk.get("gate") or {}).get("references_prior")
            print(
                f"  ok references_prior={ref} graph_tool={(rec.get('probe') or {}).get('graph_tool')!r}",
                flush=True,
            )
        _log("⏱️", f"harness item {i + 1}/{len(items)} elapsed_sec={time.monotonic() - turn_t0:.2f}")

    any_err = any(isinstance(r, dict) and r.get("error") for r in rows)
    payload = {
        "schema": "probe_gap_session_harness.v2",
        "ok": not any_err,
        "graph_path": str(graph_path),
        "harness_file": str(path),
        "session_id": session.session_id,
        "n_items": len(items),
        "rows": rows,
    }
    payload.update(
        _merge_session_into_harness_receipt(session, receipt_path, copy_files=copy_session)
    )
    receipt_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    _log("📝", f"harness receipt -> {receipt_path}")
    print(
        f"harness done n={len(items)} receipt={receipt_path} "
        f"session_copy={payload.get('session_jsonl_receipt') or payload.get('session_jsonl_live')}",
        flush=True,
    )
    _log("⏱️", f"harness total elapsed_sec={time.monotonic() - t0:.2f}")
    return 0


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graph", type=Path, default=DEFAULT_GRAPH, help="PTV JSON graph path.")
    ap.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    ap.add_argument("--probe-model", default=os.environ.get("EOH_SOURCE_ROUTER_MODEL", "eoh-llama3.2-source-router"))
    ap.add_argument("--probe-num-ctx", type=int, default=int(os.environ.get("OLLAMA_ROUTER_NUM_CTX", "8192")))
    ap.add_argument(
        "--graph-pick-model",
        default=os.environ.get("FORWARD_GRAPH_PICK_MODEL", "eoh-llama"),
        help="Model for probe graph-tool selection (default 8B).",
    )
    ap.add_argument(
        "--graph-pick-num-ctx",
        type=int,
        default=int(os.environ.get("OLLAMA_GRAPH_PICK_NUM_CTX", "32768")),
        help="Context window for graph-tool selection model.",
    )
    ap.add_argument("--gap-model", default=os.environ.get("FORWARD_GAP_MODEL", "eoh-qwen3-14b"))
    ap.add_argument("--report-model", default=os.environ.get("FORWARD_SYNTH_MODEL", "eoh-qwen3-14b"))
    ap.add_argument(
        "--retro-model",
        default=os.environ.get("FORWARD_RETRO_MODEL", "eoh-llama"),
        help="Model for retro session summary review (default eoh-llama).",
    )
    ap.add_argument(
        "--gap-num-ctx",
        type=int,
        default=int(os.environ.get("OLLAMA_AGENT_NUM_CTX", str(_FORWARD_QWEN_CALL_NUM_CTX))),
    )
    ap.add_argument(
        "--report-num-ctx",
        type=int,
        default=int(os.environ.get("OLLAMA_SYNTH_NUM_CTX", str(_FORWARD_QWEN_CALL_NUM_CTX))),
    )
    ap.add_argument(
        "--retro-num-ctx",
        type=int,
        default=int(os.environ.get("OLLAMA_RETRO_NUM_CTX", "32768")),
        help="Context window for retro summary model (default 32768).",
    )
    ap.add_argument(
        "--router-max-sources",
        type=int,
        default=int(os.environ.get("ROUTER_MAX_SOURCES", "16")),
        metavar="N",
        help="Max distinct rag_corpus.source keys for plan_route (default 16).",
    )
    ap.add_argument(
        "--router-max-modules",
        type=int,
        default=int(os.environ.get("ROUTER_MAX_MODULES", "8")),
        metavar="N",
        help="Max EoH modules for plan_route (default 8).",
    )
    ap.add_argument(
        "--no-mkg-source-coverage",
        action="store_true",
        help="Do not pin one qualifying rag_corpus hit per router-selected source (ANN/ts_rank floors).",
    )
    ap.add_argument(
        "--mkg-min-ann-score",
        type=float,
        default=float(os.environ.get("MKG_MIN_ANN_SCORE", "0.12")),
        metavar="S",
        help="Minimum dense-lane score (1 - distance) to count toward per-source coverage (default 0.12).",
    )
    ap.add_argument(
        "--mkg-min-ts-score",
        type=float,
        default=float(os.environ.get("MKG_MIN_TS_SCORE", "0.02")),
        metavar="S",
        help="Minimum TS-lane ts_rank to count toward per-source coverage (default 0.02).",
    )
    ap.add_argument(
        "--router-temperature",
        type=float,
        default=float(os.environ.get("ROUTER_TEMPERATURE", "0.27")),
        metavar="T",
        help="Sampling temperature for source-router + EoH prelude (default 0.27).",
    )
    ap.add_argument(
        "--router-min-terms",
        type=int,
        default=int(os.environ.get("ROUTER_MIN_TERMS", "4")),
        metavar="N",
        help="Minimum ts_terms plan_route should aim for before retrieval (default 4).",
    )
    ap.add_argument(
        "--debug-router",
        action="store_true",
        help="Log router system/user prompts and raw model heads (stderr).",
    )
    ap.add_argument(
        "--gap-heuristic-strength",
        type=float,
        default=float(os.environ.get("GAP_HEURISTIC_STRENGTH", "1.0")),
        metavar="S",
        help="Scale deterministic GAP follow-ups when mkg_jaccard=0 (0=off, 1=full).",
    )
    ap.add_argument("--temperature", type=float, default=0.15)
    ap.add_argument("--timeout", type=float, default=600.0)
    ap.add_argument("--top-k", type=int, default=12)
    ap.add_argument("--embed-model", default=os.environ.get("LOCAL_EMBED_MODEL", "BAAI/bge-base-en-v1.5"))
    ap.add_argument("--text-chars", type=int, default=1200)
    ap.add_argument("--no-mkg", action="store_true", help="Skip MKG DB retrieval (PTV + graph pick only).")
    ap.add_argument(
        "--no-gap-heuristic",
        action="store_true",
        help="Disable deterministic GAP follow-ups when mkg_jaccard=0 and the model returned no follow fields.",
    )
    ap.add_argument(
        "--no-bayes",
        action="store_true",
        help=(
            "Disable the Bayesian gate + bayesian_update_uc phase "
            "(see reports/STRATEGY_BAYESIAN_PTV_UC_20260423.md). "
            "Off by default — keeps it on."
        ),
    )
    ap.add_argument(
        "--no-bayes-mkg-prior",
        action="store_true",
        help=(
            "Skip MKG-derived prior lookup and use the strategy-doc weak default priors "
            "(Beta(2,8) for flare_30d, etc.). When unset, the Bayesian phase tries to "
            "fetch a population prior from public.mkg_bayes_priors keyed by hypothesis_id "
            "and patient cohort_strata; on miss it falls back to the weak default."
        ),
    )
    ap.add_argument(
        "--demo",
        action="store_true",
        default=os.environ.get("FORWARD_DEMO_MODE") == "1",
        help=(
            "Verbose demo logging tuned for screen-recording / Y Combinator demo. Enables "
            "stage banners, per-LLM raw-response previews, context-curation snapshots "
            "(probe bundle / GAP / REPORT input sizes), stage timing, and an end-of-turn "
            "summary that prints the FULL final report followed by all evidence "
            "(posteriors, MKG hits, PTV hits, graph-tool results, cited event cards). "
            "Set the env var FORWARD_DEMO_MODE=1 to enable without the flag."
        ),
    )
    ap.add_argument(
        "--bayes-gate-model",
        default=os.environ.get("FORWARD_BAYES_GATE_MODEL", ""),
        help=(
            "Model for the Bayesian gating classifier (default: same as --probe-model, "
            "i.e. eoh-llama3.2-source-router 8B). The closed-form update itself is "
            "deterministic Python and does not call an LLM."
        ),
    )
    ap.add_argument(
        "--bayes-gate-num-ctx",
        type=int,
        default=int(os.environ.get("FORWARD_BAYES_GATE_NUM_CTX", "8192")),
        help="Context window for the Bayesian gate model (default 8192).",
    )
    ap.add_argument(
        "--no-code-inventory",
        action="store_true",
        help="Do not scan metadata.code_index before the source router (ablation).",
    )
    ap.add_argument(
        "--code-inventory-compact",
        action="store_true",
        help="Omit n_events per code in JSON sent to router / graph-picker only; probe still stores full rows.",
    )
    ap.add_argument(
        "--code-inventory-router-json-max",
        type=int,
        default=int(os.environ.get("ROUTER_CODE_INVENTORY_MAX_JSON", "14000")),
        metavar="N",
        help="Max JSON chars for patient_code_inventory embedded in plan_route user payload.",
    )
    ap.add_argument(
        "--code-inventory-graph-json-max",
        type=int,
        default=8000,
        metavar="N",
        help="Max JSON chars for patient_code_inventory in probe graph-picker user payload.",
    )
    ap.add_argument(
        "--session-id",
        default=None,
        metavar="ID",
        help="Chatbot session id (default: UTC timestamp). Resumes if --session-id matches existing meta.json.",
    )
    ap.add_argument(
        "--session-dir",
        default=os.environ.get("CHATBOT_SESSION_DIR", "artifacts/chatbot_sessions"),
        metavar="DIR",
        help="Directory to write session JSONL + meta files.",
    )
    ap.add_argument(
        "--no-session",
        action="store_true",
        help="Disable session log; do not write turns to disk; disables retro retrieval.",
    )
    ap.add_argument(
        "--retro",
        action="store_true",
        help=(
            "Enable retro-retrieval (retro-gate + prior-turn search + retro-review) "
            "when a session log exists with prior turns. Default off."
        ),
    )
    ap.add_argument(
        "--retro-k",
        type=int,
        default=5,
        metavar="K",
        help="Top-K prior turns to fetch from session log when retro_query is set.",
    )
    ap.add_argument(
        "--harness-file",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Run a non-interactive session harness: JSON array of {question, id?, "
            "seed_session_turns_before?}. Implies a session id (harness_<UTC> if unset). "
            f"Default questions file: {DEFAULT_HARNESS_QUESTIONS.relative_to(ROOT)}"
        ),
    )
    ap.add_argument(
        "--harness-receipt",
        type=Path,
        default=None,
        metavar="PATH",
        help="Write harness summary JSON here (default: receipts/FORWARD_PROBE_GAP_SESSION_HARNESS_<UTC>.json).",
    )
    ap.add_argument(
        "--harness-verbose",
        action="store_true",
        help="Print full gap + final report for each harness question (default: one-line progress).",
    )
    ap.add_argument(
        "--harness-fresh",
        action="store_true",
        help="With --harness-file: delete existing session JSONL/meta for the resolved session id before run.",
    )
    ap.add_argument(
        "--harness-continue-on-error",
        action="store_true",
        help="With --harness-file: continue after a failed question (default: stop and write partial receipt).",
    )
    ap.add_argument(
        "--harness-no-session-copy",
        action="store_true",
        help=(
            "With --harness-file: do not copy session JSONL/meta next to the receipt "
            "(live paths are still recorded on the receipt JSON)."
        ),
    )
    return ap.parse_args()


def main() -> int:
    args = _parse_args()
    path = args.graph.expanduser().resolve()
    if not path.is_file():
        print(f"error: graph not found: {path}", file=sys.stderr)
        return 2

    if args.harness_file is not None and args.no_session:
        print("error: --harness-file requires session logging (omit --no-session)", file=sys.stderr)
        return 2

    gh = load_graph(path)
    print(f"Loaded {path.name} events={len(gh.events)} hash={gh.graph_hash}")
    print(
        f"probe(router)={args.probe_model} graph_pick={args.graph_pick_model} "
        f"retro={args.retro_model} gap={args.gap_model} report={args.report_model}"
    )

    session: Optional[SessionLog] = None
    if not args.no_session:
        models_meta = {
            "probe": args.probe_model,
            "retro": args.retro_model,
            "gap": args.gap_model,
            "report": args.report_model,
            "embed": args.embed_model,
        }
        base_dir = Path(args.session_dir).expanduser().resolve()
        effective_sid = args.session_id
        if args.harness_file is not None and not effective_sid:
            effective_sid = f"harness_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"

        if args.harness_file is not None and args.harness_fresh and effective_sid:
            for name in (f"{effective_sid}.jsonl", f"{effective_sid}__meta.json"):
                p = base_dir / name
                if p.is_file():
                    p.unlink()

        existing = SessionLog.open_existing(effective_sid, base_dir=base_dir) if effective_sid else None
        if existing is not None and existing.graph_hash == gh.graph_hash:
            session = existing
            print(f"session={session.session_id} (resumed) prior_turns={session.n_turns()}")
        else:
            session = SessionLog.create(
                graph_hash=gh.graph_hash,
                graph_path=str(path),
                models=models_meta,
                session_id=effective_sid,
                base_dir=base_dir,
            )
            print(f"session={session.session_id} (new) -> {session.jsonl_path}")
    else:
        print("session=DISABLED (--no-session)")

    if args.harness_file is not None:
        assert session is not None
        return _run_harness_mode(args, gh, session, path)

    print("Commands: quit | exit | q\n")

    while True:
        try:
            q = input("hybrid> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye")
            return 0
        if not q or q.lower() in {"quit", "exit", "q"}:
            print("bye")
            return 0

        try:
            _run_full_turn(question=q, gh=gh, session=session, args=args, print_reports=True)
        except Exception as exc:  # noqa: BLE001
            print(f"\nerror: {exc}\n", file=sys.stderr)
            continue


if __name__ == "__main__":
    raise SystemExit(main())
