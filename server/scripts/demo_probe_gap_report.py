#!/usr/bin/env python3
"""
Demo: probe → gap → report over a PatientTimelineVision graph.

Includes PatientChart (sentence-transformers embedding index over graph nodes)
and the full probe → gap → report cycle using GPT-4.1 for the report phase.

Usage (from 2ndOpinionMD-MVP/server):
    # Build index + run interactive probe loop:
    python3 scripts/demo_probe_gap_report.py \
      ../artifacts/timeline_full_20260327_1717/patient_timeline_vision_norman_eric_roberts_20260327_174843.json

    # Single query (non-interactive):
    python3 scripts/demo_probe_gap_report.py \
      ../artifacts/timeline_full_20260327_1717/patient_timeline_vision_norman_eric_roberts_20260327_174843.json \
      --query "Why hasn't his MG responded to treatment?"

Requires: sentence-transformers, numpy, openai (for report phase)
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import os
import sys
import time
from collections import defaultdict, deque
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------
script_dir = Path(__file__).resolve().parent
server_dir = script_dir.parent
parent_of_server = server_dir.parent

if str(parent_of_server) not in sys.path:
    sys.path.insert(0, str(parent_of_server))

os.chdir(server_dir)

from dotenv import load_dotenv
load_dotenv(server_dir / ".env", override=True)

from server.eoh.patient_timeline_vision import (
    PatientTimelineVision,
    TimelineEventVision,
)
from server.utils.parse_date import parse_clinical_date

log = logging.getLogger("demo_pgr")


# ═══════════════════════════════════════════════════════════════════════════
#  PatientChart — sentence-transformers embedding index over graph nodes
#  Pattern: identical to portal_vision/graph/repo_chart.py
# ═══════════════════════════════════════════════════════════════════════════

def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_n = np.linalg.norm(a)
    b_n = np.linalg.norm(b)
    if a_n == 0 or b_n == 0:
        return 0.0
    return float(np.dot(a, b) / (a_n * b_n))


def _event_to_embed_text(e: TimelineEventVision) -> str:
    """Build the text that gets embedded for a single graph node."""
    parts = [e.event_type]
    if e.timestamp and e.timestamp.lower() not in ("unknown", "n/a", ""):
        parts.append(e.timestamp)
    parts.append(e.preview)
    drug = e.annotations.get("drug_name")
    if drug:
        parts.append(f"drug:{drug}")
    return " | ".join(parts)


@dataclass
class PatientChartPoint:
    event_id: str
    event_type: str
    timestamp: str
    preview: str
    embedding: List[float]
    is_navigation_only: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "preview": self.preview,
            "embedding": self.embedding,
            "is_navigation_only": self.is_navigation_only,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> PatientChartPoint:
        return cls(
            event_id=d["event_id"],
            event_type=d["event_type"],
            timestamp=d.get("timestamp", ""),
            preview=d.get("preview", ""),
            embedding=d["embedding"],
            is_navigation_only=d.get("is_navigation_only", True),
        )


class PatientChart:
    """
    Vector space navigation substrate for PatientTimelineVision.

    Embeds graph nodes using sentence-transformers/all-MiniLM-L6-v2 (384 dims).
    Provides semantic search: query in natural language, get ranked graph nodes.
    NAVIGATION-ONLY: Results are suggestions, not decisions.
    """

    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ):
        self.model_name = model_name
        self._model = None
        self._points: List[PatientChartPoint] = []
        self._embeddings: Optional[np.ndarray] = None
        self._id_to_idx: Dict[str, int] = {}

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def build_from_vision(self, vision: PatientTimelineVision) -> int:
        """Embed all events from a PatientTimelineVision. Returns point count."""
        model = self._get_model()
        events = list(vision.events.values())
        if not events:
            return 0

        texts = [_event_to_embed_text(e) for e in events]
        batch_size = 64
        all_embs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            emb = model.encode(batch, show_progress_bar=len(texts) > 200)
            all_embs.append(emb)
        embeddings = np.vstack(all_embs)

        self._points = []
        self._id_to_idx = {}
        for idx, (ev, emb) in enumerate(zip(events, embeddings)):
            pt = PatientChartPoint(
                event_id=ev.event_id,
                event_type=ev.event_type,
                timestamp=ev.timestamp,
                preview=ev.preview,
                embedding=emb.tolist(),
            )
            self._points.append(pt)
            self._id_to_idx[ev.event_id] = idx

        self._embeddings = embeddings.astype(np.float32)
        return len(self._points)

    def save_index(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = {
            "_meta": True,
            "model": self.model_name,
            "built_at": datetime.now(timezone.utc).isoformat(),
            "point_count": len(self._points),
        }
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(meta) + "\n")
            for p in self._points:
                f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")

    def load_index(self, path: Path) -> int:
        self._points = []
        self._id_to_idx = {}
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                d = json.loads(line)
                if d.get("_meta"):
                    continue
                pt = PatientChartPoint.from_dict(d)
                self._id_to_idx[pt.event_id] = len(self._points)
                self._points.append(pt)

        if self._points:
            self._embeddings = np.array(
                [p.embedding for p in self._points], dtype=np.float32
            )
        else:
            self._embeddings = None
        return len(self._points)

    def search(self, query: str, top_k: int = 15) -> List[Tuple[PatientChartPoint, float]]:
        """Semantic search. Returns top-k (point, cosine_score) tuples."""
        if not self._points:
            return []
        model = self._get_model()
        q_emb = model.encode([query])[0].astype(np.float32)
        scores = []
        for i, pt in enumerate(self._points):
            sim = _cosine_similarity(q_emb, self._embeddings[i])
            scores.append((pt, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def get_near(self, event_id: str, top_k: int = 10) -> List[Tuple[PatientChartPoint, float]]:
        """Find nodes semantically similar to a given event."""
        idx = self._id_to_idx.get(event_id)
        if idx is None or self._embeddings is None:
            return []
        ref = self._embeddings[idx]
        scores = []
        for i, pt in enumerate(self._points):
            if i == idx:
                continue
            sim = _cosine_similarity(ref, self._embeddings[i])
            scores.append((pt, sim))
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]


# ═══════════════════════════════════════════════════════════════════════════
#  Graph traversal helpers (explore / zoom / traverse / ts-search)
# ═══════════════════════════════════════════════════════════════════════════

def graph_explore(vision: PatientTimelineVision) -> Dict[str, Any]:
    """Explore intent — returns the shape of the graph without node content."""
    return vision.snapshot()


def graph_zoom(
    vision: PatientTimelineVision,
    date_start: Optional[str] = None,
    date_end: Optional[str] = None,
    event_types: Optional[List[str]] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Zoom intent — return events in a date/type window."""
    dt_start = parse_clinical_date(date_start) if date_start else None
    dt_end = parse_clinical_date(date_end) if date_end else None
    results = []
    for e in vision.events.values():
        if event_types and e.event_type not in event_types:
            continue
        dt = parse_clinical_date(e.timestamp) if e.timestamp else None
        if dt_start and (dt is None or dt < dt_start):
            continue
        if dt_end and (dt is None or dt > dt_end):
            continue
        results.append(e.to_dict())
    results.sort(key=lambda x: x.get("timestamp") or "~")
    return results[:limit]


