# server/api/citation_utils.py
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Utilities expected by coding_routes.py

def _norm(s: Optional[str]) -> str:
    return (s or "").strip()

def _lc(s: Optional[str]) -> str:
    return _norm(s).lower()

def _title_tokens(t: str) -> List[str]:
    t = re.sub(r"[^A-Za-z0-9\s\-\./]+", " ", t or "")
    return [w for w in _lc(t).split() if w]

def split_matches_by_role(matches: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    """
    Light fan-out by source family for convenience.
    """
    buckets = {
        "icd10cm": [], "icd11": [], "icd10pcs": [],
        "loinc": [], "rxnorm": [], "snomed": [],
        "guidelines": [], "nice": [], "acr_eular": [],
        "medical_knowledge": [], "hpo": [], "mimic4_dx": [], "mimic4_note": [],
        "other": []
    }
    for m in matches or []:
        src = _lc(m.get("source"))
        if src in buckets:
            buckets[src].append(m)
        elif "guideline" in src:
            buckets["guidelines"].append(m)
        else:
            buckets["other"].append(m)
    return buckets

def _guess_code_from_source_id(source: str, source_id: str) -> Optional[str]:
    sid = _norm(source_id)
    if not sid:
        return None
    s = _lc(source)
    if s in ("loinc", "rxnorm", "icd10cm", "icd11", "icd10pcs", "snomed"):
        # Most of your rag_corpus rows use source_id as the code
        return sid
    return None

def enrich_missing_code_from_matches(item: Dict[str, Any], matches: List[Dict[str, Any]]) -> None:
    """
    If an item is missing a code but we have a near-title match in matches,
    copy the code from that match's source_id.
    """
    if _norm(item.get("code")):
        return
    sys = _lc(item.get("system"))
    title = _lc(item.get("title"))
    if not title:
        return

    best: Optional[Tuple[int, Dict[str, Any]]] = None
    for m in matches or []:
        src = _lc(m.get("source"))
        if (sys == "loinc" and src != "loinc") or (sys == "rxnorm" and src != "rxnorm"):
            continue
        mtitle = _lc(m.get("title"))
        # crude similarity: shared tokens
        score = len(set(_title_tokens(title)) & set(_title_tokens(mtitle)))
        if score == 0:
            continue
        if not best or score > best[0]:
            best = (score, m)

    if best:
        m = best[1]
        code = _guess_code_from_source_id(m.get("source",""), m.get("source_id",""))
        if code:
            item["code"] = code

def _match_by_title(item: Dict[str, Any], matches: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    title = _lc(item.get("title"))
    if not title:
        return None
    best: Optional[Tuple[int, Dict[str, Any]]] = None
    for m in matches or []:
        mt = _lc(m.get("title"))
        score = len(set(_title_tokens(title)) & set(_title_tokens(mt)))
        if score == 0:
            continue
        if not best or score > best[0]:
            best = (score, m)
    return best[1] if best else None

def _match_by_system_code(item: Dict[str, Any], matches: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    sys = _lc(item.get("system"))
    code = _lc(item.get("code"))
    if not sys or not code:
        return None
    for m in matches or []:
        ms = _lc(m.get("source"))
        sid = _lc(m.get("source_id"))
        if sys == "icd-10-cm" or sys == "icd10" or sys == "icd-10":
            # normalize icd10 code formatting
            norm = code.replace(".", "")
            if ms == "icd10cm" and sid.replace(".", "") == norm:
                return m
        elif sys == "loinc" and ms == "loinc" and sid == code:
            return m
        elif sys == "rxnorm" and ms == "rxnorm" and sid == code:
            return m
        elif sys == "icd-11" and ms == "icd11" and sid == code:
            return m
        elif sys == "snomed" and ms == "snomed" and sid == code:
            return m
    return None

def choose_citation(item: Dict[str, Any], matches: List[Dict[str, Any]]) -> Tuple[Optional[Dict[str, Any]], str]:
    """
    Strategy:
    1) Exact system+code match (best)
    2) Title overlap match (ok)
    3) Otherwise, None with reason
    """
    m = _match_by_system_code(item, matches)
    if m:
        return m, "system+code match"
    m = _match_by_title(item, matches)
    if m:
        return m, "title overlap"
    return None, "no exact match; waiting on more evidence"

def explain_missing_citation(item: Dict[str, Any], matches: List[Dict[str, Any]]) -> str:
    sys = _lc(item.get("system"))
    code = _lc(item.get("code"))
    title = _lc(item.get("title"))
    if sys and code:
        return f"no {sys} citation found for code {code} among {len(matches)} matches"
    if title:
        return f"no citation with overlapping title tokens for '{title}'"
    return "insufficient fields to match a citation"
