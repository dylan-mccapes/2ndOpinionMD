"""
code_index_ops.py — read/write operations on ``metadata.code_index``.

The flat code index at ``vision.metadata['code_index']`` is the
authoritative per-code chronology consumed by agents (drugs, rxnorm,
icd, labs, loinc).  It is initially built by
``graph_finalize._build_code_index`` from the heuristic extractor output
and refreshed by the opportunistic LLM enrichment pass.

When an agent (or a deterministic patch) adds a code to an event that
the regex missed, the event's annotations are no longer in sync with the
index.  Every such mutation must be paired with an index upsert — that
is the contract this module makes explicit.

Public API
----------

``derive_event_code_entries(event_id, ev)``
    Pure function.  Returns the rows this event contributes to each
    code-index bucket, derived from its current annotations.  Used by
    both the full-build pass and the single-event upsert.

``upsert_event_in_code_index(graph, event_id)``
    Remove every row for ``event_id`` from every bucket and reinsert
    the freshly-derived rows in chronological order.  Idempotent.
    The argument is either a ``PatientTimelineVision`` or the plain
    ``dict`` shape we serialize to disk — duck-typed.

``register_code_on_event(graph, event_id, ..., provenance="agent")``
    Agent-facing convenience that (a) merges the supplied fields into
    ``ev.annotations`` without clobbering existing values, (b) appends
    a provenance breadcrumb to ``ev.discovered_by`` / ``ev.annotations
    ['enriched_by']``, and (c) calls ``upsert_event_in_code_index``.

``rebuild_code_index(graph)``
    Full rebuild from scratch — the same logic
    ``_build_code_index`` uses, just surfaced here so both callsites
    share one implementation and any later refinement lands in one
    place.

Contract for agent code
-----------------------
If you write ``drug_name`` / ``icd_code`` / ``lab_name`` (or the dose /
value / unit / flag companions) to an event, you MUST follow it with
``register_code_on_event(...)`` or, at minimum,
``upsert_event_in_code_index(graph, event_id)``.  The enrichment agent
prompts explicitly teach this.
"""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from server.eoh import code_mappings

__all__ = [
    "derive_event_code_entries",
    "upsert_event_in_code_index",
    "register_code_on_event",
    "rebuild_code_index",
]


# =============================================================================
# Helpers
# =============================================================================

_ICD_IN_PREVIEW_RX = re.compile(r"\b([A-TV-Z]\d{2}(?:\.\d{1,3})?)\b")

_LAB_UNIT_TOKEN = (
    r"mg/dL|mg/dl|g/dL|g/dl|mEq/L|meq/l|mmol/L|mmol/l|U/L|u/l|IU/L|iu/l|"
    r"ng/mL|ng/ml|pg/mL|pg/ml|mIU/L|miu/l|mcg/dL|mcg/dl|seconds|sec|"
    r"K/uL|k/ul|K/µL|x10\^?\d*/L|/uL|/ul|%"
)
_LAB_VALUE_RX = re.compile(
    rf"(?P<val>\d+(?:\.\d+)?)\s*"
    rf"(?P<unit>{_LAB_UNIT_TOKEN})"
    rf"\s*(?:\((?P<flag>H|L|HIGH|LOW|A)\))?",
    re.IGNORECASE,
)


def _icd_family(code: str) -> str:
    return code.split(".", 1)[0] if code else ""


def _parse_lab_value_from_preview(preview: str) -> Tuple[str, str, str]:
    if not preview:
        return ("", "", "")
    m = _LAB_VALUE_RX.search(preview)
    if not m:
        return ("", "", "")
    return (
        m.group("val") or "",
        (m.group("unit") or "").strip(),
        (m.group("flag") or "").strip().upper(),
    )


def _getf(ev: Any, key: str, default: Any = None) -> Any:
    """Read ``ev[key]`` for dicts or ``ev.key`` for attribute-shaped objects."""
    if isinstance(ev, dict):
        return ev.get(key, default)
    return getattr(ev, key, default)


