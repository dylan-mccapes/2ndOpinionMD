#!/usr/bin/env python3
"""3-agent FORWARD PTV harness with optional MKG retrieval handoff.

Cycles through every synthetic FORWARD patient PTV under
``artifacts/forward_kaleb_package_20260423/synthetic_pro_cohort/`` and runs
a five-stage pipeline per patient + question:

  Stage A — Probe (eoh-llama, 8B q8_0)
      Runs the standard PTV toolkit agent against the patient's PTV graph.
      Emits a plan + tool-call sequence + final_answer.

  Stage B — Gap assessment + extra retrieval (eoh-llama, 8B q8_0)
      Receives Stage-A handoff (working_set, top_events, probe answer).
      Inspects what the probe missed, runs additional tool calls, and
      emits its own final_answer that fills the gaps.

  Stage C — Curation
      Combines Stage A and B working sets, top events, plans, and answers
      into a single curated bundle for the synthesis model.

  Stage D — PTV synthesis (eoh-llama, 8B q8_0)
      Receives the curated bundle and produces the patient-level clinical
      narrative grounded in the cited event_ids only. This is the patient
      timeline summary.

  Stage E — MKG retrieval + overall synthesis (default eoh-llama, 8B q8_0)
      OPTIONAL. Calls ``server.scripts.mkg_retrieval_harness.run_query``
      with the original question PLUS the Stage-D markdown as
      ``clinical_context``. The router (eoh-llama3.2-source-router) sees the
      patient context to bias source/term selection; the synthesis model sees
      both the rag_corpus hits AND the PTV summary so it can ground patient-
      specific claims in event_ids while grounding evidence claims in
      rag_corpus hit ids. Disable with ``--no-mkg``.

All five stages are recorded in a JSON receipt. Once the receipt is written,
the companion PDF renderer (``server/scripts/forward_ptv_3agent_pdf.py``)
is invoked automatically and the PDF is stored under ``reports/``.

Examples::

    python server/scripts/forward_ptv_3agent_harness.py
    python server/scripts/forward_ptv_3agent_harness.py \\
        --questions-file server/scripts/forward_ptv_phenotype_questions.json
    # Disable Stage E if rag_corpus isn't reachable from this host
    python server/scripts/forward_ptv_3agent_harness.py --no-mkg
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.ptv_toolkit.agent import AgentLog, log_to_dict, run_agent
from server.ptv_toolkit.graph import GraphHandle, load_graph
from server.ptv_toolkit.handoff import build_handoff


def _log(emoji: str, msg: str) -> None:
    print(f"{emoji} {msg}", file=sys.stderr, flush=True)


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------

DEFAULT_COHORT_DIR = ROOT / "artifacts" / "forward_kaleb_package_20260423" / "synthetic_pro_cohort"
DEFAULT_QUESTIONS_FILE = ROOT / "server" / "scripts" / "forward_ptv_phenotype_questions.json"

# Models (4090 pilot: eoh-llama 8B q8_0)
# MODEL = "eoh-qwen"  # experimental; not used for pilot
MODEL = "eoh-llama"
DEFAULT_PROBE_MODEL = os.environ.get("FORWARD_PROBE_MODEL", MODEL)
DEFAULT_GAP_MODEL = os.environ.get("FORWARD_GAP_MODEL", MODEL)
DEFAULT_SYNTH_MODEL = os.environ.get("FORWARD_SYNTH_MODEL", MODEL)
DEFAULT_OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434")

# Stage E (MKG retrieval) defaults
DEFAULT_MKG_SYNTH_MODEL = os.environ.get(
    "FORWARD_MKG_SYNTH_MODEL", os.environ.get("OLLAMA_SYNTH_MODEL", MODEL)
)
DEFAULT_MKG_ROUTER_MODEL = os.environ.get(
    "EOH_SOURCE_ROUTER_MODEL", "eoh-llama3.2-source-router"
)
DEFAULT_MKG_EMBED_MODEL = os.environ.get("LOCAL_EMBED_MODEL", "BAAI/bge-base-en-v1.5")

# Single canonical question used when no per-phenotype mapping is provided.
DEFAULT_QUESTION = (
    "Summarize this patient's five-year FORWARD trajectory: any flares, treatment "
    "escalations or de-escalations, and notable Uncertainty-Carrier widenings. "
    "Cite event_ids for every claim."
)


# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------

def _stage_probe(
    *,
    gh: GraphHandle,
    question: str,
    model: str,
    ollama_url: str,
    max_turns: int,
    temperature: float,
    timeout: float,
    num_ctx: int,
) -> Dict[str, Any]:
    _log("🛰️", f"Stage A (probe) model={model} max_turns={max_turns} num_ctx={num_ctx}")
    t0 = time.monotonic()
    log = run_agent(
        gh,
        question=question,
        model=model,
        ollama_url=ollama_url,
        max_turns=max_turns,
        temperature=temperature,
        timeout=timeout,
        num_ctx=num_ctx,
    )
    handoff = build_handoff(gh, log)
    out = {
        "stage": "probe",
        "model": model,
        "elapsed_sec": round(time.monotonic() - t0, 3),
        "agent_log": log_to_dict(log),
        "handoff": handoff,
    }
    fa = (log.final_answer or {}).get("answer") or ""
    _log(
        "🛰️",
        f"Stage A done in {out['elapsed_sec']}s tools={len(log.tools_used)} "
        f"working_set={handoff['working_set']['n_included']} answer_len={len(fa)}",
    )
    return out


def _build_gap_question(
    *,
    original_question: str,
    probe_handoff: Dict[str, Any],
) -> str:
    probe = probe_handoff.get("probe") or {}
    fa = probe.get("final_answer") or {}
    answer = (fa.get("answer") or "").strip()
    cited_ids = fa.get("evidence_event_ids") or []
    tools_used = probe.get("tools_used") or []
    working_set = (probe_handoff.get("working_set") or {}).get("event_ids") or []

    parts = [
        "GAP ASSESSMENT TASK — A previous 8B PTV probe agent already attempted to answer this "
        "clinical question. Your job is to find what it MISSED, ran shallowly, or "
        "could have grounded better, then run additional tool calls to close those gaps.",
        "",
        "Original question:",
        original_question,
        "",
        f"Probe answer (length={len(answer)} chars, citations={len(cited_ids)}):",
        answer or "(probe produced no answer)",
        "",
        f"Probe used these tools (in order): {', '.join(tools_used) or '(none)'}",
        f"Probe surfaced working_set of {len(working_set)} event_ids "
        f"(first 25): {working_set[:25]}",
        "",
        "GAP RESPONSIBILITIES:",
        "1. Identify gaps: missing temporal coverage, untouched event_types, drug names "
        "   the probe did not look up, free-text reasoning the probe glossed over.",
        "2. Run additional tool calls to fill the gaps. Prefer narrow scope + rerank "
        "   (temporal_scan/code_index_lookup -> semantic_search rerank).",
        "3. Stay grounded — cite event_ids only.",
        "4. Your final_answer should ADD to the probe answer, not just repeat it. State "
        "   explicitly which gaps you closed and which remain.",
    ]
    return "\n".join(parts)


def _stage_gap(
    *,
    gh: GraphHandle,
    original_question: str,
    probe_stage: Dict[str, Any],
    model: str,
    ollama_url: str,
    max_turns: int,
    temperature: float,
    timeout: float,
    num_ctx: int,
) -> Dict[str, Any]:
    _log("🔎", f"Stage B (gap) model={model} max_turns={max_turns} num_ctx={num_ctx}")
    gap_question = _build_gap_question(
        original_question=original_question,
        probe_handoff=probe_stage["handoff"],
    )
    t0 = time.monotonic()
    log = run_agent(
        gh,
        question=gap_question,
        model=model,
        ollama_url=ollama_url,
        max_turns=max_turns,
        temperature=temperature,
        timeout=timeout,
        num_ctx=num_ctx,
    )
    handoff = build_handoff(gh, log)
    out = {
        "stage": "gap",
        "model": model,
        "elapsed_sec": round(time.monotonic() - t0, 3),
        "constructed_question": gap_question,
        "agent_log": log_to_dict(log),
        "handoff": handoff,
    }
    fa = (log.final_answer or {}).get("answer") or ""
    _log(
        "🔎",
        f"Stage B done in {out['elapsed_sec']}s tools={len(log.tools_used)} "
        f"working_set={handoff['working_set']['n_included']} answer_len={len(fa)}",
    )
    return out


def _curate_bundle(
    *,
    original_question: str,
    probe_stage: Dict[str, Any],
    gap_stage: Dict[str, Any],
    top_n: int = 30,
) -> Dict[str, Any]:
    """Combine probe + gap working sets and pick top-weighted events for synthesis."""
    _log("🧪", "Stage C (curation) merging probe+gap working sets")

    by_id: Dict[str, Dict[str, Any]] = {}
    for src_label, stage in (("probe", probe_stage), ("gap", gap_stage)):
        for ev in (stage["handoff"].get("top_events") or []):
            eid = ev.get("event_id")
            if not eid:
                continue
            cur = by_id.setdefault(eid, dict(ev))
            cur["probe_weight"] = max(
                int(cur.get("probe_weight") or 0),
                int(ev.get("probe_weight") or 0),
            )
            cur.setdefault("agent_sources", [])
            if src_label not in cur["agent_sources"]:
                cur["agent_sources"].append(src_label)

    curated_events = sorted(
        by_id.values(),
        key=lambda r: (-int(r.get("probe_weight") or 0), r.get("event_id") or ""),
    )[:top_n]

    probe_ws = (probe_stage["handoff"].get("working_set") or {}).get("event_ids") or []
    gap_ws = (gap_stage["handoff"].get("working_set") or {}).get("event_ids") or []
    union: List[str] = []
    seen = set()
    for eid in probe_ws + gap_ws:
        if eid not in seen:
            union.append(eid)
            seen.add(eid)

    bundle = {
        "original_question": original_question,
        "patient_id": probe_stage["handoff"].get("patient_id"),
        "graph_summary": probe_stage["handoff"].get("graph"),
        "probe_answer": (probe_stage["agent_log"].get("final_answer") or {}),
        "probe_plan": (probe_stage["agent_log"].get("plan") or {}),
        "probe_tools": probe_stage["agent_log"].get("tools_used") or [],
        "gap_answer": (gap_stage["agent_log"].get("final_answer") or {}),
        "gap_plan": (gap_stage["agent_log"].get("plan") or {}),
        "gap_tools": gap_stage["agent_log"].get("tools_used") or [],
        "union_event_ids": union,
        "n_union": len(union),
        "curated_events": curated_events,
        "n_curated": len(curated_events),
    }
    _log("🧪", f"Curated {len(curated_events)} events; union working_set={len(union)}")
    return bundle


_SYNTH_SYSTEM = (
    "You are an Ethos-of-Health (EoH) clinical synthesis assistant. "
    "You are the final step in a three-agent FORWARD pilot pipeline: a probe "
    "agent and a gap agent already ran the PatientTimelineVision toolkit on a "
    "synthetic patient's longitudinal graph. You now receive a curated bundle "
    "containing the original question, both prior plans + answers, and the top "
    "weighted event rows that the two agents surfaced.\n\n"
    "RULES:\n"
    "- Do NOT invoke tools. You only synthesize.\n"
    "- Cite ONLY event_ids present in curated_events. Never fabricate IDs.\n"
    "- Reconcile probe and gap answers: where they agree, state confidence; "
    "  where they conflict, surface the disagreement and choose the better-"
    "  grounded claim.\n"
    "- For FORWARD-shaped PRO data (HAQ-II, VAS Pain, VAS Patient Global, "
    "  PAS-II, RDCI), describe trajectory, flares, escalations, and "
    "  Uncertainty-Carrier behavior explicitly.\n"
    "- Honor EoH guardrails: never auto-diagnose, never auto-escalate Stack "
    "  from Band shifts, mark uncertainty where present.\n\n"
    "OUTPUT FORMAT (markdown, exactly these headings):\n"
    "## Patient summary\n"
    "## Trajectory\n"
    "## Flares & treatment changes\n"
    "## Uncertainty carriers\n"
    "## Probe vs gap reconciliation\n"
    "## Open questions\n"
    "Keep total response under 700 words."
)


def _stage_synth(
    *,
    bundle: Dict[str, Any],
    model: str,
    ollama_url: str,
    temperature: float,
    timeout: float,
    num_ctx: int,
) -> Dict[str, Any]:
    import requests

    _log("🧠", f"Stage D (synthesis) model={model} num_ctx={num_ctx}")
    user_payload = json.dumps(bundle, ensure_ascii=False, indent=2, default=str)
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYNTH_SYSTEM},
            {"role": "user", "content": user_payload},
        ],
        "stream": False,
        "options": {"temperature": temperature, "num_ctx": num_ctx},
    }
    t0 = time.monotonic()
    try:
        r = requests.post(
            f"{ollama_url.rstrip('/')}/api/chat",
            json=payload,
            timeout=timeout,
        )
        r.raise_for_status()
        markdown = (r.json().get("message") or {}).get("content") or ""
        out = {
            "stage": "synthesis",
            "model": model,
            "num_ctx": num_ctx,
            "elapsed_sec": round(time.monotonic() - t0, 3),
            "markdown": markdown,
            "input_chars": len(user_payload),
        }
        _log("🧠", f"Stage D done in {out['elapsed_sec']}s output_len={len(markdown)}")
    except Exception as exc:  # noqa: BLE001
        out = {
            "stage": "synthesis",
            "model": model,
            "num_ctx": num_ctx,
            "elapsed_sec": round(time.monotonic() - t0, 3),
            "error": str(exc),
        }
        _log("⚠️", f"Stage D failed: {exc}")
    return out


# ---------------------------------------------------------------------------
# Stage E — MKG retrieval + overall synthesis with PTV summary as context
# ---------------------------------------------------------------------------

def _stage_mkg_synth(
    *,
    original_question: str,
    patient: Dict[str, Any],
    ptv_synth_markdown: str,
    args: argparse.Namespace,
) -> Dict[str, Any]:
    """Feed the Stage-D PTV synthesis into the MKG retrieval harness.

    The original question becomes the retrieval query. The Stage-D markdown
    becomes ``clinical_context`` so the router can bias source/term picks
    and the 70B synthesizer can ground patient-specific claims in event_ids
    while grounding evidence claims in rag_corpus hit ids.
    """
    _log(
        "🌐",
        f"Stage E (MKG retrieval+synth) synth_model={args.mkg_synth_model} "
        f"router={'on' if args.mkg_use_router else 'off'} top_k={args.mkg_top_k}",
    )
    if not ptv_synth_markdown:
        _log("⚠️", "Stage E skipped: Stage D produced no markdown")
        return {"stage": "mkg_overall_synth", "skipped": "no_stage_d_markdown"}

    try:
        from server.scripts.mkg_retrieval_harness import run_query  # type: ignore
    except Exception as exc:  # noqa: BLE001
        _log("⚠️", f"Stage E unavailable: cannot import mkg_retrieval_harness ({exc})")
        return {"stage": "mkg_overall_synth", "error": f"import_failed: {exc}"}

    user_sources = (
        [s.strip().lower() for s in args.mkg_sources.split(",") if s.strip()]
        if args.mkg_sources
        else None
    )

    # Compose extra_context with both the PTV summary and lightweight patient
    # metadata so the 70B synthesizer can address the patient by code/headline.
    extra_context: Dict[str, Any] = {
        "patient_code": patient.get("code") or "",
        "patient_phenotype": patient.get("phenotype") or "",
        "patient_label": patient.get("label") or "",
        "patient_headline": patient.get("headline") or "",
        "ptv_synthesis_markdown": ptv_synth_markdown,
        "provenance": (
            "Produced by the FORWARD 3-agent PTV pipeline (probe 8B + gap 8B "
            "+ synthesis pass). All event_id citations refer to this "
            "patient's PTV graph; do not reuse them as rag_corpus ids."
        ),
    }

    t0 = time.monotonic()
    try:
        result = run_query(
            original_question,
            top_k=args.mkg_top_k,
            user_sources=user_sources,
            embed_model=args.mkg_embed_model,
            no_llm=False,
            ollama_url=args.ollama_url,
            model=args.mkg_synth_model,  # used as fallback synth if synth_model is None
            synth_model=args.mkg_synth_model,
            synth_num_ctx=args.mkg_synth_num_ctx,
            two_pass_synth=bool(args.mkg_two_pass_synth),
            compress_model=args.mkg_compress_model,
            compress_num_ctx=args.mkg_compress_num_ctx,
            compress_evidence_k=max(1, int(args.mkg_compress_evidence_k)),
            temperature=args.temperature,
            timeout=args.timeout,
            use_router=args.mkg_use_router,
            router_model=args.mkg_router_model,
            router_num_ctx=args.mkg_router_num_ctx,
            router_restrict_sources=args.mkg_router_restrict_sources,
            clinical_context=ptv_synth_markdown,
            extra_context=extra_context,
            extra_context_label="patient_timeline_summary",
        )
        elapsed = round(time.monotonic() - t0, 3)
        # Slim the receipt-side payload (keep hits + LLM markdown; drop the
        # giant per-source reference and embedding text — they're already
        # implicit in the harness defaults).
        slim = {
            "stage": "mkg_overall_synth",
            "elapsed_sec": elapsed,
            "synth_model": args.mkg_synth_model,
            "router_model": args.mkg_router_model if args.mkg_use_router else None,
            "embed_model": args.mkg_embed_model,
            "use_router": bool(args.mkg_use_router),
            "two_pass_synth": bool(args.mkg_two_pass_synth),
            "compress_model": args.mkg_compress_model if args.mkg_two_pass_synth else None,
            "router_restrict_sources": bool(args.mkg_router_restrict_sources),
            "top_k": args.mkg_top_k,
            "user_sources": user_sources,
            "router_plan": result.get("router_plan"),
            "effective_sources": result.get("effective_sources"),
            "embed_text": result.get("embed_text"),
            "embed_device": result.get("embed_device"),
            "embed_sec": result.get("embed_sec"),
            "db_sec": result.get("db_sec"),
            "ts_strategy": result.get("ts_strategy"),
            "ts_terms_used": result.get("ts_terms_used"),
            "semantic_hits": result.get("semantic_hits"),
            "ts_hits": result.get("ts_hits"),
            "overlap": result.get("overlap"),
            "llm": result.get("llm"),
        }
        llm_obj = slim.get("llm") or {}
        if isinstance(llm_obj, dict) and llm_obj.get("mode") == "two_pass":
            markdown = str(((llm_obj.get("synth_pass") or {}).get("markdown") or ""))
        else:
            markdown = str(llm_obj.get("markdown") or "")
        _log(
            "🌐",
            f"Stage E done in {elapsed}s overlap.both={len(slim.get('overlap', {}).get('both') or [])} "
            f"answer_len={len(markdown)}",
        )
        return slim
    except Exception as exc:  # noqa: BLE001
        elapsed = round(time.monotonic() - t0, 3)
        _log("⚠️", f"Stage E failed: {exc}")
        return {
            "stage": "mkg_overall_synth",
            "elapsed_sec": elapsed,
            "synth_model": args.mkg_synth_model,
            "error": str(exc),
        }


# ---------------------------------------------------------------------------
# Patient discovery
# ---------------------------------------------------------------------------

def _discover_patients(cohort_dir: Path) -> List[Dict[str, Any]]:
    manifest_path = cohort_dir / "MANIFEST.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        patients = manifest.get("patients") or []
        out: List[Dict[str, Any]] = []
        for p in patients:
            f = p.get("file")
            if not f:
                continue
            full = cohort_dir / f
            if not full.exists():
                _log("⚠️", f"Manifest references missing file: {full}")
                continue
            out.append(
                {
                    "code": p.get("code") or full.stem,
                    "phenotype": p.get("phenotype") or "",
                    "label": p.get("label") or "",
                    "headline": p.get("headline") or "",
                    "patient_id": p.get("patient_id") or "",
                    "path": full,
                }
            )
        return out
    # Fallback: glob.
    out = []
    for f in sorted(cohort_dir.glob("ptv_synth_*.json")):
        out.append(
            {
                "code": f.stem.replace("ptv_synth_", "").upper(),
                "phenotype": "",
                "label": "",
                "headline": "",
                "patient_id": "",
                "path": f,
            }
        )
    return out


def _load_questions(path: Optional[Path]) -> Dict[str, str]:
    if not path or not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return {str(k).strip(): str(v).strip() for k, v in raw.items() if v}
    return {}


def _question_for(patient: Dict[str, Any], qmap: Dict[str, str], default: str) -> str:
    code = (patient.get("code") or "").strip().upper()
    phen = (patient.get("phenotype") or "").strip()
    if code and code in qmap:
        return qmap[code]
    if phen and phen in qmap:
        return qmap[phen]
    return default


# ---------------------------------------------------------------------------
# CLI / main
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--cohort-dir",
        type=Path,
        default=DEFAULT_COHORT_DIR,
        help="Directory containing synthetic FORWARD PTV JSONs (uses MANIFEST.json if present).",
    )
    ap.add_argument(
        "--questions-file",
        type=Path,
        default=DEFAULT_QUESTIONS_FILE,
        help="JSON map of {patient_code|phenotype: question}. Falls back to --question.",
    )
    ap.add_argument(
        "--question",
        type=str,
        default=DEFAULT_QUESTION,
        help="Default question used when --questions-file has no match for a patient.",
    )
    ap.add_argument("--probe-model", default=DEFAULT_PROBE_MODEL)
    ap.add_argument("--gap-model", default=DEFAULT_GAP_MODEL)
    ap.add_argument("--synth-model", default=DEFAULT_SYNTH_MODEL)
    ap.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    ap.add_argument("--probe-max-turns", type=int, default=6)
    ap.add_argument("--gap-max-turns", type=int, default=6)
    ap.add_argument("--temperature", type=float, default=0.15)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument(
        "--agent-num-ctx",
        type=int,
        default=int(os.environ.get("OLLAMA_AGENT_NUM_CTX", "32768")),
        help="num_ctx for Stage A/B tool-calling agents.",
    )
    ap.add_argument(
        "--synth-num-ctx",
        type=int,
        default=int(os.environ.get("OLLAMA_SYNTH_NUM_CTX", "32768")),
    )
    ap.add_argument(
        "--receipt-dir",
        type=Path,
        default=ROOT / "receipts",
    )
    ap.add_argument(
        "--reports-dir",
        type=Path,
        default=ROOT / "reports",
    )
    ap.add_argument(
        "--receipt-name",
        type=str,
        default="",
        help="Optional explicit basename (without extension). Defaults to FORWARD_PTV_3AGENT_<UTC>.",
    )
    ap.add_argument(
        "--no-pdf",
        action="store_true",
        help="Skip the auto-PDF rendering step at the end.",
    )
    ap.add_argument(
        "--patient-codes",
        type=str,
        default="",
        help="Comma-separated patient codes (e.g. P1,P3) — restrict the cycle to these patients.",
    )
    # ---- Stage E (MKG overall synth) ----
    ap.add_argument(
        "--no-mkg",
        action="store_true",
        help="Skip Stage E (MKG retrieval + overall synthesis with PTV summary as context).",
    )
    ap.add_argument(
        "--mkg-synth-model",
        default=DEFAULT_MKG_SYNTH_MODEL,
        help="Ollama model used for Stage-E overall synthesis.",
    )
    ap.add_argument(
        "--mkg-synth-num-ctx",
        type=int,
        default=int(os.environ.get("OLLAMA_SYNTH_NUM_CTX", "32768")),
        help="num_ctx for the Stage-E synthesis call (defaults to OLLAMA_SYNTH_NUM_CTX or 32768).",
    )
    ap.add_argument(
        "--mkg-use-router",
        dest="mkg_use_router",
        action="store_true",
        default=True,
        help="Enable the eoh-llama3.2 source-router during Stage-E retrieval (default on).",
    )
    ap.add_argument(
        "--mkg-no-router",
        dest="mkg_use_router",
        action="store_false",
        help="Disable the source-router during Stage-E retrieval.",
    )
    ap.add_argument(
        "--mkg-router-model",
        default=DEFAULT_MKG_ROUTER_MODEL,
    )
    ap.add_argument(
        "--mkg-router-num-ctx",
        type=int,
        default=int(os.environ.get("OLLAMA_ROUTER_NUM_CTX", "8192")),
    )
    ap.add_argument(
        "--mkg-router-restrict-sources",
        action="store_true",
        help="Restrict Stage-E retrieval to the router-selected sources.",
    )
    ap.add_argument(
        "--mkg-embed-model",
        default=DEFAULT_MKG_EMBED_MODEL,
    )
    ap.add_argument(
        "--mkg-top-k",
        type=int,
        default=10,
        help="Top-K hits per lane for Stage-E retrieval.",
    )
    ap.add_argument(
        "--mkg-two-pass-synth",
        dest="mkg_two_pass_synth",
        action="store_true",
        default=True,
        help="Enable Stage-E two-pass synth (compress summary + top evidence, then final synthesis).",
    )
    ap.add_argument(
        "--mkg-single-pass-synth",
        dest="mkg_two_pass_synth",
        action="store_false",
        help="Disable Stage-E two-pass synth and run single-pass synthesis.",
    )
    ap.add_argument(
        "--mkg-compress-model",
        default=os.environ.get("FORWARD_MKG_COMPRESS_MODEL", MODEL),
        help="Pass-1 compression model for Stage-E two-pass synth.",
    )
    ap.add_argument(
        "--mkg-compress-num-ctx",
        type=int,
        default=int(os.environ.get("OLLAMA_COMPRESS_NUM_CTX", "32768")),
        help="num_ctx for Stage-E compression pass.",
    )
    ap.add_argument(
        "--mkg-compress-evidence-k",
        type=int,
        default=8,
        help="Evidence count selected by Stage-E compression pass.",
    )
    ap.add_argument(
        "--mkg-sources",
        type=str,
        default="",
        help="Optional comma-separated rag_corpus.source filter for Stage-E retrieval.",
    )
    return ap.parse_args()


def _run_one_patient(
    *,
    patient: Dict[str, Any],
    args: argparse.Namespace,
    question: str,
) -> Dict[str, Any]:
    _log("👤", f"Patient {patient.get('code')} ({patient.get('phenotype')}) -> {patient['path'].name}")
    t0 = time.monotonic()
    gh = load_graph(patient["path"])
    _log("📈", f"Graph loaded events={len(gh.events)} hash={gh.graph_hash}")

    probe = _stage_probe(
        gh=gh,
        question=question,
        model=args.probe_model,
        ollama_url=args.ollama_url,
        max_turns=args.probe_max_turns,
        temperature=args.temperature,
        timeout=args.timeout,
        num_ctx=args.agent_num_ctx,
    )
    gap = _stage_gap(
        gh=gh,
        original_question=question,
        probe_stage=probe,
        model=args.gap_model,
        ollama_url=args.ollama_url,
        max_turns=args.gap_max_turns,
        temperature=args.temperature,
        timeout=args.timeout,
        num_ctx=args.agent_num_ctx,
    )
    bundle = _curate_bundle(
        original_question=question,
        probe_stage=probe,
        gap_stage=gap,
    )
    synth = _stage_synth(
        bundle=bundle,
        model=args.synth_model,
        ollama_url=args.ollama_url,
        temperature=args.temperature,
        timeout=args.timeout,
        num_ctx=args.synth_num_ctx,
    )

    stages: Dict[str, Any] = {
        "probe": probe,
        "gap": gap,
        "curated_bundle": bundle,
        "synthesis": synth,
    }

    if not args.no_mkg:
        ptv_md = (synth or {}).get("markdown") or ""
        stages["mkg_overall_synth"] = _stage_mkg_synth(
            original_question=question,
            patient=patient,
            ptv_synth_markdown=ptv_md,
            args=args,
        )
    else:
        _log("⏭️", "Stage E skipped (--no-mkg)")
        stages["mkg_overall_synth"] = {"stage": "mkg_overall_synth", "skipped": "flag"}

    return {
        "patient": patient,
        "question": question,
        "graph_hash": gh.graph_hash,
        "n_events": len(gh.events),
        "elapsed_sec": round(time.monotonic() - t0, 3),
        "stages": stages,
    }


def _serialize(out_path: Path, payload: Dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    _log("💾", f"Wrote receipt: {out_path}")


def _invoke_pdf(receipt_path: Path, reports_dir: Path) -> Optional[Path]:
    renderer = ROOT / "server" / "scripts" / "forward_ptv_3agent_pdf.py"
    if not renderer.exists():
        _log("⚠️", f"PDF renderer not found: {renderer}")
        return None
    # Guardrail: if reportlab is not installed in the active venv, skip PDF
    # rendering gracefully instead of surfacing a full traceback from child python.
    try:
        dep_check = subprocess.run(
            [sys.executable, "-c", "import reportlab"],
            check=False,
            capture_output=True,
            text=True,
        )
        if dep_check.returncode != 0:
            _log("⚠️", "PDF render skipped: missing Python dependency 'reportlab'")
            _log("⚠️", "Install with: pip install reportlab")
            return None
    except Exception as exc:  # noqa: BLE001
        _log("⚠️", f"PDF dependency check failed: {exc}")
        return None

    pdf_path = reports_dir / f"{receipt_path.stem}.pdf"
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable,
        str(renderer),
        "--receipt",
        str(receipt_path),
        "--out",
        str(pdf_path),
    ]
    _log("📄", f"Rendering PDF -> {pdf_path}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout.strip():
            _log("📄", result.stdout.strip().splitlines()[-1])
    except subprocess.CalledProcessError as exc:
        _log("⚠️", f"PDF render failed (rc={exc.returncode})")
        if exc.stderr:
            _log("⚠️", exc.stderr.strip()[:500])
        return None
    except FileNotFoundError as exc:
        _log("⚠️", f"PDF renderer invocation failed: {exc}")
        return None
    return pdf_path


def main() -> None:
    args = _parse_args()
    _log("🚀", "Starting FORWARD 3-agent PTV harness")

    cohort_dir = args.cohort_dir
    if not cohort_dir.exists():
        print(f"error: cohort dir not found: {cohort_dir}", file=sys.stderr)
        sys.exit(2)

    patients = _discover_patients(cohort_dir)
    if not patients:
        print(f"error: no patient PTVs found under {cohort_dir}", file=sys.stderr)
        sys.exit(2)

    if args.patient_codes:
        wanted = {c.strip().upper() for c in args.patient_codes.split(",") if c.strip()}
        patients = [p for p in patients if (p.get("code") or "").upper() in wanted]
        if not patients:
            print(f"error: no patients matched --patient-codes={args.patient_codes}", file=sys.stderr)
            sys.exit(2)
    _log("👥", f"Cycling through {len(patients)} patient(s)")

    qmap = _load_questions(args.questions_file)
    if qmap:
        _log("❓", f"Loaded per-patient question map ({len(qmap)} entries) from {args.questions_file}")
    else:
        _log("❓", "No per-patient question map found — using --question default for all.")

    started = time.monotonic()
    runs: List[Dict[str, Any]] = []
    for i, patient in enumerate(patients, start=1):
        question = _question_for(patient, qmap, args.question)
        _log("➡️", f"Patient {i}/{len(patients)} {patient.get('code')} - {question[:90]}")
        try:
            run = _run_one_patient(patient=patient, args=args, question=question)
        except Exception as exc:  # noqa: BLE001
            _log("⚠️", f"Patient {patient.get('code')} crashed: {exc}")
            run = {"patient": patient, "question": question, "error": str(exc)}
        run["index"] = i
        runs.append(run)

    payload = {
        "schema": "forward_ptv_3agent.v2",
        "built_at": datetime.now(timezone.utc).isoformat(),
        "cohort_dir": str(cohort_dir),
        "models": {
            "probe": args.probe_model,
            "gap": args.gap_model,
            "synth": args.synth_model,
            "mkg_overall_synth": None if args.no_mkg else args.mkg_synth_model,
            "mkg_router": None if (args.no_mkg or not args.mkg_use_router) else args.mkg_router_model,
            "mkg_embed": None if args.no_mkg else args.mkg_embed_model,
        },
        "config": {
            "probe_max_turns": args.probe_max_turns,
            "gap_max_turns": args.gap_max_turns,
            "temperature": args.temperature,
            "timeout": args.timeout,
            "agent_num_ctx": args.agent_num_ctx,
            "synth_num_ctx": args.synth_num_ctx,
            "ollama_url": args.ollama_url,
            "stage_e_enabled": not args.no_mkg,
            "mkg": None if args.no_mkg else {
                "use_router": bool(args.mkg_use_router),
                "two_pass_synth": bool(args.mkg_two_pass_synth),
                "compress_model": args.mkg_compress_model if args.mkg_two_pass_synth else None,
                "compress_num_ctx": args.mkg_compress_num_ctx if args.mkg_two_pass_synth else None,
                "compress_evidence_k": args.mkg_compress_evidence_k if args.mkg_two_pass_synth else None,
                "router_restrict_sources": bool(args.mkg_router_restrict_sources),
                "router_num_ctx": args.mkg_router_num_ctx,
                "synth_num_ctx": args.mkg_synth_num_ctx,
                "top_k": args.mkg_top_k,
                "user_sources": args.mkg_sources or None,
            },
        },
        "n_patients": len(patients),
        "elapsed_sec": round(time.monotonic() - started, 3),
        "runs": runs,
    }

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    base = args.receipt_name or f"FORWARD_PTV_3AGENT_{stamp}"
    receipt_path = (args.receipt_dir / f"{base}.json").resolve()
    _serialize(receipt_path, payload)

    if not args.no_pdf:
        pdf_path = _invoke_pdf(receipt_path, args.reports_dir.resolve())
        if pdf_path:
            _log("📄", f"PDF written: {pdf_path}")
    else:
        _log("⏭️", "Skipping PDF render (--no-pdf)")

    _log("🏁", "FORWARD 3-agent harness complete")


if __name__ == "__main__":
    main()
