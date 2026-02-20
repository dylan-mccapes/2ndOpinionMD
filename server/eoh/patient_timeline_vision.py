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
from typing import Any, Dict, List, Optional, Set

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
        
        os.makedirs(os.path.dirname(path), exist_ok=True)
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
    from datetime import datetime, timedelta
    
    # Sort events by timestamp
    events_sorted = sorted(
        vision.events.values(),
        key=lambda e: e.timestamp if e.timestamp else ""
    )
    
    for i, event in enumerate(events_sorted):
        if not event.timestamp:
            continue
        
        try:
            ts = datetime.fromisoformat(event.timestamp.replace("Z", "+00:00"))
        except Exception:
            continue
        
        # Look at subsequent events within window
        for j in range(i + 1, len(events_sorted)):
            other = events_sorted[j]
            if not other.timestamp:
                continue
            
            try:
                other_ts = datetime.fromisoformat(other.timestamp.replace("Z", "+00:00"))
            except Exception:
                continue
            
            delta = abs((other_ts - ts).days)
            if delta <= window_days:
                # Temporally coupled
                vision.add_connascence_link(
                    from_event_id=event.event_id,
                    to_event_id=other.event_id,
                    kind=CONNASCENCE_TEMPORAL,
                )
            else:
                # Beyond window; stop checking
                break


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
        
        vision.add_event(
            event_id=event_id,
            event_type=event_type,
            timestamp=timestamp,
            preview=preview,
            discovered_by=discovered_by,
            annotations={"pdf_page": page_num},
        )
    
    # Re-infer temporal connascence after adding new events
    # (This is lightweight; only checks new events against existing)
    _infer_temporal_connascence(vision, window_days=7)


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