def graph_traverse(
    vision: PatientTimelineVision,
    from_event_id: str,
    edge_types: Optional[List[str]] = None,
    depth: int = 2,
) -> List[Dict[str, Any]]:
    """Traverse intent — BFS neighborhood of a node along specified edge types."""
    if from_event_id not in vision.events:
        return []
    visited: Set[str] = set()
    queue: deque[Tuple[str, int]] = deque([(from_event_id, 0)])
    results = []
    while queue:
        eid, d = queue.popleft()
        if eid in visited:
            continue
        visited.add(eid)
        ev = vision.events.get(eid)
        if ev is None:
            continue
        results.append({**ev.to_dict(), "_depth": d})
        if d < depth:
            for kind, targets in ev.connascence.items():
                if edge_types and kind not in edge_types:
                    continue
                for tid in targets:
                    if tid not in visited:
                        queue.append((tid, d + 1))
    return results


def graph_ts_search(
    vision: PatientTimelineVision,
    query: str,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """Simple in-memory text search over node previews (stand-in for tsvector)."""
    terms = query.lower().split()
    scored: List[Tuple[TimelineEventVision, int]] = []
    for e in vision.events.values():
        text = (e.preview + " " + e.event_type).lower()
        hits = sum(1 for t in terms if t in text)
        if hits > 0:
            scored.append((e, hits))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [e.to_dict() for e, _ in scored[:limit]]


# ═══════════════════════════════════════════════════════════════════════════
#  Probe → Gap → Report
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class ProbeResult:
    query: str
    semantic_hits: List[Dict[str, Any]]
    ts_hits: List[Dict[str, Any]]
    merged_event_ids: List[str]

@dataclass
class GapResult:
    traversal_nodes: List[Dict[str, Any]]
    zoom_nodes: List[Dict[str, Any]]
    enrichment_targets: List[Dict[str, Any]]

@dataclass
class ReportResult:
    answer: str
    unresolved_drivers: List[Dict[str, Any]]
    clinical_arcs: List[Dict[str, Any]]
    follow_up_questions: List[str]
    enrichment_requests: List[Dict[str, Any]]
    graph_mutations_applied: int


def _reciprocal_rank_fusion(
    *ranked_lists: List[str],
    k: int = 60,
) -> List[str]:
    """Merge multiple ranked ID lists by reciprocal rank fusion."""
    scores: Dict[str, float] = defaultdict(float)
    for rlist in ranked_lists:
        for rank, eid in enumerate(rlist):
            scores[eid] += 1.0 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)


