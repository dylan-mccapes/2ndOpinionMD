"""
server/eoh/event_dedup.py
─────────────────────────
Canonical event-id computation for PatientTimelineVision deduplication.

Every source that writes events into the graph (Tier A lightweight artifact,
Tier B eoh-llama 8B extraction, journal mirror, heuristic pre-scan) must
produce the **same** event_id for logically identical events so that
``PatientTimelineVision.add_event`` collapses them (union discovered_by,
append source_artifacts) instead of inserting duplicates.

Key: ``(patient_id, event_type, utc_day, normalized_label)``

See docs/ARTIFACTS.md §6.2 for the full specification.
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional


# ── Normalisation helpers ────────────────────────────────────────────────────

def _sha16(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()[:16]


def _norm_str(s: str) -> str:
    """Lower-case, collapse whitespace, strip non-ASCII modifiers."""
    s = unicodedata.normalize("NFKD", s)
    s = s.encode("ascii", errors="ignore").decode("ascii")
    s = s.lower().strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _utc_day(ts: str) -> str:
    """Return 'YYYY-MM-DD' from an ISO-8601 string.  Falls back to 'unknown'."""
    if not ts or ts == "unknown":
        return "unknown"
    for fmt in (
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%Y/%m/%d",
        "%m/%d/%Y",
        "%d/%m/%Y",
    ):
        try:
            dt = datetime.strptime(ts.rstrip("Z"), fmt.rstrip("z%").rstrip("%z"))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            pass
    # Last-ditch: grab the first 10 chars if they look like YYYY-MM-DD
    m = re.match(r"(\d{4}-\d{2}-\d{2})", ts)
    if m:
        return m.group(1)
    return "unknown"


# ── Per-type label normalisers ────────────────────────────────────────────────

def _norm_lab(ann: Dict[str, Any], text: str) -> str:
    loinc = ann.get("loinc") or ann.get("loinc_code") or ""
    if loinc:
        return f"loinc_{_norm_str(loinc)}"
    analyte = ann.get("analyte") or ann.get("test_name") or ann.get("lab_name") or ""
    if not analyte:
        analyte = text
    return f"lab_{_norm_str(analyte)[:60]}"


def _norm_medication(ann: Dict[str, Any], text: str) -> str:
    rxcui = ann.get("rxcui") or ann.get("rxnorm") or ""
    if rxcui:
        return f"rxcui_{_norm_str(str(rxcui))}"
    drug = (
        ann.get("drug_name")
        or ann.get("generic_name")
        or ann.get("medication")
        or text
    )
    return f"med_{_norm_str(drug)[:60]}"


def _norm_diagnosis(ann: Dict[str, Any], text: str) -> str:
    icd = ann.get("icd10") or ann.get("icd_code") or ann.get("icd") or ""
    if icd:
        return f"icd_{_norm_str(icd)}"
    problem = ann.get("diagnosis") or ann.get("problem") or ann.get("condition") or text
    return f"dx_{_norm_str(problem)[:60]}"


def _norm_imaging(ann: Dict[str, Any], text: str) -> str:
    modality = _norm_str(ann.get("modality") or "")
    region = _norm_str(ann.get("body_region") or ann.get("region") or "")
    if modality or region:
        return f"img_{modality}_{region}".rstrip("_")
    return f"img_{_norm_str(text)[:60]}"


def _norm_procedure(ann: Dict[str, Any], text: str) -> str:
    cpt = ann.get("cpt") or ann.get("cpt_code") or ""
    if cpt:
        return f"cpt_{_norm_str(str(cpt))}"
    proc = ann.get("procedure") or ann.get("procedure_name") or text
    return f"proc_{_norm_str(proc)[:60]}"


def _norm_visit(ts_day: str, ann: Dict[str, Any]) -> str:
    return f"visit_{ts_day}"


_NORM_DISPATCH = {
    "lab":         _norm_lab,
    "medication":  _norm_medication,
    "diagnosis":   _norm_diagnosis,
    "imaging":     _norm_imaging,
    "procedure":   _norm_procedure,
}


def _normalized_label(
    event_type: str,
    text: str,
    annotations: Dict[str, Any],
    ts_day: str,
) -> str:
    if event_type == "visit":
        return _norm_visit(ts_day, annotations)
    fn = _NORM_DISPATCH.get(event_type)
    if fn:
        return fn(annotations, text)
    # Fallback: sha of preview text (symptom, note, flare, …)
    return f"{event_type}_{_sha16(_norm_str(text)[:200])}"


# ── Public API ────────────────────────────────────────────────────────────────

def canonical_event_id(
    patient_id: str,
    event_type: str,
    timestamp: str,
    text: str,
    annotations: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Return a deterministic, collision-resistant event_id.

    The id is stable across ingest runs: uploading the same document twice,
    or finding the same lab in a Tier A artifact and a Tier B 8B extraction,
    produces the same id so ``PatientTimelineVision.add_event`` merges them.

    Format: ``<event_type>_<sha256[:16]>``

    >>> canonical_event_id("user-1", "lab", "2024-01-15", "HbA1c 7.2%",
    ...     {"loinc_code": "4548-4"})
    'lab_...'
    """
    ann = annotations or {}
    ts_day = _utc_day(timestamp)
    label = _normalized_label(event_type, text or "", ann, ts_day)
    coord = f"{patient_id}|{event_type}|{ts_day}|{label}"
    return f"{event_type}_{_sha16(coord)}"


def artifact_id_from_bytes(data: bytes) -> str:
    """Idempotent artifact id: ``art_<sha256[:16]>`` of file bytes."""
    return "art_" + hashlib.sha256(data).hexdigest()[:16]


def artifact_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact_catalog_entry(
    artifact_id: str,
    sha256: str,
    filename: str,
    mime: str,
    size_bytes: int,
    document_type: str,
    document_date: Optional[str],
    user_notes: Optional[str],
    ingest_tier: str,  # "A" | "B"
    pages: Optional[int] = None,
    events_extracted: int = 0,
) -> Dict[str, Any]:
    """Build the catalog dict stored in ``vision.metadata['artifacts']``."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()
    return {
        "artifact_id":      artifact_id,
        "sha256":           sha256,
        "filename":         filename,
        "mime":             mime,
        "size_bytes":       size_bytes,
        "uploaded_at":      now,
        "last_seen_at":     now,
        "document_type":    document_type,
        "document_date":    document_date,
        "user_notes":       user_notes,
        "ingest_tier":      ingest_tier,
        "pages":            pages,
        "events_extracted": events_extracted,
    }
