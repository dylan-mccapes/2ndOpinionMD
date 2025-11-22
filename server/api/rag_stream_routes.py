# server/api/rag_stream_routes.py

import asyncio
import json
import logging
import os
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional, Tuple
from dataclasses import dataclass
import re

import asyncpg
import httpx
from fastapi import APIRouter, Depends, Query, Request
from openai import OpenAI
from sse_starlette.sse import EventSourceResponse

from . import valyu_client
from .stream_config import (
    BASE_RRF_K,
    CHAT_MODEL,
    CODING_DEFAULT_SOURCES,
    CODING_SOURCES,
    CODING_TS_K,
    CODING_ANN_K,
    CODING_MAX_PER_SOURCE,
    CODING_SYSTEM_PROMPT,
    EMBED_MODEL,
    MAX_CONTEXT_CHARS,
    ETHOS_SOURCE_NAME,
)

from .stream_gating import apply_code_row_filter, apply_source_gating
from .stream_router import route_coding_sources, CodingRouterPlan

# Minimum per-source retrieval depth for code sources in coding_mode.
# If the incoming `limit` is smaller than this, code sources will use this instead.
CODE_MIN_LIMIT = int(os.getenv("CODE_MIN_LIMIT", "32"))

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag-stream"])

client = OpenAI()

# ---------------------------------------------------------------------------
# Group toggles and defaults
# ---------------------------------------------------------------------------

# Enable/disable internal groups via env flags
USE_CODE_SOURCES = os.getenv("RAG_USE_CODES", "1") != "0"
USE_GUIDELINE_SOURCES = os.getenv("RAG_USE_GUIDELINES", "1") != "0"
USE_REST_SOURCES = os.getenv("RAG_USE_REST", "1") != "0"

# Default k per group (can be overridden via env)
CODE_K_DEFAULT = int(os.getenv("RAG_K_CODES", "64"))
GUIDE_K_DEFAULT = int(os.getenv("RAG_K_GUIDELINES", "4"))
# Rest uses ctx_k passed into build_fused_context / _event_generator

# Default per-code-source min chunks in coding_mode.
# These can be overridden via env if needed.
CODE_MIN_PER_SOURCE_CTX = {
    "icd10cm": int(os.getenv("RAG_CODE_MIN_ICD10", "10")),
    "icd11": int(os.getenv("RAG_CODE_MIN_ICD11", "10")),
    "snomed": int(os.getenv("RAG_CODE_MIN_SNOMED", "10")),
    "loinc": int(os.getenv("RAG_CODE_MIN_LOINC", "10")),
    "rxnorm": int(os.getenv("RAG_CODE_MIN_RXNORM", "10")),
}

# Hard cap per code source before final global trimming
CODE_MAX_PER_SOURCE_CTX = int(os.getenv("RAG_CODE_MAX_PER_SOURCE_CTX", "16"))

# Max number of DB sources we'll actually hit for /coding_stream to avoid huge fan-out.
MAX_CODING_SOURCES = 8

# Very light-weight heuristic for guideline sources
_GUIDELINE_EXACT = {
    "acr_ra_2021",
    "acr_ild_2023",
    "eular_ra_2022",
    "va_guidelines",
    "nice",
    "who_eml",
    "who_committee",
}
_GUIDELINE_PREFIXES = ("acr_", "eular_", "nice_", "who_", "guideline_")