def run_probe(
    query: str,
    vision: PatientTimelineVision,
    chart: PatientChart,
    top_k: int = 20,
) -> ProbeResult:
    """
    PROBE phase: dual retrieval.
    1. Semantic search via PatientChart (ANN)
    2. Text search over graph node previews (TS stand-in)
    3. Reciprocal rank fusion to merge
    """
    sem_results = chart.search(query, top_k=top_k)
    sem_hits = [
        {**pt.to_dict(), "_score": round(score, 4)}
        for pt, score in sem_results
    ]
    sem_ids = [pt.event_id for pt, _ in sem_results]

    ts_results = graph_ts_search(vision, query, limit=top_k)
    ts_ids = [r["event_id"] for r in ts_results]

    merged = _reciprocal_rank_fusion(sem_ids, ts_ids)[:top_k]

    return ProbeResult(
        query=query,
        semantic_hits=sem_hits,
        ts_hits=ts_results,
        merged_event_ids=merged,
    )


def run_gap(
    probe: ProbeResult,
    vision: PatientTimelineVision,
) -> GapResult:
    """
    GAP phase: follow-up graph traversal from probe hits.
    - Traverse from top probe hits along diagnostic + treatment edges
    - Zoom into the date window of the probe hits
    - Identify enrichment targets (nodes with missing timestamps or sparse data)
    """
    traversal_nodes: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()

    for eid in probe.merged_event_ids[:5]:
        neighbors = graph_traverse(
            vision, eid,
            edge_types=["diagnostic", "treatment", "drug_response", "lab_trend"],
            depth=2,
        )
        for n in neighbors:
            nid = n["event_id"]
            if nid not in seen_ids:
                seen_ids.add(nid)
                traversal_nodes.append(n)

    timestamps = []
    for eid in probe.merged_event_ids:
        ev = vision.events.get(eid)
        if ev and ev.timestamp:
            dt = parse_clinical_date(ev.timestamp)
            if dt:
                timestamps.append(dt)

    zoom_nodes: List[Dict[str, Any]] = []
    if timestamps:
        earliest = min(timestamps)
        latest = max(timestamps)
        from datetime import timedelta
        pad = timedelta(days=90)
        zoom_nodes = graph_zoom(
            vision,
            date_start=(earliest - pad).isoformat(),
            date_end=(latest + pad).isoformat(),
            limit=100,
        )

    enrichment_targets = []
    all_ids = set(probe.merged_event_ids) | seen_ids
    for eid in all_ids:
        ev = vision.events.get(eid)
        if ev is None:
            continue
        reasons = []
        if not ev.timestamp or ev.timestamp.lower() in ("unknown", "n/a", ""):
            reasons.append("missing_timestamp")
        if ev.event_type == "medication" and not ev.annotations.get("drug_name"):
            reasons.append("medication_no_drug_name")
        total_edges = sum(len(v) for v in ev.connascence.values())
        if total_edges == 0:
            reasons.append("zero_edges")
        if reasons:
            enrichment_targets.append({
                "event_id": eid,
                "reasons": reasons,
                "preview": ev.preview[:120],
            })

    return GapResult(
        traversal_nodes=traversal_nodes,
        zoom_nodes=zoom_nodes,
        enrichment_targets=enrichment_targets,
    )


