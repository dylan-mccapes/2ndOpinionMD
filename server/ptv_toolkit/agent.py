"""
agent.py — strict JSON tool-calling loop over Ollama chat API.

Usage
-----

    gh = load_graph("artifacts/.../PTV_REAL_EHR_20260423.json")
    log = run_agent(
        gh,
        question="List every hydrocodone administration in chronological order.",
        model="eoh-llama-lucifer",
    )

    for turn in log["turns"]:
        print(turn["role"], turn.get("tool"), turn.get("args"))
    print("ANSWER:", log["final_answer"])
"""
from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import requests

from .graph import GraphHandle
from .registry import TOOL_SCHEMAS, call_tool, render_tool_catalog, tool_names

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "eoh-llama-lucifer"
MAX_TOOL_TURNS = 6
MAX_TOOL_RESULT_CHARS = 6000

_BLOCK_RX = re.compile(r"\{.*\}", re.DOTALL)


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT_PREFIX = """You are the PTV probe agent (8B, RTX-4050 budget).

You have a JSON Patient Timeline Vision (PTV) graph loaded in memory. The
host exposes deterministic tools; you MUST answer by calling tools and
quoting the event_ids they return. Do not invent events, drugs, codes,
dates, or edges.

PROTOCOL — ONE JSON OBJECT PER TURN

Your FIRST turn MUST be a plan. Subsequent turns are tool_calls, and the
last turn is a final_answer. Three shapes, one per turn, no prose around
them, no markdown fences:

  1) Plan (first turn only):
     {"plan": {
        "route": "code_lookup" | "temporal" | "semantic_then_bfs" | "orient",
        "rationale": "<one sentence>",
        "expanded_query": "<only for semantic_then_bfs: original query +
           medical synonyms, ICD family hints, drug class names>"
     }}

  2) Tool call (after the plan):
     {"tool_call": {"name": "<tool_name>", "args": { ... }}}

  3) Final answer (last turn):
     {"final_answer": {
        "answer": "<concise prose, optionally bulleted>",
        "evidence_event_ids": ["pdf_pNNNN_eNNNN", ...],
        "tools_used": ["code_index_lookup", "bfs_expand", ...]
     }}

ROUTING RULES (pick one for the plan.route)

  code_lookup        — question names a drug, ICD code, RxNorm, lab, or LOINC
                       ("every hydrocodone", "ICD I10", "RxNorm 857002").
                       Use code_index_lookup first.
  temporal           — question is scoped by date or event_type window
                       ("labs in 2023", "every visit in 2016").
                       Use temporal_scan first.
  semantic_then_bfs  — free-text clinical question ("kidney trouble",
                       "back pain radiating"). Emit an `expanded_query`
                       that adds synonyms / codes. Use semantic_search,
                       then bfs_expand on the top seeds when needed.
  orient             — ambiguous or meta-question about the chart as a
                       whole. Use graph_stats / list_event_types.

QUERY EXPANSION (semantic_then_bfs only)

When the route is semantic_then_bfs, your `expanded_query` should:
- keep the user's phrase, and
- add 3–6 medical synonyms / ICD family codes / drug-class names.
Examples:
  "kidney trouble" -> "kidney trouble chronic kidney disease creatinine BUN eGFR N18 N19"
  "back pain going down the leg" -> "radiculopathy sciatica low back pain M54 G89.29 radiating"
  "heart medicine" -> "cardiac medication beta blocker ACE inhibitor statin antihypertensive"

Pass the expanded form as semantic_search.query.

HYBRID / RERANK

Prefer narrow scope + rerank over broad scans:
- For "inflammatory markers in 2023" call temporal_scan(lab, 2023) FIRST
  to collect event_ids, then semantic_search(query=..., event_ids=those).
- For "the hydrocodone event after the 2016 flare" call code_index_lookup
  first, then semantic_search(query="after flare", event_ids=those).

RULES
- Output must be parseable JSON. No prose outside the JSON object.
- Never fabricate event_ids. Cite only ids you received from a tool.
- Stop at {max_turns} tool calls; emit final_answer before you exceed.

TOOL CATALOG
{catalog}
"""


