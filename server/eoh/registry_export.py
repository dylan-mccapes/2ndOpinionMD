"""
registry_export.py — map a finalized PatientTimelineVision into
registry-friendly representations.

Two primary products:

    fhir_bundle = export_fhir_bundle(vision, redact=True)
    series      = export_derived_series(vision)

And two helpers:

    redacted    = redact_vision(vision)        # strip PHI from previews
    hint        = code_mapping_hint(kind, nm)  # tiny built-in code dict

This module is deliberately a compile-step, not a runtime service:
registries (RISE, FORWARD, et al.) ingest static bundles, not live
graphs.  Keep external deps zero — UMLS/RxNorm lookups live behind the
``code_mapping_hint`` stub so a later pass can swap in a real mapper
without touching callers.
"""
from __future__ import annotations

import copy
import hashlib
import logging
import re
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from server.eoh.patient_timeline_vision import (
    PatientTimelineVision,
    TimelineEventVision,
    normalize_graph_preview,
)
from server.utils.parse_date import parse_clinical_date

logger = logging.getLogger(__name__)


# =============================================================================
# Tiny in-process code mapping — extension point for real RxNorm/LOINC/SNOMED.
# =============================================================================
# This is intentionally minimal.  A later pass can replace ``code_mapping_hint``
# with a call to an RxNorm service / LOINC cache / SNOMED lookup.

_DRUG_TO_RXCUI: Dict[str, Tuple[str, str]] = {
    "methotrexate":     ("6851",  "RxNorm"),
    "prednisone":       ("8640",  "RxNorm"),
    "hydroxychloroquine": ("5521", "RxNorm"),
    "rituximab":        ("121191", "RxNorm"),
    "azathioprine":     ("1256",  "RxNorm"),
    "mycophenolate":    ("28889", "RxNorm"),
    "cyclosporine":     ("3008",  "RxNorm"),
    "tacrolimus":       ("42316", "RxNorm"),
    "aspirin":          ("1191",  "RxNorm"),
    "warfarin":         ("11289", "RxNorm"),
    "metformin":        ("6809",  "RxNorm"),
    "atorvastatin":     ("83367", "RxNorm"),
    "lisinopril":       ("29046", "RxNorm"),
    "metoprolol":       ("6918",  "RxNorm"),
    "amlodipine":       ("17767", "RxNorm"),
    "furosemide":       ("4603",  "RxNorm"),
    "omeprazole":       ("7646",  "RxNorm"),
    "gabapentin":       ("25480", "RxNorm"),
    "levothyroxine":    ("10582", "RxNorm"),
    "adalimumab":       ("327361", "RxNorm"),
    "etanercept":       ("214555", "RxNorm"),
    "infliximab":       ("191831", "RxNorm"),
}

_LAB_TO_LOINC: Dict[str, Tuple[str, str]] = {
    "hba1c":       ("4548-4",  "LOINC"),
    "hemoglobin":  ("718-7",   "LOINC"),
    "hgb":         ("718-7",   "LOINC"),
    "wbc":         ("6690-2",  "LOINC"),
    "creatinine":  ("2160-0",  "LOINC"),
    "sodium":      ("2951-2",  "LOINC"),
    "potassium":   ("2823-3",  "LOINC"),
    "glucose":     ("2345-7",  "LOINC"),
    "alt":         ("1742-6",  "LOINC"),
    "ast":         ("1920-8",  "LOINC"),
    "crp":         ("1988-5",  "LOINC"),
    "esr":         ("4537-7",  "LOINC"),
    "tsh":         ("3016-3",  "LOINC"),
    "inr":         ("6301-6",  "LOINC"),
    "psa":         ("2857-1",  "LOINC"),
}

_PROC_TO_SNOMED: Dict[str, Tuple[str, str]] = {
    "colonoscopy":     ("73761001", "SNOMED-CT"),
    "cholecystectomy": ("38102005", "SNOMED-CT"),
    "endoscopy":       ("423827005", "SNOMED-CT"),
    "biopsy":          ("86273004", "SNOMED-CT"),
    "mri":             ("113091000", "SNOMED-CT"),
    "ct scan":         ("77477000", "SNOMED-CT"),
    "echocardiogram":  ("40701008", "SNOMED-CT"),
    "dialysis":        ("108241001", "SNOMED-CT"),
}


def code_mapping_hint(kind: str, name: str) -> Optional[Dict[str, str]]:
    """Return ``{"system": ..., "code": ..., "display": ...}`` or None.

    Kinds: "drug", "lab", "procedure".  Unknown kind or name → None.
    """
    if not name:
        return None
    key = name.strip().lower()
    if kind == "drug":
        hit = _DRUG_TO_RXCUI.get(key)
    elif kind == "lab":
        hit = _LAB_TO_LOINC.get(key)
    elif kind == "procedure":
        hit = _PROC_TO_SNOMED.get(key)
    else:
        return None
    if not hit:
        return None
    code, system = hit
    return {"system": system, "code": code, "display": name}