async def run_report(
    query: str,
    probe: ProbeResult,
    gap: GapResult,
    vision: PatientTimelineVision,
) -> ReportResult:
    """
    REPORT phase: LLM synthesizes answer from probe + gap evidence.
    Returns structured output with follow-up questions and enrichment requests.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return _run_report_offline(query, probe, gap, vision)

    from openai import AsyncOpenAI
    client = AsyncOpenAI()

    evidence_nodes = []
    seen = set()
    for eid in probe.merged_event_ids[:15]:
        ev = vision.events.get(eid)
        if ev and eid not in seen:
            seen.add(eid)
            evidence_nodes.append(ev.to_dict())
    for n in gap.traversal_nodes[:20]:
        nid = n["event_id"]
        if nid not in seen:
            seen.add(nid)
            evidence_nodes.append(n)

    evidence_json = json.dumps(evidence_nodes[:30], indent=1, ensure_ascii=False)
    enrichment_json = json.dumps(gap.enrichment_targets[:10], indent=1, ensure_ascii=False)

    system_prompt = """You are an EoHD (Eye of Health Detective) agent analyzing a patient timeline graph.
You receive a doctor's query, a set of evidence nodes from the graph (probe + gap traversal), and a list of enrichment targets (nodes with missing data).

Return a JSON object with exactly these fields:
{
  "answer": "Direct answer to the query (2-4 paragraphs, clinical prose)",
  "unresolved_drivers": [{"driver": "...", "confidence": "high|medium|low", "evidence_ids": ["..."]}],
  "clinical_arcs": [{"arc": "...", "status": "resolved|active|uncertain", "date_range": "...", "key_event_ids": ["..."]}],
  "follow_up_questions": ["Questions that would help improve the graph and refine the answer"],
  "enrichment_requests": [{"event_ids": ["..."], "reason": "..."}]
}

The follow_up_questions should be things the DOCTOR or PATIENT could answer that would improve the graph.
The enrichment_requests should be nodes that need re-extraction or correction."""

    user_msg = f"""## Query
{query}

## Evidence Nodes (from probe + gap traversal)
{evidence_json}

## Enrichment Targets (nodes with missing data)
{enrichment_json}

