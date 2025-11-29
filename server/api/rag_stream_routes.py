# server/api/rag_stream_routes.py

import asyncio
import json
import logging
import os
from typing import Any, AsyncIterator, Dict, Iterable, List, Optional, Tuple, Set
from dataclasses import dataclass
import re
import difflib

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
    GUIDELINE_SOURCES,
    MAX_CONTEXT_CHARS,
    ETHOS_SOURCE_NAME,
    EOH_SYSTEM_PROMPT,
    CODING_GRADER_SYSTEM_PROMPT,
    CODING_USER_PROMPT_TEMPLATE,
)

from .stream_gating import apply_code_row_filter, apply_source_gating
from .stream_router import route_coding_sources, CodingRouterPlan

# Minimum per-source retrieval depth for code sources in coding_mode.
# If the incoming `limit` is smaller than this, code sources will use this instead.
CODE_MIN_LIMIT = int(os.getenv("CODE_MIN_LIMIT", "32"))

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/rag", tags=["rag-stream"])

client = OpenAI(timeout=60.0)

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

_GUIDELINE_EXACT = {
    "acr_ra_2021",
    "acr_ild_2023",
    "eular_ra_2022",
    "va_guidelines",
    "nice",
    "who_eml",
    "who_committee",
}

_GUIDELINE_PREFIXES = (
    "acr_",
    "eular_",
    "nice_",
    "who_",
    "guideline_",
    "esmo_",
    "kdigo_",
)

# ---------------------------------------------------------------------------
# Generic concept similarity helpers for slot satisfaction
# ---------------------------------------------------------------------------

# Very small, generic stopword list – *not* disease-specific.
_CONCEPT_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "in", "on", "with", "without",
    "to", "for", "by", "at", "from", "using", "use", "via", "as", "is",
    "are", "be", "being", "been", "versus", "vs", "vs.",
}


def _concept_tokens(text: str) -> set[str]:
    """
    Normalize a short clinical phrase into a set of "meaningful" tokens.

    - Lowercase
    - Strip punctuation
    - Remove very short tokens / obvious stopwords
    - No disease-class-specific specials (pure lexical).
    """
    if not text:
        return set()

    text = text.lower()
    # Split on non-alphanumeric
    raw = re.split(r"[^a-z0-9]+", text)
    out: set[str] = set()
    for tok in raw:
        tok = tok.strip()
        if not tok:
            continue
        if tok in _CONCEPT_STOPWORDS:
            continue
        if len(tok) <= 2:
            continue
        out.add(tok)
    return out


def _concept_similarity(
    slot_label: str,
    title: str,
    search_terms: list[str] | None = None,
) -> float:
    """
    Compute a coarse "concept similarity" score between a missing-slot label
    (plus optional search terms) and a ledger code title.

    This is intentionally generic and disease-agnostic:
      - token overlap
      - plus a loose SequenceMatcher ratio

    Returns a float in [0, 1]; higher = more similar.
    """
    slot_tokens = _concept_tokens(slot_label)
    if search_terms:
        for t in search_terms:
            slot_tokens |= _concept_tokens(t)

    title_tokens = _concept_tokens(title)

    if not slot_tokens or not title_tokens:
        return 0.0

    overlap = slot_tokens & title_tokens
    union = slot_tokens | title_tokens

    # Basic Jaccard
    jaccard = len(overlap) / max(1, len(union))

    # Sequence-based similarity on raw strings (helps with acronyms, etc.)
    ratio = difflib.SequenceMatcher(
        None,
        slot_label.lower(),
        title.lower(),
    ).ratio()

    # Combine with a simple weighted average
    # (tuneable; keep it simple and transparent)
    sim = 0.6 * jaccard + 0.4 * ratio
    return sim


def _norm_term_key(t: str) -> str:
    """Normalize a term for dictionary lookup."""
    return re.sub(r"\s+", " ", t.strip().lower())


# ICD-10–oriented phrase-level synonyms.
# Keys and values should be *normalized phrases* (lowercase, no weird spacing),
# aiming to bridge natural-language → ICD-10-CM wording.
ICD10_SYNONYM_MAP: Dict[str, List[str]] = {
    # Abscess / intra-abdominal
    "pelvic abscess": [
        "peritoneal abscess",
        "intra-abdominal abscess",
        "intraperitoneal abscess",
    ],
    "pelvic fluid collection": [
        "peritoneal abscess",
        "intra-abdominal abscess",
    ],
    "intraabdominal abscess": [
        "intra-abdominal abscess",
        "peritoneal abscess",
    ],

    # Cardiovascular
    "heart attack": [
        "acute myocardial infarction",
        "myocardial infarction",
        "ami",
        "stemi",
        "nstemi",
    ],
    "stemi": [
        "acute myocardial infarction",
        "myocardial infarction",
    ],
    "nstemi": [
        "acute myocardial infarction",
        "myocardial infarction",
    ],
    "chf": [
        "congestive heart failure",
        "heart failure",
    ],
    "congestive heart failure": [
        "heart failure",
    ],
    "blood clot in leg": [
        "deep vein thrombosis",
        "venous thrombosis",
    ],
    "dvt": [
        "deep vein thrombosis",
    ],
    "pe": [
        "pulmonary embolism",
        "pulmonary thromboembolism",
    ],
    "lung clot": [
        "pulmonary embolism",
    ],

    # Diabetes
    "type 2 diabetes": [
        "diabetes mellitus type 2",
        "type ii diabetes mellitus",
        "t2dm",
    ],
    "type 1 diabetes": [
        "diabetes mellitus type 1",
        "type i diabetes mellitus",
        "t1dm",
    ],
    "diabetic ketoacidosis": [
        "dka",
    ],

    # Renal
    "kidney failure": [
        "renal failure",
        "acute renal failure",
        "acute kidney failure",
    ],
    "chronic kidney disease": [
        "chronic renal failure",
        "chronic renal insufficiency",
        "ckd",
    ],
    "end stage renal disease": [
        "end-stage renal disease",
        "esrd",
    ],
    "esrd": [
        "end-stage renal disease",
        "chronic kidney disease",
    ],

    # Infection / sepsis
    "uti": [
        "urinary tract infection",
    ],
    "urine infection": [
        "urinary tract infection",
    ],
    "bladder infection": [
        "cystitis",
        "urinary tract infection",
    ],
    "urosepsis": [
        "sepsis",
        "septicemia",
    ],
    "septicemia": [
        "sepsis",
    ],
    "blood infection": [
        "sepsis",
        "septicemia",
    ],

    # Respiratory
    "pna": [
        "pneumonia",
    ],
    "lung infection": [
        "pneumonia",
    ],
    "chest infection": [
        "pneumonia",
    ],

    # Neuro
    "stroke": [
        "cerebrovascular accident",
        "cva",
        "cerebral infarction",
    ],
    "cva": [
        "cerebrovascular accident",
        "cerebral infarction",
    ],
}


