#!/usr/bin/env python3
"""
Demo: the living graph — pre-probe → probe → gap → report → enrich.

Full 5-phase cycle with enrichment write-back and graph analysis tools.

Usage (from 2ndOpinionMD-MVP/server):
    python3 scripts/demo_living_graph.py \
      ../artifacts/timeline_full_20260327_1717/patient_timeline_vision_norman_eric_roberts_20260327_174843.json \
      --query "Why hasn't his MG responded to treatment?"

Phases:
  PRE-PROBE:  Recover timestamps from previews, compute graph shape
  PROBE:      Semantic search (PatientChart) + TS search, merged by RRF
  GAP:        Graph traversal + TS follow-up + python graph analysis tool
  REPORT:     GPT-4.1 structured synthesis with follow-ups + enrichment reqs
  ENRICH:     Apply corrections, re-embed changed nodes, save improved graph
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
from collections import Counter, defaultdict, deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

script_dir = Path(__file__).resolve().parent
server_dir = script_dir.parent
parent_of_server = server_dir.parent
if str(parent_of_server) not in sys.path:
    sys.path.insert(0, str(parent_of_server))
os.chdir(server_dir)

from dotenv import load_dotenv
load_dotenv(server_dir / ".env", override=True)

from server.eoh.patient_timeline_vision import (
    PatientTimelineVision, TimelineEventVision,
)
from server.utils.parse_date import parse_clinical_date, extract_date_from_text

log = logging.getLogger("living_graph")


# ═══════════════════════════════════════════════════════════════════════════
#  PatientChart (from demo_probe_gap_report.py — reused)
# ═══════════════════════════════════════════════════════════════════════════

def _cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    an, bn = np.linalg.norm(a), np.linalg.norm(b)
    return float(np.dot(a, b) / (an * bn)) if an > 0 and bn > 0 else 0.0

def _event_text(e: TimelineEventVision) -> str:
    parts = [e.event_type]
    if e.timestamp and e.timestamp.lower() not in ("unknown", "n/a", ""):
        parts.append(e.timestamp[:10])
    parts.append(e.preview[:200])
    drug = e.annotations.get("drug_name")
    if drug:
        parts.append(f"drug:{drug}")
    return " | ".join(parts)

class PatientChart:
    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        self._points: List[Dict[str, Any]] = []
        self._embs: Optional[np.ndarray] = None
        self._id_idx: Dict[str, int] = {}

    def _get_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def build(self, vision: PatientTimelineVision) -> int:
        model = self._get_model()
        evts = list(vision.events.values())
        if not evts:
            return 0
        texts = [_event_text(e) for e in evts]
        embs = model.encode(texts, show_progress_bar=len(texts) > 200, batch_size=64)
        self._points = [{"event_id": e.event_id, "event_type": e.event_type,
                         "timestamp": e.timestamp, "preview": e.preview} for e in evts]
        self._embs = np.array(embs, dtype=np.float32)
        self._id_idx = {e.event_id: i for i, e in enumerate(evts)}
        return len(self._points)

    def save(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        meta = {"_meta": True, "model": self.model_name,
                "built_at": datetime.now(timezone.utc).isoformat(), "n": len(self._points)}
        with open(path, "w") as f:
            f.write(json.dumps(meta) + "\n")
            for pt, emb in zip(self._points, self._embs):
                row = {**pt, "embedding": emb.tolist()}
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    def load(self, path: Path) -> int:
        self._points, embs = [], []
        with open(path) as f:
            for line in f:
                d = json.loads(line.strip())
                if d.get("_meta"):
                    continue
                emb = d.pop("embedding")
                self._points.append(d)
                embs.append(emb)
        self._embs = np.array(embs, dtype=np.float32) if embs else None
        self._id_idx = {p["event_id"]: i for i, p in enumerate(self._points)}
        return len(self._points)

    def search(self, query: str, top_k: int = 15) -> List[Tuple[Dict, float]]:
        if not self._points:
            return []
        q = self._get_model().encode([query])[0].astype(np.float32)
        scores = [(p, _cosine_sim(q, self._embs[i])) for i, p in enumerate(self._points)]
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def re_embed(self, vision: PatientTimelineVision, event_ids: Set[str]) -> int:
        """Re-embed only the changed nodes. Returns count re-embedded."""
        if not event_ids or self._embs is None:
            return 0
        model = self._get_model()
        count = 0
        for eid in event_ids:
            idx = self._id_idx.get(eid)
            ev = vision.events.get(eid)
            if idx is None or ev is None:
                continue
            text = _event_text(ev)
            emb = model.encode([text])[0].astype(np.float32)
            self._embs[idx] = emb
            self._points[idx] = {"event_id": ev.event_id, "event_type": ev.event_type,
                                 "timestamp": ev.timestamp, "preview": ev.preview}
            count += 1
        return count


# ═══════════════════════════════════════════════════════════════════════════
#  Graph traversal helpers
# ═══════════════════════════════════════════════════════════════════════════

def graph_ts_search(vision: PatientTimelineVision, query: str, limit=20) -> List[str]:
    terms = query.lower().split()
    scored = []
    for e in vision.events.values():
        text = (e.preview + " " + e.event_type).lower()
        hits = sum(1 for t in terms if t in text)
        if hits:
            scored.append((e.event_id, hits))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [eid for eid, _ in scored[:limit]]

def graph_traverse(vision: PatientTimelineVision, from_id: str,
                   edge_types: Optional[List[str]] = None, depth=2) -> List[str]:
    if from_id not in vision.events:
        return []
    visited: Set[str] = set()
    queue: deque[Tuple[str, int]] = deque([(from_id, 0)])
    result = []
    while queue:
        eid, d = queue.popleft()
        if eid in visited:
            continue
        visited.add(eid)
        result.append(eid)
        if d < depth:
            ev = vision.events.get(eid)
            if ev:
                for kind, targets in ev.connascence.items():
                    if edge_types and kind not in edge_types:
                        continue
                    for tid in targets:
                        if tid not in visited:
                            queue.append((tid, d + 1))
    return result

def graph_zoom(vision: PatientTimelineVision, date_start=None, date_end=None,
               event_types=None, limit=100) -> List[str]:
    ds = parse_clinical_date(date_start) if date_start else None
    de = parse_clinical_date(date_end) if date_end else None
    results = []
    for e in vision.events.values():
        if event_types and e.event_type not in event_types:
            continue
        dt = parse_clinical_date(e.timestamp) if e.timestamp else None
        if ds and (dt is None or dt < ds):
            continue
        if de and (dt is None or dt > de):
            continue
        results.append((e.event_id, e.timestamp or "~"))
    results.sort(key=lambda x: x[1])
    return [eid for eid, _ in results[:limit]]


def _rrf(*ranked_lists: List[str], k=60) -> List[str]:
    scores: Dict[str, float] = defaultdict(float)
    for rl in ranked_lists:
        for rank, eid in enumerate(rl):
            scores[eid] += 1.0 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)


# ═══════════════════════════════════════════════════════════════════════════
#  Graph analysis tools (POC — available to gap phase)
# ═══════════════════════════════════════════════════════════════════════════

def tool_event_type_distribution(vision: PatientTimelineVision) -> Dict[str, int]:
    """Count events by type."""
    c = Counter(e.event_type for e in vision.events.values())
    return dict(c.most_common())

def tool_edge_density_by_type(vision: PatientTimelineVision) -> Dict[str, Dict[str, int]]:
    """For each event type, count edges by connascence type."""
    out: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for e in vision.events.values():
        for kind, targets in e.connascence.items():
            out[e.event_type][kind] += len(targets)
    return {k: dict(v) for k, v in out.items()}

def tool_temporal_gaps(vision: PatientTimelineVision, min_gap_days=90) -> List[Dict[str, Any]]:
    """Find temporal gaps > min_gap_days between consecutive events."""
    dated = []
    for e in vision.events.values():
        dt = parse_clinical_date(e.timestamp)
        if dt:
            dated.append((dt, e.event_id, e.event_type))
    dated.sort()
    gaps = []
    for i in range(1, len(dated)):
        delta = (dated[i][0] - dated[i - 1][0]).days
        if delta >= min_gap_days:
            gaps.append({
                "gap_days": delta,
                "before": {"id": dated[i-1][1], "type": dated[i-1][2],
                           "date": dated[i-1][0].strftime("%Y-%m-%d")},
                "after": {"id": dated[i][1], "type": dated[i][2],
                          "date": dated[i][0].strftime("%Y-%m-%d")},
            })
    return sorted(gaps, key=lambda g: g["gap_days"], reverse=True)

def tool_cluster_by_type_and_month(vision: PatientTimelineVision, event_type: str) -> Dict[str, int]:
    """Count events of a given type by month (YYYY-MM)."""
    months: Counter[str] = Counter()
    for e in vision.events.values():
        if e.event_type != event_type:
            continue
        dt = parse_clinical_date(e.timestamp)
        if dt:
            months[dt.strftime("%Y-%m")] += 1
    return dict(sorted(months.items()))

def tool_orphan_nodes(vision: PatientTimelineVision) -> List[Dict[str, str]]:
    """Find nodes with zero connascence edges."""
    orphans = []
    for e in vision.events.values():
        total = sum(len(v) for v in e.connascence.values())
        if total == 0:
            orphans.append({"id": e.event_id, "type": e.event_type,
                            "preview": e.preview[:80]})
    return orphans

GRAPH_TOOLS = {
    "event_type_distribution": tool_event_type_distribution,
    "edge_density_by_type": tool_edge_density_by_type,
    "temporal_gaps": tool_temporal_gaps,
    "cluster_by_type_and_month": tool_cluster_by_type_and_month,
    "orphan_nodes": tool_orphan_nodes,
}


# ═══════════════════════════════════════════════════════════════════════════
#  Phase 0: PRE-PROBE — timestamp recovery + graph shape
# ═══════════════════════════════════════════════════════════════════════════

def run_preprobe(vision: PatientTimelineVision) -> Dict[str, Any]:
    """Recover timestamps from previews. Returns stats."""
    recovered = 0
    for ev in vision.events.values():
        ts = ev.timestamp
        if not ts or ts.lower() in ("unknown", "n/a", "none", ""):
            dt = extract_date_from_text(ev.preview)
            if dt:
                ev.timestamp = dt.strftime("%Y-%m-%d")
                ev.annotations["ts_recovered_from"] = "preview_regex"
                recovered += 1

    total = len(vision.events)
    with_ts = sum(1 for e in vision.events.values()
                  if parse_clinical_date(e.timestamp) is not None)
    return {
        "total_events": total,
        "timestamps_recovered": recovered,
        "timestamp_rate": round(with_ts / total, 3) if total else 0,
        "with_timestamp": with_ts,
        "without_timestamp": total - with_ts,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Phase 1: PROBE — semantic + TS dual retrieval
# ═══════════════════════════════════════════════════════════════════════════

def run_probe(query: str, vision: PatientTimelineVision, chart: PatientChart,
              top_k=20) -> Dict[str, Any]:
    sem = chart.search(query, top_k=top_k)
    sem_ids = [p["event_id"] for p, _ in sem]
    sem_scores = {p["event_id"]: round(s, 4) for p, s in sem}

    ts_ids = graph_ts_search(vision, query, limit=top_k)
    merged = _rrf(sem_ids, ts_ids)[:top_k]

    return {
        "query": query,
        "semantic_ids": sem_ids,
        "semantic_scores": sem_scores,
        "ts_ids": ts_ids,
        "merged_ids": merged,
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Phase 2: GAP — graph traversal + TS follow-up + graph analysis tools
# ═══════════════════════════════════════════════════════════════════════════

def run_gap(probe: Dict, vision: PatientTimelineVision) -> Dict[str, Any]:
    traversal_ids: Set[str] = set()
    for eid in probe["merged_ids"][:5]:
        for nid in graph_traverse(vision, eid,
                                  edge_types=["diagnostic", "treatment", "drug_response", "lab_trend"],
                                  depth=2):
            traversal_ids.add(nid)

    # TS follow-up: extract key terms from top hits and search again
    terms = set()
    for eid in probe["merged_ids"][:5]:
        ev = vision.events.get(eid)
        if ev:
            for word in ev.preview.lower().split()[:10]:
                if len(word) > 4 and word.isalpha():
                    terms.add(word)
    ts_followup_ids = graph_ts_search(vision, " ".join(list(terms)[:8]), limit=30)

    # Zoom into date window of evidence
    timestamps = []
    all_evidence = set(probe["merged_ids"]) | traversal_ids | set(ts_followup_ids)
    for eid in all_evidence:
        ev = vision.events.get(eid)
        if ev:
            dt = parse_clinical_date(ev.timestamp)
            if dt:
                timestamps.append(dt)

    zoom_ids = []
    if timestamps:
        pad = timedelta(days=60)
        zoom_ids = graph_zoom(vision,
                              date_start=(min(timestamps) - pad).isoformat(),
                              date_end=(max(timestamps) + pad).isoformat(),
                              limit=100)

    # Run graph analysis tools
    analysis = {}
    analysis["event_type_distribution"] = tool_event_type_distribution(vision)
    analysis["temporal_gaps_90d"] = tool_temporal_gaps(vision, min_gap_days=90)[:5]
    analysis["orphan_count"] = len(tool_orphan_nodes(vision))

    # Identify enrichment targets
    enrichment_targets = []
    for eid in all_evidence:
        ev = vision.events.get(eid)
        if ev is None:
            continue
        reasons = []
        if not ev.timestamp or ev.timestamp.lower() in ("unknown", "n/a", ""):
            reasons.append("missing_timestamp")
        if ev.event_type == "medication" and not ev.annotations.get("drug_name"):
            reasons.append("no_drug_name")
        if sum(len(v) for v in ev.connascence.values()) == 0:
            reasons.append("zero_edges")
        if reasons:
            enrichment_targets.append({"event_id": eid, "reasons": reasons,
                                       "preview": ev.preview[:100]})

    return {
        "traversal_ids": list(traversal_ids),
        "ts_followup_ids": ts_followup_ids,
        "zoom_ids": zoom_ids,
        "analysis": analysis,
        "enrichment_targets": enrichment_targets,
        "total_evidence_nodes": len(all_evidence),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  Phase 3: REPORT — LLM synthesis
# ═══════════════════════════════════════════════════════════════════════════

async def run_report(query: str, probe: Dict, gap: Dict,
                     vision: PatientTimelineVision) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"answer": "(OPENAI_API_KEY not set — offline mode)", "follow_up_questions": [],
                "enrichment_requests": [], "unresolved_drivers": [], "clinical_arcs": []}

    from openai import AsyncOpenAI
    client = AsyncOpenAI()

    evidence = []
    seen = set()
    for eid in (probe["merged_ids"][:10] + gap["traversal_ids"][:15]):
        ev = vision.events.get(eid)
        if ev and eid not in seen:
            seen.add(eid)
            evidence.append(ev.to_dict())

    system = """You are an EoHD agent analyzing a patient timeline graph.