def _annotations(ev: Any) -> Dict[str, Any]:
    """Return the event's annotations dict, creating one if missing."""
    if isinstance(ev, dict):
        ann = ev.get("annotations")
        if ann is None:
            ann = {}
            ev["annotations"] = ann
        return ann
    ann = getattr(ev, "annotations", None)
    if ann is None:
        ann = {}
        try:
            setattr(ev, "annotations", ann)
        except Exception:
            pass
    return ann


def _iter_events(graph: Any):
    """Yield ``(event_id, ev)`` pairs for either a vision object or a dict."""
    events = _getf(graph, "events") or {}
    if isinstance(events, dict):
        yield from events.items()


def _get_event(graph: Any, event_id: str) -> Optional[Any]:
    events = _getf(graph, "events") or {}
    if isinstance(events, dict):
        return events.get(event_id)
    return None


def _metadata(graph: Any) -> Dict[str, Any]:
    md = _getf(graph, "metadata")
    if md is None:
        # Vision-shaped objects always have metadata; dicts we create it.
        if isinstance(graph, dict):
            md = {}
            graph["metadata"] = md
        else:
            md = {}
            try:
                setattr(graph, "metadata", md)
            except Exception:
                pass
    return md


def _code_index(graph: Any) -> Dict[str, Dict[str, List[Dict[str, Any]]]]:
    """Return (and lazily create) the ``metadata.code_index`` dict."""
    md = _metadata(graph)
    ci = md.get("code_index")
    if not isinstance(ci, dict):
        ci = {"drugs": {}, "rxnorm": {}, "icd": {}, "labs": {}, "loinc": {}}
        md["code_index"] = ci
    # Ensure all five buckets exist.
    for k in ("drugs", "rxnorm", "icd", "labs", "loinc"):
        if k not in ci or not isinstance(ci[k], dict):
            ci[k] = {}
    return ci


# =============================================================================
# Pure derivation — what entries does a single event contribute?
# =============================================================================

def derive_event_code_entries(event_id: str, ev: Any) -> Dict[str, List[Tuple[str, Dict[str, Any]]]]:
    """Return the code-index rows this event contributes, derived from
    its current annotations.

    Shape::

        {
          "drugs":  [(normalized_drug_name, entry), ...],
          "rxnorm": [(rxcui, entry), ...],
          "icd":    [(icd_code, entry), ...],
          "labs":   [(normalized_lab_name, entry), ...],
          "loinc":  [(loinc_code, entry), ...],
        }

    Each ``entry`` always carries ``event_id`` and ``timestamp`` so the
    single-event upsert can delete prior rows for this event.
    """
    ann = _annotations(ev) or {}
    ts = _getf(ev, "timestamp") or ""
    preview = _getf(ev, "preview") or ""
    etype = _getf(ev, "event_type") or ""

    out: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {
        "drugs": [], "rxnorm": [], "icd": [], "labs": [], "loinc": [],
    }

    # ---- Drugs --------------------------------------------------------------
    drug_name = ann.get("drug_name")
    if drug_name:
        key = code_mappings.normalize_drug_name(drug_name) or str(drug_name).strip().lower()
        if key:
            rx = code_mappings.lookup_rxnorm(drug_name)
            entry: Dict[str, Any] = {
                "event_id": event_id,
                "timestamp": ts,
                "drug": str(drug_name).strip(),
                "dose":   ann.get("drug_dosage") or ann.get("dose")   or "",
                "route":  ann.get("drug_route")  or ann.get("route")  or "",
                "status": ann.get("drug_status") or ann.get("status") or "",
            }
            if rx:
                entry["rxnorm"] = rx
            out["drugs"].append((key, entry))
            if rx:
                out["rxnorm"].append((rx, {
                    "event_id": event_id,
                    "timestamp": ts,
                    "drug": key,
                    "dose": entry["dose"],
                    "route": entry["route"],
                }))

    # ---- ICD ----------------------------------------------------------------
    icd_code = ann.get("icd_code")
    if not icd_code:
        m = _ICD_IN_PREVIEW_RX.search(preview)
        if m:
            icd_code = m.group(1)
    if icd_code:
        code_u = str(icd_code).upper()
        entry = {
            "event_id": event_id,
            "timestamp": ts,
            "family": _icd_family(code_u),
        }
        desc = (
            ann.get("icd_description")
            or ann.get("problem")
            or ann.get("dx_description")
        )
        if desc:
            entry["description"] = str(desc).strip()
        status = ann.get("problem_status") or ann.get("status")
        if status:
            entry["status"] = str(status).strip()
        out["icd"].append((code_u, entry))

    # ---- Labs ---------------------------------------------------------------
    lab_names: List[str] = []
    if ann.get("lab_name"):
        lab_names.append(str(ann["lab_name"]))
    for ek in (ann.get("entity_keys") or []):
        if isinstance(ek, str) and ek.startswith("lab:"):
            lab_names.append(ek.split(":", 1)[1])
    lab_names = list(dict.fromkeys([n for n in lab_names if n]))

    if lab_names or etype == "lab":
        parsed_val, parsed_unit, parsed_flag = _parse_lab_value_from_preview(preview)
        for lab_name in lab_names:
            key = code_mappings.normalize_lab_name(lab_name) or str(lab_name).strip().lower()
            if not key:
                continue
            lo = code_mappings.lookup_loinc(lab_name)
            entry = {
                "event_id": event_id,
                "timestamp": ts,
                "lab": str(lab_name).strip(),
                "value": ann.get("lab_value") or ann.get("value") or parsed_val or "",
                "unit":  ann.get("lab_unit")  or ann.get("unit")  or parsed_unit or "",
            }
            flag = (
                ann.get("lab_flag")
                or ann.get("flag")
                or ann.get("abnormal_flag")
                or parsed_flag
            )
            if flag:
                entry["flag"] = str(flag).strip()
            ref = ann.get("lab_reference") or ann.get("reference_range")
            if ref:
                entry["reference_range"] = str(ref).strip()
            if lo:
                entry["loinc"] = lo
            out["labs"].append((key, entry))
            if lo:
                out["loinc"].append((lo, {
                    "event_id": event_id,
                    "timestamp": ts,
                    "lab": key,
                    "value": entry["value"],
                    "unit": entry["unit"],
                    **({"flag": entry["flag"]} if "flag" in entry else {}),
                }))

    return out