# Generic short-hand → long medical phrases that are often useful across codes
GENERIC_MED_SYNONYM_MAP: Dict[str, List[str]] = {
    "htn": ["hypertension", "high blood pressure"],
    "high blood pressure": ["hypertension"],
    "afib": ["atrial fibrillation"],
    "mi": ["myocardial infarction", "acute myocardial infarction"],
    "copd": ["chronic obstructive pulmonary disease"],
    "rhf": ["right heart failure"],
    "lhf": ["left heart failure"],
    "ckd": ["chronic kidney disease"],
}


def _find_semantic_matches_for_slot(
    slot: dict,
    ledger_items: list[dict],
    *,
    min_similarity: float = 0.35,
    max_codes: int = 6,
) -> set[str]:
    """
    Given a single missing slot and all ledger items for its vocabulary,
    return a set of codes that are *conceptually close enough* to treat
    this slot as satisfied.

    - Uses only lexical similarity; no disease-class hardcoding.
    - If no items clear the min_similarity threshold, returns empty set.
    """
    label = str(slot.get("slot_label", "") or "")
    terms = slot.get("search_terms") or []
    search_terms: list[str] = []
    if isinstance(terms, list):
        for t in terms:
            if isinstance(t, str) and t.strip():
                search_terms.append(t.strip())

    satisfied_codes: set[str] = set()
    if not ledger_items or not label.strip():
        return satisfied_codes

    for item in ledger_items:
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        title = str(item.get("title") or "").strip()
        if not title:
            continue

        sim = _concept_similarity(label, title, search_terms)
        if sim < min_similarity:
            continue

        satisfied_codes.add(code)
        if len(satisfied_codes) >= max_codes:
            break

    return satisfied_codes

# ---------------------------------------------------------------------------
# Slot satisfaction heuristics for coding
# ---------------------------------------------------------------------------

# Small curated rules for treating some "missing_slots" as satisfied when
# the ledger already contains obviously correct codes (especially LOINC
# labs and RxNorm meds).
#
# This is deliberately narrow and easy to audit.
SLOT_SATISFACTION_RULES: dict[str, list[dict[str, Any]]] = {
    "loinc": [
        {
            # Urine albumin/creatinine ratio (UACR) – HEDIS & typical LOINCs
            "slot_regex": re.compile(
                r"(urine\s+albumin.*creatinine|albumin/creatinine\s+ratio|uacr)",
                re.IGNORECASE,
            ),
            "title_substrings": [
                "albumin/creat",
                "alb/creat",
                "microalbumin/creat",
            ],
            # Max codes we'll accept for this slot to keep things tidy
            "max_codes": 4,
        },
        {
            # Basic metabolic panel / BMP / Chem-7
            "slot_regex": re.compile(
                r"(basic\s+metabolic\s+panel|\bBMP\b|chem[-\s]?7)",
                re.IGNORECASE,
            ),
            "title_substrings": [
                "basic metabolic panel",
                "bas metab pnl",
                "metabolic panel",
            ],
            "max_codes": 3,
        },
    ],
    "rxnorm": [
        {
            # Metformin oral meds
            "slot_regex": re.compile(r"\bmetformin\b", re.IGNORECASE),
            "title_substrings": [
                "metformin",
            ],
            "max_codes": 6,
        }
    ],
}


def _apply_slot_satisfaction_heuristics(
    *,
    ledger: Dict[str, Any],
    keep_map: Dict[str, List[str]],
    missing_slots: List[Dict[str, Any]],
) -> tuple[Dict[str, List[str]], List[Dict[str, Any]]]:
    """
    Heuristically treat some 'missing_slots' as satisfied when the ledger
    already contains codes that are *conceptually very close* to the slot.

    Two layers, both vocabulary-agnostic wrt disease class:

      1) Generic semantic similarity
         - Compare slot_label + search_terms to ledger titles for that vocab.
         - If similarity is high enough, we:
             * add those codes to keep_map[vocab]
             * drop the slot from missing_slots

      2) Optional narrow rules in SLOT_SATISFACTION_RULES
         - For things like lab panels / drug names with very consistent titles
           (e.g., UACR, BMP, metformin).
         - Still not tied to a specific disease (RA, lupus, etc.).

    Returns:
      (new_keep_map, new_missing_slots)
    """
    sources = (ledger.get("sources") or {}) if isinstance(ledger, dict) else {}

    # Normalize keep_map into mutable sets per vocab
    norm_keep: dict[str, set[str]] = {}
    for src, codes in (keep_map or {}).items():
        if not isinstance(codes, list):
            continue
        src_norm = str(src).lower()
        bucket = norm_keep.setdefault(src_norm, set())
        for c in codes:
            if not isinstance(c, str):
                continue
            c_clean = c.strip()
            if c_clean:
                bucket.add(c_clean)

    new_missing: List[Dict[str, Any]] = []

    for slot in missing_slots or []:
        if not isinstance(slot, dict):
            new_missing.append(slot)
            continue

        vocab = str(slot.get("vocabulary", "")).lower().strip()
        label = str(slot.get("slot_label", "")).strip()
        if not vocab or not label:
            new_missing.append(slot)
            continue

        ledger_items = sources.get(vocab) or []
        if not isinstance(ledger_items, list) or not ledger_items:
            new_missing.append(slot)
            continue

        # -------------------------------------------------------------------
        # 1) Generic concept similarity: disease-agnostic and vocabulary-agnostic.
        #    If the ledger already has codes whose titles are conceptually close
        #    to this slot_label, treat the slot as satisfied.
        # -------------------------------------------------------------------
        generic_matches = _find_semantic_matches_for_slot(
            slot,
            ledger_items,
            min_similarity=0.35,  # tuneable threshold
            max_codes=6,
        )

        # -------------------------------------------------------------------
        # 2) Optional narrow per-vocab rules (e.g., UACR, BMP, metformin).
        #    These are still not tied to a specific disease class.
        # -------------------------------------------------------------------
        rule_matches: set[str] = set()
        rules = SLOT_SATISFACTION_RULES.get(vocab)
        if rules:
            for rule in rules:
                slot_rx = rule.get("slot_regex")
                substrings = rule.get("title_substrings") or []
                max_codes = int(rule.get("max_codes") or 0) or 10

                if not slot_rx or not hasattr(slot_rx, "search"):
                    continue
                if not slot_rx.search(label):
                    # This rule doesn't apply to this slot_label
                    continue

                for item in ledger_items:
                    code = str(item.get("code") or "").strip()
                    if not code:
                        continue
                    title = str(item.get("title") or "").lower()
                    if not title:
                        continue

                    for sub in substrings:
                        sub_l = str(sub).lower()
                        if sub_l and sub_l in title:
                            rule_matches.add(code)
                            break  # don't re-check other substrings for this item

                    if len(rule_matches) >= max_codes:
                        break

        satisfied_codes: set[str] = set()
        satisfied_codes |= generic_matches
        satisfied_codes |= rule_matches

        if satisfied_codes:
            bucket = norm_keep.setdefault(vocab, set())
            bucket |= satisfied_codes
            # Slot is now considered satisfied → DO NOT carry it forward
        else:
            # Still genuinely missing
            new_missing.append(slot)

    # Convert norm_keep back to list[str]
    new_keep: Dict[str, List[str]] = {}
    for src, codes in norm_keep.items():
        if codes:
            new_keep[src] = sorted(codes)

    return new_keep, new_missing


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


