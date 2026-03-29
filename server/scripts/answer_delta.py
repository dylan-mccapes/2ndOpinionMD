#!/usr/bin/env python3
"""
Answer Delta Test Harness
=========================
Proves that graph enrichment improves reasoning quality by running the same
EoH Detective query with and without opportunistic graph enrichment enabled,
then scoring each step answer with an LLM and structural metrics.

TWO MODES
---------

frozen_post (DEFAULT — correct experimental design)
  Stage one graph. Run PRE with enrichment disabled (no-op patched) to get a
  clean baseline. Then run POST with enrichment enabled on the same graph.
  Answers the question: "does in-flight enrichment improve reasoning quality?"

  Usage:
      python -u scripts/answer_delta.py \\
          --graph "artifacts/timeline_full_20260327_1717/patient_timeline_vision_norman_eric_roberts_20260327_174843_enriched.json" \\
          --chart "artifacts/timeline_full_20260327_1717/patient_chart_index_v2.jsonl" \\
          --out "artifacts/answer_delta_$(date +%Y%m%d_%H%M).md"

staged (explicit two-graph comparison)
  Stage two explicitly provided graphs. Warns if they share identical
  event/edge counts (a sign you're comparing the same graph twice).
  Answers the question: "does starting from a richer graph produce better answers?"

  Usage:
      python -u scripts/answer_delta.py --mode staged \\
          --pre  "artifacts/.../vision_raw.json" \\
          --post "artifacts/.../vision_enriched.json" \\
          --pre-chart  "artifacts/.../chart_v1.jsonl" \\
          --post-chart "artifacts/.../chart_v2.jsonl" \\
          --out "artifacts/answer_delta_$(date +%Y%m%d_%H%M).md"

The gold output is the `detective_summary` SSE event, which carries
`steps[].answer_text` for every detective step.

Use --no-cleanup to preserve the temporary Postgres rows after the run.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
script_dir = Path(__file__).resolve().parent
server_dir = script_dir.parent
parent_of_server = server_dir.parent  # 2ndOpinionMD-MVP/

if str(parent_of_server) not in sys.path:
    sys.path.insert(0, str(parent_of_server))

os.chdir(server_dir)

from dotenv import load_dotenv
load_dotenv(server_dir / ".env", override=True)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(name)s │ %(message)s",
    stream=sys.stderr,
)
log = logging.getLogger("answer_delta")
for noisy in ("httpx", "httpcore", "urllib3", "openai"):
    logging.getLogger(noisy).setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# Heavy imports (after path bootstrap)
# ---------------------------------------------------------------------------
import asyncpg
from openai import AsyncOpenAI, OpenAI

from server.api.db import init_pool, close_pool
from server.api.stream_config import EOH_STREAM_DEFAULT_SOURCES
from server.api.rag_stream_detective import eoh_detective_stream_event_generator
from server.eoh.patient_timeline_vision import PatientTimelineVision
from server.eoh.patient_timeline_chart import PatientTimelineChart
import server.eoh.graph_enrichment as _ge

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DELTA_SUFFIX_PRE = "_DELTA_PRE"
DELTA_SUFFIX_POST = "_DELTA_POST"
MODE_FROZEN_POST = "frozen_post"
MODE_STAGED = "staged"

# ---------------------------------------------------------------------------
# Enrichment gate (monkey-patch for frozen_post PRE run)
# ---------------------------------------------------------------------------
_ORIGINAL_ENRICH = _ge.enrich_graph_opportunistic


async def _noop_enrich(**kwargs: Any) -> Dict[str, Any]:
    """Drop-in no-op replacement for enrich_graph_opportunistic."""
    log.info("[frozen_post PRE] Enrichment suppressed for step %s", kwargs.get("step_id", "?"))
    return {
        "step_id": kwargs.get("step_id", "?"),
        "events_added": 0,
        "edges_added": 0,
        "elapsed_ms": 0,
        "error": None,
        "frozen": True,
    }


def _disable_enrichment() -> None:
    _ge.enrich_graph_opportunistic = _noop_enrich
    log.info("Opportunistic enrichment DISABLED (PRE run)")


def _enable_enrichment() -> None:
    _ge.enrich_graph_opportunistic = _ORIGINAL_ENRICH
    log.info("Opportunistic enrichment ENABLED (POST run)")

SCORER_SYSTEM = """
You are a clinical AI evaluator comparing two reasoning answers about the same patient.

Answer A was generated from a SMALLER, PRE-ENRICHMENT knowledge graph.
Answer B was generated from a LARGER, POST-ENRICHMENT graph that has more events and edges.

Your task: evaluate the reasoning quality improvement from A → B.