Return JSON with these fields:
{
  "answer": "Clinical answer (2-4 paragraphs)",
  "unresolved_drivers": [{"driver": "...", "confidence": "high|medium|low", "evidence_ids": ["..."]}],
  "clinical_arcs": [{"arc": "...", "status": "resolved|active|uncertain", "date_range": "..."}],
  "follow_up_questions": ["Questions for the doctor/patient that improve the graph"],
  "enrichment_requests": [{"event_ids": ["..."], "reason": "...", "corrections": {}}]
}
enrichment_requests.corrections can include: timestamp, drug_name, dose, or any annotation fix."""

    user_msg = f"""## Query
{query}

## Evidence ({len(evidence)} nodes from probe + gap traversal)
{json.dumps(evidence[:25], indent=1, ensure_ascii=False)[:8000]}

## Graph Analysis
{json.dumps(gap['analysis'], indent=1)}

## Enrichment Targets ({len(gap['enrichment_targets'])} nodes need attention)
{json.dumps(gap['enrichment_targets'][:10], indent=1)}

## Graph Shape: {len(vision.events)} events, {vision.count_edges()} edges"""

    model = os.getenv("EOH_TIMELINE_SUMMARIZER_MODEL", "gpt-4.1")
    resp = await client.chat.completions.create(
        model=model,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user_msg}],
        temperature=0.3, max_tokens=4096,
        response_format={"type": "json_object"},
    )
    raw = resp.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"answer": raw, "follow_up_questions": [], "enrichment_requests": [],
                "unresolved_drivers": [], "clinical_arcs": []}


