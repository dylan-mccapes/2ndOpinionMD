#!/usr/bin/env python3
"""
EoH source-routing harness (planning only).

Given a user clinical query, asks a local Ollama router model to choose:
  1) rag_corpus sources to search next (bounded by max sources)
  2) EoH modules to involve conceptually (bounded by max modules)
  3) lexical and semantic query expansions for TS + ANN retrieval

This harness does NOT execute retrieval. It only emits a route plan JSON.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.eoh.module_index import MODULE_INDEX
from server.mkg.portalnode_pilot_sources import pilot_source_descriptions


def _log(emoji: str, msg: str) -> None:
    print(f"{emoji} {msg}", file=sys.stderr, flush=True)


def _extract_json_object(raw: str) -> Dict[str, Any]:
    s = raw.strip()
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
    raise ValueError("No parseable JSON object in model response.")


def _load_queries(args: argparse.Namespace) -> List[str]:
    if args.questions_file:
        _log("📚", f"Reading questions file: {args.questions_file}")
        out: List[str] = []
        for raw in args.questions_file.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            out.append(line)
        return out
    if args.query_file:
        _log("📄", f"Reading query file: {args.query_file}")
        q = args.query_file.read_text(encoding="utf-8").strip()
        return [q] if q else []
    q = (args.query or "").strip()
    return [q] if q else []


def _load_source_candidates(args: argparse.Namespace) -> Dict[str, str]:
    if args.sources_file:
        _log("📚", f"Reading source candidates from: {args.sources_file}")
        wanted = []
        for raw in args.sources_file.read_text(encoding="utf-8").splitlines():
            line = raw.split("#", 1)[0].strip().lower()
            if line:
                wanted.append(line)
        full = pilot_source_descriptions(sources=None)
        return {k: v for k, v in full.items() if k in set(wanted)}
    return pilot_source_descriptions(sources=None)


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
) -> str:
    try:
        import requests
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError("Missing dependency 'requests'. Install in active venv: pip install requests") from exc

    num_ctx = max(2048, int(os.environ.get("OLLAMA_NUM_CTX", "8192")))
    _log("🤖", f"Ollama call model={model} num_ctx={num_ctx} timeout={timeout:.0f}s")
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


def _build_system_prompt() -> str:
    return (
        "You are an EoH source-routing planner. You must return STRICT JSON only.\n"
        "Task: from one user query, choose rag sources, choose EoH modules, and create retrieval queries.\n"
        "Do not answer clinically. Do not fabricate source keys or module IDs.\n\n"
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
        "}\n\n"
        "Rules:\n"
        "- Sources and modules must come from provided candidate lists.\n"
        "- Use priority=1 as highest; increase as relevance decreases.\n"
        "- Keep selected_sources <= max_sources and selected_modules <= max_modules.\n"
        "- semantic_query should include synonyms and domain terms for ANN retrieval.\n"
        "- ts_query should be concise and lexical for Postgres full-text search.\n"
        "- ts_terms should be 4-12 useful tokens/phrases for TS probing."
    )


def _build_user_prompt(
    *,
    query: str,
    source_candidates: Dict[str, str],
    module_candidates: Dict[str, Dict[str, str]],
    max_sources: int,
    max_modules: int,
) -> str:
    payload = {
        "query": query,
        "max_sources": max_sources,
        "max_modules": max_modules,
        "source_candidates": source_candidates,
        "module_candidates": module_candidates,
    }
    return "Plan source/module routing for this query.\n\n" + json.dumps(payload, ensure_ascii=True, indent=2)


def _clean_terms(items: Any) -> List[str]:
    out: List[str] = []
    for x in (items or []):
        s = str(x).strip()
        if s:
            out.append(s)
    return out


def _post_validate(
    plan: Dict[str, Any],
    *,
    source_candidates: Dict[str, str],
    module_candidates: Dict[str, Dict[str, str]],
    max_sources: int,
    max_modules: int,
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

    valid_qtypes = {"A", "B", "C", "D", "E", "OTHER"}
    if out["question_type"] not in valid_qtypes:
        out["question_type"] = "OTHER"

    for row in (plan.get("selected_sources") or []):
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

    for row in (plan.get("selected_modules") or []):
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

    # Fallbacks so downstream harnesses always get usable queries.
    if not out["semantic_query"]:
        out["semantic_query"] = out["ts_query"] or ""
    if not out["ts_query"]:
        out["ts_query"] = out["semantic_query"] or ""
    if not out["ts_terms"]:
        out["ts_terms"] = [t for t in re.split(r"\s+", out["ts_query"]) if t][:8]

    return out


def _parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="EoH source-router harness (select sources/modules + TS/semantic expansions).")
    ap.add_argument("query", nargs="?", help="User query to route")
    ap.add_argument("--query-file", type=Path, help="UTF-8 file containing query text")
    ap.add_argument(
        "--questions-file",
        type=Path,
        help="UTF-8 file with one query per line (# comments and blank lines ignored)",
    )
    ap.add_argument(
        "--sources-file",
        type=Path,
        help="Optional source candidates file (one source per line). Defaults to portal pilot source list.",
    )
    ap.add_argument("--max-sources", type=int, default=8)
    ap.add_argument("--max-modules", type=int, default=6)
    ap.add_argument("--ollama-url", default=os.environ.get("OLLAMA_URL", "http://127.0.0.1:11434"))
    ap.add_argument("--model", default=os.environ.get("EOH_SOURCE_ROUTER_MODEL", "eoh-llama3.2-source-router"))
    ap.add_argument("--temperature", type=float, default=0.1)
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--out", type=Path, help="Write output JSON to file")
    return ap.parse_args()


def _run_one_query(
    *,
    query: str,
    args: argparse.Namespace,
    source_candidates: Dict[str, str],
    module_candidates: Dict[str, Dict[str, str]],
) -> Dict[str, Any]:
    system = _build_system_prompt()
    user = _build_user_prompt(
        query=query,
        source_candidates=source_candidates,
        module_candidates=module_candidates,
        max_sources=max(1, args.max_sources),
        max_modules=max(1, args.max_modules),
    )

    t0 = time.monotonic()
    raw = _ollama_chat(
        url=args.ollama_url,
        model=args.model,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        timeout=args.timeout,
        temperature=args.temperature,
    )
    _log("✅", f"Router model completed in {time.monotonic() - t0:.3f}s")

    try:
        parsed = _extract_json_object(raw)
    except Exception as exc:  # noqa: BLE001
        _log("⚠️", f"JSON parse failed; returning raw model text ({exc})")
        out = {
            "query": query,
            "model": args.model,
            "error": "parse_failed",
            "raw": raw,
        }
    else:
        clean = _post_validate(
            parsed,
            source_candidates=source_candidates,
            module_candidates=module_candidates,
            max_sources=max(1, args.max_sources),
            max_modules=max(1, args.max_modules),
        )
        out = {
            "query": query,
            "model": args.model,
            "max_sources": max(1, args.max_sources),
            "max_modules": max(1, args.max_modules),
            "source_candidates_count": len(source_candidates),
            "module_candidates_count": len(module_candidates),
            "route_plan": clean,
        }
    return out


def main() -> None:
    args = _parse_args()
    _log("🚀", "Starting EoH source-router harness")

    queries = _load_queries(args)
    if not queries:
        print("error: provide query, --query-file, or --questions-file", file=sys.stderr)
        sys.exit(2)
    _log("❓", f"Loaded {len(queries)} question(s)")

    source_candidates = _load_source_candidates(args)
    module_candidates = _module_candidates()
    _log("📚", f"Loaded source candidates: {len(source_candidates)}")
    _log("🧩", f"Loaded module candidates: {len(module_candidates)}")

    if len(queries) == 1:
        out = _run_one_query(
            query=queries[0],
            args=args,
            source_candidates=source_candidates,
            module_candidates=module_candidates,
        )
        text = json.dumps(out, indent=2, ensure_ascii=False)
        print(text)
        if args.out:
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text(text + "\n", encoding="utf-8")
            _log("💾", f"Wrote output file: {args.out}")
        _log("🏁 Source-router harness complete")
        return

    _log("📚", "Batch mode enabled")
    t0 = time.monotonic()
    runs: List[Dict[str, Any]] = []
    for i, q in enumerate(queries, start=1):
        _log("➡️", f"Batch question {i}/{len(queries)}: {q[:90]}")
        run = _run_one_query(
            query=q,
            args=args,
            source_candidates=source_candidates,
            module_candidates=module_candidates,
        )
        run["batch_index"] = i
        runs.append(run)

    out = {
        "batch": {
            "n_questions": len(queries),
            "elapsed_sec": round(time.monotonic() - t0, 3),
            "model": args.model,
            "max_sources": max(1, args.max_sources),
            "max_modules": max(1, args.max_modules),
        },
        "runs": runs,
    }

    text = json.dumps(out, indent=2, ensure_ascii=False)
    print(text)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(text + "\n", encoding="utf-8")
        _log("💾", f"Wrote output file: {args.out}")
    _log("🏁", "Source-router harness complete")


if __name__ == "__main__":
    main()
