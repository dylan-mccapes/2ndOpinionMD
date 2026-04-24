"""
ptv_toolkit_harness.py — agentic test harness for the PTV toolkit.

Loads an indexed PTV JSON graph, runs a question set through
``eoh-llama-lucifer`` (or any Ollama model) using the deterministic
tool loop in :mod:`server.ptv_toolkit.agent`, and scores whether the
agent chose a reasonable traversal method for each question.

Usage (PowerShell)::

    python server/scripts/ptv_toolkit_harness.py `
        --graph artifacts/forward_kaleb_package_20260423/PTV_REAL_EHR_20260423.json `
        --questions server/scripts/ptv_toolkit_questions.json `
        --model eoh-llama-lucifer `
        --out-dir artifacts/ptv_toolkit_runs

Outputs:
    <out-dir>/run_<UTCSTAMP>_<model>/
        turns.jsonl         — one line per question with full transcript
        summary.json        — aggregate metrics
        summary.md          — human-readable report

Scoring is intentionally simple:

* ``primary_tool_match``  — agent's first tool call == expected_primary_tool.
* ``any_tool_match``      — agent called the expected tool anywhere in the loop.
* ``final_has_evidence``  — final_answer.evidence_event_ids is non-empty and
                             every id exists in the graph.
* ``keyword_match``       — if `must_have_any` is non-empty, does the final
                             answer text contain at least one of them.

The goal is NOT perfect grading — it's to observe whether the 8B model,
given the toolkit catalog, routes each question to the right tool.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.ptv_toolkit import build_handoff, load_graph, save_handoff  # noqa: E402
from server.ptv_toolkit.agent import log_to_dict, run_agent  # noqa: E402
from server.ptv_toolkit.registry import tool_names  # noqa: E402


def _utcstamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _score_one(question: Dict[str, Any], agent_log: Dict[str, Any], graph_event_ids: set) -> Dict[str, Any]:
    seq = agent_log.get("tool_call_sequence") or []
    tools_used = agent_log.get("tools_used") or []
    expected = question.get("expected_primary_tool")
    expected_route = question.get("expected_route")
    precursors = set(question.get("allow_precursor_tools") or [])

    plan = agent_log.get("plan") or {}
    has_plan = bool(plan)
    plan_route = plan.get("route") if isinstance(plan, dict) else None
    plan_route_match = bool(expected_route and plan_route == expected_route)
    has_expanded_query = bool(
        isinstance(plan, dict) and plan.get("expanded_query") and plan.get("expanded_query") != question["question"]
    )

    # Primary-tool match: first non-precursor call (precursors still count
    # toward "any_tool_match" via the full seq).
    primary = None
    for t in seq:
        if t not in precursors:
            primary = t
            break
    primary_match = bool(primary and primary == expected)
    any_match = bool(expected and expected in tools_used)

    fa = agent_log.get("final_answer") or {}
    ev_ids = fa.get("evidence_event_ids") or []
    evidence_valid = bool(ev_ids) and all(eid in graph_event_ids for eid in ev_ids)

    ans_text = (fa.get("answer") or "").lower()
    kw = question.get("must_have_any") or []
    keyword_match = (not kw) or any(k.lower() in ans_text for k in kw)

    return {
        "has_plan": has_plan,
        "plan_route": plan_route,
        "plan_route_expected": expected_route,
        "plan_route_match": plan_route_match,
        "has_expanded_query": has_expanded_query,
        "primary_tool_called": primary,
        "primary_tool_expected": expected,
        "primary_tool_match": primary_match,
        "any_tool_match": any_match,
        "final_has_evidence": evidence_valid,
        "n_evidence_event_ids": len(ev_ids),
        "keyword_match": keyword_match,
        "tool_call_sequence": seq,
    }


def _render_markdown(summary: Dict[str, Any]) -> str:
    head = summary["header"]
    rows = summary["questions"]
    agg = summary["aggregate"]
    lines: List[str] = []
    lines.append(f"# PTV toolkit harness — {head['model']}")
    lines.append("")
    lines.append(f"- Graph: `{head['graph_path']}`")
    lines.append(f"- Graph hash: `{head['graph_hash']}`")
    lines.append(f"- Questions: {head['n_questions']}")
    lines.append(f"- Elapsed: {head['elapsed_sec']}s")
    lines.append("")
    lines.append("## Aggregate")
    lines.append("")
    lines.append(f"- Plan emitted:       {agg['has_plan']}/{agg['n']} "
                 f"({agg['plan_pct']:.0%})")
    lines.append(f"- Plan route match:   {agg['plan_route_match']}/{agg['n']} "
                 f"({agg['plan_route_pct']:.0%})")
    lines.append(f"- Expanded query:     {agg['has_expanded_query']}/{agg['n']}")
    lines.append(f"- Primary-tool match: **{agg['primary_tool_match']}/{agg['n']}** "
                 f"({agg['primary_pct']:.0%})")
    lines.append(f"- Any-tool match:     {agg['any_tool_match']}/{agg['n']} "
                 f"({agg['any_pct']:.0%})")
    lines.append(f"- Valid evidence ids: {agg['final_has_evidence']}/{agg['n']} "
                 f"({agg['evidence_pct']:.0%})")
    lines.append(f"- Keyword-match:      {agg['keyword_match']}/{agg['n']} "
                 f"({agg['keyword_pct']:.0%})")
    lines.append("")
    lines.append("## Per-question")
    lines.append("")
    lines.append("| # | ID | Route exp → obs | Primary exp → obs | Route ✓ | Primary ✓ | Evidence ✓ | Keyword ✓ |")
    lines.append("|---|----|------------------|--------------------|---------|-----------|------------|-----------|")
    for i, r in enumerate(rows, 1):
        s = r["score"]
        lines.append(
            f"| {i} | {r['id']} | "
            f"`{s['plan_route_expected']}` → `{s['plan_route']}` | "
            f"`{s['primary_tool_expected']}` → `{s['primary_tool_called']}` | "
            f"{'✅' if s['plan_route_match'] else '❌'} | "
            f"{'✅' if s['primary_tool_match'] else '❌'} | "
            f"{'✅' if s['final_has_evidence'] else '❌'} | "
            f"{'✅' if s['keyword_match'] else '❌'} |"
        )
    lines.append("")
    lines.append("## Traces")
    lines.append("")
    for r in rows:
        lines.append(f"### {r['id']}")
        lines.append("")
        lines.append(f"> {r['question']}")
        lines.append("")
        seq = r["score"]["tool_call_sequence"]
        lines.append(f"Tool-call sequence: `{seq}`")
        lines.append(f"Reason stopped: `{r['agent']['reason_stopped']}`  "
                     f"Elapsed: {r['agent']['elapsed_sec']}s")
        fa = r["agent"].get("final_answer") or {}
        lines.append("")
        if fa.get("answer"):
            lines.append("**Answer**")
            lines.append("")
            lines.append(fa["answer"])
            lines.append("")
        if fa.get("evidence_event_ids"):
            ev = ", ".join(f"`{e}`" for e in fa["evidence_event_ids"][:12])
            lines.append(f"**Evidence**: {ev}")
            lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--graph", default=str(
        ROOT / "artifacts" / "forward_kaleb_package_20260423" / "PTV_REAL_EHR_20260423.json"
    ))
    ap.add_argument("--questions", default=str(
        ROOT / "server" / "scripts" / "ptv_toolkit_questions.json"
    ))
    ap.add_argument("--model", default="eoh-llama-lucifer")
    ap.add_argument("--ollama-url", default="http://localhost:11434")
    ap.add_argument("--out-dir", default=str(ROOT / "artifacts" / "ptv_toolkit_runs"))
    ap.add_argument("--max-turns", type=int, default=6)
    ap.add_argument("--temperature", type=float, default=0.1)
    ap.add_argument("--timeout", type=float, default=240.0)
    ap.add_argument("--only", default="", help="comma-separated question ids to include")
    args = ap.parse_args()

    graph_path = Path(args.graph).resolve()
    qs_path = Path(args.questions).resolve()
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[harness] loading graph {graph_path}")
    gh = load_graph(graph_path)
    graph_ids = set(gh.events.keys())
    print(f"[harness] {len(graph_ids)} events indexed (hash {gh.graph_hash})")

    questions = json.loads(qs_path.read_text(encoding="utf-8"))
    if args.only:
        keep = set(x.strip() for x in args.only.split(",") if x.strip())
        questions = [q for q in questions if q["id"] in keep]

    stamp = _utcstamp()
    run_dir = out_dir / f"run_{stamp}_{args.model.replace(':', '_')}"
    run_dir.mkdir(parents=True, exist_ok=True)
    turns_path = run_dir / "turns.jsonl"
    summary_path = run_dir / "summary.json"
    md_path = run_dir / "summary.md"
    handoff_dir = run_dir / "handoffs"
    handoff_dir.mkdir(exist_ok=True)

    print(f"[harness] writing to {run_dir}")
    print(f"[harness] tools available: {tool_names()}")
    print(
        "[harness] note: the first semantic_search builds a full-graph "
        "embedding cache (~632 vectors). That step can take 1–5 minutes on "
        "CPU after the model loads; watch for a tqdm bar or "
        "[ptv_toolkit] embedding … lines. Later questions reuse the cache.",
        flush=True,
    )

    t0 = time.time()
    results: List[Dict[str, Any]] = []
    with turns_path.open("w", encoding="utf-8") as fh:
        for i, q in enumerate(questions, 1):
            qid = q.get("id") or f"q{i:02d}"
            print(f"\n[harness] ({i}/{len(questions)}) {qid}: {q['question'][:80]}")
            log = run_agent(
                gh,
                q["question"],
                model=args.model,
                ollama_url=args.ollama_url,
                max_turns=args.max_turns,
                temperature=args.temperature,
                timeout=args.timeout,
            )
            agent_log = log_to_dict(log)
            score = _score_one(q, agent_log, graph_ids)
            handoff = build_handoff(gh, log)
            save_handoff(handoff, handoff_dir / f"{qid}.handoff.json")
            row = {
                "id": qid,
                "question": q["question"],
                "expected_route": q.get("expected_route"),
                "expected_primary_tool": q.get("expected_primary_tool"),
                "score": score,
                "agent": agent_log,
                "handoff_path": str(handoff_dir / f"{qid}.handoff.json"),
                "working_set_size": handoff["working_set"]["n_included"],
            }
            fh.write(json.dumps(row, default=str) + "\n")
            fh.flush()
            results.append(row)
            print(f"    route={score['plan_route']!r}/{q.get('expected_route')!r}  "
                  f"primary={score['primary_tool_called']!r}/{q.get('expected_primary_tool')!r}  "
                  f"route_ok={score['plan_route_match']}  "
                  f"primary_ok={score['primary_tool_match']}  "
                  f"ws={handoff['working_set']['n_included']}  "
                  f"elapsed={agent_log['elapsed_sec']}s")

    elapsed = round(time.time() - t0, 2)

    n = len(results)
    agg = {
        "n": n,
        "has_plan": sum(1 for r in results if r["score"]["has_plan"]),
        "plan_route_match": sum(1 for r in results if r["score"]["plan_route_match"]),
        "has_expanded_query": sum(1 for r in results if r["score"]["has_expanded_query"]),
        "primary_tool_match": sum(1 for r in results if r["score"]["primary_tool_match"]),
        "any_tool_match": sum(1 for r in results if r["score"]["any_tool_match"]),
        "final_has_evidence": sum(1 for r in results if r["score"]["final_has_evidence"]),
        "keyword_match": sum(1 for r in results if r["score"]["keyword_match"]),
    }
    agg["plan_pct"] = agg["has_plan"] / max(n, 1)
    agg["plan_route_pct"] = agg["plan_route_match"] / max(n, 1)
    agg["primary_pct"] = agg["primary_tool_match"] / max(n, 1)
    agg["any_pct"] = agg["any_tool_match"] / max(n, 1)
    agg["evidence_pct"] = agg["final_has_evidence"] / max(n, 1)
    agg["keyword_pct"] = agg["keyword_match"] / max(n, 1)

    summary = {
        "header": {
            "model": args.model,
            "graph_path": str(graph_path),
            "graph_hash": gh.graph_hash,
            "n_questions": n,
            "elapsed_sec": elapsed,
            "run_dir": str(run_dir),
            "timestamp_utc": stamp,
            "max_turns": args.max_turns,
            "temperature": args.temperature,
        },
        "aggregate": agg,
        "questions": results,
    }
    summary_path.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    md_path.write_text(_render_markdown(summary), encoding="utf-8")

    print(f"\n[harness] done in {elapsed}s")
    print(f"  plan emitted:       {agg['has_plan']}/{n} ({agg['plan_pct']:.0%})")
    print(f"  plan-route match:   {agg['plan_route_match']}/{n} ({agg['plan_route_pct']:.0%})")
    print(f"  expanded query:     {agg['has_expanded_query']}/{n}")
    print(f"  primary-tool match: {agg['primary_tool_match']}/{n} ({agg['primary_pct']:.0%})")
    print(f"  any-tool match:     {agg['any_tool_match']}/{n} ({agg['any_pct']:.0%})")
    print(f"  valid evidence:     {agg['final_has_evidence']}/{n}")
    print(f"  keyword match:      {agg['keyword_match']}/{n}")
    print(f"  transcripts:        {turns_path}")
    print(f"  markdown summary:   {md_path}")
    print(f"  handoffs:           {handoff_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