# ═══════════════════════════════════════════════════════════════════════════
#  Phase 4: ENRICH — apply corrections, re-embed, save
# ═══════════════════════════════════════════════════════════════════════════

def run_enrich(report: Dict, vision: PatientTimelineVision,
               chart: PatientChart) -> Dict[str, Any]:
    """Apply enrichment requests from the report to the graph."""
    changed_ids: Set[str] = set()
    applied = 0
    skipped = 0

    for req in report.get("enrichment_requests", []):
        corrections = req.get("corrections", {})
        if not corrections:
            skipped += 1
            continue
        for eid in req.get("event_ids", []):
            ev = vision.events.get(eid)
            if ev is None:
                continue
            if "timestamp" in corrections and corrections["timestamp"]:
                dt = parse_clinical_date(corrections["timestamp"])
                if dt:
                    ev.timestamp = dt.strftime("%Y-%m-%d")
                    ev.annotations["ts_corrected_by"] = "report_enrichment"
                    changed_ids.add(eid)
            if "drug_name" in corrections and corrections["drug_name"]:
                ev.annotations["drug_name"] = corrections["drug_name"]
                ev.annotations["drug_norm_source"] = "report_enrichment"
                changed_ids.add(eid)
            for key in ("dose", "route", "frequency"):
                if key in corrections and corrections[key]:
                    ev.annotations[key] = corrections[key]
                    changed_ids.add(eid)
            applied += 1

    re_embedded = 0
    if changed_ids:
        re_embedded = chart.re_embed(vision, changed_ids)

    return {
        "enrichment_requests_total": len(report.get("enrichment_requests", [])),
        "applied": applied,
        "skipped": skipped,
        "nodes_changed": len(changed_ids),
        "nodes_re_embedded": re_embedded,
        "changed_ids": list(changed_ids),
    }


