"""Seed chat messages and helpers."""
from __future__ import annotations

import copy
import uuid
from datetime import datetime, timezone

_T = "2025-12-10T10:00:00Z"

_SEED: list[dict] = [
    {
        "message_id": "msg-001",
        "patient_id": "norman-dev-timeline",
        "role": "patient",
        "content": "I've been having increased joint pain over the past week, especially in the mornings.",
        "created_at": "2025-12-08T09:00:00Z",
        "last_referenced": "2025-12-08T09:00:00Z",
        "decay_score": 0.95,
        "retention_reason": "recent_high_relevance",
        "anchored_event_ids": [],
        "reference_edges": {},
        "author_id": "user-norman-dev",
    },
    {
        "message_id": "msg-002",
        "patient_id": "norman-dev-timeline",
        "role": "agent",
        "content": (
            "Based on the timeline, this morning stiffness pattern has appeared before — "
            "notably in late 2023 before the rheumatology referral. "
            "The current episode is consistent with Band 3 instability. "
            "I recommend logging daily for 7 days and flagging to your rheumatologist if stiffness exceeds 1 hour."
        ),
        "created_at": "2025-12-08T09:01:00Z",
        "last_referenced": "2025-12-08T09:01:00Z",
        "decay_score": 0.93,
        "retention_reason": "agent_response",
        "anchored_event_ids": ["pdf_p0010_e0000"],
        "reference_edges": {"pdf_p0010_e0000": ["temporal"]},
        "author_id": None,
    },
    {
        "message_id": "msg-003",
        "patient_id": "norman-dev-timeline",
        "role": "patient",
        "content": "Is the A1c trend concerning in the context of my autoimmune history?",
        "created_at": "2025-12-09T14:00:00Z",
        "last_referenced": "2025-12-09T14:00:00Z",
        "decay_score": 0.88,
        "retention_reason": "recent",
        "anchored_event_ids": [],
        "reference_edges": {},
        "author_id": "user-norman-dev",
    },
    {
        "message_id": "msg-004",
        "patient_id": "norman-dev-timeline",
        "role": "agent",
        "content": (
            "Your A1c of 6.2% (2023-12) is borderline elevated. "
            "In the context of chronic autoimmune activity, metabolic dysregulation can potentiate inflammatory load "
            "via the M68 ICM inflow valve. This does not constitute a diabetes diagnosis — that requires confirmed dx lifecycle. "
            "Discuss with your endocrinologist at the next scheduled visit."
        ),
        "created_at": "2025-12-09T14:02:00Z",
        "last_referenced": "2025-12-09T14:02:00Z",
        "decay_score": 0.86,
        "retention_reason": "agent_response",
        "anchored_event_ids": ["pdf_p0010_e0000"],
        "reference_edges": {"pdf_p0010_e0000": ["treatment", "temporal"]},
        "author_id": None,
    },
    {
        "message_id": "msg-005",
        "patient_id": "norman-dev-timeline",
        "role": "patient",
        "content": "Thank you. I'll bring this up at my next appointment.",
        "created_at": "2025-12-09T14:05:00Z",
        "last_referenced": "2025-12-09T14:05:00Z",
        "decay_score": 0.80,
        "retention_reason": "recent",
        "anchored_event_ids": [],
        "reference_edges": {},
        "author_id": "user-norman-dev",
    },
]


def seed_messages() -> list[dict]:
    return copy.deepcopy(_SEED)


def make_message(patient_id: str, role: str, content: str,
                 anchored_event_ids: list, reference_edges: dict,
                 author_id: str | None = None) -> dict:
    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    return {
        "message_id": f"msg-{uuid.uuid4().hex[:8]}",
        "patient_id": patient_id,
        "role": role,
        "content": content,
        "created_at": now,
        "last_referenced": now,
        "decay_score": 1.0,
        "retention_reason": "new",
        "anchored_event_ids": anchored_event_ids or [],
        "reference_edges": reference_edges or {},
        "author_id": author_id,
    }


AGENT_REPLIES = [
    "I've reviewed the timeline context. Based on the EoH framework, this warrants monitoring over the next 7 days.",
    "That pattern appears in the 2023 record as well. The connascence between this event and the prior lab result is significant.",
    "From an M13 trajectory perspective, the trend is upward. I recommend flagging this to your clinician.",
    "The M68 ICM shows reduced allostatic headroom this month. Consider reducing discretionary stressors.",
    "This is consistent with Band 3 instability. No immediate escalation required, but continued logging is essential.",
]

_reply_idx = 0


def next_agent_reply() -> str:
    global _reply_idx
    reply = AGENT_REPLIES[_reply_idx % len(AGENT_REPLIES)]
    _reply_idx += 1
    return reply
