# server/api/valyu_client.py
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
import httpx
import logging

VALYU_BASE = os.getenv("VALYU_BASE", "https://api.valyu.ai/v1").rstrip("/")
VALYU_API_KEY = (os.getenv("VALYU_API_KEY") or "").strip()
VALYU_ORG_ID = (os.getenv("VALYU_ORG_ID") or "").strip()
VALYU_MAX_PRICE = float(os.getenv("VALYU_MAX_PRICE", "20.0"))  # dollars per query guardrail
logger = logging.getLogger(__name__)
VALYU_WARN_THRESHOLD = float(os.getenv("VALYU_WARN_THRESHOLD", "0.25"))

# Soft cost guardrails (per-valyu pricing is per 1k retrievals)
VALYU_MAX_PRICE = float(os.getenv("VALYU_MAX_PRICE", "20.0"))  # search()
VALYU_ANSWER_MAX_PRICE = float(os.getenv("VALYU_ANSWER_MAX_PRICE", "30.0"))  # answer()

# Default PubMed dataset slug per Valyu docs
DEFAULT_INCLUDED_SOURCES = ["valyu/valyu-pubmed"]

QA_SYSTEM_PROMPT_WITH_VALYU = """You are a subspecialist-level clinical assistant.

You answer questions using TWO sources of context:

1. Internal MKG context:
   - Guidelines (ACR, EULAR, ESC, KDIGO, etc.)
   - Ontologies and codes (ICD-10-CM, ICD-11, SNOMED CT, LOINC, RxNorm)
   - Curated clinical notes and internal corpus

2. External literature (Valyu publications):
   - A small set of recent papers that match the question

Rules:
- Prefer guideline-consistent, evidence-based recommendations.
- Treat internal MKG context as the PRIMARY source of truth for standards of care.
- Use Valyu publications as SUPPORTING EVIDENCE:
  - Refer to them as [VALYU-1], [VALYU-2], etc.
  - Summarize their direction of evidence, not every detail.
- If Valyu and MKG appear to disagree:
  - Explain the discrepancy clearly.
  - Default to guideline-based recommendations unless the literature context is strong and consistent.

Format:
- Start with a concise answer.
- Then provide a structured explanation with headings (e.g., Diagnosis, Initial management, Escalation, Special situations).
- When referring to specific evidence, cite MKG entries as [MKG-1], [MKG-2], etc., and papers as [VALYU-1], [VALYU-2], etc.

Do not fabricate citations or guideline names that are not in the provided context.
"""

def _headers() -> Dict[str, str]:
    h = {
        "User-Agent": "2ndOpinionMD/valyu-bridge",
        "Content-Type": "application/json",
    }
    if VALYU_API_KEY:
        # Both are accepted (headers are case-insensitive); this is the combo that
        # fixed your “missing equals-sign / Missing Authentication Token” error.
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
            try:
                body: Any = r.json()
            except Exception:
                body = {"raw": r.text}
            return {
                "success": False,
                "status_code": r.status_code,
                "error": str(e),
                "body": body,
            }


def _extract_results(vy: Dict[str, Any]) -> List[Dict[str, Any]]:
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

    # Normalize score so SSE never sees null
    score = r.get("score")
    if score is None:
        score = r.get("rank")
    if score is None:
        score = 1.0

    return {
        "id": rid,
        "title": title,
        "url": r.get("url"),
        "site": r.get("site"),
        "snippet": snippet,
        "score": float(score),
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
        "included_sources": included_sources or DEFAULT_INCLUDED_SOURCES,
    }
    out = await _post("/deepsearch", payload)
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
    Valyu /answer — RAG-style answer with built-in retrieval.
    Body key is 'query' (not 'question').
    """
    payload: Dict[str, Any] = {
        "query": query,
        "included_sources": included_sources or DEFAULT_INCLUDED_SOURCES,
        "search_type": search_type,
        "max_tokens": max_tokens,
        "cite": cite,
        # Separate guardrail for /answer
        "data_max_price": VALYU_ANSWER_MAX_PRICE,
        "tool_call_mode": True,
    }
    out = await _post("/answer", payload)
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