# ═══════════════════════════════════════════════════════════════════════════
#  CLI + orchestrator
# ═══════════════════════════════════════════════════════════════════════════

def _hdr(text: str):
    w = max(len(text) + 4, 60)
    print(f"\n{'=' * w}\n  {text}\n{'=' * w}\n")


async def run_cycle(query: str, vision: PatientTimelineVision, chart: PatientChart):
    t0 = time.perf_counter()

    # Phase 0: PRE-PROBE
    _hdr("PHASE 0: PRE-PROBE (timestamp recovery)")
    preprobe = run_preprobe(vision)
    print(f"  Timestamps recovered from previews: {preprobe['timestamps_recovered']}")
    print(f"  Timestamp rate: {preprobe['timestamp_rate']*100:.1f}% "
          f"({preprobe['with_timestamp']}/{preprobe['total_events']})")

    # Phase 1: PROBE
    _hdr("PHASE 1: PROBE (semantic + TS)")
    probe = run_probe(query, vision, chart)
    print(f"  Query: {query}")
    print(f"  Semantic hits: {len(probe['semantic_ids'])}")
    print(f"  TS hits:       {len(probe['ts_ids'])}")
    print(f"  Merged (RRF):  {len(probe['merged_ids'])}")
    print("\n  Top 5 semantic:")
    for eid in probe["semantic_ids"][:5]:
        ev = vision.events.get(eid)
        score = probe["semantic_scores"].get(eid, 0)
        if ev:
            print(f"    [{score:.3f}] {ev.event_type:12s} | {(ev.timestamp or '?')[:10]:10s} | {ev.preview[:70]}")

    # Phase 2: GAP
    _hdr("PHASE 2: GAP (traversal + TS follow-up + graph analysis)")
    gap = run_gap(probe, vision)
    print(f"  Traversal nodes:    {len(gap['traversal_ids'])}")
    print(f"  TS follow-up:       {len(gap['ts_followup_ids'])}")
    print(f"  Zoom window:        {len(gap['zoom_ids'])}")
    print(f"  Total evidence:     {gap['total_evidence_nodes']}")
    print(f"  Enrichment targets: {len(gap['enrichment_targets'])}")
    print(f"\n  Graph analysis:")
    for tool_name, result in gap["analysis"].items():
        if isinstance(result, dict):
            print(f"    {tool_name}: {json.dumps(result, default=str)[:100]}")
        elif isinstance(result, list):
            print(f"    {tool_name}: {len(result)} items")
        else:
            print(f"    {tool_name}: {result}")

    # Phase 3: REPORT
    _hdr("PHASE 3: REPORT (GPT-4.1 synthesis)")
    report = await run_report(query, probe, gap, vision)
    print(report.get("answer", "(no answer)"))
    if report.get("unresolved_drivers"):
        print("\n  Unresolved Drivers:")
        for d in report["unresolved_drivers"]:
            print(f"    [{d.get('confidence','?')}] {d.get('driver','?')}")
    if report.get("clinical_arcs"):
        print("\n  Clinical Arcs:")
        for a in report["clinical_arcs"]:
            print(f"    [{a.get('status','?')}] {a.get('arc','?')}")
    if report.get("follow_up_questions"):
        print("\n  Follow-up Questions:")
        for i, q in enumerate(report["follow_up_questions"], 1):
            print(f"    {i}. {q}")

    # Phase 4: ENRICH
    _hdr("PHASE 4: ENRICH (write-back + re-embed)")
    enrich = run_enrich(report, vision, chart)
    print(f"  Enrichment requests: {enrich['enrichment_requests_total']}")
    print(f"  Applied:             {enrich['applied']}")
    print(f"  Nodes changed:       {enrich['nodes_changed']}")
    print(f"  Nodes re-embedded:   {enrich['nodes_re_embedded']}")
    if enrich["changed_ids"]:
        print(f"  Changed IDs:         {enrich['changed_ids'][:5]}")

    elapsed = time.perf_counter() - t0
    _hdr(f"CYCLE COMPLETE ({elapsed:.1f}s)")
    print(f"  Graph now: {len(vision.events)} events, {vision.count_edges()} edges")
    ts_rate = sum(1 for e in vision.events.values() if parse_clinical_date(e.timestamp)) / len(vision.events)
    print(f"  Timestamp rate: {ts_rate*100:.1f}%")
    drug_rate = sum(1 for e in vision.events.values()
                    if e.event_type == "medication" and e.annotations.get("drug_name"))
    total_meds = sum(1 for e in vision.events.values() if e.event_type == "medication")
    print(f"  Medication drug_name rate: {drug_rate}/{total_meds}")
    print(f"  The graph grew with attention.")

    return {"preprobe": preprobe, "probe": probe, "gap": gap, "report": report, "enrich": enrich}


