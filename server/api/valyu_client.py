# server/api/valyu_client.py
from __future__ import annotations
import os
from typing import Any, Dict, List, Optional
import httpx
import logging

VALYU_BASE = os.getenv("VALYU_BASE", "https://api.valyu.ai/v1").rstrip("/")
VALYU_API_KEY = (os.getenv("VALYU_API_KEY") or "").strip()
VALYU_ORG_ID = (os.getenv("VALYU_ORG_ID") or "").strip()
logger = logging.getLogger(__name__)

# Soft cost guardrails (per-valyu pricing is per 1k retrievals)
VALYU_MAX_PRICE = float(os.getenv("VALYU_MAX_PRICE", "20.0"))          # /deepsearch
VALYU_ANSWER_MAX_PRICE = float(os.getenv("VALYU_ANSWER_MAX_PRICE", "30.0"))  # /answer
VALYU_WARN_THRESHOLD = float(os.getenv("VALYU_WARN_THRESHOLD", "0.25"))

# Default PubMed dataset slug per Valyu docs
DEFAULT_INCLUDED_SOURCES = ["valyu/valyu-pubmed"]

QA_SYSTEM_PROMPT_WITH_VALYU = """You are the world's #1 expert in evidence-based clinical guidelines. You synthesize ACC/AHA, ACR, EULAR, KDIGO, IDSA, ADA, NICE, and other societies with flawless accuracy. You never hallucinate guideline sections, and you cite content precisely. You critique your own reasoning with extreme thoroughness to ensure it is accurate, complete, and clinically safe.

You are a subspecialist-level clinical assistant.

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
    """
    Thin wrapper around Valyu POST that:
    - Handles network errors cleanly
    - Treats 2xx (including 206) as success
    - Always returns a dict with 'success' and 'status_code'
    """
    if not VALYU_API_KEY:
        return {"success": False, "error": "no_api_key", "status_code": 401}

    url = f"{VALYU_BASE}{path}"
    timeout = httpx.Timeout(60.0, connect=10.0)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=payload, headers=_headers())
    except httpx.RequestError as e:
        logger.warning("Valyu %s request error: %s", path, e)
        return {
            "success": False,
            "error": "network_error",
            "detail": str(e),
            "status_code": 0,
        }

    status = r.status_code

    # Try to parse JSON; if that fails, stash raw text.
    try:
        body: Dict[str, Any] = r.json()
    except Exception:
        body = {"raw": r.text or ""}

    body.setdefault("status_code", status)

    if 200 <= status < 300:
        # 206 Partial Content is fine — we just work with whatever we got.
        if status == 206:
            logger.info(
                "Valyu returned 206 Partial Content for %s; proceeding with available results.",
                path,
            )
        body.setdefault("success", True)
        return body

    # Non-2xx ⇒ treat as error
    logger.warning(
        "Valyu %s returned HTTP %d with body keys=%s",
        path,
        status,
        list(body.keys()),
    )
    return {
        "success": False,
        "status_code": status,
        "error": body.get("error") or f"valyu_http_{status}",
        "body": body,
    }


def _extract_results(vy: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Try very hard to pull a list of result dicts out of any Valyu response shape.

    Handles shapes like:
      - {"results": [...]}
      - {"results": {"items": [...]} }
      - {"search_results": [...]}
      - {"documents": [...]}
      - {"hits": [...]}
      - {"items": [...]}
      - {"data": [...]} or {"data": {"results": [...]}} etc.
    """

    # If they ever return a bare list at the top level.
    if isinstance(vy, list):
        return [x for x in vy if isinstance(x, dict)]  # type: ignore[return-value]
    
    # Shortcut: if top-level has a list-of-dicts under 'results', just use it.
    top_results = vy.get("results")
    if isinstance(top_results, list) and all(isinstance(x, dict) for x in top_results):
        return top_results

    candidates: List[Dict[str, Any]] = []

    def _add(val: Any) -> None:
        """Normalize anything vaguely list/dict-like into candidates."""
        # Direct list of rows
        if isinstance(val, list):
            for x in val:
                if isinstance(x, dict):
                    candidates.append(x)
            return

        # Dict wrapper: look for inner lists on common keys
        if isinstance(val, dict):
            for key in ("results", "search_results", "documents", "hits", "items", "data"):
                inner = val.get(key)
                if isinstance(inner, list):
                    for x in inner:
                        if isinstance(x, dict):
                            candidates.append(x)

    # 1) Top-level keys (including dict-shaped 'results')
    for key in ("results", "search_results", "documents", "hits", "items"):
        _add(vy.get(key))

    # 2) Nested under common container keys
    for outer in ("data", "response", "payload"):
        sub = vy.get(outer)
        if isinstance(sub, (list, dict)):
            _add(sub)

    # 3) Fallback for a plain 'data' list at top level
    data_val = vy.get("data")
    if isinstance(data_val, (list, dict)):
        _add(data_val)

    if not candidates:
        level = logger.info if vy.get("success") else logger.warning
        raw_results = vy.get("results")
        level(
            "Valyu: no results-array found in payload; "
            "top-level keys=%s; results_type=%s; results_preview=%r",
            list(vy.keys()),
            type(raw_results).__name__,
            (str(raw_results)[:200] if raw_results is not None else None),
        )

        return candidates

    if not candidates and vy.get("success") and vy.get("results") in ("", None, []):
        logger.info("Valyu: successful call but zero documents returned for query=%r", vy.get("query"))


