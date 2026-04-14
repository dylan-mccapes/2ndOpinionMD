"""Minimal Ollama /api/chat helper (no extra deps)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple


def _base_model_name(name: str) -> str:
    return (name or "").split(":", 1)[0].strip()


def ollama_fetch_tags(base_url: str, *, timeout_s: float = 10.0) -> Dict[str, Any]:
    """GET /api/tags — list local models (fast health check)."""
    import urllib.error
    import urllib.request

    url = f"{base_url.rstrip('/')}/api/tags"
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ollama_list_model_names(base_url: str, *, timeout_s: float = 10.0) -> List[str]:
    data = ollama_fetch_tags(base_url, timeout_s=timeout_s)
    out: List[str] = []
    for m in data.get("models") or []:
        n = m.get("name")
        if isinstance(n, str) and n.strip():
            out.append(n.strip())
    return out


def ollama_preflight(base_url: str, model: str, *, timeout_s: float = 10.0) -> Tuple[bool, str]:
    """
    Quick check: server reachable and model present in /api/tags.
    Does not run inference (cheap before a long harness).
    Returns (ok, message) where message is success detail or fix hint.
    """
    import urllib.error

    try:
        names = ollama_list_model_names(base_url, timeout_s=timeout_s)
    except urllib.error.URLError as e:
        return False, (
            f"Cannot reach Ollama at {base_url} (GET /api/tags). "
            f"Start the server (e.g. `ollama serve`) or set OLLAMA_URL for WSL/Docker. ({e!s})"
        )
    except Exception as e:
        return False, f"Ollama preflight failed for {base_url}: {e!s}"

    want = _base_model_name(model)
    for n in names:
        if _base_model_name(n) == want:
            return True, f"Ollama OK; model {model!r} available as {n!r}"

    sample = ", ".join(sorted(names)[:16])
    if len(names) > 16:
        sample += f", ... (+{len(names) - 16} more)"
    return False, (
        f"Model {model!r} not found in Ollama (checked /api/tags). "
        f"Available: {sample or '(none)'} — "
        f"create it: ollama create {want} -f server/ollama/eoh-llama3.1-8b-lucifer.Modelfile"
    )


def ollama_chat(
    base_url: str,
    model: str,
    user_message: str,
    *,
    system: Optional[str] = None,
    temperature: float = 0.2,
    timeout_s: int = 600,
) -> Dict[str, Any]:
    import urllib.request

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [],
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["messages"].append({"role": "system", "content": system})
    payload["messages"].append({"role": "user", "content": user_message})
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ollama_chat_messages(
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    *,
    system: Optional[str] = None,
    temperature: float = 0.2,
    timeout_s: int = 600,
) -> Dict[str, Any]:
    """POST /api/chat with a full message list (multi-turn). Each item: role + content."""
    import urllib.request

    payload: Dict[str, Any] = {
        "model": model,
        "messages": [],
        "stream": False,
        "options": {"temperature": temperature},
    }
    if system:
        payload["messages"].append({"role": "system", "content": system})
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if isinstance(role, str) and isinstance(content, str):
            payload["messages"].append({"role": role, "content": content})
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def ollama_reply_text(resp: Dict[str, Any]) -> str:
    msg = (resp.get("message") or {}).get("content")
    if isinstance(msg, str) and msg.strip():
        return msg.strip()
    return json.dumps(resp, indent=2)[:8000]