def extract_final_icd_codes_for_sse(
    results_by_source: Dict[str, List[Dict[str, Any]]],
) -> Dict[str, Any]:
    """
    Build a very simple, eval-friendly structure of ICD codes from the
    post-grading / post-pinning coding results.

    Convention:
      - For icd9cm: version = 9
      - For icd10cm: version = 10

    We look at rows in CODING_SOURCES and pull code from `source_id`
    (or `id` as a fallback). If you have a dedicated `code` field, you
    can swap that in instead.
    """
    icd9_codes: list[dict] = []
    icd10_codes: list[dict] = []

    for src, rows in results_by_source.items():
        if src not in CODING_SOURCES:
            continue

        # Infer version from source name; adjust if you use different identifiers.
        if "icd10" in src:
            version = 10
        elif "icd9" in src:
            version = 9
        else:
            # snomed, loinc, rxnorm, etc. are not ICD; skip for this eval.
            continue

        for r in rows:
            # If your pin logic tags rows, you can filter here, e.g.:
            # if not r.get("pinned", False): continue
            code = (r.get("source_id") or r.get("id") or "").strip()
            if not code:
                continue

            entry = {"code": code, "version": version}
            if version == 9:
                icd9_codes.append(entry)
            else:
                icd10_codes.append(entry)

    # Deduplicate while preserving order
    def dedupe(seq: list[dict]) -> list[dict]:
        seen = set()
        out = []
        for item in seq:
            key = (item["code"], item["version"])
            if key in seen:
                continue
            seen.add(key)
            out.append(item)
        return out

    return {
        "icd9": dedupe(icd9_codes),
        "icd10cm": dedupe(icd10_codes),
        # Optional combined convenience:
        "codes": dedupe(icd9_codes + icd10_codes),
    }

def build_coding_result_from_keep_map(keep_map: Dict[str, List[str]]) -> Dict[str, Any]:
    """
    Build the final coding_result payload directly from the grader's keep_map.

    - Only uses codes that survived pass-2 grading.
    - Currently we expose ICD-10-CM; you can extend to ICD-9/ICD-11 later.
    """
    icd10_codes = [
        {"code": code, "version": 10}
        for code in (keep_map.get("icd10cm") or [])
        if isinstance(code, str) and code.strip()
    ]

    # You can keep icd9 as an empty list for now
    return {
        "icd9": [],
        "icd10cm": icd10_codes,
        "codes": list(icd10_codes),
    }

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

async def discover_all_guideline_sources(pool: asyncpg.Pool) -> List[str]:
    """
    Automatically discover all DB sources that match guideline prefixes
    (acr_, eular_, esmo_, kdigo_, etc). Eliminates the need to hard-code.
    """
    sql = """
        SELECT DISTINCT source
        FROM rag_corpus
        WHERE source IS NOT NULL;
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)

    out = []
    for r in rows:
        src = r["source"]
        if src and _is_guideline_source(src):
            out.append(src)
    return sorted(set(out))

# ---------------------------------------------------------------------------
# Coding prepass: ledger, grader, gap retrieval, pinning
# ---------------------------------------------------------------------------

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
    For each missing slot, run an extra TS pass with the slot's search_terms
    (which should already include LLM-expanded phrases).
    """
    if not missing_slots:
        return results_by_source

    for slot in missing_slots:
        vocab = (slot.get("vocabulary") or "").lower()
        if vocab not in CODING_SOURCES:
            continue

        terms = slot.get("search_terms") or []
        search_terms = [
            t for t in terms
            if isinstance(t, str) and t.strip()
        ]
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

        merged_rows = list(combined.values())
        merged_rows.sort(
            key=lambda r: float(r.get("score", 0.0) or 0.0),
            reverse=True,
        )
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


def build_icd10_rows_from_crosswalk(
    edges: List[Dict[str, Any]],
    *,
    base_score: float = 0.35,
) -> List[Dict[str, Any]]:
    """
    Turn SNOMED→ICD-10-CM crosswalk edges into pseudo rag_corpus-style rows
    for the icd10cm source.

    These are "virtual" rows used only in coding_mode to enrich the ledger.
    """
    rows: List[Dict[str, Any]] = []

    for e in edges:
        code_norm = (e.get("icd10cm_code_norm") or "").strip()
        code_raw = (e.get("icd10cm_code_raw") or "").strip()
        code = code_norm or code_raw
        if not code:
            continue

        title_long = (e.get("icd10cm_title_long") or "").strip()
        title_short = (e.get("icd10cm_title_short") or "").strip()
        snomed_id = str(e.get("snomed_id") or "").strip()
        snomed_term = (e.get("snomed_term") or "").strip()

        title_parts = [code]
        if title_long:
            title_parts.append("— " + title_long)
        elif title_short:
            title_parts.append("— " + title_short)
        title = " ".join(title_parts).strip()

        text_parts: List[str] = []
        if snomed_term:
            text_parts.append(f"SNOMED: {snomed_term} ({snomed_id})")
        map_rule = (e.get("map_rule") or "").strip()
        map_advice = (e.get("map_advice") or "").strip()
        if map_rule:
            text_parts.append(f"Rule: {map_rule}")
        if map_advice:
            text_parts.append(f"Advice: {map_advice}")
        text = "\n".join(text_parts)

        row_id = f"crosswalk_icd10cm:{snomed_id}:{code}"

        rows.append(
            {
                "id": row_id,
                "source": "icd10cm",
                "source_id": code,
                "title": title,
                "text": text,
                "meta": {
                    **e,
                    "from_crosswalk": True,
                    "crosswalk_source": "kg.snomed_icd10cm_crosswalk",
                },
                # Give these a decent score so they show up in the ledger but
                # don’t completely swamp true ts/ann hits.
                "score": base_score,
                "method": "snomed_crosswalk",
            }
        )

    return rows


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
      - Each block is tagged as kind=INTERNAL_MKG (internal/guideline/MKG)
        or kind=VALYU_LIT (Valyu literature), so the LLM can prefer
        guidelines/internal MKG while still using Valyu evidence.
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
        src = row.get("source") or "unknown"
        title = row.get("title") or ""
        text = (row.get("text") or "").strip()
        source_id = row.get("source_id")
        method = (row.get("method") or "").lower()  # <-- FIX: define method

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
            # Non-coding mode: distinguish Valyu vs internal MKG for the prompt
            is_valyu = src.startswith("valyu") or method == "valyu"
            kind = "VALYU_LIT" if is_valyu else "INTERNAL_MKG"

            block = f"[{i}] kind={kind} {src}{source_id_str} | {title} | {text}"

        # +2 for the separating "\n\n"
        if total_len + len(block) + 2 > max_chars:
            blocks.append("[truncated]")
            break

        blocks.append(block)
        total_len += len(block) + 2

    context_str = "\n\n".join(blocks)

    # Debug logging to confirm context size + tail
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
# Crosswalk helpers (SNOMED → ICD-10-CM)
# ---------------------------------------------------------------------------


