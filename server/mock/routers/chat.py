import uuid
from datetime import datetime, timezone
from fastapi import APIRouter
from server.mock.fixtures.chat import (
    seed_messages,
    make_message,
    next_agent_reply,
)
from server.mock.config import mock_chat_use_llm
from server.mock.services.graph_chat_demo import graph_answer_for_message

router = APIRouter(prefix="/api/chat", tags=["chat"])

# In-memory per-patient store
_HISTORY: dict[str, list[dict]] = {}
_ANCHORS: list[dict] = []


def _get_history(patient_id: str) -> list[dict]:
    if patient_id not in _HISTORY:
        _HISTORY[patient_id] = seed_messages()
    return _HISTORY[patient_id]


@router.get("/history/{patient_id}")
async def chat_history(patient_id: str, limit: int = 200):
    messages = _get_history(patient_id)[-limit:]
    total_chars = sum(len(m["content"]) for m in messages)
    return {
        "patient_id": patient_id,
        "messages": messages,
        "total_active": len(messages),
        "total_chars": total_chars,
        "budget_remaining": max(0, 32000 - total_chars),
    }


@router.get("/stats/{patient_id}")
async def chat_stats(patient_id: str):
    messages = _get_history(patient_id)
    total_chars = sum(len(m["content"]) for m in messages)
    anchored = [m for m in messages if m.get("anchored_event_ids")]
    return {
        "patient_id": patient_id,
        "total_messages": len(messages),
        "active_messages": len(messages),
        "evicted_messages": 0,
        "total_chars": total_chars,
        "max_chars": 32000,
        "anchored_count": len(anchored),
        "avg_decay_score": round(
            sum(m.get("decay_score", 1.0) for m in messages) / max(len(messages), 1),
            3,
        ),
    }


@router.post("/send")
async def send_message(body: dict = None):
    body = body or {}
    patient_id = body.get("patient_id", "norman-dev-timeline")
    role = body.get("role", "patient")
    content = body.get("content", "")
    anchored_event_ids = body.get("anchored_event_ids", [])
    reference_edges = body.get("reference_edges", {})

    history = _get_history(patient_id)

    # Add user message
    user_msg = make_message(
        patient_id, role, content, anchored_event_ids, reference_edges,
        author_id="user-norman-dev",
    )
    history.append(user_msg)

    # Add agent reply (graph-backed local LLM demo if enabled)
    if mock_chat_use_llm():
        demo = graph_answer_for_message(content)
        agent_reply = str(demo.get("response_text") or "").strip() or next_agent_reply()
        anchored = [x for x in (demo.get("anchor_event_ids") or []) if isinstance(x, str)]
        edge_map = {eid: ["temporal"] for eid in anchored}
    else:
        agent_reply = next_agent_reply()
        anchored = []
        edge_map = {}
    agent_msg = make_message(patient_id, "agent", agent_reply, anchored, edge_map, author_id=None)
    history.append(agent_msg)

    return {
        "message_id": user_msg["message_id"],
        "decay_score": 1.0,
        "evicted_count": 0,
    }


@router.post("/anchor")
async def anchor_message(body: dict = None):
    body = body or {}
    _ANCHORS.append(body)
    message_id = body.get("message_id", "")
    event_id = body.get("event_id", "")

    # Update the message in history if found
    for history in _HISTORY.values():
        for msg in history:
            if msg["message_id"] == message_id:
                if event_id not in msg["anchored_event_ids"]:
                    msg["anchored_event_ids"].append(event_id)
                break

    return {"anchored": True, "message_id": message_id, "event_id": event_id}
