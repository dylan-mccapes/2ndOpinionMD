"""
chat_graph.py — Patient Chat Graph for 2ndOpinionMD

Bounded conversational memory tied to PatientTimelineVision.
Adapted from PortalVision chat_graph.py methodology:
  - Append-only at write time (eviction is explicit and logged)
  - Bounded by max_total_chars per patient
  - Nothing persists without at least one reference edge
  - Every retained message explains WHY it is retained
  - No inference, no summarization, no NLP heuristics in decay

Additional 2OPMD concepts:
  - PTV node anchoring: messages can anchor to specific graph events
  - Role-based authoring: patient, doctor, system, agent
  - Enrichment pull: high-importance messages surface during EoHD
  - Journal integration: journal entries create chat graph nodes
"""

from __future__ import annotations

import math
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


# ── Decay configuration ─────────────────────────────────────────────────────

@dataclass
class ChatDecayConfig:
    log_base: float = math.e
    decay_multiplier: float = 1.0
    min_decay_threshold: float = 0.01

    edge_boost_multipliers: Dict[str, float] = field(default_factory=lambda: {
        "ptv_event": 2.0,       # anchored to a PTV node — very high retention
        "detective_report": 1.8, # referenced in an EoHD report
        "journal_entry": 1.5,   # linked to a journal entry
        "enrichment": 1.5,      # surfaced during enrichment
        "clarification": 1.3,   # patient/doctor clarified something
        "conversation": 1.0,    # general chat
    })

    recent_reference_hours: float = 24.0
    recent_reference_boost: float = 0.2

    # Doctor messages decay slower (clinical observations are high-value)
    doctor_role_boost: float = 0.15


DEFAULT_DECAY_CONFIG = ChatDecayConfig()
DEFAULT_MAX_CHARS = 500_000


# ── Message model ────────────────────────────────────────────────────────────

@dataclass
class ChatMessage:
    message_id: str
    patient_id: str
    role: str                           # patient | doctor | system | agent
    content: str
    created_at: str                     # ISO 8601
    last_referenced: str                # ISO 8601
    decay_score: float = 1.0
    retention_reason: str = "new_message"
    anchored_event_ids: List[str] = field(default_factory=list)
    reference_edges: Dict[str, List[str]] = field(default_factory=dict)
    author_id: Optional[str] = None
    evicted_at: Optional[str] = None
    eviction_reason: Optional[str] = None

    def char_count(self) -> int:
        return len(self.content)

    def has_references(self) -> bool:
        return any(len(v) > 0 for v in self.reference_edges.values())

    def is_anchored(self) -> bool:
        return len(self.anchored_event_ids) > 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "message_id": self.message_id,
            "patient_id": self.patient_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at,
            "last_referenced": self.last_referenced,
            "decay_score": self.decay_score,
            "retention_reason": self.retention_reason,
            "anchored_event_ids": self.anchored_event_ids,
            "reference_edges": self.reference_edges,
            "author_id": self.author_id,
            "evicted_at": self.evicted_at,
            "eviction_reason": self.eviction_reason,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "ChatMessage":
        return cls(
            message_id=d["message_id"],
            patient_id=d["patient_id"],
            role=d["role"],
            content=d["content"],
            created_at=d["created_at"],
            last_referenced=d["last_referenced"],
            decay_score=d.get("decay_score", 1.0),
            retention_reason=d.get("retention_reason", "loaded"),
            anchored_event_ids=d.get("anchored_event_ids", []),
            reference_edges=d.get("reference_edges", {}),
            author_id=d.get("author_id"),
            evicted_at=d.get("evicted_at"),
            eviction_reason=d.get("eviction_reason"),
        )


# ── Core operations ──────────────────────────────────────────────────────────

def create_message(
    patient_id: str,
    role: str,
    content: str,
    reference_edges: Optional[Dict[str, List[str]]] = None,
    anchored_event_ids: Optional[List[str]] = None,
    retention_reason: str = "new_message",
    author_id: Optional[str] = None,
) -> ChatMessage:
    """Create a new chat message (does not persist — caller must save)."""
    now = datetime.now(timezone.utc).isoformat()
    return ChatMessage(
        message_id=str(uuid.uuid4()),
        patient_id=patient_id,
        role=role,
        content=content,
        created_at=now,
        last_referenced=now,
        decay_score=1.0,
        retention_reason=retention_reason,
        anchored_event_ids=anchored_event_ids or [],
        reference_edges=reference_edges or {},
        author_id=author_id,
    )


def compute_decay_score(
    msg: ChatMessage,
    now: datetime,
    config: ChatDecayConfig = DEFAULT_DECAY_CONFIG,
) -> float:
    """Compute current decay score for a message. Pure function."""
    if not msg.has_references() and not msg.is_anchored():
        return 0.0

    last_ref = datetime.fromisoformat(msg.last_referenced.replace("Z", "+00:00"))
    hours = max(0, (now - last_ref).total_seconds() / 3600.0)

    if config.log_base == math.e:
        log_val = math.log(1.0 + hours * config.decay_multiplier)
    else:
        log_val = math.log(1.0 + hours * config.decay_multiplier, config.log_base)

    score = 1.0 / (1.0 + log_val)

    # Edge boost
    for edge_type, targets in msg.reference_edges.items():
        if targets:
            mult = config.edge_boost_multipliers.get(edge_type, 1.0)
            score = min(1.0, score + len(targets) * mult * 0.05)

    # PTV anchor boost (very strong — anchored messages are structurally important)
    if msg.is_anchored():
        score = min(1.0, score + len(msg.anchored_event_ids) * 0.1)

    # Doctor role boost
    if msg.role == "doctor":
        score = min(1.0, score + config.doctor_role_boost)

    # Recent reference boost
    if hours < config.recent_reference_hours:
        score = min(1.0, score + config.recent_reference_boost)

    return round(score, 4)