def main():
    parser = argparse.ArgumentParser(description="Demo: the living graph")
    parser.add_argument("vision_json", type=Path)
    parser.add_argument("--query", "-q", type=str, default=None)
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--save", action="store_true", help="Save enriched graph back to disk")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(name)s | %(message)s")

    if not args.vision_json.exists():
        print(f"Not found: {args.vision_json}", file=sys.stderr)
        sys.exit(1)

    _hdr("LOADING GRAPH")
    with open(args.vision_json) as f:
        data = json.load(f)
    vision = PatientTimelineVision.from_dict(data)
    print(f"  Patient: {vision.patient_id}")
    print(f"  Events:  {len(vision.events)}")
    print(f"  Edges:   {vision.count_edges()}")

    index_path = args.vision_json.parent / "patient_chart_index_v2.jsonl"
    chart = PatientChart()

    if index_path.exists() and not args.rebuild_index:
        _hdr("LOADING PATIENT CHART INDEX")
        n = chart.load(index_path)
        print(f"  Loaded {n} embedded nodes")
    else:
        _hdr("BUILDING PATIENT CHART INDEX")
        t = time.perf_counter()
        n = chart.build(vision)
        print(f"  Embedded {n} nodes in {time.perf_counter()-t:.1f}s")
        chart.save(index_path)
        print(f"  Saved to {index_path.name}")

    if args.query:
        result = asyncio.run(run_cycle(args.query, vision, chart))
        if args.save:
            out = str(args.vision_json).replace(".json", "_enriched.json")
            vision.save(out, force=True)
            chart.save(index_path)
            print(f"\n  Enriched graph saved: {out}")
            print(f"  Updated index saved:  {index_path}")
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
            asyncio.run(run_cycle(q, vision, chart))

    print("\nDone.")


if __name__ == "__main__":
    main()
