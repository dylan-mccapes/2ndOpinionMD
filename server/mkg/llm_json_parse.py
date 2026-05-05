"""Shared helpers for parsing JSON objects from LLM chat output."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional


def force_json_dict(text: str) -> Optional[Dict[str, Any]]:
    """Best-effort parse of a single JSON object from model output (prose, fences, trailing junk)."""
    s = (text or "").strip()
    if not s:
        return None
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except Exception:
        pass
    fenced = re.search(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", s, re.IGNORECASE)
    if fenced:
        try:
            obj = json.loads(fenced.group(1))
            return obj if isinstance(obj, dict) else None
        except Exception:
            pass
    dec = json.JSONDecoder()
    for i, ch in enumerate(s):
        if ch != "{":
            continue
        try:
            obj, _end = dec.raw_decode(s, i)
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError:
            continue
    greedy = re.search(r"\{[\s\S]*\}", s)
    if greedy:
        chunk = greedy.group(0)
        for i in range(len(chunk)):
            if chunk[i] != "{":
                continue
            try:
                obj, _end = dec.raw_decode(chunk, i)
                if isinstance(obj, dict):
                    return obj
            except json.JSONDecodeError:
                continue
    return None