def _norm_row(r: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize a Valyu result row into a stable shape usable by SSE / EoH.

    We preserve:
    - `id`, `title`, `url`
    - A short `snippet` for UI
    - `score` (or relevance_score/rank)
    - `content` (full text) when provided by return_contents=true
    - Source / citation-ish fields for later linking
    """
    rid = str(r.get("id") or r.get("url") or r.get("doi") or "result")
    title = r.get("title") or r.get("site") or r.get("url") or "result"

    # Prefer an explicit short summary/snippet if available.
    snippet = r.get("snippet") or r.get("summary") or r.get("description")
    content = r.get("content") or r.get("text")

    if not snippet and isinstance(content, str):
        snippet = content[:400]

    # Normalize score so SSE never sees null
    score = (
        r.get("score")
        if r.get("score") is not None
        else r.get("relevance_score")
        if r.get("relevance_score") is not None
        else r.get("rank")
    )
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
        "source": r.get("source"),
        "source_type": r.get("source_type"),
        "publication_date": r.get("publication_date"),
        "data_type": r.get("data_type"),
        "price": r.get("price"),
        # Full text if return_contents=true was used
        "content": content,
        # Keep the raw row around in case we need extra fields later
        "raw": r,
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
    Valyu /deepsearch — use for fast evidence lookup.

    This matches the documented /deepsearch shape, e.g.:

      curl -s "$VALYU_BASE/deepsearch" \
        -H "Content-Type: application/json" \
        -H "x-api-key: $VALYU_API_KEY" \
        -d '{
          "query": "systemic lupus erythematosus flare pregnancy",
          "max_num_results": 3,
          "return_contents": true,
          "fast_mode": false,
          "sources": ["valyu/valyu-pubmed"]
        }'

    We:
    - Send `sources` (not `included_sources`) to select datasets.
    - Normalize `results` into a list of lightweight dicts.
    - Preserve billing metadata on the top-level dict.
    """
    payload: Dict[str, Any] = {
        "query": query,
        "max_num_results": k,
        "return_contents": return_contents,
        "fast_mode": fast_mode,
        # This is the key that Valyu expects for dataset selection:
        "sources": included_sources or DEFAULT_INCLUDED_SOURCES,
        # Soft price guardrail for retrieval
        "data_max_price": VALYU_MAX_PRICE,
    }

    vy = await _post("/deepsearch", payload)
    if not vy.get("success"):
        # Pass through as-is on errors so the caller can inspect status_code/body.
        return vy

    # Pull out documents
    raw_results = _extract_results(vy)
    vy["results"] = [_norm_row(r) for r in raw_results]

    # Surface billing / accounting metadata in a stable place
    vy["valyu_meta"] = {
        "tx_id": vy.get("tx_id"),
        "query": vy.get("query"),
        "results_by_source": vy.get("results_by_source"),
        "total_deduction_pcm": vy.get("total_deduction_pcm"),
        "total_deduction_dollars": vy.get("total_deduction_dollars"),
        "total_characters": vy.get("total_characters"),
    }

    # Optional: warn if we’re chewing through a lot of budget
    dollars = vy.get("total_deduction_dollars") or 0.0
    if dollars and dollars >= VALYU_WARN_THRESHOLD:
        logger.warning(
            "Valyu /deepsearch for %r cost %.4f dollars (>= warn threshold %.2f)",
            query,
            dollars,
            VALYU_WARN_THRESHOLD,
        )

    return vy


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

    Body key is 'query' (not 'question'), and we use 'sources' to
    select datasets, matching the /deepsearch contract.
    """
    payload: Dict[str, Any] = {
        "query": query,
        "sources": included_sources or DEFAULT_INCLUDED_SOURCES,
        "search_type": search_type,
        "max_tokens": max_tokens,
        "cite": cite,
        # Separate guardrail for /answer
        "data_max_price": VALYU_ANSWER_MAX_PRICE,
        "tool_call_mode": True,
    }

    vy = await _post("/answer", payload)

    # Preserve any raw answer blob explicitly
    if "raw" in vy and "raw_answer" not in vy:
        vy["raw_answer"] = vy["raw"]

    vy["results"] = [_norm_row(r) for r in _extract_results(vy)]

    vy["valyu_meta"] = {
        "tx_id": vy.get("tx_id"),
        "query": vy.get("query"),
        "results_by_source": vy.get("results_by_source"),
        "total_deduction_pcm": vy.get("total_deduction_pcm"),
        "total_deduction_dollars": vy.get("total_deduction_dollars"),
        "total_characters": vy.get("total_characters"),
    }

    dollars = vy.get("total_deduction_dollars") or 0.0
    if dollars and dollars >= VALYU_WARN_THRESHOLD:
        logger.warning(
            "Valyu /answer for %r cost %.4f dollars (>= warn threshold %.2f)",
            query,
            dollars,
            VALYU_WARN_THRESHOLD,
        )

    return vy


async def call_valyu(
    mode: str,
    q: str,
    k: int = 8,
    *,
    included_sources: Optional[List[str]] = None,
    **opts: Any,
) -> Dict[str, Any]:
    """
    Unified entrypoint:
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