@dataclass
class SourceMatches:
    source: str
    ts: list   # list[dict]
    ann: list  # list[dict]

    @property
    def combined(self) -> list:
        items = (self.ts or []) + (self.ann or [])
        # Deduplicate by (id, source_id, source) if you like
        seen = set()
        deduped = []
        for m in items:
            key = (m.get("id"), m.get("source_id"), m.get("source"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(m)
        return deduped[:CODING_MAX_PER_SOURCE]

async def retrieve_coding_matches_by_source(
    pool: asyncpg.Pool,
    q: str,
    sources: list[str],
    limit_ts: int = CODING_TS_K,
    limit_ann: int = CODING_ANN_K,
) -> dict[str, SourceMatches]:
    """
    Retrieve TS + ANN matches per source, without global fusion.
    This is used only for /coding_stream so we don't drop critical TS hits.
    """
    results: dict[str, SourceMatches] = {}

    # reuse your existing internal query helpers if you have them;
    # here we assume valyu_client has something like fetch_source_matches(...)
    for source in sources:
        # Skip any gating logic you want to reuse
        # e.g., apply_source_gating(...) if needed

        ts_matches = await valyu_client.fetch_source_matches(
            pool=pool,
            q=q,
            source=source,
            method="ts",
            limit=limit_ts,
        )

        ann_matches = await valyu_client.fetch_source_matches(
            pool=pool,
            q=q,
            source=source,
            method="ann",
            limit=limit_ann,
        )

        # You might log SSE events here like you do now:
        # yield sse("phase_start", {"source": source, "method": "ts"})
        # yield sse("matches", {...})
        # etc., but here we just collect for the LLM.

        results[source] = SourceMatches(
            source=source,
            ts=ts_matches or [],
            ann=ann_matches or [],
        )

    return results

def build_coding_messages(q: str, matches_by_source: dict[str, SourceMatches]) -> list[dict]:
    """
    Build structured messages for the coding LLM, with clear per-source blocks.
    """
    # Construct a compact text summary per source
    context_blocks = []
    for source, sm in matches_by_source.items():
        lines = [f"### Source: {source}"]
        for m in sm.combined:
            # expected fields: source_id, title, maybe description
            sid = m.get("source_id") or m.get("code") or m.get("id")
            title = m.get("title") or m.get("label") or ""
            score = m.get("score")
            lines.append(f"- {sid} :: {title} (score={score})")
        context_blocks.append("\n".join(lines))

    context_text = "\n\n".join(context_blocks) if context_blocks else "No matches retrieved."

    system_msg = {
        "role": "system",
        "content": CODING_SYSTEM_PROMPT,
    }

    user_msg = {
        "role": "user",
        "content": (
            "Clinical question:\n"
            f"{q}\n\n"
            "Below is the retrieved coding context, grouped by source. "
            "Remember: for each section (ICD-10-CM, ICD-11, SNOMED CT, LOINC, RxNorm), "
            "only use codes from the matching source, and do NOT invent codes.\n\n"
            f"{context_text}"
        ),
    }

    return [system_msg, user_msg]
def build_allowed_code_index(matches_by_source: dict[str, SourceMatches]) -> dict[str, set[str]]:
    """
    allowed_codes['icd10cm'] = {'M32.10', 'M32.19', ...}
    etc.
    """
    allowed: dict[str, set[str]] = {}
    for source, sm in matches_by_source.items():
        codes = set()
        for m in sm.combined:
            sid = m.get("source_id") or m.get("code") or m.get("id")
            if sid:
                codes.add(str(sid))
        allowed[source] = codes
    return allowed


def validate_coding_answer(
    answer: str,
    allowed_codes: dict[str, set[str]],
) -> tuple[bool, str | None]:
    """
    Very lightweight validation:
    - Look for patterns like 'ICD-10-CM', 'ICD-11', 'SNOMED', 'LOINC', 'RxNorm'
      followed by codes that must be in the allowed set for that system.
    - Returns (ok, error_message_if_any).
    """

    # map headings to source keys
    system_to_source = {
        "ICD-10-CM": "icd10cm",
        "ICD-11": "icd11",
        "SNOMED": "snomed",
        "SNOMED CT": "snomed",
        "LOINC": "loinc",
        "RxNorm": "rxnorm",
    }

    # Very loose regex: CODE — description
    code_pattern = re.compile(r"^[-*]\s*([A-Z0-9\.\-]+)\s+—", re.MULTILINE)

    current_system = None
    for line in answer.splitlines():
        line_stripped = line.strip()

        # detect section heading
        for heading, source in system_to_source.items():
            if line_stripped.upper().startswith(heading.upper()):
                current_system = source
                break

        # detect codes in bullet lines
        m = code_pattern.search(line_stripped)
        if m and current_system:
            code = m.group(1)
            allowed = allowed_codes.get(current_system, set())
            if code not in allowed:
                return False, (
                    f"Code {code} was emitted under {current_system}, "
                    f"but is not in the retrieved context for that system."
                )

    return True, None

def _is_guideline_source(src: str) -> bool:
    s = (src or "").lower()
    if s in _GUIDELINE_EXACT:
        return True
    return any(s.startswith(pfx) for pfx in _GUIDELINE_PREFIXES)

# ---------------------------------------------------------------------------
# Coding prepass: ledger, grader, gap retrieval, pinning
# ---------------------------------------------------------------------------

CODING_GRADER_SYSTEM_PROMPT = """
You are a medical coding auditor for a retrieval-augmented system.

You receive:
- A clinical question.
- A thin ledger of retrieved codes from ICD-10-CM, ICD-11, SNOMED CT, LOINC, and RxNorm.

Your goals:
1. Decide which retrieved codes are clinically appropriate and relevant to the question.
2. Identify IMPORTANT missing "slots" where the question clearly implies a code that is not present.

Definitions:
- "Keep codes" = codes that are clearly correct and relevant to the question.
- "Missing slot" = an axis where a code is expected but not present, e.g.
    - ICD-10-CM lupus nephritis
    - SNOMED kidney biopsy
    - LOINC protein/creatinine ratio
    - RxNorm mycophenolate mofetil, prednisone
    - etc.

Rules:
- NEVER invent codes. You can only keep codes that appear in the ledger.
- You MAY mark missing slots even if you do not know the exact code.
- Missing slots should be specific enough to guide a follow-up search:
    - Include vocabulary name (icd10cm, icd11, snomed, loinc, rxnorm).
    - Include a short human-readable label, e.g. "lupus nephritis", "kidney biopsy".
    - Include a list of 1–4 search terms to use for retrieval.

Output STRICT JSON with this exact shape:
{
  "keep": {
    "icd10cm": ["CODE1", "CODE2"],
    "icd11": ["..."],
    "snomed": ["..."],
    "loinc": ["..."],
    "rxnorm": ["..."]
  },
  "missing_slots": [
    {
      "vocabulary": "icd10cm",
      "slot_label": "lupus nephritis",
      "search_terms": ["lupus nephritis", "renal involvement in SLE"]
    }
  ]
}

Notes:
- You do NOT need to fill every vocabulary.
- If a vocabulary is not relevant, just leave it empty or omit it in "keep".
- Be conservative: only keep codes that clearly match the question.
""".strip()


def build_coding_ledger(
    results_by_source: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Build a thin, LLM-friendly ledger of retrieved codes per source.

    Shape:
      {
        "sources": {
          "icd10cm": [
            {"code": "M3210", "title": "...", "score": 0.812},
            ...
          ],
          "icd11": [...],
          ...
        }
      }
    """
    ledger_sources: Dict[str, List[Dict[str, Any]]] = {}

    for src, rows in results_by_source.items():
        items: List[Dict[str, Any]] = []
        for r in rows:
            code = r.get("source_id") or r.get("id")
            if not code:
                continue
            title = (r.get("title") or "").strip()
            score = float(r.get("score") or 0.0)
            items.append(
                {
                    "code": str(code),
                    "title": title,
                    "score": score,
                }
            )
        if items:
            # Sort high → low score for readability
            items.sort(key=lambda x: x["score"], reverse=True)
            ledger_sources[src] = items

    return {"sources": ledger_sources}


def summarize_coding_ledger(ledger: Dict[str, Any]) -> Dict[str, Any]:
    """
    Produce a compact summary for SSE traces:
      {
        "source_counts": {"icd10cm": 12, "icd11": 8, ...},
        "total_codes": 34
      }
    """
    sources = ledger.get("sources", {}) or {}
    source_counts = {src: len(items) for src, items in sources.items()}
    total_codes = sum(source_counts.values())
    return {
        "source_counts": source_counts,
        "total_codes": total_codes,
    }


async def run_coding_grader(
    q: str,
    ledger: Dict[str, Any],
    pass_id: int,
    *,
    model: str = CHAT_MODEL,
) -> Dict[str, Any]:
    """
    Call the coding grader LLM once.

    Returns:
      {
        "keep": {"icd10cm": ["..."], "icd11": [...], ...},
        "missing_slots": [
          {"vocabulary": "icd10cm", "slot_label": "...", "search_terms": ["..."]},
          ...
        ]
      }
    On failure, returns empty structures.
    """
    messages = [
        {
            "role": "system",
            "content": CODING_GRADER_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                f"PASS {pass_id}.\n\n"
                "Clinical question:\n"
                f"{q.strip()}\n\n"
                "Retrieved code ledger (per vocabulary):\n"
                f"{json.dumps(ledger, indent=2)}\n\n"
                "Return STRICT JSON ONLY, using the schema described in the system prompt."
            ),
        },
    ]

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.exception("run_coding_grader: OpenAI call failed")
        return {"keep": {}, "missing_slots": [], "error": str(e)}

    content = completion.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("run_coding_grader: JSON parse failed: %r", content[:500])
        return {"keep": {}, "missing_slots": [], "error": f"json_parse_failed: {e}"}

    keep = data.get("keep") or {}
    missing_slots = data.get("missing_slots") or []

    # Basic sanitization
    clean_keep: Dict[str, List[str]] = {}
    if isinstance(keep, dict):
        for src, codes in keep.items():
            if not isinstance(codes, list):
                continue
            cleaned: List[str] = []
            for c in codes:
                if not isinstance(c, str):
                    continue
                c_clean = c.strip()
                if c_clean:
                    cleaned.append(c_clean)
            if cleaned:
                clean_keep[str(src).lower()] = cleaned

    clean_missing: List[Dict[str, Any]] = []
    if isinstance(missing_slots, list):
        for slot in missing_slots:
            if not isinstance(slot, dict):
                continue
            vocab = str(slot.get("vocabulary", "")).strip().lower()
            if not vocab:
                continue
            label = str(slot.get("slot_label", "")).strip()
            terms_raw = slot.get("search_terms") or []
            terms: List[str] = []
            if isinstance(terms_raw, list):
                for t in terms_raw:
                    if not isinstance(t, str):
                        continue
                    t_clean = t.strip()
                    if t_clean:
                        terms.append(t_clean)
            if not terms and label:
                terms = [label]
            clean_missing.append(
                {
                    "vocabulary": vocab,
                    "slot_label": label,
                    "search_terms": terms,
                }
            )

    return {"keep": clean_keep, "missing_slots": clean_missing}


async def fill_coding_gaps(
    q: str,
    missing_slots: List[Dict[str, Any]],
    results_by_source: Dict[str, List[Dict[str, Any]]],
    pool: asyncpg.Pool,
    per_slot_limit: int = 16,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    For each missing slot, run an extra TS pass with focused search terms
    and merge any new matches into results_by_source.

    Returns the updated results_by_source.
    """
    if not missing_slots:
        return results_by_source

    for slot in missing_slots:
        vocab = slot.get("vocabulary", "").lower()
        terms = slot.get("search_terms") or []
        label = slot.get("slot_label") or ""

        if vocab not in CODING_SOURCES:
            # Only code vocabularies are supported here
            continue

        search_terms = [t for t in terms if isinstance(t, str) and t.strip()]
        if not search_terms and label:
            search_terms = [label]

        if not search_terms:
            continue

        try:
            extra_rows = await search_source_ts_for_terms(
                pool=pool,
                source=vocab,
                terms=search_terms,
                limit=per_slot_limit,
            )
        except Exception:
            logger.exception(
                "fill_coding_gaps: TS_for_terms failed for vocab=%s terms=%r",
                vocab,
                search_terms,
            )
            continue

        if not extra_rows:
            continue

        existing = results_by_source.get(vocab, [])
        combined: Dict[Any, Dict[str, Any]] = {}

        # seed with existing
        for r in existing:
            key = r.get("id")
            combined[key] = r

        # add new
        for r in extra_rows:
            norm = normalize_row(r, source=vocab)
            key = norm["id"]
            if key not in combined:
                combined[key] = norm

        # Sort by score high → low for downstream
        merged_rows = list(combined.values())
        merged_rows.sort(key=lambda r: float(r.get("score", 0.0) or 0.0), reverse=True)
        results_by_source[vocab] = merged_rows

    return results_by_source


def pin_coding_rows_from_keep_map(
    results_by_source: Dict[str, List[Dict[str, Any]]],
    keep_map: Dict[str, List[str]],
) -> Dict[str, int]:
    """
    Mark rows as pinned based on the grader's keep_map.

    keep_map like:
      {"icd10cm": ["M3210", "M3219"], "loinc": ["2890-2"], ...}

    Returns a dict of {source: pinned_count}.
    """
    pinned_counts: Dict[str, int] = {}

    # Normalize keep_map keys and values to strings for comparison
    norm_keep: Dict[str, set[str]] = {}
    for src, codes in keep_map.items():
        src_norm = str(src).lower()
        code_set: set[str] = set()
        if not isinstance(codes, list):
            continue
        for c in codes:
            if not isinstance(c, str):
                continue
            c_clean = c.strip()
            if c_clean:
                code_set.add(c_clean)
        if code_set:
            norm_keep[src_norm] = code_set

    for src, rows in results_by_source.items():
        src_norm = str(src).lower()
        wanted = norm_keep.get(src_norm)
        if not wanted:
            continue

        count = 0
        for r in rows:
            sid = r.get("source_id") or r.get("id")
            sid_str = str(sid).strip() if sid is not None else ""
            if sid_str and sid_str in wanted:
                if not r.get("pinned"):
                    r["pinned"] = True
                count += 1

        if count:
            pinned_counts[src] = count

    return pinned_counts


def _classify_internal_source(src: str) -> str:
    """
    Classify internal (DB) sources into one of:
      - 'code'       : ICD, SNOMED, RxNorm, etc.
      - 'guideline'  : ACR/EULAR/VA/NICE/WHO-style docs
      - 'rest'       : everything else
    """
    if src in CODING_SOURCES:
        return "code"
    if _is_guideline_source(src):
        return "guideline"
    return "rest"


# ---------------------------------------------------------------------------
# Result normalization / fusion
# ---------------------------------------------------------------------------


def normalize_row(
    row: Dict[str, Any],
    source: Optional[str] = None,
    method: Optional[str] = None,
) -> Dict[str, Any]:
    rid = (
        row.get("id")
        or row.get("uid")
        or row.get("pmid")
        or row.get("pubmed_id")
        or row.get("doc_id")
    )

    if rid is None:
        rid = f"auto-{hash(json.dumps(row, default=str))}"

    src = source or row.get("source") or "unknown"

    return {
        "id": rid,
        "source": src,
        "source_id": row.get("source_id"),
        "title": row.get("title") or "",
        "text": row.get("text") or row.get("abstract") or "",
        "meta": row.get("meta") or row,
        "score": float(row.get("score", 0.0)),
        "method": method or row.get("method"),
    }


def rrf_fuse(
    results_by_source: Dict[str, List[Dict[str, Any]]],
    k: int,
    base: float = 60.0,
) -> List[Dict[str, Any]]:
    scores: Dict[Tuple[str, Any], float] = {}
    rows_for_key: Dict[Tuple[str, Any], Dict[str, Any]] = {}

    for src, rows in results_by_source.items():
        for rank, row in enumerate(rows):
            norm = normalize_row(row, source=src)
            key = (norm["source"], norm["id"])
            rrf_score = 1.0 / (base + rank)
            scores[key] = scores.get(key, 0.0) + rrf_score
            rows_for_key[key] = norm

    fused = sorted(
        rows_for_key.values(),
        key=lambda r: scores[(r["source"], r["id"])],
        reverse=True,
    )
    return fused[:k]


def build_fused_context(
    results_by_source: Dict[str, List[Dict[str, Any]]],
    k: int,
    coding_mode: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fuse internal sources for final context using 3 groups, with light pinning.

    In coding_mode:
      - ALL pinned rows are preserved, even if they exceed k.
      - Non-pinned rows are still limited by k (for guidelines/rest).
      - Final truncation happens by MAX_CONTEXT_CHARS in format_context_for_llm.

    In non-coding mode:
      - Behavior is unchanged: pinned rows get priority, but global k still applies.
    """
    if not results_by_source:
        return []

    # Effective cap: in coding_mode, allow many more rows; rely on char limit later.
    if coding_mode:
        k_effective = max(k, 10_000)
    else:
        k_effective = k

    # ---------- 1) Flatten + gather pinned rows ----------------------------
    all_rows: List[Dict[str, Any]] = []
    for rows in results_by_source.values():
        all_rows.extend(rows)

    pinned_rows = [r for r in all_rows if r.get("pinned")]
    non_pinned_rows = [r for r in all_rows if not r.get("pinned")]

    def _sort_by_score(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            rows,
            key=lambda r: float(r.get("score", 0.0) or 0.0),
            reverse=True,
        )

    pinned_code: List[Dict[str, Any]] = []
    pinned_guideline: List[Dict[str, Any]] = []
    pinned_rest: List[Dict[str, Any]] = []

    for r in pinned_rows:
        src = r.get("source") or ""
        kind = _classify_internal_source(src)
        if kind == "code":
            pinned_code.append(r)
        elif kind == "guideline":
            pinned_guideline.append(r)
        else:
            pinned_rest.append(r)

    pinned_ordered: List[Dict[str, Any]] = (
        _sort_by_score(pinned_code)
        + _sort_by_score(pinned_guideline)
        + _sort_by_score(pinned_rest)
    )

    # ---------- 2) Rebuild results_by_source without pinned rows -----------
    remaining_by_source: Dict[str, List[Dict[str, Any]]] = {}
    for src, rows in results_by_source.items():
        remaining = [r for r in rows if not r.get("pinned")]
        if remaining:
            remaining_by_source[src] = remaining

    # ---------- 3) Legacy group fusion on non-pinned rows ------------------
    if not remaining_by_source:
        # All rows were pinned; DO NOT truncate in coding_mode.
        final: List[Dict[str, Any]] = []
        seen: set[Tuple[str, Any]] = set()
        for r in pinned_ordered:
            key = ((r.get("source") or ""), r.get("id"))
            if key in seen:
                continue
            seen.add(key)
            final.append(r)
            if not coding_mode and len(final) >= k_effective:
                break

        code_ct = sum(
            1 for r in final
            if _classify_internal_source(r.get("source") or "") == "code"
        )
        guide_ct = sum(
            1 for r in final
            if _classify_internal_source(r.get("source") or "") == "guideline"
        )
        rest_ct = len(final) - code_ct - guide_ct

        logger.info(
            "FUSED_CONTEXT sizes (all_pinned): codes=%d, guidelines=%d, rest=%d, total=%d (coding_mode=%s)",
            code_ct,
            guide_ct,
            rest_ct,
            len(final),
            coding_mode,
        )
        return final

    code_by_source: Dict[str, List[Dict[str, Any]]] = {}
    guideline_by_source: Dict[str, List[Dict[str, Any]]] = {}
    rest_by_source: Dict[str, List[Dict[str, Any]]] = {}

    for src, rows in remaining_by_source.items():
        kind = _classify_internal_source(src)
        if kind == "code":
            code_by_source[src] = rows
        elif kind == "guideline":
            guideline_by_source[src] = rows
        else:
            rest_by_source[src] = rows

    k_codes = max(0, CODE_K_DEFAULT)
    k_guidelines = max(0, GUIDE_K_DEFAULT)
    k_rest = max(0, k_effective)

    fused_codes: List[Dict[str, Any]] = []
    fused_guidelines: List[Dict[str, Any]] = []
    fused_rest: List[Dict[str, Any]] = []

    # --- CODE GROUP --------------------------------------------------------
    if USE_CODE_SOURCES and code_by_source:
        if coding_mode:
            per_source_rows: List[Dict[str, Any]] = []
            for src, rows in code_by_source.items():
                src_norm = (src or "").lower()
                src_rows = sorted(
                    rows,
                    key=lambda r: float(r.get("score", 0.0) or 0.0),
                    reverse=True,
                )
                min_keep = CODE_MIN_PER_SOURCE_CTX.get(src_norm, 0)
                keep_n = min(len(src_rows), CODE_MAX_PER_SOURCE_CTX)
                keep_n = max(min_keep, keep_n)
                if keep_n <= 0:
                    continue
                per_source_rows.extend(src_rows[:keep_n])

            if per_source_rows:
                per_source_rows.sort(
                    key=lambda r: float(r.get("score", 0.0) or 0.0),
                    reverse=True,
                )
                # In coding_mode we do NOT hard-cap by k_effective; we keep all these.
                fused_codes = per_source_rows
            else:
                fused_codes = []
        else:
            fused_codes = rrf_fuse(code_by_source, k=k_codes)

    # --- GUIDELINE GROUP ---------------------------------------------------
    if USE_GUIDELINE_SOURCES and guideline_by_source:
        fused_guidelines = rrf_fuse(guideline_by_source, k=k_guidelines)

    # --- REST GROUP --------------------------------------------------------
    if USE_REST_SOURCES and rest_by_source and k_rest > 0:
        fused_rest = rrf_fuse(rest_by_source, k=k_rest)

    fused_non_pinned = fused_codes + fused_guidelines + fused_rest

    # ---------- 4) Combine pinned + non-pinned, dedupe, truncate -----------
    final: List[Dict[str, Any]] = []
    seen: set[Tuple[str, Any]] = set()

    # 4a) First, add ALL pinned rows (no cap in coding_mode)
    for r in pinned_ordered:
        key = ((r.get("source") or ""), r.get("id"))
        if key in seen:
            continue
        seen.add(key)
        final.append(r)
        # In non-coding mode, we still respect k_effective
        if not coding_mode and len(final) >= k_effective:
            break

    # 4b) Add non-pinned rows — but NEVER remove pinned rows
    for r in fused_non_pinned:
        key = ((r.get("source") or ""), r.get("id"))
        if key in seen:
            continue
        seen.add(key)
        final.append(r)
        if not coding_mode and len(final) >= k_effective:
            break

    code_ct = sum(
        1 for r in final
        if _classify_internal_source(r.get("source") or "") == "code"
    )
    guide_ct = sum(
        1 for r in final
        if _classify_internal_source(r.get("source") or "") == "guideline"
    )
    rest_ct = len(final) - code_ct - guide_ct
    pinned_ct = sum(1 for r in final if r.get("pinned"))

    logger.info(
        "FUSED_CONTEXT sizes: codes=%d, guidelines=%d, rest=%d, total=%d, pinned=%d (coding_mode=%s)",
        code_ct,
        guide_ct,
        rest_ct,
        len(final),
        pinned_ct,
        coding_mode,
    )

    return final


def format_context_for_llm(
    ctx: Iterable[Dict[str, Any]],
    coding_mode: bool = False,
) -> str:
    """
    Build a compact text context for the LLM.

    In coding_mode:
      - Code sources come first, then guidelines, then rest.
      - Code IDs are made explicit (RxNorm CUI=..., ICD-10-CM=..., etc.).
      - Truncation by MAX_CONTEXT_CHARS happens *after* reordering so
        code rows are maximally preserved.

    In non-coding mode:
      - Rows keep their incoming order; we still enforce MAX_CONTEXT_CHARS.
    """
    from .stream_config import CODE_SOURCES as _CODE_SOURCES

    rows = list(ctx)

    # 1) In coding_mode, put code sources first, then guidelines, then rest.
    if coding_mode:
        code_rows: List[Dict[str, Any]] = []
        guideline_rows: List[Dict[str, Any]] = []
        rest_rows: List[Dict[str, Any]] = []

        for r in rows:
            src = r.get("source") or "unknown"
            if src in _CODE_SOURCES:
                code_rows.append(r)
            elif _is_guideline_source(src):
                guideline_rows.append(r)
            else:
                rest_rows.append(r)

        ordered_rows = code_rows + guideline_rows + rest_rows
    else:
        ordered_rows = rows

    blocks: List[str] = []
    total_len = 0
    max_chars = MAX_CONTEXT_CHARS

    for i, row in enumerate(ordered_rows, start=1):
        src = row.get("source", "unknown")
        title = row.get("title") or ""
        text = (row.get("text") or "").strip()
        source_id = row.get("source_id")

        source_id_str = f" ({source_id})" if source_id else ""

        if coding_mode:
            # Label context kind for the model
            kind = "CODE_CONTEXT" if src in _CODE_SOURCES else "CLINICAL_CONTEXT"

            # Make codes *very* explicit for the model
            if src == "rxnorm" and source_id:
                code_label = f"RxNorm CUI={source_id}"
            elif src == "icd11" and source_id:
                code_label = f"ICD-11={source_id}"
            elif src == "icd10cm" and source_id:
                code_label = f"ICD-10-CM={source_id}"
            elif src == "snomed" and source_id:
                code_label = f"SNOMED CT={source_id}"
            else:
                code_label = source_id_str.strip(" ()") if source_id else ""

            code_suffix = f" [{code_label}]" if code_label else ""

            block = (
                f"[{i}] kind={kind} {src}{source_id_str}{code_suffix} | "
                f"{title} | {text}"
            )
        else:
            block = f"[{i}] {src}{source_id_str} | {title} | {text}"

        # +2 for the separating "\n\n"
        if total_len + len(block) + 2 > max_chars:
            blocks.append("[truncated]")
            break

        blocks.append(block)
        total_len += len(block) + 2

    context_str = "\n\n".join(blocks)

    # Debug logging to confirm RxNorm / codes really made it in
    logger.info("LLM CONTEXT FINAL LEN=%s", len(context_str))
    logger.info(
        "LLM CONTEXT FINAL TAIL:\n%s",
        "\n".join(context_str.splitlines()[-20:]),
    )

    return context_str


# ---------------------------------------------------------------------------
# Embedding helpers & PG pool
# ---------------------------------------------------------------------------


async def embed_query(q: str) -> List[float]:
    resp = client.embeddings.create(model=EMBED_MODEL, input=[q])
    return resp.data[0].embedding  # type: ignore[no-any-return]


def embedding_to_vector_literal(vec: List[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


_PG_POOL: Optional[asyncpg.Pool] = None


def _get_pg_dsn() -> str:
    sync_url = os.getenv("SYNC_DATABASE_URL")
    if sync_url:
        return sync_url

    db_url = os.getenv("DATABASE_URL")
    if db_url:
        if "+asyncpg" in db_url:
            return db_url.replace("+asyncpg", "")
        if "+psycopg" in db_url:
            return db_url.replace("+psycopg", "")
        return db_url

    return "postgresql://2ndopinionmd@localhost:5432/2ndopinionmd"


async def resolve_pg_pool() -> asyncpg.Pool:
    global _PG_POOL
    if _PG_POOL is None:
        dsn = _get_pg_dsn()
        max_size = int(os.getenv("PGPOOL_MAX", "10"))
        logger.info("Creating asyncpg pool dsn=%s max_size=%s", dsn, max_size)
        _PG_POOL = await asyncpg.create_pool(dsn, min_size=1, max_size=max_size)
    return _PG_POOL


# ---------------------------------------------------------------------------
# DB Search Helpers (TS + ANN)
# ---------------------------------------------------------------------------


async def search_source_ts(
    pool: asyncpg.Pool,
    source: str,
    q: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Text-search retrieval.
    Uses rag_corpus.ts GIN index (ts) and filters by source.
    """
    sql = """
        SELECT id, source, source_id, title, text, meta,
               ts_rank(ts, plainto_tsquery($1)) AS score
        FROM rag_corpus
        WHERE source = $2
          AND ts @@ plainto_tsquery($1)
        ORDER BY score DESC
        LIMIT $3;
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, q, source, limit)

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "source": r["source"],
                "source_id": r["source_id"],
                "title": r["title"],
                "text": r["text"],
                "meta": r["meta"],
                "score": float(r["score"] or 0.0),
                "method": "ts",
            }
        )
    return out

async def search_source_ts_for_terms(
    pool: asyncpg.Pool,
    source: str,
    terms: List[str],
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Variant of text-search retrieval for code sources.

    Instead of plainto_tsquery(full_question), we run several smaller
    tsqueries (one per term) and then merge + re-rank results.

    This dramatically cuts noise for huge code corpora like RxNorm/SNOMED.
    """
    # Fallback: if we somehow have no terms, just behave like the normal TS.
    if not terms:
        return await search_source_ts(pool, source, " ".join(terms) or "", limit)

    sql = """
        SELECT id, source, source_id, title, text, meta,
               ts_rank(ts, plainto_tsquery($1)) AS score
        FROM rag_corpus
        WHERE source = $2
          AND ts @@ plainto_tsquery($1)
        ORDER BY score DESC
        LIMIT $3;
    """

    combined: Dict[Any, Dict[str, Any]] = {}

    # Simple heuristic: distribute the overall limit across terms
    per_term_limit = max(3, limit // max(1, len(terms)))

    async with pool.acquire() as conn:
        for term in terms:
            t = term.strip()
            if not t:
                continue
            rows = await conn.fetch(sql, t, source, per_term_limit)
            for r in rows:
                rid = r["id"]
                score = float(r["score"] or 0.0)
                existing = combined.get(rid)
                if existing is None or score > existing["score"]:
                    combined[rid] = {
                        "id": r["id"],
                        "source": r["source"],
                        "source_id": r["source_id"],
                        "title": r["title"],
                        "text": r["text"],
                        "meta": r["meta"],
                        "score": score,
                        "method": "ts_terms",
                    }

    merged = sorted(
        combined.values(),
        key=lambda r: r.get("score", 0.0),
        reverse=True,
    )
    return merged[:limit]

async def search_source_ann(
    pool: asyncpg.Pool,
    source: str,
    q_vec_literal: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """
    HNSW / ivfflat vector ANN search for the given source.
    Assumes partial index:
        CREATE INDEX ... WHERE source='xyz' AND embedding IS NOT NULL;
    """
    sql = """
        SELECT id, source, source_id, title, text, meta,
               1 - (embedding <=> $1::vector) AS score
        FROM rag_corpus
        WHERE source = $2
          AND embedding IS NOT NULL
        ORDER BY embedding <=> $1::vector
        LIMIT $3;
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, q_vec_literal, source, limit)

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "id": r["id"],
                "source": r["source"],
                "source_id": r["source_id"],
                "title": r["title"],
                "text": r["text"],
                "meta": r["meta"],
                "score": float(r["score"] or 0.0),
                "method": "ann",
            }
        )
    return out


# ---------------------------------------------------------------------------
# Valyu integration
# ---------------------------------------------------------------------------


async def fetch_valyu_results(
    q: str,
    mode: str,
    limit: int,
    raw: bool,
    sources: Optional[str],
    boost: float,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Bridge between ask_stream/coding_stream and server/api/valyu_client.py.

    - mode: "search" or "answer"
    - limit: how many results to retrieve from Valyu
    - raw: if true, ask Valyu to include full contents (when supported)
    - sources: optional CSV like "valyu/valyu-pubmed,valyu/another-set"
    - boost: currently unused here, but kept in signature for future tuning
    """
    # Parse included_sources into the shape valyu_client expects
    included_sources: Optional[List[str]] = None
    if sources:
        included_sources = [s.strip() for s in sources.split(",") if s.strip()]

    try:
        vy = await valyu_client.call_valyu(
            mode=mode or "search",
            q=q,
            k=limit,
            included_sources=included_sources,
            # These map onto the valyu_client.search / answer options
            return_contents=bool(raw),
            fast_mode=(mode == "search"),
        )
    except Exception as e:
        logger.exception("Valyu call failed")
        return {}

    # valyu_client._post already normalizes errors into {"success": False, ...}
    if not vy.get("success"):
        logger.warning("Valyu returned error payload: %r", vy)
        return {}

    hits = vy.get("results", [])
    if not isinstance(hits, list):
        logger.warning("Unexpected Valyu results shape: %r", type(hits))
        return {}

    grouped: Dict[str, List[Dict[str, Any]]] = {}

    for h in hits:
        src_key = "valyu_pubmed"

        base = {
            "id": h.get("id"),
            "source": src_key,
            "title": h.get("title") or "",
            "text": h.get("snippet") or "",
            "meta": h,
            "score": float(h.get("score", 0.0) or 0.0),
        }

        norm = normalize_row(base, source=src_key, method="valyu")
        grouped.setdefault(src_key, []).append(norm)

    # Sort high→low and cap per-source limit
    for src, rows in grouped.items():
        rows.sort(key=lambda r: r.get("score", 0.0), reverse=True)
        grouped[src] = rows[:limit]

    return grouped


# ---------------------------------------------------------------------------
# LLM helpers
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Term extraction (coding + QA) with expansions
# ---------------------------------------------------------------------------


TERM_EXTRACT_SYSTEM_PROMPT = """You extract coding-related medical concepts from a clinical question.

Return:
- "terms": 5–20 canonical concepts that appear or are clearly implied in the question
  and are useful for ICD-10-CM, ICD-11, SNOMED CT, LOINC, and RxNorm coding.
- "expansions": for each term, synonyms and closely related phrases that different
  coding systems or clinicians might use.

Focus on:
- diseases and conditions
- procedures and surgeries
- imaging studies
- labs and measurements
- medications and drug classes
- key pathophysiology or syndromes

Rules:
- Do NOT invent new diagnoses that are not clearly implied.
- Keep expansions tight and clinically meaningful (no long explanations).
- Output STRICT JSON, no comments or trailing commas.
"""


async def extract_query_terms(
    q: str,
    *,
    model: str = CHAT_MODEL,
    max_terms: int = 20,
) -> Dict[str, Any]:
    """
    Call the LLM once to extract canonical coding terms plus expansions (synonyms, related phrases).

    Returns:
        {
          "terms": [...],
          "expansions": {
            "term": ["syn1", "syn2", ...],
            ...
          }
        }
    """
    messages = [
        {
            "role": "system",
            "content": TERM_EXTRACT_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": (
                "Question:\n"
                f"{q}\n\n"
                "Return JSON in exactly this form (no extra keys):\n"
                '{\n'
                '  "terms": ["..."],\n'
                '  "expansions": {\n'
                '    "term1": ["...", "..."],\n'
                '    "term2": ["...", "..."]\n'
                "  }\n"
                "}\n"
            ),
        },
    ]

    logger.debug("extract_query_terms: calling LLM for term extraction")

    try:
        # NOTE: OpenAI Python client is sync; do NOT 'await' this.
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=0.0,
            response_format={"type": "json_object"},
        )
    except Exception as e:
        logger.exception("extract_query_terms: OpenAI call failed")
        # Bubble enough structure that callers can emit a useful SSE payload.
        return {
            "terms": [],
            "expansions": {},
            "error": "openai_call_failed",
            "detail": str(e),
        }

    content = completion.choices[0].message.content or "{}"
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        logger.warning("extract_query_terms: JSON parse failed, content=%r", content)
        return {
            "terms": [],
            "expansions": {},
            "error": "json_parse_failed",
            "detail": str(e),
        }

    terms = data.get("terms", []) or []
    expansions = data.get("expansions", {}) or {}

    # Enforce max_terms on canonical "terms" list
    if isinstance(terms, list):
        terms = [t for t in terms if isinstance(t, str) and t.strip()]
        terms = terms[:max_terms]
    else:
        terms = []

    # Sanitize expansions
    clean_expansions: Dict[str, List[str]] = {}
    if isinstance(expansions, dict):
        for k, v in expansions.items():
            if not isinstance(k, str):
                continue
            if not isinstance(v, list):
                continue
            cleaned = [x.strip() for x in v if isinstance(x, str) and x.strip()]
            if cleaned:
                clean_expansions[k] = cleaned

    return {
        "terms": terms,
        "expansions": clean_expansions,
    }


def build_all_terms(term_data: Dict[str, Any]) -> List[str]:
    """
    Flatten canonical terms + expansions into a single list with de-duplication.
    This list can be used for ts/ANN queries.
    """
    terms: List[str] = term_data.get("terms", []) or []
    expansions: Dict[str, List[str]] = term_data.get("expansions", {}) or {}

    seen: set[str] = set()
    all_terms: List[str] = []

    for t in terms:
        if not t or not isinstance(t, str):
            continue
        t = t.strip()
        if t and t.lower() not in seen:
            seen.add(t.lower())
            all_terms.append(t)

        for e in expansions.get(t, []):
            if not e or not isinstance(e, str):
                continue
            e_clean = e.strip()
            if e_clean and e_clean.lower() not in seen:
                seen.add(e_clean.lower())
                all_terms.append(e_clean)

    return all_terms


async def extract_code_terms(q: str) -> List[str]:
    """
    Use the chat model to extract focused search phrases for code-oriented retrieval.

    The model should:
      - Identify disease/condition phrases (e.g., 'systemic lupus erythematosus',
        'lupus nephritis', 'nephrotic syndrome').
      - Identify procedure phrases (e.g., 'kidney biopsy').
      - Identify lab analytes / test names (e.g., 'protein/creatinine ratio',
        'creatinine', 'complement levels', 'anti-dsDNA').
      - Identify medication names (e.g., 'mycophenolate mofetil', 'prednisone').

    Returns a deduplicated list of short phrases that will be used as TS
    queries across ICD-10-CM, ICD-11, SNOMED CT, LOINC, RxNorm, etc.
    """
    # We reuse CHAT_MODEL so behavior is aligned with the main coding LLM.
    try:
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a medical coding term extractor for a RAG system.\n"
                        "Given a clinical question that asks for ICD-10-CM, ICD-11, "
                        "SNOMED CT, LOINC, and/or RxNorm codes, your job is to output "
                        "a small set of focused search phrases that will be used to "
                        "query each coding vocabulary.\n\n"
                        "Rules:\n"
                        "- Return ONLY a JSON object.\n"
                        "- The JSON MUST have a key 'terms' whose value is a list of strings.\n"
                        "- Each string should be a short, code-like phrase (2–6 words), "
                        "  suitable for text search.\n"
                        "- Include:\n"
                        "    * disease/condition names (e.g., 'systemic lupus erythematosus', "
                        "      'lupus nephritis', 'nephrotic syndrome')\n"
                        "    * relevant organ or syndrome qualifiers when they meaningfully "
                        "      constrain the code (e.g., 'class iv lupus nephritis' is ok, but "
                        "      'biopsy-proven class iv lupus nephritis in an adult' is too long)\n"
                        "    * procedures (e.g., 'kidney biopsy')\n"
                        "    * lab tests/analytes (e.g., 'protein/creatinine ratio', "
                        "      'creatinine', 'complement levels', 'anti-dsDNA')\n"
                        "    * medication names (e.g., 'mycophenolate mofetil', 'prednisone')\n"
                        "- Do NOT include generic context words like 'adult', 'treated', "
                        "  'please provide', 'codes for', etc.\n"
                        "- Aim for roughly 5–20 terms depending on question complexity.\n"
                        "- Avoid duplicates; normalize obvious variants to a single phrase "
                        "  (e.g., prefer 'protein/creatinine ratio' over multiple similar forms).\n"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Clinical question:\n"
                        f"{q.strip()}\n\n"
                        "Respond ONLY with JSON of the form:\n"
                        "{\n"
                        '  \"terms\": [\"term1\", \"term2\", ...]\n'
                        "}\n"
                    ),
                },
            ],
        )
    except Exception as e:
        logger.exception("extract_code_terms: OpenAI chat call failed")
        return []

    # Parse JSON content safely
    try:
        content = resp.choices[0].message.content or ""
    except Exception:
        logger.exception("extract_code_terms: missing message content")
        return []

    try:
        data = json.loads(content)
    except Exception:
        logger.exception("extract_code_terms: JSON parse failed: %r", content[:500])
        return []

    raw_terms = data.get("terms") or data.get("code_terms") or []
    if not isinstance(raw_terms, list):
        logger.warning("extract_code_terms: 'terms' not a list: %r", type(raw_terms))
        return []

    # Clean / normalize / dedupe
    terms_set: set[str] = set()
    for t in raw_terms:
        if not isinstance(t, str):
            continue
        t_clean = t.strip()
        if not t_clean:
            continue
        # Drop very short noise tokens
        if len(t_clean) < 3:
            continue
        # Normalize whitespace
        t_clean = re.sub(r"\s+", " ", t_clean)
        terms_set.add(t_clean)

    terms = sorted(terms_set)
    logger.info("extract_code_terms: %s", terms)
    return terms