Return ONLY valid JSON with this exact structure:
{
  "better_answer": "pre" | "post" | "equal",
  "improvement_score": <integer 0-10>,
  "new_information": ["<fact in B not in A>", ...],
  "gaps_addressed": ["<gap flagged in A that B resolves>", ...],
  "still_missing": ["<important gap still unaddressed in B>", ...],
  "confidence_delta": "increased" | "decreased" | "unchanged",
  "specificity_delta": "increased" | "decreased" | "unchanged",
  "reasoning": "<1-3 sentence explanation>"
}

improvement_score guide:
  0-2  = A is better or equivalent
  3-4  = B is marginally better
  5-6  = B is clearly better
  7-8  = B is substantially better with important new information
  9-10 = B is dramatically better; A would be dangerously incomplete
""".strip()


# ---------------------------------------------------------------------------
# Mock FastAPI Request (for is_disconnected())
# ---------------------------------------------------------------------------
class _MockRequest:
    """Minimal stand-in for a FastAPI Request inside the detective generator."""

    class _EmptyParams:
        def get(self, key: str, default: Any = None) -> Any:
            return default

        def __contains__(self, key: str) -> bool:
            return False

    query_params = _EmptyParams()

    async def is_disconnected(self) -> bool:
        return False


# ---------------------------------------------------------------------------
# Graph + chart loading
# ---------------------------------------------------------------------------

async def _load_vision_to_pg(conn, vision: PatientTimelineVision) -> None:
    await conn.execute(
        """
        INSERT INTO ehr.patient_graph_vision (patient_id, graph_json, updated_at)
        VALUES ($1, $2::jsonb, NOW())
        ON CONFLICT (patient_id)
        DO UPDATE SET graph_json = EXCLUDED.graph_json, updated_at = NOW()
        """,
        vision.patient_id,
        json.dumps(vision.to_dict(), ensure_ascii=False),
    )


async def _load_chart_to_pg(conn, patient_id: str, chart: PatientTimelineChart) -> None:
    await conn.execute(
        "DELETE FROM ehr.patient_graph_chart WHERE patient_id = $1",
        patient_id,
    )
    rows = [
        (
            patient_id,
            p.event_id,
            p.event_type,
            p.timestamp,
            p.preview[:500],
            json.dumps(p.embedding),
        )
        for p in chart._points
    ]
    if rows:
        await conn.executemany(
            """
            INSERT INTO ehr.patient_graph_chart
                (patient_id, event_id, event_type, ts_text, preview, embedding)
            VALUES ($1, $2, $3, $4, $5, $6::vector)
            """,
            rows,
        )


async def _upsert_status(conn, patient_id: str, vision: PatientTimelineVision, chart_count: int) -> None:
    await conn.execute(
        """
        INSERT INTO ehr.patient_graph_status
            (patient_id, is_ready, event_count, edge_count, chart_count,
             ts_coverage, built_at, updated_at)
        VALUES ($1, TRUE, $2, $3, $4, 0.0, NOW(), NOW())
        ON CONFLICT (patient_id)
        DO UPDATE SET
            is_ready    = TRUE,
            event_count = EXCLUDED.event_count,
            edge_count  = EXCLUDED.edge_count,
            chart_count = EXCLUDED.chart_count,
            built_at    = EXCLUDED.built_at,
            updated_at  = NOW()
        """,
        patient_id,
        len(vision.events),
        vision.count_edges(),
        chart_count,
    )


async def _cleanup_pg(pool, patient_id: str) -> None:
    async with pool.acquire() as conn:
        for table in ("ehr.patient_graph_chart", "ehr.patient_graph_vision", "ehr.patient_graph_status"):
            await conn.execute(f"DELETE FROM {table} WHERE patient_id = $1", patient_id)


def _load_or_build_chart(vision: PatientTimelineVision, chart_path: Optional[Path]) -> Tuple[PatientTimelineChart, int]:
    chart = PatientTimelineChart()
    if chart_path and chart_path.exists():
        count = chart.load_index(chart_path)
        log.info("Chart loaded from file: %d points", count)
    else:
        log.info("No chart file provided — building from vision (this takes ~60s)…")
        count = chart.build_from_vision(vision)
        log.info("Chart built: %d points", count)
    return chart, count


async def stage_graph(
    pool,
    vision_path: Path,
    chart_path: Optional[Path],
    temp_patient_id: str,
) -> Dict[str, Any]:
    """Load a graph + chart into Postgres under temp_patient_id. Returns stats."""
    log.info("Loading vision: %s", vision_path)
    vision = PatientTimelineVision.load(str(vision_path))
    if not vision.events:
        raise ValueError(f"Vision at {vision_path} has no events")

    original_patient_id = vision.patient_id
    vision.patient_id = temp_patient_id

    chart, chart_count = _load_or_build_chart(vision, chart_path)

    async with pool.acquire() as conn:
        await _load_vision_to_pg(conn, vision)
        await _load_chart_to_pg(conn, temp_patient_id, chart)
        await _upsert_status(conn, temp_patient_id, vision, chart_count)

    stats = {
        "original_patient_id": original_patient_id,
        "temp_patient_id": temp_patient_id,
        "events": len(vision.events),
        "edges": vision.count_edges(),
        "chart_points": chart_count,
    }
    log.info(
        "Staged %s → %s  (%d events, %d edges, %d chart pts)",
        original_patient_id, temp_patient_id,
        stats["events"], stats["edges"], stats["chart_points"],
    )
    return stats


# ---------------------------------------------------------------------------
# Run detective + capture answers
# ---------------------------------------------------------------------------

async def run_detective(
    pool,
    patient_id: str,
    query: str,
    max_steps: int,
    label: str,
) -> Dict[str, Any]:
    """Drive the detective generator and return captured summary + mutations."""
    log.info("[%s] Starting detective run (patient_id=%s, max_steps=%d)", label, patient_id, max_steps)
    t0 = time.perf_counter()

    summary: Optional[Dict] = None
    report: Optional[str] = None
    mutations: List[Dict] = []
    event_count = 0

    async for ev in eoh_detective_stream_event_generator(
        request=_MockRequest(),
        q=query,
        timeline_patient_id=patient_id,
        pool=pool,
        max_steps=max_steps,
        db_sources=list(EOH_STREAM_DEFAULT_SOURCES),
        with_llm=True,
        use_valyu=False,
    ):
        event_count += 1
        event_name = ev.get("event", "")

        if event_name == "detective_summary":
            try:
                summary = json.loads(ev.get("data", "{}"))
            except Exception:
                log.warning("[%s] Could not parse detective_summary", label)

        elif event_name == "detective_report":
            try:
                d = json.loads(ev.get("data", "{}"))
                report = d.get("report")
            except Exception:
                log.warning("[%s] Could not parse detective_report", label)

        elif event_name == "graph_enrichment_result":
            try:
                mutations.append(json.loads(ev.get("data", "{}")))
            except Exception:
                pass

        # Progress heartbeat
        if event_count % 50 == 0:
            log.info("[%s] %d SSE events processed…", label, event_count)

    elapsed = time.perf_counter() - t0
    steps = (summary or {}).get("steps", [])
    log.info(
        "[%s] Done: %d steps, %d events answered, %.1fs",
        label, len(steps), event_count, elapsed,
    )

    # Derive final graph state from mutation log
    final_events = staged_events = None
    final_edges = staged_edges = None
    total_events_added = sum(m.get("events_added", 0) for m in mutations)
    total_edges_added = sum(m.get("edges_added", 0) for m in mutations)
    total_causal_added = sum(m.get("causal_annotations_added", 0) for m in mutations)
    total_confounders_added = sum(m.get("confounder_annotations_added", 0) for m in mutations)
    if mutations:
        last = mutations[-1]
        final_events = last.get("graph_events_total")
        final_edges = last.get("graph_edges_total")

    return {
        "label": label,
        "patient_id": patient_id,
        "elapsed_s": elapsed,
        "sse_events": event_count,
        "summary": summary,
        "report": report,
        "mutations": mutations,
        "total_events_added": total_events_added,
        "total_edges_added": total_edges_added,
        "total_causal_added": total_causal_added,
        "total_confounders_added": total_confounders_added,
        "final_events": final_events,
        "final_edges": final_edges,
    }


# ---------------------------------------------------------------------------
# Structural metrics (no LLM required)
# ---------------------------------------------------------------------------
_HEDGE_PATTERN = re.compile(
    r"\b(may|might|possibly|perhaps|unclear|uncertain|unknown|appear[s]?|suggest[s]?|seem[s]?|likely|unlikely|probable|improbable)\b",
    re.IGNORECASE,
)
_CAUSAL_PATTERN = re.compile(
    r"\b(caused by|due to|resulted in|led to|associated with|triggered by|secondary to|in response to|following|precipitated)\b",
    re.IGNORECASE,
)
_TEMPORAL_PATTERN = re.compile(
    r"\b(\d{4}|\d{1,2}/\d{4}|january|february|march|april|may|june|july|august|september|october|november|december)\b",
    re.IGNORECASE,
)


def structural_metrics(text: str) -> Dict[str, int]:
    words = text.split()
    sentences = [s.strip() for s in re.split(r"[.!?]", text) if s.strip()]
    return {
        "word_count": len(words),
        "sentence_count": len(sentences),
        "uncertainty_hedges": len(_HEDGE_PATTERN.findall(text)),
        "causal_claims": len(_CAUSAL_PATTERN.findall(text)),
        "temporal_refs": len(_TEMPORAL_PATTERN.findall(text)),
    }


def metrics_delta(pre: Dict[str, int], post: Dict[str, int]) -> Dict[str, int]:
    return {k: post[k] - pre[k] for k in pre}


# ---------------------------------------------------------------------------
# LLM scoring
# ---------------------------------------------------------------------------

async def score_step_delta(
    client: AsyncOpenAI,
    step_id: str,
    step_kind: str,
    question: str,
    pre_answer: str,
    post_answer: str,
) -> Dict[str, Any]:
    """Ask LLM to score the improvement from pre_answer → post_answer."""
    user_content = json.dumps(
        {
            "step_id": step_id,
            "step_kind": step_kind,
            "question": question,
            "answer_A_pre_enrichment": pre_answer,
            "answer_B_post_enrichment": post_answer,
        },
        ensure_ascii=False,
    )
    try:
        resp = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SCORER_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.0,
            max_tokens=600,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content or "{}"
        return json.loads(raw)
    except Exception as exc:
        log.warning("LLM scorer failed for step %s: %s", step_id, exc)
        return {
            "better_answer": "unknown",
            "improvement_score": -1,
            "new_information": [],
            "gaps_addressed": [],
            "still_missing": [],
            "confidence_delta": "unknown",
            "specificity_delta": "unknown",
            "reasoning": f"Scorer error: {exc}",
        }


async def score_all_steps(
    client: AsyncOpenAI,
    pre_steps: List[Dict],
    post_steps: List[Dict],
) -> List[Dict[str, Any]]:
    """Pair up steps by step_id and score each one in parallel."""
    pre_by_id = {s["step_id"]: s for s in pre_steps}
    post_by_id = {s["step_id"]: s for s in post_steps}

    all_step_ids = sorted(set(pre_by_id) | set(post_by_id))

    tasks = []
    for sid in all_step_ids:
        pre_s = pre_by_id.get(sid, {})
        post_s = post_by_id.get(sid, {})
        tasks.append(score_step_delta(
            client=client,
            step_id=sid,
            step_kind=pre_s.get("kind") or post_s.get("kind", "unknown"),
            question=pre_s.get("q") or post_s.get("q", ""),
            pre_answer=pre_s.get("answer_text", ""),
            post_answer=post_s.get("answer_text", ""),
        ))

    scores = await asyncio.gather(*tasks)
    return [
        {
            "step_id": sid,
            "kind": (pre_by_id.get(sid, {}).get("kind") or post_by_id.get(sid, {}).get("kind", "?")),
            "question": (pre_by_id.get(sid, {}).get("q") or post_by_id.get(sid, {}).get("q", "")),
            "pre_word_count": len((pre_by_id.get(sid, {}).get("answer_text") or "").split()),
            "post_word_count": len((post_by_id.get(sid, {}).get("answer_text") or "").split()),
            "pre_metrics": structural_metrics(pre_by_id.get(sid, {}).get("answer_text") or ""),
            "post_metrics": structural_metrics(post_by_id.get(sid, {}).get("answer_text") or ""),
            "llm_score": score,
        }
        for sid, score in zip(all_step_ids, scores)
    ]


# ---------------------------------------------------------------------------
# Markdown report generation
# ---------------------------------------------------------------------------

_SCORE_BAR = ["▱▱▱▱▱▱▱▱▱▱", "█▱▱▱▱▱▱▱▱▱", "██▱▱▱▱▱▱▱▱", "███▱▱▱▱▱▱▱",
               "████▱▱▱▱▱▱", "█████▱▱▱▱▱", "██████▱▱▱▱", "███████▱▱▱",
               "████████▱▱", "█████████▱", "██████████"]

def _score_bar(n: int) -> str:
    n = max(0, min(10, n))
    return f"{_SCORE_BAR[n]} {n}/10"


def generate_report(
    query: str,
    pre_graph_stats: Dict,
    post_graph_stats: Dict,
    pre_run: Dict,
    post_run: Dict,
    scored_steps: List[Dict],
    run_ts: str,
    mode: str = MODE_FROZEN_POST,
) -> str:
    pre_steps_by_id = {s["step_id"]: s for s in (pre_run["summary"] or {}).get("steps", [])}
    post_steps_by_id = {s["step_id"]: s for s in (post_run["summary"] or {}).get("steps", [])}

    # Aggregate LLM score
    valid_scores = [s["llm_score"]["improvement_score"] for s in scored_steps
                    if isinstance(s["llm_score"].get("improvement_score"), int) and s["llm_score"]["improvement_score"] >= 0]
    avg_score = sum(valid_scores) / len(valid_scores) if valid_scores else 0.0
    post_wins = sum(1 for s in scored_steps if s["llm_score"].get("better_answer") == "post")
    pre_wins = sum(1 for s in scored_steps if s["llm_score"].get("better_answer") == "pre")
    ties = len(scored_steps) - post_wins - pre_wins

    # Aggregate structural delta
    total_pre_words = sum(s["pre_metrics"]["word_count"] for s in scored_steps)
    total_post_words = sum(s["post_metrics"]["word_count"] for s in scored_steps)
    total_pre_hedges = sum(s["pre_metrics"]["uncertainty_hedges"] for s in scored_steps)
    total_post_hedges = sum(s["post_metrics"]["uncertainty_hedges"] for s in scored_steps)
    total_pre_causal = sum(s["pre_metrics"]["causal_claims"] for s in scored_steps)
    total_post_causal = sum(s["post_metrics"]["causal_claims"] for s in scored_steps)

    verdict = "INCONCLUSIVE"
    if avg_score >= 7:
        verdict = "STRONG IMPROVEMENT — graph enrichment materially improved reasoning"
    elif avg_score >= 5:
        verdict = "CLEAR IMPROVEMENT — post-enrichment answers are consistently better"
    elif avg_score >= 3:
        verdict = "MARGINAL IMPROVEMENT — enrichment helps but gap is small"
    elif avg_score >= 1:
        verdict = "MINIMAL IMPROVEMENT — enrichment did not substantially change answers"
    else:
        verdict = "NO IMPROVEMENT — enrichment had no measurable effect on this query"

    pre_elapsed = f"{pre_run['elapsed_s']:.1f}s"
    post_elapsed = f"{post_run['elapsed_s']:.1f}s"

    # Final graph state (from mutation log, more accurate than staging stats)
    pre_final_events = pre_run.get("final_events") or pre_graph_stats["events"]
    pre_final_edges = pre_run.get("final_edges") or pre_graph_stats["edges"]
    post_final_events = post_run.get("final_events") or post_graph_stats["events"]
    post_final_edges = post_run.get("final_edges") or post_graph_stats["edges"]

    if mode == MODE_FROZEN_POST:
        mode_label = "frozen_post — same graph, PRE=no enrichment / POST=enrichment enabled"
        pre_label = "PRE (enrichment disabled)"
        post_label = "POST (enrichment enabled)"
    else:
        mode_label = "staged — two explicit graph files"
        pre_label = "PRE graph (staged)"
        post_label = "POST graph (staged)"

    lines = [
        f"# Answer Delta Report",
        f"",
        f"**Generated:** {run_ts}  ",
        f"**Mode:** `{mode_label}`  ",
        f"**Query:** {query}",
        f"",
        f"---",
        f"",
        f"## Graph State",
        f"",
        f"| Metric | {pre_label} | {post_label} | Delta |",
        f"|--------|{'—'*len(pre_label)}|{'—'*len(post_label)}|-------|",
        f"| Staged events | {pre_graph_stats['events']:,} | {post_graph_stats['events']:,} | {post_graph_stats['events'] - pre_graph_stats['events']:+,} |",
        f"| Staged edges | {pre_graph_stats['edges']:,} | {post_graph_stats['edges']:,} | {post_graph_stats['edges'] - pre_graph_stats['edges']:+,} |",
        f"| Final events (post-run) | {pre_final_events:,} | {post_final_events:,} | {post_final_events - pre_final_events:+,} |",
        f"| Final edges (post-run) | {pre_final_edges:,} | {post_final_edges:,} | {post_final_edges - pre_final_edges:+,} |",
        f"| Events added by enrichment | {pre_run.get('total_events_added', 0)} | {post_run.get('total_events_added', 0)} | — |",
        f"| Edges added by enrichment | {pre_run.get('total_edges_added', 0)} | {post_run.get('total_edges_added', 0)} | — |",
        f"| **Causal annotations added** | **{pre_run.get('total_causal_added', 0)}** | **{post_run.get('total_causal_added', 0)}** | — |",
        f"| **Confounder annotations added** | **{pre_run.get('total_confounders_added', 0)}** | **{post_run.get('total_confounders_added', 0)}** | — |",
        f"| Runtime | {pre_elapsed} | {post_elapsed} | — |",
        f"",
        f"---",
        f"",
        f"## Aggregate Scores",
        f"",
        f"| Metric | Value |",
        f"|--------|-------|",
        f"| Average improvement score | **{avg_score:.1f}/10** |",
        f"| Steps: POST wins | {post_wins}/{len(scored_steps)} |",
        f"| Steps: PRE wins | {pre_wins}/{len(scored_steps)} |",
        f"| Steps: tied | {ties}/{len(scored_steps)} |",
        f"| Total words PRE→POST | {total_pre_words:,} → {total_post_words:,} ({total_post_words - total_pre_words:+,}) |",
        f"| Uncertainty hedges PRE→POST | {total_pre_hedges} → {total_post_hedges} ({total_post_hedges - total_pre_hedges:+,}) |",
        f"| Causal claims PRE→POST | {total_pre_causal} → {total_post_causal} ({total_post_causal - total_pre_causal:+,}) |",
        f"",
        f"### Verdict",
        f"",
        f"> **{verdict}**",
        f"",
        f"---",
        f"",
        f"## Per-Step Analysis",
        f"",
    ]

    for step_data in scored_steps:
        sid = step_data["step_id"]
        kind = step_data["kind"]
        q = step_data["question"]
        llm = step_data["llm_score"]
        score_val = llm.get("improvement_score", -1)
        score_display = _score_bar(score_val) if score_val >= 0 else "N/A"

        pre_answer = (pre_steps_by_id.get(sid) or {}).get("answer_text", "_[no answer]_")
        post_answer = (post_steps_by_id.get(sid) or {}).get("answer_text", "_[no answer]_")

        pre_m = step_data["pre_metrics"]
        post_m = step_data["post_metrics"]

        new_info = "\n".join(f"  - {x}" for x in llm.get("new_information", []))
        gaps_addressed = "\n".join(f"  - {x}" for x in llm.get("gaps_addressed", []))
        still_missing = "\n".join(f"  - {x}" for x in llm.get("still_missing", []))

        lines += [
            f"### {sid} — {kind}",
            f"",
            f"**Question:** {q}",
            f"",
            f"**Improvement score:** {score_display}",
            f"**Better answer:** `{llm.get('better_answer', '?')}`  ",
            f"**Confidence delta:** `{llm.get('confidence_delta', '?')}`  ",
            f"**Specificity delta:** `{llm.get('specificity_delta', '?')}`",
            f"",
            f"**LLM reasoning:** {llm.get('reasoning', '')}",
            f"",
            f"**Structural metrics:**",
            f"",
            f"| Metric | PRE | POST | Δ |",
            f"|--------|-----|------|---|",
            f"| Words | {pre_m['word_count']} | {post_m['word_count']} | {post_m['word_count'] - pre_m['word_count']:+d} |",
            f"| Sentences | {pre_m['sentence_count']} | {post_m['sentence_count']} | {post_m['sentence_count'] - pre_m['sentence_count']:+d} |",
            f"| Uncertainty hedges | {pre_m['uncertainty_hedges']} | {post_m['uncertainty_hedges']} | {post_m['uncertainty_hedges'] - pre_m['uncertainty_hedges']:+d} |",
            f"| Causal claims | {pre_m['causal_claims']} | {post_m['causal_claims']} | {post_m['causal_claims'] - pre_m['causal_claims']:+d} |",
            f"| Temporal refs | {pre_m['temporal_refs']} | {post_m['temporal_refs']} | {post_m['temporal_refs'] - pre_m['temporal_refs']:+d} |",
            f"",
        ]

        if new_info:
            lines += [f"**New information in POST:**", f"", new_info, f""]
        if gaps_addressed:
            lines += [f"**Gaps addressed:**", f"", gaps_addressed, f""]
        if still_missing:
            lines += [f"**Still missing:**", f"", still_missing, f""]

        # Answer side-by-side (truncated for readability)
        pre_trunc = pre_answer[:1500] + ("…" if len(pre_answer) > 1500 else "")
        post_trunc = post_answer[:1500] + ("…" if len(post_answer) > 1500 else "")

        lines += [
            f"<details>",
            f"<summary>PRE answer ({pre_m['word_count']} words)</summary>",
            f"",
            pre_trunc,
            f"",
            f"</details>",
            f"",
            f"<details>",
            f"<summary>POST answer ({post_m['word_count']} words)</summary>",
            f"",
            post_trunc,
            f"",
            f"</details>",
            f"",
            f"---",
            f"",
        ]

    # Graph mutation log
    all_mutations = pre_run.get("mutations", []) + post_run.get("mutations", [])
    if all_mutations:
        lines += [
            f"## Graph Mutations (POST run only)",
            f"",
            f"| Step | Events added | Edges added | Causal | Confounders | Graph total events | Graph total edges |",
            f"|------|-------------|-------------|--------|-------------|--------------------|--------------------|",
        ]
        for m in post_run.get("mutations", []):
            lines.append(
                f"| {m.get('step_id','?')} | +{m.get('events_added',0)} | +{m.get('edges_added',0)} "
                f"| +{m.get('causal_annotations_added',0)} | +{m.get('confounder_annotations_added',0)} "
                f"| {m.get('graph_events_total','?')} | {m.get('graph_edges_total','?')} |"
            )
        lines += [f"", f"---", f""]

    # Final reports
    if pre_run.get("report"):
        lines += [
            f"## Final Detective Report — PRE",
            f"",
            f"<details>",
            f"<summary>Expand PRE report</summary>",
            f"",
            pre_run["report"],
            f"",
            f"</details>",
            f"",
            f"---",
            f"",
        ]

    if post_run.get("report"):
        lines += [
            f"## Final Detective Report — POST",
            f"",
            post_run["report"],
            f"",
            f"---",
            f"",
        ]

    # Raw JSON appendix
    lines += [
        f"## Appendix — Raw Scores JSON",
        f"",
        f"```json",
        json.dumps(scored_steps, indent=2, ensure_ascii=False),
        f"```",
        f"",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _resolve(p: str) -> Path:
    path = Path(p)
    return path.resolve() if path.is_absolute() else (parent_of_server / p).resolve()


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Answer Delta Test Harness",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--mode",
        choices=[MODE_FROZEN_POST, MODE_STAGED],
        default=MODE_FROZEN_POST,
        help=(
            "frozen_post (default): one graph, PRE has enrichment disabled, "
            "POST has enrichment enabled — the correct experimental design. "
            "staged: two explicit graph files — warns if they are identical."
        ),
    )
    # frozen_post inputs
    parser.add_argument("--graph", default=None, help="[frozen_post] Path to vision JSON")
    parser.add_argument("--chart", default=None, help="[frozen_post] Path to chart JSONL (optional)")
    # staged inputs
    parser.add_argument("--pre", default=None, help="[staged] Path to PRE-enrichment vision JSON")
    parser.add_argument("--post", default=None, help="[staged] Path to POST-enrichment vision JSON")
    parser.add_argument("--pre-chart", default=None, help="[staged] Path to PRE chart JSONL (optional)")
    parser.add_argument("--post-chart", default=None, help="[staged] Path to POST chart JSONL (optional)")
    # shared
    parser.add_argument(
        "--query",
        default="What are the most significant unresolved clinical issues and how have treatments evolved over time?",
        help="Detective query to run against both graphs",
    )
    parser.add_argument("--max-steps", type=int, default=6, help="Max detective steps")
    parser.add_argument(
        "--out",
        default=None,
        help="Output markdown path (default: artifacts/answer_delta_<ts>.md)",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Leave temporary Postgres rows after the run",
    )
    parser.add_argument(
        "--skip-scoring",
        action="store_true",
        help="Skip LLM scoring (structural metrics only, faster)",
    )
    args = parser.parse_args()

    mode = args.mode
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # --- Resolve paths by mode ---
    if mode == MODE_FROZEN_POST:
        if not args.graph:
            parser.error("--graph is required for --mode frozen_post")
        graph_path = _resolve(args.graph)
        chart_path = _resolve(args.chart) if args.chart else None
        pre_vision_path = post_vision_path = graph_path
        pre_chart_path = post_chart_path = chart_path
    else:  # staged
        if not args.pre or not args.post:
            parser.error("--pre and --post are required for --mode staged")
        pre_vision_path = _resolve(args.pre)
        post_vision_path = _resolve(args.post)
        pre_chart_path = _resolve(args.pre_chart) if args.pre_chart else None
        post_chart_path = _resolve(args.post_chart) if args.post_chart else None

    out_path = (
        _resolve(args.out) if args.out
        else parent_of_server / "artifacts" / f"answer_delta_{datetime.now().strftime('%Y%m%d_%H%M')}.md"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Derive temp patient IDs
    probe_vision = PatientTimelineVision.load(str(pre_vision_path))
    base_patient_id = probe_vision.patient_id or "PATIENT"
    pre_temp_id = f"{base_patient_id}{DELTA_SUFFIX_PRE}"
    post_temp_id = f"{base_patient_id}{DELTA_SUFFIX_POST}"

    log.info("Answer Delta run starting")
    log.info("  Mode        : %s", mode)
    if mode == MODE_FROZEN_POST:
        log.info("  Graph       : %s", pre_vision_path)
    else:
        log.info("  PRE vision  : %s", pre_vision_path)
        log.info("  POST vision : %s", post_vision_path)
    log.info("  Query       : %s", args.query)
    log.info("  Pre temp ID : %s", pre_temp_id)
    log.info("  Post temp ID: %s", post_temp_id)
    log.info("  Output      : %s", out_path)

    pool = await init_pool(min_size=2, max_size=4)
    openai_client = AsyncOpenAI(timeout=120.0)

    pre_graph_stats: Dict = {}
    post_graph_stats: Dict = {}

    try:
        # --- Stage graphs ---
        log.info("=== STAGING PRE GRAPH ===")
        pre_graph_stats = await stage_graph(pool, pre_vision_path, pre_chart_path, pre_temp_id)

        if mode == MODE_FROZEN_POST:
            # Same graph staged twice under different IDs
            log.info("=== STAGING POST GRAPH (clone of PRE) ===")
            post_graph_stats = await stage_graph(pool, post_vision_path, post_chart_path, post_temp_id)
        else:
            log.info("=== STAGING POST GRAPH ===")
            post_graph_stats = await stage_graph(pool, post_vision_path, post_chart_path, post_temp_id)
            # Warn if they look identical — this is the bug the old harness had
            if (pre_graph_stats["events"] == post_graph_stats["events"] and
                    pre_graph_stats["edges"] == post_graph_stats["edges"]):
                log.warning(
                    "⚠️  PRE and POST graphs have identical event/edge counts "
                    "(%d events, %d edges). You may be comparing the same graph twice. "
                    "Consider using --mode frozen_post instead.",
                    pre_graph_stats["events"], pre_graph_stats["edges"],
                )

        # --- Run detectives ---
        if mode == MODE_FROZEN_POST:
            log.info("=== RUNNING PRE DETECTIVE (enrichment DISABLED) ===")
            _disable_enrichment()
            try:
                pre_run = await run_detective(pool, pre_temp_id, args.query, args.max_steps, label="PRE")
            finally:
                _enable_enrichment()  # always restore even if run fails

            log.info("=== RUNNING POST DETECTIVE (enrichment ENABLED) ===")
            post_run = await run_detective(pool, post_temp_id, args.query, args.max_steps, label="POST")
        else:
            log.info("=== RUNNING PRE DETECTIVE ===")
            pre_run = await run_detective(pool, pre_temp_id, args.query, args.max_steps, label="PRE")

            log.info("=== RUNNING POST DETECTIVE ===")
            post_run = await run_detective(pool, post_temp_id, args.query, args.max_steps, label="POST")

        # --- Validate ---
        pre_steps = (pre_run["summary"] or {}).get("steps", [])
        post_steps = (post_run["summary"] or {}).get("steps", [])
        if not pre_steps or not post_steps:
            log.error("One or both detective runs returned no step summaries. Check server logs.")
            sys.exit(1)

        # --- Score ---
        if args.skip_scoring:
            log.info("Scoring skipped (--skip-scoring)")
            post_by_id = {s["step_id"]: s for s in post_steps}
            scored_steps = [
                {
                    "step_id": s["step_id"],
                    "kind": s.get("kind", "?"),
                    "question": s.get("q", ""),
                    "pre_metrics": structural_metrics(s.get("answer_text", "")),
                    "post_metrics": structural_metrics(
                        post_by_id.get(s["step_id"], {}).get("answer_text", "")
                    ),
                    "pre_word_count": len((s.get("answer_text") or "").split()),
                    "post_word_count": len(
                        (post_by_id.get(s["step_id"], {}).get("answer_text") or "").split()
                    ),
                    "llm_score": {"improvement_score": -1, "better_answer": "unknown", "reasoning": "skipped"},
                }
                for s in pre_steps
            ]
        else:
            log.info("=== SCORING DELTA ===")
            scored_steps = await score_all_steps(openai_client, pre_steps, post_steps)

        # --- Report ---
        log.info("=== GENERATING REPORT ===")
        report_md = generate_report(
            query=args.query,
            pre_graph_stats=pre_graph_stats,
            post_graph_stats=post_graph_stats,
            pre_run=pre_run,
            post_run=post_run,
            scored_steps=scored_steps,
            run_ts=run_ts,
            mode=mode,
        )

        out_path.write_text(report_md, encoding="utf-8")
        log.info("Report written: %s", out_path)
        print(f"\n✅ Answer delta report: {out_path}", file=sys.stderr)

    finally:
        # Always restore enrichment in case of crash mid-PRE run
        _enable_enrichment()

        if not args.no_cleanup:
            log.info("Cleaning up temp patient rows…")
            try:
                await _cleanup_pg(pool, pre_temp_id)
                await _cleanup_pg(pool, post_temp_id)
                log.info("Cleanup done")
            except Exception as e:
                log.warning("Cleanup failed (non-fatal): %s", e)
        else:
            log.info("--no-cleanup set; DELTA rows preserved in Postgres")

        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