## Graph Shape
- Total events: {len(vision.events)}
- Total edges: {vision.count_edges()}
- Probe hits: {len(probe.merged_event_ids)} (semantic + TS merged)
- Gap traversal: {len(gap.traversal_nodes)} nodes reached
- Gap zoom window: {len(gap.zoom_nodes)} nodes in date range
- Enrichment targets: {len(gap.enrichment_targets)} nodes need attention"""

    model = os.getenv("EOH_TIMELINE_SUMMARIZER_MODEL", "gpt-4.1")
    log.info("Calling %s for report synthesis...", model)

    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        temperature=0.3,
        max_tokens=4096,
        response_format={"type": "json_object"},
    )

    raw = resp.choices[0].message.content or "{}"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"answer": raw, "unresolved_drivers": [], "clinical_arcs": [],
                "follow_up_questions": [], "enrichment_requests": []}

    return ReportResult(
        answer=data.get("answer", ""),
        unresolved_drivers=data.get("unresolved_drivers", []),
        clinical_arcs=data.get("clinical_arcs", []),
        follow_up_questions=data.get("follow_up_questions", []),
        enrichment_requests=data.get("enrichment_requests", []),
        graph_mutations_applied=0,
    )


def _run_report_offline(
    query: str,
    probe: ProbeResult,
    gap: GapResult,
    vision: PatientTimelineVision,
) -> ReportResult:
    """Offline report when no OPENAI_API_KEY — summarizes probe/gap mechanically."""
    top_types = defaultdict(int)
    for eid in probe.merged_event_ids[:15]:
        ev = vision.events.get(eid)
        if ev:
            top_types[ev.event_type] += 1

    answer_lines = [
        f"Query: {query}",
        f"Probe returned {len(probe.merged_event_ids)} merged hits "
        f"({len(probe.semantic_hits)} semantic, {len(probe.ts_hits)} TS).",
        f"Gap traversal reached {len(gap.traversal_nodes)} nodes; "
        f"zoom window contains {len(gap.zoom_nodes)} nodes.",
        f"Top event types in evidence: {dict(top_types)}",
        f"Enrichment targets: {len(gap.enrichment_targets)} nodes need attention.",
        "",
        "(Full report requires OPENAI_API_KEY for LLM synthesis.)",
    ]

    return ReportResult(
        answer="\n".join(answer_lines),
        unresolved_drivers=[],
        clinical_arcs=[],
        follow_up_questions=[
            "Set OPENAI_API_KEY to enable LLM-powered report synthesis.",
        ],
        enrichment_requests=[
            {"event_ids": [t["event_id"] for t in gap.enrichment_targets[:5]],
             "reason": "missing timestamps or medication detail"}
        ],
        graph_mutations_applied=0,
    )


# ═══════════════════════════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════════════════════════

def _print_header(text: str) -> None:
    w = max(len(text) + 4, 60)
    print(f"\n{'=' * w}")
    print(f"  {text}")
    print(f"{'=' * w}\n")


def _print_probe(probe: ProbeResult) -> None:
    _print_header("PROBE")
    print(f"  Query: {probe.query}")
    print(f"  Semantic hits: {len(probe.semantic_hits)}")
    print(f"  TS hits:       {len(probe.ts_hits)}")
    print(f"  Merged (RRF):  {len(probe.merged_event_ids)}")
    print()
    print("  Top 5 semantic:")
    for h in probe.semantic_hits[:5]:
        score = h.get("_score", 0)
        print(f"    [{score:.3f}] {h['event_type']:12s} | {h['timestamp'][:10] if h.get('timestamp') else '?':10s} | {h['preview'][:80]}")
    print()
    print("  Top 5 TS:")
    for h in probe.ts_hits[:5]:
        print(f"    {h['event_type']:12s} | {h.get('timestamp', '?')[:10]:10s} | {h['preview'][:80]}")


def _print_gap(gap: GapResult) -> None:
    _print_header("GAP")
    print(f"  Traversal nodes:    {len(gap.traversal_nodes)}")
    print(f"  Zoom window nodes:  {len(gap.zoom_nodes)}")
    print(f"  Enrichment targets: {len(gap.enrichment_targets)}")
    if gap.enrichment_targets:
        print()
        print("  Nodes needing attention:")
        for t in gap.enrichment_targets[:8]:
            print(f"    {t['event_id']:24s} | {', '.join(t['reasons']):30s} | {t['preview'][:60]}")


def _print_report(report: ReportResult) -> None:
    _print_header("REPORT")
    print(report.answer)

    if report.unresolved_drivers:
        print("\n  Unresolved Drivers:")
        for d in report.unresolved_drivers:
            print(f"    [{d.get('confidence', '?')}] {d.get('driver', '?')}")

    if report.clinical_arcs:
        print("\n  Clinical Arcs:")
        for a in report.clinical_arcs:
            print(f"    [{a.get('status', '?')}] {a.get('arc', '?')} ({a.get('date_range', '?')})")

    if report.follow_up_questions:
        print("\n  Follow-up Questions (feed back into next probe):")
        for i, q in enumerate(report.follow_up_questions, 1):
            print(f"    {i}. {q}")

    if report.enrichment_requests:
        print("\n  Enrichment Requests (improve the graph):")
        for r in report.enrichment_requests:
            ids = r.get("event_ids", [])
            print(f"    {ids[:3]} — {r.get('reason', '?')}")


async def _run_single_query(
    query: str,
    vision: PatientTimelineVision,
    chart: PatientChart,
) -> ReportResult:
    t0 = time.perf_counter()

    print(f"\nQuery: {query}")
    probe = run_probe(query, vision, chart)
    _print_probe(probe)

    gap = run_gap(probe, vision)
    _print_gap(gap)

    report = await run_report(query, probe, gap, vision)
    _print_report(report)

    elapsed = time.perf_counter() - t0
    print(f"\n  Total cycle time: {elapsed:.1f}s")
    return report


def main():
    parser = argparse.ArgumentParser(description="Demo: probe -> gap -> report")
    parser.add_argument("vision_json", type=Path, help="Path to PatientTimelineVision JSON")
    parser.add_argument("--query", "-q", type=str, default=None, help="Single query (skip interactive)")
    parser.add_argument("--rebuild-index", action="store_true", help="Force re-embed even if index exists")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s")

    if not args.vision_json.exists():
        print(f"Vision JSON not found: {args.vision_json}", file=sys.stderr)
        sys.exit(1)

    # Load graph
    _print_header("LOADING GRAPH")
    with open(args.vision_json) as f:
        data = json.load(f)
    vision = PatientTimelineVision.from_dict(data)
    print(f"  Patient:  {vision.patient_id}")
    print(f"  Events:   {len(vision.events)}")
    print(f"  Edges:    {vision.count_edges()}")

    # Build or load PatientChart index
    index_path = args.vision_json.parent / "patient_chart_index.jsonl"
    chart = PatientChart()

    if index_path.exists() and not args.rebuild_index:
        _print_header("LOADING PATIENT CHART INDEX")
        n = chart.load_index(index_path)
        print(f"  Loaded {n} embedded nodes from {index_path.name}")
    else:
        _print_header("BUILDING PATIENT CHART INDEX (sentence-transformers)")
        t0 = time.perf_counter()
        n = chart.build_from_vision(vision)
        elapsed = time.perf_counter() - t0
        print(f"  Embedded {n} nodes in {elapsed:.1f}s")
        chart.save_index(index_path)
        print(f"  Saved to {index_path.name}")

    # Explore — show the shape
    snap = graph_explore(vision)
    _print_header("GRAPH SHAPE (explore)")
    for etype, info in snap.get("types", {}).items():
        date_range = ""
        if "first" in info:
            date_range = f" ({info['first']} → {info['last']})"
        print(f"  {etype:16s}: {info['count']:5d} events{date_range}")

    # Run query
    if args.query:
        asyncio.run(_run_single_query(args.query, vision, chart))
    else:
        print("\n  Interactive mode. Type a question, or 'quit' to exit.\n")
        while True:
            try:
                q = input("  query> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not q or q.lower() in ("quit", "exit", "q"):
                break
            asyncio.run(_run_single_query(q, vision, chart))

    print("\nDone.")


if __name__ == "__main__":
    main()