def build_llm_messages(
    q: str,
    ctx_str: str,
    coding_mode: bool = False,
) -> List[Dict[str, Any]]:
    """
    Build messages for the chat model.

    - coding_mode=False → general guideline/QA RAG prompt
    - coding_mode=True  → strict coding prompt (only use codes in context,
                          never mix systems, etc.)
    """
    if coding_mode:
        # Extend the base coding system prompt with a few extra guardrails
        system_content = (
            CODING_SYSTEM_PROMPT
            + "\n\n"
            + "Additional guardrails:\n"
            + "- You must only emit codes that appear in the provided context.\n"
            + "- For each vocabulary (ICD-10-CM, ICD-11, SNOMED CT, LOINC, RxNorm), "
            + "  only use codes explicitly labeled for that system in the context.\n"
            + "- If the context clearly contains relevant candidate codes for a requested "
            + "  category (e.g., 'kidney biopsy', 'protein/creatinine ratio', "
            + "  'creatinine', 'complement levels', 'anti-dsDNA', 'mycophenolate ' "
            + "  or 'prednisone'), you must choose one or more of those codes instead "
            + "  of saying that no codes are present.\n"
            + "- If no candidates are present for a requested category, say "
            + "  'none_found' for that category instead of inventing codes.\n"
            + "- Do not substitute across vocabularies (e.g., do not answer a SNOMED CT "
            + "  request with a LOINC code).\n"
            + "- For systemic diseases with organ involvement (for example, lupus nephritis), "
            + "  prefer a combination of a systemic disease code (e.g., SLE) plus an "
            + "  organ/renal code when both are available in the context."
        )

        user_content = (
            "Clinical coding / abstraction request:\n"
            f"{q.strip()}\n\n"
            "Here is the retrieved coding context (codes and related clinical snippets). "
            "Rows are labeled CODE_CONTEXT when they are code systems (ICD-10-CM, ICD-11, "
            "SNOMED CT, LOINC, RxNorm) and CLINICAL_CONTEXT when they are supporting "
            "clinical text:\n\n"
            f"{ctx_str}\n\n"
            "Follow the coding instructions exactly. Use only codes from the context, "
            "and for each requested coding system, either select one or more codes "
            "or explicitly return 'none_found' for that system."
        )

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    # ------------------ non-coding mode (unchanged) -------------------------
    system_content = (
                "You are 2ndOpinionMD's retrieval-augmented medical assistant. "
                "Use ONLY the provided context to answer, citing sections by index "
                "like [1], [2], etc. If the answer is not clearly supported, say "
                "you don't know and suggest follow-up questions or tests."
    )
    return [
        {"role": "system", "content": system_content},
        {
            "role": "user",
            "content": f"Question:\n{q.strip()}",
        },
        {
            "role": "assistant",
            "content": (
                "Here is the retrieved context from medical corpora and guidelines:\n\n"
                f"{ctx_str}\n\n"
                "Now answer the question strictly based on this context."
            ),
        },
    ]

