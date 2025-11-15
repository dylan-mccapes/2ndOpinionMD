# server/api/valyu_client.py
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
import httpx

VALYU_BASE = os.getenv("VALYU_BASE", "https://api.valyu.ai/v1").rstrip("/")
VALYU_API_KEY = (os.getenv("VALYU_API_KEY") or "").strip()
VALYU_ORG_ID = (os.getenv("VALYU_ORG_ID") or "").strip()

# Default PubMed dataset slug per Valyu docs
# https://valyu.ai/healthcare (see "Healthcare Datasets")
DEFAULT_INCLUDED_SOURCES = ["valyu/valyu-pubmed"]

def _headers() -> Dict[str, str]:
    h = {
        "User-Agent": "2ndOpinionMD/valyu-bridge",
        "Content-Type": "application/json",
    }
    if VALYU_API_KEY:
        # Accept both Authorization and x-api-key (header names are case-insensitive)
        h["Authorization"] = f"Bearer {VALYU_API_KEY}"
        h["x-api-key"] = VALYU_API_KEY
    if VALYU_ORG_ID:
        h["X-Org-Id"] = VALYU_ORG_ID
    return h

async def _post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not VALYU_API_KEY:
        return {"success": False, "error": "no_api_key", "status_code": 401}
    url = f"{VALYU_BASE}{path}"
    timeout = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, json=payload, headers=_headers())
        try:
            r.raise_for_status()
            out = r.json()
            if "success" not in out:
                out["success"] = True
            return out
        except httpx.HTTPStatusError as e:
            body: Any
            try:
                body = r.json()
            except Exception:
                body = {"raw": r.text}
            return {
                "success": False,
                "status_code": r.status_code,
                "error": str(e),
                "body": body,
            }

def _extract_results(vy: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Normalize different shapes into a simple list of results.
    """
    for key in ("results", "search_results", "documents", "data"):
        val = vy.get(key)
        if isinstance(val, list):
            return val
        if isinstance(val, dict):
            for inner in ("results", "items"):
                v2 = val.get(inner)
                if isinstance(v2, list):
                    return v2
    return []

def _norm_row(r: Dict[str, Any]) -> Dict[str, Any]:
    rid = str(r.get("id") or r.get("url") or r.get("doi") or "result")
    title = r.get("title") or r.get("site") or r.get("url") or "result"
    # Prefer a short snippet-like field if present; otherwise truncate content
    snippet = r.get("snippet") or r.get("summary") or r.get("description")
    if not snippet:
        content = r.get("content") or r.get("text")
        if isinstance(content, str):
            snippet = content[:400]
    return {
        "id": rid,
        "title": title,
        "url": r.get("url"),
        "site": r.get("site"),
        "snippet": snippet,
        "score": r.get("score") or r.get("rank"),
        "doi": r.get("doi"),
        "authors": r.get("authors"),
        "source_type": r.get("source_type"),
        "publication_date": r.get("publication_date"),
    }

# -------- Public API --------

async def search(
    query: str,
    k: int = 8,
    *,
    included_sources: Optional[List[str]] = None,
    return_contents: bool = False,
    fast_mode: bool = False,
) -> Dict[str, Any]:
    """
    Valyu /search — use for fast evidence lookup.
    """
    payload: Dict[str, Any] = {
        "query": query,
        "max_num_results": k,
        "return_contents": return_contents,
        "fast_mode": fast_mode,
        # Explicitly scope to PubMed by default
        "included_sources": included_sources or DEFAULT_INCLUDED_SOURCES,
    }
    out = await _post("/search", payload)
    if not out.get("success"):
        return out
    out["results"] = [_norm_row(r) for r in _extract_results(out)]
    return out

async def answer(
    query: str,
    *,
    included_sources: Optional[List[str]] = None,
    search_type: str = "proprietary",
    max_tokens: int = 700,
    cite: bool = True,
) -> Dict[str, Any]:
    """
    Valyu /answer — ask with built-in retrieval over selected sources.
    IMPORTANT: Body key is 'query', not 'question'.
    """
    payload: Dict[str, Any] = {
        "query": query,                          # <-- required key per docs
        "included_sources": included_sources or DEFAULT_INCLUDED_SOURCES,
        "search_type": search_type,              # "proprietary" keeps it in curated sources like PubMed
        "max_tokens": max_tokens,
        "cite": cite,
    }
    out = await _post("/answer", payload)
    # Normalize a results list if the API returned any evidence
    out["results"] = [_norm_row(r) for r in _extract_results(out)]
    return out

async def call_valyu(
    mode: str,
    q: str,
    k: int = 8,
    *,
    included_sources: Optional[List[str]] = None,
    **opts: Any,
) -> Dict[str, Any]:
    """
    mode: "search" | "answer"
    """
    if mode == "answer":
        return await answer(
            q,
            included_sources=included_sources,
            search_type=str(opts.get("search_type", "proprietary")),
            max_tokens=int(opts.get("max_tokens", 700)),
            cite=bool(opts.get("cite", True)),
        )
    # default to search
    return await search(
        q,
        k=k,
        included_sources=included_sources,
        return_contents=bool(opts.get("return_contents", False)),
        fast_mode=bool(opts.get("fast_mode", False)),
    )
