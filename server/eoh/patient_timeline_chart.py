"""
PatientTimelineChart — vector space navigation substrate for PatientTimelineVision.

Embeds graph nodes using sentence-transformers/all-MiniLM-L6-v2 (384 dims).
Provides semantic search: query in natural language, get ranked graph nodes.
NAVIGATION-ONLY: results are suggestions, not decisions.

Supports both file-based (JSONL) and Postgres-backed storage.
"""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np

from server.eoh.patient_timeline_vision import (
    ClinicalArc,
    EDGE_PRIORITY,
    PatientTimelineVision,
    TimelineEventVision,
)

logger = logging.getLogger(__name__)

CHART_EMBEDDING_DIM = 384
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    a_n = np.linalg.norm(a)
    b_n = np.linalg.norm(b)
    if a_n == 0 or b_n == 0:
        return 0.0
    return float(np.dot(a, b) / (a_n * b_n))


def _event_to_embed_text(e: TimelineEventVision) -> str:
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


class PatientTimelineChart:
    """
    In-memory vector index over PatientTimelineVision graph nodes.

    Build from a vision, or load from JSONL file / Postgres.
    Provides semantic search (cosine similarity) and neighbor lookup.
    """

    def __init__(self, model_name: str = DEFAULT_MODEL):
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

    @property
    def point_count(self) -> int:
        return len(self._points)

    # ------------------------------------------------------------------
    # Build from vision
    # ------------------------------------------------------------------

    def build_from_vision(self, vision: PatientTimelineVision) -> int:
        model = self._get_model()
        events = list(vision.events.values())
        if not events:
            return 0

        texts = [_event_to_embed_text(e) for e in events]
        batch_size = 64
        all_embs = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i: i + batch_size]
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

    def re_embed(self, vision: PatientTimelineVision, event_ids: List[str]) -> int:
        """Re-embed specific events after enrichment. Returns count updated."""
        if not event_ids:
            return 0
        model = self._get_model()
        updated = 0
        for eid in event_ids:
            ev = vision.events.get(eid)
            if ev is None:
                continue
            idx = self._id_to_idx.get(eid)
            if idx is None:
                continue
            text = _event_to_embed_text(ev)
            emb = model.encode([text])[0].astype(np.float32)
            self._points[idx].embedding = emb.tolist()
            self._points[idx].preview = ev.preview
            self._points[idx].timestamp = ev.timestamp
            if self._embeddings is not None:
                self._embeddings[idx] = emb
            updated += 1
        return updated

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query: str, top_k: int = 15) -> List[Tuple[PatientChartPoint, float]]:
        if not self._points:
            return []
        model = self._get_model()
        q_emb = model.encode([query])[0].astype(np.float32)
        scores = self._embeddings @ q_emb / (
            np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(q_emb) + 1e-9
        )
        top_idx = np.argsort(-scores)[:top_k]
        return [(self._points[i], float(scores[i])) for i in top_idx]

    def get_near(self, event_id: str, top_k: int = 10) -> List[Tuple[PatientChartPoint, float]]:
        idx = self._id_to_idx.get(event_id)
        if idx is None or self._embeddings is None:
            return []
        ref = self._embeddings[idx]
        scores = self._embeddings @ ref / (
            np.linalg.norm(self._embeddings, axis=1) * np.linalg.norm(ref) + 1e-9
        )
        top_idx = np.argsort(-scores)[:top_k + 1]
        return [
            (self._points[i], float(scores[i]))
            for i in top_idx if i != idx
        ][:top_k]

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    def save_index(self, path: Path) -> None:
        path = Path(path)
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
        path = Path(path)
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
                [p.embedding for p in self._points], dtype=np.float32,
            )
        else:
            self._embeddings = None
        return len(self._points)

    # ------------------------------------------------------------------
    # Postgres I/O
    # ------------------------------------------------------------------

    async def save_to_pg(self, pool, patient_id: str) -> int:
        """Upsert graph + chart embeddings into Postgres. Returns rows written."""
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO ehr.patient_graph_vision (patient_id, graph_json, updated_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (patient_id)
                DO UPDATE SET graph_json = EXCLUDED.graph_json,
                              updated_at = NOW()
                """,
                patient_id,
                json.dumps({
                    "model": self.model_name,
                    "point_count": len(self._points),
                }),
            )

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
                for p in self._points
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
        return len(rows)

    async def load_from_pg(self, pool, patient_id: str) -> int:
        """Load chart embeddings from Postgres. Returns point count."""
        self._points = []
        self._id_to_idx = {}
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT event_id, event_type, ts_text, preview, embedding::text
                FROM ehr.patient_graph_chart
                WHERE patient_id = $1
                ORDER BY event_id
                """,
                patient_id,
            )
        for row in rows:
            emb_str = row["embedding"]
            embedding = json.loads(emb_str.replace("[", "[").replace("]", "]"))
            pt = PatientChartPoint(
                event_id=row["event_id"],
                event_type=row["event_type"],
                timestamp=row["ts_text"] or "",
                preview=row["preview"] or "",
                embedding=embedding,
            )
            self._id_to_idx[pt.event_id] = len(self._points)
            self._points.append(pt)
        if self._points:
            self._embeddings = np.array(
                [p.embedding for p in self._points], dtype=np.float32,
            )
        else:
            self._embeddings = None
        return len(self._points)