async def fetch_snomed_icd10_edges(
    pool: asyncpg.Pool,
    snomed_ids: List[str],
    max_edges_per_snomed: int = 8,
) -> List[Dict[str, Any]]:
    """
    Lookup SNOMED → ICD-10-CM edges from kg.snomed_icd10cm_crosswalk.

    snomed_ids are SNOMED concept IDs as strings; we coerce to BIGINT.
    """
    # SNOMED IDs should be numeric; filter/coerce defensively.
    numeric_ids: List[int] = []
    for sid in snomed_ids:
        s = (sid or "").strip()
        if not s:
            continue
        try:
            numeric_ids.append(int(s))
        except ValueError:
            # If you ever store non-numeric SNOMED IDs, you can extend this.
            continue

    if not numeric_ids:
        return []

    sql = """
        SELECT
            snomed_id,
            snomed_term,
            icd10cm_code_raw,
            icd10cm_code_norm,
            icd10cm_title_long,
            icd10cm_title_short,
            map_group,
            map_priority,
            map_rule,
            map_advice,
            map_category_id,
            effective_time,
            active
        FROM kg.snomed_icd10cm_crosswalk
        WHERE snomed_id = ANY($1::bigint[])
          AND active
        ORDER BY snomed_id, map_group, map_priority
        LIMIT $2;
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, numeric_ids, max_edges_per_snomed * max(1, len(numeric_ids)))

    out: List[Dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "snomed_id": str(r["snomed_id"]),
                "snomed_term": r["snomed_term"],
                "icd10cm_code_raw": r["icd10cm_code_raw"],
                "icd10cm_code_norm": r["icd10cm_code_norm"],
                "icd10cm_title_long": r["icd10cm_title_long"],
                "icd10cm_title_short": r["icd10cm_title_short"],
                "map_group": r["map_group"],
                "map_priority": r["map_priority"],
                "map_rule": r["map_rule"],
                "map_advice": r["map_advice"],
                "map_category_id": r["map_category_id"],
                "effective_time": r["effective_time"],
                "active": r["active"],
            }
        )
    return out

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

async def _llm_expand_terms_for_slot(
    q: str,
    slot: Dict[str, Any],
    base_terms: List[str],
    model: str = CHAT_MODEL,
) -> List[str]:
    """
    Use the chat model to reason about better search terms for a coding slot.

    We give it:
      - the full clinical question (q)
      - the coding slot metadata (vocabulary, slot_label)
      - the grader's base_terms

    It returns a short list of additional phrases that might capture the
    underlying condition (e.g. map "pelvic abscess" -> "peritoneal abscess").
    """
    # De-dup and normalize
    all_terms = list(
        dict.fromkeys(
            t.strip()
            for t in (base_terms)
            if isinstance(t, str) and t.strip()
        )
    )
    if not all_terms:
        return []

    vocab = (slot.get("vocabulary") or "").lower()
    slot_label = slot.get("slot_label") or ""

    system_msg = (
        "You expand search phrases for clinical coding searches. "
        "Given a coding vocabulary, a slot label, and some search terms, you must infer "
        "what underlying condition or concept is being described and propose additional "
        "short search phrases that would help find the correct code row. "
        "If a term includes a body part or region plus a condition"
        ", consider that the code may live under the condition "
        "category alone. "
        "Prefer concise medical phrases, not long sentences. "
        "Never invent implausible rare diseases; keep to realistic clinical language. "
        "If ANY search term contains the word 'abscess', you MUST include "
        "'peritoneal abscess' in your expanded_terms unless it would clearly contradict "
        "the clinical note. "
        "Always return STRICT JSON with an 'expanded_terms' array."
    )

    user_msg = f"""Clinical question:
    {q}

    Vocabulary: {vocab}
    Slot label: {slot_label}

    Base search terms from the grader:
    - """ + "\n- ".join(all_terms) + f"""

    Task:
    1. Infer the underlying condition or concept you think the code will be under.
    2. Propose 3–10 additional short search phrases that would help find the code row
       in this vocabulary. Focus on the condition/disease name, not the body region alone.
    3. Return ONLY JSON of the form:
       {{"expanded_terms": ["term1", "term2", "..."]}}.

    Remember:
    - You are not choosing the final code, only better search phrases.
    - Keep each term under ~6 words.
    """

    loop = asyncio.get_event_loop()
    try:
        resp = await loop.run_in_executor(
            None,
            lambda: client.chat.completions.create(
                model=model,
                temperature=0.0,  # <-- make this deterministic for coding gaps
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
            ),
        )
        content = resp.choices[0].message.content or ""

        # Be robust to any extra text around the JSON.
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return []

        obj = json.loads(content[start : end + 1])
        terms = obj.get("expanded_terms") or []
        terms = [
            t.strip()
            for t in terms
            if isinstance(t, str) and t.strip()
        ]

        # ---- HARD-CODED ABSCESS FALLBACK ---------------------------------
        # If any base term contains "abscess", force-add "peritoneal abscess"
        # unless it's already present.
        # lower_all = {t.lower() for t in (all_terms + terms)}
        # if any("abscess" in t for t in lower_all):
        #     if "peritoneal abscess" not in lower_all:
        #         terms.append("peritoneal abscess")
        # -------------------------------------------------------------------

        # Final de-dup preserving order
        seen: set[str] = set()
        out: List[str] = []
        for t in terms:
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            out.append(t)
        return out

    except Exception:
        logger.exception("_llm_expand_terms_for_slot failed")
        return []

async def find_coding_gap_terms(
    q: str,
    missing_slots: List[Dict[str, Any]],
    model: str = CHAT_MODEL,
) -> List[Dict[str, Any]]:
    """
    For each missing coding slot, call the LLM to expand search terms.

    Returns a new list of slot dicts with:
      - vocabulary
      - slot_label
      - base_terms
      - search_terms (base + LLM-expanded, deduped)
    """
    out_slots: List[Dict[str, Any]] = []

    for slot in missing_slots:
        if not isinstance(slot, dict):
            continue

        vocab = (slot.get("vocabulary") or "").lower()
        if vocab not in CODING_SOURCES:
            continue

        label = (slot.get("slot_label") or "").strip()
        base_terms: List[str] = []

        if label:
            base_terms.append(label)

        for t in slot.get("search_terms") or []:
            if isinstance(t, str) and t.strip():
                base_terms.append(t.strip())

        # De-dup base_terms
        seen: set[str] = set()
        base_terms = [
            t for t in base_terms
            if not (t.lower() in seen or seen.add(t.lower()))
        ]

        if not base_terms:
            continue

        # Call the LLM expander (with abscess fallback baked in)
        expanded = await _llm_expand_terms_for_slot(
            q=q,
            slot=slot,
            base_terms=base_terms,
            model=model,
        )

        # Combine base + expanded, dedup
        combined: List[str] = []
        seen = set()
        for t in [*base_terms, *expanded]:
            key = t.lower()
            if key in seen:
                continue
            seen.add(key)
            combined.append(t)

        out_slots.append(
            {
                "vocabulary": vocab,
                "slot_label": label,
                "base_terms": base_terms,
                "search_terms": combined,
            }
        )

    return out_slots
    
async def find_coding_gaps(
    q: str,
    missing_slots: List[Dict[str, Any]],
    model: str = CHAT_MODEL,
) -> List[Dict[str, Any]]:
    """
    For each missing coding slot, ask the LLM for better search phrases.

    Returns a list of entries:
      {
        "slot": slot_dict,
        "vocabulary": vocab,
        "slot_label": slot_label,
        "base_terms": [...],
        "search_terms": [...],   # base + LLM-expanded, deduped
      }

    These search_terms are what you then feed into TS (search_source_ts_for_terms).
    """
    gap_entries: List[Dict[str, Any]] = []

    for slot in missing_slots:
        if not isinstance(slot, dict):
            continue

        vocab = (slot.get("vocabulary") or "").lower()
        if vocab not in CODING_SOURCES:
            # Only run this for code vocabularies
            continue

        slot_label = (slot.get("slot_label") or "").strip()

        # Seed base_terms from grader search_terms + slot_label
        base_terms: List[str] = []
        terms = slot.get("search_terms") or []
        if isinstance(terms, list):
            for t in terms:
                if isinstance(t, str) and t.strip():
                    base_terms.append(t.strip())

        if slot_label and slot_label not in base_terms:
            base_terms.append(slot_label)

        # Dedup + normalize
        seen: set[str] = set()
        base_terms = [
            t for t in base_terms
            if not (t.lower() in seen or seen.add(t.lower()))
        ]

        if not base_terms:
            continue

        # Ask LLM for expansions (this is the function you already debugged)
        expanded_terms: List[str] = await _llm_expand_terms_for_slot(
            q=q,
            slot=slot,
            base_terms=base_terms,
            model=model,
        )

        # Combine base + expanded, dedup
        combined_seen: set[str] = set()
        combined_terms: List[str] = []
        for t in [*base_terms, *(expanded_terms or [])]:
            if not isinstance(t, str):
                continue
            t_norm = t.strip()
            if not t_norm:
                continue
            key = t_norm.lower()
            if key in combined_seen:
                continue
            combined_seen.add(key)
            combined_terms.append(t_norm)

        if not combined_terms:
            continue

        gap_entries.append(
            {
                "slot": slot,
                "vocabulary": vocab,
                "slot_label": slot_label,
                "base_terms": base_terms,
                "search_terms": combined_terms,
            }
        )

    return gap_entries


def _expand_terms_with_icd10_synonyms(terms: Iterable[str]) -> List[str]:
    """
    Expand a list of terms using ICD10_SYNONYM_MAP.
    - Preserves original terms.
    - Adds any configured synonyms.
    - De-duplicates by normalized form.
    """
    seen: Set[str] = set()
    expanded: List[str] = []

    for t in terms:
        if not t:
            continue
        norm = _norm_term_key(t)
        if norm in seen:
            continue
        seen.add(norm)
        expanded.append(t)

        # ICD-10 specific synonyms
        for syn in ICD10_SYNONYM_MAP.get(norm, []):
            syn_norm = _norm_term_key(syn)
            if syn_norm in seen:
                continue
            seen.add(syn_norm)
            expanded.append(syn)

        # Optional: generic medical shortcuts → full phrases
        for syn in GENERIC_MED_SYNONYM_MAP.get(norm, []):
            syn_norm = _norm_term_key(syn)
            if syn_norm in seen:
                continue
            seen.add(syn_norm)
            expanded.append(syn)

    return expanded

async def search_source_ts_for_terms(
    pool: asyncpg.Pool,
    source: str,
    terms: List[str],
    limit: int,
) -> List[Dict[str, Any]]:
    """
    Term augmented text-search retrieval.

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
    - boost: currently unused, kept for future tuning

    When raw=True we try to:
      - request full contents from Valyu (return_contents=True)
      - stash any full text in meta["full_text"]
      - still use snippet for row["text"] to keep context compact
    """
    included_sources: Optional[List[str]] = None
    if sources:
        included_sources = [s.strip() for s in sources.split(",") if s.strip()]

    try:
        vy = await valyu_client.call_valyu(
            mode=mode or "search",
            q=q,
            k=limit,
            included_sources=included_sources,
            return_contents=bool(raw),     # 🔑 ask Valyu for full text when raw=1
            fast_mode=(mode == "search"),
        )
    except Exception:
        logger.exception("Valyu call failed")
        return {}

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

        # Try to capture full text when raw=True; different keys depending on backend
        full_text = None
        if raw:
            full_text = (
                h.get("contents")
                or h.get("content")
                or h.get("fulltext")
                or h.get("full_text")
            )

        snippet = h.get("snippet") or ""

        # Clone original hit as meta and augment it
        meta = dict(h)
        if raw and isinstance(full_text, str) and full_text.strip():
            meta["full_text"] = full_text  # 🔑 this will flow into citations + fulltext SSE

        base = {
            "id": h.get("id"),
            "source": src_key,
            "title": h.get("title") or "",
            "text": snippet,  # keep snippet as context body for the LLM
            "meta": meta,
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
# Match helpers
# ---------------------------------------------------------------------------

def dedupe_matches(matches: list[dict]) -> list[dict]:
    """
    Deduplicate matches by (source, id). Keep the first occurrence.
    This keeps traces clean and avoids inflating pinned_counts.
    """
    seen = set()
    out = []
    for m in matches:
        key = (m.get("source"), m.get("id"))
        if key in seen:
            continue
        seen.add(key)
        out.append(m)
    return out


async def run_icd10cm_crosswalk_phase(
    send: callable,
    pool: asyncpg.Pool,
    coding_rows: list[dict],
) -> list[dict]:
    """
    Expand SNOMED coding rows to ICD-10-CM via kg.snomed_icd10cm_crosswalk.

    - Emits:
        status: coding_crosswalk_expansion
        phase_start (source=icd10cm, method=edges)
        phase_end   (source=icd10cm, method=edges)
        matches     (phase=edges, source=icd10cm)
    - Returns list of ICD-10-CM match rows, deduped by (source, id).
    """
    # Informational status, just like before
    await send(sse("status", {"status": "coding_crosswalk_expansion"}))

    # Start phase
    await send(
        sse(
            "phase_start",
            {
                "source": "icd10cm",
                "method": "edges",
            },
        )
    )

    # --- build list of SNOMED ids to expand ---
    # Expect coding_rows from previous phases with source="snomed"
    snomed_ids = {
        r["id"]
        for r in coding_rows
        if r.get("source") == "snomed" and isinstance(r.get("id"), (int, str))
    }

    if not snomed_ids:
        # No SNOMED inputs, cleanly end phase and return
        await send(
            sse(
                "phase_end",
                {
                    "source": "icd10cm",
                    "method": "edges",
                },
            )
        )
        return []

    # --- fetch crosswalk rows in one shot ---
    # You already created kg.snomed_icd10cm_crosswalk
    # snomed_id, icd10cm_code_norm, icd10cm_title_long, icd10cm_title_short, ...
    rows = []
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT
              snomed_id,
              snomed_term,
              icd10cm_code_norm,
              icd10cm_code_raw,
              icd10cm_title_long,
              icd10cm_title_short,
              map_group,
              map_priority,
              map_rule,
              map_advice,
              map_category_id,
              effective_time,
              active
            FROM kg.snomed_icd10cm_crosswalk
            WHERE snomed_id = ANY($1::bigint[])
              AND active = TRUE
            """,
            list({int(s) for s in snomed_ids if str(s).isdigit()}),
        )

    # --- convert to match objects ---
    crosswalk_matches: list[dict] = []
    for row in rows:
        icd_code = row["icd10cm_code_norm"]
        if not icd_code:
            continue

        match_id = f"crosswalk_icd10cm:{row['snomed_id']}:{icd_code}"

        # NOTE: score is arbitrary here; you can tune later or
        # make it relative to ts/ann scores if you want
        crosswalk_matches.append(
            {
                "source": "icd10cm",
                "id": match_id,
                "code": icd_code,
                "score": 0.55,  # moderate baseline, tweak as needed
                "text": row["icd10cm_title_long"] or row["icd10cm_title_short"] or icd_code,
                "meta": {
                    "kind": "coding_crosswalk",
                    "snomed_id": row["snomed_id"],
                    "snomed_term": row["snomed_term"],
                    "icd10cm_code_raw": row["icd10cm_code_raw"],
                    "icd10cm_title_long": row["icd10cm_title_long"],
                    "icd10cm_title_short": row["icd10cm_title_short"],
                    "map_group": row["map_group"],
                    "map_priority": row["map_priority"],
                    "map_rule": row["map_rule"],
                    "map_advice": row["map_advice"],
                    "map_category_id": row["map_category_id"],
                    "effective_time": row["effective_time"].isoformat()
                    if row["effective_time"]
                    else None,
                },
            }
        )

    # --- dedupe by (source, id) so trace & fusion stay clean ---
    crosswalk_matches = dedupe_matches(crosswalk_matches)

    # End phase *before* emitting matches, to mirror ts/ann
    await send(
        sse(
            "phase_end",
            {
                "source": "icd10cm",
                "method": "edges",
            },
        )
    )

    # Emit matches event (single consolidated batch)
    if crosswalk_matches:
        await send(
            sse(
                "matches",
                {
                    "phase": "edges",
                    "source": "icd10cm",
                    "matches": crosswalk_matches,
                },
            )
        )

    return crosswalk_matches

    
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

