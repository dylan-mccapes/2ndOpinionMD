#!/usr/bin/env python3
"""
patient_timeline_vision.py

Patient timeline provenance tracker (similar to repo_vision.py pattern).

Maintains incremental, provenance-rich view of timeline events:
- Seeded from StructuredProbeSnapshot (event type counts, examples)
- Built incrementally as PDFs are processed
- Tracks connascence between events (temporal, causal, diagnostic)
- Saved to patient_timeline_vision.jsonl for session state

Pattern:
- Similar to repo_vision.py incremental building during run_probe
- TimelineEventVision ~ RepoFileVision
- PatientTimelineVision ~ RepoVision
- Boring, legible, obvious

Session-only mode supported (no persistence when session_only=True).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

from server.utils.parse_date import parse_clinical_date

# Connascence types (coupling between timeline events)
CONNASCENCE_TEMPORAL = "temporal"  # Events close in time
CONNASCENCE_CAUSAL = "causal"  # One event caused/triggered another
CONNASCENCE_DIAGNOSTIC = "diagnostic"  # Events related to same diagnosis/problem
CONNASCENCE_TREATMENT = "treatment"  # Events related to same treatment
CONNASCENCE_LAB_TREND = "lab_trend"  # Labs tracking same metric over time
CONNASCENCE_SYMPTOM_CLUSTER = "symptom_cluster"  # Related symptoms


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class TimelineEventVision:
    """
    Single timeline event with provenance and connascence tracking.
    
    Similar to RepoFileVision but for timeline events instead of files.
    """
    event_id: str  # Unique event identifier (e.g., "dx_001", "lab_2024-01-15_001")
    event_type: str  # diagnosis | lab | note | med | procedure | visit | flare
    timestamp: str  # ISO format timestamp
    preview: str  # Human-readable preview/summary
    
    discovered_by: List[str] = field(default_factory=list)  # snapshot | pdf_page_15 | manual
    status: str = "included"  # included | excluded | uncertain
    
    # Connascence: events this event is coupled to
    connascence: Dict[str, List[str]] = field(default_factory=dict)
    
    # Annotations: flexible metadata
    annotations: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "preview": self.preview,
            "discovered_by": list(self.discovered_by),
            "status": self.status,
            "connascence": {k: list(v) for k, v in self.connascence.items()},
            "annotations": self.annotations or {},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TimelineEventVision":
        data = data if isinstance(data, dict) else {}
        
        # Parse discovered_by
        raw_disc = data.get("discovered_by", [])
        if isinstance(raw_disc, str):
            discovered_by = [raw_disc]
        elif isinstance(raw_disc, list):
            discovered_by = [x for x in raw_disc if isinstance(x, str)]
        else:
            discovered_by = []
        
        # Parse connascence
        connascence_raw = data.get("connascence", {})
        connascence: Dict[str, List[str]] = {}
        if isinstance(connascence_raw, dict):
            for k, v in connascence_raw.items():
                if isinstance(v, list):
                    connascence[k] = [str(x) for x in v if x]
                elif isinstance(v, str):
                    connascence[k] = [v]
        
        return cls(
            event_id=data.get("event_id", ""),
            event_type=data.get("event_type", "unknown"),
            timestamp=data.get("timestamp", ""),
            preview=data.get("preview", ""),
            discovered_by=discovered_by,
            status=data.get("status", "included"),
            connascence=connascence,
            annotations=data.get("annotations") or {},
        )
    
    def add_connascence(self, kind: str, target_event_id: str) -> None:
        """Add connascence link to another event."""
        if kind not in self.connascence:
            self.connascence[kind] = []
        if target_event_id not in self.connascence[kind]:
            self.connascence[kind].append(target_event_id)


@dataclass
class PatientTimelineVision:
    """
    Complete timeline vision for a patient (similar to RepoVision).
    
    Tracks all timeline events with provenance and connascence.
    Can be built incrementally as PDFs are processed.
    """
    patient_id: str
    built_at: str
    session_only: bool = False  # If True, no persistence (in-memory only)
    
    events: Dict[str, TimelineEventVision] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "patient_id": self.patient_id,
            "built_at": self.built_at,
            "session_only": self.session_only,
            "events": {eid: e.to_dict() for eid, e in self.events.items()},
            "metadata": self.metadata or {},
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PatientTimelineVision":
        data = data if isinstance(data, dict) else {}
        events_section = data.get("events", {}) or {}
        events: Dict[str, TimelineEventVision] = {}
        
        for eid, entry in events_section.items():
            events[eid] = TimelineEventVision.from_dict(entry)
        
        return cls(
            patient_id=data.get("patient_id", ""),
            built_at=data.get("built_at", _iso_now()),
            session_only=bool(data.get("session_only", False)),
            events=events,
            metadata=data.get("metadata") or {},
        )
    
    def count_edges(self) -> int:
        """Count total connascence edges across all events."""
        total = 0
        for event in self.events.values():
            for conn_list in event.connascence.values():
                total += len(conn_list)
        return total

    def snapshot(self) -> Dict[str, Any]:
        """The ``git ls-files`` of a patient timeline.

        Produces a lightweight JSON-serializable dict that shows the shape
        of the graph without the content.  An agent reads this first to
        decide what to explore, zoom, traverse, or enrich.
        """
        from collections import Counter, defaultdict

        type_counts: Counter[str] = Counter()
        type_date_ranges: Dict[str, list] = defaultdict(list)
        nodes: list = []

        for e in self.events.values():
            type_counts[e.event_type] += 1
            if e.timestamp and e.timestamp.lower() not in ("unknown", "n/a", ""):
                dt = parse_clinical_date(e.timestamp)
                if dt:
                    type_date_ranges[e.event_type].append(dt)

            edge_summary: Dict[str, int] = {}
            for kind, targets in e.connascence.items():
                if targets:
                    edge_summary[kind] = len(targets)

            nodes.append({
                "id": e.event_id,
                "type": e.event_type,
                "ts": e.timestamp or None,
                "edges": edge_summary or None,
            })

        # Sort nodes chronologically (unknown timestamps last)
        nodes.sort(key=lambda n: n["ts"] or "~")

        # Per-type summary
        type_summary: Dict[str, Any] = {}
        for etype, count in type_counts.most_common():
            entry: Dict[str, Any] = {"count": count}
            dates = sorted(type_date_ranges.get(etype, []))
            if dates:
                entry["first"] = dates[0].strftime("%Y-%m-%d")
                entry["last"] = dates[-1].strftime("%Y-%m-%d")
                entry["parseable"] = len(dates)
                if len(dates) >= 2:
                    gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
                    entry["median_gap_days"] = sorted(gaps)[len(gaps)//2]
                    entry["max_gap_days"] = max(gaps)
            type_summary[etype] = entry

        return {
            "patient_id": self.patient_id,
            "snapshot_at": _iso_now(),
            "total_events": len(self.events),
            "total_edges": self.count_edges(),
            "types": type_summary,
            "nodes": nodes,
        }
    
    def save(self, path: str, force: bool = False) -> None:
        """
        Save timeline vision to JSON file.
        
        Args:
            path: File path to save to
            force: If True, save even if session_only=True (for temp files)
        """
        if self.session_only and not force:
            # Session-only: no persistence (unless forced)
            return
        
        dir_name = os.path.dirname(path)
        if dir_name:
            os.makedirs(dir_name, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load(cls, path: str) -> "PatientTimelineVision":
        """Load timeline vision from JSON file."""
        if not os.path.exists(path):
            return cls(patient_id="", built_at=_iso_now(), events={}, metadata={})
        
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            if not isinstance(data, dict):
                print(f"⚠️ patient_timeline_vision load warning: expected dict, got {type(data)}")
                return cls(patient_id="", built_at=_iso_now(), events={}, metadata={})
            
            return cls.from_dict(data)
        
        except Exception as e:
            print(f"⚠️ patient_timeline_vision load error: {e}")
            return cls(patient_id="", built_at=_iso_now(), events={}, metadata={})
    
    def add_event(
        self,
        event_id: str,
        event_type: str,
        timestamp: str,
        preview: str,
        discovered_by: str,
        annotations: Optional[Dict[str, Any]] = None,
    ) -> TimelineEventVision:
        """Add or update an event in the timeline vision."""
        if event_id in self.events:
            # Event already exists; add discovered_by
            event = self.events[event_id]
            if discovered_by not in event.discovered_by:
                event.discovered_by.append(discovered_by)
            # Merge annotations
            if annotations:
                event.annotations.update(annotations)
        else:
            # New event
            event = TimelineEventVision(
                event_id=event_id,
                event_type=event_type,
                timestamp=timestamp,
                preview=preview,
                discovered_by=[discovered_by],
                annotations=annotations or {},
            )
            self.events[event_id] = event
        
        return event
    
    def add_connascence_link(
        self,
        from_event_id: str,
        to_event_id: str,
        kind: str,
    ) -> None:
        """Add bidirectional connascence link between two events."""
        if from_event_id in self.events:
            self.events[from_event_id].add_connascence(kind, to_event_id)
        
        if to_event_id in self.events:
            self.events[to_event_id].add_connascence(kind, from_event_id)

    def add_edge(
        self,
        *,
        source_event_id: str,
        target_event_id: str,
        connascence_type: str,
        strength: float = 1.0,
        discovered_by: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Gap/synthesis agents: bidirectional link plus optional provenance on source event."""
        self.add_connascence_link(source_event_id, target_event_id, connascence_type)
        if not (discovered_by or metadata):
            return
        prov: Dict[str, Any] = {
            "peer": target_event_id,
            "kind": connascence_type,
            "strength": strength,
            "by": discovered_by,
        }
        if metadata:
            prov.update(metadata)
        if source_event_id in self.events:
            self.events[source_event_id].annotations.setdefault("edge_provenance", []).append(prov)

    def iter_connascence_edges(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Denormalized edges for LLM agents (deduped by sorted pair + kind)."""
        seen: Set[Tuple[str, str, str]] = set()
        out: List[Dict[str, Any]] = []
        for eid, ev in self.events.items():
            for kind, targets in ev.connascence.items():
                for tid in targets:
                    if tid not in self.events:
                        continue
                    a, b = sorted((eid, tid))
                    key = (a, b, kind)
                    if key in seen:
                        continue
                    seen.add(key)
                    out.append(
                        {
                            "source_event_id": eid,
                            "target_event_id": tid,
                            "connascence_type": kind,
                            "strength": 1.0,
                        }
                    )
                    if len(out) >= limit:
                        return out
        return out
    
    def get_events_by_type(self, event_type: str) -> List[TimelineEventVision]:
        """Get all events of a specific type."""
        return [e for e in self.events.values() if e.event_type == event_type]
    
    def get_connascent_events(
        self,
        event_id: str,
        kind: Optional[str] = None,
    ) -> List[TimelineEventVision]:
        """
        Get all events connascent to a given event.
        
        If kind is specified, only return events connascent via that kind.
        Otherwise, return all connascent events across all kinds.
        """
        if event_id not in self.events:
            return []
        
        event = self.events[event_id]
        result_ids: Set[str] = set()
        
        if kind:
            # Specific kind only
            result_ids.update(event.connascence.get(kind, []))
        else:
            # All kinds
            for conn_list in event.connascence.values():
                result_ids.update(conn_list)
        
        return [self.events[eid] for eid in result_ids if eid in self.events]


# ---------------------------------------------------------------------------
# Builder: Seed from StructuredProbeSnapshot
# ---------------------------------------------------------------------------

def seed_from_structured_probe_snapshot(
    patient_id: str,
    snapshot_counts: Dict[str, int],
    dx_examples: List[Dict[str, Any]],
    lab_examples: List[Dict[str, Any]],
    note_examples: List[Dict[str, Any]],
    session_only: bool = False,
) -> PatientTimelineVision:
    """
    Build initial PatientTimelineVision from StructuredProbeSnapshot.
    
    This is the "git ls-files" equivalent for timelines - we bootstrap
    from the structured snapshot (event type counts + examples).
    
    Args:
        patient_id: Patient identifier
        snapshot_counts: Event type counts (e.g., {"diagnosis": 45, "lab": 320})
        dx_examples: List of diagnosis events with {ts, event_type, preview}
        lab_examples: List of lab events
        note_examples: List of note events
        session_only: If True, no persistence (in-memory only)
    
    Returns:
        PatientTimelineVision with initial events seeded
    """
    vision = PatientTimelineVision(
        patient_id=patient_id,
        built_at=_iso_now(),
        session_only=session_only,
        metadata={
            "seed_source": "StructuredProbeSnapshot",
            "event_type_counts": snapshot_counts,
        },
    )
    
    # Add diagnosis examples
    for idx, dx in enumerate(dx_examples):
        event_id = f"dx_{idx:03d}"
        vision.add_event(
            event_id=event_id,
            event_type="diagnosis",
            timestamp=str(dx.get("ts", "")),
            preview=str(dx.get("preview", "")),
            discovered_by="snapshot",
            annotations={"source": "StructuredProbeSnapshot"},
        )
    
    # Add lab examples
    for idx, lab in enumerate(lab_examples):
        event_id = f"lab_{idx:03d}"
        vision.add_event(
            event_id=event_id,
            event_type="lab",
            timestamp=str(lab.get("ts", "")),
            preview=str(lab.get("preview", "")),
            discovered_by="snapshot",
            annotations={"source": "StructuredProbeSnapshot"},
        )
    
    # Add note examples
    for idx, note in enumerate(note_examples):
        event_id = f"note_{idx:03d}"
        vision.add_event(
            event_id=event_id,
            event_type="note",
            timestamp=str(note.get("ts", "")),
            preview=str(note.get("preview", "")),
            discovered_by="snapshot",
            annotations={"source": "StructuredProbeSnapshot"},
        )
    
    # Infer basic temporal connascence (events within 7 days = temporally coupled)
    _infer_temporal_connascence(vision, window_days=7)
    
    return vision


def _infer_temporal_connascence(vision: PatientTimelineVision, window_days: int = 7) -> None:
    """
    Infer temporal connascence: events within window_days are temporally coupled.
    
    This is a simple heuristic to bootstrap connascence tracking.
    """
    import logging
    logger = logging.getLogger("server.eoh.timeline_summarizer")
    
    total_events = len(vision.events)
    no_ts = 0
    parse_fail = 0
    parse_ok = 0
    sample_fails: list[str] = []
    edges_before = vision.count_edges()

    events_sorted = sorted(
        vision.events.values(),
        key=lambda e: e.timestamp if e.timestamp else ""
    )
    
    parseable: list[tuple[TimelineEventVision, datetime]] = []
    for event in events_sorted:
        if not event.timestamp:
            no_ts += 1
            continue
        dt = parse_clinical_date(event.timestamp)
        if dt is None:
            parse_fail += 1
            if len(sample_fails) < 5:
                sample_fails.append(event.timestamp)
            continue
        parse_ok += 1
        parseable.append((event, dt))

    MAX_TEMPORAL_NEIGHBORS = 10
    edges_added = 0
    for i, (event, ts) in enumerate(parseable):
        added = 0
        for j in range(i + 1, len(parseable)):
            if added >= MAX_TEMPORAL_NEIGHBORS:
                break
            other, other_ts = parseable[j]
            delta = abs((other_ts - ts).days)
            if delta <= window_days:
                vision.add_connascence_link(
                    from_event_id=event.event_id,
                    to_event_id=other.event_id,
                    kind=CONNASCENCE_TEMPORAL,
                )
                added += 1
                edges_added += 1
            else:
                break

    edges_after = vision.count_edges()
    logger.info(
        "Temporal connascence pass: %d events total, %d no-timestamp, "
        "%d parse-ok, %d parse-fail%s → +%d links (edges %d→%d)",
        total_events, no_ts, parse_ok, parse_fail,
        f" (samples: {sample_fails})" if sample_fails else "",
        edges_added, edges_before, edges_after,
    )


# ---------------------------------------------------------------------------
# Incremental building during PDF processing
# ---------------------------------------------------------------------------

def add_events_from_pdf_page(
    vision: PatientTimelineVision,
    page_num: int,
    events: List[Dict[str, Any]],
) -> None:
    """
    Add events discovered from a PDF page to the timeline vision.
    
    This is called incrementally as PDF pages are processed (similar to
    repo_vision building during run_probe).
    
    Args:
        vision: Existing PatientTimelineVision
        page_num: PDF page number (for provenance)
        events: List of events extracted from this page
                Each event: {event_type, timestamp, preview, event_id (optional)}
    """
    discovered_by = f"pdf_page_{page_num}"
    
    for idx, event in enumerate(events):
        event_id = event.get("event_id") or f"pdf_p{page_num:04d}_e{idx:03d}"
        event_type = event.get("event_type", "unknown")
        timestamp = event.get("timestamp", "")
        preview = event.get("preview", "")
        
        annotations: Dict[str, Any] = {"pdf_page": page_num}
        drug_name = event.get("drug_name")
        if drug_name and isinstance(drug_name, str) and drug_name.strip():
            annotations["drug_name"] = drug_name.strip()
            annotations["drug_norm_source"] = "llm_extraction"
        drug_dosage = event.get("drug_dosage")
        if drug_dosage and isinstance(drug_dosage, str) and drug_dosage.strip():
            annotations["drug_dosage"] = drug_dosage.strip()
        drug_route = event.get("drug_route")
        if drug_route and isinstance(drug_route, str) and drug_route.strip():
            annotations["drug_route"] = drug_route.strip().lower()
        
        vision.add_event(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            preview=preview,
            discovered_by=discovered_by,
            annotations=annotations,
        )
    
    # Temporal connascence is now inferred once per batch in the caller
    # (timeline_summarizer.py) rather than per-page, avoiding O(n²) rescans.


# ---------------------------------------------------------------------------
# Persistence helpers
# ---------------------------------------------------------------------------

def get_default_vision_path(patient_id: str) -> str:
    """Get default path for patient_timeline_vision.jsonl."""
    # Similar to repo_vision.py pattern
    return f"ai_coder_output/patient_timeline/{patient_id}_timeline_vision.jsonl"


def save_timeline_vision(vision: PatientTimelineVision, path: Optional[str] = None) -> None:
    """Save timeline vision to file (skipped if session_only=True)."""
    if vision.session_only:
        return
    
    if path is None:
        path = get_default_vision_path(vision.patient_id)
    
    vision.save(path)


def load_timeline_vision(patient_id: str, path: Optional[str] = None) -> PatientTimelineVision:
    """Load timeline vision from file."""
    if path is None:
        path = get_default_vision_path(patient_id)
    
    return PatientTimelineVision.load(path)


# ---------------------------------------------------------------------------
# Postgres persistence
# ---------------------------------------------------------------------------

async def load_timeline_vision_pg(pool, patient_id: str) -> Optional[PatientTimelineVision]:
    """Load vision graph from ehr.patient_graph_vision. Returns None if not found."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT graph_json FROM ehr.patient_graph_vision WHERE patient_id = $1",
            patient_id,
        )
    if not row:
        return None
    import json as _json
    data = _json.loads(row["graph_json"]) if isinstance(row["graph_json"], str) else row["graph_json"]
    return PatientTimelineVision.from_dict(data)


async def save_timeline_vision_pg(pool, vision: PatientTimelineVision) -> None:
    """Save vision graph to ehr.patient_graph_vision."""
    if vision.session_only:
        return
    import json as _json
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO ehr.patient_graph_vision (patient_id, graph_json, updated_at)
            VALUES ($1, $2::jsonb, NOW())
            ON CONFLICT (patient_id)
            DO UPDATE SET graph_json = EXCLUDED.graph_json, updated_at = NOW()
            """,
            vision.patient_id,
            _json.dumps(vision.to_dict(), ensure_ascii=False),
        )


async def is_graph_ready_pg(pool, patient_id: str) -> bool:
    """Check readiness gate in ehr.patient_graph_status."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT is_ready FROM ehr.patient_graph_status WHERE patient_id = $1",
            patient_id,
        )
    return bool(row and row["is_ready"])