# =============================================================================
# Full rebuild
# =============================================================================

def rebuild_code_index(graph: Any) -> Dict[str, int]:
    """Rebuild ``metadata.code_index`` from every event.  Idempotent."""
    buckets: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        "drugs":  defaultdict(list),
        "rxnorm": defaultdict(list),
        "icd":    defaultdict(list),
        "labs":   defaultdict(list),
        "loinc":  defaultdict(list),
    }
    for eid, ev in _iter_events(graph):
        entries = derive_event_code_entries(eid, ev)
        for bucket_name, rows in entries.items():
            for key, row in rows:
                buckets[bucket_name][key].append(row)

    for b in buckets.values():
        for rows in b.values():
            rows.sort(key=lambda r: r.get("timestamp") or "\uffff")

    md = _metadata(graph)
    md["code_index"] = {k: dict(v) for k, v in buckets.items()}

    return {
        "drug_names":  len(md["code_index"]["drugs"]),
        "rxnorm":      len(md["code_index"]["rxnorm"]),
        "icd_codes":   len(md["code_index"]["icd"]),
        "lab_names":   len(md["code_index"]["labs"]),
        "loinc":       len(md["code_index"]["loinc"]),
        "drug_events": sum(len(v) for v in md["code_index"]["drugs"].values()),
        "icd_events":  sum(len(v) for v in md["code_index"]["icd"].values()),
        "lab_events":  sum(len(v) for v in md["code_index"]["labs"].values()),
    }


# =============================================================================
# Single-event upsert
# =============================================================================

def _strip_event_from_bucket(
    bucket: Dict[str, List[Dict[str, Any]]],
    event_id: str,
) -> int:
    """Remove every row with ``event_id`` from every key in ``bucket``.

    Keys that end up empty are dropped so we don't accumulate empty lists.
    """
    removed = 0
    empty_keys: List[str] = []
    for key, rows in bucket.items():
        kept = [r for r in rows if r.get("event_id") != event_id]
        if len(kept) != len(rows):
            removed += len(rows) - len(kept)
        if kept:
            bucket[key] = kept
        else:
            empty_keys.append(key)
    for k in empty_keys:
        bucket.pop(k, None)
    return removed