# ---------------------------------------------------------------------------
# MKG + Valyu formatting helpers
# ---------------------------------------------------------------------------


def format_mkg_context(matches: List[Dict[str, Any]]) -> str:
    """
    Render MKG matches into a single context string for the QA model.
    You can adapt this to your existing format (source, title, snippet, score, etc.).
    """
    if not matches:
        return "No internal MKG documents were retrieved."

    lines: List[str] = ["Internal MKG context (guidelines, codes, notes):"]
    for i, m in enumerate(matches, start=1):
        source = m.get("source", "unknown")
        title = m.get("title", "")
        score = m.get("score", None)
        text = m.get("text") or m.get("content") or ""

        header = f"[MKG-{i}] ({source})"
        if title:
            header += f" {title}"
        if score is not None:
            header += f" (score={score:.3f})"

        lines.append("")
        lines.append(header)
        if text:
            lines.append(text[:MAX_CONTEXT_CHARS])

    return "\n".join(lines)


def format_valyu_context(pubs: List[Dict[str, Any]]) -> str:
    """
    Render Valyu publications into a compact context block.

    Expects each pub to be a dict with keys like:
      - title: str | None
      - year: str | int | None
      - journal: str | None
      - authors: list[str] | str | None
      - abstract_snippet: str | None
      - doi: str | None
    """
    if not pubs:
        return "No external Valyu publications were retrieved."

    lines: List[str] = ["External literature (Valyu publications):"]

    for i, p in enumerate(pubs, start=1):
        # Title
        title = (p.get("title") or "").strip()

        # Year / publication date
        year = p.get("year")
        if isinstance(year, (int, float)):
            year_str = str(int(year))
        elif isinstance(year, str):
            year_str = year.strip()
        else:
            year_str = ""

        # Journal / site
        journal_raw = p.get("journal") or ""
        journal = journal_raw.strip() if isinstance(journal_raw, str) else ""

        # Authors can be a list or string depending on Valyu payload
        raw_authors = p.get("authors") or ""
        if isinstance(raw_authors, list):
            authors_list = [a.strip() for a in raw_authors if isinstance(a, str) and a.strip()]
            authors = ", ".join(authors_list)
        elif isinstance(raw_authors, str):
            authors = raw_authors.strip()
        else:
            authors = ""

        # Abstract / snippet
        snippet = (
            p.get("abstract_snippet")
            or p.get("abstract")
            or ""
        )
        if not isinstance(snippet, str):
            snippet = str(snippet or "")

        # DOI
        doi_raw = p.get("doi") or ""
        doi = doi_raw.strip() if isinstance(doi_raw, str) else ""

        header_parts = [f"[VALYU-{i}]"]
        if authors:
            header_parts.append(authors)
        if journal:
            header_parts.append(journal)
        if year_str:
            header_parts.append(year_str)

        lines.append("")
        lines.append(" - ".join(header_parts))

        if title:
            lines.append(f"Title: {title}")

        if snippet:
            # Limit each abstract to avoid blowing up context
            snippet_trunc = snippet[:800]
            lines.append(f"Key findings: {snippet_trunc}")

        if doi:
            lines.append(f"DOI: {doi}")

    return "\n".join(lines)