# ------------------------------------------------------------------
# Graph retrieval helpers (used by detective stream)
# ------------------------------------------------------------------

def graph_ts_search(
    vision: PatientTimelineVision,
    query: str,
    limit: int = 20,
) -> List[str]:
    """In-memory text search over node previews. Returns event_id list."""
    terms = query.lower().split()
    scored: List[Tuple[str, int]] = []
    for e in vision.events.values():
        text = (e.preview + " " + e.event_type).lower()
        hits = sum(1 for t in terms if t in text)
        if hits > 0:
            scored.append((e.event_id, hits))
    scored.sort(key=lambda x: x[1], reverse=True)
    return [eid for eid, _ in scored[:limit]]


def graph_traverse(
    vision: PatientTimelineVision,
    from_event_id: str,
    edge_types: Optional[List[str]] = None,
    depth: int = 2,
) -> List[str]:
    """BFS neighborhood of a node. Returns event_id list."""
    from collections import deque
    if from_event_id not in vision.events:
        return []
    visited: Set[str] = set()
    queue: deque = deque([(from_event_id, 0)])
    result: List[str] = []
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


def reciprocal_rank_fusion(
    *ranked_lists: List[str],
    k: int = 60,
) -> List[str]:
    """Merge multiple ranked ID lists by RRF."""
    scores: Dict[str, float] = defaultdict(float)
    for rlist in ranked_lists:
        for rank, eid in enumerate(rlist):
            scores[eid] += 1.0 / (k + rank + 1)
    return sorted(scores, key=scores.get, reverse=True)


def build_graph_context(
    vision: PatientTimelineVision,
    chart: PatientTimelineChart,
    step_q: str,
    *,
    sem_k: int = 10,
    ts_k: int = 10,
    traverse_depth: int = 2,
    max_chars: int = 4000,
) -> Tuple[str, List[str]]:
    """
    Per-step graph probe: semantic + TS + traversal → compact context string.
    Returns (context_string, merged_event_ids).
    """
    sem_results = chart.search(step_q, top_k=sem_k)
    sem_ids = [pt.event_id for pt, _ in sem_results]

    ts_ids = graph_ts_search(vision, step_q, limit=ts_k)

    merged = reciprocal_rank_fusion(sem_ids, ts_ids)[:sem_k]

    traversal_ids: Set[str] = set()
    for eid in merged[:3]:
        traversal_ids.update(
            graph_traverse(
                vision, eid,
                edge_types=["diagnostic", "treatment", "drug_response", "lab_trend", "temporal"],
                depth=traverse_depth,
            )
        )

    all_ids = list(dict.fromkeys(merged + list(traversal_ids)))
    lines = []
    for eid in all_ids:
        ev = vision.events.get(eid)
        if ev:
            lines.append(f"{ev.event_type} | {ev.timestamp or '?'} | {ev.preview[:120]}")

    header = f"--- GRAPH EVIDENCE ({len(lines)} nodes) ---"
    body = "\n".join(lines[:30])
    ctx = f"{header}\n{body}"
    if len(ctx) > max_chars:
        ctx = ctx[:max_chars]

    return ctx, merged