# =============================================================================
# De-identification
# =============================================================================

# Conservative patterns.  We only strip what's unambiguously PHI.
_PHONE_RX = re.compile(r"\b\d{3}[\s\.\-]\d{3}[\s\.\-]\d{4}\b")
_EMAIL_RX = re.compile(r"[\w\.\-]+@[\w\.\-]+\.[a-z]{2,4}", re.I)
_MRN_RX = re.compile(r"\bMRN\s*[:\-]?\s*[A-Z0-9\-]{4,20}", re.I)
_DOB_RX = re.compile(r"\b(?:dob|born|date\s+of\s+birth)\b[^\n]{0,40}", re.I)
_ADDRESS_RX = re.compile(r"\b\d+\s+[A-Z][a-zA-Z]+\s+(?:St|Street|Ave|Avenue|Rd|Road|Blvd|Boulevard|Dr|Drive|Ln|Lane|Way|Pl|Place|Ct|Court)\b")
# Capitalized two-word names after common triggers.
_NAME_AFTER_RX = re.compile(r"(?:patient|name|by|signed|attending|provider)\s*[:\-]?\s*([A-Z][A-Za-z'\-]+\s+[A-Z][A-Za-z'\-]+)")


def _redact_text(text: str) -> str:
    if not text:
        return text
    text = _PHONE_RX.sub("[PHONE]", text)
    text = _EMAIL_RX.sub("[EMAIL]", text)
    text = _MRN_RX.sub("MRN[REDACTED]", text)
    text = _DOB_RX.sub("[DOB-REDACTED]", text)
    text = _ADDRESS_RX.sub("[ADDRESS]", text)
    text = _NAME_AFTER_RX.sub(lambda m: m.group(0).replace(m.group(1), "[NAME]"), text)
    return text


def redact_vision(vision: PatientTimelineVision) -> PatientTimelineVision:
    """Return a deep-copy of ``vision`` with previews / cards / patient_phi
    scrubbed of common PHI patterns.

    Event IDs, timestamps, codes, and structural metadata are untouched —
    those are what registries care about.
    """
    out = PatientTimelineVision.from_dict(copy.deepcopy(vision.to_dict()))
    # Drop the PHI block outright.
    out.metadata.pop("patient_phi", None)
    # Redact previews and card fields.
    for ev in out.events.values():
        ev.preview = normalize_graph_preview(_redact_text(ev.preview))
        card = (ev.annotations or {}).get("card")
        if isinstance(card, dict):
            card["title"] = _redact_text(card.get("title") or "")
            card["one_line"] = _redact_text(card.get("one_line") or "")
    out.metadata.setdefault("redaction", {})["redacted_at"] = datetime.utcnow().isoformat() + "Z"
    return out


# =============================================================================
# Derived longitudinal series
# =============================================================================

def export_derived_series(vision: PatientTimelineVision) -> Dict[str, Any]:
    """Compile per-entity longitudinal series from the graph.

    Returns::

        {
          "labs": { "hba1c": [ {"ts": ..., "value": ..., "unit": ...}, ... ] },
          "meds": { "methotrexate": [ {"start": ..., "end": ..., "dose": ..., "status": ...} ] },
          "pros": { "RAPID3": [ {"ts": ..., "value": ...} ] },
          "diagnoses": { "I48": [ {"ts": ..., "icd": ..., "preview": ...} ] },
        }
    """
    labs: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    meds: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    pros: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    diagnoses: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    _numeric_rx = re.compile(r"(-?\d+(?:\.\d+)?)")

    for eid, ev in vision.events.items():
        ann = ev.annotations or {}
        ts = ev.timestamp if ev.timestamp else "unknown"

        if ev.event_type == "lab":
            # Best-effort: if preview contains a numeric value, capture it.
            m = _numeric_rx.search(ev.preview or "")
            # Attach to any known lab entity keys
            for key in ann.get("entity_keys") or []:
                if not key.startswith("lab:"):
                    continue
                name = key.split(":", 1)[1]
                labs[name].append({
                    "ts": ts,
                    "value": float(m.group(1)) if m else None,
                    "raw": ev.preview,
                    "event_id": eid,
                })

        elif ev.event_type in ("medication", "immunization"):
            name = ann.get("drug_name") or ""
            if not name:
                continue
            meds[name.strip().lower()].append({
                "start": ts,
                "end": None,  # Without explicit stop dates we can't infer.
                "dose": ann.get("drug_dosage"),
                "route": ann.get("drug_route"),
                "status": (ann.get("status_flags") or [None])[0],
                "event_id": eid,
            })

        elif ev.event_type == "pro":
            inst = ann.get("instrument") or "unknown"
            pros[inst].append({
                "ts": ts,
                "value": ann.get("value"),
                "units": ann.get("units"),
                "event_id": eid,
            })

        elif ev.event_type == "diagnosis":
            icd = ann.get("icd_code") or ""
            fam = icd[:3] if icd else "unknown"
            diagnoses[fam].append({
                "ts": ts,
                "icd": icd,
                "preview": ev.preview,
                "event_id": eid,
            })

    # Sort each series by timestamp.
    def _sort_key(row: Dict[str, Any]) -> str:
        return str(row.get("ts") or row.get("start") or "")

    for series in (labs, meds, pros, diagnoses):
        for k in list(series.keys()):
            series[k].sort(key=_sort_key)

    return {
        "labs": dict(labs),
        "meds": dict(meds),
        "pros": dict(pros),
        "diagnoses": dict(diagnoses),
    }


