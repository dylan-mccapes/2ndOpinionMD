"""Graph-backed mock chat response: reduce -> semantic seed -> BFS -> answer."""
from __future__ import annotations

import json
from functools import lru_cache
from typing import Any, Dict, List

from server.eoh.patient_timeline_vision import PatientTimelineVision
from server.graph_traversal.agent_tools import execute_graph_tool
from server.graph_traversal.ollama_local import ollama_chat, ollama_reply_text
from server.mock.config import mock_graph_ptv_json, mock_ollama_model, mock_ollama_url

_SYSTEM = """You are a concise EoH assistant for UX sandbox mode.
Use the provided graph traversal context only.
Return 3-6 sentences with:
1) what evidence was found,
2) what it likely means clinically,
3) one practical next step,
4) explicit uncertainty if evidence is weak.
Do not fabricate event IDs."""


@lru_cache(maxsize=1)
def _vision() -> PatientTimelineVision:
    return PatientTimelineVision.load(str(mock_graph_ptv_json()))


def _node_blurbs(vision: PatientTimelineVision, event_ids: List[str], max_n: int = 6) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for eid in event_ids[:max_n]:
        ev = vision.events.get(eid)
        if ev is None:
            continue
        out.append(
            {
                "event_id": ev.event_id,
                "event_type": ev.event_type,
                "timestamp": ev.timestamp,
                "preview": (ev.preview or "")[:260],
                "edge_count": sum(len(v) for v in ev.connascence.values()),
            }
        )
    return out


def graph_answer_for_message(query: str) -> Dict[str, Any]:
    """
    Execute a simple demo strategy:
      reduce -> hybrid_search(semantic) -> bfs_expand
    then ask local Ollama model for a concise response.
    """
    query = (query or "").strip()
    if not query:
        return {"response_text": "Please provide a question or observation to analyze.", "anchor_event_ids": []}

    vision = _vision()
    reduced = execute_graph_tool(
        "graph_reduce",
        vision,
        {"drop_page": True, "drop_unknown_timestamp": False, "drop_isolates": True},
    )
    reduced_ids = [x for x in (reduced.get("event_ids") or []) if isinstance(x, str)]

    seeds_result = execute_graph_tool(
        "graph_hybrid_search",
        vision,
        {
            "query": query,
            "top_k": 12,
            "semantic": True,
            "event_ids": reduced_ids,
        },
    )
    seed_ids = [x for x in (seeds_result.get("event_ids") or []) if isinstance(x, str)]
    bfs_result = execute_graph_tool(
        "graph_bfs_expand",
        vision,
        {
            "seed_event_ids": seed_ids[:6],
            "max_depth": 2,
            "restrict_to_event_ids": reduced_ids,
        },
    )
    bfs_ids = [x for x in (bfs_result.get("event_ids") or []) if isinstance(x, str)]
    anchor_ids = bfs_ids[:3] or seed_ids[:3]

    prompt_payload = {
        "query": query,
        "pipeline": {
            "reduce_kept": len(reduced_ids),
            "seed_count": len(seed_ids),
            "bfs_count": len(bfs_ids),
            "keyword_hits": seeds_result.get("keyword_hits"),
            "semantic_hits": seeds_result.get("semantic_hits"),
        },
        "top_seed_nodes": _node_blurbs(vision, seed_ids, max_n=6),
        "top_bfs_nodes": _node_blurbs(vision, bfs_ids, max_n=8),
    }
    user_msg = json.dumps(prompt_payload, ensure_ascii=False, indent=2)

    try:
        resp = ollama_chat(
            mock_ollama_url(),
            mock_ollama_model(),
            user_msg,
            system=_SYSTEM,
            temperature=0.2,
            timeout_s=240,
        )
        text = ollama_reply_text(resp)
    except Exception as exc:
        text = (
            f"Graph demo path ran but the local LLM call failed ({exc!s}). "
            f"Reduced {len(reduced_ids)} events, found {len(seed_ids)} seeds, "
            f"expanded to {len(bfs_ids)} nodes."
        )

    return {
        "response_text": text,
        "anchor_event_ids": anchor_ids,
        "pipeline": {
            "reduce_kept": len(reduced_ids),
            "seed_count": len(seed_ids),
            "bfs_count": len(bfs_ids),
            "model": mock_ollama_model(),
        },
    }