def build_graph_context_docs(
    vision: PatientTimelineVision,
    chart: PatientTimelineChart,
    step_q: str,
    *,
    sem_k: int = 15,
    ts_k: int = 15,
    traverse_depth: int = 2,
    max_nodes: int = 25,
) -> List[Dict[str, Any]]:
    """Build individual context docs from graph evidence for first-class injection.

    Returns a list of context dicts compatible with EoH fused context, each
    representing one or more graph events grouped by type.  This replaces
    the single-blob approach so that graph evidence appears as multiple
    individually citable context items.
    """
    sem_results = chart.search(step_q, top_k=sem_k)
    sem_ids = [pt.event_id for pt, _ in sem_results]

    ts_ids = graph_ts_search(vision, step_q, limit=ts_k)
    merged = reciprocal_rank_fusion(sem_ids, ts_ids)[:sem_k]

    traversal_ids: Set[str] = set()
    for eid in merged[:5]:
        traversal_ids.update(
            graph_traverse(
                vision, eid,
                edge_types=["diagnostic", "treatment", "drug_response",
                             "lab_trend", "temporal", "causal", "symptom_cluster"],
                depth=traverse_depth,
            )
        )

    all_ids = list(dict.fromkeys(merged + list(traversal_ids)))[:max_nodes]

    # Group by event_type for structured context docs
    from collections import defaultdict as _dd
    by_type: Dict[str, List] = _dd(list)
    for eid in all_ids:
        ev = vision.events.get(eid)
        if ev:
            by_type[ev.event_type].append(ev)

    _TYPE_LABELS = {
        "diagnosis": "Patient Graph — Diagnoses",
        "medication": "Patient Graph — Medications",
        "lab": "Patient Graph — Lab Results",
        "procedure": "Patient Graph — Procedures",
        "symptom": "Patient Graph — Symptoms",
        "visit": "Patient Graph — Visits",
        "note": "Patient Graph — Clinical Notes",
        "imaging": "Patient Graph — Imaging",
        "vital": "Patient Graph — Vitals",
    }

    docs: List[Dict[str, Any]] = []
    for etype in ["diagnosis", "medication", "lab", "procedure", "symptom",
                   "note", "imaging", "vital", "visit"]:
        events = by_type.get(etype, [])
        if not events:
            continue

        events_sorted = sorted(events, key=lambda e: e.timestamp or "~")
        lines = []
        for ev in events_sorted[:10]:
            ts = ev.timestamp or "unknown"
            drug = ev.annotations.get("drug_name", "")
            extra = f" [{drug}]" if drug else ""
            lines.append(f"  • {ts}: {ev.preview[:150]}{extra}")

        n_edges = sum(
            sum(len(targets) for targets in ev.connascence.values())
            for ev in events
        )

        text = (
            f"Graph {etype} evidence ({len(events)} events, {n_edges} edges):\n"
            + "\n".join(lines)
        )

        docs.append({
            "id": f"graph:{etype}",
            "source": "patient_graph",
            "source_id": f"patient_graph:{etype}",
            "title": _TYPE_LABELS.get(etype, f"Patient Graph — {etype.title()}"),
            "text": text,
            "score": 1.0,
            "method": "graph_probe",
            "meta": {
                "event_type": etype,
                "event_count": len(events),
                "edge_count": n_edges,
                "event_ids": [ev.event_id for ev in events_sorted[:10]],
            },
        })

    return docs


# ------------------------------------------------------------------
# Strategic retrieval helpers (arc-aware, topology-aware)
# ------------------------------------------------------------------

def build_arc_context_docs(
    vision: PatientTimelineVision,
    arc: ClinicalArc,
    *,
    max_events: int = 20,
) -> List[Dict[str, Any]]:
    """Build context docs for a single clinical arc's temporal spine.

    Returns a list of context dicts (same schema as build_graph_context_docs)
    containing the arc's events in chronological order grouped by type.
    Useful when a detective step is investigating a specific arc via DFS.
    """
    spine = vision.dfs_temporal_spine(arc.event_ids)[:max_events]
    if not spine:
        return []

    from collections import defaultdict as _dd
    by_type: Dict[str, List[TimelineEventVision]] = _dd(list)
    for ev in spine:
        by_type[ev.event_type].append(ev)

    docs: List[Dict[str, Any]] = []
    for etype, events in sorted(by_type.items()):
        lines = []
        for ev in events[:10]:
            ts = ev.timestamp or "unknown"
            drug = ev.annotations.get("drug_name", "")
            extra = f" [{drug}]" if drug else ""
            lines.append(f"  \u2022 {ts}: {ev.preview[:150]}{extra}")

        text = (
            f"Arc \"{arc.name}\" \u2014 {etype} events "
            f"({len(events)}/{len(arc.event_ids)} total in arc):\n"
            + "\n".join(lines)
        )

        docs.append({
            "id": f"arc:{arc.arc_id}:{etype}",
            "source": "patient_graph_arc",
            "source_id": f"patient_graph_arc:{arc.arc_id}:{etype}",
            "title": f"Arc: {arc.name} \u2014 {etype.title()}",
            "text": text,
            "score": 1.0,
            "method": "arc_dfs_spine",
            "meta": {
                "arc_id": arc.arc_id,
                "arc_name": arc.name,
                "event_type": etype,
                "event_count": len(events),
                "event_ids": [ev.event_id for ev in events[:10]],
            },
        })

    return docs