# =============================================================================
# FHIR R4 export
# =============================================================================

def _fhir_ts(ts: str) -> Optional[str]:
    if not ts or ts.lower() in ("unknown", "n/a"):
        return None
    dt = parse_clinical_date(ts)
    if dt is None:
        # Already YYYY-MM-DD?
        if re.match(r"^\d{4}-\d{2}-\d{2}$", ts):
            return ts
        return None
    return dt.strftime("%Y-%m-%d")


def _patient_resource(vision: PatientTimelineVision, *, redact: bool) -> Dict[str, Any]:
    patient = vision.metadata.get("patient") or {}
    phi = vision.metadata.get("patient_phi") or {}
    res: Dict[str, Any] = {
        "resourceType": "Patient",
        "id": vision.patient_id or "unknown",
    }
    if not redact and phi.get("name"):
        parts = phi["name"].split()
        res["name"] = [{"family": parts[-1], "given": parts[:-1]}]
    if patient.get("dob"):
        if redact:
            res["birthDate"] = patient["dob"][:4]  # year only
        else:
            res["birthDate"] = patient["dob"]
    if patient.get("sex"):
        res["gender"] = patient["sex"]
    if patient.get("zip3"):
        res["address"] = [{"postalCode": patient["zip3"]}]
    if patient.get("smoking_status"):
        res["extension"] = [{
            "url": "http://hl7.org/fhir/us/core/StructureDefinition/us-core-smokingstatus",
            "valueCodeableConcept": {"text": patient["smoking_status"]},
        }]
    return res


def _condition_resource(ev: TimelineEventVision, patient_id: str) -> Dict[str, Any]:
    ann = ev.annotations or {}
    icd = ann.get("icd_code")
    res: Dict[str, Any] = {
        "resourceType": "Condition",
        "id": f"cond-{ev.event_id}",
        "subject": {"reference": f"Patient/{patient_id}"},
    }
    if icd:
        res["code"] = {
            "coding": [{"system": "http://hl7.org/fhir/sid/icd-10-cm", "code": icd}],
            "text": ev.preview,
        }
    else:
        res["code"] = {"text": ev.preview}
    ts = _fhir_ts(ev.timestamp)
    if ts:
        res["recordedDate"] = ts
    # clinical status from status_flags.
    flags = set(ann.get("status_flags") or [])
    if "resolved" in flags:
        res["clinicalStatus"] = {"coding": [{"code": "resolved"}]}
    elif "chronic" in flags or "continued" in flags:
        res["clinicalStatus"] = {"coding": [{"code": "active"}]}
    return res


def _medication_resource(ev: TimelineEventVision, patient_id: str) -> Dict[str, Any]:
    ann = ev.annotations or {}
    drug = ann.get("drug_name") or ""
    code = code_mapping_hint("drug", drug) if drug else None
    res: Dict[str, Any] = {
        "resourceType": "MedicationStatement",
        "id": f"med-{ev.event_id}",
        "subject": {"reference": f"Patient/{patient_id}"},
        "status": "stopped" if "stopped" in (ann.get("status_flags") or []) else "active",
        "medicationCodeableConcept": {
            "text": ev.preview,
            **({"coding": [code]} if code else {}),
        },
    }
    ts = _fhir_ts(ev.timestamp)
    if ts:
        res["effectiveDateTime"] = ts
    if ann.get("drug_dosage"):
        res["dosage"] = [{"text": ann["drug_dosage"], "route": {"text": ann.get("drug_route") or ""}}]
    return res