def update_all_decay_scores(
    messages: List[ChatMessage],
    config: ChatDecayConfig = DEFAULT_DECAY_CONFIG,
) -> None:
    """Update decay scores for all messages in place."""
    now = datetime.now(timezone.utc)
    for msg in messages:
        if msg.evicted_at is None:
            msg.decay_score = compute_decay_score(msg, now, config)


def select_eviction_candidates(
    messages: List[ChatMessage],
    current_chars: int,
    max_chars: int,
) -> List[ChatMessage]:
    """
    Select messages to evict to bring total chars under budget.
    Returns list of messages to evict (lowest decay score first).
    Does NOT modify messages — caller must mark them evicted.
    """
    if current_chars <= max_chars:
        return []

    active = [m for m in messages if m.evicted_at is None]
    active.sort(key=lambda m: m.decay_score)

    to_evict = []
    freed = 0
    overage = current_chars - max_chars

    for msg in active:
        if freed >= overage:
            break
        if msg.decay_score <= 0.0:
            to_evict.append(msg)
            freed += msg.char_count()
            continue
        # Don't evict anchored messages unless truly desperate
        if msg.is_anchored() and freed < overage * 0.8:
            continue
        to_evict.append(msg)
        freed += msg.char_count()

    return to_evict


def evict_message(msg: ChatMessage, reason: str = "budget_enforcement") -> None:
    """Mark a message as evicted."""
    msg.evicted_at = datetime.now(timezone.utc).isoformat()
    msg.eviction_reason = reason
    logger.info(
        "Chat graph eviction: msg=%s patient=%s decay=%.3f reason=%s chars=%d",
        msg.message_id[:8], msg.patient_id, msg.decay_score, reason, msg.char_count(),
    )


def anchor_message_to_event(msg: ChatMessage, event_id: str) -> None:
    """Anchor a message to a PTV event node. Boosts retention."""
    if event_id not in msg.anchored_event_ids:
        msg.anchored_event_ids.append(event_id)
    if "ptv_event" not in msg.reference_edges:
        msg.reference_edges["ptv_event"] = []
    if event_id not in msg.reference_edges["ptv_event"]:
        msg.reference_edges["ptv_event"].append(event_id)
    msg.last_referenced = datetime.now(timezone.utc).isoformat()
    msg.retention_reason = f"anchored_to_ptv:{event_id}"


def touch_message(msg: ChatMessage, reason: str = "referenced") -> None:
    """Update last_referenced timestamp (resets decay clock)."""
    msg.last_referenced = datetime.now(timezone.utc).isoformat()
    if reason:
        msg.retention_reason = reason


# ── Context building for EoHD ────────────────────────────────────────────────

def build_chat_context_for_eohd(
    messages: List[ChatMessage],
    event_ids: Optional[List[str]] = None,
    max_chars: int = 8000,
    min_decay: float = 0.1,
) -> str:
    """
    Build a compact chat context string for EoHD probe/gap/report.

    Prioritizes:
    1. Messages anchored to the queried event_ids
    2. Doctor messages (clinical observations)
    3. Recent high-decay messages
    4. Patient clarifications

    Returns a formatted string ready for LLM context injection.
    """
    active = [m for m in messages if m.evicted_at is None and m.decay_score >= min_decay]

    scored: List[Tuple[float, ChatMessage]] = []
    for msg in active:
        priority = msg.decay_score

        # Boost if anchored to queried events
        if event_ids and any(eid in msg.anchored_event_ids for eid in event_ids):
            priority += 2.0

        # Boost doctor messages
        if msg.role == "doctor":
            priority += 0.5

        # Boost clarifications
        if "clarification" in msg.reference_edges:
            priority += 0.3

        scored.append((priority, msg))

    scored.sort(key=lambda x: x[0], reverse=True)

    parts = []
    total = 0
    for _, msg in scored:
        if total + msg.char_count() > max_chars:
            continue
        role_label = {"patient": "Patient", "doctor": "Doctor", "agent": "2OPMD", "system": "System"}.get(msg.role, msg.role)
        line = f"[{role_label} {msg.created_at[:10]}] {msg.content}"
        if msg.anchored_event_ids:
            line += f" [anchored:{','.join(msg.anchored_event_ids[:3])}]"
        parts.append(line)
        total += msg.char_count()

    if not parts:
        return ""

    return "=== Patient Chat Context ===\n" + "\n".join(parts)


def build_enrichment_candidates(
    messages: List[ChatMessage],
    min_decay: float = 0.3,
) -> List[ChatMessage]:
    """
    Select messages that should surface during opportunistic graph enrichment.
    High-value patient disclosures, doctor observations, and anchored clarifications.
    """
    candidates = []
    for msg in messages:
        if msg.evicted_at is not None:
            continue
        if msg.decay_score < min_decay:
            continue
        # Patient messages with substance (not just "ok" or "thanks")
        if msg.role == "patient" and msg.char_count() > 50:
            candidates.append(msg)
        # Doctor messages always
        elif msg.role == "doctor":
            candidates.append(msg)
        # Anchored agent messages (contain synthesized insights)
        elif msg.role == "agent" and msg.is_anchored():
            candidates.append(msg)
    return candidates
