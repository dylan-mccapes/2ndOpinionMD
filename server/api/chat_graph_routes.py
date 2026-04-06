"""
chat_graph_routes.py — FastAPI routes for Patient Chat Graph

Endpoints:
    POST   /api/chat/send          — Send a message (patient, doctor, or agent)
    GET    /api/chat/history/{pid} — Get active chat history for a patient
    POST   /api/chat/anchor        — Anchor a message to a PTV event node
    POST   /api/chat/touch         — Touch a message (reset decay clock)
    GET    /api/chat/context/{pid} — Get chat context for EoHD (LLM-ready)
    GET    /api/chat/stats/{pid}   — Budget / eviction stats
    POST   /api/chat/stream        — Send + get agent response via SSE
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from server.db.session import get_session
from server.eoh.chat_graph import (
    ChatMessage,
    ChatDecayConfig,
    DEFAULT_DECAY_CONFIG,
    DEFAULT_MAX_CHARS,
    create_message,
    compute_decay_score,
    update_all_decay_scores,
    select_eviction_candidates,
    evict_message,
    anchor_message_to_event,
    touch_message,
    build_chat_context_for_eohd,
    build_enrichment_candidates,
)

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Pydantic models ──────────────────────────────────────────────────────────

class SendMessageRequest(BaseModel):
    patient_id: str
    role: str = Field(..., pattern="^(patient|doctor|system|agent)$")
    content: str = Field(..., min_length=1, max_length=10000)
    reference_edges: Dict[str, List[str]] = Field(default_factory=dict)
    anchored_event_ids: List[str] = Field(default_factory=list)
    retention_reason: str = "new_message"
    author_id: Optional[str] = None

class AnchorRequest(BaseModel):
    message_id: str
    event_id: str

class TouchRequest(BaseModel):
    message_id: str
    reason: str = "referenced"

class ChatHistoryResponse(BaseModel):
    patient_id: str
    messages: List[Dict[str, Any]]
    total_active: int
    total_chars: int
    budget_remaining: int

class ChatStatsResponse(BaseModel):
    patient_id: str
    total_messages: int
    active_messages: int
    evicted_messages: int
    total_chars: int
    max_chars: int
    anchored_count: int
    avg_decay_score: float


# ── DB helpers ───────────────────────────────────────────────────────────────

async def _ensure_budget(session: AsyncSession, patient_id: str) -> Dict[str, Any]:
    """Get or create budget row for patient."""
    row = await session.execute(
        text("SELECT * FROM ehr.chat_graph_budget WHERE patient_id = :pid"),
        {"pid": patient_id},
    )
    budget = row.mappings().first()
    if budget:
        return dict(budget)

    await session.execute(
        text("""
            INSERT INTO ehr.chat_graph_budget (patient_id, max_total_chars)
            VALUES (:pid, :max_chars)
            ON CONFLICT (patient_id) DO NOTHING
        """),
        {"pid": patient_id, "max_chars": DEFAULT_MAX_CHARS},
    )
    return {
        "patient_id": patient_id,
        "max_total_chars": DEFAULT_MAX_CHARS,
        "current_total_chars": 0,
        "total_messages": 0,
        "total_evictions": 0,
    }


async def _load_active_messages(session: AsyncSession, patient_id: str) -> List[ChatMessage]:
    """Load all non-evicted messages for a patient."""
    result = await session.execute(
        text("""
            SELECT message_id, patient_id, role, content, created_at, last_referenced,
                   decay_score, retention_reason, anchored_event_ids, reference_edges,
                   author_id::text, evicted_at, eviction_reason
            FROM ehr.chat_graph
            WHERE patient_id = :pid AND evicted_at IS NULL
            ORDER BY created_at ASC
        """),
        {"pid": patient_id},
    )
    messages = []
    for row in result.mappings():
        messages.append(ChatMessage(
            message_id=str(row["message_id"]),
            patient_id=row["patient_id"],
            role=row["role"],
            content=row["content"],
            created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
            last_referenced=row["last_referenced"].isoformat() if hasattr(row["last_referenced"], "isoformat") else str(row["last_referenced"]),
            decay_score=row["decay_score"],
            retention_reason=row["retention_reason"],
            anchored_event_ids=list(row["anchored_event_ids"] or []),
            reference_edges=dict(row["reference_edges"] or {}),
            author_id=row["author_id"],
            evicted_at=None,
            eviction_reason=None,
        ))
    return messages


async def _persist_message(session: AsyncSession, msg: ChatMessage) -> None:
    """Insert a new message into the chat graph table."""
    await session.execute(
        text("""
            INSERT INTO ehr.chat_graph
                (message_id, patient_id, role, content, created_at, last_referenced,
                 decay_score, retention_reason, anchored_event_ids, reference_edges, author_id)
            VALUES
                (:mid::uuid, :pid, :role, :content, :cat::timestamptz, :lref::timestamptz,
                 :decay, :reason, :anchored::text[], :edges::jsonb, :author::uuid)
        """),
        {
            "mid": msg.message_id,
            "pid": msg.patient_id,
            "role": msg.role,
            "content": msg.content,
            "cat": msg.created_at,
            "lref": msg.last_referenced,
            "decay": msg.decay_score,
            "reason": msg.retention_reason,
            "anchored": msg.anchored_event_ids,
            "edges": json.dumps(msg.reference_edges),
            "author": msg.author_id,
        },
    )


async def _update_message(session: AsyncSession, msg: ChatMessage) -> None:
    """Update an existing message (decay, anchoring, eviction)."""
    await session.execute(
        text("""
            UPDATE ehr.chat_graph SET
                last_referenced = :lref::timestamptz,
                decay_score = :decay,
                retention_reason = :reason,
                anchored_event_ids = :anchored::text[],
                reference_edges = :edges::jsonb,
                evicted_at = :evicted::timestamptz,
                eviction_reason = :eviction_reason
            WHERE message_id = :mid::uuid
        """),
        {
            "mid": msg.message_id,
            "lref": msg.last_referenced,
            "decay": msg.decay_score,
            "reason": msg.retention_reason,
            "anchored": msg.anchored_event_ids,
            "edges": json.dumps(msg.reference_edges),
            "evicted": msg.evicted_at,
            "eviction_reason": msg.eviction_reason,
        },
    )


async def _update_budget(session: AsyncSession, patient_id: str, messages: List[ChatMessage]) -> None:
    """Recompute and update budget row."""
    active = [m for m in messages if m.evicted_at is None]
    total_chars = sum(m.char_count() for m in active)
    evicted = sum(1 for m in messages if m.evicted_at is not None)
    await session.execute(
        text("""
            UPDATE ehr.chat_graph_budget SET
                current_total_chars = :chars,
                total_messages = :total,
                total_evictions = :evicted,
                last_decay_run = NOW(),
                updated_at = NOW()
            WHERE patient_id = :pid
        """),
        {
            "pid": patient_id,
            "chars": total_chars,
            "total": len(active),
            "evicted": evicted,
        },
    )


async def _run_decay_and_eviction(
    session: AsyncSession,
    patient_id: str,
    messages: List[ChatMessage],
    max_chars: int,
) -> int:
    """Run decay update + eviction pass. Returns number evicted."""
    update_all_decay_scores(messages)
    current_chars = sum(m.char_count() for m in messages if m.evicted_at is None)
    to_evict = select_eviction_candidates(messages, current_chars, max_chars)

    for msg in to_evict:
        evict_message(msg)
        await _update_message(session, msg)

    if to_evict:
        await _update_budget(session, patient_id, messages)

    return len(to_evict)


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post("/send")
async def send_message(
    req: SendMessageRequest,
    session: AsyncSession = Depends(get_session),
):
    """Send a chat message and run decay/eviction."""
    budget = await _ensure_budget(session, req.patient_id)
    messages = await _load_active_messages(session, req.patient_id)

    msg = create_message(
        patient_id=req.patient_id,
        role=req.role,
        content=req.content,
        reference_edges=req.reference_edges,
        anchored_event_ids=req.anchored_event_ids,
        retention_reason=req.retention_reason,
        author_id=req.author_id,
    )

    # If no explicit edges, add a default "conversation" edge
    if not msg.has_references() and not msg.is_anchored():
        msg.reference_edges["conversation"] = [msg.message_id]
        msg.retention_reason = "conversation_message"

    await _persist_message(session, msg)
    messages.append(msg)

    evicted = await _run_decay_and_eviction(
        session, req.patient_id, messages, budget["max_total_chars"],
    )
    await _update_budget(session, req.patient_id, messages)
    await session.commit()

    return {
        "message_id": msg.message_id,
        "decay_score": msg.decay_score,
        "evicted_count": evicted,
    }


@router.get("/history/{patient_id}")
async def get_history(
    patient_id: str,
    limit: int = 100,
    min_decay: float = 0.0,
    session: AsyncSession = Depends(get_session),
):
    """Get active chat history for a patient."""
    budget = await _ensure_budget(session, patient_id)
    messages = await _load_active_messages(session, patient_id)
    update_all_decay_scores(messages)

    filtered = [m for m in messages if m.decay_score >= min_decay]
    filtered = filtered[-limit:]

    active_chars = sum(m.char_count() for m in messages)
    return ChatHistoryResponse(
        patient_id=patient_id,
        messages=[m.to_dict() for m in filtered],
        total_active=len(messages),
        total_chars=active_chars,
        budget_remaining=budget["max_total_chars"] - active_chars,
    )


@router.post("/anchor")
async def anchor_to_event(
    req: AnchorRequest,
    session: AsyncSession = Depends(get_session),
):
    """Anchor a message to a PTV event node."""
    result = await session.execute(
        text("""
            SELECT message_id, patient_id, role, content, created_at, last_referenced,
                   decay_score, retention_reason, anchored_event_ids, reference_edges,
                   author_id::text
            FROM ehr.chat_graph WHERE message_id = :mid::uuid AND evicted_at IS NULL
        """),
        {"mid": req.message_id},
    )
    row = result.mappings().first()
    if not row:
        raise HTTPException(404, "Message not found or already evicted")

    msg = ChatMessage(
        message_id=str(row["message_id"]),
        patient_id=row["patient_id"],
        role=row["role"],
        content=row["content"],
        created_at=row["created_at"].isoformat() if hasattr(row["created_at"], "isoformat") else str(row["created_at"]),
        last_referenced=row["last_referenced"].isoformat() if hasattr(row["last_referenced"], "isoformat") else str(row["last_referenced"]),
        decay_score=row["decay_score"],
        retention_reason=row["retention_reason"],
        anchored_event_ids=list(row["anchored_event_ids"] or []),
        reference_edges=dict(row["reference_edges"] or {}),
        author_id=row["author_id"],
    )

    anchor_message_to_event(msg, req.event_id)
    await _update_message(session, msg)
    await session.commit()

    return {"anchored": True, "event_id": req.event_id, "new_decay_score": msg.decay_score}


@router.post("/touch")
async def touch(
    req: TouchRequest,
    session: AsyncSession = Depends(get_session),
):
    """Touch a message to reset its decay clock."""
    await session.execute(
        text("""
            UPDATE ehr.chat_graph SET
                last_referenced = NOW(),
                retention_reason = :reason
            WHERE message_id = :mid::uuid AND evicted_at IS NULL
        """),
        {"mid": req.message_id, "reason": req.reason},
    )
    await session.commit()
    return {"touched": True}


@router.get("/context/{patient_id}")
async def get_eohd_context(
    patient_id: str,
    event_ids: Optional[str] = None,
    max_chars: int = 8000,
    session: AsyncSession = Depends(get_session),
):
    """Get chat context formatted for EoHD LLM injection."""
    messages = await _load_active_messages(session, patient_id)
    update_all_decay_scores(messages)

    eids = event_ids.split(",") if event_ids else None
    context = build_chat_context_for_eohd(messages, event_ids=eids, max_chars=max_chars)

    return {"patient_id": patient_id, "context": context, "message_count": len(messages)}


@router.get("/stats/{patient_id}")
async def get_stats(
    patient_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Get chat graph budget and health stats."""
    budget = await _ensure_budget(session, patient_id)
    messages = await _load_active_messages(session, patient_id)
    update_all_decay_scores(messages)

    anchored = sum(1 for m in messages if m.is_anchored())
    avg_decay = sum(m.decay_score for m in messages) / max(len(messages), 1)

    return ChatStatsResponse(
        patient_id=patient_id,
        total_messages=budget.get("total_messages", len(messages)),
        active_messages=len(messages),
        evicted_messages=budget.get("total_evictions", 0),
        total_chars=sum(m.char_count() for m in messages),
        max_chars=budget["max_total_chars"],
        anchored_count=anchored,
        avg_decay_score=round(avg_decay, 4),
    )