def _observation_resource(ev: TimelineEventVision, patient_id: str) -> Dict[str, Any]:
    ann = ev.annotations or {}
    # Prefer a mapped LOINC code if the lab name is known.
    lab_name = None
    for key in ann.get("entity_keys") or []:
        if key.startswith("lab:"):
            lab_name = key.split(":", 1)[1]
            break
    code = code_mapping_hint("lab", lab_name) if lab_name else None
    res: Dict[str, Any] = {
        "resourceType": "Observation",
        "id": f"obs-{ev.event_id}",
        "subject": {"reference": f"Patient/{patient_id}"},
        "status": "final",
        "code": {"text": ev.preview, **({"coding": [code]} if code else {})},
    }
    ts = _fhir_ts(ev.timestamp)
    if ts:
        res["effectiveDateTime"] = ts
    if ev.event_type == "pro":
        res["category"] = [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/observation-category", "code": "survey"}]}]
        if ann.get("value") is not None:
            res["valueQuantity"] = {
                "value": ann["value"],
                "unit": ann.get("units") or "",
            }
        res["code"] = {"text": ann.get("instrument") or ev.preview}
    return res


def _procedure_resource(ev: TimelineEventVision, patient_id: str) -> Dict[str, Any]:
    ann = ev.annotations or {}
    proc_name = None
    for key in ann.get("entity_keys") or []:
        if key.startswith("procedure:"):
            proc_name = key.split(":", 1)[1]
            break
    code = code_mapping_hint("procedure", proc_name) if proc_name else None
    res: Dict[str, Any] = {
        "resourceType": "Procedure",
        "id": f"proc-{ev.event_id}",
        "subject": {"reference": f"Patient/{patient_id}"},
        "status": "completed",
        "code": {"text": ev.preview, **({"coding": [code]} if code else {})},
    }
    ts = _fhir_ts(ev.timestamp)
    if ts:
        res["performedDateTime"] = ts
    return res


def _encounter_resources(vision: PatientTimelineVision, patient_id: str) -> List[Dict[str, Any]]:
    """Build an Encounter resource per distinct (encounter_date, encounter_type)."""
    buckets: Dict[Tuple[str, str], List[str]] = defaultdict(list)
    for eid, ev in vision.events.items():
        ann = ev.annotations or {}
        enc = ann.get("encounter_date")
        if not enc:
            continue
        buckets[(str(enc), str(ann.get("encounter_type") or "encounter"))].append(eid)

    out: List[Dict[str, Any]] = []
    for (enc_date, enc_type), eids in buckets.items():
        if not eids:
            continue
        h = hashlib.sha1(f"{patient_id}|{enc_date}|{enc_type}".encode()).hexdigest()[:10]
        out.append({
            "resourceType": "Encounter",
            "id": f"enc-{h}",
            "subject": {"reference": f"Patient/{patient_id}"},
            "status": "finished",
            "class": {"code": enc_type},
            "period": {"start": enc_date, "end": enc_date},
            "reasonCode": [{"text": f"{len(eids)} related events"}],
        })
    return out


def export_fhir_bundle(
    vision: PatientTimelineVision,
    *,
    redact: bool = False,
    include_administrative: bool = False,
) -> Dict[str, Any]:
    """Produce a FHIR R4 Bundle (searchset) from the graph.

    Resources produced:
      - 1 Patient
      - N Condition (from diagnosis events)
      - N MedicationStatement (from medication/immunization)
      - N Observation (from lab/vital_signs/pro events)
      - N Procedure
      - N Encounter

    Use ``redact=True`` to drop names/MRN/full DOB/etc.  Suppressed admin
    events are excluded unless ``include_administrative=True``.
    """
    src = redact_vision(vision) if redact else vision
    pid = src.patient_id or "unknown"

    entries: List[Dict[str, Any]] = []
    entries.append({"resource": _patient_resource(src, redact=redact)})

    for ev in src.events.values():
        if ev.status == "suppressed" and not include_administrative:
            continue
        et = ev.event_type
        if et == "diagnosis":
            entries.append({"resource": _condition_resource(ev, pid)})
        elif et in ("medication", "immunization"):
            entries.append({"resource": _medication_resource(ev, pid)})
        elif et in ("lab", "vital_signs", "pro"):
            entries.append({"resource": _observation_resource(ev, pid)})
        elif et == "procedure":
            entries.append({"resource": _procedure_resource(ev, pid)})

    for enc in _encounter_resources(src, pid):
        entries.append({"resource": enc})

    return {
        "resourceType": "Bundle",
        "type": "collection",
        "meta": {
            "profile": ["http://hl7.org/fhir/StructureDefinition/Bundle"],
            "extension": [{
                "url": "https://2ndopinionmd.com/fhir/extensions/source",
                "valueString": "PatientTimelineVision",
            }],
        },
        "total": len(entries),
        "entry": entries,
    }
