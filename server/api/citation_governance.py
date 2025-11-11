# server/api/citation_governance.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import re, datetime

AUTHORITATIVE = {"icd10cm","icd10-cm","icd11","snomed","snomed ct","loinc","rxnorm","hpo","orphanet"}
GUIDELINE_SOURCES = {"nice","acr","eular","cdc","va","va/dod","va-dod","dod"}
LEXICAL_ONLY = {"chv"}

def norm_sys(s: Optional[str]) -> str:
    if not s: return ""
    s = s.strip().lower().replace("_","-")
    if s in {"icd-10-cm","icd10cm"}: return "icd10-cm"
    if s in {"icd-11","icd11"}: return "icd11"
    if s in {"snomed-ct","snomed ct","snomed"}: return "snomed"
    return s

def is_authoritative(system: str) -> bool:
    return norm_sys(system) in AUTHORITATIVE

def is_lexical(system: str) -> bool:
    return norm_sys(system) in LEXICAL_ONLY

def is_guideline_src(src: str) -> bool:
    s = (src or "").lower()
    return any(k in s for k in GUIDELINE_SOURCES)

def now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def best_citation_for(item: Dict[str,Any], matches: List[Dict[str,Any]]) -> Optional[Dict[str,Any]]:
    """
    Pick one best ontology doc to cite (never CHV as the sole clinical proof).
    Preference: exact code+system → same-system title match → any authoritative containing the title.
    """
    title = (item.get("title") or "").strip().lower()
    code  = (item.get("code") or "").strip().upper()
    system= norm_sys(item.get("system"))

    if code and system:
        for m in matches:
            if norm_sys(m.get("source")) == system and (m.get("source_id") or "").strip().upper() == code:
                return m

    if title and system:
        for m in matches:
            if norm_sys(m.get("source")) == system and title in (m.get("title","").lower()):
                return m

    if title:
        for m in matches:
            if is_authoritative(m.get("source","")) and title in (m.get("title","").lower()):
                return m
    return None

def compute_col_widths(table: List[List[str]], max_width: float, min_width: float=48.0) -> List[float]:
    """
    Estimate column widths from character lengths and scale to fit page width.
    Keeps tables from overflowing and leaves them left-aligned.
    """
    if not table: return []
    cols = len(table[0])
    lengths = [0]*cols
    for row in table:
        for i, cell in enumerate(row[:cols]):
            l = len(str(cell))
            if l > lengths[i]: lengths[i] = l
    raw = [max(min_width, 6.0*l) for l in lengths]  # ~6 pt per char (crude but effective)
    total = sum(raw) or 1.0
    if total <= max_width:
        return raw
    scale = max_width / total
    return [max(min_width, w*scale) for w in raw]

def excerpt(text: str, needle: str, limit: int = 360) -> str:
    if not text: return ""
    t = re.sub(r"\s+"," ",str(text)).strip()
    if not needle:
        return t[:limit]
    i = t.lower().find(needle.lower())
    if i < 0:
        return t[:limit]
    start = max(0, i-120); end = min(len(t), i+240)
    return t[start:end][:limit]

def compose_claim_bundle(kind: str,
                         item: Dict[str,Any],
                         matches: List[Dict[str,Any]],
                         retrieved_versions: Optional[Dict[str,str]] = None) -> Dict[str,Any]:
    """
    Build the governance-compliant “one-claim → one-bundle”.
    - Include only concrete ontology IDs (no placeholders).
    - CHV only as lexical evidence (never clinical proof).
    - Map edges if present in matches.meta.edges
    """
    system = norm_sys(item.get("system"))
    code   = (item.get("code") or "").strip()
    title  = item.get("title") or ""
    why    = item.get("why") or item.get("indication") or item.get("purpose") or ""
    claim  = {"kind": kind, "claim": (why or title).strip()}

    codes: Dict[str,Dict[str,str]] = {}
    if system == "icd10-cm" and code: codes["icd10cm"] = {"code": code, "label": title}
    elif system == "icd11" and code: codes["icd11"]   = {"code": code, "label": title}
    elif system == "snomed" and code: codes["snomed"]  = {"code": code, "label": title}
    elif system == "loinc" and code: codes["loinc"]   = {"code": code, "label": title}
    elif system == "rxnorm" and code: codes["rxnorm"]  = {"code": code, "label": title}

    # Evidence
    evidence: List[Dict[str,Any]] = []

    # Guideline snippets (anchored if we have meta)
    for m in matches:
        if is_guideline_src(m.get("source","")):
            evidence.append({
                "type":"guideline",
                "source": m.get("source"),
                "doc": (m.get("meta") or {}).get("doc_key") or m.get("source_id"),
                "section": (m.get("meta") or {}).get("section") or "",
                "quote": excerpt(m.get("text",""), title, 280)
            })

    # Ontology doc as the clinical citation when appropriate
    cited = best_citation_for(item, matches)
    if cited and is_authoritative(cited.get("source","")):
        evidence.append({
            "type":"ontology",
            "source": cited.get("source"),
            "code": cited.get("source_id"),
            "title": cited.get("title"),
            "quote": excerpt(cited.get("text",""), title, 200)
        })

    # CHV purely lexical (secondary)
    for m in matches:
        if norm_sys(m.get("source","")) == "chv" and title and title.lower() in (m.get("title","").lower()):
            evidence.append({"type":"lexical","source":"chv","cui": m.get("source_id"), "label": m.get("title")})
            break

    bundle = {
        "claim": claim["claim"],
        "codes": codes,
        "evidence": evidence,
        "mappings": [],
        "provenance": {"retrieval_time": now_iso(), "release_versions": retrieved_versions or {}}
    }
    # Edge path, if it came back on matches
    for m in matches:
        for e in (m.get("meta") or {}).get("edges") or []:
            src = norm_sys(e.get("from_system")); dst = norm_sys(e.get("to_system"))
            if src in AUTHORITATIVE and dst in AUTHORITATIVE:
                bundle["mappings"].append({
                    "from": e.get("from_code"),
                    "to": e.get("to_code"),
                    "via": e.get("relation") or "unspecified"
                })
    return bundle