def build_cross_arc_context_docs(
    vision: PatientTimelineVision,
    *,
    max_edges: int = 30,
) -> List[Dict[str, Any]]:
    """Build context docs from cross-arc edges.

    Cross-arc edges are where diagnostic mysteries live: treatment in arc A
    producing symptoms attributed to arc B, lab trends that span multiple
    arcs, etc.  Returns a single context doc summarizing the cross-arc
    connections for LLM consumption.
    """
    cross_edges = vision.walk_cross_arc_edges()
    if not cross_edges:
        return []

    lines = []
    for edge in cross_edges[:max_edges]:
        lines.append(
            f"  \u2022 [{edge['source_arc']}] {edge['source_preview'][:80]} "
            f"\u2014({edge['edge_type']})\u2192 "
            f"[{edge['target_arc']}] {edge['target_preview'][:80]}"
        )

    text = (
        f"Cross-arc connections ({len(cross_edges)} edges across arc boundaries):\n"
        + "\n".join(lines)
    )

    return [{
        "id": "graph:cross_arc",
        "source": "patient_graph",
        "source_id": "patient_graph:cross_arc",
        "title": "Patient Graph \u2014 Cross-Arc Connections",
        "text": text,
        "score": 1.0,
        "method": "cross_arc_walk",
        "meta": {
            "edge_count": len(cross_edges),
            "arcs_involved": list({
                e["source_arc"] for e in cross_edges
            } | {e["target_arc"] for e in cross_edges}),
        },
    }]


def build_priority_context_docs(
    vision: PatientTimelineVision,
    seed_event_id: str,
    *,
    max_nodes: int = 25,
) -> List[Dict[str, Any]]:
    """Build context docs via priority-weighted traversal from a seed.

    Follows highest-value edges first (causal > diagnostic > treatment >
    temporal) so the agent gets the most clinically meaningful neighborhood
    rather than just the closest-in-time events.
    """
    traversed_ids = vision.priority_traverse(seed_event_id, max_nodes=max_nodes)
    if not traversed_ids:
        return []

    from collections import defaultdict as _dd
    by_type: Dict[str, List[TimelineEventVision]] = _dd(list)
    for eid in traversed_ids:
        ev = vision.events.get(eid)
        if ev:
            by_type[ev.event_type].append(ev)

    docs: List[Dict[str, Any]] = []
    seed_ev = vision.events.get(seed_event_id)
    seed_label = seed_ev.preview[:60] if seed_ev else seed_event_id

    for etype, events in sorted(by_type.items()):
        events_sorted = sorted(events, key=lambda e: e.timestamp or "~")
        lines = []
        for ev in events_sorted[:10]:
            ts = ev.timestamp or "unknown"
            lines.append(f"  \u2022 {ts}: {ev.preview[:150]}")

        text = (
            f"Priority traversal from \"{seed_label}\" \u2014 {etype} "
            f"({len(events)} events):\n"
            + "\n".join(lines)
        )

        docs.append({
            "id": f"priority:{seed_event_id}:{etype}",
            "source": "patient_graph",
            "source_id": f"patient_graph:priority:{seed_event_id}:{etype}",
            "title": f"Priority Neighborhood \u2014 {etype.title()}",
            "text": text,
            "score": 1.0,
            "method": "priority_traverse",
            "meta": {
                "seed_event_id": seed_event_id,
                "event_type": etype,
                "event_count": len(events),
                "event_ids": [ev.event_id for ev in events_sorted[:10]],
            },
        })

    return docs