async def retrieve_valyu_pubs(
    q: str,
    *,
    k: int = 5,
    mode: str = "evidence",
) -> List[Dict[str, Any]]:
    """
    Call Valyu to retrieve top-k publications for the clinical question.

    Returns a list of compact pub dicts consumed by format_valyu_context().
    """
    try:
        resp = await valyu_client.search(
            query=q,
            k=k,
        )
    except Exception:
        logger.exception("retrieve_valyu_pubs: Valyu call failed")
        return []

    raw_results = resp.get("results") or []
    if not isinstance(raw_results, list):
        logger.warning("retrieve_valyu_pubs: unexpected results shape: %r", type(raw_results))
        return []

    pubs: List[Dict[str, Any]] = []
    for item in raw_results:
        # authors may be list or string; keep raw, normalize later in formatter
        pubs.append(
            {
                "title": item.get("title"),
                "year": item.get("publication_date"),  # often YYYY-MM-DD
                "journal": item.get("site"),
                "authors": item.get("authors"),
                "abstract_snippet": item.get("snippet"),
                "doi": item.get("doi"),
            }
        )

    return pubs[:k]


async def retrieve_mkg_matches(
    q: str,
    all_terms: List[str],
    limit: int,
    ctx_k: int,
    pool: asyncpg.Pool,
) -> List[Dict[str, Any]]:
    """
    Wrap your existing ANN + ts + fusion logic.

    This function is a placeholder and should not be used directly.
    Use _event_generator instead which handles retrieval properly.
    """
    # This function is deprecated - use _event_generator instead
    # Returning empty list to avoid errors
    logger.warning("retrieve_mkg_matches is deprecated - use _event_generator instead")
    return []