@dataclass
class AgentTurn:
    role: str                     # "system" | "user" | "assistant" | "tool"
    content: str
    tool: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    ok: Optional[bool] = None
    parse_error: Optional[str] = None


@dataclass
class AgentLog:
    question: str
    model: str
    turns: List[AgentTurn] = field(default_factory=list)
    plan: Optional[Dict[str, Any]] = None
    final_answer: Optional[Dict[str, Any]] = None
    tools_used: List[str] = field(default_factory=list)
    reason_stopped: str = ""
    elapsed_sec: float = 0.0

    def tool_call_sequence(self) -> List[str]:
        return [
            t.tool for t in self.turns
            if t.role == "assistant" and t.tool and t.tool != "_plan"
        ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compact_result(obj: Any, max_chars: int = MAX_TOOL_RESULT_CHARS) -> str:
    text = json.dumps(obj, default=str)
    if len(text) <= max_chars:
        return text
    return text[:max_chars - 40] + "...\", \"_truncated\": true}"


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    """Best-effort JSON extraction from an LLM response."""
    s = text.strip()
    # Fast path.
    try:
        return json.loads(s)
    except Exception:
        pass
    # Fenced code block.
    fence = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", s, re.DOTALL | re.IGNORECASE)
    if fence:
        try:
            return json.loads(fence.group(1))
        except Exception:
            pass
    # Last-resort: find the widest outer {...}.
    m = _BLOCK_RX.search(s)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            return None
    return None


def _ollama_chat(
    url: str,
    model: str,
    messages: List[Dict[str, str]],
    *,
    timeout: float,
    temperature: float,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {"temperature": temperature},
    }
    r = requests.post(f"{url}/api/chat", json=payload, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    msg = (data.get("message") or {}).get("content") or ""
    return msg


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def run_agent(
    gh: GraphHandle,
    question: str,
    *,
    model: str = DEFAULT_MODEL,
    ollama_url: str = DEFAULT_OLLAMA_URL,
    max_turns: int = MAX_TOOL_TURNS,
    temperature: float = 0.1,
    timeout: float = 180.0,
) -> AgentLog:
    catalog = render_tool_catalog()
    system = SYSTEM_PROMPT_PREFIX.replace("{catalog}", catalog).replace(
        "{max_turns}", str(max_turns)
    )
    log = AgentLog(question=question, model=model)
    log.turns.append(AgentTurn(role="system", content=system))
    log.turns.append(AgentTurn(role="user", content=question))

    t0 = time.time()
    # The plan-first reminder lives in the user message so it overrides
    # any baked-in Modelfile system prompt that might still have stale
    # tool-naming conventions.
    user_content = (
        f"{question}\n\n"
        "Your FIRST reply MUST be the plan JSON "
        '{"plan": {"route": "...", "rationale": "...", '
        '"expanded_query": "..."}}. '
        "Only after the plan do you issue tool_call objects. Emit exactly one "
        "JSON object per turn and no prose."
    )
    msgs: List[Dict[str, str]] = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    # +2 accounts for (a) the plan preamble and (b) a nudge retry for a
    # malformed turn. Tool calls are still effectively capped at ``max_turns``.
    hard_cap = max_turns + 2
    tool_call_count = 0
    plan_accepted = False

    for turn_idx in range(hard_cap):
        try:
            raw = _ollama_chat(
                ollama_url, model, msgs, timeout=timeout, temperature=temperature
            )
        except Exception as exc:  # noqa: BLE001
            log.turns.append(AgentTurn(role="assistant", content="", parse_error=str(exc)))
            log.reason_stopped = f"ollama_error: {exc}"
            break

        parsed = _extract_json(raw)
        if parsed is None:
            log.turns.append(
                AgentTurn(
                    role="assistant",
                    content=raw[:800],
                    parse_error="could not parse JSON from model output",
                )
            )
            # Nudge and give one more try with clarifying message.
            msgs.append({"role": "assistant", "content": raw})
            msgs.append({
                "role": "user",
                "content": (
                    "Your previous turn was not valid JSON. Reply with exactly "
                    "one JSON object matching the protocol (tool_call or "
                    "final_answer). No prose."
                ),
            })
            continue

        if "plan" in parsed and isinstance(parsed["plan"], dict) and not plan_accepted:
            log.plan = parsed["plan"]
            plan_accepted = True
            log.turns.append(
                AgentTurn(role="assistant", content=json.dumps(parsed), tool="_plan", args=parsed["plan"])
            )
            msgs.append({"role": "assistant", "content": json.dumps(parsed)})
            msgs.append({
                "role": "user",
                "content": (
                    "Plan accepted. Now issue your first tool_call as a JSON "
                    "object of shape {\"tool_call\": {\"name\": ..., \"args\": {...}}}. "
                    "When enough evidence is collected, return "
                    "{\"final_answer\": {\"answer\": ..., \"evidence_event_ids\": [...], "
                    "\"tools_used\": [...]}}."
                ),
            })
            continue

        if "final_answer" in parsed:
            fa = parsed["final_answer"]
            if isinstance(fa, str):
                fa = {"answer": fa}
            log.final_answer = fa
            log.turns.append(
                AgentTurn(role="assistant", content=json.dumps(parsed), tool=None, args=None)
            )
            log.reason_stopped = "final_answer"
            break

        if "tool_call" in parsed and isinstance(parsed["tool_call"], dict):
            if tool_call_count >= max_turns:
                log.turns.append(
                    AgentTurn(
                        role="assistant",
                        content=json.dumps(parsed),
                        parse_error="tool_call budget exhausted; expected final_answer",
                    )
                )
                log.reason_stopped = "max_turns_reached"
                break
            tool_call_count += 1
            tc = parsed["tool_call"]
            name = str(tc.get("name") or "").strip()
            args = tc.get("args") or {}
            if not isinstance(args, dict):
                args = {}
            log.turns.append(
                AgentTurn(
                    role="assistant",
                    content=json.dumps(parsed),
                    tool=name,
                    args=args,
                )
            )
            if name not in tool_names():
                tool_result = {
                    "tool": name,
                    "ok": False,
                    "error": f"unknown tool. allowed: {tool_names()}",
                }
            else:
                tool_result = call_tool(name, gh, args)
                log.tools_used.append(name)
            result_str = _compact_result(tool_result)
            log.turns.append(
                AgentTurn(
                    role="tool",
                    content=result_str,
                    tool=name,
                    args=args,
                    ok=bool(tool_result.get("ok")),
                )
            )
            msgs.append({"role": "assistant", "content": json.dumps(parsed)})
            msgs.append({"role": "user", "content": f"TOOL_RESULT {name}: {result_str}"})
            continue

        # Neither tool_call nor final_answer — nudge.
        log.turns.append(
            AgentTurn(
                role="assistant",
                content=json.dumps(parsed),
                parse_error="neither tool_call nor final_answer present",
            )
        )
        msgs.append({"role": "assistant", "content": json.dumps(parsed)})
        msgs.append({
            "role": "user",
            "content": (
                "Reply with exactly one JSON object of shape "
                "{\"tool_call\": {...}} or {\"final_answer\": {...}}."
            ),
        })

    else:  # max turns exhausted
        log.reason_stopped = log.reason_stopped or "max_turns_reached"

    log.elapsed_sec = round(time.time() - t0, 2)
    return log


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------

def log_to_dict(log: AgentLog) -> Dict[str, Any]:
    return {
        "question": log.question,
        "model": log.model,
        "elapsed_sec": log.elapsed_sec,
        "reason_stopped": log.reason_stopped,
        "plan": log.plan,
        "tools_used": log.tools_used,
        "tool_call_sequence": log.tool_call_sequence(),
        "final_answer": log.final_answer,
        "turns": [
            {
                "role": t.role,
                "tool": t.tool,
                "args": t.args,
                "ok": t.ok,
                "parse_error": t.parse_error,
                "content_preview": (t.content or "")[:500],
            }
            for t in log.turns
        ],
    }
