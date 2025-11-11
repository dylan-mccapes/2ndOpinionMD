# server/api/coding_citations.py
from typing import Dict, Any, List
import os
import asyncpg
from .citation_utils import build_min_citation_bundle, _normalize_db_url

async def _get_conn() -> asyncpg.Connection:
    return await asyncpg.connect(dsn=_normalize_db_url(os.getenv("DATABASE_URL")))

def _names_list(items: List[Dict[str, Any]], key: str="title") -> List[str]:
    out = []
    for it in items or []:
        name = (it.get(key) or "").strip()
        if name:
            out.append(name)
    return out

def _lab_hints(labs: List[Dict[str, Any]]) -> List[str]:
    hints = []
    for lab in labs or []:
        title = (lab.get("title") or "").lower()
        if "troponin" in title:
            hints.append(title)
    # Default heuristic if nothing found
    return hints or ["troponin high", "high-sensitivity troponin"]

async def enrich_coding_response(resp: Dict[str, Any]) -> None:
    """
    Post-process the /coding JSON dict in-place:
      - For each ICD-10-CM probable_dx item, attach 'justification_bundle'
      - Uses authoritative ICD-10-CM label (ehr_mimic4.d_icd_diagnoses)
      - Uses rag_corpus to best-effort add LOINC/RxNorm
    """
    meds_names = _names_list(resp.get("medications", []))
    lab_hints  = _lab_hints(resp.get("labs", []))

    conn = await _get_conn()
    try:
        for dx in resp.get("probable_dx", []):
            if (dx.get("system") or "").upper() == "ICD-10-CM":
                code = dx.get("code")
                claim = dx.get("why") or "Diagnostic assertion"
                bundle = await build_min_citation_bundle(
                    conn,
                    claim_text=claim,
                    icd10_code=code,
                    meds_names=meds_names,
                    lab_hints=lab_hints,
                )
                dx["justification_bundle"] = bundle
    finally:
        await conn.close()