def stream_llm_events(
    q: str,
    context_items: List[Dict[str, Any]],
    llm_mode: str,
    coding_mode: bool = False,
) -> Iterable[Dict[str, str]]:
    """
    Stream LLM output as SSE events.

    Modes:
      - llm_mode == "delta":
          event: llm_delta  { "text": "<small token-ish piece>" }
      - llm_mode == "chunk" (default):
          event: llm_chunk  { "text": "<sentence-ish chunk>" }

    In BOTH modes, we also emit:
      event: llm_done { "text": "<full answer>" }
    """
    ctx_str = format_context_for_llm(context_items, coding_mode=coding_mode)
    messages = build_llm_messages(q, ctx_str, coding_mode=coding_mode)

    mode = (llm_mode or "chunk").lower()
    if mode not in ("chunk", "delta"):
        mode = "chunk"

    stream = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=messages,
        stream=True,
    )

    full_pieces: List[str] = []
    buf = ""

    def flush_chunk() -> Iterable[Dict[str, str]]:
        nonlocal buf
        text = buf.strip()
        if text:
            yield sse("llm_chunk", {"text": text})
        buf = ""

    for chunk in stream:
        choice = chunk.choices[0]
        delta = choice.delta
        content = getattr(delta, "content", None)
        if not content:
            continue

        # In current OpenAI client, content is usually a string
        if isinstance(content, str):
            text_piece = content
        else:
            # Fallback if content is a list of parts
            text_piece = ""
            try:
                for part in content:
                    part_text = getattr(part, "text", None) or getattr(part, "value", None)
                    if part_text:
                        text_piece += part_text
            except TypeError:
                continue

        if not text_piece:
            continue

        full_pieces.append(text_piece)

        if mode == "delta":
            # Token-ish streaming
            yield sse("llm_delta", {"text": text_piece})
        else:
            # Sentence-ish streaming
            buf += text_piece
            if any(
                buf.endswith(end)
                for end in [". ", ".\n", "?\n", "!\n", ".\n\n"]
            ) or len(buf) > 600:
                for ev in flush_chunk():
                    yield ev

    # Flush any remainder in chunk mode
    if mode == "chunk" and buf.strip():
        for ev in flush_chunk():
            yield ev

    full_text = "".join(full_pieces).strip()
    yield sse("llm_done", {"text": full_text})

def build_fused_context(
    results_by_source: Dict[str, List[Dict[str, Any]]],
    k: int,
    coding_mode: bool = False,
) -> List[Dict[str, Any]]:
    """
    Fuse internal sources for final context using 3 groups, with light pinning.

    In coding_mode:
      - ALL pinned rows are preserved, even if they exceed k.
      - Non-pinned rows are still limited by k (for guidelines/rest).
      - Final truncation happens by MAX_CONTEXT_CHARS in format_context_for_llm.

    In non-coding mode:
      - Behavior is unchanged: pinned rows get priority, but global k still applies.
    """
    if not results_by_source:
        return []

    # Effective cap: in coding_mode, allow many more rows; rely on char limit later.
    if coding_mode:
        k_effective = max(k, 10_000)
    else:
        k_effective = k

    # ---------- 1) Flatten + gather pinned rows ----------------------------
    all_rows: List[Dict[str, Any]] = []
    for rows in results_by_source.values():
        all_rows.extend(rows)

    pinned_rows = [r for r in all_rows if r.get("pinned")]
    non_pinned_rows = [r for r in all_rows if not r.get("pinned")]

    def _sort_by_score(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            rows,
            key=lambda r: float(r.get("score", 0.0) or 0.0),
            reverse=True,
        )

    pinned_code: List[Dict[str, Any]] = []
    pinned_guideline: List[Dict[str, Any]] = []
    pinned_rest: List[Dict[str, Any]] = []

    for r in pinned_rows:
        src = r.get("source") or ""
        kind = _classify_internal_source(src)
        if kind == "code":
            pinned_code.append(r)
        elif kind == "guideline":
            pinned_guideline.append(r)
        else:
            pinned_rest.append(r)

    pinned_ordered: List[Dict[str, Any]] = (
        _sort_by_score(pinned_code)
        + _sort_by_score(pinned_guideline)
        + _sort_by_score(pinned_rest)
    )

    # ---------- 2) Rebuild results_by_source without pinned rows -----------
    remaining_by_source: Dict[str, List[Dict[str, Any]]] = {}
    for src, rows in results_by_source.items():
        remaining = [r for r in rows if not r.get("pinned")]
        if remaining:
            remaining_by_source[src] = remaining

    # ---------- 3) Legacy group fusion on non-pinned rows ------------------
    if not remaining_by_source:
        # All rows were pinned; DO NOT truncate in coding_mode.
        final: List[Dict[str, Any]] = []
        seen: set[Tuple[str, Any]] = set()
        for r in pinned_ordered:
            key = ((r.get("source") or ""), r.get("id"))
            if key in seen:
                continue
            seen.add(key)
            final.append(r)
            if not coding_mode and len(final) >= k_effective:
                break

        code_ct = sum(
            1 for r in final
            if _classify_internal_source(r.get("source") or "") == "code"
        )
        guide_ct = sum(
            1 for r in final
            if _classify_internal_source(r.get("source") or "") == "guideline"
        )
        rest_ct = len(final) - code_ct - guide_ct

        logger.info(
            "FUSED_CONTEXT sizes (all_pinned): codes=%d, guidelines=%d, rest=%d, total=%d (coding_mode=%s)",
            code_ct,
            guide_ct,
            rest_ct,
            len(final),
            coding_mode,
        )
        return final

    code_by_source: Dict[str, List[Dict[str, Any]]] = {}
    guideline_by_source: Dict[str, List[Dict[str, Any]]] = {}
    rest_by_source: Dict[str, List[Dict[str, Any]]] = {}

    for src, rows in remaining_by_source.items():
        kind = _classify_internal_source(src)
        if kind == "code":
            code_by_source[src] = rows
        elif kind == "guideline":
            guideline_by_source[src] = rows
        else:
            rest_by_source[src] = rows

    k_codes = max(0, CODE_K_DEFAULT)
    k_guidelines = max(0, GUIDE_K_DEFAULT)
    k_rest = max(0, k_effective)

    fused_codes: List[Dict[str, Any]] = []
    fused_guidelines: List[Dict[str, Any]] = []
    fused_rest: List[Dict[str, Any]] = []

    # --- CODE GROUP --------------------------------------------------------
    if USE_CODE_SOURCES and code_by_source:
        if coding_mode:
            per_source_rows: List[Dict[str, Any]] = []
            for src, rows in code_by_source.items():
                src_norm = (src or "").lower()
                src_rows = sorted(
                    rows,
                    key=lambda r: float(r.get("score", 0.0) or 0.0),
                    reverse=True,
                )
                min_keep = CODE_MIN_PER_SOURCE_CTX.get(src_norm, 0)
                keep_n = min(len(src_rows), CODE_MAX_PER_SOURCE_CTX)
                keep_n = max(min_keep, keep_n)
                if keep_n <= 0:
                    continue
                per_source_rows.extend(src_rows[:keep_n])

            if per_source_rows:
                per_source_rows.sort(
                    key=lambda r: float(r.get("score", 0.0) or 0.0),
                    reverse=True,
                )
                # In coding_mode we do NOT hard-cap by k_effective; we keep all these.
                fused_codes = per_source_rows
            else:
                fused_codes = []
        else:
            fused_codes = rrf_fuse(code_by_source, k=k_codes)

    # --- GUIDELINE GROUP ---------------------------------------------------
    if USE_GUIDELINE_SOURCES and guideline_by_source:
        fused_guidelines = rrf_fuse(guideline_by_source, k=k_guidelines)

    # --- REST GROUP --------------------------------------------------------
    if USE_REST_SOURCES and rest_by_source and k_rest > 0:
        fused_rest = rrf_fuse(rest_by_source, k=k_rest)

    fused_non_pinned = fused_codes + fused_guidelines + fused_rest

    # ---------- 4) Combine pinned + non-pinned, dedupe, truncate -----------
    final: List[Dict[str, Any]] = []
    seen: set[Tuple[str, Any]] = set()

    # 4a) First, add ALL pinned rows (no cap in coding_mode)
    for r in pinned_ordered:
        key = ((r.get("source") or ""), r.get("id"))
        if key in seen:
            continue
        seen.add(key)
        final.append(r)
        # In non-coding mode, we still respect k_effective
        if not coding_mode and len(final) >= k_effective:
            break

    # 4b) Add non-pinned rows — but NEVER remove pinned rows
    for r in fused_non_pinned:
        key = ((r.get("source") or ""), r.get("id"))
        if key in seen:
            continue
        seen.add(key)
        final.append(r)
        if not coding_mode and len(final) >= k_effective:
            break

    code_ct = sum(
        1 for r in final
        if _classify_internal_source(r.get("source") or "") == "code"
    )
    guide_ct = sum(
        1 for r in final
        if _classify_internal_source(r.get("source") or "") == "guideline"
    )
    rest_ct = len(final) - code_ct - guide_ct
    pinned_ct = sum(1 for r in final if r.get("pinned"))

    logger.info(
        "FUSED_CONTEXT sizes: codes=%d, guidelines=%d, rest=%d, total=%d, pinned=%d (coding_mode=%s)",
        code_ct,
        guide_ct,
        rest_ct,
        len(final),
        pinned_ct,
        coding_mode,
    )

    return final


