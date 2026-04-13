"""
Shrink graph tool JSON for LLM prompts — avoid megabyte snapshots.
"""

from __future__ import annotations

import copy
from typing import Any, Dict, List, Optional

_MAX_LIST = 80
_MAX_PREVIEW_NODES = 40


def summarize_tool_result_for_llm(tool_name: str, result: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy safe to embed in an agent prompt."""
    out = copy.deepcopy(result)
    if tool_name == "graph_snapshot":
        snap = out.get("snapshot")
        if isinstance(snap, dict) and "nodes" in snap:
            nodes = snap["nodes"]
            if isinstance(nodes, list) and len(nodes) > _MAX_PREVIEW_NODES:
                snap["nodes"] = nodes[:_MAX_PREVIEW_NODES]
                snap["nodes_truncated"] = True
                snap["nodes_total"] = len(nodes)
    # Cap long event_id lists anywhere
    _cap_lists(out, _MAX_LIST)
    return out


def _cap_lists(obj: Any, max_len: int) -> None:
    if isinstance(obj, dict):
        for k, v in list(obj.items()):
            if k == "event_ids" and isinstance(v, list) and len(v) > max_len:
                obj[k] = v[:max_len] + [f"... +{len(v) - max_len} more"]
            elif isinstance(v, (dict, list)):
                _cap_lists(v, max_len)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            if isinstance(item, (dict, list)):
                _cap_lists(item, max_len)
