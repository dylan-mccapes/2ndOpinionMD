#!/usr/bin/env python3
"""Direct streaming test for eoh-qwen3-14b (128K default) on P1 synthetic graph."""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.ptv_toolkit.graph import load_graph
from server.ptv_toolkit.registry import call_tool

DEFAULT_GRAPH = (
    ROOT
    / "artifacts"
    / "forward_kaleb_package_20260423"
    / "synthetic_pro_cohort"
    / "ptv_synth_P1_early_responder.json"
)

QUESTION = (
    "Walk me through this patient's five-year FORWARD trajectory. Highlight any flares, "
    "treatment escalations or de-escalations, key medications around those times, and any "
    "notable areas of uncertainty."
)
DEFAULT_SEMANTIC_K = 32
DEFAULT_CODE_INDEX_LIMIT = 200
DEFAULT_TEMPORAL_LIMIT = 120


def _log(emoji: str, msg: str) -> None:
    print(f"{emoji} {msg}", file=sys.stderr, flush=True)


def _clip(value: Any, n: int = 5000) -> str:
    text = json.dumps(value, ensure_ascii=False, indent=2, default=str)
    return text if len(text) <= n else text[:n] + "\n...[truncated]"


def _build_context() -> Dict[str, Any]:
    _log("🧩", f"Loading graph: {DEFAULT_GRAPH}")
    gh = load_graph(DEFAULT_GRAPH)
    _log("📈", "Running graph_stats")
    stats = call_tool("graph_stats", gh, {})
    semantic_k = int(os.environ.get("EOH_QWEN14B_SEMANTIC_K", str(DEFAULT_SEMANTIC_K)))
    med_limit = int(os.environ.get("EOH_QWEN14B_CODE_INDEX_LIMIT", str(DEFAULT_CODE_INDEX_LIMIT)))
    temporal_limit = int(os.environ.get("EOH_QWEN14B_TEMPORAL_LIMIT", str(DEFAULT_TEMPORAL_LIMIT)))
    _log("🔎", f"Running semantic_search (k={semantic_k})")
    sem = call_tool("semantic_search", gh, {"query": QUESTION, "k": semantic_k})
    _log("💊", "Running code_index_lookup for medications")
    meds = call_tool(
        "code_index_lookup",
        gh,
        {"bucket": "drugs", "list_keys": True, "limit": med_limit},
    )
    _log("🧾", f"Running temporal_scan for longitudinal events (limit={temporal_limit})")
    timeline = call_tool(
        "temporal_scan",
        gh,
        {"order": "asc", "limit": temporal_limit},
    )
    return {
        "graph_path": str(DEFAULT_GRAPH),
        "graph_hash": gh.graph_hash,
        "n_events": len(gh.events),
        "question": QUESTION,
        "graph_stats": stats,
        "semantic_search": sem,
        "medication_index": meds,
        "temporal_scan": timeline,
    }


def main() -> int:
    model = os.environ.get("EOH_QWEN14B_MODEL", "eoh-qwen3-14b")
    ollama_url = os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
    num_ctx = int(os.environ.get("OLLAMA_NUM_CTX", "131072"))

    _log("🚀", "Starting direct eoh-qwen3-14b streaming test (high-context profile)")
    payload_context = _build_context()
    system = (
        "You are eoh-qwen3-14b in direct clinical test mode.\n"
        "Output exactly two sections in this order:\n"
        "1) THINKING\n"
        "2) FINAL ANSWER\n\n"
        "THINKING:\n"
        "- Use step-by-step bullet points.\n"
        "- Explicitly reason about trajectory phases, flares, medication changes, and uncertainty.\n"
        "- Stay grounded in supplied context only.\n\n"
        "FINAL ANSWER:\n"
        "- Give a concise clinician-facing synthesis.\n"
        "- Include a short uncertainty paragraph.\n"
    )
    user = "Use the context JSON below to answer the question.\n\n" + _clip(payload_context, n=120000)
    req = {
        "model": model,
        "stream": True,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "options": {
            "num_ctx": num_ctx,
            "temperature": 0.2,
            "top_p": 0.9,
            "repeat_penalty": 1.08,
        },
    }

    _log("🤖", f"model={model} num_ctx={num_ctx} ollama_url={ollama_url} graph={DEFAULT_GRAPH.name}")
    print(f"model={model} num_ctx={num_ctx} graph={DEFAULT_GRAPH.name} (semantic_k={os.environ.get('EOH_QWEN14B_SEMANTIC_K', str(DEFAULT_SEMANTIC_K))})")
    print("\n--- STREAM START (live chunks) ---\n")

    t0 = time.monotonic()
    n_chunks = 0
    n_chars = 0
    last_progress = t0
    _log("📡", "Posting streaming request to Ollama /api/chat")
    with requests.post(
        f"{ollama_url}/api/chat",
        json=req,
        stream=True,
        timeout=900,
    ) as resp:
        resp.raise_for_status()
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            obj = json.loads(line)
            tok = ((obj.get("message") or {}).get("content")) or ""
            if tok:
                n_chunks += 1
                n_chars += len(tok)
                print(tok, end="", flush=True)
                now = time.monotonic()
                if now - last_progress >= 2.0:
                    _log("⏱️", f"streaming... chunks={n_chunks} chars={n_chars} elapsed={now - t0:.1f}s")
                    last_progress = now
            if obj.get("done"):
                break

    print("\n\n--- STREAM END ---")
    elapsed = time.monotonic() - t0
    _log("✅", f"Done. chunks={n_chunks} chars={n_chars} elapsed={elapsed:.1f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