VALYU_EVIDENCE_SYSTEM_PROMPT = """
You are 2ndOpinionMD's literature synthesis assistant.

You will receive a clinical question and a context consisting ONLY of
peer-reviewed publications (typically PubMed articles) retrieved via Valyu.

Your job:
- Summarize the BEST AVAILABLE EVIDENCE from these studies.
- Focus on:
    - study types (RCTs, cohort studies, meta-analyses, etc.)
    - populations and inclusion/exclusion criteria
    - interventions and comparators
    - key efficacy outcomes (effect sizes when available)
    - key safety outcomes / adverse events
    - major limitations or uncertainties

Rules:
- Base your answer STRICTLY on the provided Valyu context (VALYU_LIT); do NOT hallucinate.
- If evidence is sparse or conflicting, say so explicitly.
- When studies disagree, explain the disagreement (e.g., sample size, endpoints, follow-up).
- Do NOT re-state guideline recommendations here; this pass is for evidence only.
- Use plain language and short paragraphs, but preserve important clinical details.
- When you mention specific findings, tie them to article indices [VALYU-1], [VALYU-2], etc.
- If the context does not adequately answer the question, say so and suggest what type of
  further study or guideline would be needed.
""".strip()


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
    Use the chat model to extract focused search phrases AND candidate codes
    for code-oriented retrieval.

    The model should:
      - Identify disease/condition phrases.
      - Identify procedure phrases.
      - Identify lab analytes / test names.
      - Identify medication names.
      - When possible, propose *candidate* codes for ICD-10-CM, ICD-11,
        SNOMED CT, LOINC, and RxNorm based on the question text.

    Returns:
      - A deduplicated list of short phrases and code strings that will be
        used as TS queries across ICD-10-CM, ICD-11, SNOMED CT, LOINC, RxNorm.
      - Candidate codes are also logged separately for downstream validation.
    """
    try:
        resp = client.chat.completions.create(
            model=CHAT_MODEL,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a medical coding term and code-candidate extractor "
                        "for a retrieval-augmented coding system.\n\n"
                        "Given a clinical question or discharge summary that asks for "
                        "ICD-10-CM, ICD-11, SNOMED CT, LOINC, and/or RxNorm codes, "
                        "your job is to output:\n"
                        "  1) A small set of focused search phrases.\n"
                        "  2) A small set of *candidate* codes per vocabulary.\n\n"
                        "General rules:\n"
                        "- Return ONLY a JSON object.\n"
                        "- The JSON MUST have a key 'terms' whose value is a list of strings.\n"
                        "- The JSON MAY have a key 'code_candidates' whose value is a list "
                        "  of objects.\n\n"
                        "For 'terms':\n"
                        "- Each term should be a short phrase (2–6 words) suitable for text search.\n"
                        "- Include:\n"
                        "    * disease/condition names (e.g., 'heart failure with reduced "
                        "       ejection fraction', 'chronic kidney disease stage 3b', "
                        "       'type 2 diabetes mellitus with peripheral neuropathy')\n"
                        "    * relevant organ or syndrome qualifiers when they meaningfully "
                        "      constrain the code (e.g., 'acute on chronic systolic heart failure')\n"
                        "    * procedures (e.g., 'IV diuresis', 'kidney biopsy')\n"
                        "    * lab tests/analytes (e.g., 'ejection fraction', "
                        "       'apixaban level', 'creatinine')\n"
                        "    * medication names (e.g., 'apixaban', 'metoprolol', 'lisinopril')\n"
                        "- Do NOT include generic context words like 'adult', 'treated', "
                        "  'please provide', 'codes for', etc.\n"
                        "- Aim for roughly 5–20 terms depending on question complexity.\n"
                        "- Avoid duplicates; normalize obvious variants to a single phrase.\n\n"
                        "For 'code_candidates':\n"
                        "- Use this shape for each candidate:\n"
                        "  {\n"
                        '    \"vocabulary\": \"icd10cm\" | \"icd11\" | \"snomed\" | \"loinc\" | \"rxnorm\",\n'
                        '    \"code\": \"string\",\n'
                        '    \"display\": \"human-readable title for the code\",\n'
                        '    \"reason\": \"1–2 sentence justification based on the text\",\n'
                        '    \"confidence\": \"high\" | \"medium\" | \"low\"\n'
                        "  }\n"
                        "- Only propose a code when the clinical description gives a strong\n"
                        "  signal that the code is plausible (e.g., explicit disease name, "
                        "  stage/severity, clear medication mention).\n"
                        "- Prefer a *small* set of high-yield candidates over many guesses.\n"
                        "- For 'high' confidence:\n"
                        "    * The text closely matches the official code title or a very\n"
                        "      common synonym.\n"
                        "- For 'medium' confidence:\n"
                        "    * The mapping is plausible but details (e.g., exact subtype,\n"
                        "      laterality, or complication) are not fully specified.\n"
                        "- For 'low' confidence:\n"
                        "    * Only include if the question clearly asks for codes and the\n"
                        "      best you can do is a reasonable educated guess.\n"
                        "- Never invent obviously impossible codes (e.g., wrong format for\n"
                        "  the vocabulary).\n\n"
                        "Output STRICT JSON only, with this top-level structure:\n"
                        "{\n"
                        "  \"terms\": [\"term1\", \"term2\", ...],\n"
                        "  \"code_candidates\": [\n"
                        "    {\n"
                        "      \"vocabulary\": \"icd10cm\",\n"
                        "      \"code\": \"I50.23\",\n"
                        "      \"display\": \"Acute on chronic systolic (congestive) heart failure\",\n"
                        "      \"reason\": \"The note states acute on chronic systolic HF exacerbation.\",\n"
                        "      \"confidence\": \"high\"\n"
                        "    }\n"
                        "    // ... more candidates\n"
                        "  ]\n"
                        "}\n"
                        "If you are unsure about codes, you may return an empty "
                        "'code_candidates' list, but you should still return strong 'terms'.\n"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        "Clinical question or summary:\n"
                        f"{q.strip()}\n\n"
                        "Respond ONLY with JSON of the form:\n"
                        "{\n"
                        '  \"terms\": [\"term1\", \"term2\", ...],\n'
                        '  \"code_candidates\": [ { ... } ]\n'
                        "}\n"
                    ),
                },
            ],
        )
    except Exception as e:
        logger.exception("extract_code_terms: OpenAI chat call failed")
        return []

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
    raw_code_candidates = data.get("code_candidates") or []

    if not isinstance(raw_terms, list):
        logger.warning("extract_code_terms: 'terms' not a list: %r", type(raw_terms))
        raw_terms = []

    if not isinstance(raw_code_candidates, list):
        logger.warning(
            "extract_code_terms: 'code_candidates' not a list: %r",
            type(raw_code_candidates),
        )
        raw_code_candidates = []

    # Clean / normalize / dedupe
    terms_set: set[str] = set()

    # 1) Natural language terms
    for t in raw_terms:
        if not isinstance(t, str):
            continue
        t_clean = t.strip()
        if not t_clean:
            continue
        if len(t_clean) < 3:
            continue
        t_clean = re.sub(r"\s+", " ", t_clean)
        terms_set.add(t_clean)

    # 2) Also fold in raw code strings as terms so TS can directly hit them.
    code_candidates_clean: list[dict[str, Any]] = []
    for cand in raw_code_candidates:
        if not isinstance(cand, dict):
            continue
        vocab = str(cand.get("vocabulary") or "").strip().lower()
        code = str(cand.get("code") or "").strip().upper()
        display = str(cand.get("display") or "").strip()
        confidence = str(cand.get("confidence") or "").strip().lower() or "medium"
        reason = str(cand.get("reason") or "").strip()

        if not vocab or not code:
            continue

        code_candidates_clean.append(
            {
                "vocabulary": vocab,
                "code": code,
                "display": display,
                "confidence": confidence,
                "reason": reason,
            }
        )

        # Add the raw code string as a TS term (e.g., 'I50.23', 'E11.40').
        terms_set.add(code)

    if code_candidates_clean:
        logger.info("extract_code_terms: code_candidates=%s", code_candidates_clean)

    terms = sorted(terms_set)
    logger.info("extract_code_terms: terms=%s", terms)
    return terms

# ---------------------------------------------------------------------------
# Query-term extraction for /ask_stream (Q&A)
# ---------------------------------------------------------------------------

async def extract_qna_terms(
    q: str,
    *,
    model: str = CHAT_MODEL,
    max_terms: int = 20,
    extra_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Extract canonical query terms and expansions for general Q&A (not just coding).

    If extra_context is provided (e.g., short Valyu snippets), we append it
    to the question so that the term extractor can see additional medically
    relevant vocabulary without changing the core question intent.

    Returns:
        {
          "terms": [...],
          "expansions": {...},
          "all_terms": [...],  # flattened canonical + expansions
        }

    On failure, returns all empty/[] but the caller can fall back to [q].
    """
    if extra_context:
        augmented_q = (
            f"{q}\n\n"
            "Additional context from related abstracts/titles:\n"
            f"{extra_context[:2000]}"
        )
    else:
        augmented_q = q

    term_data = await extract_query_terms(
        q=augmented_q,
        model=model,
        max_terms=max_terms,
    )
    all_terms = build_all_terms(term_data)

    return {
        "terms": term_data.get("terms", []) or [],
        "expansions": term_data.get("expansions", {}) or {},
        "all_terms": all_terms or [],
    }