# ---------------------------------------------------------------------------
# Citations helpers
# ---------------------------------------------------------------------------


def _classify_citation_kind(row: Dict[str, Any]) -> str:
    """
    Classify a context row into a citation kind:
      - 'valyu'     : Valyu PubMed-style hits
      - 'ethos'     : Ethos of Health model / preprint chunks
      - 'guideline' : everything else (guidelines, codes, ontologies, etc.)
    """
    source = (row.get("source") or "").lower()
    method = (row.get("method") or "").lower()

    if source.startswith("valyu") or method == "valyu":
        return "valyu"
    if source in {"ethos_model", "ethos"}:
        return "ethos"
    return "guideline"


def build_citations(context_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Build a citations list from the final context:

    - Each context block [i] becomes a citation with index = i.
    - Valyu citations are grouped first, then Ethos, then guidelines/other.
    - `extra.meta` carries through the row's meta so codes/etc. can be surfaced
      by the UI or report generator.
    """
    raw_citations: List[Dict[str, Any]] = []

    for i, row in enumerate(context_items, start=1):
        kind = _classify_citation_kind(row)
        src = row.get("source", "unknown")
        meta = row.get("meta") or {}
        method = row.get("method")

        if kind == "valyu":
            key = (
                meta.get("pmcid")
                or meta.get("pmid")
                or meta.get("pubmed_id")
                or meta.get("id")
                or row.get("id")
            )
        elif kind == "ethos":
            key = f"{src}:{row.get('id')}"
        else:
            key = f"{src}:{row.get('id')}"

        raw_citations.append(
            {
                "index": i,
                "kind": kind,
                "source": src,
                "key": str(key),
                "title": row.get("title") or "",
                "extra": {
                    "method": method,
                    "meta": meta,
                },
            }
        )

    kind_order = {"valyu": 0, "ethos": 1, "guideline": 2}
    raw_citations.sort(key=lambda c: (kind_order.get(c["kind"], 99), c["index"]))
    return raw_citations


# ---------------------------------------------------------------------------
# SSE helper
# ---------------------------------------------------------------------------


def sse(event: str, payload: Dict[str, Any]) -> Dict[str, str]:
    """
    Format a Server-Sent Event (SSE) message as a dict that sse_starlette understands.
    """
    return {
        "event": event,
        "data": json.dumps(payload, default=str),
    }


# ---------------------------------------------------------------------------
# Core event generator (used by /ask_stream and /coding_stream)
# ---------------------------------------------------------------------------


async def _event_generator(
    request: Request,
    q: str,
    db_sources: List[str],
    limit: int,
    ctx_k: int,
    valyu_k: int,
    with_llm: bool,
    llm_mode: str,
    use_valyu_bool: bool,
    valyu_mode: str,
    valyu_raw_bool: bool,
    valyu_sources: Optional[str],
    valyu_boost: float,
    pool: Any,
    coding_mode: bool = False,
    use_ethos_bool: bool = False,
) -> AsyncIterator[Dict[str, str]]:
    # Hard cap on Valyu context size
    VALYU_K_MAX = 4
    requested_valyu_k = valyu_k
    valyu_k = max(0, min(valyu_k, VALYU_K_MAX))

    # 0) Initial event
    yield sse(
        "start",
        {
            "q": q,
            "limit": limit,
            "ctx_k": ctx_k,
            "sources": db_sources,
            "with_llm": with_llm,
            "use_valyu": use_valyu_bool,
            "valyu_k": valyu_k,
            "valyu_k_requested": requested_valyu_k,
            "use_ethos": use_ethos_bool,
        },
    )

    # 0.1) Soft warnings
    warnings: List[str] = []
    if len(db_sources) > 8:
        warnings.append(
            f"High number of sources requested ({len(db_sources)}). "
            "This may dilute relevance; consider narrowing the 'sources=' list."
        )
    if limit > 15:
        warnings.append(
            f"High per-source limit={limit}. This may increase noise; "
            "consider a smaller 'limit' for sharper focus."
        )
    if warnings:
        yield sse("warning", {"messages": warnings})

    if await request.is_disconnected():
        return

    # 1) Embed query (ALWAYS)
    yield sse("status", {"status": "embedding_query"})
    try:
        q_emb = await embed_query(q)
        q_vec_literal = embedding_to_vector_literal(q_emb)
    except Exception as e:
        logger.exception("Error embedding query")
        yield sse(
            "error",
            {"error": "embedding_failed", "detail": str(e)},
        )
        return

    if await request.is_disconnected():
        return

    # 1.1) Extract code-oriented terms (status always, actual work only in coding_mode)
    code_terms: List[str] = []
    yield sse("status", {"status": "extracting_code_terms"})
    if coding_mode:
        try:
            code_terms = await extract_code_terms(q)
            yield sse("code_terms", {"terms": code_terms})
        except Exception as e:
            logger.exception("extract_code_terms crashed; continuing without code_terms")
            yield sse(
                "code_terms",
                {
                    "terms": [],
                    "error": "code_term_extraction_failed",
                    "detail": str(e),
                },
            )
            code_terms = []
    else:
        # Non-coding path: keep the trace shape but don't actually use code_terms.
        yield sse("code_terms", {"terms": []})

    if await request.is_disconnected():
        return

    # -----------------------------------------------------------------------
    # 1.2) EARLY Valyu fetch (NON-CODING ONLY) — SINGLE API CALL
    # -----------------------------------------------------------------------
    valyu_matches: List[Dict[str, Any]] = []

    if (not coding_mode) and use_valyu_bool and valyu_k > 0:
        yield sse("status", {"status": "valyu_fetch"})
        try:
            # Single Valyu call for this query
            valyu_by_source = await fetch_valyu_results(
                q=q,
                mode=valyu_mode,
                limit=valyu_k,
                raw=valyu_raw_bool,
                sources=valyu_sources,
                boost=valyu_boost,
            )
        except Exception as e:
            logger.exception("Valyu fetch failed")
            yield sse(
                "status",
                {"status": "valyu_error", "detail": str(e)},
            )
            valyu_by_source = {}

        # Flatten for SSE + routing + final tail
        flat_valyu: List[Dict[str, Any]] = []
        for v_src, rows in (valyu_by_source or {}).items():
            flat_valyu.extend(rows)

        # SSE: expose Valyu matches immediately
        if flat_valyu:
            valyu_matches = flat_valyu[:valyu_k]
            yield sse(
                "matches",
                {
                    "phase": "valyu",
                    "source": "valyu",
                    "matches": [
                        {
                            "id": r["id"],
                            "source": r["source"],
                            "title": r.get("title", ""),
                            "score": r.get("score", 0.0),
                            "method": r.get("method", "valyu"),
                        }
                        for r in valyu_matches
                    ],
                },
            )

    if await request.is_disconnected():
        return

    # -----------------------------------------------------------------------
    # 1.3) Routing (single pass, Valyu-aware in non-coding mode)
    # -----------------------------------------------------------------------
    router_plan: CodingRouterPlan | None = None
    effective_sources: List[str] = list(db_sources)

    yield sse("status", {"status": "routing_sources"})

    try:
        router_plan = await route_coding_sources(
            q=q,
            code_terms=code_terms if coding_mode else [],
            candidate_sources=db_sources,
            # Non-coding mode: let router see Valyu context to bias guidelines
            valyu_context=(valyu_matches if (not coding_mode and valyu_matches) else None),
        )
    except Exception as e:
        logger.exception("route_coding_sources failed; using all db_sources")
        router_plan = None

    if router_plan and router_plan.selected_sources:
        effective_sources = sorted(router_plan.selected_sources)
    else:
        effective_sources = list(db_sources)

    if router_plan is not None:
        yield sse(
            "router",
            {
                "task_type": router_plan.task_type,
                "selected_sources": effective_sources,
                "reasoning": router_plan.reasoning,
            },
        )

    if await request.is_disconnected():
        return

    yield sse(
        "event_router_summary",
        {
            "mode": "coding" if coding_mode else "ask_stream",
            "using_router": router_plan is not None,
            "effective_sources": effective_sources,
        },
    )

    # -----------------------------------------------------------------------
    # 2) Retrieve per source (TS + ANN)
    # -----------------------------------------------------------------------
    yield sse("status", {"status": "retrieving_candidates"})
    results_by_source: Dict[str, List[Dict[str, Any]]] = {}

    for src in effective_sources:
        # Deeper retrieval for code sources in coding_mode
        per_source_limit = limit
        if coding_mode and src in CODING_SOURCES:
            per_source_limit = max(limit, CODE_MIN_LIMIT)

        ts_rows: List[Dict[str, Any]] = []
        ann_rows: List[Dict[str, Any]] = []

        # TS phase
        yield sse("phase_start", {"source": src, "method": "ts"})
        try:
            if coding_mode and src in CODING_SOURCES:
                if code_terms:
                    ts_rows = await search_source_ts_for_terms(
                        pool,
                        source=src,
                        terms=code_terms,
                        limit=per_source_limit,
                    )
                else:
                    ts_rows = await search_source_ts(pool, src, q, per_source_limit)
            else:
                ts_rows = await search_source_ts(pool, src, q, per_source_limit)
        except Exception as e:
            logger.exception("TS search failed for source=%s", src)
            yield sse(
                "status",
                {"status": "ts_error", "source": src, "detail": str(e)},
            )
            ts_rows = []

        yield sse("phase_end", {"source": src, "method": "ts"})

        if ts_rows:
            yield sse(
                "matches",
                {
                    "phase": "ts",
                    "source": src,
                    "matches": [
                        {
                            "id": r["id"],
                            "source": r["source"],
                            "source_id": r.get("source_id") or "",
                            "title": r.get("title", ""),
                            "score": r.get("score", 0.0),
                            "method": r.get("method", "ts"),
                        }
                        for r in ts_rows
                    ],
                },
            )

        if await request.is_disconnected():
            return

        # ANN phase
        yield sse("phase_start", {"source": src, "method": "ann"})
        try:
            ann_rows = await search_source_ann(pool, src, q_vec_literal, per_source_limit)
        except Exception as e:
            logger.exception("ANN search failed for source=%s", src)
            yield sse(
                "status",
                {"status": "ann_error", "source": src, "detail": str(e)},
            )
            ann_rows = []
        yield sse("phase_end", {"source": src, "method": "ann"})

        if ann_rows:
            yield sse(
                "matches",
                {
                    "phase": "ann",
                    "source": src,
                    "matches": [
                        {
                            "id": r["id"],
                            "source": r["source"],
                            "source_id": r.get("source_id"),
                            "title": r.get("title", ""),
                            "score": r.get("score", 0.0),
                            "method": r.get("method", "ann"),
                        }
                        for r in ann_rows
                    ],
                },
            )

        if await request.is_disconnected():
            return

        # Combine TS + ANN (normalized)
        combined: Dict[Any, Dict[str, Any]] = {}
        for r in ts_rows + ann_rows:
            norm = normalize_row(r, source=src)
            combined[norm["id"]] = norm

        combined_rows = list(combined.values())

        # Extra de-noising for code sources in coding mode
        if coding_mode:
            combined_rows = apply_code_row_filter(combined_rows, q, src)

        results_by_source[src] = combined_rows

    # -----------------------------------------------------------------------
    # 3) Coding prepass (if coding_mode)
    # -----------------------------------------------------------------------
    if coding_mode:
        # PASS 1: Build ledger and run grader
        ledger1 = build_coding_ledger(results_by_source)
        ledger1_summary = summarize_coding_ledger(ledger1)
        yield sse(
            "coding_ledger",
            {
                "pass": 1,
                "summary": ledger1_summary,
            },
        )

        if await request.is_disconnected():
            return

        grader1 = await run_coding_grader(q, ledger1, pass_id=1)
        keep1 = grader1.get("keep") or {}
        missing1 = grader1.get("missing_slots") or []

        yield sse(
            "coding_grader",
            {
                "pass": 1,
                "keep_map": keep1,
                "missing_slots": missing1,
            },
        )

        if await request.is_disconnected():
            return

        # If we have missing slots, run a targeted gap-retrieval pass
        if missing1:
            yield sse(
                "status",
                {"status": "coding_gap_retrieval"},
            )

            results_by_source = await fill_coding_gaps(
                q=q,
                missing_slots=missing1,
                results_by_source=results_by_source,
                pool=pool,
                per_slot_limit=max(limit, 16),
            )

            # Emit a summary after gap retrieval
            ledger_gap = build_coding_ledger(results_by_source)
            ledger_gap_summary = summarize_coding_ledger(ledger_gap)
            yield sse(
                "coding_gap_retrieval",
                {
                    "missing_slots": missing1,
                    "post_gap_summary": ledger_gap_summary,
                },
            )

            if await request.is_disconnected():
                return

        # PASS 2: Rebuild ledger and run grader again over enriched codes
        ledger2 = build_coding_ledger(results_by_source)
        ledger2_summary = summarize_coding_ledger(ledger2)
        yield sse(
            "coding_ledger",
            {
                "pass": 2,
                "summary": ledger2_summary,
            },
        )

        if await request.is_disconnected():
            return

        grader2 = await run_coding_grader(q, ledger2, pass_id=2)
        keep2 = grader2.get("keep") or {}
        missing2 = grader2.get("missing_slots") or []

        yield sse(
            "coding_grader",
            {
                "pass": 2,
                "keep_map": keep2,
                "missing_slots": missing2,
            },
        )

        if await request.is_disconnected():
            return

        # Pin all rows selected by the second grader.
        pinned_counts = pin_coding_rows_from_keep_map(results_by_source, keep2)
        yield sse(
            "coding_pinned",
            {
                "pinned_counts": pinned_counts,
                "note": (
                    "All pinned codes from pass=2 are guaranteed to survive "
                    "fusion in coding_mode (subject only to MAX_CONTEXT_CHARS "
                    "later in format_context_for_llm)."
                ),
            },
        )

        if await request.is_disconnected():
            return

    raw_source_count = len(results_by_source)

    # -----------------------------------------------------------------------
    # 4) Heuristic source gating, with optional Ethos + Code force-keep.
    # -----------------------------------------------------------------------
    extra_always_keep: Optional[set[str]] = None
    if use_ethos_bool:
        extra_always_keep = {ETHOS_SOURCE_NAME}

    if coding_mode:
        code_keep = set(CODING_SOURCES)
        if extra_always_keep is None:
            extra_always_keep = code_keep
        else:
            extra_always_keep |= code_keep

    gated_results_by_source, gating_info = apply_source_gating(
        results_by_source,
        query=q,
        extra_always_keep=extra_always_keep,
        coding_mode=coding_mode,
        ctx_k=ctx_k,
    )

    yield sse("gating", gating_info)

    if await request.is_disconnected():
        return

    # -----------------------------------------------------------------------
    # 5) Fuse internal contexts and append Valyu tail (from EARLY fetch)
    # -----------------------------------------------------------------------
    yield sse("status", {"status": "fusing_context"})

    internal_ctx = build_fused_context(
        gated_results_by_source,
        k=ctx_k,
        coding_mode=coding_mode,
    )

    # Valyu tail: reuse EARLY results; NO second Valyu API call
    if (not coding_mode) and use_valyu_bool and valyu_k > 0 and valyu_matches:
        valyu_tail = valyu_matches[:valyu_k]
    else:
        valyu_tail = []

    final_ctx = internal_ctx + valyu_tail
    valyu_ctx_count = len(valyu_tail)

    yield sse(
        "matches",
        {
            "phase": "fused",
            "source": "fused",
            "matches": [
                {
                    "id": r["id"],
                    "source": r["source"],
                    "source_id": r.get("source_id"),
                    "title": r.get("title", ""),
                    "score": r.get("score", 0.0),
                    "method": r.get("method", None),
                }
                for r in final_ctx
            ],
        },
    )

    if await request.is_disconnected():
        return

    citations = build_citations(final_ctx)

    # -----------------------------------------------------------------------
    # 6) with_llm == 0 → just metadata
    # -----------------------------------------------------------------------
    if not with_llm:
        yield sse("status", {"status": "done_no_llm"})
        yield sse("citations", {"citations": citations})
        yield sse(
            "end",
            {
                "meta": {
                    "n_sources_raw": raw_source_count,
                    "n_sources": len(gated_results_by_source),
                    "n_ctx_internal": len(internal_ctx),
                    "n_ctx_valyu": valyu_ctx_count,
                    "n_ctx_total": len(final_ctx),
                    "ctx_k": ctx_k,
                    "valyu_k": valyu_k,
                    "with_llm": with_llm,
                    "use_ethos": use_ethos_bool,
                }
            },
        )
        return

    if not final_ctx:
        yield sse("status", {"status": "done_no_llm"})
        yield sse("citations", {"citations": []})
        yield sse(
            "end",
            {
                "meta": {
                    "n_sources_raw": raw_source_count,
                    "n_sources": len(gated_results_by_source),
                    "n_ctx_internal": 0,
                    "n_ctx_valyu": 0,
                    "n_ctx_total": 0,
                    "ctx_k": ctx_k,
                    "valyu_k": valyu_k,
                    "with_llm": with_llm,
                    "use_ethos": use_ethos_bool,
                }
            },
        )
        return

    # -----------------------------------------------------------------------
    # 7) LLM streaming
    # -----------------------------------------------------------------------
    yield sse("phase_start", {"source": "fusion", "method": "llm"})
    yield sse("status", {"status": "generating_answer"})

    try:
        for ev in stream_llm_events(q, final_ctx, llm_mode, coding_mode=coding_mode):
            if await request.is_disconnected():
                return
            yield ev
    except Exception as e:
        logger.exception("Error during LLM streaming")
        yield sse(
            "error",
            {"error": "llm_failed", "detail": str(e)},
        )

    yield sse("phase_end", {"source": "fusion", "method": "llm"})
    yield sse("citations", {"citations": citations})
    yield sse(
        "end",
        {
            "meta": {
                "n_sources_raw": raw_source_count,
                "n_sources": len(gated_results_by_source),
                "n_ctx_internal": len(internal_ctx),
                "n_ctx_valyu": valyu_ctx_count,
                "n_ctx_total": len(final_ctx),
                "ctx_k": ctx_k,
                "valyu_k": valyu_k,
                "with_llm": with_llm,
                "use_ethos": use_ethos_bool,
            }
        },
    )
    