def upsert_event_in_code_index(graph: Any, event_id: str) -> Dict[str, int]:
    """Re-derive ``event_id``'s code_index rows and replace any stale ones.

    Intended to be called by every code path that mutates an event's
    ``drug_name`` / ``icd_code`` / ``lab_name`` / dose / value / unit / flag.
    Idempotent — calling twice in a row on the same event is a no-op on
    the second call.
    """
    ev = _get_event(graph, event_id)
    if ev is None:
        return {"removed": 0, "inserted": 0, "missing_event": 1}

    ci = _code_index(graph)

    # 1. Remove every existing row for this event_id from every bucket.
    removed = 0
    for bucket_name in ("drugs", "rxnorm", "icd", "labs", "loinc"):
        removed += _strip_event_from_bucket(ci[bucket_name], event_id)

    # 2. Derive fresh rows and insert them in chronological order.
    inserted = 0
    entries = derive_event_code_entries(event_id, ev)
    for bucket_name, rows in entries.items():
        bucket = ci[bucket_name]
        for key, row in rows:
            lst = bucket.setdefault(key, [])
            lst.append(row)
            # Keep the bucket chronologically sorted; cheap because
            # most buckets are small and already mostly sorted.
            lst.sort(key=lambda r: r.get("timestamp") or "\uffff")
            inserted += 1

    return {"removed": removed, "inserted": inserted}


# =============================================================================
# Agent-facing write + upsert
# =============================================================================

def register_code_on_event(
    graph: Any,
    event_id: str,
    *,
    drug_name: Optional[str] = None,
    drug_dosage: Optional[str] = None,
    drug_route: Optional[str] = None,
    drug_status: Optional[str] = None,
    icd_code: Optional[str] = None,
    icd_description: Optional[str] = None,
    problem_status: Optional[str] = None,
    lab_name: Optional[str] = None,
    lab_value: Optional[str] = None,
    lab_unit: Optional[str] = None,
    lab_flag: Optional[str] = None,
    lab_reference: Optional[str] = None,
    provenance: str = "agent",
    overwrite: bool = False,
) -> Dict[str, Any]:
    """Write agent-discovered codes onto an event and refresh the index.

    Behavior
    --------
    * Writes each non-``None`` field into ``ev.annotations[<field>]``.
    * When ``overwrite=False`` (default) an existing non-empty value is
      preserved and the new value is dropped — agents supplement, they
      don't overwrite heuristic output unless they have to.
    * Appends ``provenance`` (e.g. ``"agent:ogre-enrichment"``) to
      ``ev.annotations['enriched_by']`` (deduped).
    * Calls :func:`upsert_event_in_code_index` once.

    Returns a report with the applied / skipped field list and the
    upsert's ``{removed, inserted}`` counts.
    """
    ev = _get_event(graph, event_id)
    if ev is None:
        return {"missing_event": event_id, "applied": [], "skipped": []}

    ann = _annotations(ev)

    fields: Dict[str, Optional[str]] = {
        "drug_name":        drug_name,
        "drug_dosage":      drug_dosage,
        "drug_route":       drug_route,
        "drug_status":      drug_status,
        "icd_code":         (icd_code.upper() if isinstance(icd_code, str) else icd_code),
        "icd_description":  icd_description,
        "problem_status":   problem_status,
        "lab_name":         lab_name,
        "lab_value":        lab_value,
        "lab_unit":         lab_unit,
        "lab_flag":         lab_flag,
        "lab_reference":    lab_reference,
    }

    applied: List[str] = []
    skipped: List[str] = []
    for k, v in fields.items():
        if v is None or v == "":
            continue
        existing = ann.get(k)
        if existing in (None, "", []):
            ann[k] = v
            applied.append(k)
        elif overwrite and existing != v:
            ann[k] = v
            applied.append(k + ":overwritten")
        else:
            skipped.append(k)

    if applied:
        enriched = list(ann.get("enriched_by") or [])
        if provenance and provenance not in enriched:
            enriched.append(provenance)
            ann["enriched_by"] = enriched

    upsert = upsert_event_in_code_index(graph, event_id)

    return {
        "event_id": event_id,
        "applied":  applied,
        "skipped":  skipped,
        "upsert":   upsert,
        "provenance": provenance,
    }