def build_llm_messages(
    q: str,
    ctx_str: str,
    coding_mode: bool = False,
    *,
    answer_mode: str = "guideline",  # 'guideline' | 'valyu' | 'eoh'
) -> List[Dict[str, Any]]:
    """
    Build messages for the chat model.

    Modes:
      - coding_mode=True
            → strict coding prompt (enhanced for completeness).
      - coding_mode=False, answer_mode='guideline'
            → guideline/MKG-first QA prompt (existing behavior).
      - coding_mode=False, answer_mode='valyu'
            → Valyu literature synthesis prompt (peer-reviewed evidence only).
      - coding_mode=False, answer_mode='eoh'
            → Ethos-of-Health reasoning prompt over EoH/MKG context.
    """
    if coding_mode:
        system_content = CODING_SYSTEM_PROMPT

        user_content = CODING_USER_PROMPT_TEMPLATE.format(
            question=q.strip(),
            context=ctx_str,
        )

        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content},
        ]

    # ------------------ non-coding mode ------------------
    answer_mode = (answer_mode or "guideline").lower()

    # ---- Valyu / peer-reviewed evidence synthesis ----
    if answer_mode == "valyu":
        system_content = VALYU_EVIDENCE_SYSTEM_PROMPT
        return [
            {"role": "system", "content": system_content},
            {
                "role": "user",
                "content": (
                    "Clinical question:\n"
                    f"{q.strip()}\n\n"
                    "Here are peer-reviewed articles retrieved for this question. "
                    "Each block is a Valyu literature snippet with index labels like [VALYU-1], [VALYU-2], etc.:\n\n"
                    f"{ctx_str}\n\n"
                    "Now synthesize the evidence strictly from these articles, following the instructions."
                ),
            },
        ]

    # ---- NEW: Ethos-of-Health reasoning mode ----
    if answer_mode == "eoh":
        system_content = EOH_SYSTEM_PROMPT
        return [
            {"role": "system", "content": system_content},
            {
                "role": "user",
                "content": (
                    "Ethos-of-Health (EoH) question:\n"
                    f"{q.strip()}\n\n"
                    "Here is the retrieved EoH / MKG context. Blocks may include EoH rules, "
                    "stability bands, stack levels, safeguards, drift logic, and example cases:\n\n"
                    f"{ctx_str}\n\n"
                    "Interpret the patient’s situation using ONLY this context. "
                    "Focus on stack level, stability band, drift detection, safety alerts, "
                    "and when a clinician should review."
                ),
            },
        ]

    # ---- Default: guideline/MKG-first QA (existing behavior) ----
    system_content = (
        "You are 2ndOpinionMD's retrieval-augmented medical assistant.\n"
        "The context you receive contains two kinds of evidence, marked in each "
        "block as kind=INTERNAL_MKG or kind=VALYU_LIT.\n\n"
        "INTERNAL_MKG:\n"
        "- Curated internal corpora such as guidelines (NICE, ACR, KDIGO, WHO, VA), "
        "  ontologies, and other 2ndOpinionMD knowledge-graph sources.\n\n"
        "VALYU_LIT:\n"
        "- External literature snippets retrieved via Valyu, typically PubMed "
        "  articles (clinical trials, meta-analyses, cohort studies, etc.).\n\n"
        "When answering:\n"
        "- Prefer INTERNAL_MKG guideline content **only when it directly addresses the "
        "  clinical problem in the question**.\n"
        "- If INTERNAL_MKG passages are clearly about unrelated topics, ignore them.\n"
        "- Use VALYU_LIT to fill gaps and add detail, but keep the backbone aligned with guidelines.\n"
        "- If INTERNAL_MKG does not answer the question at all, it is acceptable to "
        "  base your answer primarily on VALYU_LIT, making clear that your answer is "
        "  derived from PubMed literature rather than formal guidelines.\n"
        "- If INTERNAL_MKG and VALYU_LIT appear to disagree, prioritize INTERNAL_MKG "
        "  recommendations, but you may briefly note important newer evidence from "
        "  VALYU_LIT.\n\n"
        "Use ONLY the provided context to answer, citing sections by index like [1], [2], etc. "
        "If the answer is not clearly supported by either INTERNAL_MKG or VALYU_LIT, say you "
        "do not know and suggest useful follow-up guidelines or literature to consult."
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
    *,
    event_prefix: str = "llm",
    answer_mode: str = "guideline",
    
) -> Iterable[Dict[str, str]]:
    """
    Stream LLM output as SSE events.

    Modes:
      - llm_mode == "delta":
          event: <event_prefix>_delta  { "text": "<small token-ish piece>" }
      - llm_mode == "chunk" (default):
          event: <event_prefix>_chunk  { "text": "<sentence-ish chunk>" }

    In BOTH modes, we also emit:
      event: <event_prefix>_done { "text": "<full answer>" }

    answer_mode:
      - 'guideline' → guideline/MKG-first QA
      - 'valyu'     → peer-reviewed evidence synthesis
      - ignored when coding_mode=True
    """
    ctx_str = format_context_for_llm(context_items, coding_mode=coding_mode)
    messages = build_llm_messages(
        q,
        ctx_str,
        coding_mode=coding_mode,
        answer_mode=answer_mode,
    )

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
            yield sse(f"{event_prefix}_chunk", {"text": text})
        buf = ""

    for chunk in stream:
        choice = chunk.choices[0]
        delta = choice.delta
        content = getattr(delta, "content", None)
        if not content:
            continue

        if isinstance(content, str):
            text_piece = content
        else:
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
            yield sse(f"{event_prefix}_delta", {"text": text_piece})
        else:
            buf += text_piece
            if any(
                buf.endswith(end)
                for end in [". ", ".\n", "?\n", "!\n", ".\n\n"]
            ) or len(buf) > 600:
                for ev in flush_chunk():
                    yield ev

    if mode == "chunk" and buf.strip():
        for ev in flush_chunk():
            yield ev

    full_text = "".join(full_pieces).strip()
    yield sse(f"{event_prefix}_done", {"text": full_text})


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
    